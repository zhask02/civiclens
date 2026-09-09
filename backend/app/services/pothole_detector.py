from io import BytesIO

from PIL import Image
from ultralytics import YOLO

from app.schemas.vision import (
    BoundingBox,
    VisionDetection,
    VisionPrediction,
)
from app.services.vision import VisionModel


class PotholeDetector(VisionModel):
    def __init__(self, model_path: str):
        self.model = YOLO(model_path)

    def analyze(self, image_bytes: bytes) -> VisionPrediction:
        image = Image.open(BytesIO(image_bytes))

        results = self.model(image)

        detections = []

        for result in results:
            for box in result.boxes:
                confidence = float(box.conf[0])
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
            category="pothole",
            severity="medium",
            confidence=highest_confidence,
            model_name="yolo26-pothole",
            detections=detections,
        )