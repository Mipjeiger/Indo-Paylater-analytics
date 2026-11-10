"""FastAPI application for PayLater Indodana."""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.middleware import setup_middleware
from app.api.routers import classify, health, metrics, score


app = FastAPI(title="PayLater Indodana ML API", version="1.0.0")

frontend_origins = [
    origin.strip()
    for origin in os.getenv(
        "FRONTEND_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173,"
        "http://localhost:4173,http://127.0.0.1:4173",
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=frontend_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

setup_middleware(app)
app.include_router(health.router, prefix="/health", tags=["health"])
app.include_router(score.router, prefix="/score", tags=["score"])
app.include_router(classify.router, prefix="/classify", tags=["classify"])
app.include_router(metrics.router, prefix="/metrics", tags=["metrics"])
