from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from ccw.classify import classify as classify_text
from ccw.compile import do_compile
from ccw.episodes import add_episode as persist_episode
from ccw.facts import add_fact as persist_fact
from ccw.index import index_repository
from ccw.init import init_local_state, require_initialized_local_state, resolve_target_directory
from ccw.session import prepare_session_bundle, validate_session_bundle
from ccw.update import post_run_update
from ccw.validate import validate_compiled_artifact as validate_artifact_file


DEFAULT_TARGET_ENV = "CCW_TARGET_ROOT"

mcp = FastMCP("ccw")


def _resolve_target_path(target_path: str = "") -> Path:
    raw_target = str(target_path or "").strip() or os.getenv(DEFAULT_TARGET_ENV, "").strip() or "."
    return resolve_target_directory(Path(raw_target), description="CCW target")


def _resolve_repo_path(target: Path, candidate: str, description: str) -> Path:
    raw_candidate = str(candidate or "").strip()
    if not raw_candidate:
        raise ValueError(f"{description} must not be empty")

    path = Path(raw_candidate).expanduser()
    if not path.is_absolute():
        path = target / path

    return path.resolve()


def _index_counts(database_path: Path) -> dict[str, int]:
    with sqlite3.connect(database_path) as connection:
        file_count = connection.execute("SELECT COUNT(*) FROM files").fetchone()[0]
        symbol_count = connection.execute("SELECT COUNT(*) FROM symbols").fetchone()[0]
        edge_count = connection.execute("SELECT COUNT(*) FROM edges").fetchone()[0]
        artifact_count = connection.execute("SELECT COUNT(*) FROM artifacts").fetchone()[0]

    return {
        "file_count": int(file_count),
        "symbol_count": int(symbol_count),
        "edge_count": int(edge_count),
        "artifact_count": int(artifact_count),
    }


def _latest_compilation(database_path: Path, output_path: Path) -> dict[str, int | str] | None:
    with sqlite3.connect(database_path) as connection:
        row = connection.execute(
            "SELECT task, mode, budget, output_path, created_at "
            "FROM compilations WHERE output_path = ? ORDER BY id DESC LIMIT 1",
            (str(output_path),),
        ).fetchone()

    if row is None:
        return None

    return {
        "task": str(row[0]),
        "mode": str(row[1]),
        "budget": int(row[2]),
        "output_path": str(row[3]),
        "created_at": str(row[4]),
    }


@mcp.tool()
def init_repo(target_path: str = "") -> dict[str, str]:
    """Initialize CCW local state for a repository."""
    target = _resolve_target_path(target_path)
    state_dir = init_local_state(target)
    return {
        "target_path": target.as_posix(),
        "state_dir": state_dir.as_posix(),
        "database_path": (state_dir / "index.sqlite").as_posix(),
        "config_path": (state_dir / "config.yaml").as_posix(),
    }


@mcp.tool()
def index_repo(target_path: str = "") -> dict[str, int | str]:
    """Index a repository into deterministic CCW local state."""
    target = _resolve_target_path(target_path)
    database_path = index_repository(target)
    payload: dict[str, int | str] = {
        "target_path": target.as_posix(),
        "database_path": database_path.as_posix(),
        "snapshot_path": (database_path.parent / "snapshots" / "index.json").as_posix(),
    }
    payload.update(_index_counts(database_path))
    return payload


@mcp.tool()
def record_fact(kind: str, text: str, target_path: str = "") -> dict[str, str]:
    """Append one explicit project fact."""
    target = _resolve_target_path(target_path)
    database_path = persist_fact(target, kind, text)
    return {
        "target_path": target.as_posix(),
        "database_path": database_path.as_posix(),
        "kind": kind.strip().lower(),
        "text": text.strip(),
    }


@mcp.tool()
def record_episode(summary: str, touched_files: list[str], target_path: str = "") -> dict[str, object]:
    """Append one explicit completed-run episode."""
    target = _resolve_target_path(target_path)
    normalized_files = [str(path).strip() for path in touched_files if str(path).strip()]
    database_path = persist_episode(target, summary, ",".join(normalized_files))
    return {
        "target_path": target.as_posix(),
        "database_path": database_path.as_posix(),
        "summary": summary.strip(),
        "touched_files": normalized_files,
    }


@mcp.tool()
def classify_task(task_description: str, target_path: str = "") -> dict[str, str]:
    """Classify a task into a deterministic CCW mode."""
    target = _resolve_target_path(target_path)
    mode = classify_text(target, task_description)
    return {
        "target_path": target.as_posix(),
        "task_description": task_description.strip(),
        "mode": mode,
    }


@mcp.tool()
def compile_task_context(
    task_description: str,
    target_path: str = "",
    output_path: str = "",
    mode: str = "",
    budget: int = 0,
) -> dict[str, int | str]:
    """Compile a task-scoped context artifact for a repository."""
    target = _resolve_target_path(target_path)
    resolved_output_path = _resolve_repo_path(target, output_path, "Output path") if output_path.strip() else None
    resolved_budget = budget if budget > 0 else None
    resolved_mode = mode.strip() or None
    artifact_path = do_compile(
        target=target,
        task_description=task_description,
        output_path=resolved_output_path,
        mode=resolved_mode,
        budget=resolved_budget,
    )

    database_path = require_initialized_local_state(target)
    latest = _latest_compilation(database_path, artifact_path)

    payload: dict[str, int | str] = {
        "target_path": target.as_posix(),
        "database_path": database_path.as_posix(),
        "artifact_path": artifact_path.as_posix(),
    }
    if latest is not None:
        payload.update(latest)
    return payload


@mcp.tool()
def prepare_session(
    task_description: str,
    target_path: str = "",
    output_dir: str = "",
    mode: str = "",
    budget: int = 0,
) -> dict[str, object]:
    """Prepare a portable session bundle that a model can consume on a first or later turn."""
    target = _resolve_target_path(target_path)
    resolved_output_dir = Path(output_dir.strip()) if output_dir.strip() else None
    resolved_budget = budget if budget > 0 else None
    resolved_mode = mode.strip() or None
    bundle_dir = prepare_session_bundle(
        target=target,
        task_description=task_description,
        output_dir=resolved_output_dir,
        mode=resolved_mode,
        budget=resolved_budget,
    )

    manifest_path = bundle_dir / "session.json"
    manifest: dict[str, object] = {}
    if manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    return {
        "target_path": target.as_posix(),
        "bundle_dir": bundle_dir.as_posix(),
        "session_file": (bundle_dir / "SESSION.md").as_posix(),
        "compiled_artifact": (bundle_dir / "compiled-context.md").as_posix(),
        "manifest_path": manifest_path.as_posix(),
        "mode": str(manifest.get("mode", "")),
        "budget": int(manifest.get("budget", 0) or 0),
        "index_hash": str(manifest.get("index_hash", "")),
        "created_at": str(manifest.get("created_at", "")),
    }


@mcp.tool()
def validate_session(bundle_dir: str, target_path: str = "") -> dict[str, object]:
    """Validate a portable session bundle and check freshness against the current index."""
    target = _resolve_target_path(target_path)
    resolved_bundle_dir = _resolve_repo_path(target, bundle_dir, "Bundle directory")
    errors = validate_session_bundle(bundle_dir=resolved_bundle_dir, target=target)
    return {
        "target_path": target.as_posix(),
        "bundle_dir": resolved_bundle_dir.as_posix(),
        "valid": not errors,
        "errors": errors,
    }


@mcp.tool()
def update_memory(
    summary: str,
    touched_files: list[str],
    decision: str = "",
    target_path: str = "",
) -> dict[str, object]:
    """Record a post-run memory update: re-index, append an episode, and optionally a decision fact."""
    target = _resolve_target_path(target_path)
    normalized_files = [str(path).strip() for path in touched_files if str(path).strip()]
    resolved_decision = decision.strip() or None
    state_dir = post_run_update(
        target=target,
        summary=summary,
        touched_files=",".join(normalized_files),
        decision=resolved_decision,
    )
    return {
        "target_path": target.as_posix(),
        "state_dir": state_dir.as_posix(),
        "summary": summary.strip(),
        "touched_files": normalized_files,
        "decision": resolved_decision or "",
    }


@mcp.tool()
def validate_compiled_artifact(artifact_path: str, target_path: str = "") -> dict[str, object]:
    """Validate one compiled context artifact."""
    target = _resolve_target_path(target_path)
    resolved_artifact_path = _resolve_repo_path(target, artifact_path, "Artifact path")

    database_path = None
    try:
        database_path = require_initialized_local_state(target)
    except ValueError:
        database_path = None

    errors = validate_artifact_file(
        artifact_path=resolved_artifact_path,
        database_path=database_path,
    )
    return {
        "target_path": target.as_posix(),
        "artifact_path": resolved_artifact_path.as_posix(),
        "database_path": database_path.as_posix() if database_path is not None else "",
        "valid": not errors,
        "errors": errors,
    }


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
