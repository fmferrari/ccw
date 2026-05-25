from __future__ import annotations

import os
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def run_ccw(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    python_path = str(ROOT / "src")
    env["PYTHONPATH"] = python_path if not env.get("PYTHONPATH") else f"{python_path}{os.pathsep}{env['PYTHONPATH']}"
    return subprocess.run(
        [sys.executable, "-m", "ccw", *args],
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
    )


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


class SessionPrepareCliTests(unittest.TestCase):
    def test_session_prepare_writes_default_bundle_layout(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir)
            self.assertEqual(run_ccw("init", cwd=target).returncode, 0)

            write_text(target / "src" / "auth" / "login.py", "def login():\n    pass\n")
            self.assertEqual(run_ccw("index", cwd=target).returncode, 0)

            result = run_ccw("session", "prepare", "--task", "Fix the login bug", cwd=target)

            self.assertEqual(result.returncode, 0, result.stderr)

            session_dir = target / ".ccw" / "session" / "latest"
            session_file = session_dir / "SESSION.md"
            compiled_context = session_dir / "compiled-context.md"
            manifest = session_dir / "session.json"

            self.assertTrue(session_file.is_file())
            self.assertTrue(compiled_context.is_file())
            self.assertTrue(manifest.is_file())

            session_text = session_file.read_text(encoding="utf-8")
            compiled_text = compiled_context.read_text(encoding="utf-8")

            self.assertIn("Fix the login bug", session_text)
            self.assertIn("compiled-context.md", session_text)
            self.assertIn("before re-gathering", session_text)
            self.assertIn("request a refreshed bundle", session_text)
            self.assertIn("Fix the login bug", compiled_text)
            self.assertIn("src/auth/login.py", compiled_text)

            validate_result = run_ccw("validate", str(compiled_context), cwd=target)
            self.assertEqual(validate_result.returncode, 0, validate_result.stderr)

    def test_session_prepare_respects_explicit_output_dir(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            target = workspace / "project"
            target.mkdir()
            self.assertEqual(run_ccw("init", str(target), cwd=workspace).returncode, 0)

            write_text(target / "src" / "review.py", "def review_changes():\n    pass\n")
            self.assertEqual(run_ccw("index", str(target), cwd=workspace).returncode, 0)

            result = run_ccw(
                "session", "prepare", "--task", "Review the latest auth changes",
                "--mode", "review", "--out-dir", "bundles/review", str(target),
                cwd=workspace,
            )

            self.assertEqual(result.returncode, 0, result.stderr)

            session_dir = target / "bundles" / "review"
            self.assertTrue((session_dir / "SESSION.md").is_file())
            self.assertTrue((session_dir / "compiled-context.md").is_file())
            self.assertTrue((session_dir / "session.json").is_file())

            manifest = json.loads((session_dir / "session.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["mode"], "review")
            self.assertEqual(manifest["compiled_artifact"], "compiled-context.md")


class SessionValidateCliTests(unittest.TestCase):
    def test_session_validate_succeeds_on_fresh_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir)
            self.assertEqual(run_ccw("init", cwd=target).returncode, 0)
            write_text(target / "src" / "auth" / "login.py", "def login():\n    pass\n")
            self.assertEqual(run_ccw("index", cwd=target).returncode, 0)
            prepare_result = run_ccw(
                "session", "prepare", "--task", "Fix the login bug", cwd=target,
            )
            self.assertEqual(prepare_result.returncode, 0, prepare_result.stderr)

            bundle_dir = target / ".ccw" / "session" / "latest"
            result = run_ccw("session", "validate", str(bundle_dir), cwd=target)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Valid session bundle", result.stdout)

    def test_session_validate_fails_on_missing_bundle_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir)
            bundle_dir = target / "nonexistent-bundle"
            result = run_ccw("session", "validate", str(bundle_dir), cwd=target)
            self.assertEqual(result.returncode, 1)
            self.assertIn("Missing required bundle file", result.stderr)

    def test_session_validate_fails_on_corrupt_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir)
            bundle_dir = target / "bundle"
            bundle_dir.mkdir(parents=True)
            (bundle_dir / "SESSION.md").write_text("# bundle\n", encoding="utf-8")
            (bundle_dir / "compiled-context.md").write_text("---\nmode: x\n---\n", encoding="utf-8")
            (bundle_dir / "session.json").write_text("not json\n", encoding="utf-8")
            result = run_ccw("session", "validate", str(bundle_dir), cwd=target)
            self.assertEqual(result.returncode, 1)
            self.assertIn("Cannot parse session.json", result.stderr)

    def test_session_validate_fails_on_frontmatter_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir)
            self.assertEqual(run_ccw("init", cwd=target).returncode, 0)
            write_text(target / "src" / "auth" / "login.py", "def login():\n    pass\n")
            self.assertEqual(run_ccw("index", cwd=target).returncode, 0)
            prepare_result = run_ccw(
                "session", "prepare", "--task", "Fix the login bug", cwd=target,
            )
            self.assertEqual(prepare_result.returncode, 0, prepare_result.stderr)

            bundle_dir = target / ".ccw" / "session" / "latest"

            manifest_path = bundle_dir / "session.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["mode"] = "refactor"
            manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

            result = run_ccw("session", "validate", str(bundle_dir), cwd=target)
            self.assertEqual(result.returncode, 1)
            self.assertIn("session.json.mode", result.stderr)

    def test_session_validate_fails_on_index_hash_staleness(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir)
            self.assertEqual(run_ccw("init", cwd=target).returncode, 0)
            write_text(target / "src" / "auth" / "login.py", "def login():\n    pass\n")
            self.assertEqual(run_ccw("index", cwd=target).returncode, 0)
            prepare_result = run_ccw(
                "session", "prepare", "--task", "Fix the login bug", cwd=target,
            )
            self.assertEqual(prepare_result.returncode, 0, prepare_result.stderr)

            bundle_dir = target / ".ccw" / "session" / "latest"

            write_text(target / "src" / "new_feature.py", "def new():\n    pass\n")
            self.assertEqual(run_ccw("index", cwd=target).returncode, 0)

            result = run_ccw("session", "validate", str(bundle_dir), cwd=target)
            self.assertEqual(result.returncode, 1)
            self.assertIn("index_hash mismatch", result.stderr)

    def test_session_validate_fails_on_index_hash_mismatch_in_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir)
            self.assertEqual(run_ccw("init", cwd=target).returncode, 0)
            write_text(target / "src" / "auth" / "login.py", "def login():\n    pass\n")
            self.assertEqual(run_ccw("index", cwd=target).returncode, 0)
            prepare_result = run_ccw(
                "session", "prepare", "--task", "Fix the login bug", cwd=target,
            )
            self.assertEqual(prepare_result.returncode, 0, prepare_result.stderr)

            bundle_dir = target / ".ccw" / "session" / "latest"

            manifest_path = bundle_dir / "session.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["index_hash"] = "tampered_hash"
            manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

            result = run_ccw("session", "validate", str(bundle_dir), cwd=target)
            self.assertEqual(result.returncode, 1)
            self.assertIn("session.json.index_hash", result.stderr)

    def test_session_validate_respects_explicit_target_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            target = workspace / "project"
            target.mkdir()
            self.assertEqual(run_ccw("init", str(target), cwd=workspace).returncode, 0)
            write_text(target / "src" / "review.py", "def review():\n    pass\n")
            self.assertEqual(run_ccw("index", str(target), cwd=workspace).returncode, 0)
            prepare_result = run_ccw(
                "session", "prepare", "--task", "Review changes", "--out-dir", "bundles/out", str(target),
                cwd=workspace,
            )
            self.assertEqual(prepare_result.returncode, 0, prepare_result.stderr)

            bundle_dir = target / "bundles" / "out"
            result = run_ccw("session", "validate", str(bundle_dir), str(target), cwd=workspace)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Valid session bundle", result.stdout)


if __name__ == "__main__":
    unittest.main()
