"""
Benchmark a lightweight pretrained image-embedding model.

This script is intentionally separate from CivicLens's production
services. We first want to measure whether the candidate model is
small and fast enough on the development machine before integrating
it into duplicate detection.
"""

import sys
import time
from pathlib import Path

import timm
import torch
from PIL import Image


# The first candidate embedding model for CivicLens.
# MobileNetV3 Small is lightweight enough to be practical on CPU.
MODEL_NAME = "mobilenetv3_small_100.lamb_in1k"


def load_image(image_path: Path) -> Image.Image:
    """
    Load and validate the image used for the benchmark.

    Keeping image loading separate makes it obvious where failures
    come from if the supplied test image is invalid.
    """

    # Open the image and explicitly convert it to RGB so the model
    # always receives the same three-channel input format.
    try:
        return Image.open(image_path).convert("RGB")
    except Exception as exc:
        raise ValueError(
            f"Could not open image: {image_path}"
        ) from exc


def main() -> None:
    """
    Load the embedding model, generate one embedding, and report
    useful performance information.
    """

    # Require the caller to provide a real image rather than silently
    # benchmarking an arbitrary image from the project.
    if len(sys.argv) != 2:
        print(
            "Usage: python scripts/benchmark_embedding.py "
            "<image_path>"
        )
        raise SystemExit(1)

    image_path = Path(sys.argv[1])

    if not image_path.exists():
        print(f"Image not found: {image_path}")
        raise SystemExit(1)

    # CivicLens v1 is designed to run on CPU, so explicitly select CPU
    # instead of accidentally depending on a CUDA-capable machine.
    device = torch.device("cpu")

    print(f"Model: {MODEL_NAME}")
    print(f"Device: {device}")
    print(f"Image: {image_path}")

    # Load the pretrained model without its ImageNet classification
    # layer. The resulting output is a feature vector suitable for
    # similarity comparisons.
    model = timm.create_model(
        MODEL_NAME,
        pretrained=True,
        num_classes=0,
    )

    # Evaluation mode disables training-specific behavior such as
    # dropout, making inference deterministic and appropriate for
    # generating embeddings.
    model = model.to(device)
    model.eval()

    # Ask timm for the preprocessing configuration expected by this
    # particular pretrained model rather than hard-coding resize and
    # normalization values ourselves.
    data_config = timm.data.resolve_model_data_config(model)
    transform = timm.data.create_transform(
        **data_config,
        is_training=False,
    )

    image = load_image(image_path)

    # Convert the PIL image into the tensor format expected by the
    # neural network and add a batch dimension.
    input_tensor = transform(image).unsqueeze(0).to(device)

    # The first inference can include one-time framework/model overhead,
    # so we perform a warm-up before measuring actual inference time.
    with torch.inference_mode():
        model(input_tensor)

    # Measure the actual embedding generation time after warm-up.
    start_time = time.perf_counter()

    with torch.inference_mode():
        embedding = model(input_tensor)

    elapsed_ms = (time.perf_counter() - start_time) * 1000

    # Flatten the single-image batch into a simple feature vector.
    embedding = embedding.squeeze(0)

    # Normalize the embedding so cosine similarity can later be used
    # directly as a measure of visual similarity.
    embedding = torch.nn.functional.normalize(
        embedding,
        dim=0,
    )

    print()
    print("Embedding benchmark")
    print("-------------------")
    print(f"Embedding dimensions: {embedding.shape[0]}")
    print(f"Inference time:       {elapsed_ms:.2f} ms")
    print(f"Embedding norm:       {embedding.norm().item():.4f}")
    print(f"Model parameters:     {sum(p.numel() for p in model.parameters()):,}")


if __name__ == "__main__":
    main()