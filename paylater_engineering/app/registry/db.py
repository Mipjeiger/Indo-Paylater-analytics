from __future__ import annotations
from pathlib import Path
from typing import Any
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

"""Database connection management for the model registry."""

DEFAULT_MIGRATION_PATH = (
    Path(__file__).resolve().parents[2] / "database" / "migrations" / "001_initial_schema.sql"
)

def get_database_url(url: str | None = None) -> str:
    """Return the configured PostgreSQL URL, failing explicitly when absent."""
    if url:
        return url

    from app.api.config import settings

    configured_url = settings.POSTGRES_URL
    if not configured_url:
        raise RuntimeError("POSTGRES_URL is required to connect to PostgreSQL")
    return configured_url

def create_database_engine(
    url: str | None = None,
    *,
    pool_size: int = 5,
    max_overflow: int = 10,
) -> Engine:
    """Create a pooled SQLAlchemy engine for PostgreSQL."""
    url = get_database_url(url)
    kwargs: dict[str, Any] = {"pool_pre_ping": True}
    if not url.startswith("sqlite"):
        kwargs.update(pool_size=pool_size, max_overflow=max_overflow, pool_recycle=1800)
    return create_engine(url, **kwargs)

class Database:
    """Small lifecycle wrapper around a SQLAlchemy engine."""

    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    @classmethod
    def from_url(cls, url: str | None = None, **kwargs: Any) -> "Database":
        return cls(create_database_engine(url, **kwargs))

    def check_connection(self) -> None:
        """Raise a database exception if the configured database is unreachable."""
        try:
            with self.engine.connect() as connection:
                connection.execute(text("SELECT 1"))
        except Exception as exc:
            raise RuntimeError("Unable to connect to the configured PostgreSQL database") from exc

    def run_migrations(self, migration_path: Path | None = None) -> None:
        """Execute the idempotent schema migration in one transaction."""
        path = migration_path or DEFAULT_MIGRATION_PATH
        
        if not path.is_file():
            raise FileNotFoundError(f"Migration file does not exist: {path}")
        script = path.read_text(encoding="utf-8")
        
        try:
            with self.engine.begin() as connection:
                connection.exec_driver_sql(script)
        except Exception as exc:
            raise RuntimeError(f"Database migration failed: {path}") from exc

    def dispose(self) -> None:
        self.engine.dispose()
