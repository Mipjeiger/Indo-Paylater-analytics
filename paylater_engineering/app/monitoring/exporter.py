"""Persistence helper for structured drift reports."""

from typing import Any

from sqlalchemy import text


def persist_drift_report(database: Any, task_name: str, report: dict[str, Any]) -> int:
    if not task_name:
        raise ValueError("task_name is required")
    detected = any(item.get("drift_detected", False) for item in report.values())
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
