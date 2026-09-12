from datetime import datetime

from pydantic import BaseModel, Field

from app.enums.incident import (
    IncidentCategory,
    IncidentSeverity,
    PriorityLevel,
)

from app.schemas.location import LocationContext
from app.schemas.vision import VisionPrediction


class AnalysisResult(BaseModel):
    """
    Complete result produced by the CivicLens analysis pipeline.

    This is an internal orchestration contract. It keeps the outputs
    of the independent analysis stages together before the final
    EvidenceAnalysis database record is created.
    """

    # Raw visual evidence produced by the pothole detector.
    vision: VisionPrediction

    # Visual severity calculated from the detector's evidence.
    severity: IncidentSeverity
    severity_score: float

    # Geographic context associated with the incident coordinates.
    location: LocationContext

    # Operational urgency calculated from severity, location,
    # and model confidence.
    priority_score: float
    priority_level: PriorityLevel
    requires_review: bool

class AnalysisResponse(BaseModel):
    """
    Public representation of a completed evidence analysis.

    This schema exposes the results produced by CivicLens rather than
    accepting analysis values from the API caller.
    """

    # Database identifiers connect this analysis to the evidence
    # that produced it.
    id: int
    evidence_id: int

    # Visual classification produced by the pothole detector.
    category: IncidentCategory

    # Severity estimated from the visual evidence.
    severity: IncidentSeverity

    # Confidence represents how strongly the detector supports
    # the visual classification.
    confidence: float = Field(
        ge=0,
        le=1,
    )

    # Identifies the model responsible for the visual prediction.
    model_name: str

    # Numerical score behind the human-readable severity.
    severity_score: float

    # Operational urgency after applying severity, location,
    # and confidence.
    priority_score: float

    # Operational priority is deliberately separate from severity.
    priority_level: PriorityLevel

    # Low-confidence analyses should be surfaced for human review.
    requires_review: bool

    # Timestamp allows us to track when this analysis was produced.
    created_at: datetime

    # SQLAlchemy ORM objects can be returned directly from the service
    # and converted into this Pydantic response model.
    model_config = {
        "from_attributes": True
    }