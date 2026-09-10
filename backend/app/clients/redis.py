import os

import redis
from dotenv import load_dotenv


# Load configuration from the project's .env file.
load_dotenv("../.env")


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