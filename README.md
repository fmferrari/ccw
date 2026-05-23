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
- `wiki/user/architecture/development-plan.md`
- `wiki/user/architecture/phase-1-deterministic-compiler-spec.md`
- `wiki/user/architecture/ccw-stack-companion-boundary.md`
- `wiki/user/architecture/agentic-development-workflow.md`
- `docs/adr/0001-use-microsoft-conductor-as-the-orchestrator.md`
- `docs/adr/0002-keep-orchestration-and-portable-brain-in-ccw-stack.md`

## Current status

This repo currently contains the planning, workflow, and opencode scaffolding
for the compiler-first implementation slices, plus the documented boundary to
the sibling `ccw-stack` orchestration repo.
