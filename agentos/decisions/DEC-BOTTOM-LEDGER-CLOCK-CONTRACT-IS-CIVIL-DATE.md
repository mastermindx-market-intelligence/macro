---
key: BOTTOM-LEDGER-CLOCK-CONTRACT-IS-CIVIL-DATE
question: >
  What is the one lawful clock/date representation for bottom-call capture, maturity,
  grading, persisted rows, CLI `--as-of` and historical replay — and is stripping the
  timezone at the crashing comparison the right repair?
answer: >
  A ledger date is a CIVIL CALENDAR DATE — no clock, no timezone: `YYYY-MM-DD` on every
  wire/persisted boundary, a tz-naive midnight `pd.Timestamp` in process. One coercion
  rule, in engine/ledger_clock.py: parse, and if the value carries a UTC offset take its
  WALL CLOCK AT ITS OWN OFFSET, then normalize. Enforced at every boundary — CLI/today,
  run_pipeline, persisted store read, producer accrual, price index, the maturity
  comparison, and the emit. Unreadable values are REJECTED (`ClockContractError`), never
  coerced into a plausible-looking date.
rationale: >
  Date-only is the measured contract, not a preference: 41/41 `as_of` values in
  data/us_board_ledger/snapshots.jsonl, every date field across 422 site/prophet/plans/
  *.json, and every data/stocks + data/yahoo price index are date-only; `grade_call`
  resolves the signal bar by calendar-date match; both write sites already discarded the
  clock via `str(as_of.date())`; `--as-of` is documented `YYYY-MM-DD`. There is no instant
  anywhere in the domain — a US session dated 2026-09-17 is an exchange civil date, not
  2026-09-17T00:00:00Z — so a tz-aware pipeline would invent precision the data lacks and
  force the price index to be localized to a zone it was never stamped in. The
  wall-clock-at-own-offset rule is chosen over convert-to-UTC-first because a stamped
  offset already names the civil day in the zone that wrote it (UTC-first would file an
  Asian 00:00+08 session a day early), and because it reproduces the previous default
  EXACTLY: `Timestamp.utcnow().normalize()` is UTC-zoned, so its wall clock at +00 is the
  UTC civil date that `today_ledger_date()` now returns. The repair therefore fixes the
  type without moving any semantics. It is DST-stable: both readings of an ambiguous
  fall-back wall clock name the same civil date.
alternatives: >
  (a) `.tz_localize(None)` at the crashing line only — the one-line patch: leaves the
  producer/reader boundary unrepaired, and would NOT have touched the silent-None defect in
  grade_call, where a tz-mismatched price index matched no bar and the row accrued forever.
  (b) Make the pipeline tz-aware UTC: requires attaching UTC to exchange session dates
  (false precision) and would still need a rule for the naive price index.
  (c) Convert aware values to UTC before taking the date: mis-files any session stamped at a
  positive offset near midnight.
  (d) Keep `|| true` and just fix the crash: leaves the next failure equally invisible.
evidence: >
  Pre-fix repro: `python -m scripts.grade_bottom_calls --force-local --out-dir <dir>` →
  TypeError at scripts/grade_bottom_calls.py:479, output dir EMPTY. Post-fix, same real
  inputs: 2454 rows accrued, 312 pass the calendar pre-check, all 312 correctly withheld by
  grade_call (fewer than H=60 trading bars follow), 0 graded — consistent with the module's
  own FIRST_MATURITY_EST of 2026-09-25. Maturity proven against REAL prices on a 300-row
  real-ticker back-dated cohort: 0 -> 300 graded, then 0 regrades across same/later/earlier
  `as_of` with byte-identical frozen values. Store is byte-idempotent over 3 consecutive
  real runs. Mutation proof: restoring the pre-fix date handling fails exactly
  test_production_mixed_tz_maturity_comparison_no_longer_raises and
  test_grade_call_resolves_a_tz_aware_price_index_instead_of_silently_returning_none.
reversibility: >
  Reversible. The contract lives in one module (engine/ledger_clock.py) with a single
  coercion rule; changing the rule is a one-function edit plus its tests. No grading
  arithmetic, no frozen grade, and no baseline was touched — calibration/
  bottom_ruler_baseline.json is unchanged and the 16 pre-existing tests pass untouched.
affects:
  - scripts/grade_bottom_calls.py
  - engine/bottom_ruler.py
  - engine/ledger_clock.py
  - engine/neuralweb/prophet_governor.py
  - .github/workflows/daily.yml
confidence: high
reversibility: easy
decided_by: coo-fable
decided_at: 2026-09-18
review_by: 2026-12-18
---

