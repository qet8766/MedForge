#!/usr/bin/env python3
"""One-time script: download CIFAR-100 and extract holdout labels from the test set.

Output: apps/api/data/competitions/cifar-100-classification/holdout_labels.csv
        (10,000 rows — image_id,label with label in 0–99)

Uses only stdlib modules (pickle, tarfile, urllib, csv).
"""
from __future__ import annotations

import csv
import io
import json
import pickle
import sys
import tarfile
import urllib.request
from pathlib import Path

CIFAR100_URL = "https://www.cs.toronto.edu/~kriz/cifar-100-python.tar.gz"
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "apps" / "api" / "data" / "competitions" / "cifar-100-classification"
OUTPUT_CSV = OUTPUT_DIR / "holdout_labels.csv"
MANIFEST_PATH = OUTPUT_DIR / "manifest.json"

EXPECTED_TEST_COUNT = 10_000


def download_cifar100(url: str) -> bytes:
    print(f"Downloading CIFAR-100 from {url} ...")
    with urllib.request.urlopen(url) as resp:  # noqa: S310
        data = resp.read()
    print(f"Downloaded {len(data):,} bytes.")
    return data


def extract_test_labels(archive_bytes: bytes) -> list[int]:
    with tarfile.open(fileobj=io.BytesIO(archive_bytes), mode="r:gz") as tar:
        # The test batch is at cifar-100-python/test
        test_member = None
        for member in tar.getmembers():
            if member.name.endswith("/test"):
                test_member = member
                break

        if test_member is None:
            raise RuntimeError("Could not find 'test' batch inside CIFAR-100 archive.")

        extracted = tar.extractfile(test_member)
        if extracted is None:
            raise RuntimeError("Failed to extract test batch.")

        batch = pickle.loads(extracted.read(), encoding="latin1")  # noqa: S301

    fine_labels: list[int] = list(batch["fine_labels"])
    if len(fine_labels) != EXPECTED_TEST_COUNT:
        raise RuntimeError(
            f"Expected {EXPECTED_TEST_COUNT} test labels, got {len(fine_labels)}."
        )
    return fine_labels


def write_holdout_csv(labels: list[int], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["image_id", "label"])
        for idx, label in enumerate(labels):
            writer.writerow([idx, label])
    print(f"Wrote {len(labels)} rows to {output_path}")


def write_manifest(manifest_path: Path) -> None:
    payload = {
        "evaluation_split_version": "v1-test",
        "scoring_mode": "single_realtime_hidden",
        "leaderboard_rule": "best_per_user",
        "evaluation_policy": "canonical_test_first",
        "id_column": "image_id",
        "target_columns": ["label"],
        "label_source": "cifar100-original-test",
        "expected_row_count": EXPECTED_TEST_COUNT,
    }
    manifest_path.write_text(f"{json.dumps(payload)}\n", encoding="utf-8")
    print(f"Wrote manifest to {manifest_path}")


def main() -> None:
    if OUTPUT_CSV.exists():
        print(f"{OUTPUT_CSV} already exists. Delete it to regenerate.")
        sys.exit(1)

    archive_bytes = download_cifar100(CIFAR100_URL)
    fine_labels = extract_test_labels(archive_bytes)

    # Sanity check: labels must be in 0–99
    for i, label in enumerate(fine_labels):
        if not (0 <= label <= 99):
            raise RuntimeError(f"Label out of range at index {i}: {label}")

    write_holdout_csv(fine_labels, OUTPUT_CSV)
    write_manifest(MANIFEST_PATH)
    print("Done.")


if __name__ == "__main__":
    main()
