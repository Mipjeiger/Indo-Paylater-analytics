"""Model version metadata operations backed by PostgreSQL."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any
from sqlalchemy import text

from app.registry.db import Database

@dataclass(frozen=True)
class ModelVersion:
    task_name: str
    model_name: str
    version: str
    stage: str = "candidate"
    algorithm: str | None = None
    mlflow_run_id: str | None = None
    artifact_path: str | None = None
    feature_columns: list[str] | None = None
    metrics: dict[str, Any] | None = None

def register_model_version(database: Database, model: ModelVersion) -> int:
    """Insert or update one model version and return its database identifier."""
    values = asdict(model)
    values["feature_columns"] = json.dumps(values["feature_columns"])
    values["metrics"] = json.dumps(values["metrics"])
    statement = text(
        """
        INSERT INTO paylater.model_versions
            (task_name, model_name, version, stage, algorithm, mlflow_run_id,
             artifact_path, feature_columns, metrics)
        VALUES
            (:task_name, :model_name, :version, :stage, :algorithm, :mlflow_run_id,
             :artifact_path, CAST(:feature_columns AS JSONB), CAST(:metrics AS JSONB))
        ON CONFLICT (task_name, version) DO UPDATE SET
            model_name = EXCLUDED.model_name,
            stage = EXCLUDED.stage,
            algorithm = EXCLUDED.algorithm,
            mlflow_run_id = EXCLUDED.mlflow_run_id,
            artifact_path = EXCLUDED.artifact_path,
            feature_columns = EXCLUDED.feature_columns,
            metrics = EXCLUDED.metrics
        RETURNING id
        """
    )
    try:
        with database.engine.begin() as connection:
            identifier = connection.execute(statement, values).scalar_one()
    except Exception as exc:
        raise RuntimeError(
            f"Unable to register model {model.task_name}:{model.version}"
        ) from exc
    return int(identifier)

def get_model_version(
    database: Database,
    task_name: str,
    version: str | None = None,
) -> dict[str, Any]:
    """Retrieve explicit metadata or the newest active version for a task."""
    if not task_name:
        raise ValueError("task_name must not be empty")
    
    if version is None:
        where = "task_name = :task_name AND is_active = TRUE"
        ordering = "trained_at DESC, id DESC"
    else:
        where = "task_name = :task_name AND version = :version"
        ordering = "id DESC"
    
    statement = text(
        f"""
        SELECT id, task_name, model_name, version, stage, algorithm, mlflow_run_id,
               artifact_path, feature_columns, metrics, trained_at, promoted_at,
               promoted_by, is_active
        FROM paylater.model_versions
        WHERE {where}
        ORDER BY {ordering}
        LIMIT 1
        """
    )
    params = {"task_name": task_name, "version": version}
    with database.engine.connect() as connection:
        row = connection.execute(statement, params).mappings().first()
    
    if row is None:
        selection = f"{task_name}:{version}" if version else f"active {task_name}"
        raise LookupError(f"Model version not found: {selection}")
    return dict(row)

def promote_model_version(
    database: Database,
    task_name: str,
    version: str,
    promoted_by: str,
) -> None:
    """Make one version active for a task and deactivate its previous version."""
    if not promoted_by:
        raise ValueError("promoted_by must not be empty")
    
    try:
        with database.engine.begin() as connection:
            updated = connection.execute(
                text(
                    """
                    UPDATE paylater.model_versions
                    SET is_active = FALSE, promoted_at = NULL
                    WHERE task_name = :task_name
                    """
                ),
                {"task_name": task_name},
            )
            if updated.rowcount == 0:
                raise LookupError(f"No model versions found for task: {task_name}")
            selected = connection.execute(
                text(
                    """
                    UPDATE paylater.model_versions
                    SET is_active = TRUE, stage = 'production',
                        promoted_at = CURRENT_TIMESTAMP, promoted_by = :promoted_by
                    WHERE task_name = :task_name AND version = :version
                    """
                ),
                {"task_name": task_name, "version": version, "promoted_by": promoted_by},
            )
            if selected.rowcount != 1:
                raise LookupError(f"Model version not found: {task_name}:{version}")
    
    except LookupError:
        raise
    except Exception as exc:
        raise RuntimeError(f"Unable to promote model {task_name}:{version}") from exc
