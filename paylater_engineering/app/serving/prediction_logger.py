from __future__ import annotations

import time
from typing import Any
from sqlalchemy import text
from app.registry.db import Database

"""Persist inference results to paylater.predictions.

Every successful model call is mirrored here so the aggregate router and the
frontend can read prediction history back out of PostgreSQL. Failures are
never logged (they go to the Prometheus failure counters instead).
"""

def log_prediction(
    database: Database,
    *,
    borrower_id: str,
    task_name: str,
    prediction: dict[str, Any],
    prediction_score: float | None = None,
    features: dict[str, Any] | None = None,
    model_version: str | None = None,
    inference_latency_ms: float | None = None,
) -> int:
    """Insert one row into paylater.predictions and return its id."""
    if not borrower_id:
        raise ValueError("borrower_id is required")
    if not task_name:
        raise ValueError("task_name is required")
    if prediction is None:
        raise ValueError("prediction payload is required")

    statement = text(
        """
        INSERT INTO paylater.predictions
            (borrower_id, task_name, model_version, prediction,
             prediction_score, features, inference_latency_ms)
        VALUES
            (:borrower_id, :task_name, :model_version,`
             CAST(:prediction AS JSONB), :prediction_score,
             CAST(:features AS JSONB), :inference_latency_ms)
        RETURNING id
        """
    )
    import json

    with database.engine.begin() as connection:
        identifier = connection.execute(
            statement,
            {
                "borrower_id": borrower_id,
                "task_name": task_name,
                "model_version": model_version,
                "prediction": json.dumps(prediction),
                "prediction_score": prediction_score,
                "features": json.dumps(features) if features is not None else None,
                "inference_latency_ms": inference_latency_ms,
            },
        ).scalar_one()
    return int(identifier)

class PredictionLogger:
    """Context-manager-free helper that times a block and logs on success."""

    def __init__(self, database: Database) -> None:
        self._database = database
        self._started: float | None = None

    def start(self) -> None:
        self._started = time.perf_counter()

    def record(
        self,
        *,
        borrower_id: str,
        task_name: str,
        prediction: dict[str, Any],
        prediction_score: float | None = None,
        features: dict[str, Any] | None = None,
        model_version: str | None = None,
    ) -> int:
        if self._started is None:
            self.start()
        latency_ms = (time.perf_counter() - (self._started or time.perf_counter())) * 1000.0
        return log_prediction(
            self._database,
            borrower_id=borrower_id,
            task_name=task_name,
            prediction=prediction,
            prediction_score=prediction_score,
            features=features,
            model_version=model_version,
            inference_latency_ms=round(latency_ms, 2),
        )