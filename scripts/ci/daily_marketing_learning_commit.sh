#!/usr/bin/env bash
# EXTRACTED-VERBATIM-FROM: .github/workflows/daily.yml
# Preserve the default workflow shell's errexit behavior.
set -e
. "${GITHUB_WORKSPACE:-.}/scripts/ci/push_retry.sh"
git config user.name "dashboard-bot"
git config user.email "actions@users.noreply.github.com"
git add data/marketing/learning 2>/dev/null || true
if git diff --cached --quiet; then echo "no marketing learning changes"; exit 0; fi
HALTED=$(python3 -c "import json,pathlib;p=pathlib.Path('data/marketing/learning/halts.json');d=json.loads(p.read_text()) if p.exists() else {};print(','.join(sorted(a for a,r in (d.get('accounts') or {}).items() if isinstance(r,dict) and r.get('state')=='halted')) or 'none')" 2>/dev/null || echo "unknown")
# METADATA-ONLY PUSH (P0 d29e4dd44d/#4167, same shape as the chronicle
# step): this push runs while the SIBLING data/marketing/ paths that
# "commit standout audit US artifacts" broad-adds NEXT are still dirty
# — a `pull --rebase --autostash` here could conflict its re-apply,
# exit 0, and hand that step a marker-polluted tree. Replay in a temp
# index and push the object id; the dirty tree is never touched.
LEARNING_PARENT=$(git rev-parse HEAD)
git commit -m "marketing-learning: labels + scorecard + desk health $(date -u +%F) (halted: ${HALTED})"
LEARNING_COMMIT=$(git rev-parse HEAD)
LEARNING_MESSAGE=$(git log -1 --format=%B "$LEARNING_COMMIT")
PUSH_ALARM=420
push_retry_init "marketing learning artifacts"
while push_attempt; do
  perl -e 'alarm 120; exec @ARGV or die' -- git fetch origin main || true
  if LEARNING_PUBLISH=$(push_metadata_replay_commit "$LEARNING_PARENT" origin/main \
      "$LEARNING_COMMIT" "$LEARNING_MESSAGE" "${RUNNER_TEMP:-/tmp}/learning-replay.idx"); then
    if [ "$(git rev-parse "$LEARNING_PUBLISH^{tree}")" = "$(git rev-parse origin/main^{tree})" ]; then
      echo "marketing learning content already on origin/main — nothing to push"
      push_won; exit 0
    fi
    if push_do origin "$LEARNING_PUBLISH:refs/heads/main"; then
      echo "pushed marketing learning artifacts on attempt $PUSH_ATTEMPT (metadata replay — dirty marketing tree untouched)"
      push_won; exit 0
    fi
  else
    PUSH_FAIL_CLASS="rebase-conflict"
  fi
  push_backoff
done
push_lost
echo "::warning title=marketing_learning::could not push learning artifacts (they advance again tomorrow)"
exit 0
