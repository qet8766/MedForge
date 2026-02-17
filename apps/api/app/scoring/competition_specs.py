from __future__ import annotations

# Competition registry for scoring.
# @filename apps/api/app/scoring/competition_parsers.py
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from .competition_parsers import (
    _parse_cifar_rows,
    _parse_detection_labels,
    _parse_detection_submission,
    _parse_segmentation_rows,
    _parse_titanic_rows,
    _validate_cifar_row,
    _validate_detection_row,
    _validate_segmentation_row,
    _validate_titanic_row,
)
from .csv_io import _validate_required_columns
from .metrics import _compute_accuracy, _compute_map_iou, _compute_mean_iou

ParsedPayload = Any
RowValidator = Callable[[dict[str, str]], None]
RowsParser = Callable[[list[dict[str, str]]], ParsedPayload]
ScoreFn = Callable[[ParsedPayload, ParsedPayload], float]


@dataclass(frozen=True)
class CompetitionSpec:
    slug: str
    metric: str
    metric_version: str
    submission_required_columns: tuple[str, ...]
    label_required_columns: tuple[str, ...]
    manifest_id_column: str
    manifest_target_columns: tuple[str, ...]
    validate_submission_row: RowValidator
    parse_labels: RowsParser
    parse_submission: RowsParser
    score_fn: ScoreFn

    def validate_submission_rows(self, rows: list[dict[str, str]]) -> None:
        _validate_required_columns(rows, set(self.submission_required_columns))
        for row in rows:
            self.validate_submission_row(row)

    def validate_label_columns(self, rows: list[dict[str, str]]) -> None:
        _validate_required_columns(rows, set(self.label_required_columns))


_COMPETITION_SPECS: dict[str, CompetitionSpec] = {
    "titanic-survival": CompetitionSpec(
        slug="titanic-survival",
        metric="accuracy",
        metric_version="accuracy-v1",
        submission_required_columns=("PassengerId", "Survived"),
        label_required_columns=("PassengerId", "Survived"),
        manifest_id_column="PassengerId",
        manifest_target_columns=("Survived",),
        validate_submission_row=_validate_titanic_row,
        parse_labels=_parse_titanic_rows,
        parse_submission=_parse_titanic_rows,
        score_fn=_compute_accuracy,
    ),
    "rsna-pneumonia-detection": CompetitionSpec(
        slug="rsna-pneumonia-detection",
        metric="map_iou",
        metric_version="map_iou-v1",
        submission_required_columns=("patientId", "confidence", "x", "y", "width", "height"),
        label_required_columns=("patientId", "x", "y", "width", "height", "Target"),
        manifest_id_column="patientId",
        manifest_target_columns=("x", "y", "width", "height", "Target"),
        validate_submission_row=_validate_detection_row,
        parse_labels=_parse_detection_labels,
        parse_submission=_parse_detection_submission,
        score_fn=_compute_map_iou,
    ),
    "cifar-100-classification": CompetitionSpec(
        slug="cifar-100-classification",
        metric="accuracy",
        metric_version="accuracy-v1",
        submission_required_columns=("image_id", "label"),
        label_required_columns=("image_id", "label"),
        manifest_id_column="image_id",
        manifest_target_columns=("label",),
        validate_submission_row=_validate_cifar_row,
        parse_labels=_parse_cifar_rows,
        parse_submission=_parse_cifar_rows,
        score_fn=_compute_accuracy,
    ),
    "oxford-pet-segmentation": CompetitionSpec(
        slug="oxford-pet-segmentation",
        metric="mean_iou",
        metric_version="mean_iou-v1",
        submission_required_columns=("image_id", "rle_mask"),
        label_required_columns=("image_id", "rle_mask"),
        manifest_id_column="image_id",
        manifest_target_columns=("rle_mask",),
        validate_submission_row=_validate_segmentation_row,
        parse_labels=_parse_segmentation_rows,
        parse_submission=_parse_segmentation_rows,
        score_fn=_compute_mean_iou,
    ),
}


def get_competition_spec(slug: str) -> CompetitionSpec:
    spec = _COMPETITION_SPECS.get(slug)
    if spec is None:
        raise ValueError(f"Unsupported competition slug: {slug}")
    return spec
