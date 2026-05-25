---
type: architecture
tags: [architecture, spec, slice, compiler, rank, snippet, validate]
created: 2026-05-25
updated: 2026-05-25
status: archived
---

# Phase 4 - Context compiler and validator spec

## Purpose

Ship the first deterministic context compiler and compiled-artifact validator.
This is the bridge between recipe+budget definitions (Phase 3D) and a working
`ccw compile` that produces bounded, inspectable task context for execution
models.

## In scope

### Compiler core (ranking and snippet extraction)
- Define `CompiledContext`, `RankedFile`, `Snippet`, `ContextSection` dataclasses
- Implement `rank_files()` — deterministic file ranking by task keyword overlap
  with file paths, symbol names, and artifact titles, plus git-freshness boost
- Implement `extract_snippets()` — line-based snippet extraction with stable
  `file:start_line:end_line` anchors
- Implement `compile_context()` — the main composition function that takes a
  task description, recipe, and database path, and returns a `CompiledContext`
- Assign budget proportions to sections via recipe, and cap items by
  `section.max_items`

### Markdown renderer
- Implement `render_compiled_context()` — produce structured markdown from a
  `CompiledContext` with deterministic section ordering
- Output format:
  - YAML frontmatter: task mode, budget, index hash, timestamp
  - `## Task` — classification mode and description
  - `## Project state` — repo snapshot summary
  - `## Relevant files` — ranked files with snippets
  - `## Symbol graph` — relevant symbols and edges
  - `## Facts` — relevant project facts
  - `## Episodes` — recent episodes
  - `## Constraints` — explicit constraints
- Token estimation: count characters / 4 as approximate token count, truncate
  sections when cumulative exceeds allocated budget

### `ccw compile` CLI
- `ccw compile --task <description> [--budget <N>] [--out <path>] [--mode <mode>] [path]`
- Wire classify → get_recipe → allocate_budget → compile_context → render → write
- Default `--out` to `.ccw/compiled/compile-output.md`
- `--mode` skips deterministic classification (explicit override)
- Fail if local state is not initialized
- Persist the compilation record (append to a `compilations` table)

### `ccw validate` CLI
- `ccw validate <artifact_path> [path]`
- Check YAML frontmatter is parseable and has required keys
- Check all required sections present
- Verify no referenced file path is invented (cross-check against index)
- Verify budget constraints (total ≤ allocated budget)
- Return exit code 0 (valid) or 1 (invalid with error messages)

### Validation and golden tests
- Unit tests for ranking: keyword scoring, freshness boost, tie-breaking
- Unit tests for snippet extraction: exact anchors, budget truncation
- Unit tests for markdown rendering: section presence, frontmatter, format
- Unit tests for compiled-context composition: wire classify→recipe→compile
- CLI tests for `ccw compile`: temp repo, fixture index, artifact output
- CLI tests for `ccw validate`: valid artifact, missing section, invented path
- Golden test: fixture `index.json` + known task → expected markdown snapshot

## Explicit non-goals

- Tokenization or exact token counting — budget is chars/4 estimation
- ML- or LLM-based ranking or snippet selection
- Configurable render templates (Phase 5+)
- Multi-file compiled output (single markdown file only)
- Compression layer or `ccw compress` (Phase 6)
- Post-run memory updates (Phase 5)
- Compilation persistence querying or listing (`compilations` table is
  append-only; no `ccw compilations list` in this slice)
- User-defined recipes or budget overrides saved to config

## Data structures

```python
@dataclass(frozen=True)
class Snippet:
    file_path: str
    start_line: int
    end_line: int
    text: str

@dataclass(frozen=True)
class RankedFile:
    file_path: str
    score: float
    language: str
    snippets: tuple[Snippet, ...]

@dataclass(frozen=True)
class ContextSection:
    name: str
    items: tuple[RankedFile | str, ...]  # file items or text items
    allocated_budget: int
    used_budget: int

@dataclass(frozen=True)
class CompiledContext:
    task_description: str
    mode: str
    total_budget: int
    index_hash: str
    sections: tuple[ContextSection, ...]
    facts: tuple[str, ...]
    episodes: tuple[str, ...]
    constraints: tuple[str, ...]
    created_at: str
```

## Ranking algorithm

1. Tokenize task description into lowercase tokens (split on whitespace).
   Filter out common stopwords (`"the"`, `"a"`, `"an"`, `"is"`, `"it"`,
   `"to"`, `"for"`, `"of"`, `"in"`, `"on"`, `"and"`, `"or"`).
2. For each indexed file, compute base score:
   - `path_match_count`: tokens found in the file's posix path (split on `/`,
     `_`, `-`, `.`). Additionally, for each path component, check if the
     component **starts with** the token (e.g. `"auth"` matches
     `"authentication"` in a directory name) for fuzzy prefix match.
   - `symbol_match_count`: tokens found in any symbol name declared in the file
     (substring match — `"auth"` matches a symbol named `authenticate`).
   - `artifact_match_count`: tokens found in artifact title or search_text
     (substring match).
   - `base_score = path_match_count * 3 + symbol_match_count * 2 + artifact_match_count * 1`
3. Apply git freshness boost:
   - last_commit_at within last 7 days: +5
   - last_commit_at within last 30 days: +2
   - otherwise: 0
4. Apply test-mapping boost (+3) if file is a test target of another high-scoring file
5. Sort files by score descending, then by path ascending for deterministic tie-breaking
6. Return top `max_items` files from the `files` section recipe

## Snippet extraction algorithm

1. For each ranked file, read current content from disk at `target / file_path`
2. Determine best snippet anchor:
   - If any task token matches a symbol name in the file, use that symbol's
     `(line, end_line)` as the anchor and expand ±5 lines for context
   - If no symbol match, use first `min(40, total_lines)` lines
3. Truncate lines to fit within the section's remaining token budget (chars/4)
4. If tokens remain, add additional snippets from next-best anchors up to
   `max_items` per section limit

## Compiled markdown format

```markdown
---
mode: bugfix
budget: 6000
index_hash: abc123...
created_at: 2026-05-25T12:00:00Z
---

# Compiled context

## Task

**Mode:** bugfix
**Description:** Fix the login bug
**Budget:** 6000 tokens

## Project state

- Indexed files: 42
- Total symbols: 156
- Last indexed: 2026-05-25T10:00:00Z

## Relevant files (`budget: 1500`)

1. `src/auth/login.py` (score: 8)
   ```python
   lines 10-25:
   def authenticate(user, password):
       # FIXME: no rate limiting
       return db.query(...)
   ```

## Symbol graph

- `src/auth/login.py` :: `authenticate` → `src/db/query.py` (import)
- `tests/test_auth.py` → `src/auth/login.py` (tests)

## Facts

- **goal**: Add rate limiting to login endpoint
- **constraint**: Must support OAuth2

## Episodes

- `2026-05-24`: Added login form validation (touched: src/auth/login.py, src/auth/forms.py)

## Constraints

- No PII in logs
- Must pass existing test suite

---
*Estimated tokens: 5800 / 6000 allocated (chars/4 approximation)*
```

## Proposed modules and surfaces

```
src/ccw/compile.py   — CompiledContext, ranking, snippets, compilation, renderer
src/ccw/validate.py  — validate_compiled_artifact()
src/ccw/cli.py       — compile + validate subcommands
tests/test_compile.py      — unit tests for ranking, snippets, rendering
tests/test_cli_compile.py  — CLI tests for ccw compile + validate
tests/fixtures/compile/    — golden test fixtures
```

## Schema addition

```sql
CREATE TABLE IF NOT EXISTS compilations (
    id INTEGER PRIMARY KEY,
    task TEXT NOT NULL,
    mode TEXT NOT NULL,
    budget INTEGER NOT NULL,
    output_path TEXT,
    created_at TEXT NOT NULL
);
```

Required columns constant matching existing pattern:

```python
COMPILATIONS_COLUMNS = ("id", "task", "mode", "budget", "output_path", "created_at")
COMPILATIONS_OPTIONAL_COLUMNS: tuple[tuple[str, str], ...] = ()
```

Append `compilations` to `SCHEMA_TABLES` in `schema.py`. Wire
`_ensure_compilations_table()` following the same `_ensure_facts_table()`
pattern: check placeholder upgrade via `set(COMPILATIONS_COLUMNS).issubset(...)`,
then `_ensure_optional_columns` for additive future fields.

## Work packets

### Packet A — Compiler core: dataclasses, ranking, snippets, composition
**Owned files:** `src/ccw/compile.py`, `tests/test_compile.py` (ranking and snippet tests)
**Contract:** `rank_files()`, `extract_snippets()`, `compile_context()` signatures
**Non-goals:** markdown rendering, CLI wiring
**Validation:** unit tests for ranking scores, snippet anchors, budget enforcement
**Review lens:** determinism, edge cases (empty index, all-zero scores, large files)

### Packet B — Markdown renderer
**Owned files:** `src/ccw/compile.py` (render function), `tests/test_compile.py` (render tests)
**Contract:** `render_compiled_context(ctx: CompiledContext) -> str`
**Non-goals:** CLI output, file writing
**Validation:** unit tests for frontmatter keys, section order, no markdown injection
**Review lens:** output stability, budget display accuracy, no chunk dump

### Packet C — `ccw compile` CLI surface
**Owned files:** `src/ccw/cli.py`, `tests/test_cli_compile.py`
**Contract:** `ccw compile --task ...` wires classify → recipe → budget → compile → render → write
**Non-goals:** custom formats, multi-output
**Validation:** CLI tests with temp repo + fixture index, golden output file
**Review lens:** argument handling, error paths, output path creation, `compilations` persistence

### Packet D — `ccw validate` CLI surface
**Owned files:** `src/ccw/validate.py`, `tests/test_cli_compile.py` (validate tests)
**Contract:** `ccw validate <path>` checks frontmatter, sections, no invented paths, budget
**Non-goals:** semantic validation, compression validation
**Validation:** CLI tests with valid/invalid artifacts, exit code checks
**Review lens:** error messages, false negatives, cross-check against index

### Packet E — Golden fixture tests
**Owned files:** `tests/fixtures/compile/`, `tests/test_cli_compile.py` (golden test)
**Contract:** deterministic task + fixture index → exact markdown output
**Non-goals:** full coverage of every recipe
**Validation:** snapshot comparison of rendered output against golden file
**Review lens:** fixture stability, output structure, diff readability

**Dependency graph:**
```
Packet A (core) ──→ Packet B (renderer) ──→ Packet C (compile CLI)
                                                      │
                                            Packet D (validate CLI)
                                                      │
                                            Packet E (golden tests)
```

Packet D and Packet C share no write-ownership conflict and can proceed in
parallel after Packets A+B are stable.

## Validation

- Unit test: `rank_files` with task keywords scores matching files highest
- Unit test: `rank_files` git-freshness boost applies correctly
- Unit test: `rank_files` returns at most `max_items` files
- Unit test: `extract_snippets` returns correct `file:start_line:end_line` anchors
- Unit test: `extract_snippets` respects section token budget
- Unit test: `compile_context` produces all required sections
- Unit test: `render_compiled_context` includes all required frontmatter keys
- Unit test: `render_compiled_context` section ordering is deterministic
- CLI test: `ccw compile --task "fix bug"` produces artifact at `--out` path
- CLI test: `ccw compile` without init fails with error
- CLI test: `ccw compile --mode bugfix --task "x"` skips classification
- CLI test: `ccw validate` on valid artifact returns 0
- CLI test: `ccw validate` on artifact with invented path returns 1
- CLI test: `ccw validate` on artifact with missing section returns 1
- CLI test: `ccw validate` on missing file returns error
- Guard test: `compile_context` on 200-file fixture completes under 0.5 seconds
- Project validation: `python -m unittest`

## Premortem-driven controls

- Ranking is purely keyword-overlap + deterministic signals — no ML, no
  stochastic scoring. Substring prefix matching ensures `"auth"` matches
  `"authentication"` directories.
- Snippet extraction reads file content from disk, not from index cache, so
  snippets always reflect current source. Reads at most `max_items` files
  (20-30) with a 40-line cap per snippet for bounded I/O.
- Budget is chars/4 estimation, not exact tokenization — keeps cost low and
  deterministic. Over-budget sections are silently truncated, not error-raised.
  The rendered artifact footer shows `(estimated N tokens / allocated N tokens)`
  for user calibration.
- `compilations` table is append-only with additive future columns (defined via
  `COMPILATIONS_COLUMNS + COMPILATIONS_OPTIONAL_COLUMNS` following the exact
  `_ensure_optional_columns` pattern from `schema.py:209-218`).
- `validate` cross-checks file paths against the current index to prevent
  invented paths without requiring a full scan of the markdown.
- Golden tests compare rendered output as a string with clear diff messages on
  failure. Golden files are per-recipe-mode and kept small (single fixture
  task).

## Performance guard

- `compile_context` on a 200-file fixture repo (20 ranked files, 40-line
  snippets) must complete in under 0.5 seconds on a standard developer
  machine. Add a `@slow` unit test with a timer assertion.

## Done when

- `rank_files()` returns correctly scored, bounded file lists for any indexed repo
- `extract_snippets()` returns stable line-anchored snippets under budget
- `compile_context()` produces a complete `CompiledContext` with all sections
- `render_compiled_context()` produces valid markdown with YAML frontmatter
- `ccw compile --task "..." --out output.md` produces a correct artifact file
- `ccw validate artifact.md` returns 0 for valid artifacts, 1 with errors for invalid
- Schema upgrade path handles placeholder `compilations` table
- Golden test shows stable rendered output for a fixture task
- `python -m unittest` passes with all new and existing tests
