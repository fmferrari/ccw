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


def rank_files(
    target: Path,
    task_description: str,
    database_path: Path,
    max_items: int = 20,
) -> list[RankedFile]:
    tokens = _tokenize(task_description)
    if not tokens:
        return []

    try:
        with sqlite3.connect(database_path) as connection:
            rows = connection.execute(
                "SELECT path, language, last_commit_at FROM files ORDER BY path"
            ).fetchall()
    except sqlite3.Error:
        return []

    symbol_names: dict[str, list[str]] = {}
    try:
        with sqlite3.connect(database_path) as connection:
            symbol_rows = connection.execute(
                "SELECT DISTINCT file_path, name FROM symbols"
            ).fetchall()
            for file_path, name in symbol_rows:
                symbol_names.setdefault(file_path, []).append(name)
    except sqlite3.Error:
        pass

    now_ts = int(time.time())
    seven_days = 7 * 86400
    thirty_days = 30 * 86400

    scored: list[tuple[float, str, str]] = []
    for file_path, language, last_commit_at in rows:
        score = float(_base_score(file_path, tokens))

        file_symbols = symbol_names.get(file_path, [])
        for symbol_name in file_symbols:
            for token in tokens:
                if token in symbol_name.lower():
                    score += 2.0

        if last_commit_at is not None:
            age = now_ts - last_commit_at
            if age <= seven_days:
                score += 5.0
            elif age <= thirty_days:
                score += 2.0

        scored.append((score, file_path, language))

    scored.sort(key=lambda x: (-x[0], x[1]))

    return [
        RankedFile(file_path=fp, score=sc, language=lang)
        for sc, fp, lang in scored[:max_items]
    ]


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
            best_range = (1, min(40, len(lines)))

        start_line, end_line = best_range
        snippet_lines = lines[start_line - 1 : end_line]
        snippet_text = "".join(snippet_lines)
        estimated = _estimate_tokens(snippet_text)

        if estimated > remaining_budget and remaining_budget > 0:
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
        output_path = resolved_target / ".ccw" / "compiled" / "compile-output.md"

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


def _compute_index_hash(database_path: Path) -> str:
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
    from ccw.recipe import allocate_budget

    total_budget = recipe.total_budget if budget is None else budget
    section_budgets = allocate_budget(recipe, total_budget)

    # Rank and extract snippets
    files_section = recipe.sections.get("files")
    max_items = files_section.max_items if files_section else 20
    ranked = rank_files(
        target=target,
        task_description=task_description,
        database_path=database_path,
        max_items=max_items,
    )

    snippet_budget = section_budgets.get("files", 0)
    ranked_with_snippets = extract_snippets(
        target=target,
        ranked_files=ranked,
        task_description=task_description,
        database_path=database_path,
        budget=snippet_budget,
    )

    # Load facts, episodes, constraints
    facts = _load_facts(database_path)
    episodes = _load_episodes(database_path)
    constraints = _load_constraints(database_path)
    index_hash = _compute_index_hash(database_path)

    sections: list[ContextSection] = []

    if ranked_with_snippets:
        sections.append(
            ContextSection(
                name="files",
                items=tuple(ranked_with_snippets),
                allocated_budget=snippet_budget,
                used_budget=snippet_budget,
            )
        )

    if facts:
        sections.append(
            ContextSection(
                name="facts",
                items=tuple(facts),
                allocated_budget=section_budgets.get("facts", 0),
                used_budget=sum(len(f) // 4 for f in facts),
            )
        )

    if episodes:
        sections.append(
            ContextSection(
                name="episodes",
                items=tuple(episodes),
                allocated_budget=section_budgets.get("episodes", 0),
                used_budget=sum(len(e) // 4 for e in episodes),
            )
        )

    if constraints:
        sections.append(
            ContextSection(
                name="constraints",
                items=tuple(constraints),
                allocated_budget=section_budgets.get("constraints", 0),
                used_budget=sum(len(c) // 4 for c in constraints),
            )
        )

    import datetime
    created_at = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")

    return CompiledContext(
        task_description=task_description,
        mode=mode,
        total_budget=total_budget,
        index_hash=index_hash,
        sections=tuple(sections),
        facts=tuple(facts),
        episodes=tuple(episodes),
        constraints=tuple(constraints),
        created_at=created_at,
    )
