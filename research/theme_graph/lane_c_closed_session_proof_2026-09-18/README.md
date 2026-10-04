# Lane C closed-session real-input proof — 2026-09-18

This is a bounded immutable evidence receipt for PR #7455 / operation
`theme-intelligence-c-early-leadership-and-subthemes-20260919-sol-001`.
It is evidence, not a new data store, publisher, model, score, or authority plane.

The receipt is bound to source commit
`2208fe40039d356929fac0f96b626edc33d42288` and the committed
`data/themes_heatmap/themes_tree.json` plus `data/yahoo/<ticker>.parquet`
Git objects at that commit. The Semiconductors source group contains 47 unique
member tickers. Exactly 46 Yahoo member tapes exist at that source commit;
`NVEC` is absent. `SPY` is the benchmark.

`price_manifest.json` records every requested ticker, exact Git blob SHA-1,
file SHA-256 and byte length (or `MISSING`). Its SHA-256 is:

`f1a47938cae47d7709e3c1f052b581efe042757cf2fba1df69c671ddb37cdb81`

`result.json` is the exact `compute_closed_session_leadership` output for
completed sessions through 2026-09-18 using those committed Yahoo bytes. Its
SHA-256 is:

`435a45de7167f99e07bc44475a2f161c3d81e488862804f5f6a9d28d970008ef`

The reproduced headline rows are unchanged from the original Lane C return:
Compute +2.6267% (5 sessions), Memory +3.4006%, Lithography -2.5324%, and
Packaging +1.1493%; their 60-session values are -5.3124%, -15.6379%,
-22.7415%, and -13.8387% respectively. Packaging remains PARTIAL.

This receipt proves reproducibility of that historical closed-session input and
measurement. It does not prove current production publication, browser parity,
predictive edge, or trading authority.
