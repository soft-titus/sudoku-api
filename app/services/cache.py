"""
Cache service module with Redis.
"""

import logging
from redis import Redis, exceptions as redis_exceptions

import config

logger = logging.getLogger(__name__)


class RedisClient:
    """
    Singleton wrapper for Redis client.
    """

    _instance: Redis | None = None

    @classmethod
    def get_client(cls) -> Redis:
        """
        Get the Redis client instance.
        Initializes the client if it hasn't been created yet.
        """
        if cls._instance is None:
            cls._instance = Redis(
                host=config.REDIS_HOST,
                port=config.REDIS_PORT,
                db=config.REDIS_DB,
                decode_responses=True,
            )
            logger.info("Redis client initialized")
        return cls._instance

    @classmethod
    def check_health(cls) -> None:
        """
        Perform a simple health check on Redis by pinging the server.

        Raises:
            redis.exceptions.ConnectionError: if Redis is not reachable.
        """
        client = cls.get_client()
        try:
            client.ping()
            logger.info("Redis ping successful")
        except redis_exceptions.ConnectionError as e:
            logger.error("Redis ping failed: %s", e)
            raise e

    @classmethod
    def set_with_ttl(cls, key: str, value: str, ttl: int | None = None) -> None:
        """
        Set a key-value pair in Redis with a TTL.

        Args:
            key (str): Redis key.
            value (str): Value to store.
            ttl (int | None): Time-to-live in seconds.
        """
        client = cls.get_client()

        if ttl is None:
            ttl_hours = config.CACHE_TTL_HOURS
            ttl = ttl_hours * 60 * 60

        try:
            client.setex(name=key, time=ttl, value=value)
            logger.info("Set key in Redis with TTL=%s seconds: %s", ttl, key)
        except redis_exceptions.RedisError as e:
            logger.warning("Failed to set key in Redis: %s", e)

    @classmethod
    def clear_key(cls, key: str) -> bool:
        """
        Delete a key from Redis if it exists.

        Args:
            key (str): Redis key to delete.

        Returns:
            bool: True if the key was deleted, False if the key did not exist.
        """
        client = cls.get_client()
        try:
            deleted_count = client.delete(key)
            if deleted_count > 0:
                logger.info("Deleted key from Redis: %s", key)
                return True
            logger.info("Key not found in Redis: %s", key)
            return False
        except redis_exceptions.RedisError as e:
            logger.warning("Failed to delete key from Redis: %s", e)
            return False
