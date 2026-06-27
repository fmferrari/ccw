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

_RANKING_NOISE_PATH_SEGMENTS = frozenset({
    "build",
    "dev-dist",
    "dist",
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

_PINNED_AGENTIC_CONTEXT_PATHS = frozenset({
    "AGENTS.md",
    "CONTEXT.md",
    "wiki/AGENTS.md",
    "wiki/user/index.md",
    "wiki/user/log.md",
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

_TASK_REFACTOR_HINT_TOKENS = frozenset({
    "clarify",
    "cleanup",
    "preserve",
    "preserving",
    "refactor",
    "restructure",
    "simplify",
})

_TASK_KEYWORD_ALIASES: dict[str, frozenset[str]] = {
    "document": frozenset({"doc", "wiki", "spec", "guide"}),
    "documentation": frozenset({"doc", "wiki", "spec", "guide"}),
    "retrieval": frozenset({"lookup", "query", "router", "search"}),
    "search": frozenset({"query", "lookup", "retrieval"}),
    "ranking": frozenset({"order", "ordering", "rank", "score", "sort", "tie"}),
    "rank": frozenset({"rerank", "reranker", "score", "order", "sort", "tie"}),
    "rerank": frozenset({"rank", "ranking", "score", "order", "sort"}),
    "troubleshooting": frozenset({"debug", "diagnostic", "runbook"}),
}

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

_TASK_FRONTEND_PATH_SEGMENTS = frozenset({
    "app",
    "components",
    "frontend",
    "pages",
    "ui",
    "web",
})

_TASK_FRONTEND_HINT_TOKENS = frozenset({
    "component",
    "components",
    "css",
    "frontend",
    "hook",
    "hooks",
    "jsx",
    "page",
    "pages",
    "react",
    "tailwind",
    "tsx",
    "ui",
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

_TASK_CODE_LANGUAGES = frozenset({
    "c",
    "cpp",
    "csharp",
    "go",
    "java",
    "javascript",
    "kotlin",
    "php",
    "python",
    "ruby",
    "rust",
    "scala",
    "shell",
    "swift",
    "typescript",
})

_TASK_DOC_EXTENSIONS = _AGENTIC_CONTEXT_HINT_DOC_EXTENSIONS | frozenset({
    "mdown",
})

_TASK_DOC_CANDIDATE_EXCLUDED_BASENAMES = frozenset({
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
class RankingScore:
    total: float
    features: dict[str, float]


@dataclass(frozen=True)
class DocsAdjacencyEvidence:
    anchor_terms: frozenset[str]
    best_anchor_topical: float


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
    if component.startswith(token):
        return True
    if "_" in component and token in component.split("_"):
        return True
    return False


def _base_score(path: str, tokens: list[str]) -> int:
    score = 0
    components = _path_tokens(path)
    for token in tokens:
        for comp in components:
            if token == comp or _fuzzy_prefix_match(token, comp):
                score += 3
                break
    return score


def _path_term_set(path: str) -> set[str]:
    terms: set[str] = set()
    for component in re.findall(r"[a-zA-Z0-9_]+", _normalize_path(path).lower()):
        terms.add(component)
        for part in component.split("_"):
            if part:
                terms.add(part)
    return terms


def _path_match_feature_scores(path: str, tokens: list[str]) -> tuple[float, float]:
    components = _path_tokens(path)
    lexical = 0.0
    alias = 0.0
    for token in tokens:
        matched_token = False
        for comp in components:
            if token == comp or _fuzzy_prefix_match(token, comp):
                lexical += 3.0
                matched_token = True
                break
        if matched_token:
            continue
        for alias_token in _TASK_KEYWORD_ALIASES.get(token, ()):
            for comp in components:
                if alias_token == comp or _fuzzy_prefix_match(alias_token, comp):
                    alias += 3.0
                    matched_token = True
                    break
            if matched_token:
                break
    return (lexical, alias)


def _term_variants(token: str) -> set[str]:
    variants = {token}
    if token.endswith("ing") and len(token) > 5:
        variants.add(token[:-3])
    if token.endswith("ed") and len(token) > 4:
        variants.add(token[:-2])
    if token.endswith("er") and len(token) > 4:
        variants.add(token[:-2])
    if token.endswith("s") and len(token) > 3:
        variants.add(token[:-1])
    if token == "ranking":
        variants.update({"rank", "rerank", "reranker"})
    if token == "rank":
        variants.update({"ranking", "rerank", "reranker"})
    if token == "retrieval":
        variants.add("retrieve")
    if token == "troubleshooting":
        variants.update({"troubleshoot", "troubleshooter"})
    return {variant for variant in variants if len(variant) > 2}


def _morphological_task_terms(tokens: list[str]) -> set[str]:
    terms: set[str] = set()
    for token in tokens:
        terms.update(_term_variants(token))
    return terms


def _term_matches_symbol(term: str, symbol_name: str) -> bool:
    components = _path_tokens(symbol_name.lower())
    return any(term == component or _fuzzy_prefix_match(term, component) for component in components)


def _expand_task_terms(tokens: list[str]) -> list[str]:
    expanded: list[str] = []
    seen: set[str] = set()
    for token in tokens:
        if token in seen:
            continue
        seen.add(token)
        expanded.append(token)
        for alias in _TASK_KEYWORD_ALIASES.get(token, ()):
            if alias in seen:
                continue
            seen.add(alias)
            expanded.append(alias)
    return expanded


def _load_artifact_search_text(database_path: Path) -> dict[str, str]:
    try:
        with sqlite3.connect(database_path) as connection:
            rows = connection.execute(
                "SELECT file_path, title, search_text FROM artifacts"
            ).fetchall()
    except sqlite3.Error:
        return {}

    text_by_path: dict[str, str] = {}
    for file_path, title, search_text in rows:
        text_by_path[file_path] = f"{title or ''} {search_text or ''}".strip()
    return text_by_path


def _normalize_task_mode(task_mode: str | None) -> str:
    if task_mode is None:
        return ""
    return task_mode.strip().lower()


def _infer_preferred_task_language(
    rows: list[tuple[str, str, int | None]],
    tokens: list[str],
    symbol_names: dict[str, list[str]],
    docs_intent: bool,
) -> str:
    if docs_intent:
        return ""

    token_set = set(tokens)
    asks_for_frontend = bool(token_set & _TASK_FRONTEND_HINT_TOKENS)
    search_terms = _expand_task_terms(tokens)
    signal_by_language: dict[str, float] = {}
    for file_path, language, _ in rows:
        normalized_path = _normalize_path(file_path)
        parent_segments = _path_segments(normalized_path)[:-1]
        if _is_third_party_path(normalized_path) or _is_ranking_noise_path(normalized_path):
            continue
        if language not in _TASK_CODE_LANGUAGES:
            continue
        if (
            any(segment in _TASK_FRONTEND_PATH_SEGMENTS for segment in parent_segments)
            and not asks_for_frontend
        ):
            continue
        if _is_task_documentation_candidate(normalized_path):
            continue

        signal = float(_base_score(file_path, search_terms))
        symbol_matches = 0
        for symbol_name in symbol_names.get(file_path, []):
            if any(_term_matches_symbol(token, symbol_name) for token in search_terms):
                symbol_matches += 1
        signal += min(symbol_matches * 2.0, 6.0)

        if signal <= 0:
            continue
        signal_by_language[language] = signal_by_language.get(language, 0.0) + signal

    if not signal_by_language:
        return ""

    ranked = sorted(signal_by_language.items(), key=lambda item: (-item[1], item[0]))
    top_language, top_score = ranked[0]
    second_score = ranked[1][1] if len(ranked) > 1 else 0.0
    if top_score < 6.0:
        return ""
    if second_score > 0 and top_score < (second_score * 1.3):
        return ""
    return top_language


def _infer_locality_anchor_terms(
    rows: list[tuple[str, str, int | None]],
    tokens: list[str],
    symbol_names: dict[str, list[str]],
    task_mode: str | None,
) -> set[str]:
    if _normalize_task_mode(task_mode) != "refactor":
        return set()

    search_terms = _expand_task_terms(tokens)
    focus_terms = [
        term
        for term in search_terms
        if term
        not in {
            "behavior",
            "behaviour",
            "clarify",
            "clarity",
            "cleanup",
            "flow",
            "preserve",
            "preserving",
            "refactor",
            "restructure",
            "simplify",
        }
    ]
    token_set = set(tokens)
    asks_for_frontend = bool(token_set & _TASK_FRONTEND_HINT_TOKENS)
    candidates: list[tuple[float, str]] = []
    for file_path, language, _ in rows:
        normalized = _normalize_path(file_path)
        parent_segments = _path_segments(normalized)[:-1]
        if _is_third_party_path(normalized) or _is_ranking_noise_path(normalized):
            continue
        if _looks_like_test_path(normalized):
            continue
        if language not in _TASK_CODE_LANGUAGES:
            continue
        if (
            any(segment in _TASK_FRONTEND_PATH_SEGMENTS for segment in parent_segments)
            and not asks_for_frontend
        ):
            continue
        path_score = float(_base_score(file_path, search_terms))
        focus_path_score = float(_base_score(file_path, focus_terms))
        symbol_score = 0.0
        focus_symbol_score = 0.0
        for symbol_name in symbol_names.get(file_path, []):
            if any(_term_matches_symbol(term, symbol_name) for term in search_terms):
                symbol_score += 2.0
            if any(_term_matches_symbol(term, symbol_name) for term in focus_terms):
                focus_symbol_score += 2.0
        signal = path_score + min(symbol_score, 8.0)
        focus_signal = focus_path_score + min(focus_symbol_score, 8.0)
        if signal >= 5.0 and focus_signal > 0:
            candidates.append((signal, file_path))

    if not candidates:
        return set()

    candidates.sort(key=lambda item: (-item[0], item[1]))
    anchor_terms: set[str] = set()
    common_terms = {
        "app",
        "file",
        "js",
        "jsx",
        "md",
        "py",
        "src",
        "test",
        "tests",
        "ts",
        "tsx",
    }
    for _, file_path in candidates[:2]:
        anchor_terms.update(_path_term_set(file_path) - common_terms)
    return anchor_terms


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


def _is_ranking_noise_path(path: str) -> bool:
    segments = _path_segments(path)[:-1]
    return any(segment in _RANKING_NOISE_PATH_SEGMENTS for segment in segments)


def _is_task_evidence_noise_path(path: str) -> bool:
    normalized = _normalize_path(path).lower()
    segments = _path_segments(normalized)
    if any(segment in {".obsidian", ".vscode"} for segment in segments[:-1]):
        return True
    basename = normalized.rsplit("/", 1)[-1]
    if basename.startswith(".env") or basename in {"docker-compose.yml", "package-lock.json", "yarn.lock", "pnpm-lock.yaml"}:
        return True
    stem, dot, extension = basename.rpartition(".")
    return bool(dot and extension in {"gif", "ico", "jpeg", "jpg", "lock", "png", "svg", "webp"})


def _task_allows_generic_clutter(tokens: list[str], task_mode: str | None) -> bool:
    if _normalize_task_mode(task_mode) in {"review"}:
        return True
    return bool(
        set(tokens)
        & {
            "build",
            "ci",
            "config",
            "configuration",
            "container",
            "dependency",
            "dependencies",
            "docker",
            "environment",
            "harness",
            "infra",
            "infrastructure",
            "package",
            "release",
            "tool",
            "tooling",
        }
    )


def _is_generic_clutter_path(path: str) -> bool:
    normalized = _normalize_path(path).lower()
    segments = _path_segments(normalized)
    basename = segments[-1] if segments else normalized
    parent_segments = segments[:-1]
    if basename in {".ds_store", "thumbs.db"}:
        return True
    if basename.endswith(".lock") or basename in {"package-lock.json", "yarn.lock", "pnpm-lock.yaml"}:
        return True
    if basename in {"dockerfile", "docker-compose.yml", "docker-compose.yaml"}:
        return True
    root_config_basenames = {
        ".env",
        ".env.example",
        ".gitignore",
        ".prettierrc",
        ".ruff.toml",
        "pyproject.toml",
        "tsconfig.json",
        "package.json",
    }
    if parent_segments:
        return False
    if basename in root_config_basenames:
        return True
    if "." in basename:
        extension = basename.rsplit(".", 1)[-1]
        return extension in {"json", "lock", "toml", "yaml", "yml"}
    return False


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


def _is_pinned_agentic_anchor_path(path: str) -> bool:
    normalized = _normalize_path(path)
    return normalized in _PINNED_AGENTIC_CONTEXT_PATHS


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


def _agentic_instruction_family(path: str) -> str:
    normalized = _normalize_path(path).lower()
    for prefix, family in (
        (".cursor/", ".cursor"),
        (".github/", ".github"),
        (".opencode/", ".opencode"),
        (".claude/", ".claude"),
        (".codex/", ".codex"),
        (".gemini/", ".gemini"),
    ):
        if normalized.startswith(prefix):
            return family
    return ""


def _cap_repeated_agentic_instruction_families(
    scored_items: list[tuple[float, str, str]],
) -> list[tuple[float, str, str]]:
    capped: list[tuple[float, str, str]] = []
    seen_families: set[str] = set()
    for item in scored_items:
        family = _agentic_instruction_family(item[1])
        if family and family in seen_families:
            continue
        if family:
            seen_families.add(family)
        capped.append(item)
    return capped


def _default_snippet_range(file_path: str, line_count: int) -> tuple[int, int]:
    normalized = _normalize_path(file_path)
    if normalized in {"wiki/log.md", "wiki/user/log.md"} or normalized.endswith("/wiki/user/log.md"):
        start = max(1, line_count - 39)
        return (start, line_count)
    return (1, min(40, line_count))


def _score_task_file(
    file_path: str,
    file_language: str,
    tokens: list[str],
    file_symbols: list[str],
    last_commit_at: int | None,
    now_ts: int,
    docs_intent: bool,
    task_mode: str | None,
    preferred_language: str,
    topical_text: str = "",
    locality_anchor_terms: set[str] | None = None,
) -> float:
    return explain_task_file_score(
        file_path=file_path,
        file_language=file_language,
        task_description=" ".join(tokens),
        file_symbols=file_symbols,
        last_commit_at=last_commit_at,
        task_mode=task_mode,
        preferred_language=preferred_language,
        now_ts=now_ts,
        docs_intent=docs_intent,
        topical_text=topical_text,
        locality_anchor_terms=locality_anchor_terms,
    ).total


def explain_task_file_score(
    file_path: str,
    file_language: str,
    task_description: str,
    file_symbols: tuple[str, ...] | list[str] = (),
    last_commit_at: int | None = None,
    task_mode: str | None = None,
    preferred_language: str = "",
    now_ts: int | None = None,
    docs_intent: bool | None = None,
    topical_text: str = "",
    locality_anchor_terms: set[str] | None = None,
) -> RankingScore:
    tokens = _tokenize(task_description)
    if docs_intent is None:
        docs_intent = _has_documentation_intent(tokens) or _normalize_task_mode(task_mode) == "docs"
    if now_ts is None:
        now_ts = int(time.time())

    features = {
        "lexical": 0.0,
        "alias": 0.0,
        "role": 0.0,
        "document_shape": 0.0,
        "topicality": 0.0,
        "symbol": 0.0,
        "freshness": 0.0,
        "language_penalty": 0.0,
        "generic_index_penalty": 0.0,
        "locality": 0.0,
        "artifact_penalty": 0.0,
        "subject_coupling": 0.0,
        "docs_adjacency": 0.0,
        "clutter_penalty": 0.0,
    }

    lexical, alias = _path_match_feature_scores(file_path, tokens)
    features["lexical"] = lexical
    features["alias"] = alias
    features["role"] = _score_task_role(file_path=file_path, tokens=tokens, task_mode=task_mode)
    features["document_shape"] = _documentation_intent_file_boost(
        file_path=file_path,
        docs_intent=docs_intent,
        task_mode=task_mode,
    )

    search_terms = _expand_task_terms(tokens)
    features["topicality"] = _topicality_score(
        file_path=file_path,
        tokens=tokens,
        search_terms=search_terms,
        topical_text=topical_text,
    )
    if docs_intent and _is_task_documentation_candidate(file_path):
        features["topicality"] += _documentation_intent_topicality_score(
            file_path=file_path,
            tokens=tokens,
            topical_text=topical_text,
        )
    if docs_intent:
        features["subject_coupling"] = _subject_coupling_score(
            file_path=file_path,
            tokens=tokens,
            topical_text=topical_text,
        )
    if (
        docs_intent
        and _is_task_documentation_candidate(file_path)
        and features["subject_coupling"] >= _subject_coupling_threshold(tokens)
    ):
        features["document_shape"] += 8.0

    symbol_boost = 0.0
    weak_symbol_terms = {
        "add",
        "behavior",
        "behaviour",
        "case",
        "cases",
        "clarity",
        "doc",
        "docs",
        "document",
        "documentation",
        "flow",
        "note",
        "notes",
        "preserve",
        "preserving",
        "regression",
        "test",
        "tests",
    }
    symbol_terms_set: set[str] = set()
    for token in tokens:
        if token not in weak_symbol_terms:
            symbol_terms_set.update(_term_variants(token))
    symbol_terms = sorted(symbol_terms_set)
    for symbol_name in file_symbols:
        for token in symbol_terms:
            if _term_matches_symbol(token, symbol_name):
                symbol_boost += 2.0
    features["symbol"] = min(symbol_boost, 8.0)

    if last_commit_at is not None:
        age = now_ts - last_commit_at
        if age <= 7 * 86400:
            features["freshness"] = 5.0
        elif age <= 30 * 86400:
            features["freshness"] = 2.0

    mode = _normalize_task_mode(task_mode)
    if (
        preferred_language
        and mode in {"bugfix", "implementation", "refactor"}
        and file_language in _TASK_CODE_LANGUAGES
        and file_language != preferred_language
    ):
        features["language_penalty"] = -4.0 if mode == "refactor" else -3.0

    features["generic_index_penalty"] = _generic_document_penalty(
        file_path=file_path,
        docs_intent=docs_intent,
        task_mode=task_mode,
    )
    features["locality"] = _locality_score(
        file_path=file_path,
        task_mode=task_mode,
        locality_anchor_terms=locality_anchor_terms,
    )

    total = sum(features.values())
    return RankingScore(total=total, features=features)


def _generic_document_penalty(
    file_path: str,
    docs_intent: bool,
    task_mode: str | None,
) -> float:
    mode = _normalize_task_mode(task_mode)
    if not docs_intent and mode != "docs":
        return 0.0
    normalized = _normalize_path(file_path)
    if not _is_task_documentation_candidate(normalized):
        return 0.0
    basename = _path_segments(normalized)[-1]
    stem = basename.rsplit(".", 1)[0]
    if stem in {"index", "log", "changelog"}:
        return -12.0
    return 0.0


def _topicality_score(
    file_path: str,
    tokens: list[str],
    search_terms: list[str],
    topical_text: str,
) -> float:
    weak_terms = {
        "behavior",
        "behaviour",
        "clarity",
        "doc",
        "docs",
        "document",
        "documentation",
        "flow",
        "note",
        "notes",
        "preserve",
        "preserving",
        "regression",
        "test",
        "tests",
    }
    strong_exact_terms = {token.lower() for token in tokens if len(token) > 2 and token.lower() not in weak_terms}
    exact_terms = strong_exact_terms or {token.lower() for token in tokens if len(token) > 2}
    morph_terms: set[str] = set()
    for token in tokens:
        if token.lower() not in weak_terms:
            morph_terms.update(_term_variants(token.lower()))
    weak_synonyms = weak_terms | {"guide", "guides", "spec", "specs", "wiki"}
    synonym_terms = {
        term.lower()
        for term in search_terms
        if len(term) > 2
        and term.lower() not in exact_terms
        and term.lower() not in morph_terms
        and term.lower() not in weak_synonyms
    }
    path_terms = _path_term_set(file_path)
    text_terms = set(_tokenize(topical_text)) if topical_text else set()
    evidence_terms = path_terms | text_terms

    exact_path_matches = len(exact_terms & path_terms)
    exact_text_matches = len(exact_terms & text_terms)
    morph_matches = len((morph_terms - exact_terms) & evidence_terms)
    synonym_matches = len(synonym_terms & evidence_terms)
    cooccurrence_boost = 0.0
    if len(exact_terms & evidence_terms) >= 2:
        cooccurrence_boost = 4.0

    return min(
        (exact_path_matches * 3.0)
        + (exact_text_matches * 2.0)
        + (morph_matches * 2.0)
        + min(synonym_matches * 1.0, 4.0)
        + cooccurrence_boost,
        28.0,
    )


def _documentation_intent_topicality_score(
    file_path: str,
    tokens: list[str],
    topical_text: str,
) -> float:
    """Score docs-intent terms only for documentation-shaped candidates.

    General topicality treats terms like "behavior", "troubleshooting", and
    "notes" as weak so source/test files cannot win solely on generic task
    wording. In docs mode those terms are meaningful evidence for doc files: a
    behavior spec or troubleshooting note should clear the docs topicality gate
    before source/test files when no more specific retrieval docs exist.
    """

    doc_terms = {
        "behavior",
        "behaviour",
        "guide",
        "guides",
        "note",
        "notes",
        "readme",
        "troubleshoot",
        "troubleshooting",
    }
    task_doc_terms = {token for token in tokens if token in doc_terms}
    if not task_doc_terms:
        return 0.0

    evidence_terms = _path_term_set(file_path)
    if topical_text:
        evidence_terms.update(_tokenize(topical_text))
    matches = task_doc_terms & evidence_terms
    return min(len(matches) * 2.5, 7.5)


def _subject_terms(tokens: list[str]) -> set[str]:
    base_terms = _primary_subject_base_terms(tokens)
    terms = _primary_subject_terms(tokens)
    for lowered in base_terms:
        terms.update(_TASK_KEYWORD_ALIASES.get(lowered, ()))
    return terms


def _primary_subject_base_terms(tokens: list[str]) -> set[str]:
    lane_terms = (
        _TASK_DOC_HINT_TOKENS
        | _TASK_DOC_INTENT_SECONDARY_TOKENS
        | _TASK_TEST_HINT_TOKENS
        | _TASK_IMPLEMENT_HINT_TOKENS
        | _TASK_REFACTOR_HINT_TOKENS
        | {
            "behavior",
            "behaviour",
            "clarity",
            "flow",
            "note",
            "notes",
            "preserve",
            "preserving",
            "troubleshoot",
            "troubleshooting",
        }
    )
    return {
        token.lower()
        for token in tokens
        if len(token.lower()) > 2 and token.lower() not in lane_terms
    }


def _primary_subject_terms(tokens: list[str]) -> set[str]:
    base_terms = _primary_subject_base_terms(tokens)
    terms: set[str] = set()
    for lowered in base_terms:
        terms.update(_term_variants(lowered))
    return terms


def _subject_coupling_score(file_path: str, tokens: list[str], topical_text: str) -> float:
    subject_terms = _primary_subject_terms(tokens)
    if not subject_terms:
        return 0.0

    path_terms = _path_term_set(file_path)
    text_terms = set(_tokenize(topical_text)) if topical_text else set()
    exact_path_matches = len(subject_terms & path_terms)
    exact_text_matches = len(subject_terms & text_terms)
    cooccurrence_boost = 3.0 if len(subject_terms & (path_terms | text_terms)) >= 2 else 0.0
    return min((exact_path_matches * 3.0) + (exact_text_matches * 2.0) + cooccurrence_boost, 18.0)


def _subject_coupling_threshold(tokens: list[str]) -> float:
    primary_terms = _primary_subject_base_terms(tokens)
    return 3.0 if len(primary_terms) <= 1 else 8.0


def _with_score_feature(score: RankingScore, feature_name: str, value: float) -> RankingScore:
    if value == 0.0:
        return score
    features = dict(score.features)
    features[feature_name] = features.get(feature_name, 0.0) + value
    return RankingScore(total=score.total + value, features=features)


def _infer_docs_adjacency_evidence(
    scored_items: list[tuple[RankingScore, str, str, bool]],
) -> DocsAdjacencyEvidence:
    common_terms = {
        "app",
        "file",
        "js",
        "jsx",
        "md",
        "py",
        "src",
        "test",
        "tests",
        "ts",
        "tsx",
    }
    anchors: list[tuple[float, str]] = []
    for score, file_path, _language, is_third_party in scored_items:
        if is_third_party or _is_task_documentation_candidate(file_path):
            continue
        topical = _topical_component(score)
        if topical >= 8.0 or score.features.get("subject_coupling", 0.0) >= 3.0:
            anchors.append((topical, file_path))

    anchors.sort(key=lambda item: (-item[0], item[1]))
    terms: set[str] = set()
    for _, file_path in anchors[:3]:
        terms.update(_path_term_set(file_path) - common_terms)
    return DocsAdjacencyEvidence(
        anchor_terms=frozenset(terms),
        best_anchor_topical=anchors[0][0] if anchors else 0.0,
    )


def _docs_adjacency_score(
    file_path: str,
    topical_text: str,
    tokens: list[str],
    evidence: DocsAdjacencyEvidence,
) -> float:
    if not evidence.anchor_terms or not _is_task_documentation_candidate(file_path):
        return 0.0

    path_terms = _path_term_set(file_path)
    text_terms = _path_term_set(topical_text) if topical_text else set()
    subject_terms = _primary_subject_terms(tokens)

    shared_subject_terms = subject_terms & (path_terms | text_terms)
    anchor_mentions = evidence.anchor_terms & text_terms
    same_topic_path_terms = evidence.anchor_terms & path_terms

    score = 0.0
    if shared_subject_terms:
        score += min(len(shared_subject_terms) * 2.0, 6.0)
    if len(anchor_mentions) >= 2:
        score += min(len(anchor_mentions) * 2.5, 7.5)
    if len(same_topic_path_terms) >= 2:
        score += 4.0
    return min(score, 12.0)


def _locality_score(
    file_path: str,
    task_mode: str | None,
    locality_anchor_terms: set[str] | None,
) -> float:
    if _normalize_task_mode(task_mode) != "refactor" or not locality_anchor_terms:
        return 0.0
    normalized = _normalize_path(file_path)
    if _is_third_party_path(normalized) or _is_ranking_noise_path(normalized):
        return 0.0

    path_terms = _path_term_set(normalized)
    shared = path_terms & locality_anchor_terms
    if not shared:
        return 0.0

    parent_segments = _path_segments(normalized)[:-1]
    boost = min(len(shared) * 1.5, 6.0)
    if parent_segments and parent_segments[-1] in locality_anchor_terms:
        boost += 2.0
    if any(segment in _TASK_TEST_PATH_SEGMENTS for segment in parent_segments) and len(shared) >= 2:
        boost += 12.0
    return min(boost, 18.0)


def _topical_component(score: RankingScore) -> float:
    return (
        score.features.get("lexical", 0.0)
        + min(score.features.get("alias", 0.0), 4.0)
        + score.features.get("topicality", 0.0)
        + score.features.get("symbol", 0.0)
        + score.features.get("locality", 0.0)
        + score.features.get("subject_coupling", 0.0)
        + score.features.get("docs_adjacency", 0.0)
    )


def _looks_like_test_path(file_path: str) -> bool:
    normalized = _normalize_path(file_path)
    segments = _path_segments(normalized)
    if not segments:
        return False
    basename = segments[-1]
    parent_segments = segments[:-1]
    return (
        any(segment in _TASK_TEST_PATH_SEGMENTS for segment in parent_segments)
        or basename.startswith("test_")
        or basename.endswith("_test.py")
        or ".test." in basename
        or ".spec." in basename
    )


def _is_code_path(file_path: str) -> bool:
    basename = _path_segments(file_path)[-1] if _path_segments(file_path) else ""
    stem, dot, extension = basename.rpartition(".")
    return bool(dot and extension.lower() in _TASK_CODE_EXTENSIONS)


def _apply_topicality_gate(
    score: RankingScore,
    file_path: str,
    tokens: list[str],
    task_mode: str | None,
    best_topical: float,
) -> float:
    mode = _normalize_task_mode(task_mode)
    token_set = set(tokens)
    asks_for_tests = bool(token_set & _TASK_TEST_HINT_TOKENS) or mode == "review"
    asks_for_docs = bool(token_set & _TASK_DOC_HINT_TOKENS) or mode == "docs"
    asks_for_refactor = bool(token_set & _TASK_REFACTOR_HINT_TOKENS) or mode == "refactor"
    topical = _topical_component(score)
    if best_topical < 5.0:
        return score.total

    if asks_for_docs and _is_task_documentation_candidate(file_path):
        has_subject_coupling = score.features.get("subject_coupling", 0.0) >= _subject_coupling_threshold(tokens)
        has_docs_adjacency = score.features.get("docs_adjacency", 0.0) >= 12.0
        if not has_subject_coupling and not has_docs_adjacency and best_topical >= 8.0:
            return score.total - 55.0
        primary_topical = (
            score.features.get("lexical", 0.0)
            + score.features.get("topicality", 0.0)
            + score.features.get("symbol", 0.0)
            + score.features.get("subject_coupling", 0.0)
            + score.features.get("docs_adjacency", 0.0)
        )
        if (
            score.features.get("lexical", 0.0) <= 0.0
            and primary_topical < 12.0
            and primary_topical < (best_topical * 0.9)
        ):
            return score.total - 55.0

    if asks_for_docs and not _is_task_documentation_candidate(file_path) and topical >= 8.0:
        return score.total + 4.0

    if asks_for_refactor and _is_task_documentation_candidate(file_path):
        return score.total - 24.0

    if asks_for_refactor and any(segment in _TASK_FRONTEND_PATH_SEGMENTS for segment in _path_segments(file_path)[:-1]):
        return score.total - 50.0

    below_floor = topical < 8.0
    far_from_best = topical < (best_topical * 0.45)
    if not below_floor and not far_from_best:
        return score.total

    gated_lane_shape = False
    if asks_for_docs and _is_task_documentation_candidate(file_path):
        gated_lane_shape = True
    elif asks_for_tests and _looks_like_test_path(file_path):
        gated_lane_shape = True
    elif asks_for_refactor and _is_code_path(file_path):
        gated_lane_shape = True

    if not gated_lane_shape:
        return score.total

    penalty = 35.0 if asks_for_docs and _is_task_documentation_candidate(file_path) else 16.0
    return score.total - penalty


def _score_task_role(file_path: str, tokens: list[str], task_mode: str | None) -> float:
    normalized = _normalize_path(file_path)
    segments = _path_segments(normalized)
    if not segments:
        return 0.0

    basename = segments[-1]
    stem, dot, extension = basename.rpartition(".")
    extension = extension.lower() if dot else ""
    token_set = set(tokens)

    mode = _normalize_task_mode(task_mode)
    asks_for_tests = bool(token_set & _TASK_TEST_HINT_TOKENS) or mode == "review"
    asks_for_docs = bool(token_set & _TASK_DOC_HINT_TOKENS) or mode == "docs"
    asks_for_frontend = bool(token_set & _TASK_FRONTEND_HINT_TOKENS)
    asks_for_implementation = bool(token_set & _TASK_IMPLEMENT_HINT_TOKENS) or mode in {
        "bugfix",
        "implementation",
    }
    asks_for_refactor = bool(token_set & _TASK_REFACTOR_HINT_TOKENS) or mode == "refactor"
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
    in_frontend_tree = any(segment in _TASK_FRONTEND_PATH_SEGMENTS for segment in parent_segments)
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
    looks_like_frontend_file = in_frontend_tree and extension in {"js", "jsx", "ts", "tsx"}

    score = 0.0
    if in_source_tree:
        if asks_for_refactor:
            score += 5.0
        elif asks_for_docs:
            score += 0.5
        else:
            score += 3.0 if asks_for_implementation else 1.5
    if is_code_file:
        if asks_for_refactor:
            score += 3.0
        elif asks_for_docs:
            score -= 1.0
        else:
            score += 2.0 if asks_for_implementation else 1.0
    if looks_like_test_file:
        if asks_for_tests:
            score += 3.0
        elif asks_for_refactor:
            score -= 12.0
        elif asks_for_docs:
            score -= 5.0
        else:
            score -= 2.0
    if is_doc_file:
        score += 4.0 if asks_for_docs else -1.5
    if in_doc_tree and asks_for_implementation:
        score -= 1.0

    if mode == "docs":
        if in_doc_tree:
            score += 2.0
        if in_source_tree:
            score -= 1.0

    if looks_like_frontend_file and not asks_for_frontend:
        if mode == "refactor":
            score -= 14.0
        elif mode in {"bugfix", "implementation", "docs"}:
            score -= 3.0

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
    if extension in _TASK_CODE_EXTENSIONS:
        return False

    in_doc_tree = any(segment in _TASK_DOC_PATH_SEGMENTS for segment in parent_segments)
    has_spec_name = "spec" in stem or "specification" in stem
    has_doc_name_hint = any(token in stem for token in _TASK_DOC_FILENAME_HINT_TOKENS)
    return (
        extension in _TASK_DOC_EXTENSIONS
        or in_doc_tree
        or has_spec_name
        or has_doc_name_hint
    )


def _documentation_intent_file_boost(
    file_path: str,
    docs_intent: bool,
    task_mode: str | None,
) -> float:
    mode = _normalize_task_mode(task_mode)
    if not docs_intent and mode != "docs":
        return 0.0
    if _is_task_documentation_candidate(file_path):
        parent_segments = _path_segments(_normalize_path(file_path))[:-1]
        if mode == "docs":
            boost = 20.0
            priority_boost = 10.0
        else:
            boost = 10.0
            priority_boost = 6.0
        if any(segment in _TASK_DOC_PRIORITY_PATH_SEGMENTS for segment in parent_segments):
            boost += priority_boost
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
    task_mode: str | None = None,
) -> tuple[list[RankedFile], list[RankedFile]]:
    tokens = _tokenize(task_description)
    if not tokens or max_items <= 0:
        return ([], [])
    mode = _normalize_task_mode(task_mode)
    docs_intent = _has_documentation_intent(tokens) or mode == "docs"

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

    artifact_search_text = _load_artifact_search_text(database_path)

    uses_default_agentic_limit = max_agentic_items is None
    if uses_default_agentic_limit:
        max_agentic_items = _agentic_lane_item_limit(max_items)
    max_agentic_items = max(0, min(max_agentic_items, max_items))
    max_task_items = max(0, max_items - max_agentic_items)

    now_ts = int(time.time())
    preferred_language = _infer_preferred_task_language(
        rows=rows,
        tokens=tokens,
        symbol_names=symbol_names,
        docs_intent=docs_intent,
    )
    refactor_for_ranking = mode == "refactor" or bool(set(tokens) & _TASK_REFACTOR_HINT_TOKENS)
    locality_anchor_terms = _infer_locality_anchor_terms(
        rows=rows,
        tokens=tokens,
        symbol_names=symbol_names,
        task_mode="refactor" if refactor_for_ranking else mode,
    )

    task_score_details: list[tuple[RankingScore, str, str, bool]] = []
    agentic_anchor_scored: list[tuple[float, str, str]] = []
    agentic_scored: list[tuple[float, str, str]] = []
    for file_path, language, last_commit_at in rows:
        normalized_path = _normalize_path(file_path)
        if _is_ranking_noise_path(normalized_path) or _is_task_evidence_noise_path(normalized_path):
            continue
        if _is_generic_clutter_path(normalized_path) and not _task_allows_generic_clutter(tokens, mode):
            continue
        prioritize_in_task_lane = (
            (docs_intent or mode == "docs")
            and _is_task_documentation_candidate(normalized_path)
            and not _is_pinned_agentic_anchor_path(normalized_path)
        )
        agentic_score = _agentic_context_score(file_path)
        if agentic_score > 0 and max_agentic_items > 0 and not prioritize_in_task_lane:
            if _is_agentic_anchor_path(normalized_path):
                agentic_anchor_scored.append((agentic_score, file_path, language))
            else:
                agentic_scored.append((agentic_score, file_path, language))
            continue

        if (
            any(segment in _TASK_DOC_CANDIDATE_EXCLUDED_SEGMENTS for segment in _path_segments(normalized_path)[:-1])
            and not _is_pinned_agentic_anchor_path(normalized_path)
        ):
            continue

        if max_task_items == 0:
            continue

        score = explain_task_file_score(
            file_path=file_path,
            file_language=language,
            task_description=task_description,
            file_symbols=symbol_names.get(file_path, []),
            last_commit_at=last_commit_at,
            now_ts=now_ts,
            docs_intent=docs_intent,
            task_mode=mode,
            preferred_language=preferred_language,
            topical_text=artifact_search_text.get(file_path, ""),
            locality_anchor_terms=locality_anchor_terms,
        )
        task_score_details.append((score, file_path, language, _is_third_party_path(normalized_path)))

    if docs_intent:
        docs_adjacency_evidence = _infer_docs_adjacency_evidence(task_score_details)
        with_adjacency: list[tuple[RankingScore, str, str, bool]] = []
        for score, file_path, language, is_third_party in task_score_details:
            adjacency = _docs_adjacency_score(
                file_path=file_path,
                topical_text=artifact_search_text.get(file_path, ""),
                tokens=tokens,
                evidence=docs_adjacency_evidence,
            )
            with_adjacency.append((_with_score_feature(score, "docs_adjacency", adjacency), file_path, language, is_third_party))
        task_score_details = with_adjacency

    best_topical = max((_topical_component(score) for score, _, _, _ in task_score_details), default=0.0)
    adjusted_task_details: list[tuple[float, str, str, bool]] = []
    for score, file_path, language, is_third_party in task_score_details:
        final_score = _apply_topicality_gate(
            score=score,
            file_path=file_path,
            tokens=tokens,
            task_mode=mode,
            best_topical=best_topical,
        )
        adjusted_task_details.append((final_score, file_path, language, is_third_party))

    if refactor_for_ranking:
        preferred_code_scores = [
            final_score
            for final_score, file_path, language, is_third_party in adjusted_task_details
            if not is_third_party
            and not _looks_like_test_path(file_path)
            and _is_code_path(file_path)
            and not any(segment in _TASK_FRONTEND_PATH_SEGMENTS for segment in _path_segments(file_path)[:-1])
            and (not preferred_language or language == preferred_language)
        ]
        best_preferred_code_score = max(preferred_code_scores, default=None)
        if best_preferred_code_score is not None:
            capped_details: list[tuple[float, str, str, bool]] = []
            for final_score, file_path, language, is_third_party in adjusted_task_details:
                if _looks_like_test_path(file_path) and final_score >= best_preferred_code_score:
                    final_score = best_preferred_code_score - 0.5
                elif (
                    _is_code_path(file_path)
                    and any(segment in _TASK_FRONTEND_PATH_SEGMENTS for segment in _path_segments(file_path)[:-1])
                ):
                    final_score = min(final_score, best_preferred_code_score - 50.0)
                elif (
                    _is_code_path(file_path)
                    and preferred_language
                    and language != preferred_language
                    and final_score >= best_preferred_code_score - 1.0
                ):
                    final_score = best_preferred_code_score - 6.0
                capped_details.append((final_score, file_path, language, is_third_party))
            adjusted_task_details = capped_details

    task_scored: list[tuple[float, str, str]] = []
    third_party_task_scored: list[tuple[float, str, str]] = []
    for final_score, file_path, language, is_third_party in adjusted_task_details:
        if is_third_party:
            third_party_task_scored.append((final_score, file_path, language))
        else:
            task_scored.append((final_score, file_path, language))

    task_scored.sort(key=lambda x: (-x[0], x[1]))
    third_party_task_scored.sort(key=lambda x: (-x[0], x[1]))
    agentic_anchor_scored.sort(key=lambda x: (-x[0], x[1]))
    agentic_scored.sort(key=lambda x: (-x[0], x[1]))
    agentic_scored = _cap_repeated_agentic_instruction_families(agentic_scored)

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
