from pydantic import BaseModel, Field

from app.enums.incident import IncidentCategory, IncidentSeverity


class BoundingBox(BaseModel):
    x_min: float
    y_min: float
    x_max: float
    y_max: float


class VisionDetection(BaseModel):
    label: str
    confidence: float = Field(
        ge=0,
        le=1,
    )
    bounding_box: BoundingBox


class VisionPrediction(BaseModel):
    category: IncidentCategory | None
    severity: IncidentSeverity | None
    confidence: float = Field(
        ge=0,
        le=1,
    )
    model_name: str
    detections: list[VisionDetection] = Field(
        default_factory=list
    )