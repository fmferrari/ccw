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
from ccw.session import (
    prepare_context_payload as build_context_payload,
    prepare_session_bundle,
    read_compiled_context_payload,
    validate_session_bundle,
)
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
    """Initialize CCW local state for a repository.

    Call this FIRST on any repo before calling any other CCW tool.
    Creates a `.ccw/` directory with SQLite database and config file.
    Safe to call again on an already-initialized repo (idempotent).

    Full workflow order:
      1. init_repo      — run once per repo (or after a clean)
      2. index_repo     — run after init and after any file changes
      3. record_fact    — optional: add constraints/decisions that code doesn't capture
      4. prepare_session — compile + package context for a specific task
      5. validate_session — confirm the bundle is fresh before handing to a model
      6. update_memory  — run after a task completes to record what changed

    Args:
        target_path: Absolute path to the repository root. If empty, uses the
                     CCW_TARGET_ROOT environment variable, then the current directory.

    Returns:
        target_path: Resolved absolute path to the repo root.
        state_dir: Path to the created `.ccw/` directory.
        database_path: Path to the SQLite index database.
        config_path: Path to the CCW config file.
    """
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
    """Index a repository into deterministic CCW local state.

    Walks the repo and extracts files, symbols (classes, functions), import/export
    edges, git recency signals, and document artifacts into a local SQLite database.
    Must be called after init_repo and again whenever files change (update_memory
    does this automatically as part of post-run bookkeeping).

    Excluded automatically: .git, .venv, __pycache__, node_modules, browser-data,
    .playwright-profile, .openclaw, logs, tmp, build, dist, and other common cache
    directories.

    Args:
        target_path: Absolute path to the repository root. Defaults to CCW_TARGET_ROOT
                     or the current directory.

    Returns:
        target_path: Resolved repo root.
        database_path: Path to the updated SQLite index.
        snapshot_path: Path to the JSON snapshot of the index.
        file_count: Total indexed files.
        symbol_count: Total extracted symbols (classes, functions).
        edge_count: Total import/export edges.
        artifact_count: Total document artifacts (markdown, yaml, json).
    """
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
    """Append one explicit project fact that the raw code does not capture.

    Facts are injected into every future compiled context artifact, giving a model
    architectural memory that persists across tasks. Use this to record constraints,
    decisions, and preferences before compiling context for a task.

    Valid kind values:
        "constraint"  — a hard rule the implementation must not violate
                        (e.g. "Never log plaintext passwords")
        "decision"    — an architecture or design choice that was made
                        (e.g. "Hermes owns Telegram transport; direct-runner is fallback")
        "preference"  — a style or convention preference
                        (e.g. "Use dataclasses over dicts for structured data")
        "goal"        — a high-level objective for the project

    Facts are append-only. To supersede a fact, add a new one with the same kind
    and a note that it replaces the previous one.

    Args:
        kind: Category of fact. Validated lowercase values: constraint, decision,
              preference, goal.
        text: The fact content. Be specific and actionable.
        target_path: Repo root. Defaults to CCW_TARGET_ROOT.

    Returns:
        kind: Normalized kind that was stored.
        text: The fact text that was stored.
    """
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
    """Append one explicit completed-run episode to the project memory.

    Episodes are run-history entries: what was done, when, and which files changed.
    They appear in the 'Episodes' section of future compiled context artifacts so
    a model has grounded run history without reading chat transcripts.

    Prefer update_memory over calling record_episode directly: update_memory also
    re-indexes the repo so the next compile sees current file state. Use
    record_episode directly only when you want to record a past event without
    triggering a re-index.

    Args:
        summary: One-sentence description of what the run accomplished.
                 Example: "Fixed the login handler to reject empty credentials."
        touched_files: List of repo-relative file paths that were modified.
                       Example: ["src/auth/login.py", "tests/test_login.py"]
        target_path: Repo root. Defaults to CCW_TARGET_ROOT.

    Returns:
        summary: The summary that was stored.
        touched_files: Normalized list of file paths that were stored.
    """
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
    """Classify a task description into a deterministic CCW compile mode.

    Classification is keyword-based and deterministic — no LLM involved.
    The returned mode controls which recipe (file cap, section weights, token budget)
    is used by compile_task_context and prepare_session.

    Modes and their default budgets:
        bugfix         — 6,000 tokens. Prioritizes the fewest relevant files and
                         tests. Use for defect fixes.
        implementation — 8,000 tokens. Broader file surface. Use for new features.
        review         — 8,000 tokens. Emphasizes tests and recent changes.
        docs           — 7,000 tokens. Prioritizes wiki/docs/spec evidence for
                         documentation and troubleshooting tasks.
        refactor       — 10,000 tokens. Widest file surface. Use for restructuring.

    You do not need to call this explicitly: prepare_session and
    compile_task_context both auto-classify when mode is not supplied.
    Call it directly only when you want to inspect or override the mode.

    Args:
        task_description: Free-text description of the task.
        target_path: Repo root. Defaults to CCW_TARGET_ROOT.

    Returns:
        mode: One of bugfix | implementation | review | docs | refactor.
        task_description: The input text that was classified.
    """
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
    """Compile a bounded, grounded, task-scoped context artifact for a repository.

    Runs the full compiler pipeline: classify → recipe → rank files → extract
    snippets → load facts and episodes → assemble → render to markdown.
    The output is a single markdown file with YAML frontmatter that a model can
    read as its authoritative view of the repo for this task.

    Use prepare_session instead when you want a portable bundle (SESSION.md +
    compiled-context.md + session.json) ready for direct model consumption.
    Use compile_task_context when you only need the compiled artifact path and
    metadata, or want a custom output location.

    The artifact cites only real indexed file paths. Run validate_compiled_artifact
    to confirm this after compile.

    Args:
        task_description: Free-text description of the task. Used for ranking
                          and classification.
        target_path: Repo root. Defaults to CCW_TARGET_ROOT.
        output_path: Where to write the artifact. Relative paths resolve against
                     target_path. Defaults to .ccw/compiled/latest.md.
        mode: Override compile mode. One of: bugfix, implementation, review,
              docs, refactor. If empty, auto-classifies from task_description.
        budget: Override token budget. If 0, uses the recipe default for the mode.

    Returns:
        artifact_path: Absolute path to the compiled markdown artifact.
        mode: The mode used (auto-detected or overridden).
        budget: The token budget applied.
        task: The task description stored with the compilation record.
        created_at: ISO 8601 timestamp of the compilation.
    """
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
    """Compile and package a portable session bundle for a task.

    This is the PRIMARY tool for giving a model grounded task context.
    It compiles a bounded context artifact and wraps it in three files:

        SESSION.md           — model-facing entry point. Instructs the model to
                               read compiled-context.md before re-gathering repo
                               context and to request a refresh if the bundle is stale.
        compiled-context.md  — the grounded, budgeted context artifact with ranked
                               files, line-anchored snippets, facts, episodes, and
                               constraints.
        session.json         — machine-readable metadata: task, mode, budget,
                               index_hash, and created_at timestamp.

    After receiving the bundle, a model should:
      1. Read SESSION.md for instructions.
      2. Use compiled-context.md as the authoritative repo state for the task.
      3. Check session.json.index_hash — if it no longer matches the current
         index, call prepare_session again to get a fresh bundle.

    Run validate_session after prepare_session to confirm the bundle is internally
    consistent and the index_hash is current before handing it to a model.

    Args:
        task_description: Free-text description of the task.
        target_path: Repo root. Defaults to CCW_TARGET_ROOT.
        output_dir: Where to write the bundle directory. Relative paths resolve
                    against target_path. Defaults to .ccw/session/latest/.
        mode: Override compile mode: bugfix | implementation | review | docs | refactor.
              If empty, auto-classifies.
        budget: Override token budget. If 0, uses the recipe default.

    Returns:
        bundle_dir: Absolute path to the session bundle directory.
        session_file: Absolute path to SESSION.md (model entry point).
        compiled_artifact: Absolute path to compiled-context.md.
        manifest_path: Absolute path to session.json.
        mode: Compile mode used.
        budget: Token budget applied.
        index_hash: Short hash of the index state at compile time.
        created_at: ISO 8601 timestamp.
    """
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
def prepare_context_payload(
    task_description: str,
    target_path: str = "",
    output_dir: str = "",
    mode: str = "",
    budget: int = 0,
) -> dict[str, object]:
    """Compile, validate, and return task context content in one MCP response.

    This is the portable ingestion tool for generic MCP-capable harnesses. It
    prepares the same session bundle as prepare_session, validates freshness and
    artifact grounding, then returns the actual SESSION.md instructions and
    compiled-context.md content directly in the tool payload.

    Use this first for non-trivial repository tasks when the harness cannot be
    trusted to read returned file paths on its own. The returned context is
    task-scoped and bounded by the compile recipe; it is not global prompt
    injection and should not be reused for unrelated tasks.

    Args:
        task_description: Free-text description of the task.
        target_path: Repo root. Defaults to CCW_TARGET_ROOT.
        output_dir: Where to write the backing bundle directory. Relative paths
                    resolve against target_path. Defaults to .ccw/session/latest/.
        mode: Override compile mode: bugfix | implementation | review | docs | refactor.
              If empty, auto-classifies.
        budget: Override token budget. If 0, uses the recipe default.

    Returns:
        valid: True only when the bundle and compiled artifact are fresh and valid.
        errors: Explicit validation errors when valid is False.
        session_instructions: Contents of SESSION.md.
        compiled_context: Contents of compiled-context.md.
        manifest: Parsed session.json metadata.
        content_hash: SHA-256 hash of compiled_context.
        content_bytes: UTF-8 byte count of compiled_context.
        content_chars: Character count of compiled_context.
        index_hash: Index hash recorded at compile time.
        created_at: Compilation timestamp.
        mode: Compile mode used.
        budget: Token budget applied.
        bundle_dir: Backing bundle directory path.
        source_paths: Paths for SESSION.md, compiled-context.md, and session.json.
    """
    target = _resolve_target_path(target_path)
    resolved_output_dir = Path(output_dir.strip()) if output_dir.strip() else None
    resolved_budget = budget if budget > 0 else None
    resolved_mode = mode.strip() or None
    payload = build_context_payload(
        target=target,
        task_description=task_description,
        output_dir=resolved_output_dir,
        mode=resolved_mode,
        budget=resolved_budget,
    )
    payload["target_path"] = target.as_posix()
    return payload


@mcp.tool()
def read_compiled_context(
    path: str,
    target_path: str = "",
) -> dict[str, object]:
    """Read an existing compiled artifact or session bundle as validated content.

    The path may point to a session bundle directory containing SESSION.md,
    compiled-context.md, and session.json, or directly to a compiled markdown
    artifact. In both cases the artifact is structurally validated and its
    index_hash must match the current repo index before compiled_context is
    returned. Stale or invalid inputs fail closed with compiled_context empty
    and explicit errors.

    Args:
        path: Bundle directory or compiled markdown artifact. Relative paths
              resolve against target_path.
        target_path: Repo root used for index freshness. Defaults to CCW_TARGET_ROOT.

    Returns:
        Same payload shape as prepare_context_payload.
    """
    target = _resolve_target_path(target_path)
    resolved_path = _resolve_repo_path(target, path, "Context path")
    if resolved_path.is_dir():
        payload = read_compiled_context_payload(bundle_dir=resolved_path, target=target)
    else:
        payload = read_compiled_context_payload(artifact_path=resolved_path, target=target)
    payload["target_path"] = target.as_posix()
    return payload


@mcp.tool()
def validate_session(bundle_dir: str, target_path: str = "") -> dict[str, object]:
    """Validate a portable session bundle and check freshness against the current index.

    Checks that SESSION.md, compiled-context.md, and session.json all exist, that
    the manifest metadata matches the compiled artifact frontmatter, and that the
    stored index_hash still matches the current repo index.

    A bundle becomes stale when files in the repo change after the bundle was
    prepared (e.g. after update_memory re-indexes). Always validate before
    handing a bundle to a model, and call prepare_session to refresh a stale bundle.

    Args:
        bundle_dir: Path to the session bundle directory. Relative paths resolve
                    against target_path.
        target_path: Repo root used for freshness check. Defaults to CCW_TARGET_ROOT.

    Returns:
        valid: True if the bundle is internally consistent and index_hash is current.
        errors: List of error strings. Empty when valid is True.
    """
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
    """Record a post-run memory update: re-index the repo, append an episode, and optionally a decision fact.

    Call this after completing any task that changed files. It does three things
    in one call:
      1. Re-runs index_repo so the next compile sees the current file state.
      2. Appends an episode (run summary + touched files) to the project memory.
      3. Optionally appends a decision fact if a key architecture choice was made.

    This is what closes the memory loop: the episode recorded here appears in
    the Episodes section of the next compiled context, giving future models
    grounded run history without reading chat transcripts.

    After update_memory, any previously prepared session bundle is stale
    (its index_hash no longer matches). Call prepare_session again for the
    next task.

    Args:
        summary: One-sentence description of what was accomplished.
                 Example: "Fixed the login handler to reject empty credentials."
        touched_files: Repo-relative paths of files that were modified.
                       Example: ["src/auth/login.py", "tests/test_login.py"]
        decision: Optional architecture or design decision to record as a fact.
                  Example: "Always validate credentials before creating a session."
                  If provided, stored as kind=decision for future compiles.
        target_path: Repo root. Defaults to CCW_TARGET_ROOT.

    Returns:
        summary: The summary that was stored.
        touched_files: Normalized list of file paths.
        decision: The decision fact text, or empty string if none was provided.
        state_dir: Path to the .ccw/ directory where state was updated.
    """
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
    """Validate one compiled context artifact for correctness and grounding.

    Checks that the artifact has valid YAML frontmatter with all required keys
    (mode, budget, index_hash, created_at), required sections (Task), and that
    every file path cited in the artifact exists in the current index. An artifact
    that passes validation contains no invented paths and is safe to hand to a model.

    You do not normally need to call this manually: prepare_session produces
    a valid artifact by construction. Use this for debugging or when consuming
    an artifact produced by compile_task_context with a custom output path.

    Args:
        artifact_path: Path to the compiled markdown artifact. Relative paths
                       resolve against target_path.
        target_path: Repo root used to locate the index for path validation.
                     Defaults to CCW_TARGET_ROOT.

    Returns:
        valid: True if all checks pass.
        errors: List of error strings describing failures. Empty when valid is True.
        artifact_path: Absolute path to the artifact that was checked.
    """
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
