"""Root-cause classification endpoint."""

from fastapi import APIRouter, HTTPException

from app.api.schemas import RootCauseResponse, TWP90Request
from app.serving.infer_root_cause import predict_root_cause

router = APIRouter()

@router.post("/root-cause/{borrower_id}", response_model=RootCauseResponse)
def classify_root_cause(borrower_id: str, request: TWP90Request):
    try:
        result = predict_root_cause(request.features)
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"borrower_id": borrower_id, **result}
