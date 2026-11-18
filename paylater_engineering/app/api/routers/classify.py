"""Root-cause classification endpoint."""

from fastapi import APIRouter, BackgroundTasks, HTTPException

from app.api.schemas import RootCauseResponse, TWP90Request
from app.actions.notifier import notify_api_hit
from app.serving.infer_root_cause import predict_root_cause

router = APIRouter()

@router.post("/root-cause/{borrower_id}", response_model=RootCauseResponse)
def classify_root_cause(borrower_id: str, request: TWP90Request, background_tasks: BackgroundTasks):
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
    background_tasks.add_task(
        notify_api_hit,
        "POST /classify/root-cause/{borrower_id}",
        borrower_id,
        "success",
    )
    return {"borrower_id": borrower_id, **result}
