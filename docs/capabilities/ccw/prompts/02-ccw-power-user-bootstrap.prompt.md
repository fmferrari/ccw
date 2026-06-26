Use $ccw-power-user to prepare this repository for CCW-backed agent sessions.

First read the repo instructions and detect whether CCW local state already exists. Run `ccw init` and `ccw index` for the repo, then prepare and validate a session bundle for the task: "Verify CCW setup and project-memory integration." Treat the compiled context as task-scoped and do not reuse stale bundles.

Record explicit CCW facts only when they are already established by repo files or user instructions; do not invent preferences, goals, or decisions. If this session changes source or documentation files, close the loop with `ccw update --run ... --touched-files ...` using repo-relative paths. If no repo files changed, do not force an episode. Report commands run, bundle paths, memory writes, validation results, and any setup gap.
