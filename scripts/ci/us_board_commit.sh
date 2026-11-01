#!/usr/bin/env bash
# EXTRACTED-VERBATIM-FROM: .github/workflows/daily.yml
# job `us_board_ledgers`, step `commit US board and rotation artifacts`.
# Kept out of the YAML because of the workflow size budget (tests/test_workflow_file_size.py).
# Invoked as: bash scripts/ci/us_board_commit.sh
set -e  # mirror GitHub's default `bash -e {0}` step shell

. "${GITHUB_WORKSPACE:-.}/scripts/ci/push_retry.sh"
git config user.name "dashboard-bot"
git config user.email "actions@users.noreply.github.com"
git add data/us_board_ledger 2>/dev/null || true
git add data/us_sector_rotation 2>/dev/null || true
git add site/factordata/us_board_track.json 2>/dev/null || true
git add site/factordata/us_board_outcomes.json 2>/dev/null || true
git add site/factordata/us_track_ledger.json 2>/dev/null || true
git add site/factordata/us_board_track_v2.json 2>/dev/null || true
if git diff --cached --quiet; then echo "no US board or rotation changes"; exit 0; fi
push_staged_heal data/ site/factordata/ || exit 1
push_hold_oversize_staged data/ site/factordata/ || exit 1
if git diff --cached --quiet; then echo "nothing left to land"; [ -z "$PUSH_HELD_BACK" ] || exit 1; exit 0; fi
git commit -m "us-board: nightly ledger and rotation advance $(date -u +%F)"
PUSH_ALARM=420
push_retry_init "US board and rotation artifacts"
while push_attempt; do
  perl -e 'alarm 120; exec @ARGV or die' -- git fetch origin main || true
  comm -12 <(git ls-files --others --exclude-standard | LC_ALL=C sort) \
           <(git ls-tree -r --name-only origin/main | LC_ALL=C sort) \
    | while IFS= read -r f; do rm -f -- "$f" || true; done
  if perl -e 'alarm 420; exec @ARGV or die' -- git pull --rebase --autostash -X theirs origin main && push_autostash_ok; then
    if push_do; then
      echo "pushed US board and rotation artifacts on attempt $PUSH_ATTEMPT"
      push_won
      [ -z "$PUSH_HELD_BACK" ] || exit 1
      exit 0
    fi
  fi
  push_abort_rebase
  push_backoff
done
push_lost
echo "::error::could not push US board and rotation artifacts after $PUSH_ATTEMPT attempts ($PUSH_STOP)"
exit 1
