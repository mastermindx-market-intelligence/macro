#!/usr/bin/env bash
# EXTRACTED-VERBATIM-FROM: .github/workflows/daily.yml
# Original engine chronicle metadata replay; dirty DATA checkout untouched.
set -e
if [ "${GITHUB_REPOSITORY:-}" = mastermindx-market-intelligence/macro ]; then
  umask 077
  native_code_root="${RUNNER_TEMP%/}/native-publication-code-${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT}-${GITHUB_JOB}"
  native_bootstrap="${RUNNER_TEMP%/}/native-publication-bootstrap-${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT}-${GITHUB_JOB}-${NATIVE_PUBLICATION_PUBLISHING_STEP}.sh"
  case "$(GIT_NO_REPLACE_OBJECTS=1 GIT_NO_LAZY_FETCH=1 git ls-tree "$GITHUB_WORKFLOW_SHA" -- scripts/ci/native_publication_source.sh)" in
    100644*) : ;; *) exit 76 ;;
  esac
  (set -o noclobber; GIT_NO_REPLACE_OBJECTS=1 GIT_NO_LAZY_FETCH=1 git show "$GITHUB_WORKFLOW_SHA:scripts/ci/native_publication_source.sh" > "$native_bootstrap")
  . "$native_bootstrap"
  native_publication_prepare_source "$native_code_root" "$GITHUB_WORKFLOW_SHA"
  . "$native_code_root/scripts/ci/push_retry.sh"
else
  . "${GITHUB_WORKSPACE:-.}/scripts/ci/push_retry.sh"
fi
git config user.name "dashboard-bot"
git config user.email "actions@users.noreply.github.com"
git add data/chronicle 2>/dev/null || true
if git diff --cached --quiet; then echo "no chronicle changes"; exit 0; fi
CHRONICLE_PARENT=$(git rev-parse HEAD)
git commit -m "chronicle: nightly event spine + state_log + rollups $(date -u +%F)"
CHRONICLE_COMMIT=$(git rev-parse HEAD)
CHRONICLE_MESSAGE=$(git log -1 --format=%B "$CHRONICLE_COMMIT")
PUSH_ALARM=420
push_retry_init "chronicle artifacts"
while push_attempt; do
  perl -e 'alarm 120; exec @ARGV or die' -- git fetch origin +refs/heads/main:refs/remotes/origin/main || true
  if CHRONICLE_PUBLISH=$(push_metadata_replay_commit "$CHRONICLE_PARENT" origin/main \
      "$CHRONICLE_COMMIT" "$CHRONICLE_MESSAGE" "${RUNNER_TEMP:-/tmp}/chronicle-replay.idx"); then
    # A replay whose tree equals origin/main means the chronicle content
    # already landed (e.g. a prior attempt's push worked but its alarm
    # misread it) — pushing it would create an empty duplicate commit.
    if [ "$(git rev-parse "$CHRONICLE_PUBLISH^{tree}")" = "$(git rev-parse origin/main^{tree})" ]; then
      echo "chronicle content already on origin/main — nothing to push"
      push_won; exit 0
    fi
    native_initial_rc=0
    push_native_do origin "$CHRONICLE_PUBLISH:refs/heads/main" || native_initial_rc=$?
    case "$native_initial_rc" in
      0) push_won; exit 0 ;;
      77) echo "publication=pending" >> "$GITHUB_OUTPUT"; exit 0 ;;
      80) export NATIVE_PUBLICATION_EXPECT_OFF=1 ;;
      *) exit "$native_initial_rc" ;;
    esac
    if push_do origin "$CHRONICLE_PUBLISH:refs/heads/main"; then
      echo "pushed chronicle artifacts on attempt $PUSH_ATTEMPT (metadata replay — dirty render tree untouched)"
      push_won; exit 0
    fi
  else
    # data/chronicle is single-writer: a replay conflict means another
    # writer touched it on main — anomalous, surface it while retrying.
    echo "::warning title=chronicle replay conflict::newer main changed data/chronicle differently (single-writer contract broken?) — retrying"
    PUSH_FAIL_CLASS="rebase-conflict"
  fi
  push_backoff
done
push_lost
echo "::warning::could not push chronicle artifacts after $PUSH_ATTEMPT attempts ($PUSH_STOP) (non-fatal — the local chronicle commit still rides the engine push loop below)"
