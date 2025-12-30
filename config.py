"""
Configuration, read from environment variables
"""

import os


LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

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

AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", "sudoku")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "verySECRET123")
AWS_REGION = os.getenv("AWS_REGION", "ap-southeast-1")

S3_PROTOCOL = os.getenv("S3_PROTOCOL", "https")
S3_HOST = os.getenv("S3_HOST")
S3_PORT = os.getenv("S3_PORT")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "sudoku")

S3_ENDPOINT_URL = ""
if S3_HOST:
    S3_ENDPOINT_URL = f"{S3_PROTOCOL}://{S3_HOST}"
    if S3_PORT:
        S3_ENDPOINT_URL = f"{S3_ENDPOINT_URL}:{S3_PORT}"
