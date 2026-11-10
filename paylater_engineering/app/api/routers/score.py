"""Risk scoring endpoints."""

from fastapi import APIRouter, HTTPException

from app.api.schemas import DTIResponse, TWP90Request, TWP90Response
from app.serving.infer_dti_distress import predict_dti_distress
from app.serving.infer_twp90 import predict_twp90

router = APIRouter()

@router.post("/twp90", response_model=TWP90Response)
def score_twp90(request: TWP90Request):
    try:
        result = predict_twp90(request.features)
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"borrower_id": request.borrower_id, **result}

@router.get("/dti-distress/{borrower_id}", response_model=DTIResponse)
def score_dti_distress(borrower_id: str, features: dict[str, object]):
    try:
        result = predict_dti_distress(features)
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"borrower_id": borrower_id, **result}
