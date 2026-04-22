#!/usr/bin/env bash
# Story 1.3 Task 5 — apply master branch protection via GitHub API.
#
# Usage: OWNER=<github-owner> bash scripts/setup_branch_protection.sh
#        or pass --owner=<github-owner>
#
# Requires `gh` CLI (>= 2.50) authenticated with a PAT that carries the
# `repo` scope (branch protection edits). PAT must live in the OS Keychain
# (NFR-S1); `.env` storage is banned (Story 1.2 AC-3).
#
# Re-running the script is idempotent: `gh api -X PUT` overwrites the rule.
# Export the baseline to `infra/github/branch_protection.json` afterwards so
# future drift-detection jobs (Story 1.9 or Epic 8 Story 8.6) have a reference.
set -euo pipefail

REPO=invest_training
OWNER="${OWNER:-}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --owner=*) OWNER="${1#*=}"; shift ;;
    --owner)   OWNER="$2"; shift 2 ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

if [[ -z "$OWNER" ]]; then
  OWNER="$(gh repo view --json owner --jq .owner.login)"
fi
if [[ -z "$OWNER" ]]; then
  echo "OWNER not set and gh repo view could not determine it" >&2
  exit 2
fi

echo "Applying branch protection to ${OWNER}/${REPO}@master ..." >&2

gh api -X PUT "repos/${OWNER}/${REPO}/branches/master/protection" \
  -H "Accept: application/vnd.github+json" \
  --input - <<'EOF'
{
  "required_status_checks": {
    "strict": true,
    "contexts": [
      "stage-1-pre-commit",
      "stage-2-pytest-unit",
      "stage-3-pytest-integration",
      "stage-4-snapshot-regression",
      "stage-5-walk-forward-smoke",
      "stage-6-cooling-gate",
      "stage-7-paper-replay-marker"
    ]
  },
  "enforce_admins": true,
  "required_pull_request_reviews": {
    "required_approving_review_count": 0,
    "dismiss_stale_reviews": false
  },
  "restrictions": null,
  "required_linear_history": true,
  "allow_force_pushes": false,
  "allow_deletions": false,
  "required_conversation_resolution": true,
  "required_signatures": true
}
EOF

echo "Exporting baseline to infra/github/branch_protection.json ..." >&2
mkdir -p infra/github
# Use python3 -m json.tool (stdlib) instead of jq so the script stays self-contained
# on a minimal WSL2 Ubuntu install (jq is not in default apt selections).
gh api "repos/${OWNER}/${REPO}/branches/master/protection" \
  | python3 -m json.tool \
  > infra/github/branch_protection.json
echo "done." >&2
