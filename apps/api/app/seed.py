from __future__ import annotations

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
from app.models import Competition, CompetitionExposure, CompetitionStatus, Dataset, Exposure, GpuDevice, Pack, PackExposure


class DatasetSeed(TypedDict):
    slug: str
    title: str
    source: str
    exposure: Exposure
    license: str
    dataset_dir: str
    bytes: int
    checksum: str


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
        "bytes": 0,
        "checksum": "pending",
    },
    {
        "slug": "rsna-pneumonia-detection-challenge",
        "title": "RSNA Pneumonia Detection Challenge",
        "source": "kaggle",
        "exposure": Exposure.EXTERNAL,
        "license": "Kaggle Competition Terms (internal mirror; redistribution restricted)",
        "dataset_dir": "rsna-pneumonia-detection",
        "bytes": 0,
        "checksum": "pending",
    },
    {
        "slug": "cifar-100",
        "title": "CIFAR-100",
        "source": "toronto-cs",
        "exposure": Exposure.EXTERNAL,
        "license": "MIT-like (Alex Krizhevsky, internal mirror)",
        "dataset_dir": "cifar-100",
        "bytes": 0,
        "checksum": "pending",
    },
    {
        "slug": "oxford-iiit-pet",
        "title": "Oxford-IIIT Pet",
        "source": "kaggle",
        "exposure": Exposure.INTERNAL,
        "license": "Dataset terms per source mirror",
        "dataset_dir": "oxford-iiit-pet",
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
        "description": "Permanent mock competition based on RSNA pneumonia imaging data.",
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
        "description": "Permanent mock competition — classify 32x32 images into 100 fine-grained categories.",
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
        "description": "INTERNAL semantic segmentation benchmark with Kaggle-style RLE submissions.",
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


def _dataset_payload_with_storage_path(dataset_payload: DatasetSeed, training_data_root: Path) -> DatasetSeedResolved:
    payload: DatasetSeedResolved = {
        "slug": dataset_payload["slug"],
        "title": dataset_payload["title"],
        "source": dataset_payload["source"],
        "exposure": dataset_payload["exposure"],
        "license": dataset_payload["license"],
        "storage_path": str(training_data_root / dataset_payload["dataset_dir"]),
        "bytes": dataset_payload["bytes"],
        "checksum": dataset_payload["checksum"],
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
        existing_dataset = session.exec(
            select(Dataset).where(Dataset.slug == dataset_payload["slug"])
        ).first()
        if existing_dataset is None:
            existing_dataset = Dataset(**resolved_dataset_payload)
            session.add(existing_dataset)
            session.flush()
        else:
            existing_dataset.storage_path = str(resolved_dataset_payload["storage_path"])
            existing_dataset.exposure = resolved_dataset_payload["exposure"]
            session.add(existing_dataset)
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

    session.commit()
