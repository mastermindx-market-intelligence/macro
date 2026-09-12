# Leadership Persistence RPH-1 — Daily Sector-Control Preregistration

**Frozen:** 2026-09-12, before any RPH-1 archive outcome is read  
**Operation:** `leadership-persistence-sector-control-rph1-20260912-sol-001`  
**Parent workstream:** `WS:LEADERSHIP-PERSISTENCE-INTELLIGENCE`  
**Parent source carrier:** Macro PR #7064, exact head `8d198b42f6bff491a49b1f3467b56ca4bb673f80`  
**Cross-owner boundary:** `WS:TEMPORAL-GRAIN-INTELLIGENCE`, Macro PR #6803  
**Protected procedure:** `mastermindx-market-intelligence/Mastermind@57a2672af5b9dcea282e4bae01d1a0b9d10bb1cd`  
**Capability at freeze:** `SPEC_ONLY`  
**Authority at birth:** research/display context only; rank, gate, size, entry, exit, trade, Prophet, Oracle and portfolio authority are all false

## 1. Outcome and exact bounded question

RPH-0 measured the persistence of the **published theme-output surface**. It found that broad ordering,
strict-leader residency and published-score pressure can move on different clocks. It did not test
whether the corresponding liquid sector proxies still carry economic continuation, and it did not
test daily versus two-session or three-session MACD timing.

RPH-1 is a deliberately smaller **daily-data control** over the eleven Select Sector SPDR ETFs. It
asks:

> On the exact repository price bytes available to this carrier, how persistent is five-session and
> twenty-one-session sector leadership; how do cross-sectional dispersion and short-window sector
> correlation compare with their immediately preceding history; and, under a phase-complete standard
> MACD construction, do one-session bullish crosses retain more subsequent close-to-close sector and
> SPY-relative return than two-session or three-session crosses?

This is a discriminating control, not the whole Chairman outcome. It can falsify or support the
narrow claim that slower daily-derived confirmation is late on this archive. It cannot answer the
four-hour question, reproduce a TradingView chart, establish execution utility, infer causal capital
migration, or choose a production timeframe.

## 2. Why this is one successor and not a duplicate system

- RPH-0 remains the sole carrier for published theme-output persistence and stays byte-untouched.
- Temporal Grain remains the owner of exact chart identity, exchange/session anchoring, lower-grain
  construction, G/A/K/D separation and any later usefulness/mechanism diagnosis.
- Existing Sector Pulse, Rotation Events, Subsector Turn and Prophet Entry Truth retain all product,
  event, rank and entry authority.
- RPH-1 adds no regime enum, state store, event ledger, membership model, page, ranker, gate or
  scheduler. It is a deterministic research projection whose result is inert unless a later,
  independently governed consumer study is admitted.

The implementation must live under the existing `research/rotation_persistence` research surface and
must reuse the existing strict JSON/output-boundary utilities. It may not import a production writer.

## 3. Frozen universe and source identity

Sector universe, in fixed lexical order:

`XLB, XLC, XLE, XLF, XLI, XLK, XLP, XLRE, XLU, XLV, XLY`

Benchmark:

`SPY`

Source paths:

`data/yahoo/<SYMBOL>.parquet`

The source revision at commission is the parent exact head
`8d198b42f6bff491a49b1f3467b56ca4bb673f80`. Every file is bound by a byte SHA-256 in the result.
The result reports the actual first and last retained session; no date is inferred from the current
clock or from the preregistration date.

For each file the loader must:

1. require a `close` column;
2. convert the index to timezone-naive normalized dates;
3. stable-sort ascending and keep the first row for a duplicate date, recording every duplicate;
4. coerce close to numeric and drop non-finite or non-positive observations, recording the count;
5. preserve only one close per session and never forward-fill, backward-fill or interpolate.

The analysis panel is the exact complete-date intersection of all twelve retained series. The result
reports union rows, complete rows, excluded rows and each symbol's retained coverage. If the complete
panel cannot support at least 100 completed bars for every three-session phase plus the largest
forward horizon, the operation returns `INSUFFICIENT_HISTORY`; it does not silently shorten warm-up.

This source is an archive control, not a point-in-time membership reconstruction and not proof that
Yahoo matches a vendor chart.

## 4. Leadership constructions

Primary construction:

`L = 5` complete common sessions.

Sensitivity construction:

`L = 21` complete common sessions.

For sector `i` on session `t`:

`leadership_return(i,t,L) = ln(close(i,t) / close(i,t-L))`

Ranks are descending leadership return, average-ranked for correlation. An exact top-three set is
formed by stable sorting on `(leadership_return descending, ticker ascending)` so ties never create a
variable denominator. The chance-retention reference is fixed at `3 / 11`.

Frozen forward horizons:

`H = [1, 3, 5, 7, 10, 20]` complete common sessions.

For each lookback and horizon, compute once per eligible anchor:

1. **Descriptive rank persistence** — cross-sectional Spearman correlation between leadership ranks
   at `t` and `t+h`.
2. **Predictive persistence** — cross-sectional Spearman correlation between the trailing leadership
   return at `t` and the strictly subsequent log return `ln(close(i,t+h)/close(i,t))`.
3. **Top-three retention** — fraction of the exact top-three at `t` still in the exact top-three at
   `t+h`.

These are separate estimands. A persistent rank surface can coexist with negative predictive
persistence. Neither is a trade rule.

## 5. Frozen windows, floors and summaries

Every anchor-indexed metric is summarized over:

- `all`: every eligible matured anchor;
- `recent_20`: the latest 20 eligible matured anchors;
- `recent_60`: the latest 60 eligible matured anchors;
- `prior_252`: up to 252 eligible anchors immediately preceding `recent_20`.

A summary is `MEASURED` only when it contains at least eight observations. Otherwise estimates are
null with `INSUFFICIENT_HISTORY`. Every summary publishes count, start date, end date, arithmetic
mean, median and sample standard deviation. The end date is the anchor date, so it naturally differs
by horizon. No confidence interval or multiple-testing promotion decision is attached to this bounded
control.

## 6. Dispersion and correlation controls

Daily sector return is the simple close-to-close return on the complete panel.

**Dispersion** on date `t` is the sample standard deviation across the eleven sector daily returns.
It is summarized over the same `all`, `recent_20`, `recent_60` and `prior_252` windows.

**Correlation** is constructed for every date with twenty complete daily-return observations:

1. compute the 11-by-11 Pearson correlation matrix over the trailing 20 sessions;
2. average the 55 unique off-diagonal sector pairs;
3. summarize that date-indexed series over the same windows.

The result reports recent-minus-prior and recent/prior ratios when both sides are measured. These
statistics describe co-movement. They may not be called breadth, money migration, crowding, causality
or a regime authority.

## 7. Frozen daily/2-session/3-session MACD control

Timeframes:

- `1D`: one complete common session; phase `0`;
- `2D`: two complete common sessions; phases `0` and `1`;
- `3D`: three complete common sessions; phases `0`, `1` and `2`.

For timeframe length `n` and phase `p`, drop the first `p` sessions, partition the remaining ordered
common-session vector into consecutive non-overlapping groups of `n`, discard the incomplete tail,
and use the final close and final session date of each group. Every phase is reported separately.
This positional phase grid is intentional sensitivity analysis. It is **not** represented as exact
TradingView, exchange-session or absolute-calendar parity; that remains Temporal Grain ownership.

Standard MACD is frozen as:

- fast EMA span 12;
- slow EMA span 26;
- signal EMA span 9;
- pandas-style recursive EMA with `adjust=False`;
- a bullish cross when histogram changes from `<= 0` to `> 0`;
- no cross is eligible until at least 100 completed timeframe bars exist, regardless of EMA
  initialization.

A signal date is the final daily session of the completed timeframe bar. No incomplete bar may emit a
cross.

## 8. Frozen forward diagnostic ruler

For every eligible bullish cross and sector, compute close-to-close simple return from the signal
session close to `1, 3, 5, 10` complete daily sessions later. Compute SPY-relative return as sector
return minus SPY return over the identical dates.

This is a diagnostic mark, not an executable fill. It assumes no order, spread, slippage, tax,
latency or same-close attainability. It does not compute P&L, stop/exit policy, MFE/MAE or remaining
trend life.

For every timeframe, phase and forward horizon, summarize:

- `all` matured observations;
- observations whose signal dates are among the latest 20 unique matured signal dates;
- observations whose signal dates are among the latest 60 unique matured signal dates.

Each cell reports unique signal-date count, observation count, signal-date start/end, median and mean
absolute return, median and mean SPY-relative return, and positive-rate for each. A cell requires at
least eight observations to be `MEASURED`. Phase-pooled rows are displayed only as explicitly
non-independent descriptive aggregates; phase-specific rows remain primary.

## 9. Predeclared phase-robust hierarchy descriptor

For each forward horizon and signal-date window, use median SPY-relative return as the primary ruler.
The descriptor is emitted only when 1D and every 2D/3D phase each have at least eight observations:

- `ONE_DAY_ABOVE_ALL_SLOWER_PHASES` when the 1D median is greater than the maximum median of all 2D
  and 3D phases;
- `ONE_DAY_BELOW_ALL_SLOWER_PHASES` when the 1D median is less than the minimum median of all 2D and
  3D phases;
- `MIXED_PHASES` otherwise;
- `INSUFFICIENT_SIGNALS` when the evidence floor is not met.

This descriptor is descriptive and archive-specific. It does not establish causality, optimality,
execution utility or a production timeframe. No favorable horizon is selected after outcomes are
read; all four frozen forward horizons remain visible.

## 10. Result contract

The CLI writes strict deterministic UTF-8 JSON and Markdown to an explicitly supplied research output
directory. The schema is:

`research.rotation_persistence_sector_control_rph1.v1`

Required top-level fields:

- `schema_version`
- `operation_key`
- `produced_at`
- `source`
- `parameters`
- `quality`
- `leadership`
- `dispersion`
- `correlation`
- `macd_control`
- `hierarchy`
- `authority`
- `limitations`

JSON keys are sorted and NaN/Infinity are forbidden. The only injected nondeterminism is
`produced_at`. The CLI refuses outputs inside `data/`, `site/`, `engine/` or `config/` and performs no
network access.

Authority is fixed to:

```json
{
  "is_context_only": true,
  "may_rank": false,
  "may_gate": false,
  "may_size": false,
  "may_trade": false,
  "may_modify_prophet": false,
  "may_modify_oracle": false
}
```

## 11. Interpretation boundaries fixed before results

RPH-1 may conclude only that, on the exact source bytes:

- sector leadership ranks and subsequent sector returns show measured persistence, reversal or an
  unresolved/mixed surface at the frozen horizons;
- recent dispersion or average pairwise correlation is above, below or similar to its immediate
  prior window as a descriptive comparison;
- one-session MACD cross outcomes are above, below or mixed relative to every tested slower phase
  under the frozen descriptor.

RPH-1 may not conclude:

- that 4H is superior or inferior;
- that 1D/2D/3D is an optimal or production timeframe;
- that a bullish cross is an entry instruction;
- that correlation proves money movement or a causal rotation regime;
- that sector ETF behavior proves current theme/member behavior;
- that the result generalizes beyond the exact archive, market era or data basis;
- that any favorable cell can be selected while unfavorable frozen cells are hidden.

A null, mixed or negative result is successful scientific completion. The exact next dependency after
this control is the existing Temporal Grain gate for exact lower-grain/chart identity and a separately
preregistered utility/latency study; RPH-1 itself cannot bypass that gate.
