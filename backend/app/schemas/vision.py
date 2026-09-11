from pydantic import BaseModel, Field

from app.enums.incident import IncidentCategory


class BoundingBox(BaseModel):
    # Pixel coordinates describing the detected object's location.
    x_min: float
    y_min: float
    x_max: float
    y_max: float


class VisionDetection(BaseModel):
    # Label produced by the vision model, such as "pothole".
    label: str

    # Confidence represents how strongly the model believes this
    # particular detection belongs to the predicted class.
    confidence: float = Field(
        ge=0,
        le=1,
    )

    # Bounding box provides the visual evidence used by downstream
    # components such as the severity engine.
    bounding_box: BoundingBox


class VisionPrediction(BaseModel):
    """
    Structured output produced by a vision model.

    This contract contains visual evidence only. Severity and priority
    are calculated by dedicated downstream engines.
    """

    # The incident category inferred from the visual detections.
    category: IncidentCategory | None

    # Highest-confidence detection, used as the overall reliability
    # signal for the visual analysis.
    confidence: float = Field(
        ge=0,
        le=1,
    )

    # Identifies which model produced the visual evidence.
    model_name: str

    # Individual detections provide the evidence used by downstream
    # reasoning components.
    detections: list[VisionDetection] = Field(
        default_factory=list,
    )