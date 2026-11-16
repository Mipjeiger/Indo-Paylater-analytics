from __future__ import annotations

import mlflow
import pandas as pd
import tempfile
from pathlib import Path
from typing import Any
from sqlalchemy import create_engine, text
from catboost import CatBoostClassifier
from prefect import flow, task
from sklearn.metrics import average_precision_score, precision_recall_curve, accuracy_score, r2_score, mean_squared_error, mean_absolute_error, mean_absolute_percentage_error
from app.training.flows.artifacts import MinioArtifactStore
from app.api.config import settings

"""Prefect training flow for TWP90 default classification."""

TARGET = "twp90_default_status"
TS_COL = "created_at" 
LEAKAGE = {
    TARGET,
    "risk_score", "risk_short", "is_high_risk", "distress_bin",
    "financial_distress_index", "debt_to_income_ratio",
    "primary_default_root_cause",
    "cot_financial_psychology_rationale", "confidence_score",
    "days_past_due",
    "borrower_id", "created_at", "updated_at",  
}
FORBIDDEN_FEATURES = LEAKAGE - {TARGET}

def fetch_database() -> pd.DataFrame:
    """Fetch the training dataset from the configured PostgreSQL database."""
    url = settings.POSTGRES_URL

    if not url:
        raise RuntimeError("POSTGRES_URL is required to connect to PostgreSQL")

    engine = create_engine(url)
    with engine.connect() as conn:
        query = text("SELECT * FROM paylater.database")
        return pd.read_sql(query, conn)

def temporal_split(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    if TS_COL not in df.columns:
        raise ValueError(f"Required timestamp column is missing: {TS_COL}")

    ordered = df.sort_values(by=TS_COL)
    first = int(len(ordered) * 0.7)
    second = int(len(ordered) * 0.85)
    return ordered.iloc[:first], ordered.iloc[first:second], ordered.iloc[second:]

def prepare_data(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series, list[str]]:
    if TARGET not in df:
        raise ValueError(f"Required target column is missing: {TARGET}")

    # Labeling the target variable as binary
    labels = (df[TARGET].astype(str) != "Current-Performing").astype(int)

    # Preparing features by dropping leakage columns and handling missing values
    features = df.drop(columns=[col for col in LEAKAGE if col in df])
    features = features.drop(columns=["borrower_id", TS_COL], errors="ignore")

    leaked = FORBIDDEN_FEATURES & set(features.columns)
    if leaked:
        raise ValueError(f"Forbidden features detected in the dataset: {sorted(leaked)}")

    # Handling categorical and numerical features about missing values
    categorical = features.select_dtypes(include=["object", "category"]).columns.tolist()
    features[categorical] = features[categorical].fillna("__missing__").astype(str)
    numeric = features.columns.difference(categorical)
    features[numeric] = features[numeric].fillna(0)

    return features, labels, categorical

def recall_at_precision(y_true: pd.Series, scores: Any, minimum_precision: float = 0.95) -> float:
    precision, recall, _ = precision_recall_curve(y_true, scores)
    valid = recall[precision >= minimum_precision]
    return float(valid.max()) if len(valid) else 0.0

@task
def train_twp90() -> dict[str, Any]:
    # Get the database
    df = fetch_database()

    # Train & validation splitting
    train_df, validation_df, test_df = temporal_split(df)
    train_x, train_y, categorical = prepare_data(train_df)
    validation_x, validation_y, _ = prepare_data(validation_df)

    # Test splitting
    test_x, test_y, _ = prepare_data(test_df)
    
    # Model chosen & training
    model = CatBoostClassifier(
        iterations=400,
        depth=7,
        learning_rate=0.05,
        loss_function="Logloss",
        eval_metric="PRAUC",
        auto_class_weights="Balanced",
        random_seed=42,
        verbose=False,
    )
    model.fit(
        train_x,
        train_y,
        cat_features=categorical,
        eval_set=(validation_x, validation_y),
        early_stopping_rounds=50,
    )

    # Evaluate score metrics on the test set
    scores = model.predict_proba(test_x)[:, 1]
    metrics = {
        "pr_auc": float(average_precision_score(test_y, scores)),
        "recall_at_95_precision": recall_at_precision(test_y, scores),
        "accuracy": float(accuracy_score(test_y, model.predict(test_x))),
        "temporal_performance_gap": float(
            average_precision_score(validation_y, model.predict_proba(validation_x)[:, 1]) - average_precision_score(test_y, scores)
        ),
        "r2": float(r2_score(test_y, scores)),
        "mse": float(mean_squared_error(test_y, scores)),
        "mae": float(mean_absolute_error(test_y, scores)),
        "mape": float(mean_absolute_percentage_error(test_y, scores)),
    }

    # Update metrics for each target variable
    for idx, target in enumerate([TARGET]):
        metrics[f"{target}_mse"] = float(mean_squared_error(test_y, scores))
        metrics[f"{target}_r2"] = float(r2_score(test_y, scores))
        metrics[f"{target}_mae"] = float(mean_absolute_error(test_y, scores))
        metrics[f"{target}_mape"] = float(mean_absolute_percentage_error(test_y, scores))

    # Store minio artifact and log metrics to MLflow
    store = MinioArtifactStore._environment()
    mlflow.set_experiment("paylater/twp90")
    with mlflow.start_run(run_name="twp90") as run:
        with tempfile.TemporaryDirectory(prefix="twp90-") as directory:
            local_artifact = Path(directory) / "twp90.cbm"
            model.save_model(str(local_artifact))
            artifact_uri = store.upload_file(
                local_artifact,
                f"models/twp90/{run.info.run_id}/twp90.cbm",
            )
            mlflow.log_params({"features": len(train_x.columns), "seed": 42})
            mlflow.log_metrics(metrics)
            mlflow.log_artifact(str(local_artifact))

            # Log the model as MLFlow pyfunc and register it
            model_info = mlflow.catboost.log_model(
                cb_model=model,
                artifact_path="model",
                registered_model_name="paylater_twp90",
            )

            # Promote the new version 'staging'
            client = mlflow.tracking.MlflowClient()
            client.transition_model_version_stage(
                name="paylater_twp90",
                version=model_info.registered_model_version,
                stage="Staging",
            )

    return {
        "model_path": artifact_uri,
        "model_version": model_info.registered_model_version,
        "features": list(train_x.columns),
        "metrics": metrics,
        "mlflow_run_id": run.info.run_id,
    }

@flow(name="task1_twp90")
def task1_flow() -> dict[str, Any]:
    return train_twp90()