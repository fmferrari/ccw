from __future__ import annotations

import math
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Section:
    name: str
    weight: float
    min_budget: int
    max_items: int


@dataclass(frozen=True)
class Recipe:
    mode: str
    total_budget: int
    sections: dict[str, Section] = field(compare=False)


_RECIPES: dict[str, Recipe] = {
    "bugfix": Recipe(
        mode="bugfix",
        total_budget=6000,
        sections={
            "files": Section("files", 3.0, 500, 15),
            "symbols": Section("symbols", 1.5, 300, 10),
            "edges": Section("edges", 1.0, 200, 8),
            "facts": Section("facts", 0.5, 100, 5),
            "episodes": Section("episodes", 1.0, 200, 5),
            "constraints": Section("constraints", 0.3, 50, 3),
        },
    ),
    "implementation": Recipe(
        mode="implementation",
        total_budget=8000,
        sections={
            "files": Section("files", 3.0, 500, 20),
            "symbols": Section("symbols", 2.0, 400, 15),
            "edges": Section("edges", 1.5, 300, 12),
            "artifacts": Section("artifacts", 0.5, 100, 5),
            "facts": Section("facts", 0.5, 100, 5),
            "episodes": Section("episodes", 0.3, 50, 3),
            "constraints": Section("constraints", 0.3, 50, 3),
        },
    ),
    "review": Recipe(
        mode="review",
        total_budget=8000,
        sections={
            "files": Section("files", 3.0, 500, 25),
            "symbols": Section("symbols", 1.0, 200, 10),
            "edges": Section("edges", 1.0, 200, 10),
            "artifacts": Section("artifacts", 1.0, 200, 8),
            "facts": Section("facts", 1.0, 200, 8),
            "episodes": Section("episodes", 0.3, 50, 3),
            "constraints": Section("constraints", 0.5, 100, 5),
        },
    ),
    "refactor": Recipe(
        mode="refactor",
        total_budget=10000,
        sections={
            "files": Section("files", 3.0, 500, 30),
            "symbols": Section("symbols", 2.0, 400, 20),
            "edges": Section("edges", 2.0, 400, 15),
            "artifacts": Section("artifacts", 1.0, 200, 10),
            "facts": Section("facts", 0.5, 100, 5),
            "episodes": Section("episodes", 0.3, 50, 3),
            "constraints": Section("constraints", 0.3, 50, 3),
        },
    ),
}

_SUPPORTED_MODES = frozenset(_RECIPES.keys())


def get_recipe(mode: str) -> Recipe:
    normalized = mode.strip().lower()
    return _RECIPES.get(normalized, _RECIPES["implementation"])


def allocate_budget(
    recipe: Recipe, total_budget: int | None = None
) -> dict[str, int]:
    budget = recipe.total_budget if total_budget is None else total_budget

    sections = list(recipe.sections.values())
    total_weight = sum(s.weight for s in sections)

    if total_weight == 0:
        return {s.name: 0 for s in sections}

    min_sum = sum(s.min_budget for s in sections)
    if min_sum >= budget:
        return {s.name: s.min_budget for s in sections}

    raw: dict[str, int] = {}
    for s in sections:
        raw[s.name] = max(s.min_budget, int(math.floor(budget * s.weight / total_weight)))

    allocated = sum(raw.values())
    remainder = budget - allocated

    sections_sorted = sorted(sections, key=lambda s: s.weight, reverse=True)
    remaining_budget = remainder
    for s in sections_sorted:
        if remaining_budget <= 0:
            break
        raw[s.name] += 1
        remaining_budget -= 1

    return raw
