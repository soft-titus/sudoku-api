"""
Sudoku test data ingester.

This module inserts or updates Sudoku puzzle data in MongoDB.
It is intentionally permissive and designed for testing purposes only.
"""

import argparse
import logging
import random
import sys
from datetime import datetime, timezone
from typing import List

from pymongo import MongoClient
from pymongo.errors import PyMongoError

import config
from ingester import config as ingester_config
from ingester import s3


def parse_csv_numbers(value: str) -> List[int]:
    """Parse a comma-separated string into a flat list of integers."""
    try:
        return [int(item.strip()) for item in value.split(",")]
    except Exception:  # pylint: disable=broad-except
        logging.warning("Failed to parse CSV numbers: %s", value)
        return []


def to_matrix(flat: List[int], puzzle_size: int) -> List[List[int]]:
    """
    Convert a flat list into a 2D matrix.

    If the flat list length is invalid, return an empty matrix.
    """
    expected = puzzle_size * puzzle_size
    if len(flat) != expected:
        logging.warning(
            "Invalid flat list length=%d expected=%d",
            len(flat),
            expected,
        )
        return []

    return [
        flat[row * puzzle_size : (row + 1) * puzzle_size] for row in range(puzzle_size)
    ]


def generate_random_solution(puzzle_size: int) -> List[List[int]]:
    """Generate a random 2D solution matrix (not guaranteed valid Sudoku)."""
    return [
        [random.randint(1, puzzle_size) for _ in range(puzzle_size)]
        for _ in range(puzzle_size)
    ]


def generate_random_puzzle(solution: List[List[int]]) -> List[List[int]]:
    """
    Generate a puzzle by removing ~50% of values from the solution.
    Removed values are replaced with zeroes.
    """
    puzzle = [row.copy() for row in solution]
    puzzle_size = len(puzzle)
    total_cells = puzzle_size * puzzle_size
    remove_count = total_cells // 2

    indices = random.sample(range(total_cells), remove_count)
    for idx in indices:
        row = idx // puzzle_size
        col = idx % puzzle_size
        puzzle[row][col] = 0

    return puzzle


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Sudoku test data ingester")
    parser.add_argument("--puzzle-id", required=True, help="Puzzle ID (required)")
    parser.add_argument(
        "--puzzle-size",
        type=int,
        default=9,
        help="Puzzle size (default: 9)",
    )
    parser.add_argument(
        "--level",
        default="EASY",
        help="Puzzle difficulty level (default: EASY)",
    )
    parser.add_argument(
        "--status",
        default="SUCCESS",
        help="Puzzle status (default: SUCCESS)",
    )
    parser.add_argument("--solution", help="Comma-separated sudoku solution")
    parser.add_argument("--puzzle", help="Comma-separated sudoku puzzle")
    parser.add_argument(
        "--failed-at",
        type=datetime.fromisoformat,
        default=None,
        help="Failure timestamp (ISO-8601",
    )
    parser.add_argument(
        "--failed-reason",
        default=None,
        help="Failure reason",
    )
    parser.add_argument(
        "--solution-image-path",
        default=None,
        help="Path to solution image",
    )
    parser.add_argument(
        "--puzzle-image-path",
        default=None,
        help="Path to puzzle image",
    )

    return parser.parse_args()


# pylint: disable=too-many-branches,too-many-statements
def main() -> None:
    """Entry point for the ingester."""
    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(message)s",
    )
    logging.getLogger("pymongo").setLevel(logging.WARNING)

    args = parse_arguments()

    # Solution handling
    if args.solution:
        flat_solution = parse_csv_numbers(args.solution)
        solution = to_matrix(flat_solution, args.puzzle_size)
    else:
        solution = generate_random_solution(args.puzzle_size)

    # Puzzle handling
    if args.puzzle:
        flat_puzzle = parse_csv_numbers(args.puzzle)
        puzzle = to_matrix(flat_puzzle, args.puzzle_size)
    else:
        puzzle = generate_random_puzzle(solution)

    try:
        client = MongoClient(config.MONGO_URI, serverSelectionTimeoutMS=10_000)
        collection = client[config.MONGO_DB][config.MONGO_COLLECTION_NAME]

        now = datetime.now(timezone.utc)

        solution_image_key = None
        puzzle_image_key = None

        if args.solution_image_path:
            try:
                solution_image_key = f"{args.puzzle_id}/solution.png"
                s3.upload_file_from_path(
                    args.solution_image_path,
                    solution_image_key,
                    ingester_config.S3_BUCKET_NAME,
                    content_type="image/png",
                )
            except FileNotFoundError:
                logging.warning(
                    "Solution image not found at path %s", args.solution_image_path
                )
                sys.exit(1)
            except Exception:  # pylint: disable=broad-except
                logging.exception("Failed to upload solution image")
                sys.exit(1)

        if args.puzzle_image_path:
            try:
                puzzle_image_key = f"{args.puzzle_id}/puzzle.png"
                s3.upload_file_from_path(
                    args.puzzle_image_path,
                    puzzle_image_key,
                    ingester_config.S3_BUCKET_NAME,
                    content_type="image/png",
                )
            except FileNotFoundError:
                logging.warning(
                    "Puzzle image not found at path %s", args.puzzle_image_path
                )
                sys.exit(1)
            except Exception:  # pylint: disable=broad-except
                logging.exception("Failed to upload puzzle image")
                sys.exit(1)

        filter_doc = {"puzzleId": args.puzzle_id}

        set_fields = {
            "puzzleSize": args.puzzle_size,
            "level": args.level,
            "status": args.status,
            "solution": solution,
            "puzzle": puzzle,
            "updatedAt": now,
        }

        if args.failed_at is not None:
            set_fields["failedAt"] = args.failed_at
        if args.failed_reason is not None:
            set_fields["failedReason"] = args.failed_reason
        if solution_image_key:
            set_fields["solutionImageKey"] = solution_image_key
        if puzzle_image_key:
            set_fields["puzzleImageKey"] = puzzle_image_key

        update_doc = {
            "$set": set_fields,
            "$setOnInsert": {"createdAt": now},
        }

        result = collection.update_one(filter_doc, update_doc, upsert=True)

        if result.matched_count > 0:
            logging.info("Updated puzzle with ID %s", args.puzzle_id)
        elif result.upserted_id is not None:
            logging.info("Inserted puzzle with ID %s", args.puzzle_id)
        else:
            logging.info("No changes made to puzzle with ID %s", args.puzzle_id)

    except PyMongoError as exc:
        logging.error("MongoDB error: %s", exc, exc_info=True)
        sys.exit(1)
    finally:
        try:
            client.close()
        except Exception:  # pylint: disable=broad-except
            pass


if __name__ == "__main__":
    main()
