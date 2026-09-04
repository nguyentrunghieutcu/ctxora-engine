# CTXORA product boundary

## CTXORA Free

CTXORA Free includes the unlimited local context engine. Indexes, embeddings, CAG, RAG, graph data, memory and handoffs remain local and customer-owned. Developers can run indexing and context preparation manually with the `ctxora` CLI or CTXORA MCP without a seat, usage or repository limit imposed by the engine.

## CTXORA Pro — Waitlist

CTXORA Pro is currently waitlist-only and reserved for customer-facing collaboration and repository operations:

- **Managed automation** — install and run CTXORA automatically for customer repositories on push and pull requests.
- **Private workflows** — manage private repository workflows, controlled updates and organization-specific execution policy.
- **Team context** — share approved context configuration and context state across multiple developers.

## Current implementation status

CTXORA Free is implemented in this OSS repository and is the current product focus. CTXORA Pro is a waitlist: billing, entitlements, hosted automation and team services are not implemented here and remain a separate future control-plane trust boundary. Run `ctxora pro` to inspect the planned paid scope without enabling or installing paid functionality.

The workflow in `.github/workflows/ci.yml` is the public CI and release-quality pipeline for the CTXORA Engine repository itself. It is not the customer-facing managed automation included in CTXORA Pro. The local `ctxora ci` command also remains part of the free engine; Pro begins when CTXORA operates, updates or shares this workflow on behalf of a customer or team.
