---
type: architecture
tags: [architecture, spec, slice, session, portability]
created: 2026-05-25
updated: 2026-05-25
status: active
---

# Phase 5B - Portable session bundle spec

## Purpose

Ship a provider- and harness-independent session-bundle contract so a compiled
context artifact is clearly consumable by an execution model on a first or
later turn without re-gathering repository context.

This slice should keep `ccw compile` as the source of truth for compiled
context while adding a portable handoff layer in CCW itself. Provider-specific
attachment and session-thread behavior stay in `ccw-stack`.

## In scope

### Session-bundle writer and CLI surface
- Add `src/ccw/session.py`
- Add `ccw session prepare --task <description> [--budget <N>] [--mode <mode>] [--out-dir <path>] [path]`
- Reuse existing compile logic rather than forking ranking, snippet extraction,
  or artifact rendering
- Default output to `.ccw/session/latest/`

### Portable file contract
- Emit `SESSION.md` as the top-level model-facing file
- Emit `compiled-context.md` as the exact compiled artifact backing the session
- Emit `session.json` as machine-readable metadata
- `SESSION.md` must make these points explicit in plain language:
  - this bundle is the grounded context for the named task
  - the model should use this compiled context before re-gathering repo context
  - if the task or repo state no longer matches the bundle metadata, request a
    refresh instead of silently trusting stale context

### Freshness and provenance contract
- Persist task description, resolved mode, budget, created-at timestamp,
  compiled-artifact path, and index hash in `session.json`
- Keep paths repo-relative or bundle-relative so the contract stays portable
- Add bundle validation through `ccw session validate <path>`
- Validation must confirm required files exist and the bundle metadata agrees
  with the referenced compiled artifact

### Tests and docs
- Add regression coverage for default latest output, explicit output dirs,
  bundle validation, and model-facing session instructions
- Update `README.md` with harness-agnostic file consumption examples
- Advance roadmap, boundary, and workflow docs to this slice

## Explicit non-goals

- Provider-specific role schemas, message envelopes, or chat API payloads
- Automatic bundle injection into a provider session
- Portable-brain memory or long-lived cross-run lessons beyond the compiled
  artifact itself
- Conductor workflow scaffolding in this packet
- Post-run memory updates in this packet

## Modules and files

```text
src/ccw/session.py        - session-bundle writer and validator helpers
src/ccw/cli.py            - `ccw session prepare|validate` surface
src/ccw/compile.py        - reuse compiled-artifact generation where needed
tests/test_session.py     - session-bundle unit coverage
tests/test_cli_session.py - CLI regression coverage
README.md                 - portable session-bundle usage examples
```

## Work packets

### Packet B1 - Session bundle writer and layout

- Owner: `capability-developer`
- Owned surfaces: `src/ccw/session.py`, `src/ccw/cli.py`, reusable helpers in
  `src/ccw/compile.py`, `tests/test_cli_session.py`
- Dependencies: existing `ccw compile` behavior only
- Frozen assumptions:
  - `.ccw/session/latest/` is the default stable output directory
  - `SESSION.md`, `compiled-context.md`, and `session.json` are the required
    bundle files
  - compiled-context rendering stays sourced from existing compile logic rather
    than a second renderer
- Explicit non-goals:
  - provider-specific prompt roles or message envelopes
  - bundle validation logic beyond presence and write correctness
- Validation target:
  - `ccw session prepare` writes the required files to the default and explicit
    output directories
  - `compiled-context.md` stays structurally valid under existing `ccw validate`
- Artifact updates on completion: [[development-plan]],
  [[phase-5b-portable-session-bundle-spec]], `wiki/user/log.md`
- Review lens: contract reuse, stable output paths, and no duplicate compiler
  semantics

### Packet B2 - Freshness metadata and bundle validation

- Owner: `capability-developer`
- Owned surfaces: `src/ccw/session.py`, `src/ccw/cli.py`,
  `tests/test_session.py`, `tests/test_cli_session.py`
- Dependencies: Packet B1 file layout and metadata shape
- Frozen assumptions:
  - `session.json` stores task description, mode, budget, created-at, index
    hash, and compiled-artifact reference
  - `ccw session validate` checks required files plus metadata agreement with the
    referenced compiled artifact
- Explicit non-goals:
  - deciding when a harness should refresh or reuse a bundle at runtime
  - provider-side session caching rules
- Validation target:
  - validator fails on missing files, mismatched index hashes, and mismatched
    compiled-artifact metadata
  - validator succeeds on a freshly prepared bundle
- Artifact updates on completion: [[development-plan]],
  [[phase-5b-portable-session-bundle-spec]], `wiki/user/log.md`
- Review lens: provenance, stale-context tripwires, and deterministic failure
  behavior

### Packet B3 - Consumer guidance, docs, and regression coverage

- Owner: `capability-developer`
- Owned surfaces: `README.md`, `tests/test_session.py`,
  `tests/test_cli_session.py`
- Dependencies: Packets B1 and B2
- Frozen assumptions:
  - `SESSION.md` is the model-facing entry file for first-turn and later-turn
    consumers
  - examples stay harness-agnostic and file-based
- Explicit non-goals:
  - Conductor workflow scaffolding
  - provider- or harness-specific adapter examples
- Validation target:
  - tests assert `SESSION.md` clearly instructs consumers to use compiled
    context first and request refresh on mismatch
  - README examples show plain file consumption without MCP or provider APIs
- Artifact updates on completion: [[development-plan]],
  [[phase-5b-portable-session-bundle-spec]], `wiki/user/log.md`
- Review lens: clarity for downstream agents, no chunk-dump regression, and doc
  accuracy against the shipped contract

## Premortem summary

Failure headline:

- Two weeks after shipping, agents still re-gather repo context because the
  bundle is ambiguous, stale, or tied to one harness.

Top risks and controls:

- Ambiguous model-facing file: require `SESSION.md` to state that it is the
  grounded task context and should be used before re-gathering.
- Harness-specific drift: keep the bundle file-only and ban provider role or API
  semantics from the contract.
- Silent staleness: persist index hash and task metadata, then validate bundle
  consistency explicitly.
- Duplicate compiler logic: route session preparation through the existing
  compile path rather than a parallel renderer.

Go recommendation:

- Proceed, but keep the slice narrow: portable file contract now, Conductor and
  provider adapters later.

## Validation

- `python -m unittest`
- Focus checks:
  - `ccw session prepare` writes `SESSION.md`, `compiled-context.md`, and
    `session.json` under the expected directory
  - `SESSION.md` clearly instructs model consumers to use compiled context first
    and request refresh on task or repo mismatch
  - `ccw session validate` fails on missing files, mismatched index hashes, or
    mismatched artifact metadata
  - session preparation reuses the same compiled-context semantics as `ccw compile`
