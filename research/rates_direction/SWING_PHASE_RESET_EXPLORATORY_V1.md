# Phase/reset exploratory study v1 — pre-outcome contract

Parent: WS:RATES-INFLATION-COMMAND / operation rates-direction-20260924-sol-001 / PR 7909.

Procedure pin: Mastermind 819abc8c23609cdded2b33f6e1bfc7854bd5c847,
Skillpack mastermind.sol_skillpack.v1 1.0.1 / bootstrap major 1.

## Why this is a new hypothesis

The frozen default-crossover studies are negative and remain immutable. They tested
confirmed MACD-RSI / price-Stochastic / Stochastic-RSI crossings as direct next-swing
signals. They did not test the Chairman's more specific visual hypothesis: a broad
yield trend can persist while fast oscillators reset, and a shallow price retracement
plus renewed oscillator acceleration may foreshadow continuation of the next yield
impulse.

This study is explicitly exploratory because the two-year capture's outcomes have
already been examined by the prior crossover study. It can select a candidate for
future prospective shadowing; it cannot establish predictive authority or rescue the
negative crossover result.

## Immutable input and target

Input is only the already-preserved two-year Yahoo ^TNX hourly capture:

- capture time: 2026-09-24T14:17:57Z
- SHA256: 1dc7e9121fd6aa36c5019beba303b629257eb1cab752ae937e4cef1aa8161b76
- symbol/source: Yahoo ^TNX proxy, not proven equivalent to TVC:US10Y
- source semantics: provider regular sessions; no fabricated OHLC or overnight path

Reuse the exact session parser, 12-completed-bar observed-session first-passage
target, one-completed-bar decision delay, volatility-scaled barrier with 5bp floor,
warmup and purged expanding-history probability evaluation from the prior frozen
study. A same-hour dual barrier touch stays ambiguous; neither touch stays no_hit.

Primary discovery partition remains target windows ending strictly before
2026-06-24T00:00:00Z. The later overlap is reported separately. Neither partition is
a pristine holdout because this source history has now been seen by the program.

## Frozen phase features

Broad trend is deliberately distinct from the old 5-bar baseline:

- EMA20 of the yield close, recursive adjust=False
- up trend: close > EMA20 and EMA20 > EMA20 four bars ago
- down trend: close < EMA20 and EMA20 < EMA20 four bars ago
- otherwise neutral

M_EARLY (MACD-RSI early curl):
- up: MACD-RSI histogram remains below zero, its slope turns from non-positive to
  positive, and the broad trend is up
- down: mirror image above zero in a down trend
- a curl remains active for at most 3 bars while histogram slope still points in the
  curl direction

P_RESET (price Stochastic reset):
- up: broad trend up, K visited below 20 within the last 4 completed bars, current
  K > D, and K is rising
- down: broad trend down, K visited above 80 within 4 bars, current K < D, K falling

R_RESET uses the same rule on the supplied Stochastic RSI K/D.

PR_RESET requires P_RESET and R_RESET in the same direction.
MPR_RESET requires M_EARLY, P_RESET and R_RESET in the same direction.

SHALLOW_PR adds relative price strength:
- up: current close is in the top 40% of its trailing 12-bar high-low close range
- down: current close is in the bottom 40%
- neutral / zero-range is inactive

SHALLOW_MPR adds the same strength gate to MPR_RESET and is the declared primary
candidate.

The seven searched candidate configurations are:
M_EARLY, P_RESET, R_RESET, PR_RESET, MPR_RESET, SHALLOW_PR, SHALLOW_MPR.

No parameter variants, threshold sweep, wavelength period search, chart-picked
exceptions or post-outcome reranking are authorized inside this study.

## Baselines and decision metric

Report:
1. unconditional expanding historical frequencies;
2. the prior 5-bar-trend + volatility baseline;
3. a new EMA20 broad-trend + volatility baseline;
4. each phase candidate as an incremental state on top of baseline 3.

Primary comparison: SHALLOW_MPR versus EMA20 broad-trend + volatility using the
three-class sum Brier score on common origins. Lower is better. Also report log loss,
active origins, non-overlapping resolved episodes, directional successes, no-hit
counts and date-averaged HAC diagnostics. The 50-resolved-active-episode floor from
the prior study remains a minimum descriptive adequacy floor, not significance.

The study must report the broad-trend baseline itself versus the old 5-bar baseline,
so an apparent candidate gain cannot secretly be only a trend-definition change.

## Promotion ceiling

All history here is seen-history exploratory development. Even a large positive
result authorizes at most freezing one candidate for a future prospective shadow
through an existing evaluation owner. It cannot alter RIC display authority, equity
risk posture, rank, size, gate, trade, alert or portfolio behavior.

Native Pine/TVC parity, source-clock qualification, independent review and genuinely
prospective issuance/outcomes remain mandatory for stronger claims.
