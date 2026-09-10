import pytest

from app.enums.incident import IncidentSeverity
from app.schemas.vision import (
    BoundingBox,
    VisionDetection,
    VisionPrediction,
)
from app.services.severity import SeverityEngine


# Use a single image size throughout these tests so that
# the expected bounding-box coverage is easy to reason about.
IMAGE_WIDTH = 1000
IMAGE_HEIGHT = 1000


def make_prediction(boxes, confidence=0.9):
    """
    Build VisionPrediction objects quickly for test scenarios.

    The helper keeps the actual tests focused on severity behaviour
    instead of repeating Pydantic object construction.
    """

    detections = [
        VisionDetection(
            label="pothole",
            confidence=confidence,
            bounding_box=BoundingBox(
                x_min=x_min,
                y_min=y_min,
                x_max=x_max,
                y_max=y_max,
            ),
        )
        for x_min, y_min, x_max, y_max in boxes
    ]

    return VisionPrediction(
        category="pothole" if detections else None,
        severity=None,
        confidence=confidence if detections else 0.0,
        model_name="test-model",
        detections=detections,
    )


def test_no_potholes_returns_low():
    """No detections should never be treated as a severe pothole."""

    prediction = make_prediction([])

    result = SeverityEngine().assess(
        prediction,
        IMAGE_WIDTH,
        IMAGE_HEIGHT,
    )

    assert result.severity == IncidentSeverity.LOW
    assert result.score == 0.0


def test_small_pothole_returns_low_or_medium():
    """A small apparent pothole should remain on the lower end."""

    prediction = make_prediction([
        (0, 0, 100, 100),
    ])

    result = SeverityEngine().assess(
        prediction,
        IMAGE_WIDTH,
        IMAGE_HEIGHT,
    )

    assert result.severity in {
        IncidentSeverity.LOW,
        IncidentSeverity.MEDIUM,
    }


def test_medium_pothole_returns_medium():
    """A moderately sized detection should produce medium severity."""

    prediction = make_prediction([
        (0, 0, 250, 250),
    ])

    result = SeverityEngine().assess(
        prediction,
        IMAGE_WIDTH,
        IMAGE_HEIGHT,
    )

    assert result.severity == IncidentSeverity.MEDIUM


def test_large_pothole_returns_high():
    """A large apparent pothole should reach high severity."""

    prediction = make_prediction([
        (0, 0, 500, 500),
    ])

    result = SeverityEngine().assess(
        prediction,
        IMAGE_WIDTH,
        IMAGE_HEIGHT,
    )

    assert result.severity == IncidentSeverity.HIGH


def test_multiple_large_potholes_can_be_critical():
    """Several large detections should be capable of reaching critical."""

    prediction = make_prediction([
        (0, 0, 500, 500),
        (500, 0, 1000, 500),
        (0, 500, 500, 1000),
        (500, 500, 1000, 1000),
    ])

    result = SeverityEngine().assess(
        prediction,
        IMAGE_WIDTH,
        IMAGE_HEIGHT,
    )

    assert result.severity == IncidentSeverity.CRITICAL


def test_invalid_image_dimensions_raise_error():
    """The engine should reject impossible image dimensions."""

    prediction = make_prediction([
        (0, 0, 100, 100),
    ])

    with pytest.raises(ValueError):
        SeverityEngine().assess(
            prediction,
            0,
            IMAGE_HEIGHT,
        )