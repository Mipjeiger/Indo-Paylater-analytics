import os
from datetime import date

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.actions.blocker import block_borrower
from app.actions.notifier import send_notification
from app.registry.db import create_database_engine

router = APIRouter(prefix="/admin", tags=["admin"])
_engine = create_database_engine()

class _DB:
    def __init__(self, engine): self.engine = engine

class NotifyIn(BaseModel):
    channel: str = "slack"
    message: str

class BlockIn(BaseModel):
    borrower_id: str
    rule_code: str
    reason: str
    idempotency_key: str | None = None
    approved_by: str | None = None

@router.post("/notify")
def admin_notify(body: NotifyIn):
    if os.getenv("ADMIN_DEV_ENDPOINTS", "0") != "1":
        raise HTTPException(404)
    return send_notification(body.channel, body.message)

@router.post("/block")
def admin_block(body: BlockIn):
    if os.getenv("ADMIN_DEV_ENDPOINTS", "0") != "1":
        raise HTTPException(404)

    key = body.idempotency_key or f"{body.borrower_id}:block:{body.rule_code}:{date.today().isoformat()}"

    return block_borrower(
        database=_DB(_engine),
        borrower_id=body.borrower_id,
        rule_code=body.rule_code,
        reason=body.reason,
        idempotency_key=key,
        approved_by=body.approved_by,
    )