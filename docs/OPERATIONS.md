# Operator guide

Install with scripts/install.sh or python -m pip install . Initialize a workspace with ctxora setup --workspace ., verify it with ctxora doctor --workspace ., and run stdio with ctxora run --workspace . --transport stdio. Streamable HTTP is loopback-only unless --allow-external is explicit.

Use ctxora index, ctxora query, ctxora inspect, ctxora repair, and ctxora ci --base <ref> --head <ref> for routine operation. New state is stored below .ctxora; existing .harness state remains readable during migration. Uninstall preserves indexed data unless --delete-data is explicitly requested. Run python scripts/audit_topology.py before release packaging.

CTXORA Free onboarding commands are `ctxora explain`, `ctxora context-score`, `ctxora repo-map`, `ctxora generate-agents-md`, `ctxora generate-copilot-instructions`, and `ctxora generate-cursor-rules`. Generated instruction files are never overwritten without `--force`. `ctxora pro` is informational only and reports that CTXORA Pro remains on the waitlist.

Run `ctxora dashboard --workspace . --open` for the CTXORA Console. It binds only to `127.0.0.1`, `localhost`, or `::1`, defaults to an ephemeral port, works without external assets, and exposes operator snapshots, redacted events, and allowlisted plan/confirm actions. Package update apply remains CLI-only.

Update workflow: run `ctxora update check --workspace .`, then `ctxora update plan --workspace .`. Review the returned target, ownership counts, manual skill targets, expiry, and digest. Apply exactly that one-time plan with `ctxora update apply <digest> --workspace . --yes`. The updater installs only the validated npm release, verifies the global version, reapplies CTXORA-owned default integrations, writes a receipt, and rolls back on failure. Interactive npm launcher sessions perform a cached availability check at most once per 24 hours; set `CTXORA_NO_UPDATE_CHECK=1` to disable notifications. No update is applied silently.
