"""Puzzle routes for Sudoku API."""

from datetime import datetime, timezone
import json

from fastapi import APIRouter, HTTPException
from pymongo.errors import DuplicateKeyError

from app.helpers.logger import logger
from app.models.puzzle import (
    PuzzleCreationRequest,
    PuzzleUpdateRequest,
    PuzzleResponse,
    PuzzleStatus,
)
from app.services.cache import RedisClient
from app.services.kafka import KafkaClient
from app.services.mongodb import MongoDBClient
from app.services.s3 import S3Client
import config

router = APIRouter()


@router.post(
    "/puzzle",
    summary="Create a new Sudoku puzzle",
    description=(
        "Creates a new Sudoku puzzle generation request.\n\n"
        "The puzzle metadata is stored in MongoDB with status "
        "`GENERATING_PUZZLE`, and a Kafka message containing only "
        "the `puzzleId` is published for asynchronous processing.\n\n"
        "If a puzzle with the same `puzzleId` already exists, "
        "the request will be rejected with HTTP 409."
    ),
    response_model=PuzzleResponse,
    responses={
        200: {
            "description": "Puzzle successfully created",
        },
        409: {
            "description": "Puzzle with the given puzzleId already exists",
            "content": {
                "application/json": {
                    "example": {"detail": "Puzzle with id 'abc123' already exists"}
                }
            },
        },
        500: {
            "description": "Internal server error",
            "content": {
                "application/json": {"example": {"detail": "Failed to save puzzle"}}
            },
        },
    },
)
def create_puzzle(request: PuzzleCreationRequest):
    """
    Insert puzzle data into MongoDB with status `GENERATING_PUZZLE`
    and enqueue a Kafka message.

    Args:
        request (PuzzleCreationRequest): Puzzle creation request payload.

    Returns:
        PuzzleResponse: The created puzzle document.
    """
    logger.info("Received puzzle request: %s", request.json())

    now = datetime.now(timezone.utc)

    puzzle_doc = {
        "puzzleId": request.puzzleId,
        "puzzleSize": request.puzzleSize,
        "level": request.level,
        "status": PuzzleStatus.GENERATING_PUZZLE.value,
        "solutionCSVKey": None,
        "puzzleCSVKey": None,
        "solutionImageKey": None,
        "puzzleImageKey": None,
        "failedAt": None,
        "failedReason": None,
        "createdAt": now,
        "updatedAt": now,
    }

    try:
        db = MongoDBClient.get_db()
        collection = db[config.MONGO_COLLECTION_NAME]
        collection.insert_one(puzzle_doc)
        logger.info("Puzzle inserted into MongoDB: %s", request.puzzleId)
    except DuplicateKeyError as e:
        logger.info("Puzzle already exists: %s", request.puzzleId)
        raise HTTPException(
            status_code=409,
            detail=f"Puzzle with id '{request.puzzleId}' already exists",
        ) from e
    except Exception as e:  # pylint: disable=broad-except
        logger.exception("Failed to insert puzzle into MongoDB")
        raise HTTPException(
            status_code=500,
            detail="Failed to save puzzle",
        ) from e

    try:
        kafka_payload = json.dumps({"puzzleId": request.puzzleId})
        KafkaClient.produce_message(
            topic=config.KAFKA_PUZZLE_TOPIC,
            key=request.puzzleId,
            value=kafka_payload,
        )
        logger.info(
            "Kafka message published to %s: %s",
            config.KAFKA_PUZZLE_TOPIC,
            kafka_payload,
        )
    except Exception as e:  # pylint: disable=broad-except
        logger.exception("Failed to enqueue puzzle request to Kafka")
        raise HTTPException(
            status_code=500,
            detail="Failed to enqueue puzzle request",
        ) from e

    return puzzle_doc


@router.get(
    "/puzzle",
    summary="Get a Sudoku puzzle",
    description=(
        "Fetch a Sudoku puzzle by puzzle_id.\n\n"
        "First tries to fetch from Redis cache. If not found, fetches from MongoDB.\n\n"
        "Only stores the puzzle in cache if its status is `SUCCESS` or `FAILED`.\n\n"
        "If the puzzle does not exist, a 404 is returned."
    ),
    response_model=PuzzleResponse,
    responses={
        200: {"description": "Puzzle successfully fetched"},
        404: {"description": "Puzzle with the given puzzle_id not found"},
        500: {"description": "Internal server error"},
    },
)
def get_puzzle(puzzle_id: str):
    """
    Retrieve a puzzle from cache or MongoDB.

    Args:
        puzzle_id (str): The ID of the puzzle to fetch.

    Returns:
        PuzzleResponse: The puzzle document.
    """
    logger.info("Fetching puzzle: %s", puzzle_id)
    cache_key = f"sudoku:{puzzle_id}:data"

    try:
        cached_data = RedisClient.get_key(cache_key)
        if cached_data:
            logger.info("Cache hit for puzzle %s", puzzle_id)
            return json.loads(cached_data)

        db = MongoDBClient.get_db()
        collection = db[config.MONGO_COLLECTION_NAME]

        puzzle = collection.find_one({"puzzleId": puzzle_id})
        if not puzzle:
            logger.info("Puzzle not found: %s", puzzle_id)
            raise HTTPException(status_code=404, detail="Puzzle not found")

        if puzzle["status"] in (PuzzleStatus.SUCCESS.value, PuzzleStatus.FAILED.value):
            ttl_seconds = config.CACHE_TTL_HOURS * 3600
            try:
                RedisClient.set_key(cache_key, json.dumps(puzzle), ttl_seconds)
                logger.info("Puzzle cached with key %s", cache_key)
            except Exception as e:  # pylint: disable=broad-except
                logger.warning("Failed to cache puzzle %s: %s", puzzle_id, e)

        return puzzle

    except HTTPException:
        raise
    except Exception as e:  # pylint: disable=broad-except
        logger.exception("Failed to fetch puzzle %s", puzzle_id)
        raise HTTPException(status_code=500, detail="Failed to fetch puzzle") from e


@router.patch(
    "/puzzle",
    summary="Update an existing Sudoku puzzle",
    description=(
        "Update a Sudoku puzzle's metadata (puzzleSize or level) by puzzleId.\n\n"
        "The update is only allowed if the puzzle's current status is "
        "`SUCCESS` or `FAILED`. If the puzzle is still being processed, "
        "the request will be rejected with HTTP 409.\n\n"
        "After a successful PATCH, the puzzle and solution fields are reset, "
        "image keys cleared, status set to `GENERATING_PUZZLE`, and a Kafka message "
        "containing the `puzzleId` is published for re-generation."
    ),
    response_model=PuzzleResponse,
    responses={
        200: {"description": "Puzzle successfully updated and re-queued"},
        404: {"description": "Puzzle with the given puzzleId not found"},
        409: {
            "description": "Puzzle is still processing, cannot update",
            "content": {
                "application/json": {
                    "example": {"detail": "Puzzle is still generating"}
                }
            },
        },
        500: {"description": "Internal server error"},
    },
)
def update_puzzle(request: PuzzleUpdateRequest):
    """
    Update an existing puzzle's size or level if allowed, reset generated fields,
    delete old puzzle data from S3, clear Redis cache, and enqueue a Kafka message
    to regenerate the puzzle and solution.

    Args:
        request (PuzzleUpdateRequest): Puzzle update payload.

    Returns:
        PuzzleResponse: The updated puzzle document.
    """
    logger.info("Received puzzle update request: %s", request.json())

    try:
        db = MongoDBClient.get_db()
        collection = db[config.MONGO_COLLECTION_NAME]

        existing = collection.find_one({"puzzleId": request.puzzleId})
        if not existing:
            logger.info("Puzzle not found: %s", request.puzzleId)
            raise HTTPException(status_code=404, detail="Puzzle not found")

        if existing["status"] not in (
            PuzzleStatus.SUCCESS.value,
            PuzzleStatus.FAILED.value,
        ):
            logger.info("Puzzle %s is still processing", request.puzzleId)
            raise HTTPException(
                status_code=409,
                detail="Puzzle is still generating or processing, cannot update",
            )

        puzzle_id = request.puzzleId

        cleanup_puzzle_data(puzzle_id)

        now = datetime.now(timezone.utc)
        update_fields = {
            "updatedAt": now,
            "status": PuzzleStatus.GENERATING_PUZZLE.value,
            "solution": None,
            "puzzle": None,
            "solutionCSVKey": None,
            "puzzleCSVKey": None,
            "solutionImageKey": None,
            "puzzleImageKey": None,
            "failedAt": None,
            "failedReason": None,
        }
        if request.puzzleSize is not None:
            update_fields["puzzleSize"] = request.puzzleSize
        if request.level is not None:
            update_fields["level"] = request.level

        collection.update_one({"puzzleId": puzzle_id}, {"$set": update_fields})
        logger.info("Puzzle reset for re-generation: %s", puzzle_id)

        kafka_payload = json.dumps({"puzzleId": puzzle_id})
        KafkaClient.produce_message(
            topic=config.KAFKA_PUZZLE_TOPIC,
            key=puzzle_id,
            value=kafka_payload,
        )
        logger.info(
            "Kafka message published to %s for puzzle %s: %s",
            config.KAFKA_PUZZLE_TOPIC,
            puzzle_id,
            kafka_payload,
        )

        updated = collection.find_one({"puzzleId": puzzle_id})
        return updated

    except HTTPException:
        raise
    except Exception as e:  # pylint: disable=broad-except
        logger.exception("Failed to update puzzle %s", request.puzzleId)
        raise HTTPException(status_code=500, detail="Failed to update puzzle") from e


@router.delete(
    "/puzzle",
    summary="Delete an existing Sudoku puzzle",
    description=(
        "Deletes a Sudoku puzzle by puzzleId.\n\n"
        "This endpoint will remove the puzzle document from MongoDB, "
        "delete any associated files from S3, and clear Redis cache.\n\n"
        "If the puzzle does not exist, a 404 is returned."
    ),
    response_model=PuzzleResponse,
    responses={
        200: {"description": "Puzzle successfully deleted"},
        404: {"description": "Puzzle with the given puzzleId not found"},
        500: {"description": "Internal server error"},
    },
)
def delete_puzzle(puzzle_id: str):
    """
    Delete a puzzle, including its data in S3, Redis, and MongoDB.

    Args:
        puzzle_id (str): The ID of the puzzle to delete.

    Returns:
        PuzzleResponse: The deleted puzzle document.
    """
    logger.info("Received request to delete puzzle: %s", puzzle_id)

    try:
        db = MongoDBClient.get_db()
        collection = db[config.MONGO_COLLECTION_NAME]

        existing = collection.find_one({"puzzleId": puzzle_id})
        if not existing:
            logger.info("Puzzle not found: %s", puzzle_id)
            raise HTTPException(status_code=404, detail="Puzzle not found")

        cleanup_puzzle_data(puzzle_id)

        collection.delete_one({"puzzleId": puzzle_id})
        logger.info("Puzzle deleted from MongoDB: %s", puzzle_id)

        return existing

    except HTTPException:
        raise
    except Exception as e:  # pylint: disable=broad-except
        logger.exception("Failed to delete puzzle %s", puzzle_id)
        raise HTTPException(status_code=500, detail="Failed to delete puzzle") from e


def cleanup_puzzle_data(puzzle_id: str) -> None:
    """Delete puzzle-related objects from S3 and clear Redis cache."""
    s3_keys = [
        f"{puzzle_id}/solution.csv",
        f"{puzzle_id}/puzzle.csv",
        f"{puzzle_id}/solution.png",
        f"{puzzle_id}/puzzle.png",
    ]
    for key in s3_keys:
        try:
            S3Client.delete_object(bucket=config.S3_BUCKET_NAME, object_key=key)
        except Exception as e:  # pylint: disable=broad-except
            logger.warning("Failed to delete S3 object %s: %s", key, e)

    redis_keys = [
        f"sudoku:{puzzle_id}:data",
        f"sudoku:{puzzle_id}:solution:csv",
        f"sudoku:{puzzle_id}:puzzle:csv",
        f"sudoku:{puzzle_id}:solution:image",
        f"sudoku:{puzzle_id}:puzzle-image",
    ]
    try:
        RedisClient.clear_keys(redis_keys)
    except Exception as e:  # pylint: disable=broad-except
        logger.warning("Failed to clear Redis keys %s: %s", redis_keys, e)
