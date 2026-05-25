---
type: architecture
tags: [architecture, spec, slice, mcp, integration]
created: 2026-05-25
updated: 2026-05-25
status: archived
---

# Phase 5A - MCP server spec

## Purpose

Ship an MCP-facing tool surface so external agent frameworks can call CCW's
deterministic core directly against another repository.

This slice should make CCW installable as `ccw-mcp` while keeping the existing
CLI and core modules as the source of truth for behavior.

## In scope

### FastMCP server and entrypoint
- Add `src/ccw/mcp_server.py`
- Expose an installable `ccw-mcp` entrypoint from `pyproject.toml`
- Use `FastMCP("ccw")` with stdio transport via `mcp.run()`

### Tool surface
- `init_repo(target_path="")`
- `index_repo(target_path="")`
- `record_fact(kind, text, target_path="")`
- `record_episode(summary, touched_files, target_path="")`
- `classify_task(task_description, target_path="")`
- `compile_task_context(task_description, target_path="", output_path="", mode="", budget=0)`
- `validate_compiled_artifact(artifact_path, target_path="")`

All tool implementations must call the existing deterministic CCW modules
directly rather than shelling out to the CLI.

### Target-path contract
- Every tool accepts an optional `target_path`
- If `target_path` is omitted, use `CCW_TARGET_ROOT`
- If neither is set, fall back to `.`
- Relative `output_path` and `artifact_path` values resolve against the target
  repo root, not the server checkout root

### Structured responses
- `init_repo`: return target path, state dir, database path, config path
- `index_repo`: return target path, database path, snapshot path, and index row
  counts
- `record_fact`: return normalized fact payload and database path
- `record_episode`: return summary, touched files, and database path
- `classify_task`: return task description and resolved mode
- `compile_task_context`: return artifact path plus latest persisted compilation
  metadata when available
- `validate_compiled_artifact`: return `valid` plus `errors`

### Validation and docs
- Add regression coverage for explicit target paths and env-default target paths
- Exclude common runtime/cache directories and `*.egg-info` metadata during
  repository walks so MCP indexing works on normal development checkouts
- Update `README.md` with MCP server setup for another project
- Advance roadmap and workflow docs to this slice

## Explicit non-goals

- New orchestration logic inside CCW
- Hosted network service behavior
- Conductor workflow scaffolding (`ccw conductor init`) in this packet
- Post-run memory updates
- Repo-specific ignore configuration beyond the built-in cache/runtime
  exclusions

## Modules and files

```text
src/ccw/mcp_server.py   - FastMCP tool adapter over existing CCW functions
pyproject.toml          - mcp dependency and ccw-mcp entrypoint
tests/test_mcp_server.py - MCP integration regression tests
README.md               - public MCP onboarding and config examples
```

## Validation

- `python -m unittest`
- Focus checks:
  - MCP tool functions operate against an explicit external repo path
  - `CCW_TARGET_ROOT` works as a default target
  - repo-relative output and artifact paths resolve against the target repo root
  - compiled artifacts validate cleanly after MCP-driven init/index/compile
