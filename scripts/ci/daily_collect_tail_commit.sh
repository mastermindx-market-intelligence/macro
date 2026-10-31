#!/usr/bin/env bash
# EXTRACTED-VERBATIM-FROM: .github/workflows/daily.yml job collect_tail, step commit tail data
# Moved out of daily.yml by EW-P1 (2026-10-31) to keep the workflow under its 512 KB processing cap;
# the only change from the YAML block is the EW-P1 QLedger carve after `git add`.
set -e
. "${GITHUB_WORKSPACE:-.}/scripts/ci/push_retry.sh"
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
# EW-P1 (2026-10-31): carve oversize QLedger blobs out of the collect-tail commit, as the collect
# job has since #9556. Run 40803269874 / collect_tail job 123688869633 was rejected for a 146.50 MB
# QLedger blob. Helper: scripts/ci/qledger_oversize_carve.sh.
. "${GITHUB_WORKSPACE:-.}/scripts/ci/qledger_oversize_carve.sh"
qledger_carve_staged collect-tail
if [ "${QLEDGER_WITHHELD:-}" = true ]; then exit 0; fi
if [ "${QLEDGER_CARVED:-}" = true ]; then trap 'qledger_restore' EXIT; qledger_park; if [ "${QLEDGER_PARKED:-}" != true ]; then exit 0; fi; fi
if git diff --cached --quiet; then echo "no tail data changes to commit"; exit 0; fi
git commit -m "data: collect-tail accrual $(date -u +%F)"
# best-effort push: same 5-retry rebase loop as the collect job's
# "commit market data" (see the pre-sync collision-sweep rationale there —
# render.yml / #2252). -X theirs prefers THIS job's freshly-accrued
# data on any conflict; exhausting the retry budget is non-fatal (the
# stores are state-resumable and re-accrue next night).
PUSH_ALARM=420
push_retry_init "tail data"
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
