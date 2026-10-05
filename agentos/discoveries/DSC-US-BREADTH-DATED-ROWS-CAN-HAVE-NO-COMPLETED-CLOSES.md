---
key: US-BREADTH-DATED-ROWS-CAN-HAVE-NO-COMPLETED-CLOSES
claim: >
  A successful breadth download can carry a completed-session date and populated
  volume while every adjusted closing price on that row is absent. Historical
  column coverage and a successful HTTP response do not prove current prices;
  without semantic response validation the collector reports success and the
  real alpha producer remains on the prior session. Even after response validation,
  fresh.combine_first(cached) can refill a provider-missing completed-session cell
  from an earlier same-date cache observation whose settlement finality is unknown.
falsifier: >
  Run python -m pytest tests/test_us_breadth_completed_close.py -q. The production
  fetch and health-consumer regressions must reject or retry the observed
  completed-row null shape, retain old cache bytes on exhaustion, refuse cached
  same-session substitution for a missing fresh close, and fail when calendar,
  response, post-seam, or cache-quarantine validation is removed.
so_what: >
  Require real finite positive closes on the canonical completed NYSE session
  inside the existing US batch retry and final persistence boundaries. Before
  historical cache merge, quarantine that expected-session row for requested
  names so only the fresh completed-session response may populate it. Do not fix
  this by restamping a date, changing ranks, ignoring invalid fields, or inventing
  another collector, retry scheduler or freshness authority.
kind: data
verified_at: 2026-09-16
verified_by: >
  python -m pytest tests/test_us_breadth_completed_close.py tests/test_breadth_split_seam.py
  tests/test_russell_breadth.py tests/test_universe_split_seam.py -q;
  gh run view 35041133038 --repo mastermindx-market-intelligence/macro
scope:
  - WS:PROPHET-US-AVAILABILITY
  - collectors/breadth.py
  - scripts/build_site.py
confidence: verified
---

Incident source: main `aad0aaf33810c881a2da398380930eb50a9cdeda`, collector write `6a930b613598`, collector job `104621037120`, engine job `104658157677`. Before: three September-15 price rows with zero current closes despite populated volume. The isolated repaired source recovered 500/503, 599/602 and 400/400 current closes; the real alpha consumer advanced to September 15. Exact source/input/output hashes and the narrower-than-production proof boundary live in `research/us_prophet_availability/2026-09-16-completed-close/live-source-receipt.json`.

This extends the incident diagnosis; it does not supersede #7187’s reader-cache defect, #7180’s source-clock/provenance repair or #7163’s publication-link/evidence repair. None of those existing branch writers is replaced by this disjoint collector operation.


A later exact-head adversarial test planted a finite same-date value in the existing cache, then returned four fresh valid closes and one missing close at the 80% floor. Before repair, `fresh.combine_first(cached)` silently repopulated the missing name with the cached value and published five members. The cache carries no per-cell finality stamp, so that value could have been observed intraday. Current source now removes the expected-session cells for requested names from the historical merge input; prior history and regional/Russell behavior remain unchanged. The RED observed the cached value `102.0`; the repaired four-suite battery passes 75 tests. Evidence: `research/us_prophet_availability/2026-09-16-completed-close/same-session-cache-quarantine-receipt.json`.


The settlement-finality rule also covers the accepted response's High, Low, and Volume caches. A response can carry valid completed closes while one companion field is absent for one name; merging a finite earlier same-date extra from cache then creates false completed-session OHLCV evidence. Current source quarantines the expected-session cache row for requested US names before every Close/High/Low/Volume historical merge. RED/GREEN evidence: `research/us_prophet_availability/2026-09-16-completed-close/same-session-extra-cache-quarantine-receipt.json`.


A completed-session OHLCV row is coherent only when Close is valid for that name. The accepted 80% partial-coverage policy does not authorize High, Low, or Volume to publish independently for the missing-close remainder. Current source masks those same-response companion fields before acceptance. RED/GREEN evidence: `research/us_prophet_availability/2026-09-16-completed-close/same-response-ohlcv-coherence-receipt.json`.


A whole omitted companion field is distinct from a missing cell. Because `_last_extras` contains only present fields, persistence must still visit each existing US High/Low/Volume cache and quarantine its expected-session requested-universe row when that field is absent. Review finding and RED/GREEN closure: `research/us_prophet_availability/2026-09-16-completed-close/whole-field-extra-omission-receipt.json`.
