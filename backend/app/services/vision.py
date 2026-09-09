from abc import ABC, abstractmethod

from app.schemas.vision import VisionPrediction


class VisionModel(ABC):

    @abstractmethod
    def analyze(
        self,
        image_bytes: bytes,
    ) -> VisionPrediction:
        pass