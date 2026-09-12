from pydantic import BaseModel, Field

from app.enums.incident import PriorityLevel


class PriorityResult(BaseModel):
    """
    Structured result produced by the CivicLens Priority Engine.

    Keeping the result in a schema gives the rest of the application
    a stable contract without coupling it to the engine's internals.
    """

    # Final priority score, always bounded between 0 and 100.
    score: float = Field(
        ge=0,
        le=100,
    )

    # Operational urgency is intentionally represented separately
    # from IncidentSeverity.
    level: PriorityLevel

    # Low-confidence detections should be surfaced for human verification
    # instead of being treated as equally trustworthy automated decisions.
    requires_review: bool