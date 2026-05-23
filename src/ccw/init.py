from __future__ import annotations

import os
from pathlib import Path

from ccw.config import default_config_text


def init_local_state(target: Path) -> Path:
    resolved_target = target.expanduser().resolve()
    _validate_target(resolved_target)

    state_dir = resolved_target / ".ccw"
    _ensure_directory(state_dir, "Local state path")
    _ensure_directory(state_dir / "compiled", "Compiled artifact directory")
    _ensure_directory(state_dir / "snapshots", "Snapshots directory")

    config_path = state_dir / "config.yaml"
    if config_path.exists() and not config_path.is_file():
        raise ValueError(f"Config path exists as a directory: {config_path}")
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


def _ensure_directory(path: Path, description: str) -> None:
    if path.exists():
        if not path.is_dir():
            raise ValueError(f"{description} exists as a file: {path}")
        return

    path.mkdir()
