#!/usr/bin/env bash
# EXTRACTED-VERBATIM-FROM: .github/workflows/asia-close.yml
# Original asia/push asia data business body; staged native route preserves original budget.
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
push_retry_init "asia data"
native_initial_rc=0
push_native_do origin HEAD:main || native_initial_rc=$?
case "$native_initial_rc" in
  0) push_won; exit 0 ;;
  77) echo "publication=pending" >> "$GITHUB_OUTPUT"; exit 0 ;;
  80) export NATIVE_PUBLICATION_EXPECT_OFF=1 ;;
  *) exit "$native_initial_rc" ;;
esac
while push_attempt; do
  # pre-sync collision sweep (render.yml / #2252): a mid-run commit on origin/main can
  # TRACK a path this job wrote as an UNTRACKED side-effect — the rebase checkout then
  # refuses ("untracked working tree files would be overwritten") and --autostash can't
  # clear it (it parks tracked modifications only), so every retry dies identically.
  # Everything this step publishes is already committed above, so a path untracked HERE
  # but tracked on origin/main is a throwaway local write — origin/main is authoritative.
  # Gitignored files and untracked paths origin/main doesn't track never enter the
  # intersection (runner-local stores and caches are untouched).
  git fetch origin main || true
  comm -12 <(git ls-files --others --exclude-standard | LC_ALL=C sort) \
           <(git ls-tree -r --name-only origin/main | LC_ALL=C sort) \
    | while IFS= read -r f; do rm -f -- "$f" || true; done
  # push_autostash_ok (P0 d29e4dd44d/#4167): a conflicted autostash apply
  # here would leave marker blocks that the broad "commit engine outputs"
  # add later in THIS job stages verbatim — the exact chronicle-step shape
  # that polluted the US nightly. Detect, discard, retry clean.
  if git pull --rebase --autostash -X theirs origin main && push_autostash_ok; then
    if push_do; then echo "pushed asia data (attempt $PUSH_ATTEMPT)"; push_won; break; fi
  fi
  push_abort_rebase
  push_backoff
done
push_lost
