from __future__ import annotations

from pathlib import Path

from ccw.episodes import add_episode
from ccw.facts import add_fact
from ccw.index import index_repository
from ccw.init import require_initialized_local_state, resolve_target_directory


def post_run_update(
    target: Path,
    summary: str,
    touched_files: str,
    decision: str | None = None,
) -> Path:
    resolved_target = resolve_target_directory(target, description="Update target")
    require_initialized_local_state(resolved_target)

    if not summary.strip():
        raise ValueError("Run summary must not be empty")

    index_repository(resolved_target)
    add_episode(resolved_target, summary, touched_files)

    if decision:
        add_fact(resolved_target, "decision", decision)

    return resolved_target / ".ccw"
