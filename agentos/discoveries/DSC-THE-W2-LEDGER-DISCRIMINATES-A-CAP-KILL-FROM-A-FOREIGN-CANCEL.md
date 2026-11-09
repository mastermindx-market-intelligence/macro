---
key: THE-W2-LEDGER-DISCRIMINATES-A-CAP-KILL-FROM-A-FOREIGN-CANCEL
claim: >
  A `cancelled` nightly conclusion is produced by at least two opposite causes, and the
  run conclusion cannot tell them apart — so the reflex "the nightly was cancelled, raise
  the cap" is right about half the time and actively wrong the other half. Measured on two
  CONSECUTIVE nights of the same workflow. CAP EXHAUSTION — run 36364562743 (2026-09-28):
  `collect_tail` 201.3m against a 200 cap and `engine` 305.0m against a 300 cap, both cap
  plus the ~5-min grace; a cap raise is the correct repair. FOREIGN CANCEL — run
  36511549800 (2026-09-29): the three LONGEST jobs were cancelled at 97.2m/240,
  96.3m/200 and 118.8m/300, i.e. 40-59% of cap, across TWO runners (mac-builder-5 and
  mac-builder-light), while 14 other jobs succeeded including `tech_lab_offrender` at
  74.8m on the same mac-builder-5 AFTER both of its cancels; a cap raise cannot help and
  runner health is exonerated in both directions. The one-line discriminator is already
  written every night by W2: `data/ops/nightly_timings/<job>.jsonl` carries `pct_of_cap`
  and the band count. A cap kill reads ~100% with a full band set; the 09-29 rows read
  40.3% and 41.1% with `bands:2` against a healthy night's `bands:4`. The 85% tripwire
  correctly stayed silent on both 09-29 runs, which is why a creep alarm is not a
  cancellation alarm and must never be read as one. Two candidate mechanisms are
  eliminated by config rather than inference: concurrency supersession cannot take a job
  95 minutes into RUNNING (`cancel-in-progress: false`, per-cron groups, and the recorded
  08-14/15 kill only reaches a PENDING run), and `run collectors` carries no step-level
  timeout — an unpaired step timeout would also mark the step `failure`, not `cancelled`.
  The agent of the foreign cancel is NOT established; a cancel remains invisible to every
  staleness instrument in this repo.
falsifier: >
  Read the ledger rows and the job durations for the two nights and compare against the
  caps. `python3 -c "import json;[print(r['date'],r['run_id'],r['elapsed_minutes'],r['cap_minutes'],r['pct_of_cap'],len(r.get('bands') or {})) for r in (json.loads(l) for l in open('data/ops/nightly_timings/collect.jsonl') if l.strip())][-6:]"`
  and `gh api repos/mastermindx-market-intelligence/macro/actions/runs/36511549800/jobs?per_page=100
  --jq '.jobs[]|"\(.conclusion) \(.started_at) \(.completed_at) \(.runner_name) \(.name)"'`.
  The claim is false if the 09-29 run shows any cancelled job at or near its cap, if
  `pct_of_cap` is >= 85 on those rows, or if the cancelled jobs share a single runner.
so_what: >
  When triaging a `cancelled` nightly, read `data/ops/nightly_timings/<job>.jsonl` FIRST —
  it is one local line, costs no API quota, and answers "was this the cap?" before any
  theory is formed. Propose a cap raise only when `pct_of_cap` is near 100. Then read the
  killed job's `steps[]` (never the run log) and look specifically at whether
  `commit market data` ran: SKIPPED means the session was lost at COLLECTION, upstream of
  the checkpoint, and the publication path is not implicated at all — the commit gate
  refusing a partial collection and the `published` receipt staying unset (so the
  downstream consumers skip) is the designed behaviour working, not the defect. This
  prevents attributing a collection-stage loss to a publication repair, and prevents
  raising a cap that was never the binding constraint.
kind: runtime
verified_at: 2026-09-29
verified_by: "gh api repos/mastermindx-market-intelligence/macro/actions/runs/36511549800/jobs?per_page=100 + data/ops/nightly_timings/collect.jsonl"
scope:
  - macro
  - .github/workflows/daily.yml
  - data/ops/nightly_timings/**
  - scripts/nightly_timings*.py
confidence: verified
---

See `DSC:CANCELLED-DAILY-RUN-CAN-STILL-DELIVER-PROPHET` for the companion landmine in the
other direction: a run conclusion also fails to tell you whether delivery HAPPENED, because
`prophet_checkpoint` commits mid-job. Together the two records say the same thing about the
same field — a `daily.yml` run conclusion carries near-zero information about what the night
did, in either direction, and the artifact must be read instead.

`DSC:A-JOB-TIMEOUT-RUNS-THE-ALWAYS-TAIL-INSIDE-A-BOUNDED-GRACE` covers what happens once a
cap genuinely does fire; this record is about deciding whether it fired at all.
