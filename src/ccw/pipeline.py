from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from ccw.compile import (
    CompiledContext,
    ContextSection,
    RankedFile,
    compute_index_hash,
    _load_constraints,
    _load_episodes,
    _load_facts,
    extract_snippets,
    rank_file_lanes,
    split_file_lane_budget,
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
    task_files: list[RankedFile] = field(default_factory=list)
    agentic_context_files: list[RankedFile] = field(default_factory=list)
    task_files_budget: int = 0
    agentic_context_budget: int = 0
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
        task_files, agentic_context_files = rank_file_lanes(
            target=target,
            task_description=ir.task_description,
            database_path=database_path,
            max_items=max_items,
        )
        ir.task_files = task_files
        ir.agentic_context_files = agentic_context_files
        ir.ranked_files = [*task_files, *agentic_context_files]
        return ir


class ExtractSnippetsPass:
    def run(self, ir: CompilationIR, target: Path, database_path: Path) -> CompilationIR:
        file_budget = ir.section_budgets.get("files", 0)
        task_budget, agentic_budget = split_file_lane_budget(file_budget)
        ir.task_files_budget = task_budget
        ir.agentic_context_budget = agentic_budget

        ir.task_files = extract_snippets(
            target=target,
            ranked_files=ir.task_files,
            task_description=ir.task_description,
            database_path=database_path,
            budget=task_budget,
        )
        ir.agentic_context_files = extract_snippets(
            target=target,
            ranked_files=ir.agentic_context_files,
            task_description=ir.task_description,
            database_path=database_path,
            budget=agentic_budget,
        )
        ir.ranked_files = [*ir.task_files, *ir.agentic_context_files]
        return ir


class LoadMemoryPass:
    def run(self, ir: CompilationIR, target: Path, database_path: Path) -> CompilationIR:
        ir.facts = _load_facts(database_path)
        ir.episodes = _load_episodes(database_path)
        ir.constraints = _load_constraints(database_path)
        ir.index_hash = compute_index_hash(database_path)
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

    if ir.task_files:
        used_budget = sum(
            len(snippet.text) // 4
            for item in ir.task_files
            for snippet in item.snippets
        )
        sections.append(
            ContextSection(
                name="files",
                items=tuple(ir.task_files),
                allocated_budget=ir.task_files_budget,
                used_budget=used_budget,
            )
        )

    if ir.agentic_context_files:
        used_budget = sum(
            len(snippet.text) // 4
            for item in ir.agentic_context_files
            for snippet in item.snippets
        )
        sections.append(
            ContextSection(
                name="agentic context",
                items=tuple(ir.agentic_context_files),
                allocated_budget=ir.agentic_context_budget,
                used_budget=used_budget,
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
