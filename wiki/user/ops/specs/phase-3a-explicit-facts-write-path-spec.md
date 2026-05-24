---
type: architecture
tags: [architecture, spec, slice, memory, facts]
created: 2026-05-24
updated: 2026-05-24
status: archived
---

# Phase 3A explicit facts write path spec

Completed explicit-facts slice. Superseded by
[[phase-3b-explicit-episodes-write-path-spec]] for the active Phase 3 work.

## Purpose

Open Phase 3 by shipping the first explicit project-memory write path:
append-only facts added by the user through `ccw facts add`.

This slice deliberately ships the lowest-risk memory primitive before episodes,
task classification, or compile recipes widen the Phase 3 contract.

## In scope

- Add `ccw facts add` as the first public memory-write surface
- Freeze the first shipped fact record shape in the existing SQLite `facts`
  table
- Require explicit user-provided fact kind and text
- Keep facts append-only across repeated writes, `ccw init`, and `ccw index`
- Upgrade the shipped placeholder `facts` table additively during write-path or
  init flows
- Add focused CLI tests for persistence, repeated appends, missing-init failure,
  and upgrade behavior

## Explicit non-goals

- Episode storage
- Task classification
- Compile recipes or budget allocation
- Automatic fact extraction or inference
- Fact editing, deletion, deduplication, or ranking
- A `ccw facts list` or search UX beyond what tests can verify through SQLite
- A JSONL projection for facts in this slice; the first shipped source of truth
  remains the SQLite `facts` table

## Contract

1. `ccw facts add <kind> <text> [path]` writes one explicit fact row into an
   initialized repo-local state directory.
2. Facts are append-only for this slice: adding a fact inserts a new row and
   never edits or removes previous rows.
3. Each fact row stores:
   - `kind` as one of `goal`, `constraint`, `decision`, or `preference`
   - `text` as the explicit user-provided fact body
   - `created_at` as a real UTC timestamp in ISO 8601 `Z` form
4. Empty fact text or unsupported fact kinds fail loudly with a stable error.
5. The shipped placeholder `facts` table upgrades additively when `ccw init` or
   `ccw facts add` touches an already-bootstrapped repo.
6. `ccw index` and `ccw init` preserve previously stored facts unchanged.

## Proposed modules or surfaces

- `ccw.cli` - command parsing and dispatch for `ccw facts add`
- `ccw.facts` - fact validation and append-only persistence
- `ccw.init` - shared repo-target and initialized-state validation
- `ccw.schema` - additive `facts` table schema expansion for shipped repos
- `tests/test_cli_facts.py` - public CLI coverage for facts behavior

## Validation

- CLI test: `ccw facts add` inserts one fact row into initialized local state
- CLI test: repeated adds append rows without overwriting prior facts
- CLI test: missing `.ccw/` local state fails with a stable error
- CLI test: unsupported kind or empty text fails loudly
- CLI test: `ccw index` after fact insertion preserves facts unchanged
- CLI test: placeholder `facts` table upgrades additively during init or add
- Project validation: `python -m unittest`

## Premortem-driven controls

- Keep the fact schema minimal so later episodes, classifiers, and recipes can
  extend memory additively instead of inheriting guessed structure.
- Keep facts fully user-supplied so CCW does not invent or infer memory during
  the first write path.
- Preserve append-only behavior by shipping no edit or delete surface in this
  slice.
- Use explicit stable validation on fact kinds and text to prevent vague or
  underspecified rows from polluting the memory substrate.
- Treat SQLite as the first shipped fact source of truth and defer any JSONL
  projection until a later memory slice proves it is needed.

## Done when

- A contributor can run `ccw init` and then `ccw facts add`
- Facts persist append-only through repeated writes
- `ccw init` and `ccw index` preserve previously stored facts
- Placeholder fact-schema state upgrades additively without destructive re-init
- Tests cover happy path, append-only behavior, failure behavior, and upgrade
  behavior

## Implementation status

- `ccw facts add <kind> <text> [path]` now persists explicit append-only facts
  into the SQLite `facts` table under initialized repo-local state
- The shipped placeholder `facts` table upgrades additively during `ccw init`
  and `ccw facts add`
- Fact kinds are validated against `goal`, `constraint`, `decision`, and
  `preference`, while empty fact text fails loudly
- `ccw init` and `ccw index` preserve previously stored facts unchanged
- Validation passes with `python -m unittest` from the repo root

## Follow-on slice

After this slice, the next planned work is append-only episode storage, then
task classification and compile-recipe selection on top of explicit project
memory.
