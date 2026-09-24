# Yield swing phase: the Chairman's two-hour-chart hypothesis

Status: pre-outcome research specification and executed source-contract audit; NOT a validated forecast, completed intraday study, or deployed capability.
Parent: WS:RATES-INFLATION-COMMAND / Macro PR 7909.
Operation: rates-direction-20260924-sol-001 (records-only continuation; no new control plane).
Authority: continuing end-to-end Chairman delegation plus September 24 chart clarification.
Procedure: Mastermind 5060527c1d52639eb1bfd84413ab7419e7470cbd, Skillpack 1.0.1/bootstrap1.
Source inspected: Macro b076a4004599215ef21765c437aaade48f40388d.
Records carrier recovered clean at 748067a3631959e2dd6ffe25ebc7675ed82395ee.
Direct principal reason: PRINCIPAL_JUDGMENT for the target distinction; LOWER_TOTAL_OVERHEAD for bounded synthetic source probes. No worker commissioned.

## 1. The actual hypothesis

The user points to alternating yield impulses and retracements nested within a broader trend. The job is to identify a developing swing, its likely continuation/reversal and its conditional equity effect, not merely forecast the level at a fixed future endpoint.
A yield path can fall 15bp, recover 15bp, and end unchanged. An endpoint forecast can miss the entire tradable or risk-relevant path. This is a distinct target, not a way to relabel RD1's failed construction as successful.
Retain separate outputs: observed phase; forecast of the next material excursion; chance of an abrupt discontinuity; and conditional equity transmission. No output automatically ranks, sizes, gates or originates a trade.

## 2. What the supplied image supports

The screenshot identifies TVC:US10Y, 2h, September 24 at 05:09 UTC-7. It displays 5.118% and a blue overlay at 4.997%, a 12.1bp difference. The overlay formula/period is not visible. The rightmost candle has a countdown and is unfinished.
The visible yield path has a rising broader trend, repeated retracements, and a new local high area. The lower oscillators have repeated cycles and the fastest lower panel is curling down from a high reading. These are image observations, not authenticated quotes or closed-bar signals.
The two-hour chart alone does not establish daily/weekly indicator alignment, a fixed wavelength, current equity-rate correlation, or a validated probability that the yield is topping.
A high oscillator is not proof of an impending yield decline. Momentum slowing, yields actually falling, and a durable trend reversal are different states. A negative oscillator reset during an uptrend can precede renewed upward yield pressure.

## 3. Intended measurement, not a sinusoidal clock

Use one-sided, closed-bar measurements. Candidate state dimensions are yield level; recent bp change and its acceleration; distance from a trailing baseline; impulse/retracement amplitude; canonical RSI-MACD line/signal/histogram and slope; StochRSI K/D; and source-qualified higher-timeframe context.
Ordinary MACD, MACD of RSI, and RSI of MACD are not interchangeable. engine/canon.py owns the current RSI14 -> EMA14 minus EMA60 -> EMA5 signal and StochRSI14/3/3 formulas. The image does not certify those exact settings. Bind an exported indicator/settings golden slice before calling a run an exact replication.
Begin with a two-hour primary signal and the last completed daily context. Four-hour and weekly context are separately registered additions, not a vote-counting ensemble. Shared input bars make these features dependent.
Describe rising/accelerating, rising/decelerating, falling/accelerating and falling/decelerating separately. Keep the oscillator's own phase distinct from actual yield velocity: a histogram is not literally the second derivative of yields.
Do not assume an oscillator cycle is periodic in clock time. If spectral or wavelet features are studied, use only historical windows, test endpoint stability and compare with autocorrelated/volatility-clustered surrogates. No centered smoother, future pivot, full-sample phase estimate or future closed daily bar may enter a forecast.

## 4. Rate direction is not a universal risk switch

Estimate equity responses from matched-clock equity RETURNS and yield CHANGES, not correlations of their levels. Learn any response sign only from data known before the decision. Same-bar comovement is not lead-lag prediction or causal identification.
Distinguish conditional scenarios: yields up/equities down (discount/inflation pressure); yields down/equities up (rate relief); yields down/equities down (growth/credit stress); yields up/equities up (growth-led repricing). The observed quadrant is not sufficient to diagnose the cause.
A rates downswing is an equity tailwind only when the currently qualified response is consistent with that interpretation. Preserve credit, breadth, real-yield and policy context through existing owners. Do not call every yield decline risk-on.
Use 2Y/5Y/10Y/30Y and real/nominal decomposition as corroborating context, with asynchronous or unavailable sources explicit. Bond-price futures must not be interpreted as yields without the required instrument/roll convention.

## 5. Discriminating experiment, before any new market outcomes

Question A: does a causal oscillator turn improve the probability of a material yield move in its direction BEFORE an equally sized adverse move, conditional on prior trend and volatility?
Question B: does that signal improve forecasts of SUBSEQUENT equity returns/drawdowns beyond equity-only trend/volatility and the prevailing rates-response baseline? Success on A does not establish B.
Proposed primary instrument/timeframe: qualified 10Y yield, 2h completed bars. Proposed path window: next 12 completed bars, explicitly NOT 24 continuous hours. Before registration, freeze the source calendar, latency, barrier size/rule, flat/no-hit category and one trigger definition.
Compare an early curl with a confirmed crossover as separate candidates: earlier can buy lead time but more false signals. Do not retrospectively choose whichever trigger preceded a turning point most attractively.
At the decision, freeze a symmetric bp barrier scaled by PRE-decision volatility and a predeclared floor. Score first up-hit/down-hit/neither; if both barriers are crossed inside a bar and order is unavailable, retain ambiguous, never assume the favorable order. A missing bar, unresolved horizon or stale source is not a losing trade or a neutral market.
Primary score should be a proper probability score on common eligible origins, compared with a train-only conditional-frequency benchmark and a trend/volatility baseline. Also retain a simple oscillator-extreme rule and the canonical crossover as comparators. No-change point MSE is not the only ruler for a path-dependent classification question.
Report precision, recall, false-alert rate, abstention/coverage, actual confirmation latency, bp remaining AFTER confirmation, and adverse excursion. A beautiful backdated peak is useless if most of the move was gone before a signal could be known.
One episode contributes one primary decision, under a frozen reset rule. Cluster uncertainty by time/episode, purge overlapping horizons, register all configurations in the existing TrialLedger before evaluation, and preserve failed/abstained examples. Do not convert overlapping bars into independent sample counts.
RD1's examined 2021-2025 history and the motivating September 2026 chart are SEEN. They can be developmental diagnostics, not relabeled untouched holdouts. Forward validation starts only when an immutable accepted signal is actually recorded before its outcome.
This document freezes the question and boundaries, not completed TrialLedger registration. No new market outcome, empirical fit, threshold search or historical return study ran in this continuation.

## 6. Existing HS-1 is not an exact replication; source probes found material defects

Inspected files: scripts/research/hs1_yield_turn_catalog.py, engine/cycles.py, engine/canon.py and reports/ric-hs1-yield-turn-catalog.md at the pinned Macro revision.
The old report uses three-business-day resampling and 21/63-observation outcomes. Its header calls the MACD events RSI-MACD, but _make_3b_grid calls cycles.macd_parts(grid): ordinary 12/26/9 MACD on yield levels. canon.rsi_macd instead transforms RSI with 14/60/5 EMA parameters. Neither the old label nor RD1's ridge test certifies the exact two-hour screenshot hypothesis.

Executed on the original Studio, process 99660, pandas 3.0.5, using the exact git-show HS1 source and byte-equal canon/cycles dependencies. Synthetic input only: 720 business-dated observations, 4 + .0005*t + .12*sin(t/9). Four assertions passed; no repository write or market-data read occurred.
Source script SHA256: 78ac732312fc33368bf2f75d2f7e15c5b7cf03b79a9dc6642b0eb7eb0b2d51b8.

1. Timing defect: resample('3B').last() keeps the left bucket label; _extract_events_from_grid copies that label into daily_date as though it were the last observation. All 112 synthetic events were dated before the last input in their bucket. First example: event dated 2024-08-20 requires the 2024-08-22 input. This is a source-clock defect, not a measured intraday strategy result.
2. Direction-baseline defect: _compute_base_rates always computes P(yield higher). _summarize_events subtracts this unchanged base from both bull and bear directional-hit rates. On a monotone rising synthetic series its base is 1.0; the appropriate falling-yield baseline is 0.0. Real-data correction must compute the appropriate direction directly and retain flats, not blindly use 1-P(up).
3. Formula identity check: ordinary price MACD doubles when the positive input scale doubles; canonical RSI-MACD is unchanged. Both passed on the synthetic path, demonstrating the claimed indicators are not the same calculation.

Do not use the legacy excess hit rates or event timing as predictive acceptance until repaired and independently reviewed. Preserve the old report as disputed historical evidence; do not erase it, overwrite it with favorable numbers, or rerun all its market outcomes casually. This finding neither kills the swing hypothesis nor establishes that it works.
Required repair: preserve first-known/last-input/closed-bar clocks; never re-date a completed aggregate to its first session; compare bull with P(up), bear with P(down), and keep ties separate; bind the exact formula/grid identity. A corrected report requires its own versioned reconstruction with retained selection history.

## 7. Consumer and implementation order

Keep RD2's contract-constituent and roll-attribution work; it addresses a different measurement error. Do not block every waveform source/clock unit on every policy dependency, and do not quietly replace the original program with chart pattern recognition.
First qualify the actual 2h source and the exact indicator golden vector, while repairing the demonstrated HS1 clock/baseline defects on separately reconciled source custody. Then preregister the one path-target experiment and run through existing TrialLedger/Evaluation owners. Only after a checked useful result should an experimental phase/probability projection enter existing RIC/Transmission and their forecast/evaluation publication path.
The product should distinguish: observed state; candidate warning; confirmed change; and evidence/uncertainty. A sample description is 'broader yield uptrend; short-term momentum cooling; yield reversal not confirmed; equity effect depends on the active rates-response regime.' This is descriptive copy, not an actual generated forecast.
For chart-time precision, preserve provider identity, instrument mapping, quote vs settlement basis, timezone/session alignment, bar completion and first-known timestamps. Do not upsample FRED daily closes into fake two-hour observations. A futures proxy must retain price/yield sign, contract rolls and cheapest-to-deliver/benchmark differences.
Acceptance requires live closed-bar input -> existing indicator -> dated state -> existing consumer -> immutable forward record -> matured evaluation, plus real browser proof when a UI ships. Evidence clocks, failures and no-promotion ceilings remain visible.

## 8. Public methodological sources checked September 24

- TradingView Stochastic RSI documentation: https://www.tradingview.com/support/solutions/43000502333-stochastic-rsi-stoch-rsi/ (indicator-of-indicator and trend caveats).
- TradingView execution model: https://www.tradingview.com/pine-script-docs/language/execution-model/ (forming vs confirmed bars).
- BIS, The correlation of equity and bond returns: https://www.bis.org/publications/correlation-equity-and-bond-returns (inflation/growth conditions; bond RETURN sign differs from yield-change sign).
- Federal Reserve, Jumps in Bond Yields at Known Times: https://www.federalreserve.gov/econres/feds/jumps-in-bond-yields-at-known-times.htm (scheduled event times, uncertain jump sizes; not a current calibrated forecast).
- Federal Reserve, The Treasury Tantrum of 2023: https://www.federalreserve.gov/econres/notes/feds-notes/the-treasury-tantrum-of-2023-20240903.html (historical two-sided yield move, model-dependent attribution).

MISSION_COMPLETE: false. This continuation delivered a scoped hypothesis and verified source-counterexamples, not a new forecasting edge. RD1 freeze/results/ledger, the existing RD2 bundle and all sibling holds remain unchanged. No worker, background watcher, new collector, live risk change or production release was started.

## Appendix: reproduce the bounded source-contract probes (synthetic only)

Run from the reconciled original Macro workspace with its existing dependencies.
This loads only the pinned script and verified indicator dependencies; it never
calls the report's main(), reads its market data, or updates a result/ledger.

```python
import hashlib, json, subprocess, types
from pathlib import Path
import numpy as np
import pandas as pd
root = Path.cwd()
rev = 'b076a4004599215ef21765c437aaade48f40388d'
path = 'scripts/research/hs1_yield_turn_catalog.py'
raw = subprocess.check_output(['git', 'show', f'{rev}:{path}'])
mod = types.ModuleType('hs1_source_probe')
mod.__file__ = str(root / path)
exec(compile(raw, mod.__file__, 'exec'), mod.__dict__)
from engine import canon, cycles
for name in ('engine/canon.py', 'engine/cycles.py'):
    assert (root/name).read_bytes() == subprocess.check_output(['git', 'show', f'{rev}:{name}'])
idx = pd.bdate_range('2024-01-02', periods=720)
t = np.arange(len(idx), dtype=float)
s = pd.Series(4.0 + .0005*t + .12*np.sin(t/9.0), index=idx)
events = mod._extract_events_from_grid('DGS10', mod._make_3b_grid(s, 'DGS10'))
closes = pd.Series(idx, index=idx).resample('3B').last()
early = [(e['daily_date'], closes.loc[e['daily_date']]) for e in events
         if e['daily_date'] < closes.loc[e['daily_date']]]
assert events and early
up = pd.Series(3.0 + .001*t, index=idx)
base = mod._compute_base_rates(up, str(idx[0].date()), str(idx[-1].date()), None)
p_down = float(((up.shift(-21)-up).dropna() < 0).mean())
assert base['h21_base'] == 1.0 and p_down == 0.0
m1, m2 = cycles.macd_parts(s)['line'], cycles.macd_parts(2*s)['line']
r1, _ = canon.rsi_macd(s)
r2, _ = canon.rsi_macd(2*s)
assert np.allclose(m2.dropna(), 2*m1.dropna())
assert np.allclose(r1.dropna(), r2.dropna())
print(json.dumps({'events':len(events), 'early':len(early),
 'first':[str(x.date()) for x in early[0]], 'base_up':base['h21_base'],
 'base_down':p_down, 'script_sha256':hashlib.sha256(raw).hexdigest()}))
```
