# Change log

Append-only record of vault changes. Each entry starts with
`- <kind> :: [[page]] - short note` under a date header.

## 2026-05-23

- architecture :: [[development-plan]] - marked Phase 1A runtime bootstrap complete and advanced the next active slice to Phase 1B schema bootstrap
- architecture :: [[phase-1-deterministic-compiler-spec]] - recorded the shipped Phase 1A runtime bootstrap surfaces, validations, and explicit no-SQLite behavior
- architecture :: [[phase-1-deterministic-compiler-spec]] - narrowed the active Phase 1 slice to installable CLI and `.ccw/` runtime bootstrap, deferring SQLite schema bootstrap after a premortem surfaced data-model coupling risk
- architecture :: [[development-plan]] - split Phase 1 into next runtime-bootstrap work and follow-on schema-bootstrap work, with explicit failure-behavior acceptance criteria
- architecture :: [[ccw-stack-companion-boundary]] - documented the ownership split between CCW core and the sibling `ccw-stack` repo for orchestration, harness adapters, and optional portable brain behavior
- architecture :: [[ccw-mvp-prd]] - clarified that multi-harness orchestration and optional portable brain work live outside CCW core in `ccw-stack`
- architecture :: [[development-plan]] - clarified that the Conductor-facing compiler contract should support the companion `ccw-stack` repo
- architecture :: [[agentic-development-workflow]] - removed leftover `wikiagent` terminology like "capability-centered slice" from the CCW workflow and agent prompts, while keeping the three-agent structure intact
- architecture :: [[agentic-development-workflow]] - simplified the opencode workflow to three custom agents only: `capability-plan-manager`, `capability-developer`, and `capability-reviewer`, and removed the extra specialist prompts
- architecture :: [[ccw-mvp-prd]] - created the initial local PRD for CCW's deterministic context compiler, Conductor integration, and optional compression layer
- architecture :: [[development-plan]] - created the phased roadmap from repo scaffold through indexing, compilation, Conductor integration, and post-run updates
- architecture :: [[phase-1-deterministic-compiler-spec]] - created the first execution spec for CLI bootstrap, `.ccw/` initialization, and SQLite schema setup
- architecture :: [[agentic-development-workflow]] - adapted the planning and delivery workflow for CCW's PRD, roadmap, ADR, and slice-spec flow
- architecture :: [[index]] - added the initial architecture index and template references
- architecture :: [[phase-1-deterministic-compiler-spec]] - advanced the active slice spec to Phase 1B schema bootstrap and recorded the shipped SQLite bootstrap contract and follow-on indexing direction
- architecture :: [[development-plan]] - marked Phase 1 schema bootstrap complete and advanced the next active slice to Phase 2 deterministic repo inventory and indexing
- architecture :: [[phase-1-deterministic-compiler-spec]] - recorded `python -m unittest` as the passing Phase 1B validation command after making default unittest discovery cover the repo suite
