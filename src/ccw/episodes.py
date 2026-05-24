from __future__ import annotations

import datetime
import json
import sqlite3
from pathlib import Path, PurePosixPath

from ccw.init import require_initialized_local_state, resolve_target_directory
from ccw.schema import bootstrap_index_database


def add_episode(target: Path, summary: str, touched_files: str) -> Path:
    resolved_target = resolve_target_directory(target, description="Episode target")
    database_path = require_initialized_local_state(resolved_target)

    normalized_summary = summary.strip()
    if not normalized_summary:
        raise ValueError("Episode summary must not be empty")

    normalized_files = _normalize_touched_files(touched_files)
    if not normalized_files:
        raise ValueError("Episode touched files must not be empty")

    bootstrap_index_database(database_path)

    created_at = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")

    try:
        with sqlite3.connect(database_path) as connection:
            connection.execute(
                "INSERT INTO episodes (summary, touched_files, created_at) VALUES (?, ?, ?)",
                (normalized_summary, json.dumps(normalized_files), created_at),
            )
    except sqlite3.Error as error:
        raise ValueError(f"Failed to persist episode: {database_path}") from error

    return database_path


def _normalize_touched_files(touched_files: str) -> list[str]:
    normalized_files: set[str] = set()
    for raw_path in touched_files.split(","):
        candidate = raw_path.strip()
        if not candidate:
            continue

        pure_path = PurePosixPath(candidate)
        if pure_path.is_absolute() or any(part == ".." for part in pure_path.parts):
            raise ValueError(f"Invalid touched file path: {candidate}")

        normalized_parts = [part for part in pure_path.parts if part not in {"", "."}]
        if not normalized_parts:
            raise ValueError(f"Invalid touched file path: {candidate}")

        normalized_files.add(PurePosixPath(*normalized_parts).as_posix())

    return sorted(normalized_files)
