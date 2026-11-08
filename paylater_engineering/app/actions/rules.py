"""Deterministic, environment-configured action rules."""

import json
import os
from typing import Any


def get_rules() -> dict[str, Any]:
    raw = os.getenv("ACTION_RULES_JSON", "{}")
    try:
        rules = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("ACTION_RULES_JSON must contain valid JSON") from exc
    if not isinstance(rules, dict):
        raise ValueError("ACTION_RULES_JSON must contain a JSON object")
    return rules


def evaluate_rules(features: dict[str, Any], rules: dict[str, Any] | None = None) -> list[dict[str, str]]:
    configured = rules if rules is not None else get_rules()
    matches = []
    for code, definition in configured.items():
        field = definition.get("field")
        threshold = definition.get("threshold")
        operator = definition.get("operator", "gte")
        value = features.get(field)
        if value is None:
            continue
        matched = {
            "gte": value >= threshold,
            "gt": value > threshold,
            "lte": value <= threshold,
            "lt": value < threshold,
            "eq": value == threshold,
        }.get(operator)
        if matched is None:
            raise ValueError(f"Unsupported rule operator: {operator}")
        if matched:
            matches.append({"rule_code": code, "reason": str(definition.get("reason", code))})
    return matches
