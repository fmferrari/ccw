---
type: architecture
tags: [architecture, spec, slice, indexing, graph]
created: 2026-05-23
updated: 2026-05-23
status: active
---

# Phase 2C deterministic multi-language graph spec

## Purpose

Close Phase 2 by extending `ccw index` from file and Python top-level symbol
inventory into a deterministic multi-language repo graph with document
artifacts, git ranking signals, and test-to-source mapping.

This slice completes the Phase 2 substrate without pulling in external parsing
dependencies or full semantic analysis.

## In scope

- Preserve shipped Phase 2A file inventory behavior and Phase 2B Python top-level
  symbol behavior
- Extend Python indexing with:
  - top-level imports
  - deterministic export marking
  - basic local import edges
- Add TypeScript/JavaScript indexing with deterministic support for:
  - top-level `class`, `function`, `const`, `let`, and `var` declarations
  - static `import` statements
  - static `export` forms
  - local relative import and re-export edges only
- Index Markdown, JSON, and YAML files as searchable project artifacts
- Capture nullable git ranking signals per indexed file:
  - last commit timestamp
  - last author identity
  - dominant author identity
  - dominant author commit count
- Map tests to source files when naming or local-import signals are unambiguous
- Refresh files, symbols, edges, document artifacts, and index snapshot output
  transactionally on each run
- Add fixture-backed regression coverage for mixed-language indexing output and
  upgrade paths

## Explicit non-goals

- External parser dependencies such as tree-sitter, Babel, or the TypeScript
  compiler
- Dynamic imports, `require()` graphing, tsconfig aliases, or package-export
  resolution
- Python nested symbol indexing, call graphs, decorator analysis, or inheritance
  graphs
- Markdown section graphs, frontmatter semantics, or YAML schema validation
- SQLite FTS, ranking implementation, or compile behavior
- Blame-level ownership, rename tracking, or probabilistic test inference

## Contract

1. `ccw index [path]` remains the only public indexing surface for Phase 2.
2. Python files produce top-level symbol rows plus deterministic top-level import
   and export signals.
3. TypeScript/JavaScript support is syntax-pattern based and intentionally
   limited to supported static forms; unsupported forms are skipped
   deterministically instead of guessed.
4. Basic edges are limited to repo-local relative import, re-export, and
   test-to-source relationships.
5. Test-to-source edges are created only when naming or local-import evidence is
   unambiguous.
6. Markdown, JSON, and YAML files each produce one searchable artifact row with
   a stable title and normalized search text.
7. Git signals are best-effort and nullable; non-git directories or untracked
   files do not fail indexing.
8. Index refresh remains transactional: collection happens before replacement so
   parse failures preserve the previous SQLite and snapshot state.
9. Index results remain inspectable through SQLite and a deterministic snapshot
   artifact file under `.ccw/snapshots/`.

## Proposed modules or surfaces

- `ccw.index` - multi-language extraction, git metadata capture, test mapping,
  and deterministic snapshot rendering
- `ccw.schema` - additive schema expansion for files, symbols, edges, and
  document artifacts
- `tests/test_cli_index.py` - public CLI coverage for mixed-language indexing,
  regression output, and upgrade behavior

## Validation

- CLI test: Python imports, exports, and local import edges are persisted
- CLI test: Python `__all__` literal lists override default export marking
- CLI test: TypeScript/JavaScript supported static declarations, imports, and
  exports produce stable symbols and edges
- CLI test: Markdown, JSON, and YAML files produce deterministic searchable
  artifact rows
- CLI test: git ranking signals populate for tracked files and stay nullable for
  untracked or non-git repos
- CLI test: test-to-source edges land for unambiguous naming and import cases
  and are skipped for ambiguous cases
- CLI test: rerunning without repo changes preserves stable files, symbols,
  edges, artifacts, and snapshot output
- CLI test: placeholder and partial prior-state schemas upgrade additively
- Project validation: `python -m unittest`

## Premortem-driven controls

- Keep schema additions minimal so later ranking and compile work extend them
  additively instead of inheriting guessed abstractions.
- Freeze TypeScript/JavaScript support to static top-level forms and relative
  module paths only.
- Skip unsupported syntax deterministically instead of inventing partial facts.
- Build all index records before SQLite replacement so parse failures cannot
  leave mixed state behind.
- Emit test-to-source edges only when the mapping is clearly one-to-one.

## Done when

- `ccw index` persists deterministic files, symbols, edges, document artifacts,
  git signals, and test mappings for the supported contract
- Python and TypeScript/JavaScript indexing stay stable across reruns
- Markdown, JSON, and YAML files are inspectable as searchable project artifacts
- Index results are inspectable through SQLite and a deterministic snapshot file
- Regression tests cover mixed-language output, upgrade paths, and failure
  behavior

## Implementation status

- `ccw index [path]` now preserves the shipped Phase 2A and Phase 2B behavior
  while adding deterministic Python import edges, export marking, and
  TypeScript/JavaScript static symbol and local-edge extraction
- Markdown, JSON, and YAML files now persist one searchable artifact row each
  with stable titles and normalized search text
- Indexed files now carry nullable git ranking signals for last commit, last
  author, dominant author, and dominant author commit count when git history is
  available
- Test files now map to source files only when naming or local-import evidence
  is unambiguous
- `.ccw/snapshots/index.json` now captures a deterministic inspectable snapshot
  of files, symbols, edges, and artifacts after indexing
- Placeholder and partial pre-Phase-2C schema shapes upgrade additively during
  indexing without requiring destructive re-init
- Validation passes with `python -m unittest` from the repo root

## Follow-on slice

After this slice, the next planned work is Phase 3 explicit memory and task
recipes on top of the deterministic Phase 2 index substrate.
