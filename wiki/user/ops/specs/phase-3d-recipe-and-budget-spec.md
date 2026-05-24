---
type: architecture
tags: [architecture, spec, slice, recipe, budget]
created: 2026-05-25
updated: 2026-05-25
status: archived
---

# Phase 3D compile recipes and budget allocation spec

## Purpose

Ship the first deterministic compile-recipe definitions and budget-allocation
algorithm. This is the bridge between task classification (Phase 3C) and the
full context compiler (Phase 4): recipes define what index evidence to include
per task mode, and budgets allocate a token cap across recipe sections.

## In scope

- Define `Recipe` data structure with mode, total budget, and per-section
  weight definitions
- Define section types: `files`, `symbols`, `edges`, `artifacts`, `facts`,
  `episodes`, `constraints`
- Define one recipe per classification mode (`bugfix`, `implementation`,
  `review`, `refactor`) plus a catch-all default
- Implement `get_recipe(mode: str) -> Recipe` for deterministic lookup
- Implement `allocate_budget(recipe: Recipe, total_budget: int | None = None)
  -> dict[str, int]` that distributes budget proportionally by section weight
- Clamp section budgets to a minimum floor and never exceed total budget
- Default unknown or empty mode to the `implementation` recipe
- Add focused tests for recipe lookup, mode-to-recipe mapping, budget
  proportional allocation, zero/small budget edge cases, and unknown-mode
  fallback

## Explicit non-goals

- Full compiled-context artifact assembly (Phase 4)
- `ccw compile` or `ccw validate` CLI surfaces (Phase 4)
- HTML or markdown rendering (Phase 4)
- Reading facts or episodes to influence recipe selection (future slice)
- ML- or LLM-based budget tuning
- Tokenization of actual index content — budgets are target caps, not exact
  token counts
- Configurable or user-defined recipes (future)

## Contract

1. `get_recipe(mode: str) -> Recipe` returns the recipe for a classification
   mode. Unknown modes fall back to `implementation`. Case-insensitive.
2. Each `Recipe` has:
   - `mode: str` — canonical mode name
   - `total_budget: int` — default token budget for this recipe
   - `sections: dict[str, Section]` — section name to Section mapping
3. Each `Section` has:
   - `name: str` — section key (e.g. `files`, `symbols`)
   - `weight: float` — proportion of total budget (relative to other sections)
   - `min_budget: int` — minimum token allocation for this section
   - `max_items: int` — maximum number of items to include
4. `allocate_budget(recipe, total_budget=None)` returns a dict of
   `{section_name: token_budget}`. If `total_budget` is None, use
   `recipe.total_budget`.
5. Proportional allocation: each section gets
   `floor(total_budget * section.weight / total_weight)`, then any remainder
   tokens are distributed one by one to sections sorted by weight descending.
6. Each section allocation is clamped to `[section.min_budget, total_budget]`.
7. If the sum of all `min_budget` exceeds `total_budget`, each section gets
   exactly its `min_budget` (no valid distribution).
8. The recipe and allocation are purely deterministic — same inputs always
   produce the same outputs.

## Recipe definitions

### bugfix (default budget: 6000)

| Section | Weight | Min | Max items |
|---|---|---|---|
| `files` | 3.0 | 500 | 15 |
| `symbols` | 1.5 | 300 | 10 |
| `edges` | 1.0 | 200 | 8 |
| `facts` | 0.5 | 100 | 5 |
| `episodes` | 1.0 | 200 | 5 |
| `constraints` | 0.3 | 50 | 3 |

Focus on error context: exact file evidence, relevant symbols, recent episodes.

### implementation (default budget: 8000)

| Section | Weight | Min | Max items |
|---|---|---|---|
| `files` | 3.0 | 500 | 20 |
| `symbols` | 2.0 | 400 | 15 |
| `edges` | 1.5 | 300 | 12 |
| `artifacts` | 0.5 | 100 | 5 |
| `facts` | 0.5 | 100 | 5 |
| `episodes` | 0.3 | 50 | 3 |
| `constraints` | 0.3 | 50 | 3 |

Broad context: files, symbols, dependency graph, and project docs.

### review (default budget: 8000)

| Section | Weight | Min | Max items |
|---|---|---|---|
| `files` | 3.0 | 500 | 25 |
| `symbols` | 1.0 | 200 | 10 |
| `edges` | 1.0 | 200 | 10 |
| `artifacts` | 1.0 | 200 | 8 |
| `facts` | 1.0 | 200 | 8 |
| `episodes` | 0.3 | 50 | 3 |
| `constraints` | 0.5 | 100 | 5 |

Full-survey context: broad file view, project docs, and explicit constraints.

### refactor (default budget: 10000)

| Section | Weight | Min | Max items |
|---|---|---|---|
| `files` | 3.0 | 500 | 30 |
| `symbols` | 2.0 | 400 | 20 |
| `edges` | 2.0 | 400 | 15 |
| `artifacts` | 1.0 | 200 | 10 |
| `facts` | 0.5 | 100 | 5 |
| `episodes` | 0.3 | 50 | 3 |
| `constraints` | 0.3 | 50 | 3 |

Heaviest context: full dependency graph, symbol inventory, and documentation.

## Proposed modules or surfaces

- `src/ccw/recipe.py` — `Recipe` dataclass, `Section` dataclass, recipe
  definitions, `get_recipe()`, `allocate_budget()`
- `tests/test_recipes.py` — unit tests for recipe lookup and budget allocation

## Validation

- Unit test: `get_recipe('bugfix')` returns recipe with mode `bugfix`
- Unit test: `get_recipe('BUGFIX')` returns same recipe (case-insensitive)
- Unit test: `get_recipe('unknown')` returns `implementation` recipe
- Unit test: `get_recipe('')` returns `implementation` recipe
- Unit test: each recipe has all required sections
- Unit test: `allocate_budget` with default budget distributes proportionally
- Unit test: `allocate_budget` with custom total_budget scales proportionally
- Unit test: `allocate_budget` with zero budget clamps to min_budget per section
- Unit test: small budget near min_budget sum works correctly
- Unit test: remainder token distribution goes to highest-weight sections
- Project validation: `python -m unittest`

## Premortem-driven controls

- Totally separate from context assembly — recipes are pure data structures
  with no DB or I/O coupling, making them easy to test and review.
- Proportional allocation with minimum floors prevents any section being
  starved while keeping the algorithm simple and deterministic.
- Remainder distribution by weight ensures no token is wasted while keeping
  the algorithm predictable.
- Case-insensitive mode lookup with explicit fallback to `implementation`
  prevents silent failures for unexpected inputs.
- Using dataclasses rather than raw dicts gives stable attribute access and
  clear schema for future Phase 4 consumers.
- Decoupling recipe definitions from budget allocation means either can change
  or be tested independently.

## Done when

- `Recipe` and `Section` dataclasses exist with stable field schemas
- `get_recipe(mode)` returns the correct recipe for each defined mode
- `allocate_budget(recipe, total_budget)` returns correctly distributed
  per-section budgets with minimum clamping and remainder handling
- All edge cases (unknown mode, zero budget, small budget) produce correct
  deterministic output
- Full test suite passes with `python -m unittest`
