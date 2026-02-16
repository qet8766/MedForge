from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from app.competition_policy import (
    LEADERBOARD_RULE_BEST_PER_USER,
    SCORING_MODE_SINGLE_REALTIME_HIDDEN,
    SUPPORTED_EVALUATION_POLICIES,
    SUPPORTED_LEADERBOARD_RULES,
    SUPPORTED_SCORING_MODES,
)
from app.models import Competition

SCORER_VERSION = "alpha-v1"

_MAP_IOU_THRESHOLDS = [0.4, 0.45, 0.5, 0.55, 0.6, 0.65, 0.7, 0.75]


@dataclass(frozen=True)
class ScoreResult:
    leaderboard_score: float
    evaluation_split_version: str


@dataclass(frozen=True)
class ManifestMetadata:
    evaluation_split_version: str
    scoring_mode: str
    leaderboard_rule: str
    evaluation_policy: str
    id_column: str
    target_columns: tuple[str, ...]
    label_source: str
    expected_row_count: int


@dataclass(frozen=True)
class Box:
    x: float
    y: float
    w: float
    h: float
    confidence: float = 0.0


def _manifest_str(payload: dict[str, Any], field: str) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Manifest field '{field}' must be a non-empty string.")
    return value.strip()


def _manifest_target_columns(payload: dict[str, Any]) -> tuple[str, ...]:
    value = payload.get("target_columns")
    if not isinstance(value, list) or not value:
        raise ValueError("Manifest field 'target_columns' must be a non-empty list.")

    normalized: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ValueError("Manifest field 'target_columns' contains an invalid column.")
        normalized.append(item.strip())
    return tuple(normalized)


def _manifest_expected_row_count(payload: dict[str, Any]) -> int:
    value = payload.get("expected_row_count")
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError("Manifest field 'expected_row_count' must be a positive integer.")
    return value


def _load_manifest(manifest_path: Path) -> ManifestMetadata:
    if not manifest_path.exists():
        raise ValueError(f"Manifest file is missing: {manifest_path}")

    with manifest_path.open("r", encoding="utf-8") as file:
        payload = json.load(file)

    if not isinstance(payload, dict):
        raise ValueError("Invalid manifest format.")

    evaluation_split_version = _manifest_str(payload, "evaluation_split_version")
    scoring_mode = _manifest_str(payload, "scoring_mode")
    leaderboard_rule = _manifest_str(payload, "leaderboard_rule")
    evaluation_policy = _manifest_str(payload, "evaluation_policy")
    id_column = _manifest_str(payload, "id_column")
    target_columns = _manifest_target_columns(payload)
    label_source = _manifest_str(payload, "label_source")
    expected_row_count = _manifest_expected_row_count(payload)

    if scoring_mode not in SUPPORTED_SCORING_MODES:
        raise ValueError(f"Unsupported manifest scoring_mode: {scoring_mode}")
    if leaderboard_rule not in SUPPORTED_LEADERBOARD_RULES:
        raise ValueError(f"Unsupported manifest leaderboard_rule: {leaderboard_rule}")
    if evaluation_policy not in SUPPORTED_EVALUATION_POLICIES:
        raise ValueError(f"Unsupported manifest evaluation_policy: {evaluation_policy}")

    return ManifestMetadata(
        evaluation_split_version=evaluation_split_version,
        scoring_mode=scoring_mode,
        leaderboard_rule=leaderboard_rule,
        evaluation_policy=evaluation_policy,
        id_column=id_column,
        target_columns=target_columns,
        label_source=label_source,
        expected_row_count=expected_row_count,
    )


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


def _compute_accuracy(labels: dict[str, int], preds: dict[str, int]) -> float:
    keys = set(labels.keys())
    if keys != set(preds.keys()):
        raise ValueError("Submission IDs do not match expected evaluation IDs.")

    total = len(keys)
    correct = sum(1 for key in keys if labels[key] == preds[key])
    return correct / total if total else 0.0


def _validate_manifest_contract(
    manifest: ManifestMetadata,
    *,
    expected_id_column: str,
    expected_target_columns: tuple[str, ...],
) -> None:
    if manifest.id_column != expected_id_column:
        raise ValueError(
            f"Manifest id_column mismatch: expected {expected_id_column}, got {manifest.id_column}"
        )
    if tuple(manifest.target_columns) != expected_target_columns:
        raise ValueError(
            "Manifest target_columns mismatch: "
            f"expected {list(expected_target_columns)}, got {list(manifest.target_columns)}"
        )
    if manifest.scoring_mode != SCORING_MODE_SINGLE_REALTIME_HIDDEN:
        raise ValueError(
            "Manifest scoring_mode must be "
            f"'{SCORING_MODE_SINGLE_REALTIME_HIDDEN}'."
        )
    if manifest.leaderboard_rule != LEADERBOARD_RULE_BEST_PER_USER:
        raise ValueError(
            "Manifest leaderboard_rule must be "
            f"'{LEADERBOARD_RULE_BEST_PER_USER}'."
        )


def _validate_label_row_count(label_rows: list[dict[str, str]], manifest: ManifestMetadata) -> None:
    if len(label_rows) != manifest.expected_row_count:
        raise ValueError(
            "Holdout label row count mismatch: "
            f"expected {manifest.expected_row_count}, got {len(label_rows)}."
        )


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


# ---------------------------------------------------------------------------
# Object-detection scoring (mAP @ IoU)
# ---------------------------------------------------------------------------


def _iou(a: Box, b: Box) -> float:
    x1 = max(a.x, b.x)
    y1 = max(a.y, b.y)
    x2 = min(a.x + a.w, b.x + b.w)
    y2 = min(a.y + a.h, b.y + b.h)

    inter_w = max(0.0, x2 - x1)
    inter_h = max(0.0, y2 - y1)
    inter_area = inter_w * inter_h

    area_a = a.w * a.h
    area_b = b.w * b.h
    union_area = area_a + area_b - inter_area

    if union_area <= 0.0:
        return 0.0
    return inter_area / union_area


def _score_single_image(
    gt_boxes: list[Box],
    pred_boxes: list[Box],
    iou_thresholds: list[float],
) -> float:
    # Negative image (no GT boxes) → always 1.0 per Kaggle RSNA rules
    if not gt_boxes:
        return 1.0

    sorted_preds = sorted(pred_boxes, key=lambda b: b.confidence, reverse=True)

    threshold_precisions: list[float] = []
    for threshold in iou_thresholds:
        matched_gt: set[int] = set()
        tp = 0
        fp = 0

        for pred in sorted_preds:
            best_iou = 0.0
            best_gt_idx = -1
            for gt_idx, gt in enumerate(gt_boxes):
                if gt_idx in matched_gt:
                    continue
                current_iou = _iou(pred, gt)
                if current_iou > best_iou:
                    best_iou = current_iou
                    best_gt_idx = gt_idx

            if best_iou >= threshold and best_gt_idx >= 0:
                tp += 1
                matched_gt.add(best_gt_idx)
            else:
                fp += 1

        fn = len(gt_boxes) - tp
        precision = tp / (tp + fp + fn) if (tp + fp + fn) > 0 else 0.0
        threshold_precisions.append(precision)

    return sum(threshold_precisions) / len(threshold_precisions)


def _compute_map_iou(
    labels: dict[str, list[Box]],
    preds: dict[str, list[Box]],
) -> float:
    if set(labels.keys()) != set(preds.keys()):
        raise ValueError("Submission patient IDs do not match expected evaluation IDs.")

    image_scores: list[float] = []
    for patient_id in labels:
        gt_boxes = labels[patient_id]
        pred_boxes = preds[patient_id]
        image_scores.append(
            _score_single_image(gt_boxes, pred_boxes, _MAP_IOU_THRESHOLDS)
        )

    return sum(image_scores) / len(image_scores) if image_scores else 0.0


def _parse_detection_labels(rows: list[dict[str, str]]) -> dict[str, list[Box]]:
    result: dict[str, list[Box]] = {}
    for row in rows:
        pid = row["patientId"]
        if pid not in result:
            result[pid] = []
        target = row.get("Target", "")
        if target == "1":
            result[pid].append(Box(
                x=float(row["x"]),
                y=float(row["y"]),
                w=float(row["width"]),
                h=float(row["height"]),
            ))
        # Target == 0 → negative image, leave box list empty
    return result


def _parse_detection_submission(rows: list[dict[str, str]]) -> dict[str, list[Box]]:
    result: dict[str, list[Box]] = {}
    for row in rows:
        pid = row["patientId"]
        if pid not in result:
            result[pid] = []
        conf_str = row.get("confidence", "").strip()
        if conf_str:
            result[pid].append(Box(
                x=float(row["x"]),
                y=float(row["y"]),
                w=float(row["width"]),
                h=float(row["height"]),
                confidence=float(conf_str),
            ))
        # Empty confidence → no detection for this row
    return result


def _validate_detection_row(row: dict[str, str]) -> None:
    bbox_fields = ["confidence", "x", "y", "width", "height"]
    values = [row.get(f, "").strip() for f in bbox_fields]
    all_empty = all(v == "" for v in values)
    all_present = all(v != "" for v in values)

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


def validate_submission_schema(competition_slug: str, submission_path: Path) -> None:
    rows = _read_csv_rows(submission_path)

    if competition_slug == "titanic-survival":
        _validate_required_columns(rows, {"PassengerId", "Survived"})
        for row in rows:
            _int01(row["Survived"], "Survived")
    elif competition_slug == "rsna-pneumonia-detection":
        _validate_required_columns(rows, {"patientId", "confidence", "x", "y", "width", "height"})
        for row in rows:
            _validate_detection_row(row)
    elif competition_slug == "cifar-100-classification":
        _validate_required_columns(rows, {"image_id", "label"})
        for row in rows:
            _int_range(row["label"], "label", 0, 99)
    else:
        raise ValueError(f"Unsupported competition slug: {competition_slug}")


def score_submission_file(
    *,
    competition: Competition,
    submission_path: Path,
    labels_path: Path,
    manifest_path: Path,
) -> ScoreResult:
    submission_rows = _read_csv_rows(submission_path)
    label_rows = _read_csv_rows(labels_path)

    manifest = _load_manifest(manifest_path)
    split_version = manifest.evaluation_split_version
    _validate_label_row_count(label_rows, manifest)

    if competition.slug == "titanic-survival":
        _validate_required_columns(submission_rows, {"PassengerId", "Survived"})
        _validate_required_columns(label_rows, {"PassengerId", "Survived"})
        _validate_manifest_contract(
            manifest,
            expected_id_column="PassengerId",
            expected_target_columns=("Survived",),
        )

        titanic_labels = _build_unique_int_map(
            label_rows,
            id_column="PassengerId",
            value_column="Survived",
            parser=_int01,
        )
        titanic_predictions = _build_unique_int_map(
            submission_rows,
            id_column="PassengerId",
            value_column="Survived",
            parser=_int01,
        )
        score = _compute_accuracy(titanic_labels, titanic_predictions)

    elif competition.slug == "rsna-pneumonia-detection":
        _validate_required_columns(
            submission_rows, {"patientId", "confidence", "x", "y", "width", "height"}
        )
        _validate_required_columns(
            label_rows, {"patientId", "x", "y", "width", "height", "Target"}
        )
        _validate_manifest_contract(
            manifest,
            expected_id_column="patientId",
            expected_target_columns=("x", "y", "width", "height", "Target"),
        )

        rsna_labels = _parse_detection_labels(label_rows)
        rsna_preds = _parse_detection_submission(submission_rows)
        score = _compute_map_iou(rsna_labels, rsna_preds)

    elif competition.slug == "cifar-100-classification":
        _validate_required_columns(submission_rows, {"image_id", "label"})
        _validate_required_columns(label_rows, {"image_id", "label"})
        _validate_manifest_contract(
            manifest,
            expected_id_column="image_id",
            expected_target_columns=("label",),
        )

        cifar_labels = _build_unique_int_map(
            label_rows,
            id_column="image_id",
            value_column="label",
            parser=lambda value, _: _int_range(value, "label", 0, 99),
        )
        cifar_preds = _build_unique_int_map(
            submission_rows,
            id_column="image_id",
            value_column="label",
            parser=lambda value, _: _int_range(value, "label", 0, 99),
        )
        score = _compute_accuracy(cifar_labels, cifar_preds)

    else:
        raise ValueError(f"Unsupported competition slug: {competition.slug}")

    return ScoreResult(leaderboard_score=score, evaluation_split_version=split_version)
