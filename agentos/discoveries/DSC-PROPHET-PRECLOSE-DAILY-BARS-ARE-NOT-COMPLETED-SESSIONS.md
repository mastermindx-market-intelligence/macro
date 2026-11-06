---
key: PROPHET-PRECLOSE-DAILY-BARS-ARE-NOT-COMPLETED-SESSIONS
claim: >
  A weekday pre-close vendor refresh can put a current-date provisional daily bar on
  only part of the US universe, so ranking the raw panel before clipping to one
  expected_last_session creates a genuine mixed-vintage cross-section even though the
  completed-session data underneath is healthy.
falsifier: >
  Run `python -m pytest -q
  tests/test_us_completed_session_panel.py::test_preclose_panel_excludes_provisional_equity_bars_but_keeps_raw_reach`;
  falsify this claim by making the test pass after removing producer-side clipping while
  preserving the captured provisional-current-date input shape.
so_what: >
  Capture one observation timestamp and clip every non-crypto close/high/OHLC input to
  expected_last_session before extension, dispersion, technical, entry, alpha, or
  ranking consumers. Never weaken the downstream mixed-vintage refusal to restore
  availability; genuine completed-session tears must still fail closed.
kind: data
verified_at: 2026-09-15
verified_by: >
  GitHub Actions daily run 34957877090 engine log: 3,038 members at 2026-09-14 and
  198 members at provisional 2026-09-15 before ranking; site/prophet/index.json intake
  then reported 16 eligible, 16 clock-provenance failures, 0 originated.
scope: [macro, prophet-us, scripts/build_stock_library.py, scripts/build_site.py]
confidence: verified
---
