# B12 — Live hazard feature parity verdict + estimator register (SIC-D-B12)

**Date:** 2026-10-20 · **Base:** `a038b3f35aafd3acc8879212a25373d4c94510c2` · **Lane:** `sic-d-B12-20261021-r1`

## Verdict

```
PARITY_FAILS
```

The live Sector Cycles hazard input vector is **not** the vector the admitted W4.2
scorer was trained on. 13 of 19 `_DESIGN` features fail the 0.05-sd / exact-equality
gate, direction disagrees at 44 of 80 month-ends (45% agreement), and turn-detection
basis/epoch parity cannot be established on the live side. This is a finite negative
finding: it is recorded and disclosed, NOT repaired. No current MODEL claim may be
presented from the live vector. Existing historical hazard verdicts (four of six
cells qualified; up/3m and up/6m PRIOR), priors, inert sizing multipliers (1.0) and
the lead-lag STOP are unchanged.

The verdict is wired into the disclosure chain: `engine/hazard_parity.py::LIVE_HAZARD_PARITY`
(frozen from the measurement run below) → `engine/cycle_rhythm.py::estimate_kinds`
now stamps `model_cell_current_claim: "parity_failed"` (was `"parity_not_established"`)
plus `live_feature_parity: {verdict, failing, report}` on every Cycles record.

## Method

Unit: one instrument at one as-of session, `us_sector` family, daily, direction as
each side computes it.

- **Training side** — the row `scripts/build_hazard_panel.py` would produce at the
  as-of, computed by IMPORTING the panel/fit functions (`importlib`; never copying
  formulas — drift breaks the harness, which the monkeypatch test proves).
  `_detect_turns_for_instrument` (ZigZag v2, `confirmed_at` PIT, 14%, `close_price`
  basis) on the full tape; `_build_instrument_rows` at each month-end with
  `_compute_half_medians`/`_family_half_medians`/`_blended_median` (k=6) and an EMPTY
  `regime_hist` (quad/liquidity read None exactly as the live record does);
  `scripts/fit_cycle_hazard.py::build_design` produces the design vector.
- **Live side** — `engine.sector_cycles.build_sector` (the real live builder) on the
  same tape truncated at the as-of, then `_live_hazard_inputs` (the B12 pure
  extraction of `_stamp_hazard`'s input assembly, byte-identical behavior) →
  `engine.hazard_score._build_feature_vector`.
- **Comparison at the scorer-vector level**, per `_DESIGN` feature: MATCH iff
  |train − live| ≤ 0.05 × training sd (frozen from
  `data/hazard/model_price_c4414dcb.json:coefficients[dir].sd`); age dummies and 0/1
  features require exact equality. A feature classed SAME_DEFINITION that numerically
  mismatches would be a harness failure — none did (both family dummies match).

**Input 1 (required evidence):** seeded synthetic daily tape, seed 12, 2015-06-01 →
2024-06-28 (2,370 bdays), two superposed cycles (~1.7y, ~3.3y) + noise so several
≥14% swings confirm on both detectors; TR = price × 1.5%/yr accrual so the
structure(price)-vs-TR basis seam is exercised. Both sides run at **every month-end
after 30-month warm-up: 80 as-ofs, 80 rows on both sides** (no as-of dropped).
Single-instrument panel: the k=6 family-median pool degenerates to the own median
(disclosed limitation — the pooled-family blend is a multi-instrument property).

**Input 2 (real tape): GAP.** No tracked price history for the 11 SPDR ETFs exists
under `data/` at the base (`git ls-tree` shows no `data/yahoo/XL*.parquet`; only
`SPY.parquet` exists and no sector columns), so the five-latest-month-ends real-tape
repetition could not be run. The synthetic verdict is the recorded verdict.

## Per-feature table (measured, 80 month-ends; worst = max |diff| over as-ofs)

| feature | static class | match | worst \|diff\| (sd) | worst \|diff\| (raw) | training source | live source |
|---|---|---|---|---|---|---|
| age_b1..b5 | DIFFERENT_DEFINITION | NO | exact gate | 1.0 (bucket flip) | `build_hazard_panel.py:_build_instrument_rows` — age_m = days/30.44 since `confirmed_at` turn; `_age_bucket` ratio edges .5/.8/1.1/1.5 | `sector_cycles.py:_live_hazard_inputs`→`hazard_score.py:_age_buckets` — bars = Δdecimal-yrs×252; cuts −.19/.45/.99/1.63 |
| log_age_ratio | DIFFERENT_DEFINITION | NO | 0.218 | 0.205 | `_log_age_ratio` — ln(age_m / k=6 blended median, months) | `_live_hazard_inputs` — ln(bars/252×12 ÷ median_half_yrs×12), `proj.period_yrs.median/2`, no blend |
| amp_proxy | DIFFERENT_DEFINITION | NO | 3.31 | 0.944 | `_amp_proxy` — expanding pctile of 63d range/price (TR) | `_live_hazard_inputs` — `amp_leg_pct` = last swing `mag_pct`/100 (open leg, provisional allowed) |
| pos_osc_s | DIFFERENT_DEFINITION | NO | 1.70 | 0.427 | `_detrended_osc` — SMA200 dev, expanding pctile (TR) → /100 | `sector_cycles.py:_detrended_osc` — EMA252 detrend, 252-stochastic (price) → /100 |
| osc_slope_s | DIFFERENT_DEFINITION | NO | 1.61 | 2.69 | `_osc_slope` — panel osc `diff(21)` → /10 | `_record_core` — live osc 22-bar diff → /10 |
| trend_pass | DIFFERENT_DEFINITION | NO | exact gate | 1.0 (state flip) | `_trend_pass` — close>SMA200 min100 (TR) | `_record_core` — `struct[-1]>mean(struct[-200:])` (price basis) |
| mom_score | **PROXY** | NO | 169.7 | 33.76 | `_mom_score` — 126d−21d own TR return (fraction) | `_live_hazard_inputs` — `mom_score = now.rs_63d` (percent) — §6.2 suspected gap, confirmed |
| rs_63d | DIFFERENT_DEFINITION | NO | 379.8 | 33.66 | `_rs_63d` — rel. return vs bench (fraction) | `_leadership` — `rs.pct_change(63)×100` (percent, rounded 0.1) |
| vol_pctile | **IMPUTED_CONSTANT** | NO | 1.93 | 0.579 | `_rolling_vol_pctile` — expanding pctile of 63d realized vol | `_live_hazard_inputs` — `None` → scorer constant 0.42 — §6.2 suspected gap, confirmed |
| quad_Q2/Q3/Q4 | ABSENT_LIVE | yes (0=0) | exact | 0.0 | regime_hist quad asof t | `nw.quad` never set by the live build → 0 |
| liq_expanding | ABSENT_LIVE | yes (0=0) | exact | 0.0 | regime liquidity == 'expanding' | `nw.liq_expanding` never set → 0 |
| fam_country, fam_cn | SAME_DEFINITION | yes | exact | 0.0 | `build_design` family dummies | `hazard_score._FAM_DUMMIES` (sector = reference level) |

The rs_63d/mom_score raw gaps are dominated by the **percent-vs-fraction scale seam**
(live ×100): the same economic quantity expressed in the wrong units for the fitted
coefficients. Even ignoring scale, live rs rounding (0.1) and the proxy substitution
remain. Direction of blame is not assigned here — this is a parity measurement, not
a repair decision.

## Missing-value policy

| field | training (panel/build_design) | live (_live_hazard_inputs / scorer) |
|---|---|---|
| pos | NaN → column median fill | `now.pos or 50.0`; scorer refuses only on None |
| osc_slope | NaN → column median fill | `now.osc_slope or 0.0` |
| amp_leg_pct | NaN → column median fill | None → scorer constant 0.42 |
| mom_score | NaN → column median fill | None → 0.0 (`or 0.0`) |
| rs_63d | NaN → column median fill | None → 0.0 |
| vol_pctile | NaN → column median fill | always None live → constant 0.42 |
| trend_pass | NaN → median fill (fill list) | `above200d or 0.0` |
| age / median_half_yrs | NaN ratio → b_unknown (all dummies 0) + median fill | missing age or median ≤0 → scorer REFUSES to score |
| quad / liquidity | NaN → 0 via `==` | None → 0 |

Policies disagree on every row except the dummies: training median-fills from the
panel distribution; live substitutes constants (0.42/0.0/50.0) or refuses.

## Direction

Training: "up" iff the last `confirmed_at`-PIT turn is a trough. Live: "up" iff
`now.phase or now.phase_v2` ∈ `{Recovery, Expansion, Trough}` (`hazard_score._UP_PHASES`).
Measured agreement over the 80 month-ends: **36 agree / 44 disagree (45%)**. The live
phase classifier is a different object from the turn-state leg direction (and counts
"Trough" as up), so direction parity fails independently of any feature.

## Basis and epoch

- Training: `engine/cycle_ontology.py:detect_turns` (ZigZag **v2**, `confirmed_at`),
  pct 14.0, basis `close_price`; `turn_epoch` = `price_c4414dcb` == the model
  artifact's `turn_def_version` ✔. Features on TR close; turns on price — the D4
  substrate split.
- Live: `engine/sector_cycles.py:_detect_swings` (ZigZag **v1** — no `confirmed_at`,
  no NP-6 seed fix), pct 14.0, on the record's structure basis (`price` on the
  synthetic tape; `tr_fallback` degrades silently to TR in production when the price
  panel lacks the ticker). Features on the structure (price) basis; RS on TR. The
  record carries **no epoch stamp**; the epoch printed on a stamped score block is
  the scorer's own constant, never measured from the live turn set.
- Verdict: basis/epoch parity **cannot be established live** (different detector
  version, no epoch identity) → recorded as failing.

## Premise verification (all held at base)

`_stamp_hazard` assembly (`engine/sector_cycles.py:1047-1124` pre-B12), scorer
`_build_feature_vector`/`_DESIGN`/epoch (`engine/hazard_score.py:44-223`), panel
contract (`scripts/build_hazard_panel.py:177-520, 850-1067`), `build_design`
(`scripts/fit_cycle_hazard.py:95-120`), live osc/turns/proj/leadership
(`engine/sector_cycles.py:163-174, 360-375, 474-500, 718-792`). No contradiction
found; no packet reinterpretation was needed.

## Estimator register

| # | frozen question | baseline | inputs | data maturity | falsifier | finite verdict |
|---|---|---|---|---|---|---|
| E1 | Is the live hazard input vector the same vector the W4.2 scorer was trained on (feature, missing-value policy, direction, basis, epoch)? | W4.2 admitted fit `model_price_c4414dcb` (four of six cells qualified; up/3m, up/6m PRIOR) | seeded synthetic daily tape (seed 12, 2015-06→2024-06), both sides at 80 month-ends; real-tape repetition GAP (no tracked XL* history) | synthetic-only; single-instrument family pool | any feature >0.05 sd (exact for dummies), any direction disagreement, any basis/epoch mismatch | **PARITY_FAILS** — 13 features + direction + basis_epoch fail (this packet, measured 2026-10-20) |
| E2 | Does a live feature repair that builds the panel-contract features live (`vol_pctile`, `mom_score`, `rs_63d` scale, osc/pos definitions, age pipeline, quad/liq stamping) match the training vector within 0.05 sd and keep out-of-sample Brier no worse than the KM prior? | same W4.2 fit + KM baselines | repaired live vector vs panel rows on synthetic + real tapes | DEFERRED — not run | repaired vector >0.05 sd on any feature, or OOS Brier worse than KM on any qualified cell | **DEFERRED (not run)** — it would change `now.hazard`, so it needs the science owner and an independent reviewer; not a Cycles-lane decision |
| E3 | B07 grader v2 conditional directional hit rate with date-clustered SE | ~0.274 conditional hit rate (grader v2) | existing call log | descriptive measurement of the existing call log — **not an estimator, no predictive claim** | n/a (descriptive) | recorded by B07; retained and cited, not re-run here |
| E4 | B05 measured phase age | — | forward-log replay | descriptive, not an estimator | n/a | B05 measured; retained and cited, not re-run |
| E5 | B06 rhythm windows | — | record's own confirmed turns | descriptive, not an estimator | n/a | B06 measured; retained and cited, not re-run |

Retained and cited, not re-run: W4.2 four of six cells qualified (up/3m and up/6m
PRIOR), inert sizing multipliers 1.0, lead-lag STOP.

## Receiver follow-on (templates — NOT edited by this packet)

`templates/sector_cycles.js` does not yet read `estimate_kinds`. When it does, it
must read `estimate_kinds.model_cell_current_claim` BEFORE any current-MODEL wording:
the value is now `"parity_failed"`, so a MODEL cell may only be phrased as a
historically qualified estimate whose live feature parity has failed — never as a
current calibrated probability. `estimate_kinds.live_feature_parity` carries
{verdict, failing, report} for that disclosure.
