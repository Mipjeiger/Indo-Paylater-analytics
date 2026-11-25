from typing import Any
from sqlalchemy import text
from app.monitoring.metrics import DRIFT_STATUS

"""Persistence helper for structured drift reports."""

def persist_drift_report(database: Any, task_name: str, report: dict[str, Any]) -> int:
    if not task_name:
        raise ValueError("task_name is required")

    # Detect if any feature drift was detected in the report
    detected = any(item.get("drift_detected", False) for item in report.values())
    for feature, details in report.items():
        DRIFT_STATUS.labels(task=task_name, feature=str(feature)).set(
            1 if bool(details.get("drift_detected")) else 0
        )
    with database.engine.begin() as connection:
        identifier = connection.execute(
            text(
                """
                INSERT INTO paylater.drift_reports
                    (task_name, drift_type, drift_detected, feature_drift, report_data)
                VALUES (:task, 'feature', :detected, CAST(:features AS JSONB),
                        CAST(:report AS JSONB))
                RETURNING id
                """
            ),
            {
                "task": task_name,
                "detected": detected,
                "features": __import__("json").dumps(report),
                "report": __import__("json").dumps(report),
            },
        ).scalar_one()
    return int(identifier)
