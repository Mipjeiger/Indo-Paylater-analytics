"""Leakage-safe inputs for TWP90 prediction."""

from datetime import timedelta

from feast import FeatureView, Field
from feast.types import Float64, Int64, String

from app.feast.data_sources import paylater_data_source
from app.feast.entities import borrower


twp90_signals = FeatureView(
    name="twp90_signals",
    entities=[borrower],
    ttl=timedelta(days=3650),
    source=paylater_data_source,
    schema=[
        Field(name="age", dtype=Int64),
        Field(name="monthly_income_idr", dtype=Float64),
        Field(name="regional_minimum_wage_umr_idr", dtype=Float64),
        Field(name="num_active_lending_apps", dtype=Int64),
        Field(name="loan_tenor_months", dtype=Int64),
        Field(name="daily_interest_rate_pct", dtype=Float64),
        Field(name="credit_limit_utilization_ratio", dtype=Float64),
        Field(name="debt_service_ratio", dtype=Float64),
        Field(name="disposable_income_after_debt_idr", dtype=Float64),
        Field(name="primary_loan_purpose", dtype=String),
        Field(name="province", dtype=String),
    ],
)
