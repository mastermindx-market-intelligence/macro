#!/usr/bin/env bash
# EXTRACTED-VERBATIM-FROM: .github/workflows/daily.yml
# job collect, original market publication; same original generation.
set -e
echo "published=false" >> "$GITHUB_OUTPUT"
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
# best-effort push: losing a race with a concurrent push must NOT fail the
# pipeline (the data is collected; the next run re-syncs). Retry rebase+push,
# preferring our freshly-collected data on any conflict.
#
# The capital-structure paths carved out of the commit above are DIRTY here,
# and --autostash parks them across the rebase. On a clean re-apply the
# compilers below read the ledger the collectors just wrote — the normal
# night. On a conflicted re-apply push_autostash_ok resets hard and retries,
# so the compilers read origin/main's committed ledger instead. Both are
# sound inputs: the second is exactly #4600's restore-a-clean-ledger self-heal.
PUSH_ALARM=420
push_retry_init "collected market data"
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
  # (Asia paths unstaged above: when newly tracked on main, deleting the local stale
  # copy lets the rebase materialize asia-close's fresh commit — the W0b intent.)
  perl -e 'alarm 120; exec @ARGV or die' -- git fetch origin main || true
  comm -12 <(git ls-files --others --exclude-standard | LC_ALL=C sort) \
           <(git ls-tree -r --name-only origin/main | LC_ALL=C sort) \
    | while IFS= read -r f; do rm -f -- "$f" || true; done
  # Append-only base freshness (2026-08-18 lost update, DSC-OVERLAPPING-
  # DAILY-COLLECT-JOBS-LOSE-APPEND-ONLY-ROWS): two collect jobs that OVERLAP
  # each build data/government_revenue/ from the base each checked out, and
  # `-X theirs` below then REPLACES the earlier run's appended rows with this
  # run's instead of unioning them. Runs after the fetch and before the rebase
  # because that is the only point where origin/main's version is known and
  # this run's commit is still withholdable. No-op on an ordinary night.
  # Non-zero ONLY when the fence proved a loss and then could not withhold it;
  # publishing that tree is the corruption the fence exists to stop, so skip the
  # attempt rather than fail open. Every other fence outcome returns 0.
  if ! push_append_only_fence origin/main; then push_backoff; continue; fi
  if perl -e 'alarm 420; exec @ARGV or die' -- git pull --rebase --autostash -X theirs origin main && push_autostash_ok; then
    GOVREV_PUSH_SOURCE_SHA=$(git rev-parse HEAD)
    if push_do; then
      echo "pushed market data on attempt $PUSH_ATTEMPT"
      # No caller binding is emitted if the checkout drifted across push.
      [ "$(git rev-parse HEAD)" = "$GOVREV_PUSH_SOURCE_SHA" ] || exit 75
      printf 'source_sha=%s\n' "$GOVREV_PUSH_SOURCE_SHA" >> "$GITHUB_OUTPUT"
      echo "published=true" >> "$GITHUB_OUTPUT"
      push_won
      exit 0
    fi
  fi
  push_abort_rebase
  push_backoff
done
push_lost
echo "::warning::could not push collected market data after $PUSH_ATTEMPT attempts ($PUSH_STOP) (non-fatal)"
