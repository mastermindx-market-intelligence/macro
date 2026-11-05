#!/usr/bin/env bash
# EXTRACTED-VERBATIM-FROM: .github/workflows/daily.yml
# job standout_audit_us, original publishing step; native graph added in the SAME candidate.
set -e
if [ "${GITHUB_REPOSITORY:-}" = mastermindx-market-intelligence/macro ] && [ "${GITHUB_REF:-}" = refs/heads/main ]; then
  # Capture repository-owned execution bytes from the original protected
  # workflow SHA BEFORE rebase can replace files in the candidate tree.
  umask 077
  [[ "$GITHUB_WORKFLOW_SHA" =~ ^[0-9a-f]{40}$ ]]
  native_code_root="${RUNNER_TEMP%/}/native-publication-code-${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT}-${GITHUB_JOB}"
  mkdir -m 700 -- "$native_code_root"
  mkdir -p -- "$native_code_root/scripts/ci"
  GIT_NO_REPLACE_OBJECTS=1 GIT_NO_LAZY_FETCH=1 git show \
    "$GITHUB_WORKFLOW_SHA:scripts/ci/native_publication_source.sh" \
    > "$native_code_root/scripts/ci/native_publication_source.sh"
  case "$(GIT_NO_REPLACE_OBJECTS=1 git ls-tree "$GITHUB_WORKFLOW_SHA" -- scripts/ci/native_publication_source.sh)" in
    100644*) : ;; *) exit 76 ;;
  esac
  . "$native_code_root/scripts/ci/native_publication_source.sh"
  native_publication_capture_source "$native_code_root" "$GITHUB_WORKFLOW_SHA"
  . "$native_code_root/scripts/ci/push_retry.sh"
else
  . "${GITHUB_WORKSPACE:-.}/scripts/ci/push_retry.sh"
fi
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
native_initial_rc=0
push_native_do origin HEAD:main || native_initial_rc=$?
case "$native_initial_rc" in
  0) push_won; exit 0 ;;
  77) echo "publication=pending" >> "$GITHUB_OUTPUT"; exit 0 ;;
  80) export NATIVE_PUBLICATION_EXPECT_OFF=1 ;;
  *) exit "$native_initial_rc" ;;
esac
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
