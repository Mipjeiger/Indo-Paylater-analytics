from fastapi import APIRouter, Depends
from app.api.deps import get_db

"""Service health endpoint."""

router = APIRouter()

@router.get("/")
def health_check(database=Depends(get_db)):
    database.check_connection()
    return {"status": "ok"}
