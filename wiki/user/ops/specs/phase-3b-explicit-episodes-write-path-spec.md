---
type: architecture
tags: [architecture, spec, slice, memory, episodes]
created: 2026-05-24
updated: 2026-05-24
status: archived
---

# Phase 3B explicit episodes write path spec

## Purpose

Continue Phase 3 by shipping the second explicit project-memory write path:
append-only episodes added by the user through `ccw episodes add`.

This slice deliberately ships manual explicit episode storage before automatic
run capture, task classification, or compile recipes expand the Phase 3
contract.

## In scope

- Add `ccw episodes add` as the first public episode-write surface
- Freeze the first shipped episode record shape in the existing SQLite
  `episodes` table
- Require explicit user-provided summary and touched files
- Keep episodes append-only across repeated writes, `ccw init`, and `ccw index`
- Upgrade the shipped placeholder `episodes` table additively during write-path
  or init flows
- Add focused CLI tests for persistence, repeated appends, missing-init failure,
  and upgrade behavior

## Explicit non-goals

- Automatic post-run capture from Conductor or harnesses
- `ccw update --run ...`
- Task classification
- Compile recipes or budget allocation
- Episode editing, deletion, deduplication, ranking, or search UX
- Inference of touched files from git diff, chat, or index state
- Rich evidence capture like tests run, decisions, or diffs
- A JSONL projection for episodes in this slice; the first shipped source of
  truth remains the SQLite `episodes` table

## Contract

1. `ccw episodes add <summary> <touched-files> [path]` writes one explicit
   episode row into an initialized repo-local state directory.
2. Episodes are append-only for this slice: adding an episode inserts a new row
   and never edits or removes previous rows.
3. Each episode row stores:
   - `summary` as the explicit user-provided completed-run summary
   - `touched_files` as a normalized JSON array of repo-relative file paths
   - `created_at` as a real UTC timestamp in ISO 8601 `Z` form
4. Empty summaries, empty touched-file sets, or invalid touched-file paths fail
   loudly with a stable error.
5. Touched files are normalized to sorted repo-relative POSIX paths before
   persistence.
6. The shipped placeholder `episodes` table upgrades additively when `ccw init`
   or `ccw episodes add` touches an already-bootstrapped repo.
7. `ccw index` and `ccw init` preserve previously stored episodes unchanged.

## Proposed modules or surfaces

- `ccw.cli` - command parsing and dispatch for `ccw episodes add`
- `ccw.episodes` - episode validation and append-only persistence
- `ccw.init` - shared repo-target and initialized-state validation
- `ccw.schema` - additive `episodes` table schema expansion for shipped repos
- `tests/test_cli_episodes.py` - public CLI coverage for episodes behavior

## Validation

- CLI test: `ccw episodes add` inserts one episode row into initialized local
  state
- CLI test: repeated adds append rows without overwriting prior episodes
- CLI test: missing `.ccw/` local state fails with a stable error
- CLI test: empty summaries or empty/invalid touched-file sets fail loudly
- CLI test: `ccw init` after episode insertion preserves episodes unchanged
- CLI test: `ccw index` after episode insertion preserves episodes unchanged
- CLI test: placeholder `episodes` table upgrades additively during init or add
- Project validation: `python -m unittest`

## Premortem-driven controls

- Keep the episode schema minimal so later `update`, classifier, and recipe work
  can extend memory additively instead of inheriting guessed structure.
- Keep episodes fully user-supplied so CCW does not invent run history during
  the first episode write path.
- Preserve append-only behavior by shipping no edit or delete surface in this
  slice.
- Normalize touched-file paths before persistence so episode evidence stays
  deterministic and inspectable.
- Treat SQLite as the first shipped episode source of truth and defer any JSONL
  projection until a later memory slice proves it is needed.

## Done when

- A contributor can run `ccw init` and then `ccw episodes add`
- Episodes persist append-only through repeated writes
- `ccw init` and `ccw index` preserve previously stored episodes
- Placeholder episode-schema state upgrades additively without destructive
  re-init
- Tests cover happy path, append-only behavior, failure behavior, and upgrade
  behavior

## Implementation status

- `ccw episodes add <summary> <touched-files> [path]` now persists explicit
  append-only episodes into the SQLite `episodes` table under initialized
  repo-local state
- Touched-file inputs are normalized to sorted repo-relative POSIX paths and
  stored as a JSON array string
- The shipped placeholder `episodes` table upgrades additively during `ccw init`
  and `ccw episodes add`
- Empty summaries, empty touched-file sets, and invalid touched-file paths fail
  loudly with stable errors
- `ccw init` and `ccw index` preserve previously stored episodes unchanged
- Validation passes with `python -m unittest` from the repo root

## Follow-on slice

Completed episodes slice. Superseded by
[[phase-3c-deterministic-task-classifier-spec]] for the active Phase 3 work.

After this slice, the next planned work is deterministic task classification,
then compile-recipe selection and budget allocation on top of explicit facts
and episodes.
