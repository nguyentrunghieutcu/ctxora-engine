# Codex issue autofix

This repository can turn explicitly approved GitHub issues into draft pull requests.

## Safety model

1. A maintainer adds the `codex-ready` label, or starts the workflow manually.
2. The `codex-review` GitHub Environment pauses the job for its required reviewers.
3. Codex CLI receives only the selected issue and the checked-out repository.
4. Codex changes are pushed to a `codex/issue-*` branch and opened as a **draft PR**.
5. A maintainer reviews, tests, and merges the PR manually. The workflow never merges.

The scheduled run checks for the oldest open `codex-ready` issue every 30 minutes. An existing open PR for the issue prevents duplicate work.

## One-time setup

1. Add repository secret `OPENAI_API_KEY`.
2. Create the `codex-review` environment in repository settings.
3. Configure required reviewers for that environment.
4. Create the `codex-ready` label.
5. Enable Actions permissions to allow the workflow to create branches, PRs, and issue comments.

For a manual run, use **Actions → Codex issue fix → Run workflow** and optionally provide an issue number.

## GitHub App notifications

GitHub sends issue and pull-request notifications through the normal repository notification settings. Reviewers should watch the repository or subscribe to the `codex-ready` label workflow and draft PRs; no personal token is stored in the repository.
