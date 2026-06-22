# ccw

**CCW is a deterministic context compiler for small-window coding models.**

Most context pipelines give a model either everything (too noisy) or
an embedding-retrieved guess (unverifiable). CCW does neither. It walks the
repo, records explicit facts and run history, and assembles a bounded,
grounded markdown artifact whose every file path, symbol, and constraint traces
back to the real index. No vector store. No LLM in the critical path. Receipts
included.

The compiled artifact and a portable session bundle are the primary surfaces.
An MCP server exposes the same pipeline as callable tools so an agent framework
can drive the full loop without shelling out.

CCW intentionally keeps workflow packaging, harness adapters, and
orchestrator-specific definitions in a separate companion repo (`ccw-stack`)
so this core stays deterministic and inspectable.

## Why deterministic compilation matters

A small-window model working on a real codebase needs:

- **Relevance** — only files and symbols related to the task
- **Boundedness** — a hard token budget it cannot overflow
- **Grounding** — every cited path must exist in the index; invented paths fail validation
- **Memory** — project constraints and past decisions the raw code does not contain
- **Freshness** — the model should never silently trust a stale artifact

CCW enforces all five. The integration test (`tests/test_integration_mcp_value.py`)
asserts each claim deterministically without an LLM.

## Install

Requires Python 3.11 or newer.

**Stable install from PyPI:**

```bash
pip install ccw
```

**Isolated CLI install (recommended — keeps ccw out of your project's environment):**

```bash
pipx install ccw
```

**Zero-install MCP server launch via [uv](https://github.com/astral-sh/uv):**

```bash
uvx ccw-mcp
```

**Install through Microsoft APM:**

```bash
apm install fmferrari/ccw --target copilot
```

This package publishes CCW as an APM package that installs the MCP server
declaration into supported harnesses. The server itself is launched with
`uvx ccw-mcp`, so consumers need both `apm` and `uv` available on `PATH`.

**Development install from source:**

```bash
git clone https://github.com/fmferrari/ccw
cd ccw
python -m venv .venv && source .venv/bin/activate
pip install -e .
```

The `mcp` dependency installs automatically. Verify:

```bash
ccw --help
python -c "import ccw; print(ccw.__version__)"
```

## End-to-end demo

The full value loop in five CLI steps:

```bash
# 1. Bootstrap local state for this repo
ccw init

# 2. Index the repo: files, symbols, imports, edges, git signals
ccw index .

# 3. Record an explicit constraint that the raw code does not contain
ccw facts add constraint "Never log plaintext passwords"

# 4. Compile a task-scoped context artifact (auto-classifies mode and budget)
ccw compile --task "Fix the login bug that rejects valid credentials"

# 5. Validate: only real paths, required sections present, no invented symbols
ccw validate .ccw/compiled/latest.md
```

The compiled artifact is `.ccw/compiled/latest.md` by default, a markdown file
with YAML frontmatter carrying the task, mode, token budget, and an
`index_hash` that pins the artifact to the exact repo state it was built from.
Pass `--out <path>` to write somewhere else.

After a run completes:

```bash
ccw update --run "Fixed the login bug" --touched-files "login.py" \
  --decision "Treat empty credentials as invalid"
```

This re-indexes the repo and appends an episode and optional decision fact so
future compilations include the run outcome.

## How compilation works

`ccw compile` runs a named pass pipeline:

1. **ResolveTask** — classifies the task (`bugfix`, `implementation`, `review`, `refactor`) and selects the matching recipe with per-section budgets
2. **RankFiles** — scores indexed files by keyword overlap, fuzzy prefix match, symbol-name match, and git freshness; caps at the recipe file limit
3. **ExtractSnippets** — pulls line-anchored code snippets up to each section's token allocation
4. **LoadMemory** — loads explicit facts, episodes, and constraints from the append-only store
5. **Assemble** — composes ranked files, snippets, memory, and constraints into a `CompiledContext`, then renders to bounded markdown

Token budgets per mode:

| Mode | Default budget |
|------|---------------|
| `bugfix` | 6 000 tokens |
| `implementation` | 8 000 tokens |
| `review` | 8 000 tokens |
| `refactor` | 10 000 tokens |

## MCP server

`ccw-mcp` exposes the full pipeline as MCP tools so an agent framework can
drive the entire loop without shelling out. The target repo is set via the
`CCW_TARGET_ROOT` environment variable or the `target_path` parameter on each
tool call.

```bash
# Manual launch (for testing)
CCW_TARGET_ROOT=/path/to/project ccw-mcp
```

Available tools:

| Tool | What it does |
|------|-------------|
| `init_repo` | Bootstrap `.ccw/` local state |
| `index_repo` | Walk and index the repo into SQLite |
| `record_fact` | Append an explicit fact (constraint, decision, preference) |
| `record_episode` | Append a completed-run episode with touched files |
| `classify_task` | Deterministically classify task text into a compile mode |
| `compile_task_context` | Compile a bounded, grounded context artifact |
| `prepare_session` | Compile and package a portable session bundle |
| `validate_session` | Check bundle freshness against the current index hash |
| `update_memory` | Re-index and record a post-run episode and optional decision |
| `validate_compiled_artifact` | Validate frontmatter, sections, and file paths |

Every tool accepts an explicit `target_path`. If omitted, CCW reads
`CCW_TARGET_ROOT` from the environment.

## APM distribution

CCW can also be consumed as a Microsoft APM package. In APM terms, this repo is
primarily an MCP primitive package: when a consumer runs `apm install`, APM
writes the `ccw` MCP server entry into each detected harness config.

Consumer install:

```bash
apm install fmferrari/ccw --target copilot
```

What APM installs for the consumer is equivalent to this self-defined MCP
server declaration:

```yaml
dependencies:
  mcp:
    - name: ccw
      registry: false
      transport: stdio
      command: uvx
      args: ["ccw-mcp"]
```

Important constraints:

- APM distributes the harness configuration, not the Python wheel.
- `uvx ccw-mcp` is what makes the server portable here: `uvx` resolves and runs
  the PyPI package on demand.
- If the harness does not launch the MCP server from the repo root, pass
  `target_path` explicitly on tool calls or set `CCW_TARGET_ROOT` in the
  generated config.
- Because this is a self-defined MCP server (`registry: false`), consumers
  should install it as a direct dependency, not rely on it flowing transitively.

### Connecting CCW to your project

Add this to your project's `.mcp.json` (or equivalent harness config).

**Option A — zero-install via `uvx` (recommended if you have [uv](https://github.com/astral-sh/uv)):**

```json
{
  "mcpServers": {
    "ccw": {
      "command": "uvx",
      "args": ["ccw-mcp"],
      "env": {
        "CCW_TARGET_ROOT": "/absolute/path/to/your/project"
      }
    }
  }
}
```

**Option B — after `pip install ccw` or `pipx install ccw`:**

```json
{
  "mcpServers": {
    "ccw": {
      "command": "ccw-mcp",
      "env": {
        "CCW_TARGET_ROOT": "/absolute/path/to/your/project"
      }
    }
  }
}
```

**Option C — development checkout:**

```json
{
  "mcpServers": {
    "ccw": {
      "command": "/path/to/ccw/.venv/bin/python",
      "args": ["-m", "ccw.mcp_server"],
      "env": {
        "CCW_TARGET_ROOT": "/absolute/path/to/your/project"
      }
    }
  }
}
```

### `.ccw/` in your target repo

CCW creates a `.ccw/` directory at your project root. The SQLite database
(`.ccw/index.sqlite`) stores both the regenerable file index and your durable
project memory (facts and episodes).

**Recommended `.gitignore` additions for your project:**

```gitignore
# CCW ephemeral artifacts — regenerated on demand
.ccw/compiled/
.ccw/session/
.ccw/snapshots/
```

Leave `.ccw/index.sqlite` and `.ccw/config.yaml` **uncommitted** if CCW is
personal tooling, or **commit them** if you want the team to share facts and
episodes across clones. Either works; the index portion regenerates in seconds
with `ccw index`.

## Session bundle

A session bundle is a portable, file-only handoff that any agent, script, or
CI step can consume without MCP, provider APIs, or workflow orchestration.

```bash
ccw session prepare --task "Fix the login bug" --mode implementation
```

The bundle lives at `.ccw/session/latest/` by default:

| File | Role |
|------|------|
| `SESSION.md` | Model-facing entry file — instructs the model to use the compiled context before re-gathering repo context and to request a refresh on mismatch |
| `compiled-context.md` | The grounded, budgeted context artifact |
| `session.json` | Machine-readable metadata: task, mode, budget, `index_hash`, and timestamps |

### File-only consumption

```python
import json
from pathlib import Path

bundle = Path(".ccw/session/latest/")

session_md = (bundle / "SESSION.md").read_text()
compiled_context = (bundle / "compiled-context.md").read_text()
metadata = json.loads((bundle / "session.json").read_text())
```

Validate that the bundle is internally consistent and the `index_hash` still
matches the current repo state:

```bash
ccw session validate .ccw/session/latest/
```

For multi-repo or harness-managed workflows:

```bash
ccw session prepare \
  --task "Refactor auth module" \
  --mode refactor \
  --out-dir /shared/sessions/auth-refactor \
  /path/to/repo
```

### Consumption contract

1. Read `SESSION.md` first — it explains the grounded task context.
2. Use `compiled-context.md` as the authoritative task-scoped repo state. Do not re-gather repo context unless the bundle is stale.
3. Check `session.json` — if the `index_hash`, task, or mode no longer match, request a refreshed bundle rather than silently trusting stale context.

## Conductor workflow scaffold

```bash
ccw conductor init
```

Generates a `ccw-code-task/` directory with a shell script showing the full
pipeline as script steps (init → index → classify → compile → session prepare →
validate) and a README explaining the consumption contract.

Full Conductor workflow packaging and harness adapters belong in the companion
`ccw-stack` repo.

## Architecture boundary

- **CCW** — deterministic context compiler and post-run update engine (this repo)
- **CCW Stack** — companion repo for Conductor workflow packaging, harness adapters, and optional portable brain behavior
- **Conductor** — the external workflow orchestrator that calls CCW as a script or tool step
- **Model provider** — the inference backend that consumes CCW artifacts (OpenAI, Anthropic, GitHub Models, etc.)

## Development

```bash
python -m unittest
```

146 tests covering CLI surfaces, compiler passes, pipeline composition, MCP
tools, session bundle, Conductor scaffold, and the end-to-end value integration.

See `CONTRIBUTING.md` for contribution flow and documentation expectations.

## Community

- Contribution guide: `CONTRIBUTING.md`
- Code of conduct: `CODE_OF_CONDUCT.md`
- Security reporting: `SECURITY.md`
- Bug reports and feature requests: GitHub Issues

## License

CCW is licensed under the MIT License. See `LICENSE`.
