"""Cached TWP90 model loading and validated inference."""

from functools import lru_cache
from typing import Any

import mlflow
import pandas as pd
from mlflow.tracking import MlflowClient

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

@lru_cache(maxsize=32)
def load_model(task_name: str, version: str | None = None) -> Any:
    try:
        if version is not None:
            uri = f"models:/{task_name}/{version}"
        else:
            found = (
                _client.search_model_versions(f"name='{task_name}' and current_stage='Production'")
                or _client.search_model_versions(f"name='{task_name}' and current_stage='Staging'")
            )

            if not found:
                raise LookupError(f"No deployed model version found for {task_name}")

            uri = f"models:/{task_name}/{found[0].version}"

        return mlflow.pyfunc.load_model(uri)

    except Exception as exc:
        raise RuntimeError(f"Unable to load model {task_name}:{version}") from exc

def _features(values: dict[str, Any]) -> pd.DataFrame:
    missing = [name for name in REQUIRED_FEATURES if name not in values]
    if missing:
        raise ValueError(f"Missing required TWP90 features: {missing}")

    row = {name: values[name] for name in REQUIRED_FEATURES}

    for col in CATEGORICAL_FEATURES:
        row[col] = str(row[col])

    return pd.DataFrame([row], columns=list(REQUIRED_FEATURES))

def predict_twp90(borrower_features: dict[str, Any], version: str | None = None) -> dict[str, Any]:
    """Predict TWP90 default probability for a borrower."""
    model = load_model(REGISTERED_MODEL_NAME, version)
    prediction = model.predict(_features(borrower_features))
    value = float(prediction[0][0] if getattr(prediction, "ndim", 1) > 1 else prediction[0])
    
    if not 0 <= value <= 1:
        raise ValueError("TWP90 model returned a probability outside [0, 1]")

    # Return the version actually loaded
    if version is None:
        found = _client.search_model_versions(
            f"name='{REGISTERED_MODEL_NAME}' and current_stage='Production'"
        ) or _client.search_model_versions(
            f"name='{REGISTERED_MODEL_NAME}' and current_stage='Staging'"
        )
        actual_version = found[0].version if found else None

    return {"default_probability": value, "model_version": actual_version}