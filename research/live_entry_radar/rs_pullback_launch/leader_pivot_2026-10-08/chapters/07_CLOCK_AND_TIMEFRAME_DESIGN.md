# 07 | Clock and timeframe research design

## Separate G, A, K and D

**G: grain** is the observation interval. **A: anchor/session** defines where intervals begin, end and reset. **K: kernel/filter memory** determines how much physical history a transform uses. **D: data plane** includes source, basis, identity, corporate actions, finality and known-at semantics. Change one axis at a time or explicitly call the comparison joint. [I14–I15]

The 30m structural core is the reference. A 15m anticipation role, later 1m/5m/15m execution observations, a higher intraday context and daily leadership are separate roles. The same timeframe can be useful for one role and inappropriate for another. Evaluation horizons stay fixed while a clock changes.

## Exact session arithmetic, executed

Normal US core hours are 09:30–16:00 ET; a published 13:00 early close creates a 210-minute core session. Arithmetic below was checked by the included script. No return series was involved. [E01, M01]

| Grain | Full bars in 390m | Normal closing stub | Full bars in 210m | Early-close stub |
|---|---:|---:|---:|---:|
| 15m | 26 | 0m | 14 | 0m |
| 30m | 13 | 0m | 7 | 0m |
| 60m | 6 | 30m | 3 | 30m |
| 65m | 6 | 0m | 3 | 15m |
| 120m | 3 | 30m | 1 | 90m |
| 130m | 3 | 0m | 1 | 80m |
| 195m | 2 | 0m | 1 | 15m |
| 240m | 1 | 150m | 0 | 210m |

A nominal 240m bar spanning the 150-minute closing remainder is not a full four-hour observation. On an early close, there is no full current-day 240m bar at all. Similarly, normal-session-native 65/130/195m clocks are not early-close-native.

Thirty minutes also has no unique divisibility argument: fifteen minutes divides both session lengths. Thirty is a reasonable sparsity/interpretability prior; its predictive superiority is still an empirical question.

## Availability is a major confound

With a 09:30 anchor, the first full current-day 240m bar closes at 13:30. Using it for a morning entry backdates information. Using the prior day's completed 240m context is causal but changes freshness. Restricting the sample to the afternoon changes the population. Under a full 120-RTH-minute outcome ending before the close, the fresh-current-day 240m comparison has a particularly narrow remaining decision window. [M01]

Session-native higher bars are also often out of phase with 30m decision boundaries. A newly completed 65m bar at 10:35 is not available at 10:30, while a completed 60m bar may be. Preserve each latest-completed context's age, and report both common-support comparisons and full-population missed/abstained opportunities. Do not interpolate or use the unfinished higher bar to make the clocks look equally fresh.

## Bounded pairing family

The planned higher-context comparison consists of these ten named specifications, each using the same daily eligibility and source plane:

1. 30m + Daily.
2. 15m anticipation → 30m + Daily.
3. 30m + 60m + Daily.
4. 30m + 65m + Daily.
5. 30m + 120m + Daily.
6. 30m + 130m + Daily.
7. 30m + 195m + Daily.
8. 30m + 240m + Daily.
9. Later execution observation + 30m + 120m + Daily.
10. Later execution observation + 30m + 240m + Daily.

Separately compare the fixed-multiscale references and a lawful adaptive-band challenger. This list is a bounded design family, not ten authorized or completed trials. Execution observation has one primary 1m definition; 5m and 15m execution are secondary registered comparisons, not an unlimited search.

Before crowning 30m itself, run core 15m/30m/60m comparisons on a fixed eligible population and horizon. Higher-timeframe comparisons alone cannot establish that the structural core is best. Keep lookback memory in physical time when comparing core grains; the primary 30m four-bar reference corresponds to 120 minutes, not an automatic four bars on every grain.

## Filter-memory control, executed

For an exponential filter with coefficient `α` on grain `g`:

```text
half_life_minutes = g × log(0.5) / log(1 − α)
α_new = 1 − (1 − α_reference)^(g_new / g_reference)
```

For EMA-N, `α = 2/(N+1)`; for Wilder-N, `α = 1/N`. A 120m EMA14 has a physical half-life about **581.25 minutes**. A memory-matched 30m exponential filter has effective EMA period about **55.91**, not 14. A 120m Wilder14 has a half-life about **1,122.38 minutes** and a matched 30m effective Wilder period about **54.48**. [M01]

These formulas match the decay kernel, not the entire nonlinear indicator. An RSI, stochastic, high/low range or nested MACD stack may not have an exact equivalent under resampling. Include a same-minute-path physical-time filter control and report residual differences. Merely keeping “14 periods” while quadrupling grain changes memory fourfold and cannot identify a pure G effect.

## Registered controls

For each reference comparison, bind: exchange calendar/version; timezone and DST rule; regular versus extended session; anchor; full/stub policy; price basis; known-at rule; indicator formula; physical kernel; current-bar completeness; previous-session carry rule; and observation age.

Primary context uses the latest fully completed supported bar, with explicit age. Full closing stubs are retained as a separate duration-tagged observation but are not passed to a formula as if they had the nominal duration. Missing/no-trade/halts follow the data owner's semantics; absent rows are never blindly forward-filled.

Compare the reference 09:30 bucket anchor with one predeclared alternative anchor and a rolling fixed-duration context. These are A experiments. Different vendor bars or adjusted versus unadjusted histories are D experiments and must not be sold as clock effects.

## Fixed multiscale must be difficult to beat

Use three references: an equal-weight fixed multiscale context; a median/consensus context; and the same primitive multiresolution covariates in a model without explicit clock selection. Keep the context vector visible rather than turning agreement into an opaque score. A selected timeframe must add value beyond simply supplying the model those same horizons. [I15]

Temporal Grain may eventually supply `STABLE_BAND`, `MULTISCALE`, `UNSTABLE` or `UNRESOLVED`, not a forced winning interval. A changing band must have a known-at time, support, uncertainty, transition policy and fixed target reference. A clock cannot change the outcome horizon that will grade it. [I15–I16]

## Time of day and setup species

Use prior-only same-slot range/volume expectations, initially the preceding 20 supported sessions with at least ten observations per slot. Separate opening, midmorning, midday, afternoon and auction-adjacent periods; stratify normal and short sessions rather than pretending the same slot always means the same market environment. These support choices are protocol priors, not estimated optimal parameters.

The first population is leader pullback/reclaim. Breakout retests, deep bases, post-news digestion, slow megacap resets and hypervolatile resets are possible later Setup Species, not excuses to make each ticker its own strategy. A structural clock must generalize across measured behavior and untouched names. [I16–I19]
