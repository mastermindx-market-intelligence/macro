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
plus a `live_feature_parity` disclosure on qualified records (B12r2: a
{verdict, failing, report_ref} pointer — see Receiver follow-on).

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
| pos | missing → column median fill | `now.pos or 50.0`; scorer refuses only on None |
| osc_slope | missing → column median fill | `now.osc_slope or 0.0` |
| amp_leg_pct | missing → column median fill | None → scorer constant 0.42 |
| mom_score | missing → column median fill | None → 0.0 (`or 0.0`) |
| rs_63d | missing → column median fill | None → 0.0 |
| vol_pctile | missing → column median fill | always None live → constant 0.42 |
| trend_pass | missing → median fill (fill list) | `above200d or 0.0` |
| age / median_half_yrs | missing ratio → b_unknown (all dummies 0) + median fill | missing age or median ≤0 → scorer REFUSES to score |
| quad / liquidity | missing → 0 via `==` | None → 0 |

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
{verdict, failing, report_ref} — qualified records only — for that disclosure.

Payload size (B12r2 / RB12 repair, measured on the synthetic qualified record of
the disclosure test set): the per-record payload is **268 bytes**
(`len(json.dumps(...))`, default separators; 249 compact) — it was **10,824 bytes**
(10,353 compact, ≈10.1 KiB) when the full report rode every record, i.e. ~798 KiB
across the 79 Cycles records of the boot-critical `site/sector_cycles_data.js`.
The report itself is published **exactly once per payload, in
`meta.live_hazard_parity`** (10,883 bytes by the same measure): verdict, failing,
provenance keys and the full report, read from the recorded `LIVE_HAZARD_PARITY`
inside a try (`None` on any failure); no record's `estimate_kinds` carries a
`report` key, and unqualified records carry `live_feature_parity: null`.


---

## Lane 8 disposition register (P18 / B12) — 2026-11-09

**Lane:** Sector Intelligence build-out, lane 8 (analytics and history), program Macro #7646.
**Code:** branch `claude/ssd-t3-bc9ff67e-78688517a78d520a`. Numbers below were computed at commit
`121421c85e23455c8bdaa20eccd2b02f2fa306b1` on top of `origin/main` `ba77e7d4ca45887bdd89145911dd6f27232619fe`.
**Data actually read** (all tracked on `main`): `data/hazard/model_price_c4414dcb.json`,
`data/hazard/km_baseline_price_c4414dcb.json`, `data/hazard/panel_price_c4414dcb.parquet`,
`data/yahoo/{SPY,XLK,XLE,XLF,XLV,XLY,XLP,XLI,XLB,XLU,XLRE,XLC}.parquet`,
`data/sector_central/calls.parquet`, `data/regime/ladder_risk_calibration.json`. On a sparse tree
materialize them first (`git sparse-checkout add data/hazard`; the other files can be read with
`git show origin/main:<path> > <file>`). Nothing here is synthetic except where a row says so.

**Standing result.** `LIVE_HAZARD_PARITY = PARITY_FAILS` is unchanged. It is now confirmed on
real tapes, not only on the seeded synthetic tape. The historical 4/6 qualified-cell verdict
(W4.2) is retained. It is a statement about the fitted artifact on its own panel. It does
**not** certify the current runtime: the live turn set, features, direction and cohort are not
the ones the artifact was qualified on.

### Disposition vocabulary

`QUALIFIED` — passed its frozen protocol, and the qualification applies to the object named in the
question · `PRIOR` — only the baseline may be shown · `NO-GO` — the question was answered negatively
or a required qualifier fails · `UNDERPOWERED` — the data cannot answer it at the frozen bar ·
`ACCRUING` — not enough matured observations yet. Negative results stay in this document. None of
them, and none of the positive ones, authorize a trade, a size, a gate or a rank:
`may_rank / may_gate / may_size / may_trade / may_escalate` stay false everywhere.

### Register

| # | Admitted finite question | Frozen protocol it was judged under | n (honest) | Effect | Uncertainty | Multiplicity | Disposition | What would change it | Reproduce |
|---|---|---|---|---|---|---|---|---|---|
| Q1 | Is the live Sector Cycles hazard input vector the training vector of the W4.2 scorer (seeded synthetic tape)? | B12 parity harness: per-feature match iff \|diff\| ≤ 0.05 training-sd (exact for 0/1 and age dummies); direction, basis and epoch must agree (§ Method above) | 80 month-ends, 1 synthetic instrument | 15 failing items: 13 features + direction + basis_epoch; direction agreement 36/80 = 0.45 | deterministic; no sampling error | none needed (any single failure fails) | **NO-GO** (`PARITY_FAILS`), re-run at this commit: identical | a live feature/turn repair that passes this harness (E2), with a fresh owner-qualified verdict | `python3 -m engine.hazard_parity` |
| Q1r | Same question on the real SPDR tapes (the input kind 2 the base packet could not run) | same harness via `hazard_parity.real_tape_report` (price = close_price, TR = close, benchmark SPY, no fill on missing benchmark sessions) | 11 ETFs; 2,919 month-end as-ofs with both sides (9 × 305, XLRE 103, XLC 71) | 0/11 tapes hold. 14 items fail on **every** tape (age_b1–b5, log_age_ratio, amp_proxy, pos_osc_s, osc_slope_s, mom_score, rs_63d, vol_pctile, direction, basis_epoch); trend_pass fails on 10/11 (XLC passes). Direction agreement 1,619/2,919 = 0.555 (per tape 0.49–0.58) | deterministic; per-tape spread shown | none needed | **NO-GO** (`PARITY_FAILS` confirmed on real data) | same as Q1 | `python3 -m engine.hazard_parity --real XLK,XLE,XLF,XLV,XLY,XLP,XLI,XLB,XLU,XLRE,XLC --tape-dir <dir with data/yahoo parquet> --measured-on <sha> --out out.json`; stored result `b12/real_tape_parity_2026-11-09.json` (sha256 `28ef04605d13f55c9ba8acdeb5a538837818078d2b38f674c6dda591504ff8d7`) |
| Q2 | W4.2 cell up/1m: does the hazard model beat the age-bucket KM baseline out of sample? | W4.2 fit gate (`scripts/fit_cycle_hazard.py`): walk-forward from 2010, 6-month embargo, Brier skill vs KM, 90% month-block bootstrap (800 draws, seed 7), BH-FDR q = 0.10 over the 6 cells | 9,246 OOS rows over 198 months (overlapping monthly rows; month is the resampling unit) | Brier 0.22542 vs KM 0.23942; skill +0.0140 | CI90 [+0.0068, +0.0209]; p = 0.0012; skill-positive in 14/17 years | BH-FDR q 0.10 across 6 cells: survives | **QUALIFIED (historical, on its panel)** | a re-fit on a new panel/epoch; nothing in the current runtime | `python -m scripts.fit_cycle_hazard` (see W42_HAZARD_VERDICT.md) |
| Q3 | W4.2 cell up/3m | same | 9,246 / 198 months | 0.24922 vs 0.25629; +0.00707 | CI90 [−0.00026, +0.0143]; p = 0.061; 11/17 years | survives BH but CI includes 0 | **PRIOR** | same | same |
| Q4 | W4.2 cell up/6m | same | 9,246 / 198 months | 0.24307 vs 0.24326; +0.0002 | CI90 [−0.0057, +0.0062]; p = 0.52; 10/17 years | does not survive | **PRIOR** | same | same |
| Q5 | W4.2 cell down/1m | same | 3,744 / 197 months | 0.23082 vs 0.24494; +0.01413 | CI90 [+0.0034, +0.0247]; p = 0.018; 11/17 years | survives | **QUALIFIED (historical)** | same | same |
| Q6 | W4.2 cell down/3m | same | 3,744 / 197 months | 0.17650 vs 0.18427; +0.00777 | CI90 [+0.0005, +0.0155]; p = 0.036; 13/17 years | survives | **QUALIFIED (historical)** | same | same |
| Q7 | W4.2 cell down/6m | same | 3,744 / 197 months | 0.10466 vs 0.10885; +0.00419 | CI90 [+0.0005, +0.0079]; p = 0.024; 12/17 years | survives | **QUALIFIED (historical)** | same | same |
| Q8 | May any Sector Cycles record show a **current** MODEL turn probability today? | Round 3 §6.4 + this lane's frozen gate `hazard_score.qualify_current_model`: parity, epoch, cohort, direction, basis, horizon (every horizon of the direction PASS) and whole-curve validity must all hold | every sector / basket / amalgam record of every build | parity fails (Q1, Q1r); the live turn set has no epoch identity (`turn_knowledge.epoch = null`, ZigZag v1); up legs can never pass the horizon qualifier (up/3m, up/6m are PRIOR cells, Q3–Q4). Real-tape smoke at the 2026-11-06 session: XLK and XLU are scored `up` while the last confirmed turn is a peak (direction fails); XLK, XLE and XLU scored curves were already inverted (`non_monotone_cdf`) | n/a | n/a | **NO-GO**. The payload now carries no 1m/3m/6m cell for an unqualified block: `unavailable_reason: "current_model_unqualified"`, `current_model.failing` and `withheld_horizons`; the PRIOR is disclosed as withheld (Q9) | every qualifier holding at once: a parity-passing live vector, an epoch-stamped turn set, a trained cohort, matching direction and basis, and a direction whose three cells are all qualified | `python3 -m pytest tests/test_sector_analytics_boundaries.py -k "qualifier or curve or live_sector"` |
| Q9 | Does the shipped KM PRIOR (`km_by_month`, 1 − S(h), the value `_km_prior` returns for PRIOR cells) describe any population a reader could be told — legs from their start, or turns from today? | Recompute `km_by_month` from its builder (`scripts/build_hazard_panel.py`, the integer-month KM block: `at_risk_m = int((grp["age_m"] >= m - 1).sum())`) and compare with leg-level durations and the panel labels | us_sector panel: up 2,554 rows / **200 legs**; down 531 rows / **179 legs** (legs = distinct `(id, leg_open_date)`); 11 ETFs; 323 month-ends 1999-08 → 2026-06 | The at-risk set counts panel **rows** aged ≥ m − 1, not legs alive: at m = 1 the at-risk is 2,554 = every up row. So 1 − S(h) = 0.0125 / 0.0474 / 0.0894 (up) and 0.0188 / 0.2146 / 0.485 (down) is a row-weighted quantity. For comparison, rough leg-level shares ending within 1/3/6 months of leg start are about 0.13 / 0.38 / 0.49 (up) and 0.07 / 0.49 / 0.78 (down). These are reviewer recomputations, not left-truncation- or censoring-corrected. The panel from-now label means are 0.241 / 0.333 / 0.441 (up) and 0.708 / 0.881 / 0.959 (down), but see Q15 for what those labels count | the defect is definitional (estimator construction), not sampling noise; the leg-level figures are approximate | n/a | **NO-GO** as a displayed probability of any kind. The 1m/3m/6m PRIOR numbers are withheld from the payload (`prior.status: "withheld"`, `reason: "km_by_month_at_risk_counts_panel_rows_not_legs"`). The PRIOR cells the incumbent shipped for up/3m and up/6m carried this number too. *Correction:* an earlier draft of this row called it a valid leg-origin share and emitted it as `leg_origin_prior`. The independent review (below) refuted that, and the field is gone. | a leg-level KM with left truncation and censoring, admitted by the science owner as the baseline (an estimator change outside this lane) | `python3 - <<'EOF'` with pandas: load `data/hazard/km_baseline_price_c4414dcb.json`; assert `families.us_sector.up.km_by_month[0].at_risk == families.us_sector.up.n_rows`. Load `data/hazard/panel_price_c4414dcb.parquet`; for us_sector count legs with `groupby(["direction", "id", "leg_open_date"]).size()` |
| Q10 | May a thematic-basket or amalgam record use the W4.2 model or its PRIOR as its own? | cohort qualifier: the panel `family` column holds only `us_sector`, `country`, `cn_sector` | panel: 3,085 us_sector, 8,982 country, 6,552 cn_sector rows; 0 basket rows | baskets are scored with the us_sector dummy (`_FAM_DUMMIES`) and the us_sector KM | n/a | n/a | **NO-GO** for MODEL. The PRIOR is shown with `population_matches_record: false` | a basket-family panel and fit | `test_basket_prior_disclosure_does_not_match_the_record` |
| Q11 | Does the cycle-ladder state earn a risk size multiplier ≠ 1.0 (W4.6)? | W4.6: vol-residualized p10 drawdown gap vs family base, month-block bootstrap 95% CI, BH-FDR q 0.10, embargo from 2024-01-01 | 48 (state × family × horizon) cells over 8,344 PIT stamps, counted in months | 0 of 48 cells survive | per-cell CIs in the artifact | BH-FDR q 0.10 | **NO-GO** — every multiplier stays 1.0 (inert sizing) | a fresh preregistered risk-channel study | `python -m scripts.fit_ladder_risk_calibration --print`; artifact `data/regime/ladder_risk_calibration.json` `verdict` |
| Q12 | Do cross-instrument cycle position changes lead each other usefully (W5.1)? | W5.1 two-stage protocol: in-sample screen ≤ 2017, out-of-sample Brier test | 136 in-sample FDR survivors; top 20 pairs tested OOS over 9 year-blocks | OOS relative Brier improvement 0.029% | CI90 spans 0; 3/9 blocks positive | BH-FDR q 0.10 in stage A | **NO-GO (STOP)** — the lead-lag scope stays stopped; not re-run | a new preregistration on untouched data | `research/cycle_masterplan/W51_LEADLAG_VERDICT.md` |
| Q13 | Does cycle position (decile) carry a forward-return edge? | W0.4 keystone: within-family position deciles, gap-vs-base CIs at 21/63/126d | 128–220 months per cell | every decile's gap CI straddles 0 | see keystone table | keystone family | **NO-GO** | a new preregistered construction | `research/cycle_masterplan/W04_KEYSTONE_VERDICT.md` §2.1 |
| Q14 | Do Sector Central conviction directions show directional skill (grader v2 conditional hit rate)? | B07 grader v2 definition: next-bar fill, H ∈ {21, 63, 126} sessions, conditional rate = correct up/down calls ÷ directional calls, date-clustered SE. Reproduced here for the **sector** subset only (basket levels not read) | call log 2026-06-28 → 2026-10-16. Sector subset: 21d — 429 directional calls on 69 call dates; 63d — 220 calls on 31 dates; 126d — 0 matured. The windows overlap heavily: about 4 non-overlapping 21-session windows and 1–2 non-overlapping 63-session windows span the matured calls | 21d 0.448; 63d 0.455 (mostly `down` calls: 360/429 and 157/220) | date-clustered SE 0.029 (21d) and 0.022 (63d). The SE ignores overlap across dates, so it is optimistic | none (descriptive) | **UNDERPOWERED** (21d, 63d) · **ACCRUING** (126d). No skill claim either way; the figure is not a win rate | ≥ 12 non-overlapping matured windows per horizon, read under the frozen definition by the nightly grader | `python3 research/sector_completion_20261021/b12/grader_sector_subset.py data/sector_central/calls.parquet data/yahoo` |
| Q15 | What do the W4.2 targets `y1/y3/y6` (and so any qualified MODEL cell) actually measure? | Read the label code (`scripts/build_hazard_panel.py`: the event is the first closing extremum after `last_turn_date`; `y_h = event_date <= t_end + h months`; no requirement that `event_date > t_end`) and measure it on the panel | us_sector rows: up 2,554 (616 y1 events); down 531 (376 y1 events) | Up: 459 rows (74.5% of y1 events) have a closing extremum already dated on or before the as-of. Down: 261 rows (69.4%). Turns strictly after the as-of and within h: up 0.062 / 0.154 / 0.261, down 0.217 / 0.390 / 0.467 as shares of all rows (0.075 / 0.187 / 0.318 and 0.426 / 0.767 / 0.919 among rows whose extremum is not already past) | deterministic count | n/a | **Disposition on meaning, not on skill.** The historical QUALIFIED cells (Q2, Q5–Q7) are qualified for the target "the open leg's closing extremum is dated within h months of the as-of, including one already past but not yet confirmed". They do not qualify "a new turn within h months". The builder's comment that an extremum before `t_end` "is impossible" is wrong for confirmation-lagged turns. The gate now publishes the target with every block (`current_model.target`), and any future UI wording must use it | a relabelled panel (strictly forward events, or confirmation-dated events) and a re-fit: science owner | `python3 - <<'EOF'` with pandas: `p = pd.read_parquet("data/hazard/panel_price_c4414dcb.parquet")`; for `family == "us_sector"` and each `direction`, count `(p.event_date <= p.date)` and compare with `y1.sum()` |

**Not admitted (no disposition claimed):** E2 — rebuilding the live features to the panel
contract. It would change `now.hazard`, so it needs the science owner, an independent reviewer
and its own frozen protocol. Descriptive readings are not scientific questions and get no
disposition: phase age (B05), rhythm windows (B06), turn confirmation lags (`turn_knowledge`
below) and the grader's descriptive fields.

### What the emitted payload now says (Q8 and Q9 wired)

`engine/sector_cycles._stamp_hazard` passes every scored block through
`engine/hazard_score.qualify_current_model`. With today's facts every Sector Cycles block is:

```
now.hazard = {
  "epoch": "price_c4414dcb", "revision_optimistic": true,
  "unavailable": true, "unavailable_reason": "current_model_unqualified",
  "direction": <from the last CONFIRMED turn; omitted when there is none>,
  "turn_kind": "peak"|"trough",
  "current_model": {"schema": "sector_cycles.current_model_qualification.v1",
                    "qualified": false,
                    "qualifiers": {"parity": false, "epoch": false, "cohort": ..., "direction": ...,
                                   "basis": ..., "horizon": ..., "whole_curve": ...},
                    "failing": [...], "withheld_horizons": [...],
                    "target": "closing extremum of the open leg dated within h months of the as-of, ..."},
  "prior": {"status": "withheld", "reason": "km_by_month_at_risk_counts_panel_rows_not_legs",
            "source": "data/hazard/km_baseline_price_c4414dcb.json#km_by_month",
            "family": ..., "population_matches_record": ..., "direction": ...},
  "scored_direction": <present when the scorer's phase-based direction differs or no turn is confirmed>
}
```

`estimate_kinds` labels every horizon `missing_estimate` and keeps
`model_cell_current_claim` (`"parity_failed"` when parity is among the failing qualifiers,
otherwise `"qualifier_failed"` — never `"parity_holds"` next to a withheld curve),
`model_withheld_horizons` and the `live_feature_parity` pointer, so the withholding is
never silent. Other engines that call
`hazard_score.score` directly — country and China cycles, and `engine/commodity_cycle_state.py`
(family `flagship`) — are **unchanged**. Their parity was never measured and their PRIOR cells
carry the same row-weighted KM value, so Q8/Q9 are open for them (owner: those engines; not
this lane).

**Single-qualifier falsifiers** (each passes on its own with every other qualifier held true):
`test_single_failed_block_qualifier_downgrades_model_to_prior[parity|epoch|cohort|direction|basis]`,
`test_single_failed_horizon_downgrades_model_to_prior`, `test_partial_curve_downgrades_model_to_prior`,
`test_inverted_model_curve_is_withheld_whole_not_sorted`,
`test_a_prior_cell_inside_a_passing_ledger_fails_the_horizon_qualifier`; positive control
`test_all_qualifiers_hold_keeps_model`; `test_withheld_block_is_independent_of_the_model_value`,
`test_km_prior_is_row_weighted_and_therefore_withheld`,
`test_withheld_for_another_qualifier_never_claims_parity_holds`;
`test_live_sector_build_emits_no_current_model_cell` (all in `tests/test_sector_analytics_boundaries.py`).

### Receiver follow-on (templates — not edited by this lane)

`templates/sector_cycles.js` already renders `hz.unavailable` as "Unavailable today". Its generic
reason text ("a required input didn't settle cleanly") does not fit `current_model_unqualified`;
the Cycles UI lane should add a reason-specific EN/ZH line. No PRIOR number is available to show.
The "Turn hazard (calibrated)" label and its "P(next confirmed turn within horizon)" tooltip
describe neither quantity correctly (Q9, Q15). They must not return for these blocks.

### Independent review (2026-11-09)

A read-only native reviewer (Opus, separate context, no write tools) attacked this register
and the gate before release.
- **Claim A (the original Q9):** REFUTED. The KM at-risk counts rows, and the panel labels include past extrema. Both were verified by the lane on the data: `build_hazard_panel.py` `at_risk_m`; 459/2,554 and 261/531 already-past rows; 200/179 legs. Q9 was corrected and Q15 added.
- **Claim B (the gate):** UPHELD-WITH-NOTES. Its minor notes are fixed:
  - the claim no longer reads `parity_holds` beside a curve withheld for another reason
  - direction comes only from the last confirmed turn
  - the qualified path requires MODEL/PASS cells
- **Remaining reviewer gaps:** a proper leg-level KM was not computed; country, cn_sector and commodity were not recomputed.

### v1.1 per-head qualification (2026-11-10)

The four remaining-opportunity heads are now judged one at a time, each under its own
predeclared protocol: `B12_V11_HEADS_PROTOCOL.md`, committed at `9a7fbf9e2563` before any
result existed. Results and the review adjudication are in `B12_V11_HEADS_RESULTS.md`.

| head | disposition |
|---|---|
| remaining-return distribution | WITHHELD_FAILED |
| adverse tail | QUALIFIED_RESEARCH, fragile |
| target before invalidation | QUALIFIED_RESEARCH, mostly leg direction |
| transition time | QUALIFIED_RESEARCH, mostly leg direction |

Every head is still emitted as `withheld` on every record, each with its own reason code
(`engine/sector_heads.py`). Nothing above changes `LIVE_HAZARD_PARITY = PARITY_FAILS` or the
Q1–Q15 register. The historical 4/6 verdict is still no input to the current runtime.
