# Codex issue handoff

GitHub is currently only the issue and notification surface. No local Codex issue runner or LaunchAgent is installed by this repository.

## Safety model

1. A maintainer adds `codex-ready` to an issue.
2. A maintainer reviews the issue and adds `codex-approved` as explicit approval.
3. GitHub Actions posts status comments only. It never runs Codex, receives an OpenAI key, changes code, or merges anything.
4. A maintainer starts any implementation manually and reviews the resulting pull request.

## One-time setup

1. Create labels `codex-ready` and `codex-approved`. The legacy spelling `codex_ready` is also accepted for compatibility.
2. Enable Actions permissions for issue comments if GitHub notifications are desired.

No `OPENAI_API_KEY` is required in GitHub repository secrets.

## Manual approval flow

- Open or update an issue with the requested behavior.
- Add `codex-ready` when the issue is clear enough to inspect.
- After reviewing the issue, add `codex-approved` to authorize local execution.
- Start the implementation manually after approval.
- Review the diff and CI results before merging.

The workflow in `.github/workflows/codex-issue-fix.yml` is deliberately limited to GitHub comments. It does not execute untrusted issue text on GitHub-hosted runners.
