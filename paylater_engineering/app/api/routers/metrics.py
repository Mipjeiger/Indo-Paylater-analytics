from fastapi import APIRouter, Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

"""Metrics endpoint for Prometheus scraping."""

router = APIRouter()

@router.get("", include_in_schema=False)
async def metrics_endpoint():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)