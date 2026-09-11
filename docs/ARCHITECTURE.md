# Architecture

CTXORA Engine is local-first and provider-neutral. Transport code under harness_context.mcp delegates to application services; application services depend on domain contracts; local scanning, parsing, indexing, graph, snapshot, SQLite memory, and handoff implementations live behind those boundaries. Immutable candidate snapshots are validated before atomic promotion, and each context request pins one active snapshot.

All production Python packages use the src layout. harness_context.server owns the MCP compatibility implementation; repository-root server.py only preserves historical source-checkout invocation and imports.

External ECC memory is optional, explicit, read-only, and marked unreviewed. The default runtime has no hosted or paid control-plane dependency.

The CTXORA Console remains a loopback-only adapter over application modules. Mutations cross one safe-action seam: an allowlisted request produces a deterministic short-lived plan, and execution requires both the exact digest and explicit confirmation. The HTTP adapter adds same-origin CSRF protection; application policy confines diagnostics exports to workspace-owned state and keeps install preview non-mutating. Audit events record action identifiers, digests, receipt IDs, and outcomes, never customer paths, queries, or source content.

The product boundary is architectural: CTXORA Free owns the unlimited local engine, while CTXORA Pro may automate customer repositories, manage private workflows and synchronize approved team context from a separate control plane. The paid system must not become a runtime dependency of the local engine.
