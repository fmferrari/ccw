from __future__ import annotations

import re
import sqlite3
from pathlib import Path


_REQUIRED_FRONTMATTER_KEYS = ("mode", "budget", "index_hash", "created_at")
_REQUIRED_SECTIONS = ("Task",)


def validate_compiled_artifact(
    artifact_path: Path,
    database_path: Path | None = None,
) -> list[str]:
    errors: list[str] = []

    if not artifact_path.is_file():
        return [f"Artifact file not found: {artifact_path}"]

    try:
        text = artifact_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        return [f"Cannot read artifact: {e}"]

    # Check YAML frontmatter
    if not text.startswith("---"):
        errors.append("Missing YAML frontmatter: artifact must start with '---'")

    # Parse frontmatter
    frontmatter_end = text.find("---", 3)
    if frontmatter_end == -1:
        errors.append("Unclosed YAML frontmatter: missing closing '---'")
    else:
        frontmatter_text = text[3:frontmatter_end].strip()
        frontmatter_lines = frontmatter_text.splitlines()
        frontmatter_keys: set[str] = set()
        for line in frontmatter_lines:
            match = re.match(r"^(\w+):\s*(.*)", line)
            if match:
                frontmatter_keys.add(match.group(1))

        for key in _REQUIRED_FRONTMATTER_KEYS:
            if key not in frontmatter_keys:
                errors.append(f"Missing required frontmatter key: {key}")

    # Check required sections
    for section in _REQUIRED_SECTIONS:
        if f"## {section}" not in text:
            errors.append(f"Missing required section: {section}")

    # Cross-check file paths against index
    if database_path is not None and database_path.is_file():
        try:
            with sqlite3.connect(database_path) as connection:
                indexed_paths = {
                    row[0]
                    for row in connection.execute(
                        "SELECT path FROM files"
                    ).fetchall()
                }
        except sqlite3.Error as e:
            errors.append(f"Cannot query index database: {e}")
            indexed_paths = set()
    else:
        indexed_paths = set()

    if indexed_paths:
        # Find all backtick-quoted paths in the artifact
        referenced_paths = set(re.findall(r"`([^`]+)`", text))
        for ref_path in referenced_paths:
            # Only check paths that look like file paths with extensions
            if "." in ref_path and "/" in ref_path:
                if ref_path not in indexed_paths:
                    errors.append(f"Referenced file path not in index: {ref_path}")

    return errors
