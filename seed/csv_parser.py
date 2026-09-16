"""Utility: robust CSV parsing with schema validation.

Common pattern used across data-engineering projects to load
tabular source files with consistent error handling and type coercion.
"""
from __future__ import annotations

import csv
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def parse_csv(
    path: str | Path,
    required_columns: list[str] | None = None,
    delimiter: str = ",",
    encoding: str = "utf-8-sig",
) -> list[dict[str, Any]]:
    """Parse a CSV file and return a list of row dicts.

    Args:
        path: Path to the CSV file.
        required_columns: If provided, raises ValueError when any column is absent.
        delimiter: Field delimiter (default comma).
        encoding: File encoding; utf-8-sig strips the BOM on Windows exports.

    Returns:
        List of row dicts keyed by the header row.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If required columns are missing from the header.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"CSV not found: {path}")

    with path.open(encoding=encoding, newline="") as fh:
        reader = csv.DictReader(fh, delimiter=delimiter)
        fieldnames = reader.fieldnames or []

        if required_columns:
            missing = set(required_columns) - set(fieldnames)
            if missing:
                raise ValueError(f"Missing required columns: {sorted(missing)}")

        rows = list(reader)

    logger.debug("Parsed %d rows from %s", len(rows), path)
    return rows


def parse_csv_typed(
    path: str | Path,
    schema: dict[str, type],
    **kwargs: Any,
) -> list[dict[str, Any]]:
    """Parse CSV and coerce columns to the types defined in schema.

    schema example: {"id": int, "amount": float, "active": bool}
    Rows that fail coercion are skipped with a warning.
    """
    _BOOL_TRUE = {"true", "1", "yes", "y"}

    rows = parse_csv(path, required_columns=list(schema), **kwargs)
    typed: list[dict[str, Any]] = []

    for i, row in enumerate(rows):
        try:
            coerced: dict[str, Any] = {}
            for col, cast in schema.items():
                raw = row[col].strip()
                if cast is bool:
                    coerced[col] = raw.lower() in _BOOL_TRUE
                else:
                    coerced[col] = cast(raw)
            # Keep columns not in schema as-is
            for col in row:
                if col not in coerced:
                    coerced[col] = row[col]
            typed.append(coerced)
        except (ValueError, KeyError) as exc:
            logger.warning("Skipping row %d due to type coercion error: %s", i, exc)

    return typed
