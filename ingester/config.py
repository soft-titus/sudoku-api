"""
Configuration, read from environment variables
"""

import os


AWS_ACCESS_KEY_ID = os.getenv("MINIO_ROOT_USER", "sudoku")
AWS_SECRET_ACCESS_KEY = os.getenv("MINIO_ROOT_PASSWORD", "verySECRET123")
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
