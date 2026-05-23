from __future__ import annotations

import os
from pathlib import Path

from ccw.config import default_config_text
from ccw.schema import bootstrap_index_database


def init_local_state(target: Path) -> Path:
    resolved_target = target.expanduser().resolve()
    _validate_target(resolved_target)

    state_dir = resolved_target / ".ccw"
    compiled_dir = state_dir / "compiled"
    snapshots_dir = state_dir / "snapshots"
    config_path = state_dir / "config.yaml"
    database_path = state_dir / "index.sqlite"

    _validate_runtime_paths(state_dir, compiled_dir, snapshots_dir, config_path, database_path)

    _ensure_directory(state_dir, "Local state path")
    _ensure_directory(compiled_dir, "Compiled artifact directory")
    _ensure_directory(snapshots_dir, "Snapshots directory")

    bootstrap_index_database(database_path)

    if not config_path.exists():
        config_path.write_text(default_config_text(), encoding="utf-8")

    return state_dir


def _validate_target(target: Path) -> None:
    if not target.exists():
        raise FileNotFoundError(f"Init target does not exist: {target}")
    if not target.is_dir():
        raise NotADirectoryError(f"Init target is not a directory: {target}")
    if not os.access(target, os.W_OK | os.X_OK):
        raise PermissionError(f"Init target is not writable: {target}")


def _validate_runtime_paths(
    state_dir: Path,
    compiled_dir: Path,
    snapshots_dir: Path,
    config_path: Path,
    database_path: Path,
) -> None:
    _validate_directory_path(state_dir, "Local state path")
    _validate_directory_path(compiled_dir, "Compiled artifact directory")
    _validate_directory_path(snapshots_dir, "Snapshots directory")
    _validate_file_path(config_path, "Config path")
    _validate_file_path(database_path, "Index database path")


def _validate_directory_path(path: Path, description: str) -> None:
    if path.exists() and not path.is_dir():
        raise ValueError(f"{description} exists as a file: {path}")


def _validate_file_path(path: Path, description: str) -> None:
    if path.exists() and not path.is_file():
        raise ValueError(f"{description} exists as a directory: {path}")


def _ensure_directory(path: Path, description: str) -> None:
    if path.exists():
        if not path.is_dir():
            raise ValueError(f"{description} exists as a file: {path}")
        return

    path.mkdir()
