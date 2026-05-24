# AGENTS.md - root

Contract for coding agents working in this repo.
Every subdirectory may have its own `AGENTS.md` that narrows these rules. Read
those files before editing inside that subtree.

## Read These First (every session)

1. `wiki/AGENTS.md` - project knowledge and retrieval contract.
2. `wiki/user/index.md` - canonical architecture index.
3. Last ~30 lines of `wiki/user/log.md` - recent design and planning changes.
4. `CONTEXT.md` - canonical vocabulary for CCW, compiled context, facts,
   episodes, and Conductor integration.

Only then open `README.md` or deeper architecture docs as needed.

## Non-negotiables

1. **Wiki-first project memory**: durable architecture, roadmap, and decision
   history live under `wiki/user/`, following the Karpathy LLM-Wiki pattern.
2. **Deterministic first**: indexing, memory, compile, validate, and update
   paths must work without an LLM. The LLM layer is optional compression only.
3. **No vector store in the MVP critical path**: retrieval should come from
   deterministic indexing, search, ranking, and explicit facts.
4. **Keep orchestration out of core**: harness adapters, workflow packaging,
   and any optional portable brain belong in the companion `ccw-stack` repo,
   not in CCW core.
5. **Real dates only**: never invent `created`, `updated`, or log dates.
6. **Per-directory AGENTS.md is law**: subdirectory rules override this file
   for files inside that subtree.
7. **Keep docs aligned with delivery**: when PRD, roadmap, slice, or ADR
   assumptions change, update the relevant artifact and the wiki log in the
   same slice.

## Product Shape

- `Microsoft Conductor` is the workflow orchestrator.
- `CCW` is the deterministic context compiler and post-run update engine.
- `CCW Stack` is the companion repo for orchestration, harness adapters, and
  optional portable brain behavior.
- Small-window or free models are the execution backends that consume CCW
  artifacts.
- `.ccw/` is runtime state, not source-of-truth project documentation.

## Repo Conventions

- Prefer Python for the initial CLI, indexer, compiler, and storage layers
  unless a document in `wiki/user/architecture/` says otherwise.
- Keep output artifacts inspectable: stable schemas, hashes, file paths,
  symbol names, and explicit constraints beat prose.
- If you add an LLM-assisted step, define the deterministic validation contract
  alongside it.
- Keep new documents small and purpose-specific: PRD, roadmap, slice spec, and
  ADR are separate artifacts.

## Where To Look Next

- Product intent: `wiki/user/architecture/ccw-mvp-prd.md`
- Roadmap: `wiki/user/ops/plans/development-plan.md`
- Active slice spec: `wiki/user/ops/specs/phase-3b-explicit-episodes-write-path-spec.md`
- Companion boundary: `wiki/user/architecture/ccw-stack-companion-boundary.md`
- Delivery workflow: `wiki/user/architecture/sdlc/agentic-development-workflow.md`
- Hard decision log: `docs/adr/`
