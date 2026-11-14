# Risk Radar walk-forward scorecard v1 — out of sample 2022-01-03 → 2023-12-29; 2024-01-02 → 2026-11-10 is seen history

Prereg `PREREG_WALKFORWARD_v1.md` (sha256 01e66c59…ca7e7ca, verified) with addenda 1–3. Scored
run at code commit `e28f5ccde58` (addendum 3 committed before the run; the earlier one-session-lag
compute was discarded unread). Raw: `WALKFORWARD_SCORECARD_OOS_v1.json`, fold log
`WALKFORWARD_FOLDS_v1.json`, series `data/risk_radar/walkforward_state_series.json` and
`data/risk_radar/walkforward_alert_series.csv` (1,219 sessions, loud budget 19.3%).

**Label.** 2022-01-03 → 2023-12-29 is out of sample; 2024+ is the Radar's own seen history, not
the desk's sealed confirmation. The design (legs, transforms, tiers) was chosen knowing 2020+.
Exact 90% Clopper-Pearson intervals; counts beside every figure. Out-of-sample and seen-history
figures are combined only in the table headed as pooled, which is not out of sample.

> **Corrected 2026-11-12 (#11137 review), regenerated through the fixed code.** (1) A fold is marked seen history by its *score* window: F24, F25 and F26 score 2024+ and are seen history (F24 was wrongly written `seen_history: false` because the flag tested the fit end). (2) The HY OAS baseline now uses the availability release rule (observation + one federal-holiday business day), not a one-session shift that admitted a Friday value on a holiday Monday. (3) The insurer peak starts from opening capital 1.0. Every moved cell is listed in the PR comment for the correcting commit.

## 1. Primary endpoint: refitting did not change the Radar — inconclusive (difference 0)

**The decision rests on the out-of-sample folds F22 and F23** (scored 2022 and 2023). F24, F25 and F26 score 2024+, the Radar's own seen history, and are shown for continuity only; they agree.

Every fold retained the shipped default (g = 0.40, Δ = 0). The walk-forward loud state is
therefore identical to shipped v2 on every session. The prereg's practical-difference rule
(≥2 more turns, no more false + premature calls) is not met: the difference is 0.

| Fold | Scored | Matured fit turns | Decision |
|---|---|---:|---|
| F22 | 2022, out of sample | 4 | retained: best candidate J 0.0 = default 0.0 |
| F23 | 2023, out of sample | 5 | retained: best −7.0 vs default −2.5 |
| F24 | 2024, **seen history** | 6 | retained: best −7.0 vs default −2.5 |
| F25 | 2025, **seen history** | 10 | retained: best −5.0 vs default −2.5 |
| F26 | 2026, **seen history** | 14 | retained: best −5.5 vs default −3.0 |

Why (a property of the frozen procedure, reported, not repaired): Δ is set per gate cut to hit a
15% loud share, so Δ = 0 is never itself a candidate. After 2022 the default's fit-window share is
18–29%, so every candidate tightens the bands (Δ = +8/+10), which multiplies premature all-clears
(12–17 in the fit window) and loses on J. Gate cuts 0.30/0.40/0.50 give identical states in F22
and near-identical ones later. "No gate" adds false risk-off calls. Refitting these two quantities
cannot improve the incumbent; the result condemns nothing and promotes nothing.

## 2a. Pivot read, out of sample only: 2022-01-03 → 2023-12-29 (post window 10; ≥5%)

The only out-of-sample line. Outcomes through 2023-12-29. One ≥5% episode (2022-01-03 → 2022-10-12) peaks in the window: its top is left-censored, so no top is scored, and its bottom is the one scored turn. JSON: `pivot_read.oos_2022_2023`.

| Series | Days on | ≥5% tops scored (censored) | ≥5% bottoms | ≥5% false risk-off /yr | ≥5% premature all-clear /yr |
|---|---:|---|---|---:|---:|
| Radar loud (walk-forward = shipped v2) | 38.5% | 0/0 (1 censored) | 0/1 | 0.00 | 2.52 |
| HY OAS 21d top decile (release-rule lag) | 17.0% | 0/0 (1 censored) | 1/1 (+2) | 0.00 | 6.04 |
| HY OAS, budget-matched per fold | 23.2% | 0/0 (1 censored) | 1/1 (+2) | 0.00 | 6.04 |
| SPY < 200d | 43.9% | 0/0 (1 censored) | 0/1 | 0.00 | 2.52 |
| VIX ≥ 20 | 53.9% | 0/0 (1 censored) | 0/1 | 0.00 | 3.02 |
| VIX ≥ 25 | 26.8% | 0/0 (1 censored) | 0/1 | 0.00 | 4.53 |
| Mechanical: within 1% of high | 3.0% | 0/0 (1 censored) | 0/1 | 1.01 | 0.50 |
| Mechanical: ≥5% below peak | 81.6% | 0/0 (1 censored) | 0/1 | 0.00 | 2.01 |

## 2b. Pivot read, POOLED 2022–26 — pools out-of-sample 2022–23 with seen 2024+; not out of sample (post window 10; ≥10%, then ≥7%, then ≥5%)

Turns: 7 ≥5% episodes peak in the window; the 2022-01-03 top is left-censored (its pre-window
lies before 2022) and the 2026-10 episode is open (no bottom). Of the scored turns, only the
2022 bottom is in the out-of-sample years; everything else is 2024+ seen history.

| Series | Days on | ≥10% tops (n=1) | ≥10% bottoms (n=2) | ≥7% tops (n=3) | ≥7% bottoms (n=4) | **≥5% tops (n=6)** | **≥5% bottoms (n=6)** | ≥5% false risk-off /yr | ≥5% premature all-clear /yr |
|---|---:|---|---|---|---|---|---|---:|---:|
| **Radar loud (walk-forward = shipped v2)** | 19.3% | 0 | 0 | 0 | 1 (+2) | **0/6 [0.00, 0.39]** | **1/6 [0.01, 0.58]** (+2) | 0.0 | 1.45 |
| HY OAS 21d top decile (release-rule lag) | 12.6% | 0 | 1 | 0 | 3 | 2/6 [0.06, 0.73] (+5, −5) | 4/6 [0.27, 0.94] | 0.0 | 3.72 |
| HY OAS, budget-matched per fold | 21.0% | 1 | 1 | 1 | 2 | 3/6 [0.15, 0.85] (+3, −11, −6) | 3/6 [0.15, 0.85] | 0.83 | 4.13 |
| SPY < 200d | 22.5% | 0 | 0 | 0 | 1 | 0/6 | 1/6 (+6) | 0.0 | 1.24 |
| VIX ≥ 20 | 32.8% | 1 | 0 | 2 | 2 | 3/6 (+6, −13, −5) | 3/6 | 2.07 | 2.69 |
| VIX ≥ 25 | 14.3% | 0 | 1 | 0 | 3 | 1/6 (−9) | 4/6 | 0.21 | 2.48 |
| Mechanical: within 1% of high | 32.2% | 1 | 0 | 2 | 2 | 5/6 [0.42, 0.99] (−20…−7) | 4/6 | 5.79 | 2.48 |
| Mechanical: ≥5% below peak | 39.3% | 1 | 0 | 1 | 2 | 1/6 (+9) | 4/6 | 0.0 | 1.03 |

Window sensitivity, ≥5% (tops · bottoms): Radar post 5: 0 · 1; post 21: 1 · 2. HY OAS decile
post 21: 5 · 5.

**Beyond the near-high reference (strict, ruling point 4):** no series makes an early top catch
that the "within 1% of high" reference does not also make, at any depth. Same as in-sample.

## 3. Against the placebo (2,000 draws, seed 0, tol 0.01; ≥5%, post 10)

> **Placebo not matched on alert exposure** (placement defect, see PR comment 6835380019). On this table's window (2022-01-03 → 2026-11-10 pooled, out-of-sample 2022–23 plus seen history 2024+; 2,000 draws, seed 0) the pre-repair mean placed mass for the Radar loud series was 221.1 of 235 sessions near highs and 223.4 of 235 near lows. Figures in this table are not verified until the repair.

| Radar loud | Observed | Near-high / near-low placebo median | Placebo p90 | Draws ≥ observed |
|---|---:|---:|---:|---:|
| Tops flagged | 0.00 | 0.67 (near high) | 0.83 | 100% |
| Bottoms flagged | 0.17 | 0.50 (near low) | 0.67 | 98% |
| False risk-off /yr | 0.0 | 2.07 (near high) | — | — |
| Premature all-clear /yr | 1.45 | 0.21 (near high) / 0.62 (near low) | — | — |

**NOT VERIFIED (placebo placement defect, PR comment 6835380019):** both halves are unverified: Against the proposed slate-v2 pass line (flagged share ≥ placebo p90 and false calls ≤ placebo
median), the Radar fails on flagged share for both turn kinds and passes on false calls. A re-score under the repaired placement rule, not part of this PR and not yet reviewed, leaves the direction of this statement unchanged; the regenerated tables are in the follow-up PR.

## 4. What this says

1. **The loud Radar does not identify tops.** Pooled over out-of-sample 2022–23 and seen 2024+ it flags 0 of 6
   ≥5% tops within 10 sessions (1 within 21) and no ≥7% or ≥10% top. Random runs of the same
   lengths placed near highs do better on every draw. (NOT VERIFIED: placebo placement defect, PR comment 6835380019. A re-score under the repaired placement rule, not part of this PR and not yet reviewed, does not support "every draw": a small share of draws ties the Radar rather than beating it; the regenerated tables are in the follow-up PR.) Its loud state behaves as a mid-decline
   confirmation, not a pivot call.
2. **Its virtue is silence outside declines:** zero false risk-off calls. Its fault is the
   all-clear: 1.45 premature all-clears a year (against a placebo median of 0.2–0.6: NOT VERIFIED, placebo placement defect, PR comment 6835380019). A re-score under the repaired placement rule, not part of this PR and not yet reviewed, leaves the direction of this statement unchanged; the regenerated tables are in the follow-up PR.
3. **Credit-spread velocity remains the stronger pivot reader** (pooled: 2/6 tops flagged, one early;
   4/6 bottoms within 3 sessions; 0 false calls) but it re-alarms inside declines (3.7 premature
   all-clears a year).
   None of its early catches is beyond the near-high reference.
4. **Refitting the gate and band offset is not the lever.** The failure is in what the loud state
   is built to mean, not in its two tunable quantities.
5. Sample: 6 scored tops and 6 bottoms, 1 bottom truly out of sample. Every interval is wide.

## Appendix (descriptive only; never a bar or headline)

The insurer profile and sleeve comparators are in the JSON under `appendix_descriptive`, and the
retrospective arithmetic attribution under `secondary_scorecard`. They choose nothing.
