import time
from fastapi import FastAPI, Request
from app.monitoring.metrics import HTTP_LATENCY, HTTP_REQUESTS

"""HTTP metrics middleware."""

def setup_middleware(app: FastAPI) -> None:
    @app.middleware("http")
    async def metrics_middleware(request: Request, call_next):
        started = time.perf_counter()
        status = "500"
        try:
            response = await call_next(request)
            status = str(response.status_code)
            return response

        finally:
            # Use the route template when available
            route = request.scope.get("route")
            path = getattr(route, "path", request.url.path)
            elapsed = time.perf_counter() - started
            HTTP_REQUESTS.labels(request.method, path, status).inc()
            HTTP_LATENCY.labels(path).observe(elapsed)