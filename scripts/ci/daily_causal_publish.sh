#!/usr/bin/env bash
# EXTRACTED-VERBATIM-FROM: .github/workflows/daily.yml
# job causal, original causal publication; same original generation.
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
# CHF-R11 narrow git-add block (pre-written in masterplan)
git add data/neuralweb/causal_feature_inventory.json 2>/dev/null || true
git add data/neuralweb/causal_edges.jsonl data/neuralweb/causal_nulls.jsonl 2>/dev/null || true
git add data/neuralweb/causal_mechanisms.jsonl 2>/dev/null || true
git add data/neuralweb/causal_filing_budget.jsonl 2>/dev/null || true  # M3 ISO-week filing budget (never trial_ledger.jsonl)
git add data/neuralweb/causal_frontier.json data/neuralweb/causal_surprise_queue.jsonl 2>/dev/null || true
git add data/neuralweb/causal_confluence_audit.json 2>/dev/null || true
git add data/neuralweb/causal_lab_state.json site/neuralwebdata/causal_lab_state.json 2>/dev/null || true
git add data/neuralweb/causal_brainstorm_runs.jsonl data/neuralweb/causal_llm_lane.json 2>/dev/null || true
git add data/trial_ledger.jsonl 2>/dev/null || true
if git diff --cached --quiet; then echo "no causal output changes"; exit 0; fi
git commit -m "causal: frontier drift + lab state $(date -u +%F)"
# Retry-rebase push loop with --autostash (stranded-data law #1823)
PUSH_ALARM=420
push_retry_init "causal outputs"
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
  perl -e 'alarm 120; exec @ARGV or die' -- git fetch origin main || true
  comm -12 <(git ls-files --others --exclude-standard | LC_ALL=C sort) \
           <(git ls-tree -r --name-only origin/main | LC_ALL=C sort) \
    | while IFS= read -r f; do rm -f -- "$f" || true; done
  if perl -e 'alarm 420; exec @ARGV or die' -- git pull --rebase --autostash origin main && push_autostash_ok; then
    if push_do; then echo "pushed causal outputs on attempt $PUSH_ATTEMPT"; push_won; exit 0; fi
  fi
  push_abort_rebase
  push_backoff
done
push_lost
echo "::warning::could not push causal outputs after $PUSH_ATTEMPT attempts ($PUSH_STOP) (non-fatal — downstream reads last committed)"
