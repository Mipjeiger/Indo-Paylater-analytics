"""Reusable feature retrieval helpers."""

from collections.abc import Iterable
from typing import Any

import pandas as pd


LEAKAGE_COLUMNS = frozenset(
    {
        "confidence_score",
        "risk_score",
        "risk_short",
        "is_high_risk",
        "distress_bin",
        "cot_financial_psychology_rationale",
        "twp90_default_status",
        "primary_default_root_cause",
        "days_past_due",
        "total_loan_outstanding_idr",
    }
)

def sanitize_features(
    features: pd.DataFrame,
    *,
    excluded: Iterable[str] = (),
) -> pd.DataFrame:
    """Return a copy with target and explicitly excluded leakage columns removed."""
    excluded_columns = LEAKAGE_COLUMNS | set(excluded)
    return features.drop(
        columns=[column for column in features.columns if column in excluded_columns],
        errors="ignore",
    )

def retrieve_features(
    store: Any,
    borrower_ids: Iterable[str],
    feature_refs: list[str],
) -> pd.DataFrame:
    """Retrieve online features for borrower IDs with explicit error propagation."""
    ids = list(borrower_ids) 
    if not ids:
        raise ValueError("borrower_ids must contain at least one borrower ID")
    if not feature_refs:
        raise ValueError("feature_refs must contain at least one feature reference")
    
    try:
        result = store.get_online_features(
            features=feature_refs,
            entity_rows=[{"borrower_id": borrower_id} for borrower_id in ids],
        )
        return result.to_df()
    
    except Exception as exc:
        raise RuntimeError("Feast feature retrieval failed") from exc
