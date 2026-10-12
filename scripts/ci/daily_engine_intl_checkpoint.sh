#!/usr/bin/env bash
# Durable checkpoint for International public surfaces after normalization.
set -euo pipefail

. "${GITHUB_WORKSPACE:-.}/scripts/ci/push_retry.sh"
git config user.name "dashboard-bot"
git config user.email "actions@users.noreply.github.com"

INTL_PATHS=(
  site/intl.html
  site/intl_stocks.html
  site/intl_stock.html
  site/japan.html
  site/south_korea.html
  site/euro_area.html
  site/united_kingdom.html
  site/india.html
)

if git diff --quiet HEAD -- "${INTL_PATHS[@]}"; then
  echo "no international page changes"
  exit 0
fi

CHECKPOINT_PARENT=$(git rev-parse HEAD)
git commit --only -m "intl: normalized dashboard checkpoint $(date -u +%F)" -- "${INTL_PATHS[@]}"
CHECKPOINT_COMMIT=$(git rev-parse HEAD)
CHECKPOINT_MESSAGE=$(git log -1 --format=%B "$CHECKPOINT_COMMIT")
PUSH_ALARM=180
PUSH_BUDGET_SECS=360
PUSH_MAX_ATTEMPTS=8
push_retry_init "international dashboard checkpoint"
while push_attempt; do
  git fetch origin main || true
  if CHECKPOINT_PUBLISH=$(push_metadata_replay_commit \
      "$CHECKPOINT_PARENT" origin/main "$CHECKPOINT_COMMIT" "$CHECKPOINT_MESSAGE" \
      "${RUNNER_TEMP:-/tmp}/intl-checkpoint-replay.idx"); then
    if [ "$(git rev-parse "$CHECKPOINT_PUBLISH^{tree}")" = "$(git rev-parse origin/main^{tree})" ]; then
      echo "international checkpoint already present on origin/main"
      push_won
      exit 0
    fi
    if push_do origin "$CHECKPOINT_PUBLISH:refs/heads/main"; then
      echo "pushed international dashboard checkpoint on attempt $PUSH_ATTEMPT"
      push_won
      exit 0
    fi
  else
    PUSH_FAIL_CLASS="replay-conflict"
    echo "::warning title=international checkpoint replay conflict::newer main changed an international page; retrying"
  fi
  push_backoff
done
push_lost
echo "::error title=international dashboard checkpoint failed::fresh normalized pages remain local and may be lost if the engine job later times out"
exit 1