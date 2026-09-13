"""
Visual embedding service for CivicLens.

This service converts an image into a numerical feature vector that
can later be compared with embeddings from other incident evidence.

The service intentionally does NOT decide whether two incidents are
duplicates. That responsibility belongs to DuplicateService.

Architecture:

    image bytes
        ↓
    VisualEmbeddingService
        ↓
    normalized embedding vector
"""


from io import BytesIO

import numpy as np
import timm
import torch
from PIL import Image


class VisualEmbeddingService:
    """
    Generate visual embeddings using a lightweight pretrained model.

    MobileNetV3 Small was selected because our benchmark showed strong
    separation between synthetic positive and negative pairs while
    remaining very lightweight and fast on CPU.

    The model is used only as a feature extractor. Its ImageNet
    classification head is removed by setting num_classes=0.
    """

    MODEL_NAME = "mobilenetv3_small_100.lamb_in1k"

    def __init__(self) -> None:
        """
        Load the embedding model and its preprocessing pipeline once.

        Loading the model during initialization avoids downloading and
        constructing the neural network for every image.
        """

        # Remove the ImageNet classification head so the model returns
        # a feature vector instead of class probabilities.
        self.model = timm.create_model(
            self.MODEL_NAME,
            pretrained=True,
            num_classes=0,
        )

        # Evaluation mode disables training-specific behavior such as
        # dropout and makes inference deterministic.
        self.model.eval()

        # CivicLens v1 is designed to work on CPU.
        self.model.to("cpu")

        # Different pretrained models can expect different image
        # preprocessing. We therefore obtain the configuration directly
        # from the selected MobileNetV3 model.
        data_config = timm.data.resolve_model_data_config(
            self.model
        )

        # Build the preprocessing pipeline expected by the model.
        self.transform = timm.data.create_transform(
            **data_config,
            is_training=False,
        )

    def embed(
        self,
        image_bytes: bytes,
    ) -> np.ndarray:
        """
        Convert an image into a normalized visual embedding.

        Args:
            image_bytes:
                Raw image bytes, such as those downloaded from
                Supabase Storage.

        Returns:
            A normalized NumPy vector representing the image visually.

        Raises:
            ValueError:
                If the supplied bytes do not contain a valid image.
        """

        try:
            # Decode the raw bytes into a PIL image.
            # The embedding service accepts bytes so it remains
            # independent of Supabase, HTTP, or filesystem details.
            with Image.open(
                BytesIO(image_bytes)
            ) as image:
                image = image.convert("RGB")

        except Exception as exc:
            # Hide implementation-specific PIL errors behind a stable
            # application-level error.
            raise ValueError(
                "Invalid or corrupted image"
            ) from exc

        # Apply MobileNetV3's expected resize and normalization steps.
        tensor = self.transform(image).unsqueeze(0)

        # Embedding generation is inference only, so gradient tracking
        # would waste memory and computation.
        with torch.inference_mode():
            embedding = self.model(tensor)

        # Remove the batch dimension and convert the result to NumPy.
        vector = embedding.squeeze(0).numpy()

        # Normalize the vector to unit length.
        #
        # This makes cosine similarity equivalent to a simple dot
        # product later, while keeping similarity values interpretable.
        norm = np.linalg.norm(vector)

        if norm == 0:
            raise ValueError(
                "Embedding has zero magnitude"
            )

        return vector / norm