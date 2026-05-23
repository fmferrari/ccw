# Agent Layout

`.opencode/agents/` is the canonical agent-prompt source for opencode in this
repo.

- opencode loads project agents from this directory
- this repo intentionally keeps only three custom agents:
  - `capability-plan-manager`
  - `capability-developer`
  - `capability-reviewer`
- when agent behavior changes, update `.opencode/agents/` first
- keep the prompts aligned with the local PRD, roadmap, slice-spec, and wiki
  workflow artifacts
