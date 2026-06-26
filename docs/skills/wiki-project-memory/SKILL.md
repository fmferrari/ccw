---
name: wiki-project-memory
description: Maintain an optional lightweight project-memory vault made of small Markdown pages, YAML frontmatter, local links, grep-friendly retrieval, and an append-only log. Use when a repository needs durable project memory for architecture, plans, decisions, handoffs, or operating notes, especially when the repo has no existing memory convention or the user asks to create, update, or follow a local wiki-style documentation structure.
---

# Wiki Project Memory

## Overview

Use a small Markdown vault as canonical project memory. Keep it human-readable, grep-friendly, and explicit; do not hide durable knowledge in chat transcripts or generated runtime state.

This skill is optional. If the repository already has its own memory or documentation rules, follow those instead.

## Layout

Use this layout when creating a new vault:

```text
wiki/
  AGENTS.md
  index.md
  log.md
  architecture/
  ideas/
  ops/
```

Keep source-of-truth project memory under `wiki/`. Use `wiki/AGENTS.md` to define local retrieval and write rules.

## Page Rules

Every canonical page except `log.md` should have YAML frontmatter:

```yaml
---
type: architecture|idea|op
tags: [short, searchable, tags]
created: YYYY-MM-DD
updated: YYYY-MM-DD
status: draft|active|archived
---
```

Use real dates from the system clock. Do not invent created, updated, or log dates.

Use short, focused pages:

- `architecture/` for product, system, and design truth
- `ops/plans/` for roadmaps and execution plans
- `ops/specs/` for slice or feature contracts
- `ops/adr/` or `docs/adr/` for hard decisions
- `ideas/` for non-canonical exploration
- `ops/` for handoffs, prompts, runbooks, and coordination notes

Prefer local wikilinks such as `[[development-plan]]` for intra-vault references. Use normal Markdown links for external URLs or files outside the vault.

## Read Loop

Before changing project knowledge:

1. State what you are looking for in one line.
2. Search with `rg` using likely tags, titles, and terms.
3. Read `wiki/index.md` and the last 30 lines of `wiki/log.md` when they exist.
4. Open only the pages needed for the task. If more than three pages look necessary, split the question first.

## Write Loop

When project knowledge changes:

1. Edit the smallest existing page that owns the knowledge, or create a focused page in the right folder.
2. Update `updated:` with today's real date. Use `created:` only when creating a new page.
3. Do not delete canonical pages. Mark obsolete pages with `status: archived` and point to the successor.
4. Append one line under today's date in `wiki/log.md`.

Log format:

```markdown
## YYYY-MM-DD

- architecture :: [[page-name]] - short note
- ops :: [[page-name]] - short note
- idea :: [[page-name]] - short note
```

## Validation

Before finishing:

- Check frontmatter exists and uses real dates.
- Check new local links point to plausible page names.
- Check the log entry names the changed page and the actual change.
- Keep runtime artifacts, generated caches, and tool state out of the canonical vault unless the repo explicitly says otherwise.
