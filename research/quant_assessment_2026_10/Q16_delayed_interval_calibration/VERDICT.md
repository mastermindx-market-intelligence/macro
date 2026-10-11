# Q16 — Delayed-feedback and regime-shift calibration of existing forecast intervals

## VERDICT: REJECT

The adaptive layer (delayed-feedback adaptive conformal inference, ACI) is **rejected**.
**Honest fixed split calibration is retained.** This follows the brief's falsifier: "If
delayed feedback makes adaptation unreliable or intervals expand without useful sharpness,
reject the adaptive layer and retain honest fixed calibration."

Research only. Nothing is wired, registered, scheduled, promoted or gated. CN-HAR-2 and every
other registration, trial and live forecast are untouched. `engine/interval_delayed_calibration.py`
has `RESEARCH_ONLY = True`, and nothing imports it.

## What was tested (frozen design: PREREG.md sha256 `edc8a34a3a77878960cc0ae4a96bda7ea0b4036b3539a30b5420015c490853c0`)

- **Forecast being calibrated:** the 80% central interval (alpha = 0.2) for the 22-trading-day log
  return of SPY, QQQ, IWM, TLT and GLD. The interval is built around the incumbent
  `engine/vol_forecast.har_vol` scale, with sigma_h = har_vol·sqrt(22).
- **Score:** s = y / sigma_h.
- **Label timing:** an origin-t label matures at t + 22 (available lag 0).
- **Competitors:**
  - M0: incumbent Gaussian ±z·sigma.
  - FIXED: split-conformal on training labels that matured by the cutoff.
  - ROLLING: 504-origin window of matured labels.
  - ACI: delayed-feedback ACI. Gamma is tuned inside training only.
  - LEAKY: ACI with delay 1. This is a diagnostic, invalid by construction.
- **Split:** one chronological split. Training runs to 2014-12-31 (axis position 2546). The holdout
  covers 2015-01-02 to 2026-09-08, which is 2937 common dates.
- **Run discipline:** one evaluation run (RUNS.log record 2, rc 0). A rerun was refused (record 3,
  rc 4), so there was no repeated holdout search. One provenance reproduction (record 4, rc 0) was
  then made under `PREREG_AMENDMENT.md` (see "Provenance reproduction" below); it changed no design
  parameter and reproduced every output byte for byte.

## Primary result (pooled, normalized interval score; lower is better)

| method | coverage | mean width | mean interval score |
|---|---|---|---|
| FIXED (retained) | 0.7898 | 3.009 | **4.8259** |
| ROLLING | 0.8011 | 3.128 | 4.8963 |
| ACI (delayed feedback) | 0.8029 | 3.180 | 4.9318 |
| ACI, avail_lag 1 (robustness) | 0.8031 | 3.180 | 4.9310 |
| M0 incumbent Gaussian | 0.7192 | 2.563 | 4.9251 |
| LEAKY (invalid diagnostic) | 0.8033 | 3.169 | 4.8456 |

- **Relative effect R = (IS_ACI − IS_FIXED)/IS_FIXED = +0.0220.** ACI is 2.2% *worse*.
  - Circular block bootstrap (block 44, B = 2000, seed 16, 67 blocks): 95% CI **[+0.0114, +0.0335]**.
  - Newey–West t, lag 44: 4.47.
- **ACI vs ROLLING:** relative difference (IS_ACI − IS_ROLLING)/IS_ROLLING = +0.0073 (0.73% worse),
  block-bootstrap 95% CI of that relative difference [+0.0042, +0.0107]; the absolute mean
  difference in normalized interval score is +0.0355.
- **Honest N:** 134 non-overlapping 22-day blocks. There was no attrition beyond the 22 immature
  labels per asset at the data end.
- **Per asset:** ACI's interval score is worse than FIXED for all five assets (`empirical.json`
  `per_asset_test`).
- **Maturity violations:** 0 for FIXED, ROLLING, ACI and ACI-lag1. LEAKY has 5505 per asset, which
  confirms the timing check bites. This count is partly self-confirming: `maturity_violations`
  checks the `consumed_max` that each runner reports for itself under the same delay. The
  independent evidence for requirement 1 (no immature label consumed) is the future-label
  perturbation test in `tests/test_interval_delayed_calibration.py` (perturbing labels that have not
  matured leaves the issued-quantile prefix bit-identical) together with the LEAKY contrast, not the
  zero-violation count.

ACI bought about 1.3 points of extra coverage with about 5.7% wider intervals. Under the interval
score, that extra width did not pay for itself.

## Decision-rule criteria (PREREG §12)

| criterion | result |
|---|---|
| c1 R ≤ −0.02 with CI upper < 0 | **FAIL** (R = +0.022, CI entirely > 0) |
| c2 coverage gap ≤ 0.03 | pass (ACI gap 0.0029) |
| c3 width cap | pass |
| c4 ACI beats ROLLING | **FAIL** |
| c5 controls discriminate and no maturity violations | pass |

KEEP needs c1 through c5 to pass. c1 and c4 fail, and N = 134 honest blocks is at least 60, so the
result is **REJECT**, not INSUFFICIENT_DATA.

## Synthetic controls (requirement 4)

There are 200 repetitions for each scenario, with seeds 10000+r, 20000+r and 30000+r.

| control | result |
|---|---|
| Stationary: ACI/FIXED interval-score ratio | 1.0198. This is under the 1.02 noise-chasing bar, but only just. |
| Abrupt up-shift: post-shift coverage gap | ACI 0.0064 vs FIXED 0.318 |
| Abrupt down-shift | ACI sharpens |

ACI therefore adapts in the way the control was built to detect: it can tell a genuine shift from
noise. On real data, adaptation still cost more than it returned. The 2015–2026 holdout does not
contain shifts large or persistent enough for adaptation to beat a fixed quantile on interval
score. Per-regime coverage is disclosed in `empirical.json` `regime_support`:
- low: 124 blocks, ACI coverage 0.705
- mid: 128 blocks, ACI coverage 0.813
- high: 126 blocks, ACI coverage 0.897

No method is conditionally calibrated across regimes, and no conditional-coverage claim is made.

## Limitations

1. **Gamma grid floor binds.** The tuned gamma was 0.001, the lowest grid value, for every asset
   and in about 97% of control repetitions. A still smaller gamma would converge on FIXED/ROLLING.
   That would not overturn the verdict: the adaptive *layer* adds nothing at its weakest setting.
2. **Adjusted closes are not point-in-time.** The vendor-adjusted series at vintage cdab6268 may
   embed later corporate-action revisions.
3. **Single base forecaster.** The base scale is the incumbent `vol_forecast.har_vol`. Q07 (fitted
   HAR) is a possible alternative base predictor. It was not used and is not a prerequisite.
4. **Stationary ratio near its bar.** 1.0198 against 1.02. Noise chasing is mild but not zero.
5. **Five liquid ETFs at one horizon** (22 days) and one level (80%). Other horizons and levels were
   not tested; the verdict should not be generalized beyond them.
6. **The baseline is a reproduction.** The incumbent `vol_forecast.py` in this snapshot is
   byte-identical to `_base` (sha256 `bcd6ec2c…06c0`). See RUNS.log record 1.

## Provenance reproduction (independent audit fix)

The audit found that `engine/interval_delayed_calibration.py` was edited after record 2 (record 2
hashed `a8eba0a0…67cb`; the shipped file is `59db81bd…6725`) and that `evaluate.py` did not
hash-check the module, so the post-run edit (claimed to be the verdict text only) could not be
checked. Fix:

1. `PREREG_AMENDMENT.md` (sha256 `57bda48f…aff8`, witnessed in `AMENDMENT.log` at 10:36:58Z before
   the run) authorized one reproduction with no design change. `evaluate.py` now refuses unless the
   harness module hashes to `59db81bd…6725` and the amendment matches its witness.
2. The record-2 outputs were moved aside byte-unchanged, and `evaluate.py` was run once (RUNS.log
   record 4, rc 0) on the shipped module.
3. `controls.json` (`7f464a9b…14a9`), `empirical.json` (`661aa666…ee4b`) and `decision.json`
   (`dacfee6c…1085`) are byte-identical to record 2. The shipped module therefore computes exactly
   the published evidence, and the verdict REJECT stands. The archived record-2 copies were
   duplicates and are not shipped; both RUNS.log records bind the same hashes.

`baseline_train.json` (training-window only, pre-freeze, RUNS.log record 1) is not witnessed in
FREEZE.log; it is bound only by its RUNS.log record-1 output hash `ef388b25…6dfb`, which the shipped
file matches.

## Artifacts

- `PREREG.md`, `FREEZE.log`, `PREREG_AMENDMENT.md`, `AMENDMENT.log`, `evaluate.py`, `q16_common.py`,
  `baseline_repro.py`, `RUNS.log`
- `baseline_train.json`, `controls.json`, `empirical.json`, `decision.json`

Output sha256 values are recorded in RUNS.log records 2 and 4 (identical).
