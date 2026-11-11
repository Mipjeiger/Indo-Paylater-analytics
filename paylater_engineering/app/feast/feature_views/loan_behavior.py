"""Loan behavior features available to downstream models."""

from datetime import timedelta

from feast import FeatureView, Field
from feast.types import Float64, Int64

from app.feast.data_sources import paylater_data_source
from app.feast.entities import borrower

loan_behavior = FeatureView(
    name="loan_behavior",
    entities=[borrower],
    ttl=timedelta(days=3650),
    source=paylater_data_source,
    schema=[
        Field(name="credit_limit_granted_idr", dtype=Float64),
        Field(name="loan_tenor_months", dtype=Int64),
        Field(name="daily_interest_rate_pct", dtype=Float64),
        Field(name="credit_limit_utilization_ratio", dtype=Float64),
        Field(name="monthly_installment_estimate_idr", dtype=Float64),
        Field(name="debt_service_ratio", dtype=Float64),
        Field(name="disposable_income_after_debt_idr", dtype=Float64),
    ],
)
