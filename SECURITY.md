# Security Policy

CTXORA Engine is local-first. Source content is read only from canonical registered roots and retrieved content is always treated as untrusted evidence.

Do not report secrets by opening a public issue. Report path authorization, workspace isolation, secret exclusion or persistence vulnerabilities privately to the repository owner.

Remote telemetry and external HTTP binding are disabled by default. Non-loopback HTTP requires the explicit `--allow-external` flag and should be protected by an authorization layer before production use.
