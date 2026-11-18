import logging
import os
from typing import Any
import requests
from app.monitoring.metrics import ACTION_OUTCOMES
from app.api.config import settings

"""Optional Slack notification delivery."""

logger = logging.getLogger(__name__)

def send_notification(channel: str, message: str, *, timeout: float = 5.0) -> dict[str, Any]:
    webhook = settings.SLACK_WEBHOOK_URL
    if not webhook:
        ACTION_OUTCOMES.labels(action="notify_slack", status="not_configured").inc()
        return {
            "channel": channel, 
            "delivered": False,
            "reason": "not_configured"
            }

    # Call slack response
    try:
        response = requests.post(
            webhook,
            json={"text": message},
            timeout=timeout,
        )
        response.raise_for_status()
    except requests.RequestException as e:
        logger.exception("⚠️ Notification delivery failed", extra={"channel": channel})
        ACTION_OUTCOMES.labels(action="notify_slack", status="failed").inc()

        return {
            "channel": channel,
            "delivered": False,
            "reason": str(e)
        }
    ACTION_OUTCOMES.labels(action="notify_slack", status="sent").inc()

    return {
        "channel": channel, 
        "delivered": True, 
        "status_code": response.status_code, 
        "response": response.text
        }