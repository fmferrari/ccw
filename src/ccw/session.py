from __future__ import annotations

import hashlib
import json
from pathlib import Path

from ccw.compile import compute_index_hash, do_compile
from ccw.init import resolve_target_directory, require_initialized_local_state
from ccw.validate import validate_compiled_artifact


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


def validate_session_bundle(
    bundle_dir: Path,
    target: Path | None = None,
) -> list[str]:
    errors: list[str] = []

    required_files = ["SESSION.md", "compiled-context.md", "session.json"]
    for fname in required_files:
        if not (bundle_dir / fname).is_file():
            errors.append(f"Missing required bundle file: {fname}")

    if errors:
        return errors

    try:
        manifest = json.loads((bundle_dir / "session.json").read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        return [f"Cannot parse session.json: {e}"]

    frontmatter = _read_frontmatter(bundle_dir / "compiled-context.md")
    if not frontmatter:
        errors.append("compiled-context.md is missing or has no frontmatter")
        return errors

    for key in ("mode", "budget", "index_hash", "created_at"):
        manifest_val = str(manifest.get(key, ""))
        fm_val = str(frontmatter.get(key, ""))
        if manifest_val != fm_val:
            errors.append(
                f"session.json.{key} ('{manifest_val}') does not match "
                f"compiled-context.md frontmatter ('{fm_val}')"
            )

    if target is not None:
        try:
            resolved_target = resolve_target_directory(target, description="Session validate target")
            database_path = require_initialized_local_state(resolved_target)
            current_hash = compute_index_hash(database_path)
            stored_hash = manifest.get("index_hash", "")
            if current_hash and current_hash != stored_hash:
                errors.append(
                    f"index_hash mismatch: session.json has '{stored_hash}', "
                    f"current index is '{current_hash}'"
                )
        except (ValueError, FileNotFoundError, NotADirectoryError, PermissionError) as e:
            errors.append(f"Cannot check index freshness: {e}")

    return errors


def prepare_context_payload(
    target: Path,
    task_description: str,
    output_dir: Path | None = None,
    mode: str | None = None,
    budget: int | None = None,
) -> dict[str, object]:
    bundle_dir = prepare_session_bundle(
        target=target,
        task_description=task_description,
        output_dir=output_dir,
        mode=mode,
        budget=budget,
    )
    return read_compiled_context_payload(bundle_dir=bundle_dir, target=target)


def read_compiled_context_payload(
    bundle_dir: Path | None = None,
    artifact_path: Path | None = None,
    target: Path | None = None,
) -> dict[str, object]:
    if bundle_dir is None and artifact_path is None:
        return _empty_context_payload(["Either bundle_dir or artifact_path is required"])

    resolved_target: Path | None = None
    database_path: Path | None = None
    if target is not None:
        try:
            resolved_target = resolve_target_directory(target, description="Context payload target")
            database_path = require_initialized_local_state(resolved_target)
        except (ValueError, FileNotFoundError, NotADirectoryError, PermissionError) as e:
            return _empty_context_payload([f"Cannot check index freshness: {e}"])

    if bundle_dir is not None:
        return _payload_from_bundle(bundle_dir=bundle_dir, target=resolved_target, database_path=database_path)

    assert artifact_path is not None
    return _payload_from_artifact(artifact_path=artifact_path, target=resolved_target, database_path=database_path)


def _payload_from_bundle(
    bundle_dir: Path,
    target: Path | None,
    database_path: Path | None,
) -> dict[str, object]:
    errors = validate_session_bundle(bundle_dir=bundle_dir, target=target)
    session_path = bundle_dir / "SESSION.md"
    compiled_context_path = bundle_dir / "compiled-context.md"
    manifest_path = bundle_dir / "session.json"

    manifest: dict[str, object] = {}
    if manifest_path.is_file():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            errors.append(f"Cannot parse session.json: {e}")

    errors.extend(_validate_artifact_and_freshness(compiled_context_path, database_path))
    if errors:
        return _empty_context_payload(
            errors=errors,
            bundle_dir=bundle_dir,
            manifest=manifest,
            source_paths=_source_paths(bundle_dir, session_path, compiled_context_path, manifest_path),
        )

    session_instructions = session_path.read_text(encoding="utf-8")
    compiled_context = compiled_context_path.read_text(encoding="utf-8")
    return _context_payload(
        valid=True,
        errors=[],
        session_instructions=session_instructions,
        compiled_context=compiled_context,
        manifest=manifest,
        bundle_dir=bundle_dir,
        source_paths=_source_paths(bundle_dir, session_path, compiled_context_path, manifest_path),
    )


def _payload_from_artifact(
    artifact_path: Path,
    target: Path | None,
    database_path: Path | None,
) -> dict[str, object]:
    errors = _validate_artifact_and_freshness(artifact_path, database_path)
    frontmatter = _read_frontmatter(artifact_path) if artifact_path.is_file() else {}
    manifest: dict[str, object] = {
        "mode": frontmatter.get("mode", ""),
        "budget": _parse_int(frontmatter.get("budget", "0")),
        "index_hash": frontmatter.get("index_hash", ""),
        "created_at": frontmatter.get("created_at", ""),
        "compiled_artifact": artifact_path.name,
    }

    if errors:
        return _empty_context_payload(
            errors=errors,
            bundle_dir=artifact_path.parent,
            manifest=manifest,
            source_paths={
                "session_file": "",
                "compiled_context": artifact_path.as_posix(),
                "manifest": "",
            },
        )

    compiled_context = artifact_path.read_text(encoding="utf-8")
    return _context_payload(
        valid=True,
        errors=[],
        session_instructions="",
        compiled_context=compiled_context,
        manifest=manifest,
        bundle_dir=artifact_path.parent,
        source_paths={
            "session_file": "",
            "compiled_context": artifact_path.as_posix(),
            "manifest": "",
        },
    )


def _validate_artifact_and_freshness(
    compiled_context_path: Path,
    database_path: Path | None,
) -> list[str]:
    errors = validate_compiled_artifact(compiled_context_path, database_path=database_path)
    if database_path is not None and compiled_context_path.is_file():
        frontmatter = _read_frontmatter(compiled_context_path)
        stored_hash = frontmatter.get("index_hash", "")
        current_hash = compute_index_hash(database_path)
        if current_hash and stored_hash and current_hash != stored_hash:
            errors.append(
                f"index_hash mismatch: compiled artifact has '{stored_hash}', "
                f"current index is '{current_hash}'"
            )
    return errors


def _context_payload(
    valid: bool,
    errors: list[str],
    session_instructions: str,
    compiled_context: str,
    manifest: dict[str, object],
    bundle_dir: Path,
    source_paths: dict[str, str],
) -> dict[str, object]:
    encoded = compiled_context.encode("utf-8")
    return {
        "valid": valid,
        "errors": errors,
        "session_instructions": session_instructions,
        "compiled_context": compiled_context,
        "manifest": manifest,
        "content_hash": hashlib.sha256(encoded).hexdigest(),
        "content_bytes": len(encoded),
        "content_chars": len(compiled_context),
        "index_hash": str(manifest.get("index_hash", "")),
        "created_at": str(manifest.get("created_at", "")),
        "mode": str(manifest.get("mode", "")),
        "budget": int(manifest.get("budget", 0) or 0),
        "bundle_dir": bundle_dir.as_posix(),
        "source_paths": source_paths,
    }


def _empty_context_payload(
    errors: list[str],
    bundle_dir: Path | None = None,
    manifest: dict[str, object] | None = None,
    source_paths: dict[str, str] | None = None,
) -> dict[str, object]:
    return _context_payload(
        valid=False,
        errors=errors,
        session_instructions="",
        compiled_context="",
        manifest=manifest or {},
        bundle_dir=bundle_dir or Path(""),
        source_paths=source_paths or {
            "session_file": "",
            "compiled_context": "",
            "manifest": "",
        },
    )


def _source_paths(
    bundle_dir: Path,
    session_path: Path,
    compiled_context_path: Path,
    manifest_path: Path,
) -> dict[str, str]:
    return {
        "session_file": session_path.as_posix(),
        "compiled_context": compiled_context_path.as_posix(),
        "manifest": manifest_path.as_posix(),
    }
