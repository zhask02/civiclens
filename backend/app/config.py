import os
from pathlib import Path

from dotenv import load_dotenv


# Resolve the project root from this file so configuration works
# regardless of whether Uvicorn is started from backend/ or the repo root.
PROJECT_ROOT = Path(__file__).resolve().parents[2]

def load_project_environment(project_root: Path = PROJECT_ROOT) -> bool:
    """Load the project's authoritative .env configuration.

    Local configuration must take precedence over variables inherited from a
    terminal or Uvicorn reload parent. Otherwise a stale bearer token in that
    parent process silently overrides the configured token.
    """

    return load_dotenv(project_root / ".env", override=True)


# Load environment variables from the single project-level .env file.
load_project_environment()


# Read the relative model path from environment configuration.
# Keeping this configurable means deployment can point CivicLens at
# a different model without modifying API or service code.
POTHOLE_MODEL_PATH = os.getenv(
    "POTHOLE_MODEL_PATH",
    "ml/weights/yolo26_best.pt",
)


def get_pothole_model_path() -> str:
    """
    Resolve the configured pothole model path to an absolute path.

    Relative paths are interpreted from the CivicLens project root,
    keeping model configuration independent from the process's
    current working directory.
    """

    model_path = Path(POTHOLE_MODEL_PATH)

    # Absolute paths are already fully resolved and need no adjustment.
    if model_path.is_absolute():
        return str(model_path)

    # Relative model paths are anchored to the project root.
    return str(PROJECT_ROOT / model_path)
