from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ccw.compile import rank_files


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


class RankFilesTests(unittest.TestCase):
    def test_rank_files_scores_path_matches_highest(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir)
            state_dir = target / ".ccw"
            state_dir.mkdir()
            (state_dir / "compiled").mkdir()
            (state_dir / "snapshots").mkdir()
            write_text(state_dir / "config.yaml", "config_version: 1\n")
            database_path = state_dir / "index.sqlite"

            import sqlite3
            with sqlite3.connect(database_path) as connection:
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
                    INSERT INTO files (path, content_hash, size_bytes, language)
                    VALUES
                        ('src/auth/login.py', 'abc', 10, 'python'),
                        ('src/utils/helpers.py', 'def', 10, 'python');
                    """
                )

            ranked = rank_files(
                target=target,
                task_description="Fix the login bug",
                database_path=database_path,
                max_items=10,
            )

            self.assertEqual(len(ranked), 2)
            self.assertEqual(ranked[0].file_path, "src/auth/login.py")
            self.assertGreater(ranked[0].score, ranked[1].score)


if __name__ == "__main__":
    unittest.main()
