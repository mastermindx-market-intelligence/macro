# Risk Radar Probability Recalibration — OOS Candidate Results

Protocol commit: `c64d72e14446f6f2e89924873aba7df2a67a9e02`.
Method freeze: `293b19626d426d1812b5a88a574773fc1dca9d63`.

## Verdict

**NOT PROMOTION-ELIGIBLE. No live probability change.**

A state-only surface fitted on pre-2020 history with fixed Jeffreys smoothing + weighted monotonic pooling preserved the current Market-State authority partition, but it did not generalize strongly enough to 2020+.

The existing conjunction bump was held byte-for-byte constant.

## Frozen candidate

| Horizon | Calm | Watch | Caution | Elevated | Risk-off |
|---|---:|---:|---:|---:|---:|
| H5 | 2.04% | 2.04% | 2.04% | 15.09% | 15.67% |
| H10 | 6.34% | 6.34% | 6.49% | 25.15% | 26.36% |
| H21 | 12.89% | 12.89% | 15.49% | 41.89% | 41.89% |

H21 authority partition remains unchanged relative to the shipped 17.8% base:
calm/watch/caution below base; elevated/risk-off above base.

## 2020+ holdout

| Horizon | Current Brier | Candidate Brier | Candidate-current | 90% paired block CI | Current WACE | Candidate WACE |
|---|---:|---:|---:|---|---:|---:|
| H5 | 0.032745 | 0.032700 | -0.000045 | [-0.001542, +0.001292] | 0.02295 | 0.01815 |
| H10 | 0.070161 | 0.069415 | -0.000746 | [-0.003688, +0.002417] | 0.04750 | 0.03630 |
| H21 | 0.132598 | 0.133499 | **+0.000901** | [-0.003731, +0.005536] | 0.06098 | 0.06175 |

The candidate improves point Brier at H5/H10, but H10 misses the preregistered uncertainty ceiling by 0.000417. H21 is worse on both point Brier and weighted absolute calibration error, and its paired interval crosses materially positive harm.

## Interpretation

The failure is informative about era transfer. Pre-2020 history wants a much steeper upper-state H21 surface (~42% for both elevated and risk-off). The modern holdout does **not** support promoting that uplift as a general calibration.

This is not evidence that the current surface is precision-grade; the accepted probability audit already shows it is not. It is evidence that a simple old-era state-only refit is not a safe replacement.

The next model-quality action is therefore **not** to tune a second candidate against the now-observed 2020+ holdout. That would contaminate the holdout. Instead:
1. keep the current live probabilities;
2. preserve the evidence-depth disclosure;
3. harden the self-correction loop so any future `prob_cal` proposal must pass its own probability/Brier and authority-partition do-no-harm gate, rather than piggybacking on alert F1.

## Evidence boundary

This is reconstructed historical replay, not genuinely issued forecast history. No collector ran. No `data/risk_radar/calibration.json`, review log, forward ledger, runtime model file, policy, sizing, ranking, or capital authority was written.
