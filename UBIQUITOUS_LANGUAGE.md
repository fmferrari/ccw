# Ubiquitous Language

## Core compiler terms

| Term | Definition | Aliases to avoid |
| --- | --- | --- |
| **CCW** | The deterministic context compiler product in this repo. | agent framework, orchestrator |
| **Conductor** | The external workflow orchestrator that runs CCW as a script step. | planner inside CCW |
| **Repo index** | The deterministic repository evidence derived from files, symbols, imports, tests, and history. | vector index, embedding store |
| **Compiled context** | The bounded markdown content assembled for one task from deterministic evidence and constraints. | prompt dump, summary blob |
| **Compiled artifact** | The on-disk file that stores one compiled context instance. | prompt file, chat transcript |

## Runtime bootstrap terms

| Term | Definition | Aliases to avoid |
| --- | --- | --- |
| **Local state** | The repo-local runtime files under `.ccw/` for one repository. | cache, docs vault |
| **Init target** | The repository root where `ccw init` materializes local state. | output directory, workspace |
| **State layout** | The required directories and files that must exist in local state after runtime bootstrap. | scaffold, tree |
| **Config file** | The repo-local `.ccw/config.yaml` file that stores stable CCW defaults for one repository. | global config, settings blob |
| **Schema bootstrap** | Deterministic creation of the initial SQLite tables inside local state. | migration, indexing |
| **Snapshot** | A stored repository-state capture under `.ccw/snapshots/` for later deterministic use. | backup, archive |

## Relationships

- `ccw init` materializes **local state** inside the **init target**.
- The **state layout** includes the **config file**, `.ccw/compiled/`, and `.ccw/snapshots/` before **schema bootstrap** lands.
- **Schema bootstrap** adds the SQLite substrate that later stores the **repo index**, **facts**, and **episodes**.
- A **compiled artifact** stores one **compiled context** inside **local state**.

## Example dialogue

> **Dev:** "Does the first Phase 1 slice have to create the SQLite tables too?"
>
> **Domain expert:** "No. First freeze the **state layout** and **init target** contract. **Schema bootstrap** is the follow-on slice."
>
> **Dev:** "So `ccw init` only materializes **local state** and the **config file** for now?"
>
> **Domain expert:** "Exactly. That keeps the first slice small while preserving the path contract for later **repo index** work."
>
> **Dev:** "And the future compiled markdown lives as a **compiled artifact** under `.ccw/compiled/`?"
>
> **Domain expert:** "Yes. The file is the **compiled artifact**; its content is the **compiled context**."

## Flagged ambiguities

- "local state" and "runtime state" were being used interchangeably. Prefer **Local state**.
- "compiled context" and the file under `.ccw/compiled/` were easy to blur together. Use **Compiled context** for the content and **Compiled artifact** for the file.
- "bootstrap" was overloaded to mean both directory creation and SQLite setup. Split the terms into **state layout** or runtime bootstrap vs **Schema bootstrap**.
