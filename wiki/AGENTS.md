# AGENTS.md - wiki/

`wiki/user/` is the canonical committed project vault. Durable project memory
lives there, using the Karpathy LLM-Wiki pattern: frontmatter, wikilinks,
small focused pages, grep-based retrieval, and an append-only change log.

## Retrieval Contract (the loop)

Every agent action that touches project knowledge should follow this loop:

1. **Point.** State what you are looking for in one line. Pick a page type and
   a few tags.
2. **Query.** Use `rg`, repo search, or local read/search tools. Also read the
   last ~30 lines of `wiki/user/log.md` for fresh context.
3. **Read.** Open the pages that matter. If the question needs more than 3
   pages, split it first.
4. **Write.** Edit an existing page or create a new one under
   `wiki/user/architecture/`, `wiki/user/ideas/`, or `wiki/user/ops/`.
5. **Log.** Append one line under today's date in `wiki/user/log.md` using the
   format `- <kind> :: [[page]] - short note`.
6. **Validate.** Check frontmatter, wikilinks, and dates by inspection until
   dedicated wiki tooling exists in this repo.

Retrieval is grep + frontmatter + wikilinks. There is no vector store in the
critical path. If a question is hard to answer, the vault probably needs better
structure.

## Non-negotiables

1. **Frontmatter on canonical pages.** Every page in `wiki/user/` except
   `wiki/user/log.md` must have YAML frontmatter.
2. **Wikilinks over markdown links** for intra-vault references:
   `[[development-plan]]`, `[[ccw-mvp-prd]]`.
3. **Append to `wiki/user/log.md` on every meaningful change.**
4. **Never delete pages.** Supersede them with `status: archived` and a pointer
   to the successor.
5. **Real dates only.** Use the system clock for `created`, `updated`, and log
   headers.

## Frontmatter Schema

```yaml
---
type: architecture|idea|op
tags: [compiler, roadmap]
created: 2026-05-23
updated: 2026-05-23
status: draft|active|archived
---
```

Required: `type`, `tags`, `created`, `updated`.
Optional: `status` (defaults to `active`).

## Directory Layout

```text
wiki/
  AGENTS.md
  index.md
  log.md
  user/
    index.md
    log.md
    architecture/
    ideas/
    ops/
```

## Page Roles

- `architecture/` - PRDs, plans, slice specs, workflow docs, design notes
- `ideas/` - future work, references, source captures
- `ops/` - operational notes, handoff-style project coordination docs
