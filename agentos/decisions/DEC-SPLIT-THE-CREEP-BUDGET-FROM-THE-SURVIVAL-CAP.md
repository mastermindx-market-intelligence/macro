---
key: SPLIT-THE-CREEP-BUDGET-FROM-THE-SURVIVAL-CAP
question: >
  A nightly job's `timeout-minutes` is both the kill point AND the denominator of its
  85% creep tripwire. Raising the cap to stop a job dying mid-publish therefore also
  slides the alarm up by the same amount. How should a cap be raised without silencing
  the creep detection that justified raising it?
answer: >
  Separate the two numbers. `scripts/ci/nightly_timings_finish.sh` takes an optional
  SECOND argument, the creep budget, and `cmd_finish` gained `warn_minutes` (default =
  `cap_minutes`). The 85% tripwire and the trend report measure against the budget; the
  cap remains only the kill point. `collect` passes `300 240` — 300 so a normal night
  clears the whole collector + checkpoint + push path, 240 so the alarm stays on the
  workload that forced the raise. Rows carry `warn_minutes` and `warn_pct` alongside the
  unchanged `pct_of_cap`, and `nightly_timings_report.py` falls back to `cap_minutes`
  when `warn_minutes` is absent, so pre-existing and backfilled rows render exactly as
  before. A job that passes one argument is byte-identical in behaviour.
rationale: >
  `WARN_PCT = 85.0` is applied to whatever the finish step is handed. Taking `collect`
  from 240 to 300 moves the warn line from 204m to 255m, which silences every night the
  repair itself cites as prior warning: 242.5m (101.1% -> 80.8%), 229.4m (95.6% ->
  76.5%), 226.7m (94.5% -> 75.6%), 226.3m (94.3% -> 75.4%), 220.1m (91.7% -> 73.4%).
  That is the worst possible failure shape for an alarm — it goes quiet precisely because
  the incident it predicted was addressed, and the next creep is then invisible until the
  next kill night. The cap and the alarm answer different questions (survive tonight vs.
  is the workload growing), so tying them to one number was a latent defect that only
  became visible when a cap was finally raised for headroom rather than after a kill.
  Making the budget optional keeps the blast radius at one job: the other instrumented
  jobs are untouched, and the defaulting rule means no call site can accidentally lose
  its alarm by omission.
alternatives:
  - option: Leave the cap at 240 and trim the collector workload first.
    why_not: >
      Correct in the long run and still the standing follow-up, but it leaves the nightly
      dying at the cap while the trim is designed. The cap raise is containment; the
      structural trim is the fix. Shipping only the trim means more lost nights meanwhile.
  - option: Raise the cap and accept the alarm moving with it.
    why_not: >
      This is what the first version of the change did. It disarms the only detector of
      the creep, and the 226m nights that justified the raise immediately read as a
      comfortable 75%. An independent review caught it; nothing in CI would have.
  - option: Lower WARN_PCT for this job so 85% of 300 lands near 204m.
    why_not: >
      A per-job percentage encodes the same coupling one level down and rots the moment
      the cap moves again. It also makes the annotation's "85%" a lie for that job. The
      budget is the honest primitive: an absolute number of minutes the workload should
      not exceed.
  - option: Keep one argument and add a separate absolute-minutes alarm step.
    why_not: >
      A second alarm mechanism beside the existing one means two things to keep in step
      and two places to go dark; the W2 ledger already carries elapsed minutes per band.
      Changing the denominator is strictly smaller than adding a parallel tripwire.
evidence:
  - "scripts/nightly_timings.py:82 WARN_PCT = 85.0; the tripwire divides elapsed by the finish step's budget argument"
  - "data/ops/nightly_timings/collect.jsonl rows 2026-09-17/23/24/25/26 — 242.5m, 226.7m, 226.3m, 229.4m, 220.1m"
  - "tests/test_nightly_timings.py::test_a_cap_raise_without_a_creep_budget_silences_the_alarm — asserts the 229.4m night IS silent at a bare 300m cap"
  - "tests/test_nightly_timings.py::test_the_creep_budget_keeps_the_alarm_on_the_old_workload — 95.6%, annotation names both numbers"
  - "tests/test_daily_collect_commit_path.py::test_the_creep_budget_is_pinned_below_the_raised_cap — fails if the budget is dropped"
  - "python3 scripts/nightly_timings_report.py — collect still reads 240m budget / 96% max / 4 breaches / TRIPWIRE from pre-existing rows"
  - "PR 8008"
affects:
  - "WS:RUNNER-FLEET-RESILIENCE"
  - ".github/workflows/daily.yml"
  - "scripts/nightly_timings.py"
  - "scripts/nightly_timings_report.py"
  - "scripts/ci/nightly_timings_finish.sh"
confidence: high
reversibility: easy
decided_by: "session: claude/macro-01-nightly-checkpoint-20260929"
decided_at: 2026-09-29
---
