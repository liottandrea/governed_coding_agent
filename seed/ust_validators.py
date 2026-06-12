"""UST utility: reusable data validation helpers.

Used across UST ingestion pipelines and API layers to validate
incoming data with consistent error messages and field-level reporting.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ValidationResult:
    """Holds field-level validation errors; truthy when there are no errors."""

    errors: dict[str, list[str]] = field(default_factory=dict)

    def add(self, field_name: str, message: str) -> None:
        """Record a validation error for field_name."""
        self.errors.setdefault(field_name, []).append(message)

    def __bool__(self) -> bool:
        return not self.errors

    def as_text(self) -> str:
        lines = []
        for fname, msgs in self.errors.items():
            for msg in msgs:
                lines.append(f"  {fname}: {msg}")
        return "\n".join(lines)


def validate_email(value: str) -> bool:
    """Return True if value looks like a valid e-mail address."""
    pattern = r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, value.strip()))


def validate_non_empty(value: Any) -> bool:
    """Return True if value is not None and not an empty string/collection."""
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip() != ""
    try:
        return len(value) > 0
    except TypeError:
        return True


def validate_range(value: float | int, min_val: float, max_val: float) -> bool:
    """Return True if min_val <= value <= max_val."""
    return min_val <= value <= max_val


def validate_record(
    record: dict[str, Any],
    rules: dict[str, list[str]],
) -> ValidationResult:
    """Validate a dict against a set of named rules.

    rules example:
        {"email": ["non_empty", "email"], "age": ["non_empty"]}

    Supported rule names: "non_empty", "email".
    Unknown rule names are ignored with a warning.
    """
    result = ValidationResult()
    _validators = {
        "non_empty": validate_non_empty,
        "email": validate_email,
    }

    for fname, rule_names in rules.items():
        value = record.get(fname)
        for rule_name in rule_names:
            fn = _validators.get(rule_name)
            if fn is None:
                continue
            if not fn(value):
                result.add(fname, f"failed rule '{rule_name}'")

    return result
