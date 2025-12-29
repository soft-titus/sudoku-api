"""
Configuration, read from environment variables
"""

import os


LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

IMAGE_BASE_URL = os.getenv("IMAGE_BASE_URL", "http://minio:9000/sudoku")
CACHE_TTL_HOURS = int(os.getenv("CACHE_TTL_HOURS", "168"))

KAFKA_BROKER_HOST = os.getenv("KAFKA_BROKER_HOST", "kafka")
KAFKA_BROKER_PORT = os.getenv("KAFKA_BROKER_PORT", "9092")

KAFKA_BOOTSTRAP_SERVERS = f"{KAFKA_BROKER_HOST}:{KAFKA_BROKER_PORT}"

KAFKA_PUZZLE_TOPIC = os.getenv("KAFKA_PUZZLE_TOPIC", "sudoku.puzzle.generate")

MONGO_HOST = os.getenv("MONGO_HOST", "mongodb")
MONGO_PORT = os.getenv("MONGO_PORT", "27017")
MONGO_USER = os.getenv("MONGO_USER", "sudoku")
MONGO_PASSWORD = os.getenv("MONGO_PASSWORD", "Sudoku123")
MONGO_DB = os.getenv("MONGO_DB", "sudoku")
MONGO_OPTIONS = os.getenv("MONGO_OPTIONS")
MONGO_COLLECTION_NAME = os.getenv("MONGO_COLLECTION_NAME", "puzzle")

MONGO_URI = (
    f"mongodb://{MONGO_USER}:{MONGO_PASSWORD}" f"@{MONGO_HOST}:{MONGO_PORT}/{MONGO_DB}"
)
if MONGO_OPTIONS:
    MONGO_URI = f"{MONGO_URI}?{MONGO_OPTIONS.lstrip('?')}"

REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
