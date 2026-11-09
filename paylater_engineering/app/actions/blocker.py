import os
from typing import Any
from sqlalchemy import text

"""Safe borrower action service with approval and audit requirements."""

def block_borrower(
    database: Any,
    borrower_id: str,
    rule_code: str,
    reason: str,
    idempotency_key: str,
    *,
    approved_by: str | None = None,
) -> dict[str, Any]:
    if not all((borrower_id, rule_code, reason, idempotency_key)):
        raise ValueError("borrower_id, rule_code, reason, and idempotency_key are required")
    if os.getenv("ACTION_KILL_SWITCH", "0") == "1":
        status = "disabled"
    elif os.getenv("AUTO_BLOCK", "0") == "1" and approved_by:
        status = "approved"
    else:
        status = "pending_approval"
    statement = text(
        """
        INSERT INTO paylater.actions_log
            (borrower_id, action_type, action_status, rule_code, recommendation,
             executed_by, idempotency_key)
        VALUES (:borrower_id, 'block', :status, :rule_code, :reason, :executed_by, :key)
        ON CONFLICT (idempotency_key) DO NOTHING
        RETURNING id
        """
    )
    with database.engine.begin() as connection:
        identifier = connection.execute(
            statement,
            {
                "borrower_id": borrower_id,
                "status": status,
                "rule_code": rule_code,
                "reason": reason,
                "executed_by": approved_by or "system",
                "key": idempotency_key,
            },
        ).scalar()
    return {
        "borrower_id": borrower_id,
        "action_type": "block",
        "action_status": status,
        "action_id": identifier,
        "idempotency_key": idempotency_key,
    }
