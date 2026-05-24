# ccw

CCW is a deterministic context compiler for small-window coding models.

It indexes a repository, stores explicit project facts and episodes, compiles
task-scoped context to a fixed budget, and can optionally compress that context
with an LLM after deterministic assembly.

The companion orchestration repo for multi-harness workflows, Conductor
packaging, and any optional portable brain behavior lives separately in
`../ccw-stack`.

## Target CLI

```bash
ccw init
ccw index .
ccw compile --task "fix auth bug" --budget 4000
ccw validate .ccw/compiled/latest.md
ccw update --run ./conductor/runs/latest
```

## Core idea

- `Microsoft Conductor` is the deterministic workflow orchestrator.
- `CCW` is the deterministic context compiler and post-run update layer.
- `CCW Stack` is the companion orchestration repo for harness adapters,
  workflow packaging, and optional portable brain behavior.
- Small or free models are the execution backends that consume CCW artifacts.

## Key docs

- `wiki/user/architecture/ccw-mvp-prd.md`
- `wiki/user/ops/plans/development-plan.md`
- `wiki/user/ops/specs/phase-3c-deterministic-task-classifier-spec.md`
- `wiki/user/ops/specs/phase-3b-explicit-episodes-write-path-spec.md`
- `wiki/user/ops/specs/phase-3a-explicit-facts-write-path-spec.md`
- `wiki/user/ops/specs/phase-2c-deterministic-multi-language-graph-spec.md`
- `wiki/user/architecture/ccw-stack-companion-boundary.md`
- `wiki/user/architecture/sdlc/agentic-development-workflow.md`
- `docs/adr/0001-use-microsoft-conductor-as-the-orchestrator.md`
- `docs/adr/0002-keep-orchestration-and-portable-brain-in-ccw-stack.md`

## Current status

This repo now ships `ccw init` for deterministic local-state bootstrap and
`ccw index` for deterministic file inventory, multi-language symbols, basic
edges, document artifacts, git signals, and snapshot output into
`.ccw/index.sqlite` and `.ccw/snapshots/index.json`, plus `ccw facts add`,
`ccw episodes add` for explicit append-only project memory, and `ccw classify`
for deterministic task classification. The active slice remains Phase 3C
deterministic task classification until the next Phase 3 spec is frozen.
