from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.config import get_pothole_model_path
from app.db.dependencies import get_db
from app.schemas.report import ReportResponse
from app.schemas.report import ReportDetailResponse, ReportListItem
from app.models.analysis import EvidenceAnalysis
from app.models.evidence import IncidentEvidence
from app.models.incident import Incident
from app.services.analysis import AnalysisService
from app.services.pothole_detector import PotholeDetector
from app.services.report import ReportService, ReportValidationError
from app.services.storage import create_evidence_signed_url
from app.services.rate_limit import limit_report_submission

router = APIRouter(tags=["reports"])


@router.get("/reports", response_model=list[ReportListItem])
def get_reports(db: Session = Depends(get_db)):
    """List reports for the current unauthenticated v1 deployment.

    Authentication and report ownership have not been introduced yet, so this
    endpoint remains public like the existing incident API.
    """
    incidents = db.query(Incident).order_by(Incident.created_at.desc()).all()
    return [
        ReportListItem(
            report_id=incident.id,
            description=incident.description,
            category=incident.category,
            severity=incident.severity,
            status=incident.status,
            created_at=incident.created_at,
        )
        for incident in incidents
    ]


@router.get("/reports/{report_id}", response_model=ReportDetailResponse)
def get_report(report_id: int, db: Session = Depends(get_db)):
    """Retrieve persisted evidence and analysis for citizen report tracking."""
    incident = db.query(Incident).filter(Incident.id == report_id).first()
    if incident is None:
        raise HTTPException(status_code=404, detail="Report not found")

    evidence = (
        db.query(IncidentEvidence)
        .filter(IncidentEvidence.incident_id == report_id)
        .order_by(IncidentEvidence.created_at.desc())
        .first()
    )
    analysis = None
    evidence_url = None
    if evidence is not None:
        analysis = (
            db.query(EvidenceAnalysis)
            .filter(EvidenceAnalysis.evidence_id == evidence.id)
            .order_by(EvidenceAnalysis.created_at.desc())
            .first()
        )
        evidence_url = create_evidence_signed_url(evidence.storage_path)

    return ReportDetailResponse(
        report_id=incident.id,
        incident=incident,
        evidence=evidence,
        evidence_url=evidence_url,
        analysis=analysis,
    )


@router.post("/reports", response_model=ReportResponse, status_code=201)
def submit_report(
    _: None = Depends(limit_report_submission),
    description: str = Form(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    photo: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Submit one citizen pothole report and return its completed assessment."""
    service = ReportService(
        AnalysisService(detector=PotholeDetector(get_pothole_model_path()))
    )
    try:
        return service.submit(
            db=db,
            description=description,
            latitude=latitude,
            longitude=longitude,
            file_bytes=photo.file.read(),
            content_type=photo.content_type,
            filename=photo.filename,
        )
    except (ReportValidationError, ValidationError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValueError as exc:
        # V1 rejects reports that cannot be confirmed as potholes.
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to submit report")
