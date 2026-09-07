# Changelog

## Unreleased

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
