"""FastAPI dependencies for database and feature access."""

from collections.abc import Generator
from app.registry.db import Database

def get_db() -> Generator[Database, None, None]:
    database = Database.from_url()
    try:
        yield database
    finally:
        database.dispose()
