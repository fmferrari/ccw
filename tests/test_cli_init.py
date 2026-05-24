from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
import venv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ccw.config import DEFAULT_CONFIG, load_config


EXPECTED_SCHEMA_TABLES = {"artifacts", "classifications", "edges", "episodes", "facts", "files", "symbols"}


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


def run_installed_ccw(*args: str, cwd: Path, venv_dir: Path) -> subprocess.CompletedProcess[str]:
    scripts_dir = venv_dir / ("Scripts" if os.name == "nt" else "bin")
    python = scripts_dir / ("python.exe" if os.name == "nt" else "python")
    ccw = scripts_dir / ("ccw.exe" if os.name == "nt" else "ccw")

    install = subprocess.run(
        [str(python), "-m", "pip", "install", "-e", str(ROOT)],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    assert install.returncode == 0, install.stderr

    return subprocess.run(
        [str(ccw), *args],
        cwd=cwd,
        text=True,
        capture_output=True,
    )


class InitCliTests(unittest.TestCase):
    def assert_schema_tables(self, database_path: Path) -> None:
        with sqlite3.connect(database_path) as connection:
            rows = connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()

        self.assertEqual({name for (name,) in rows}, EXPECTED_SCHEMA_TABLES)

    def assert_runtime_layout(self, target: Path) -> None:
        self.assertTrue((target / ".ccw").is_dir())
        self.assertTrue((target / ".ccw" / "compiled").is_dir())
        self.assertTrue((target / ".ccw" / "snapshots").is_dir())
        self.assertTrue((target / ".ccw" / "config.yaml").is_file())
        self.assertTrue((target / ".ccw" / "index.sqlite").is_file())
        self.assert_schema_tables(target / ".ccw" / "index.sqlite")

    def test_init_creates_runtime_layout(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir)
            result = run_ccw("init", cwd=target)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assert_runtime_layout(target)

    def test_init_creates_runtime_layout_for_explicit_target(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            target = root / "repo"
            target.mkdir()

            result = run_ccw("init", str(target), cwd=root)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assert_runtime_layout(target)

    def test_init_is_idempotent_and_preserves_existing_config(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir)
            first = run_ccw("init", cwd=target)
            config_path = target / ".ccw" / "config.yaml"
            database_path = target / ".ccw" / "index.sqlite"
            original_config = config_path.read_text(encoding="utf-8")
            with sqlite3.connect(database_path) as connection:
                connection.execute(
                    "INSERT INTO facts (kind, text, created_at) VALUES (?, ?, ?)",
                    ("goal", "Preserve existing facts", "2026-05-24T00:00:00Z"),
                )
                connection.commit()

            second = run_ccw("init", cwd=target)

            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertEqual(config_path.read_text(encoding="utf-8"), original_config)
            with sqlite3.connect(database_path) as connection:
                fact_count = connection.execute("SELECT COUNT(*) FROM facts").fetchone()

            self.assertEqual(fact_count, (1,))
            self.assert_schema_tables(database_path)

    def test_init_creates_loadable_config_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir)
            result = run_ccw("init", cwd=target)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(load_config(target / ".ccw" / "config.yaml"), DEFAULT_CONFIG)

    def test_init_fails_for_invalid_target_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir)
            missing_target = target / "missing-repo"

            result = run_ccw("init", str(missing_target), cwd=target)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Init target does not exist", result.stderr)

    def test_init_fails_for_non_writable_target(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            target = root / "repo"
            target.mkdir()
            target.chmod(0o555)

            try:
                result = run_ccw("init", str(target), cwd=root)
            finally:
                target.chmod(0o755)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("not writable", result.stderr.lower())

    def test_init_fails_with_stable_error_when_local_state_path_is_a_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir)
            local_state = target / ".ccw"
            local_state.write_text("conflict", encoding="utf-8")

            result = run_ccw("init", cwd=target)

            self.assertNotEqual(result.returncode, 0)
            self.assertTrue(result.stderr.startswith("Error: "))
            self.assertIn("Local state path exists as a file", result.stderr)

    def test_init_fails_with_stable_error_when_compiled_directory_path_is_a_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir)
            compiled_path = target / ".ccw" / "compiled"
            compiled_path.parent.mkdir()
            compiled_path.write_text("conflict", encoding="utf-8")

            result = run_ccw("init", cwd=target)

            self.assertNotEqual(result.returncode, 0)
            self.assertTrue(result.stderr.startswith("Error: "))
            self.assertIn("Compiled artifact directory exists as a file", result.stderr)

    def test_init_fails_with_stable_error_when_snapshots_directory_path_is_a_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir)
            snapshots_path = target / ".ccw" / "snapshots"
            snapshots_path.parent.mkdir()
            snapshots_path.write_text("conflict", encoding="utf-8")

            result = run_ccw("init", cwd=target)

            self.assertNotEqual(result.returncode, 0)
            self.assertTrue(result.stderr.startswith("Error: "))
            self.assertIn("Snapshots directory exists as a file", result.stderr)

    def test_init_fails_with_stable_error_when_config_path_is_a_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir)
            config_path = target / ".ccw" / "config.yaml"
            config_path.mkdir(parents=True)

            result = run_ccw("init", cwd=target)

            self.assertNotEqual(result.returncode, 0)
            self.assertTrue(result.stderr.startswith("Error: "))
            self.assertIn("Config path exists as a directory", result.stderr)

    def test_init_fails_with_stable_error_when_index_database_path_is_a_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir)
            database_path = target / ".ccw" / "index.sqlite"
            database_path.mkdir(parents=True)

            result = run_ccw("init", cwd=target)

            self.assertNotEqual(result.returncode, 0)
            self.assertTrue(result.stderr.startswith("Error: "))
            self.assertIn("Index database path exists as a directory", result.stderr)
            self.assertFalse((target / ".ccw" / "config.yaml").exists())

    def test_init_upgrades_placeholder_facts_table_non_destructively(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir)
            state_dir = target / ".ccw"
            state_dir.mkdir()
            (state_dir / "compiled").mkdir()
            (state_dir / "snapshots").mkdir()
            (state_dir / "config.yaml").write_text("config_version: 1\n", encoding="utf-8")

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
                    CREATE TABLE facts (id INTEGER PRIMARY KEY);
                    CREATE TABLE episodes (id INTEGER PRIMARY KEY);
                    """
                )
                connection.execute("INSERT INTO facts DEFAULT VALUES")
                connection.commit()

            result = run_ccw("init", cwd=target)

            self.assertEqual(result.returncode, 0, result.stderr)
            with sqlite3.connect(state_dir / "index.sqlite") as connection:
                columns = [name for _, name, *_ in connection.execute("PRAGMA table_info(facts)").fetchall()]
                rows = connection.execute("SELECT kind, text, created_at FROM facts ORDER BY id").fetchall()

            self.assertEqual(columns, ["id", "kind", "text", "created_at"])
            self.assertEqual(rows, [(None, None, None)])

    def test_init_upgrades_placeholder_episodes_table_non_destructively(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir)
            state_dir = target / ".ccw"
            state_dir.mkdir()
            (state_dir / "compiled").mkdir()
            (state_dir / "snapshots").mkdir()
            (state_dir / "config.yaml").write_text("config_version: 1\n", encoding="utf-8")

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

            result = run_ccw("init", cwd=target)

            self.assertEqual(result.returncode, 0, result.stderr)
            with sqlite3.connect(state_dir / "index.sqlite") as connection:
                columns = [name for _, name, *_ in connection.execute("PRAGMA table_info(episodes)").fetchall()]
                rows = connection.execute("SELECT summary, touched_files, created_at FROM episodes ORDER BY id").fetchall()

            self.assertEqual(columns, ["id", "summary", "touched_files", "created_at"])
            self.assertEqual(rows, [(None, None, None)])

    def test_init_upgrades_placeholder_classifications_table_non_destructively(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir)
            state_dir = target / ".ccw"
            state_dir.mkdir()
            (state_dir / "compiled").mkdir()
            (state_dir / "snapshots").mkdir()
            (state_dir / "config.yaml").write_text("config_version: 1\n", encoding="utf-8")

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

            result = run_ccw("init", cwd=target)

            self.assertEqual(result.returncode, 0, result.stderr)
            with sqlite3.connect(state_dir / "index.sqlite") as connection:
                columns = [name for _, name, *_ in connection.execute("PRAGMA table_info(classifications)").fetchall()]
                rows = connection.execute("SELECT text, mode, created_at FROM classifications ORDER BY id").fetchall()

            self.assertEqual(columns, ["id", "text", "mode", "created_at"])
            self.assertEqual(rows, [(None, None, None)])

    def test_installed_console_entrypoint_bootstraps_repo(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            venv_dir = root / "venv"
            venv.EnvBuilder(with_pip=True).create(venv_dir)
            target = root / "repo"
            target.mkdir()

            result = run_installed_ccw("init", str(target), cwd=root, venv_dir=venv_dir)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assert_runtime_layout(target)


if __name__ == "__main__":
    unittest.main()
