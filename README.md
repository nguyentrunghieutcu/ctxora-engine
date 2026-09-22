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

### Set up your project

Run these commands from the repository you want your coding agent to understand:

```bash
npx ctxora setup --workspace .
npx ctxora index --workspace .
npx ctxora install --workspace . --profile claude-code --dry-run
npx ctxora install --workspace . --profile claude-code
npx ctxora explain --workspace . \
  "Where is authentication implemented?"
```

Then restart your coding client. The first two commands create and index the local workspace; `install` connects the MCP server to Claude Code. Use `--profile codex`, `--profile cursor`, or `--profile generic-mcp` for another client. Expected query output is structured JSON containing relevant files, symbols, provenance, coverage diagnostics, and recommended tests when available.

If you only want the CLI, run `npx ctxora query --workspace . "your task"`. If setup fails, run `npx ctxora doctor --workspace .` before retrying.

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

Starting with `6.5.0`, interactive npm launcher sessions check for a newer stable release at most once per 24 hours and print a notice only. Disable the check with `CTXORA_NO_UPDATE_CHECK=1`. Updates are never applied silently:

```bash
ctxora update check --workspace .
ctxora update plan --workspace .
ctxora update apply <plan-digest> --workspace . --yes
```

Apply is restricted to the validated npm version, verifies the global installation, reapplies CTXORA-owned MCP profiles and unchanged profile-based skill targets, and rolls back on failure. Customized skill selections are reported for manual review.

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

The repository-level pack contains CTXORA's own setup, navigation, repository-context, health, profile, and learning workflows. The current `skills` CLI requires Node.js 22.20 or newer.

CTXORA also vendors the current ECC catalog: 286 skills pinned to ECC commit `e04ea0b9cc8248686edf5ac751cadff550e162b8` on September 8, 2026. Start from an ECC profile, inspect it, then customize modules or individual skills:

```bash
npx ctxora skills profiles --workspace .
npx ctxora skills modules --workspace .
npx ctxora skills preview --workspace . --profile developer
npx ctxora skills preview --workspace . --profile developer \
  --add-module security --remove-skill security-scan
npx ctxora skills install --workspace . --profile developer \
  --add-module security --remove-skill security-scan
ctxora skills install --workspace . --profile developer \
  --target codex --target claude --target cursor --target gemini
ctxora skills route "Fix React hydration performance" --workspace . --profile developer
```

Skill installation defaults to a shared runtime catalog: `--target all` records one workspace profile and five lightweight receipts without copying the catalog into each host. Use `route_skills` or `prepare_context` to inject only relevant instructions. `--delivery materialized` is an explicit compatibility mode for hosts that require local files; `--prune` is required to migrate legacy copies and removes only unchanged CTXORA-owned skills. Preview never mutates files, and customized skills are never overwritten. See `THIRD_PARTY_NOTICES.md` for provenance and licensing.

### Commands and agent roles

CTXORA also ships explicit workflow templates inspired by ECC's command-first entry points:

Canonical reusable guidance lives under `skills/`. Start with `ctxora-navigation` when the right workflow is unclear, use `ctxora-workflow-profiles` to select and customize an ECC skill profile, and use `ctxora-continuous-learning` only after a lesson is verified. See `docs/COMMAND-SKILL-MAP.md` for the compact routing map.

Skill reranking is project-scoped and outcome-driven. Routed tasks remain visible as fingerprint-only pending entries until `skill_feedback` records a verified result; CTXORA does not infer success from Git changes or store raw task prompts. `ctxora skills learning --workspace .` and the local Console show completed outcomes, pending routes, and active boost/penalty signals.

| Command | Use | CTXORA capability |
|---|---|---|
| `/ctxora:context <task>` | Retrieve grounded evidence before coding | `plan_context`, `retrieve_context`, `prepare_context` |
| `/ctxora:route <task>` | Rank profile-enabled ECC skills automatically | `route_skills`, `skill_feedback` |
| `/ctxora:plan <task>` | Create an evidence-based implementation plan | `plan_context`, `retrieve_context` |
| `/ctxora:review [scope]` | Review a change with repository context | `retrieve_context` |
| `/ctxora:health` | Check workspace and index readiness | `doctor`, `context-score`, `inspect` |
| `/ctxora:handoff save\|restore` | Continue work across sessions | handoff MCP tools |

The templates are included in the npm package under `commands/`. In a Claude Code plugin installation, the namespace is `/ctxora:<command>`. If you copy a file manually into a host command directory, use the host's naming convention; clients without custom slash commands can invoke the same workflow as a normal prompt. The MCP server alone does not register slash commands.

#### Enable the slash commands in Claude Code

This workflow requires Claude Code installed and authenticated, plus the MCP setup above. The plugin files are included starting with npm `6.3.0` and are also available from a source checkout containing `.claude-plugin/plugin.json`, `commands/`, and `agents/`.

Replace both paths below. Start in **your application repository**, not the CTXORA source repository:

```bash
cd "/absolute/path/to/your/project"
claude --plugin-dir "/absolute/path/to/ctxora-engine"
```

Pass `--plugin-dir` again on subsequent launches. Inside Claude Code, run `/help` to check command discovery and `/mcp` to check that CTXORA is connected. These are separate checks. Then try:

```text
/ctxora:plan Add password reset
/ctxora:context Trace the token refresh flow
/ctxora:review
/ctxora:health
```

For the supported Codex or Cursor profile, use `npx ctxora install --workspace . --profile codex` or replace `codex` with `cursor`. Other MCP clients need their own configuration; there is no dedicated Copilot install profile. Installing MCP does not make `/ctxora:*` commands appear automatically. Try this normal chat prompt after connecting:

```text
Use CTXORA retrieve_context for this workspace to find the authentication
implementation and its tests. Cite the files and propose a plan; do not edit yet.
```

If commands are missing, check the plugin path. If commands appear but tools are unavailable, check MCP connection and run `npx ctxora doctor --workspace .` in your application repository. If retrieval is stale, run `npx ctxora index --workspace . --incremental`.

#### Which agent should I use?

Choose the role that matches the work:

| Need | Role | Use when |
|---|---|---|
| Ground repository context | `ctxora-context-engineer` | The task spans unfamiliar or multiple files. |
| Plan an implementation | `ctxora-planner` | You need files, dependencies, risks, tests, and success criteria before edits. |
| Research a question | `ctxora-researcher` | You need repository evidence plus clearly attributed primary sources. |
| Review a proposed change | `ctxora-reviewer` | You need findings, not autonomous implementation. |
| Maintain setup and session state | `ctxora-maintainer` | You need indexing, diagnostics, memory, or handoffs. |

These are role prompts, not separate LLMs. Your host agent remains responsible for edits; CTXORA supplies local context, memory, and handoff tools. Canonical templates are packaged under `src/harness_context/artifacts/canonical/`; `agents/`, `commands/`, and `skills/` are generated compatibility projections for the Claude plugin and npm ecosystem.

To request one explicitly in a host that has loaded these agents, say: "Use the ctxora-reviewer agent to review my uncommitted changes; report findings without editing." Otherwise ask the current assistant to perform that role; do not assume a separate agent was launched. Start with `plan` for a feature, implement and run your project's tests, then use `review`. For a bug, reproduce it first and retrieve the relevant code before changing it.

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

### Accurate Setup Guide for New Projects

When configuring CTXORA for a new project (especially with **Codex CLI** or other coding agents), follow these two core rules to avoid runtime path drift and namespace protocol errors:

#### 1. Stable Runtime Path (`runtime/current`)

Starting from `6.5.5`, CTXORA automatically maintains a symlink at `~/.local/share/ctxora/runtime/current` pointing to the latest versioned runtime. Never hardcode an old version directory (e.g. `.../runtime/6.5.4/...`) to prevent configuration breaks across updates.

- **Automated setup for Codex** (project-scoped to avoid overriding global config):
  ```bash
  ctxora install --workspace . --profile codex --client-config .codex/config.toml
  ```

- **Standard `.codex/config.toml` in the project**:
  ```toml
  [mcp_servers.ctxora]
  command = "/Users/<username>/.local/share/ctxora/runtime/current/venv/bin/python"
  args = ["-m", "harness_context.cli.app", "run", "--workspace", "/absolute/path/to/project", "--transport", "stdio"]

  [mcp_servers.ctxora.env]
  CTXORA_ALLOWED_ROOTS = "/absolute/path/to/project"
  PYTHONUTF8 = "1"
  ```
  *(Or use `command = "ctxora"` and `args = ["run", "--workspace", ".", "--transport", "stdio"]` if global CLI is installed)*

- **Standard `.mcp.json`** (Claude Code / Cursor / generic MCP):
  ```json
  {
    "mcpServers": {
      "ctxora": {
        "command": "/Users/<username>/.local/share/ctxora/runtime/current/venv/bin/python",
        "args": [
          "-m",
          "harness_context.cli.app",
          "run",
          "--workspace",
          "/absolute/path/to/project",
          "--transport",
          "stdio"
        ],
        "env": {
          "CTXORA_ALLOWED_ROOTS": "/absolute/path/to/project",
          "PYTHONUTF8": "1"
        }
      }
    }
  }
  ```

#### 2. Codex CLI Best Practice: CLI Execution Over Terminal (Avoid Namespace Errors)

Codex CLI enables **Dynamic Tool Discovery** by default, wrapping external MCP servers under `default_api:mcp__<server>(reason: String)`. When using third-party API wire protocols, calling this placeholder or direct sub-tools triggers `unsupported call: mcp__ctxora` or `unsupported call: <tool>`.

**Accurate Solution**: Add instructions to the project's `AGENTS.md` (or `.codex/rules/RULE.md`) directing the agent to execute CTXORA operations via shell commands:

```markdown
- **Codex CLI Rule**: Do not call `default_api:mcp__ctxora` or direct MCP function calls if they return `unsupported call`. Execute CTXORA via shell CLI:
  - **Route skills**: `ctxora skills route "<task>" --compact --workspace .`
    *(Compresses token usage from ~7,600 to ~180 tokens)*
  - **Retrieve context**: `ctxora query "<task>" --compact --workspace .`
    *(Filters to `evidence.items` path + line + code, reducing from ~2,300 to ~70 tokens)*
  - **Submit feedback**: `ctxora skills feedback <route_id> --outcome <success|failure|corrected> --workspace .`
  - **Refresh index**: `ctxora index --incremental --workspace .`
```

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
| `dashboard` | Open the loopback-only CTXORA Console with redacted views and allowlisted plan/confirm actions. |
| `update check`, `update plan`, `update apply` | Check, preview and explicitly apply a verified npm update with rollback. |
| `export` | Export a snapshot to JSON. |
| `profile` | List supported coding-agent profiles. |
| `install`, `uninstall` | Add or remove MCP client configuration safely. |
| `skills profiles`, `skills modules`, `skills list` | Inspect the pinned ECC skill catalog. |
| `skills preview`, `skills install` | Start from a profile, customize it, then preview or install selected skills. |
| `skills route`, `skills feedback`, `skills learning` | Route tasks and maintain project-scoped feedback. |
| `ci` | Refresh files changed between two Git refs. |
| `generate-agents-md` | Generate repository instructions for agents. |
| `generate-copilot-instructions` | Generate GitHub Copilot instructions. |
| `generate-cursor-rules` | Generate Cursor rules. |
| `pro` | Show CTXORA Pro waitlist status; installs no paid functionality. |

All commands support `--workspace`. Run `ctxora <command> --help` for command-specific options.

## MCP tools

CTXORA MCP currently exposes 21 tools.

### Context and workspace

| Tool | Purpose |
|---|---|
| `register_workspace` | Register an allowed repository root. |
| `refresh_workspace` | Build or incrementally refresh its snapshot. |
| `plan_context` | Select the best retrieval strategy for a task. |
| `retrieve_context` | Return ranked evidence with coverage diagnostics. |
| `prepare_context` | Produce the final budgeted package with automatic skill recommendations. |
| `context_stats` | Inspect index and snapshot statistics. |
| `invalidate_context` | Invalidate indexes or cached state. |

### Memory and handoffs

| Tool | Purpose |
|---|---|
| `memory_save`, `memory_search` | Persist and retrieve scoped knowledge. |
| `memory_list`, `memory_delete` | Manage local memory lifecycle. |
| `handoff_conversation` | Store a raw provider-format conversation handoff. |
| `restore_conversation_handoff` | Restore an explicitly selected handoff. |
| `list_conversation_handoffs` | List retained handoffs. |
| `delete_conversation_handoff`, `purge_expired_handoffs` | Remove selected or expired handoffs. |

### Skills and ECC

| Tool | Purpose |
|---|---|
| `route_skills`, `skill_feedback`, `skill_learning_status` | Rank enabled skills and learn from verified outcomes. |
| `ecc_status`, `ecc_search` | Inspect and search the optional read-only ECC adapter. |

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

CTXORA has two separate ECC integrations:

- A vendored, pinned skill catalog that can copy selected guidance files into a project. It never executes ECC scripts, enables hooks, or installs external dependencies.
- An optional read-only adapter for the [`ecc.memory.v1`](https://github.com/affaan-m/ECC) vault format. It does not clone, invoke, or modify an external ECC installation.

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
