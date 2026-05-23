# CCW

CCW is the deterministic context compiler layer in a repo-aware coding
workflow. It prepares inspectable context artifacts for small-window execution
models and deterministic workflow orchestrators such as Microsoft Conductor.

## Language

**CCW**:
The product in this repo. CCW indexes repositories, stores explicit facts and
episodes, compiles task-scoped context, and updates memory after a run.
_Avoid_: assistant framework, orchestrator

**Conductor**:
The external deterministic workflow orchestrator that calls CCW as a script or
tool step. Conductor owns workflow routing, gates, and execution order.
_Avoid_: planner engine inside CCW

**CCW Stack**:
The companion repo that owns Conductor workflow packaging, harness adapters,
run manifests, and any optional portable brain behavior around CCW artifacts.
_Avoid_: compiler replacement

**Repo index**:
The deterministic representation of repository structure and code facts derived
from files, symbols, imports, history, and tests.
_Avoid_: embedding store, vector index

**Fact**:
An explicit append-only memory entry about project goals, constraints,
decisions, or preferences.
_Avoid_: vague summary, inferred belief

**Episode**:
An append-only record of a completed task or run outcome, including touched
files, summary, and timestamp.
_Avoid_: raw chat transcript

**Compiled context**:
The bounded markdown artifact produced for a task from indexed repo evidence,
facts, constraints, and exact snippets.
_Avoid_: free-form prompt dump

**Compression layer**:
An optional LLM post-process that reduces wording after deterministic context is
assembled. It may shorten, but must not invent.
_Avoid_: source of truth

**Budget**:
The target token or size cap for a compiled context artifact.
_Avoid_: model choice

**Recipe**:
The deterministic context-assembly mode selected for a task class such as bug
fix, implementation, review, or refactor.
_Avoid_: ad hoc prompt

## Relationships

- **Conductor** runs **CCW** as a script step.
- **CCW Stack** orchestrates harness execution around **CCW** artifacts.
- The **repo index** and **facts** feed the **compiled context**.
- The **compression layer** can only rewrite an existing **compiled context**.
- **Episodes** update memory after a completed run.

## Example Dialogue

> **Dev:** "Should CCW decide agent order too?"
>
> **Domain expert:** "No. **Conductor** owns workflow order. **CCW** only
> prepares deterministic context artifacts and post-run updates."
>
> **Dev:** "Then where do multi-harness adapters and optional portable brain
> behavior go?"
>
> **Domain expert:** "In **CCW Stack**, the companion orchestration repo. CCW
> should not absorb that scope."
>
> **Dev:** "So the **compiled context** is what the execution model reads?"
>
> **Domain expert:** "Exactly. The model consumes the **compiled context**,
> while the **repo index** and **facts** remain the deterministic evidence
> underneath it."
