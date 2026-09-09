from io import BytesIO

from PIL import Image, UnidentifiedImageError
from ultralytics import YOLO

from app.schemas.vision import (
    BoundingBox,
    VisionDetection,
    VisionPrediction,
)
from app.services.vision import VisionModel


CONFIDENCE_THRESHOLD = 0.40


class PotholeDetector(VisionModel):
    def __init__(self, model_path: str):
        self.model = YOLO(model_path)

    def analyze(self, image_bytes: bytes) -> VisionPrediction:
        try:
            image = Image.open(BytesIO(image_bytes))
        except (UnidentifiedImageError, OSError):
            raise ValueError("Invalid or corrupted image")

        results = self.model(image)

        detections = []

        for result in results:
            for box in result.boxes:
                confidence = float(box.conf[0])

                if confidence < CONFIDENCE_THRESHOLD:
                    continue

                class_id = int(box.cls[0])

                x_min, y_min, x_max, y_max = map(
                    float,
                    box.xyxy[0],
                )

                detections.append(
                    VisionDetection(
                        label=result.names[class_id],
                        confidence=confidence,
                        bounding_box=BoundingBox(
                            x_min=x_min,
                            y_min=y_min,
                            x_max=x_max,
                            y_max=y_max,
                        ),
                    )
                )

        highest_confidence = (
            max(detection.confidence for detection in detections)
            if detections
            else 0.0
        )

        return VisionPrediction(
            category="pothole" if detections else None,
            severity="medium" if detections else None,
            confidence=highest_confidence,
            model_name="yolo26-pothole",
            detections=detections,
        )