import logging
import time
from typing import Any
import requests
from app.monitoring.metrics import ACTION_OUTCOMES
from app.api.config import settings

"""Optional Slack notification delivery."""

logger = logging.getLogger(__name__)

_last_failure_alert: dict[str, float] = {}
_FAILURE_ALERT_INTERVAL = 60.0   # one alert per minute per key

def notify_api_hit(endpoint: str, borrower_id: str, status: str, detail: str = "") -> dict[str, Any]:
    if not settings.SLACK_NOTIFY_ON_API_HIT:
        return {"channel": "api", "delivered": False, "reason": "api_notifications_disabled"}

    # Rate-limit all statuses except block triggered and failed
    if status not in ("block_triggered", "block_failed"):
        now = time.monotonic()
        last = _last_failure_alert.get(status, 0.0)
        if now - last < _FAILURE_ALERT_INTERVAL:
            return {"channel": "api", "delivered": False, "reason": "rate_limited"}
        _last_failure_alert[status] = now

    message = f"PayLater API {status}: {endpoint} borrower={borrower_id}"
    if detail:
        message += f" detail={detail}"
    return send_notification("api", message)

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
        logger.warning("⚠️ Notification delivery failed: %s", e, extra={"channel": channel})
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