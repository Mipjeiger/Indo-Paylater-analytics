from datetime import timedelta

from feast import FeatureView, Field
from feast.types import Float64, Int64, String

from app.feast.data_sources import paylater_data_source
from app.feast.entities import borrower

"""Borrower demographic and income features."""

borrower_profile = FeatureView(
    name="borrower_profile",
    entities=[borrower],
    ttl=timedelta(days=3650),
    source=paylater_data_source,
    schema=[
        Field(name="age", dtype=Int64),
        Field(name="gender", dtype=String),
        Field(name="province", dtype=String),
        Field(name="education_level", dtype=String),
        Field(name="employment_status", dtype=String),
        Field(name="monthly_income_idr", dtype=Float64),
        Field(name="regional_minimum_wage_umr_idr", dtype=Float64),
        Field(name="num_active_lending_apps", dtype=Int64),
        Field(name="income_to_umr_ratio", dtype=Float64),
    ],
)
