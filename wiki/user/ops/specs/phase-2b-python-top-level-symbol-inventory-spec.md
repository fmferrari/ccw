---
type: architecture
tags: [architecture, spec, slice, indexing, symbols]
created: 2026-05-23
updated: 2026-05-23
status: archived
---

# Phase 2B Python top-level symbol inventory spec

Superseded by [[phase-2c-deterministic-multi-language-graph-spec]] for the active Phase 2 completion slice.

## Purpose

Extend the deterministic file inventory substrate with the first real symbol
rows by extracting Python top-level declarations during `ccw index`.

This slice deliberately proves one language and one symbol boundary before CCW
takes on imports, edges, exports, or TypeScript/JavaScript parsing.

## In scope

- Extend `ccw index [path]` so Python files also populate `symbols`
- Extract only top-level Python declarations:
  - `class`
  - `def`
  - `async def`
- Persist deterministic symbol rows with:
  - repo-relative file path
  - symbol name
  - symbol kind
  - start line
  - end line
- Refresh symbol rows transactionally on each index run so changed and deleted
  files reconcile cleanly
- Fail loudly on invalid Python syntax and leave the previously indexed SQLite
  state untouched for that run
- Add fixture-backed CLI tests through `ccw index`

## Explicit non-goals

- Python imports, exports, or edges
- Any TypeScript/JavaScript parsing
- Nested or local symbols
- Decorator, docstring, argument, inheritance, or type analysis
- Any new CLI surface beyond `ccw index`
- Ranking, compile, memory, compression, update, or Conductor work

## Contract

1. `ccw index [path]` keeps the shipped Phase 2A file inventory behavior.
2. Python files contribute deterministic `symbols` rows for top-level `class`,
   `def`, and `async def` declarations only.
3. Each symbol row stores:
   - `file_path` as a repo-relative POSIX path
   - `name` as the declared symbol name
   - `kind` as `class`, `function`, or `async_function`
   - `line` as the 1-based starting line number
   - `end_line` as the 1-based ending line number
4. Symbol output order is deterministic from file path order and source order
   within each file.
5. Non-Python files do not populate `symbols` in this slice.
6. The shipped placeholder `symbols` table is upgraded additively when an
   already-bootstrapped repo is indexed.
7. If any Python file in the target repo has invalid syntax, `ccw index` fails
   loudly and does not replace either `files` or `symbols` for that run.

## Proposed modules or surfaces

- `ccw.index` - Python AST extraction and coordinated file/symbol refresh
- `ccw.schema` - additive `symbols` table schema expansion for shipped repos
- `tests/test_cli_index.py` - public CLI coverage for symbol extraction and
  refresh behavior

## Validation

- CLI test: first index run persists deterministic top-level symbol rows for
  Python files
- CLI test: rerunning `ccw index` without repo changes preserves identical
  symbol output
- CLI test: editing a Python file updates symbol rows deterministically
- CLI test: deleting a Python file removes its symbol rows
- CLI test: a repo with the shipped placeholder `symbols` table upgrades
  additively during indexing
- CLI test: invalid Python syntax fails loudly and preserves the previous
  indexed state
- CLI test: non-Python files still only populate `files`
- Project validation: `python -m unittest`

## Premortem-driven controls

- Keep the `symbols` schema minimal so imports, edges, and multi-language work
  can extend it additively instead of inheriting guessed graph fields.
- Freeze the slice to top-level declarations only so nested traversal rules do
  not blur determinism or contract clarity.
- Derive symbol ordering from file path order and source order only, never from
  SQLite row IDs or hash-map iteration.
- Parse all targeted Python files before replacing SQLite state so invalid
  syntax cannot leave a partial refresh behind.
- If the slice needs import targets, export flags, or cross-file edges, it is
  too large and should be split again.

## Done when

- A contributor can run `ccw init` and then `ccw index` to populate `files` and
  Python top-level `symbols`
- Re-indexing reflects changed and deleted Python symbols deterministically
- Invalid Python syntax fails loudly without replacing prior indexed state
- Tests cover happy path, rerun stability, refresh behavior, invalid syntax,
  and placeholder-schema upgrade behavior

## Implementation status

- `ccw index [path]` now preserves the shipped Phase 2A file inventory behavior
  while also extracting Python top-level symbol rows into `symbols`
- Python files contribute `class`, `function`, and `async_function` rows with
  repo-relative file paths and line anchors
- Nested functions and class methods are intentionally excluded from this slice
- Invalid Python syntax now fails the index run before SQLite state is replaced
- The shipped placeholder `symbols` table is upgraded additively when an
  already-bootstrapped repo is indexed
- Validation passes with `python -m unittest` from the repo root

## Follow-on slice

After this slice, the next Phase 2 work is Python import and basic edge
persistence on top of the deterministic file and symbol substrate, followed by
TypeScript/JavaScript parsing.
