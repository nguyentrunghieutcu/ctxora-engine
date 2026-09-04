# Operator guide

Install with scripts/install.sh or python -m pip install . Initialize a workspace with ctxora setup --workspace ., verify it with ctxora doctor --workspace ., and run stdio with ctxora run --workspace . --transport stdio. Streamable HTTP is loopback-only unless --allow-external is explicit.

Use ctxora index, ctxora query, ctxora inspect, ctxora repair, and ctxora ci --base <ref> --head <ref> for routine operation. New state is stored below .ctxora; existing .harness state remains readable during migration. Uninstall preserves indexed data unless --delete-data is explicitly requested. Run python scripts/audit_topology.py before release packaging.

CTXORA Free onboarding commands are `ctxora explain`, `ctxora context-score`, `ctxora repo-map`, `ctxora generate-agents-md`, `ctxora generate-copilot-instructions`, and `ctxora generate-cursor-rules`. Generated instruction files are never overwritten without `--force`. `ctxora pro` is informational only and reports that CTXORA Pro remains on the waitlist.
