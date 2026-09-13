"""
Benchmark MobileNetV3 embeddings for pothole image similarity.

This experiment compares:
1. Positive pairs: an image against a controlled transformation of itself.
2. Negative pairs: two different pothole images.

The goal is to determine whether the lightweight embedding model
produces a useful separation between visually similar and different
images before integrating embeddings into CivicLens duplicate detection.

IMPORTANT:
The positive pairs represent transformation robustness, NOT proof that
two independently captured photos are the same physical pothole.
"""

from io import BytesIO
from pathlib import Path
import random

import numpy as np
import torch
import timm
from PIL import Image, ImageEnhance
from torchvision import transforms


# Keep the random selection reproducible so the benchmark can be rerun
# later and produce the same source-image sample.
RANDOM_SEED = 42

# We deliberately keep the first experiment small and interpretable.
# The full dataset contains hundreds of pothole images, but 25 positive
# and 25 negative pairs are enough for an initial sanity benchmark.
NUM_POSITIVE_PAIRS = 25
NUM_NEGATIVE_PAIRS = 25

# Class 2 is "pothole" according to the dataset's data.yaml.
POTHOLE_CLASS_ID = "2"

# The benchmark dataset lives outside the Git repository.
BENCHMARK_ROOT = (
    Path.home()
    / "Downloads"
    / "civiclens-pothole-benchmark"
)

TEST_IMAGES = BENCHMARK_ROOT / "test" / "images"
TEST_LABELS = BENCHMARK_ROOT / "test" / "labels"


def contains_pothole(label_path: Path) -> bool:
    """
    Determine whether a YOLO annotation file contains class 2.

    We use the dataset's ground-truth annotation rather than running
    our pothole detector because this experiment is evaluating the
    embedding model, not the detector.
    """

    # Read each annotation line. The first field is the YOLO class ID.
    for line in label_path.read_text().splitlines():
        fields = line.split()

        # Ignore malformed or empty annotation lines.
        if not fields:
            continue

        # Class 2 corresponds to pothole in data.yaml.
        if fields[0] == POTHOLE_CLASS_ID:
            return True

    return False


def find_pothole_images() -> list[Path]:
    """
    Return test images that have at least one pothole annotation.
    """

    pothole_images = []

    # Iterate through YOLO label files and map each label back to its image.
    for label_path in TEST_LABELS.glob("*.txt"):
        if not contains_pothole(label_path):
            continue

        # The image and label share the same filename stem.
        for extension in (".jpg", ".jpeg", ".png"):
            image_path = TEST_IMAGES / f"{label_path.stem}{extension}"

            if image_path.exists():
                pothole_images.append(image_path)
                break

    return sorted(pothole_images)


def create_transformed_image(image: Image.Image) -> Image.Image:
    """
    Create a mild transformation of the same image.

    These transformations approximate harmless differences that can occur
    when the same scene is uploaded more than once.
    """

    # Slight rotation tests whether embeddings remain stable under
    # small viewpoint/orientation changes.
    transformed = image.rotate(
        3,
        expand=False,
    )

    # Mild brightness adjustment simulates different camera exposure.
    transformed = ImageEnhance.Brightness(
        transformed
    ).enhance(1.08)

    # A small crop followed by resize changes framing while preserving
    # the overall visual content.
    width, height = transformed.size

    crop_width = int(width * 0.94)
    crop_height = int(height * 0.94)

    left = (width - crop_width) // 2
    top = (height - crop_height) // 2

    transformed = transformed.crop(
        (
            left,
            top,
            left + crop_width,
            top + crop_height,
        )
    )

    transformed = transformed.resize(
        (width, height),
        Image.Resampling.BILINEAR,
    )

    # JPEG round-tripping introduces realistic compression artifacts.
    buffer = BytesIO()

    transformed.save(
        buffer,
        format="JPEG",
        quality=85,
    )

    buffer.seek(0)

    return Image.open(buffer).convert("RGB")


def build_embedding_model():
    """
    Load the lightweight pretrained MobileNetV3 embedding model.

    num_classes=0 removes the ImageNet classification head and exposes
    the learned feature representation instead.
    """

    # This is the model we benchmarked earlier:
    # approximately 1.5M parameters and fast CPU inference.
    model = timm.create_model(
        "mobilenetv3_small_100.lamb_in1k",
        pretrained=True,
        num_classes=0,
    )

    # Evaluation mode disables training-specific behavior such as dropout.
    model.eval()

    # CivicLens v1 is designed to work on CPU, so keep this benchmark CPU-only.
    model = model.to("cpu")

    return model


def build_preprocessing():
    """
    Return the preprocessing expected by the pretrained model.
    """

    # timm provides model-specific preprocessing so our inputs match
    # the distribution the pretrained encoder expects.
    data_config = timm.data.resolve_model_data_config(
        "mobilenetv3_small_100.lamb_in1k"
    )

    return timm.data.create_transform(
        **data_config,
        is_training=False,
    )


def embed_image(
    image: Image.Image,
    model,
    preprocess,
) -> np.ndarray:
    """
    Convert an image into a normalized embedding vector.
    """

    # Convert the PIL image into the tensor format expected by the model.
    tensor = preprocess(image).unsqueeze(0)

    # inference_mode avoids gradient tracking because this benchmark
    # only performs inference.
    with torch.inference_mode():
        embedding = model(tensor)

    # Flatten the model output into a one-dimensional feature vector.
    vector = embedding.squeeze(0).cpu().numpy()

    # L2 normalization makes the dot product equivalent to cosine
    # similarity for these embeddings.
    norm = np.linalg.norm(vector)

    if norm == 0:
        raise ValueError("Embedding has zero magnitude")

    return vector / norm


def cosine_similarity(
    embedding_a: np.ndarray,
    embedding_b: np.ndarray,
) -> float:
    """
    Calculate cosine similarity between two normalized embeddings.
    """

    # Because both vectors are normalized, their dot product is cosine
    # similarity and ranges approximately from -1 to 1.
    return float(
        np.dot(
            embedding_a,
            embedding_b,
        )
    )


def main() -> None:
    """
    Run the complete embedding similarity benchmark.
    """

    # Seed the random generator so the selected image pairs are reproducible.
    random.seed(RANDOM_SEED)

    # Verify that the expected external dataset exists before proceeding.
    if not TEST_IMAGES.exists() or not TEST_LABELS.exists():
        raise FileNotFoundError(
            f"Expected test dataset at {BENCHMARK_ROOT}"
        )

    # Select only images whose ground-truth labels contain potholes.
    pothole_images = find_pothole_images()

    if len(pothole_images) < NUM_POSITIVE_PAIRS * 2:
        raise ValueError(
            "Not enough pothole images for the benchmark"
        )

    # Load the lightweight embedding encoder and its preprocessing pipeline.
    model = build_embedding_model()
    preprocess = build_preprocessing()

    # Randomly select independent source images for reproducible positive pairs.
    positive_sources = random.sample(
        pothole_images,
        NUM_POSITIVE_PAIRS,
    )

    positive_scores = []

    for image_path in positive_sources:
        # Open the original source image.
        with Image.open(image_path) as image:
            original = image.convert("RGB")

            # Create a controlled variation of that same source image.
            transformed = create_transformed_image(original)

            # Generate embeddings for both versions.
            original_embedding = embed_image(
                original,
                model,
                preprocess,
            )

            transformed_embedding = embed_image(
                transformed,
                model,
                preprocess,
            )

        # Measure how much the embedding changed after transformation.
        score = cosine_similarity(
            original_embedding,
            transformed_embedding,
        )

        positive_scores.append(score)

    # Select a separate set of images for negative pairs so that no source
    # image is accidentally compared against itself.
    negative_sources = random.sample(
        pothole_images,
        NUM_NEGATIVE_PAIRS * 2,
    )

    negative_scores = []

    for index in range(NUM_NEGATIVE_PAIRS):
        image_a_path = negative_sources[index * 2]
        image_b_path = negative_sources[index * 2 + 1]

        # Load two independently sourced pothole images.
        with Image.open(image_a_path) as image_a:
            image_a = image_a.convert("RGB")

        with Image.open(image_b_path) as image_b:
            image_b = image_b.convert("RGB")

        # Generate embeddings for the two different images.
        embedding_a = embed_image(
            image_a,
            model,
            preprocess,
        )

        embedding_b = embed_image(
            image_b,
            model,
            preprocess,
        )

        # Measure their visual embedding similarity.
        score = cosine_similarity(
            embedding_a,
            embedding_b,
        )

        negative_scores.append(score)

    # Print summary statistics rather than dumping all 50 comparisons.
    print()
    print("MobileNetV3 embedding benchmark")
    print("--------------------------------")
    print(f"Pothole test images available: {len(pothole_images)}")
    print(f"Positive pairs:                 {len(positive_scores)}")
    print(f"Negative pairs:                 {len(negative_scores)}")
    print()

    print("Positive pairs")
    print(
        f"  Mean cosine similarity: {np.mean(positive_scores):.4f}"
    )
    print(
        f"  Min cosine similarity:  {np.min(positive_scores):.4f}"
    )
    print(
        f"  Max cosine similarity:  {np.max(positive_scores):.4f}"
    )

    print()

    print("Negative pairs")
    print(
        f"  Mean cosine similarity: {np.mean(negative_scores):.4f}"
    )
    print(
        f"  Min cosine similarity:  {np.min(negative_scores):.4f}"
    )
    print(
        f"  Max cosine similarity:  {np.max(negative_scores):.4f}"
    )

    # This gap is a simple first diagnostic. A large positive-vs-negative
    # separation suggests the encoder may provide useful visual evidence.
    print()

    separation = (
        np.mean(positive_scores)
        - np.mean(negative_scores)
    )

    print(
        f"Mean positive-negative separation: {separation:.4f}"
    )


if __name__ == "__main__":
    main()