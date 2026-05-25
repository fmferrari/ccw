from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from ccw.compile import (
    CompiledContext,
    ContextSection,
    RankedFile,
    _compute_index_hash,
    _load_constraints,
    _load_episodes,
    _load_facts,
    extract_snippets,
    rank_files,
)
from ccw.classify import classify as classify_text
from ccw.recipe import Recipe, allocate_budget, get_recipe


@dataclass
class CompilationIR:
    task_description: str = ""
    mode: str = ""
    recipe: Recipe | None = None
    total_budget: int = 0
    section_budgets: dict[str, int] = field(default_factory=dict)
    index_hash: str = ""
    ranked_files: list[RankedFile] = field(default_factory=list)
    facts: list[str] = field(default_factory=list)
    episodes: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    created_at: str = ""


class Pass(Protocol):
    def run(self, ir: CompilationIR, target: Path, database_path: Path) -> CompilationIR: ...


class CompilationPipeline:
    def __init__(self, passes: list[Pass]) -> None:
        self._passes = passes

    def run(self, ir: CompilationIR, target: Path, database_path: Path) -> CompilationIR:
        current = ir
        for pass_ in self._passes:
            current = pass_.run(current, target, database_path)
        return current


class ResolveTaskPass:
    def run(self, ir: CompilationIR, target: Path, database_path: Path) -> CompilationIR:
        if ir.recipe is None:
            mode = ir.mode if ir.mode else classify_text(target, ir.task_description)
            ir.mode = mode
            ir.recipe = get_recipe(mode)
        if ir.total_budget == 0:
            ir.total_budget = ir.recipe.total_budget
        if not ir.section_budgets:
            ir.section_budgets = allocate_budget(ir.recipe, ir.total_budget)
        return ir


class RankFilesPass:
    def run(self, ir: CompilationIR, target: Path, database_path: Path) -> CompilationIR:
        max_items = 20
        if ir.recipe is not None:
            files_section = ir.recipe.sections.get("files")
            if files_section is not None:
                max_items = files_section.max_items
        ir.ranked_files = rank_files(
            target=target,
            task_description=ir.task_description,
            database_path=database_path,
            max_items=max_items,
        )
        return ir


class ExtractSnippetsPass:
    def run(self, ir: CompilationIR, target: Path, database_path: Path) -> CompilationIR:
        snippet_budget = ir.section_budgets.get("files", 0)
        ir.ranked_files = extract_snippets(
            target=target,
            ranked_files=ir.ranked_files,
            task_description=ir.task_description,
            database_path=database_path,
            budget=snippet_budget,
        )
        return ir


class LoadMemoryPass:
    def run(self, ir: CompilationIR, target: Path, database_path: Path) -> CompilationIR:
        ir.facts = _load_facts(database_path)
        ir.episodes = _load_episodes(database_path)
        ir.constraints = _load_constraints(database_path)
        ir.index_hash = _compute_index_hash(database_path)
        return ir


class AssemblePass:
    def run(self, ir: CompilationIR, target: Path, database_path: Path) -> CompilationIR:
        import datetime
        ir.created_at = (
            datetime.datetime.now(datetime.timezone.utc)
            .isoformat(timespec="seconds")
            .replace("+00:00", "Z")
        )
        return ir


def build_pipeline() -> CompilationPipeline:
    return CompilationPipeline([
        ResolveTaskPass(),
        RankFilesPass(),
        ExtractSnippetsPass(),
        LoadMemoryPass(),
        AssemblePass(),
    ])


def ir_to_compiled_context(ir: CompilationIR) -> CompiledContext:
    sections: list[ContextSection] = []

    if ir.ranked_files:
        sections.append(
            ContextSection(
                name="files",
                items=tuple(ir.ranked_files),
                allocated_budget=ir.section_budgets.get("files", 0),
                used_budget=ir.section_budgets.get("files", 0),
            )
        )

    if ir.facts:
        sections.append(
            ContextSection(
                name="facts",
                items=tuple(ir.facts),
                allocated_budget=ir.section_budgets.get("facts", 0),
                used_budget=sum(len(f) // 4 for f in ir.facts),
            )
        )

    if ir.episodes:
        sections.append(
            ContextSection(
                name="episodes",
                items=tuple(ir.episodes),
                allocated_budget=ir.section_budgets.get("episodes", 0),
                used_budget=sum(len(e) // 4 for e in ir.episodes),
            )
        )

    if ir.constraints:
        sections.append(
            ContextSection(
                name="constraints",
                items=tuple(ir.constraints),
                allocated_budget=ir.section_budgets.get("constraints", 0),
                used_budget=sum(len(c) // 4 for c in ir.constraints),
            )
        )

    return CompiledContext(
        task_description=ir.task_description,
        mode=ir.mode,
        total_budget=ir.total_budget,
        index_hash=ir.index_hash,
        sections=tuple(sections),
        facts=tuple(ir.facts),
        episodes=tuple(ir.episodes),
        constraints=tuple(ir.constraints),
        created_at=ir.created_at,
    )


def run_pipeline(
    task_description: str,
    mode: str,
    target: Path,
    database_path: Path,
    recipe: Recipe | None = None,
    budget: int | None = None,
) -> CompiledContext:
    ir = CompilationIR(
        task_description=task_description,
        mode=mode,
        recipe=recipe,
        total_budget=budget or 0,
    )
    pipeline = build_pipeline()
    result = pipeline.run(ir, target, database_path)
    return ir_to_compiled_context(result)
