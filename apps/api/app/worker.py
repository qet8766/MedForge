from __future__ import annotations

import argparse
import time
from typing import Any, cast

from sqlalchemy import asc
from sqlmodel import Session, select

from app.config import get_settings
from app.database import engine, init_db
from app.models import ScoreStatus, Submission
from app.services import process_submission_by_id


def process_once(limit: int) -> int:
    processed = 0
    settings = get_settings()

    with Session(engine) as session:
        queued = session.exec(
            select(Submission)
            .where(Submission.score_status == ScoreStatus.QUEUED)
            .order_by(asc(cast(Any, Submission.created_at)))
            .limit(limit)
        ).all()

        for submission in queued:
            process_submission_by_id(session, submission_id=submission.id, settings=settings)
            processed += 1

    return processed


def main() -> None:
    parser = argparse.ArgumentParser(description="MedForge scoring worker")
    parser.add_argument("--once", action="store_true", help="Process queue one time and exit")
    parser.add_argument("--interval", type=int, default=5, help="Polling interval in seconds")
    parser.add_argument("--batch-size", type=int, default=10, help="Max queued items per iteration")
    args = parser.parse_args()

    init_db()

    if args.once:
        processed = process_once(args.batch_size)
        print(f"Processed {processed} queued submissions")
        return

    while True:
        processed = process_once(args.batch_size)
        if processed:
            print(f"Processed {processed} queued submissions")
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
