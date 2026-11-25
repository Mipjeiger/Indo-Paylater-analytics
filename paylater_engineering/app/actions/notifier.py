import logging
import time
from typing import Any
import requests
from app.monitoring.metrics import ACTION_OUTCOMES
from app.api.config import settings

"""Optional Slack notification delivery."""

logger = logging.getLogger(__name__)

_last_failure_alert: dict[str, float] = {}
_FAILURE_ALERT_INTERVAL = 5.0   # Cooldown for exact duplicate borrower alert (seconds)

def notify_api_hit(
    endpoint: str,
    borrower_id: str,
    status: str,
    detail: str = "",
    *,
    force: bool = False,
) -> dict[str, Any]:
    if not settings.SLACK_NOTIFY_ON_API_HIT:
        logger.debug("Slack notify skipped: SLACK_NOTIFY_ON_API_HIT is disabled")
        return {"channel": "api", "delivered": False, "reason": "api_notifications_disabled"}

    # Rate-limit only rapid duplicates of the exact same borrower on the same endpoint
    key = f"{endpoint}:{borrower_id}:{status}"
    if not force and status not in ("block_triggered", "block_failed"):
        now = time.monotonic()
        last = _last_failure_alert.get(key, 0.0)
        if _FAILURE_ALERT_INTERVAL > 0 and (now - last < _FAILURE_ALERT_INTERVAL):
            logger.info("⏱️ Slack notification for %s rate-limited (last sent %.1fs ago)", key, now - last)
            return {"channel": "api", "delivered": False, "reason": "rate_limited"}
        _last_failure_alert[key] = now

    message = f"PayLater API {status}: {endpoint} borrower={borrower_id}"
    if detail:
        message += f" | {detail}"
    return send_notification("api", message)

def send_notification(channel: str, message: str, *, timeout: float = 5.0) -> dict[str, Any]:
    webhook = settings.SLACK_WEBHOOK_URL
    if not webhook:
        logger.warning("⚠️ Slack notification not configured: SLACK_WEBHOOK_URL is not set")
        ACTION_OUTCOMES.labels(action="notify_slack", status="not_configured").inc()
        return {
            "channel": channel, 
            "delivered": False, 
            "reason": "not_configured",
        }

    logger.info("📣 Sending Slack notification [%s]: %s", channel, message)
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
            "reason": str(e),
        }

    logger.info("✅ Slack notification delivered successfully (HTTP %s)", response.status_code)
    ACTION_OUTCOMES.labels(action="notify_slack", status="sent").inc()
    return {
        "channel": channel, 
        "delivered": True, 
        "status_code": response.status_code, 
        "response": response.text,
    }
