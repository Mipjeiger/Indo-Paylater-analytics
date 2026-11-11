"""Feast entities for PayLater feature retrieval."""

from feast import Entity

borrower = Entity(
    name="borrower",
    join_keys=["borrower_id"],
    description="Stable borrower identifier from paylater.data.borrower_id.",
)
