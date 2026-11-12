from feast.infra.offline_stores.contrib.postgres_offline_store.postgres_source import PostgreSQLSource

"""Feast data sources backed by the PayLater PostgreSQL database."""

paylater_data_source = PostgreSQLSource(
    name="paylater_data",
    query=(
        "SELECT *, COALESCE(updated_at, created_at) AS event_timestamp "
        "FROM paylater.database"
    ),
    timestamp_field="event_timestamp",
    created_timestamp_column="created_at",
)
