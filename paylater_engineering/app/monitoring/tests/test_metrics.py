from prometheus_client import generate_latest

from app.monitoring.metrics import ACTION_OUTCOMES, DRIFT_STATUS


def test_drift_and_action_metrics_are_exposed():
    DRIFT_STATUS.labels(task="test_task", feature="test_feature").set(1)
    ACTION_OUTCOMES.labels(action="test_action", status="test_status").inc()

    output = generate_latest().decode("utf-8")

    assert 'paylater_drift_detected{feature="test_feature",task="test_task"} 1.0' in output
    assert 'paylater_action_outcomes_total{action="test_action",status="test_status"}' in output
