#!/usr/bin/env bash
# EXTRACTED-VERBATIM-FROM: .github/workflows/asia-close.yml
# Original ths_rescrape/commit THS scrape artifacts business body; staged native route preserves original budget.
set -e
export NATIVE_PUBLICATION_PUBLISHING_STEP=native_publication_stage
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
publisher_source_root="${native_code_root:-${GITHUB_WORKSPACE:-.}}"
git config user.name "dashboard-bot"
git config user.email "actions@users.noreply.github.com"
git add data/baskets_china_ths/
if git diff --cached --quiet; then echo "no THS scrape changes"; else
  git commit -m "data: ths concept re-scrape $(date -u +%F)"
  push_retry_init "ths scrape"
  native_initial_rc=0
  push_native_do origin HEAD:main || native_initial_rc=$?
  case "$native_initial_rc" in
    0) push_won; exit 0 ;;
    77) echo "publication=pending" >> "$GITHUB_OUTPUT"; exit 0 ;;
    80) export NATIVE_PUBLICATION_EXPECT_OFF=1 ;;
    *) exit "$native_initial_rc" ;;
  esac
  while push_attempt; do
    git fetch origin main || true
    if git pull --rebase --autostash -X theirs origin main && push_autostash_ok; then
      if push_do; then echo "pushed ths scrape (attempt $PUSH_ATTEMPT)"; push_won; break; fi
    fi
    push_abort_rebase
    push_backoff
  done
  push_lost
fi
