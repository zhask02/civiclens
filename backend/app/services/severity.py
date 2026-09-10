from dataclasses import dataclass

from app.enums.incident import IncidentSeverity
from app.schemas.vision import VisionPrediction


@dataclass
class SeverityAssessment:
    """
    Result produced by the severity engine.

    Keeping the numerical score and reasons alongside the final
    severity makes the system explainable instead of returning
    only a black-box LOW/HIGH decision.
    """

    score: float
    severity: IncidentSeverity
    reasons: list[str]


class SeverityEngine:
    """
    Estimates pothole severity from visual detection evidence.

    This is an engineered heuristic for CivicLens v1.
    It estimates apparent visual severity from the image rather
    than claiming to measure physical pothole depth or dimensions.
    """

    def assess(
        self,
        prediction: VisionPrediction,
        image_width: int,
        image_height: int,
    ) -> SeverityAssessment:

        # No detected potholes means there is no pothole severity
        # to estimate.
        if not prediction.detections:
            return SeverityAssessment(
                score=0.0,
                severity=IncidentSeverity.LOW,
                reasons=["No potholes detected"],
            )

        # Calculate the total number of pixels in the image.
        image_area = image_width * image_height

        # Protect against invalid image dimensions.
        if image_area <= 0:
            raise ValueError("Image dimensions must be positive")

        # Find the largest apparent pothole region.
        largest_area_ratio = 0.0

        for detection in prediction.detections:
            box = detection.bounding_box

            # Bounding-box width and height are measured in pixels.
            box_width = max(0.0, box.x_max - box.x_min)
            box_height = max(0.0, box.y_max - box.y_min)

            # This is image-space coverage, NOT physical pothole size.
            box_area = box_width * box_height
            area_ratio = box_area / image_area

            largest_area_ratio = max(
                largest_area_ratio,
                area_ratio,
            )

        # Convert apparent size into a 0–60 score.
        # Size is our strongest visual signal, but deliberately
        # does not dominate the entire severity decision.
        if largest_area_ratio >= 0.30:
            size_score = 60
            size_reason = "Very large apparent pothole region"
        elif largest_area_ratio >= 0.15:
            size_score = 45
            size_reason = "Large apparent pothole region"
        elif largest_area_ratio >= 0.05:
            size_score = 30
            size_reason = "Moderate apparent pothole region"
        elif largest_area_ratio >= 0.01:
            size_score = 15
            size_reason = "Small apparent pothole region"
        else:
            size_score = 5
            size_reason = "Very small apparent pothole region"

        # Multiple potholes increase the severity score because a cluster
        # of road defects represents a larger affected area.
        # We cap this contribution so that many tiny detections alone
        # cannot automatically make an incident critical.
        pothole_count = len(prediction.detections)

        if pothole_count >= 4:
            count_score = 25
        elif pothole_count == 3:
            count_score = 20
        elif pothole_count == 2:
            count_score = 10
        else:
            count_score = 0

        if pothole_count >= 5:
            count_reason = f"{pothole_count} potholes detected"
        elif pothole_count > 1:
            count_reason = f"{pothole_count} potholes detected"
        else:
            count_reason = "One pothole detected"

        # Confidence is treated as detection reliability rather than
        # physical danger. We use the strongest detection confidence
        # only as a small supporting signal.
        confidence_score = round(
            prediction.confidence * 15,
            2,
        )

        # Combine the three signals into one transparent score.
        score = round(
            size_score
            + count_score
            + confidence_score,
            2,
        )

        # Map the numerical score to our four severity categories.
        if score >= 75:
            severity = IncidentSeverity.CRITICAL
        elif score >= 50:
            severity = IncidentSeverity.HIGH
        elif score >= 25:
            severity = IncidentSeverity.MEDIUM
        else:
            severity = IncidentSeverity.LOW

        return SeverityAssessment(
            score=score,
            severity=severity,
            reasons=[
                size_reason,
                count_reason,
                f"Highest detector confidence: {prediction.confidence:.2f}",
            ],
        )