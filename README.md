# ccw

**CCW is a deterministic context compiler for small-window coding models.**

Most context pipelines give a model either everything (too noisy) or
an embedding-retrieved guess (unverifiable). CCW does neither. It walks the
repo, records explicit facts and run history, and assembles a bounded,
grounded markdown artifact whose every file path, symbol, and constraint traces
back to the real index. No vector store. No LLM in the critical path. Receipts
included.

The compiled artifact and a portable session bundle are the primary surfaces.
An MCP server exposes the same pipeline as callable tools so your existing
harness, editor, agent, or workflow runner can consume deterministic context
without shelling out.

CCW is not an agent framework, coding assistant, editor, orchestrator, or
harness adapter. It does one job: compile grounded repository context that
other tools can use.

## What CCW is for

- Use CCW when you want a task-scoped repo briefing with explicit receipts.
- Use it when hidden editor context, giant prompt dumps, or vector search feel
  too opaque for a coding task.
- Bring your own harness. CCW provides CLI commands, MCP tools, and file-only
  session bundles; it does not manage model sessions or execute agent loops.

## Compared to adjacent tools

- **Repomix** packs a repository for an LLM. CCW compiles a validated,
  task-specific artifact from an indexed repo, explicit memory, and a budget.
- **aider repo map** gives aider's own agent a compact code map. CCW produces
  provider-neutral artifacts any compatible tool can consume.
- **LangGraph** orchestrates stateful agents. CCW prepares the deterministic
  repo context such an agent may read before acting.
- **Cursor, Claude Code, Codex, Copilot, and similar tools** include their own
  context systems. CCW makes context selection inspectable outside any one
  product.

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
pip install ccw-mcp
```

**Isolated CLI install (recommended — keeps ccw out of your project's environment):**

```bash
pipx install ccw-mcp
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

For maintainers: this public repo can mount a private wiki clone locally via
`scripts/link-private-wiki.sh`.

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

## Updating clients

After a new release, update both the package and the client runtime that launches
the MCP server.

Python environment installs:

```bash
pip install -U ccw-mcp
```

Isolated `pipx` installs:

```bash
pipx upgrade ccw-mcp
```

`uvx`-launched clients:

```bash
uvx --refresh ccw-mcp==0.1.20 --help
```

APM-based clients:

```bash
apm install fmferrari/ccw --target copilot
```

Then restart the harness/editor process so it reloads the server binary. Without
a restart, clients may continue running an old server version.

Quick verification:

```bash
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
2. **RankFiles** — scores indexed files by keyword overlap, fuzzy prefix match, symbol-name match, and git freshness; separates task evidence from agentic/harness context files so instruction docs do not crowd out task files
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

`ccw-mcp` exposes the full compiler pipeline as MCP tools. The target repo is
set via the `CCW_TARGET_ROOT` environment variable or the `target_path`
parameter on each tool call.

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
| `prepare_context_payload` | Compile, validate, and return the actual context markdown in one payload |
| `read_compiled_context` | Read an existing bundle or artifact as validated content |
| `update_memory` | Re-index and record a post-run episode and optional decision |
| `validate_compiled_artifact` | Validate frontmatter, sections, and file paths |

Every tool accepts an explicit `target_path`. If omitted, CCW reads
`CCW_TARGET_ROOT` from the environment.

### Portable MCP context ingestion

For generic MCP harnesses, call `prepare_context_payload` first for any
non-trivial repo task. Unlike `compile_task_context` or `prepare_session`, this
returns the actual compiled markdown in the tool response, so the harness does
not need custom file-reading behavior.

Tool call shape:

```json
{
  "task_description": "Fix the login bug",
  "target_path": "/absolute/path/to/project",
  "mode": "",
  "budget": 0,
  "output_dir": ""
}
```

The response includes:

| Field | Role |
|------|------|
| `valid` / `errors` | Fail-closed validation result |
| `session_instructions` | Contents of `SESSION.md` |
| `compiled_context` | The bounded task briefing markdown |
| `manifest` | Parsed `session.json` metadata |
| `content_hash` | SHA-256 hash of `compiled_context` |
| `content_bytes` / `content_chars` | Explicit payload size counts |
| `index_hash`, `created_at`, `mode`, `budget` | Compile receipts |
| `bundle_dir`, `source_paths` | Backing files for audit/debugging |

Consumption contract for MCP clients:

1. Treat `compiled_context` as the primary briefing for that task only.
2. Do not inject it globally or reuse it for unrelated tasks.
3. If `valid` is false, do not use `compiled_context`; refresh with
   `prepare_context_payload` after resolving the errors.
4. After making changes, call `update_memory` so the next task sees the fresh
   index and completed-run episode.

Use `read_compiled_context` when a workflow already has a bundle directory or
compiled artifact path and needs to return validated content through MCP. It
checks freshness before returning markdown and fails closed on stale or invalid
inputs.

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

**Option B — after `pip install ccw-mcp` or `pipx install ccw-mcp`:**

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

This scaffold is only an example of how to call CCW from a workflow runner.
CCW does not provide workflow packaging, harness adapters, or model-session
management.

## Architecture boundary

- **CCW** — deterministic context compiler and post-run update engine (this repo)
- **Harness or workflow runner** — your existing tool that calls CCW through CLI,
  MCP, or file-only session bundles
- **Model provider** — the inference backend that consumes CCW artifacts (OpenAI, Anthropic, GitHub Models, etc.)

## Development

```bash
python -m unittest
```

192 tests covering CLI surfaces, compiler passes, pipeline composition, MCP
tools, session bundle, Conductor scaffold, and the end-to-end value integration.

See `CONTRIBUTING.md` for contribution flow and documentation expectations.

## Public release notes

- `0.1.20` — docs-lane subject-pairing after downstream feedback:
  - requires stronger subject coupling for multi-subject docs prompts such as
    retrieval + ranking before documentation-shaped files can lead
  - tightens deterministic docs adjacency so broad long-form docs do not bypass
    topicality gates through incidental anchor mentions
  - lets symbol scoring recognize multiple matched subject terms while preserving
    the existing cap, helping retrieval/ranking source and tests outrank broad docs

- `0.1.19` — lane-audit tightening after downstream feedback:
  - routes regression/stability/coverage test prompts to the review recipe so
    test-shaped tasks keep a test-biased lane
  - suppresses generic root JSON/YAML/TOML/lock config clutter from task lanes
    unless the task asks for config/infra/tooling work
  - adds a docs-mode regression proving subject-relevant retrieval evidence beats
    unrelated docs-shaped wiki/spec/notes pages when no topical docs exist

- `0.1.18` — subject-coupled docs ranking and wiki-structure evidence:
  - requires docs candidates to have subject coupling or deterministic adjacency
    before they can lead docs-mode lanes
  - exposes Markdown frontmatter, wikilinks, and markdown links as deterministic
    artifact search text for ranking
  - suppresses generic root config, lockfiles, Dockerfiles, and OS junk from
    code-task lanes unless the task asks for config/infra/tooling work

- `0.1.17` — docs-lane moderation after downstream audit:
  - lets docs-mode documentation candidates earn topicality from docs-intent
    terms such as behavior, troubleshooting, and notes
  - keeps those terms weak for source/test files so implementation and test lane
    behavior remains unchanged
  - adds a regression for the `wikiagent` docs-shaped retrieval-ranking audit
    case where a wiki/spec doc should lead before benchmark/source files

- `0.1.16` — deterministic topical relevance scoring:
  - makes topical relevance dominate lane-shape priors so unrelated docs/specs
    cannot lead docs-mode retrieval/ranking tasks merely because they are docs
  - lets strongly topical source/tests outrank weak docs when no topical docs
    exist, while topical docs still lead when present
  - tightens refactor ranking so preferred source remains ahead of tests and
    frontend/cross-language noise for non-frontend refactor tasks
  - strengthens focused test ranking for retrieval/ranking/tie prompts

- `0.1.15` — deterministic ranking topicality guardrails:
  - adds docs-mode topicality scoring so docs-shaped tasks lead with docs that
    match the requested retrieval/ranking/troubleshooting subject, not generic
    indexes or unrelated specs
  - adds generic locality scoring for refactor tasks so direct retrieval/ranking
    hits keep sibling source/tests/docs nearby before broad runtime spillover
  - introduces an explainable ranking score substrate with deterministic feature
    buckets for lexical, alias, document-shape, topicality, locality, penalties,
    and final score
  - updates the downstream lane-regression prompt to run the pytest-style
    retrieval benchmark with pytest instead of unittest

- `0.1.14` — lane-quality anchor and refactor-classification follow-up:
  - keeps docs-shaped tasks from stealing the five canonical repo anchors out of
    `## Agentic Context` by pinning `AGENTS.md`, `wiki/AGENTS.md`, `CONTEXT.md`,
    `wiki/user/index.md`, and `wiki/user/log.md`
  - classifies refactor prompts phrased as "clarity"/"preserving behavior" as
    `refactor` instead of `docs`
  - caps repeated `.github`/`.opencode`/`.cursor` instruction-family files so
    duplicate harness guidance cannot crowd out canonical anchors

- `0.1.13` — corrective version-metadata release:
  - aligns the package runtime version and APM manifest with the published
    distribution version
  - supersedes `0.1.12`, whose PyPI artifacts contained stale `0.1.11`
    runtime/APM version metadata
  - includes the `0.1.12` docs-classification and retrieval-ranking fixes

- `0.1.10` — lane-quality noise and affinity follow-up:
  - adds ranking-time build-artifact noise filtering for `build/`, `dist/`,
    and `dev-dist/` so stale artifact paths cannot leak into lanes
  - improves backend-task focus with task-language inference and cross-language
    penalties that reduce frontend TypeScript/TSX leakage in refactor tasks
  - strengthens frontend-noise penalties for non-frontend tasks while keeping
    deterministic, generic path-shape heuristics

- `0.1.9` — lane-quality docs/refactor tuning follow-up:
  - adds a deterministic `docs` task mode and recipe, so documentation-shaped
    prompts no longer fall back to implementation mode
  - makes lane ranking mode-aware and strengthens docs-lane priority for
    `wiki/`, `docs/`, and `spec` evidence under docs tasks
  - reduces refactor task test-file dominance by increasing refactor test
    penalties and capping per-file symbol-match inflation
  - improves retrieval-specific relevance with broader alias terms
    (planner/router/tie/sort) and keeps underscore-aware matching

- `0.1.8` — lane-quality ranking follow-up:
  - boosts docs-shaped tasks so wiki/docs/spec pages remain in `## Files` even
    when many retrieval-themed tests/source files have strong lexical overlap
  - strengthens refactor intent weighting to favor source files over tests for
    "refactor ... preserving behavior" style tasks
  - improves retrieval/ranking semantic matching via task-term aliases and
    underscore-aware token matching (e.g., `wiki_search`)

- `0.1.7` — docs-intent ranking follow-up:
  - prioritizes architecture/spec documentation paths (for example
    `architecture/`, `design/`, `adr/`, `spec/`, `specs/`, `runbook/`,
    `guide/`) as task-lane evidence for docs-shaped tasks
  - prevents markdown docs under `spec`/`specs` from being misclassified as
    test-tree files
  - keeps ranking generic and deterministic with no repo-specific path boosts

- `0.1.6` — Phase 5F lane-quality ranking fixes:
  - adds documentation-intent task-lane boosting so docs-shaped tasks lead with
    generic docs/wiki/spec evidence in `## Files`
  - keeps instruction/harness anchors in `## Agentic Context` while still
    allowing docs-shaped files to rank in the task lane for docs tasks
  - excludes `dev-dist/` during indexing (alongside existing `dist/` and
    `build/` exclusions) so build artifacts do not crowd ranking lanes
  - adds deterministic regression coverage for docs-lane leadership and
    build-artifact index exclusion

- `0.1.5` — lane-ranking correctness fixes (follow-up to the 0.1.4 audit):
  - keeps every agentic anchor (e.g. `AGENTS.md`, `CONTEXT.md`, wiki
    `index.md`/`log.md`) in the agentic lane under tighter default item limits,
    without starving the task lane on small budgets
  - broadens documentation-intent detection so tasks phrased as
    "document …"/"documentation" prioritize docs/wiki/spec files
  - stops snippet extraction from overshooting the lane budget once it is
    exhausted (later files keep their reference but drop the snippet body)

- `0.1.4` — generic lane-quality hardening update:
  - removes repository-specific path boosts in file ranking heuristics
  - prioritizes generic anchor/context files in agentic context lane
  - keeps third-party/vendor files as task-lane fallback only
  - adds task-intent-aware weighting so implementation tasks prefer source
    files, while explicit test/docs tasks prioritize their corresponding files
  - adds a reusable wikiagent regression prompt with explicit client-update
    instructions after a CCW release

- `0.1.3` — lane-aware compilation update:
  - separates ranked task evidence (`## Files`) from project/harness context
    (`## Agentic Context`)
  - broadens harness context detection by default (`.cursor`, `.codex`,
    `.claude`, GitHub/Copilot instructions, MCP config patterns)
  - keeps vendored/tooling directories from crowding context lanes
  - keeps wiki log snippets tail-biased to prioritize recent project history

Detailed notes:
- `docs/releases/0.1.20.md`
- `docs/releases/0.1.19.md`
- `docs/releases/0.1.18.md`
- `docs/releases/0.1.17.md`
- `docs/releases/0.1.16.md`
- `docs/releases/0.1.15.md`
- `docs/releases/0.1.14.md`
- `docs/releases/0.1.13.md`
- `docs/releases/0.1.12.md`
- `docs/releases/0.1.11.md`
- `docs/releases/0.1.10.md`
- `docs/releases/0.1.9.md`
- `docs/releases/0.1.8.md`
- `docs/releases/0.1.7.md`
- `docs/releases/0.1.6.md`
- `docs/releases/0.1.5.md`
- `docs/releases/0.1.4.md`
- `docs/releases/0.1.3.md`

Release process for maintainers: `docs/releases/RELEASING.md`

Maintainer publish helper (loads local `.env` token safely): `scripts/release-pypi.sh`

## Community

- Contribution guide: `CONTRIBUTING.md`
- Code of conduct: `CODE_OF_CONDUCT.md`
- Security reporting: `SECURITY.md`
- Bug reports and feature requests: GitHub Issues

## License

CCW is licensed under the MIT License. See `LICENSE`.
