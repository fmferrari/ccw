---
type: architecture
tags: [architecture, spec, slice]
created: 2026-05-23
updated: 2026-05-23
status: active
---

# Phase 1 deterministic compiler spec

## Purpose

Ship the first executable CCW slice: an installable CLI that can bootstrap the
local `.ccw/` state layout and SQLite schema deterministically.

## In scope

- An installable `ccw` CLI entrypoint
- `ccw init` for the current repo or a passed path
- Creation of `.ccw/`, `compiled/`, and `snapshots/`
- Creation of `.ccw/config.yaml`
- Creation of `.ccw/index.sqlite` with the initial tables from the MVP data
  model
- Idempotent rerun behavior
- Focused CLI and schema tests

## Explicit non-goals

- Full file walking or indexing
- Symbol extraction
- Task classification
- `ccw compile`, `ccw validate`, `ccw compress`, or `ccw update`
- Conductor integration commands
- Any LLM dependency

## Contract

1. `ccw init` creates the local state directory if missing.
2. `ccw init` creates these paths when absent:
   - `.ccw/index.sqlite`
   - `.ccw/config.yaml`
   - `.ccw/compiled/`
   - `.ccw/snapshots/`
3. The SQLite bootstrap creates the initial `files`, `symbols`, `edges`,
   `facts`, and `episodes` tables.
4. Re-running `ccw init` must not destroy existing runtime data.
5. The command should fail loudly on invalid target paths or non-writable
   locations.

## Proposed modules or surfaces

- `ccw.cli` - command parsing and dispatch
- `ccw.init` - repo bootstrap flow
- `ccw.config` - local config file defaults and loading
- `ccw.db` - schema creation and connection bootstrap
- `tests/` fixtures for CLI bootstrap behavior

## Validation

- CLI test: `ccw init` creates the expected layout in a temp repo
- CLI test: re-running `ccw init` is idempotent
- DB test: expected tables exist after init
- Config test: default config file is created and loadable

## Done when

- A contributor can install the package locally and run `ccw init`
- The generated `.ccw/` layout matches the documented MVP shape
- The schema is created without manual SQL steps
- Tests cover happy path and rerun safety

## Follow-on slice

After this slice lands, the next build step is deterministic repo inventory and
indexing from Phase 2 of [[development-plan]].
