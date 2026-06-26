---
name: ccw-power-user
description: Use CCW correctly as a deterministic context compiler and explicit project-memory tool. Use when preparing task context with CCW, consuming compiled context or session bundles, recording facts or post-run episodes, validating freshness, integrating CCW through MCP/CLI/Conductor, or deciding what belongs in CCW runtime memory versus a repository's own documentation or memory contract.
---

# CCW Power User

## Overview

Use CCW as a deterministic compiler of grounded task context. Do not treat it as an agent framework, vector memory, chat summarizer, or autonomous memory writer.

The correct loop is: initialize/index, compile or prepare a task-scoped context, consume it only for that task, validate freshness, complete work, then explicitly update memory.

## Two-Session Bootstrap Prompts

Use these prompts when a harness imports both CCW skills and wants to prepare a repository in separate sessions. Canonical harness-readable copies live in:

- `docs/capabilities/ccw/prompts/01-wiki-project-memory-bootstrap.prompt.md`
- `docs/capabilities/ccw/prompts/02-ccw-power-user-bootstrap.prompt.md`

Harnesses can discover both through `docs/capabilities/ccw/capability.json`.

Session 1, optional project-memory setup:

```text
Use $wiki-project-memory to initialize or align a lightweight project memory vault in this repository.

First inspect the repo root instructions, existing docs, and any AGENTS.md files for an existing canonical documentation or memory contract. If one exists, follow it and do not create a competing structure. If none exists, create the generic `wiki/` vault with `AGENTS.md`, `index.md`, `log.md`, `architecture/`, `ideas/`, and `ops/`.

Seed only the minimum useful content: local read/write rules in `wiki/AGENTS.md`, a concise map of page roles in `wiki/index.md`, and a real-date entry in `wiki/log.md` for the setup. Use YAML frontmatter on canonical pages except `log.md`, keep pages small, use local wikilinks for intra-vault references, do not move existing docs, and report the files changed plus any assumptions.
```

Session 2, CCW setup:

```text
Use $ccw-power-user to prepare this repository for CCW-backed agent sessions.

First read the repo instructions and detect whether CCW local state already exists. Run `ccw init` and `ccw index` for the repo, then prepare and validate a session bundle for the task: "Verify CCW setup and project-memory integration." Treat the compiled context as task-scoped and do not reuse stale bundles.

Record explicit CCW facts only when they are already established by repo files or user instructions; do not invent preferences, goals, or decisions. If this session changes source or documentation files, close the loop with `ccw update --run ... --touched-files ...` using repo-relative paths. If no repo files changed, do not force an episode. Report commands run, bundle paths, memory writes, validation results, and any setup gap.
```

## Operating Rules

- Keep CCW deterministic first. Ranking, indexing, memory loading, validation, and update paths must work without an LLM.
- Treat compiled context as task-scoped. Do not reuse it for unrelated work and do not inject it globally.
- Trust only fresh context. If `index_hash` no longer matches the current index, re-index and prepare a new bundle.
- Write memory only through explicit surfaces: `facts add`, `episodes add`, `update`, `record_fact`, `record_episode`, or `update_memory`.
- Do not infer durable facts from vibes, chat history, or unstated intent. Record only explicit constraints, decisions, preferences, goals, or completed-run outcomes.
- Keep `.ccw/` runtime memory separate from the repository's canonical documentation or memory contract. If the repo has an `AGENTS.md`, docs index, changelog, or project-memory rules, follow those rules for durable architecture, roadmap, ADR, or planning changes.
- Keep CCW core separate from orchestration. Conductor and ccw-stack decide workflow order; CCW compiles context and records post-run updates.
- If the user wants a lightweight project-memory vault and the repo does not already define one, suggest the optional `wiki-project-memory` skill instead of making CCW own that structure.

## Start A Task

1. Identify the target repo root.
2. Ensure local state exists:

```bash
ccw init /path/to/repo
ccw index /path/to/repo
```

3. For a non-trivial repo task, prepare context before broad manual repo exploration.

Prefer MCP when available:

```text
prepare_context_payload(task_description, target_path)
```

Use CLI/file handoff when MCP is not available:

```bash
ccw session prepare --task "Describe the exact task" /path/to/repo
ccw session validate /path/to/repo/.ccw/session/latest /path/to/repo
```

Then read `SESSION.md`, `compiled-context.md`, and `session.json`.

## Consume Context

- Use the compiled context as the primary briefing for the current task.
- Respect the ranked files, snippets, facts, episodes, and constraints it surfaces.
- If the task changes materially, compile again with the new task description.
- If validation fails, do not use the stale or invalid context. Re-run `ccw index`, then prepare a fresh context.
- Re-gather extra repo context only when the compiled context is insufficient for the current task.

## Write Memory

### Facts

Record facts when the user or project artifacts establish durable information that raw code does not fully express:

```bash
ccw facts add constraint "Never log plaintext passwords" /path/to/repo
ccw facts add decision "Treat empty credentials as invalid" /path/to/repo
ccw facts add preference "Prefer dataclasses for structured compiler records" /path/to/repo
ccw facts add goal "Keep compile outputs bounded and inspectable" /path/to/repo
```

Allowed kinds are `goal`, `constraint`, `decision`, and `preference`.

### Episodes

Record episodes after a completed task or run, with repo-relative touched files:

```bash
ccw update \
  --run "Fixed login validation and added regression coverage" \
  --touched-files "src/auth/login.py,tests/test_login.py" \
  --decision "Validate credentials before creating a session" \
  /path/to/repo
```

Use `ccw update` instead of `episodes add` after code changes because it re-indexes before writing the episode. Current CCW code requires at least one non-empty touched file.

MCP equivalents:

```text
record_fact(kind, text, target_path)
record_episode(summary, touched_files, target_path)
update_memory(summary, touched_files, decision, target_path)
```

Prefer `update_memory` after work because it re-indexes, appends an episode, and optionally records a decision.

## Read Frequency And Motives

CCW memory is read when compiling context or preparing a session bundle. The compiler loads all facts, the latest episodes, and constraints during the `LoadMemory` pass, then renders them into the compiled markdown.

Read memory for:

- starting a non-trivial repo task
- handing context to a small-window model
- validating an existing bundle or artifact before use
- refreshing context after file changes or post-run memory updates

Do not read memory as a substitute for validation. Freshness still depends on the current repo index and matching `index_hash`.

## End Of Task

Before considering a CCW-backed task complete:

1. Run the task's relevant tests or validation.
2. If files changed, call `ccw update` or MCP `update_memory`.
3. If durable architecture/planning docs changed, update the repository's canonical docs or memory vault according to its local instructions.
4. Tell the user what context was prepared, what memory was written, and any validation that could not be run.
