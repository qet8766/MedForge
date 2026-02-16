## 5. Dataset Formats

Storage root: `/data/medforge/datasets/`

**Two distinct paths exist — don't confuse them:**

- `/data/medforge/datasets/` — full dataset mirrors stored at the host level (training data, images, CSVs). Managed outside the API.
- `{COMPETITIONS_DATA_DIR}` (default `data/competitions` relative to API root) — holdout labels + scoring manifests only. Used by the scoring engine at runtime.

Retention policy:

- Keep full source datasets under the storage root; do not keep only holdout labels.
- `apps/api/data/competitions/*` contains scoring manifests + hidden holdout labels only, not the raw competition datasets.

Competition evaluation uses a canonical-test-first policy:

- Use official test split labels when available from a trusted source.
- Otherwise use a documented internal holdout built from training data.

### Local Mirror Requirements

Expected on-disk dataset coverage:

| Dataset path | Required files/directories |
|--------------|----------------------------|
| `/data/medforge/datasets/titanic-kaggle/` | `train.csv`, `test.csv`, `sample_submission.csv` |
| `/data/medforge/datasets/rsna-pneumonia-detection/` | `train_labels.csv`, `detailed_class_info.csv`, `test_ids.csv`, `sample_submission.csv`, `train_images/` (21,347 `.dcm`), `test_images/` (5,337 `.dcm`) |
| `/data/medforge/datasets/cifar-100/` | `train_labels.csv`, `test_ids.csv`, `sample_submission.csv`, `train/` (50,000 `.png`), `test/` (10,000 `.png`) |

---

### 1. Titanic — Machine Learning from Disaster

**Dataset slug:** `titanic-kaggle` | **Competition slug:** `titanic-survival`
**Path:** `/data/medforge/datasets/titanic-kaggle/`
**Metric:** accuracy | **Source:** [Kaggle](https://www.kaggle.com/competitions/titanic)

Predict which passengers survived the 1912 Titanic shipwreck.

#### Files

| File | Rows | Description |
|------|------|-------------|
| `train.csv` | 891 | Labelled training set (original Kaggle train split) |
| `test.csv` | 418 | Unlabelled test set (original Kaggle test split) |
| `sample_submission.csv` | 418 | Sample submission |

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
**Path:** `/data/medforge/datasets/rsna-pneumonia-detection/`
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
**Path:** `/data/medforge/datasets/cifar-100/`
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

### Re-download / Rehydrate

Use these when files are missing or corrupted.
Prerequisites for Kaggle downloads: installed `kaggle` CLI and `~/.kaggle/kaggle.json`.

#### Titanic (Kaggle)

```bash
mkdir -p /data/medforge/datasets/titanic-kaggle
kaggle competitions download -c titanic -p /data/medforge/datasets/titanic-kaggle --force
find /data/medforge/datasets/titanic-kaggle -maxdepth 1 -name '*.zip' -print0 | xargs -0 -n1 unzip -o -d /data/medforge/datasets/titanic-kaggle
```

#### RSNA Pneumonia (Kaggle)

```bash
mkdir -p /data/medforge/datasets/rsna-pneumonia-detection
kaggle competitions download -c rsna-pneumonia-detection-challenge -p /data/medforge/datasets/rsna-pneumonia-detection --force
find /data/medforge/datasets/rsna-pneumonia-detection -maxdepth 1 -name '*.zip' -print0 | xargs -0 -n1 unzip -o -d /data/medforge/datasets/rsna-pneumonia-detection
```

#### CIFAR-100 (torchvision)

```bash
python3 - <<'PY'
from pathlib import Path
import csv
from torchvision.datasets import CIFAR100

root = Path("/data/medforge/datasets/cifar-100")
cache = root / ".torchvision-cache"
train_dir = root / "train"
test_dir = root / "test"
root.mkdir(parents=True, exist_ok=True)
cache.mkdir(parents=True, exist_ok=True)
train_dir.mkdir(parents=True, exist_ok=True)
test_dir.mkdir(parents=True, exist_ok=True)

train = CIFAR100(root=str(cache), train=True, download=True)
test = CIFAR100(root=str(cache), train=False, download=True)

for i, (img, label) in enumerate(train):
  img.save(train_dir / f"{i}.png")
with (root / "train_labels.csv").open("w", newline="", encoding="utf-8") as f:
  w = csv.writer(f)
  w.writerow(["image_id", "label"])
  w.writerows((i, int(train[i][1])) for i in range(len(train)))

for i, (img, _) in enumerate(test):
  img.save(test_dir / f"{i}.png")
with (root / "test_ids.csv").open("w", newline="", encoding="utf-8") as f:
  w = csv.writer(f)
  w.writerow(["image_id"])
  w.writerows((i,) for i in range(len(test)))
with (root / "sample_submission.csv").open("w", newline="", encoding="utf-8") as f:
  w = csv.writer(f)
  w.writerow(["image_id", "label"])
  w.writerows((i, 0) for i in range(len(test)))
PY
```

Quick checks:

```bash
find /data/medforge/datasets/rsna-pneumonia-detection/train_images -type f -name '*.dcm' | wc -l   # 21347
find /data/medforge/datasets/rsna-pneumonia-detection/test_images -type f -name '*.dcm' | wc -l    # 5337
find /data/medforge/datasets/cifar-100/train -type f -name '*.png' | wc -l                          # 50000
find /data/medforge/datasets/cifar-100/test -type f -name '*.png' | wc -l                           # 10000
```

---

### Scoring

Holdout labels live in `{COMPETITIONS_DATA_DIR}/{competition_slug}/holdout_labels.csv` (default `data/competitions` relative to API root). Each directory also contains a strict `manifest.json` with:

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

Titanic `titanic-survival` uses labelled Kaggle test IDs (`892..1309`, 418 rows) from `wesleyhowe/titanic-labelled-test-set/test_augmented.csv`, stored server-side only.
