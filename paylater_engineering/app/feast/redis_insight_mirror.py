"""Maintain readable borrower feature hashes beside Feast's native Redis data."""

from __future__ import annotations

import argparse
import json
import logging
import os
import signal
import socket
import subprocess
import time
from collections.abc import Mapping, Sequence
from datetime import datetime, timedelta, timezone
from typing import Any

import redis
from feast import FeatureStore
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

MIRROR_KEY_PREFIX = "paylater_indodana:borrower:"
MIRROR_TTL_SECONDS = 3600
REFRESH_INTERVAL_SECONDS = 2400
BORROWER_BATCH_SIZE = 500
logger = logging.getLogger(__name__)


def readable_fields(
    response: Mapping[str, Sequence[Any]],
    borrower_id: str,
    row_index: int = 0,
) -> dict[str, str]:
    """Convert one Feast online response row into RedisInsight-friendly text."""
    returned_borrowers = response.get("borrower_id")
    if (
        returned_borrowers is None
        or row_index >= len(returned_borrowers)
        or returned_borrowers[row_index] != borrower_id
    ):
        raise ValueError(f"Feast response did not contain borrower {borrower_id}")

    fields: dict[str, str] = {}
    for name, values in response.items():
        if name == "borrower_id":
            continue
        if row_index >= len(values):
            raise ValueError(f"Feast response has no row {row_index} for {name}")
        value = values[row_index]
        if isinstance(value, (dict, list, tuple)):
            fields[name] = json.dumps(value, ensure_ascii=False, sort_keys=True)
        elif value is None:
            fields[name] = "null"
        elif isinstance(value, bool):
            fields[name] = str(value).lower()
        else:
            fields[name] = str(value)

    if not any(value != "null" for value in fields.values()):
        raise LookupError(
            f"No online features found for borrower {borrower_id}; "
            "verify Feast materialization and the PostgreSQL source."
        )
    return fields


def load_borrower_ids(engine: Engine) -> list[str]:
    """Read the complete current borrower set from the PostgreSQL source table."""
    with engine.connect() as connection:
        borrower_ids = list(
            connection.execute(
                text("SELECT borrower_id FROM paylater.database ORDER BY borrower_id")
            ).scalars()
        )
    if not borrower_ids:
        raise LookupError("paylater.database contains no borrowers to mirror")
    return borrower_ids


def get_feature_refs(store: FeatureStore) -> list[str]:
    """Return all registered feature-view references for online retrieval."""
    feature_refs = [
        f"{view.name}:{feature.name}"
        for view in store.list_feature_views()
        for feature in view.features
    ]
    if not feature_refs:
        raise RuntimeError("No Feast feature views are registered.")
    return feature_refs


def mirror_borrowers(
    store: FeatureStore,
    redis_client: redis.Redis,
    borrower_ids: Sequence[str],
    feature_refs: Sequence[str],
    batch_size: int = BORROWER_BATCH_SIZE,
) -> int:
    """Write all provided borrowers to readable Redis hashes in bounded batches."""
    if batch_size < 1:
        raise ValueError("batch_size must be greater than zero")
    if not borrower_ids:
        raise ValueError("borrower_ids must contain at least one borrower ID")

    for start in range(0, len(borrower_ids), batch_size):
        batch = borrower_ids[start : start + batch_size]
        response = store.get_online_features(
            features=list(feature_refs),
            entity_rows=[{"borrower_id": borrower_id} for borrower_id in batch],
            full_feature_names=True,
        ).to_dict()

        returned_ids = response.get("borrower_id")
        if returned_ids is None or len(returned_ids) != len(batch):
            raise ValueError("Feast response borrower count did not match the request")
        row_indices = {
            borrower_id: index for index, borrower_id in enumerate(returned_ids)
        }
        if len(row_indices) != len(batch) or set(row_indices) != set(batch):
            raise ValueError("Feast response borrower IDs did not match the request")

        with redis_client.pipeline(transaction=False) as pipeline:
            for borrower_id in batch:
                row_index = row_indices[borrower_id]
                fields = readable_fields(response, borrower_id, row_index)
                key = f"{MIRROR_KEY_PREFIX}{borrower_id}"
                pipeline.delete(key)
                pipeline.hset(key, mapping=fields)
                pipeline.expire(key, MIRROR_TTL_SECONDS)
            pipeline.execute()
    return len(borrower_ids)


def synchronize_once(
    store: FeatureStore,
    engine: Engine,
    redis_client: redis.Redis,
) -> int:
    """Rematerialize the source and refresh every readable borrower hash."""
    borrower_ids = load_borrower_ids(engine)
    feature_refs = get_feature_refs(store)
    store.materialize(
        start_date=datetime(1970, 1, 1, tzinfo=timezone.utc),
        end_date=datetime.now(timezone.utc) + timedelta(minutes=5),
        full_feature_names=True,
    )
    return mirror_borrowers(store, redis_client, borrower_ids, feature_refs)


def wait_for_feast_server(host: str, port: int, timeout_seconds: int = 300) -> None:
    """Wait until Feast has applied its registry and started serving."""
    deadline = time.monotonic() + timeout_seconds
    while True:
        try:
            with socket.create_connection((host, port), timeout=2):
                logger.info("Feast server is ready at %s:%s", host, port)
                return
        except OSError as error:
            if time.monotonic() >= deadline:
                raise TimeoutError(
                    f"Feast server at {host}:{port} did not become ready "
                    f"within {timeout_seconds} seconds"
                ) from error
            time.sleep(2)


def wait_for_feast_process(process: subprocess.Popen[bytes], seconds: int) -> None:
    """Wait in short intervals so an exited Feast server is detected promptly."""
    deadline = time.monotonic() + seconds
    while True:
        return_code = process.poll()
        if return_code is not None:
            raise RuntimeError(
                f"Feast server exited unexpectedly with status {return_code}"
            )
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return
        time.sleep(min(5, remaining))


def refresh_loop(
    store: FeatureStore,
    engine: Engine,
    redis_client: redis.Redis,
    once: bool,
    feast_process: subprocess.Popen[bytes] | None = None,
) -> None:
    """Refresh readable hashes and report failures while keeping Feast supervised."""
    while True:
        try:
            borrower_count = synchronize_once(store, engine, redis_client)
            logger.info(
                "Refreshed readable Redis hashes for %d borrowers; "
                "next refresh in %d seconds",
                borrower_count,
                REFRESH_INTERVAL_SECONDS,
            )
        except Exception:
            logger.exception("Readable Feast-to-Redis refresh failed")
            if once:
                raise
            if feast_process is None:
                time.sleep(60)
                continue
            wait_for_feast_process(feast_process, 60)
            continue

        if once:
            return
        if feast_process is None:
            time.sleep(REFRESH_INTERVAL_SECONDS)
        else:
            wait_for_feast_process(feast_process, REFRESH_INTERVAL_SECONDS)


def run_managed_service(once: bool) -> None:
    """Apply definitions, then supervise Feast serving and its refresh loop."""
    feast_host = os.getenv("FEAST_SERVER_HOST", "127.0.0.1")
    feast_port = int(os.getenv("FEAST_SERVER_PORT", "6566"))
    bind_host = os.getenv("FEAST_SERVER_BIND_HOST", "0.0.0.0")
    feast_process: subprocess.Popen[bytes] | None = None
    previous_sigterm = signal.signal(signal.SIGTERM, _shutdown_signal)
    previous_sigint = signal.signal(signal.SIGINT, _shutdown_signal)
    try:
        subprocess.run(["feast", "-c", "app/feast", "apply"], check=True)
        feast_process = subprocess.Popen(
            [
                "feast",
                "-c",
                "app/feast",
                "serve",
                "--host",
                bind_host,
                "--port",
                str(feast_port),
            ]
        )
        wait_for_feast_server(feast_host, feast_port)

        postgres_url = os.getenv("POSTGRES_URL")
        redis_url = os.getenv("REDIS_URL")
        if not postgres_url:
            raise RuntimeError(
                "POSTGRES_URL must be set for the readable Redis projection."
            )
        if not redis_url:
            raise RuntimeError(
                "REDIS_URL must be set for the readable Redis projection."
            )

        store = FeatureStore(repo_path=os.path.dirname(__file__))
        engine = create_engine(postgres_url, pool_pre_ping=True)
        redis_client = redis.Redis.from_url(redis_url, decode_responses=True)
        try:
            refresh_loop(store, engine, redis_client, once, feast_process)
        finally:
            engine.dispose()
            redis_client.close()
    except KeyboardInterrupt:
        logger.info("Shutdown requested")
    finally:
        if feast_process is not None and feast_process.poll() is None:
            feast_process.terminate()
            try:
                feast_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                feast_process.kill()
                feast_process.wait()
        signal.signal(signal.SIGTERM, previous_sigterm)
        signal.signal(signal.SIGINT, previous_sigint)


def _shutdown_signal(signum: int, frame: Any) -> None:
    raise KeyboardInterrupt(f"Received signal {signum}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Refresh readable hashes for all PostgreSQL borrowers."
    )
    parser.add_argument(
        "--serve",
        action="store_true",
        help="Run Feast serving and the refresh loop under one process supervisor.",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run one complete materialization and mirror refresh, then exit.",
    )
    args = parser.parse_args()

    if args.serve:
        run_managed_service(args.once)
        return

    postgres_url = os.getenv("POSTGRES_URL")
    redis_url = os.getenv("REDIS_URL")
    if not postgres_url:
        raise RuntimeError(
            "POSTGRES_URL must be set for the readable Redis projection."
        )
    if not redis_url:
        raise RuntimeError(
            "REDIS_URL must be set for the readable Redis projection."
        )

    feast_host = os.getenv("FEAST_SERVER_HOST", "feast")
    feast_port = int(os.getenv("FEAST_SERVER_PORT", "6566"))
    wait_for_feast_server(feast_host, feast_port)

    store = FeatureStore(repo_path=os.path.dirname(__file__))
    engine = create_engine(postgres_url, pool_pre_ping=True)
    redis_client = redis.Redis.from_url(redis_url, decode_responses=True)
    try:
        refresh_loop(store, engine, redis_client, args.once)
    finally:
        engine.dispose()
        redis_client.close()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    main()
