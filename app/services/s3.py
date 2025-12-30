"""
S3 service module.

Provides a cached health check for AWS S3 or S3-compatible storage (e.g. MinIO)
using a low-cost HeadBucket operation.
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
    S3 client wrapper with cached health check.
    """

    _client: Optional[BaseClient] = None
    _last_check_ts: float = 0.0
    _cache_ttl: int = 3600  # seconds (1 hour)

    @classmethod
    def _create_client(cls) -> BaseClient:
        """
        Create a botocore S3 client using optional custom endpoint.
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
        """
        if cls._client is None:
            cls._client = cls._create_client()

        return cls._client

    @classmethod
    def check_health(cls) -> None:
        """
        Check S3 availability using HeadBucket.

        This method is cached to reduce request cost and latency.
        Raises ClientError if the bucket is unreachable.
        """
        now = time.time()

        is_aws_s3 = not config.S3_ENDPOINT_URL
        if is_aws_s3 and now - cls._last_check_ts < cls._cache_ttl:
            return

        client = cls.get_client()

        try:
            client.head_bucket(Bucket=config.S3_BUCKET_NAME)
            cls._last_check_ts = now
            logger.info("S3 health check OK")
        except ClientError as exc:
            logger.error("S3 health check FAILED: %s", exc)
            raise
