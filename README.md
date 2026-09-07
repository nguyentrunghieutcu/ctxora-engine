<div align="center">

<a href="https://ctxora-landing.vercel.app/">
  <img src="assets/ctxora-app-icon.png" alt="CTXORA icon" width="128" height="128">
</a>

# CTXORA Engine

### Index once. Ground every agent.

**Local-first context engine for coding agents.**

[![CI](https://github.com/nguyentrunghieutcu/ctxora-engine/actions/workflows/ci.yml/badge.svg)](https://github.com/nguyentrunghieutcu/ctxora-engine/actions/workflows/ci.yml)
[![npm](https://img.shields.io/npm/v/ctxora?logo=npm)](https://www.npmjs.com/package/ctxora)
[![skills.sh](https://skills.sh/b/nguyentrunghieutcu/ctxora-engine)](https://skills.sh/nguyentrunghieutcu/ctxora-engine)
[![Python](https://img.shields.io/badge/Python-3.10--3.13-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-22c55e.svg)](LICENSE)
[![Local first](https://img.shields.io/badge/Context-local--first-7c3aed)](#privacy-and-security)
[![Plan](https://img.shields.io/badge/CTXORA_Free-unlimited-0ea5e9)](docs/PRICING.md)

**English** · [Tiếng Việt](README.vi.md)

[Website](https://ctxora-landing.vercel.app/) · [Quick start](#quick-start) · [Installation](#installation) · [Agent skills](#agent-skills) · [CLI](#cli-reference) · [MCP](#mcp-tools) · [Security](#privacy-and-security)

</div>

> [!IMPORTANT]
> **Official sources:** use the `ctxora` package on npm or this GitHub repository. The `ctxora-engine` package is not published on PyPI. Third-party packages using the CTXORA name are not maintained or reviewed by this project.

CTXORA Engine builds a reusable, local representation of a repository and supplies the right evidence to Codex, Claude Code, Cursor, GitHub Copilot, or any MCP-compatible agent. Source code, indexes, embeddings, graph data, memory, and handoffs remain on your machine.

## Quick start

```bash
npx ctxora setup --workspace /path/to/your/project
npx ctxora index --workspace /path/to/your/project
npx ctxora explain --workspace /path/to/your/project \
  "Where is authentication implemented?"
```

Expected output is structured JSON containing relevant files, symbols, dependency signals, provenance, coverage diagnostics, and recommended tests or conventions when available.

## Why CTXORA?

Coding agents often spend tokens rediscovering a repository, select the wrong layer, miss local conventions, or lose context between sessions. Static instruction files help, but they cannot select task-specific evidence.

CTXORA adds a local context layer:

```text
Repository
   ↓ scan, parse, chunk
Immutable local snapshot
   ↓ lexical + semantic + symbol + path + graph indexes
Context planner
   ↓ CAG / RAG / long context / graph-augmented retrieval
Codex · Claude Code · Cursor · Copilot · MCP clients
```

- **Fewer wrong edits** — retrieve the module, dependency path, and tests related to the task.
- **Less repeated prompting** — reuse repository knowledge across agent sessions.
- **Agent-neutral context** — one engine serves multiple coding tools.
- **Private by default** — no hosted index, remote telemetry, or required cloud account.
- **Deterministic evidence** — every retrieved item includes source path and provenance.

## What you get

### Local context engine

- AST-aware chunking for Python, JavaScript, and TypeScript, with bounded fallback chunking for other text formats.
- Framework-agnostic setup, indexing, retrieval, and MCP startup verified for Python, TypeScript, Flutter, Go, Rust, Java, Kotlin, Swift, PHP, and Ruby repositories.
- Hybrid lexical and local semantic retrieval using BM25, TF-IDF/LSA, keyword overlap, symbols, and paths.
- Code dependency graph traversal and graph-augmented context selection.
- CAG, RAG, hybrid CAG/RAG, long-context, and graph-augmented planning strategies.
- Immutable snapshots with candidate validation, atomic promotion, recovery, and incremental refresh.
- Workspace-scoped SQLite memory and raw conversation handoffs.
- Token budgeting for OpenAI, Anthropic, and Gemini context windows.

### Agent onboarding

```bash
ctxora repo-map --workspace .
ctxora context-score --workspace .
ctxora generate-agents-md --workspace .
ctxora generate-copilot-instructions --workspace .
ctxora generate-cursor-rules --workspace .
```

Generated instruction files are deterministic and are never overwritten unless `--force` is provided.

### Safety and operations

- Canonical workspace-root authorization and symlink-escape rejection.
- Secret-like, binary, dependency, VCS, generated-state, and oversized-file exclusions.
- Retrieved repository content is always treated as untrusted evidence, never as agent instructions.
- Machine-readable diagnostics, context health reports, evaluation gates, and stable CLI exit codes.
- Local `ctxora ci` support for indexing changed files between Git refs.

## Installation

### npm / npx — recommended

```bash
npx ctxora setup --workspace /path/to/your/project
npx ctxora doctor --workspace /path/to/your/project
```

The dependency-free npm launcher bundles the MIT-licensed Python source and installs CTXORA Engine into a versioned local environment. It does not require a global Python package or a cloud account. Python 3.10–3.13 must already be available.

For a persistent shell command:

```bash
npm install --global ctxora
ctxora setup --workspace /path/to/your/project
```

### Install from GitHub

```bash
python3 -m pip install \
  "git+https://github.com/nguyentrunghieutcu/ctxora-engine.git"
```

### Install from a clone

```bash
git clone https://github.com/nguyentrunghieutcu/ctxora-engine.git
cd ctxora-engine
python3 -m pip install .
ctxora doctor --workspace .
```

### Development environment

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
```

Requirements: Python 3.10–3.13 and Git. Runtime state is stored under `.ctxora/`; compatible legacy `.harness/` state remains readable during migration.

## Agent skills

Install all CTXORA skills from this repository:

```bash
npx skills add nguyentrunghieutcu/ctxora-engine
```

Install the curated CTXORA pack:

```bash
npx skills add https://www.skills.sh/p/2fCkKUwjcYsPi0WX
```

List or install one skill:

```bash
npx skills add nguyentrunghieutcu/ctxora-engine --list
npx skills add nguyentrunghieutcu/ctxora-engine --skill ctxora-setup
```

The pack includes setup, grounded repository context, and context-health workflows. The current `skills` CLI requires Node.js 22.20 or newer.

## Connect a coding agent

CTXORA can safely edit supported client configuration while preserving unrelated entries:

```bash
ctxora profile --workspace .
ctxora install --workspace . --profile codex
ctxora install --workspace . --profile claude-code
ctxora install --workspace . --profile cursor
ctxora install --workspace . --profile generic-mcp
```

Use `--dry-run` to preview changes and `--client-config` to target a non-default file. Supported defaults:

| Profile | Default configuration |
|---|---|
| Codex | `~/.codex/config.toml` |
| Claude Code | `~/.claude.json` |
| Cursor | `~/.cursor/mcp.json` |
| Generic MCP | `~/.config/mcp/servers.json` |

Manual MCP configuration:

```json
{
  "mcpServers": {
    "ctxora": {
      "command": "ctxora",
      "args": ["run", "--workspace", "/absolute/path/to/project", "--transport", "stdio"],
      "env": {
        "CTXORA_ALLOWED_ROOTS": "/absolute/path/to/project",
        "PYTHONUTF8": "1"
      }
    }
  }
}
```

Do not commit client configuration containing personal absolute paths.

## Core workflows

### Understand a repository

```bash
ctxora setup --workspace .
ctxora index --workspace .
ctxora query --workspace . "How does request authentication flow?"
ctxora explain --workspace . "Where should token rotation be changed?"
ctxora inspect --workspace . snapshot
```

### Refresh changed files

```bash
ctxora index --workspace . --incremental
ctxora ci --workspace . --base origin/main --head HEAD
```

### Run the MCP server

```bash
# Recommended local transport
ctxora run --workspace . --transport stdio

# Local HTTP transport
ctxora run --workspace . --transport streamable-http \
  --host 127.0.0.1 --port 8765
```

Non-loopback HTTP binding requires `--allow-external` and must be protected by an authorization layer before production use.

### Export local state

```bash
ctxora export --workspace . --output ./ctxora-snapshot.json
ctxora doctor --workspace .
ctxora repair --workspace .
```

## CLI reference

| Command | Purpose |
|---|---|
| `setup` | Create local workspace configuration. |
| `register` | Register and authorize a workspace. |
| `run` | Start CTXORA MCP in the foreground. |
| `start`, `status`, `stop` | Manage the local background process. |
| `index` | Build or refresh the local snapshot. |
| `query` | Return a structured context package. |
| `explain` | Explain where and how a change should be made. |
| `context-score` | Score repository context readiness. |
| `repo-map` | Produce a compact repository map. |
| `inspect` | Inspect workspace, snapshot, bundle, or ECC state. |
| `doctor`, `repair` | Diagnose or rebuild local state. |
| `export` | Export a snapshot to JSON. |
| `profile` | List supported coding-agent profiles. |
| `install`, `uninstall` | Add or remove MCP client configuration safely. |
| `ci` | Refresh files changed between two Git refs. |
| `generate-agents-md` | Generate repository instructions for agents. |
| `generate-copilot-instructions` | Generate GitHub Copilot instructions. |
| `generate-cursor-rules` | Generate Cursor rules. |
| `pro` | Show CTXORA Pro waitlist status; installs no paid functionality. |

All commands support `--workspace`. Run `ctxora <command> --help` for command-specific options.

## MCP tools

CTXORA MCP currently exposes 24 tools.

### Context and workspace

| Tool | Purpose |
|---|---|
| `register_workspace` | Register an allowed repository root. |
| `refresh_workspace` | Build or incrementally refresh its snapshot. |
| `plan_context` | Select the best retrieval strategy for a task. |
| `retrieve_context` | Return ranked evidence with coverage diagnostics. |
| `prepare_context` | Produce the final budgeted context package. |
| `context_stats` | Inspect index and snapshot statistics. |
| `invalidate_context` | Invalidate indexes or cached state. |
| `retrieve_context_legacy` | Compatibility entry point for older clients. |

### Memory and handoffs

| Tool | Purpose |
|---|---|
| `memory_save`, `memory_search`, `memory_inject` | Persist, retrieve, and inject scoped knowledge. |
| `memory_list`, `memory_delete`, `memory_evict`, `memory_stats` | Manage local memory lifecycle. |
| `handoff_conversation` | Store a raw provider-format conversation handoff. |
| `restore_conversation_handoff` | Restore an explicitly selected handoff. |
| `list_conversation_handoffs` | List retained handoffs. |
| `delete_conversation_handoff`, `purge_expired_handoffs` | Remove selected or expired handoffs. |

### Utilities

| Tool | Purpose |
|---|---|
| `estimate_tokens` | Estimate token usage for supplied text. |
| `get_token_budget` | Return model context budget and reserved headroom. |
| `invalidate_cache` | Clear the retrieval cache. |
| `reindex_paths` | Force reindexing for selected paths. |

JSON Schemas for API v2 are published under [`schemas/mcp-v2/`](schemas/mcp-v2/).

## Retrieval strategies

| Strategy | Best for |
|---|---|
| `cag` | Stable instructions and compact repository knowledge. |
| `hybrid_rag` | Focused code questions requiring ranked evidence. |
| `long_context` | Small repositories that fit within the target budget. |
| `hybrid_cag_rag` | Stable guidance plus task-specific code evidence. |
| `graph_augmented` | Architecture, call paths, dependencies, and impact analysis. |

The planner is deterministic and can be overridden when a caller needs a specific strategy.

## ECC integration

CTXORA can read the [`ecc.memory.v1`](https://github.com/affaan-m/ECC) vault format as optional external context. It does not install, clone, invoke, or modify ECC.

```bash
ctxora run --workspace . --transport stdio --ecc
ctxora inspect --workspace . --ecc ecc
```

Project memory at `.ecc/memory` is read-only. User-level memory at `~/.ecc/memory` stays disabled unless `--ecc-user-scope` or `ecc_allow_user_scope = true` is explicitly configured. Imported memories are marked with external provenance and unreviewed trust.

## Architecture

```text
CLI / MCP / CI transports
          ↓
Application services
          ↓
Domain contracts and planning
          ↓
Local scanners · parsers · indexes · graph · snapshots · SQLite
```

Production packages use the `src/` layout. `harness_context` remains the internal Python namespace for compatibility; public branding and commands use CTXORA. See [Architecture](docs/ARCHITECTURE.md) and [OSS release scope](docs/OSS-IMPLEMENTATION-PLAN.md).

## Privacy and security

- No remote telemetry by default.
- No required cloud account or hosted index.
- Workspace roots are explicitly authorized and canonicalized.
- Symlinks cannot escape an authorized root.
- Secret-like and binary files are excluded before indexing.
- Retrieved source is untrusted evidence and cannot override agent instructions.
- External HTTP is opt-in and requires your own authorization layer.

Report vulnerabilities through [GitHub Private Vulnerability Reporting](https://github.com/nguyentrunghieutcu/ctxora-engine/security/advisories/new). If that channel is unavailable, email `nguyentrunghieutcu@gmail.com`. See [SECURITY.md](SECURITY.md).

## Free and Pro

### CTXORA Free — available now

The entire local engine in this MIT-licensed repository is free and unlimited: manual indexing, CAG/RAG/graph retrieval, MCP, local memory, handoffs, health tools, repository maps, and instruction generation.

### CTXORA Pro — waitlist

Planned paid scope is limited to managed repository automation, private workflow operations, and shared team context. Billing, entitlements, hosted automation, and team services are not implemented in this repository. Running `ctxora pro` only returns waitlist information.

See [the product boundary](docs/PRICING.md).

## Project structure

```text
src/harness_context/   Runtime, domain, application, MCP, CLI, storage
src/chunking/          AST-aware and fallback chunking
src/context/           Assembly, sanitization, token budgeting
src/retrieval/         BM25, local embeddings, graph, reranking, cache
src/memory/            Local episodic and vector memory
src/compact/           Provider handoff and compaction helpers
src/evaluation/        Quality metrics and release gates
bin/                   Dependency-free npm/npx launcher
skills/                Installable coding-agent skills
schemas/mcp-v2/        Published API v2 JSON Schemas
tests/                 Unit, security, evaluation, E2E, packaging tests
scripts/               Install, uninstall, migration, topology audit
```

## Development and verification

```bash
npm test
npm pack --dry-run
ruff check .
python scripts/audit_topology.py
python -m unittest discover -s tests -t . -v
python -m evaluation.gates
python -m compileall -q src tests scripts
git diff --check
```

The CI matrix runs on Python 3.10, 3.11, 3.12, and 3.13. Evaluation fixtures cover Python, TypeScript, Flutter, monorepos, Vietnamese content, malicious prompt-like files, long documents, and duplicate symbols.

## Troubleshooting

### `ctxora` is not found

Use the npm launcher without installing a global command:

```bash
npx ctxora --version
npx ctxora doctor --workspace .
```

### Workspace is rejected

Use an absolute existing path and ensure it is included in `CTXORA_ALLOWED_ROOTS` when the MCP client sets an allowlist.

### Existing instruction file is not replaced

This is intentional. Review the generated output path or rerun the generator with `--force` only when replacement is desired.

### HTTP binding is rejected

Loopback is the default security boundary. Use `--allow-external` only behind an authentication and network-access layer you control.

### Local state needs rebuilding

```bash
ctxora doctor --workspace .
ctxora repair --workspace .
```

## Documentation

- [OSS release scope](docs/OSS-IMPLEMENTATION-PLAN.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Operations](docs/OPERATIONS.md)
- [Free and Pro boundary](docs/PRICING.md)
- [Security policy](SECURITY.md)
- [Support policy](SUPPORT.md)
- [Contributing](CONTRIBUTING.md)
- [Changelog](CHANGELOG.md)

## Community

- Open a [GitHub issue](https://github.com/nguyentrunghieutcu/ctxora-engine/issues) for reproducible bugs and feature requests.
- Use private vulnerability reporting for security issues.
- Contributions that preserve the local-first and paid-control-plane independence boundaries are welcome.

## License

CTXORA Engine is released under the [MIT License](LICENSE).
