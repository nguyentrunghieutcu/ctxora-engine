# CTXORA Engine v6.2 — OSS Implementation Plan

Status date: **2026-09-04**
Source of truth: `CTXORA-Project-Structure-and-Run-Flow.md` plus the current repository.

This is the living implementation ledger for the public OSS repository. It records
working behavior separately from the final module topology so a prototype is not
mistaken for a completed architecture.

## Status legend

- **Done**: behavior, tests, packaging and documentation meet the current OSS acceptance criteria.
- **Partial**: working baseline exists, but one or more required boundaries, artifacts or gates are missing.
- **Not started**: no production implementation exists.
- **Deferred**: intentionally outside the OSS release scope.

## Locked architecture decisions

1. One deployable modular monolith; no core microservices.
2. CLI, MCP and CI remain thin transports over application services.
3. Domain logic must not depend on transports, vendors, billing or control-plane code.
4. Each request reads one immutable workspace snapshot.
5. Refresh builds a candidate and atomically promotes it; readers never see partial indexes.
6. Core OSS and the future paid control plane remain independent repositories and trust boundaries.
7. ECC is optional, local and read-only; it is never cloned or installed by CTXORA Engine.
8. Source, indexes, embeddings, CAG, graph, memory and handoffs stay customer-owned by default.

## OSS completion audit — 2026-09-04

| # | Roadmap implementation order | Status | Implemented now | Remaining for Done |
|---|---|---|---|---|
| 1 | Freeze API v2 schemas and contract tests | **Done** | Completed and covered by the Phase A–F implementation and release gates. | None for the OSS definition of done. |
| 2 | Bootstrap, runtime and application container | **Done** | Completed and covered by the Phase A–F implementation and release gates. | None for the OSS definition of done. |
| 3 | Thin MCP transport | **Done** | Completed and covered by the Phase A–F implementation and release gates. | None for the OSS definition of done. |
| 4 | Workspace registry, authorization and immutable snapshots | **Done** | Completed and covered by the Phase A–F implementation and release gates. | None for the OSS definition of done. |
| 5 | Scanning, chunking and indexing behind RefreshService | **Done** | Completed and covered by the Phase A–F implementation and release gates. | None for the OSS definition of done. |
| 6 | Planner, retrieval, graph and selection behind services | **Done** | Completed and covered by the Phase A–F implementation and release gates. | None for the OSS definition of done. |
| 7 | Atomic candidate build and promotion | **Done** | Completed and covered by the Phase A–F implementation and release gates. | None for the OSS definition of done. |
| 8 | Canonical ctxora run and lifecycle | **Done** | Completed and covered by the Phase A–F implementation and release gates. | None for the OSS definition of done. |
| 9 | Local storage migration and recovery | **Done** | Completed and covered by the Phase A–F implementation and release gates. | None for the OSS definition of done. |
| 10 | Installer ownership and rollback lifecycle | **Done** | Completed and covered by the Phase A–F implementation and release gates. | None for the OSS definition of done. |
| 11 | Codex, Claude Code and Cursor adapters | **Done** | Completed and covered by the Phase A–F implementation and release gates. | None for the OSS definition of done. |
| 12 | GitHub Actions one-shot CI mode | **Done** | Completed and covered by the Phase A–F implementation and release gates. | None for the OSS definition of done. |
| 13 | ECC read-only adapter | **Done** | Completed and covered by the Phase A–F implementation and release gates. | None for the OSS definition of done. |
| 14 | E2E, security and evaluation gates | **Done** | Completed and covered by the Phase A–F implementation and release gates. | None for the OSS definition of done. |
| 15 | CTXORA Pro automation and team context | **Deferred** | CTXORA Pro is waitlist-only. Managed automation, private workflows and team context remain outside OSS. | Validate demand before building billing, entitlements or a paid control plane. |

## Implemented capability notes

### Runtime and consistency

- Workspace identity and bootstrap composition are implemented in `harness_context/bootstrap.py`.
- Runtime configuration, warm recovery and MCP startup are implemented in `harness_context/runtime.py`.
- Candidate refresh and atomic persisted promotion are implemented by
  `harness_context/application/services.py` and `harness_context/storage/snapshots.py`.
- Incremental refresh replaces changed files without dropping unrelated indexed files.

### Context engine

- Provider-neutral API v2 package: `harness_context/api/v2/models.py`.
- Local hybrid semantic, lexical, symbol and path fusion, CAG bundles, code dependency expansion,
  long-context routing and budgeted selection: `harness_context/engine.py`.
- Workspace-scoped memory and raw conversation handoffs use local SQLite storage.

### Security and external context

- Authorized roots, path isolation, ignore rules and resource limits: `harness_context/workspace.py`.
- Secret-like values in ordinary source files are excluded by
  `harness_context/security/secret_patterns.py`.
- ECC integration is under `harness_context/adapters/ecc/` and never writes to ECC or CTXORA memory.

### Operations and quality

- Canonical CLI commands and one-shot CI entrypoint: `harness_context/cli/app.py`.
- MCP API v2 tools: `harness_context/mcp/server.py`.
- GitHub Actions matrix: `.github/workflows/ci.yml`.
- Executable retrieval quality gate: `evaluation/gates.py`.
- Unit, ECC, security, evaluation and CLI E2E suites live under `tests/`.

## Delivery phases

### Phase A — Contract and module boundaries (P0) — **Done**

Goal: freeze public contracts before moving implementation files.

- Export all MCP v2 JSON Schemas under `schemas/mcp-v2/`.
- Split API requests, responses, diagnostics, enums and typed errors.
- Introduce application command/query interfaces and dedicated services.
- Split MCP lifecycle, middleware, error mapping, capabilities and tools.
- Add import-boundary tests enforcing transport → application → domain/ports.

Exit criteria: schema tests pass; transports contain no retrieval, indexing or persistence decisions.

### Phase B — Workspace, snapshot and persistence core (P0) — **Done**

Goal: complete the immutable snapshot consistency model.

- Extract workspace identity, policy, roots, state machine and lock modules.
- Add explicit snapshot pinning for every context request.
- Add candidate build records and validation before promotion.
- Introduce versioned migrations and recovery/rollback integration tests.
- Preserve old active snapshots during refresh and degraded provider failures.

Exit criteria: concurrent requests observe exactly one snapshot ID; failed builds never alter active state.

### Phase C — Deep application and domain modules (P0) — **Done**

Goal: remove the current `ContextEngine` god-module without changing behavior.

- Extract scanning, manifest, fingerprints and change-set calculation.
- Extract parser dispatcher, stable chunk IDs and bounded fallback windows.
- Extract lexical, semantic, symbol and path indexes behind ports.
- Extract planner, rank fusion, graph expander, CAG store, selector and coverage policy.
- Keep local infrastructure as the default implementation.

Exit criteria: `ContextEngine` becomes a compatibility facade; domain modules import no CLI/MCP code.

### Phase D — Installer and client adapters (P1) — **Done**

Goal: provide safe adoption and removal for real coding clients.

- Implement mutation plans, dry-run, atomic backups and ownership manifests.
- Make uninstall preserve indexes/data unless `--delete-data` is explicit.
- Add Codex, Claude Code, Cursor and generic MCP profiles.
- Add provider formatters that preserve warnings and provenance exactly.

Exit criteria: installer round-trip tests prove unrelated client configuration is unchanged.

### Phase E — CI and operational hardening (P1) — **Done**

Goal: make local and GitHub execution predictable and diagnosable.

- Add least-privilege workflow permissions and fork-safe behavior.
- Cache customer-owned snapshots and emit machine-readable health reports.
- Add request IDs, redacted structured events and local metrics.
- Add readiness, graceful drain and deterministic exit/error mapping.

Exit criteria: CI cache misses do not affect correctness and telemetry contains no paths, queries or source text.

### Phase F — Full OSS release gates (P1) — **Done**

Goal: satisfy the complete fixture and performance matrix.

- Add Python, TypeScript, Flutter, monorepo, Vietnamese, malicious, duplicate-symbol and long-document fixtures.
- Compare RAG, full context, CAG, hybrid and graph-augmented strategies.
- Measure freshness, cold/warm latency, p50/p95 and token cost.
- Add packaging/install/uninstall tests in clean environments.

Exit criteria: every release quality gate in the roadmap is automated and blocking in CI.

### Phase G — OSS release completion (P2) — **Done**

Goal: publish a repository matching the documented topology and operator experience.

- Move to the final `src/harness_context/` package layout after Phases A–C stabilize imports.
- Add examples, schema artifacts, migrations, installer scripts, support policy and architecture docs.
- Generate a topology audit in CI so required OSS artifacts cannot disappear silently.

Exit criteria: the OSS definition of done is met; no paid control-plane dependency is required to install or run.

## Release status

Phases A–G are complete as of 2026-09-04. Future work must preserve the frozen API v2 contracts, local-first operation, and the blocking release gates.

## Implementation log

### 2026-09-04

- Completed Phases A–G and migrated all production packages to the final `src/` topology.
- Moved the MCP compatibility implementation into `harness_context.server`; root `server.py` is shim-only.
- Added examples, complete schema documentation, migration and installer scripts, support policy, architecture and operator guides.
- Added a deterministic topology and OSS-independence audit as a blocking CI gate.
- Verified unit, evaluation, packaging, compile, topology, diff, and lint release gates.

### 2026-09-03

- Added modular runtime/bootstrap/application baseline and immutable snapshot persistence.
- Added workspace isolation, scanning limits, secret/binary/symlink exclusions and incremental refresh.
- Added hybrid retrieval, CAG, code dependency graph, strategy planner and structured context packages.
- Added memory and raw handoff lifecycle with workspace scope.
- Added canonical CLI, stdio/streamable HTTP MCP runtime, watcher and CI command.
- Added optional read-only adapter for `affaan-m/ECC`.
- Added security, evaluation and CLI E2E gates; current suite contains 25 passing tests.
