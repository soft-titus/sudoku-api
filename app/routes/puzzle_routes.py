"""Puzzle routes for Sudoku API."""

from datetime import datetime, timezone
import json

from fastapi import APIRouter, HTTPException
from pymongo.errors import DuplicateKeyError

from app.helpers.logger import logger
from app.models.puzzle import (
    PuzzleRequest,
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
def create_puzzle(request: PuzzleRequest):
    """
    Insert puzzle data into MongoDB with status `GENERATING_PUZZLE`
    and enqueue a Kafka message.

    Args:
        request (PuzzleRequest): Puzzle creation request payload.

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
