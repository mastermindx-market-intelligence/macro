# Tech Lab Parity Fixtures (TLT-R5)

These fixtures are the **anti-drift contract** between this repo's Python engine and the Terminal's TypeScript `indicatorMath` implementation.

## Source of truth

**This script is the source of truth.** Always regenerate from:

```
python scripts/build_tech_parity_fixtures.py
```

The Terminal copies these fixtures into its own test suite and asserts that its TypeScript indicator implementations produce numerically identical output.

## Fixtures

| File | Contents |
|------|----------|
| `ohlcv.json` | Deterministic synthetic OHLCV input (numpy default_rng(42), 500 business days) |
| `expected_ichimoku.json` | Per-bar Ichimoku lines: tenkan, kijun, span_a, span_b, chikou |
| `expected_ribbon.json` | Per-bar ribbon EMAs: fast_ema (span=20), slow_ema (span=50), ribbon_state (+1/0/-1) |
| `expected_rsi.json` | Per-bar Wilder RSI: rsi_7, rsi_14, rsi_21 (SMA-seeded RMA, same as Pine ta.rsi) |
| `expected_bollinger.json` | Per-bar **event-signal** Bollinger bands: upper, mid, lower (SMA(20), **ddof=1 sample** sigma, k=2.0) — see the scope note below |

## Tolerance

Comparison tolerance: **1e-6 relative** (i.e., `abs(a - b) / max(abs(a), 1e-12) < 1e-6`).

Null (`None`) entries correspond to warmup bars where the indicator is not yet defined.

## Determinism guard

`tests/test_tech_parity_fixtures.py` verifies that regenerating from the script produces byte-identical output. The seed (`_RNG_SEED = 42`) and the OHLCV generator parameters are **frozen** and must not change without re-committing the fixtures.

## Canonical implementations

| Indicator | Python module | Key function |
|-----------|---------------|--------------|
| Ichimoku | `engine.ichimoku_signals` | `_ichimoku_components()` |
| Ribbon EMAs | `engine.dannytrades` | `ribbon_trend()`, `_ema()` |
| RSI (Wilder) | `engine.canon` | `rsi()` (SMA-seeded RMA) |
| Bollinger Bands (event-signal, ddof=1) | `engine.bollinger_event_signals` | `_bb_bands()` |

## Scope note — Bollinger bands are two different indicators

`expected_bollinger.json` pins the **sample-sigma (ddof=1)** bands that drive
`engine/bollinger_event_signals.py`. That is deliberate and unchanged: ddof=1 is what
`pandas.Series.std()` computes by default and it is a reasonable statistical estimator for
an event signal.

It is **not** the contract for the Bollinger Bands the Terminal draws on a chart. Those are
**population sigma (ddof=0)**, because the Terminal publishes `ta.stdev(close, length)` to
its own users as the indicator's definition (`terminal/lib/indicators.ts` `IND_DEFS.bb.source`,
shown by the chart's "Source code…" button) and Pine's `ta.stdev` is population. On this
fixture the two differ by up to 0.24% of band value — ~2,000x the tolerance below.

So the Terminal calls `bollingerBands(bars, len, mult, /* ddof */ 1)` **explicitly** when
asserting against this fixture, and its charted bands are pinned separately in
`terminal/lib/__tests__/bollingerRenderParity.test.ts` against the published Pine source.
Do not "reconcile" the two by regenerating this fixture or by changing `_bb_bands()`.
Decision of record: `DEC:TERMINAL-CHARTED-BOLLINGER-IS-POPULATION-SIGMA`.
