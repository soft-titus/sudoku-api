"""
Main FastAPI application for the Sudoku API
"""

from fastapi import FastAPI

from app.helpers.logger import logger
from app.routes.health_routes import router as health_router


app = FastAPI(title="Sudoku Generation API")

app.include_router(health_router)
logger.info("Health router registered at /health")

logger.info("FastAPI Sudoku Generation API initialized")
