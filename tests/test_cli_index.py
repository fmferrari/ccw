from __future__ import annotations

import datetime
import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIXTURES_ROOT = ROOT / "tests" / "fixtures" / "index"
SNAPSHOT_NAME = "index.json"
FIXTURE_COMMIT_EMAIL = "owner@example.com"
FIXTURE_COMMIT_NAME = "Fixture Owner"
FIXTURE_COMMIT_DATE = "2026-05-23T12:00:00+0000"
FIXTURE_COMMIT_TIMESTAMP = int(datetime.datetime(2026, 5, 23, 12, 0, tzinfo=datetime.timezone.utc).timestamp())

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


def run_git(*args: str, cwd: Path, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    full_env = os.environ.copy()
    if env is not None:
        full_env.update(env)
    return subprocess.run(["git", *args], cwd=cwd, env=full_env, text=True, capture_output=True)


def initialize_fixture_git_repo(target: Path) -> None:
    env = {
        "GIT_AUTHOR_NAME": FIXTURE_COMMIT_NAME,
        "GIT_AUTHOR_EMAIL": FIXTURE_COMMIT_EMAIL,
        "GIT_AUTHOR_DATE": FIXTURE_COMMIT_DATE,
        "GIT_COMMITTER_NAME": FIXTURE_COMMIT_NAME,
        "GIT_COMMITTER_EMAIL": FIXTURE_COMMIT_EMAIL,
        "GIT_COMMITTER_DATE": FIXTURE_COMMIT_DATE,
    }
    assert run_git("init", cwd=target).returncode == 0
    assert run_git("add", ".", cwd=target).returncode == 0
    commit = run_git("commit", "-m", "fixture index repo", cwd=target, env=env)
    assert commit.returncode == 0, commit.stderr


def copy_fixture_repo(name: str, target: Path) -> None:
    shutil.copytree(FIXTURES_ROOT / name, target)


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


def fetch_file_signal_rows(database_path: Path) -> list[tuple[str, int | None, str | None, str | None, int | None]]:
    with sqlite3.connect(database_path) as connection:
        rows = connection.execute(
            "SELECT path, last_commit_at, last_author_email, owner_email, owner_commit_count FROM files ORDER BY path"
        ).fetchall()

    return [
        (path, last_commit_at, last_author_email, owner_email, owner_commit_count)
        for path, last_commit_at, last_author_email, owner_email, owner_commit_count in rows
    ]


def fetch_symbols_rows(database_path: Path) -> list[tuple[str, str, str, int, int]]:
    with sqlite3.connect(database_path) as connection:
        rows = connection.execute(
            "SELECT file_path, name, kind, line, end_line FROM symbols ORDER BY file_path, line, name, kind"
        ).fetchall()

    return [(file_path, name, kind, line, end_line) for file_path, name, kind, line, end_line in rows]


def fetch_symbols_columns(database_path: Path) -> list[str]:
    with sqlite3.connect(database_path) as connection:
        rows = connection.execute("PRAGMA table_info(symbols)").fetchall()

    return [name for _, name, *_ in rows]


def fetch_symbol_export_rows(database_path: Path) -> list[tuple[str, str, str, str | None]]:
    with sqlite3.connect(database_path) as connection:
        rows = connection.execute(
            "SELECT file_path, name, kind, export_name FROM symbols ORDER BY file_path, line, name, kind"
        ).fetchall()

    return [(file_path, name, kind, export_name) for file_path, name, kind, export_name in rows]


def fetch_edges_rows(database_path: Path) -> list[tuple[str, str, str, str | None, int | None]]:
    with sqlite3.connect(database_path) as connection:
        rows = connection.execute(
            "SELECT source_path, kind, target_path, detail, line FROM edges ORDER BY source_path, kind, target_path, COALESCE(line, 0), COALESCE(detail, '')"
        ).fetchall()

    return [(source_path, kind, target_path, detail, line) for source_path, kind, target_path, detail, line in rows]


def fetch_edges_columns(database_path: Path) -> list[str]:
    with sqlite3.connect(database_path) as connection:
        rows = connection.execute("PRAGMA table_info(edges)").fetchall()

    return [name for _, name, *_ in rows]


def fetch_artifact_rows(database_path: Path) -> list[tuple[str, str, str, str]]:
    with sqlite3.connect(database_path) as connection:
        rows = connection.execute(
            "SELECT file_path, kind, title, search_text FROM artifacts ORDER BY file_path"
        ).fetchall()

    return [(file_path, kind, title, search_text) for file_path, kind, title, search_text in rows]


def fetch_artifact_columns(database_path: Path) -> list[str]:
    with sqlite3.connect(database_path) as connection:
        rows = connection.execute("PRAGMA table_info(artifacts)").fetchall()

    return [name for _, name, *_ in rows]


def read_snapshot(target: Path) -> dict[str, object]:
    snapshot_path = target / ".ccw" / "snapshots" / SNAPSHOT_NAME
    return json.loads(snapshot_path.read_text(encoding="utf-8"))


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def expected_row(path: str, content: str, language: str) -> tuple[str, str, int, str]:
    encoded = content.encode("utf-8")
    return (path, hashlib.sha256(encoded).hexdigest(), len(encoded), language)


def expected_row_from_file(target: Path, relative_path: str, language: str) -> tuple[str, str, int, str]:
    return expected_row(relative_path, (target / relative_path).read_text(encoding="utf-8"), language)


def expected_symbol_row(file_path: str, name: str, kind: str, line: int, end_line: int) -> tuple[str, str, str, int, int]:
    return (file_path, name, kind, line, end_line)


def expected_symbol_export_row(
    file_path: str,
    name: str,
    kind: str,
    export_name: str | None,
) -> tuple[str, str, str, str | None]:
    return (file_path, name, kind, export_name)


def expected_edge_row(
    source_path: str,
    kind: str,
    target_path: str,
    detail: str | None,
    line: int | None,
) -> tuple[str, str, str, str | None, int | None]:
    return (source_path, kind, target_path, detail, line)


def expected_artifact_row(file_path: str, kind: str, title: str, search_text: str) -> tuple[str, str, str, str]:
    return (file_path, kind, title, search_text)


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
            write_text(target / "__pycache__" / "app.cpython-312.pyc", "bytecode\n")
            write_text(target / ".venv" / "bin" / "python", "#!/usr/bin/env python\n")
            write_text(target / ".openclaw" / "agents" / "main" / "sessions" / "run.trajectory.jsonl", "{}\n")
            write_text(target / "package.egg-info" / "PKG-INFO", "Name: fixture\n")

            symlink_path = target / "linked.py"
            symlink_created = False
            try:
                symlink_path.symlink_to(target / "src" / "app.py")
                symlink_created = True
            except OSError:
                pass

            result = run_ccw("index", cwd=target)

            self.assertEqual(result.returncode, 0, result.stderr)
            database_path = target / ".ccw" / "index.sqlite"
            rows = fetch_files_rows(database_path)
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
            self.assertEqual(
                fetch_file_signal_rows(database_path),
                [
                    ("README.md", None, None, None, None),
                    ("config/settings.yaml", None, None, None, None),
                    ("notes.txt", None, None, None, None),
                    ("package.json", None, None, None, None),
                    ("src/app.py", None, None, None, None),
                ],
            )
            indexed_paths = [path for path, *_ in rows]
            self.assertNotIn(".ccw/config.yaml", indexed_paths)
            self.assertNotIn(".git/HEAD", indexed_paths)
            self.assertNotIn("__pycache__/app.cpython-312.pyc", indexed_paths)
            self.assertNotIn(".venv/bin/python", indexed_paths)
            self.assertNotIn(".openclaw/agents/main/sessions/run.trajectory.jsonl", indexed_paths)
            self.assertNotIn("package.egg-info/PKG-INFO", indexed_paths)
            self.assertEqual(fetch_symbols_rows(database_path), [])
            self.assertEqual(fetch_edges_rows(database_path), [])
            self.assertEqual(
                fetch_artifact_rows(database_path),
                [
                    expected_artifact_row("README.md", "markdown", "Sample repo", "# Sample repo"),
                    expected_artifact_row("config/settings.yaml", "yaml", "settings", "mode: test"),
                    expected_artifact_row("package.json", "json", "package", '{"name":"fixture"}'),
                ],
            )
            if symlink_created:
                self.assertNotIn("linked.py", indexed_paths)

    def test_index_is_stable_when_repo_contents_do_not_change(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir)
            self.assertEqual(run_ccw("init", cwd=target).returncode, 0)
            write_text(target / "src" / "app.py", "def stable():\n    return 'stable'\n")
            write_text(target / "docs" / "guide.md", "Guide\n")

            first = run_ccw("index", cwd=target)
            database_path = target / ".ccw" / "index.sqlite"
            first_rows = fetch_files_rows(database_path)
            first_symbols = fetch_symbols_rows(database_path)
            first_edges = fetch_edges_rows(database_path)
            first_artifacts = fetch_artifact_rows(database_path)
            first_snapshot = read_snapshot(target)

            second = run_ccw("index", cwd=target)
            second_rows = fetch_files_rows(database_path)
            second_symbols = fetch_symbols_rows(database_path)
            second_edges = fetch_edges_rows(database_path)
            second_artifacts = fetch_artifact_rows(database_path)
            second_snapshot = read_snapshot(target)

            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertEqual(first_rows, second_rows)
            self.assertEqual(first_symbols, second_symbols)
            self.assertEqual(first_edges, second_edges)
            self.assertEqual(first_artifacts, second_artifacts)
            self.assertEqual(first_snapshot, second_snapshot)

    def test_index_accepts_an_explicit_target_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            target = root / "repo"
            target.mkdir()
            self.assertEqual(run_ccw("init", str(target), cwd=root).returncode, 0)
            write_text(target / "src" / "tool.ts", "export const tool = 1;\n")

            result = run_ccw("index", str(target), cwd=root)

            self.assertEqual(result.returncode, 0, result.stderr)
            database_path = target / ".ccw" / "index.sqlite"
            self.assertEqual(
                fetch_files_rows(database_path),
                [expected_row("src/tool.ts", "export const tool = 1;\n", "typescript")],
            )
            self.assertEqual(fetch_symbols_rows(database_path), [expected_symbol_row("src/tool.ts", "tool", "variable", 1, 1)])
            self.assertEqual(fetch_edges_rows(database_path), [])

    def test_index_persists_python_top_level_symbols_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir)
            self.assertEqual(run_ccw("init", cwd=target).returncode, 0)
            write_text(
                target / "src" / "app.py",
                "class Greeter:\n"
                "    def greet(self) -> str:\n"
                "        return 'hi'\n"
                "\n"
                "def helper():\n"
                "    def inner():\n"
                "        return None\n"
                "    return inner()\n"
                "\n"
                "async def run():\n"
                "    return None\n",
            )

            result = run_ccw("index", cwd=target)

            self.assertEqual(result.returncode, 0, result.stderr)
            database_path = target / ".ccw" / "index.sqlite"
            self.assertEqual(
                fetch_symbols_rows(database_path),
                [
                    expected_symbol_row("src/app.py", "Greeter", "class", 1, 3),
                    expected_symbol_row("src/app.py", "helper", "function", 5, 8),
                    expected_symbol_row("src/app.py", "run", "async_function", 10, 11),
                ],
            )
            self.assertEqual(
                fetch_symbol_export_rows(database_path),
                [
                    expected_symbol_export_row("src/app.py", "Greeter", "class", "Greeter"),
                    expected_symbol_export_row("src/app.py", "helper", "function", "helper"),
                    expected_symbol_export_row("src/app.py", "run", "async_function", "run"),
                ],
            )

    def test_index_persists_script_async_functions(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir)
            self.assertEqual(run_ccw("init", cwd=target).returncode, 0)
            write_text(target / "src" / "app.ts", "export async function load() {}\n")

            result = run_ccw("index", cwd=target)

            self.assertEqual(result.returncode, 0, result.stderr)
            database_path = target / ".ccw" / "index.sqlite"
            self.assertEqual(
                fetch_symbols_rows(database_path),
                [expected_symbol_row("src/app.ts", "load", "async_function", 1, 1)],
            )
            self.assertEqual(
                fetch_symbol_export_rows(database_path),
                [expected_symbol_export_row("src/app.ts", "load", "async_function", "load")],
            )

    def test_index_respects_python_all_exports_and_local_import_edges(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir)
            self.assertEqual(run_ccw("init", cwd=target).returncode, 0)
            write_text(target / "pkg" / "helpers.py", "def helper_value():\n    return 1\n")
            write_text(
                target / "pkg" / "module.py",
                "from .helpers import helper_value\n"
                "\n"
                "def public():\n"
                "    return helper_value()\n"
                "\n"
                "def hidden():\n"
                "    return 0\n"
                "\n"
                "__all__ = ['hidden']\n",
            )

            result = run_ccw("index", cwd=target)

            self.assertEqual(result.returncode, 0, result.stderr)
            database_path = target / ".ccw" / "index.sqlite"
            self.assertEqual(
                fetch_symbol_export_rows(database_path),
                [
                    expected_symbol_export_row("pkg/helpers.py", "helper_value", "function", "helper_value"),
                    expected_symbol_export_row("pkg/module.py", "public", "function", None),
                    expected_symbol_export_row("pkg/module.py", "hidden", "function", "hidden"),
                ],
            )
            self.assertEqual(
                fetch_edges_rows(database_path),
                [expected_edge_row("pkg/module.py", "import", "pkg/helpers.py", ".helpers", 1)],
            )

    def test_index_collects_mixed_language_fixture_output_and_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "repo"
            copy_fixture_repo("mixed_repo", target)
            initialize_fixture_git_repo(target)
            self.assertEqual(run_ccw("init", str(target), cwd=target.parent).returncode, 0)

            result = run_ccw("index", str(target), cwd=target.parent)

            self.assertEqual(result.returncode, 0, result.stderr)
            database_path = target / ".ccw" / "index.sqlite"

            expected_files = [
                expected_row_from_file(target, "README.md", "markdown"),
                expected_row_from_file(target, "config/settings.yaml", "yaml"),
                expected_row_from_file(target, "docs/guide.md", "markdown"),
                expected_row_from_file(target, "package.json", "json"),
                expected_row_from_file(target, "pkg/__init__.py", "python"),
                expected_row_from_file(target, "pkg/core.py", "python"),
                expected_row_from_file(target, "pkg/helpers.py", "python"),
                expected_row_from_file(target, "tests/test_core.py", "python"),
                expected_row_from_file(target, "web/index.ts", "typescript"),
                expected_row_from_file(target, "web/legacy.js", "javascript"),
                expected_row_from_file(target, "web/math.js", "javascript"),
                expected_row_from_file(target, "web/util.test.ts", "typescript"),
                expected_row_from_file(target, "web/util.ts", "typescript"),
            ]
            self.assertEqual(fetch_files_rows(database_path), expected_files)
            self.assertEqual(
                fetch_file_signal_rows(database_path),
                [
                    (path, FIXTURE_COMMIT_TIMESTAMP, FIXTURE_COMMIT_EMAIL, FIXTURE_COMMIT_EMAIL, 1)
                    for path, *_ in expected_files
                ],
            )
            self.assertEqual(
                fetch_symbols_rows(database_path),
                [
                    expected_symbol_row("pkg/core.py", "PublicThing", "class", 4, 5),
                    expected_symbol_row("pkg/core.py", "build", "function", 8, 9),
                    expected_symbol_row("pkg/core.py", "_private", "function", 12, 13),
                    expected_symbol_row("pkg/helpers.py", "helper_value", "function", 1, 2),
                    expected_symbol_row("tests/test_core.py", "test_public_thing", "function", 4, 5),
                    expected_symbol_row("web/index.ts", "webEntry", "variable", 3, 3),
                    expected_symbol_row("web/legacy.js", "total", "variable", 2, 2),
                    expected_symbol_row("web/math.js", "sum", "function", 1, 1),
                    expected_symbol_row("web/util.test.ts", "utilTest", "variable", 3, 3),
                    expected_symbol_row("web/util.ts", "util", "function", 1, 1),
                    expected_symbol_row("web/util.ts", "VALUE", "variable", 2, 2),
                ],
            )
            self.assertEqual(
                fetch_symbol_export_rows(database_path),
                [
                    expected_symbol_export_row("pkg/core.py", "PublicThing", "class", "PublicThing"),
                    expected_symbol_export_row("pkg/core.py", "build", "function", "build"),
                    expected_symbol_export_row("pkg/core.py", "_private", "function", None),
                    expected_symbol_export_row("pkg/helpers.py", "helper_value", "function", "helper_value"),
                    expected_symbol_export_row("tests/test_core.py", "test_public_thing", "function", "test_public_thing"),
                    expected_symbol_export_row("web/index.ts", "webEntry", "variable", "webEntry"),
                    expected_symbol_export_row("web/legacy.js", "total", "variable", "total"),
                    expected_symbol_export_row("web/math.js", "sum", "function", "sum"),
                    expected_symbol_export_row("web/util.test.ts", "utilTest", "variable", "utilTest"),
                    expected_symbol_export_row("web/util.ts", "util", "function", "util"),
                    expected_symbol_export_row("web/util.ts", "VALUE", "variable", "VALUE"),
                ],
            )
            self.assertEqual(
                fetch_edges_rows(database_path),
                [
                    expected_edge_row("pkg/__init__.py", "import", "pkg/core.py", ".core", 1),
                    expected_edge_row("pkg/core.py", "import", "pkg/helpers.py", ".helpers", 1),
                    expected_edge_row("tests/test_core.py", "import", "pkg/core.py", "pkg.core", 1),
                    expected_edge_row("tests/test_core.py", "tests", "pkg/core.py", "import", None),
                    expected_edge_row("web/index.ts", "import", "web/util.ts", "./util", 1),
                    expected_edge_row("web/index.ts", "re_export", "web/util.ts", "./util", 2),
                    expected_edge_row("web/legacy.js", "import", "web/math.js", "./math.js", 1),
                    expected_edge_row("web/util.test.ts", "import", "web/util.ts", "./util", 1),
                    expected_edge_row("web/util.test.ts", "tests", "web/util.ts", "import", None),
                ],
            )
            self.assertEqual(
                fetch_artifact_rows(database_path),
                [
                    expected_artifact_row(
                        "README.md",
                        "markdown",
                        "Mixed Fixture",
                        "# Mixed Fixture Phase 2 indexing fixture.",
                    ),
                    expected_artifact_row(
                        "config/settings.yaml",
                        "yaml",
                        "settings",
                        "mode: deterministic owner: fixture",
                    ),
                    expected_artifact_row(
                        "docs/guide.md",
                        "markdown",
                        "Guide",
                        "# Guide Deterministic docs are searchable.",
                    ),
                    expected_artifact_row(
                        "package.json",
                        "json",
                        "package",
                        '{"name":"mixed-fixture","version":"1.0.0"}',
                    ),
                ],
            )

            expected_snapshot = {
                "artifacts": [
                    {
                        "file_path": "README.md",
                        "kind": "markdown",
                        "title": "Mixed Fixture",
                        "search_text": "# Mixed Fixture Phase 2 indexing fixture.",
                    },
                    {
                        "file_path": "config/settings.yaml",
                        "kind": "yaml",
                        "title": "settings",
                        "search_text": "mode: deterministic owner: fixture",
                    },
                    {
                        "file_path": "docs/guide.md",
                        "kind": "markdown",
                        "title": "Guide",
                        "search_text": "# Guide Deterministic docs are searchable.",
                    },
                    {
                        "file_path": "package.json",
                        "kind": "json",
                        "title": "package",
                        "search_text": '{"name":"mixed-fixture","version":"1.0.0"}',
                    },
                ],
                "edges": [
                    {"detail": ".core", "kind": "import", "line": 1, "source_path": "pkg/__init__.py", "target_path": "pkg/core.py"},
                    {"detail": ".helpers", "kind": "import", "line": 1, "source_path": "pkg/core.py", "target_path": "pkg/helpers.py"},
                    {"detail": "pkg.core", "kind": "import", "line": 1, "source_path": "tests/test_core.py", "target_path": "pkg/core.py"},
                    {"detail": "import", "kind": "tests", "line": None, "source_path": "tests/test_core.py", "target_path": "pkg/core.py"},
                    {"detail": "./util", "kind": "import", "line": 1, "source_path": "web/index.ts", "target_path": "web/util.ts"},
                    {"detail": "./util", "kind": "re_export", "line": 2, "source_path": "web/index.ts", "target_path": "web/util.ts"},
                    {"detail": "./math.js", "kind": "import", "line": 1, "source_path": "web/legacy.js", "target_path": "web/math.js"},
                    {"detail": "./util", "kind": "import", "line": 1, "source_path": "web/util.test.ts", "target_path": "web/util.ts"},
                    {"detail": "import", "kind": "tests", "line": None, "source_path": "web/util.test.ts", "target_path": "web/util.ts"},
                ],
                "files": [
                    {
                        "content_hash": content_hash,
                        "language": language,
                        "last_author_email": FIXTURE_COMMIT_EMAIL,
                        "last_commit_at": FIXTURE_COMMIT_TIMESTAMP,
                        "owner_commit_count": 1,
                        "owner_email": FIXTURE_COMMIT_EMAIL,
                        "path": path,
                        "size_bytes": size_bytes,
                    }
                    for path, content_hash, size_bytes, language in expected_files
                ],
                "symbols": [
                    {"end_line": 5, "export_name": "PublicThing", "file_path": "pkg/core.py", "kind": "class", "line": 4, "name": "PublicThing"},
                    {"end_line": 9, "export_name": "build", "file_path": "pkg/core.py", "kind": "function", "line": 8, "name": "build"},
                    {"end_line": 13, "export_name": None, "file_path": "pkg/core.py", "kind": "function", "line": 12, "name": "_private"},
                    {"end_line": 2, "export_name": "helper_value", "file_path": "pkg/helpers.py", "kind": "function", "line": 1, "name": "helper_value"},
                    {"end_line": 5, "export_name": "test_public_thing", "file_path": "tests/test_core.py", "kind": "function", "line": 4, "name": "test_public_thing"},
                    {"end_line": 3, "export_name": "webEntry", "file_path": "web/index.ts", "kind": "variable", "line": 3, "name": "webEntry"},
                    {"end_line": 2, "export_name": "total", "file_path": "web/legacy.js", "kind": "variable", "line": 2, "name": "total"},
                    {"end_line": 1, "export_name": "sum", "file_path": "web/math.js", "kind": "function", "line": 1, "name": "sum"},
                    {"end_line": 3, "export_name": "utilTest", "file_path": "web/util.test.ts", "kind": "variable", "line": 3, "name": "utilTest"},
                    {"end_line": 1, "export_name": "util", "file_path": "web/util.ts", "kind": "function", "line": 1, "name": "util"},
                    {"end_line": 2, "export_name": "VALUE", "file_path": "web/util.ts", "kind": "variable", "line": 2, "name": "VALUE"},
                ],
            }
            self.assertEqual(read_snapshot(target), expected_snapshot)

    def test_index_resolves_parent_directory_script_imports_and_re_exports(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir)
            self.assertEqual(run_ccw("init", cwd=target).returncode, 0)
            write_text(target / "src" / "lib" / "util.ts", "export function util() {}\n")
            write_text(
                target / "src" / "feature" / "index.ts",
                "import { util } from '../lib/util';\n"
                "export { util } from '../lib/util';\n",
            )

            result = run_ccw("index", cwd=target)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(
                fetch_edges_rows(target / ".ccw" / "index.sqlite"),
                [
                    expected_edge_row("src/feature/index.ts", "import", "src/lib/util.ts", "../lib/util", 1),
                    expected_edge_row("src/feature/index.ts", "re_export", "src/lib/util.ts", "../lib/util", 2),
                ],
            )

    def test_index_skips_ambiguous_test_mapping(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir)
            self.assertEqual(run_ccw("init", cwd=target).returncode, 0)
            write_text(target / "src" / "shared.py", "def source():\n    return 1\n")
            write_text(target / "pkg" / "shared.py", "def package_source():\n    return 2\n")
            write_text(target / "tests" / "test_shared.py", "def test_shared():\n    return None\n")

            result = run_ccw("index", cwd=target)

            self.assertEqual(result.returncode, 0, result.stderr)
            database_path = target / ".ccw" / "index.sqlite"
            self.assertEqual(
                [edge for edge in fetch_edges_rows(database_path) if edge[1] == "tests"],
                [],
            )

    def test_index_skips_conflicting_naming_and_import_test_mapping(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir)
            self.assertEqual(run_ccw("init", cwd=target).returncode, 0)
            write_text(target / "src" / "alpha.py", "def alpha():\n    return 1\n")
            write_text(target / "src" / "beta.py", "def beta():\n    return 2\n")
            write_text(
                target / "tests" / "test_alpha.py",
                "from src.beta import beta\n\n"
                "def test_alpha():\n"
                "    assert beta() == 2\n",
            )

            result = run_ccw("index", cwd=target)

            self.assertEqual(result.returncode, 0, result.stderr)
            database_path = target / ".ccw" / "index.sqlite"
            self.assertEqual(
                [edge for edge in fetch_edges_rows(database_path) if edge[1] == "tests"],
                [],
            )

    def test_index_skips_naming_match_when_import_targets_are_multiple(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir)
            self.assertEqual(run_ccw("init", cwd=target).returncode, 0)
            write_text(target / "src" / "alpha.py", "def alpha():\n    return 1\n")
            write_text(target / "src" / "beta.py", "def beta():\n    return 2\n")
            write_text(
                target / "tests" / "test_alpha.py",
                "from src import alpha, beta\n\n"
                "def test_alpha():\n"
                "    assert alpha() != beta()\n",
            )

            result = run_ccw("index", cwd=target)

            self.assertEqual(result.returncode, 0, result.stderr)
            database_path = target / ".ccw" / "index.sqlite"
            self.assertEqual(
                [edge for edge in fetch_edges_rows(database_path) if edge[1] == "tests"],
                [],
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

    def test_index_refreshes_changed_and_deleted_python_symbols(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir)
            self.assertEqual(run_ccw("init", cwd=target).returncode, 0)
            app_path = target / "src" / "app.py"
            stale_path = target / "src" / "stale.py"
            write_text(app_path, "def first():\n    return 1\n")
            write_text(stale_path, "class Stale:\n    pass\n")

            first = run_ccw("index", cwd=target)
            self.assertEqual(first.returncode, 0, first.stderr)

            write_text(app_path, "async def second():\n    return 2\n")
            stale_path.unlink()

            second = run_ccw("index", cwd=target)

            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertEqual(
                fetch_symbols_rows(target / ".ccw" / "index.sqlite"),
                [expected_symbol_row("src/app.py", "second", "async_function", 1, 2)],
            )

    def test_index_fails_on_invalid_python_syntax_and_preserves_previous_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir)
            self.assertEqual(run_ccw("init", cwd=target).returncode, 0)
            app_path = target / "src" / "app.py"
            helper_path = target / "src" / "helper.py"
            readme_path = target / "README.md"
            write_text(helper_path, "def helper():\n    return 1\n")
            write_text(app_path, "from .helper import helper\n\ndef valid():\n    return helper()\n")
            write_text(readme_path, "# Stable\n")

            first = run_ccw("index", cwd=target)
            self.assertEqual(first.returncode, 0, first.stderr)
            database_path = target / ".ccw" / "index.sqlite"
            original_files = fetch_files_rows(database_path)
            original_symbols = fetch_symbols_rows(database_path)
            original_edges = fetch_edges_rows(database_path)
            original_artifacts = fetch_artifact_rows(database_path)
            original_snapshot = read_snapshot(target)

            write_text(app_path, "def broken(:\n    return 2\n")

            second = run_ccw("index", cwd=target)

            self.assertNotEqual(second.returncode, 0)
            self.assertTrue(second.stderr.startswith("Error: "))
            self.assertIn("Invalid Python syntax", second.stderr)
            self.assertEqual(fetch_files_rows(database_path), original_files)
            self.assertEqual(fetch_symbols_rows(database_path), original_symbols)
            self.assertEqual(fetch_edges_rows(database_path), original_edges)
            self.assertEqual(fetch_artifact_rows(database_path), original_artifacts)
            self.assertEqual(read_snapshot(target), original_snapshot)

    def test_index_preserves_previous_state_when_snapshot_write_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir)
            self.assertEqual(run_ccw("init", cwd=target).returncode, 0)
            app_path = target / "src" / "app.py"
            write_text(app_path, "def first():\n    return 1\n")

            first = run_ccw("index", cwd=target)
            self.assertEqual(first.returncode, 0, first.stderr)

            database_path = target / ".ccw" / "index.sqlite"
            original_files = fetch_files_rows(database_path)
            original_symbols = fetch_symbols_rows(database_path)
            original_snapshot = read_snapshot(target)

            write_text(app_path, "def second():\n    return 2\n")
            snapshots_dir = target / ".ccw" / "snapshots"
            snapshots_dir.chmod(0o555)

            try:
                second = run_ccw("index", cwd=target)
            finally:
                snapshots_dir.chmod(0o755)

            self.assertNotEqual(second.returncode, 0)
            self.assertEqual(fetch_files_rows(database_path), original_files)
            self.assertEqual(fetch_symbols_rows(database_path), original_symbols)
            self.assertEqual(read_snapshot(target), original_snapshot)

    def test_index_upgrades_phase_1_placeholder_tables(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir)
            state_dir = target / ".ccw"
            state_dir.mkdir()
            (state_dir / "compiled").mkdir()
            (state_dir / "snapshots").mkdir()
            write_text(state_dir / "config.yaml", "config_version: 1\n")
            write_text(target / "main.py", "def build():\n    return True\n")
            write_text(target / "README.md", "# Build\n")

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
            database_path = state_dir / "index.sqlite"
            self.assertEqual(
                fetch_files_columns(database_path),
                [
                    "id",
                    "path",
                    "content_hash",
                    "size_bytes",
                    "language",
                    "last_commit_at",
                    "last_author_email",
                    "owner_email",
                    "owner_commit_count",
                ],
            )
            self.assertEqual(
                fetch_symbols_columns(database_path),
                ["id", "file_path", "name", "kind", "line", "end_line", "export_name"],
            )
            self.assertEqual(
                fetch_edges_columns(database_path),
                ["id", "source_path", "kind", "target_path", "detail", "line"],
            )
            self.assertEqual(
                fetch_artifact_columns(database_path),
                ["id", "file_path", "kind", "title", "search_text"],
            )
            self.assertEqual(
                fetch_files_rows(database_path),
                [
                    expected_row("README.md", "# Build\n", "markdown"),
                    expected_row("main.py", "def build():\n    return True\n", "python"),
                ],
            )
            self.assertEqual(
                fetch_symbols_rows(database_path),
                [expected_symbol_row("main.py", "build", "function", 1, 2)],
            )
            self.assertEqual(fetch_edges_rows(database_path), [])
            self.assertEqual(
                fetch_artifact_rows(database_path),
                [expected_artifact_row("README.md", "markdown", "Build", "# Build")],
            )

    def test_index_upgrades_phase_2b_index_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir)
            state_dir = target / ".ccw"
            state_dir.mkdir()
            (state_dir / "compiled").mkdir()
            (state_dir / "snapshots").mkdir()
            write_text(state_dir / "config.yaml", "config_version: 1\n")
            write_text(target / "src" / "current.py", "from .helper import helper\n\ndef current():\n    return helper()\n")
            write_text(target / "src" / "helper.py", "def helper():\n    return 1\n")

            with sqlite3.connect(state_dir / "index.sqlite") as connection:
                connection.executescript(
                    """
                    CREATE TABLE files (
                        id INTEGER PRIMARY KEY,
                        path TEXT NOT NULL UNIQUE,
                        content_hash TEXT NOT NULL,
                        size_bytes INTEGER NOT NULL,
                        language TEXT NOT NULL
                    );
                    CREATE TABLE symbols (
                        id INTEGER PRIMARY KEY,
                        file_path TEXT NOT NULL,
                        name TEXT NOT NULL,
                        kind TEXT NOT NULL,
                        line INTEGER NOT NULL,
                        end_line INTEGER NOT NULL
                    );
                    CREATE TABLE edges (id INTEGER PRIMARY KEY);
                    CREATE TABLE facts (id INTEGER PRIMARY KEY);
                    CREATE TABLE episodes (id INTEGER PRIMARY KEY);
                    """
                )
                connection.execute(
                    "INSERT INTO files (path, content_hash, size_bytes, language) VALUES (?, ?, ?, ?)",
                    ("stale.py", "outdated", 7, "python"),
                )
                connection.execute(
                    "INSERT INTO symbols (file_path, name, kind, line, end_line) VALUES (?, ?, ?, ?, ?)",
                    ("stale.py", "stale", "function", 1, 1),
                )
                connection.commit()

            result = run_ccw("index", cwd=target)

            self.assertEqual(result.returncode, 0, result.stderr)
            database_path = state_dir / "index.sqlite"
            self.assertEqual(
                fetch_files_columns(database_path),
                [
                    "id",
                    "path",
                    "content_hash",
                    "size_bytes",
                    "language",
                    "last_commit_at",
                    "last_author_email",
                    "owner_email",
                    "owner_commit_count",
                ],
            )
            self.assertEqual(
                fetch_symbols_columns(database_path),
                ["id", "file_path", "name", "kind", "line", "end_line", "export_name"],
            )
            self.assertEqual(
                fetch_files_rows(database_path),
                [
                    expected_row("src/current.py", "from .helper import helper\n\ndef current():\n    return helper()\n", "python"),
                    expected_row("src/helper.py", "def helper():\n    return 1\n", "python"),
                ],
            )
            self.assertEqual(
                fetch_symbols_rows(database_path),
                [
                    expected_symbol_row("src/current.py", "current", "function", 3, 4),
                    expected_symbol_row("src/helper.py", "helper", "function", 1, 2),
                ],
            )
            self.assertEqual(
                fetch_edges_rows(database_path),
                [expected_edge_row("src/current.py", "import", "src/helper.py", ".helper", 1)],
            )


if __name__ == "__main__":
    unittest.main()
