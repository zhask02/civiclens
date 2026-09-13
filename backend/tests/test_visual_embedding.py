"""
Tests for the VisualEmbeddingService.

These tests verify the contract of the embedding component rather
than trying to prove that MobileNetV3 understands potholes correctly.

Real-world visual quality is evaluated separately through our
embedding benchmarks.
"""


import io

import numpy as np
from PIL import Image

from app.services.visual_embedding import VisualEmbeddingService


def create_test_image() -> bytes:
    """
    Create a tiny valid JPEG image entirely in memory.

    Using an in-memory image keeps this test independent of local files.
    """

    # Create a simple RGB image that PIL and MobileNet can process.
    image = Image.new(
        "RGB",
        (128, 128),
        (120, 120, 120),
    )

    # Store the image as JPEG in memory instead of writing to disk.
    buffer = io.BytesIO()

    image.save(
        buffer,
        format="JPEG",
    )

    return buffer.getvalue()


def test_embedding_has_expected_shape_and_normalization():
    """
    Verify that the service returns a normalized feature vector.
    """

    # Load the actual lightweight embedding model.
    service = VisualEmbeddingService()

    # Generate an embedding from a valid image.
    embedding = service.embed(
        create_test_image()
    )

    # MobileNetV3 Small's feature extractor produces 1024 features.
    assert embedding.shape == (1024,)

    # The service contract requires a unit-length vector.
    assert np.isclose(
        np.linalg.norm(embedding),
        1.0,
        atol=1e-5,
    )


def test_embedding_is_deterministic_for_same_image():
    """
    The same image should produce the same embedding during inference.
    """

    # Load the model once and reuse it for both calls.
    service = VisualEmbeddingService()

    image_bytes = create_test_image()

    first_embedding = service.embed(
        image_bytes
    )

    second_embedding = service.embed(
        image_bytes
    )

    # Identical inputs should produce effectively identical vectors.
    assert np.allclose(
        first_embedding,
        second_embedding,
        atol=1e-6,
    )


def test_invalid_image_raises_value_error():
    """
    Invalid bytes should produce a predictable application error.
    """

    service = VisualEmbeddingService()

    # These bytes do not represent a valid image.
    invalid_bytes = b"not an image"

    try:
        service.embed(invalid_bytes)

        # The test should never reach this point.
        assert False, "Expected ValueError"

    except ValueError as exc:
        # Confirm that the service exposes the intended error contract.
        assert str(exc) == "Invalid or corrupted image"