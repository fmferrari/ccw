from __future__ import annotations

import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ccw.pipeline import (
    AssemblePass,
    CompilationIR,
    CompilationPipeline,
    ExtractSnippetsPass,
    LoadMemoryPass,
    RankFilesPass,
    ResolveTaskPass,
    build_pipeline,
    ir_to_compiled_context,
)


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _init_database(database_path: Path) -> None:
    with sqlite3.connect(database_path) as connection:
        connection.executescript("""
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
        """)


class CompilationIRTests(unittest.TestCase):
    def test_ir_default_construction(self) -> None:
        ir = CompilationIR()
        self.assertEqual(ir.task_description, "")
        self.assertEqual(ir.mode, "")
        self.assertIsNone(ir.recipe)
        self.assertEqual(ir.total_budget, 0)
        self.assertEqual(ir.section_budgets, {})
        self.assertEqual(ir.index_hash, "")
        self.assertEqual(ir.ranked_files, [])
        self.assertEqual(ir.facts, [])
        self.assertEqual(ir.episodes, [])
        self.assertEqual(ir.constraints, [])
        self.assertEqual(ir.created_at, "")

    def test_ir_custom_construction(self) -> None:
        ir = CompilationIR(
            task_description="Fix bug",
            mode="bugfix",
            total_budget=6000,
        )
        self.assertEqual(ir.task_description, "Fix bug")
        self.assertEqual(ir.mode, "bugfix")
        self.assertEqual(ir.total_budget, 6000)


class PipelineRunnerTests(unittest.TestCase):
    def test_empty_pipeline_returns_ir_unchanged(self) -> None:
        ir = CompilationIR(task_description="test")
        pipeline = CompilationPipeline([])
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir)
            state_dir = target / ".ccw"
            state_dir.mkdir(parents=True, exist_ok=True)
            database_path = state_dir / "index.sqlite"
            result = pipeline.run(ir, target, database_path)
        self.assertIs(result, ir)
        self.assertEqual(result.task_description, "test")

    def test_pipeline_forwards_ir_through_passes(self) -> None:
        ir = CompilationIR(task_description="test")
        seen: list[str] = []

        class CapturePass:
            def run(self, ir: CompilationIR, target: Path, database_path: Path) -> CompilationIR:
                seen.append(ir.task_description)
                return ir

        pipeline = CompilationPipeline([CapturePass(), CapturePass()])
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir)
            state_dir = target / ".ccw"
            state_dir.mkdir(parents=True, exist_ok=True)
            database_path = state_dir / "index.sqlite"
            pipeline.run(ir, target, database_path)
        self.assertEqual(seen, ["test", "test"])


class PassIntegrationTests(unittest.TestCase):
    def test_resolve_task_pass_without_recipe(self) -> None:
        ir = CompilationIR(
            task_description="Fix the login bug",
            mode="bugfix",
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir)
            state_dir = target / ".ccw"
            state_dir.mkdir(parents=True, exist_ok=True)
            database_path = state_dir / "index.sqlite"
            _init_database(database_path)
            result = ResolveTaskPass().run(ir, target, database_path)
        self.assertIsNotNone(result.recipe)
        self.assertEqual(result.mode, "bugfix")
        self.assertGreater(result.total_budget, 0)
        self.assertIn("files", result.section_budgets)

    def test_resolve_task_pass_with_prepopulated_recipe(self) -> None:
        from ccw.recipe import get_recipe
        recipe = get_recipe("review")
        ir = CompilationIR(
            task_description="Review login",
            mode="review",
            recipe=recipe,
            total_budget=recipe.total_budget,
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir)
            state_dir = target / ".ccw"
            state_dir.mkdir(parents=True, exist_ok=True)
            database_path = state_dir / "index.sqlite"
            _init_database(database_path)
            result = ResolveTaskPass().run(ir, target, database_path)
        self.assertEqual(result.recipe, recipe)
        self.assertEqual(result.mode, "review")
        self.assertIn("files", result.section_budgets)

    def test_rank_files_pass_populates_ranked_files(self) -> None:
        ir = CompilationIR(task_description="Fix login bug")
        from ccw.recipe import get_recipe
        ir.recipe = get_recipe("bugfix")
        from ccw.recipe import allocate_budget
        ir.section_budgets = allocate_budget(ir.recipe, ir.recipe.total_budget)

        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir)
            state_dir = target / ".ccw"
            state_dir.mkdir(parents=True, exist_ok=True)
            write_text(state_dir / "config.yaml", "config_version: 1\n")
            database_path = state_dir / "index.sqlite"
            _init_database(database_path)

            result = RankFilesPass().run(ir, target, database_path)
        self.assertGreater(len(result.ranked_files), 0)
        self.assertEqual(result.ranked_files[0].file_path, "src/auth/login.py")

    def test_extract_snippets_pass_attaches_snippets(self) -> None:
        ir = CompilationIR(task_description="Fix login bug")
        from ccw.recipe import get_recipe
        ir.recipe = get_recipe("bugfix")
        from ccw.recipe import allocate_budget
        ir.section_budgets = allocate_budget(ir.recipe, ir.recipe.total_budget)

        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir)
            state_dir = target / ".ccw"
            state_dir.mkdir(parents=True, exist_ok=True)
            write_text(state_dir / "config.yaml", "config_version: 1\n")
            database_path = state_dir / "index.sqlite"
            _init_database(database_path)
            write_text(
                target / "src" / "auth" / "login.py",
                "import sys\n\ndef login_handler(user, pwd):\n    return authenticate(user, pwd)\n\n",
            )

            ir = RankFilesPass().run(ir, target, database_path)
            result = ExtractSnippetsPass().run(ir, target, database_path)
        self.assertGreater(len(result.ranked_files), 0)
        self.assertGreater(len(result.ranked_files[0].snippets), 0)

    def test_load_memory_pass_populates_facts_episodes(self) -> None:
        ir = CompilationIR()
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir)
            state_dir = target / ".ccw"
            state_dir.mkdir(parents=True, exist_ok=True)
            write_text(state_dir / "config.yaml", "config_version: 1\n")
            database_path = state_dir / "index.sqlite"
            _init_database(database_path)

            result = LoadMemoryPass().run(ir, target, database_path)
        self.assertGreater(len(result.facts), 0)
        self.assertGreater(len(result.episodes), 0)
        self.assertGreater(len(result.index_hash), 0)

    def test_assemble_pass_sets_timestamp(self) -> None:
        ir = CompilationIR()
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir)
            database_path = target / "nonexistent.sqlite"
            result = AssemblePass().run(ir, target, database_path)
        self.assertNotEqual(result.created_at, "")

    def test_full_pipeline_produces_compiled_context(self) -> None:
        from ccw.recipe import get_recipe
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir)
            state_dir = target / ".ccw"
            state_dir.mkdir(parents=True, exist_ok=True)
            write_text(state_dir / "config.yaml", "config_version: 1\n")
            database_path = state_dir / "index.sqlite"
            _init_database(database_path)
            write_text(
                target / "src" / "auth" / "login.py",
                "import sys\n\ndef login_handler(user, pwd):\n    return authenticate(user, pwd)\n\n",
            )

            ir = CompilationIR(
                task_description="Fix login handler bug",
                mode="bugfix",
                recipe=get_recipe("bugfix"),
            )
            pipeline = build_pipeline()
            result = pipeline.run(ir, target, database_path)
            ctx = ir_to_compiled_context(result)

        self.assertEqual(ctx.task_description, "Fix login handler bug")
        self.assertEqual(ctx.mode, "bugfix")
        self.assertEqual(ctx.total_budget, 6000)
        section_names = [s.name for s in ctx.sections]
        self.assertIn("files", section_names)
        self.assertIn("facts", section_names)


class IrToCompiledContextTests(unittest.TestCase):
    def test_converts_ir_to_compiled_context(self) -> None:
        from ccw.compile import CompiledContext
        ir = CompilationIR(
            task_description="Fix bug",
            mode="bugfix",
            total_budget=6000,
            index_hash="abc123",
            facts=["goal: Add rate limiting"],
            episodes=["2026-05-25T12:00:00Z: Added login form"],
            constraints=["constraint: Use HTTPS"],
            created_at="2026-05-25T12:00:00Z",
        )
        ctx = ir_to_compiled_context(ir)
        self.assertIsInstance(ctx, CompiledContext)
        self.assertEqual(ctx.task_description, "Fix bug")
        self.assertEqual(ctx.mode, "bugfix")
        self.assertEqual(len(ctx.sections), 3)
        section_names = [s.name for s in ctx.sections]
        self.assertIn("facts", section_names)
        self.assertIn("episodes", section_names)
        self.assertIn("constraints", section_names)

    def test_empty_ir_produces_minimal_context(self) -> None:
        ir = CompilationIR()
        ctx = ir_to_compiled_context(ir)
        self.assertEqual(ctx.sections, ())
        self.assertEqual(ctx.facts, ())
        self.assertEqual(ctx.episodes, ())


if __name__ == "__main__":
    unittest.main()
