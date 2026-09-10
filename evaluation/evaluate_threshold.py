from pathlib import Path

import cv2
import numpy as np
from ultralytics import YOLO


# -----------------------------
# Configuration
# -----------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent

MODEL_PATH = PROJECT_ROOT / "ml" / "weights" / "yolo26_best.pt"
TEST_IMAGES = PROJECT_ROOT / "evaluation" / "dataset" / "test" / "images"
TEST_LABELS = PROJECT_ROOT / "evaluation" / "dataset" / "test" / "labels"

POTHOLE_CLASS_ID = 2

# Keep confidence fixed at the best threshold found during
# our previous validation sweep so that only IoU changes here.
CONFIDENCE_THRESHOLD = 0.19

# Test different localization strictness levels.
# A higher IoU means the predicted box must overlap the
# ground-truth box more accurately to count as a true positive.
#IOU_THRESHOLDS = [0.30, 0.50, 0.75]

# Use the standard IoU criterion selected for our final evaluation.
# We are no longer comparing thresholds because the test set must
# remain a single final held-out measurement.
IOU_THRESHOLD = 0.50


# -----------------------------
# Utility functions
# -----------------------------

def load_ground_truth(label_path: Path, image_width: int, image_height: int):
    """
    Load pothole ground-truth boxes from a YOLO-format label file.

    YOLO format:
        class_id x_center y_center width height

    Coordinates are normalized to [0, 1].
    """

    boxes = []

    if not label_path.exists():
        return boxes

    with label_path.open("r", encoding="utf-8") as file:
        for line in file:
            parts = line.strip().split()

            if len(parts) != 5:
                continue

            class_id = int(parts[0])

            # Only potholes are relevant for this evaluation.
            if class_id != POTHOLE_CLASS_ID:
                continue

            x_center = float(parts[1]) * image_width
            y_center = float(parts[2]) * image_height
            width = float(parts[3]) * image_width
            height = float(parts[4]) * image_height

            x_min = x_center - width / 2
            y_min = y_center - height / 2
            x_max = x_center + width / 2
            y_max = y_center + height / 2

            boxes.append([x_min, y_min, x_max, y_max])

    return boxes


def calculate_iou(box_a, box_b):
    """
    Calculate Intersection over Union (IoU) between two boxes.

    IoU measures how much the predicted bounding box overlaps
    with the ground-truth bounding box.
    """

    x_left = max(box_a[0], box_b[0])
    y_top = max(box_a[1], box_b[1])
    x_right = min(box_a[2], box_b[2])
    y_bottom = min(box_a[3], box_b[3])

    intersection_width = max(0.0, x_right - x_left)
    intersection_height = max(0.0, y_bottom - y_top)

    intersection_area = intersection_width * intersection_height

    area_a = max(0.0, box_a[2] - box_a[0]) * max(
        0.0, box_a[3] - box_a[1]
    )

    area_b = max(0.0, box_b[2] - box_b[0]) * max(
        0.0, box_b[3] - box_b[1]
    )

    union_area = area_a + area_b - intersection_area

    if union_area == 0:
        return 0.0

    return intersection_area / union_area


def match_predictions_to_ground_truth(
    predictions,
    ground_truths,
    iou_threshold,
):
    """
    Match predictions against ground-truth potholes.

    A prediction becomes a true positive when its best available
    ground-truth box has IoU >= the supplied threshold.

    Each ground-truth box can only be matched once.
    """

    matched_ground_truth = set()

    true_positives = 0
    false_positives = 0

    # Match high-confidence predictions first.
    predictions = sorted(
        predictions,
        key=lambda prediction: prediction["confidence"],
        reverse=True,
    )

    for prediction in predictions:
        best_iou = 0.0
        best_ground_truth_index = None

        for index, ground_truth in enumerate(ground_truths):
            if index in matched_ground_truth:
                continue

            iou = calculate_iou(
                prediction["box"],
                ground_truth,
            )

            if iou > best_iou:
                best_iou = iou
                best_ground_truth_index = index

        # The same prediction is a TP only if its overlap
        # satisfies the IoU criterion being tested.
        if (
            best_ground_truth_index is not None
            and best_iou >= iou_threshold
        ):
            true_positives += 1
            matched_ground_truth.add(best_ground_truth_index)
        else:
            false_positives += 1

    # Any unmatched ground-truth pothole is a missed detection.
    false_negatives = len(ground_truths) - len(matched_ground_truth)

    return (
        true_positives,
        false_positives,
        false_negatives,
    )


def calculate_metrics(tp, fp, fn):
    """
    Calculate precision, recall and F1 score.
    """

    precision = (
        tp / (tp + fp)
        if (tp + fp) > 0
        else 0.0
    )

    recall = (
        tp / (tp + fn)
        if (tp + fn) > 0
        else 0.0
    )

    if precision + recall == 0:
        f1 = 0.0
    else:
        f1 = (
            2 * precision * recall
            / (precision + recall)
        )

    return precision, recall, f1


# -----------------------------
# Evaluation
# -----------------------------

def main():
    print("Loading pothole model...")
    model = YOLO(str(MODEL_PATH))

    image_paths = sorted(
        list(TEST_IMAGES.glob("*.jpg"))
        + list(TEST_IMAGES.glob("*.jpeg"))
        + list(TEST_IMAGES.glob("*.png"))
    )

    if not image_paths:
        raise RuntimeError(
            f"No test images found in {TEST_IMAGES}"
        )

    print(f"Model: {MODEL_PATH}")
    print(f"Test images: {len(image_paths)}")
    print(f"Ground-truth pothole class ID: {POTHOLE_CLASS_ID}")
    print(f"Fixed confidence threshold: {CONFIDENCE_THRESHOLD}")
    print(f"IoU threshold: {IOU_THRESHOLD}")
    print()

    # Store predictions and ground truth for each image so the
    # final metric calculation is separated from model inference.
    image_results = []

    total_ground_truth_potholes = 0

    for index, image_path in enumerate(image_paths, start=1):

        image = cv2.imread(str(image_path))

        if image is None:
            print(
                f"WARNING: could not read {image_path.name}"
            )
            continue

        image_height, image_width = image.shape[:2]

        label_path = (
            TEST_LABELS
            / f"{image_path.stem}.txt"
        )

        ground_truths = load_ground_truth(
            label_path,
            image_width,
            image_height,
        )

        total_ground_truth_potholes += len(ground_truths)

        # Use a very low inference cutoff so Ultralytics does not
        # remove predictions that we may want to evaluate.
        results = model(
            image,
            conf=0.001,
            verbose=False,
        )

        predictions = []

        for result in results:
            for box in result.boxes:

                confidence = float(box.conf[0])
                class_id = int(box.cls[0])

                # The selected model is a single-class pothole detector,
                # so class ID 0 represents the model's pothole class.
                if class_id != 0:
                    continue

                x_min, y_min, x_max, y_max = map(
                    float,
                    box.xyxy[0],
                )

                predictions.append(
                    {
                        "confidence": confidence,
                        "box": [
                            x_min,
                            y_min,
                            x_max,
                            y_max,
                        ],
                    }
                )

        # Apply our fixed confidence threshold once.
        filtered_predictions = [
            prediction
            for prediction in predictions
            if prediction["confidence"] >= CONFIDENCE_THRESHOLD
        ]

        image_results.append(
            {
                "predictions": filtered_predictions,
                "ground_truths": ground_truths,
            }
        )

        if index % 100 == 0:
            print(
                f"Processed {index}/{len(image_paths)} images..."
            )

    print()
    print(
        f"Total ground-truth potholes: "
        f"{total_ground_truth_potholes}"
    )
    print()

    # Evaluate once on the held-out test set using the operating point
    # selected from validation: confidence 0.19 and IoU 0.50.
    total_tp = 0
    total_fp = 0
    total_fn = 0

    for image_result in image_results:

        tp, fp, fn = match_predictions_to_ground_truth(
            image_result["predictions"],
            image_result["ground_truths"],
            IOU_THRESHOLD,
        )

        total_tp += tp
        total_fp += fp
        total_fn += fn

    precision, recall, f1 = calculate_metrics(
        total_tp,
        total_fp,
        total_fn,
    )

    print(f"IoU threshold: {IOU_THRESHOLD:.2f}")
    print(f"Precision:     {precision:.3f}")
    print(f"Recall:        {recall:.3f}")
    print(f"F1:            {f1:.3f}")
    print(f"TP:            {total_tp}")
    print(f"FP:            {total_fp}")
    print(f"FN:            {total_fn}")


if __name__ == "__main__":
    main()