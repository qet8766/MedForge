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


class SubmissionUploadTooLargeError(ValueError):
    def __init__(self, *, max_bytes: int, size_bytes: int) -> None:
        super().__init__(f"Submission file exceeds maximum size of {max_bytes} bytes.")
        self.max_bytes = max_bytes
        self.size_bytes = size_bytes


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
    if len(payload) > settings.submission_upload_max_bytes:
        raise SubmissionUploadTooLargeError(
            max_bytes=settings.submission_upload_max_bytes,
            size_bytes=len(payload),
        )
    destination.write_bytes(payload)

    digest = hashlib.sha256(payload).hexdigest()
    row_count = payload.count(b"\n")

    return StoredFile(path=destination, sha256=digest, row_count=max(0, row_count - 1))
