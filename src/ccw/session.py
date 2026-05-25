from __future__ import annotations

import json
from pathlib import Path

from ccw.compile import do_compile
from ccw.init import resolve_target_directory


def prepare_session_bundle(
    target: Path,
    task_description: str,
    output_dir: Path | None = None,
    mode: str | None = None,
    budget: int | None = None,
) -> Path:
    resolved_target = resolve_target_directory(target, description="Session target")
    bundle_dir = _resolve_bundle_dir(resolved_target, output_dir)
    bundle_dir.mkdir(parents=True, exist_ok=True)

    compiled_context_path = bundle_dir / "compiled-context.md"
    do_compile(
        target=resolved_target,
        task_description=task_description,
        output_path=compiled_context_path,
        mode=mode,
        budget=budget,
    )

    frontmatter = _read_frontmatter(compiled_context_path)

    session_path = bundle_dir / "SESSION.md"
    session_path.write_text(
        _render_session_file(task_description, frontmatter.get("mode", "")),
        encoding="utf-8",
    )

    manifest_path = bundle_dir / "session.json"
    manifest_path.write_text(
        json.dumps(
            {
                "bundle_version": 1,
                "task_description": task_description,
                "mode": frontmatter.get("mode", ""),
                "budget": _parse_int(frontmatter.get("budget", "0")),
                "index_hash": frontmatter.get("index_hash", ""),
                "created_at": frontmatter.get("created_at", ""),
                "session_file": session_path.name,
                "compiled_artifact": compiled_context_path.name,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    return bundle_dir


def _resolve_bundle_dir(target: Path, output_dir: Path | None) -> Path:
    if output_dir is None:
        return target / ".ccw" / "session" / "latest"

    expanded_output_dir = output_dir.expanduser()
    if expanded_output_dir.is_absolute():
        return expanded_output_dir
    return target / expanded_output_dir


def _read_frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return {}

    lines = text.splitlines()
    frontmatter: dict[str, str] = {}
    for line in lines[1:]:
        if line == "---":
            break
        key, separator, value = line.partition(":")
        if separator:
            frontmatter[key.strip()] = value.strip()
    return frontmatter


def _render_session_file(task_description: str, mode: str) -> str:
    lines = [
        "# Session bundle",
        "",
        "This bundle is the grounded context for the task below on a first or later turn.",
        "Read `compiled-context.md` before re-gathering repository context.",
        "If the task or repo state no longer matches `session.json`, request a refreshed bundle instead of silently trusting stale context.",
        "",
        "## Task",
        "",
        f"- Description: {task_description}",
        f"- Mode: {mode or 'implementation'}",
        "- Compiled context: `compiled-context.md`",
        "- Metadata: `session.json`",
        "",
    ]
    return "\n".join(lines)


def _parse_int(raw_value: str) -> int:
    try:
        return int(raw_value)
    except ValueError:
        return 0
