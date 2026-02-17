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


def _decode_rle_mask(rle_mask: str, *, field: str) -> set[int]:
    value = rle_mask.strip()
    if not value:
        return set()

    tokens = value.split()
    if len(tokens) % 2 != 0:
        raise ValueError(f"{field} must contain an even number of start/length tokens.")

    pixels: set[int] = set()
    for i in range(0, len(tokens), 2):
        try:
            start = int(tokens[i])
            length = int(tokens[i + 1])
        except ValueError as exc:
            raise ValueError(f"{field} must contain integer start/length tokens.") from exc
        if start < 1:
            raise ValueError(f"{field} run start must be >= 1.")
        if length < 1:
            raise ValueError(f"{field} run length must be >= 1.")
        run_start = start - 1
        run_end = run_start + length
        pixels.update(range(run_start, run_end))
    return pixels


def _validate_segmentation_row(row: dict[str, str]) -> None:
    image_id = row.get("image_id", "").strip()
    if not image_id:
        raise ValueError("image_id is required.")
    _decode_rle_mask(row.get("rle_mask", ""), field="rle_mask")


def _parse_segmentation_rows(rows: list[dict[str, str]]) -> dict[str, set[int]]:
    parsed: dict[str, set[int]] = {}
    for row in rows:
        image_id = row["image_id"].strip()
        if image_id in parsed:
            raise ValueError(f"Duplicate image_id in submission: {image_id}")
        parsed[image_id] = _decode_rle_mask(row.get("rle_mask", ""), field="rle_mask")
    return parsed
