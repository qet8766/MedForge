from __future__ import annotations

import hashlib
import uuid
from pathlib import Path
from typing import TypedDict

from sqlmodel import Session, select

from app.competition_policy import (
    DEFAULT_EVALUATION_POLICY,
    DEFAULT_LEADERBOARD_RULE,
    DEFAULT_SCORING_MODE,
)
from app.config import get_settings
from app.models import (
    Competition,
    CompetitionExposure,
    CompetitionStatus,
    Dataset,
    Exposure,
    GpuDevice,
    Pack,
    PackExposure,
    Role,
    User,
)
from app.security import hash_password, normalize_email


class DatasetSeed(TypedDict):
    slug: str
    title: str
    source: str
    exposure: Exposure
    license: str
    dataset_dir: str


class DatasetSeedResolved(TypedDict):
    slug: str
    title: str
    source: str
    exposure: Exposure
    license: str
    storage_path: str
    bytes: int
    checksum: str


class CompetitionSeed(TypedDict):
    slug: str
    title: str
    description: str
    dataset_slug: str
    metric: str
    metric_version: str
    scoring_mode: str
    leaderboard_rule: str
    evaluation_policy: str
    competition_spec_version: str
    competition_exposure: CompetitionExposure
    submission_cap_per_day: int


DEFAULT_PACK_ID = uuid.UUID("00000000-0000-0000-0000-000000000100")

SEED_DATASETS: list[DatasetSeed] = [
    {
        "slug": "titanic-kaggle",
        "title": "Titanic - Machine Learning from Disaster",
        "source": "kaggle",
        "exposure": Exposure.EXTERNAL,
        "license": "Kaggle Competition Terms (internal mirror; redistribution restricted)",
        "dataset_dir": "titanic-kaggle",
    },
    {
        "slug": "rsna-pneumonia-detection-challenge",
        "title": "RSNA Pneumonia Detection Challenge",
        "source": "kaggle",
        "exposure": Exposure.EXTERNAL,
        "license": "Kaggle Competition Terms (internal mirror; redistribution restricted)",
        "dataset_dir": "rsna-pneumonia-detection",
    },
    {
        "slug": "cifar-100",
        "title": "CIFAR-100",
        "source": "toronto-cs",
        "exposure": Exposure.EXTERNAL,
        "license": "MIT-like (Alex Krizhevsky, internal mirror)",
        "dataset_dir": "cifar-100",
    },
    {
        "slug": "oxford-iiit-pet",
        "title": "Oxford-IIIT Pet",
        "source": "oxford-vgg",
        "exposure": Exposure.INTERNAL,
        "license": "Dataset terms per source mirror",
        "dataset_dir": "oxford-iiit-pet",
    },
]

SEED_COMPETITIONS: list[CompetitionSeed] = [
    {
        "slug": "titanic-survival",
        "title": "Titanic Survival",
        "description": (
            "## Overview\n\n"
            "Predict which passengers survived the Titanic shipwreck. This classic binary "
            "classification challenge uses real passenger data to explore feature engineering "
            "and model selection.\n\n"
            "## Data Description\n\n"
            "The dataset contains demographics and travel information for 891 training passengers:\n\n"
            "- **PassengerId** — Unique identifier\n"
            "- **Survived** — Target variable (0 = No, 1 = Yes)\n"
            "- **Pclass** — Ticket class (1 = 1st, 2 = 2nd, 3 = 3rd)\n"
            "- **Name** — Passenger name\n"
            "- **Sex** — Gender\n"
            "- **Age** — Age in years (fractional for children under 1)\n"
            "- **SibSp** — Number of siblings/spouses aboard\n"
            "- **Parch** — Number of parents/children aboard\n"
            "- **Ticket** — Ticket number\n"
            "- **Fare** — Passenger fare\n"
            "- **Cabin** — Cabin number\n"
            "- **Embarked** — Port of embarkation (C = Cherbourg, Q = Queenstown, S = Southampton)\n\n"
            "The test set contains 418 passengers without the Survived column.\n\n"
            "## Evaluation\n\n"
            "Submissions are scored using **accuracy** — the percentage of correctly predicted "
            "survival outcomes.\n\n"
            "$$\\\\text{Accuracy} = \\\\frac{\\\\text{Correct Predictions}}{\\\\text{Total Predictions}}$$\n\n"
            "## Submission Format\n\n"
            "Submit a CSV with exactly two columns:\n\n"
            "| Column | Description |\n"
            "|--------|-------------|\n"
            "| PassengerId | ID from the test set |\n"
            "| Survived | Your binary prediction (0 or 1) |\n"
        ),
        "dataset_slug": "titanic-kaggle",
        "metric": "accuracy",
        "metric_version": "accuracy-v1",
        "scoring_mode": DEFAULT_SCORING_MODE,
        "leaderboard_rule": DEFAULT_LEADERBOARD_RULE,
        "evaluation_policy": DEFAULT_EVALUATION_POLICY,
        "competition_spec_version": "v1",
        "competition_exposure": CompetitionExposure.EXTERNAL,
        "submission_cap_per_day": 20,
    },
    {
        "slug": "rsna-pneumonia-detection",
        "title": "RSNA Pneumonia Detection",
        "description": (
            "## Overview\n\n"
            "Detect and localize lung opacities suggestive of pneumonia in chest radiographs. "
            "This object detection challenge uses DICOM images from the RSNA and STR, requiring "
            "both classification and bounding box prediction.\n\n"
            "## Data Description\n\n"
            "The dataset contains frontal chest radiographs in DICOM format:\n\n"
            "- **patientId** — Unique patient identifier\n"
            "- **x, y, width, height** — Bounding box coordinates for opacity regions (training only)\n"
            "- **Target** — Binary label (1 = opacity present, 0 = normal)\n\n"
            "Images vary in resolution and bit depth. Multiple bounding boxes may exist per image "
            "when several opacity regions are present. Images labeled as normal have no bounding box "
            "annotations.\n\n"
            "Additional metadata from the DICOM headers includes patient age, sex, and view position.\n\n"
            "## Evaluation\n\n"
            "Submissions are evaluated using **mean Average Precision at IoU thresholds** from "
            "0.4 to 0.75 in steps of 0.05.\n\n"
            "For each IoU threshold, a predicted box is a true positive if it overlaps a ground "
            "truth box above the threshold. mAP is computed as the mean of per-class AP values "
            "across all thresholds.\n\n"
            "## Submission Format\n\n"
            "Submit a CSV with the following columns:\n\n"
            "| Column | Description |\n"
            "|--------|-------------|\n"
            "| patientId | Patient ID from the test set |\n"
            "| PredictionString | Space-delimited list of `confidence x y width height` groups |\n\n"
            "For normal predictions (no opacity), leave PredictionString empty.\n"
        ),
        "dataset_slug": "rsna-pneumonia-detection-challenge",
        "metric": "map_iou",
        "metric_version": "map_iou-v1",
        "scoring_mode": DEFAULT_SCORING_MODE,
        "leaderboard_rule": DEFAULT_LEADERBOARD_RULE,
        "evaluation_policy": DEFAULT_EVALUATION_POLICY,
        "competition_spec_version": "v1",
        "competition_exposure": CompetitionExposure.EXTERNAL,
        "submission_cap_per_day": 10,
    },
    {
        "slug": "cifar-100-classification",
        "title": "CIFAR-100 Classification",
        "description": (
            "## Overview\n\n"
            "Classify 32x32 color images into 100 fine-grained categories. CIFAR-100 is a "
            "standard benchmark for image recognition, grouped into 20 superclasses each "
            "containing 5 fine-grained classes.\n\n"
            "## Data Description\n\n"
            "The dataset contains 60,000 color images of size 32x32 pixels:\n\n"
            "- **Training set** — 50,000 images (500 per class)\n"
            "- **Test set** — 10,000 images (100 per class)\n"
            "- **Fine labels** — 100 classes (e.g., apple, aquarium_fish, baby, bear, beaver, ...)\n"
            "- **Coarse labels** — 20 superclasses (e.g., fruit_and_vegetables, fish, people, ...)\n\n"
            "Each image belongs to exactly one fine-grained class and one superclass. Images are "
            "stored as numpy arrays with shape `(32, 32, 3)` in RGB channel order.\n\n"
            "## Evaluation\n\n"
            "Submissions are scored using **top-1 accuracy** on fine-grained labels — the fraction "
            "of test images whose predicted class matches the true class.\n\n"
            "$$\\\\text{Accuracy} = \\\\frac{\\\\text{Correct Predictions}}{\\\\text{Total Predictions}}$$\n\n"
            "## Submission Format\n\n"
            "Submit a CSV with exactly two columns:\n\n"
            "| Column | Description |\n"
            "|--------|-------------|\n"
            "| image_id | Zero-indexed ID from the test set (0\u20139999) |\n"
            "| label | Predicted fine-grained class name |\n"
        ),
        "dataset_slug": "cifar-100",
        "metric": "accuracy",
        "metric_version": "accuracy-v1",
        "scoring_mode": DEFAULT_SCORING_MODE,
        "leaderboard_rule": DEFAULT_LEADERBOARD_RULE,
        "evaluation_policy": DEFAULT_EVALUATION_POLICY,
        "competition_spec_version": "v1",
        "competition_exposure": CompetitionExposure.EXTERNAL,
        "submission_cap_per_day": 20,
    },
    {
        "slug": "oxford-pet-segmentation",
        "title": "Oxford-IIIT Pet Segmentation",
        "description": (
            "## Overview\n\n"
            "Perform pixel-level semantic segmentation of pet images, delineating the pet from "
            "the background and separating the body from the head/face region. This is an "
            "INTERNAL benchmark for trimap segmentation.\n\n"
            "## Data Description\n\n"
            "The Oxford-IIIT Pet Dataset contains images of 37 pet breeds:\n\n"
            "- **Images** — RGB images of varying sizes, each containing a single pet\n"
            "- **Trimap annotations** — Pixel-level labels with three classes:\n"
            "  - Class 1: Foreground (pet body)\n"
            "  - Class 2: Background\n"
            "  - Class 3: Boundary/ambiguous region\n"
            "- **Breeds** — 25 dog breeds and 12 cat breeds, roughly 200 images per breed\n\n"
            "The training/test split follows the original dataset partition. All images have "
            "corresponding trimap ground truth masks.\n\n"
            "## Evaluation\n\n"
            "Submissions are evaluated using **mean Intersection over Union (mIoU)** averaged "
            "across the three trimap classes.\n\n"
            "$$\\\\text{IoU}_c = \\\\frac{|P_c \\\\cap G_c|}{|P_c \\\\cup G_c|}$$\n\n"
            "$$\\\\text{mIoU} = \\\\frac{1}{C} \\\\sum_{c=1}^{C} \\\\text{IoU}_c$$\n\n"
            "## Submission Format\n\n"
            "Submit predictions using run-length encoding (RLE) in a CSV:\n\n"
            "| Column | Description |\n"
            "|--------|-------------|\n"
            "| image_id | Image filename (without extension) |\n"
            "| class_id | Trimap class (1, 2, or 3) |\n"
            "| rle | Run-length encoded mask |\n\n"
            "Each image must have exactly 3 rows (one per class).\n"
        ),
        "dataset_slug": "oxford-iiit-pet",
        "metric": "mean_iou",
        "metric_version": "mean_iou-v1",
        "scoring_mode": DEFAULT_SCORING_MODE,
        "leaderboard_rule": DEFAULT_LEADERBOARD_RULE,
        "evaluation_policy": DEFAULT_EVALUATION_POLICY,
        "competition_spec_version": "v1",
        "competition_exposure": CompetitionExposure.INTERNAL,
        "submission_cap_per_day": 20,
    },
]


def _split_pack_image(image: str) -> tuple[str, str]:
    image_ref = image.strip()
    if not image_ref:
        raise RuntimeError("PACK_IMAGE is required and must include a sha256 digest.")
    if "@sha256:" not in image_ref:
        raise RuntimeError("PACK_IMAGE must be sha256-pinned using the format <image>@sha256:<digest>.")
    return image_ref, image_ref.split("@sha256:", 1)[1]


def _compute_directory_bytes(path: Path) -> int:
    """Sum file sizes under *path*; returns 0 if dir doesn't exist."""
    if not path.is_dir():
        return 0
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())


def _compute_directory_checksum(path: Path) -> str:
    """SHA-256 over sorted (relative_path, size) pairs — structure checksum, no I/O reads."""
    if not path.is_dir():
        return "pending"
    entries = sorted(
        (str(f.relative_to(path)), f.stat().st_size)
        for f in path.rglob("*")
        if f.is_file()
    )
    digest = hashlib.sha256()
    for rel, size in entries:
        digest.update(f"{rel}:{size}\n".encode())
    return digest.hexdigest()


def _dataset_payload_with_storage_path(dataset_payload: DatasetSeed, training_data_root: Path) -> DatasetSeedResolved:
    storage_path = training_data_root / dataset_payload["dataset_dir"]
    payload: DatasetSeedResolved = {
        "slug": dataset_payload["slug"],
        "title": dataset_payload["title"],
        "source": dataset_payload["source"],
        "exposure": dataset_payload["exposure"],
        "license": dataset_payload["license"],
        "storage_path": str(storage_path),
        "bytes": _compute_directory_bytes(storage_path),
        "checksum": _compute_directory_checksum(storage_path),
    }
    return payload


def seed_defaults(session: Session) -> None:
    settings = get_settings()
    image_ref, image_digest = _split_pack_image(settings.pack_image)

    default_pack = session.get(Pack, DEFAULT_PACK_ID)
    if default_pack is None:
        default_pack = Pack(
            id=DEFAULT_PACK_ID,
            name="default-pack",
            exposure=PackExposure.BOTH,
            image_ref=image_ref,
            image_digest=image_digest,
        )
        session.add(default_pack)
    else:
        default_pack.exposure = PackExposure.BOTH
        default_pack.image_ref = image_ref
        default_pack.image_digest = image_digest
        session.add(default_pack)

    for gpu_id in range(7):
        gpu = session.get(GpuDevice, gpu_id)
        if gpu is None:
            session.add(GpuDevice(id=gpu_id, enabled=True))

    session.flush()

    dataset_by_slug: dict[str, Dataset] = {}
    training_data_root = settings.training_data_root

    for dataset_payload in SEED_DATASETS:
        resolved_dataset_payload = _dataset_payload_with_storage_path(dataset_payload, training_data_root)
        existing_dataset = session.exec(select(Dataset).where(Dataset.slug == dataset_payload["slug"])).first()
        if existing_dataset is None:
            existing_dataset = Dataset(**resolved_dataset_payload)
            session.add(existing_dataset)
            session.flush()
        else:
            existing_dataset.storage_path = str(resolved_dataset_payload["storage_path"])
            existing_dataset.exposure = resolved_dataset_payload["exposure"]
            existing_dataset.bytes = resolved_dataset_payload["bytes"]
            existing_dataset.checksum = resolved_dataset_payload["checksum"]
            session.add(existing_dataset)
        dataset_by_slug[existing_dataset.slug] = existing_dataset

    for competition_payload in SEED_COMPETITIONS:
        existing_competition = session.exec(
            select(Competition).where(Competition.slug == competition_payload["slug"])
        ).first()
        if existing_competition is not None:
            existing_competition.description = competition_payload["description"]
            session.add(existing_competition)
            continue

        dataset = dataset_by_slug[competition_payload["dataset_slug"]]
        competition = Competition(
            slug=competition_payload["slug"],
            title=competition_payload["title"],
            description=competition_payload["description"],
            competition_exposure=competition_payload["competition_exposure"],
            status=CompetitionStatus.ACTIVE,
            is_permanent=True,
            metric=competition_payload["metric"],
            metric_version=competition_payload["metric_version"],
            higher_is_better=True,
            scoring_mode=competition_payload["scoring_mode"],
            leaderboard_rule=competition_payload["leaderboard_rule"],
            evaluation_policy=competition_payload["evaluation_policy"],
            competition_spec_version=competition_payload["competition_spec_version"],
            submission_cap_per_day=competition_payload["submission_cap_per_day"],
            dataset_id=dataset.id,
        )
        session.add(competition)

    _seed_admin_user(session, email="admin@naver.com", password="adminadmin")

    session.commit()


def _seed_admin_user(session: Session, *, email: str, password: str) -> None:
    """Create admin user if it does not already exist."""
    normalized = normalize_email(email)
    existing = session.exec(select(User).where(User.email == normalized)).first()
    if existing is not None:
        return
    session.add(
        User(
            email=normalized,
            password_hash=hash_password(password),
            role=Role.ADMIN,
            can_use_internal=True,
            max_concurrent_sessions=4,
        )
    )
