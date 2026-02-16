from __future__ import annotations

# Per-competition row parsing and validation.
# @filename apps/api/app/scoring/competition_specs.py
from .csv_io import (
    _build_unique_int_map,
    _float01,
    _int01,
    _int_range,
    _nonneg_float,
)
from .types import Box


def _validate_titanic_row(row: dict[str, str]) -> None:
    _int01(row["Survived"], "Survived")


def _parse_titanic_rows(rows: list[dict[str, str]]) -> dict[str, int]:
    return _build_unique_int_map(
        rows,
        id_column="PassengerId",
        value_column="Survived",
        parser=_int01,
    )


def _validate_cifar_row(row: dict[str, str]) -> None:
    _int_range(row["label"], "label", 0, 99)


def _parse_cifar_rows(rows: list[dict[str, str]]) -> dict[str, int]:
    return _build_unique_int_map(
        rows,
        id_column="image_id",
        value_column="label",
        parser=lambda value, _: _int_range(value, "label", 0, 99),
    )


def _validate_detection_row(row: dict[str, str]) -> None:
    bbox_fields = ["confidence", "x", "y", "width", "height"]
    values = [row.get(field, "").strip() for field in bbox_fields]
    all_empty = all(value == "" for value in values)
    all_present = all(value != "" for value in values)

    if not all_empty and not all_present:
        raise ValueError(
            f"Detection row for {row.get('patientId', '?')}: "
            "bbox fields must be all-empty (no detection) or all-present."
        )

    if all_present:
        _float01(row["confidence"], "confidence")
        _nonneg_float(row["x"], "x")
        _nonneg_float(row["y"], "y")
        _nonneg_float(row["width"], "width")
        _nonneg_float(row["height"], "height")


def _parse_detection_labels(rows: list[dict[str, str]]) -> dict[str, list[Box]]:
    result: dict[str, list[Box]] = {}
    for row in rows:
        patient_id = row["patientId"]
        result.setdefault(patient_id, [])
        if row.get("Target", "") == "1":
            result[patient_id].append(
                Box(
                    x=float(row["x"]),
                    y=float(row["y"]),
                    w=float(row["width"]),
                    h=float(row["height"]),
                )
            )
    return result


def _parse_detection_submission(rows: list[dict[str, str]]) -> dict[str, list[Box]]:
    result: dict[str, list[Box]] = {}
    for row in rows:
        patient_id = row["patientId"]
        result.setdefault(patient_id, [])
        confidence = row.get("confidence", "").strip()
        if confidence:
            result[patient_id].append(
                Box(
                    x=float(row["x"]),
                    y=float(row["y"]),
                    w=float(row["width"]),
                    h=float(row["height"]),
                    confidence=float(confidence),
                )
            )
    return result
