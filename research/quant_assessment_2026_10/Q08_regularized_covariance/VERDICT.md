# Q08 VERDICT — Regularized covariance and uncertainty-aware independent-bet counts

**VERDICT: REJECT** (the estimator contest). The incumbent sample correlation stays.

The authority level does not change. Every output remains `context`. Nothing is wired, gated, ranked or sized.

## The decision rule

The rule is PREREG §6, frozen with sha256 `23a6f671…8a03` (see FREEZE.log) before any outcome was read.

A challenger is kept only if all three of these hold:
- its mean held-out Gaussian/Stein loss contrast, D = sample − challenger, is at least 0.005 nats/day;
- the lower bound of its Bonferroni-adjusted (98.33%) circular moving-block bootstrap interval is above 0;
- its Frobenius off-diagonal contrast is not worse.

## Evidence

Source: `results.json`, written by `evaluate.py --mode evaluate`, exit 0, logged in RUNS.log.

### Code provenance (independent-audit MAJOR finding, resolved by replay)

- The original baseline and evaluation RUNs recorded module sha256 `93fa5994…789f5`, the value frozen in PREREG §3. The shipped module is `b591ee9b…4317`. The `93fa…` bytes are not retained anywhere, so a docstring-only change could not be proven by sha or AST comparison.
- `PREREG_AMENDMENT.md` (sha256 `6c1b25b2…a308`) was written before any replay output was read. It authorised exactly one replay of both modes, with an identical specification, on the shipped bytes.
- The replay outputs are **byte-identical** to the originals, so no result-bearing code path differs between the two module versions for this evaluation:
  - `baseline_reproduction.json` `0e624c08…6d9a`;
  - `results.json` `4e72ab05…6df0`;
  - `results_detail.json` `17a2a5ed…523d`.
- RUNS.log holds the two replay RUN lines and a non-RUN `PROVENANCE` line.
- **Remaining limitation:** the `93fa…` source itself cannot be shown. What is shown is output equivalence on this data and specification.

### Data and support

- **Data:** `data/breadth/_factor_legs.parquet` at vintage cdab6268 (sha256 `cc3476e6…94bd`). This holds 4 daily long-short factor legs: size, value, quality and low_vol.
- **Support:**
  - Complete-case span 2024-02-01..2026-07-31: 626 of 777 rows. low_vol is missing on 151 rows.
  - Evaluation span 2025-02-04..2026-07-08.
- **Honest N:** K = 17 non-overlapping 21-day held-out blocks. All 17 were evaluable and 0 were unavailable. There was one comparison and no repeated holdout search.

### Primary contest

Training window 252 days. The baseline's mean Stein loss is 1.4004.

| Challenger | mean D (nats/day) | 98.33% MBB CI | HAC t (p) | Frobenius contrast | blocks won | qualifies |
|---|---|---|---|---|---|---|
| lw_identity (LW2004) | −0.00981 | [−0.0562, +0.0344] | −0.484 (0.628) | +0.00682 | 7/17 | no |
| lw_constant_corr (LW2003) | −0.00130 | [−0.0330, +0.0297] | −0.096 (0.923) | +0.00610 | 8/17 | no |
| lw_nonlinear (QIS 2022) | +0.00837 | [−0.0105, +0.0263] | +1.045 (0.296) | +0.02165 | 11/17 | no (CI includes 0) |

### Sensitivity check

Training window 60 days; this check does not affect the decision.

- Both linear shrinkers lose: lw_identity −0.0898 and lw_constant_corr −0.0372 nats/day, and both are worse on Frobenius.
- Nonlinear shrinkage gives +0.0130 nats/day with CI [−0.033, +0.066], so it is not decisive.

## What survives: PR uncertainty

This is diagnostic only, not a decision.

Interval at the final origin: trailing 252 rows, 90% stationary bootstrap, mean block 10, B = 1000, 0 failed resamples.

| Estimator | point PR | 90% interval |
|---|---|---|
| sample (the incumbent formula) | 2.481 | [2.224, 2.722] |
| lw_identity | 2.584 | [2.327, 2.840] |
| lw_constant_corr | 2.546 | [2.293, 2.799] |
| lw_nonlinear | 2.507 | [2.253, 2.754] |

**Reading the incumbent's PR.** The incumbent's 4-decimal participation ratio, 2.4807, overstates its precision. Its uncertainty has two components, and the bootstrap interval captures only the first.
- **Within-window sampling uncertainty.** The 90% interval at the final origin is [2.224, 2.722], about ±0.25. It holds the training window fixed. The median within-window 90% width across the 17 rolling origins is 0.31.
- **Across-origin instability.** This component is at least as large. Across the 17 rolling origins (training windows ending 2025-02-03 to 2026-06-05) the sample point PR ranges from 2.639 to 2.892 (std 0.077). The final-origin point (2.481) and its whole interval lie *below* that range: the trailing window (2025-07-31..2026-07-31), which ends later than any rolling origin's window, sits outside the across-origin envelope. A within-window interval therefore understates how much the number moves as the window rolls.
- An honest reading is "between about 2.2 and 2.9 effective bets depending on window, with about ±0.25 sampling noise inside any one window". It is not "2.48 ± 0.25".
- **This finding has a scope limit.** It does not show that the incumbent's number is wrong: the baseline was reproduced exactly (`baseline_reproduction.json`). It shows only that the number is reported without its uncertainty.

## Interpretation

With N = 4 legs and T = 252 days, N/T is about 0.016. The sample covariance is already well conditioned, so shrinkage has little to correct. The synthetic N/T-large case in `test_req5_shrinkage_beats_sample_on_held_out_loss_when_n_over_t_is_large` shows the estimators do work where theory says they should. That case is not the incumbent's regime.

## Scope limits (from the independent audit)

- **Requirement 1 (basis/unit/clock guard) is shown synthetically only.** `evaluate.py` declares the four empirical series as `long_short` / `decimal_return` / `daily_close` (`SeriesSpec`). It does not derive those labels from the data, so on the real panel the guard checks declared labels for consistency. It does not detect a mislabelled input. The refusal behaviour is exercised by the synthetic req1 tests.
- **HAC cross-check:** it uses the incumbent `engine.validation.newey_west_tstat`. The Q18 brief is sequenced after Q08 and was not read.
- **Data recency:** the data end at the last available row (2026-07-31), stale relative to the run date.

## Falsifier

This REJECT would be overturned by a future frozen rerun that shows any challenger clearing the same §6 rule on a new, non-overlapping held-out span. Two examples:
- a larger factor panel, where N/T is materially higher;
- legs with longer complete-case support.

A different window, block length or bar chosen after seeing these numbers does not qualify.

## Offered as a research reference (NOT WIRED)

`engine/covariance_shrinkage_diagnostics.py` provides:
- the basis/unit/clock guard, which refuses incompatible series instead of silently falling back;
- symmetry/PSD validation and preservation of exact zeros;
- PR interval reporting.

Nothing imports it. Any adoption would be a separate, reviewed decision.
