from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any

import mlflow
import numpy as np
import pandas as pd
import tensorflow as tf
from prefect import flow, task
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error, mean_absolute_percentage_error
from sklearn.preprocessing import StandardScaler

from app.training.flows.artifacts import MinioArtifactStore
from app.api.config import settings

"""Prefect TensorFlow multi-output training flow for DTI and distress."""

TARGETS = ["debt_to_income_ratio", "financial_distress_index"]
EXCLUDED = {
    *TARGETS,
    "total_loan_outstanding_idr",
    "confidence_score",
    "risk_score",
    "risk_short",
    "is_high_risk",
    "distress_bin",
    "twp90_default_status",
    "primary_default_root_cause",
    "cot_financial_psychology_rationale",
    "days_past_due",
    "borrower_id", "created_at", "updated_at",
}

def prepare_data(df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, StandardScaler, list[str]]:
    """Prepare features and targets for training and testing."""
    missing = [column for column in TARGETS if column not in df]
    if missing:
        raise ValueError(f"Required target columns are missing: {missing}")

    features = df.drop(columns=[column for column in EXCLUDED if column in df])
    features = features.select_dtypes(exclude=["object", "category", "datetime64", "datetime", "timedelta"]).fillna(0)
    
    # Scale and split the data into features and targets
    scaler = StandardScaler()
    x = scaler.fit_transform(features)
    y = df[TARGETS].to_numpy(dtype=np.float32)
    return x.astype(np.float32), y, scaler, list(features.columns)

def build_model(input_size: int) -> tf.keras.Model:
    """Build a multi-output regression model for DTI and distress."""
    inputs = tf.keras.Input(shape=(input_size,), name="features")
    hidden = tf.keras.layers.Dense(64, activation="relu")(inputs)
    hidden = tf.keras.layers.Dropout(0.2)(hidden)
    hidden = tf.keras.layers.Dense(32, activation="relu")(hidden)
    outputs = tf.keras.layers.Dense(2, name="outputs")(hidden)
    model = tf.keras.Model(inputs, outputs)
    model.compile(optimizer="adam", loss="mse")
    return model

@task(name="load_dti_data_from_postgres")
def load_data_from_postgres() -> pd.DataFrame:
    """Load data from postgres database."""
    pg_user = settings.POSTGRES_USER
    pg_password = settings.POSTGRES_PASSWORD
    pg_host = settings.POSTGRES_HOST
    pg_port = settings.POSTGRES_PORT
    pg_db = settings.POSTGRES_DB
    pg_schema = settings.POSTGRES_SCHEMA
    pg_table = settings.POSTGRES_TABLE

    # Create the connection string for PostgreSQL
    conn_str = f"postgresql://{pg_user}:{pg_password}@{pg_host}:{pg_port}/{pg_db}"
    query = f"SELECT * FROM {pg_schema}.{pg_table};"

    return pd.read_sql(query, conn_str)    

@task
def train_dti_distress(data_source: str | pd.DataFrame) -> dict[str, Any]:
    """Train the DTI and financial distress regression model using neural networks."""
    if isinstance(data_source, pd.DataFrame):
        df = data_source
    else:
        df = pd.read_parquet(data_source)

    ordered = df.sort_values("borrower_id")
    split = int(len(ordered) * 0.8)
    train, test = ordered.iloc[:split], ordered.iloc[split:]
    x_train, y_train, scaler, features = prepare_data(train)
    x_test, y_test, _, _ = prepare_data(test)

    # Build and train the neural network model
    model = build_model(x_train.shape[1])
    model.fit(
        x_train,
        y_train,
        validation_split=0.2,
        epochs=int(os.getenv("DTI_EPOCHS", "50")),
        batch_size=32,
        callbacks=[tf.keras.callbacks.EarlyStopping(patience=8, restore_best_weights=True)],
        verbose=0,
    )

    # Predict on the test set and evaluate metrics
    predicted = model.predict(x_test, verbose=0)
    metrics = {
        "mse": float(mean_squared_error(y_test, predicted)),
        "r2": float(r2_score(y_test, predicted)),
        "mae": float(mean_absolute_error(y_test, predicted)),
        "mape": float(mean_absolute_percentage_error(y_test, predicted)),
    }
   
    # Update metrics for each target variable 
    for i, target in enumerate(TARGETS):
        metrics[f"{target}_mse"] = float(mean_squared_error(y_test[:, i], predicted[:, i]))
        metrics[f"{target}_r2"] = float(r2_score(y_test[:, i], predicted[:, i]))
        metrics[f"{target}_mae"] = float(mean_absolute_error(y_test[:, i], predicted[:, i]))
        metrics[f"{target}_mape"] = float(mean_absolute_percentage_error(y_test[:, i], predicted[:, i]))

    # Store the model and set up experiment tracking with MLflow
    store = MinioArtifactStore._environment()
    mlflow.set_experiment("paylater/dti_distress")
    with mlflow.start_run(run_name="dti_distress") as run:
        with tempfile.TemporaryDirectory(prefix="dti-distress-") as directory:
            local_directory = Path(directory)
            local_model = local_directory / "dti_distress.keras"
            local_scaler = local_directory / "dti_distress_scaler.npz"
            model.save(local_model)
            np.savez(local_scaler, mean=scaler.mean_, scale=scaler.scale_)
            model_uri = store.upload_file(
                local_model,
                f"models/dti_distress/{run.info.run_id}/dti_distress.keras",
            )
            scaler_uri = store.upload_file(
                local_scaler,
                f"models/dti_distress/{run.info.run_id}/dti_distress_scaler.npz",
            )
            mlflow.log_metrics(metrics)
            mlflow.log_artifacts(str(local_directory))
            mlflow.log_params({
                "features": ",".join(features),
                "n_features": len(features),
                "seed": 42,
            })

            # Register the Keras model for pyfunc load model can be found
            model_info = mlflow.tensorflow.log_model(
                model=model,
                artifact_path="model",
                registered_model_name="paylater_dti_distress",
            )
            client = mlflow.tracking.MlflowClient()
            client.transition_model_version_stage(
                name="paylater_dti_distress",
                version=model_info.registered_model_version,
                stage="Staging",
            )

    return {
        "model_path": model_uri,
        "scaler_path": scaler_uri,
        "model_version": model_info.registered_model_version,
        "features": features,
        "metrics": metrics,
        "mlflow_run_id": run.info.run_id,
    }

@flow(name="task2_dti_distress")
def task2_flow() -> dict[str, Any]:
    """Prefect orchestration flow for Task 2."""
    df = load_data_from_postgres()
    return train_dti_distress(df)