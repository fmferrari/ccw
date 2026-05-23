---
type: architecture
tags: [architecture, boundary, integration]
created: 2026-05-23
updated: 2026-05-23
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
- post-run compiler updates
- `.ccw/` runtime state

## CCW Stack owns

- Conductor workflow packaging
- harness adapters and bridges
- planner/implementer/reviewer run contracts
- run manifests and orchestration diagnostics
- optional portable brain behavior
- `.ccw-stack/` runtime state

## CCW should not do

- build its own harness adapter manager
- absorb optional portable brain or lesson-review scope
- hide workflow logic inside compiler code paths
- become a general multi-harness runtime framework

## CCW should expose stable surfaces for CCW Stack

- `ccw init`
- `ccw index`
- `ccw compile`
- `ccw validate`
- `ccw update`

CCW Stack should integrate through those explicit CLI and artifact contracts
rather than by copying compiler internals.

## Why this split exists

The compiler and the orchestration layer solve different problems. CCW stays
boring and deterministic about project context. CCW Stack stays boring and
deterministic about workflow coordination across harnesses. Keeping them
separate avoids turning CCW into a portability shell, installer, or workflow
engine.
