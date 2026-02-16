from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path

from app.models import Competition

SCORER_VERSION = "alpha-v1"


@dataclass(frozen=True)
class ScoreResult:
    leaderboard_score: float
    evaluation_split_version: str


def _load_manifest(manifest_path: Path) -> dict[str, str]:
    if not manifest_path.exists():
        return {"evaluation_split_version": "v1"}

    with manifest_path.open("r", encoding="utf-8") as file:
        payload = json.load(file)

    if not isinstance(payload, dict):
        raise ValueError("Invalid manifest format.")

    split = str(payload.get("evaluation_split_version", "v1"))
    return {"evaluation_split_version": split}


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


def _int01(value: str, field_name: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise ValueError(f"Invalid integer value for {field_name}: {value}") from exc
    if parsed not in (0, 1):
        raise ValueError(f"{field_name} must be 0 or 1.")
    return parsed


def _compute_accuracy(labels: dict[str, int], preds: dict[str, int]) -> float:
    keys = set(labels.keys())
    if keys != set(preds.keys()):
        raise ValueError("Submission IDs do not match expected evaluation IDs.")

    total = len(keys)
    correct = sum(1 for key in keys if labels[key] == preds[key])
    return correct / total if total else 0.0


def _compute_binary_auc(labels: dict[str, int], scores: dict[str, float]) -> float:
    keys = set(labels.keys())
    if keys != set(scores.keys()):
        raise ValueError("Submission IDs do not match expected evaluation IDs.")

    paired = [(scores[key], labels[key]) for key in keys]
    positives = sum(label for _, label in paired)
    negatives = len(paired) - positives

    if positives == 0 or negatives == 0:
        raise ValueError("AUC is undefined when only one class is present.")

    paired.sort(key=lambda item: item[0])

    sum_pos_ranks = 0.0
    rank = 1
    index = 0
    while index < len(paired):
        end = index
        while end < len(paired) and paired[end][0] == paired[index][0]:
            end += 1

        tie_count = end - index
        avg_rank = (rank + (rank + tie_count - 1)) / 2.0
        positives_in_tie = sum(label for _, label in paired[index:end])
        sum_pos_ranks += positives_in_tie * avg_rank

        rank += tie_count
        index = end

    auc = (sum_pos_ranks - (positives * (positives + 1) / 2.0)) / (positives * negatives)
    return auc


def validate_submission_schema(competition_slug: str, submission_path: Path) -> None:
    rows = _read_csv_rows(submission_path)

    if competition_slug == "titanic-survival":
        _validate_required_columns(rows, {"PassengerId", "Survived"})
        for row in rows:
            _int01(row["Survived"], "Survived")
    elif competition_slug == "rsna-pneumonia-detection":
        _validate_required_columns(rows, {"patientId", "Target"})
        for row in rows:
            _float01(row["Target"], "Target")
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
    split_version = manifest["evaluation_split_version"]

    if competition.slug == "titanic-survival":
        _validate_required_columns(submission_rows, {"PassengerId", "Survived"})
        _validate_required_columns(label_rows, {"PassengerId", "Survived"})

        titanic_labels = {row["PassengerId"]: _int01(row["Survived"], "Survived") for row in label_rows}
        titanic_predictions = {
            row["PassengerId"]: _int01(row["Survived"], "Survived") for row in submission_rows
        }
        score = _compute_accuracy(titanic_labels, titanic_predictions)

    elif competition.slug == "rsna-pneumonia-detection":
        _validate_required_columns(submission_rows, {"patientId", "Target"})
        _validate_required_columns(label_rows, {"patientId", "Target"})

        rsna_labels = {row["patientId"]: _int01(row["Target"], "Target") for row in label_rows}
        rsna_scores = {row["patientId"]: _float01(row["Target"], "Target") for row in submission_rows}
        score = _compute_binary_auc(rsna_labels, rsna_scores)

    else:
        raise ValueError(f"Unsupported competition slug: {competition.slug}")

    return ScoreResult(leaderboard_score=score, evaluation_split_version=split_version)
