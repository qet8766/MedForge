## Dataset Formats

Storage root: `/data/medforge/datasets/`

Both datasets are 80/20 splits from the original Kaggle training data (seed 42). The Kaggle test sets had no public labels so we discarded them and built our own holdout.

---

### 1. Titanic — Machine Learning from Disaster

**Dataset slug:** `titanic-kaggle` | **Competition slug:** `titanic-survival`
**Path:** `/data/medforge/datasets/titanic-kaggle/`
**Metric:** accuracy | **Source:** [Kaggle](https://www.kaggle.com/competitions/titanic)

Predict which passengers survived the 1912 Titanic shipwreck.

#### Files

| File | Rows | Description |
|------|------|-------------|
| `train.csv` | 712 | Labelled training set |
| `test.csv` | 179 | Unlabelled test set |
| `sample_submission.csv` | 179 | Sample submission (all zeros) |

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
**Metric:** ROC AUC | **Source:** [Kaggle](https://www.kaggle.com/competitions/rsna-pneumonia-detection-challenge)

Binary classification — predict probability of pneumonia from frontal-view chest X-rays. Dataset provided by RSNA, NIH, and MD.ai. Original Kaggle filenames were prefixed `stage_2_`; renamed here.

#### Files

| File | Count / Rows | Description |
|------|--------------|-------------|
| `train_labels.csv` | ~24k rows | Bounding-box annotations + binary target (train patients only) |
| `detailed_class_info.csv` | ~24k rows | Three-class diagnostic label (train patients only) |
| `test_ids.csv` | 5,337 rows | Test patient IDs (no labels) |
| `sample_submission.csv` | 5,337 rows | Sample submission (all 0.5) |
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
patientId,Target
0004cfab-14fd-4e49-80ba-63a80b6bddd6,0.75
00313ee0-9eaa-42f4-b0ab-c148ed3241cd,0.12
```

`patientId` must match every patient in `test_ids.csv`. `Target` is a float in [0.0, 1.0].

---

### Scoring

Holdout labels live in `{COMPETITIONS_DATA_DIR}/{competition_slug}/holdout_labels.csv` (default `data/competitions` relative to API root). Each directory also contains a `manifest.json` with `evaluation_split_version`.

| Competition | Holdout columns |
|-------------|-----------------|
| `titanic-survival` | `PassengerId,Survived` (int 0/1) |
| `rsna-pneumonia-detection` | `patientId,Target` (int 0/1) |
