---
type: architecture
tags: [architecture, spec, slice, indexing]
created: 2026-05-23
updated: 2026-05-23
status: archived
---

# Phase 2A deterministic file inventory spec

Superseded by [[phase-2b-python-top-level-symbol-inventory-spec]] for the active symbol-inventory slice.

## Purpose

Turn the Phase 1 bootstrap substrate into a usable deterministic repo index by
adding `ccw index [path]` and populating the `files` table with the first real
inventory rows.

This slice is intentionally narrower than full indexing. It freezes the file
inventory contract before symbol extraction, ranking signals, memory, or
compiled-context assembly expand the data model.

## In scope

- Add `ccw index [path]` as a public CLI command
- Require initialized repo-local state under `.ccw/` and fail loudly when it is
  missing
- Walk the target repo deterministically
- Persist one row per indexed file in `files`
- Store only the minimal file inventory fields needed now:
  - repo-relative path
  - SHA-256 content hash
  - file size in bytes
  - detected language label
- Reconcile the `files` table transactionally on each index run so changed and
  deleted files are reflected deterministically
- Exclude `.ccw/`, `.git/`, and symlinks from this slice's inventory
- Add fixture-backed CLI tests for initial indexing, rerun stability, changed
  files, deleted files, and missing-init failure

## Explicit non-goals

- Symbol, import, export, or edge extraction
- Git recency, ownership, or ranking signals
- Test-to-source mapping
- A broad ignore-engine or `.gitignore` parity
- Language-specific parsing beyond deterministic label detection
- Schema migrations beyond the additive `files` table expansion needed for this
  shipped Phase 2A contract
- `ccw compile`, `ccw validate`, `ccw compress`, or `ccw update`
- Conductor integration commands
- Any LLM dependency

## Contract

1. `ccw index [path]` defaults to `.` and indexes the resolved repo root passed
   by the user.
2. The command fails loudly when the target path does not exist, is not a
   directory, is not writable, or does not already contain initialized `.ccw/`
   local state.
3. The `files` table is extended additively from the Phase 1 placeholder schema
   so already-bootstrapped repos do not require a destructive re-init.
4. The persisted `files` rows include these fields:
   - `path` as a repo-relative POSIX-style path
   - `content_hash` as a SHA-256 hex digest of file bytes
   - `size_bytes` as the current file size in bytes
   - `language` as a deterministic label from file name or extension
5. Each index run writes a full deterministic snapshot of the current repo file
   inventory into `files` and removes rows for files that no longer exist.
6. The slice excludes `.ccw/`, `.git/`, and symlinks rather than following or
   indexing them.
7. This slice does not populate `symbols`, `edges`, `facts`, or `episodes`.

## Proposed modules or surfaces

- `ccw.cli` - command parsing and dispatch for `ccw index`
- `ccw.init` - shared repo-target validation and runtime-path helpers
- `ccw.schema` - additive `files` table schema expansion for shipped repos
- `ccw.index` - deterministic repo walk, hashing, language detection, and file
  inventory orchestration
- `tests/test_cli_index.py` - fixture-backed indexing behavior through the
  public CLI

## Validation

- CLI test: `ccw index` fails with a stable error when `.ccw/` local state is
  missing
- CLI test: `ccw index [path]` accepts an explicit target path from outside the
  repo root being indexed
- CLI test: first index run populates `files` with the expected rows for a
  fixture repo
- CLI test: rerunning `ccw index` without repo changes preserves the same file
  inventory
- CLI test: editing a file changes its stored hash and size deterministically
- CLI test: deleting a file removes its row from `files`
- CLI test: `.ccw/`, `.git/`, and symlinks are not indexed
- Project validation: `python -m unittest`

## Premortem-driven controls

- Keep the `files` schema intentionally minimal so later symbol and ranking work
  can extend it additively instead of inheriting guessed fields.
- Reconcile the full table transactionally on each run so refresh behavior does
  not depend on clocks or partial updates.
- Persist repo-relative POSIX paths only so SQLite output stays inspectable and
  portable across machines.
- Freeze the exclusion set explicitly in this slice instead of accidentally
  growing a broad ignore subsystem.
- Skip symlinks in this slice to avoid recursive or out-of-repo reads.

## Done when

- A contributor can run `ccw init` and then `ccw index`
- The `files` table contains deterministic file inventory rows for the repo
- Re-indexing reflects changed and deleted files deterministically
- `.ccw/`, `.git/`, and symlinks are excluded from inventory
- Tests cover happy path, rerun stability, failure behavior, and refresh
  behavior

## Implementation status

- `ccw index [path]` now walks the repo deterministically and refreshes the
  `files` table from the public CLI
- The `files` table stores repo-relative path, SHA-256 content hash,
  `size_bytes`, and language labels for indexed files
- Re-indexing performs a full table refresh so changed and deleted files are
  reflected deterministically
- `.ccw/`, `.git/`, and symlinks are excluded from the inventory walk
- The shipped Phase 1 placeholder `files` table is upgraded additively when the
  index command touches an already-bootstrapped repo
- Validation passes with `python -m unittest` from the repo root

## Follow-on slice

After this slice, the next Phase 2 work is symbol extraction and edge
persistence on top of the deterministic file inventory substrate.
