"""Pydantic models for Sudoku puzzle requests and responses."""

from enum import Enum
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, constr


class PuzzleSize(int, Enum):
    """Allowed sizes for Sudoku puzzles."""

    SIZE_4 = 4
    SIZE_9 = 9
    SIZE_16 = 16


class PuzzleLevel(str, Enum):
    """Difficulty levels for Sudoku puzzles."""

    EASY = "EASY"
    MEDIUM = "MEDIUM"
    HARD = "HARD"


class PuzzleStatus(str, Enum):
    """Statuses for Sudoku puzzle generation."""

    GENERATING_PUZZLE = "GENERATING_PUZZLE"
    GENERATING_IMAGE = "GENERATING_IMAGE"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class PuzzleCreationRequest(BaseModel):
    """
    Model for Sudoku puzzle creation request.

    Attributes:
        puzzleId: Unique identifier for the puzzle (required).
        puzzleSize: Size of the puzzle (optional, default 9).
        level: Difficulty level (optional, default MEDIUM).
    """

    puzzleId: constr(min_length=1)
    puzzleSize: PuzzleSize = PuzzleSize.SIZE_9
    level: PuzzleLevel = PuzzleLevel.MEDIUM


class PuzzleUpdateRequest(BaseModel):
    """
    Model for Sudoku puzzle update request.

    Attributes:
        puzzleSize: Size of the puzzle (optional, default None).
        level: Difficulty level (optional, default None).
    """

    puzzleSize: Optional[PuzzleSize] = None
    level: Optional[PuzzleLevel] = None


class PuzzleResponse(BaseModel):
    """
    Model representing a Sudoku puzzle document stored in MongoDB.

    Attributes:
        puzzleId: Unique identifier of the puzzle.
        puzzleSize: Size of the puzzle.
        level: Difficulty level.
        status: Current status of the puzzle generation.
        failedAt: UTC timestamp when the puzzle generation failed (optional).
        failedReason: Reason for failure (optional).
        createdAt: UTC timestamp when the puzzle generation request was created.
        updatedAt: UTC timestamp when the puzzle generation request was updated.
    """

    puzzleId: str
    puzzleSize: PuzzleSize
    level: PuzzleLevel
    status: PuzzleStatus
    failedAt: Optional[datetime] = None
    failedReason: Optional[str] = None
    createdAt: datetime
    updatedAt: datetime
