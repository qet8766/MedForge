from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol, cast

from app.api_contract import ApiEnvelope
from app.problem_details import ProblemDocument

type JSONObject = dict[str, object]
type JSONArray = list[object]

type SuccessPayload = dict[str, object] | list[object]
type MetaDict = dict[str, object]
type ProblemPayload = dict[str, object]


class _HasJsonResponse(Protocol):
    status_code: int
    headers: Mapping[str, str]

    def json(self) -> object: ...


def _problem_media_type() -> str:
    return "application/problem+json"


def _assert_status(response: _HasJsonResponse, *, status_code: int) -> None:
    assert response.status_code == status_code


def _assert_content_type(response: _HasJsonResponse, *, expected: str) -> None:
    content_type = response.headers.get("content-type", "")
    assert expected in content_type


def _failure_message(operation: str, error: Exception) -> str:
    return f"{operation} payload failed validation: {error}"


def _parse_success_envelope(response: _HasJsonResponse, *, status_code: int) -> tuple[SuccessPayload, MetaDict]:
    _assert_status(response, status_code=status_code)
    try:
        envelope = ApiEnvelope[SuccessPayload].model_validate(response.json())
    except Exception as error:
        raise AssertionError(_failure_message("Success", error)) from error

    assert isinstance(envelope.meta.request_id, str) and envelope.meta.request_id
    return envelope.data, envelope.meta.model_dump()


def _parse_problem_payload(response: _HasJsonResponse, *, status_code: int) -> ProblemDocument:
    _assert_status(response, status_code=status_code)
    _assert_content_type(response, expected=_problem_media_type())
    try:
        payload = ProblemDocument.model_validate(response.json())
    except Exception as error:
        raise AssertionError(_failure_message("Problem", error)) from error

    return payload


def assert_success(
    response: _HasJsonResponse,
    *,
    status_code: int,
) -> tuple[SuccessPayload, MetaDict]:
    data, meta = _parse_success_envelope(response, status_code=status_code)
    return data, meta


def assert_success_dict(
    response: _HasJsonResponse,
    *,
    status_code: int,
) -> tuple[JSONObject, MetaDict]:
    data, meta = assert_success(response, status_code=status_code)
    if not isinstance(data, dict):
        raise AssertionError(f"Expected success payload dict, got {type(data).__name__}")
    return cast(JSONObject, data), meta


def assert_success_list(
    response: _HasJsonResponse,
    *,
    status_code: int,
) -> tuple[JSONArray, MetaDict]:
    data, meta = assert_success(response, status_code=status_code)
    if not isinstance(data, list):
        raise AssertionError(f"Expected success payload list, got {type(data).__name__}")
    return cast(JSONArray, data), meta


def assert_problem(
    response: _HasJsonResponse,
    *,
    status_code: int,
    type_suffix: str,
    include_type_prefix: bool = True,
) -> ProblemPayload:
    payload = _parse_problem_payload(response, status_code=status_code)

    expected_type = f"https://medforge.dev/problems/{type_suffix}" if include_type_prefix else type_suffix
    assert payload.status == status_code
    assert payload.type == expected_type

    assert payload.title
    assert payload.detail
    assert payload.code
    assert payload.request_id
    assert payload.instance

    return cast(ProblemPayload, payload.model_dump())


__all__ = [
    "JSONArray",
    "JSONObject",
    "MetaDict",
    "ProblemPayload",
    "SuccessPayload",
    "assert_problem",
    "assert_success",
    "assert_success_dict",
    "assert_success_list",
]
