from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.dependencies import get_db
from app.models.incident import Incident
from app.schemas.incident import IncidentCreate, IncidentResponse

from app.schemas.incident import IncidentCreate

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
