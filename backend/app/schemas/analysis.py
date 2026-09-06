from datetime import datetime

from pydantic import BaseModel, Field

from app.enums.incident import IncidentCategory, IncidentSeverity


class AnalysisCreate(BaseModel):
    category: IncidentCategory
    severity: IncidentSeverity
    confidence: float = Field(
        ge=0,
        le=1,
    )
    model_name: str = Field(
        min_length=1,
        max_length=100,
    )


class AnalysisResponse(BaseModel):
    id: int
    evidence_id: int
    category: IncidentCategory
    severity: IncidentSeverity
    confidence: float
    model_name: str
    created_at: datetime

    model_config = {
        "from_attributes": True
    }