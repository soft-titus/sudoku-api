"""
Helper functions to upload files to S3 or MinIO using botocore.
"""

import logging
from pathlib import Path
from typing import Optional

import botocore.session
from botocore.client import BaseClient

import config


def get_s3_client() -> BaseClient:
    """Return a botocore S3 client, using custom endpoint if provided."""
    session = botocore.session.get_session()

    s3_config = {
        "aws_access_key_id": config.AWS_ACCESS_KEY_ID,
        "aws_secret_access_key": config.AWS_SECRET_ACCESS_KEY,
        "region_name": config.AWS_REGION,
    }

    if config.S3_ENDPOINT_URL:
        s3_config["endpoint_url"] = config.S3_ENDPOINT_URL

    return session.create_client("s3", **s3_config)


def upload_file_from_path(
    file_path: str,
    object_key: str,
    bucket: str,
    content_type: Optional[str] = None,
) -> None:
    """
    Upload a file from disk to S3 / MinIO.

    Args:
        file_path: Local path to the file
        object_key: S3 object key (e.g. puzzleId/solution.png)
        bucket: S3 bucket name
        content_type: Optional MIME type
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    client = get_s3_client()

    put_kwargs = {
        "Bucket": bucket,
        "Key": object_key,
    }

    if content_type:
        put_kwargs["ContentType"] = content_type

    try:
        with path.open("rb") as file_obj:
            client.put_object(
                Body=file_obj,
                **put_kwargs,
            )
        logging.info("Uploaded file to s3://%s/%s", bucket, object_key)
    except Exception:
        logging.exception("Failed to upload file %s to bucket %s", file_path, bucket)
        raise
