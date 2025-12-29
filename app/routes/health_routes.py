"""
Health router
"""

from fastapi import APIRouter, HTTPException
from app.helpers.logger import logger
from app.services.cache import RedisClient
from app.services.kafka import KafkaClient
from app.services.mongodb import MongoDBClient

router = APIRouter()


@router.get(
    "/health",
    summary="Health check for all dependencies",
    responses={
        200: {
            "description": "All dependencies are healthy.",
            "content": {
                "application/json": {
                    "example": {
                        "status": "ok",
                        "redis": "connected",
                        "kafka": "connected",
                        "mongodb": "connected",
                    }
                }
            },
        },
        503: {
            "description": "One or more dependencies are unreachable.",
            "content": {
                "application/json": {
                    "examples": {
                        "redis_down": {
                            "summary": "Redis unreachable",
                            "value": {"detail": "Redis: not connected"},
                        },
                        "kafka_down": {
                            "summary": "Kafka unreachable",
                            "value": {"detail": "Kafka: not connected"},
                        },
                        "mongodb_down": {
                            "summary": "MongoDB unreachable",
                            "value": {"detail": "MongoDB: not connected"},
                        },
                    }
                }
            },
        },
    },
)
def health():
    """
    Health check endpoint ensuring dependencies are reachable.
    Returns 200 if healthy, 503 if any dependency fails.
    """
    logger.info("Health endpoint hit")

    try:
        RedisClient.check_health()
        redis_status = "connected"
        logger.info("Redis connection OK")
    except Exception as e:
        logger.error("Redis connection FAILED: %s", e)
        raise HTTPException(status_code=503, detail="Redis: not connected") from e

    try:
        KafkaClient.check_health()
        kafka_status = "connected"
        logger.info("Kafka connection OK")
    except Exception as e:
        logger.error("Kafka connection FAILED: %s", e)
        raise HTTPException(status_code=503, detail="Kafka: not connected") from e

    try:
        MongoDBClient.check_health()
        mongodb_status = "connected"
        logger.info("MongoDB connection OK")
    except Exception as e:
        logger.error("MongoDB connection FAILED: %s", e)
        raise HTTPException(status_code=503, detail="MongoDB: not connected") from e

    logger.info("Health endpoint : success")

    return {
        "status": "ok",
        "redis": redis_status,
        "kafka": kafka_status,
        "mongodb": mongodb_status,
    }
