# Keep the portable session handoff contract in CCW

CCW will own the provider- and harness-independent file contract that makes a
compiled artifact clearly consumable by a model on a first or later turn,
including the top-level session file, freshness metadata, and stable `.ccw/`
layout. The sibling `ccw-stack` repo will own provider-specific attachment,
re-sending, caching, and session-thread integration for those files. This keeps
compiled-context semantics portable across harnesses without turning CCW into a
session runtime or adapter framework.
