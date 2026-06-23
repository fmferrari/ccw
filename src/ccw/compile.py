from __future__ import annotations

import re
import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path

from ccw.recipe import Recipe


_STOPWORDS = frozenset({
    "the", "a", "an", "is", "it", "to", "for", "of", "in", "on",
    "and", "or", "at", "by", "with", "from", "as", "be", "this", "that",
})

_AGENTIC_CONTEXT_EXACT_SCORES = {
    "AGENTS.md": 120.0,
    "CONTEXT.md": 110.0,
    "CLAUDE.md": 95.0,
    "GEMINI.md": 95.0,
    "CODEX.md": 95.0,
    "COPILOT_INSTRUCTIONS.md": 95.0,
    "wiki/AGENTS.md": 120.0,
    "wiki/user/index.md": 105.0,
    "wiki/user/log.md": 105.0,
    "wiki/index.md": 85.0,
    "wiki/log.md": 85.0,
    ".github/copilot-instructions.md": 95.0,
    ".github/copilot-instructions.instructions.md": 95.0,
    ".mcp.json": 45.0,
    "mcp.json": 45.0,
    "opencode.json": 55.0,
    "apm.yml": 45.0,
}

_AGENTIC_CONTEXT_BASENAME_SCORES = {
    "AGENTS.md": 100.0,
    "UBIQUITOUS_LANGUAGE.md": 70.0,
    "CLAUDE.md": 90.0,
    "GEMINI.md": 90.0,
    "CODEX.md": 90.0,
    "COPILOT_INSTRUCTIONS.md": 90.0,
    "COPILOT_INSTRUCTIONS.instructions": 90.0,
    "copilot-instructions.md": 90.0,
    "copilot-instructions.instructions.md": 90.0,
    ".cursorrules": 80.0,
    ".mcp.json": 45.0,
    "mcp.json": 45.0,
    "mcp.yml": 45.0,
    "mcp.yaml": 45.0,
    "opencode.json": 55.0,
    "apm.yml": 45.0,
    "apm.yaml": 45.0,
}

_AGENTIC_CONTEXT_PATH_SEGMENTS = (
    ".cursor/rules/",
    ".cursor/instructions/",
    ".opencode/instructions/",
    ".github/instructions/",
    ".github/prompts/",
    ".github/copilot-instructions",
    ".claude/",
    ".gemini/",
    ".codex/",
)

_AGENTIC_CONTEXT_EXCLUDED_PREFIXES = (
    "apm_modules/",
    "vendor/",
    "third_party/",
    "external/",
    "site-packages/",
    "node_modules/",
)

_AGENTIC_CONTEXT_EXCLUDED_SEGMENTS = frozenset({
    "apm_modules",
    "vendor",
    "third_party",
    "external",
    "site-packages",
    "node_modules",
})

_AGENTIC_CONTEXT_HINT_DOC_EXTENSIONS = frozenset({
    "md",
    "mdx",
    "txt",
    "rst",
    "adoc",
})

_AGENTIC_CONTEXT_BASENAME_HINT_TOKENS = (
    "ubiquitous-language",
    "ubiquitous_language",
    "language",
    "vocabulary",
    "glossary",
    "terminology",
    "lexicon",
)

_AGENTIC_ANCHOR_BASENAMES = frozenset({
    "agents.md",
    "context.md",
})

_AGENTIC_ANCHOR_STRUCTURE_BASENAMES = frozenset({
    "index.md",
    "log.md",
    "changelog.md",
    "history.md",
})

_AGENTIC_ANCHOR_KNOWLEDGE_ROOT_SEGMENTS = frozenset({
    "wiki",
    "docs",
    "doc",
    "knowledge",
    "notes",
    "handbook",
    "playbook",
})

_TASK_IMPLEMENT_HINT_TOKENS = frozenset({
    "build",
    "feature",
    "fix",
    "implement",
    "improve",
    "optimize",
    "refactor",
})

_TASK_TEST_HINT_TOKENS = frozenset({
    "assert",
    "benchmark",
    "coverage",
    "e2e",
    "integration",
    "regression",
    "spec",
    "test",
    "tests",
    "unittest",
    "validate",
    "verification",
})

_TASK_DOC_HINT_TOKENS = frozenset({
    "architecture",
    "changelog",
    "comment",
    "comments",
    "context",
    "design",
    "doc",
    "docs",
    "document",
    "documentation",
    "explain",
    "guide",
    "manual",
    "note",
    "notes",
    "readme",
    "spec",
    "specification",
    "troubleshooting",
    "tutorial",
    "wiki",
})

_TASK_DOC_INTENT_PRIMARY_TOKENS = frozenset({
    "doc",
    "docs",
    "document",
    "documentation",
    "explain",
    "guide",
    "note",
    "notes",
    "readme",
    "spec",
    "specification",
    "troubleshooting",
})

_TASK_DOC_INTENT_SECONDARY_TOKENS = frozenset({
    "behavior",
    "behaviour",
    "note",
    "notes",
})

_TASK_SOURCE_PATH_SEGMENTS = frozenset({
    "app",
    "backend",
    "client",
    "cmd",
    "core",
    "frontend",
    "internal",
    "lib",
    "pkg",
    "scripts",
    "server",
    "service",
    "services",
    "src",
})

_TASK_TEST_PATH_SEGMENTS = frozenset({
    "test",
    "tests",
    "__tests__",
    "e2e",
})

_TASK_TEST_CODE_HINT_PATH_SEGMENTS = frozenset({
    "spec",
    "specs",
})

_TASK_DOC_PATH_SEGMENTS = frozenset({
    "doc",
    "docs",
    "wiki",
    "knowledge",
    "notes",
    "architecture",
    "design",
    "adr",
    "runbook",
    "playbook",
    "guide",
    "guides",
    "spec",
    "specs",
})

_TASK_DOC_PRIORITY_PATH_SEGMENTS = frozenset({
    "architecture",
    "design",
    "adr",
    "runbook",
    "playbook",
    "handbook",
    "guide",
    "guides",
    "spec",
    "specs",
})

_TASK_CODE_EXTENSIONS = frozenset({
    "c",
    "cc",
    "cpp",
    "cs",
    "go",
    "h",
    "hpp",
    "java",
    "js",
    "jsx",
    "kt",
    "m",
    "php",
    "py",
    "rb",
    "rs",
    "scala",
    "sh",
    "swift",
    "ts",
    "tsx",
})

_TASK_DOC_EXTENSIONS = _AGENTIC_CONTEXT_HINT_DOC_EXTENSIONS | frozenset({
    "mdown",
})

_TASK_DOC_CANDIDATE_EXCLUDED_BASENAMES = frozenset({
    "agents.md",
    "context.md",
    "claude.md",
    "gemini.md",
    "codex.md",
    "copilot_instructions.md",
    "copilot-instructions.md",
    "copilot-instructions.instructions.md",
    ".mcp.json",
    "mcp.json",
    "mcp.yml",
    "mcp.yaml",
    "apm.yml",
    "apm.yaml",
})

_TASK_DOC_CANDIDATE_EXCLUDED_SEGMENTS = frozenset({
    ".claude",
    ".codex",
    ".cursor",
    ".gemini",
    ".github",
    ".opencode",
})

_TASK_DOC_FILENAME_HINT_TOKENS = frozenset({
    "architecture",
    "behavior",
    "behaviour",
    "changelog",
    "guide",
    "manual",
    "note",
    "notes",
    "readme",
    "spec",
    "specification",
    "troubleshooting",
})


@dataclass(frozen=True)
class Snippet:
    file_path: str
    start_line: int
    end_line: int
    text: str


@dataclass(frozen=True)
class RankedFile:
    file_path: str
    score: float
    language: str
    snippets: tuple[Snippet, ...] = ()


@dataclass(frozen=True)
class ContextSection:
    name: str
    items: tuple[RankedFile | str, ...] = ()
    allocated_budget: int = 0
    used_budget: int = 0


@dataclass(frozen=True)
class CompiledContext:
    task_description: str
    mode: str
    total_budget: int
    index_hash: str
    sections: tuple[ContextSection, ...] = ()
    facts: tuple[str, ...] = ()
    episodes: tuple[str, ...] = ()
    constraints: tuple[str, ...] = ()
    created_at: str = ""


def _estimate_tokens(text: str) -> int:
    return len(text) // 4


def _tokenize(text: str) -> list[str]:
    tokens = re.findall(r"[a-zA-Z_][a-zA-Z0-9_]*", text.lower())
    return [t for t in tokens if t not in _STOPWORDS]


def _path_tokens(path: str) -> list[str]:
    return re.findall(r"[a-zA-Z_][a-zA-Z0-9_]*", path)


def _fuzzy_prefix_match(token: str, component: str) -> bool:
    return component.startswith(token)


def _base_score(path: str, tokens: list[str]) -> int:
    score = 0
    components = _path_tokens(path)
    for token in tokens:
        for comp in components:
            if token == comp or _fuzzy_prefix_match(token, comp):
                score += 3
                break
    return score


def _normalize_path(path: str) -> str:
    normalized = path.replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized


def _path_segments(path: str) -> list[str]:
    return [segment.lower() for segment in _normalize_path(path).split("/") if segment]


def _is_third_party_path(path: str) -> bool:
    normalized = _normalize_path(path)
    if normalized.startswith(_AGENTIC_CONTEXT_EXCLUDED_PREFIXES):
        return True

    segments = _path_segments(normalized)[:-1]
    return any(segment in _AGENTIC_CONTEXT_EXCLUDED_SEGMENTS for segment in segments)


def _is_excluded_agentic_path(path: str) -> bool:
    return _is_third_party_path(path)


def _is_agentic_anchor_path(path: str) -> bool:
    normalized = _normalize_path(path)
    segments = _path_segments(normalized)
    if not segments:
        return False

    basename = segments[-1]
    if basename in _AGENTIC_ANCHOR_BASENAMES:
        return True

    if basename in _AGENTIC_ANCHOR_STRUCTURE_BASENAMES:
        parent_segments = segments[:-1]
        return any(
            segment in _AGENTIC_ANCHOR_KNOWLEDGE_ROOT_SEGMENTS
            for segment in parent_segments
        )

    return False


def _agentic_context_score(path: str) -> float:
    normalized = _normalize_path(path)
    if _is_excluded_agentic_path(normalized):
        return 0.0

    basename = normalized.rsplit("/", 1)[-1]
    lowered_basename = basename.lower()
    score = _AGENTIC_CONTEXT_EXACT_SCORES.get(normalized, 0.0)
    score = max(score, _AGENTIC_CONTEXT_BASENAME_SCORES.get(basename, 0.0))

    stem, dot, extension = lowered_basename.rpartition(".")
    if dot and extension in _AGENTIC_CONTEXT_HINT_DOC_EXTENSIONS:
        if any(token in stem for token in _AGENTIC_CONTEXT_BASENAME_HINT_TOKENS):
            score = max(score, 65.0)

    for segment in _AGENTIC_CONTEXT_PATH_SEGMENTS:
        if segment in normalized:
            score = max(score, 75.0)
            break

    if normalized.endswith("/AGENTS.md"):
        score = max(score, 85.0)

    if _is_agentic_anchor_path(normalized):
        score = max(score, 92.0)

    return score


def _default_snippet_range(file_path: str, line_count: int) -> tuple[int, int]:
    normalized = _normalize_path(file_path)
    if normalized in {"wiki/log.md", "wiki/user/log.md"} or normalized.endswith("/wiki/user/log.md"):
        start = max(1, line_count - 39)
        return (start, line_count)
    return (1, min(40, line_count))


def _score_task_file(
    file_path: str,
    tokens: list[str],
    file_symbols: list[str],
    last_commit_at: int | None,
    now_ts: int,
    docs_intent: bool,
) -> float:
    score = float(_base_score(file_path, tokens))
    score += _score_task_role(file_path=file_path, tokens=tokens)
    score += _documentation_intent_file_boost(file_path=file_path, docs_intent=docs_intent)
    for symbol_name in file_symbols:
        for token in tokens:
            if token in symbol_name.lower():
                score += 2.0
                break

    if last_commit_at is not None:
        age = now_ts - last_commit_at
        if age <= 7 * 86400:
            score += 5.0
        elif age <= 30 * 86400:
            score += 2.0

    return score


def _score_task_role(file_path: str, tokens: list[str]) -> float:
    normalized = _normalize_path(file_path)
    segments = _path_segments(normalized)
    if not segments:
        return 0.0

    basename = segments[-1]
    stem, dot, extension = basename.rpartition(".")
    extension = extension.lower() if dot else ""
    token_set = set(tokens)

    asks_for_tests = bool(token_set & _TASK_TEST_HINT_TOKENS)
    asks_for_docs = bool(token_set & _TASK_DOC_HINT_TOKENS)
    asks_for_implementation = bool(token_set & _TASK_IMPLEMENT_HINT_TOKENS)
    if not asks_for_tests and not asks_for_docs and not asks_for_implementation:
        asks_for_implementation = True

    parent_segments = segments[:-1]
    in_source_tree = any(segment in _TASK_SOURCE_PATH_SEGMENTS for segment in parent_segments)
    in_test_tree = any(segment in _TASK_TEST_PATH_SEGMENTS for segment in parent_segments)
    in_test_code_hint_tree = any(
        segment in _TASK_TEST_CODE_HINT_PATH_SEGMENTS
        for segment in parent_segments
    )
    in_doc_tree = any(segment in _TASK_DOC_PATH_SEGMENTS for segment in parent_segments)
    is_doc_extension = extension in _TASK_DOC_EXTENSIONS
    looks_like_test_file = (
        (in_test_tree and not is_doc_extension)
        or (in_test_code_hint_tree and extension in _TASK_CODE_EXTENSIONS)
        or basename.startswith("test_")
        or basename.endswith("_test.py")
        or basename.endswith(".test.ts")
        or basename.endswith(".test.tsx")
        or basename.endswith(".test.js")
        or basename.endswith(".spec.ts")
        or basename.endswith(".spec.tsx")
        or basename.endswith(".spec.js")
    )
    is_doc_file = is_doc_extension or in_doc_tree
    is_code_file = extension in _TASK_CODE_EXTENSIONS

    score = 0.0
    if in_source_tree:
        score += 3.0 if asks_for_implementation else 1.5
    if is_code_file:
        score += 2.0 if asks_for_implementation else 1.0
    if looks_like_test_file:
        score += 3.0 if asks_for_tests else -2.0
    if is_doc_file:
        score += 2.5 if asks_for_docs else -1.5
    if in_doc_tree and asks_for_implementation:
        score -= 1.0

    if stem and stem in {"index", "log", "changelog"} and asks_for_docs:
        score += 1.5

    return score


def _has_documentation_intent(tokens: list[str]) -> bool:
    token_set = set(tokens)
    if token_set & _TASK_DOC_INTENT_PRIMARY_TOKENS:
        return True
    has_behavior = bool(token_set & {"behavior", "behaviour"})
    has_notes = bool(token_set & (_TASK_DOC_INTENT_SECONDARY_TOKENS - {"behavior", "behaviour"}))
    return has_behavior and has_notes


def _is_task_documentation_candidate(file_path: str) -> bool:
    normalized = _normalize_path(file_path)
    segments = _path_segments(normalized)
    if not segments:
        return False

    basename = segments[-1].lower()
    if basename in _TASK_DOC_CANDIDATE_EXCLUDED_BASENAMES:
        return False

    parent_segments = segments[:-1]
    if any(segment in _TASK_DOC_CANDIDATE_EXCLUDED_SEGMENTS for segment in parent_segments):
        return False

    stem, dot, extension = basename.rpartition(".")
    extension = extension.lower() if dot else ""

    in_doc_tree = any(segment in _TASK_DOC_PATH_SEGMENTS for segment in parent_segments)
    has_spec_name = "spec" in stem or "specification" in stem
    has_doc_name_hint = any(token in stem for token in _TASK_DOC_FILENAME_HINT_TOKENS)
    return (
        extension in _TASK_DOC_EXTENSIONS
        or in_doc_tree
        or has_spec_name
        or has_doc_name_hint
    )


def _documentation_intent_file_boost(file_path: str, docs_intent: bool) -> float:
    if not docs_intent:
        return 0.0
    if _is_task_documentation_candidate(file_path):
        parent_segments = _path_segments(_normalize_path(file_path))[:-1]
        boost = 8.0
        if any(segment in _TASK_DOC_PRIORITY_PATH_SEGMENTS for segment in parent_segments):
            boost += 4.0
        return boost
    return 0.0


def _agentic_lane_item_limit(max_items: int) -> int:
    if max_items <= 3:
        return 0
    return max(1, min(6, max_items // 5))


def split_file_lane_budget(total_file_budget: int) -> tuple[int, int]:
    if total_file_budget <= 0:
        return (0, 0)

    if total_file_budget < 400:
        agentic_budget = max(40, total_file_budget // 5)
    else:
        agentic_budget = max(120, total_file_budget // 5)

    agentic_budget = min(800, agentic_budget)
    if agentic_budget >= total_file_budget:
        agentic_budget = max(0, total_file_budget - 1)

    task_budget = total_file_budget - agentic_budget
    return (task_budget, agentic_budget)


def rank_file_lanes(
    target: Path,
    task_description: str,
    database_path: Path,
    max_items: int = 20,
    max_agentic_items: int | None = None,
) -> tuple[list[RankedFile], list[RankedFile]]:
    tokens = _tokenize(task_description)
    if not tokens or max_items <= 0:
        return ([], [])
    docs_intent = _has_documentation_intent(tokens)

    try:
        connection = sqlite3.connect(database_path)
        try:
            rows = connection.execute(
                "SELECT path, language, last_commit_at FROM files ORDER BY path"
            ).fetchall()
        finally:
            connection.close()
    except sqlite3.Error:
        return ([], [])

    symbol_names: dict[str, list[str]] = {}
    try:
        connection = sqlite3.connect(database_path)
        try:
            symbol_rows = connection.execute(
                "SELECT DISTINCT file_path, name FROM symbols"
            ).fetchall()
            for file_path, name in symbol_rows:
                symbol_names.setdefault(file_path, []).append(name)
        finally:
            connection.close()
    except sqlite3.Error:
        pass

    uses_default_agentic_limit = max_agentic_items is None
    if uses_default_agentic_limit:
        max_agentic_items = _agentic_lane_item_limit(max_items)
    max_agentic_items = max(0, min(max_agentic_items, max_items))
    max_task_items = max(0, max_items - max_agentic_items)

    now_ts = int(time.time())

    task_scored: list[tuple[float, str, str]] = []
    third_party_task_scored: list[tuple[float, str, str]] = []
    agentic_anchor_scored: list[tuple[float, str, str]] = []
    agentic_scored: list[tuple[float, str, str]] = []
    for file_path, language, last_commit_at in rows:
        normalized_path = _normalize_path(file_path)
        prioritize_in_task_lane = docs_intent and _is_task_documentation_candidate(normalized_path)
        agentic_score = _agentic_context_score(file_path)
        if agentic_score > 0 and max_agentic_items > 0 and not prioritize_in_task_lane:
            if _is_agentic_anchor_path(normalized_path):
                agentic_anchor_scored.append((agentic_score, file_path, language))
            else:
                agentic_scored.append((agentic_score, file_path, language))
            continue

        if max_task_items == 0:
            continue

        score = _score_task_file(
            file_path=file_path,
            tokens=tokens,
            file_symbols=symbol_names.get(file_path, []),
            last_commit_at=last_commit_at,
            now_ts=now_ts,
            docs_intent=docs_intent,
        )
        if _is_third_party_path(normalized_path):
            third_party_task_scored.append((score, file_path, language))
        else:
            task_scored.append((score, file_path, language))

    task_scored.sort(key=lambda x: (-x[0], x[1]))
    third_party_task_scored.sort(key=lambda x: (-x[0], x[1]))
    agentic_anchor_scored.sort(key=lambda x: (-x[0], x[1]))
    agentic_scored.sort(key=lambda x: (-x[0], x[1]))

    # Anchors (repo contract/context files) should not be evicted by the small
    # default agentic slot heuristic. Grow the agentic lane to fit anchors, but
    # only into spare capacity so the task lane is never starved on tight budgets.
    if uses_default_agentic_limit:
        anchor_count = len(agentic_anchor_scored)
        anchor_cap = min(anchor_count, max(max_agentic_items, max_items // 2))
        if anchor_cap > max_agentic_items:
            max_agentic_items = anchor_cap
            max_task_items = max(0, max_items - max_agentic_items)

    ordered_task_scored = [*task_scored, *third_party_task_scored]
    ordered_agentic_scored = [*agentic_anchor_scored, *agentic_scored]

    ranked_task_files = [
        RankedFile(file_path=fp, score=sc, language=lang)
        for sc, fp, lang in ordered_task_scored[:max_task_items]
    ]
    ranked_agentic_files = [
        RankedFile(file_path=fp, score=sc, language=lang)
        for sc, fp, lang in ordered_agentic_scored[:max_agentic_items]
    ]

    if uses_default_agentic_limit:
        remaining_slots = max_items - len(ranked_task_files) - len(ranked_agentic_files)
        if remaining_slots > 0:
            overflow_task = ordered_task_scored[len(ranked_task_files) :]
            extra_task = overflow_task[:remaining_slots]
            ranked_task_files.extend(
                RankedFile(file_path=fp, score=sc, language=lang)
                for sc, fp, lang in extra_task
            )
            remaining_slots -= len(extra_task)

        if remaining_slots > 0:
            overflow_agentic = ordered_agentic_scored[len(ranked_agentic_files) :]
            extra_agentic = overflow_agentic[:remaining_slots]
            ranked_agentic_files.extend(
                RankedFile(file_path=fp, score=sc, language=lang)
                for sc, fp, lang in extra_agentic
            )
    return (ranked_task_files, ranked_agentic_files)


def rank_files(
    target: Path,
    task_description: str,
    database_path: Path,
    max_items: int = 20,
) -> list[RankedFile]:
    task_files, agentic_files = rank_file_lanes(
        target=target,
        task_description=task_description,
        database_path=database_path,
        max_items=max_items,
    )

    return [*task_files, *agentic_files][:max_items]


def _load_symbol_ranges(
    database_path: Path,
) -> dict[str, list[tuple[int, int, str]]]:
    ranges: dict[str, list[tuple[int, int, str]]] = {}
    try:
        with sqlite3.connect(database_path) as connection:
            rows = connection.execute(
                "SELECT file_path, line, end_line, name FROM symbols ORDER BY line"
            ).fetchall()
            for file_path, line, end_line, name in rows:
                ranges.setdefault(file_path, []).append((line, end_line, name))
    except sqlite3.Error:
        pass
    return ranges


def extract_snippets(
    target: Path,
    ranked_files: list[RankedFile],
    task_description: str,
    database_path: Path,
    budget: int,
) -> list[RankedFile]:
    tokens = _tokenize(task_description)
    symbol_ranges = _load_symbol_ranges(database_path)
    remaining_budget = budget

    result: list[RankedFile] = []
    for rf in ranked_files:
        file_path = target / rf.file_path
        if not file_path.is_file():
            result.append(rf)
            continue

        try:
            lines = file_path.read_text(encoding="utf-8").splitlines(keepends=True)
        except (OSError, UnicodeDecodeError):
            result.append(rf)
            continue

        file_symbols = symbol_ranges.get(rf.file_path, [])

        # Find best matching symbol for the task
        best_range: tuple[int, int] | None = None
        if tokens and file_symbols:
            for s_line, s_end, s_name in file_symbols:
                for token in tokens:
                    if token in s_name.lower():
                        start = max(1, s_line - 5)
                        end = min(len(lines), s_end + 5)
                        best_range = (start, end)
                        break
                if best_range is not None:
                    break

        if best_range is None:
            best_range = _default_snippet_range(rf.file_path, len(lines))

        start_line, end_line = best_range
        snippet_lines = lines[start_line - 1 : end_line]
        snippet_text = "".join(snippet_lines)
        estimated = _estimate_tokens(snippet_text)

        if remaining_budget <= 0:
            # Budget exhausted: keep the file reference but drop the snippet body
            # so later files never push the artifact over its allocation.
            result.append(rf)
            continue

        if estimated > remaining_budget:
            # Truncate: fit what we can
            target_chars = remaining_budget * 4
            snippet_text = snippet_text[:target_chars]
            end_line = start_line + snippet_text.count("\n")
            estimated = remaining_budget

        remaining_budget -= estimated
        snippet = Snippet(
            file_path=rf.file_path,
            start_line=start_line,
            end_line=end_line,
            text=snippet_text,
        )
        result.append(
            RankedFile(
                file_path=rf.file_path,
                score=rf.score,
                language=rf.language,
                snippets=(snippet,),
            )
        )

    return result


def render_compiled_context(ctx: CompiledContext) -> str:
    lines: list[str] = []

    # YAML frontmatter
    lines.append("---")
    lines.append(f"mode: {ctx.mode}")
    lines.append(f"budget: {ctx.total_budget}")
    lines.append(f"index_hash: {ctx.index_hash}")
    lines.append(f"created_at: {ctx.created_at}")
    lines.append("---")
    lines.append("")

    # Title
    lines.append("# Compiled context")
    lines.append("")

    # Task section
    lines.append("## Task")
    lines.append("")
    lines.append(f"**Mode:** {ctx.mode}")
    lines.append(f"**Description:** {ctx.task_description}")
    lines.append(f"**Budget:** {ctx.total_budget} tokens")
    lines.append("")

    total_used = 0

    # Sections
    for section in ctx.sections:
        lines.append(f"## {section.name.title()}")
        lines.append("")

        section_used = 0

        for item in section.items:
            if isinstance(item, RankedFile):
                lines.append(f"- `{item.file_path}` (score: {item.score})")
                for snippet in item.snippets:
                    if snippet.text:
                        lines.append(f"  ```{item.language}")
                        if snippet.start_line > 0:
                            lines.append(f"  lines {snippet.start_line}-{snippet.end_line}:")
                        for sl in snippet.text.splitlines():
                            lines.append(f"  {sl}")
                        lines.append("  ```")
                lines.append("")
                section_used += sum(len(s.text) // 4 for s in item.snippets)

            elif isinstance(item, str):
                lines.append(f"- {item}")
                lines.append("")
                section_used += len(item) // 4

        total_used += section_used

    # Footer with budget estimate
    lines.append("---")
    lines.append(f"*Estimated tokens: {total_used} / {ctx.total_budget} allocated*")
    lines.append("")

    return "\n".join(lines)


def do_compile(
    target: Path,
    task_description: str,
    output_path: Path | None = None,
    mode: str | None = None,
    budget: int | None = None,
) -> Path:
    from ccw.classify import classify as classify_text
    from ccw.init import require_initialized_local_state, resolve_target_directory
    from ccw.recipe import allocate_budget, get_recipe
    from ccw.schema import bootstrap_index_database

    resolved_target = resolve_target_directory(target, description="Compile target")
    database_path = require_initialized_local_state(resolved_target)
    bootstrap_index_database(database_path)

    if mode is None:
        resolved_mode = classify_text(resolved_target, task_description)
    else:
        resolved_mode = mode.strip().lower()

    recipe = get_recipe(resolved_mode)
    ctx = compile_context(
        target=resolved_target,
        task_description=task_description,
        mode=resolved_mode,
        database_path=database_path,
        recipe=recipe,
        budget=budget,
    )

    rendered = render_compiled_context(ctx)

    if output_path is None:
        output_path = resolved_target / ".ccw" / "compiled" / "latest.md"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(rendered, encoding="utf-8")

    # Persist compilation record
    import datetime
    try:
        created_at = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
        with sqlite3.connect(database_path) as connection:
            connection.execute(
                "INSERT INTO compilations (task, mode, budget, output_path, created_at) VALUES (?, ?, ?, ?, ?)",
                (task_description, resolved_mode, ctx.total_budget, str(output_path), created_at),
            )
    except sqlite3.Error:
        pass  # Non-fatal: compilation output already written

    return output_path


def compute_index_hash(database_path: Path) -> str:
    import hashlib
    try:
        with sqlite3.connect(database_path) as connection:
            rows = connection.execute(
                "SELECT path, content_hash FROM files ORDER BY path"
            ).fetchall()
        combined = "|".join(f"{p}:{h}" for p, h in rows)
        return hashlib.sha256(combined.encode()).hexdigest()[:12]
    except (sqlite3.Error, OSError):
        return ""


def _load_facts(database_path: Path) -> list[str]:
    try:
        with sqlite3.connect(database_path) as connection:
            rows = connection.execute(
                "SELECT kind, text FROM facts ORDER BY id"
            ).fetchall()
        return [f"{kind}: {text}" for kind, text in rows if kind and text]
    except sqlite3.Error:
        return []


def _load_episodes(database_path: Path) -> list[str]:
    try:
        with sqlite3.connect(database_path) as connection:
            rows = connection.execute(
                "SELECT summary, created_at FROM episodes ORDER BY id DESC LIMIT 5"
            ).fetchall()
        return [
            f"{created_at}: {summary}" for summary, created_at in rows if summary
        ]
    except sqlite3.Error:
        return []


def _load_constraints(database_path: Path) -> list[str]:
    facts = _load_facts(database_path)
    return [f for f in facts if f.startswith("constraint:")]


def compile_context(
    target: Path,
    task_description: str,
    mode: str,
    database_path: Path,
    recipe: Recipe,
    budget: int | None = None,
) -> CompiledContext:
    from ccw.pipeline import run_pipeline
    return run_pipeline(
        target=target,
        task_description=task_description,
        mode=mode,
        database_path=database_path,
        recipe=recipe,
        budget=budget,
    )
