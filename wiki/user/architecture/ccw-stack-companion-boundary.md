---
type: architecture
tags: [architecture, boundary, integration]
created: 2026-05-23
updated: 2026-05-25
status: active
---

# CCW Stack companion boundary

This document freezes the ownership split between CCW core and the sibling
`ccw-stack` repo.

## CCW owns

- repository indexing
- explicit facts and episodes
- task classification for compile recipes
- compiled context assembly
- compiled-context validation
- provider- and harness-independent session handoff contract for compiled
  artifacts
- session-bundle file format, freshness metadata, and stable paths under
  `.ccw/`
- post-run compiler updates
- `.ccw/` runtime state

## CCW Stack owns

- Conductor workflow packaging
- harness adapters and bridges
- provider-specific session attachment and injection of CCW session bundles
- planner/implementer/reviewer run contracts
- run manifests and orchestration diagnostics
- optional portable brain behavior
- `.ccw-stack/` runtime state

## CCW should not do

- build its own harness adapter manager
- encode provider-specific message roles or session APIs into compiler outputs
- absorb optional portable brain or lesson-review scope
- hide workflow logic inside compiler code paths
- become a general multi-harness runtime framework

## CCW should expose stable surfaces for CCW Stack

- `ccw init`
- `ccw index`
- `ccw compile`
- `ccw validate`
- portable session-bundle files under `.ccw/` that clearly tell a model to use
  compiled context before re-gathering repo context
- `ccw update`

CCW Stack should integrate through those explicit CLI and artifact contracts
rather than by copying compiler internals.

## Boundary rule for compiled-artifact consumption

CCW owns the portable file contract that makes one compiled artifact obviously
consumable by an execution model on a first or later turn. That means the
top-level session file, the metadata needed to judge freshness, and the stable
on-disk layout belong in CCW because they are provider- and harness-independent.

CCW Stack owns how those files get attached, re-sent, cached, or threaded
through a specific provider or harness session. That keeps portability in the
artifact contract while keeping session APIs and orchestration details out of
CCW core.

## Why this split exists

The compiler and the orchestration layer solve different problems. CCW stays
boring and deterministic about project context. CCW Stack stays boring and
deterministic about workflow coordination across harnesses. Keeping them
separate avoids turning CCW into a portability shell, installer, or workflow
engine.
