from __future__ import annotations

from pathlib import Path

import pytest

from app.config import Settings


def test_legacy_dataset_env_var_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MEDFORGE_DATASETS_ROOT", "/tmp/legacy-datasets")
    with pytest.raises(ValueError, match="MEDFORGE_DATASETS_ROOT"):
        Settings()


def test_legacy_holdout_env_var_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COMPETITIONS_DATA_DIR", "/tmp/legacy-holdouts")
    with pytest.raises(ValueError, match="COMPETITIONS_DATA_DIR"):
        Settings()


def test_dataset_roots_must_be_disjoint(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="overlaps"):
        Settings(
            training_data_root=tmp_path / "datasets",
            public_eval_data_root=tmp_path / "datasets" / "public-eval",
            test_holdouts_dir=tmp_path / "holdouts",
        )


def test_resolves_dataset_roots_to_absolute_paths(tmp_path: Path) -> None:
    settings = Settings(
        training_data_root=tmp_path / "train",
        public_eval_data_root=tmp_path / "public-eval",
        test_holdouts_dir=tmp_path / "holdouts",
    )

    assert settings.training_data_root == (tmp_path / "train").resolve(strict=False)
    assert settings.public_eval_data_root == (tmp_path / "public-eval").resolve(strict=False)
    assert settings.test_holdouts_dir == (tmp_path / "holdouts").resolve(strict=False)


def test_symlink_overlap_is_rejected(tmp_path: Path) -> None:
    training_root = tmp_path / "train"
    training_root.mkdir(parents=True)
    linked_eval = tmp_path / "linked-eval"

    try:
        linked_eval.symlink_to(training_root, target_is_directory=True)
    except OSError:
        pytest.skip("Symlink creation unavailable on this platform.")

    with pytest.raises(ValueError, match="overlaps"):
        Settings(
            training_data_root=training_root,
            public_eval_data_root=linked_eval,
            test_holdouts_dir=tmp_path / "holdouts",
        )
