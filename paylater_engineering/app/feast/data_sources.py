"""Feast data sources backed by the PayLater PostgreSQL database."""

import os

from feast import SQLSource


paylater_data_source = SQLSource(
    name="paylater_data",
    query=(
        "SELECT *, COALESCE(updated_at, created_at) AS event_timestamp "
        "FROM paylater.data"
    ),
    endpoint=os.getenv("POSTGRES_URL"),
    timestamp_field="event_timestamp",
    created_timestamp_column="created_at",
)
