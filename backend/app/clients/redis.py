import os
from pathlib import Path

import redis
from dotenv import load_dotenv


# Resolve the project root from this file's location rather than relying
# on the directory from which Python happens to be launched.
PROJECT_ROOT = Path(__file__).resolve().parents[3]

# Load environment variables from the project's root .env file.
load_dotenv(PROJECT_ROOT / ".env")


# Read the Redis connection URL from environment configuration.
# Keeping this outside the code means production can use a different
# Redis server without changing application code.
REDIS_URL = os.environ["REDIS_URL"]


# Create the Redis client used by CivicLens.
# decode_responses=True means Redis returns normal Python strings
# instead of raw bytes when we retrieve cached values.
redis_client = redis.Redis.from_url(
    REDIS_URL,
    decode_responses=True,
)