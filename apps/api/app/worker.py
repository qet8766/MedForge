from __future__ import annotations

import argparse
import logging
import time
from datetime import UTC, datetime, timedelta
from typing import Any, cast

from sqlalchemy import asc
from sqlmodel import Session, or_, select

from app.config import get_settings
from app.database import engine, init_db
from app.models import ScoreStatus, Submission
from app.services import process_submission_by_id

log = logging.getLogger("medforge.worker")

SCORING_STUCK_THRESHOLD = timedelta(minutes=10)


def process_once(limit: int) -> int:
    processed = 0
    settings = get_settings()

    with Session(engine) as session:
        scoring_cutoff = datetime.now(UTC) - SCORING_STUCK_THRESHOLD
        created_at_col = cast(Any, Submission.created_at)
        queued = session.exec(
            select(Submission)
            .where(
                or_(
                    Submission.score_status == ScoreStatus.QUEUED,
                    (Submission.score_status == ScoreStatus.SCORING)
                    & (created_at_col < scoring_cutoff),
                )
            )
            .order_by(asc(created_at_col))
            .limit(limit)
        ).all()

        for submission in queued:
            sub_id = submission.id
            try:
                process_submission_by_id(session, submission_id=sub_id, settings=settings)
                processed += 1
            except Exception:
                log.exception(
                    "unexpected error processing submission=%s user=%s",
                    sub_id,
                    submission.user_id,
                )
                session.rollback()

    return processed


def main() -> None:
    logging.basicConfig(
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        level=logging.INFO,
    )

    parser = argparse.ArgumentParser(description="MedForge scoring worker")
    parser.add_argument("--once", action="store_true", help="Process queue one time and exit")
    parser.add_argument("--interval", type=int, default=5, help="Polling interval in seconds")
    parser.add_argument("--batch-size", type=int, default=10, help="Max queued items per iteration")
    args = parser.parse_args()

    init_db()

    if args.once:
        processed = process_once(args.batch_size)
        log.info("Processed %d queued submissions", processed)
        return

    while True:
        processed = process_once(args.batch_size)
        if processed:
            log.info("Processed %d queued submissions", processed)
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
