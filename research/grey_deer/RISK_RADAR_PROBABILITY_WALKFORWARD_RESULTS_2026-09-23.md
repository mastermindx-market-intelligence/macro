# Risk Radar Probability Walk-Forward — Results

Protocol commit: `055b3564d1a31b763638e38563afc245c89dcf2f`.

Primary verdict: **not_promotion_eligible**.

Research-only annual expanding-origin evaluation. No live probability or authority changed.

| Horizon | n | Current Brier | Candidate Brier | Delta | 90% block CI | Current WACE | Candidate WACE | Year wins |
|---|---:|---:|---:|---:|---|---:|---:|---:|
| H5 | 4024 | 0.028620 | 0.028857 | +0.000237 | [-0.000619, +0.001025] | 0.016436 | 0.028849 | 7/16 |
| H10 | 4024 | 0.064341 | 0.064821 | +0.000480 | [-0.001205, +0.002124] | 0.032271 | 0.072071 | 6/16 |
| H21 | 4024 | 0.125518 | 0.127709 | +0.002190 | [-0.000266, +0.004842] | 0.037085 | 0.122629 | 5/16 |

## Frozen promotion checks

- PASS — `identical_populations`
- PASS — `authority_partition_preserved`
- FAIL — `point_brier_improves_all`
- FAIL — `brier_ci_upper_nonpositive_all`
- FAIL — `wace_nonworse_all`
- FAIL — `annual_wins_at_least_10_all`

## Evidence boundary

These are overlapping reconstructed historical windows evaluated strictly out-of-fold by calendar year. They are not genuinely issued forecasts and do not authorize a runtime probability change.

The already-inspected 2020+ single holdout was not used to tune this candidate. No second candidate is fit to these walk-forward results in this wave.
