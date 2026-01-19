"""
Prometheus custom metrics.
"""

from prometheus_client import Counter

sudoku_api_requests_total = Counter(
    "sudoku_api_requests_total",
    "Total number of /puzzle requests",
    ["method", "endpoint"],
)
