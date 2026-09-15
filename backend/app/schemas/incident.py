from pydantic import BaseModel, Field
from app.enums.incident import IncidentStatus

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
    """
    Fields that operators are allowed to update manually.

    AI-generated fields such as category, severity, and confidence are
    intentionally excluded. Those values must come from the CivicLens
    analysis pipeline rather than being supplied by an API client.
    """

    status: IncidentStatus | None = None