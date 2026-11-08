"""HTTP metrics middleware."""

import time

from fastapi import FastAPI, Request

from app.monitoring.metrics import HTTP_LATENCY, HTTP_REQUESTS


def setup_middleware(app: FastAPI) -> None:
    @app.middleware("http")
    async def metrics_middleware(request: Request, call_next):
        started = time.perf_counter()
        response = await call_next(request)
        path = request.url.path
        HTTP_REQUESTS.labels(request.method, path, response.status_code).inc()
        HTTP_LATENCY.labels(path).observe(time.perf_counter() - started)
        return response
