---
key: F3-TURN-WATCH-IS-STRUCTURALLY-UNREACHABLE-IN-PRODUCTION
claim: >
  engine/yield_momentum.py gates `turn_watch` on `enough and path_qualified`, and
  `_series_read` sets `path_qualified = all(observed) and numeric.notna().all() and
  source_basis == 'captured_source_rows'` over a TURN_LOOKBACK=1260-row
  `pd.bdate_range` weekday grid. `observed` is true only where the captured source
  origin date equals the grid timestamp. US Treasury CMT series (DGS2/5/10/20/30) do
  not print on US market holidays, so every holiday inside a ~5-year weekday window is
  ffill-carried and therefore NOT observed. Measured 2026-09-22 on the real feature
  frame at macro ea194c5d: 1260-row window, 1206 observed, **54 carried** for us20y
  (59 of 1430 on a 2000-day window) -> `path_qualified=False` and `turn_watch=None`
  for ALL FIVE series (2y/5y/10y/20y/30y), every night, forever. The committed
  pre-#7291 artifact at origin/main still carries `turn_watch: "extreme_high_watch"`
  on 4 of 5 series, so #7291 (merged 2026-09-20, `calculation_version:
  fixed_grid_origin.v2`) silently converted a firing capability into a permanently
  null one. The test suite does not catch it: tests/test_yield_momentum.py ~line 88
  asserts `turn_watch == "rolldown_forming"` on a SYNTHETIC fixture that prints on
  every weekday, and 115 F3-related tests pass green at HEAD. Isolation proof: the
  same real DGS20 series reindexed so it prints every weekday flips
  `path_qualified` to True and `turn_watch` to `extreme_high_watch`; the ONLY
  difference is holiday prints.
falsifier: >
  `python3 -c "..."` building the real feature frame and asserting
  `build_yield_momentum(f)['series']['20y']['path_qualified'] is True` would refute it,
  as would any change that excludes expected market-holiday absences from the
  `observed` test (e.g. qualifying against a trading calendar rather than
  `pd.bdate_range`), or a decision record stating that a permanently-null turn_watch
  is the intended contract.
so_what: >
  Do NOT read `turn_watch: null` in a rates artifact as "no turn is forming" — it is
  not a market verdict, it is an unreachable gate (see the standing rule that
  instrument verdicts are not market verdicts). Do NOT "fix" this by relaxing
  `path_qualified` wholesale: the qualification exists to stop endpoint comparisons
  masquerading as a continuously observed path, and that intent is correct. The
  bounded repair is to distinguish an EXPECTED absence (market holiday — no print was
  ever due) from a REAL gap (a due print that is missing), which is a change to how
  `observed` is computed, not to the turn logic. Any future F3 consumer that renders a
  turn/watch state must not ship before this is repaired, or it will render a dead
  field. Note the consequence is currently invisible because the field has no reader
  at all ([[DSC:F3-YIELD-MOMENTUM-HAS-NO-CONSUMER]]).
confidence: verified
kind: landmine
verified_at: 2026-09-22
verified_by: >
  macro ea194c5d215c64158a828abdc676f47bb7723374 (== origin/main at session start).
  Real-path run of engine.inputs.build_features() + engine.yield_momentum
  .build_yield_momentum(f): all 5 series `path_qualified=false`, `turn_watch=null`,
  `null_reason="endpoint comparisons only; complete observed path not qualified"`.
  Holiday census: 1260-row window, 54 non-observed rows for us20y (first
  2021-11-25 Thanksgiving, last 2026-09-07 Labor Day). Isolation A/B/C: real series on
  real bdate grid -> path_qualified=False, turn_watch=None; same series reindexed to
  print every weekday -> path_qualified=True, turn_watch=extreme_high_watch; real
  series on a short holiday-free window -> path_qualified=True. `git show
  origin/main:data/transmission/latest.json` 20y turn_watch="extreme_high_watch"
  (v1-era, calculation_version absent). `python3 -m pytest
  tests/test_yield_momentum.py tests/test_rates_command.py
  tests/test_rate_inflation_transmission.py tests/test_inputs_yield_curve.py -q` ->
  115 passed.
scope:
  - mastermindx-market-intelligence/macro
---

The gate is one line, `engine/yield_momentum.py` `_series_read`:

    out['path_qualified'] = (all(observed) and numeric.notna().all()
                             and item['source_basis'] == 'captured_source_rows')

`observed` is `[o == _date(t) for o, t in zip(dates, index)]` against a
`pd.bdate_range` grid. A US market holiday is a weekday the grid demands and the
Treasury never prints, so it is indistinguishable here from a genuinely missing
print — and one such day anywhere in 1260 rows disqualifies the whole path.

Related: [[DSC-F3-YIELD-MOMENTUM-HAS-NO-CONSUMER]] — why this regression has been
invisible. The field is unread, so a capability that went permanently null between
#6721 and #7291 changed nothing any user or machine could observe.
