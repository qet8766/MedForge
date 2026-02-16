from __future__ import annotations

import uuid
from typing import TypedDict

from sqlmodel import Session, select

from app.config import get_settings
from app.models import Competition, CompetitionStatus, CompetitionTier, Dataset, GpuDevice, Pack, PackTier


class DatasetSeed(TypedDict):
    slug: str
    title: str
    source: str
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
    submission_cap_per_day: int


DEFAULT_PACK_ID = uuid.UUID("00000000-0000-0000-0000-000000000100")

SEED_DATASETS: list[DatasetSeed] = [
    {
        "slug": "titanic-kaggle",
        "title": "Titanic - Machine Learning from Disaster",
        "source": "kaggle",
        "license": "Kaggle Competition Terms (internal/private mirror)",
        "storage_path": "/data/medforge/datasets/titanic-kaggle",
        "bytes": 0,
        "checksum": "pending",
    },
    {
        "slug": "rsna-pneumonia-detection-challenge",
        "title": "RSNA Pneumonia Detection Challenge",
        "source": "kaggle",
        "license": "Kaggle Competition Terms (internal/private mirror)",
        "storage_path": "/data/medforge/datasets/rsna-pneumonia-detection",
        "bytes": 0,
        "checksum": "pending",
    },
]

SEED_COMPETITIONS: list[CompetitionSeed] = [
    {
        "slug": "titanic-survival",
        "title": "Titanic Survival",
        "description": "Permanent mock competition based on Titanic Kaggle data.",
        "dataset_slug": "titanic-kaggle",
        "metric": "accuracy",
        "submission_cap_per_day": 20,
    },
    {
        "slug": "rsna-pneumonia-detection",
        "title": "RSNA Pneumonia Detection",
        "description": "Permanent mock competition based on RSNA pneumonia imaging data.",
        "dataset_slug": "rsna-pneumonia-detection-challenge",
        "metric": "roc_auc",
        "submission_cap_per_day": 10,
    },
]


def _split_pack_image(image: str) -> tuple[str, str]:
    image_ref = image.strip()
    if not image_ref:
        raise RuntimeError("PACK_IMAGE is required and must include a sha256 digest.")
    if "@sha256:" not in image_ref:
        raise RuntimeError("PACK_IMAGE must be sha256-pinned using the format <image>@sha256:<digest>.")
    return image_ref, image_ref.split("@sha256:", 1)[1]


def seed_defaults(session: Session) -> None:
    settings = get_settings()
    image_ref, image_digest = _split_pack_image(settings.pack_image)

    default_pack = session.get(Pack, DEFAULT_PACK_ID)
    if default_pack is None:
        default_pack = Pack(
            id=DEFAULT_PACK_ID,
            name="default-pack",
            tier=PackTier.BOTH,
            image_ref=image_ref,
            image_digest=image_digest,
        )
        session.add(default_pack)
    else:
        default_pack.image_ref = image_ref
        default_pack.image_digest = image_digest
        session.add(default_pack)

    for gpu_id in range(7):
        gpu = session.get(GpuDevice, gpu_id)
        if gpu is None:
            session.add(GpuDevice(id=gpu_id, enabled=True))

    session.flush()

    dataset_by_slug: dict[str, Dataset] = {}

    for dataset_payload in SEED_DATASETS:
        existing_dataset = session.exec(
            select(Dataset).where(Dataset.slug == dataset_payload["slug"])
        ).first()
        if existing_dataset is None:
            existing_dataset = Dataset(**dataset_payload)
            session.add(existing_dataset)
            session.flush()
        dataset_by_slug[existing_dataset.slug] = existing_dataset

    for competition_payload in SEED_COMPETITIONS:
        existing_competition = session.exec(
            select(Competition).where(Competition.slug == competition_payload["slug"])
        ).first()
        if existing_competition is not None:
            continue

        dataset = dataset_by_slug[competition_payload["dataset_slug"]]
        competition = Competition(
            slug=competition_payload["slug"],
            title=competition_payload["title"],
            description=competition_payload["description"],
            competition_tier=CompetitionTier.PUBLIC,
            status=CompetitionStatus.ACTIVE,
            is_permanent=True,
            metric=competition_payload["metric"],
            higher_is_better=True,
            submission_cap_per_day=competition_payload["submission_cap_per_day"],
            dataset_id=dataset.id,
        )
        session.add(competition)

    session.commit()
