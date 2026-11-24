"""Risk scoring endpoints."""

from fastapi import APIRouter, BackgroundTasks, HTTPException

from app.api.schemas import DTIResponse, TWP90Request, TWP90Response
from app.actions.notifier import notify_api_hit
from app.serving.infer_dti_distress import predict_dti_distress
from app.serving.infer_twp90 import predict_twp90
from app.serving.prediction_logger import PredictionLogger

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
    try:
        logger.record(
            borrower_id=request.borrower_id,
            task_name="twp90",
            prediction=result,
            prediction_score=float(result.get("default_probability", 0.0)),
            features=request.features,
            model_version=str(result.get("model_version", "")),
        )
    except Exception as exc:
        background_tasks.add_task(
            notify_api_hit,
            "POST /score/twp90",
            request.borrower_id,
            "prediction_log_failed",
            str(exc),
        )

    # ─── Notify API hit for successful scoring
    background_tasks.add_task(
        notify_api_hit,
        "POST /score/twp90",
        request.borrower_id,
        "success",
    )
    return {"borrower_id": request.borrower_id, **result}


@router.get("/dti-distress/{borrower_id}", response_model=DTIResponse)
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
    background_tasks.add_task(
        notify_api_hit,
        "GET /score/dti-distress/{borrower_id}",
        borrower_id,
        "success",
    )
    return {"borrower_id": borrower_id, **result}