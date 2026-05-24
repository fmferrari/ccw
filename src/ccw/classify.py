from __future__ import annotations

import datetime
import sqlite3
from pathlib import Path

from ccw.init import require_initialized_local_state, resolve_target_directory
from ccw.schema import bootstrap_index_database


CLASSIFICATION_MODES = ("bugfix", "implementation", "review", "refactor")

_KEYWORDS: dict[str, tuple[str, ...]] = {
    "review": ("review", "audit", "inspect", "check", "verify"),
    "bugfix": ("fix", "bug", "error", "crash", "broken", "defect"),
    "refactor": ("refactor", "restructure", "clean", "improve", "simplify", "extract", "consolidate", "rename", "optimize", "modernize", "migrate"),
    "implementation": ("implement", "add", "feature", "create", "build", "write", "new"),
}


def classify(target: Path, text: str) -> str:
    resolved_target = resolve_target_directory(target, description="Classify target")
    database_path = require_initialized_local_state(resolved_target)

    normalized_text = text.strip()
    if not normalized_text:
        raise ValueError("Classification text must not be empty")

    bootstrap_index_database(database_path)

    mode = _determine_mode(normalized_text)

    created_at = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")

    try:
        with sqlite3.connect(database_path) as connection:
            connection.execute(
                "INSERT INTO classifications (text, mode, created_at) VALUES (?, ?, ?)",
                (normalized_text, mode, created_at),
            )
    except sqlite3.Error as error:
        raise ValueError(f"Failed to persist classification: {database_path}") from error

    return mode


def _determine_mode(text: str) -> str:
    tokens = text.lower().split()
    scores: dict[str, int] = {mode: 0 for mode in CLASSIFICATION_MODES}

    for token in tokens:
        for mode, keywords in _KEYWORDS.items():
            if token in keywords:
                scores[mode] += 1

    max_score = max(scores.values())
    if max_score == 0:
        return "implementation"

    candidates = [mode for mode, score in scores.items() if score == max_score]

    tie_priority: dict[str, int] = {"review": 0, "bugfix": 1, "refactor": 2, "implementation": 3}
    candidates.sort(key=lambda m: tie_priority[m])

    return candidates[0]
