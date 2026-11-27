from __future__ import annotations

from functools import lru_cache
from typing import Any
import mlflow
import json
import pandas as pd
import numpy as np
from mlflow.tracking import MlflowClient
from app.monitoring.metrics import MODEL_PREDICTIONS, MODEL_FAILURES

"""Cached root-cause model loading and validated inference."""

REGISTERED_MODEL_NAME = "paylater_root_cause"
REQUIRED_FEATURES_FALLBACK = (
    "age",
    "gender",
    "province",
    "education_level",
    "employment_status",
    "monthly_income_idr",
    "regional_minimum_wage_umr_idr",
    "num_active_lending_apps",
    "total_loan_outstanding_idr",
    "credit_limit_granted_idr",
    "loan_tenor_months",
    "daily_interest_rate_pct",
    "primary_loan_purpose",
    "income_to_umr_ratio",
    "credit_limit_utilization_ratio",
    "monthly_installment_estimate_idr",
    "debt_service_ratio",
    "disposable_income_after_debt_idr",
    "debt_to_income_ratio",
    "financial_distress_index",
)
CATEGORICAL_FEATURES = (
    "gender",
    "province",
    "education_level",
    "employment_status",
    "primary_loan_purpose",
)

# Mlflow client
_client = MlflowClient()

# --- Version resolution -------------------------------
def _resolve_version(version: str | None = None) -> str:
    if version is not None:
        return version

    all_versions = _client.search_model_versions(f"name='{REGISTERED_MODEL_NAME}'")
    if not all_versions:
        raise LookupError(f"No registered versions for {REGISTERED_MODEL_NAME}")

    production = [v for v in all_versions if v.current_stage == "Production"]
    staging = [v for v in all_versions if v.current_stage == "Staging"]
    candidates = production or staging or all_versions
    return max(candidates, key=lambda v: int(v.version)).version

# --- Cached loaders -------------------------------
@lru_cache(maxsize=32)
def load_model(version: str | None = None) -> Any:
    v = _resolve_version(version)
    try:
        return mlflow.pyfunc.load_model(f"models:/{REGISTERED_MODEL_NAME}/{v}")
    except Exception as e:
        raise RuntimeError(
            f"Unable to load model {REGISTERED_MODEL_NAME}:{v} "
            f"({type(e).__name__}: {e})"
        ) from e

# --- feature registry -------------------------------
def _features_from_registry(version: str | None = None) -> tuple[str, ...]:
    v = _resolve_version(version)
    mv = _client.get_model_version(REGISTERED_MODEL_NAME, v)
    run = _client.get_run(mv.run_id)
    raw = run.data.params.get("features")

    if not raw or raw.isdigit():
        return REQUIRED_FEATURES_FALLBACK
    return tuple(raw.split(","))

# --- Public entry point -------------------------------
@lru_cache(maxsize=32)
def _class_labels(version: str | None = None) -> tuple[str, ...]:
    v = _resolve_version(version)
    mv = _client.get_model_version(REGISTERED_MODEL_NAME, v)
    run = _client.get_run(mv.run_id)
    raw = run.data.params.get("class_labels")

    if not raw:
        raise RuntimeError(
            f"Model {REGISTERED_MODEL_NAME} v{v} did not log class_labels. "
            f"Add mlflow.log_param('class_labels', ','.join(encoder.classes_)) "
            f"to the training flow and retrain."
        )
    return tuple(raw.split(","))

@lru_cache(maxsize=32)
def _cat_categories(version: str | None = None) -> dict[str, list[str]]:
    """Retrieve the categorical feature categories features addition to the model registry."""
    v = _resolve_version(version)
    mv = _client.get_model_version(REGISTERED_MODEL_NAME, v)
    run = _client.get_run(mv.run_id)
    raw = run.data.params.get("cat_categories")

    if not raw:
        return {} # Fallback to empty dict if not logged
    return json.loads(raw)

def _build_frame(values: dict[str, Any], expected: tuple[str, ...], version: str) -> pd.DataFrame:
    """Build a single-row DataFrame from the provided feature values, ensuring all expected features are present."""
    missing = [name for name in expected if name not in values]
    if missing:
        raise ValueError(f"Missing required features: {missing}")

    # Convert categorical features to strings
    row = {name: values[name] for name in expected}
    return pd.DataFrame([row], columns=list(expected))

def predict_root_cause(
    features: dict[str, Any], version: str | None = None
) -> dict[str, Any]:
    v = _resolve_version(version)
    expected = _features_from_registry(v)
    model = load_model(v)

    frame = _build_frame(features, expected, v)

    try:
        prediction = model.predict(frame)                
    except Exception:
        MODEL_FAILURES.labels(task="root_cause").inc()  # ← FAILURE actions notified
        raise

    values = np.asarray(prediction)
    if values.ndim == 2 and values.shape[0] == 1:
        values = values[0]

    classes = _class_labels(v)
    if len(classes) != len(values):
        MODEL_FAILURES.labels(task="root_cause").inc() 
        raise ValueError(
            f"class_labels length ({len(classes)}) != model output length ({len(values)})"
        )

    idx = int(np.argmax(values))
    MODEL_PREDICTIONS.labels(task="root_cause").inc() # ← SUCCESS actions notified

    return {
        "root_cause": classes[idx],
        "confidence": float(values[idx]),
        "model_version": v,
    }