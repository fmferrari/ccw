from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


from ccw.mcp_server import (  # noqa: E402
    classify_task,
    compile_task_context,
    index_repo,
    init_repo,
    prepare_context_payload,
    read_compiled_context,
    record_episode,
    record_fact,
    validate_compiled_artifact,
)


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


class McpServerTests(unittest.TestCase):
    def test_mcp_tools_support_explicit_target_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "repo"
            target.mkdir()
            write_text(target / "src" / "auth" / "login.py", "def login_handler(user):\n    return user\n")

            init_payload = init_repo(target_path=str(target))
            self.assertEqual(init_payload["target_path"], target.resolve().as_posix())
            self.assertTrue((target / ".ccw" / "index.sqlite").is_file())

            index_payload = index_repo(target_path=str(target))
            self.assertEqual(index_payload["file_count"], 1)
            self.assertEqual(index_payload["symbol_count"], 1)
            self.assertTrue((target / ".ccw" / "snapshots" / "index.json").is_file())

            fact_payload = record_fact(
                kind="constraint",
                text="Do not break the login flow",
                target_path=str(target),
            )
            self.assertEqual(fact_payload["kind"], "constraint")

            episode_payload = record_episode(
                summary="Indexed the auth module",
                touched_files=["src/auth/login.py"],
                target_path=str(target),
            )
            self.assertEqual(episode_payload["touched_files"], ["src/auth/login.py"])

            classify_payload = classify_task(
                task_description="Fix the login bug",
                target_path=str(target),
            )
            self.assertEqual(classify_payload["mode"], "bugfix")

            compile_payload = compile_task_context(
                task_description="Fix the login bug",
                target_path=str(target),
            )
            artifact_path = Path(str(compile_payload["artifact_path"]))
            self.assertTrue(artifact_path.is_file())
            self.assertEqual(compile_payload["mode"], "bugfix")

            validate_payload = validate_compiled_artifact(
                artifact_path=str(artifact_path),
                target_path=str(target),
            )
            self.assertTrue(validate_payload["valid"])
            self.assertEqual(validate_payload["errors"], [])

    def test_mcp_tools_use_environment_default_target_and_repo_relative_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "repo"
            target.mkdir()
            write_text(target / "src" / "app.py", "def review_target():\n    return True\n")

            with patch.dict(os.environ, {"CCW_TARGET_ROOT": str(target)}):
                init_repo()
                index_repo()

                compile_payload = compile_task_context(
                    task_description="Review the app module",
                    output_path="artifacts/review.md",
                )

                artifact_path = target / "artifacts" / "review.md"
                self.assertEqual(compile_payload["artifact_path"], artifact_path.resolve().as_posix())
                self.assertEqual(compile_payload["mode"], "review")

                validate_payload = validate_compiled_artifact("artifacts/review.md")
                self.assertTrue(validate_payload["valid"])

    def test_prepare_context_payload_returns_content_for_generic_mcp_clients(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "repo"
            target.mkdir()
            write_text(target / "src" / "auth" / "login.py", "def login_handler(user):\n    return user\n")

            init_repo(target_path=str(target))
            index_repo(target_path=str(target))

            payload = prepare_context_payload(
                task_description="Fix the login handler",
                target_path=str(target),
            )

            self.assertTrue(payload["valid"], payload["errors"])
            self.assertIn("before re-gathering", str(payload["session_instructions"]))
            self.assertIn("src/auth/login.py", str(payload["compiled_context"]))
            self.assertGreater(int(payload["content_bytes"]), 0)
            self.assertGreater(int(payload["content_chars"]), 0)
            self.assertTrue(str(payload["content_hash"]))
            self.assertTrue(str(payload["bundle_dir"]).endswith(".ccw/session/latest"))

            source_paths = payload["source_paths"]
            self.assertIsInstance(source_paths, dict)
            self.assertTrue(Path(str(source_paths["compiled_context"])).is_file())

    def test_read_compiled_context_validates_existing_bundle_before_returning_content(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "repo"
            target.mkdir()
            write_text(target / "src" / "auth" / "login.py", "def login_handler(user):\n    return user\n")

            init_repo(target_path=str(target))
            index_repo(target_path=str(target))
            payload = prepare_context_payload(
                task_description="Fix the login handler",
                target_path=str(target),
                output_dir=".ccw/session/run-a",
            )
            self.assertTrue(payload["valid"], payload["errors"])

            read_payload = read_compiled_context(
                path=".ccw/session/run-a",
                target_path=str(target),
            )
            self.assertTrue(read_payload["valid"], read_payload["errors"])
            self.assertEqual(read_payload["compiled_context"], payload["compiled_context"])

            write_text(target / "src" / "auth" / "session_store.py", "def issue_token(user):\n    return user\n")
            index_repo(target_path=str(target))

            stale_payload = read_compiled_context(
                path=".ccw/session/run-a",
                target_path=str(target),
            )
            self.assertFalse(stale_payload["valid"])
            self.assertEqual(stale_payload["compiled_context"], "")
            self.assertTrue(any("index_hash mismatch" in error for error in stale_payload["errors"]))

    def test_read_compiled_context_fails_closed_on_invalid_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "repo"
            target.mkdir()
            write_text(target / "src" / "app.py", "def app():\n    return True\n")

            init_repo(target_path=str(target))
            index_repo(target_path=str(target))
            broken = target / ".ccw" / "compiled" / "broken.md"
            write_text(broken, "# Broken context\n")

            payload = read_compiled_context(
                path=".ccw/compiled/broken.md",
                target_path=str(target),
            )

            self.assertFalse(payload["valid"])
            self.assertEqual(payload["compiled_context"], "")
            self.assertTrue(any("frontmatter" in error for error in payload["errors"]))
