# Preregistration — Exact China Risk Radar Revalidation

**Operation:** `cn-risk-p1-radar-revalidation-20260923-solpro-001`  
**Frozen before outcome inspection:** yes  
**Calendar date:** 2026-09-23 America/New_York  
**Repository:** `mastermindx-market-intelligence/macro`  
**Frozen base:** `8db6896dab2199a4b7fc61a005c225380cac7cd6`  
**Protected Skillpack:** `a7d2b3049e5cdc523e91e61a6e9d70a1cb911157`

## 1. Purpose and non-goals

This study tests the exact current production China external-driver Risk Radar. It does not tune, replace, or ship the model. It adjudicates the current claims against reconstructed historical evidence and the genuinely issued forward ledger, keeping those evidence classes separate.

This PR must not change production behavior, bands, probability surfaces, gross factors, `can_force`, UI/templates, Market State policy, audit semantics, forward-log historical rows, or downstream consumers. A better construction, if discovered, requires a separately timestamped preregistration and remains a challenger only.

## 2. Frozen production construction

The canonical construction is `engine/risk_radar_intl.py::CN_PROFILE` and `composite_series` at the frozen base.

### Source fingerprints

| Path | Git blob | SHA-256 |
|---|---|---|
| `engine/risk_radar_intl.py` | `4ed9bdebf6e76cbf529115203ae5d8820ba07f13` | `1596e1da4794bf97d49f6f0ae42eaabff7226fa812fb0a96bfb0a6242faf7cd7` |
| `engine/indicators.py` | `b944d777ba284276cb11060efd1b20b743b26e08` | `edb47847dba4e3ae011341e17c9c914b58639b0ae42a09969800044b4cd4a5b5` |
| `scripts/calibrate_risk_radar_intl.py` | `685476e94fdfa390dc13efe2e5c88cb76cf2f965` | `ec613aa8b38f317ebd4ed8a4ab9dca153db9c632898c40a5edae663e69c26458` |
| `lib/store.py` | `70aa80ccf92527e19f77c15407510dba472af532` | `77051ae1e522e415e2b8c3be51f51187f2571d53a049472a52ca54e9ee1a3c4b` |

A run is invalid if these frozen production fingerprints drift, if a committed or local `data/risk_radar_intl/cn_calibration.json` silently overlays the baked surface, or if the production signal is reimplemented differently for the primary test.

### Exact signal

- Benchmark/calendar and context source: `china/000001.SS` (Shanghai Composite).
- External rate sub-legs: 21-session changes in US 2-year yield, US 10-year real yield, and US 10-year nominal yield, each transformed by a causal trailing-504-session percentile.
- FX sub-leg: 21-session USD/CNH change; DXY 63-session change fills the pre-CNH era; causal trailing-504-session percentile.
- Yield-gap sub-leg: 21-session change in US 10-year minus China government 10-year; causal trailing-504-session percentile.
- Breadth sub-leg: negative China percent-above-200DMA; causal trailing-504-session percentile.
- Component weights: rates `1.0`, USD `0.6`, differential `0.8`, breadth `1.0`.
- Composite: weighted mean of available component means followed by another causal trailing-504-session percentile.
- Bands on the composite percentile ×100: watch `58`, caution `72`, elevated `83`, risk-off `91`.
- Context gate: loud states are available only when Shanghai Composite is below its causal 200-session moving average; otherwise elevated/risk-off is capped to caution.
- Baked displayed probabilities for `>=5%` drawdown:
  - h5: `0.06, 0.08, 0.09, 0.12, 0.15`
  - h10: `0.13, 0.16, 0.18, 0.21, 0.32`
  - h21: `0.27, 0.32, 0.35, 0.40, 0.50`
  - state order: calm, watch, caution, elevated, risk-off
- Baked base rates: h5 `0.072`, h10 `0.160`, h21 `0.305`.

The production calibration script is not presumed to have generated this baked CN ladder. Provenance is an explicit research question.

## 3. Benchmarks and provenance rules

### Canonical benchmark

Shanghai Composite is the primary benchmark because it is the production benchmark and carries the deepest exact input history for the current construction.

### Replication benchmark

CSI300 is tested only if an exact A-share-native CSI300 close series is lawfully available in the repository or approved local data store. Its path, symbol, provider, hash, columns, row count, and date range must be disclosed. The canonical production signal remains the Shanghai-built signal; CSI300 is an outcome-only replication aligned to those signal dates. FXI or another offshore proxy is not an acceptable substitute.

If exact CSI300 data is unavailable or too shallow for the frozen warm-up and outcome windows, the replication verdict is `INSUFFICIENT_EVIDENCE`, not a proxy result.

### Point-in-time qualification

All transforms must be causal: at date `t`, no observation after `t` may enter a signal or baseline. Data-source vintage status is separately disclosed. Latest-vintage historical snapshots without vintage identifiers are classified as `causal_transform_on_snapshot`, not fully vintage-PIT evidence. That limitation cannot be repaired by a causal rolling transform alone.

## 4. Outcomes and horizons

### Primary current-UI target

`Y_5_21(t) = 1` when the minimum benchmark close over the next 21 benchmark sessions, excluding date `t`, is at least 5% below the close at `t`:

`min(close[t+1:t+21]) / close[t] - 1 <= -0.05`.

### Historical claim target

`Y_10_42(t) = 1` when the minimum benchmark close over the next 42 benchmark sessions, excluding date `t`, is at least 10% below the close at `t`:

`min(close[t+1:t+42]) / close[t] - 1 <= -0.10`.

### Secondary diagnostics

Because the production surface displays h5 and h10, report `>=5%` within 5 and 10 sessions as preregistered secondary diagnostics. They cannot promote a claim that fails both primary targets.

Rows without the complete future horizon are immature and excluded, never coded as non-events.

## 5. Eligible sample

- Begin only when the exact production composite and state are available after their causal warm-up.
- Require a nonmissing benchmark close and complete outcome horizon.
- Do not backfill a state across missing signal dates.
- Use each benchmark’s actual trading-session calendar.
- Report exact first/last eligible dates and all missing-leg coverage transitions.
- The daily-row count is descriptive and is never presented as independent N.

## 6. Frozen stability slices

### Chronological split-half

Split eligible signal dates at their chronological median. No threshold or model refit occurs. Report both halves separately.

### Modern-coupling era

Modern era begins `2016-01-01`. Report pre-2016 and 2016+ separately where both are powered.

### Leave-one-crisis-out windows

The following windows are frozen before outcome inspection:

1. Asian/Russia/LTCM spillover: `1997-07-01` through `1999-02-28`.
2. Global financial crisis: `2007-10-01` through `2009-06-30`.
3. China equity/devaluation crisis: `2015-06-01` through `2016-03-31`.
4. US–China trade-war drawdown: `2018-01-01` through `2019-01-31`.
5. COVID shock: `2020-01-01` through `2020-06-30`.
6. China property/regulatory/zero-COVID drawdown: `2021-02-01` through `2022-11-30`.

For each leave-one-crisis-out run, remove every signal date whose full forward-outcome window intersects the omitted calendar window. This embargo prevents a retained pre-crisis signal from retaining an omitted crisis outcome.

## 7. Dependence-aware uncertainty

### Moving-block bootstrap

- Circular moving blocks over eligible chronological rows.
- Block length: 42 sessions for every target so one procedure protects the longest overlap dependence.
- Default replications: 5,000.
- Seed: 20260923.
- Percentile 95% confidence intervals.
- Degenerate resamples are counted and disclosed; they are not silently replaced until a favorable interval appears.

### Episode bootstrap

State-conditioned dates are grouped into episodes: consecutive qualifying dates belong to the same episode until more than 42 benchmark sessions separate them. Resample whole episodes for state probabilities and state differences. Report episode count, hit episodes, and non-hit episodes.

### Block permutation

For lift significance, circularly shift the outcome sequence relative to the frozen signal by a random offset of at least 42 sessions, preserving each series’ serial structure. Default replications: 5,000; one-sided p-value `(1 + null >= observed) / (R + 1)`. This is confirmatory only for the two primary targets.

## 8. Effective-N ceilings

Report, per target and conditioned state:

- daily eligible rows;
- non-overlapping-window ceiling `floor(rows / horizon)`;
- distinct signal episodes;
- distinct outcome episodes;
- hit and non-hit signal episodes.

The effective-N ceiling for a state probability is the smaller of its signal-episode count and non-overlapping-window ceiling. Exact probability adjudication requires at least 20 effective signal episodes and at least 5 hit and 5 non-hit episodes. A directional discrimination claim requires at least 8 signal episodes; `KEEP` requires at least 20.

## 9. Discrimination metrics

For both primary targets:

- unconditional event rate;
- state event rates;
- risk-off lift and elevated-plus lift versus unconditional;
- average precision and AP/base-rate ratio using the continuous production composite;
- ROC AUC as a secondary rank metric;
- moving-block confidence intervals;
- block-permutation p-value for the two primary lift claims.

A daily-row p-value never overrides episode insufficiency.

## 10. Calibration metrics

For the displayed `>=5%` h5/h10/h21 ladder:

- Brier score;
- Brier skill versus the baked unconditional base probability;
- Brier comparison versus a delayed causal expanding-base forecast;
- per-state forecast, observed rate, rows, effective episodes, block CI, and episode CI;
- reliability curve using the five fixed production state bins where powered;
- calibration intercept and slope only when at least three state bins have eight episodes each and there are at least 20 hit and 20 non-hit effective episodes;
- adjacent state-bin inversion.

A material inversion is a later state at least 5 percentage points below the prior populated state with a dependence-aware 95% interval for the difference entirely below zero.

## 11. Frozen baselines

No baseline may tune a threshold after outcomes are inspected.

1. **Baked unconditional:** constant production base probability for Brier comparison.
2. **Delayed expanding unconditional:** at date `t`, use only outcomes that had fully matured before `t`; start after 252 matured observations and shrink with a Jeffreys prior `(hits + 0.5)/(n + 1)`.
3. **Breadth-only:** exact production China breadth percentile as a continuous score; fixed production elevated/risk-off thresholds `0.83/0.91`; apply no fitted threshold.
4. **Rates-only:** mean of available exact production US rate-shock sub-leg percentiles, followed by the same causal trailing-504-session percentile; fixed `0.83/0.91` thresholds.
5. **Trend/context:** binary Shanghai-below-200DMA context score, computed causally.
6. **Ungated composite:** exact production composite and bands without the context cap. This is a counterfactual value-add baseline, not a candidate model.

Compare AP, AUC, fixed-threshold lift, Brier where a probability forecast is defined, and effective episodes.

## 12. Claim promotion and falsification thresholds

### Evidence levels

- **Robust discrimination:** point lift >1; 95% moving-block lower bound >1; both split halves >1; 2016+ >1; every powered LOCO run >1; permutation p <=0.05; at least 20 effective signal episodes.
- **Directional discrimination:** point lift >1 and a majority of split/era/LOCO slices remain >1, but the 95% lower bound includes 1 or effective N is 8–19.
- **Failure:** point lift <=1 with adequate episodes, or the 95% upper bound <=1, or instability reverses the claim across a majority of powered slices.
- **Insufficient:** fewer than 8 effective signal episodes or required benchmark/source provenance is unavailable.

### Exact probability

A displayed probability can be `KEEP` only when effective-N requirements are met, absolute calibration error is <=10 percentage points, the displayed probability lies inside both the block and episode 95% intervals, Brier skill is nonnegative versus the baked base, and no material inversion exists.

With adequate evidence, an absolute error >10 points, exclusion from either dependence-aware interval, negative Brier skill, or a material inversion makes it a `RECALIBRATION_CANDIDATE`. Error >20 points with both intervals excluding the display and negative skill supports `FAIL / REMOVE`. Without adequate effective N, use `INSUFFICIENT_EVIDENCE`.

### Historical 2.07x lift

`KEEP` requires robust discrimination and a re-estimated exact-production lift within ±0.25x of 2.07. `KEEP_BUT_RELABEL` applies when the point estimate is directionally consistent or within tolerance but uncertainty/LOCO dependence prevents robust promotion. Adequately powered point lift <=1 supports `FAIL / REMOVE`.

### Elevated versus risk-off

Require at least 12 effective episodes in each state to adjudicate separation. `KEEP` requires risk-off minus elevated >0 with a dependence-aware lower bound >=0. `KEEP_BUT_RELABEL` applies to a positive point difference with interval overlap. A nonpositive point difference with adequate evidence is a `RECALIBRATION_CANDIDATE`; material inversion supports `FAIL / REMOVE`.

### Context gate

`KEEP` requires the gated construction to improve Brier or elevated-plus lift with dependence-aware support while not materially reducing AP. Mixed/neutral evidence is `KEEP_BUT_RELABEL`. Adequately powered deterioration in both calibration and discrimination is `FAIL / REMOVE`. Sparse loud-state episodes are `INSUFFICIENT_EVIDENCE`.

## 13. Claim-by-claim mapping

The final report must assign exactly one allowed verdict to each:

1. “extreme China external-driver hazard”
2. 98th-percentile intensity semantics
3. `>=5%/21d` risk-off probability = 50%
4. `>=10%/42d` historical lift ≈2.07x
5. elevated versus risk-off separation
6. 5d/10d/21d ladder
7. context-gate value-add

Allowed verdicts: `KEEP`, `KEEP_BUT_RELABEL`, `RECALIBRATION_CANDIDATE`, `FAIL / REMOVE`, `INSUFFICIENT_EVIDENCE`.

The 98th-percentile claim is additionally checked as a semantic/code contract: it means a causal trailing-504-session rank of the composite, not a 98% drawdown probability, not an all-history percentile, and not an independent confidence level.

## 14. Forward-ledger law

The committed CN forward ledger is read only after this preregistration is committed. Use its exact issued state/model cohort and existing maturity rules. Report matured, pending, loud, risk-off, hit, and unresolved counts. Do not alter historical rows and do not pool them with reconstructed history.

The forward ledger alone cannot promote or recalibrate the current surface before at least 25 graded rows and adequate loud/risk-off episode counts. The current September episode remains unresolved until its exact maturity date.

## 15. Multiple testing and challengers

The confirmatory family contains exactly two targets: 5%/21 and 10%/42. h5/h10, AUC, component baselines, and individual state cells are secondary diagnostics. No threshold, era start, crisis window, block length, benchmark, state pooling rule, or outcome definition may be selected after inspection to rescue a claim.

A challenger may be studied only under a new `CHALLENGER_PREREGISTRATION.md` written before its outcomes are inspected. Challenger evidence cannot overwrite the primary result in this PR and cannot ship live.

## 16. Reproducibility contract

One entry point must regenerate all committed research artifacts:

```bash
python3 -m scripts.research.cn_risk_radar_revalidation \
  --repo-root . \
  --output-dir research/cn_risk_revalidation \
  --bootstrap-reps 5000 \
  --permutation-reps 5000 \
  --seed 20260923
```

The machine result must include exact source/data hashes, parameters, sample windows, excluded/immature rows, all metrics, effective N, forward-ledger separation, and claim verdict reasons. A second run on unchanged inputs must produce byte-identical JSON and Markdown.

## 17. Pre-inspection declaration

Before this document was written, the session inspected the production implementation, source fingerprints, branch/main collision state, and calibration-harness policy comments. It did **not** inspect `data/risk_radar_intl/rri_study_results.json`, any historical outcome result artifact, any benchmark outcome calculation, or any row of `data/risk_radar_intl/cn_forward_log.jsonl`. The numerical claims supplied by the Chairman and embedded in production documentation are hypotheses of record, not newly inspected outcomes.
