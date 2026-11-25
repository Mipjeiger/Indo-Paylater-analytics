from functools import lru_cache
from typing import Any

import io
import mlflow
import numpy as np
import pandas as pd
from mlflow.tracking import MlflowClient
from minio import Minio
from sklearn.preprocessing import StandardScaler
from app.api.config import settings
from app.monitoring.metrics import MODEL_PREDICTIONS, MODEL_FAILURES

"""Cached DTI and financial distress inference."""

REGISTERED_MODEL_NAME = "paylater_dti_distress"

_client = MlflowClient()

# ─── helpers ────────────────────────────────────────────────────────────

def _resolve_version(version: str | None) -> str:
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

def _minio() -> Minio:
    return Minio(
        settings.MINIO_ENDPOINT,
        access_key=settings.MINIO_ACCESS_KEY,
        secret_key=settings.MINIO_SECRET_KEY,
        secure=False,
    )

def _fetch_uri(uri: str) -> bytes:
    """Fetch url from MinIO s3 bucket"""
    assert uri.startswith("s3://"), f"Unsupported URI: {uri}"
    bucket_key = uri[len("s3://"):]
    bucket, _, key = bucket_key.partition("/")
    resp = _minio().get_object(bucket, key)
    try:
        return resp.read()
    finally:
        resp.close()
        resp.release_conn()

# ─── cached loaders ─────────────────────────────────────────────────────

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


def _raw_keras(model: Any):
    """Return the underlying Keras model behind the mlflow.tensorflow wrapper."""
    impl = getattr(model, "_model_impl", None)
    if impl is not None and hasattr(impl, "keras_model"):
        return impl.keras_model
    if impl is not None and hasattr(impl, "model"):
        return impl.model
    if impl is not None and hasattr(impl, "predict"):
        return impl
    raw = getattr(model, "get_raw_model", lambda: None)()
    if raw is not None and hasattr(raw, "predict"):
        return raw
    if hasattr(model, "unwrap_python_model"):
        try:
            unwrapped = model.unwrap_python_model()
            if hasattr(unwrapped, "keras_model"):
                return unwrapped.keras_model
            if hasattr(unwrapped, "predict"):
                return unwrapped
        except Exception:
            pass
    return None


@lru_cache(maxsize=8)
def load_features(version: str | None = None) -> tuple[str, ...]:
    """The feature list captured at training time (log_params).
    Falls back to the run's params; raises clearly if missing."""
    v = _resolve_version(version)
    mv = _client.get_model_version(REGISTERED_MODEL_NAME, v)
    run = _client.get_run(mv.run_id)
    raw = run.data.params.get("features")
    if not raw:
        raise RuntimeError(
            f"Model {REGISTERED_MODEL_NAME} v{v} did not log its feature list. "
            f"Add mlflow.log_params({{'features': ','.join(features)}}) to the training flow "
            f"and retrain before serving."
        )
    return tuple(raw.split(","))


def _build_frame(
    features: dict[str, Any], expected: tuple[str, ...], version: str
) -> pd.DataFrame:
    """Build a single-row DataFrame from the provided feature values, scaled
    with the training-time StandardScaler."""
    missing = [name for name in expected if name not in features]
    if missing:
        raise ValueError(
            f"Missing required DTI features (expected {len(expected)}): {missing}"
        )

    frame = pd.DataFrame(
        [{k: features[k] for k in expected}],
        columns=list(expected),
    )

    # Apply the same StandardScaler that was fit during training.
    scaler = load_scaler(version)
    x_scaled = scaler.transform(frame).astype("float32")
    return pd.DataFrame(x_scaled, columns=list(expected))


@lru_cache(maxsize=8)
def load_scaler(version: str | None = None) -> StandardScaler:
    """Rebuild StandardScaler from the .npz saved next to the run artifact."""
    v = _resolve_version(version)
    mv = _client.get_model_version(REGISTERED_MODEL_NAME, v)
    run = _client.get_run(mv.run_id)

    # Locate the scaler .npz. Your training flow uploaded
    candidates = [
        f"s3://paylater-models/models/dti_distress/{run.info.run_id}/dti_distress_scaler.npz",
        f"s3://paylater-models/models/dti_distress/{v}/dti_distress_scaler.npz",
    ]
    last_err: Exception | None = None
    for uri in candidates:
        try:
            buf = _fetch_uri(uri)
            data = np.load(io.BytesIO(buf))
            scaler = StandardScaler()
            scaler.mean_ = data["mean"]
            scaler.scale_ = data["scale"]
            scaler.var_ = scaler.scale_ ** 2
            scaler.n_features_in_ = len(scaler.mean_)
            return scaler

        except Exception as exc:
            last_err = exc

    raise RuntimeError(
        f"❌ Unable to load DTI scaler for {REGISTERED_MODEL_NAME} v{v}. "
        f"❌ Check that the training flow uploaded dti_distress_scaler.npz to MinIO. "
        f"❌ Last error: {last_err}"
    )

# ─── public entry point ─────────────────────────────────────────────────

def predict_dti_distress(
    features: dict[str, Any], version: str | None = None
) -> dict[str, float | str | None]:
    # Feature contract comes from the model's own logged params.
    expected = load_features(version)
    v = _resolve_version(version)
    model = load_model(v)

    missing = [name for name in expected if name not in features]
    if missing:
        raise ValueError(
            f"Missing required DTI features (expected {len(expected)}): {missing}"
        )

    raw_frame = pd.DataFrame(
        [{k: features[k] for k in expected}],
        columns=list(expected),
    )

    scaler = load_scaler(v)
    x_scaled = scaler.transform(raw_frame).astype("float32")

    # Predict using the raw Keras model or un-validated model implementation
    # to avoid pyfunc schema casting errors (which fail when continuous scaled float32
    # values are validated against pre-scaled integer schema columns like age/num_active_lending_apps).
    keras_model = _raw_keras(model)
    try:
        if keras_model is not None and hasattr(keras_model, "predict"):
            try:
                prediction = keras_model.predict(x_scaled, verbose=0)
            except (TypeError, ValueError):
                prediction = keras_model.predict(x_scaled)
        elif hasattr(model, "_model_impl") and hasattr(model._model_impl, "predict"):
            prediction = model._model_impl.predict(x_scaled)
        else:
            frame = pd.DataFrame(x_scaled, columns=list(expected))
            prediction = model.predict(frame)
    except Exception:
        MODEL_FAILURES.labels(task="dti_distress").inc()
        raise

    values = np.asarray(prediction).reshape(-1, 2)
    if values.shape != (1, 2):
        MODEL_FAILURES.labels(task="dti_distress").inc()
        raise ValueError(f"DTI model returned unexpected shape: {values.shape}")

    MODEL_PREDICTIONS.labels(task="dti_distress").inc()

    return {
        "dti": float(values[0, 0]),
        "financial_distress_index": float(values[0, 1]),
        "model_version": v,
    }