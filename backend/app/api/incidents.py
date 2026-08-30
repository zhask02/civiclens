from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.dependencies import get_db
from app.models.incident import Incident
from app.schemas.incident import IncidentCreate, IncidentResponse


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



