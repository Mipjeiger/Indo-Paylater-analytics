from datetime import timedelta

from feast import FeatureView, Field
from feast.types import Float64

from app.feast.data_sources import paylater_data_source
from app.feast.entities import borrower

"""Derived ratios that are safe to compute from source observations."""

engineered_ratios = FeatureView(
    name="engineered_ratios",
    entities=[borrower],
    ttl=timedelta(days=3650),
    source=paylater_data_source,
    schema=[
        Field(name="income_to_umr_ratio", dtype=Float64),
        Field(name="credit_limit_utilization_ratio", dtype=Float64),
        Field(name="debt_service_ratio", dtype=Float64),
    ],
)
