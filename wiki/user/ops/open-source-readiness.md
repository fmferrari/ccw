---
type: op
tags: [ops, open-source, release]
created: 2026-05-25
updated: 2026-05-25
status: active
---

# Open-source readiness

## Goal

Make the repository publishable on GitHub with clear usage rights, public
onboarding, contribution entry points, and baseline automation.

## Baseline completed

- added a permissive OSS license and public package metadata
- expanded `README.md` with install, quickstart, development, community, and license guidance
- added `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, and `SECURITY.md`
- added GitHub issue templates, a pull request template, and CI that runs `python -m unittest`
- removed machine-specific absolute paths from tracked opencode config and instructions
- replaced local-sibling assumptions in public-facing docs with repo-stable guidance

## Remaining follow-up

- enable GitHub private vulnerability reporting in repository settings
- publish the first tagged release when the Phase 6 surface is ready
