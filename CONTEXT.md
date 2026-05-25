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

**Model provider**:
The backend or vendor that serves model inference, such as OpenAI,
Anthropic, OpenRouter, or GitHub Models.
_Avoid_: agent runtime, workflow orchestrator

**Harness**:
The agent runtime or client that talks to a model provider, manages tools, and
attaches CCW artifacts to a session.
_Avoid_: compiler, model vendor

**Session**:
The provider- or harness-level conversation state for one active run or thread.
_Avoid_: durable project memory, compiled artifact

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

**Local state**:
The repo-local runtime files under `.ccw/` that hold config, the index
database, compiled artifacts, snapshots, and append-only memory for one
repository.
_Avoid_: source-of-truth docs, global cache

**Compiled context**:
The bounded markdown artifact produced for a task from indexed repo evidence,
facts, constraints, and exact snippets.
_Avoid_: free-form prompt dump

**Compiled artifact**:
The on-disk file that stores one compiled context instance under CCW local
state.
_Avoid_: ephemeral prompt text, chat transcript

**Session handoff**:
The provider- and harness-independent convention by which CCW presents a
compiled context artifact for model consumption on a first or later turn.
_Avoid_: provider session API, harness-specific prompt injection

**Session bundle**:
The on-disk handoff files that package one compiled artifact with portable
instructions and metadata for model consumption.
_Avoid_: portable brain, chat transcript

**Portable brain**:
The optional `ccw-stack` memory and coordination layer that reuses CCW
artifacts across agents, sessions, and workflows without replacing CCW as the
deterministic source of compiled project context.
_Avoid_: CCW core, source-of-truth project memory

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
- A **harness** talks to a **model provider** and manages one or more
  **sessions**.
- **CCW** materializes **local state** per repository under `.ccw/`.
- A **compiled artifact** stores one **compiled context**.
- A **session bundle** packages a **compiled artifact** for portable model
  consumption.
- The optional **portable brain** lives in **CCW Stack** and reuses
  **session bundles** plus explicit run memory.
- The **repo index** and **facts** feed the **compiled context**.
- **CCW Stack** attaches **session bundles** to provider-specific sessions.
- The **compression layer** can only rewrite an existing **compiled context**.
- **Episodes** update memory inside **local state** after a completed run.

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
