from __future__ import annotations

import hashlib
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


def fetch_files_rows(database_path: Path) -> list[tuple[str, str, int, str]]:
    with sqlite3.connect(database_path) as connection:
        rows = connection.execute(
            "SELECT path, content_hash, size_bytes, language FROM files ORDER BY path"
        ).fetchall()

    return [(path, content_hash, size_bytes, language) for path, content_hash, size_bytes, language in rows]


def fetch_files_columns(database_path: Path) -> list[str]:
    with sqlite3.connect(database_path) as connection:
        rows = connection.execute("PRAGMA table_info(files)").fetchall()

    return [name for _, name, *_ in rows]


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def expected_row(path: str, content: str, language: str) -> tuple[str, str, int, str]:
    encoded = content.encode("utf-8")
    return (path, hashlib.sha256(encoded).hexdigest(), len(encoded), language)


class IndexCliTests(unittest.TestCase):
    def test_index_fails_when_local_state_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir)

            result = run_ccw("index", cwd=target)

            self.assertNotEqual(result.returncode, 0)
            self.assertTrue(result.stderr.startswith("Error: "))
            self.assertIn("Run 'ccw init' first", result.stderr)

    def test_index_persists_expected_file_inventory_and_excludes_runtime_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir)
            self.assertEqual(run_ccw("init", cwd=target).returncode, 0)

            write_text(target / "README.md", "# Sample repo\n")
            write_text(target / "config" / "settings.yaml", "mode: test\n")
            write_text(target / "package.json", '{"name": "fixture"}\n')
            write_text(target / "notes.txt", "plain text\n")
            write_text(target / "src" / "app.py", "print('hello')\n")
            write_text(target / ".git" / "HEAD", "ref: refs/heads/main\n")

            symlink_path = target / "linked.py"
            symlink_created = False
            try:
                symlink_path.symlink_to(target / "src" / "app.py")
                symlink_created = True
            except OSError:
                pass

            result = run_ccw("index", cwd=target)

            self.assertEqual(result.returncode, 0, result.stderr)
            rows = fetch_files_rows(target / ".ccw" / "index.sqlite")
            self.assertEqual(
                rows,
                [
                    expected_row("README.md", "# Sample repo\n", "markdown"),
                    expected_row("config/settings.yaml", "mode: test\n", "yaml"),
                    expected_row("notes.txt", "plain text\n", "unknown"),
                    expected_row("package.json", '{"name": "fixture"}\n', "json"),
                    expected_row("src/app.py", "print('hello')\n", "python"),
                ],
            )
            indexed_paths = [path for path, *_ in rows]
            self.assertNotIn(".ccw/config.yaml", indexed_paths)
            self.assertNotIn(".git/HEAD", indexed_paths)
            if symlink_created:
                self.assertNotIn("linked.py", indexed_paths)

    def test_index_is_stable_when_repo_contents_do_not_change(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir)
            self.assertEqual(run_ccw("init", cwd=target).returncode, 0)
            write_text(target / "src" / "app.py", "print('stable')\n")
            write_text(target / "docs" / "guide.md", "Guide\n")

            first = run_ccw("index", cwd=target)
            first_rows = fetch_files_rows(target / ".ccw" / "index.sqlite")
            second = run_ccw("index", cwd=target)
            second_rows = fetch_files_rows(target / ".ccw" / "index.sqlite")

            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertEqual(first_rows, second_rows)

    def test_index_accepts_an_explicit_target_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            target = root / "repo"
            target.mkdir()
            self.assertEqual(run_ccw("init", str(target), cwd=root).returncode, 0)
            write_text(target / "src" / "tool.ts", "export const tool = 1;\n")

            result = run_ccw("index", str(target), cwd=root)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(
                fetch_files_rows(target / ".ccw" / "index.sqlite"),
                [expected_row("src/tool.ts", "export const tool = 1;\n", "typescript")],
            )

    def test_index_refreshes_changed_and_deleted_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir)
            self.assertEqual(run_ccw("init", cwd=target).returncode, 0)
            app_path = target / "src" / "app.py"
            stale_path = target / "stale.txt"
            write_text(app_path, "print('v1')\n")
            write_text(stale_path, "remove me\n")

            first = run_ccw("index", cwd=target)
            self.assertEqual(first.returncode, 0, first.stderr)

            write_text(app_path, "print('v2 updated')\n")
            stale_path.unlink()

            second = run_ccw("index", cwd=target)

            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertEqual(
                fetch_files_rows(target / ".ccw" / "index.sqlite"),
                [expected_row("src/app.py", "print('v2 updated')\n", "python")],
            )

    def test_index_upgrades_phase_1_placeholder_files_table(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir)
            state_dir = target / ".ccw"
            state_dir.mkdir()
            (state_dir / "compiled").mkdir()
            (state_dir / "snapshots").mkdir()
            write_text(state_dir / "config.yaml", "config_version: 1\n")
            write_text(target / "main.js", "console.log('hello');\n")

            with sqlite3.connect(state_dir / "index.sqlite") as connection:
                connection.executescript(
                    """
                    CREATE TABLE files (id INTEGER PRIMARY KEY);
                    CREATE TABLE symbols (id INTEGER PRIMARY KEY);
                    CREATE TABLE edges (id INTEGER PRIMARY KEY);
                    CREATE TABLE facts (id INTEGER PRIMARY KEY);
                    CREATE TABLE episodes (id INTEGER PRIMARY KEY);
                    """
                )

            result = run_ccw("index", cwd=target)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(
                fetch_files_columns(state_dir / "index.sqlite"),
                ["id", "path", "content_hash", "size_bytes", "language"],
            )
            self.assertEqual(
                fetch_files_rows(state_dir / "index.sqlite"),
                [expected_row("main.js", "console.log('hello');\n", "javascript")],
            )


if __name__ == "__main__":
    unittest.main()
