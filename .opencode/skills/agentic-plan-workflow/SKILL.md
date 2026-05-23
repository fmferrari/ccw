---
name: agentic-plan-workflow
description: Orchestrate CCW plan delivery from architecture discussion to PRD, roadmap, premortem, implementation, review, and handoff. Use when the user is shaping a feature plan, architecture direction, delivery workflow, PRD, roadmap, risk workup, or wants agentic execution structure in this repo.
---

# Agentic plan workflow

Use this skill when the user wants a repeatable development workflow in this
repo, especially around architecture or plan execution.

## Workflow

1. Stabilize the language.
   - Use `grill-with-docs` when the architecture is still fuzzy.
   - Use `ubiquitous-language` when a wider glossary extraction is useful.
2. Record any hard-to-reverse architecture decision in an ADR.
3. Follow the `to-prd` skill logic to create a local PRD in the workspace.
4. Keep the PRD, roadmap, and slice spec separate:
   - PRD = product intent
   - roadmap = phased task plan
   - slice spec = exact next implementation contract
5. Run `premortem` before freezing a new slice, especially for determinism,
   storage, adapter, or migration work.
6. Shape the slice into independently reviewable work packets with explicit dependencies so implementation can run in parallel safely.
7. Use only these three custom agents:
   - `capability-plan-manager`
   - `capability-developer`
   - `capability-reviewer`
8. Use `handoff` when the session should stop before delivery is complete.
9. Before calling a slice done, update roadmap/spec/checklist artifacts and the
   wiki log, then run the full project validation available in the repo unless
   the user explicitly scoped validation down. If no full suite exists yet, run
   the strongest deterministic checks available and record the gap.
10. If the session includes commit work, create a commit only after step 9 is
    complete.

## Rules

- Do not merge PRD, roadmap, and spec into one giant doc.
- Prefer local repo artifacts over issue-tracker publishing for this project.
- Preserve reusable substrate and remove dead scaffolding.
- Keep readable compiled artifacts, browsability, and no-chunk-dump acceptance
  criteria visible in every implementation plan.
- Prefer packetized slices that can be executed and reviewed independently, then
  reviewed again after recombination.
- Treat checklist/task-file updates and full-suite validation as part of completion, not cleanup.
- Treat commits as a post-validation finish step when the current session
  includes commit work.

## Key files

- `wiki/user/architecture/agentic-development-workflow.md`
- `wiki/user/architecture/ccw-mvp-prd.md`
- `wiki/user/architecture/development-plan.md`
- `wiki/user/architecture/phase-1-deterministic-compiler-spec.md`
- `CONTEXT.md`
