from __future__ import annotations

import datetime
import sqlite3
from pathlib import Path

from ccw.init import require_initialized_local_state, resolve_target_directory
from ccw.schema import bootstrap_index_database


ALLOWED_FACT_KINDS = {"goal", "constraint", "decision", "preference"}


def add_fact(target: Path, kind: str, text: str) -> Path:
    resolved_target = resolve_target_directory(target, description="Fact target")
    database_path = require_initialized_local_state(resolved_target)

    normalized_kind = kind.strip().lower()
    normalized_text = text.strip()
    if normalized_kind not in ALLOWED_FACT_KINDS:
        allowed = ", ".join(sorted(ALLOWED_FACT_KINDS))
        raise ValueError(f"Unsupported fact kind: {kind}. Allowed kinds: {allowed}")
    if not normalized_text:
        raise ValueError("Fact text must not be empty")

    bootstrap_index_database(database_path)

    created_at = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")

    try:
        with sqlite3.connect(database_path) as connection:
            connection.execute(
                "INSERT INTO facts (kind, text, created_at) VALUES (?, ?, ?)",
                (normalized_kind, normalized_text, created_at),
            )
    except sqlite3.Error as error:
        raise ValueError(f"Failed to persist fact: {database_path}") from error

    return database_path
