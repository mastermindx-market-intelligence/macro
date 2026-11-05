#!/usr/bin/env bash
# EXTRACTED-VERBATIM-FROM: .github/workflows/daily.yml
# job ledger_heartbeat, original publishing step; native graph added in the SAME candidate.
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
git add data/ci/ledger_heartbeat_state.json 2>/dev/null || true
if git diff --cached --quiet; then echo "no heartbeat state change"; exit 0; fi
git commit -m "ops: ledger heartbeat state $(date -u +%F)"
PUSH_ALARM=120
PUSH_MAX_ATTEMPTS=6      # a one-line ops state file, non-fatal — a shorter budget than the render lanes is right, but 3 was not enough to outlast main's commit rate
push_retry_init "ledger heartbeat state"
native_initial_rc=0
push_native_do origin HEAD:main || native_initial_rc=$?
case "$native_initial_rc" in
  0) push_won; exit 0 ;;
  77) echo "publication=pending" >> "$GITHUB_OUTPUT"; exit 0 ;;
  80) export NATIVE_PUBLICATION_EXPECT_OFF=1 ;;
  *) exit "$native_initial_rc" ;;
esac
while push_attempt; do
  perl -e 'alarm 60; exec @ARGV or die' -- git fetch origin main || true
  if perl -e 'alarm 120; exec @ARGV or die' -- git pull --rebase --autostash -X theirs origin main && push_autostash_ok; then
    if push_do; then echo "heartbeat state pushed on attempt $PUSH_ATTEMPT"; push_won; exit 0; fi
  fi
  push_abort_rebase
  push_backoff
done
push_lost
echo "::warning::could not push heartbeat state after $PUSH_ATTEMPT attempts ($PUSH_STOP) (non-fatal)"
