from fastapi import APIRouter

from app.schemas.incident import IncidentCreate

router = APIRouter()


@router.post("/incidents")
def create_incident(incident: IncidentCreate):
    return {
        "message": "Incident received",
        "incident": incident,
    }