"""FastAPI dependencies for database and feature access."""

from collections.abc import Generator

from app.registry.db import Database


def get_db() -> Generator[Database, None, None]:
    database = Database.from_dsn()
    try:
        yield database
    finally:
        database.dispose()
