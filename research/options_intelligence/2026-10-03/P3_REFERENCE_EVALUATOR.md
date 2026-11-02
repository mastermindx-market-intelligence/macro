# P3 positive variance forecast: executable reference

**Status:** isolated research reference, synthetic validation only. Operation `options-intelligence-deep-research-20261003-astra-001`. This file supports the P3 design in [PILOT_STUDY_SPEC_V1.md](PILOT_STUDY_SPEC_V1.md); it does not fit market data, construct the incumbent-information adapter, authenticate point-in-time evidence, or implement a production model. Its numerical kernel can also support the identically specified P5 link after that pilot's separate inputs qualify.

## What was made concrete

OIF19 is a volatility residual, `IV - sqrt(physical variance forecast)`. It can be negative. A variance forecast must be strictly positive before it can be evaluated with the selected QLIKE loss. The frozen candidate mapping is

\[
v_{2i}=v_{1i}\exp(\beta z_i),\qquad -1\leq\beta\leq1,
\]

where `v1` is the positive target-matched incumbent-information research forecast and `z` is the training-scaled OIF19 residual. There is one coefficient, no intercept, no second smearing factor and no feature clipping. Setting beta to zero exactly recovers the supplied incumbent forecast. The coefficient interval is a principal design choice, not an empirical optimum or an economic risk limit.

The reference minimizes the weighted mean of

\[
L_i=\log(v_{1i})+\beta z_i+\frac{y_i}{v_{1i}}\exp(-\beta z_i).
\]

The derivative is the weighted mean of `z*(1 - (y/v1)*exp(-beta*z))`. Its derivative is nonnegative for `y>=0`, so the objective is convex. If either interval endpoint satisfies the corresponding derivative sign, the constrained optimum is that boundary. Otherwise a monotone derivative root is bracketed by bisection to width at most `1e-10`, with a maximum of 100 iterations. A boundary result is reported explicitly.

A nonzero constant feature can identify this through-origin coefficient. Nonconstant data are not an independent algebraic requirement. If all curvature terms are zero, the objective is affine; an exact binary-rational weighted slope distinguishes a truly flat objective from a small nonzero slope. A flat objective returns `FIT_UNIDENTIFIED`. This mathematical distinction does not relax the separate positive-MAD requirement for the actual RZ transform.

Independent review exposed floating-point failures in the first draft: a tiny curved feature could round both endpoint derivatives to zero and select the wrong boundary, rounded normalized weight products could reverse a tiny affine slope, and subnormal derivatives could create a false exact root. The accepted implementation uses `log1p`/`expm1` near a unit target/forecast ratio, a small-argument series for the QLIKE curvature term, and exact binary-rational summation of weighted row derivatives. Nonzero derivative underflow, subnormal derivatives and unresolved curved endpoint derivatives return `NUMERICALLY_UNIDENTIFIED`. The original failing examples remain executable regression cases. These measures protect the stated finite reference domain; they are not arbitrary-precision economic or production performance guarantees.

## API and refusal contract

| Function | Purpose | Boundary |
|---|---|---|
| `fit(rows)` | Fit the one coefficient to supplied `id, y, v1, z, weight` rows | All rows retained; positive weights; unique IDs; no automatic data selection |
| `evaluate(rows, beta)` | Produce positive forecasts, weighted QLIKE and derivative | Fixed coefficient domain; same finite-number policy as fitting |
| `robust_scaler(history, fit_at_ns, root, clock_bin)` | Fit median/MAD on the last 60 eligible supplied sessions, minimum 40 | Prequalified fixed feature scope; explicit eligibility census; no pooling, epsilon or future availability |
| `transform(value, scaler)` | Apply `(x-median)/(1.4826*MAD)` without clipping | Raw value remains a separate input; zero/invalid scale refuses |
| `validate_training_chronology(...)` | Check original raw-feature and baseline forecast ordering and upstream label maturity | Supplied integer-nanosecond ordering only; no receipt authenticity or clock calibration attestation |

The optimizer accepts caller-supplied weights so its arithmetic can be independently checked. The study runner must construct the exact equal-date/within-date weights from the study specification; arbitrary weights do not qualify that study. The module does not construct HAR regressors, estimate physical variance, select option pairs, or construct labels. Those inputs retain their own source, model and population qualification gates.

The chronology checker requires nonempty revision references and orders contributing availability, publication, receipt and formation clocks. Training targets must mature after formation and no later than the augmentation fit cutoff; their final immutable label revision must become available no earlier than maturity and no later than that cutoff. A provisional pre-maturity value is not that final revision. The nuisance and incumbent model training labels must mature no later than their respective historical fit clocks. The final fit must precede the first test decision. Final training-fold RZ scaling is separate from those honest historical raw predictions: fitting a training-only scaler does not falsely require its final fit to predate every training row.

Clock values are nonnegative integer epoch nanoseconds. A fractional float is refused, rather than silently truncated. Synthetic records use small integer clocks only to exercise ordering; they are explicitly not real dated receipts. A successful ordering check returns `availability_attested:false` and `consumer_capture_attested:false`. Authentic original capture and source condition/correction evidence belong to the [source-admission contract](SOURCE_ADMISSION_SPEC.md) and the current data owner.

Zero realized variance is allowed in QLIKE. Missing values, Boolean numbers, negative targets, nonpositive baseline variance/weights, duplicated row identities, exponential overflow, positive underflow to zero, nonfinite products/losses, and failed solver/domain conditions return typed refusal. Failed rows are not dropped, turned into zero, or replaced by B0/B1. Evaluating the fixed coefficient boundaries is part of fit qualification: a large unbounded RZ value can make the proposed model numerically unavailable even when a smaller coefficient might have been representable. The reference does not silently choose a different bracket.

## Discriminating synthetic checks

The executable bundle tests a known interior optimum at beta `0.35`, exact beta-zero nesting, negative features with positive forecasts, constrained boundary optima, zero targets, flat and identifiable constant-feature cases, row permutation and common weight scaling. Scaling both target and forecast by the same variance-unit factor leaves the fitted coefficient and paired QLIKE benefit unchanged. The numerical-domain cases require refusal, including a failed row appended to otherwise valid observations.

Separate cases expose feature publication after the decision, delayed consumer delivery, upstream nuisance/baseline label leakage, immature augmentation labels, missing revisions, fractional clocks, future scaler availability, cross-root pooling, duplicate sessions, insufficient history and zero MAD. These checks test the declared functions; they do not establish natural source coverage, empirical signal value, power, or correct production integration.

Run from this artifact directory:

```bash
python pilot-p3-reference.py --output /tmp/pilot-p3-reference-check.json
```

The command creates a new output file and refuses to overwrite an existing file. Its output reports the case count, script digest and complete result digest. [pilot-p3-reference-results.json](pilot-p3-reference-results.json) preserves the accepted synthetic run; [P3_REFERENCE_REVIEW.md](P3_REFERENCE_REVIEW.md) records the independent review and exact reviewed version. The repository manifest binds all final bytes.

## Statistical meaning and remaining work

QLIKE is applied to matched variance units and a separate realized-variance label. Its useful robustness properties depend on the volatility proxy assumptions; the chosen loss cannot cure stale observations, unavailable original vintages, or an ill-defined sampling window. The study's realized variance estimator remains an estimator, not latent variance truth. See Patton's primary paper, [Volatility forecast comparison using imperfect volatility proxies](https://public.econ.duke.edu/~ap172/Patton_vol_proxies_JoE_2011.pdf), for the forecast-loss/proxy analysis.

The principal still needs an accepted existing-owner study implementation, qualified dynamic-panel snapshots, source and model availability evidence, actual train/validation/test manifests, and feasible pretest power before any empirical run can be called the sealed study. This reference removes the previously unspecified positive-forecast mapping and supplies falsifiable arithmetic; it supplies none of those data-dependent acceptances.
