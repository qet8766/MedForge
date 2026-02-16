from __future__ import annotations

from pathlib import Path

from app.models import Competition, CompetitionStatus, CompetitionTier
from app.scoring import score_submission_file


def test_titanic_scoring_deterministic(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.json"
    labels = tmp_path / "labels.csv"
    submission = tmp_path / "submission.csv"

    manifest.write_text('{"evaluation_split_version":"vdet"}', encoding="utf-8")
    labels.write_text("PassengerId,Survived\n1,0\n2,1\n3,1\n", encoding="utf-8")
    submission.write_text("PassengerId,Survived\n1,0\n2,1\n3,0\n", encoding="utf-8")

    competition = Competition(
        slug="titanic-survival",
        title="Titanic",
        description="",
        competition_tier=CompetitionTier.PUBLIC,
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

    assert first.leaderboard_score == second.leaderboard_score
    assert first.evaluation_split_version == "vdet"
