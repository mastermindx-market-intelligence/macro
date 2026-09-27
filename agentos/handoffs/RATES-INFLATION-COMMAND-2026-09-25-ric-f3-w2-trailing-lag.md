---
workstream: WS:RATES-INFLATION-COMMAND
session: claude/ric-f3-w2-trailing-lag-20260925
model: fable
prs: [8030]
ended_because: complete
mission: >
  RIC F3 W2 — make yield momentum measurable on the real nightly path by treating a
  trailing FRED publication lag (T+1, at most three weekday rows) as an expected absence,
  measured and dated at the last captured source row, never at the frame date.
state_before: >
  RIC F3 W1 (fixed_grid_origin.v3, holiday-aware expected-absence grid) was live on main
  but every tenor was still null each nightly: FRED DGS* publishes one business day late,
  so the frame's last one-to-three weekday rows are always carried, and the fixed-grid
  measurement at the latest grid row could never qualify. Six consecutive bakes were null
  with the same null_reason. credit_momentum still reads only the interim TLT/IEF block.
changed:
  - path: engine/yield_momentum.py
    what: TRAILING_PUBLICATION_LAG_ROWS=3 and LAG_BASIS; a trailing carried suffix of at most three rows with a finite carried fill and no interior unexpected absence is trimmed and momentum is measured at the last captured row; new wire keys trailing_publication_lag_rows, trailing_expected_absent_rows, lag_tolerance_rows, lag_basis, measurement_origin; null_reason names a lag beyond tolerance or an interior absence; calculation_version fixed_grid_origin.v4; caveat states the dating rule.
  - path: tests/test_yield_momentum.py
    what: Three carry pins re-pointed at the captured row; parametrized lag 1/2/3 cases, lag 4 stale, interior absence plus lag, holiday inside the run, frame ending on a holiday, nonfinite trailing print, determinism and wire-key superset; 48 cases.
  - path: research/RIC_F3_W2_TRAILING_PUBLICATION_LAG_2026-09-25.md
    what: What changed, the six-bake null table, why three rows, the honest dating rule, and what W3 needs.
verified:
  - claim: The W2 suite and the consuming suites pass on the merged tree.
    command: python3 -m pytest -q tests/test_yield_momentum.py tests/test_rates_command.py tests/test_yield_curve.py
    result: 48 passed (W2 suite) and 265 passed, 3 skipped (consumers) at 8021be5a; ontology guard + W2 suite 49 passed at 1408a41e; CI green at 15b0ce51 (ci-gate success), merged 2026-09-25T17:32:05Z as 3f4b572f9ff6.
  - claim: No contract delta introduced by the change.
    command: python3 scripts/check_contract_delta.py --base origin/main
    result: 0 introduced, 2 inherited from base d9d83b11 (main's own); the contract-delta check was green at every ratified head.
unverified:
  - claim: The first nightly bake carries calculation_version fixed_grid_origin.v4 with a non-null velocity_bp.22d for at least one tenor.
    what_would_verify: The next data/transmission/latest.json on origin/main showing yield_momentum.calculation_version == fixed_grid_origin.v4 and a finite series.<tenor>.velocity_bp.22d with measurement_origin last_captured_source_row.
unresolved:
  - The VPS pull cron is held by the disk-triage marker, so no merged artifact reaches the served site until the operator lifts the hold.
  - credit_momentum still exposes only the interim TLT/IEF block; the yield_momentum consumer is W3.
next_actions:
  - Confirm v4 liveness on the first nightly artifact after the merge (read origin/main data/transmission/latest.json; do not re-bake from a session).
  - W3 — add one display-only yield_momentum block to engine/credit_momentum.py beside interim_tlt (never replacing it in W3), passing through as_of, measurement_origin and null_reason verbatim, never emitting ledger events, never entering credit_market_turn or theme tags.
  - Remove the interim TLT/IEF block only after two consecutive live v4 nightlies, in a later wave.
do_not_redo:
  - Do not rewrite F3 or reopen #6721; the fixed-grid engine (v3 holidays, v4 trailing-lag tolerance) is accepted.
  - Do not widen TRAILING_PUBLICATION_LAG_ROWS beyond 3 or measure at the frame date; the dating rule is the acceptance.
  - Do not touch the interim TLT/IEF block in credit_momentum before two live v4 nightlies.
danger_areas:
  - A nonfinite trailing print is not a publication lag; the trim requires a finite carried fill across the whole suffix.
  - An interior unexpected absence withholds the path even when the trailing lag is within tolerance.
  - The artifact's top-level calculation_version is the version to read; per-series objects do not repeat it.
---
