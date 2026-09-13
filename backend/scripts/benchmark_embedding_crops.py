"""
Benchmark MobileNetV3 embeddings using pothole-region crops.

This experiment compares:
    1. Positive pairs:
       The same pothole crop before and after a small transformation.

    2. Negative pairs:
       Pothole crops taken from different source images.

The goal is to determine whether focusing the embedding model on the
actual pothole region gives better visual separation than embedding
the entire road image.

IMPORTANT:
The positive pairs are transformed versions of the same source crop.
They are NOT independently captured photographs of the same physical
pothole, so this is a robustness benchmark rather than a production
duplicate-detection accuracy measurement.
"""

from pathlib import Path
import random

import numpy as np
import timm
import torch

from PIL import Image, ImageEnhance


# Keep the public benchmark dataset outside the Git repository.
# This prevents a large dataset from accidentally being committed.
DATASET_ROOT = Path(
    r"C:\Users\vedan\Downloads\civiclens-pothole-benchmark"
)

# The test split is used so that this benchmark remains separate from
# the model-training data.
TEST_IMAGES = DATASET_ROOT / "test" / "images"
TEST_LABELS = DATASET_ROOT / "test" / "labels"


# The IIT Madras dataset uses class ID 2 for potholes.
POTHOLE_CLASS_ID = 2

# Use a fixed seed so the experiment produces reproducible pairs.
RANDOM_SEED = 42

# Number of source images used for the benchmark.
PAIR_COUNT = 25

# Add context around the annotated pothole.
# A little surrounding road is useful because appearance and context
# can help distinguish two visually similar potholes.
CROP_PADDING = 0.20


def find_pothole_boxes(label_path: Path) -> list[tuple[float, float, float, float]]:
    """
    Read pothole bounding boxes from a YOLO-format label file.

    YOLO labels use:
        class_id x_center y_center width height

    All coordinates are normalized to the image dimensions.

    Returns:
        A list of normalized pothole boxes.
    """

    # Return no boxes when an image has no corresponding label file.
    if not label_path.exists():
        return []

    pothole_boxes = []

    # Read every annotation in the label file.
    for line in label_path.read_text().splitlines():
        parts = line.split()

        # Ignore malformed annotation rows rather than crashing the
        # entire benchmark.
        if len(parts) != 5:
            continue

        class_id = int(parts[0])

        # We only care about the pothole class for this experiment.
        if class_id != POTHOLE_CLASS_ID:
            continue

        x_center, y_center, width, height = map(
            float,
            parts[1:],
        )

        pothole_boxes.append(
            (
                x_center,
                y_center,
                width,
                height,
            )
        )

    return pothole_boxes


def crop_largest_pothole(
    image: Image.Image,
    pothole_boxes: list[tuple[float, float, float, float]],
) -> Image.Image:
    """
    Crop the largest annotated pothole from an image.

    A small amount of padding is added around the bounding box so the
    embedding retains useful surrounding road context.
    """

    # Choose the largest annotated pothole because it provides the most
    # substantial visual region for this first benchmark.
    box = max(
        pothole_boxes,
        key=lambda item: item[2] * item[3],
    )

    x_center, y_center, width, height = box

    image_width, image_height = image.size

    # Convert normalized YOLO coordinates into pixel coordinates.
    box_width = width * image_width
    box_height = height * image_height

    center_x = x_center * image_width
    center_y = y_center * image_height

    # Expand the crop slightly to preserve surrounding road context.
    padded_width = box_width * (1 + CROP_PADDING)
    padded_height = box_height * (1 + CROP_PADDING)

    left = center_x - padded_width / 2
    top = center_y - padded_height / 2
    right = center_x + padded_width / 2
    bottom = center_y + padded_height / 2

    # Clip the crop to the actual image boundaries.
    left = max(0, int(left))
    top = max(0, int(top))
    right = min(image_width, int(right))
    bottom = min(image_height, int(bottom))

    return image.crop(
        (left, top, right, bottom)
    )


def transform_crop(image: Image.Image) -> Image.Image:
    """
    Create a controlled variation of a pothole crop.

    These transformations simulate small differences in image capture
    while preserving the underlying visual subject.
    """

    # Apply a tiny rotation to simulate a slightly different camera angle.
    transformed = image.rotate(
        3,
        expand=False,
    )

    # Slightly change brightness to simulate different lighting.
    transformed = ImageEnhance.Brightness(
        transformed
    ).enhance(1.08)

    # Apply a small center crop to simulate a framing difference.
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

    return transformed


def build_pothole_crops() -> list[Image.Image]:
    """
    Find test images containing potholes and extract one crop per image.

    One crop is selected per source image so that each benchmark pair
    represents a distinct source image rather than multiple annotations
    from the same photograph.
    """

    crops = []

    # Inspect every test image in a deterministic order.
    for image_path in sorted(TEST_IMAGES.glob("*")):
        # Only process common image formats.
        if image_path.suffix.lower() not in {
            ".jpg",
            ".jpeg",
            ".png",
        }:
            continue

        label_path = TEST_LABELS / (
            image_path.stem + ".txt"
        )

        pothole_boxes = find_pothole_boxes(
            label_path
        )

        # Skip images without an annotated pothole.
        if not pothole_boxes:
            continue

        # Load the source image and extract the largest pothole region.
        with Image.open(image_path) as image:
            crop = crop_largest_pothole(
                image.convert("RGB"),
                pothole_boxes,
            )

        # Ignore pathological crops that are too small to provide
        # meaningful visual information.
        if crop.width < 20 or crop.height < 20:
            continue

        crops.append(crop)

    return crops


def create_embedding_model():
    """
    Load the lightweight MobileNetV3 embedding model.

    num_classes=0 removes the ImageNet classification head so the model
    returns a feature vector instead of class probabilities.
    """

    model = timm.create_model(
        "mobilenetv3_small_100.lamb_in1k",
        pretrained=True,
        num_classes=0,
    )

    # Evaluation mode disables training-specific behavior such as
    # dropout and makes inference deterministic.
    model.eval()

    # CivicLens v1 is designed to run on CPU, so explicitly use CPU here.
    model.to("cpu")

    # Use the preprocessing expected by this particular pretrained model.
    data_config = timm.data.resolve_model_data_config(model)

    transform = timm.data.create_transform(
        **data_config,
        is_training=False,
    )

    return model, transform


def embed_image(
    image: Image.Image,
    model,
    transform,
) -> np.ndarray:
    """
    Convert one image crop into a normalized embedding vector.
    """

    # Apply the pretrained model's expected resize/normalization pipeline.
    tensor = transform(image).unsqueeze(0)

    # Inference mode avoids gradient tracking because this is not training.
    with torch.inference_mode():
        embedding = model(tensor)

    # Convert the tensor into a NumPy vector.
    vector = embedding.squeeze(0).numpy()

    # Normalize the vector so cosine similarity becomes a dot product.
    norm = np.linalg.norm(vector)

    if norm == 0:
        raise ValueError("Embedding has zero magnitude")

    return vector / norm


def cosine_similarity(
    vector_a: np.ndarray,
    vector_b: np.ndarray,
) -> float:
    """
    Calculate cosine similarity between two normalized embeddings.
    """

    # Both vectors are already normalized, so their dot product is
    # equivalent to cosine similarity.
    return float(
        np.dot(vector_a, vector_b)
    )


def main() -> None:
    """
    Run the pothole-crop embedding benchmark.
    """

    # Seed Python's random module so the selected images are reproducible.
    random.seed(RANDOM_SEED)

    print("MobileNetV3 pothole-crop benchmark")
    print("----------------------------------")

    # Extract one pothole crop from each suitable test image.
    crops = build_pothole_crops()

    print(
        f"Pothole crops available:        {len(crops)}"
    )

    if len(crops) < PAIR_COUNT:
        raise RuntimeError(
            f"Need at least {PAIR_COUNT} pothole crops, "
            f"but only found {len(crops)}."
        )

    # Randomly choose distinct source crops for the benchmark.
    selected_crops = random.sample(
        crops,
        PAIR_COUNT * 2,
    )

    positive_sources = selected_crops[:PAIR_COUNT]
    negative_sources = selected_crops[PAIR_COUNT:]

    # Load the lightweight embedding model once.
    model, transform = create_embedding_model()

    # Cache embeddings so each source crop only needs one model inference.
    positive_original_embeddings = []
    positive_transformed_embeddings = []
    negative_embeddings = []

    # Embed the original and transformed version of every positive source.
    for crop in positive_sources:
        original_embedding = embed_image(
            crop,
            model,
            transform,
        )

        transformed_embedding = embed_image(
            transform_crop(crop),
            model,
            transform,
        )

        positive_original_embeddings.append(
            original_embedding
        )

        positive_transformed_embeddings.append(
            transformed_embedding
        )

    # Embed the independent negative-source crops.
    for crop in negative_sources:
        negative_embeddings.append(
            embed_image(
                crop,
                model,
                transform,
            )
        )

    # Compare every source crop with its own transformed version.
    positive_scores = [
        cosine_similarity(
            original,
            transformed,
        )
        for original, transformed in zip(
            positive_original_embeddings,
            positive_transformed_embeddings,
        )
    ]

    # Compare each positive source against a different pothole source.
    # This gives us a simple negative distribution without needing
    # thousands of pair combinations for this first experiment.
    negative_scores = [
        cosine_similarity(
            positive_original_embeddings[index],
            negative_embeddings[index],
        )
        for index in range(PAIR_COUNT)
    ]

    positive_mean = np.mean(
        positive_scores
    )

    negative_mean = np.mean(
        negative_scores
    )

    separation = (
        positive_mean
        - negative_mean
    )

    print()
    print("Positive pairs")
    print(
        f"  Mean cosine similarity: "
        f"{positive_mean:.4f}"
    )
    print(
        f"  Min cosine similarity:  "
        f"{min(positive_scores):.4f}"
    )
    print(
        f"  Max cosine similarity:  "
        f"{max(positive_scores):.4f}"
    )

    print()
    print("Negative pairs")
    print(
        f"  Mean cosine similarity: "
        f"{negative_mean:.4f}"
    )
    print(
        f"  Min cosine similarity:  "
        f"{min(negative_scores):.4f}"
    )
    print(
        f"  Max cosine similarity:  "
        f"{max(negative_scores):.4f}"
    )

    print()
    print(
        f"Mean positive-negative separation: "
        f"{separation:.4f}"
    )

    # This is a useful diagnostic for the tiny benchmark:
    # if the distributions overlap, the embedding model may have
    # difficulty distinguishing transformed positives from negatives.
    overlap_count = sum(
        positive <= max(negative_scores)
        for positive in positive_scores
    )

    print(
        f"Positive pairs at/below max negative: "
        f"{overlap_count}/{PAIR_COUNT}"
    )


if __name__ == "__main__":
    main()