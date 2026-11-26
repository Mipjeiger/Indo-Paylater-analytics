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

# Add helper codes for root-cause classification
CRITICAL_ROOT_CAUSE_FIELDS = (
    "monthly_income_idr",
    "num_active_lending_apps",
    "total_loan_outstanding_idr",
)

ROOT_CAUSE_DEFAULTS = {
    "age": 30,
    "gender": "Female",
    "province": "DKI Jakarta",
    "education_level": "Bachelor (S1)",
    "employment_status": "Formal Private Employee",
    "primary_loan_purpose": "Daily Living & Emergency Buffer",
    "regional_minimum_wage_umr_idr": 0.0,
    "credit_limit_granted_idr": 0.0,
    "loan_tenor_months": 6,
    "daily_interest_rate_pct": 0.1,
    "income_to_umr_ratio": 0.0,
    "credit_limit_utilization_ratio": 0.0,
    "monthly_installment_estimate_idr": 0.0,
    "debt_service_ratio": 0.0,
    "disposable_income_after_debt_idr": 0.0,
}

def fill_root_cause_defaults(features: dict) -> tuple[dict, list[str]]:
    missing = [f for f in CRITICAL_ROOT_CAUSE_FIELDS if features.get(f) in (None, "")]
    if missing:
        raise ValueError(f"Missing critical fields for root-cause classification: {missing}")

    merged = dict(features)
    defaulted: list[str] = []
    for k, v in ROOT_CAUSE_DEFAULTS.items():
        if merged.get(k) in (None, ""):
            merged[k] = v
            defaulted.append(k)

    return merged, defaulted


@router.post("/root-cause/{borrower_id}", response_model=RootCauseResponse)
def classify_root_cause(
    borrower_id: str,
    request: TWP90Request,
    background_tasks: BackgroundTasks,
):
    # ─── Step 1: fill defaults before inference
    try:
        merged_features, defaulted_fields = fill_root_cause_defaults(request.features)
    except ValueError as exc:
        background_tasks.add_task(
            notify_api_hit,
            "POST /classify/root-cause/{borrower_id}",
            borrower_id, "input_validation_failed", str(exc),
        )
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    # ─── Step 2: inference on merged features
    try:
        result = predict_root_cause(merged_features)
    except (RuntimeError, ValueError) as exc:
        background_tasks.add_task(
            notify_api_hit,
            "POST /classify/root-cause/{borrower_id}",
            borrower_id, "failed", str(exc),
        )
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    # ─── Step 3: rules (on raw request.features — rules check user-supplied DPD etc.)
    try:
        matches = evaluate_rules(borrower_id, request.features)
    except ValueError as exc:
        background_tasks.add_task(
            notify_api_hit,
            "POST /classify/root-cause/{borrower_id}",
            borrower_id, "rule_config_error", str(exc),
        )
        matches = []

    # ─── Step 4: block if any rule matched
    block_outcome = None
    if matches:
        top = matches[0]
        reason = (
            f"{top['reason']}; root_cause={result['root_cause']} "
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
                borrower_id, "block_failed", str(exc),
            )

    # ─── Step 5: return with defaulted_fields so frontend can warn
    return {
        "borrower_id": borrower_id,
        **result,
        "block": block_outcome,
        "defaulted_fields": defaulted_fields,
    }