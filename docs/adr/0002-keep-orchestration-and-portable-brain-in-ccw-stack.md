# Keep orchestration and portable brain work in ccw-stack

CCW will remain focused on deterministic indexing, compiled context,
validation, and post-run updates, while the sibling `ccw-stack` repo owns
Conductor workflows, harness adapters, run manifests, and any optional portable
brain sidecar behavior. This keeps compiler scope tight, prevents harness-
specific concerns from contaminating CCW core, and lets the orchestration layer
evolve without turning CCW into a general agent platform.
