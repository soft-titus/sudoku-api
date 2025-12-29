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
from app.services.kafka import KafkaClient
from app.services.mongodb import MongoDBClient
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
    and enqueue a Kafka message to regenerate the puzzle and solution.

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

        # Prepare fields for reset and re-generation
        now = datetime.now(timezone.utc)
        update_fields = {
            "updatedAt": now,
            "status": PuzzleStatus.GENERATING_PUZZLE.value,
            "solution": None,
            "puzzle": None,
            "solutionImageKey": None,
            "puzzleImageKey": None,
            "failedAt": None,
            "failedReason": None,
        }
        if request.puzzleSize is not None:
            update_fields["puzzleSize"] = request.puzzleSize
        if request.level is not None:
            update_fields["level"] = request.level

        collection.update_one({"puzzleId": request.puzzleId}, {"$set": update_fields})
        logger.info("Puzzle reset for re-generation: %s", request.puzzleId)

        # Produce Kafka message for re-generation
        kafka_payload = json.dumps({"puzzleId": request.puzzleId})
        KafkaClient.produce_message(
            topic=config.KAFKA_PUZZLE_TOPIC,
            key=request.puzzleId,
            value=kafka_payload,
        )
        logger.info(
            "Kafka message published to %s for puzzle %s: %s",
            config.KAFKA_PUZZLE_TOPIC,
            request.puzzleId,
            kafka_payload,
        )

        # Return updated document
        updated = collection.find_one({"puzzleId": request.puzzleId})
        return updated

    except HTTPException:
        raise
    except Exception as e:  # pylint: disable=broad-except
        logger.exception("Failed to update puzzle %s", request.puzzleId)
        raise HTTPException(status_code=500, detail="Failed to update puzzle") from e
