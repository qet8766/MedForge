from __future__ import annotations

from datetime import UTC, datetime
from typing import TypeVar

from fastapi import Request
from pydantic import BaseModel, Field

API_VERSION = "v2.0"
T = TypeVar("T")


class ApiMeta(BaseModel):
    request_id: str
    api_version: str = API_VERSION
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    limit: int | None = None
    next_cursor: str | None = None
    has_more: bool | None = None


class ApiEnvelope[T](BaseModel):
    data: T
    meta: ApiMeta


def build_meta(
    request: Request,
    *,
    limit: int | None = None,
    next_cursor: str | None = None,
    has_more: bool | None = None,
) -> ApiMeta:
    request_id = getattr(request.state, "request_id", "")
    return ApiMeta(
        request_id=request_id,
        limit=limit,
        next_cursor=next_cursor,
        has_more=has_more,
    )


def envelope[T](
    request: Request,
    data: T,
    *,
    limit: int | None = None,
    next_cursor: str | None = None,
    has_more: bool | None = None,
) -> ApiEnvelope[T]:
    return ApiEnvelope(
        data=data,
        meta=build_meta(
            request,
            limit=limit,
            next_cursor=next_cursor,
            has_more=has_more,
        ),
    )
