#!/usr/bin/env python3
"""Prepare Titanic holdout labels from a labelled Kaggle test CSV.

Input CSV must include PassengerId and Survived columns (e.g. test_augmented.csv from
wesleyhowe/titanic-labelled-test-set).

Output:
- apps/api/data/competitions/titanic-survival/holdout_labels.csv
- apps/api/data/competitions/titanic-survival/manifest.json
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

EXPECTED_ROWS = 418

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "apps" / "api" / "data" / "competitions" / "titanic-survival"
OUTPUT_CSV = OUTPUT_DIR / "holdout_labels.csv"
OUTPUT_MANIFEST = OUTPUT_DIR / "manifest.json"

DEFAULT_SPLIT_VERSION = "v2-kaggle-labelled-test418"
DEFAULT_LABEL_SOURCE = "kaggle-dataset:wesleyhowe/titanic-labelled-test-set/test_augmented.csv"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate Titanic holdout labels and manifest.")
    parser.add_argument("--input-csv", required=True, type=Path, help="Path to labelled Titanic test CSV.")
    parser.add_argument(
        "--evaluation-split-version",
        default=DEFAULT_SPLIT_VERSION,
        help="evaluation_split_version value for manifest.json.",
    )
    parser.add_argument(
        "--label-source",
        default=DEFAULT_LABEL_SOURCE,
        help="label_source value for manifest.json.",
    )
    return parser.parse_args()


def _parse_int(value: str, field: str) -> int:
    try:
        return int(value)
    except ValueError as exc:
        raise RuntimeError(f"Invalid integer in {field}: {value}") from exc


def load_rows(path: Path) -> list[tuple[int, int]]:
    with path.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        if reader.fieldnames is None:
            raise RuntimeError("Input CSV is missing headers.")

        required = {"PassengerId", "Survived"}
        headers = set(reader.fieldnames)
        missing = sorted(required - headers)
        if missing:
            raise RuntimeError(f"Input CSV missing required columns: {', '.join(missing)}")

        rows: list[tuple[int, int]] = []
        seen_ids: set[int] = set()

        for row in reader:
            passenger_id = _parse_int(row["PassengerId"], "PassengerId")
            survived = _parse_int(row["Survived"], "Survived")
            if survived not in (0, 1):
                raise RuntimeError(f"Survived must be 0 or 1, got {survived}")
            if passenger_id in seen_ids:
                raise RuntimeError(f"Duplicate PassengerId found: {passenger_id}")

            seen_ids.add(passenger_id)
            rows.append((passenger_id, survived))

    if len(rows) != EXPECTED_ROWS:
        raise RuntimeError(f"Expected {EXPECTED_ROWS} rows, got {len(rows)}.")

    rows.sort(key=lambda item: item[0])
    return rows


def write_holdout(rows: list[tuple[int, int]], output_csv: Path) -> None:
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["PassengerId", "Survived"])
        writer.writerows(rows)


def write_manifest(
    output_manifest: Path,
    *,
    evaluation_split_version: str,
    label_source: str,
) -> None:
    payload = {
        "evaluation_split_version": evaluation_split_version,
        "scoring_mode": "single_realtime_hidden",
        "leaderboard_rule": "best_per_user",
        "evaluation_policy": "canonical_test_first",
        "id_column": "PassengerId",
        "target_columns": ["Survived"],
        "label_source": label_source,
        "expected_row_count": EXPECTED_ROWS,
    }
    output_manifest.write_text(f"{json.dumps(payload)}\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    rows = load_rows(args.input_csv)
    write_holdout(rows, OUTPUT_CSV)
    write_manifest(
        OUTPUT_MANIFEST,
        evaluation_split_version=args.evaluation_split_version,
        label_source=args.label_source,
    )
    print(f"Wrote {len(rows)} holdout labels to {OUTPUT_CSV}")
    print(f"Wrote manifest to {OUTPUT_MANIFEST}")


if __name__ == "__main__":
    main()
