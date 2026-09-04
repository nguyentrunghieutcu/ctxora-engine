# CTXORA Engine v6.2 — OSS Release Scope

Status: **Released on 2026-09-04**

This document records only the public CTXORA Engine OSS scope. Commercial planning,
managed-service design and internal implementation history are maintained outside this
repository.

## Public product scope

CTXORA Engine is a local-first context engine distributed under the MIT License. The
public release includes:

- Local workspace registration, scanning, indexing and refresh.
- CAG, hybrid retrieval, code graph traversal and context selection.
- Immutable snapshots, local memory and conversation handoffs.
- The `ctxora` CLI and CTXORA MCP API v2.
- Local adapters for supported coding agents and optional read-only ECC context.
- Local health reports, evaluation gates and repository CI tooling.
- Deterministic generation of `AGENTS.md`, Copilot instructions and Cursor rules.

The Free and Pro product boundary is documented in `docs/PRICING.md`. Paid service
implementation and control-plane design are not part of this public repository.

## Architecture guarantees

1. The engine remains local-first and provider-neutral.
2. CLI, MCP and CI transports delegate to application services.
3. Domain logic does not depend on billing, hosted services or a paid control plane.
4. Each context request reads one immutable workspace snapshot.
5. Refresh validates a candidate snapshot before atomic promotion.
6. Source, indexes, embeddings, graph data, memory and handoffs remain customer-owned.
7. External ECC context is optional, explicit and read-only.

## Completed OSS phases

| Phase | Public outcome | Status |
|---|---|---|
| A | API v2 contracts, schemas and compatibility boundaries | **Done** |
| B | Workspace isolation, state, snapshots and recovery | **Done** |
| C | Domain services, indexing, retrieval, CAG and graph | **Done** |
| D | CLI/MCP lifecycle and coding-agent adapters | **Done** |
| E | Security, diagnostics, operations and health reporting | **Done** |
| F | Unit, E2E, packaging and evaluation release gates | **Done** |
| G | Final `src/` topology, release artifacts and CI audit | **Done** |

## Release verification

The public release is blocked unless these checks pass:

```bash
ruff check .
python scripts/audit_topology.py
python -m unittest discover -s tests -t . -v
python -m evaluation.gates
python -m compileall -q src tests scripts
git diff --check
```

The topology audit also rejects paid control-plane dependencies from the OSS runtime.
