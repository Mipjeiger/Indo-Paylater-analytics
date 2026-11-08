from feast.infra.offline_stores.contrib.postgres_offline_store.postgres_source import PostgresSource

raw_data_source = PostgresSource(
    name="paylater_data",
    query="SELECT * FROM paylater.data",
    timestamp_field="date"
)