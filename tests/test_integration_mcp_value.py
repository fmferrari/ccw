"""Integration test that proves the CCW MCP API delivers its core value claim.

The pitch CCW sells: a small-window model gets deterministic, relevant,
grounded, bounded project memory through the MCP tools alone -- with receipts.

This test exercises the public MCP tool surface end to end against a fixture
repository that contains one clearly relevant module surrounded by unrelated
noise, then asserts each individual value claim the API makes:

1. Relevance     - the compiled context surfaces the task-relevant file/symbol.
2. Boundedness   - it selects a small subset instead of dumping the whole repo.
3. Grounding     - it cites only real files (validation passes, no invented paths).
4. Memory        - explicit project facts the raw code does not contain are surfaced.
5. Determinism   - identical inputs produce an identical compiled body.
6. Freshness     - a stale bundle is detected after the index changes.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


from ccw.mcp_server import (  # noqa: E402
    compile_task_context,
    index_repo,
    init_repo,
    prepare_session,
    record_fact,
    update_memory,
    validate_compiled_artifact,
    validate_session,
)


RELEVANT_FILE = "src/auth/login.py"
RELEVANT_SYMBOL = "login_handler"
NOISE_FILE = "src/zzz_unrelated/widget.py"
NOISE_SYMBOL = "widget_render_pass"
CONSTRAINT_TEXT = "Never log plaintext passwords"
TASK = "Fix the login bug that rejects valid credentials"


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def build_fixture_repo(root: Path) -> int:
    """Create one relevant module plus unrelated noise. Returns total source bytes."""
    write_text(
        root / RELEVANT_FILE,
        "def login_handler(username, password):\n"
        "    if not username or not password:\n"
        "        return {'ok': False, 'reason': 'missing credentials'}\n"
        "    return {'ok': True, 'user': username}\n",
    )

    # Enough unrelated noise modules to exceed the recipe file cap (15), so the
    # compiler is forced to drop the lowest-priority module rather than dump all.
    for i in range(20):
        write_text(
            root / f"src/noise/mod_{i:02d}.py",
            f"def compute_value_{i:02d}(seed):\n    return seed * {i + 1}\n" * 6,
        )

    # This module sorts last by path, so it is the one dropped from the cap.
    write_text(
        root / NOISE_FILE,
        f"def {NOISE_SYMBOL}(widget):\n    return widget.upper()\n" * 6,
    )

    total_bytes = sum(
        p.stat().st_size for p in root.rglob("*.py") if ".ccw" not in p.parts
    )
    return total_bytes


def strip_frontmatter(markdown: str) -> str:
    """Remove the leading YAML frontmatter block (carries the only timestamp)."""
    if not markdown.startswith("---\n"):
        return markdown
    end = markdown.find("\n---\n", 4)
    if end == -1:
        return markdown
    return markdown[end + len("\n---\n") :]


class McpApiValueTests(unittest.TestCase):
    def test_mcp_api_delivers_relevant_grounded_bounded_deterministic_memory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "repo"
            target.mkdir()
            total_source_bytes = build_fixture_repo(target)

            # Drive the public MCP API exactly as an agent framework would.
            init_repo(target_path=str(target))
            index_payload = index_repo(target_path=str(target))
            self.assertGreaterEqual(int(index_payload["file_count"]), 7)

            record_fact(
                kind="constraint",
                text=CONSTRAINT_TEXT,
                target_path=str(target),
            )

            bundle_payload = prepare_session(
                task_description=TASK,
                target_path=str(target),
                output_dir=".ccw/session/run-a",
            )
            compiled_path = Path(str(bundle_payload["compiled_artifact"]))
            self.assertTrue(compiled_path.is_file())
            compiled_text = compiled_path.read_text(encoding="utf-8")

            # 1. Relevance: the task-relevant file and symbol are surfaced.
            self.assertIn(RELEVANT_FILE, compiled_text)
            self.assertIn(RELEVANT_SYMBOL, compiled_text)

            # 2. Boundedness: it selects a subset, not the whole repo. The
            #    lowest-priority noise module is excluded, and the artifact is
            #    materially smaller than dumping all source.
            self.assertNotIn(NOISE_SYMBOL, compiled_text)
            self.assertLess(len(compiled_text.encode("utf-8")), total_source_bytes)

            listed_files = [
                line for line in compiled_text.splitlines()
                if line.strip().startswith("- `") and line.strip().endswith("`)")
            ]
            self.assertLess(
                len(listed_files),
                int(index_payload["file_count"]),
                "compiled context should not list every indexed file",
            )

            # 3. Grounding: validation passes -> only real paths, no invented ones.
            validation = validate_compiled_artifact(
                artifact_path=str(compiled_path),
                target_path=str(target),
            )
            self.assertTrue(validation["valid"], validation["errors"])

            # 4. Memory: an explicit fact absent from the raw code is surfaced.
            self.assertNotIn(CONSTRAINT_TEXT, (target / RELEVANT_FILE).read_text())
            self.assertIn(CONSTRAINT_TEXT, compiled_text)

            # 5. Determinism: identical inputs produce an identical compiled body.
            second_compile = compile_task_context(
                task_description=TASK,
                target_path=str(target),
                output_path=".ccw/compiled/run-b.md",
            )
            second_text = Path(str(second_compile["artifact_path"])).read_text(encoding="utf-8")
            self.assertEqual(
                strip_frontmatter(compiled_text),
                strip_frontmatter(second_text),
            )

            # The freshly prepared bundle validates clean while the repo is unchanged.
            fresh = validate_session(
                bundle_dir=".ccw/session/run-a",
                target_path=str(target),
            )
            self.assertTrue(fresh["valid"], fresh["errors"])

            # 6. Freshness: changing the repo invalidates the stale bundle. The
            #    API never lets a model silently trust outdated receipts.
            write_text(
                target / "src/auth/session_store.py",
                "def issue_token(user):\n    return f'token-for-{user}'\n",
            )
            update_memory(
                summary="Add session token issuance to the auth module",
                touched_files=["src/auth/session_store.py"],
                decision="Tokens are issued per authenticated user",
                target_path=str(target),
            )

            stale = validate_session(
                bundle_dir=".ccw/session/run-a",
                target_path=str(target),
            )
            self.assertFalse(stale["valid"])
            self.assertTrue(
                any("index_hash" in error for error in stale["errors"]),
                stale["errors"],
            )


if __name__ == "__main__":
    unittest.main()
