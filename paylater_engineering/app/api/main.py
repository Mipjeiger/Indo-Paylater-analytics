"""FastAPI application for PayLater Indodana."""

from fastapi import FastAPI

from app.api.middleware import setup_middleware
from app.api.routers import classify, health, metrics, score


app = FastAPI(title="PayLater Indodana ML API", version="1.0.0")
setup_middleware(app)
app.include_router(health.router, prefix="/health", tags=["health"])
app.include_router(score.router, prefix="/score", tags=["score"])
app.include_router(classify.router, prefix="/classify", tags=["classify"])
app.include_router(metrics.router, prefix="/metrics", tags=["metrics"])
