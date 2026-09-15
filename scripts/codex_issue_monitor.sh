#!/bin/zsh
set -euo pipefail

repo="${CTXORA_REPO:-nguyentrunghieutcu/ctxora-engine}"
root="${CTXORA_WORKSPACE:-/Users/hieu/Workspaces/Projects/Modoro/compact-token}"
codex_bin="${CODEX_BIN:-/Applications/ChatGPT.app/Contents/Resources/codex}"
log_dir="${HOME}/.codex/log"
mkdir -p "$log_dir"
exec >>"$log_dir/ctxora-issue-monitor.log" 2>&1

cd "$root"
issue_number="$(gh issue list --repo "$repo" --state open --label codex-approved --limit 20 --json number,labels --jq '.[] | select(([.labels[].name] | index("codex-blocked")) | not) | .number' | head -n 1)"
[ -n "$issue_number" ] || exit 0

if gh pr list --repo "$repo" --state open --search "codex issue #$issue_number" --json number --jq 'length' | grep -qv '^0$'; then
  exit 0
fi

issue_json="$(gh issue view "$issue_number" --repo "$repo" --json number,title,body,url,labels)"
branch="codex/issue-${issue_number}"
git fetch origin main
git switch -C "$branch" origin/main

prompt=$(cat <<EOF
Fix GitHub issue #${issue_number} in this repository.
Issue JSON:
${issue_json}

Use the smallest root-cause fix. Add focused tests, run the narrowest relevant tests,
and do not modify release metadata or unrelated files. Do not merge anything.
Leave the working tree with the implementation ready for a draft pull request.
EOF
)

if ! "$codex_bin" exec -C "$root" --sandbox workspace-write --approve-for-me -m sol "$prompt"; then
  gh issue edit "$issue_number" --repo "$repo" --add-label codex-blocked
  gh issue comment "$issue_number" --repo "$repo" --body "Local Codex failed while processing this issue. The issue was marked codex-blocked; inspect the local monitor log before retrying."
  exit 1
fi

if git diff --quiet; then
  gh issue comment "$issue_number" --repo "$repo" --body "Local Codex reviewed this issue but produced no code changes."
  exit 0
fi

git add -A
git commit -m "fix: address issue #${issue_number}"
git push --set-upstream origin "$branch"
gh pr create --repo "$repo" --draft --title "fix: address issue #${issue_number}" --body "Closes #${issue_number}\n\nCreated by local Codex using the Custom provider configured in ~/.codex/config.toml."
