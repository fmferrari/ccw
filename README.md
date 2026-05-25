# ccw

CCW is a deterministic context compiler for small-window coding models.

It indexes a repository, stores explicit project facts and episodes, compiles
task-scoped context to a fixed budget, and can optionally compress that context
with an LLM after deterministic assembly.

CCW intentionally keeps workflow packaging, harness adapters, and any optional
portable-brain behavior in a separate companion repo (`ccw-stack`) so the core
stays deterministic and inspectable.

## Status

CCW is alpha software. CLI surfaces, artifact schemas, and workflow packaging
details may still change as follow-on slices land.

## Install

CCW requires Python 3.11 or newer.

For contributor or local development installs:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

For a non-editable local install from a checkout:

```bash
pip install .
```

## Quickstart

```bash
ccw init
ccw index .
ccw compile --task "fix auth bug" --budget 4000
ccw validate .ccw/compiled/latest.md
ccw update --run ./conductor/runs/latest
```

## MCP server

CCW also ships an MCP server so another project can call the deterministic core
as tools instead of shelling out through the CLI.

From a source checkout:

```bash
pip install -e .
```

Run the server with a default target repo:

```bash
CCW_TARGET_ROOT=/path/to/project ccw-mcp
```

Available tools:

- `init_repo`
- `index_repo`
- `record_fact`
- `record_episode`
- `classify_task`
- `compile_task_context`
- `validate_compiled_artifact`

Tool calls may pass `target_path` explicitly. If omitted, CCW uses
`CCW_TARGET_ROOT`. Relative artifact paths and output paths resolve against that
target repo root.

Example `.mcp.json` for another project:

```json
{
  "mcpServers": {
    "ccw": {
      "command": "ccw-mcp",
      "env": {
        "CCW_TARGET_ROOT": "/path/to/project"
      }
    }
  }
}
```

Development config from a local checkout:

```json
{
  "mcpServers": {
    "ccw": {
      "command": "/path/to/ccw/.venv/bin/python",
      "args": ["-m", "ccw.mcp_server"],
      "cwd": "/path/to/ccw",
      "env": {
        "CCW_TARGET_ROOT": "/path/to/project"
      }
    }
  }
}
```

## Session bundle

A session bundle is a portable, file-only handoff that wraps a compiled context
artifact so it can be consumed directly by an execution model on any harness
without MCP, provider APIs, or workflow orchestration.

Create a bundle from a repo root:

```bash
ccw init
ccw index .
ccw session prepare --task "Fix the login bug" --mode implementation
```

The bundle lives at `.ccw/session/latest/` by default and contains three files:

| File | Role |
|------|------|
| `SESSION.md` | Model-facing entry file. Instructs the model to use the compiled context below before re-gathering repo context, and to request a refresh on mismatch. |
| `compiled-context.md` | The grounded, budgeted context artifact produced by `ccw compile`. |
| `session.json` | Machine-readable metadata: task description, mode, budget, index hash, and timestamps. |

### File-only consumption

A downstream agent, script, or CI step can read the bundle directly:

```python
import json
from pathlib import Path

bundle = Path(".ccw/session/latest/")

# Model instructions
session_md = (bundle / "SESSION.md").read_text()

# Grounded context for the task
compiled_context = (bundle / "compiled-context.md").read_text()

# Machine-parseable metadata
metadata = json.loads((bundle / "session.json").read_text())
```

Validate that the bundle is internally consistent and not stale:

```bash
ccw session validate .ccw/session/latest/
```

For multi-repo or harness-managed workflows, write bundles to an explicit path:

```bash
ccw session prepare \
  --task "Refactor auth module" \
  --mode refactor \
  --out-dir /shared/sessions/auth-refactor \
  /path/to/repo
```

### Consumption contract

Any agent or model receiving a session bundle should:

1. Read `SESSION.md` first — it explains that this bundle is the grounded
   task context.
2. Use `compiled-context.md` as the authoritative task-scoped repo state.
   Do not re-gather repository context unless the bundle metadata is stale.
3. Check `session.json` — if the task, mode, index hash, or timestamp no
   longer match the current need, request a refreshed bundle instead of
   silently trusting stale context.

This contract keeps CCW harness-agnostic. Provider-specific session
attachment and workflow integration belong in the companion `ccw-stack` repo,
not in CCW core.

## Conductor workflow scaffold

CCW ships a scaffold command that generates a sample workflow directory
showing how the deterministic pipeline composes as script steps inside
Microsoft Conductor or any workflow orchestrator:

```bash
ccw conductor init
```

This creates `ccw-code-task/` in the current directory with:

| File | Role |
|------|------|
| `bin/run.sh` | Shell script showing the full pipeline: init → index → classify → compile → session prepare → session validate |
| `README.md` | Explains each step, the consumption contract, and the companion boundary |

The scaffold demonstrates how Conductor would call CCW as script steps.
Full Conductor workflow packaging, harness adapters, and orchestrator-specific
definitions belong in the companion `ccw-stack` repo, not in CCW core.

Write the scaffold to an explicit path:

```bash
ccw conductor init --out /path/to/workflows
```

## Core idea

- `Microsoft Conductor` is the deterministic workflow orchestrator.
- `CCW` is the deterministic context compiler and post-run update layer.
- `CCW Stack` is the companion orchestration repo for harness adapters,
  workflow packaging, and optional portable brain behavior.
- Small or free models are the execution backends that consume CCW artifacts.

## Key docs

- `wiki/user/architecture/ccw-mvp-prd.md`
- `wiki/user/ops/plans/development-plan.md`
- `wiki/user/ops/specs/phase-5d-post-run-update-spec.md`
- `wiki/user/architecture/ccw-stack-companion-boundary.md`
- `wiki/user/architecture/sdlc/agentic-development-workflow.md`
- `docs/adr/0001-use-microsoft-conductor-as-the-orchestrator.md`
- `docs/adr/0002-keep-orchestration-and-portable-brain-in-ccw-stack.md`

## Current status

This repo now ships `ccw init` for deterministic local-state bootstrap and
`ccw index` for deterministic file inventory, multi-language symbols, basic
edges, document artifacts, git signals, and snapshot output into
`.ccw/index.sqlite` and `.ccw/snapshots/index.json`, plus `ccw facts add`,
`ccw episodes add` for explicit append-only project memory, and `ccw classify`
for deterministic task classification, `ccw compile` and `ccw validate` for
inspectable task-scoped context artifacts, `ccw-mcp` for agent-framework
tool integration against external repos, `ccw conductor init` for Conductor
workflow scaffolding, and `ccw update --run ...` for post-run re-indexing plus
episode and decision-fact recording. Indexing skips common runtime and cache
directories such as `.git`, `.ccw`, `.venv`, `__pycache__`, `.pytest_cache`,
`.ruff_cache`, and `*.egg-info`. Phase 5D post-run update support is complete;
Phase 6 is the next follow-on slice.

## Development

Run the full deterministic validation suite before opening a pull request:

```bash
python -m unittest
```

See `CONTRIBUTING.md` for contribution flow and documentation expectations.

## Community

- Contribution guide: `CONTRIBUTING.md`
- Code of conduct: `CODE_OF_CONDUCT.md`
- Security reporting: `SECURITY.md`
- Bug reports and feature requests: GitHub Issues

## License

CCW is licensed under the MIT License. See `LICENSE`.
