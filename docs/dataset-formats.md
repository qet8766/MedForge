## Dataset Formats

### Scope

Canonical dataset layout and submission/holdout format requirements.

### In Scope

- required on-disk layout for `TRAINING_DATA_ROOT`, `PUBLIC_EVAL_DATA_ROOT`, and `TEST_HOLDOUTS_DIR`
- per-competition dataset and submission column/row format contracts
- holdout/manifest placement and scoring input format expectations


### Out of Scope

- competition API behavior and leaderboard semantics (`@docs/competitions.md`)
- runtime auth/routing and session lifecycle contracts (`@docs/auth-routing.md`, `@docs/sessions.md`)
- host/service operational runbook procedures (`@docs/runbook.md`)

### Canonical Sources

- `@apps/api/data/public-eval/`
- `@apps/api/data/scoring-holdouts/`
- `@apps/api/app/scoring/`
- `@apps/api/app/storage.py`
- `@tools/data-prep/`

Canonical roots:

- `TRAINING_DATA_ROOT` (training-only files)
- `PUBLIC_EVAL_DATA_ROOT` (public non-training evaluation inputs + `manifest.json`)
- `TEST_HOLDOUTS_DIR` (hidden holdout labels only)

Recommended values:

- Local repo development (from `@apps/api`):
  - `TRAINING_DATA_ROOT=../../datasets/train`
  - `PUBLIC_EVAL_DATA_ROOT=data/public-eval`
  - `TEST_HOLDOUTS_DIR=data/scoring-holdouts`
- Host deployment:
  - `TRAINING_DATA_ROOT=/data/medforge/datasets/train`
  - `PUBLIC_EVAL_DATA_ROOT=/data/medforge/datasets/public-eval`
  - `TEST_HOLDOUTS_DIR=/data/medforge/scoring-holdouts`

Before running shell examples below:

```bash
export TRAINING_DATA_ROOT="${TRAINING_DATA_ROOT:-/data/medforge/datasets/train}"
export PUBLIC_EVAL_DATA_ROOT="${PUBLIC_EVAL_DATA_ROOT:-data/public-eval}"
export TEST_HOLDOUTS_DIR="${TEST_HOLDOUTS_DIR:-data/scoring-holdouts}"
```

**Three distinct roots exist — keep them isolated:**

- `${TRAINING_DATA_ROOT}/` — training files only.
- `${PUBLIC_EVAL_DATA_ROOT}/` — public evaluation inputs + `manifest.json` used by scoring and user-facing format validation.
- `${TEST_HOLDOUTS_DIR}/` — hidden holdout labels used by scoring only.

Runtime guardrails:

- API startup fails if any legacy variables are present: `MEDFORGE_DATASETS_ROOT`, `COMPETITIONS_DATA_DIR`.
- API startup fails when any pair of roots overlap (same path, parent/child, or symlink overlap).

Retention policy:

- Keep full source training and public evaluation inputs in their dedicated roots.
- `@apps/api/data/public-eval/*` contains only public eval artifacts (`manifest.json`, test IDs/images, sample submission files).
- `@apps/api/data/scoring-holdouts/*` contains hidden holdout labels only.

Competition evaluation uses a canonical-test-first policy:

- Use official test split labels when available from a trusted source.
- Otherwise use a documented internal holdout built from training data.

### Local Mirror Requirements

Expected on-disk dataset coverage:

| Dataset slug | Training root (`${TRAINING_DATA_ROOT}/...`) | Public eval root (`${PUBLIC_EVAL_DATA_ROOT}/...`) |
|--------------|----------------------------------------------|----------------------------------------------------|
| `titanic-kaggle` | `train.csv` | `test.csv`, `sample_submission.csv`, `manifest.json` (under competition slug) |
| `rsna-pneumonia-detection` | `train_labels.csv`, `detailed_class_info.csv`, `train_images/` | `test_ids.csv`, `sample_submission.csv`, `test_images/`, `manifest.json` (under competition slug) |
| `cifar-100` | `train_labels.csv`, `train/` | `test_ids.csv`, `sample_submission.csv`, `test/`, `manifest.json` (under competition slug) |
| `oxford-iiit-pet` | `train_labels.csv`, `train_images/`, `train_masks/`, `train_trimaps/` | `test_ids.csv`, `sample_submission.csv`, `test_images/`, `manifest.json` (under competition slug) |

---

### 1. Titanic — Machine Learning from Disaster

**Dataset slug:** `titanic-kaggle` | **Competition slug:** `titanic-survival`
**Training path:** `${TRAINING_DATA_ROOT}/titanic-kaggle/`
**Public eval path:** `${PUBLIC_EVAL_DATA_ROOT}/titanic-kaggle/`
**Metric:** accuracy | **Source:** [Kaggle](https://www.kaggle.com/competitions/titanic)

#### Files

| File | Rows | Description |
|------|------|-------------|
| `train.csv` | 891 | Labelled training set (original Kaggle train split) |
| `test.csv` | 418 | Unlabelled test set (original Kaggle test split) |
| `sample_submission.csv` | 418 | Sample submission |

Placement contract: `train.csv` is stored under `${TRAINING_DATA_ROOT}/titanic-kaggle/`; `test.csv` and `sample_submission.csv` are stored under `${PUBLIC_EVAL_DATA_ROOT}/titanic-kaggle/`.

#### Columns

| Column | Type | Notes |
|--------|------|-------|
| PassengerId | int | Unique ID |
| Survived | int 0/1 | **Target.** `test.csv` omits this column. |
| Pclass | int 1/2/3 | Proxy for socio-economic status (1st = Upper, 2nd = Middle, 3rd = Lower) |
| Name | string | |
| Sex | string | `male` / `female` |
| Age | float | Fractional if < 1; estimated ages in the form xx.5. May be missing. |
| SibSp | int | Siblings + spouses aboard |
| Parch | int | Parents + children aboard. Some children with nanny only have parch = 0. |
| Ticket | string | |
| Fare | float | |
| Cabin | string | May be missing |
| Embarked | string | C = Cherbourg, Q = Queenstown, S = Southampton |

#### Submission

```
PassengerId,Survived
123,0
456,1
```

`PassengerId` must match every ID in `test.csv`. `Survived` is `0` or `1`.

---

### 2. RSNA Pneumonia Detection

**Dataset slug:** `rsna-pneumonia-detection-challenge` | **Competition slug:** `rsna-pneumonia-detection`
**Training path:** `${TRAINING_DATA_ROOT}/rsna-pneumonia-detection/`
**Public eval path:** `${PUBLIC_EVAL_DATA_ROOT}/rsna-pneumonia-detection/`
**Metric:** mAP @ IoU [0.4–0.75] | **Source:** [Kaggle](https://www.kaggle.com/competitions/rsna-pneumonia-detection-challenge)

Object detection — localize pneumonia opacities with bounding boxes on frontal-view chest X-rays. Scored with mean average precision across IoU thresholds 0.4–0.75. Dataset provided by RSNA, NIH, and MD.ai. Original Kaggle filenames were prefixed `stage_2_`; renamed here.

#### Files

| File | Count / Rows | Description |
|------|--------------|-------------|
| `train_labels.csv` | ~24k rows | Bounding-box annotations + binary target (train patients only) |
| `detailed_class_info.csv` | ~24k rows | Three-class diagnostic label (train patients only) |
| `test_ids.csv` | 5,337 rows | Test patient IDs (no labels) |
| `sample_submission.csv` | 5,337 rows | Sample submission (empty detection rows) |
| `train_images/` | 21,347 `.dcm` | Training chest X-rays (1024x1024, 8-bit, MONOCHROME2) |
| `test_images/` | 5,337 `.dcm` | Test chest X-rays |

Placement contract: `train_labels.csv`, `detailed_class_info.csv`, and `train_images/` live under `${TRAINING_DATA_ROOT}/rsna-pneumonia-detection/`; `test_ids.csv`, `sample_submission.csv`, and `test_images/` live under `${PUBLIC_EVAL_DATA_ROOT}/rsna-pneumonia-detection/`.

#### `train_labels.csv`

| Column | Type | Notes |
|--------|------|-------|
| patientId | string (UUID) | Maps to `{patientId}.dcm` |
| x, y | float | Bounding-box upper-left corner (empty when Target = 0) |
| width, height | float | Bounding-box size (empty when Target = 0) |
| Target | int 0/1 | 1 = pneumonia opacity present |

Multiple rows per patient when Target = 1 (one per bounding box).

#### `detailed_class_info.csv`

| Class | Meaning |
|-------|---------|
| `Normal` | Healthy lung |
| `No Lung Opacity / Not Normal` | Abnormal but not a lung opacity (e.g. pleural effusion) |
| `Lung Opacity` | Opacity suggestive of pneumonia (Target = 1 cases) |

#### Submission

```
patientId,confidence,x,y,width,height
0004cfab-14fd-4e49-80ba-63a80b6bddd6,0.95,264.0,152.0,213.0,379.0
0004cfab-14fd-4e49-80ba-63a80b6bddd6,0.82,562.0,152.0,256.0,453.0
00313ee0-9eaa-42f4-b0ab-c148ed3241cd,,,,,
```

One row per predicted detection; multiple rows per patient OK. No-detection: one row with all fields empty after `patientId`. Every patient in `test_ids.csv` must appear at least once. `confidence` ∈ [0.0, 1.0]; `x, y, width, height` ≥ 0.0.

---

### 3. CIFAR-100 Classification

**Dataset slug:** `cifar-100` | **Competition slug:** `cifar-100-classification`
**Training path:** `${TRAINING_DATA_ROOT}/cifar-100/`
**Public eval path:** `${PUBLIC_EVAL_DATA_ROOT}/cifar-100/`
**Metric:** accuracy | **Source:** [University of Toronto](https://www.cs.toronto.edu/~kriz/cifar.html)

Classify 32x32 colour images into 100 fine-grained categories. Uses the **original CIFAR-100 test set** as holdout (not an 80/20 split).

#### Files

| File | Count / Rows | Description |
|------|--------------|-------------|
| `train_labels.csv` | 50,000 rows | Image IDs + fine labels (training set) |
| `train/` | 50,000 `.png` | 32x32 training images |
| `test_ids.csv` | 10,000 rows | Test image IDs (no labels) |
| `test/` | 10,000 `.png` | 32x32 test images |
| `sample_submission.csv` | 10,000 rows | Sample submission (all zeros) |

Placement contract: `train_labels.csv` and `train/` live under `${TRAINING_DATA_ROOT}/cifar-100/`; `test_ids.csv`, `test/`, and `sample_submission.csv` live under `${PUBLIC_EVAL_DATA_ROOT}/cifar-100/`.

#### Columns

| Column | Type | Notes |
|--------|------|-------|
| image_id | int | 0-based index within the split |
| label | int 0–99 | **Target.** `test_ids.csv` omits this column. |

#### Submission

```
image_id,label
0,49
1,33
2,72
```

`image_id` must match every ID in `test_ids.csv`. `label` is an integer in 0–99.

---

### 4. Oxford-IIIT Pet Segmentation

**Dataset slug:** `oxford-iiit-pet` | **Competition slug:** `oxford-pet-segmentation`
**Training path:** `${TRAINING_DATA_ROOT}/oxford-iiit-pet/`
**Public eval path:** `${PUBLIC_EVAL_DATA_ROOT}/oxford-pet-segmentation/`
**Metric:** mean_iou | **Source:** [Oxford VGG](https://www.robots.ox.ac.uk/~vgg/data/pets/)

Binary semantic segmentation — segment pet foreground from background in variable-resolution images. Scored with mean IoU over the test split. Dataset provided by Oxford Visual Geometry Group and IIIT Hyderabad.

#### Files

| File | Count / Rows | Description |
|------|--------------|-------------|
| `train_labels.csv` | ~3,680 rows | Image IDs + RLE masks + dimensions (trainval split) |
| `train_images/` | ~3,680 `.jpg` | Training images (variable resolution) |
| `train_masks/` | ~3,680 `.png` | Binary masks (255=foreground, 0=background — matches scoring format) |
| `train_trimaps/` | ~3,680 `.png` | Original 3-class trimaps (1=pet, 2=background, 3=boundary) |
| `test_ids.csv` | ~3,669 rows | Test image IDs + dimensions (no masks) |
| `test_images/` | ~3,669 `.jpg` | Test images |
| `sample_submission.csv` | ~3,669 rows | Sample submission (empty RLE masks) |

Placement contract: `train_labels.csv`, `train_images/`, `train_masks/`, and `train_trimaps/` live under `${TRAINING_DATA_ROOT}/oxford-iiit-pet/`; `test_ids.csv`, `test_images/`, `sample_submission.csv`, and `manifest.json` live under `${PUBLIC_EVAL_DATA_ROOT}/oxford-pet-segmentation/`.

#### Trimap and boundary annotations

`train_trimaps/` contains the original 3-class annotations from the Oxford-IIIT Pet dataset:
- **1** = pet (foreground)
- **2** = background
- **3** = boundary (pet/background edge)

`train_masks/` contains binary masks derived from the trimaps where only value 1 is foreground. Boundary pixels (trimap value 3) are excluded from scoring ground truth (don't-care), following the original paper's evaluation protocol.

Users may leverage the full trimaps for advanced training strategies such as boundary-aware loss functions, multi-class training, or edge-sensitive architectures.

#### Columns

| Column | Type | Notes |
|--------|------|-------|
| image_id | string | Filename stem (e.g. `Abyssinian_1`, `Bengal_42`) |
| rle_mask | string | RLE-encoded binary mask (row-major, 1-based); empty string = no foreground |
| width | int | Image width in pixels (in `train_labels.csv` and `test_ids.csv`) |
| height | int | Image height in pixels (in `train_labels.csv` and `test_ids.csv`) |

#### Submission

```
image_id,rle_mask
Abyssinian_1,5 10 20 15
Bengal_42,
```

`image_id` must match every ID in `test_ids.csv`. `rle_mask` is a space-separated string of `start length` pairs (1-based pixel indices, row-major / C-order flattening). Empty string means no foreground pixels predicted.

#### RLE convention

- Flatten mask array in row-major (C) order to a 1D vector of length `width * height`.
- Find contiguous runs of 1s (foreground pixels).
- Encode each run as `start length` where `start` is the 1-based index of the first pixel in the run.
- Example: a 4x4 mask with foreground at pixels [0,1,2,5,6] (0-based) encodes as `1 3 6 2`.

---

### Re-download / Rehydrate

Use these when files are missing or corrupted.
Prerequisites for Kaggle downloads: installed `kaggle` CLI and `~/.kaggle/kaggle.json`.

#### Titanic (Kaggle)

```bash
tmp_dir="$(mktemp -d)"
mkdir -p "${TRAINING_DATA_ROOT}/titanic-kaggle" "${PUBLIC_EVAL_DATA_ROOT}/titanic-kaggle"
kaggle competitions download -c titanic -p "${tmp_dir}" --force
find "${tmp_dir}" -maxdepth 1 -name '*.zip' -print0 | xargs -0 -n1 unzip -o -d "${tmp_dir}"
mv "${tmp_dir}/train.csv" "${TRAINING_DATA_ROOT}/titanic-kaggle/train.csv"
mv "${tmp_dir}/test.csv" "${PUBLIC_EVAL_DATA_ROOT}/titanic-kaggle/test.csv"
mv "${tmp_dir}/gender_submission.csv" "${PUBLIC_EVAL_DATA_ROOT}/titanic-kaggle/sample_submission.csv"
rm -rf "${tmp_dir}"
```

#### RSNA Pneumonia (Kaggle)

```bash
tmp_dir="$(mktemp -d)"
mkdir -p "${TRAINING_DATA_ROOT}/rsna-pneumonia-detection" "${PUBLIC_EVAL_DATA_ROOT}/rsna-pneumonia-detection"
kaggle competitions download -c rsna-pneumonia-detection-challenge -p "${tmp_dir}" --force
find "${tmp_dir}" -maxdepth 1 -name '*.zip' -print0 | xargs -0 -n1 unzip -o -d "${tmp_dir}"
mv "${tmp_dir}/train_labels.csv" "${TRAINING_DATA_ROOT}/rsna-pneumonia-detection/train_labels.csv"
mv "${tmp_dir}/detailed_class_info.csv" "${TRAINING_DATA_ROOT}/rsna-pneumonia-detection/detailed_class_info.csv"
mv "${tmp_dir}/train_images" "${TRAINING_DATA_ROOT}/rsna-pneumonia-detection/train_images"
mv "${tmp_dir}/test_ids.csv" "${PUBLIC_EVAL_DATA_ROOT}/rsna-pneumonia-detection/test_ids.csv"
mv "${tmp_dir}/sample_submission.csv" "${PUBLIC_EVAL_DATA_ROOT}/rsna-pneumonia-detection/sample_submission.csv"
mv "${tmp_dir}/test_images" "${PUBLIC_EVAL_DATA_ROOT}/rsna-pneumonia-detection/test_images"
rm -rf "${tmp_dir}"
```

#### CIFAR-100 (torchvision)

```bash
python3 - <<'PY'
import os
from pathlib import Path
import csv
from torchvision.datasets import CIFAR100

train_root = Path(os.environ["TRAINING_DATA_ROOT"]) / "cifar-100"
eval_root = Path(os.environ["PUBLIC_EVAL_DATA_ROOT"]) / "cifar-100"
cache = train_root / ".torchvision-cache"
train_dir = train_root / "train"
test_dir = eval_root / "test"
train_root.mkdir(parents=True, exist_ok=True)
eval_root.mkdir(parents=True, exist_ok=True)
cache.mkdir(parents=True, exist_ok=True)
train_dir.mkdir(parents=True, exist_ok=True)
test_dir.mkdir(parents=True, exist_ok=True)

train = CIFAR100(root=str(cache), train=True, download=True)
test = CIFAR100(root=str(cache), train=False, download=True)

for i, (img, label) in enumerate(train):
  img.save(train_dir / f"{i}.png")
with (train_root / "train_labels.csv").open("w", newline="", encoding="utf-8") as f:
  w = csv.writer(f)
  w.writerow(["image_id", "label"])
  w.writerows((i, int(train[i][1])) for i in range(len(train)))

for i, (img, _) in enumerate(test):
  img.save(test_dir / f"{i}.png")
with (eval_root / "test_ids.csv").open("w", newline="", encoding="utf-8") as f:
  w = csv.writer(f)
  w.writerow(["image_id"])
  w.writerows((i,) for i in range(len(test)))
with (eval_root / "sample_submission.csv").open("w", newline="", encoding="utf-8") as f:
  w = csv.writer(f)
  w.writerow(["image_id", "label"])
  w.writerows((i, 0) for i in range(len(test)))
PY
```

#### Oxford-IIIT Pet (torchvision)

```bash
python3 tools/data-prep/prepare-oxford-pet.py
```

Quick checks:

```bash
find ${TRAINING_DATA_ROOT}/oxford-iiit-pet/train_images -type f -name '*.jpg' | wc -l                 # ~3680
find ${PUBLIC_EVAL_DATA_ROOT}/oxford-pet-segmentation/test_images -type f -name '*.jpg' | wc -l       # ~3669
wc -l < ${TEST_HOLDOUTS_DIR}/oxford-pet-segmentation/holdout_labels.csv                               # ~3670 (header + data)
```

Quick checks:

```bash
find ${TRAINING_DATA_ROOT}/rsna-pneumonia-detection/train_images -type f -name '*.dcm' | wc -l       # 21347
find ${PUBLIC_EVAL_DATA_ROOT}/rsna-pneumonia-detection/test_images -type f -name '*.dcm' | wc -l     # 5337
find ${TRAINING_DATA_ROOT}/cifar-100/train -type f -name '*.png' | wc -l                              # 50000
find ${PUBLIC_EVAL_DATA_ROOT}/cifar-100/test -type f -name '*.png' | wc -l                            # 10000
```

---

### Scoring

Scoring inputs are split by sensitivity:

- Public manifest: `${PUBLIC_EVAL_DATA_ROOT}/{competition_slug}/manifest.json`
- Hidden labels: `${TEST_HOLDOUTS_DIR}/{competition_slug}/holdout_labels.csv`

`manifest.json` defines:

- `evaluation_split_version`
- `scoring_mode`
- `leaderboard_rule`
- `evaluation_policy`
- `id_column`
- `target_columns`
- `expected_row_count`

| Competition | Holdout columns |
|-------------|-----------------|
| `titanic-survival` | `PassengerId,Survived` (int 0/1) |
| `rsna-pneumonia-detection` | `patientId,x,y,width,height,Target` (bbox + int 0/1) |
| `cifar-100-classification` | `image_id,label` (int 0–99) |
| `oxford-pet-segmentation` | `image_id,rle_mask` (1-based RLE, row-major) |

Titanic `titanic-survival` uses labelled Kaggle test IDs (`892..1309`, 418 rows) from `wesleyhowe/titanic-labelled-test-set/test_augmented.csv`, stored server-side only.
