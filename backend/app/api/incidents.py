from fastapi import APIRouter, Depends, HTTPException
from fastapi import File, UploadFile
from sqlalchemy.orm import Session
import uuid

from app.db.dependencies import get_db
from app.models.incident import Incident
from app.models.evidence import IncidentEvidence
from app.schemas.incident import IncidentCreate, IncidentResponse, IncidentUpdate
from app.services.incident import can_transition_status
from app.schemas.evidence import (
    EvidenceCreate,
    EvidenceResponse,
    EvidenceURLResponse,
)
from app.clients.supabase import supabase



router = APIRouter()

@router.post("/incidents")
def create_incident(incident: IncidentCreate, db: Session = Depends(get_db),):
    new_incident = Incident(
        description=incident.description,
        latitude=incident.latitude,
        longitude=incident.longitude,
    )

    db.add(new_incident)
    db.commit()
    db.refresh(new_incident)

    return new_incident

@router.get("/incidents", response_model=list[IncidentResponse])
def get_incidents(db: Session = Depends(get_db)):
    incidents = db.query(Incident).all()
    return incidents

@router.get("/incidents/{incident_id}", response_model=IncidentResponse)
def get_incident(incident_id: int, db: Session = Depends(get_db),):
    incident = db.query(Incident).filter(Incident.id == incident_id).first()

    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found")

    return incident

@router.patch("/incidents/{incident_id}", response_model=IncidentResponse)
def update_incident(
    incident_id: int,
    incident_update: IncidentUpdate,
    db: Session = Depends(get_db),
):
    incident = db.query(Incident).filter(Incident.id == incident_id).first()

    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found")

    update_data = incident_update.model_dump(exclude_unset=True)

    if "status" in update_data:
        new_status = update_data["status"]

        if not can_transition_status(incident.status, new_status):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status transition: {incident.status.value} -> {new_status.value}",
            )

    for field, value in update_data.items():
        setattr(incident, field, value)

    db.commit()
    db.refresh(incident)

    return incident

@router.delete("/incidents/{incident_id}", status_code=204)
def delete_incident(incident_id: int, db: Session = Depends(get_db)):
    incident = db.query(Incident).filter(Incident.id == incident_id).first()

    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found")

    db.delete(incident)
    db.commit()

@router.post(
    "/incidents/{incident_id}/evidence",
    response_model=EvidenceResponse,
)
def create_evidence(
    incident_id: int,
    evidence: EvidenceCreate,
    db: Session = Depends(get_db),
):
    incident = (
        db.query(Incident)
        .filter(Incident.id == incident_id)
        .first()
    )

    if incident is None:
        raise HTTPException(
            status_code=404,
            detail="Incident not found",
        )

    new_evidence = IncidentEvidence(
        incident_id=incident_id,
        storage_path=evidence.storage_path,
        file_type=evidence.file_type,
    )

    db.add(new_evidence)
    db.commit()
    db.refresh(new_evidence)

    return new_evidence


@router.get(
    "/incidents/{incident_id}/evidence",
    response_model=list[EvidenceResponse],
)
def get_incident_evidence(
    incident_id: int,
    db: Session = Depends(get_db),
):
    incident = (
        db.query(Incident)
        .filter(Incident.id == incident_id)
        .first()
    )

    if incident is None:
        raise HTTPException(
            status_code=404,
            detail="Incident not found",
        )

    evidence = (
        db.query(IncidentEvidence)
        .filter(IncidentEvidence.incident_id == incident_id)
        .all()
    )

    return evidence

@router.post(
    "/incidents/{incident_id}/evidence/upload",
    response_model=EvidenceResponse,
)
def upload_evidence(
    incident_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    incident = (
        db.query(Incident)
        .filter(Incident.id == incident_id)
        .first()
    )

    if incident is None:
        raise HTTPException(
            status_code=404,
            detail="Incident not found",
        )

    if file.content_type not in [
        "image/jpeg",
        "image/png",
        "image/webp",
    ]:
        raise HTTPException(
            status_code=400,
            detail="Unsupported image type",
        )

    file_extension = file.filename.split(".")[-1].lower()

    storage_path = (
        f"incidents/{incident_id}/{uuid.uuid4()}.{file_extension}"
    )

    file_bytes = file.file.read()

    max_file_size = 10 * 1024 * 1024

    if len(file_bytes) > max_file_size:
        raise HTTPException(
            status_code=400,
            detail="File size must be 10 MB or less",
        )

    try:
        supabase.storage.from_("civiclens-evidence").upload(
            storage_path,
            file_bytes,
            {
                "content-type": file.content_type,
            },
        )

        new_evidence = IncidentEvidence(
            incident_id=incident_id,
            storage_path=storage_path,
            file_type=file.content_type,
        )

        db.add(new_evidence)
        db.commit()
        db.refresh(new_evidence)

        return new_evidence

    except Exception:
        db.rollback()

        try:
            supabase.storage.from_("civiclens-evidence").remove(
                [storage_path]
            )
        except Exception:
            pass

        raise HTTPException(
            status_code=500,
            detail="Failed to upload evidence",
        )

@router.get(
    "/incidents/{incident_id}/evidence/{evidence_id}/url",
    response_model=EvidenceURLResponse,
)
def get_evidence_url(
    incident_id: int,
    evidence_id: int,
    db: Session = Depends(get_db),
):
    evidence = (
        db.query(IncidentEvidence)
        .filter(
            IncidentEvidence.id == evidence_id,
            IncidentEvidence.incident_id == incident_id,
        )
        .first()
    )

    if evidence is None:
        raise HTTPException(
            status_code=404,
            detail="Evidence not found",
        )

    signed_url_response = (
        supabase.storage
        .from_("civiclens-evidence")
        .create_signed_url(
            evidence.storage_path,
            3600,
        )
    )

    return {
        "url": signed_url_response["signedURL"],
    }
