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
from sklearn.metrics import balanced_accuracy_score, cohen_kappa_score
from sklearn.preprocessing import LabelEncoder
from sklearn.ensemble import RandomForestClassifier
from sklearn.tree import DecisionTreeClassifier

from app.api.config import settings
from app.training.flows.artifacts import MinioArtifactStore

"""Prefect LightGBM root-cause classification training flow."""

TARGET = "primary_default_root_cause"
EXPECTED_LABELS = {
    "Income-Shock-Underemployment",
    "Gali-Lubang-Debt-Spiral",
    "Compulsive-FOMO-Spending",
    "High-Interest-Rate-Compounding",
    "Speculative-Losses",
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
    "primary_default_root_cause",
    "days_past_due",
    "borrower_id",
    "created_at",
    "updated_at",
}

def prepare_data(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series, LabelEncoder]:
    if TARGET not in df:
        raise ValueError(f"Required target column is missing: {TARGET}")

    clean_target = df[TARGET].dropna().astype(str).str.strip()
    labels = set(clean_target)
    missing = EXPECTED_LABELS - labels
    
    if missing:
        raise ValueError(f"Expected root-cause labels are unavailable: {sorted(missing)}")

    # Prepare features and categorical selection
    features = df.drop(columns=[column for column in LEAKAGE if column in df])
    features = features.drop(columns=["borrower_id", "created_at"], errors="ignore")
    datetime_cols = features.select_dtypes(include=["datetime64", "datetime", "timedelta"]).columns
    features = features.drop(columns=datetime_cols, errors="ignore")
    categorical = features.select_dtypes(include=["object", "category"]).columns

    # Handle missing values for categorical and numerical features    
    features[categorical] = features[categorical].fillna("__missing__").astype("category")
    numeric = features.columns.difference(categorical)
    features[numeric] = features[numeric].fillna(0)
    
    encoder = LabelEncoder()
    return features, pd.Series(encoder.fit_transform(clean_target)), encoder

@task(name="load_root_cause_data_from_postgres")
def load_data_from_postgres() -> pd.DataFrame:
    """Load data from postgres database."""
    conn_str = f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
    query = f"SELECT * FROM {settings.POSTGRES_SCHEMA}.{settings.POSTGRES_TABLE};"

    return pd.read_sql(query, conn_str)    

@task
def train_root_cause(data_source: str | pd.DataFrame) -> dict[str, Any]:
    """Train multiple root-cause classification models."""
    
    if isinstance(data_source, pd.DataFrame):
        df = data_source
    else:
        df = pd.read_parquet(data_source).sort_values("borrower_id")

    split = int(len(df) * 0.8)
    train, test = df.iloc[:split], df.iloc[split:]
    train_x, train_y, encoder = prepare_data(train)
    test_x, test_y, _ = prepare_data(test)

    # For scikit-learn models, encode categories to numeric codes
    train_x_sk = train_x.copy()
    test_x_sk = test_x.copy()
    for col in train_x_sk.select_dtypes(include=["category"]).columns:
        train_x_sk[col] = train_x_sk[col].cat.codes
        test_x_sk[col] = test_x_sk[col].cat.codes

    # Train classes must match the expected labels
    train_classes = set(train["primary_default_root_cause"].dropna().astype(str).str.strip())
    missing_in_train = EXPECTED_LABELS - train_classes
    if missing_in_train:
        raise ValueError(f"Expected root-cause labels are missing in training data: {sorted(missing_in_train)}")
    
    # Train a LightGBM classifier with balanced class weights and early stopping
    models = {
        "lightgbm": lgb.LGBMClassifier(
            objective="multiclass",
            num_class=len(EXPECTED_LABELS),
            class_weight="balanced",
            n_estimators=200,
            learning_rate=0.05,
            min_child_samples=10,
            random_state=42
        ),
        "random_forest": RandomForestClassifier(
            class_weight="balanced",
            n_estimators=200,
            random_state=42,
            min_samples_split=2,
            max_leaf_nodes=10,
        ),
        "decision_tree": DecisionTreeClassifier(
            class_weight="balanced",
            min_samples_split=2,
            max_depth=10,
            random_state=42,
        ),
    }

    # Store trained models, all metrics, and model uris
    trained_models = {}
    all_metrics = {}
    model_uris = {}

    store = MinioArtifactStore._environment()
    mlflow.set_experiment("paylater/root_cause")

    # Train and logs to MLFlow for each model
    with mlflow.start_run(run_name="root_cause_multi_model") as run:
        with tempfile.TemporaryDirectory(prefix="root-cause-") as directory:
            local_dir = Path(directory)

            for name, model in models.items():
                if name == "lightgbm":
                    model.fit(
                        train_x,
                        train_y,
                        categorical_feature=train_x.select_dtypes("category").columns.tolist(),
                    )
                    preds = model.predict(test_x)
                else:
                    model.fit(train_x_sk, train_y)
                    preds = model.predict(test_x_sk)

                trained_models[name] = model

                # Compute metrics for each model
                metrics = {
                    f"{name}_balanced_accuracy": float(balanced_accuracy_score(test_y, preds)),
                    f"{name}_qwk": float(cohen_kappa_score(test_y, preds, weights="quadratic"))
                }
                all_metrics.update(metrics)

                # Log scalar float/int metrics to MLflow
                scalar_metrics = {k: v for k, v in metrics.items() if isinstance(v, (int, float))}
                mlflow.log_metrics(scalar_metrics)

                # Save model artifacts
                if name == "lightgbm":
                    artifact_path = local_dir / f"{name}.txt"
                    model.booster_.save_model(str(artifact_path))
                else:
                    import joblib
                    artifact_path = local_dir / f"{name}.joblib"
                    joblib.dump(model, str(artifact_path))

                uri = store.upload_file(
                    artifact_path,
                    f"models/root_cause/{run.info.run_id}/{artifact_path.name}",
                )
                model_uris[name] = uri
                mlflow.log_artifact(str(artifact_path))

            explainer = shap.TreeExplainer(trained_models["lightgbm"])
            shap_values = explainer.shap_values(test_x.head(100))

            best_name = max(
                trained_models,
                key=lambda k: all_metrics.get(f"{k}_qwk", float("-inf"))
            )
            best_model = trained_models[best_name]

            # MLflow logs
            mlflow.log_param("best_model", best_name)
            mlflow.log_param("features", ",".join(train_x.columns))
            mlflow.log_param("n_features", len(train_x.columns))
            mlflow.log_param("class_labels", ",".join(encoder.classes_.tolist()))

            if best_name == "lightgbm":
                model_info = mlflow.lightgbm.log_model(
                    lgb_model=best_model,
                    artifact_path="model",
                    registered_model_name="paylater_root_cause",
                )
            else:
                model_info = mlflow.sklearn.log_model(
                    sk_model=best_model,
                    artifact_path="model",
                    registered_model_name="paylater_root_cause",
                )

            # Client for tracking mlflow model versions
            client = mlflow.tracking.MlflowClient()
            client.transition_model_version_stage(
                name="paylater_root_cause",
                version=model_info.model_version,
                stage="Staging",
            )
    
    return {
        "model_paths": model_uris,
        "bst_model": best_name,
        "model_version": model_info.registered_model_version,
        "labels": encoder.classes_.tolist(),
        "metrics": all_metrics,
        "shap_values": shap_values,
        "mlflow_run_id": run.info.run_id,
    }

@flow(name="task3_root_cause")
def task3_flow() -> dict[str, Any]:
    df = load_data_from_postgres()
    return train_root_cause(df)
