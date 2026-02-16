"""Competitions route package.

Routing ownership:
- competition, leaderboard, dataset reads: @public.py
- submission create/list flows: @submissions.py
- admin submission scoring: @admin.py
- leaderboard SQL ranking query: @leaderboard.py
- submission row persistence helpers: @submission_records.py
"""

from fastapi import APIRouter

from .admin import router as admin_router
from .public import router as public_router
from .submissions import router as submissions_router

router = APIRouter(tags=["competitions"])
router.include_router(public_router)
router.include_router(submissions_router)
router.include_router(admin_router)
