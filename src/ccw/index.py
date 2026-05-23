from __future__ import annotations

import hashlib
import os
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from ccw.init import require_initialized_local_state, resolve_target_directory
from ccw.schema import bootstrap_index_database


EXCLUDED_DIRECTORIES = {".ccw", ".git"}

LANGUAGE_BY_SUFFIX = {
    ".py": "python",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "javascript",
    ".jsx": "javascript",
    ".md": "markdown",
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
}


@dataclass(frozen=True)
class FileRecord:
    path: str
    content_hash: str
    size_bytes: int
    language: str


def index_repository(target: Path) -> Path:
    resolved_target = resolve_target_directory(target, description="Index target")
    database_path = require_initialized_local_state(resolved_target)

    bootstrap_index_database(database_path)
    records = list(_collect_file_records(resolved_target))
    _replace_file_inventory(database_path, records)

    return database_path


def _collect_file_records(target: Path) -> list[FileRecord]:
    records: list[FileRecord] = []

    for root, directory_names, file_names in os.walk(target, topdown=True):
        root_path = Path(root)
        directory_names[:] = [
            directory_name
            for directory_name in sorted(directory_names)
            if directory_name not in EXCLUDED_DIRECTORIES and not (root_path / directory_name).is_symlink()
        ]

        for file_name in sorted(file_names):
            file_path = root_path / file_name

            if file_path.is_symlink() or not file_path.is_file():
                continue

            relative_path = file_path.relative_to(target).as_posix()
            file_bytes = file_path.read_bytes()
            records.append(
                FileRecord(
                    path=relative_path,
                    content_hash=hashlib.sha256(file_bytes).hexdigest(),
                    size_bytes=len(file_bytes),
                    language=_detect_language(file_path),
                )
            )

    return records


def _detect_language(path: Path) -> str:
    return LANGUAGE_BY_SUFFIX.get(path.suffix.lower(), "unknown")


def _replace_file_inventory(database_path: Path, records: list[FileRecord]) -> None:
    try:
        with sqlite3.connect(database_path) as connection:
            connection.execute("DELETE FROM files")
            connection.executemany(
                "INSERT INTO files (path, content_hash, size_bytes, language) VALUES (?, ?, ?, ?)",
                [(record.path, record.content_hash, record.size_bytes, record.language) for record in records],
            )
    except sqlite3.Error as error:
        raise ValueError(f"Failed to persist file inventory: {database_path}") from error
