# ADR 0001: Canonical artifacts with harness adapters

- Status: Accepted for planning
- Date: 2026-09-09

## Context

CTXORA currently has separate client configuration, skill installation, root-level agent/command assets, and host path mappings. Adding more ECC-derived agents, commands, validators, and a local console without a shared model would multiply target-specific conditionals and copied content.

## Decision

CTXORA will store each product artifact once in a host-neutral canonical form. Every supported harness will have a capability manifest and adapter that renders only supported artifact kinds into native paths and formats.

Profiles select artifacts. Targets select destinations. A profile must never infer `all` targets.

Installers will resolve an immutable per-target plan before mutation and write an install receipt after successful application. CLI, MCP, and CTXORA Console will call the same application modules rather than read storage or duplicate workflows.

The Console will remain local-only and will start read-only. Session orchestration, arbitrary shell execution, model management, and worktree control are outside this decision.

## Consequences

- Canonical content and workflow logic remain local to one module.
- Harness differences are explicit and testable through adapters.
- Packaging and migration require compatibility shims while old paths are retired.
- Adding a harness requires a manifest, adapter, fixtures, and compliance tests rather than edits across CLI and installers.
- The refactor must proceed incrementally; a big-bang directory move is rejected.

## Rejected alternatives

- One complete copied artifact tree per harness: creates drift and duplicate maintenance.
- Continue with path dictionaries and CLI branching: shallow interface with target knowledge spread across callers.
- Port ECC's full lifecycle/control plane: exceeds CTXORA's local context-engine scope.
