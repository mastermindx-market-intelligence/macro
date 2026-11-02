---
key: HEATMAP-INTRADAY-ROW-COUNT-ALIASES-TIME
claim: >
  At Macro 7f1e4ede020b53b1d86b39642e9c88f334f0d61a, the S&P heatmap
  intraday_returns function labeled previous-row changes as 1H regardless of
  elapsed time, reproducing a false 1H label on five-minute, two-hour and weekend gaps.
falsifier: >
  Execute the three timestamp-gap controls against that immutable baseline;
  this claim is false if the incumbent checks the actual timestamp distance
  or declines the mismatched 1H values. The candidate is separately tested
  by tests/test_sp500_heatmap_intraday_clock.py.
so_what: >
  Use exact observed timestamp endpoints for intraday horizon labels. Do not
  turn row counts into elapsed hours, infer a timezone, or rewind past an
  invalid latest observation. The tested candidate does not prove production
  incidence, source finality, synchronized groups, or a live rotation detector.
kind: landmine
verified_at: 2026-10-13
verified_by: >
  Baseline direct Python probes of engine.sp500_heatmap.intraday_returns;
  pytest red 18 failed/6 passed and candidate focused suite 49 passed;
  research/rotation_intelligence/intraday_sessions_20261013/red.txt,
  green.txt and controls.json preserve the bounded evidence.
scope:
  - macro
  - sector-rotation-intelligence
  - engine/sp500_heatmap.py
  - scripts/build_sp500_heatmap.py
confidence: verified
---

The repair is on the independent attended-source operation
`rotation-intraday-session-research-20261013`. Publication, required review,
CI and production proof remain separate. The existing hourly collector is not
changed into a minute feed. The retained research report contains the exact
source pins, executed proof and continuation frontier; no workstream is invented
or reassigned to record this source-local finding.
