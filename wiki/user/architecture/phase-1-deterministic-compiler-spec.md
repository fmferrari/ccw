---
type: architecture
tags: [architecture, spec, slice]
created: 2026-05-23
updated: 2026-05-23
status: archived
---

# Phase 1B schema bootstrap spec

Superseded by [[phase-2a-deterministic-file-inventory-spec]] for the next active implementation slice.

## Purpose

Bootstrap the SQLite substrate inside repo-local `.ccw/` state now that the
Phase 1A runtime layout contract is stable.

This slice extends `ccw init` to create `.ccw/index.sqlite` and the first named
tables while deliberately avoiding Phase 2 indexing logic and Phase 3 memory
semantics.

## In scope

- Creation of `.ccw/index.sqlite` during `ccw init`
- Creation of the `files`, `symbols`, `edges`, `facts`, and `episodes` tables
- Idempotent rerun behavior when the database already exists
- Explicit conflicting-database-path failure behavior
- Focused CLI tests for schema presence and rerun safety

## Explicit non-goals

- Full file walking or indexing
- Populating rows in any SQLite table
- Finalizing the Phase 2 indexing or Phase 3 memory column model
- Schema migrations or version-management policy
- Symbol extraction
- Task classification
- `ccw compile`, `ccw validate`, `ccw compress`, or `ccw update`
- Conductor integration commands
- Any LLM dependency

## Contract

1. `ccw init` preserves the Phase 1A init-target, runtime-layout, and config
   creation behavior.
2. `ccw init` creates `.ccw/index.sqlite` when it is absent.
3. The bootstrapped database contains these named tables:
   - `files`
   - `symbols`
   - `edges`
   - `facts`
   - `episodes`
4. Each initial table is intentionally minimal and reserves only the primary-key
   surface needed to freeze table names without prematurely locking the later
   indexing or memory model.
5. Re-running `ccw init` does not overwrite config, directories, or existing
   database contents.
6. The command fails loudly on invalid target paths, non-writable locations, or
   a conflicting `.ccw/index.sqlite` path.

## Proposed modules or surfaces

- `ccw.cli` - command parsing and dispatch
- `ccw.init` - repo bootstrap flow
- `ccw.config` - local config file defaults and loading
- `ccw.schema` - SQLite schema bootstrap for local state
- `tests/` fixtures for CLI bootstrap behavior

## Validation

- CLI test: `ccw init` creates the expected layout and `.ccw/index.sqlite`
- CLI test: the bootstrapped database contains the expected table names
- CLI test: re-running `ccw init` preserves config and existing database rows
- CLI test: invalid, non-writable, or conflicting database-path targets fail
  with a stable error
- Config test: default config file is created and loadable

## Premortem-driven controls

- Keep the initial table definitions intentionally minimal so Phase 2 indexing
  and Phase 3 memory work can extend them additively instead of inheriting a
  guessed data model.
- Treat invalid-target, non-writable-path, and conflicting database-path
  behavior as first-class acceptance criteria to prevent silent partial
  bootstrap.
- Keep all SQLite bootstrap SQL behind one dedicated module so later migrations
  or schema expansion do not leak into CLI parsing.
- Verify rerun safety by preserving existing database rows, not just by checking
  that the file still exists.

## Done when

- A contributor can install the package locally and run `ccw init`
- The generated `.ccw/` layout includes `.ccw/index.sqlite`
- The bootstrapped database exposes the expected table names
- No manual file or SQL creation is needed to prepare repo-local runtime state
- Tests cover happy path, rerun safety, and failure behavior

## Implementation status

- `ccw init` now materializes `.ccw/index.sqlite` alongside the Phase 1A local
  state layout and config file
- SQLite bootstrap lives in `ccw.schema` and creates the `files`, `symbols`,
  `edges`, `facts`, and `episodes` tables idempotently
- The schema intentionally reserves table names with minimal primary-key-only
  tables so later slices can extend the model additively
- Validation passes with `python -m unittest` from the repo root
- Tests cover happy path, table presence, rerun preservation, invalid-target
  failure, non-writable-path failure, conflicting database-path failure, and
  the installed console entrypoint

## Follow-on slice

After this slice lands, the next build step is Phase 2 deterministic repo
inventory: walk the repo, persist file metadata and hashes into `files`, and
add fixture-backed indexing tests before symbol extraction expands the schema.
