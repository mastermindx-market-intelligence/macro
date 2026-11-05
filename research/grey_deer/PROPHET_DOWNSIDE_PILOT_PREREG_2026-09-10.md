# Absolute-downside archive pilot — preregistration P1

Record date: September 10, 2026 (US); execution may occur September 11 UTC. Existing records operation: `prophet-absolute-downside-research-20260910-sol-001`, PR #7043. Sol owns this bounded methodological investigation; existing Grey Deer/Prophet/Fusion and data owners remain unchanged. No production or trading authority.

## Status and purpose

This file is committed BEFORE reading numeric price columns or computing labels/model results in this pilot. Only filenames, schemas, row/date counts, metadata, source documentation and byte hashes have been inspected. The motivating September incident and previous research are known; the test period below excludes that incident. This is a new, deliberately limited source-native absolute-loss diagnostic, not a relabelling or reopening of GD-1C.

Question: do lagged sector-participation observations improve prediction of an absolute adverse SPY daily-bar outcome beyond a simple SPY volatility/range baseline? This does not test stock selection, constituent breadth, opening-auction executions, an operational Prophet policy or realized customer P&L. A negative result is useful and must be retained.

## Source qualification and scope limits

Data source is the existing Massive whole-market daily store, on a read-only, separately dated local mirror of the R2-canonical store. The current main checkout has only the two JSON sidecars; no SPY parquet. A documented older data location contains the 14 selected parquets. Each file has 1,254 unique dates from 2021-07-06 through 2026-07-02. Its nearby manifest claims August 18 and 1,286 SPY rows; those claims do NOT override the actual selected file dates. The current committed canonical manifest at Macro `14dc3b38111081a0d559d27b9c36ab995c8aa441` is a different observation, through September 8.

Internal research rights are recorded in `research/licenses/MASSIVE_ENTITLEMENT_RECORD.md`, blob `3969a9aae918141b51baffbb0e17d8a2ec2485a0` at that Macro pin. No private agreement, credentials or raw quote history will be published in this PR. The store and collector are unchanged.

Official source documentation read before the pilot says flat-file prices are unadjusted and daily files are normally finalized around 11 a.m. ET on the following day. Therefore a prior day's finalized flat file is NOT assumed available at the next pre-open. The registered lag is TWO SPY-observation rows. This is a conservative study assumption, not proof of each historical file's first availability. The mirror has no historical first-capture/revision ledger, and daily bar open/close are not independently certified here as the regular-session opening/closing auctions. Consequently all results are `RETROSPECTIVE_ARCHIVE_DIAGNOSTIC`, never point-in-time operational replay, promotion or execution proof.

References: https://massive.com/docs/flat-files/stocks/day-aggregates ; https://massive.com/docs/flat-files/stocks/overview ; https://massive.com/docs/rest/stocks/aggregates/custom-bars . REST split adjustment is not a substitute for a validated common-basis historical producer. No REST data is mixed into this pilot.

## Frozen input identities

Selected symbols: SPY, QQQ, IWM, and the 11 sector funds XLB, XLC, XLE, XLF, XLI, XLK, XLP, XLRE, XLU, XLV, XLY. IWM is retained in the source census but not used as a fitted feature or an alternative endpoint. No symbol substitutions after outcome access.

SHA256 of the actual parquet bytes:

| Symbol | SHA256 |
|---|---|
| SPY | a04b4b27782c90707f84f9b19903914ca26e72bca9d739077da7df787a14fda6 |
| QQQ | ab1a48e218dd4ca7a2ff322dffb023ddfab39301ee7b1f8743ed57fc079bab68 |
| IWM | be4d143db7968a41455488b0b5479b48e863b0480155856f55002375bc596079 |
| XLB | 8b2041adf453ce008f6e1c4b0f4ad8061360b9026ebcb4c382ab7b9a190b59ab |
| XLC | 7073b95f5d02c072500eae8053b0e2416b24f36660a9deadc0ce45fec8369c33 |
| XLE | 67f287d27d63fe5dc58a7782c4bc484ca9e49ee49f7e4ad1e096f503aa9de4f6 |
| XLF | c88c9d3b3821fdfbb4f294c4f2404aa8401e2c898287d613d9c284ab921b28e5 |
| XLI | 68244cc7b74e240db59ff06f0a02d270e3c82ea33e06a80fb364b0a4d1c602e1 |
| XLK | a218245c0d112ef9aa0b621378fab388be3d9b0d943f9e74152c104d8d0ce2d2 |
| XLP | 8f32475cb279dca7ab8ad43b5c0ed42ac0d2c2ffa6431faddf6b065869d827ca |
| XLRE | 11f7b6c824150f8883035b7f56c4a295c6878d06afed027622ce27a0c9fecf52 |
| XLU | b16d5dfee6f521d4d01e86ca21a06ffd511a79b0d0cdff56e82a604c9f25f557 |
| XLV | 5b9c776f8127222d4796fab85c0cf4977dc9536f5549adb85749a1bd3211c6fc |
| XLY | 0f9b38c77afe1cb3b29e56274a49ee2452d6d29b199dc7ef972228626067761f |

Abort on hash changes; no silent newer-snapshot substitution. Require unique increasing SPY dates and exact date alignment of the selected inputs. No forward fill or imputation. Reject nonfinite/nonpositive OHLC and rows whose low exceeds min(open,close), high is below max(open,close), or high < low. Disclose every exclusion by stage. A missing input makes the feature row unavailable, not zero. Do not remove an observation merely because its loss is large.

## Targets and time mapping

Let body_j = close_j/open_j - 1; range_j = (high_j-low_j)/open_j. All computations are within the same raw bar, avoiding an assumed cross-date adjustment factor. This does NOT establish an executable fill at open_j.

Primary endpoint at SPY row t: `body_SPY,t <= -0.01`.
Secondary descriptive endpoint: `low_SPY,t/open_SPY,t - 1 <= -0.01`. The same method may be fitted separately to this secondary endpoint and must be reported separately; it may not rescue a failed primary result. It is an adverse move relative to the source bar's open, not a complete path/stop-order reconstruction.

Prediction at row t may use only features through row t-2. The one-row embargo represents the documented following-morning archive delay under the study's pre-open analogy. Dates are the actual SPY observation index, not a newly invented market calendar. Source sessions later than the frozen cutoff are never consumed.

Every fully specified eligible row is evaluated, not only rows when a warning would fire. No selection by today's Prophet constituents or by losses.

## Six frozen features, before the two-row shift

1. Absolute SPY body return, in percentage points.
2. SPY range, in percentage points.
3. Fraction of the 11 sector fund bodies below zero. Zero is neither negative nor missing.
4. Equal-weight mean of those sector body returns, in percentage points.
5. The five-row moving mean of feature 3 minus its 20-row moving mean. Require all 20 observations.
6. QQQ body return minus SPY body return, in percentage points.

Standardization uses TRAINING means and standard deviations only; a constant training column is assigned scale 1. No feature selection, interactions, threshold changes or extra model classes after outcomes.

## Splits and models

Training: available observations from 2021-07-06 through 2023-12-31 after warmup and lag. Calibration: 2024-01-01 through 2024-12-31. Locked test: 2025-01-01 through 2026-06-30. July 2026 and all later data are excluded. No rolling refit in this pilot.

Models:

- P0: constant event prevalence over all eligible training + calibration rows with Beta(1,1) smoothing.
- P1: logistic regression on features 1-2.
- P2: logistic regression on all six features.

For P1/P2 minimize mean binary log loss + 0.01/2 times the squared standardized-feature coefficients; intercept unpenalized. Use deterministic L-BFGS-B, initial coefficients zero and intercept equal to the smoothed training log odds, maxiter 2000, ftol 1e-12. Abort and report optimizer failure, do not switch solver/tune penalties to obtain a desired result.

Fit a calibration-only logistic mapping `sigmoid(a*logit(raw_probability)+b)` separately for each model/endpoint on 2024 only. Bounds a=[0,10], b=[-10,10]; initial a=1,b=0; weak penalty 0.0001/2*((a-1)^2+b^2), same optimizer settings. Report raw AND calibrated outputs. P0 is not fitted through another calibrator.

No class weighting, random train/test split, oversampling or post-test sign flipping. Seeds only govern the uncertainty calculation, not model selection.

## Reporting and fixed interpretation

Primary comparison: calibrated P2 minus calibrated P1 on the SAME locked test dates, using Brier loss. Report P0 and raw scores as context. Also report mean log loss, event prevalence, mean predicted probability, all model coefficients, split counts/exclusions, and results separately for 2025 and 2026H1. No hit-rate headline without a specified threshold.

Uncertainty: 1,000 paired circular moving-block bootstrap draws on test losses, block length 10, RNG seed 20260910. Report 2.5/50/97.5 percentiles of (P2 squared error minus P1 squared error). This is a dependence-aware diagnostic, not a distribution-free guarantee. Minimum descriptive test adequacy: 100 eligible test rows and 20 primary events. If below that, label UNDERPOWERED; do not enlarge the endpoint or shift the split after looking.

An incremental candidate is interesting only if the primary difference is negative, the bootstrap upper bound is below zero, and neither reported test subperiod has worse Brier loss. Even then the verdict is NEEDS_PIT_AND_FORWARD_VALIDATION, never promotion. Otherwise record NO_INCREMENTAL_SUPPORT or UNDERPOWERED with the exact reason. Secondary outcomes, raw-only improvement or a compelling story cannot overwrite this rule.

No portfolio backtest, annualized return, Sharpe, trade recommendation, automatic gating, sizing or execution claim follows from this pilot. No unrestricted inspection of the existing gated W3 comparison ledger. No new canonical model/identity/price/outcome store.

## Run and stop contract

Implement a small standalone offline analysis harness outside production source; test label, timing, null, alignment and training-only transforms before real-data execution. Use the selected read-only local files; never restore/publish the full store or modify another worker's checkout. Retain code/input hashes, optimizer receipts, per-split metrics, and report failures without rerunning another specification. If tools interrupt the same process, reconcile its output rather than launching another run blindly.

After the first result, publish a separate dated disposition on this SAME records carrier and update the existing handoff. Do not edit this preregistration to agree with the result. An implementation bug found independently may be corrected with explicit pre/post evidence while preserving the frozen scientific specification; a scientific change needs a new preregistration and untouched future evaluation.
