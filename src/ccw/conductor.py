from __future__ import annotations

from pathlib import Path


TEMPLATE_RUN_SH = """\
#!/usr/bin/env bash
set -euo pipefail

# ccw-code-task — sample workflow script
#
# This script demonstrates how CCW composes as a set of deterministic
# script steps inside Microsoft Conductor or any workflow orchestrator.
#
# Each step produces a stable output contract (files under .ccw/) that a
# downstream step, agent, or harness can consume without MCP or provider APIs.
#
# Full Conductor workflow packaging and harness adapters live in a
# companion orchestration repo such as ccw-stack, not in CCW core.

CCW="${CCW:-ccw}"
TARGET="${1:-.}"

# Step 1 — Initialize CCW local state
echo "==> ccw init"
"$CCW" init "$TARGET"

# Step 2 — Index the repository
echo "==> ccw index"
"$CCW" index "$TARGET"

# Step 3 — Classify the task (maps to a compile recipe and budget)
echo "==> ccw classify"
MODE=$("$CCW" classify "Fix the login bug" "$TARGET")
echo "Mode: $MODE"

# Step 4 — Compile task-scoped context
echo "==> ccw compile"
"$CCW" compile --task "Fix the login bug" --mode "$MODE" "$TARGET"

# Step 5 — Prepare a portable session bundle
echo "==> ccw session prepare"
"$CCW" session prepare --task "Fix the login bug" --mode "$MODE" "$TARGET"

# Step 6 — Validate the session bundle
echo "==> ccw session validate"
"$CCW" session validate "$TARGET/.ccw/session/latest" "$TARGET"

echo "==> Done. Session bundle ready at $TARGET/.ccw/session/latest/"
echo "    Consume SESSION.md → compiled-context.md → session.json"
"""

TEMPLATE_README = """\
# ccw-code-task

A sample workflow scaffold showing how CCW composes as deterministic script
steps inside Microsoft Conductor or another workflow orchestrator.

## What this demonstrates

| Step | Command | Output |
|------|---------|--------|
| Init | `ccw init` | `.ccw/` runtime directory, SQLite schema, config |
| Index | `ccw index` | `.ccw/index.sqlite`, `.ccw/snapshots/index.json` |
| Classify | `ccw classify` | Mode string (bugfix/implementation/review/refactor) |
| Compile | `ccw compile` | `.ccw/compiled/.../compiled-context.md` |
| Session prepare | `ccw session prepare` | `.ccw/session/latest/` bundle |
| Session validate | `ccw session validate` | Exit code 0 or failure list |

## Consumption contract

The session bundle at `.ccw/session/latest/` is the stable handoff:

- `SESSION.md` — model-facing instructions (read this first)
- `compiled-context.md` — grounded, budgeted context artifact
- `session.json` — machine-readable metadata (mode, budget, index hash, timestamps)

Any workflow step, agent, or harness can consume these files directly
without MCP, provider APIs, or CCW itself.

## Companion repo boundary

CCW owns this deterministic pipeline. A companion orchestration repo such as
`ccw-stack`, when used, should own:

- Conductor workflow definitions that wrap these steps
- Harness-specific adapters and session attachment
- Optional portable brain behavior
- Planner/implementer/reviewer run contracts

See the CCW repository docs for the full ownership split:
https://github.com/fmferrari/ccw/blob/main/wiki/user/architecture/ccw-stack-companion-boundary.md

## Usage

```bash
chmod +x bin/run.sh
./bin/run.sh /path/to/target/repo
```

Or run individual steps through the orchestrator of your choice.
"""


def scaffold_conductor_workflow(
    output_dir: Path,
) -> Path:
    scaffold_root = output_dir / "ccw-code-task"
    scaffold_root.mkdir(parents=True, exist_ok=True)

    bin_dir = scaffold_root / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)

    run_sh_path = bin_dir / "run.sh"
    run_sh_path.write_text(TEMPLATE_RUN_SH, encoding="utf-8")

    readme_path = scaffold_root / "README.md"
    readme_path.write_text(TEMPLATE_README, encoding="utf-8")

    return scaffold_root
