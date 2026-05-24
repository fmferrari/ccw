# Change log

Append-only record of vault changes. Each entry starts with
`- <kind> :: [[page]] - short note` under a date header.

## 2026-05-25

- architecture :: [[phase-4-context-compiler-spec]] — created and shipped the Phase 4 contract for deterministic context compilation, ranking, snippet extraction, markdown rendering, `ccw compile`, `ccw validate`, and golden tests; frozen after premortem with substring-prefix ranking, I/O perf guard, budget-display calibration, and `compilations` schema aligned to existing patterns
- architecture :: [[development-plan]] — advanced Phase 4 as the active slice, archived Phase 3D, and decomposed Phase 4 into five work packets (A-E) with explicit dependencies
- architecture :: [[phase-3d-recipe-and-budget-spec]] — archived the completed Phase 3D recipe-and-budget spec after promoting Phase 4 as the active slice spec
- architecture :: [[index]] — advanced the wiki index to the active Phase 4 context-compiler spec and archived the completed Phase 3D recipe-and-budget spec entry
- architecture :: [[architecture/sdlc/agentic-development-workflow]] — advanced the workflow artifact reference from the completed Phase 3D recipe-and-budget spec to the active Phase 4 context-compiler spec
- architecture :: [[phase-4-context-compiler-spec]] — implemented all 5 Phase 4 work packets (A-E): ranking, snippets, composition, markdown renderer, `ccw compile` CLI, `ccw validate` CLI, compilations schema, golden tests, perf guard; 23 new tests, 102 total
- architecture :: [[development-plan]] — marked all Phase 4 work packets complete, advanced to Phase 5 follow-on

- architecture :: [[phase-3c-deterministic-task-classifier-spec]] - created and shipped the Phase 3C contract for deterministic keyword-based task classification, classification-row persistence in the `classifications` table, additive placeholder-table upgrade behavior, tie-breaking by definition-order priority with implementation default, and stable validation for `ccw classify`
- architecture :: [[development-plan]] - marked Phase 3C deterministic task classifier complete, recorded `python -m unittest` as the passing validation command, and left compile recipes and budget allocation as the next Phase 3 follow-on work
- architecture :: [[phase-3b-explicit-episodes-write-path-spec]] - archived the completed Phase 3B episodes-write spec after promoting Phase 3C as the active slice spec
- architecture :: [[index]] - advanced the wiki index to the active Phase 3C task-classifier spec and archived the completed Phase 3B episodes-write spec entry
- architecture :: [[architecture/sdlc/agentic-development-workflow]] - advanced the workflow artifact reference from the archived Phase 3B episodes-write spec to the active Phase 3C task-classifier spec (via AGENTS.md update)
- architecture :: [[phase-3d-recipe-and-budget-spec]] - created and shipped the Phase 3D contract for deterministic compile-recipe definitions and budget-allocation algorithm with `Recipe`/`Section` dataclasses, per-mode recipe definitions (bugfix 6k, implementation 8k, review 8k, refactor 10k), proportional budget distribution with minimum floor clamping and remainder-by-weight, case-insensitive mode lookup falling back to implementation, and stable validation for `get_recipe()` and `allocate_budget()`
- architecture :: [[development-plan]] - marked Phase 3D compile recipes and budget allocation complete, recorded `python -m unittest` (78 tests) as the passing validation command, and advanced the next follow-on work to Phase 4 context compiler and validator
- architecture :: [[phase-3c-deterministic-task-classifier-spec]] - archived the completed Phase 3C task classifier spec after promoting Phase 3D as the active slice spec
- architecture :: [[index]] - advanced the wiki index to the active Phase 3D recipe-and-budget spec and archived the completed Phase 3C task-classifier spec entry

## 2026-05-24

- ops :: [[index]] - restructured wiki/user/ to separate architecture (code and sdlc subfolders) from operations (plans, specs, adr subfolders) following the wikiagent pattern
- ops :: [[ops/plans/index]] - moved development-plan to ops/plans/
- ops :: [[ops/specs/index]] - moved all phase specs to ops/specs/
- architecture :: [[architecture/sdlc/index]] - moved agentic-development-workflow to architecture/sdlc/
- architecture :: [[architecture/code/index]] - created code architecture subfolder for PRD and companion boundary docs
- architecture :: [[phase-3a-explicit-facts-write-path-spec]] - created and then shipped the Phase 3A contract for explicit append-only facts, placeholder-table upgrade behavior, and stable validation for `ccw facts add`
- architecture :: [[development-plan]] - marked Phase 3A explicit facts write path complete, recorded `python -m unittest` as the passing validation command, and left episodes plus task routing as the next Phase 3 follow-on work
- architecture :: [[phase-2c-deterministic-multi-language-graph-spec]] - archived the completed Phase 2 closeout spec after promoting Phase 3A as the active slice spec
- architecture :: [[index]] - advanced the wiki index to the active Phase 3A explicit-facts spec and archived the completed Phase 2 closeout spec entry
- architecture :: [[architecture/sdlc/agentic-development-workflow]] - advanced the workflow artifact reference from the completed Phase 2C closeout spec to the active Phase 3A explicit-facts spec
- architecture :: [[architecture/sdlc/agentic-development-workflow]] - aligned opencode agent context references to the moved SDLC workflow path under `architecture/sdlc/`
- architecture :: [[phase-3b-explicit-episodes-write-path-spec]] - created and then shipped the Phase 3B contract for explicit append-only episodes, placeholder-table upgrade behavior, and stable validation for `ccw episodes add`
- architecture :: [[development-plan]] - marked Phase 3B explicit episodes write path complete, recorded `python -m unittest` as the passing validation command, and left task classification as the next Phase 3 follow-on work
- architecture :: [[phase-3a-explicit-facts-write-path-spec]] - archived the completed Phase 3A facts-write spec after promoting Phase 3B as the active slice spec
- architecture :: [[index]] - advanced the wiki index to the active Phase 3B explicit-episodes spec and archived the completed Phase 3A facts-write spec entry
- architecture :: [[architecture/sdlc/agentic-development-workflow]] - advanced the workflow artifact reference from the completed Phase 3A facts-write spec to the active Phase 3B explicit-episodes spec

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
- architecture :: [[phase-2a-deterministic-file-inventory-spec]] - created and then shipped the Phase 2A file-inventory contract for `ccw index`, deterministic `files` refresh, and placeholder-schema upgrade behavior
- architecture :: [[development-plan]] - marked Phase 2A deterministic file inventory complete, recorded `python -m unittest` as the passing validation command, and left symbol extraction as the next Phase 2 follow-on work
- architecture :: [[phase-1-deterministic-compiler-spec]] - archived the completed Phase 1B schema bootstrap spec after promoting Phase 2A as the active slice spec
- architecture :: [[index]] - advanced the architecture index to the active Phase 2A file-inventory slice spec and archived the completed Phase 1 spec entry
- architecture :: [[agentic-development-workflow]] - generalized the workflow artifact role from a single next-slice spec to the active slice spec used for implementation and closeout
- architecture :: [[phase-2b-python-top-level-symbol-inventory-spec]] - created and then shipped the Phase 2B contract for Python top-level symbol extraction, placeholder-schema upgrade behavior, and syntax-failure rollback during `ccw index`
- architecture :: [[development-plan]] - marked Phase 2B Python top-level symbol inventory complete, recorded `python -m unittest` as the passing validation command, and left Python imports and edges as the next Phase 2 follow-on work
- architecture :: [[phase-2a-deterministic-file-inventory-spec]] - archived the completed Phase 2A file-inventory spec after promoting Phase 2B as the active slice spec
- architecture :: [[index]] - advanced the architecture index to the active Phase 2B Python symbol-inventory slice spec and archived the completed Phase 2A spec entry
- architecture :: [[agentic-development-workflow]] - advanced the workflow artifact reference from the archived Phase 2A file-inventory spec to the active Phase 2B Python symbol-inventory spec
- architecture :: [[phase-2c-deterministic-multi-language-graph-spec]] - created and then shipped the Phase 2C contract for deterministic multi-language symbols, edges, document artifacts, git signals, test mapping, and snapshot output during `ccw index`
- architecture :: [[development-plan]] - marked all remaining Phase 2 roadmap items complete, recorded `python -m unittest` as the passing validation command, and advanced the next follow-on work to Phase 3 explicit memory and task recipes
- architecture :: [[phase-2b-python-top-level-symbol-inventory-spec]] - archived the completed Phase 2B symbol-inventory spec after promoting Phase 2C as the active Phase 2 closeout slice
- architecture :: [[index]] - advanced the architecture index to the active Phase 2C closeout spec and archived the completed Phase 2B spec entry
- architecture :: [[agentic-development-workflow]] - advanced the workflow artifact reference from the archived Phase 2B symbol-inventory spec to the active Phase 2C closeout spec
- architecture :: [[phase-2c-deterministic-multi-language-graph-spec]] - archived the completed Phase 2 closeout spec while Phase 3 slice planning remains unfrozen
- architecture :: [[development-plan]] - clarified that Phase 2 is complete, Phase 2C is the latest completed slice spec, and the next Phase 3 spec is not yet frozen
- architecture :: [[agentic-development-workflow]] - clarified that Phase 2C is the latest completed slice contract until a new active slice is frozen
