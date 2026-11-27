"""Risk scoring endpoints."""

from fastapi import APIRouter, BackgroundTasks, HTTPException

from app.api.schemas import DTIResponse, TWP90Request, TWP90Response
from app.actions.notifier import notify_api_hit
from app.serving.infer_dti_distress import predict_dti_distress
from app.serving.infer_twp90 import predict_twp90
from app.serving.prediction_logger import PredictionLogger
from app.actions.rules import evaluate_rules
from app.actions.blocker import block_borrower
from app.api.deps import get_db

# ==========================
# Helper codes for TWP90 scoring
# ==========================
CRITICAL_TWP90_FIELDS = (
    "age",
    "monthly_income_idr",
    "regional_minimum_wage_umr_idr",
    "num_active_lending_apps",
)

# training distribution. If a field is filled by the user, the user value wins.
TWP90_DEFAULTS = {
    "gender": "Female",
    "province": "DKI Jakarta",
    "education_level": "Bachelor (S1)",
    "employment_status": "Formal Private Employee",
    "primary_loan_purpose": "Daily Living & Emergency Buffer",
    "total_loan_outstanding_idr": 0.0,
    "credit_limit_granted_idr": 0.0,
    "loan_tenor_months": 6,
    "daily_interest_rate_pct": 0.1,
    "income_to_umr_ratio": 0.0,
    "credit_limit_utilization_ratio": 0.0,
    "monthly_installment_estimate_idr": 0.0,
    "debt_service_ratio": 0.0,
    "disposable_income_after_debt_idr": 0.0,
}

# ==========================
# Helper codes for DTI distress scoring
# ==========================
CRITICAL_DTI_FIELDS = (
    "monthly_income_idr",
    "total_loan_outstanding_idr",
    "monthly_installment_estimate_idr",
)

DTI_DEFAULTS = {
    "age": 30,
    "gender": "Female",
    "province": "DKI Jakarta",
    "education_level": "Bachelor (S1)",
    "employment_status": "Formal Private Employee",
    "primary_loan_purpose": "Daily Living & Emergency Buffer",
    "regional_minimum_wage_umr_idr": 0.0,
    "num_active_lending_apps": 1,
    "credit_limit_granted_idr": 0.0,
    "loan_tenor_months": 6,
    "daily_interest_rate_pct": 0.1,
    "income_to_umr_ratio": 0.0,
    "credit_limit_utilization_ratio": 0.0,
    "debt_service_ratio": 0.0,
    "disposable_income_after_debt_idr": 0.0,
}

def fill_twp90_defaults(features: dict) -> tuple[dict, list[str]]:
    """Merge user features with model defaults. Returns (merged, defaulted fields)."""
    missing_critical = [f for f in CRITICAL_TWP90_FIELDS if features.get(f) in (None, "")]
    if missing_critical:
        raise ValueError(f"Missing critical fields: {', '.join(missing_critical)}")

    merged = dict(features)
    defaulted: list[str] = []
    for k, v in TWP90_DEFAULTS.items():
        if merged.get(k) in (None, ""):
            merged[k] = v
            defaulted.append(k)

    return merged, defaulted

def fill_dti_defaults(features: dict) -> tuple[dict, list[str]]:
    missing = [f for f in CRITICAL_DTI_FIELDS if features.get(f) in (None, "")]
    if missing:
        raise ValueError(f"Missing required fields: {missing}")
    merged = dict(features)
    defaulted = []
    for k, v in DTI_DEFAULTS.items():
        if merged.get(k) in (None, ""):
            merged[k] = v
            defaulted.append(k)
    return merged, defaulted

router = APIRouter()

@router.post("/twp90", response_model=TWP90Response)
def score_twp90(request: TWP90Request, background_tasks: BackgroundTasks):

    # --- Step 1: merge user input with defaults
    try:
        merged_features, defaulted_fields = fill_twp90_defaults(request.features)
    except (RuntimeError, ValueError) as exc:
        background_tasks.add_task(
            notify_api_hit,
            "POST /score/twp90",
            request.borrower_id,
            "input_validation_failed",
            str(exc),
        )
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    # --- Step 2: prediction logger
    database = next(get_db())
    predict_logger = PredictionLogger(database)
    predict_logger.start()

    # --- Step 3: Inference on Merged Features
    try:
        result = predict_twp90(merged_features)
    except (RuntimeError, ValueError) as exc:
        background_tasks.add_task(
            notify_api_hit,
            "POST /score/twp90",
            request.borrower_id,
            "inference_failed",
            str(exc),
        )
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    prob = float(result.get("twp90_prob", 0.0))
    risk_tier = "HIGH_RISK" if prob >= 0.5 else "LOW_RISK"
    model_version = str(result.get("model_version", ""))

    # ─── Step 4: persist (record both input AND merged for audit)
    try:
        predict_logger.record(
            borrower_id=request.borrower_id,
            task_name="twp90",
            prediction=result,
            prediction_score=prob,
            features={
                **request.features,
                "_defaulted_fields": defaulted_fields,   # ← audit trail
            },
            model_version=model_version,
        )
    except Exception as exc:
        background_tasks.add_task(
            notify_api_hit, "POST /score/twp90", request.borrower_id,
            "prediction_log_failed", str(exc),
        )

    # ─── Step 5: rules (existing logic; uses raw request.features)
    try:
        matches = evaluate_rules(request.borrower_id, request.features)
        if matches:
            top = matches[0]
            reason = f"{top['reason']}; twp90_prob={prob:.4f}"
            block_outcome = block_borrower(
                database=database,
                borrower_id=request.borrower_id,
                rule_code=top["rule_code"],
                reason=reason,
                idempotency_key=top["idempotency_key"],
            )
            background_tasks.add_task(
                notify_api_hit, "POST /score/twp90", request.borrower_id,
                "block_triggered",
                f"rule={top['rule_code']} status={block_outcome['action_status']} prob={prob:.4f}",
            )
    except Exception as exc:
        background_tasks.add_task(
            notify_api_hit, "POST /score/twp90", request.borrower_id,
            "rule_evaluation_error", str(exc),
        )

    # ─── Step 6: notify + return
    detail = (
        f"probability={prob:.4f} | risk_level={risk_tier} | "
        f"model_version={model_version} | defaulted={len(defaulted_fields)}"
    )
    background_tasks.add_task(
        notify_api_hit, "POST /score/twp90", request.borrower_id, "success", detail,
    )
    return {
        "borrower_id": request.borrower_id,
        **result,
        "defaulted_fields": defaulted_fields,
    }

@router.api_route(
    "/dti-distress/{borrower_id}",
    methods=["GET", "POST"],
    response_model=DTIResponse,
)
def score_dti_distress(
    borrower_id: str,
    features: dict[str, object],
    background_tasks: BackgroundTasks,
):
    database = next(get_db())
    predict_logger = PredictionLogger(database)
    predict_logger.start()
    try:
        result = predict_dti_distress(features)
    except (RuntimeError, ValueError) as exc:
        background_tasks.add_task(
            notify_api_hit,
            "GET /score/dti-distress/{borrower_id}",
            borrower_id,
            "failed",
            str(exc),
        )
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    # ─── Persist the prediction to paylater.predictions (MinIO-backed model)
    try:
        predict_logger.record(
            borrower_id=borrower_id,
            task_name="dti_distress",
            prediction=result,
            prediction_score=float(result.get("financial_distress_index", 0.0)),
            features=features,
            model_version=str(result.get("model_version", "")),
        )
    except Exception as exc:
        background_tasks.add_task(
            notify_api_hit,
            "GET /score/dti-distress/{borrower_id}",
            borrower_id,
            "prediction_log_failed",
            str(exc),
        )

    # ─── Notify API hit for successful scoring
    dti_val = float(result.get("dti", 0.0))
    distress_idx = float(result.get("financial_distress_index", 0.0))
    dti_version = str(result.get("model_version", ""))
    dti_detail = f"dti={dti_val:.4f} distress_index={distress_idx:.4f} version={dti_version}"

    background_tasks.add_task(
        notify_api_hit,
        "/score/dti-distress/{borrower_id}",
        borrower_id,
        "success",
        dti_detail,
    )
    return {"borrower_id": borrower_id, **result}