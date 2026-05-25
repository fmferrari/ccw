from __future__ import annotations

import json
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


def fetch_episode_rows(database_path: Path) -> list[tuple[str | None, str | None, str | None]]:
    with sqlite3.connect(database_path) as connection:
        rows = connection.execute("SELECT summary, touched_files, created_at FROM episodes ORDER BY id").fetchall()
    return [(summary, touched_files, created_at) for summary, touched_files, created_at in rows]


def fetch_fact_rows(database_path: Path) -> list[tuple[str | None, str | None, str | None]]:
    with sqlite3.connect(database_path) as connection:
        rows = connection.execute("SELECT kind, text, created_at FROM facts ORDER BY id").fetchall()
    return [(kind, text, created_at) for kind, text, created_at in rows]


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


class UpdateCliTests(unittest.TestCase):
    def test_update_records_episode_and_reindexes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir)
            self.assertEqual(run_ccw("init", cwd=target).returncode, 0)
            write_text(target / "old.py", "x = 1\n")
            self.assertEqual(run_ccw("index", cwd=target).returncode, 0)

            write_text(target / "new.py", "y = 2\n")
            write_text(target / "old.py", "x = 2\n")

            result = run_ccw(
                "update",
                "--run", "Added new feature and updated old module",
                "--touched-files", "new.py,old.py",
                cwd=target,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Post-run memory update recorded", result.stdout)

            rows = fetch_episode_rows(target / ".ccw" / "index.sqlite")
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0][0], "Added new feature and updated old module")
            self.assertEqual(json.loads(rows[0][1] or "[]"), ["new.py", "old.py"])

            with sqlite3.connect(target / ".ccw" / "index.sqlite") as connection:
                files = {row[0]: row[1] for row in connection.execute("SELECT path, content_hash FROM files").fetchall()}
            self.assertIn("new.py", files)
            self.assertIn("old.py", files)

    def test_update_records_episode_with_decision_fact(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir)
            self.assertEqual(run_ccw("init", cwd=target).returncode, 0)
            write_text(target / "src" / "app.py", "x = 1\n")
            self.assertEqual(run_ccw("index", cwd=target).returncode, 0)

            write_text(target / "src" / "app.py", "x = 2\n")
            result = run_ccw(
                "update",
                "--run", "Fixed login validation",
                "--touched-files", "src/app.py",
                "--decision", "Added null check to login form",
                cwd=target,
            )

            self.assertEqual(result.returncode, 0, result.stderr)

            episode_rows = fetch_episode_rows(target / ".ccw" / "index.sqlite")
            self.assertEqual(len(episode_rows), 1)
            self.assertEqual(episode_rows[0][0], "Fixed login validation")

            fact_rows = fetch_fact_rows(target / ".ccw" / "index.sqlite")
            self.assertEqual(len(fact_rows), 1)
            self.assertEqual(fact_rows[0][0], "decision")
            self.assertEqual(fact_rows[0][1], "Added null check to login form")

    def test_update_fails_without_initialized_local_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir)

            result = run_ccw(
                "update",
                "--run", "Fix bug",
                "--touched-files", "src/app.py",
                cwd=target,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertTrue(result.stderr.startswith("Error: "))
            self.assertIn("Run 'ccw init' first", result.stderr)

    def test_update_fails_with_empty_summary(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir)
            self.assertEqual(run_ccw("init", cwd=target).returncode, 0)

            result = run_ccw(
                "update",
                "--run", "   ",
                "--touched-files", "src/app.py",
                cwd=target,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertTrue(result.stderr.startswith("Error: "))

    def test_update_fails_with_invalid_touched_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir)
            self.assertEqual(run_ccw("init", cwd=target).returncode, 0)

            result = run_ccw(
                "update",
                "--run", "Fix bug",
                "--touched-files", "../outside.py",
                cwd=target,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertTrue(result.stderr.startswith("Error: "))
            self.assertIn("Invalid touched file path", result.stderr)

    def test_update_fails_with_empty_touched_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir)
            self.assertEqual(run_ccw("init", cwd=target).returncode, 0)

            result = run_ccw(
                "update",
                "--run", "Fix bug",
                "--touched-files", "   ",
                cwd=target,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertTrue(result.stderr.startswith("Error: "))
            self.assertIn("Episode touched files must not be empty", result.stderr)

    def test_update_upgrades_placeholder_episodes_table(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir)
            state_dir = target / ".ccw"
            state_dir.mkdir()
            (state_dir / "compiled").mkdir()
            (state_dir / "snapshots").mkdir()
            write_text(state_dir / "config.yaml", "config_version: 1\n")

            with sqlite3.connect(state_dir / "index.sqlite") as connection:
                connection.executescript(
                    """
                    CREATE TABLE files (
                        id INTEGER PRIMARY KEY,
                        path TEXT NOT NULL UNIQUE,
                        content_hash TEXT NOT NULL,
                        size_bytes INTEGER NOT NULL,
                        language TEXT NOT NULL,
                        last_commit_at INTEGER,
                        last_author_email TEXT,
                        owner_email TEXT,
                        owner_commit_count INTEGER
                    );
                    CREATE TABLE symbols (
                        id INTEGER PRIMARY KEY,
                        file_path TEXT NOT NULL,
                        name TEXT NOT NULL,
                        kind TEXT NOT NULL,
                        line INTEGER NOT NULL,
                        end_line INTEGER NOT NULL,
                        export_name TEXT
                    );
                    CREATE TABLE edges (
                        id INTEGER PRIMARY KEY,
                        source_path TEXT NOT NULL,
                        kind TEXT NOT NULL,
                        target_path TEXT NOT NULL,
                        detail TEXT,
                        line INTEGER
                    );
                    CREATE TABLE artifacts (
                        id INTEGER PRIMARY KEY,
                        file_path TEXT NOT NULL,
                        kind TEXT NOT NULL,
                        title TEXT NOT NULL,
                        search_text TEXT NOT NULL
                    );
                    CREATE TABLE facts (
                        id INTEGER PRIMARY KEY,
                        kind TEXT,
                        text TEXT,
                        created_at TEXT
                    );
                    CREATE TABLE episodes (id INTEGER PRIMARY KEY);
                    """
                )
                connection.execute("INSERT INTO episodes DEFAULT VALUES")
                connection.commit()

            write_text(target / "src" / "app.py", "x = 1\n")
            self.assertEqual(run_ccw("index", cwd=target).returncode, 0)

            write_text(target / "src" / "app.py", "x = 2\n")
            result = run_ccw(
                "update",
                "--run", "Updated after placeholder upgrade",
                "--touched-files", "src/app.py",
                cwd=target,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            rows = fetch_episode_rows(state_dir / "index.sqlite")
            self.assertEqual(rows[0], (None, None, None))
            self.assertEqual(rows[1][0], "Updated after placeholder upgrade")
            self.assertEqual(json.loads(rows[1][1] or "[]"), ["src/app.py"])


if __name__ == "__main__":
    unittest.main()
