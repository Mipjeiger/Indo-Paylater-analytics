"""Central Prometheus metrics."""

from prometheus_client import Counter, Gauge, Histogram

HTTP_REQUESTS = Counter("paylater_http_requests_total", "HTTP requests", ["method", "path", "status"])
HTTP_LATENCY = Histogram("paylater_http_request_latency_seconds", "HTTP request latency", ["path"])
MODEL_PREDICTIONS = Counter("paylater_model_predictions_total", "Model predictions", ["task"])
MODEL_FAILURES = Counter("paylater_model_inference_failures_total", "Model failures", ["task"])
FEATURE_FAILURES = Counter("paylater_feature_retrieval_failures_total", "Feature failures")
DRIFT_STATUS = Gauge("paylater_drift_detected", "Current drift status", ["task", "feature"])
ACTION_OUTCOMES = Counter("paylater_action_outcomes_total", "Action outcomes", ["action", "status"])