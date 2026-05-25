from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from ccw.session import prepare_session_bundle, validate_session_bundle

ROOT = Path(__file__).resolve().parents[1]


def make_compiled_context(bundle_dir: Path, frontmatter: dict[str, str]) -> None:
    lines = ["---"]
    for key, value in frontmatter.items():
        lines.append(f"{key}: {value}")
    lines.append("---")
    lines.append("")
    lines.append("## Task")
    lines.append("")
    lines.append("Some compiled context content.")
    (bundle_dir / "compiled-context.md").write_text("\n".join(lines), encoding="utf-8")


class ValidateSessionBundleTests(unittest.TestCase):
    def test_validates_fresh_bundle(self) -> None:
        bundle_dir = Path(tempfile.mkdtemp())
        manifest = {
            "bundle_version": 1,
            "task_description": "Fix login bug",
            "mode": "implementation",
            "budget": 2000,
            "index_hash": "abc123def456",
            "created_at": "2026-05-25T12:00:00Z",
            "session_file": "SESSION.md",
            "compiled_artifact": "compiled-context.md",
        }
        (bundle_dir / "session.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        (bundle_dir / "SESSION.md").write_text("# Session bundle\n", encoding="utf-8")
        make_compiled_context(
            bundle_dir,
            {"mode": "implementation", "budget": "2000", "index_hash": "abc123def456", "created_at": "2026-05-25T12:00:00Z"},
        )
        errors = validate_session_bundle(bundle_dir)
        self.assertEqual(errors, [])

    def test_fails_on_missing_files(self) -> None:
        bundle_dir = Path(tempfile.mkdtemp())
        (bundle_dir / "SESSION.md").write_text("# Session bundle\n", encoding="utf-8")
        errors = validate_session_bundle(bundle_dir)
        self.assertIn("compiled-context.md", " ".join(errors))
        self.assertIn("session.json", " ".join(errors))

    def test_fails_on_invalid_manifest_json(self) -> None:
        bundle_dir = Path(tempfile.mkdtemp())
        (bundle_dir / "SESSION.md").write_text("# Session bundle\n", encoding="utf-8")
        (bundle_dir / "compiled-context.md").write_text("---\nmode: test\n---\n", encoding="utf-8")
        (bundle_dir / "session.json").write_text("not json\n", encoding="utf-8")
        errors = validate_session_bundle(bundle_dir)
        self.assertTrue(any("Cannot parse session.json" in e for e in errors))

    def test_fails_on_frontmatter_mismatch(self) -> None:
        bundle_dir = Path(tempfile.mkdtemp())
        manifest = {
            "bundle_version": 1,
            "mode": "implementation",
            "budget": 2000,
            "index_hash": "abc123def456",
            "created_at": "2026-05-25T12:00:00Z",
            "session_file": "SESSION.md",
            "compiled_artifact": "compiled-context.md",
        }
        (bundle_dir / "session.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        (bundle_dir / "SESSION.md").write_text("# Session bundle\n", encoding="utf-8")
        make_compiled_context(
            bundle_dir,
            {"mode": "review", "budget": "2000", "index_hash": "abc123def456", "created_at": "2026-05-25T12:00:00Z"},
        )
        errors = validate_session_bundle(bundle_dir)
        self.assertTrue(any("session.json.mode" in e for e in errors))

    def test_fails_on_index_hash_mismatch(self) -> None:
        bundle_dir = Path(tempfile.mkdtemp())
        manifest = {
            "bundle_version": 1,
            "mode": "implementation",
            "budget": 2000,
            "index_hash": "abc123def456",
            "created_at": "2026-05-25T12:00:00Z",
            "session_file": "SESSION.md",
            "compiled_artifact": "compiled-context.md",
        }
        (bundle_dir / "session.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        (bundle_dir / "SESSION.md").write_text("# Session bundle\n", encoding="utf-8")
        make_compiled_context(
            bundle_dir,
            {"mode": "implementation", "budget": "2000", "index_hash": "different_hash_456", "created_at": "2026-05-25T12:00:00Z"},
        )
        errors = validate_session_bundle(bundle_dir)
        self.assertTrue(any("session.json.index_hash" in e for e in errors))

    def test_fails_on_missing_frontmatter(self) -> None:
        bundle_dir = Path(tempfile.mkdtemp())
        manifest = {
            "bundle_version": 1,
            "mode": "implementation",
            "budget": 2000,
            "index_hash": "abc123def456",
            "created_at": "2026-05-25T12:00:00Z",
            "session_file": "SESSION.md",
            "compiled_artifact": "compiled-context.md",
        }
        (bundle_dir / "session.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        (bundle_dir / "SESSION.md").write_text("# Session bundle\n", encoding="utf-8")
        (bundle_dir / "compiled-context.md").write_text("No frontmatter here\n", encoding="utf-8")
        errors = validate_session_bundle(bundle_dir)
        self.assertTrue(any("no frontmatter" in e for e in errors))


if __name__ == "__main__":
    unittest.main()
