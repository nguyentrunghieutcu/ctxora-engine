# Security Policy

CTXORA Engine is local-first. Source content is read only from canonical registered roots and retrieved content is always treated as untrusted evidence.

## Report a vulnerability

Do not disclose suspected vulnerabilities, exploit details, customer data or secrets in a public issue or discussion.

Use [GitHub Private Vulnerability Reporting](https://github.com/nguyentrunghieutcu/ctxora-engine/security/advisories/new) as the preferred reporting channel. If GitHub reporting is unavailable, email [nguyentrunghieutcu@gmail.com](mailto:nguyentrunghieutcu@gmail.com).

Include the affected version, impact, reproduction steps and any proposed mitigation. Replace live credentials and customer content with safe test data before submitting a report.

Remote telemetry and external HTTP binding are disabled by default. Non-loopback HTTP requires the explicit `--allow-external` flag and should be protected by an authorization layer before production use.
