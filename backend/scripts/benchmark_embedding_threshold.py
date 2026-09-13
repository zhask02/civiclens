"""
Evaluate MobileNetV3 image embeddings across many similarity pairs.

This experiment uses the IIT Madras pothole test split and creates:

    Positive pairs:
        The same source image with a controlled visual transformation.

    Negative pairs:
        Different pothole source images.

We then sweep many cosine-similarity thresholds and calculate:

    - Precision
    - Recall
    - F1
    - False positives
    - False negatives

IMPORTANT:
The positive examples are transformed versions of the same photograph.
They are NOT independent photographs of the same physical pothole.

Therefore, these metrics measure embedding robustness on this synthetic
benchmark. They must not be presented as real-world duplicate-detection
accuracy.
"""

from pathlib import Path
import random

import numpy as np
import timm
import torch

from PIL import Image, ImageEnhance


# The benchmark dataset deliberately remains outside the Git repository.
DATASET_ROOT = Path(
    r"C:\Users\vedan\Downloads\civiclens-pothole-benchmark"
)

# We use only the test split for this experiment.
TEST_IMAGES = DATASET_ROOT / "test" / "images"
TEST_LABELS = DATASET_ROOT / "test" / "labels"

# IIT Madras uses class ID 2 for potholes.
POTHOLE_CLASS_ID = 2

# Fixed seed makes the experiment reproducible.
RANDOM_SEED = 42

# Number of positive pairs.
POSITIVE_PAIR_COUNT = 50

# Number of negative pairs.
NEGATIVE_PAIR_COUNT = 200

# Cosine thresholds to evaluate.
# A threshold means:
#     similarity >= threshold -> predicted duplicate
#
# We sweep the range instead of arbitrarily choosing a threshold.
THRESHOLDS = np.arange(
    0.30,
    0.991,
    0.01,
)


def has_pothole(label_path: Path) -> bool:
    """
    Check whether a YOLO label file contains at least one pothole.

    We only need to know whether the source image is eligible for the
    embedding benchmark; unlike the crop experiment, we do not need
    the bounding-box coordinates.
    """

    # Missing labels mean there is no usable pothole annotation.
    if not label_path.exists():
        return False

    # Inspect every annotation in the file.
    for line in label_path.read_text().splitlines():
        parts = line.split()

        # Ignore malformed rows.
        if len(parts) != 5:
            continue

        # The first YOLO value is the class ID.
        class_id = int(parts[0])

        # Class 2 represents potholes in this dataset.
        if class_id == POTHOLE_CLASS_ID:
            return True

    return False


def find_pothole_images() -> list[Path]:
    """
    Find all test images containing at least one annotated pothole.
    """

    pothole_images = []

    # Process images in deterministic order.
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

        if has_pothole(label_path):
            pothole_images.append(image_path)

    return pothole_images


def transform_image(image: Image.Image) -> Image.Image:
    """
    Create a controlled variation of an image.

    The transformation represents small differences in capture conditions
    while preserving the underlying scene.
    """

    # Slight rotation represents a small camera-angle difference.
    transformed = image.rotate(
        3,
        expand=False,
    )

    # Slight brightness change represents different lighting.
    transformed = ImageEnhance.Brightness(
        transformed
    ).enhance(1.08)

    # Small center crop represents slightly different framing.
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


def load_embedding_model():
    """
    Load the lightweight MobileNetV3 embedding model.

    The ImageNet classification head is removed so the model produces
    feature vectors instead of class predictions.
    """

    model = timm.create_model(
        "mobilenetv3_small_100.lamb_in1k",
        pretrained=True,
        num_classes=0,
    )

    # Evaluation mode disables training-only behavior.
    model.eval()

    # Explicitly use CPU because CivicLens v1 is CPU-compatible.
    model.to("cpu")

    # Use preprocessing associated with this exact pretrained model.
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
    Convert an image into a normalized MobileNetV3 embedding.
    """

    # Apply the model's expected preprocessing pipeline.
    tensor = transform(image).unsqueeze(0)

    # No gradients are needed because this is inference only.
    with torch.inference_mode():
        embedding = model(tensor)

    # Convert the model output to a NumPy vector.
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
    Calculate cosine similarity between two normalized vectors.
    """

    # Normalized vectors make the dot product equal to cosine similarity.
    return float(
        np.dot(vector_a, vector_b)
    )


def create_pairs(
    images: list[Path],
    model,
    transform,
) -> tuple[list[float], list[float]]:
    """
    Create positive and negative similarity scores.

    Positive:
        source image vs transformed version of itself.

    Negative:
        one source image vs a different source image.
    """

    # Ensure reproducible pair selection.
    random.seed(RANDOM_SEED)

    # We need enough unique images for the requested negative pairs.
    if len(images) < 2:
        raise RuntimeError(
            "At least two pothole images are required."
        )

    # Cache embeddings for every selected source image.
    embedding_cache = {}

    def get_embedding(image_path: Path) -> np.ndarray:
        """Load and cache one source image's embedding."""

        if image_path not in embedding_cache:
            with Image.open(image_path) as image:
                rgb_image = image.convert("RGB")

            embedding_cache[image_path] = embed_image(
                rgb_image,
                model,
                transform,
            )

        return embedding_cache[image_path]

    positive_scores = []

    # Select source images for the positive experiment.
    positive_sources = random.sample(
        images,
        POSITIVE_PAIR_COUNT,
    )

    for image_path in positive_sources:
        # Load the original source image.
        with Image.open(image_path) as image:
            original = image.convert("RGB")

            # Create the controlled positive transformation.
            transformed = transform_image(original)

            # Embed both versions.
            original_embedding = embed_image(
                original,
                model,
                transform,
            )

            transformed_embedding = embed_image(
                transformed,
                model,
                transform,
            )

        positive_scores.append(
            cosine_similarity(
                original_embedding,
                transformed_embedding,
            )
        )

    negative_scores = []

    # Generate negative pairs by selecting two different source images.
    for _ in range(NEGATIVE_PAIR_COUNT):
        image_a, image_b = random.sample(
            images,
            2,
        )

        embedding_a = get_embedding(image_a)
        embedding_b = get_embedding(image_b)

        negative_scores.append(
            cosine_similarity(
                embedding_a,
                embedding_b,
            )
        )

    return positive_scores, negative_scores


def calculate_metrics(
    positive_scores: list[float],
    negative_scores: list[float],
    threshold: float,
) -> dict[str, float]:
    """
    Calculate classification metrics for one similarity threshold.

    Ground truth:
        Positive pair -> duplicate
        Negative pair -> not duplicate

    Prediction:
        similarity >= threshold -> duplicate
    """

    # Positive pairs above the threshold are correctly identified.
    true_positive = sum(
        score >= threshold
        for score in positive_scores
    )

    # Positive pairs below the threshold are missed duplicates.
    false_negative = sum(
        score < threshold
        for score in positive_scores
    )

    # Negative pairs above the threshold become false duplicates.
    false_positive = sum(
        score >= threshold
        for score in negative_scores
    )

    # Negative pairs below the threshold are correctly rejected.
    true_negative = sum(
        score < threshold
        for score in negative_scores
    )

    # Precision answers:
    # "When we say duplicate, how often are we correct?"
    precision_denominator = (
        true_positive + false_positive
    )

    precision = (
        true_positive / precision_denominator
        if precision_denominator
        else 0.0
    )

    # Recall answers:
    # "How many actual duplicate pairs did we find?"
    recall_denominator = (
        true_positive + false_negative
    )

    recall = (
        true_positive / recall_denominator
        if recall_denominator
        else 0.0
    )

    # F1 balances precision and recall.
    f1_denominator = precision + recall

    f1 = (
        2 * precision * recall / f1_denominator
        if f1_denominator
        else 0.0
    )

    return {
        "threshold": threshold,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "true_positive": true_positive,
        "false_positive": false_positive,
        "false_negative": false_negative,
        "true_negative": true_negative,
    }


def main() -> None:
    """
    Run the complete threshold evaluation.
    """

    print("MobileNetV3 embedding threshold benchmark")
    print("-----------------------------------------")

    # Find all test images containing potholes.
    images = find_pothole_images()

    print(
        f"Pothole test images available: {len(images)}"
    )

    # Confirm that the dataset is large enough for our experiment.
    required_images = max(
        POSITIVE_PAIR_COUNT,
        2,
    )

    if len(images) < required_images:
        raise RuntimeError(
            "Not enough pothole images for the benchmark."
        )

    print(
        f"Positive pairs:                 "
        f"{POSITIVE_PAIR_COUNT}"
    )

    print(
        f"Negative pairs:                 "
        f"{NEGATIVE_PAIR_COUNT}"
    )

    # Load MobileNetV3 once for the entire experiment.
    model, transform = load_embedding_model()

    # Generate the similarity distributions.
    positive_scores, negative_scores = create_pairs(
        images,
        model,
        transform,
    )

    # Print the raw distribution statistics first.
    print()
    print("Positive pairs")
    print(
        f"  Mean cosine similarity: "
        f"{np.mean(positive_scores):.4f}"
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
        f"{np.mean(negative_scores):.4f}"
    )
    print(
        f"  Min cosine similarity:  "
        f"{min(negative_scores):.4f}"
    )
    print(
        f"  Max cosine similarity:  "
        f"{max(negative_scores):.4f}"
    )

    # Evaluate every threshold.
    results = [
        calculate_metrics(
            positive_scores,
            negative_scores,
            float(threshold),
        )
        for threshold in THRESHOLDS
    ]

    # Choose the threshold with the highest F1 score on this benchmark.
    # This is a benchmark result, NOT automatically our production
    # threshold. We still need real-world duplicate pairs.
    best_result = max(
        results,
        key=lambda result: result["f1"],
    )

    print()
    print("Best benchmark threshold")
    print(
        f"  Threshold:  {best_result['threshold']:.2f}"
    )
    print(
        f"  Precision:  {best_result['precision']:.4f}"
    )
    print(
        f"  Recall:     {best_result['recall']:.4f}"
    )
    print(
        f"  F1:         {best_result['f1']:.4f}"
    )
    print(
        f"  TP:         {best_result['true_positive']}"
    )
    print(
        f"  FP:         {best_result['false_positive']}"
    )
    print(
        f"  FN:         {best_result['false_negative']}"
    )
    print(
        f"  TN:         {best_result['true_negative']}"
    )

    # Also show several thresholds around the strongest result.
    # This helps us see whether the optimum is stable or just a narrow
    # spike caused by this small synthetic benchmark.
    print()
    print("Threshold stability")
    print(
        "  threshold   precision   recall      F1"
    )

    for result in results:
        # Only display thresholds near the best result.
        if abs(
            result["threshold"]
            - best_result["threshold"]
        ) <= 0.05:
            print(
                f"  {result['threshold']:.2f}"
                f"        {result['precision']:.3f}"
                f"        {result['recall']:.3f}"
                f"        {result['f1']:.3f}"
            )

    print()
    print("Important:")
    print(
        "These are synthetic same-image positives, "
        "not real same-pothole captures."
    )


if __name__ == "__main__":
    main()