from feast import Entity
from feast.value_type import ValueType

"""Feast entities for PayLater feature retrieval."""

borrower = Entity(
    name="borrower",
    join_keys=["borrower_id"],
    value_type=ValueType.STRING,
    description="Stable borrower identifier from paylater.data.borrower_id.",
)
