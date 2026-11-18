from __future__ import annotations

from functools import lru_cache
from typing import Any
import mlflow
import pandas as pd
import numpy as np
from mlflow.tracking import MlflowClient

"""Cached root-cause model loading and validated inference."""

REGISTERED_MODEL_NAME = "paylater_root_cause"
REQUIRED_FEATURES = (
    "age",
    "monthly_income_idr",
    "regional_minimum_wage_umr_idr",
    "num_active_lending_apps",
)

CATEGORICAL_FEATURES = ()

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

# --- feature frame -------------------------------
def _features(values: dict[str, Any]) -> pd.DataFrame:
    """Validate and return a feature frame for inference."""
    missing = [name for name in REQUIRED_FEATURES if name not in values]

    if missing:
        raise ValueError(f"Missing required features: {missing}")

    row = {name: values[name] for name in REQUIRED_FEATURES}
    for col in CATEGORICAL_FEATURES:
        if not isinstance(row[col], str):
            row[col] = str(row[col])

    return pd.DataFrame([row], columns=list(REQUIRED_FEATURES))

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

def predict_root_cause(features: dict[str, Any], version: str | None = None) -> dict[str, Any]:
    v = _resolve_version(version)
    model = load_model(v)
    prediction = model.predict(_features(features))

    # Model multiclass pyfunc typically return shape (1, n_classes)
    values = np.asarray(prediction)
    if values.ndim == 2 and values.shape[0] == 1:
        values = values[0]

    classes = _class_labels(v)
    if len(classes) != len(values):
        raise ValueError(
            f"class_labels length {len(classes)} does not match model output length {len(values)}"
        )
    
    idx = int(np.argmax(values))
    confidence = float(values[idx])
    return {
        "root_cause": classes[idx],
        "confidence": confidence,
        "model_version": v,
    }