from pydantic import BaseModel, Field
from app.enums.incident import IncidentCategory, IncidentSeverity, IncidentStatus

class IncidentCreate(BaseModel):
    description: str = Field(
        min_length = 5,
        max_length = 1000,
        examples = ["Large pothole near the college main gate"]
    )
    latitude: float = Field(
        ge=-90,
        le=90,
        examples = [12.9716],
    )
    longitude: float = Field(
        ge=-180,
        le=180,
        examples = [77.5946],
    )

from datetime import datetime
from pydantic import BaseModel

class IncidentResponse(BaseModel):
    id:int
    description: str
    latitude: float
    longitude: float
    category: str | None
    severity: str | None    
    status: str
    confidence: float | None
    created_at: datetime

    model_config = {
        "from_attributes": True
    }

class IncidentUpdate(BaseModel):
    category: IncidentCategory | None = None
    severity: IncidentSeverity | None = None
    status: IncidentStatus | None = None
    confidence: float | None = None