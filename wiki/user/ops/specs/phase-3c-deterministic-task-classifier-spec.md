---
type: architecture
tags: [architecture, spec, slice, task, classification]
created: 2026-05-25
updated: 2026-05-25
status: active
---

# Phase 3C deterministic task classifier spec

## Purpose

Ship the first deterministic task classifier that maps a plain-text task
description to a stable task mode: bug fix, implementation, review, or
refactor. This is the first step toward compile recipes and budget allocation
in Phase 3D/E.

## In scope

- Add `ccw classify <text>` CLI surface
- Implement a deterministic keyword-based classifier returning one of:
  `bugfix`, `implementation`, `review`, `refactor`
- Store each classification in a new `classifications` table via additive
  schema upgrade
- Print the classification mode to stdout
- Add focused CLI tests for happy path, append-only, missing-init failure,
  empty-text rejection, and placeholder-table upgrade behavior

## Explicit non-goals

- Compile recipes or budget allocation (separate slice after 3C)
- Reading facts or episodes to inform classification during this slice
- ML or LLM-based classification
- Multi-classification or batch classification
- Classification of anything other than free-text task descriptions
- A `classifications` subcommand surface beyond `ccw classify`

## Contract

1. `ccw classify <text>` classifies the given text, stores the result in the
   `classifications` table, and prints the mode to stdout.
2. Classification is deterministic: same input always produces the same mode.
3. Each classified row stores `text`, `mode`, and `created_at` in the
   `classifications` table.
4. Empty text fails loudly with a stable error and no row is written.
5. The shipped placeholder `classifications` table upgrades additively when
   `ccw init` or `ccw classify` touches an already-bootstrapped repo.
6. `ccw init` and `ccw index` preserve previously stored classifications.
7. Output is printed to stdout as a single line containing the mode name.

## Classification rules

Tokenise the input into lowercase space-separated words. Score the input
against four mode keyword sets. The mode with the highest score wins. Ties
and zero-score inputs default to `implementation`.

| Mode | Keywords |
|---|---|
| `bugfix` | fix, bug, error, crash, broken, defect |
| `implementation` | implement, add, feature, create, build, write, new |
| `review` | review, audit, inspect, check, verify |
| `refactor` | refactor, restructure, clean, improve, simplify, extract, consolidate, rename, optimize, modernize, migrate |

Scoring: each occurrence of a keyword in the tokenised input adds 1 to that
mode's score. Ties default to the mode with the earlier definition order:
`review` > `bugfix` > `refactor` > `implementation`.

## Proposed modules or surfaces

- `ccw.cli` - command parsing for `ccw classify`
- `ccw.classify` - deterministic keyword-based classifier and classification-row persistence
- `ccw.schema` - additive `classifications` table schema for shipped repos
- `tests/test_cli_classify.py` - public CLI coverage for classification behavior

## Validation

- CLI test: `ccw classify` on a known keyword set prints the expected mode to stdout
- CLI test: repeated classifies append rows without overwriting prior classifications
- CLI test: missing `.ccw/` local state fails with a stable error
- CLI test: empty input text fails loudly
- CLI test: `ccw init` after classification preserves existing rows unchanged
- CLI test: `ccw index` after classification preserves existing rows unchanged
- CLI test: placeholder `classifications` table upgrades additively during init or classify
- Project validation: `python -m unittest`

## Premortem-driven controls

- Keep keyword lists minimal and discriminating to avoid ambiguous
  classification in the first shipped classifier.
- Use deterministic scoring so every classification is repeatable and
  explainable from the input alone.
- Store classification rows so the compile step (later slice) can read the
  latest classification without re-classifying.
- Tie-breaking by definition-order priority ensures stable output for
  multi-keyword inputs.
- Default to `implementation` for zero-score inputs so new or unusual task
  descriptions still produce a safe default mode.

## Done when

- A contributor can run `ccw classify <text>` and see the mode printed
- Same input always returns the same mode
- Classifications persist append-only through repeated calls
- `ccw init` and `ccw index` preserve previously stored classifications
- Placeholder classification-table state upgrades additively without
  destructive re-init
- Tests cover happy path, append-only, failure modes, and upgrade behavior

## Implementation status

- `ccw classify <text>` classifies plain-text task descriptions deterministically
  using keyword scoring with tie-breaking and prints the mode to stdout
- Classification rows persist in the `classifications` table via additive schema
  upgrade during `ccw classify` or `ccw init`
- Same input always returns the same mode; zero-score inputs default to
  `implementation`
- Empty text fails loudly with a stable error and no row is written
- `ccw init` and `ccw index` preserve previously stored classifications
- Validation passes with `python -m unittest` from the repo root (52 tests)

## Follow-on slice

After this slice, the next planned work is compile-recipe selection and budget
allocation on top of explicit facts, episodes, and task classification.
