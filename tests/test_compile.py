from __future__ import annotations

import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ccw.compile import (
    CompiledContext,
    ContextSection,
    RankedFile,
    Snippet,
    compile_context,
    extract_snippets,
    rank_file_lanes,
    rank_files,
    render_compiled_context,
)
from ccw.recipe import allocate_budget, get_recipe


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


class RankFilesTests(unittest.TestCase):
    def test_rank_files_respects_max_items(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir)
            state_dir = target / ".ccw"
            state_dir.mkdir(parents=True, exist_ok=True)
            (state_dir / "compiled").mkdir(parents=True, exist_ok=True)
            (state_dir / "snapshots").mkdir(parents=True, exist_ok=True)
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
                        last_commit_at INTEGER
                    );
                    INSERT INTO files (path, content_hash, size_bytes, language, last_commit_at)
                    VALUES
                        ('src/auth/login.py', 'a', 1, 'python', NULL),
                        ('src/utils/login_helper.py', 'b', 1, 'python', NULL),
                        ('src/api/login_handler.py', 'c', 1, 'python', NULL);
                    """
                )

            ranked = rank_files(
                target=target,
                task_description="Fix the login bug",
                database_path=database_path,
                max_items=2,
            )

            self.assertEqual(len(ranked), 2)

    def test_rank_files_empty_task_returns_empty(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir)
            state_dir = target / ".ccw"
            state_dir.mkdir(parents=True, exist_ok=True)
            (state_dir / "compiled").mkdir(parents=True, exist_ok=True)
            (state_dir / "snapshots").mkdir(parents=True, exist_ok=True)
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
                        last_commit_at INTEGER
                    );
                    INSERT INTO files (path, content_hash, size_bytes, language, last_commit_at)
                    VALUES ('src/auth/login.py', 'a', 1, 'python', NULL);
                    """
                )

            ranked = rank_files(
                target=target,
                task_description="",
                database_path=database_path,
                max_items=10,
            )

            self.assertEqual(ranked, [])

    def test_rank_files_fuzzy_prefix_match(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir)
            state_dir = target / ".ccw"
            state_dir.mkdir(parents=True, exist_ok=True)
            (state_dir / "compiled").mkdir(parents=True, exist_ok=True)
            (state_dir / "snapshots").mkdir(parents=True, exist_ok=True)
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
                        last_commit_at INTEGER
                    );
                    INSERT INTO files (path, content_hash, size_bytes, language, last_commit_at)
                    VALUES
                        ('src/auth/login.py', 'a', 1, 'python', NULL),
                        ('src/notmatched/other.py', 'b', 1, 'python', NULL);
                    """
                )

            ranked = rank_files(
                target=target,
                task_description="auth fix",
                database_path=database_path,
                max_items=10,
            )

            self.assertGreater(len(ranked), 0)
            self.assertEqual(ranked[0].file_path, "src/auth/login.py")

    def test_rank_files_symbol_name_boosts_score(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir)
            state_dir = target / ".ccw"
            state_dir.mkdir(parents=True, exist_ok=True)
            (state_dir / "compiled").mkdir(parents=True, exist_ok=True)
            (state_dir / "snapshots").mkdir(parents=True, exist_ok=True)
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
                        last_commit_at INTEGER
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
                    INSERT INTO files (path, content_hash, size_bytes, language, last_commit_at)
                    VALUES
                        ('src/auth/login.py', 'a', 1, 'python', NULL),
                        ('src/other/stuff.py', 'b', 1, 'python', NULL);
                    INSERT INTO symbols (file_path, name, kind, line, end_line)
                    VALUES
                        ('src/other/stuff.py', 'authenticate', 'function', 1, 5);
                    """
                )

            ranked = rank_files(
                target=target,
                task_description="authenticate user",
                database_path=database_path,
                max_items=10,
            )

            self.assertEqual(ranked[0].file_path, "src/other/stuff.py")

    def test_rank_files_git_freshness_boost(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir)
            state_dir = target / ".ccw"
            state_dir.mkdir(parents=True, exist_ok=True)
            (state_dir / "compiled").mkdir(parents=True, exist_ok=True)
            (state_dir / "snapshots").mkdir(parents=True, exist_ok=True)
            write_text(state_dir / "config.yaml", "config_version: 1\n")
            database_path = state_dir / "index.sqlite"

            import time
            now = int(time.time())
            recent = now - 86400  # 1 day ago (within 7 days)
            old = now - 86400 * 60  # 60 days ago (outside 30 days)

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
                        last_commit_at INTEGER
                    );
                    """
                )
                connection.execute(
                    "INSERT INTO files (path, content_hash, size_bytes, language, last_commit_at) VALUES (?, ?, ?, ?, ?)",
                    ("src/recent/file.py", "a", 1, "python", recent),
                )
                connection.execute(
                    "INSERT INTO files (path, content_hash, size_bytes, language, last_commit_at) VALUES (?, ?, ?, ?, ?)",
                    ("src/old/file.py", "b", 1, "python", old),
                )

            ranked = rank_files(
                target=target,
                task_description="check file",
                database_path=database_path,
                max_items=10,
            )

            # Both have same base path-match score ("file" matches both);
            # freshness boost should make recent file rank higher
            self.assertEqual(len(ranked), 2)
            self.assertEqual(ranked[0].file_path, "src/recent/file.py")
            self.assertGreater(ranked[0].score, ranked[1].score)

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
                    INSERT INTO files (path, content_hash, size_bytes, language, last_commit_at)
                    VALUES
                        ('src/auth/login.py', 'abc', 10, 'python', NULL),
                        ('src/utils/helpers.py', 'def', 10, 'python', NULL);
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

    def test_rank_files_preserves_task_files_when_agentic_context_exists(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir)
            state_dir = target / ".ccw"
            state_dir.mkdir(parents=True, exist_ok=True)
            (state_dir / "compiled").mkdir(parents=True, exist_ok=True)
            (state_dir / "snapshots").mkdir(parents=True, exist_ok=True)
            write_text(state_dir / "config.yaml", "config_version: 1\n")
            database_path = state_dir / "index.sqlite"

            with sqlite3.connect(database_path) as connection:
                connection.executescript(
                    """
                    CREATE TABLE files (
                        id INTEGER PRIMARY KEY,
                        path TEXT NOT NULL UNIQUE,
                        content_hash TEXT NOT NULL,
                        size_bytes INTEGER NOT NULL,
                        language TEXT NOT NULL,
                        last_commit_at INTEGER
                    );
                    INSERT INTO files (path, content_hash, size_bytes, language, last_commit_at)
                    VALUES
                        ('src/auth/login.py', 'a', 1, 'python', NULL),
                        ('src/auth/session.py', 'aa', 1, 'python', NULL),
                        ('src/auth/refresh.py', 'ab', 1, 'python', NULL),
                        ('src/auth/token.py', 'ac', 1, 'python', NULL),
                        ('AGENTS.md', 'b', 1, 'markdown', NULL),
                        ('CONTEXT.md', 'c', 1, 'markdown', NULL),
                        ('wiki/AGENTS.md', 'd', 1, 'markdown', NULL),
                        ('wiki/user/index.md', 'e', 1, 'markdown', NULL),
                        ('wiki/user/log.md', 'f', 1, 'markdown', NULL);
                    """
                )

            ranked = rank_files(
                target=target,
                task_description="Implement login refresh behavior",
                database_path=database_path,
                max_items=5,
            )

            ranked_paths = [rf.file_path for rf in ranked]
            agentic_paths = {
                "AGENTS.md",
                "CONTEXT.md",
                "wiki/AGENTS.md",
                "wiki/user/index.md",
                "wiki/user/log.md",
            }
            self.assertIn("AGENTS.md", ranked_paths)
            self.assertIn("src/auth/login.py", ranked_paths)
            self.assertLessEqual(
                len([p for p in ranked_paths if p in agentic_paths]),
                2,
            )

    def test_rank_file_lanes_prioritize_nested_agentic_context_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir)
            state_dir = target / ".ccw"
            state_dir.mkdir(parents=True, exist_ok=True)
            (state_dir / "compiled").mkdir(parents=True, exist_ok=True)
            (state_dir / "snapshots").mkdir(parents=True, exist_ok=True)
            write_text(state_dir / "config.yaml", "config_version: 1\n")
            database_path = state_dir / "index.sqlite"

            with sqlite3.connect(database_path) as connection:
                connection.executescript(
                    """
                    CREATE TABLE files (
                        id INTEGER PRIMARY KEY,
                        path TEXT NOT NULL UNIQUE,
                        content_hash TEXT NOT NULL,
                        size_bytes INTEGER NOT NULL,
                        language TEXT NOT NULL,
                        last_commit_at INTEGER
                    );
                    INSERT INTO files (path, content_hash, size_bytes, language, last_commit_at)
                    VALUES
                        ('src/auth/login.py', 'a', 1, 'python', NULL),
                        ('src/auth/refresh.py', 'aa', 1, 'python', NULL),
                        ('src/auth/AGENTS.md', 'b', 1, 'markdown', NULL),
                        ('.opencode/instructions/AGENTIC_PLAN_WORKFLOW.instructions', 'c', 1, 'text', NULL),
                        ('.cursor/rules/review.mdc', 'd', 1, 'markdown', NULL);
                    """
                )

            task_ranked, agentic_ranked = rank_file_lanes(
                target=target,
                task_description="Review auth implementation workflow",
                database_path=database_path,
                max_items=5,
                max_agentic_items=3,
            )

            task_paths = [rf.file_path for rf in task_ranked]
            agentic_paths = [rf.file_path for rf in agentic_ranked]
            self.assertIn("src/auth/login.py", task_paths)
            self.assertEqual(agentic_paths[0], "src/auth/AGENTS.md")
            self.assertIn(".opencode/instructions/AGENTIC_PLAN_WORKFLOW.instructions", agentic_paths)
            self.assertIn(".cursor/rules/review.mdc", agentic_paths)

    def test_rank_file_lanes_detects_multiple_harness_context_sources(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir)
            state_dir = target / ".ccw"
            state_dir.mkdir(parents=True, exist_ok=True)
            (state_dir / "compiled").mkdir(parents=True, exist_ok=True)
            (state_dir / "snapshots").mkdir(parents=True, exist_ok=True)
            write_text(state_dir / "config.yaml", "config_version: 1\n")
            database_path = state_dir / "index.sqlite"

            with sqlite3.connect(database_path) as connection:
                connection.executescript(
                    """
                    CREATE TABLE files (
                        id INTEGER PRIMARY KEY,
                        path TEXT NOT NULL UNIQUE,
                        content_hash TEXT NOT NULL,
                        size_bytes INTEGER NOT NULL,
                        language TEXT NOT NULL,
                        last_commit_at INTEGER
                    );
                    INSERT INTO files (path, content_hash, size_bytes, language, last_commit_at)
                    VALUES
                        ('src/auth/login.py', 'a', 1, 'python', NULL),
                        ('.github/copilot-instructions.md', 'b', 1, 'markdown', NULL),
                        ('.cursor/instructions/repo-rules.md', 'c', 1, 'markdown', NULL),
                        ('.codex/policies/safe.md', 'd', 1, 'markdown', NULL),
                        ('.claude/agents/main.md', 'e', 1, 'markdown', NULL);
                    """
                )

            _, agentic_ranked = rank_file_lanes(
                target=target,
                task_description="Implement login behavior",
                database_path=database_path,
                max_items=6,
                max_agentic_items=4,
            )

            agentic_paths = [rf.file_path for rf in agentic_ranked]
            self.assertIn(".github/copilot-instructions.md", agentic_paths)
            self.assertIn(".cursor/instructions/repo-rules.md", agentic_paths)
            self.assertIn(".codex/policies/safe.md", agentic_paths)
            self.assertIn(".claude/agents/main.md", agentic_paths)

    def test_rank_file_lanes_detects_language_and_terminology_hints(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir)
            state_dir = target / ".ccw"
            state_dir.mkdir(parents=True, exist_ok=True)
            (state_dir / "compiled").mkdir(parents=True, exist_ok=True)
            (state_dir / "snapshots").mkdir(parents=True, exist_ok=True)
            write_text(state_dir / "config.yaml", "config_version: 1\n")
            database_path = state_dir / "index.sqlite"

            with sqlite3.connect(database_path) as connection:
                connection.executescript(
                    """
                    CREATE TABLE files (
                        id INTEGER PRIMARY KEY,
                        path TEXT NOT NULL UNIQUE,
                        content_hash TEXT NOT NULL,
                        size_bytes INTEGER NOT NULL,
                        language TEXT NOT NULL,
                        last_commit_at INTEGER
                    );
                    INSERT INTO files (path, content_hash, size_bytes, language, last_commit_at)
                    VALUES
                        ('src/auth/login.py', 'a', 1, 'python', NULL),
                        ('docs/project-language.md', 'b', 1, 'markdown', NULL),
                        ('docs/domain-terminology.md', 'c', 1, 'markdown', NULL);
                    """
                )

            _, agentic_ranked = rank_file_lanes(
                target=target,
                task_description="Implement login behavior",
                database_path=database_path,
                max_items=5,
                max_agentic_items=2,
            )

            agentic_paths = [rf.file_path for rf in agentic_ranked]
            self.assertIn("docs/project-language.md", agentic_paths)
            self.assertIn("docs/domain-terminology.md", agentic_paths)

    def test_rank_file_lanes_does_not_treat_code_language_names_as_agentic(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir)
            state_dir = target / ".ccw"
            state_dir.mkdir(parents=True, exist_ok=True)
            (state_dir / "compiled").mkdir(parents=True, exist_ok=True)
            (state_dir / "snapshots").mkdir(parents=True, exist_ok=True)
            write_text(state_dir / "config.yaml", "config_version: 1\n")
            database_path = state_dir / "index.sqlite"

            with sqlite3.connect(database_path) as connection:
                connection.executescript(
                    """
                    CREATE TABLE files (
                        id INTEGER PRIMARY KEY,
                        path TEXT NOT NULL UNIQUE,
                        content_hash TEXT NOT NULL,
                        size_bytes INTEGER NOT NULL,
                        language TEXT NOT NULL,
                        last_commit_at INTEGER
                    );
                    INSERT INTO files (path, content_hash, size_bytes, language, last_commit_at)
                    VALUES
                        ('src/language_server.py', 'a', 1, 'python', NULL),
                        ('docs/project-language.md', 'b', 1, 'markdown', NULL),
                        ('src/auth/login.py', 'c', 1, 'python', NULL);
                    """
                )

            task_ranked, agentic_ranked = rank_file_lanes(
                target=target,
                task_description="Fix language server login path",
                database_path=database_path,
                max_items=4,
                max_agentic_items=2,
            )

            task_paths = [rf.file_path for rf in task_ranked]
            agentic_paths = [rf.file_path for rf in agentic_ranked]
            self.assertIn("src/language_server.py", task_paths)
            self.assertIn("docs/project-language.md", agentic_paths)
            self.assertNotIn("src/language_server.py", agentic_paths)

    def test_rank_file_lanes_do_not_boost_vendored_agentic_context_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir)
            state_dir = target / ".ccw"
            state_dir.mkdir(parents=True, exist_ok=True)
            (state_dir / "compiled").mkdir(parents=True, exist_ok=True)
            (state_dir / "snapshots").mkdir(parents=True, exist_ok=True)
            write_text(state_dir / "config.yaml", "config_version: 1\n")
            database_path = state_dir / "index.sqlite"

            with sqlite3.connect(database_path) as connection:
                connection.executescript(
                    """
                    CREATE TABLE files (
                        id INTEGER PRIMARY KEY,
                        path TEXT NOT NULL UNIQUE,
                        content_hash TEXT NOT NULL,
                        size_bytes INTEGER NOT NULL,
                        language TEXT NOT NULL,
                        last_commit_at INTEGER
                    );
                    INSERT INTO files (path, content_hash, size_bytes, language, last_commit_at)
                    VALUES
                        ('AGENTS.md', 'a', 1, 'markdown', NULL),
                        ('src/vendor/ccw/AGENTS.md', 'b', 1, 'markdown', NULL),
                        ('src/auth/login.py', 'c', 1, 'python', NULL);
                    """
                )

            task_ranked, agentic_ranked = rank_file_lanes(
                target=target,
                task_description="Review login implementation",
                database_path=database_path,
                max_items=4,
                max_agentic_items=2,
            )

            task_paths = [rf.file_path for rf in task_ranked]
            agentic_paths = [rf.file_path for rf in agentic_ranked]
            self.assertIn("src/auth/login.py", task_paths)
            self.assertIn("AGENTS.md", agentic_paths)
            self.assertNotIn("src/vendor/ccw/AGENTS.md", agentic_paths)

    def test_rank_file_lanes_prioritizes_agentic_anchor_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir)
            state_dir = target / ".ccw"
            state_dir.mkdir(parents=True, exist_ok=True)
            (state_dir / "compiled").mkdir(parents=True, exist_ok=True)
            (state_dir / "snapshots").mkdir(parents=True, exist_ok=True)
            write_text(state_dir / "config.yaml", "config_version: 1\n")
            database_path = state_dir / "index.sqlite"

            with sqlite3.connect(database_path) as connection:
                connection.executescript(
                    """
                    CREATE TABLE files (
                        id INTEGER PRIMARY KEY,
                        path TEXT NOT NULL UNIQUE,
                        content_hash TEXT NOT NULL,
                        size_bytes INTEGER NOT NULL,
                        language TEXT NOT NULL,
                        last_commit_at INTEGER
                    );
                    INSERT INTO files (path, content_hash, size_bytes, language, last_commit_at)
                    VALUES
                        ('src/auth/login.py', 'a', 1, 'python', NULL),
                        ('AGENTS.md', 'b', 1, 'markdown', NULL),
                        ('docs/index.md', 'c', 1, 'markdown', NULL),
                        ('docs/log.md', 'd', 1, 'markdown', NULL),
                        ('.cursor/rules/review.mdc', 'e', 1, 'markdown', NULL);
                    """
                )

            _, agentic_ranked = rank_file_lanes(
                target=target,
                task_description="Implement login behavior",
                database_path=database_path,
                max_items=6,
                max_agentic_items=3,
            )

            agentic_paths = [rf.file_path for rf in agentic_ranked]
            self.assertEqual(agentic_paths[0], "AGENTS.md")
            self.assertIn("docs/index.md", agentic_paths)
            self.assertIn("docs/log.md", agentic_paths)
            self.assertNotIn(".cursor/rules/review.mdc", agentic_paths)

    def test_rank_file_lanes_keeps_third_party_task_files_as_fallback_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir)
            state_dir = target / ".ccw"
            state_dir.mkdir(parents=True, exist_ok=True)
            (state_dir / "compiled").mkdir(parents=True, exist_ok=True)
            (state_dir / "snapshots").mkdir(parents=True, exist_ok=True)
            write_text(state_dir / "config.yaml", "config_version: 1\n")
            database_path = state_dir / "index.sqlite"

            with sqlite3.connect(database_path) as connection:
                connection.executescript(
                    """
                    CREATE TABLE files (
                        id INTEGER PRIMARY KEY,
                        path TEXT NOT NULL UNIQUE,
                        content_hash TEXT NOT NULL,
                        size_bytes INTEGER NOT NULL,
                        language TEXT NOT NULL,
                        last_commit_at INTEGER
                    );
                    INSERT INTO files (path, content_hash, size_bytes, language, last_commit_at)
                    VALUES
                        ('src/auth/login.py', 'a', 1, 'python', NULL),
                        ('src/auth/refresh.py', 'b', 1, 'python', NULL),
                        ('vendor/auth/login.py', 'c', 1, 'python', NULL);
                    """
                )

            task_ranked_small, _ = rank_file_lanes(
                target=target,
                task_description="Implement login refresh behavior",
                database_path=database_path,
                max_items=2,
                max_agentic_items=0,
            )
            small_paths = [rf.file_path for rf in task_ranked_small]
            self.assertEqual(
                small_paths,
                ["src/auth/login.py", "src/auth/refresh.py"],
            )

            task_ranked_large, _ = rank_file_lanes(
                target=target,
                task_description="Implement login refresh behavior",
                database_path=database_path,
                max_items=3,
                max_agentic_items=0,
            )
            large_paths = [rf.file_path for rf in task_ranked_large]
            self.assertEqual(large_paths[-1], "vendor/auth/login.py")

    def test_rank_file_lanes_prioritizes_source_for_implementation_tasks(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir)
            state_dir = target / ".ccw"
            state_dir.mkdir(parents=True, exist_ok=True)
            (state_dir / "compiled").mkdir(parents=True, exist_ok=True)
            (state_dir / "snapshots").mkdir(parents=True, exist_ok=True)
            write_text(state_dir / "config.yaml", "config_version: 1\n")
            database_path = state_dir / "index.sqlite"

            with sqlite3.connect(database_path) as connection:
                connection.executescript(
                    """
                    CREATE TABLE files (
                        id INTEGER PRIMARY KEY,
                        path TEXT NOT NULL UNIQUE,
                        content_hash TEXT NOT NULL,
                        size_bytes INTEGER NOT NULL,
                        language TEXT NOT NULL,
                        last_commit_at INTEGER
                    );
                    INSERT INTO files (path, content_hash, size_bytes, language, last_commit_at)
                    VALUES
                        ('src/retrieval/ranker.py', 'a', 1, 'python', NULL),
                        ('tests/test_ranker.py', 'b', 1, 'python', NULL),
                        ('docs/ranker-design.md', 'c', 1, 'markdown', NULL);
                    """
                )

            impl_ranked, _ = rank_file_lanes(
                target=target,
                task_description="Implement deterministic ranker tie break behavior",
                database_path=database_path,
                max_items=3,
                max_agentic_items=0,
            )
            impl_paths = [rf.file_path for rf in impl_ranked]
            self.assertEqual(impl_paths[0], "src/retrieval/ranker.py")

            test_ranked, _ = rank_file_lanes(
                target=target,
                task_description="Add regression tests for deterministic ranker tie break",
                database_path=database_path,
                max_items=3,
                max_agentic_items=0,
            )
            test_paths = [rf.file_path for rf in test_ranked]
            self.assertEqual(test_paths[0], "tests/test_ranker.py")


class ExtractSnippetsTests(unittest.TestCase):
    def test_extract_snippets_returns_anchored_lines(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir)
            state_dir = target / ".ccw"
            state_dir.mkdir(parents=True, exist_ok=True)
            (state_dir / "compiled").mkdir(parents=True, exist_ok=True)
            (state_dir / "snapshots").mkdir(parents=True, exist_ok=True)
            write_text(state_dir / "config.yaml", "config_version: 1\n")
            database_path = state_dir / "index.sqlite"

            file_content = "import sys\n\ndef login_handler(user, pwd):\n    return authenticate(user, pwd)\n\n"
            write_text(target / "src" / "auth" / "login.py", file_content)

            with sqlite3.connect(database_path) as connection:
                connection.executescript(
                    """
                    CREATE TABLE files (
                        id INTEGER PRIMARY KEY,
                        path TEXT NOT NULL UNIQUE,
                        content_hash TEXT NOT NULL,
                        size_bytes INTEGER NOT NULL,
                        language TEXT NOT NULL,
                        last_commit_at INTEGER
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
                    INSERT INTO files (path, content_hash, size_bytes, language, last_commit_at)
                    VALUES ('src/auth/login.py', 'abc', 30, 'python', NULL);
                    INSERT INTO symbols (file_path, name, kind, line, end_line)
                    VALUES ('src/auth/login.py', 'login_handler', 'function', 2, 4);
                    """
                )

            ranked = rank_files(
                target=target,
                task_description="login handler",
                database_path=database_path,
                max_items=10,
            )

            self.assertEqual(len(ranked), 1)

            with_snippets = extract_snippets(
                target=target,
                ranked_files=ranked,
                task_description="login handler",
                database_path=database_path,
                budget=500,
            )

            self.assertEqual(len(with_snippets), 1)
            self.assertEqual(len(with_snippets[0].snippets), 1)
            snippet = with_snippets[0].snippets[0]
            self.assertEqual(snippet.file_path, "src/auth/login.py")
            # Symbol login_handler is at lines 2-4, expanded ±5 = lines 1-5
            self.assertEqual(snippet.start_line, 1)
            self.assertEqual(snippet.end_line, 5)
            self.assertIn("login_handler", snippet.text)

    def test_extract_snippets_no_symbol_fallback_to_first_lines(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir)
            state_dir = target / ".ccw"
            state_dir.mkdir(parents=True, exist_ok=True)
            (state_dir / "compiled").mkdir(parents=True, exist_ok=True)
            (state_dir / "snapshots").mkdir(parents=True, exist_ok=True)
            write_text(state_dir / "config.yaml", "config_version: 1\n")
            database_path = state_dir / "index.sqlite"

            lines = [f"line{i}\n" for i in range(1, 50)]
            file_content = "".join(lines)
            write_text(target / "src" / "file.py", file_content)

            with sqlite3.connect(database_path) as connection:
                connection.executescript(
                    """
                    CREATE TABLE files (
                        id INTEGER PRIMARY KEY,
                        path TEXT NOT NULL UNIQUE,
                        content_hash TEXT NOT NULL,
                        size_bytes INTEGER NOT NULL,
                        language TEXT NOT NULL,
                        last_commit_at INTEGER
                    );
                    INSERT INTO files (path, content_hash, size_bytes, language, last_commit_at)
                    VALUES ('src/file.py', 'abc', 200, 'python', NULL);
                    """
                )

            ranked = rank_files(
                target=target,
                task_description="check file",
                database_path=database_path,
                max_items=10,
            )

            with_snippets = extract_snippets(
                target=target,
                ranked_files=ranked,
                task_description="check file",
                database_path=database_path,
                budget=500,
            )

            self.assertEqual(len(with_snippets), 1)
            snippet = with_snippets[0].snippets[0]
            self.assertEqual(snippet.file_path, "src/file.py")
            # No symbol match: first 40 lines
            self.assertEqual(snippet.start_line, 1)
            self.assertEqual(snippet.end_line, 40)

    def test_extract_snippets_uses_recent_tail_for_wiki_log(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir)
            state_dir = target / ".ccw"
            state_dir.mkdir(parents=True, exist_ok=True)
            (state_dir / "compiled").mkdir(parents=True, exist_ok=True)
            (state_dir / "snapshots").mkdir(parents=True, exist_ok=True)
            write_text(state_dir / "config.yaml", "config_version: 1\n")
            database_path = state_dir / "index.sqlite"

            log_lines = [f"- old entry {i}\n" for i in range(1, 61)]
            write_text(target / "wiki" / "user" / "log.md", "".join(log_lines))

            with sqlite3.connect(database_path) as connection:
                connection.executescript(
                    """
                    CREATE TABLE files (
                        id INTEGER PRIMARY KEY,
                        path TEXT NOT NULL UNIQUE,
                        content_hash TEXT NOT NULL,
                        size_bytes INTEGER NOT NULL,
                        language TEXT NOT NULL,
                        last_commit_at INTEGER
                    );
                    """
                )

            with_snippets = extract_snippets(
                target=target,
                ranked_files=[RankedFile("wiki/user/log.md", 1.0, "markdown")],
                task_description="review recent work",
                database_path=database_path,
                budget=500,
            )

            snippet = with_snippets[0].snippets[0]
            self.assertEqual(snippet.start_line, 21)
            self.assertEqual(snippet.end_line, 60)
            self.assertNotIn("old entry 1", snippet.text)
            self.assertIn("old entry 60", snippet.text)

    def test_extract_snippets_respects_budget(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir)
            state_dir = target / ".ccw"
            state_dir.mkdir(parents=True, exist_ok=True)
            (state_dir / "compiled").mkdir(parents=True, exist_ok=True)
            (state_dir / "snapshots").mkdir(parents=True, exist_ok=True)
            write_text(state_dir / "config.yaml", "config_version: 1\n")
            database_path = state_dir / "index.sqlite"

            lines = [f"line{i}\n" for i in range(1, 50)]
            file_content = "".join(lines)
            write_text(target / "src" / "big.py", file_content)

            with sqlite3.connect(database_path) as connection:
                connection.executescript(
                    """
                    CREATE TABLE files (
                        id INTEGER PRIMARY KEY,
                        path TEXT NOT NULL UNIQUE,
                        content_hash TEXT NOT NULL,
                        size_bytes INTEGER NOT NULL,
                        language TEXT NOT NULL,
                        last_commit_at INTEGER
                    );
                    INSERT INTO files (path, content_hash, size_bytes, language, last_commit_at)
                    VALUES ('src/big.py', 'abc', 200, 'python', NULL);
                    """
                )

            ranked = rank_files(
                target=target,
                task_description="check file",
                database_path=database_path,
                max_items=10,
            )

            # Budget of 10 chars → ~2 tokens → only ~2 lines
            with_snippets = extract_snippets(
                target=target,
                ranked_files=ranked,
                task_description="check file",
                database_path=database_path,
                budget=10,
            )

            self.assertEqual(len(with_snippets), 1)
            snippet = with_snippets[0].snippets[0]
            # 10 chars budget = ~2 tokens = ~8 char of text + anchor overhead
            snippet_chars = len(snippet.text)
            estimated_tokens = snippet_chars / 4
            self.assertLessEqual(estimated_tokens, 10)


class CompileContextTests(unittest.TestCase):
    def test_compile_context_creates_all_sections(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir)
            state_dir = target / ".ccw"
            snapshots_dir = state_dir / "snapshots"
            snapshots_dir.mkdir(parents=True, exist_ok=True)
            (state_dir / "compiled").mkdir(parents=True, exist_ok=True)
            write_text(state_dir / "config.yaml", "config_version: 1\n")
            database_path = state_dir / "index.sqlite"

            file_content = "def login_handler(user):\n    pass\n"
            write_text(target / "src" / "auth" / "login.py", file_content)

            with sqlite3.connect(database_path) as connection:
                connection.executescript(
                    """
                    CREATE TABLE files (
                        id INTEGER PRIMARY KEY,
                        path TEXT NOT NULL UNIQUE,
                        content_hash TEXT NOT NULL,
                        size_bytes INTEGER NOT NULL,
                        language TEXT NOT NULL,
                        last_commit_at INTEGER
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
                    CREATE TABLE classifications (
                        id INTEGER PRIMARY KEY,
                        text TEXT,
                        mode TEXT,
                        created_at TEXT
                    );
                    INSERT INTO files (path, content_hash, size_bytes, language, last_commit_at)
                    VALUES ('src/auth/login.py', 'abc', 30, 'python', NULL);
                    INSERT INTO symbols (file_path, name, kind, line, end_line)
                    VALUES ('src/auth/login.py', 'login_handler', 'function', 1, 2);
                    INSERT INTO facts (kind, text, created_at)
                    VALUES ('goal', 'Add rate limiting', '2026-05-25T12:00:00Z');
                    INSERT INTO episodes (summary, touched_files, created_at)
                    VALUES ('Added login form', '["src/auth/login.py"]', '2026-05-25T12:00:00Z');
                    """
                )

            recipe = get_recipe("bugfix")
            ctx = compile_context(
                target=target,
                task_description="Fix login handler bug",
                mode="bugfix",
                database_path=database_path,
                recipe=recipe,
            )

            self.assertEqual(ctx.task_description, "Fix login handler bug")
            self.assertEqual(ctx.mode, "bugfix")
            self.assertEqual(ctx.total_budget, 6000)
            self.assertGreater(len(ctx.sections), 0)
            section_names = [s.name for s in ctx.sections]
            self.assertIn("files", section_names)
            self.assertIn("facts", section_names)
            self.assertGreater(len(ctx.facts), 0)
            self.assertGreater(len(ctx.episodes), 0)

    def test_compile_context_includes_agentic_context_lane(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir)
            state_dir = target / ".ccw"
            snapshots_dir = state_dir / "snapshots"
            snapshots_dir.mkdir(parents=True, exist_ok=True)
            (state_dir / "compiled").mkdir(parents=True, exist_ok=True)
            write_text(state_dir / "config.yaml", "config_version: 1\n")
            database_path = state_dir / "index.sqlite"

            write_text(target / "src" / "auth" / "login.py", "def login_handler(user):\n    pass\n")
            write_text(target / "AGENTS.md", "# repo instructions\n")

            with sqlite3.connect(database_path) as connection:
                connection.executescript(
                    """
                    CREATE TABLE files (
                        id INTEGER PRIMARY KEY,
                        path TEXT NOT NULL UNIQUE,
                        content_hash TEXT NOT NULL,
                        size_bytes INTEGER NOT NULL,
                        language TEXT NOT NULL,
                        last_commit_at INTEGER
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
                    CREATE TABLE classifications (
                        id INTEGER PRIMARY KEY,
                        text TEXT,
                        mode TEXT,
                        created_at TEXT
                    );
                    INSERT INTO files (path, content_hash, size_bytes, language, last_commit_at)
                    VALUES
                        ('src/auth/login.py', 'a', 30, 'python', NULL),
                        ('AGENTS.md', 'b', 25, 'markdown', NULL);
                    INSERT INTO symbols (file_path, name, kind, line, end_line)
                    VALUES ('src/auth/login.py', 'login_handler', 'function', 1, 2);
                    """
                )

            recipe = get_recipe("bugfix")
            ctx = compile_context(
                target=target,
                task_description="Fix login handler bug",
                mode="bugfix",
                database_path=database_path,
                recipe=recipe,
            )

            sections = {section.name: section for section in ctx.sections}
            self.assertIn("files", sections)
            self.assertIn("agentic context", sections)
            self.assertEqual(
                sections["files"].items[0].file_path,
                "src/auth/login.py",
            )
            self.assertEqual(
                sections["agentic context"].items[0].file_path,
                "AGENTS.md",
            )


class RenderCompiledContextTests(unittest.TestCase):
    def test_render_includes_frontmatter(self) -> None:
        ctx = CompiledContext(
            task_description="Fix bug",
            mode="bugfix",
            total_budget=6000,
            index_hash="abc123",
            sections=(),
            facts=(),
            episodes=(),
            constraints=(),
            created_at="2026-05-25T12:00:00Z",
        )
        output = render_compiled_context(ctx)
        self.assertIn("---", output)
        self.assertIn("mode: bugfix", output)
        self.assertIn("budget: 6000", output)
        self.assertIn("index_hash: abc123", output)
        self.assertIn("created_at: 2026-05-25T12:00:00Z", output)

    def test_render_includes_task_section(self) -> None:
        ctx = CompiledContext(
            task_description="Fix login bug",
            mode="bugfix",
            total_budget=6000,
            index_hash="abc",
            sections=(),
            facts=(),
            episodes=(),
            constraints=(),
            created_at="2026-05-25T12:00:00Z",
        )
        output = render_compiled_context(ctx)
        self.assertIn("## Task", output)
        self.assertIn("Fix login bug", output)
        self.assertIn("bugfix", output)

    def test_render_includes_estimated_tokens_footer(self) -> None:
        fact_text = "test constraint goal"
        ctx = CompiledContext(
            task_description="Fix bug",
            mode="bugfix",
            total_budget=6000,
            index_hash="abc",
            sections=(
                ContextSection(
                    name="facts",
                    items=(fact_text,),
                    allocated_budget=1500,
                    used_budget=50,
                ),
            ),
            facts=(fact_text,),
            episodes=(),
            constraints=(),
            created_at="2026-05-25T12:00:00Z",
        )
        output = render_compiled_context(ctx)
        self.assertIn("Estimated tokens:", output)
        self.assertIn("/ 6000 allocated", output)

    def test_render_includes_files_with_snippets(self) -> None:
        snippet = Snippet(file_path="src/file.py", start_line=1, end_line=3, text="def f():\n    pass\n")
        rf = RankedFile(file_path="src/file.py", score=8.0, language="python", snippets=(snippet,))
        ctx = CompiledContext(
            task_description="Fix bug",
            mode="bugfix",
            total_budget=6000,
            index_hash="abc",
            sections=(
                ContextSection(
                    name="files",
                    items=(rf,),
                    allocated_budget=1500,
                    used_budget=50,
                ),
            ),
            facts=(),
            episodes=(),
            constraints=(),
            created_at="2026-05-25T12:00:00Z",
        )
        output = render_compiled_context(ctx)
        self.assertIn("src/file.py", output)
        self.assertIn("score: 8.0", output)
        self.assertIn("python", output)
        self.assertIn("def f()", output)


class PerformanceGuardTests(unittest.TestCase):
    def test_compile_context_under_half_second_on_small_repo(self) -> None:
        import time
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir)
            state_dir = target / ".ccw"
            state_dir.mkdir(parents=True, exist_ok=True)
            (state_dir / "compiled").mkdir(parents=True, exist_ok=True)
            (state_dir / "snapshots").mkdir(parents=True, exist_ok=True)
            write_text(state_dir / "config.yaml", "config_version: 1\n")
            database_path = state_dir / "index.sqlite"

            # Create 200 file records and corresponding files
            with sqlite3.connect(database_path) as connection:
                connection.executescript(
                    """
                    CREATE TABLE files (
                        id INTEGER PRIMARY KEY,
                        path TEXT NOT NULL UNIQUE,
                        content_hash TEXT NOT NULL,
                        size_bytes INTEGER NOT NULL,
                        language TEXT NOT NULL,
                        last_commit_at INTEGER
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
                    CREATE TABLE classifications (
                        id INTEGER PRIMARY KEY,
                        text TEXT,
                        mode TEXT,
                        created_at TEXT
                    );
                    """
                )
                for i in range(200):
                    fpath = f"src/module{i // 20}/file{i}.py"
                    connection.execute(
                        "INSERT INTO files (path, content_hash, size_bytes, language, last_commit_at) VALUES (?, ?, ?, ?, ?)",
                        (fpath, "abc", 100, "python", None),
                    )
                    write_text(target / fpath, f"def func{i}():\n    pass\n")
            from ccw.recipe import get_recipe
            recipe = get_recipe("implementation")

            start = time.monotonic()
            ctx = compile_context(
                target=target,
                task_description="Fix the login handler bug",
                mode="bugfix",
                database_path=database_path,
                recipe=recipe,
            )
            elapsed = time.monotonic() - start

            self.assertLess(elapsed, 0.5, f"compile_context took {elapsed:.3f}s (limit 0.5s)")
            self.assertGreater(len(ctx.sections), 0)


if __name__ == "__main__":
    unittest.main()
