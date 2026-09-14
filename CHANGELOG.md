# Changelog

## 6.5.0 — 2026-09-14

- Added target-aware instruction generation during install for Codex, Claude Code, Cursor, generic MCP clients, and Copilot.
- Added compact CTXORA context, memory, checkpoint, handoff, security, and review guidance to generated agent instructions.
- Added conflict-safe previews and regression coverage so install never overwrites existing instruction files or fans out to unselected targets.
- Incorporated compatible ECC workflow practices without imposing ECC-specific agent counts, mandatory TDD, or universal coverage targets.

## 6.4.0 — 2026-09-08

- Added explicit Codex, Claude, Cursor, Gemini, and OpenCode project skill targets with multi-target preview, ownership, conflict protection, and pruning.
- Added validation-gated feedback policy metadata so agents retain route IDs and automatically reinforce skills only after successful validation.

## 6.3.0 — 2026-09-08

- Vendored the 286-skill ECC catalog pinned at commit `e04ea0b9cc8248686edf5ac751cadff550e162b8`, including provenance and MIT license copies.
- Added skill-only `minimal`, `opencode`, `core`, `developer`, `security`, `research`, and `full` profiles with module- and skill-level customization.
- Added safe `ctxora skills profiles|modules|list|preview|install` workflows with conflict detection, optional pruning, and per-output ownership manifests.
- Added automatic profile-scoped skill routing to `prepare_context`, the CLI, and MCP.
- Added privacy-safe project feedback learning with confidence smoothing, decay, bounded pending routes, and no raw task storage.
- Added CTXORA navigation, learning, profile, command, and Claude Code plugin templates.

## 6.2.2 — 2026-09-07

- Made workspace scanning framework-agnostic and pruned generated outputs before indexing.
- Added full-flow MCP readiness coverage across ten language and framework ecosystems.

- Made workspace scanning framework-agnostic by honoring directory-style ignore rules and excluding generated outputs across common language ecosystems.
- Added full-flow MCP readiness coverage for Python, TypeScript, Flutter, Go, Rust, Java, Kotlin, Swift, PHP, and Ruby repositories.

### CTXORA rebrand — 2026-09-04

- Renamed the public brand to CTXORA, the product to CTXORA Engine, and the MCP server to CTXORA MCP.
- Renamed the distribution to `ctxora-engine` and public commands to `ctxora` and `ctxora-mcp`.
- Added `.ctxora` state/config defaults while preserving reads from legacy `.harness` workspaces.
- Adopted the tagline “Index once. Ground every agent.” and the description “Local-first context engine for coding agents.”
- Defined CTXORA Free as the unlimited local engine and reserved managed automation, private workflows and team context for CTXORA Pro.
- Added local Free onboarding commands for repository explanation, context scoring, repository maps and instruction generation; CTXORA Pro now reports waitlist status only.

## 6.2.1 — 2026-09-07

- Fixed CLI Python discovery to prefer supported versioned interpreters from Python 3.10 through 3.13.
- Added CTXORA landing-page metadata and README branding assets.

### 2026-09-04

- Completed OSS implementation Phases A–G.
- Migrated production packages to the final `src/` layout and moved the server implementation into `harness_context.server`.
- Added examples, schema and migration documentation, installer scripts, support policy, architecture and operations guides.
- Added a deterministic, blocking topology and paid-control-plane independence audit.

- Added executable security, retrieval evaluation, and CLI end-to-end release gates.
- Added secret-like credential exclusion for ordinary indexed source files.
- Added a living phased OSS implementation plan with audited Done/Partial/Deferred status.

## 6.2.0 — 2026-09-03

- Added the MCP API v2 context engine and compatibility adapter.
- Added authorized workspace scanning, deterministic chunks, hybrid retrieval, CAG and code graph support.
- Added immutable candidate snapshots, atomic promotion, warm recovery and optional workspace watching.
- Added the canonical CLI and thin MCP runtime transport.
- Added workspace-scoped memory and handoff lifecycle controls.
- Added an optional read-only adapter for ECC `ecc.memory.v1` project and user vaults.
