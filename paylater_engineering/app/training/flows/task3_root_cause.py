from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any

import lightgbm as lgb
import mlflow
import pandas as pd
import shap
from prefect import flow, task
from sklearn.metrics import balanced_accuracy_score, cohen_kappa_score, confusion_matrix
from sklearn.preprocessing import LabelEncoder

from app.training.flows.artifacts import MinioArtifactStore

"""Prefect LightGBM root-cause classification training flow."""

TARGET = "primary_default_root_cause"
EXPECTED_LABELS = {
    "Income-Shock-Underemployment",
    "Gali-Lubang-Debt-Spiral",
    "Compulsive-FOMO-Spending",
    "Medical-Emergency-Shock",
    "Business-Failure",
}
LEAKAGE = {
    TARGET,
    "twp90_default_status",
    "confidence_score",
    "risk_score",
    "risk_short",
    "is_high_risk",
    "distress_bin",
    "cot_financial_psychology_rationale",
}

def prepare_data(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series, LabelEncoder]:
    if TARGET not in df:
        raise ValueError(f"Required target column is missing: {TARGET}")
    labels = set(df[TARGET].dropna().astype(str))
    missing = EXPECTED_LABELS - labels
    
    if missing:
        raise ValueError(f"Expected root-cause labels are unavailable: {sorted(missing)}")

    # Prepare features and categorical selection
    features = df.drop(columns=[column for column in LEAKAGE if column in df])
    features = features.drop(columns=["borrower_id", "created_at"], errors="ignore")
    categorical = features.select_dtypes(include=["object", "category"]).columns

    # Handle missing values for categorical and numerical features    
    features[categorical] = features[categorical].fillna("__missing__").astype("category")
    numeric = features.columns.difference(categorical)
    features[numeric] = features[numeric].fillna(0)
    
    encoder = LabelEncoder()
    return features, pd.Series(encoder.fit_transform(df[TARGET].astype(str))), encoder

@task
def train_root_cause(
    data_path: str = "database/dataset/indonesia_fintech_paylater.parquet",
) -> dict[str, Any]:
    df = pd.read_parquet(data_path).sort_values("borrower_id")
    split = int(len(df) * 0.8)
    train, test = df.iloc[:split], df.iloc[split:]
    train_x, train_y, encoder = prepare_data(train)
    test_x, test_y, _ = prepare_data(test)
    model = lgb.LGBMClassifier(
        objective="multiclass",
        num_class=len(encoder.classes_),
        class_weight="balanced",
        n_estimators=300,
        random_state=42,
    )
    model.fit(
        train_x,
        train_y,
        categorical_feature=train_x.select_dtypes("category").columns.tolist(),
    )
    predicted = model.predict(test_x)
    metrics = {
        "balanced_accuracy": float(balanced_accuracy_score(test_y, predicted)),
        "qwk": float(cohen_kappa_score(test_y, predicted, weights="quadratic")),
        "confusion_matrix": confusion_matrix(test_y, predicted).tolist(),
    }
    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(test_x.head(100))

    store = MinioArtifactStore._environment()
    mlflow.set_experiment("paylater/root_cause")
    with mlflow.start_run(run_name="root_cause") as run:
        with tempfile.TemporaryDirectory(prefix="root-cause-") as directory:
            local_artifact = Path(directory) / "root_cause.txt"
            model.booster_.save_model(str(local_artifact))
            artifact_uri = store.upload_file(
                local_artifact,
                f"models/root_cause/{run.info.run_id}/root_cause.txt",
            )
            mlflow.log_metrics(
                {key: value for key, value in metrics.items() if isinstance(value, float)}
            )
            mlflow.log_artifact(str(local_artifact))

    return {
        "model_path": artifact_uri,
        "labels": encoder.classes_.tolist(),
        "metrics": metrics,
        "shap_values": shap_values,
        "mlflow_run_id": run.info.run_id,
    }

@flow(name="task3_root_cause")
def task3_flow(
    data_path: str = "database/dataset/indonesia_fintech_paylater.parquet",
) -> dict[str, Any]:
    return train_root_cause(data_path)
