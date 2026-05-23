---
type: architecture
tags: [architecture, workflow, opencode, agents]
created: 2026-05-23
updated: 2026-05-23
status: active
---

# Agentic development workflow

## Purpose

This workflow defines how CCW design and implementation should move from fuzzy
architecture discussion to agent-executable delivery using opencode.

## Artifact roles

- [[ccw-mvp-prd]]: product intent, user stories, implementation decisions,
  testing decisions
- [[development-plan]]: multi-phase implementation roadmap and task checklist
- [[phase-2a-deterministic-file-inventory-spec]]: exact execution contract for the
  active slice being implemented or closed out
- `CONTEXT.md`: domain vocabulary and architectural language used consistently
  across the workflow
- `docs/adr/*`: hard-to-reverse architecture decisions
- `docs/templates/development-plan-template.md`: example roadmap structure
- `docs/templates/adr-template.md`: example ADR structure

These are not the same document:

- PRD answers: what problem are we solving and what must the product do?
- roadmap answers: what phases and tasks will we execute?
- slice spec answers: what exact contract must the next slice implement?

## Execution shape

Every implementation slice should be decomposed into **work packets** before the
developer manager starts execution.

A work packet is the smallest independently implementable and independently
reviewable unit that still moves the slice forward.

Each work packet should declare:

- owned files, modules, or surfaces
- frozen contract or interface assumptions
- explicit non-goals
- focused validation targets
- the review lens needed for that packet
- which roadmap/spec/checklist files must be updated when the packet is done

Parallelization rule:

- if packets can proceed without conflicting write ownership or unstable shared
  interfaces, they should be delegated in parallel
- if a packet cannot be reviewed on its own, it is still too large or poorly
  bounded and should be split again
- slice completion requires both packet-level review and a final aggregate
  review across the recombined result

## Workflow

### 1. Stress-test the language and architecture

- Use the `grill-with-docs` skill when the plan is still fuzzy or
  contradictory.
- Update `CONTEXT.md` inline so terms stabilize before implementation planning.
- Use the `ubiquitous-language` skill when a broader glossary export is useful.

### 2. Record hard decisions

- Write or update an ADR for hard-to-reverse architecture choices.
- Keep the ADR small and decision-focused.

### 3. Produce a PRD

- Use the `to-prd` skill logic to synthesize the current context into a local
  PRD.
- Save the PRD in `wiki/user/architecture/`.
- The PRD must call out modules, testing decisions, and out-of-scope areas.

### 4. Turn the PRD into a roadmap and slice spec

- Keep a roadmap page with phased tasks and acceptance criteria.
- Keep a separate slice spec whenever the next build step needs a more exact
  contract.
- Do not merge PRD, roadmap, and spec into one file.

### 5. Plan with the planning agent

- Use the planning manager agent to:
  - resolve the target roadmap item
  - gather the needed context
  - decompose the slice into parallelizable work packets with explicit
    dependencies
  - shape the work for the shared developer and reviewer agents
  - keep the PRD, roadmap, spec, and log aligned
- The planning manager should load and follow the `premortem` skill before
  freezing a new slice or materially expanding scope, especially for
  determinism, indexing, storage, adapter, or migration work.
- The planning manager should emit packet-level validation and review
  expectations, plus the final aggregate review needed after packet
  recombination.

### 6. Implement with the developer agent

- Use the developer manager agent to own one implementation slice.
- The developer manager should load and follow the `tdd` skill for
  implementation slices.
- Keep work packets explicit and parallelize only when dependencies make that
  safe.
- Prefer many small coherent packets over one large mixed-context task when
  dependencies allow parallel execution.
- Recombine packet outputs only after each packet has validation evidence and a
  review target.
- Use focused validation while packets are in progress.
- Before calling the slice done, run the full project validation available in
  the repo, unless the user explicitly narrows validation. If no full suite
  exists yet, run the strongest deterministic checks available and record the
  gap explicitly.
- Update the relevant roadmap/spec/checklist artifacts immediately when packet
  or slice work is complete.
- Preserve reusable substrate and delete replaced scaffolding.
- Use the `handoff` skill if implementation must stop before the slice is left
  in a coherent continuation state.

### 7. Review with the reviewer agent

- Use the reviewer manager agent before a task is considered done.
- The reviewer manager should load and follow the `premortem` skill when a
  slice is risky, under-specified, or missing explicit tripwires.
- Review each work packet independently when the slice was delegated in
  parallel.
- After packet-level review, run an aggregate review over the recombined slice
  to catch integration drift, contract mismatches, and cross-packet regressions.
- Verify that the claimed completion includes the required checklist/task-file
  updates and the expected validation evidence.
- Focus review on behavior, determinism, provenance, no-chunk-dump output, and
  testing gaps.
- Use the `handoff` skill if review must stop before findings and residual
  risks are captured cleanly.

### 8. Commit after completion

- If the current session includes commit work, create a commit only after
  packet-level review, aggregate review, roadmap/spec/checklist updates,
  wiki-log updates, and final validation are complete.
- Keep the commit to one logical slice outcome and follow the repo commit
  discipline.

### 9. Handoff when stopping

- Use the `handoff` skill when a fresh session should continue the work.
- Prefer a handoff document over ad hoc chat summaries when the next agent will
  need artifact paths, remaining risks, or suggested skills.

## Agent roles

- This repo keeps exactly three custom opencode agents:
  - `capability-plan-manager`
  - `capability-developer`
  - `capability-reviewer`
- planning manager: owns PRD -> roadmap -> slice alignment, work-packet
  decomposition, and dependency shaping
- developer manager: owns implementation for one slice, delegates parallel work
  packets, and recombines them coherently
- reviewer manager: owns packet-level and aggregate review before the slice is
  considered done

## Non-negotiables

- no dead code after replacement paths land
- no chunk dumping as an accepted regression
- deterministic truth boundaries must remain explicit
- the same core semantics must power CLI, compiled artifacts, and
  workflow integration
- a slice is not done until the required checklist/task files and wiki log are
  updated
- a slice is not done until the required validation is run
