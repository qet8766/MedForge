from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.competition_policy import (
    LEADERBOARD_RULE_BEST_PER_USER,
    SCORING_MODE_SINGLE_REALTIME_HIDDEN,
    SUPPORTED_EVALUATION_POLICIES,
    SUPPORTED_LEADERBOARD_RULES,
    SUPPORTED_SCORING_MODES,
)

from .types import ManifestMetadata


def _manifest_str(payload: dict[str, Any], field: str) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Manifest field '{field}' must be a non-empty string.")
    return value.strip()


def _manifest_target_columns(payload: dict[str, Any]) -> tuple[str, ...]:
    value = payload.get("target_columns")
    if not isinstance(value, list) or not value:
        raise ValueError("Manifest field 'target_columns' must be a non-empty list.")

    normalized: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ValueError("Manifest field 'target_columns' contains an invalid column.")
        normalized.append(item.strip())
    return tuple(normalized)


def _manifest_expected_row_count(payload: dict[str, Any]) -> int:
    value = payload.get("expected_row_count")
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError("Manifest field 'expected_row_count' must be a positive integer.")
    return value


def _load_manifest(manifest_path: Path) -> ManifestMetadata:
    if not manifest_path.exists():
        raise ValueError(f"Manifest file is missing: {manifest_path}")

    with manifest_path.open("r", encoding="utf-8") as file:
        payload = json.load(file)

    if not isinstance(payload, dict):
        raise ValueError("Invalid manifest format.")

    metadata = ManifestMetadata(
        evaluation_split_version=_manifest_str(payload, "evaluation_split_version"),
        scoring_mode=_manifest_str(payload, "scoring_mode"),
        leaderboard_rule=_manifest_str(payload, "leaderboard_rule"),
        evaluation_policy=_manifest_str(payload, "evaluation_policy"),
        id_column=_manifest_str(payload, "id_column"),
        target_columns=_manifest_target_columns(payload),
        label_source=_manifest_str(payload, "label_source"),
        expected_row_count=_manifest_expected_row_count(payload),
    )

    if metadata.scoring_mode not in SUPPORTED_SCORING_MODES:
        raise ValueError(f"Unsupported manifest scoring_mode: {metadata.scoring_mode}")
    if metadata.leaderboard_rule not in SUPPORTED_LEADERBOARD_RULES:
        raise ValueError(f"Unsupported manifest leaderboard_rule: {metadata.leaderboard_rule}")
    if metadata.evaluation_policy not in SUPPORTED_EVALUATION_POLICIES:
        raise ValueError(f"Unsupported manifest evaluation_policy: {metadata.evaluation_policy}")

    return metadata


def _validate_manifest_contract(
    manifest: ManifestMetadata,
    *,
    expected_id_column: str,
    expected_target_columns: tuple[str, ...],
) -> None:
    if manifest.id_column != expected_id_column:
        raise ValueError(
            f"Manifest id_column mismatch: expected {expected_id_column}, got {manifest.id_column}"
        )
    if tuple(manifest.target_columns) != expected_target_columns:
        raise ValueError(
            "Manifest target_columns mismatch: "
            f"expected {list(expected_target_columns)}, got {list(manifest.target_columns)}"
        )
    if manifest.scoring_mode != SCORING_MODE_SINGLE_REALTIME_HIDDEN:
        raise ValueError("Manifest scoring_mode must be " f"'{SCORING_MODE_SINGLE_REALTIME_HIDDEN}'.")
    if manifest.leaderboard_rule != LEADERBOARD_RULE_BEST_PER_USER:
        raise ValueError("Manifest leaderboard_rule must be " f"'{LEADERBOARD_RULE_BEST_PER_USER}'.")


def _validate_label_row_count(label_rows: list[dict[str, str]], manifest: ManifestMetadata) -> None:
    if len(label_rows) != manifest.expected_row_count:
        raise ValueError(
            "Holdout label row count mismatch: "
            f"expected {manifest.expected_row_count}, got {len(label_rows)}."
        )
