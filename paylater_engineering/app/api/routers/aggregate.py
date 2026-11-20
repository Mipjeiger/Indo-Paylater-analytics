from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from app.api.deps import get_db

"""Read-only aggregation contracts used by the frontend."""

router = APIRouter()

def _json_value(value: Any) -> Any:
    if isinstance(value, (Decimal,)):
        return float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if hasattr(value, "to_dict"):
        return value.to_dict()
    return value

def _rows(connection: Any, statement: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    result = connection.execute(text(statement), params or {})
    return [
        {key: _json_value(value) for key, value in row.items()}
        for row in result.mappings()
    ]

@router.get("/dashboard/kpis")
def dashboard_kpis(database=Depends(get_db)):
    try:
        with database.engine.connect() as connection:
            row = connection.execute(
                text(
                    """
                    SELECT
                        COUNT(*)::int AS total_borrowers,
                        COUNT(*) FILTER (WHERE is_high_risk IS FALSE)::int AS active_borrowers,
                        COALESCE(SUM(total_loan_outstanding_idr), 0) AS outstanding_exposure,
                        CASE WHEN COUNT(*) = 0 THEN 0
                             ELSE COUNT(*) FILTER (
                                WHERE twp90_default_status IS NOT NULL
                                  AND lower(twp90_default_status) NOT LIKE '%default%'
                             )::float / COUNT(*)::float
                        END AS repayment_rate,
                        CASE WHEN COUNT(*) = 0 THEN 0
                             ELSE COUNT(*) FILTER (
                                WHERE twp90_default_status IS NOT NULL
                                  AND lower(twp90_default_status) LIKE '%default%'
                             )::float / COUNT(*)::float
                        END AS twp90_rate
                    FROM paylater.database
                    """
                )
            ).mappings().one()
        return {key: _json_value(value) for key, value in row.items()}
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Dashboard data unavailable") from exc

@router.get("/borrowers")
def borrowers(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    search: str | None = Query(default=None),
    database=Depends(get_db),
):
    params = {"limit": limit, "offset": offset}
    where = ""
    if search:
        where = "WHERE CAST(borrower_id AS TEXT) ILIKE :search"
        params["search"] = f"%{search}%"

    try:
        with database.engine.connect() as connection:
            rows = _rows(
                connection,
                f"""
                SELECT borrower_id, age, gender, province, education_level,
                       employment_status, monthly_income_idr,
                       total_loan_outstanding_idr, debt_to_income_ratio,
                       risk_score, risk_short, is_high_risk,
                       twp90_default_status, primary_default_root_cause,
                       updated_at
                FROM paylater.database
                {where}
                ORDER BY borrower_id
                LIMIT :limit OFFSET :offset
                """,
                params,
            )
            total = connection.execute(
                text(
                    f"SELECT COUNT(*)::int AS count FROM paylater.database {where}"
                ),
                params,
            ).mappings().one()["count"]
        return {"items": rows, "total": int(total), "limit": limit, "offset": offset}
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Borrower data unavailable") from exc

@router.get("/decisions")
def decisions(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    database=Depends(get_db),
):
    try:
        with database.engine.connect() as connection:
            rows = _rows(
                connection,
                """
                SELECT id, borrower_id, action_type, action_status, rule_code,
                       recommendation, executed_by, idempotency_key, created_at
                FROM paylater.actions_log
                ORDER BY created_at DESC
                LIMIT :limit OFFSET :offset
                """,
                {"limit": limit, "offset": offset},
            )
            total = connection.execute(
                text("SELECT COUNT(*)::int AS count FROM paylater.actions_log")
            ).mappings().one()["count"]
        return {"items": rows, "total": int(total), "limit": limit, "offset": offset}
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Decision data unavailable") from exc

@router.get("/portfolio/summary")
def portfolio_summary(database=Depends(get_db)):
    try:
        with database.engine.connect() as connection:
            row = connection.execute(
                text(
                    """
                    SELECT
                        COUNT(*)::int AS total_borrowers,
                        COALESCE(SUM(total_loan_outstanding_idr), 0) AS outstanding_exposure,
                        COALESCE(AVG(debt_to_income_ratio), 0) AS average_dti,
                        COUNT(*) FILTER (WHERE is_high_risk IS TRUE)::int AS high_risk_borrowers,
                        COUNT(*) FILTER (
                            WHERE twp90_default_status IS NOT NULL
                              AND lower(twp90_default_status) LIKE '%default%'
                        )::int AS defaulted_borrowers
                    FROM paylater.database
                    """
                )
            ).mappings().one()
        return {key: _json_value(value) for key, value in row.items()}
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Portfolio data unavailable") from exc

@router.get("/portfolio/{borrower_id}")
def portfolio_by_borrower(borrower_id: str, database=Depends(get_db)):
    try:
        with database.engine.connect() as connection:
            row = connection.execute(
                text(
                    """
                    SELECT
                        borrower_id,
                        age,
                        gender,
                        province,
                        education_level,
                        employment_status,
                        monthly_income_idr,
                        total_loan_outstanding_idr,
                        credit_limit_granted_idr,
                        credit_limit_utilization_ratio,
                        debt_to_income_ratio,
                        days_past_due,
                        financial_distress_index,
                        risk_score,
                        risk_short,
                        is_high_risk,
                        twp90_default_status,
                        primary_default_root_cause,
                        primary_loan_purpose,
                        updated_at
                    FROM paylater.database
                    WHERE borrower_id = :borrower_id
                    """
                ),
                {"borrower_id": borrower_id},
            ).mappings().one_or_none()

            if row is None:
                raise HTTPException(status_code=404, detail="Borrower not found")

            # Also fetch decisions/actions for this borrower
            actions = _rows(
                connection,
                """
                SELECT id, borrower_id, action_type, action_status, rule_code,
                       recommendation, executed_by, idempotency_key, created_at
                FROM paylater.actions_log
                WHERE borrower_id = :borrower_id
                ORDER BY created_at DESC
                LIMIT 20
                """,    
                {"borrower_id": borrower_id},
            )

            # Fetch predictions for this borrower
            predictions = _rows(
                connection,
                """
                SELECT id, borrower_id, task_name, prediction, created_at
                FROM paylater.predictions
                WHERE borrower_id = :borrower_id
                ORDER BY created_at DESC
                LIMIT 20
                """,
                {"borrower_id": borrower_id},
            )

        result = {key: _json_value(value) for key, value in row.items()}
        result["recent_actions"] = actions
        result["recent_predictions"] = predictions
        return result
    
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Borrower portfolio data unavailable") from exc

@router.get("/models")
def model_versions(database=Depends(get_db)):
    try:
        with database.engine.connect() as connection:
            rows = _rows(
                connection,
                """
                SELECT id, task_name, model_name, version, stage, algorithm,
                       mlflow_run_id, artifact_path, feature_columns, metrics,
                       trained_at, promoted_at, promoted_by, is_active
                FROM paylater.model_versions
                ORDER BY trained_at DESC, id DESC
                """,
            )
        return {"items": rows}
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Model registry unavailable") from exc


@router.get("/audit/events")
def audit_events(
    limit: int = Query(default=100, ge=1, le=500),
    database=Depends(get_db),
):
    try:
        with database.engine.connect() as connection:
            rows = _rows(
                connection,
                """
                (
                    SELECT 'action' AS event_type, created_at AS occurred_at,
                           borrower_id, action_status AS status,
                           jsonb_build_object(
                               'action_type', action_type,
                               'rule_code', rule_code,
                               'recommendation', recommendation,
                               'executed_by', executed_by,
                               'idempotency_key', idempotency_key
                           ) AS details
                    FROM paylater.actions_log
                )
                UNION ALL
                (
                    SELECT 'prediction' AS event_type, created_at AS occurred_at,
                           borrower_id, task_name AS status, prediction AS details
                    FROM paylater.predictions
                )
                UNION ALL
                (
                    SELECT 'drift' AS event_type, created_at AS occurred_at,
                           NULL::varchar AS borrower_id,
                           CASE WHEN drift_detected THEN 'detected' ELSE 'clear' END AS status,
                           COALESCE(report_data, '{}'::jsonb) AS details
                    FROM paylater.drift_reports
                )
                ORDER BY occurred_at DESC
                LIMIT :limit
                """,
                {"limit": limit},
            )
        return {"items": rows}
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Audit events unavailable") from exc
