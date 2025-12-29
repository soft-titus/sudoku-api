"""
Centralized application logger setup.
This module exposes a configured logger used across the application.
"""

import logging

from config import LOG_LEVEL

logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

logger = logging.getLogger("sudoku-api")
