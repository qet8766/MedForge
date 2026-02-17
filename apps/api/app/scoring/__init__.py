from __future__ import annotations

# Scoring facade exports.
# @filename apps/api/app/scoring/pipeline.py
# @filename apps/api/app/scoring/metrics.py
# @filename apps/api/app/scoring/types.py
from .metrics import _MAP_IOU_THRESHOLDS, _iou, _score_single_image
from .pipeline import score_submission_file, validate_submission_schema
from .types import Box

SCORER_VERSION = "v2-score-runs"

__all__ = [
    "SCORER_VERSION",
    "_MAP_IOU_THRESHOLDS",
    "Box",
    "_iou",
    "_score_single_image",
    "score_submission_file",
    "validate_submission_schema",
]
