# Use Microsoft Conductor as the orchestrator

CCW will stay focused on deterministic repository indexing, explicit memory,
context compilation, validation, and post-run updates, while Microsoft
Conductor owns workflow orchestration, step routing, parallel execution, and
human gates. This keeps CCW inspectable and boring, lets workflows call it as a
normal script step, and avoids rebuilding an agent framework inside the context
compiler itself.
