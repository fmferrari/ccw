---
type: architecture
tags: [architecture, spec, slice]
created: 2026-05-23
updated: 2026-05-23
status: active
---

# Phase 1A runtime bootstrap spec

## Purpose

Ship the first executable CCW slice: an installable CLI that can materialize
repo-local `.ccw/` state layout deterministically.

This narrows the earlier Phase 1 bundle so runtime path semantics, rerun
behavior, and config defaults are frozen before SQLite schema bootstrap binds
the implementation to a data model.

## In scope

- An installable `ccw` CLI entrypoint
- `ccw init` for the current repo or a passed path
- Creation of `.ccw/`, `compiled/`, and `snapshots/`
- Creation of `.ccw/config.yaml`
- Idempotent rerun behavior
- Explicit invalid-target and non-writable-path failure behavior
- Focused CLI tests

## Explicit non-goals

- Full file walking or indexing
- Creation of `.ccw/index.sqlite`
- SQLite schema bootstrap for `files`, `symbols`, `edges`, `facts`, and
  `episodes`
- Symbol extraction
- Task classification
- `ccw compile`, `ccw validate`, `ccw compress`, or `ccw update`
- Conductor integration commands
- Any LLM dependency

## Contract

1. `ccw init` resolves an init target from the current repo or a passed path.
2. `ccw init` creates the local state directory if missing.
3. `ccw init` creates these paths when absent:
   - `.ccw/config.yaml`
   - `.ccw/compiled/`
   - `.ccw/snapshots/`
4. `ccw init` does not overwrite existing config or runtime artifacts on rerun.
5. The command fails loudly on invalid target paths or non-writable locations.
6. The command does not create SQLite state yet; schema bootstrap is the
   immediate follow-on slice.

## Proposed modules or surfaces

- `ccw.cli` - command parsing and dispatch
- `ccw.init` - repo bootstrap flow
- `ccw.config` - local config file defaults and loading
- `tests/` fixtures for CLI bootstrap behavior

## Validation

- CLI test: `ccw init` creates the expected layout in a temp repo
- CLI test: re-running `ccw init` is idempotent
- CLI test: invalid or non-writable targets fail with a stable error
- Config test: default config file is created and loadable

## Premortem-driven controls

- Keep SQLite schema bootstrap out of this slice so runtime path and packaging
  contracts can stabilize without hidden data-model coupling.
- Treat invalid-target and non-writable-path behavior as first-class acceptance
  criteria to prevent silent partial bootstrap.
- Freeze only the minimal config surface needed for follow-on slices so later
  schema work can extend state without redefining the `ccw init` contract.

## Done when

- A contributor can install the package locally and run `ccw init`
- The generated `.ccw/` layout matches the documented runtime bootstrap shape
- No manual file creation is needed to prepare repo-local runtime state
- Tests cover happy path, rerun safety, and failure behavior

## Implementation status

- Implemented with an installable `ccw` console entrypoint from `pyproject.toml`
- `ccw init` now materializes `.ccw/`, `.ccw/compiled/`, `.ccw/snapshots/`, and `.ccw/config.yaml`
- The config file uses a minimal YAML subset and is loadable through `ccw.config`
- Tests cover happy path, rerun safety, invalid-target failure, non-writable-path failure, and the absence of `.ccw/index.sqlite`

## Follow-on slice

After this slice lands, the next build step is Phase 1B schema bootstrap:
create `.ccw/index.sqlite`, add the initial tables, and extend tests to prove
that the runtime layout contract survives schema creation. Phase 2 indexing
starts after that follow-on lands.
