# Local Codex issue autofix

GitHub is only the issue/notification surface. Codex CLI runs locally from the Scheduled Codex task, so this repository does not need an `OPENAI_API_KEY` GitHub secret.

## Safety model

1. A maintainer adds `codex-ready` to an issue.
2. A maintainer reviews the issue and adds `codex-approved` as the explicit execution approval.
3. Scheduled Codex checks the repository every 30 minutes, reads the approved issue through `gh`, and works in this local checkout.
4. Codex creates a `codex/issue-*` branch, runs focused tests, pushes the branch, and opens a **draft PR**.
5. GitHub Actions posts status comments only. It never runs Codex, receives an OpenAI key, changes code, or merges anything.
6. A maintainer reviews and merges the draft PR manually.

## One-time setup

1. Create labels `codex-ready` and `codex-approved`.
2. Authenticate local `gh` with access to issues, contents, and pull requests: `gh auth login`.
3. Keep the Scheduled Codex automation `CTXORA Codex issue monitor` active.
4. Enable Actions permissions for issue comments if GitHub notifications are desired.

No `OPENAI_API_KEY` is required in GitHub repository secrets. The local Codex session uses the local Codex configuration and credentials.

## Manual approval flow

- Open or update an issue with the requested behavior.
- Add `codex-ready` when the issue is clear enough to inspect.
- After reviewing the issue, add `codex-approved` to authorize local execution.
- Scheduled Codex picks it up, reports progress in the issue, and opens a draft PR.
- Review the diff and CI results before merging.

The workflow in `.github/workflows/codex-issue-fix.yml` is deliberately limited to GitHub comments. It does not execute untrusted issue text on GitHub-hosted runners.
