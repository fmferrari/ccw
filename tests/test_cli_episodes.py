from __future__ import annotations

import datetime
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


def fetch_episode_columns(database_path: Path) -> list[str]:
    with sqlite3.connect(database_path) as connection:
        rows = connection.execute("PRAGMA table_info(episodes)").fetchall()

    return [name for _, name, *_ in rows]


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


class EpisodesCliTests(unittest.TestCase):
    def test_episodes_add_persists_one_explicit_episode(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir)
            self.assertEqual(run_ccw("init", cwd=target).returncode, 0)

            result = run_ccw(
                "episodes",
                "add",
                "Completed indexing slice",
                "src/app.py,README.md",
                cwd=target,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            rows = fetch_episode_rows(target / ".ccw" / "index.sqlite")
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0][0], "Completed indexing slice")
            self.assertEqual(json.loads(rows[0][1] or "[]"), ["README.md", "src/app.py"])
            self.assertIsNotNone(rows[0][2])
            self.assertEqual(
                datetime.datetime.fromisoformat(rows[0][2].replace("Z", "+00:00")).tzinfo,  # type: ignore[union-attr]
                datetime.timezone.utc,
            )

    def test_episodes_add_is_append_only_and_survives_init_and_index(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir)
            self.assertEqual(run_ccw("init", cwd=target).returncode, 0)

            first = run_ccw("episodes", "add", "Completed indexing", "src/app.py", cwd=target)
            second = run_ccw("episodes", "add", "Updated docs", "README.md,docs/guide.md", cwd=target)
            reinit = run_ccw("init", cwd=target)
            write_text(target / "src" / "app.py", "def app():\n    return 1\n")
            reindex = run_ccw("index", cwd=target)

            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertEqual(reinit.returncode, 0, reinit.stderr)
            self.assertEqual(reindex.returncode, 0, reindex.stderr)
            self.assertEqual(
                [(summary, json.loads(touched_files or "[]")) for summary, touched_files, _ in fetch_episode_rows(target / ".ccw" / "index.sqlite")],
                [
                    ("Completed indexing", ["src/app.py"]),
                    ("Updated docs", ["README.md", "docs/guide.md"]),
                ],
            )

    def test_episodes_add_fails_without_initialized_local_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir)

            result = run_ccw("episodes", "add", "Episode", "src/app.py", cwd=target)

            self.assertNotEqual(result.returncode, 0)
            self.assertTrue(result.stderr.startswith("Error: "))
            self.assertIn("Run 'ccw init' first", result.stderr)

    def test_episodes_add_rejects_empty_or_invalid_touched_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir)
            self.assertEqual(run_ccw("init", cwd=target).returncode, 0)

            empty_summary = run_ccw("episodes", "add", "   ", "src/app.py", cwd=target)
            empty_files = run_ccw("episodes", "add", "Episode", "   ", cwd=target)
            invalid_file = run_ccw("episodes", "add", "Episode", "../outside.py", cwd=target)

            self.assertNotEqual(empty_summary.returncode, 0)
            self.assertIn("Episode summary must not be empty", empty_summary.stderr)
            self.assertNotEqual(empty_files.returncode, 0)
            self.assertIn("Episode touched files must not be empty", empty_files.stderr)
            self.assertNotEqual(invalid_file.returncode, 0)
            self.assertIn("Invalid touched file path", invalid_file.stderr)
            trailing_parent = run_ccw("episodes", "add", "Episode", "src/..", cwd=target)
            self.assertNotEqual(trailing_parent.returncode, 0)
            self.assertIn("Invalid touched file path", trailing_parent.stderr)
            self.assertEqual(fetch_episode_rows(target / ".ccw" / "index.sqlite"), [])

    def test_episodes_add_upgrades_placeholder_episodes_table(self) -> None:
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

            result = run_ccw("episodes", "add", "Completed fix", "src/app.py,README.md", cwd=target)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(fetch_episode_columns(state_dir / "index.sqlite"), ["id", "summary", "touched_files", "created_at"])
            rows = fetch_episode_rows(state_dir / "index.sqlite")
            self.assertEqual(rows[0], (None, None, None))
            self.assertEqual(rows[1][0], "Completed fix")
            self.assertEqual(json.loads(rows[1][1] or "[]"), ["README.md", "src/app.py"])
            self.assertIsNotNone(rows[1][2])


if __name__ == "__main__":
    unittest.main()
