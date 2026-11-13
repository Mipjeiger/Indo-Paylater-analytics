import mlflow
import numpy as np
import pandas as pd
from mlflow.tracking import MlflowClient

from functools import lru_cache
from typing import Any

"""Cached DTI and financial distress inference."""

REGISTERED_MODEL_NAME = "paylater_dti_distress"
FEATURES = (
    "age",
    "monthly_income_idr",
    "regional_minimum_wage_umr_idr",
    "num_active_lending_apps",
)

_client = MlflowClient()

@lru_cache(maxsize=8)
def load_model(version: str | None = None) -> Any:
    if version is None:

        all_versions = _client.search_model_versions(f"name='{REGISTERED_MODEL_NAME}'")

        # Production first, then Staging.
        production = [v for v in all_versions if v.current_stage == "Production"]
        staging = [v for v in all_versions if v.current_stage == "Staging"]

        candidates = production or staging
        if not candidates:
            raise LookupError(f"No deployed model version found for {REGISTERED_MODEL_NAME}")

        # Pick the highest version number among candidates.
        version = max(candidates, key=lambda v: int(v.version)).version

    uri = f"models:/{REGISTERED_MODEL_NAME}/{version}"
    return mlflow.pyfunc.load_model(uri)

def predict_dti_distress(features: dict[str, Any], version: str | None = None) -> dict[str, float | str | None]:
    missing = [name for name in FEATURES if name not in features]
    
    if missing:
        raise ValueError(f"Missing required DTI features: {missing}")
    
    frame = pd.DataFrame([{k: features[k] for k in FEATURES}], columns=list(FEATURES))

    model = load_model(version)
    values = np.asarray(model.predict(frame)).reshape(-1, 2)

    if values.shape != (1, 2):
        raise ValueError(f"DTI model returned unexpected shape: {np.asarray(values).shape}")

    loaded_version = version
    if loaded_version is None:
        candidates = (
            _client.search_model_versions(f"name='{REGISTERED_MODEL_NAME}' and current_stage='Production'")
            or _client.search_model_versions(f"name='{REGISTERED_MODEL_NAME}' and current_stage='Staging'")
        )
        loaded_version = candidates[0].version if candidates else None

    return {
        "dti": float(values[0, 0]),
        "financial_distress_index": float(values[0, 1]),
        "model_version": loaded_version,
    }