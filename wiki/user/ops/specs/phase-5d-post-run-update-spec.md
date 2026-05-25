---
type: architecture
tags: [architecture, spec, slice, update, post-run]
created: 2026-05-25
updated: 2026-05-25
status: archived
---

# Phase 5D — Post-run update spec

## Purpose

Ship a `ccw update --run ...` command that records post-run memory updates
after a model or agent completes a task: re-index changed files, persist the
run as an episode, and optionally persist a decision fact.

This completes the last unfinished Packet D of Phase 5 in the
[[development-plan]].

## In scope

### CLI command
- Add `ccw update --run <summary> --touched-files <files> [--decision <text>]`
- Positional `path` (optional, default `.`) for the target repo

### Update module (`src/ccw/update.py`)
- `post_run_update(target, summary, touched_files, decision=None)` function
- Re-index the repository via `index_repository()` to capture file changes
- Record an episode via `add_episode()` with the summary and touched files
- Optionally record a decision fact via `add_fact()` with `kind="decision"`
- Fail fast: require initialized local state, reject empty summary, reject
  invalid touched files (delegates to `add_episode` validation)

### Tests
- `tests/test_cli_update.py` — CLI integration tests

### Documentation
- [[ccw-stack-companion-boundary]] — document the `ccw update` integration
  path for ccw-stack planner, implementer, and reviewer workflows

## Explicit non-goals

- Compression (Phase 6)
- Automatic mode classification for the update step
- Batch or multi-run update in one invocation
- Updating compiled artifacts inline (post-run update is about memory, not
  context artifacts)

## Work packets

### Packet D1 — update module and CLI

- Owned surfaces: `src/ccw/update.py`, `src/ccw/cli.py`
- Dependencies: existing `src/ccw/init.py`, `src/ccw/index.py`,
  `src/ccw/episodes.py`, `src/ccw/facts.py`
- Validation target: `ccw update --run "summary" --touched-files "a.py,b.py"`
  records an episode, re-indexes, and optionally records a decision fact

### Packet D2 — Tests

- Owned surfaces: `tests/test_cli_update.py`
- Dependencies: Packet D1
- Validation target: 6+ tests pass covering happy path, decision fact,
  missing-init failure, empty summary, invalid touched files, and
  placeholder-table upgrade behavior

### Packet D3 — Docs and plan updates

- Owned surfaces: `wiki/user/architecture/ccw-stack-companion-boundary.md`,
  `wiki/user/ops/plans/development-plan.md`, `wiki/user/log.md`
- Dependencies: Packets D1 and D2

## Validation

- `python -m unittest` — all tests pass
- `ccw update --run "summary" --touched-files "a.py,b.py"` records an episode
  and re-indexes the repo
- `ccw update --run "summary" --touched-files "a.py" --decision "Fixed it"`
  also records a decision fact
- Missing init, empty summary, and invalid touched files all fail loudly
