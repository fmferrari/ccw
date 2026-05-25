---
type: architecture
tags: [architecture, spec, slice, conductor, workflow]
created: 2026-05-25
updated: 2026-05-25
status: active
---

# Phase 5C — Conductor workflow scaffold spec

## Purpose

Ship a `ccw conductor init` command that scaffolds a sample workflow
directory showing how the deterministic CCW pipeline composes as script
steps inside Microsoft Conductor or any workflow orchestrator.

This packet stays within the companion boundary: CCW provides the template
and CLI; actual Conductor workflow definitions, harness adapters, and
orchestrator-specific packaging live in `ccw-stack`.

## In scope

### CLI command
- Add `ccw conductor init [--out <path>]` to `src/ccw/conductor.py`
- Default output places the scaffold in the current directory

### Scaffold layout
- `ccw-code-task/README.md` — explains each pipeline step, the consumption
  contract, and the companion boundary
- `ccw-code-task/bin/run.sh` — shell script demonstrating the full pipeline:
  init → index → classify → compile → session prepare → session validate

### Tests
- Default location scaffold produces expected files and content
- Explicit `--out` path is respected
- Idempotency: repeated `conductor init` does not fail

### Docs
- README section for `ccw conductor init` with usage examples
- Development plan updated to mark Packet C complete

## Explicit non-goals

- Conductor-specific workflow YAML/JSON definitions (belongs in ccw-stack)
- Conductor SDK imports or runtime dependencies
- Harness-specific adapter or session-attachment logic
- Post-run update behavior (Phase 5D)
- Compression (Phase 6)

## Work packets

All three packets are implemented and validated.

### Packet C1 — CLI scaffold command

- Owner: `capability-developer`
- Owned surfaces: `src/ccw/conductor.py`, `src/ccw/cli.py`
- Dependencies: existing `src/ccw/` package structure
- Generated files:
  - `ccw-code-task/README.md` — step explanation and companion boundary
  - `ccw-code-task/bin/run.sh` — full pipeline demonstration script
- Validation target: `ccw conductor init` writes expected files to the
  default and explicit output directories

### Packet C2 — Tests

- Owner: `capability-developer`
- Owned surfaces: `tests/test_cli_conductor.py`
- Dependencies: Packet C1
- Validation target: 3 tests pass (default location, explicit path,
  idempotency)

### Packet C3 — README and plan updates

- Owner: `capability-developer`
- Owned surfaces: `README.md`, `wiki/user/ops/plans/development-plan.md`,
  `wiki/user/log.md`, `wiki/user/index.md`
- Dependencies: Packets C1 and C2

## Validation

- `python -m unittest` — 138 tests pass
- `ccw conductor init` produces a valid scaffold with README and bin/run.sh
- `ccw conductor init --out <path>` respects the explicit output directory
- Repeated `ccw conductor init` is idempotent
