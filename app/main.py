"""
Main FastAPI application for the Sudoku API
"""

from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

from app.helpers.logger import logger
from app.routes.health_routes import router as health_router
from app.routes.puzzle_routes import router as puzzle_router


app = FastAPI(title="Sudoku Generation API")

Instrumentator(
    excluded_handlers=["/health"],
    should_group_status_codes=False,
    should_ignore_untemplated=True,
).instrument(app)

app.include_router(health_router)
logger.info("Health router registered at /health")

app.include_router(puzzle_router)
logger.info("Puzzle router registered at /puzzle")

logger.info("FastAPI Sudoku Generation API initialized")
