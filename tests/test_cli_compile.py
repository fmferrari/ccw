from __future__ import annotations

import os
import sqlite3
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


class CompileCliTests(unittest.TestCase):
    def test_compile_creates_artifact_with_task(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir)
            self.assertEqual(run_ccw("init", cwd=target).returncode, 0)

            write_text(target / "src" / "auth" / "login.py", "def login():\n    pass\n")
            self.assertEqual(run_ccw("index", cwd=target).returncode, 0)

            output_path = target / "compiled.md"
            result = run_ccw(
                "compile", "--task", "Fix the login bug", "--out", str(output_path),
                cwd=target,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(output_path.is_file())
            content = output_path.read_text(encoding="utf-8")
            self.assertIn("Fix the login bug", content)
            self.assertIn("mode: bugfix", content)
            self.assertIn("src/auth/login.py", content)

    def test_compile_with_explicit_mode(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir)
            self.assertEqual(run_ccw("init", cwd=target).returncode, 0)

            output_path = target / "compiled.md"
            result = run_ccw(
                "compile", "--task", "Hello world", "--mode", "review", "--out", str(output_path),
                cwd=target,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            content = output_path.read_text(encoding="utf-8")
            self.assertIn("mode: review", content)

    def test_compile_fails_without_init(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir)
            output_path = target / "compiled.md"
            result = run_ccw(
                "compile", "--task", "Fix bug", "--out", str(output_path),
                cwd=target,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Run 'ccw init' first", result.stderr)

    def test_compile_persists_compilation_record(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir)
            self.assertEqual(run_ccw("init", cwd=target).returncode, 0)
            write_text(target / "file.py", "def f():\n    pass\n")
            self.assertEqual(run_ccw("index", cwd=target).returncode, 0)

            result = run_ccw(
                "compile", "--task", "Add new feature", cwd=target,
            )
            self.assertEqual(result.returncode, 0, result.stderr)

            database_path = target / ".ccw" / "index.sqlite"
            with sqlite3.connect(database_path) as connection:
                rows = connection.execute(
                    "SELECT task, mode, budget FROM compilations ORDER BY id"
                ).fetchall()
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0][0], "Add new feature")
            self.assertEqual(rows[0][1], "implementation")


class ValidateCliTests(unittest.TestCase):
    def test_validate_valid_artifact_returns_zero(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir)
            artifact_path = target / "compiled.md"
            artifact_path.write_text(
                "---\n"
                "mode: bugfix\n"
                "budget: 6000\n"
                "index_hash: abc\n"
                "created_at: 2026-05-25T12:00:00Z\n"
                "---\n"
                "\n"
                "# Compiled context\n"
                "\n"
                "## Task\n"
                "\n"
                "**Mode:** bugfix\n",
                encoding="utf-8",
            )

            result = run_ccw("validate", str(artifact_path), cwd=target)

            self.assertEqual(result.returncode, 0, result.stderr)

    def test_validate_missing_frontmatter_key_returns_one(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir)
            artifact_path = target / "compiled.md"
            artifact_path.write_text(
                "---\n"
                "mode: bugfix\n"
                "budget: 6000\n"
                "---\n"
                "\n"
                "# Compiled context\n"
                "\n"
                "## Task\n",
                encoding="utf-8",
            )

            result = run_ccw("validate", str(artifact_path), cwd=target)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Error:", result.stderr)

    def test_validate_missing_section_returns_one(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir)
            artifact_path = target / "compiled.md"
            artifact_path.write_text(
                "---\n"
                "mode: bugfix\n"
                "budget: 6000\n"
                "index_hash: abc\n"
                "created_at: 2026-05-25T12:00:00Z\n"
                "---\n"
                "\n"
                "# Compiled context\n",
                encoding="utf-8",
            )

            result = run_ccw("validate", str(artifact_path), cwd=target)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Missing required section:", result.stderr)

    def test_validate_missing_artifact_file_returns_one(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir)
            missing_path = target / "nonexistent.md"

            result = run_ccw("validate", str(missing_path), cwd=target)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Artifact file not found", result.stderr)


GOLDEN_FILE = ROOT / "tests" / "fixtures" / "compile" / "bugfix-simple.golden.md"
FIXTURES_COMPILE = ROOT / "tests" / "fixtures" / "compile"


def _normalize_golden(text: str) -> str:
    """Replace dynamic index_hash and created_at with placeholders."""
    import re
    text = re.sub(r"^index_hash: .+$", "index_hash: <hash>", text, flags=re.MULTILINE)
    text = re.sub(r"^created_at: .+$", "created_at: <timestamp>", text, flags=re.MULTILINE)
    return text


class GoldenCompileTests(unittest.TestCase):
    def test_golden_bugfix_compile(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir)
            self.assertEqual(run_ccw("init", cwd=target).returncode, 0)

            (target / "src" / "auth" / "login.py").parent.mkdir(parents=True)
            (target / "src" / "auth" / "login.py").write_text(
                "def login_handler(user):\n    pass\n"
            )
            self.assertEqual(run_ccw("index", cwd=target).returncode, 0)

            out_path = target / "compiled.md"
            result = run_ccw(
                "compile", "--task", "Fix login bug", "--mode", "bugfix",
                "--out", str(out_path), cwd=target,
            )
            self.assertEqual(result.returncode, 0, result.stderr)

            actual = out_path.read_text(encoding="utf-8")
            actual_normalized = _normalize_golden(actual)

            if not GOLDEN_FILE.is_file():
                GOLDEN_FILE.parent.mkdir(parents=True, exist_ok=True)
                GOLDEN_FILE.write_text(actual_normalized, encoding="utf-8")
                self.skipTest("Golden file created; run again to compare")

            expected = _normalize_golden(
                GOLDEN_FILE.read_text(encoding="utf-8")
            )

            self.assertMultiLineEqual(expected, actual_normalized)

    def test_golden_compile_structural_checks(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir)
            self.assertEqual(run_ccw("init", cwd=target).returncode, 0)

            (target / "src" / "auth" / "login.py").parent.mkdir(parents=True)
            (target / "src" / "auth" / "login.py").write_text(
                "def login_handler(user):\n    pass\n"
            )
            self.assertEqual(run_ccw("index", cwd=target).returncode, 0)

            out_path = target / "compiled.md"
            result = run_ccw(
                "compile", "--task", "Refactor auth module", "--mode", "refactor",
                "--budget", "2000",
                "--out", str(out_path), cwd=target,
            )
            self.assertEqual(result.returncode, 0, result.stderr)

            content = out_path.read_text(encoding="utf-8")
            self.assertIn("mode: refactor", content)
            self.assertIn("budget: 2000", content)
            self.assertIn("## Task", content)
            self.assertIn("## Files", content)
            self.assertIn("src/auth/login.py", content)
            self.assertIn("score:", content)
            self.assertIn("lines 1-2:", content)
            self.assertIn("def login_handler(user):", content)
            self.assertIn("Estimated tokens:", content)


if __name__ == "__main__":
    unittest.main()
