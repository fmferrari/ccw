---
type: architecture
tags: [architecture, spec, slice, compiler, pipeline]
created: 2026-05-25
updated: 2026-05-25
status: active
---

# Phase 4.5 - Explicit compiler pass pipeline spec

## Purpose

Refactor `compile_context()` into an explicit pipeline of named compiler passes
with a formal intermediate representation (IR), so the "deterministic context
compiler" claim maps directly to code architecture. No behavioral change —
identical input produces identical output.

This slice addresses the gap called out in external review: the compiler
narrative (Index → Resolve → Expand → Select → Layout → Validate) is convincing,
but the code still runs a single 80-line function. Making the passes explicit
creates clean extension points for Phase 6 compression, future graph-traversal
passes, and independently testable compiler stages.

## In scope

### Pass protocol and pipeline runner
- Add `src/ccw/pipeline.py` with the `Pass` protocol and `CompilationPipeline`
  runner
- Define `CompilationIR` as the explicit intermediate representation between
  passes

### Named passes
Refactor each logical step inside `compile_context()` into a `Pass` subclass:

- `ResolveTaskPass`: classify mode, look up recipe, allocate per-section budgets
- `RankFilesPass`: deterministic file ranking (path tokens + symbol-name boost +
  git freshness — existing `rank_files` logic)
- `ExtractSnippetsPass`: file reading, symbol-aware anchoring, budget-truncated
  snippet extraction (existing `extract_snippets` logic)
- `LoadMemoryPass`: load facts, episodes, constraints, index hash from DB
- `AssemblePass`: build `CompiledContext` from `CompilationIR`

### Module boundaries
- `compile_context()` stays in `compile.py` but delegates to the pipeline
- `pipeline.py` owns the pass definitions and runner
- No change to `render_compiled_context`, `do_compile`, `rank_files`, or
  `extract_snippets` public signatures unless needed for clean pass boundaries

### Tests
- Add tests for `CompilationIR` construction and pass-chaining behavior
- Verify existing golden tests and performance guard still pass
- Verify `ccw compile` CLI behavior is unchanged

## Explicit non-goals

- Behavioral changes to compiler output
- Adding new passes like `CompressPass` or `GraphWalkPass` — those belong in
  Phase 6
- Moving `ccw index`, `ccw classify`, or `ccw validate` into the pipeline
- Changing the `CompiledContext`, `RankedFile`, `Snippet`, or `ContextSection`
  schemas
- Performance optimization — the pipeline runner should add negligible overhead

## Modules and files

```text
src/ccw/pipeline.py          - Pass protocol, CompilationIR, pipeline runner
src/ccw/compile.py           - compile_context() delegates to pipeline
tests/test_pipeline.py       - pipeline unit tests (pass chaining, IR)
tests/test_compile.py        - existing tests must pass unchanged
tests/test_cli_compile.py    - existing CLI tests must pass unchanged
```

## Work packets

### Packet A - Pass protocol, IR, and pipeline runner

- Owner: `capability-developer`
- Owned surfaces: `src/ccw/pipeline.py`, `src/ccw/compile.py`
- Dependencies: existing compile model classes (`CompiledContext`, `RankedFile`,
  `Snippet`, `ContextSection`, `Recipe`)
- Frozen assumptions:
  - `Pass` is a protocol with `def run(self, ir: CompilationIR, target: Path,
    database_path: Path) -> CompilationIR`
  - `CompilationIR` carries task_description, mode, recipe, total_budget,
    section_budgets, ranked_files with snippets, facts, episodes, constraints,
    index_hash
  - `CompilationPipeline` is `list[Pass]`; the runner calls `pass.run(ir, ...)`
    in order, threading the IR through
  - `compile_context()` constructs the pipeline and runs it
- Explicit non-goals:
  - import-time pipeline registry or dynamic pass discovery
  - pass-level parallelism
- Validation target:
  - `CompilationIR` round-trips through all passes without data loss
  - Existing `test_compile_context_creates_all_sections` passes
  - Golden tests pass
- Artifact updates on completion: [[development-plan]],
  [[phase-45-compiler-pipeline-spec]], `wiki/user/log.md`
- Review lens: no behavioral change, clean pass boundaries, minimal new
  abstraction surface

### Packet B - Refactor existing functions into Pass subclasses

- Owner: `capability-developer`
- Owned surfaces: `src/ccw/pipeline.py`, `src/ccw/compile.py`
- Dependencies: Packet A — the `Pass` protocol and `CompilationIR` must exist
- Frozen assumptions:
  - Each pass wraps exactly one existing function or logical group
  - `ResolveTaskPass` calls `classify`, `get_recipe`, `allocate_budget`
  - `RankFilesPass` calls existing `rank_files`
  - `ExtractSnippetsPass` calls existing `extract_snippets`
  - `LoadMemoryPass` calls `_load_facts`, `_load_episodes`,
    `_load_constraints`, `_compute_index_hash`
  - `AssemblePass` builds `CompiledContext` from IR fields
  - Internal helpers (`_base_score`, `_fuzzy_prefix_match`, `_tokenize`, etc.)
    stay in `compile.py` unless a pass boundary cleanly pulls them out
- Explicit non-goals:
  - splitting `RankFilesPass` into sub-passes (path-match, symbol-boost,
    freshness-boost)
  - changing `_load_facts` or `_load_episodes` signatures
- Validation target:
  - `compile_context()` produces identical `CompiledContext` for identical
    inputs before and after the refactoring
  - All existing unit, CLI, and golden tests pass
  - Performance guard still completes under 0.5s
- Artifact updates on completion: [[development-plan]],
  [[phase-45-compiler-pipeline-spec]], `wiki/user/log.md`
- Review lens: pass wiring correctness, no behavior drift, golden-test parity

### Packet C - Pipeline composition tests

- Owner: `capability-developer`
- Owned surfaces: `tests/test_pipeline.py`
- Dependencies: Packets A and B
- Frozen assumptions:
  - Pass chaining is tested: IR fields propagate correctly from one pass to the
    next
  - Pipeline construction can be unit-tested without a real database
  - A `NullPass` or no-op pipeline can be created and run
- Explicit non-goals:
  - full integration test for every pass combination (covered by existing
    compile tests)
  - test coverage for every IR field mutation inside each pass
- Validation target:
  - pipeline unit tests pass in isolation
  - full suite (`python -m unittest`) still passes
- Artifact updates on completion: [[development-plan]],
  [[phase-45-compiler-pipeline-spec]], `wiki/user/log.md`
- Review lens: IR field propagation, null-pipeline behavior, test isolation

## Premortem summary

Failure headline:

- The pass abstraction adds surface area without enough structural value,
  making the code harder to read for no behavioral benefit.

Top risks and controls:

- Over-engineered pipeline: keep the `Pass` protocol minimal (one method, no
  lifecycle hooks) and the `CompilationPipeline` runner trivial (for-loop).
- Behavioral drift during refactoring: rely on golden tests and the performance
  guard as regression detectors.
- Vague pass boundaries: freeze each pass to exactly one existing function or
  logical group; do not invent new decomposition in this slice.
- Users who only need `ccw compile` now import an extra module: keep
  `compile_context()` as the stable entry point; `pipeline.py` is an internal
  detail.

Go recommendation:

- Proceed with all three packets. The structural value (named passes, explicit
  IR, extension points) justifies the small abstraction cost. Keep packets
  strictly no-behavior-change.

## Validation

- `python -m unittest`
- Focus checks:
  - `CompilationIR` carries all fields needed by `AssemblePass` to build a
    `CompiledContext`
  - `compile_context()` returns identical `CompiledContext` before and after
    the refactoring (proven by golden tests)
  - Pipeline runner handles zero-pass and single-pass edge cases
  - `ccw compile --task ... --out ... CLI produces identical output
