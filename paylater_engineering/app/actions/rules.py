import json
import os
from typing import Any
from datetime import date

"""Deterministic, environment-configured action rules."""

def get_rules() -> dict[str, Any]:
    raw = os.getenv("ACTION_RULES_JSON", "{}")
    try:
        rules = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("ACTION_RULES_JSON must contain valid JSON") from exc

    if not isinstance(rules, dict):
        raise ValueError("ACTION_RULES_JSON must contain a JSON object")
    return rules

def evaluate_rules(
    borrower_id: str,
    features: dict[str, Any],
    rules: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Return matched rules as dicts with rule_code, reason, idempotency_key."""
    configured = rules if rules is not None else get_rules()
    matches = []
    for code, definition in configured.items():
        field = definition.get("field")
        threshold = definition.get("threshold")
        operator = definition.get("operator", "gte")
        value = features.get(field)

        if value is None:
            continue  # Skip if feature is missing

        # Matched rule based on operator
        matched = {
            "gte": value >= threshold,
            "gt": value > threshold,
            "lte": value <= threshold,
            "lt": value < threshold,
            "eq": value == threshold,
        }.get(operator)

        if matched is None:
            raise ValueError(f"Unsupported operator '{operator}' in rule '{code}'")
        if matched:
            # Append matched rule with idempotency key
            matches.append(
                {
                    "rule_code": code,
                    "reason": str(definition.get("reason", code)),
                    "idempotency_key": (
                        f"{borrower_id}:block:{code}:{date.today().isoformat()}"
                    )
                }
            )
   
    return matches