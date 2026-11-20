from fastapi import APIRouter, BackgroundTasks, HTTPException

from app.actions.blocker import block_borrower
from app.actions.notifier import notify_api_hit
from app.actions.rules import evaluate_rules
from app.api.schemas import RootCauseResponse, TWP90Request
from app.serving.infer_root_cause import predict_root_cause
from app.registry.db import create_database_engine

"""Root-cause classification endpoint."""

router = APIRouter()
_engine = create_database_engine()

class _DB:
    def __init__(self, engine):
        self.engine = engine

@router.post("/root-cause/{borrower_id}", response_model=RootCauseResponse)
def classify_root_cause(
    borrower_id: str,
    request: TWP90Request,
    background_tasks: BackgroundTasks,
):
    try:
        result = predict_root_cause(request.features)
    except (RuntimeError, ValueError) as exc:
        background_tasks.add_task(
            notify_api_hit,
            "POST /classify/root-cause/{borrower_id}",
            borrower_id, "failed", str(exc),
        )
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    # Evaluate rules
    try:
        matches = evaluate_rules(borrower_id, request.features)
    except ValueError as exc:
        background_tasks.add_task(
            notify_api_hit,
            "POST /classify/root-cause/{borrower_id}",
            borrower_id, "rule_config_error", str(exc),
        )
        matches = []

    # Fire block for the TOP match only (Fix 2 from previous message)
    block_outcome = None
    if matches:
        top = matches[0]
        reason = (
            f"{top['reason']}; "
            f"root_cause={result['root_cause']} "
            f"(confidence={result['confidence']:.2f})"
        )
        try:
            block_outcome = block_borrower(
                database=_DB(_engine),
                borrower_id=borrower_id,
                rule_code=top["rule_code"],
                reason=reason,
                idempotency_key=top["idempotency_key"],
            )
            # ONLY notify on actual block trigger (not on success)
            background_tasks.add_task(
                notify_api_hit,
                "POST /classify/root-cause/{borrower_id}",
                borrower_id, "block_triggered",
                f"rule={top['rule_code']} status={block_outcome['action_status']}",
            )
        except Exception as exc:
            background_tasks.add_task(
                notify_api_hit,
                "POST /classify/root-cause/{borrower_id}",
                borrower_id, 
                "block_failed", 
                str(exc),
            )

    # NO success notification
    return {
        "borrower_id": borrower_id, 
        **result, 
        "block": block_outcome
    }