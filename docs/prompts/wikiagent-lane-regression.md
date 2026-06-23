# Wikiagent lane regression prompt

Copy/paste this prompt when validating CCW lane behavior end-to-end in
`wikiagent` without requesting new feature implementation.

```text
You are in the `wikiagent` repository.

Goal: run an end-to-end regression audit of CCW lane quality (no feature implementation).

## Rules

- Do NOT implement product changes unless a lane failure is found and explicitly requested.
- Focus on validating lane behavior from compiled context output.
- If behavior is already correct, report "no code changes required".

## Tasks to drive context (run all 3)

1) Implementation-shaped task:
"Refactor retrieval ranking flow for clarity while preserving behavior."

2) Test-shaped task:
"Add regression tests for retrieval ranking stability and tie handling."

3) Docs-shaped task:
"Document retrieval ranking behavior and troubleshooting notes."

## Required process (for each task)

1. Call `prepare_context_payload` with the exact task text.
2. From `compiled_context`, extract:
   - `## Files` (task evidence lane)
   - `## Agentic Context` (project/harness lane)
3. Evaluate assertions:
   - Agentic lane includes anchor/context files when present (`AGENTS.md`, `wiki/AGENTS.md`, `CONTEXT.md`, `wiki/user/index.md`, `wiki/user/log.md`).
   - Task lane matches intent:
     - implementation task => source/implementation files should lead
     - test task => test files should lead
     - docs task => docs/wiki/spec files should lead
   - Vendored/tool copies (`apm_modules/`, `vendor/`, `third_party/`, `node_modules/`) must not dominate either lane.
4. Report pass/fail with evidence (top files and short reason).

## Client update instruction (required)

Before running final verification, ensure wikiagent is using the latest CCW release:

- `pip install -U ccw-mcp` OR `pipx upgrade ccw-mcp`
- for uvx launchers: `uvx --refresh ccw-mcp==0.1.5 --help`
- if using APM: `apm install fmferrari/ccw --target copilot`
- restart the editor/harness process so the MCP server reloads

Then CONFIRM the running server actually loaded the upgrade (a vendored copy or
cached launcher can silently keep an old binary):

```bash
python -c "import ccw, inspect; print(ccw.__version__, inspect.getfile(ccw))"
```

The version must be `0.1.5` and `getfile(ccw)` must point at the upgraded
install (not a vendored `apm_modules/.../ccw` path). If either check fails,
repoint the MCP launch or re-vendor, then restart before auditing.

If this upgrade/verification step is skipped, mark audit confidence as low and explain why.

## Optional checks

- Run existing retrieval-related tests only (no new tests unless requested).
- Confirm no regressions in existing ranking behavior.

## Output format

- Lane audit per task:
  - Task lane files (top N)
  - Agentic lane files (top N)
  - Assertion results (pass/fail + evidence)
- Regression test results (if run)
- Code changes made: "none" or list
- Lane-quality issues and suggested heuristic fixes
- Final verdict: "lane behavior acceptable" or "needs tuning"
```
