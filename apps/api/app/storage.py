from __future__ import annotations

import hashlib
from pathlib import Path
from typing import NamedTuple
from uuid import UUID

from fastapi import UploadFile

from app.config import Settings


class StoredFile(NamedTuple):
    path: Path
    sha256: str
    row_count: int


async def store_submission_file(
    *,
    settings: Settings,
    competition_slug: str,
    user_id: UUID,
    submission_id: UUID,
    upload: UploadFile,
) -> StoredFile:
    destination_dir = settings.submissions_dir / competition_slug / str(user_id)
    destination_dir.mkdir(parents=True, exist_ok=True)

    suffix = Path(upload.filename or "submission.csv").suffix.lower()
    if suffix != ".csv":
        raise ValueError("Submission file must be a CSV.")

    destination = destination_dir / f"{submission_id}.csv"
    payload = await upload.read()
    destination.write_bytes(payload)

    digest = hashlib.sha256(payload).hexdigest()
    row_count = payload.count(b"\n")

    return StoredFile(path=destination, sha256=digest, row_count=max(0, row_count - 1))
