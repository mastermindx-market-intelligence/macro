# Narrative Repricing V2 — Clock-Clean Wave 1 Results

Date: 2026-09-25
State: TRAINING_EVIDENCE / RESEARCH_ONLY / PRODUCTION_INERT / NO TRADING AUTHORITY
Operation: geopolitical-relief-event-study-20260924-sol-001
Carrier: Macro PR #8012 / sol/geopolitical-relief-event-study-20260924
Source-wave freeze: 0472a27f8e997585d84ddeb16b81ecfefbd82cb4
Source-clock audit: 17966036f6835e81cd650a6d5815210ea91cb78e
V2 preregistration: research/NARRATIVE_REPRICING_V2_PREREG_2026-09-25.md
Evaluation split: research/NARRATIVE_REPRICING_V2_EVALUATION_SPLIT_2026-09-25.json

## 1. Evidence boundary

This receipt records the first outcome extraction from the clock-clean V2 training wave.
Event identities and clocks were frozen before these returns were fetched.

The run used the incumbent Massive/Polygon U.S.-stocks minute-aggregate entitlement with
no permanent minute store. USO remains an explicit oil-price proxy, not direct WTI/Brent
truth. SMH is the response cohort and QQQ the benchmark.

The extraction used the preregistered first-pass law:

- pre-event USO returns at trailing 60 and 240 minutes where available;
- USO move from event availability to +5 minutes;
- SMH minus QQQ residual return from +5 minutes to +20/+35/+65 minutes
  (15/30/60-minute response horizons);
- source-clock and market-data gaps remain null;
- no event timestamp was shifted after observing returns.

The pure repository helper repricing_first_pass() was added after this extraction to
codify the same window semantics. At exact head
54bff69e2466ee2a43dda71ebf6b481e67791c81, the combined focused event-study/replay
suite passed 19 tests. This receipt does not claim a second vendor rerun at that head.

## 2. Primary training rows

| Event | USO pre-60m | USO 0→+5m | SMH-QQQ +5→+20 | +5→+35 primary | +5→+65 |
|---|---:|---:|---:|---:|---:|
| 2026-08-04 Bessent: may have Hormuz deal tomorrow | -272.25 bp | -164.32 bp | +16.12 bp | **+22.86 bp** | +11.87 bp |
| 2026-08-05 agreement approaching | -6.97 bp | +6.10 bp | -17.90 bp | **-29.55 bp** | -5.37 bp |
| 2026-08-06 broad framework 08:28Z | — | — | — | **data gap** | — |
| 2026-08-06 Oman/Iran agreement 19:53Z | +79.06 bp | -43.20 bp | -37.98 bp | **-10.76 bp** | +16.88 bp |
| 2026-08-07 US official expects deal soon | +9.20 bp | -61.84 bp | +3.36 bp | **-20.32 bp** | +16.01 bp |
| 2026-08-09 final stages 11:43Z | — | — | — | **market closed** | — |
| 2026-08-21 navigation talks | -13.34 bp | -17.07 bp | +0.70 bp | **-12.60 bp** | -12.75 bp |
| 2026-08-25 final stages 07:41Z | — | — | — | **market closed / no U.S. ETF tape** | — |
| 2026-09-16 peaceful solution 09:39Z | -67.84 bp | +22.56 bp | — | **response data gap** | — |

Five of nine primary training events had complete +5→+35 response measurement.
Their 30-minute residuals were:

+22.855, -29.551, -10.762, -20.315, -12.598 bp.

Descriptive summary only:

- mean: **-10.07 bp**
- median: **-12.60 bp**
- positive rate: **1/5 = 20%**
- range: **-29.55 to +22.86 bp**

This small training slice does not support a broad claim that geopolitical relief headlines
produce positive semiconductor continuation.

## 3. Causal-direction read

Four fully measured primary rows had USO moving in the expected relief direction over the
first five minutes:

- Aug 4: USO -164.32 bp; primary residual +22.86 bp
- Aug 6 19:53Z: USO -43.20 bp; primary residual -10.76 bp
- Aug 7: USO -61.84 bp; primary residual -20.32 bp
- Aug 21: USO -17.07 bp; primary residual -12.60 bp

Their mean primary residual was approximately **-5.21 bp**, median approximately
**-11.68 bp**, positive rate **25%**.

No V2 threshold is selected from those values. In particular, the old V1 25-bp causal
threshold is not imported as a V2 acceptance rule.

## 4. Strong falsifiers to the simple risk-premium story

Two events are especially useful because oil was rising into the headline and then reversed
lower, yet semiconductor continuation was negative.

### Aug 6, 19:53Z

- USO trailing 60m: +79.06 bp
- USO trailing 240m: +123.57 bp
- USO versus prior RTH close: +371.97 bp
- event→+5m USO: -43.20 bp
- SMH-QQQ +5→+35: **-10.76 bp**

### Aug 7, 19:00Z

- USO trailing 60m: +9.20 bp
- USO trailing 240m: +25.17 bp
- USO versus prior RTH close: +67.86 bp
- event→+5m USO: -61.84 bp
- SMH-QQQ +5→+35: **-20.32 bp**

Therefore:

> "oil risk premium elevated + relief headline + oil reversal" is not sufficient for a
> positive 30-minute semiconductor continuation.

That is a useful falsification of the simplest V2 mechanism.

## 5. Aug 4 is a different state

The only positive complete primary row in this wave, Aug 4, had USO already falling sharply
before the event:

- trailing 60m USO: -272.25 bp
- event→+5m USO: -164.32 bp
- SMH-QQQ +5→+35: +22.86 bp

This is not the Sep 24 setup of a same-session oil risk premium being sharply unwound by a
new headline. It may represent continuation of an already-active relief narrative or a
different cross-asset regime. It must not be used to rescue the original mechanism by
post-hoc relabeling.

## 6. Explicit weak/denial control

The separately frozen Sep 22 09:14Z "could open Hormuz within seven days" report, later
subject to denial/conflict, produced:

- USO trailing 60m: -192.54 bp
- USO event→+5m: -13.63 bp
- SMH-QQQ +5→+20: -5.10 bp
- SMH-QQQ +5→+35: -1.07 bp
- +65m response unavailable

Classification remains a weak/conflicted narrative control, not primary training evidence.

## 7. What the evidence says now

The data so far support a narrower research conclusion:

1. Exact source clocks are load-bearing. Later article/video clocks can fabricate apparent
   lead-lag.
2. Immediate oil confirmation is useful as a filter against generic diplomatic headlines,
   but is not sufficient for semiconductor continuation.
3. Pre-event oil elevation plus a first-five-minute oil reversal is also not sufficient in
   this small sample.
4. September 24 remains unusual. Its continuation needs additional explanatory variables
   before it can be generalized.

Candidate dimensions that remain legitimate under the preregistration and should be measured
without outcome-driven thresholds:

- source novelty / execution credibility (proposal vs signed/official implementation);
- physical-channel specificity (actual Hormuz opening/blockade relief vs generic talks);
- first-impulse breadth across QQQ/SPY/SMH and energy;
- semiconductor-specific competing news;
- broad technology regime and intraday dispersion;
- event timing relative to U.S. cash session / Asia handoff;
- causal reversal normalized by pre-event intraday volatility rather than raw basis points.

These are candidate features to measure, not a new signal recipe.

## 8. Missingness is part of the result

Three source-clean events could not support the primary U.S.-ETF response window:

- Aug 6 08:28Z: SMH tape missing at the event clock;
- Aug 9 11:43Z: Sunday / U.S. ETF market closed;
- Aug 25 07:41Z: before U.S. ETF extended-hours availability.

Sep 16 had causal observations but insufficient SMH response coverage.

The study will not move these event clocks to the next liquid bar or next U.S. open. Doing so
would turn data availability into outcome-selected timing.

## 9. Current disposition

- V1 simple oil-leads-semis lag: falsified at the earliest Sep 24 distribution clock.
- V2 broad oil-risk-unwind continuation: **not supported as a sufficient rule** by Wave 1.
- V2 remains a valid research family because source quality, physical specificity,
  first-impulse breadth and regime interactions remain untested.
- No threshold/model has been selected.
- No holdout has been inspected.
- No product, ranking, alert, sizing, portfolio or execution authority is granted.

## 10. Exact continuation

1. Keep Wave 2 event clocks frozen before outcome access.
2. Continue source-clock expansion toward the >=20-cluster research target.
3. Measure source novelty/credibility and physical-channel specificity as source-side
   attributes before using outcome returns.
4. Add first-impulse breadth and volatility-normalized causal reversal through the pure
   research kernel.
5. Preserve market-closed/data-gap rows rather than re-anchoring them.
6. Do not open the prospective holdout or tune a threshold until training/development
   features are frozen.
