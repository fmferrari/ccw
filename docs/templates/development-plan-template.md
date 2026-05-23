# Development Plan Template

Development plans live under `wiki/user/architecture/` and should stay
phase-based, checklist-driven, and separate from PRDs and exact slice specs.

## Template

```md
---
type: architecture
tags: [architecture, plan, iterations]
created: YYYY-MM-DD
updated: YYYY-MM-DD
status: active
---

# Development plan

One or two paragraphs describing the current product state, what is already
true, and what the next priorities are.

## Phase 1 - Name (current)

Goal: one sentence describing the capability this phase proves.

- [ ] concrete task
- [ ] concrete task
- [ ] concrete task

Acceptance criteria:

- observable behavior or artifact requirement
- validation requirement
- explicit boundary or non-goal when useful

Deliverable: one sentence describing what exists when the phase lands.

## Phase 2 - Name

Goal: one sentence.

- [ ] concrete task
- [ ] concrete task

Acceptance criteria:

- observable behavior or artifact requirement

Deliverable: one sentence.
```

## Notes

- Keep one roadmap file per capability stream, not one file per tiny task.
- Each phase should have a goal, checklist, acceptance criteria, and
  deliverable.
- Use checkboxes only for executable tasks.
- Add a separate slice spec when the next build step needs a tighter contract
  than the roadmap can provide.
- Update the `updated` date and `wiki/user/log.md` whenever the plan changes in
  a meaningful way.
