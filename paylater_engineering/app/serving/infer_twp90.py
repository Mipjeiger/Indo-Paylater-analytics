"""Cached TWP90 model loading and validated inference."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

import mlflow
import numpy as np
import pandas as pd
from mlflow.tracking import MlflowClient
from app.monitoring.metrics import MODEL_PREDICTIONS, MODEL_FAILURES

REGISTERED_MODEL_NAME = "paylater_twp90" 

REQUIRED_FEATURES = (
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
)

CATEGORICAL_FEATURES = (
    "gender",
    "province",
    "education_level",
    "employment_status",
    "primary_loan_purpose",
)

# Define a global MlflowClient
_client = MlflowClient()

def _resolve_version(version: str | None = None) -> str:
    """Pick Production first, then Staging, then newest."""
    if version is not None:
        return version
    
    all_versions = _client.search_model_versions(f"name='{REGISTERED_MODEL_NAME}'")
    if not all_versions:
        raise LookupError(f"No registered versions for {REGISTERED_MODEL_NAME}")

    # Find the highest models version in systems
    production = [v for v in all_versions if v.current_stage == "Production"]
    staging = [v for v in all_versions if v.current_stage == "Staging"]
    candidates = production or staging or all_versions
    return max(candidates, key=lambda v: int(v.version)).version

@lru_cache(maxsize=32)
def load_model(version: str | None = None) -> Any:
    v = _resolve_version(version)
    try:
        return mlflow.pyfunc.load_model(f"models:/{REGISTERED_MODEL_NAME}/{v}")

    except Exception as exc:
        raise RuntimeError(
            f"Unable to load model {REGISTERED_MODEL_NAME}:{v} "
            f"({type(exc).__name__}: {exc})"
        ) from exc


def _raw_catboost(model: Any):
    """Return the underlying CatBoost classifier behind the pyfunc wrapper.

    The mlflow.catboost wrapper only exposes ``predict`` (the hard class
    label), so to obtain the default *probability* we need the raw estimator.
    """
    impl = getattr(model, "_model_impl", None)
    if impl is not None and hasattr(impl, "cb_model"):
        return impl.cb_model
    raw = getattr(model, "get_raw_model", lambda: None)()
    if raw is not None and hasattr(raw, "predict_proba"):
        return raw
    return None


def _features(values: dict[str, Any]) -> pd.DataFrame:
    missing = [name for name in REQUIRED_FEATURES if name not in values]
    if missing:
        raise ValueError(f"Missing required TWP90 features: {missing}")

    row = {name: values[name] for name in REQUIRED_FEATURES}
    for col in CATEGORICAL_FEATURES:
        if not isinstance(row[col], str):
            row[col] = str(row[col])

    frame = pd.DataFrame([row], columns=list(REQUIRED_FEATURES))
    # CatBoost needs the categorical columns as real pandas category dtype,
    # otherwise it silently returns the majority class (always 0).
    for col in CATEGORICAL_FEATURES:
        frame[col] = frame[col].astype("category")
    return frame


def predict_twp90(
    borrower_features: dict[str, Any], version: str | None = None
) -> dict[str, Any]:
    """Predict TWP90 default probability for a borrower."""
    v = _resolve_version(version)
    model = load_model(v)
    frame = _features(borrower_features)

    cb = _raw_catboost(model)
    try:
        if cb is not None and hasattr(cb, "predict_proba"):
            proba = cb.predict_proba(frame)
            values = np.asarray(proba).reshape(-1)
            # CatBoost orders columns by class index; P(default) is the last.
            value = float(values[-1]) if values.size > 1 else float(values[0])
        else:
            prediction = model.predict(frame)
            raw = prediction[0]
            if hasattr(raw, "__len__") and not isinstance(raw, (str, bytes)):
                value = float(raw[1]) if len(raw) > 1 else float(raw[0])
            else:
                value = float(raw)
    except Exception:
        MODEL_FAILURES.labels(task="twp90").inc()
        raise

    if not 0 <= value <= 1:
        MODEL_FAILURES.labels(task="twp90").inc()
        raise ValueError(f"TWP90 model returned a probability outside [0, 1]: {value}")

    MODEL_PREDICTIONS.labels(task="twp90").inc()

    return {"default_probability": value, "model_version": v}