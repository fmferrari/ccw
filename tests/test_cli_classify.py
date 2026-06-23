from __future__ import annotations

import datetime
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


def fetch_classify_rows(database_path: Path) -> list[tuple[str | None, str | None, str | None]]:
    with sqlite3.connect(database_path) as connection:
        rows = connection.execute("SELECT text, mode, created_at FROM classifications ORDER BY id").fetchall()

    return [(text, mode, created_at) for text, mode, created_at in rows]


def fetch_classify_columns(database_path: Path) -> list[str]:
    with sqlite3.connect(database_path) as connection:
        rows = connection.execute("PRAGMA table_info(classifications)").fetchall()

    return [name for _, name, *_ in rows]


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


class ClassifyCliTests(unittest.TestCase):
    def test_classify_bugfix_mode(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir)
            self.assertEqual(run_ccw("init", cwd=target).returncode, 0)

            result = run_ccw("classify", "Fix the login bug", cwd=target)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), "bugfix")
            rows = fetch_classify_rows(target / ".ccw" / "index.sqlite")
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0][0:2], ("Fix the login bug", "bugfix"))
            self.assertIsNotNone(rows[0][2])
            self.assertEqual(
                datetime.datetime.fromisoformat(rows[0][2].replace("Z", "+00:00")).tzinfo,  # type: ignore[union-attr]
                datetime.timezone.utc,
            )

    def test_classify_implementation_mode(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir)
            self.assertEqual(run_ccw("init", cwd=target).returncode, 0)

            result = run_ccw("classify", "Implement user authentication", cwd=target)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), "implementation")

    def test_classify_review_mode(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir)
            self.assertEqual(run_ccw("init", cwd=target).returncode, 0)

            result = run_ccw("classify", "Review the pull request", cwd=target)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), "review")

    def test_classify_refactor_mode(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir)
            self.assertEqual(run_ccw("init", cwd=target).returncode, 0)

            result = run_ccw("classify", "Refactor the database layer", cwd=target)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), "refactor")

    def test_classify_docs_mode(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir)
            self.assertEqual(run_ccw("init", cwd=target).returncode, 0)

            result = run_ccw(
                "classify",
                "Document retrieval ranking behavior and troubleshooting notes",
                cwd=target,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), "docs")

    def test_classify_defaults_to_implementation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir)
            self.assertEqual(run_ccw("init", cwd=target).returncode, 0)

            result = run_ccw("classify", "Hello world test case", cwd=target)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), "implementation")

    def test_classify_is_append_only_and_survives_init_and_index(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir)
            self.assertEqual(run_ccw("init", cwd=target).returncode, 0)

            first = run_ccw("classify", "Fix the login bug", cwd=target)
            second = run_ccw("classify", "Add a new feature", cwd=target)
            reinit = run_ccw("init", cwd=target)
            write_text(target / "src" / "app.py", "def app():\n    return 1\n")
            reindex = run_ccw("index", cwd=target)

            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertEqual(reinit.returncode, 0, reinit.stderr)
            self.assertEqual(reindex.returncode, 0, reindex.stderr)
            self.assertEqual(
                [(text, mode) for text, mode, _ in fetch_classify_rows(target / ".ccw" / "index.sqlite")],
                [
                    ("Fix the login bug", "bugfix"),
                    ("Add a new feature", "implementation"),
                ],
            )

    def test_classify_fails_without_initialized_local_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir)

            result = run_ccw("classify", "Fix a bug", cwd=target)

            self.assertNotEqual(result.returncode, 0)
            self.assertTrue(result.stderr.startswith("Error: "))
            self.assertIn("Run 'ccw init' first", result.stderr)

    def test_classify_rejects_empty_text(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir)
            self.assertEqual(run_ccw("init", cwd=target).returncode, 0)

            result = run_ccw("classify", "   ", cwd=target)

            self.assertNotEqual(result.returncode, 0)
            self.assertTrue(result.stderr.startswith("Error: "))
            self.assertIn("Classification text must not be empty", result.stderr)
            self.assertEqual(fetch_classify_rows(target / ".ccw" / "index.sqlite"), [])

    def test_classify_upgrades_placeholder_classifications_table(self) -> None:
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
                    CREATE TABLE episodes (
                        id INTEGER PRIMARY KEY,
                        summary TEXT,
                        touched_files TEXT,
                        created_at TEXT
                    );
                    CREATE TABLE classifications (id INTEGER PRIMARY KEY);
                    """
                )
                connection.execute("INSERT INTO classifications DEFAULT VALUES")
                connection.commit()

            result = run_ccw("classify", "Review the architecture", cwd=target)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), "review")
            self.assertEqual(
                fetch_classify_columns(state_dir / "index.sqlite"),
                ["id", "text", "mode", "created_at"],
            )
            rows = fetch_classify_rows(state_dir / "index.sqlite")
            self.assertEqual(rows[0], (None, None, None))
            self.assertEqual(rows[1][0], "Review the architecture")
            self.assertEqual(rows[1][1], "review")
            self.assertIsNotNone(rows[1][2])


if __name__ == "__main__":
    unittest.main()
