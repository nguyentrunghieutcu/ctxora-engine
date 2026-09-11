# Phase 0 migration map

Baseline date: 2026-09-09

## Current public seams

- CLI: `harness_context.cli.app:main` and npm `bin/ctxora.mjs`.
- MCP: `harness_context.server` compatibility surface and MCP v2 contracts.
- Python: `harness_context.engine.ContextEngine` facade plus legacy top-level packages.
- State: workspace-local `.ctxora/` with legacy `.harness-context/` fallback.
- Artifacts: root `agents/`, `commands/`, `skills/`, and vendored ECC skills under the package.
- Install ownership: client config ownership plus destination-hash skill manifests.

## Legacy import migration order

1. `evaluation`
2. `compact`
3. `chunking`
4. `retrieval`
5. `memory`
6. `context`

Each move updates internal imports first, retains a deprecated forwarding package for one release,
and adds an architecture gate preventing new legacy imports.

## Release-window cleanup status

As of 2026-09-09, canonical packages and artifact manifests are active, but the root artifact projections and deprecated Python forwarding packages remain supported compatibility surfaces. Phase 8 does not remove them because one full release window has not elapsed. The next cleanup release may remove a projection or forwarding import only after package consumers have migrated and the architecture/packaging gates are updated in the same change.

The CTXORA Console safe-action surface does not expand this compatibility contract. It is limited to refresh, invalidate, expired-handoff purge, index repair, diagnostics export under `.ctxora/exports/`, and non-mutating install preview.

## Baseline verification

- Python suite: 85 passed.
- npm launcher suite: 5 passed.
- packaging/E2E/security/evaluation subset: 10 passed.
- Topology audit: passed as part of the focused suite.

No skipped validation was reported by these commands.
