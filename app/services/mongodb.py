"""
MongoDB service module
"""

import logging
from pymongo import MongoClient
from pymongo.errors import PyMongoError

import config

logger = logging.getLogger(__name__)


class MongoDBClient:
    """
    Singleton wrapper for MongoDB client.
    """

    _instance: MongoClient | None = None

    @classmethod
    def get_client(cls) -> MongoClient:
        """
        Get the MongoDB client instance.
        Initializes the client if it hasn't been created yet.
        """
        if cls._instance is None:
            cls._instance = MongoClient(config.MONGO_URI, serverSelectionTimeoutMS=2000)
            logger.info("MongoDB client initialized")
        return cls._instance

    @classmethod
    def check_health(cls) -> None:
        """
        Perform a simple health check by pinging the MongoDB server.

        Raises:
            RuntimeError: If MongoDB is not reachable.
        """
        client = cls.get_client()
        try:
            client.admin.command("ping")
            logger.info("MongoDB connection OK")
        except PyMongoError as e:
            logger.error("MongoDB health check failed: %s", e)
            raise RuntimeError("MongoDB: not connected") from e
