#!/usr/bin/env python3
"""Prepare Oxford-IIIT Pet dataset for the oxford-pet-segmentation competition.

Downloads via torchvision, converts trimaps to binary masks, encodes RLE,
and writes train/test/holdout outputs to the three canonical data roots.

Required env vars:
  TRAINING_DATA_ROOT    — training files (images, masks, labels)
  PUBLIC_EVAL_DATA_ROOT — public evaluation inputs (test images, manifest, sample submission)
  TEST_HOLDOUTS_DIR     — hidden holdout labels for scoring

Dependencies: numpy, Pillow, torchvision (+ torch)
"""
from __future__ import annotations

import csv
import json
import os
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from torchvision.datasets import OxfordIIITPet


# ---------------------------------------------------------------------------
# Mask helpers
# ---------------------------------------------------------------------------


def trimap_to_binary_mask(trimap: np.ndarray) -> np.ndarray:
    """Convert Oxford-IIIT Pet trimap to binary foreground mask.

    Trimap values: 1 = pet (foreground), 2 = background, 3 = boundary.
    Only value 1 is scored as foreground; boundary is excluded from scoring
    ground truth (don't-care), following the original paper's evaluation.
    """
    return (trimap == 1).astype(np.uint8)


def encode_rle(mask: np.ndarray) -> str:
    """Encode binary mask as RLE string (row-major, 1-based pixel indices).

    Matches the convention in competition_parsers._decode_rle_mask:
    space-separated "start length" pairs where start is 1-based.
    """
    flat = mask.flatten(order="C")
    if flat.sum() == 0:
        return ""

    padded = np.concatenate([[0], flat, [0]])
    diff = np.diff(padded)
    starts = np.where(diff == 1)[0]
    ends = np.where(diff == -1)[0]

    pairs: list[str] = []
    for s, e in zip(starts, ends):
        pairs.append(f"{s + 1} {e - s}")  # 1-based start
    return " ".join(pairs)


# ---------------------------------------------------------------------------
# Env helpers
# ---------------------------------------------------------------------------


def _require_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        print(f"ERROR: Required environment variable {name} is not set.", file=sys.stderr)
        sys.exit(1)
    return value


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    training_root = Path(_require_env("TRAINING_DATA_ROOT"))
    public_eval_root = Path(_require_env("PUBLIC_EVAL_DATA_ROOT"))
    holdouts_dir = Path(_require_env("TEST_HOLDOUTS_DIR"))

    dataset_slug = "oxford-iiit-pet"
    competition_slug = "oxford-pet-segmentation"

    train_base = training_root / dataset_slug
    eval_base = public_eval_root / competition_slug
    holdout_base = holdouts_dir / competition_slug

    train_images_dir = train_base / "train_images"
    train_masks_dir = train_base / "train_masks"
    train_trimaps_dir = train_base / "train_trimaps"
    test_images_dir = eval_base / "test_images"

    for d in [train_images_dir, train_masks_dir, train_trimaps_dir, test_images_dir, holdout_base]:
        d.mkdir(parents=True, exist_ok=True)

    cache_dir = train_base / ".torchvision-cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    # ----- Download both splits -----
    print("Downloading trainval split...")
    trainval = OxfordIIITPet(
        root=str(cache_dir),
        split="trainval",
        target_types="segmentation",
        download=True,
    )

    print("Downloading test split...")
    test = OxfordIIITPet(
        root=str(cache_dir),
        split="test",
        target_types="segmentation",
        download=True,
    )

    # ----- Process training split -----
    print(f"Processing {len(trainval)} trainval images...")
    train_label_rows: list[tuple[str, str, int, int]] = []

    for idx in range(len(trainval)):
        img, trimap_img = trainval[idx]
        image_id = trainval._images[idx]  # e.g. "Abyssinian_1.jpg"
        image_id = Path(image_id).stem  # strip extension

        # Save image
        img_rgb = img.convert("RGB")
        img_rgb.save(train_images_dir / f"{image_id}.jpg")

        # Save original 3-class trimap
        trimap_arr = np.array(trimap_img)
        trimap_save = Image.fromarray(trimap_arr.astype(np.uint8))
        trimap_save.save(train_trimaps_dir / f"{image_id}.png")

        # Binary mask: foreground only
        binary = trimap_to_binary_mask(trimap_arr)
        mask_save = Image.fromarray(binary * 255, mode="L")
        mask_save.save(train_masks_dir / f"{image_id}.png")

        # RLE for train labels
        rle = encode_rle(binary)
        h, w = binary.shape
        train_label_rows.append((image_id, rle, w, h))

        if (idx + 1) % 500 == 0:
            print(f"  trainval: {idx + 1}/{len(trainval)}")

    # Write train_labels.csv
    train_labels_path = train_base / "train_labels.csv"
    with train_labels_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["image_id", "rle_mask", "width", "height"])
        writer.writerows(train_label_rows)

    print(f"Wrote {len(train_label_rows)} rows to {train_labels_path}")

    # ----- Process test split -----
    print(f"Processing {len(test)} test images...")
    test_id_rows: list[tuple[str, int, int]] = []
    holdout_rows: list[tuple[str, str]] = []

    for idx in range(len(test)):
        img, trimap_img = test[idx]
        image_id = test._images[idx]
        image_id = Path(image_id).stem

        # Save test image
        img_rgb = img.convert("RGB")
        img_rgb.save(test_images_dir / f"{image_id}.jpg")

        # Binary mask for holdout
        trimap_arr = np.array(trimap_img)
        binary = trimap_to_binary_mask(trimap_arr)
        rle = encode_rle(binary)
        h, w = binary.shape
        test_id_rows.append((image_id, w, h))
        holdout_rows.append((image_id, rle))

        if (idx + 1) % 500 == 0:
            print(f"  test: {idx + 1}/{len(test)}")

    # test_ids.csv
    test_ids_path = eval_base / "test_ids.csv"
    with test_ids_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["image_id", "width", "height"])
        writer.writerows(test_id_rows)

    # sample_submission.csv (empty masks)
    sample_sub_path = eval_base / "sample_submission.csv"
    with sample_sub_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["image_id", "rle_mask"])
        writer.writerows((row[0], "") for row in test_id_rows)

    # manifest.json
    manifest_path = eval_base / "manifest.json"
    manifest = {
        "evaluation_split_version": "v1-pet-seg-test",
        "scoring_mode": "single_realtime_hidden",
        "leaderboard_rule": "best_per_user",
        "evaluation_policy": "canonical_test_first",
        "id_column": "image_id",
        "target_columns": ["rle_mask"],
        "expected_row_count": len(test),
    }
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    # holdout_labels.csv
    holdout_path = holdout_base / "holdout_labels.csv"
    with holdout_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["image_id", "rle_mask"])
        writer.writerows(holdout_rows)

    print(f"Wrote {len(test_id_rows)} test IDs to {test_ids_path}")
    print(f"Wrote {len(holdout_rows)} holdout rows to {holdout_path}")
    print(f"Wrote manifest to {manifest_path}")

    # ----- Validation summary -----
    print("\n--- Summary ---")
    print(f"Train images:  {len(train_label_rows)}")
    print(f"Test images:   {len(test_id_rows)}")
    print(f"Holdout rows:  {len(holdout_rows)}")
    print(f"Manifest expected_row_count: {manifest['expected_row_count']}")

    assert len(holdout_rows) == manifest["expected_row_count"], (
        f"Holdout row count {len(holdout_rows)} != manifest {manifest['expected_row_count']}"
    )
    print("Validation passed.")


if __name__ == "__main__":
    main()
