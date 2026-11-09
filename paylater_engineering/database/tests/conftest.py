import os
import pytest
from app.registry.db import Database

@pytest.fixture
def postgres_database():
    url = os.getenv("POSTGRES_URL")
    if not url:
        pytest.skip("Set POSTGRES_URL to run PostgreSQL integration tests")
    database = Database.from_url(url)
    
    try:
        database.check_connection()
    except RuntimeError as exc:
        database.dispose()
        pytest.skip(str(exc))
    yield database
    database.dispose()
