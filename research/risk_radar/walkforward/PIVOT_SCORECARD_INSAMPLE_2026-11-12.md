# Risk Radar pivot scorecard — in-sample reference, 2020-01-02 → 2026-11-10

**Primary read (Chairman steer 2026-11-12):** the goal is identifying pivots accurately, not beating
SPY. For every turn into risk-off (a top) and back to risk-on (a bottom): was it flagged, and how
many sessions before or after. Paper economics (`SCORECARD_INSAMPLE_2026-11-12.md` §3b) are now a
secondary column.

**Label: IN-SAMPLE.** v2 constants were chosen on this window; 2024+ is the Radar's own seen
history, not the desk's sealed confirmation. Episode counts sit beside every figure; intervals are
exact 90% (Clopper-Pearson) and no tighter claim is made on 9 turns.

Code: `engine/risk_radar_eval/pivots.py` (`score_pivots`, `Turn`, `turns_from_episodes`);
runner `scripts/research/risk_radar_pivot_insample.py`; raw output
`PIVOT_INSAMPLE_v2_2020-2026.json` (depths 5/7/10%, post windows 5/10/21).

## Definitions

- **Turns.** Top = the SPY total-return peak of a ≥depth drawdown episode (shared definition in
  `labels.py`). Bottom = the episode trough, only once the episode has recovered (an open
  episode's low is not a turn yet). Any other turn catalogue (the desk's swing rule, other assets)
  plugs in as a list of `Turn` and is scored identically.
- **Calls.** Risk-off call = an alert run starting. All-clear = the alert switching off **and
  staying off ≥10 sessions**; a shorter off-flicker is not an all-clear.
- **Flagged** = a call within [turn − 21, turn + post] sessions. Delay = call − turn (negative =
  early). Primary post window = **10 sessions** ("a reliable call a few sessions after the turn");
  5 and 21 shown for sensitivity. A state already on before the window does not flag the turn.
- **False risk-off** = a risk-off call in no top window and not inside an episode. **Premature
  all-clear** = an all-clear or flicker between an episode's onset and its trough.
- Censored turns (window outside the scored span) are excluded, not scored as misses.

## Results, ≥5% turns (9 tops, 8 bottoms; the 2026-10 episode is open), post window 10

| Series | Days on | Tops flagged [90% CI] | Top delays | Bottoms flagged [90% CI] | Bottom delays | False risk-off /yr | Premature all-clear /yr |
|---|---:|---|---|---|---|---:|---:|
| Radar loud | 15.7% | 1/9 [.01, .43] | +6 | 1/8 [.01, .47] | +1 | 0.0 | 1.75 |
| Radar risk-off | 13.9% | 1/9 [.01, .43] | +6 | 1/8 [.01, .47] | +1 | 0.0 | 2.05 |
| Radar caution+ | 78.0% | 4/9 [.17, .75] | −12, −16, −21, −20 | 1/8 [.01, .47] | +4 | 4.09 | 0.88 |
| SPY < 200d | 19.3% | 1/9 [.01, .43] | +6 | 1/8 [.01, .47] | +6 | 0.0 | 1.17 |
| VIX ≥ 20 | 41.2% | 6/9 [.35, .90] | +3, −11, −16, +6, −13, −5 | 4/8 [.19, .81] | +6, +6, +3, +7 | 2.78 | 2.19 |
| VIX ≥ 25 | 20.3% | 2/9 [.04, .55] | +3, −9 | 5/8 [.29, .89] | −9, +3, −19, +1, +6 | 1.61 | 1.75 |
| HY OAS 21d top decile | 11.0% | 3/9 [.10, .66] | −16, −13, −6 | 4/8 [.19, .81] | +1, +2, −11, +1 | 0.15 | 2.92 |

Window sensitivity (tops / bottoms flagged, ≥5%):

| Series | post 5 | post 10 | post 21 |
|---|---|---|---|
| Radar risk-off | 0/9 · 1/8 | 1/9 · 1/8 | 3/9 (median +13) · 3/8 (median +14) |
| HY OAS top decile | 3/9 · 4/8 | 3/9 · 4/8 | 7/9 (median +13) · 6/8 (median +1.5) |
| VIX ≥ 20 | 5/9 · 1/8 | 6/9 · 4/8 | 8/9 · 4/8 |

By era (≥5%, post 10; tops · bottoms): Radar risk-off 2020–21 1/2 · 0/2; 2022–23 0/1 · 0/1;
2024+ seen 0/6 · 1/5. HY OAS: 1/2 · 0/2; 0/1 · 1/1; 2/6 · 3/5.

## What this says (in-sample, so an upper bound)

1. **Scored as a confirmation of the top, the loud Radar is late beyond "a few sessions".** It
   flags 1 of 9 tops within 10 sessions (2020, +6); within 21 sessions, 3 of 9 at a median +13. In
   2024+ it flagged none of 6 tops within 10 sessions. Why (gate, bands or shallow declines) is not
   yet diagnosed.
2. **The all-clear is unreliable rather than late.** The loud state switches off near the bottom
   (the economics table's "0 sessions trough → all-clear"), but mostly as flickers that switch back
   on: 15 off-flickers in the window and 1.75 premature all-clears a year. Only 1 of 8 bottoms gets
   a clean (≥10-session) all-clear within 10 sessions.
3. **Credit-spread velocity is the stronger pivot reader at a smaller budget** (11% of days): 3/9
   tops flagged early (−16 to −6) and 4/8 bottoms within 2 sessions, at 0.15 false risk-off calls
   a year. It also has the highest premature all-clear rate (2.9/yr). It is the baseline to beat;
   it enters only through the challenger rule.
4. **No series is good at both turns.** VIX ≥ 20 flags most tops but is on 41% of days with 2.8
   false risk-off calls a year.

## Not settled

- The ±window and the 10-session hold are proposed defaults. They go to the research desk for
  reconciliation with its swing-rule catalogue, so that one label set and one scorecard serve both,
  and they are frozen with the prereg.
- Turns here are SPY episode peaks and troughs only. The desk's multi-asset tops and bottoms will
  enter as `Turn` lists and are not scored here.

## Placebo (added 2026-11-12, research desk falsification proposal)

`pivots.placebo()` draws 300 alert series with the signal's own run lengths (same budget and
persistence), placing each run start (a) anywhere, (b) within 1% of the running high, or (c) within
1% of the lowest close since the running high. Raw: `PIVOT_PLACEBO_INSAMPLE_v2.json`. ≥5% turns,
post 10, in-sample.

| Series | Tops: observed vs placebo (any / near high) | Bottoms: observed vs placebo (any / near low) | False risk-off /yr: observed vs placebo (any / near high) |
|---|---|---|---|
| Radar loud | 0.11 vs 0.39 / 0.61 | 0.13 vs 0.37 / 0.43 | 0.0 vs 1.2 / 2.2 |
| HY OAS top decile | 0.33 vs 0.53 / 0.74 | 0.50 vs 0.50 / 0.58 | 0.15 vs 1.6 / 3.2 |
| VIX ≥ 20 | 0.67 vs 0.75 / 0.89 | 0.50 vs 0.64 / 0.67 | 2.8 vs 3.0 / 5.7 |
| SPY < 200d | 0.11 vs 0.29 / 0.50 | 0.13 vs 0.29 / 0.34 | 0.0 vs 0.8 / 1.6 |

**Every series flags fewer turns than random runs of the same lengths, near-high placebo
included.** Random runs spread their starts across the calendar, so they land in more turn
windows, and they pay for it in false calls. The real signals buy their low false-call rates by
concentrating inside declines. That also explains why they record more premature all-clears than
the placebo: a placebo that is rarely on inside a decline rarely switches off inside one.

Consequence for the shared scorecard: **a flagged share is not readable on its own.** It is read
against the placebo at the same false-call rate. The proposed primary statement is a pair: flagged
share and false calls per year, each beside its near-high (tops) or near-low (bottoms) placebo.
None of the in-sample Radar or baseline series beats its placebo on flagged share; all of them beat
it on false calls.
