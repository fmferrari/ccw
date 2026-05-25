---
type: architecture
tags: [architecture, plan, iterations]
created: 2026-05-23
updated: 2026-05-25
status: active
---

# Development plan

Roadmap from an empty repo to a working deterministic context compiler that can
feed small-window execution models through Microsoft Conductor.

The first job is not clever retrieval. It is creating a clean artifact flow:
repo scaffold, explicit vocabulary, PRD, roadmap, ADRs, slice specs, and
opencode workflow assets. After that, implementation should move from local CLI
bootstrap to deterministic indexing, then to context compilation, validation,
Conductor integration, and finally optional compression plus post-run memory
updates.

## Phase 0 - Repo and workflow scaffold (completed)

Goal: give the repo a repeatable planning and execution discipline for CCW.

- [x] Create root `AGENTS.md`, `wiki/AGENTS.md`, and `CONTEXT.md`
- [x] Create a local PRD, roadmap, next-slice spec, and agentic workflow doc
- [x] Import opencode agents and skills from the reference repo and retarget them to CCW
- [x] Document ADR and roadmap conventions with example templates
- [x] Record the first hard architecture decision in `docs/adr/`
- [x] Freeze the ownership boundary between CCW core and the sibling `ccw-stack` orchestration repo

Deliverable: future work in this repo can be planned and executed through local
artifacts instead of ad hoc chat context.

## Phase 1 - CLI scaffold and local state bootstrap (completed)

Goal: ship an installable `ccw` CLI with `ccw init` and deterministic local
state bootstrap under `.ccw/`.

- [x] Slice 1A: create the Python package and installable `ccw` entrypoint
- [x] Slice 1A: implement `ccw init` to create `.ccw/`, `compiled/`, `snapshots/`, and `.ccw/config.yaml`
- [x] Slice 1A: add CLI tests for initialization, rerun safety, invalid-target failure, config creation, non-writable-path failure, and no pre-schema SQLite bootstrap
- [x] Slice 1B (follow-on): bootstrap the SQLite schema for files, symbols, edges, facts, and episodes
- [x] Slice 1B (follow-on): add schema creation tests after the runtime layout contract is stable

Next slice rationale:

- Freeze the installable CLI and repo-local runtime layout before binding the implementation to an unfinished SQLite data model.
- Keep invalid-path and idempotency behavior explicit now so later schema work cannot quietly redefine the `ccw init` contract.

Acceptance criteria:

- The installable `ccw` CLI can materialize the runtime layout and default config for a new repo without manual file creation
- `ccw init` is idempotent
- Invalid target paths or non-writable locations fail loudly
- A new repo can create the full local state layout without manual SQL or file
  creation
- The CLI surface is test-covered and installable from the repo

Deliverable: a user can run `ccw init` and get a valid deterministic local
state scaffold, including SQLite schema bootstrap under `.ccw/index.sqlite`.

Current status:

- Phase 1 is implemented and validated.
- Validation command: `python -m unittest`
- The next active slice is Phase 2 deterministic repo inventory and indexing,
  starting with file metadata, hashes, and language persistence in `files`.

## Phase 2 - Deterministic repo inventory and indexing (completed)

Goal: build the deterministic repository index that powers later compilation.

- [x] Slice 2A: implement `ccw index [path]` for deterministic repo walking and full `files` table refresh
- [x] Slice 2A: persist repo-relative paths, SHA-256 content hashes, file sizes, and detected language in `files`
- [x] Slice 2A: fail loudly when local `.ccw/` state is missing and exclude `.ccw/`, `.git/`, and symlinks from inventory
- [x] Slice 2A: add fixture-backed tests for initial indexing, rerun stability, changed files, deleted files, explicit target paths, and missing-init failure
- [x] Slice 2B: extract top-level Python `class`, `def`, and `async def` declarations during `ccw index`
- [x] Slice 2B: persist deterministic symbol rows with file path, symbol name, kind, and source-line anchors in `symbols`
- [x] Slice 2B: fail loudly on invalid Python syntax and leave previous indexed state intact
- [x] Slice 2B: add CLI tests for symbol extraction, rerun stability, changed files, deleted files, and placeholder-schema upgrade behavior
- [x] Slice 2C: extract deterministic imports, exports, and basic local edges for Python and TypeScript/JavaScript
- [x] Slice 2C: index Markdown and JSON/YAML documents as searchable project artifacts
- [x] Slice 2C: capture nullable git recency and ownership signals per indexed file
- [x] Slice 2C: map tests to source files when naming or local-import signals are unambiguous
- [x] Slice 2C: add fixture-backed regression coverage for mixed-language indexing output and schema upgrades

Acceptance criteria:

- Re-indexing updates changed files deterministically
- Supported languages produce stable metadata and symbol output
- Index results are inspectable through SQLite and artifact files

Deliverable: `ccw index .` produces the deterministic substrate needed for
context compilation.

Current status:

- Phase 2 is implemented and validated through file inventory, multi-language symbols, basic edges, document artifacts, git ranking signals, test mapping, and deterministic snapshot output.
- Validation command: `python -m unittest`
- The latest completed slice spec is [[phase-2c-deterministic-multi-language-graph-spec]].
- The next Phase 3 memory and recipe slice spec is not frozen yet.
- Follow-on work: begin Phase 3 explicit memory and task recipes on top of the now-inspectable Phase 2 index substrate.

## Phase 3 - Explicit memory and task recipes (current)

Goal: add deterministic project memory and task classification.

- [x] Slice 3A: implement append-only facts persistence and `ccw facts add`
- [x] Slice 3A: freeze the first shipped fact record shape and additive upgrade path for the placeholder `facts` table
- [x] Slice 3A: reject empty or unsupported fact inputs while preserving append-only behavior
- [x] Slice 3A: add CLI tests for fact persistence, repeated appends, missing-init failure, and placeholder-table upgrade behavior
- [x] Slice 3B: implement append-only episodes persistence and `ccw episodes add`
- [x] Slice 3B: freeze the first shipped episode record shape and additive upgrade path for the placeholder `episodes` table
- [x] Slice 3B: require explicit summary plus touched files while preserving append-only behavior
- [x] Slice 3B: add CLI tests for episode persistence, repeated appends, missing-init failure, and placeholder-table upgrade behavior
- [x] Slice 3C: implement deterministic task classifier for bug fix, implementation, review, and refactor modes
- [x] Slice 3C: freeze the first shipped classification record shape and additive upgrade path for the placeholder `classifications` table
- [x] Slice 3C: classify by keyword matching with tie-breaking and implementation default
- [x] Slice 3C: add CLI tests for all four modes, default mode, append-only, missing-init failure, empty-text rejection, and placeholder-table upgrade behavior
- [x] Define compile recipes and budget allocation by task mode
- [x] Add tests for compile recipes and budget allocation

Acceptance criteria:

- Facts remain explicit and low-inference
- Task classification stays deterministic and explainable
- Recipe selection can be reproduced from input text alone

Deliverable: compile behavior can depend on explicit project memory, a stable
task mode, and a deterministic recipe with per-section budget allocation.

Current status:

- Phase 3 is fully implemented and validated: fact persistence, episode persistence,
  deterministic task classification, compile recipes, and budget allocation.
- Phase 3D compile recipes and budget allocation is implemented and validated.
- Validation command: `python -m unittest` (78 tests)
- Phase 3D spec is now archived as a completed slice.
- The active slice spec is now [[phase-4-context-compiler-spec]].
- Follow-on work: begin Phase 4 implementation starting with compiler core (Packet A).

## Phase 4 - Context compiler and validator (current)

Goal: generate inspectable task-scoped context artifacts under a strict budget.

- [x] Packet A: compiler core — dataclasses, ranking, snippets, composition
- [x] Packet B: markdown renderer for CompiledContext
- [x] Packet C: `ccw compile --task ... --budget ... --out ... --mode ...`
- [x] Packet D: `ccw validate <artifact>` CLI surface
- [x] Packet E: golden fixture tests for rendered output

Acceptance criteria:

- The compiled artifact includes task, project state, relevant files, symbol
  graph, snippets, and constraints
- Validation catches malformed or unsupported output
- Golden tests show stable output for fixture tasks

Deliverable: `ccw compile` produces a bounded, inspectable context artifact for
execution models.

Current status:

- All 5 Phase 4 work packets are implemented and validated.
- `rank_files()`: deterministic keyword-overlap + fuzzy prefix + symbol-name + git-freshness ranking
- `extract_snippets()`: line-anchored snippet extraction with symbol anchors and budget truncation
- `compile_context()`: composition of ranking, snippets, recipe, budget, facts, episodes, constraints
- `render_compiled_context()`: structured markdown with YAML frontmatter and estimated token footer
- `ccw compile --task ... --mode ... --budget ... --out ...`: full CLI wired through classify → recipe → budget → compile → render → write
- `ccw validate <path>`: frontmatter, section, and invented-path validation
- Golden tests: snapshot comparison + structural assertions
- Performance guard: compile_context completes in 0.038s on 200-file fixture (limit: 0.5s)
- Schema: `compilations` table added with additive optional-column pattern
- Validation command: `python -m unittest` (102 tests, 1 pre-existing fixture failure)
- New test files: `tests/test_compile.py` (15 tests), `tests/test_cli_compile.py` (10 tests)
- Active slice spec: [[phase-4-context-compiler-spec]] (frozen after premortem, now implemented)
- Follow-on work: formalize the compiler pass pipeline (Phase 4.5)

## Phase 4.5 - Explicit compiler pass pipeline (current)

Goal: Refactor `compile_context()` into an explicit pipeline of named compiler
passes with a formal intermediate representation (IR), so the "deterministic
context compiler" architecture matches the code structure.

- [ ] Packet A: Pass protocol, CompilationIR, pipeline runner
- [ ] Packet B: Refactor existing functions into Pass subclasses
- [ ] Packet C: Pipeline composition tests

Acceptance criteria:

- No behavioral change — identical input produces identical output
- All existing unit, CLI, and golden tests pass
- Performance guard still completes under 0.5s
- Pipeline runner adds negligible overhead

Deliverable: `compile_context()` delegates to a named pass pipeline. The code
structure matches the compiler narrative.

Current status:

- Phase 4.5 spec is frozen but not yet implemented.
- Active slice spec: [[phase-45-compiler-pipeline-spec]]
- Execution note: implement Packets A→B→C in order; no behavioral change means
  golden-test parity is the primary regression detector.
- Validation command: `python -m unittest`
- Follow-on work: resume Phase 5 workflow and agent integration surfaces.

## Phase 5 - Workflow and agent integration surfaces

Goal: make CCW a first-class deterministic step inside Conductor workflows and
MCP-capable agent clients.

- [x] Packet A: ship `ccw-mcp` as an installable MCP server entrypoint
- [x] Packet A: expose init, index, facts, episodes, classify, compile, and validate as structured MCP tools
- [x] Packet A: support explicit `target_path` inputs plus `CCW_TARGET_ROOT` for default external-repo targeting
- [x] Packet A: add regression tests and README examples for attaching CCW to another project as an MCP server
- [x] Packet B1: add `ccw session prepare` and write a stable `.ccw/session/latest/` bundle layout
- [x] Packet B1: emit a model-facing `SESSION.md`, `compiled-context.md`, and `session.json`
- [ ] Packet B2: include freshness and provenance metadata plus `ccw session validate`
- [ ] Packet B2: fail loudly on missing files, mismatched bundle metadata, or stale compiled-artifact references
- [ ] Packet B3: add regression tests and README examples for harness-agnostic session-bundle consumption
- [ ] Packet C: add `ccw conductor init` for a starter workflow scaffold
- [ ] Packet C: ship a sample `ccw-code-task` workflow that indexes and prepares a session bundle
- [ ] Packet C: support workflow-friendly file outputs for compiled artifacts and session bundles
- [ ] Packet D: add `ccw update --run ...` for post-run memory updates
- [ ] Packet D: document the integration path for the companion `ccw-stack` planner, implementer, and reviewer workflows

Acceptance criteria:

- An MCP client can call deterministic CCW operations against an external repo without shelling out
- A session bundle can be consumed as plain files without MCP, provider APIs, or harness-specific prompt schemas
- The top-level session file makes it obvious to a model that the compiled context should be used on a first or later turn
- A Conductor workflow can call `ccw index` and `ccw compile` directly
- The compiled artifact and session bundle are consumable by later workflow steps
- Post-run updates can attach the resulting decision and file-change evidence

Deliverable: CCW fits cleanly into deterministic workflows and MCP-capable
agents without becoming the workflow engine.

Current status:

- Phase 5A MCP server integration is implemented and validated.
- `ccw-mcp` exposes `init_repo`, `index_repo`, `record_fact`, `record_episode`,
  `classify_task`, `compile_task_context`, and `validate_compiled_artifact`
  over FastMCP.
- Relative MCP artifact paths resolve against the target repo root, using either
  explicit `target_path` arguments or `CCW_TARGET_ROOT`.
- Repository indexing now excludes common runtime/cache directories and
  `*.egg-info` metadata so MCP-driven indexing behaves on lived-in working
  trees, not just clean fixtures.
- Packet B1 session-bundle writer/layout is implemented and validated.
- Validation command: `python -m unittest`
- Active slice spec: [[phase-5b-portable-session-bundle-spec]]
- Execution note: treat the active slice as Packet B2 validator/freshness, then
  Packet B3 docs/tests before moving to Conductor workflow scaffolding.
- Follow-on work: portable session-bundle contract first, then Conductor
  workflow scaffolding, post-run `ccw update`, and configurable ignore-policy
  support beyond the built-in exclusions.

## Phase 6 - Optional compression and post-run learning

Goal: add the optional LLM optimization layer without weakening determinism.

- [ ] Implement `ccw compress --in ... --budget ...`
- [ ] Validate compressed artifacts for no new files, symbols, or constraints
- [ ] Extend `ccw update` with diff, tests, and decision inputs
- [ ] Add regression tests for compressor safety and update integrity

Acceptance criteria:

- Compression never becomes the source of truth
- Validation fails loud on invented facts or dropped required constraints
- Post-run updates enrich future compile steps with explicit episode history

Deliverable: CCW can optimize prompt size and learn from completed runs while
keeping deterministic truth boundaries intact.
