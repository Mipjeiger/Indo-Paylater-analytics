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
    background_tasks: BackgroundTasks
):
    try:
        result = predict_root_cause(request.features)
    except (RuntimeError, ValueError) as exc:
        background_tasks.add_task(
            notify_api_hit,
            "POST /classify/root-cause/{borrower_id}",
            borrower_id,
            "failed",
            str(exc),
        )
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    # ─── Evaluate rules from the request features
    try:
        matches = evaluate_rules(borrower_id, request.features)
    except ValueError as exc:
        background_tasks.add_task(
            notify_api_hit,
            "POST /classify/root-cause/{borrower_id}",
            borrower_id,
            "rule_config_error",
            str(exc),
        )
        matches = []

    # ─── Block borrower for matched rules
    block_outcomes = []
    for match in matches:
        reason = (
            f"{match['reason']}; root_cause={result['root_cause']}"
            f"(confidence={result['confidence']:.2f}),"
            f"model_version={result['model_version']}"
        )
        try:
            # Identify block borrower with required parameters
            outcome = block_borrower(
                database=_DB(_engine),
                borrower_id=borrower_id,
                rule_code=match["rule_code"],
                reason=reason,
                idempotency_key=match["idempotency_key"],
            )
            block_outcomes.append(outcome)
        except Exception as exc:
            background_tasks.add_task(
                notify_api_hit,
                "POST /classify/root-cause/{borrower_id}",
                borrower_id,
                "block_failed",
                f"rule={match['rule_code']} err={exc}",
            )

    # Background task to notify API hit with success and block outcomes
    background_tasks.add_task(
        notify_api_hit,
        "POST /classify/root-cause/{borrower_id}",
        borrower_id,
        "success",
        f"root_cause={result['root_cause']} blocks={len(block_outcomes)}"
    )

    return {
        "borrower_id": borrower_id,
        **result,
        "block": block_outcomes[0] if len(block_outcomes) == 1 else block_outcomes or None,
    }