"""Risk scoring endpoints."""

from fastapi import APIRouter, BackgroundTasks, HTTPException

from app.api.schemas import DTIResponse, TWP90Request, TWP90Response
from app.actions.notifier import notify_api_hit
from app.serving.infer_dti_distress import predict_dti_distress
from app.serving.infer_twp90 import predict_twp90
from app.serving.prediction_logger import PredictionLogger
from app.actions.rules import evaluate_rules
from app.actions.blocker import block_borrower

router = APIRouter()

@router.post("/twp90", response_model=TWP90Response)
def score_twp90(request: TWP90Request, background_tasks: BackgroundTasks):
    from app.api.deps import get_db

    database = next(get_db())
    logger = PredictionLogger(database)
    logger.start()
    try:
        result = predict_twp90(request.features)
    except (RuntimeError, ValueError) as exc:
        background_tasks.add_task(
            notify_api_hit,
            "POST /score/twp90",
            request.borrower_id,
            "failed",
            str(exc),
        )
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    # ─── Persist the prediction to paylater.predictions (MinIO-backed model)
    prob = float(result.get("default_probability", 0.0))
    model_version = str(result.get("model_version", ""))
    risk_tier = "HIGH_RISK" if prob >= 0.5 else "LOW_RISK"

    try:
        logger.record(
            borrower_id=request.borrower_id,
            task_name="twp90",
            prediction=result,
            prediction_score=prob,
            features=request.features,
            model_version=model_version,
        )
    except Exception as exc:
        background_tasks.add_task(
            notify_api_hit,
            "POST /score/twp90",
            request.borrower_id,
            "prediction_log_failed",
            str(exc),
        )

    # ─── Check action rules (DPD 90+, High Utilization) & execute auto-block if matched
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
                notify_api_hit,
                "POST /score/twp90",
                request.borrower_id,
                "block_triggered",
                f"rule={top['rule_code']} status={block_outcome['action_status']} prob={prob:.4f}",
            )
    except Exception as exc:
        background_tasks.add_task(
            notify_api_hit,
            "POST /score/twp90",
            request.borrower_id,
            "rule_evaluation_error",
            str(exc),
        )

    # ─── Notify API hit for successful scoring
    detail = f"prob={prob:.4f} risk={risk_tier} version={model_version}"
    background_tasks.add_task(
        notify_api_hit,
        "POST /score/twp90",
        request.borrower_id,
        "success",
        detail,
    )
    return {"borrower_id": request.borrower_id, **result}


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
    from app.api.deps import get_db

    database = next(get_db())
    logger = PredictionLogger(database)
    logger.start()
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
        logger.record(
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