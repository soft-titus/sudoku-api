"""
S3 service module.
"""

import logging
import time
from typing import Optional

import botocore.session
from botocore.client import BaseClient
from botocore.exceptions import ClientError

import config

logger = logging.getLogger(__name__)


class S3Client:
    """
    S3 client wrapper with cached health check and object deletion.
    """

    _client: Optional[BaseClient] = None
    _last_check_ts: float = 0.0
    _cache_ttl: int = 3600  # seconds (1 hour)

    @classmethod
    def _create_client(cls) -> BaseClient:
        """
        Create a botocore S3 client using optional custom endpoint.

        Returns:
            BaseClient: Botocore S3 client
        """
        session = botocore.session.get_session()

        s3_config = {
            "aws_access_key_id": config.AWS_ACCESS_KEY_ID,
            "aws_secret_access_key": config.AWS_SECRET_ACCESS_KEY,
            "region_name": config.AWS_REGION,
        }

        if config.S3_ENDPOINT_URL:
            s3_config["endpoint_url"] = config.S3_ENDPOINT_URL

        return session.create_client("s3", **s3_config)

    @classmethod
    def get_client(cls) -> BaseClient:
        """
        Return a singleton S3 client.

        Returns:
            BaseClient: Botocore S3 client
        """
        if cls._client is None:
            cls._client = cls._create_client()

        return cls._client

    @classmethod
    def check_health(cls, bucket: str) -> None:
        """
        Check S3 / MinIO availability using HeadBucket.

        This method is cached for AWS S3 to reduce request cost and latency.
        Raises ClientError if the bucket is unreachable.

        Args:
            bucket (str): The S3 bucket name to check.
        """
        now = time.time()
        is_aws_s3 = not config.S3_ENDPOINT_URL

        if is_aws_s3 and now - cls._last_check_ts < cls._cache_ttl:
            return

        client = cls.get_client()

        try:
            client.head_bucket(Bucket=bucket)
            cls._last_check_ts = now
            logger.info("S3 health check OK for bucket '%s'", bucket)
        except ClientError as e:
            logger.error("S3 health check FAILED for bucket '%s': %s", bucket, e)
            raise

    @classmethod
    def delete_object(cls, bucket: str, object_key: str) -> None:
        """
        Delete an object from S3 / MinIO.

        Args:
            bucket (str): The S3 bucket name.
            object_key (str): The S3 object key to delete (e.g., 'puzzleId/solution.png').

        Raises:
            ClientError: If the delete operation fails.
        """
        client = cls.get_client()

        try:
            client.delete_object(Bucket=bucket, Key=object_key)
            logger.info("Deleted object s3://%s/%s", bucket, object_key)
        except ClientError as e:
            logger.error(
                "Failed to delete object s3://%s/%s: %s",
                bucket,
                object_key,
                e,
            )
            raise

    @classmethod
    def download_object(cls, bucket: str, object_key: str) -> bytes:
        """
        Download an object from S3 / MinIO.

        Args:
            bucket (str): S3 bucket name.
            object_key (str): Object key (e.g., 'puzzleId/solution.png').

        Returns:
            bytes: Object content.

        Raises:
            ClientError: If the object does not exist or download fails.
        """
        client = cls.get_client()
        try:
            response = client.get_object(Bucket=bucket, Key=object_key)
            data = response["Body"].read()
            logger.info("Downloaded object s3://%s/%s", bucket, object_key)
            return data
        except ClientError as e:
            logger.error(
                "Failed to download object s3://%s/%s: %s",
                bucket,
                object_key,
                e,
            )
            raise
