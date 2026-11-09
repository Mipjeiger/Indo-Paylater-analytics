from typing import Any
import numpy as np
import pandas as pd
from scipy.stats import chisquare, ks_2samp

"""Statistical drift calculations for numerical and categorical features."""

def _validate(reference: pd.Series, current: pd.Series) -> tuple[pd.Series, pd.Series]:
    reference = reference.dropna()
    current = current.dropna()

    if len(reference) < 2 or len(current) < 2:
        raise ValueError("Both drift samples require at least two non-null values")
    return reference, current

def psi(reference: pd.Series, current: pd.Series, bins: int = 10) -> float:
    reference, current = _validate(reference, current)
    edges = np.unique(np.quantile(reference.astype(float), np.linspace(0, 1, bins + 1)))

    if len(edges) < 2:
        return 0.0

    # Calculate the PSI (Population Stability Index) between the reference and current distributions
    expected = np.histogram(reference, bins=edges)[0] / len(reference)
    actual = np.histogram(current, bins=edges)[0] / len(current)
    expected = np.clip(expected, 1e-6, None)
    actual = np.clip(actual, 1e-6, None)

    return float(np.sum((actual - expected) * np.log(actual / expected)))

def detect_drift(
    reference: pd.DataFrame,
    current: pd.DataFrame,
    *,
    psi_threshold: float = 0.2,
    p_value_threshold: float = 0.05,
) -> dict[str, dict[str, Any]]:
    """
    Detect drift between reference and current data.
    """
    report: dict[str, dict[str, Any]] = {}
    for column in sorted(set(reference.columns) & set(current.columns)):
        left, right = _validate(reference[column], current[column])

        # Numerical features: use PSI and KS test
        if pd.api.types.is_numeric_dtype(left):
            score = psi(left, right)
            statistic, p_value = ks_2samp(left, right)
            report[column] = {
                "method": "psi_ks",
                "psi": score,
                "ks_statistic": float(statistic),
                "p_value": float(p_value),
                "drift_detected": score >= psi_threshold or p_value < p_value_threshold,
            }
    
        # Categorical features: use Chi-square test
        else:
            categories = sorted(set(left.astype(str)) | set(right.astype(str)))
            expected = left.astype(str).value_counts().reindex(categories, fill_value=0)
            observed = right.astype(str).value_counts().reindex(categories, fill_value=0)
            statistic, p_value = chisquare(observed + 1, expected + 1)
            report[column] = {
                "method": "chi_square",
                "chi_square": float(statistic),
                "p_value": float(p_value),
                "drift_detected": bool(p_value < p_value_threshold),
            }
    
    return report
