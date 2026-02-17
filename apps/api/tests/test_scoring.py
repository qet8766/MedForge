from __future__ import annotations

from pathlib import Path

import pytest

from app.models import Competition, CompetitionStatus, CompetitionExposure
from app.scoring import (
    _MAP_IOU_THRESHOLDS,
    Box,
    _iou,
    _score_single_image,
    score_submission_file,
    validate_submission_schema,
)


def _write_manifest(
    path: Path,
    *,
    evaluation_split_version: str,
    id_column: str,
    target_columns: list[str],
    expected_row_count: int,
) -> None:
    target_columns_json = ",".join(f'"{column}"' for column in target_columns)
    path.write_text(
        (
            "{"
            f'"evaluation_split_version":"{evaluation_split_version}",'
            '"scoring_mode":"single_realtime_hidden",'
            '"leaderboard_rule":"best_per_user",'
            '"evaluation_policy":"canonical_test_first",'
            f'"id_column":"{id_column}",'
            f'"target_columns":[{target_columns_json}],'
            f'"expected_row_count":{expected_row_count}'
            "}"
        ),
        encoding="utf-8",
    )


def _rsna_competition() -> Competition:
    return Competition(
        slug="rsna-pneumonia-detection",
        title="RSNA",
        description="",
        competition_exposure=CompetitionExposure.EXTERNAL,
        status=CompetitionStatus.ACTIVE,
        is_permanent=True,
        metric="map_iou",
        higher_is_better=True,
        submission_cap_per_day=10,
        dataset_id="00000000-0000-0000-0000-000000000002",
    )


def test_titanic_scoring_deterministic(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.json"
    labels = tmp_path / "labels.csv"
    submission = tmp_path / "submission.csv"

    _write_manifest(
        manifest,
        evaluation_split_version="vdet",
        id_column="PassengerId",
        target_columns=["Survived"],
        expected_row_count=3,
    )
    labels.write_text("PassengerId,Survived\n1,0\n2,1\n3,1\n", encoding="utf-8")
    submission.write_text("PassengerId,Survived\n1,0\n2,1\n3,0\n", encoding="utf-8")

    competition = Competition(
        slug="titanic-survival",
        title="Titanic",
        description="",
        competition_exposure=CompetitionExposure.EXTERNAL,
        status=CompetitionStatus.ACTIVE,
        is_permanent=True,
        metric="accuracy",
        higher_is_better=True,
        submission_cap_per_day=20,
        dataset_id="00000000-0000-0000-0000-000000000001",
    )

    first = score_submission_file(
        competition=competition,
        submission_path=submission,
        labels_path=labels,
        manifest_path=manifest,
    )
    second = score_submission_file(
        competition=competition,
        submission_path=submission,
        labels_path=labels,
        manifest_path=manifest,
    )

    assert first.primary_score == second.primary_score
    assert first.metric_version == "accuracy-v1"
    assert first.evaluation_split_version == "vdet"


# ---------------------------------------------------------------------------
# IoU unit tests
# ---------------------------------------------------------------------------


def test_iou_identical_boxes() -> None:
    box = Box(x=10, y=20, w=100, h=200)
    assert _iou(box, box) == 1.0


def test_iou_no_overlap() -> None:
    a = Box(x=0, y=0, w=10, h=10)
    b = Box(x=100, y=100, w=10, h=10)
    assert _iou(a, b) == 0.0


def test_iou_partial_overlap() -> None:
    # Box A: (0,0)-(10,10) area=100
    # Box B: (5,5)-(15,15) area=100
    # Intersection: (5,5)-(10,10) area=25
    # Union: 100+100-25=175
    # IoU = 25/175 = 1/7
    a = Box(x=0, y=0, w=10, h=10)
    b = Box(x=5, y=5, w=10, h=10)
    expected = 25.0 / 175.0
    assert abs(_iou(a, b) - expected) < 1e-9


# ---------------------------------------------------------------------------
# Single-image scoring tests
# ---------------------------------------------------------------------------


def test_score_negative_image() -> None:
    # Negative image (no GT boxes) always scores 1.0
    assert _score_single_image([], [], _MAP_IOU_THRESHOLDS) == 1.0
    # Even with spurious predictions
    assert _score_single_image([], [Box(0, 0, 10, 10, confidence=0.9)], _MAP_IOU_THRESHOLDS) == 1.0


# ---------------------------------------------------------------------------
# RSNA full-pipeline scoring tests
# ---------------------------------------------------------------------------


def test_rsna_scoring_perfect_match(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.json"
    labels = tmp_path / "labels.csv"
    submission = tmp_path / "submission.csv"

    _write_manifest(
        manifest,
        evaluation_split_version="v2",
        id_column="patientId",
        target_columns=["x", "y", "width", "height", "Target"],
        expected_row_count=2,
    )
    labels.write_text(
        "patientId,x,y,width,height,Target\n"
        "p1,100.0,150.0,200.0,250.0,1\n"
        "p2,,,,,0\n",
        encoding="utf-8",
    )
    # Perfect prediction: exact match for p1, no detection for p2
    submission.write_text(
        "patientId,confidence,x,y,width,height\n"
        "p1,0.99,100.0,150.0,200.0,250.0\n"
        "p2,,,,,\n",
        encoding="utf-8",
    )

    result = score_submission_file(
        competition=_rsna_competition(),
        submission_path=submission,
        labels_path=labels,
        manifest_path=manifest,
    )
    assert result.primary_score == 1.0
    assert result.metric_version == "map_iou-v1"


def test_rsna_scoring_no_predictions(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.json"
    labels = tmp_path / "labels.csv"
    submission = tmp_path / "submission.csv"

    _write_manifest(
        manifest,
        evaluation_split_version="v2",
        id_column="patientId",
        target_columns=["x", "y", "width", "height", "Target"],
        expected_row_count=3,
    )
    labels.write_text(
        "patientId,x,y,width,height,Target\n"
        "p1,100.0,150.0,200.0,250.0,1\n"
        "p2,,,,,0\n"
        "p3,50.0,60.0,150.0,160.0,1\n",
        encoding="utf-8",
    )
    # No detections at all
    submission.write_text(
        "patientId,confidence,x,y,width,height\n"
        "p1,,,,,\n"
        "p2,,,,,\n"
        "p3,,,,,\n",
        encoding="utf-8",
    )

    result = score_submission_file(
        competition=_rsna_competition(),
        submission_path=submission,
        labels_path=labels,
        manifest_path=manifest,
    )
    # p2 (negative) scores 1.0, p1 and p3 (positive, no preds) score 0.0
    # Mean = 1/3
    assert abs(result.primary_score - 1.0 / 3.0) < 1e-9


def test_rsna_scoring_deterministic(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.json"
    labels = tmp_path / "labels.csv"
    submission = tmp_path / "submission.csv"

    _write_manifest(
        manifest,
        evaluation_split_version="v2",
        id_column="patientId",
        target_columns=["x", "y", "width", "height", "Target"],
        expected_row_count=2,
    )
    labels.write_text(
        "patientId,x,y,width,height,Target\n"
        "p1,100.0,150.0,200.0,250.0,1\n"
        "p2,,,,,0\n",
        encoding="utf-8",
    )
    submission.write_text(
        "patientId,confidence,x,y,width,height\n"
        "p1,0.8,90.0,140.0,210.0,260.0\n"
        "p2,,,,,\n",
        encoding="utf-8",
    )

    first = score_submission_file(
        competition=_rsna_competition(),
        submission_path=submission,
        labels_path=labels,
        manifest_path=manifest,
    )
    second = score_submission_file(
        competition=_rsna_competition(),
        submission_path=submission,
        labels_path=labels,
        manifest_path=manifest,
    )

    assert first.primary_score == second.primary_score
    assert first.metric_version == "map_iou-v1"
    assert first.evaluation_split_version == "v2"


# ---------------------------------------------------------------------------
# CIFAR-100 scoring tests
# ---------------------------------------------------------------------------


def _cifar100_competition() -> Competition:
    return Competition(
        slug="cifar-100-classification",
        title="CIFAR-100 Classification",
        description="",
        competition_exposure=CompetitionExposure.EXTERNAL,
        status=CompetitionStatus.ACTIVE,
        is_permanent=True,
        metric="accuracy",
        higher_is_better=True,
        submission_cap_per_day=20,
        dataset_id="00000000-0000-0000-0000-000000000003",
    )


def test_cifar100_scoring_deterministic(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.json"
    labels = tmp_path / "labels.csv"
    submission = tmp_path / "submission.csv"

    _write_manifest(
        manifest,
        evaluation_split_version="cifar100-test",
        id_column="image_id",
        target_columns=["label"],
        expected_row_count=3,
    )
    labels.write_text("image_id,label\n0,42\n1,7\n2,99\n", encoding="utf-8")
    # 2 correct (0 and 2), 1 wrong (1: predicted 50 instead of 7)
    submission.write_text("image_id,label\n0,42\n1,50\n2,99\n", encoding="utf-8")

    first = score_submission_file(
        competition=_cifar100_competition(),
        submission_path=submission,
        labels_path=labels,
        manifest_path=manifest,
    )
    second = score_submission_file(
        competition=_cifar100_competition(),
        submission_path=submission,
        labels_path=labels,
        manifest_path=manifest,
    )

    assert first.primary_score == second.primary_score
    assert abs(first.primary_score - 2.0 / 3.0) < 1e-9
    assert first.metric_version == "accuracy-v1"
    assert first.evaluation_split_version == "cifar100-test"


def test_cifar100_label_out_of_range_rejected(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.json"
    labels = tmp_path / "labels.csv"

    _write_manifest(
        manifest,
        evaluation_split_version="cifar100-test",
        id_column="image_id",
        target_columns=["label"],
        expected_row_count=1,
    )
    labels.write_text("image_id,label\n0,42\n", encoding="utf-8")

    # label = 100 (out of range)
    submission_high = tmp_path / "sub_high.csv"
    submission_high.write_text("image_id,label\n0,100\n", encoding="utf-8")

    with pytest.raises(ValueError, match="label must be within"):
        score_submission_file(
            competition=_cifar100_competition(),
            submission_path=submission_high,
            labels_path=labels,
            manifest_path=manifest,
        )

    # label = -1 (out of range)
    submission_neg = tmp_path / "sub_neg.csv"
    submission_neg.write_text("image_id,label\n0,-1\n", encoding="utf-8")

    with pytest.raises(ValueError, match="label must be within"):
        score_submission_file(
            competition=_cifar100_competition(),
            submission_path=submission_neg,
            labels_path=labels,
            manifest_path=manifest,
        )


def test_titanic_duplicate_passenger_id_rejected(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.json"
    labels = tmp_path / "labels.csv"
    submission = tmp_path / "submission.csv"

    _write_manifest(
        manifest,
        evaluation_split_version="vdet",
        id_column="PassengerId",
        target_columns=["Survived"],
        expected_row_count=3,
    )
    labels.write_text("PassengerId,Survived\n1,0\n2,1\n3,1\n", encoding="utf-8")
    submission.write_text("PassengerId,Survived\n1,0\n1,1\n3,1\n", encoding="utf-8")

    competition = Competition(
        slug="titanic-survival",
        title="Titanic",
        description="",
        competition_exposure=CompetitionExposure.EXTERNAL,
        status=CompetitionStatus.ACTIVE,
        is_permanent=True,
        metric="accuracy",
        higher_is_better=True,
        submission_cap_per_day=20,
        dataset_id="00000000-0000-0000-0000-000000000001",
    )

    with pytest.raises(ValueError, match="Duplicate ID"):
        score_submission_file(
            competition=competition,
            submission_path=submission,
            labels_path=labels,
            manifest_path=manifest,
        )


def test_manifest_expected_row_count_mismatch_rejected(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.json"
    labels = tmp_path / "labels.csv"
    submission = tmp_path / "submission.csv"

    _write_manifest(
        manifest,
        evaluation_split_version="vdet",
        id_column="PassengerId",
        target_columns=["Survived"],
        expected_row_count=4,
    )
    labels.write_text("PassengerId,Survived\n1,0\n2,1\n3,1\n", encoding="utf-8")
    submission.write_text("PassengerId,Survived\n1,0\n2,1\n3,1\n", encoding="utf-8")

    competition = Competition(
        slug="titanic-survival",
        title="Titanic",
        description="",
        competition_exposure=CompetitionExposure.EXTERNAL,
        status=CompetitionStatus.ACTIVE,
        is_permanent=True,
        metric="accuracy",
        higher_is_better=True,
        submission_cap_per_day=20,
        dataset_id="00000000-0000-0000-0000-000000000001",
    )

    with pytest.raises(ValueError, match="Holdout label row count mismatch"):
        score_submission_file(
            competition=competition,
            submission_path=submission,
            labels_path=labels,
            manifest_path=manifest,
        )


def test_manifest_missing_required_fields_rejected(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.json"
    labels = tmp_path / "labels.csv"
    submission = tmp_path / "submission.csv"

    manifest.write_text('{"evaluation_split_version":"vdet"}', encoding="utf-8")
    labels.write_text("PassengerId,Survived\n1,0\n", encoding="utf-8")
    submission.write_text("PassengerId,Survived\n1,0\n", encoding="utf-8")

    competition = Competition(
        slug="titanic-survival",
        title="Titanic",
        description="",
        competition_exposure=CompetitionExposure.EXTERNAL,
        status=CompetitionStatus.ACTIVE,
        is_permanent=True,
        metric="accuracy",
        higher_is_better=True,
        submission_cap_per_day=20,
        dataset_id="00000000-0000-0000-0000-000000000001",
    )

    with pytest.raises(ValueError, match="Manifest keys mismatch"):
        score_submission_file(
            competition=competition,
            submission_path=submission,
            labels_path=labels,
            manifest_path=manifest,
        )


def test_manifest_extra_fields_rejected(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.json"
    labels = tmp_path / "labels.csv"
    submission = tmp_path / "submission.csv"

    manifest.write_text(
        (
            '{"evaluation_split_version":"vdet","scoring_mode":"single_realtime_hidden",'
            '"leaderboard_rule":"best_per_user","evaluation_policy":"canonical_test_first",'
            '"id_column":"PassengerId","target_columns":["Survived"],'
            '"label_source":"legacy-fixture","expected_row_count":1}'
        ),
        encoding="utf-8",
    )
    labels.write_text("PassengerId,Survived\n1,0\n", encoding="utf-8")
    submission.write_text("PassengerId,Survived\n1,0\n", encoding="utf-8")

    competition = Competition(
        slug="titanic-survival",
        title="Titanic",
        description="",
        competition_exposure=CompetitionExposure.EXTERNAL,
        status=CompetitionStatus.ACTIVE,
        is_permanent=True,
        metric="accuracy",
        higher_is_better=True,
        submission_cap_per_day=20,
        dataset_id="00000000-0000-0000-0000-000000000001",
    )

    with pytest.raises(ValueError, match="Manifest keys mismatch"):
        score_submission_file(
            competition=competition,
            submission_path=submission,
            labels_path=labels,
            manifest_path=manifest,
        )


def test_validate_submission_schema_unsupported_slug_rejected(tmp_path: Path) -> None:
    submission = tmp_path / "submission.csv"
    submission.write_text("id,value\n1,1\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Unsupported competition slug"):
        validate_submission_schema("unknown-competition", submission)


def test_validate_submission_schema_detection_partial_bbox_rejected(tmp_path: Path) -> None:
    submission = tmp_path / "submission.csv"
    submission.write_text(
        "patientId,confidence,x,y,width,height\n"
        "p1,0.95,10.0,20.0,,40.0\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="bbox fields must be all-empty"):
        validate_submission_schema("rsna-pneumonia-detection", submission)
