from __future__ import annotations

import csv
from collections.abc import Callable
from pathlib import Path


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        if reader.fieldnames is None:
            raise ValueError("CSV file is missing headers.")
        return list(reader)


def _validate_required_columns(rows: list[dict[str, str]], required: set[str]) -> None:
    if not rows:
        raise ValueError("Submission file is empty.")

    headers = set(rows[0].keys())
    missing = required - headers
    if missing:
        raise ValueError(f"Submission is missing required columns: {', '.join(sorted(missing))}")


def _float01(value: str, field_name: str) -> float:
    try:
        parsed = float(value)
    except ValueError as exc:
        raise ValueError(f"Invalid numeric value for {field_name}: {value}") from exc
    if parsed < 0.0 or parsed > 1.0:
        raise ValueError(f"{field_name} must be within [0, 1].")
    return parsed


def _nonneg_float(value: str, field_name: str) -> float:
    try:
        parsed = float(value)
    except ValueError as exc:
        raise ValueError(f"Invalid numeric value for {field_name}: {value}") from exc
    if parsed < 0.0:
        raise ValueError(f"{field_name} must be non-negative.")
    return parsed


def _int01(value: str, field_name: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise ValueError(f"Invalid integer value for {field_name}: {value}") from exc
    if parsed not in (0, 1):
        raise ValueError(f"{field_name} must be 0 or 1.")
    return parsed


def _int_range(value: str, field_name: str, lo: int, hi: int) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise ValueError(f"Invalid integer value for {field_name}: {value}") from exc
    if parsed < lo or parsed > hi:
        raise ValueError(f"{field_name} must be within [{lo}, {hi}].")
    return parsed


def _build_unique_int_map(
    rows: list[dict[str, str]],
    *,
    id_column: str,
    value_column: str,
    parser: Callable[[str, str], int],
) -> dict[str, int]:
    mapped: dict[str, int] = {}
    for row in rows:
        identifier = row[id_column]
        if identifier in mapped:
            raise ValueError(f"Duplicate ID found in {id_column}: {identifier}")
        mapped[identifier] = parser(row[value_column], value_column)
    return mapped
