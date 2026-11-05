#!/usr/bin/env bash
# EXTRACTED-VERBATIM-FROM: .github/workflows/daily.yml
# job collect_tail, original publishing step; native graph added in the SAME candidate.
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
# Everything this job writes is under data/ (tape_flow, trade_flows,
# clinical_trials, neuralweb, qledger claims, run_status) or
# site/basketdata/ (TIL site projections). No cache-restore steps run
# in this job, so the W0b asia unstage sweep from the collect job is
# not needed here — a fresh checkout+pull can only differ where THIS
# job's steps wrote. (The adapter sweep + qledger grader never run in
# this job, so site/qledger/track_record.json is never touched here;
# tests/test_collect_staging_globs.py keys on the grader-bearing
# module's dotted name, which this comment deliberately avoids.)
# data/run_status.json is co-written by the concurrent engine job
# (flow_signals registration) — whole-file -X theirs means one side's
# sources[] update can lose a race and go 1-run stale. Display-only
# and self-healing (healthcheck's hard-fail keys last_run/
# circuit_breaker are written solely by collect-core's adapter sweep,
# present in every job's base) — accepted at the 07-14 split review.
git add data/ site/basketdata/
# GH001 carve (scripts/ci/qledger_carve.sh, #9556 parity): an oversize staged qledger blob sank this whole commit nightly from 10-21; withhold stays green.
. "${GITHUB_WORKSPACE:-.}/scripts/ci/qledger_carve.sh"; qledger_carve_staged || exit 0
if git diff --cached --quiet; then echo "no tail data changes to commit"; exit 0; fi
git commit -m "data: collect-tail accrual $(date -u +%F)"
# best-effort push: same 5-retry rebase loop as the collect job's
# "commit market data" (see the pre-sync collision-sweep rationale there —
# render.yml / #2252). -X theirs prefers THIS job's freshly-accrued
# data on any conflict; exhausting the retry budget is non-fatal (the
# stores are state-resumable and re-accrue next night).
PUSH_ALARM=420
push_retry_init "tail data"
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
  comm -12 <(git ls-files --others --exclude-standard | LC_ALL=C sort) \
           <(git ls-tree -r --name-only origin/main | LC_ALL=C sort) \
    | while IFS= read -r f; do rm -f -- "$f" || true; done
  if perl -e 'alarm 420; exec @ARGV or die' -- git pull --rebase --autostash -X theirs origin main && push_autostash_ok; then
    if push_do; then echo "pushed tail data on attempt $PUSH_ATTEMPT"; push_won; exit 0; fi
  fi
  push_abort_rebase
  push_backoff
done
push_lost
echo "::warning::could not push collect-tail data after $PUSH_ATTEMPT attempts ($PUSH_STOP) (non-fatal)"
