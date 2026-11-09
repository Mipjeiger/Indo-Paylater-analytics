import os
import pytest

from app.registry.loader import (
    ModelVersion,
    get_model_version,
    promote_model_version,
    register_model_version,
)

def test_model_version_requires_task_and_version_metadata():
    model = ModelVersion(
        task_name="twp90",
        model_name="twp90_classifier",
        version="1",
        algorithm="catboost",
        artifact_path="models:/twp90/1",
        feature_columns=["age", "days_past_due"],
        metrics={"f1": 0.8},
    )

    assert model.task_name == "twp90"
    assert model.feature_columns == ["age", "days_past_due"]

def test_model_metadata_operations(postgres_database):
    model = ModelVersion(
        task_name="registry_test",
        model_name="test_model",
        version="1",
        algorithm="test",
        feature_columns=["age"],
        metrics={"accuracy": 0.9},
    )
    identifier = register_model_version(postgres_database, model)
    assert identifier > 0

    promote_model_version(postgres_database, "registry_test", "1", "pytest")
    metadata = get_model_version(postgres_database, "registry_test")

    assert metadata["task_name"] == "registry_test"
    assert metadata["version"] == "1"
    assert metadata["is_active"] is True

@pytest.fixture
def postgres_database():
    url = os.getenv("POSTGRES_URL")
    if not url:
        pytest.skip("Set POSTGRES_URL to run PostgreSQL integration tests")

    from app.registry.db import Database

    database = Database.from_url(url)
    try:
        database.check_connection()
        database.run_migrations()
    except RuntimeError as exc:
        database.dispose()
        pytest.skip(str(exc))
    yield database
    database.dispose()
