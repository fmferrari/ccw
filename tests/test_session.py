from __future__ import annotations

import json
import hashlib
import tempfile
import unittest
from pathlib import Path

from ccw.init import init_local_state
from ccw.index import index_repository
from ccw.session import (
    prepare_context_payload,
    prepare_session_bundle,
    read_compiled_context_payload,
    validate_session_bundle,
)

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



class PrepareSessionBundleTests(unittest.TestCase):
    def test_session_md_instructs_consumer_to_use_compiled_context_first(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir)
            init_local_state(target)
            src = target / "src"
            src.mkdir()
            (src / "auth.py").write_text("def login():\n    pass\n", encoding="utf-8")
            index_repository(target)

            bundle_dir = prepare_session_bundle(
                target=target,
                task_description="Fix login bug",
            )
            session_text = (bundle_dir / "SESSION.md").read_text(encoding="utf-8")

            self.assertIn("before re-gathering", session_text)
            self.assertIn("request a refreshed bundle", session_text)
            self.assertIn("compiled-context.md", session_text)
            self.assertIn("session.json", session_text)
            self.assertIn("Fix login bug", session_text)

    def test_session_md_includes_mode_in_instructions(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir)
            init_local_state(target)
            src = target / "src"
            src.mkdir()
            (src / "review.py").write_text("def review_changes():\n    pass\n", encoding="utf-8")
            index_repository(target)

            bundle_dir = prepare_session_bundle(
                target=target,
                task_description="Review auth code",
                mode="review",
            )
            session_text = (bundle_dir / "SESSION.md").read_text(encoding="utf-8")

            self.assertIn("before re-gathering", session_text)
            self.assertIn("request a refreshed bundle", session_text)
            self.assertIn("review", session_text)


class ContextPayloadTests(unittest.TestCase):
    def test_prepare_context_payload_returns_validated_content_and_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir)
            init_local_state(target)
            src = target / "src"
            src.mkdir()
            (src / "auth.py").write_text("def login_handler(user):\n    return user\n", encoding="utf-8")
            index_repository(target)

            payload = prepare_context_payload(
                target=target,
                task_description="Fix the login handler",
                mode="bugfix",
            )

            self.assertTrue(payload["valid"], payload["errors"])
            self.assertEqual(payload["errors"], [])
            self.assertIn("before re-gathering", str(payload["session_instructions"]))
            self.assertIn("src/auth.py", str(payload["compiled_context"]))
            self.assertIn("Fix the login handler", str(payload["compiled_context"]))
            self.assertEqual(payload["mode"], "bugfix")
            self.assertGreater(int(payload["budget"]), 0)
            self.assertGreater(int(payload["content_bytes"]), 0)
            self.assertGreater(int(payload["content_chars"]), 0)
            self.assertEqual(
                payload["content_hash"],
                hashlib.sha256(str(payload["compiled_context"]).encode("utf-8")).hexdigest(),
            )
            source_paths = payload["source_paths"]
            self.assertIsInstance(source_paths, dict)
            self.assertTrue(Path(str(source_paths["session_file"])).is_file())
            self.assertTrue(Path(str(source_paths["compiled_context"])).is_file())
            self.assertTrue(Path(str(source_paths["manifest"])).is_file())

    def test_read_compiled_context_payload_fails_closed_on_stale_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir)
            init_local_state(target)
            src = target / "src"
            src.mkdir()
            (src / "auth.py").write_text("def login_handler(user):\n    return user\n", encoding="utf-8")
            index_repository(target)

            bundle_dir = prepare_session_bundle(
                target=target,
                task_description="Fix the login handler",
            )
            (src / "session_store.py").write_text("def issue_token(user):\n    return user\n", encoding="utf-8")
            index_repository(target)

            payload = read_compiled_context_payload(bundle_dir=bundle_dir, target=target)

            self.assertFalse(payload["valid"])
            self.assertEqual(payload["compiled_context"], "")
            self.assertTrue(any("index_hash mismatch" in error for error in payload["errors"]))

    def test_read_compiled_context_payload_fails_closed_on_invalid_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir)
            init_local_state(target)
            src = target / "src"
            src.mkdir()
            (src / "auth.py").write_text("def login_handler(user):\n    return user\n", encoding="utf-8")
            index_repository(target)

            artifact_path = target / ".ccw" / "compiled" / "broken.md"
            artifact_path.parent.mkdir(parents=True, exist_ok=True)
            artifact_path.write_text("# Broken context\n", encoding="utf-8")

            payload = read_compiled_context_payload(artifact_path=artifact_path, target=target)

            self.assertFalse(payload["valid"])
            self.assertEqual(payload["compiled_context"], "")
            self.assertTrue(any("frontmatter" in error for error in payload["errors"]))


if __name__ == "__main__":
    unittest.main()
