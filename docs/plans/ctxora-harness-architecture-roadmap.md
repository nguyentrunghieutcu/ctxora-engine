# CTXORA harness architecture and Console roadmap

- Date: 2026-09-09
- Goal status: Active
- Inputs: `docs/research/ecc-full-repository-adoption-audit.md`, `docs/research/ecc-scripts-installer-audit.md`, ADR 0001

## Progress

| Phase | Status | Validation |
|---|---|---|
| 0 — Baseline and migration map | Complete | Baseline and migration map captured |
| 1 — Harness and artifact domain | Complete | Typed registry, adapters, fixtures, compatibility alias coverage |
| 2 — Pure resolver and target-aware installer | Complete | Deterministic plans, preflight, stale checks, rollback, receipts |
| 3 — Canonical artifact migration | Complete | Canonical manifest/projections, wheel/npm packaging, 98 Python and 6 npm tests |
| 4 — Validators and compliance | Complete | Schemas, semantic validators, adapter goldens, wheel/package gates; 104 Python and 6 npm tests |
| 5 — Package structure consolidation | Complete | Canonical infrastructure/interfaces, forwarding shims, architecture and clean-wheel gates; 106 Python and 6 npm tests |
| 6 — Operator snapshot module | Complete | Shared versioned/redacted snapshot, cursor events, action receipts; 118 Python and 6 npm tests |
| 7 — CTXORA Console MVP | Complete | Offline loopback-only read-only HTTP/SSE Console with task-learning/rerank visibility; 119 Python and 6 npm tests |
| 8 — Safe actions and cleanup | Complete | Plan/confirm/CSRF/path/audit gates; 127 Python and 6 npm tests |
| 9 — Safe update lifecycle | Complete | Cached no-mutation checks, durable one-time plans, verified apply/rollback, Console preview; 136 Python and 7 npm tests |

## Objective

Refactor CTXORA into one canonical core with an isolated adapter per LLM/harness, then add target-aware artifact installation, portable agents/commands, validation, and a local CTXORA Console without breaking public CLI/MCP behavior or user-owned data.

## Success criteria

- Codex, Claude Code, Cursor, Gemini CLI, and OpenCode are represented by typed capability manifests and adapters.
- Profiles select content only; installs mutate only explicit targets or the documented Codex compatibility default.
- Skills, agents, and commands share one request → resolve → plan → apply → receipt pipeline.
- No canonical artifact is duplicated across harness directories.
- Existing CLI commands, MCP v2 contracts, installed skill ownership, and ECC provenance remain compatible or have tested migrations.
- CTXORA Console works offline on loopback, initially read-only, and uses the same application modules as CLI/MCP.
- Architecture, unit, integration, packaging, migration, and security gates pass with no skipped validation.

## Target structure

```text
src/harness_context/
  domain/
    context/                 # retrieval, planning, budgeting contracts
    artifacts/               # Artifact, Profile, Selection, Plan, Receipt
    harnesses/               # Harness, Target, Capability definitions
    operations/              # operator snapshot and safe-action contracts
  application/
    context/                 # prepare/retrieve/refresh orchestration
    artifacts/               # resolve, plan, install, verify, uninstall
    operations/              # doctor and Console query orchestration
  adapters/
    harnesses/
      codex/
      claude_code/
      cursor/
      gemini/
      opencode/
    persistence/             # snapshots, memory, receipts, events
    ecc/                     # read-only ECC compatibility/provenance
  infrastructure/
    indexing/
    parsing/
    retrieval/
    observability/
    runtime/
  interfaces/
    cli/
    mcp/
    console/
  artifacts/
    canonical/
      agents/
      commands/
      skills/
    manifests/
    schemas/
```

Old import paths remain thin compatibility modules until the final cleanup phase. Target directories contain adapter code and fixtures only, never copied canonical content.

## Phase 0 — Baseline and migration map

Deliverables:

- Freeze current CLI, MCP, package-content, installer, snapshot, memory, and handoff behavior with characterization tests.
- Inventory imports from `chunking`, `compact`, `context`, `memory`, `retrieval`, and `evaluation` into a migration map.
- Record current user-state paths and manifest formats.
- Add a fixture for each supported harness and current installation layout.

Gate: tests reproduce current behavior, including `developer` not implying all targets.

## Phase 1 — Harness and artifact domain

Deliverables:

- Add immutable `Harness`, `Target`, `Capability`, `Artifact`, `ArtifactProfile`, `InstallPlan`, and `InstallReceipt` models.
- Add one registry consumed by profile output, installers, doctor, packaging checks, and future Console queries.
- Encode supported artifact kinds, native roots, scope, config format, and adapter ID per harness.

Gate: adding a fake harness requires only registry data, one adapter, and fixtures; no CLI branching.

## Phase 2 — Pure resolver and target-aware installer

Deliverables:

- Split current skill operation calculation from mutation.
- Resolve profile → modules/artifacts → target compatibility → per-target plans.
- Preflight every requested target before applying any plan.
- Add stable plan digest, locks, staging, rollback, and receipt migration from destination-hash manifests.
- Make `all` explicit and keep profile semantics target-neutral.

Gate: dry-run is deterministic; stale plans and user-modified files fail loud; multi-target failure rolls back owned changes.

## Phase 3 — Canonical artifact migration

Deliverables:

- Move root `agents/`, `commands/`, and installable skill metadata into `artifacts/canonical/` package data.
- Keep compatibility copies or generated package projections only during migration.
- Add `ctxora-planner` and `ctxora-researcher`; retain the current three CTXORA roles.
- Adapt artifacts per harness without fixed model names or undeclared tools.
- Preserve ECC license, source commit, and content hash for derived artifacts.

Gate: package verification proves canonical artifacts and rendered target outputs are synchronized.

## Phase 4 — Validators and compliance

Deliverables:

- Add schemas for harness registry, artifact manifest, install request, plan, receipt, agent, and command definitions.
- Validate IDs, references, capabilities, dependency cycles, Unicode safety, personal paths, provenance, and package contents.
- Add harness adapter compliance tests and golden rendered fixtures.

Gate: invalid references or unsupported target/artifact combinations fail CI before packaging.

## Phase 5 — Package structure consolidation

Deliverables:

- Move legacy top-level Python packages behind `harness_context` domain/infrastructure modules one package at a time.
- Update internal imports first; retain deprecated import shims for one release.
- Move CLI and MCP implementations under `interfaces/` while preserving existing entry points.
- Keep `server.py` as the existing tiny compatibility shim.

Recommended move order: `evaluation` → `compact` → `chunking` → `retrieval` → `memory` → `context`.

Gate: architecture tests reject new imports through legacy paths; clean-wheel and npm launcher tests pass.

## Phase 6 — Operator snapshot module

Deliverables:

- Add a deep `OperatorSnapshot` interface aggregating runtime, workspace, snapshot, index, retrieval, memory, handoff, skills, installer, metrics, and recent-event state.
- Refactor `doctor` to call this module.
- Add cursor-based event queries and explicit safe-action receipts.

Gate: CLI and an in-memory adapter test the same interface the Console will use.

## Phase 7 — CTXORA Console MVP

Deliverables:

- Add `ctxora dashboard --workspace . --open` bound to `127.0.0.1` with an ephemeral or explicit port.
- Provide Overview, Index Health, Retrieval, Memory/Handoffs, Skills, Install Targets, and Events views.
- Use local HTTP JSON plus SSE for updates; no frontend access to storage files.
- Start read-only. Do not add agent spawning, arbitrary shell, git/worktree control, cloud dependencies, or remote binding.

Gate: offline E2E test, loopback/security test, clean shutdown test, and parity tests against `doctor`.

## Phase 8 — Safe actions and cleanup

Deliverables:

- Add confirmed actions for refresh, invalidate, purge expired handoffs, repair index, diagnostics export, and install preview.
- Require action plan/receipt, CSRF protection, path policy, and audit events.
- Remove compatibility artifact projections and deprecated Python imports only after one release window.
- Update migration documentation and release notes.

Gate: no action can execute arbitrary commands or mutate an unplanned target; uninstall restores only CTXORA-owned state.

Implementation note (2026-09-09): the Console exposes only the six allowlisted actions through a short-lived deterministic plan digest and explicit confirmation. The loopback HTTP adapter requires a per-process CSRF token, diagnostics exports are confined to `.ctxora/exports/`, install preview delegates to `SkillCatalog.plan_install()` without applying it, and audit events contain identifiers and outcomes only. Compatibility projections and deprecated Python forwarding imports remain intentionally available for the promised release window; their removal is deferred to the next breaking cleanup after downstream migration evidence is collected.

## Phase 9 — Safe update lifecycle

Deliverables:

- Automatically check the npm release channel at most once per 24 hours for interactive npm-launcher sessions; never auto-apply.
- Add `ctxora update check`, `ctxora update plan`, and confirmed `ctxora update apply` commands.
- Persist deterministic update plans across CLI processes and consume each digest once.
- Restrict apply and rollback to fixed `npm install --global ctxora@<validated-semver>` commands.
- Verify the installed global package version, reapply only CTXORA-owned MCP profiles and unchanged profile-based skill targets, and roll back on any failure.
- Preserve customized skill installations for manual review rather than replacing their selection.
- Store versioned redacted receipts and expose update check/plan through the Console safe-action flow; Console never applies package updates.

Gate: no silent update, arbitrary package/command/version, path traversal, or mutation of user-customized skill selections. Failed verification restores the previous package and owned integrations.

## Delivery slices

Each phase should be a separately releasable slice. Do not combine package moves, installer semantics, and Console UI in one pull request.

Suggested first three implementation changes:

1. Add harness/artifact domain models and registry without changing behavior.
2. Extract `plan_install()` from the current skill installer and add characterization tests.
3. Make `doctor` return a stable operator snapshot contract before building UI.

## Risks

- Import moves can break clean installations even when source-checkout tests pass.
- Package-data changes can silently omit agents/commands/skills from npm or wheel artifacts.
- Target adapters can drift if registry, renderer, and docs are separate sources of truth.
- Multi-target rollback and receipt migration can damage user-modified files if ownership hashes are incomplete.
- A Console with mutation controls increases local attack surface; read-only must ship first.

## Non-goals

- Reimplement ECC or vendor its complete agent/rule/hook catalog.
- Build a cloud control plane, billing layer, or remote dashboard.
- Manage model selection or credentials.
- Spawn and orchestrate coding-agent sessions.
- Change retrieval algorithms merely as part of directory cleanup.
