---
name: premortem
description: Stress-test a proposed plan, slice, or change by assuming it already failed and working backward to likely causes, tripwires, mitigations, and validation gaps. Use when shaping roadmap slices, planning refactors or migrations, reviewing risky changes, or when the user asks for a premortem, risk review, failure modes, guardrails, or "what could go wrong".
---

# Premortem

Use this before implementation or approval when hidden failure modes matter more
than broad ideation.

## Goal

Assume the proposal shipped and failed. Identify the most plausible reasons
early, then convert them into concrete slice changes, acceptance criteria,
tests, and review checks.

## Best-fit cases

- new roadmap slice or slice spec
- contract, schema, adapter, or sidecar changes
- trust-boundary, write-path, grounding, scope, or migration work
- large refactor with scaffolding removal
- review phase where "looks fine" may hide systemic risk

## Workflow

1. Freeze the target.
   - name the artifact or change under review
   - state in-scope and explicit non-goals
2. Write the failure headline.
   - `Two weeks after shipping, this failed because...`
3. Generate failure modes across these lenses:
   - user-visible behavior and readability
   - grounding, provenance, and chunk-dump regression
   - contract drift across CLI, compiled artifacts, and Conductor integration
   - auth, access, session, and scope safety
   - data migration, sidecar staleness, and rebuildability
   - performance, latency, cost, and retry loops
   - observability, recovery, and rollback gaps
   - dead scaffolding and partial replacement traps
4. Rank only the top 3-5 risks.
   - severity
   - plausibility
   - blast radius
5. Turn each top risk into controls.
   - mitigation or slice reduction
   - early tripwire or signal
   - exact test or eval
   - exact artifact update: roadmap, spec, ADR, review checklist, or log
6. Decide the outcome.
   - proceed unchanged
   - shrink slice
   - split slice
   - block pending decision

## Output shape

- failure headline
- top risks
- controls and tripwires
- required artifact changes
- go or no-go recommendation

## Rules

- Prefer repo-specific failure modes over generic risk laundry lists.
- If a risk matters, encode it in acceptance criteria, tests, or review checks.
- Separate observed facts from speculation.
- Preserve reusable substrate and flag dead scaffolding clearly.
- Keep readable grounding and no-chunk-dump checks explicit.
- Keep the list short. High signal beats exhaustive risk spam.
