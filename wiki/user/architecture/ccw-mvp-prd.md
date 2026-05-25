---
type: architecture
tags: [architecture, prd, compiler]
created: 2026-05-23
updated: 2026-05-25
status: active
---

# CCW MVP PRD

## Problem Statement

Small-window and low-cost coding models break down when they need broad project
context. Today the usual workaround is either huge context windows or
stochastic summarization. Both are costly or hard to trust. CCW should make a
4k/8k model behave like it has project memory by compiling deterministic,
inspectable task context before model execution.

## Solution

Build a local CLI that indexes a repository, stores explicit project facts and
episodes, compiles task-scoped context to a strict budget, optionally compresses
that context with a cheap model after deterministic assembly, and integrates as
a script step inside Microsoft Conductor workflows.

## User Stories

1. As a maintainer, I want to index a repo once and reuse the resulting code
   facts, so that later task context assembly is fast and deterministic.
2. As a workflow author, I want to call CCW from a Conductor script step, so
   that context compilation becomes part of a deterministic multi-step run.
3. As a developer, I want compiled context to cite exact files, symbols, and
   hashes, so that I can verify what the model was shown.
4. As a developer, I want CCW to include constraints and non-goals in the
   output artifact, so that implementation runs stay bounded.
5. As a project owner, I want explicit append-only facts and decisions, so that
   durable project memory is not hidden inside chat transcripts.
6. As a reviewer, I want deterministic validation for compiled context and
   compressed context, so that no new facts can be invented silently.
7. As a budget-conscious user, I want small or free execution models to work
   against compiled context artifacts, so that I can avoid paying for giant
   context windows.
8. As a maintainer, I want post-run updates that capture what changed, why, and
   what tests ran, so that later tasks can reuse that grounded history.
9. As a contributor, I want a boring local storage model built on SQLite and
   files, so that the project stays easy to inspect and hack on.
10. As a developer, I want deterministic task recipes for bug fix,
    implementation, review, and refactor work, so that context assembly is
    predictable.
11. As an operator, I want Conductor and CCW to stay separate concerns, so that
    CCW does not turn into another agent framework.
12. As a contributor, I want MVP language support for Python, TypeScript,
    JavaScript, Markdown, JSON, and YAML, so that common repos are useful from
    day one.
13. As a harness integrator, I want CCW to emit a provider-neutral session
    handoff artifact, so that a model can reuse compiled context on a first or
    later turn without re-gathering repo state.

## Implementation Decisions

- CCW is a CLI-first local tool, not a hosted service.
- Microsoft Conductor remains the workflow orchestrator; CCW is a scriptable
  context compiler and update tool.
- Multi-harness orchestration, harness adapters, and any optional portable
  brain behavior live in the companion `ccw-stack` repo rather than inside CCW
  core.
- Repository state lives under `.ccw/` using SQLite plus append-only JSONL
  artifacts.
- The indexer is deterministic and syntax-driven, using tools such as
  tree-sitter, ripgrep, SQLite, and git metadata.
- Facts and episodes are explicit append-only records. CCW should infer as
  little as possible.
- Compiled context is a structured markdown artifact with task, project state,
  relevant files, symbol graph, snippets, and constraints.
- CCW should expose a provider-neutral session handoff contract around compiled
  artifacts so any harness can present the same grounded context to a model.
- Ranking and budgeting stay deterministic.
- LLM compression is optional and sits strictly after deterministic assembly.
- Compression output must be validated against known file paths, symbols,
  hashes, and required constraints.

## Testing Decisions

- Test behavior through public CLI commands and stable output artifacts.
- Use fixture repositories to verify indexing, ranking, and compiled-context
  assembly.
- Add golden tests for compiled markdown structure and validator behavior.
- Validate rerun safety and idempotency for initialization and indexing.
- Treat any optional LLM compression as a contract-tested optimization, not a
  trusted reasoning path.

## Out of Scope

- Building a full multi-agent framework inside CCW
- Owning multi-harness workflow packaging or adapter installation
- Owning a portable cross-harness brain layer as canonical project memory
- Owning provider-specific session attachment or prompt-role behavior
- Vector search or embedding infrastructure in the MVP critical path
- Replacing Conductor as the orchestrator
- Rich semantic analysis beyond the initial supported languages
- Making the LLM compression layer mandatory for useful output

## Further Notes

The MVP should be intentionally boring. Deterministic indexing, explicit memory,
inspectable artifacts, and workflow-friendly CLI surfaces matter more than
novelty in the first release.
