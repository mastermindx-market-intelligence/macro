---
key: TERMINAL-CHARTED-BOLLINGER-IS-POPULATION-SIGMA
question: >
  The Terminal's Bollinger Bands existed as two different formulas — ChartPanel
  rendered population sigma (ddof=0) while the parity-tested indicatorMath used
  sample sigma (ddof=1) to match this repo's engine/bollinger_event_signals.py
  `_bb_bands()`. Which one is canonical for the indicator a user sees, and what
  happens to the cross-repo parity fixture that pinned the other one?
answer: >
  Population sigma (ddof=0) is canonical for the CHARTED "Bollinger Bands"
  indicator. indicatorMath.bollingerBands() now defaults to it and is the single
  owner; ChartPanel's inlined stddev() is deleted and all three of its BB
  consumers call the owner. The Macro Python `_bb_bands()` contract is NOT
  changed and its fixture (tests/fixtures/tech_parity/expected_bollinger.json)
  is NOT regenerated — it is re-scoped and renamed as what it always actually
  was: the sample-sigma EVENT-SIGNAL bands behind engine/bollinger_event_signals.py,
  now requested explicitly via `bollingerBands(..., ddof: 1)` instead of riding a
  library default that belongs to a different indicator. Two real contracts, named
  separately instead of conflated. Do not "fix" the charted bands back to ddof=1,
  and do not change `_bb_bands()` to population to make them agree.
rationale: >
  The authority is what the product publishes to its own users, not which side
  had a test. Terminal lib/indicators.ts:127 ships IND_DEFS.bb.source — the
  read-only Pine shown by the chart's "Source code..." button (lib/indicators.ts:39)
  — and it reads `dev = mult * ta.stdev(close, length)`. Pine's ta.stdev is
  population, both on TradingView and in the Terminal's own interpreter
  (lib/pine-engine/runtime.ts:481 divides by len). Four other Terminal modules had
  already chosen population deliberately and said so in comments
  (suites/trend/marketDashboard.ts:247 "population sigma, like ta.stdev";
  intradayMath.ts ttmSqueeze, which explicitly says it follows ChartPanel "not
  indicatorMath"; suites/rsix/rsiChannels.ts; indicatorMath volbox). The lone
  ddof=1 outlier traces to pandas' `.std()` DEFAULT inside an event-signal module,
  never to a charting contract — and the same fixture family already aligns RSI to
  Pine ("SMA-seeded RMA, same as Pine ta.rsi"). So the rendered values were right
  and the tested library was wrong; the fix moved the library, leaving user-visible
  bands unchanged. Changing the Python instead would have moved live Macro event
  signals across bb_upper_rejection / bb_lower_rejection and their backtests to
  repair a Terminal-side naming error — a far larger blast radius, in the wrong repo.
alternatives:
  - option: Change ChartPanel to sample sigma (ddof=1) so the chart matches the fixture
    why_not: >
      It would put the displayed chart in conflict with its own published
      "Source code..." definition, with Pine ta.stdev, with TradingView, and with
      the four Terminal modules that already match population on purpose. It also
      changes what users see to satisfy a contract that was never about the chart.
  - option: Change Macro `_bb_bands()` to population and regenerate the fixture
    why_not: >
      ddof=1 is defensible for a statistical event signal, and this moves live
      signal output (bollinger_event_signals) and every backtest that consumes it,
      in this repo, to fix a Terminal-side mistake. Wrong repo, wrong blast radius.
  - option: Leave the divergence documented as the existing test.todo
    why_not: >
      That is the status quo being retired. The todo made the parity suite's green
      misleading: "indicator parity passes" did not imply the displayed bands had
      parity, and the gap had already propagated into a user-visible AI readout.
  - option: Add a second "shared" BB helper for the render path
    why_not: >
      Leaves both old implementations live and creates a third. The point is one
      owner, with the duplicate deleted.
evidence:
  - "Terminal PR mastermindx-market-intelligence/mastermind-terminal#637"
  - "Terminal lib/indicators.ts:127 IND_DEFS.bb.source = `dev = mult * ta.stdev(close, length)`; lib/indicators.ts:39 documents it as user-visible via 'Source code...'"
  - "Terminal lib/pine-engine/runtime.ts:481 — ta.stdev returns Math.sqrt(sum / len), population"
  - "Terminal lib/suites/trend/marketDashboard.ts:247 — `const sd = Math.sqrt(ss / BB_LEN); // population sigma, like ta.stdev`"
  - "Macro engine/bollinger_event_signals.py `_bb_bands()` — close.rolling(n).std(ddof=1), i.e. the pandas default"
  - "Measured on the 500-bar tech_parity fixture: published Pine source vs population bands = 1.4e-15 max relative (same formula); vs ddof=1 = 0.1997% upper / 0.2360% lower (worst bar 246: 101.3087 vs 101.1067)"
  - "Downstream readout impact: get_technicals %B shifts up to 2.171 percentage points and its bbPos label flips on 4/481 fixture bars"
  - "That gap is ~2,000x the 1e-6 parity tolerance and 4x larger than the retired test.todo's '~0.05%' estimate"
  - "Terminal lib/__tests__/bollingerRenderParity.test.ts — pins the charted contract against the published Pine source executed by lib/pine-engine, with a positive control proving the oracle rejects ddof=1 bands"
  - "tests/fixtures/tech_parity/expected_bollinger.json unchanged; no tolerance loosened (new budget 1e-12)"
affects:
  - engine/bollinger_event_signals.py
  - scripts/build_tech_parity_fixtures.py
  - tests/fixtures/tech_parity/expected_bollinger.json
  - tests/fixtures/tech_parity/README.md
  - "DSC:TERMINAL-PUBLISHED-INDICATOR-SOURCE-IS-THE-FORMULA-AUTHORITY"
confidence: high
reversibility: costly
decided_by: 079518c4-0e18-47db-919f-fce689123898
decided_at: 2026-09-18
---

There were never two versions of one indicator here — there were two indicators wearing
one name.

The charted "Bollinger Bands" is defined by what the product shows the user when they
click "Source code…": `ta.sma` for the basis and `ta.stdev` for the deviation, and
`ta.stdev` is population sigma. The Macro engine's `_bb_bands()` is a sample-sigma band
used to fire event signals, and it got ddof=1 because that is what `pandas.Series.std()`
does when you do not pass an argument — not because anyone decided a displayed band
should be a sample estimate.

Conflating them made an anti-drift suite that could pass while the product drifted. The
suite validated a function the chart never called, and a `test.todo` recorded that fact
for as long as it stayed unresolved. Meanwhile the ddof=1 bands did reach a user surface:
`get_technicals`, which advertises itself as TradingView-style, was reporting Bollinger
position and %B derived from bands 2.6% wider than the ones drawn beside them. On the
parity fixture that is up to **2.171 percentage points** of %B — %B is a ratio whose
denominator is the band width, so it moves by roughly ten times the 0.2% band-value gap —
and it flipped the `bbPos` label on 4 of 481 bars (2 `upper_half` to `above_upper_band`,
2 `lower_half` to `below_lower_band`), because the correct population bands are narrower
and price breaches them slightly more often.

Naming them separately costs one `ddof` argument and keeps both honest. The Ribbon EMA
divergence in the same fixture family is deliberately NOT resolved by this decision: the
Terminal already calls the shared `trendRibbon()` from its chart, so it has no equivalent
render-path drift, and its fix is unbounded (shared `ema()`, live Macro signals, and no
clean oracle — the Terminal's Pine `ta.ema` is first-value seeded while TradingView's is
SMA-seeded, a third convention). It stays an open successor problem.
