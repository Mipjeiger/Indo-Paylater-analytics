from typing import Any
import pandas as pd
from app.serving.infer_twp90 import load_model

"""Cached root-cause inference."""

FEATURES = (
    "age",
    "monthly_income_idr",
    "regional_minimum_wage_umr_idr",
    "num_active_lending_apps",
)

def predict_root_cause(features: dict[str, Any], version: str | None = None) -> dict[str, str | None]:
    missing = [name for name in FEATURES if name not in features]

    if missing:
        raise ValueError(f"Missing required root-cause features: {missing}")
    values = load_model("root_cause", version).predict(
        pd.DataFrame([{key: features[key] for key in FEATURES}])
    )

    if len(values) != 1:
        raise ValueError("Root-cause model returned an invalid output shape")
    return {"root_cause": str(values[0]), "model_version": version}
