"""
Metrics sidecar for Prometheus.

Exposes /metrics endpoint using multiprocess mode.
"""

from fastapi import FastAPI
from prometheus_client import CollectorRegistry, multiprocess, make_asgi_app

metrics_app = FastAPI(title="Metrics")

registry = CollectorRegistry()
multiprocess.MultiProcessCollector(registry)

metrics_app.mount("/metrics", make_asgi_app(registry=registry))
