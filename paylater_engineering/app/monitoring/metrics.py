"""Central Prometheus metrics."""

from prometheus_client import Counter, Gauge, Histogram

# HTTP
HTTP_REQUESTS = Counter("paylater_http_requests_total", "HTTP requests", ["method", "path", "status"])
HTTP_LATENCY = Histogram("paylater_http_request_latency_seconds", "HTTP request latency", ["path"])

# Model
MODEL_PREDICTIONS = Counter("paylater_model_predictions_total", "Model predictions", ["task"])
MODEL_FAILURES = Counter("paylater_model_inference_failures_total", "Model failures", ["task"])
FEATURE_FAILURES = Counter("paylater_feature_retrieval_failures_total", "Feature failures")

# Drift
DRIFT_STATUS = Gauge("paylater_drift_detected", "Current drift status", ["task", "feature"])

# Actions
ACTION_OUTCOMES = Counter("paylater_action_outcomes_total", "Action outcomes", ["action", "status"])

# Initialize labeled series so Prometheus/Grafana can query them before the first increment. This avoids "no data" errors in dashboards.
DRIFT_STATUS.labels(task="uninitialized", feature="uninitialized").set(0)
for action, status in (
    ("block", "pending_approval"),
    ("block", "approved"),
    ("block", "disabled"),
    ("block", "deduped"),
    ("notify_slack", "sent"),
    ("notify_slack", "failed"),
    ("notify_slack", "not_configured"),
):
    ACTION_OUTCOMES.labels(action=action, status=status).inc(0)