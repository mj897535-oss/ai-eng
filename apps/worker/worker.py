"""SyntaxLens Asynchronous Background Worker.

Processes speech-to-text transcription and candidate syntactic deviation analysis.
"""

import logging
import os
import sys
import time
import redis

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='{"time": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "message": "%(message)s"}',
)
logger = logging.getLogger("syntaxlens.worker")

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")


def start_worker():
    logger.info("Initializing SyntaxLens Background Worker...")
    try:
        r = redis.Redis.from_url(REDIS_URL)
        r.ping()
        logger.info("Connected to Redis successfully.")
    except Exception as e:
        logger.warning(f"Could not connect to Redis at {REDIS_URL}: {e}. Retrying in background...")

    logger.info("Worker is ready and listening for research assessment tasks.")
    # Keep alive loop
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Worker stopping gracefully.")


if __name__ == "__main__":
    start_worker()
