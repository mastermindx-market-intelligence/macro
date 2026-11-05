# Independent review: P3 positive-variance reference

**Disposition: accepted as a bounded synthetic numerical reference at the digests below; no remaining blocking finding from this review.** This is not empirical model acceptance, a proof of globally accurate floating-point optimization, an authentication of historical availability, or production authority.

Review date: 2026-10-03. Reviewer: independent native research worker under the principal. The principal authored and repaired `pilot-p3-reference.py`; the reviewer did not edit that source, its documentation or its result artifact. The reviewer created this report and, at the principal's later request, preserved the independent probes in a separate portable checker. No production, market-data, provider, M2 or further agent work occurred.

## 1. Exact reviewed artifacts

| Artifact | Bytes | SHA256 |
|---|---:|---|
| [pilot-p3-reference.py](pilot-p3-reference.py) | 27,206 | `29fc1cc5ff79abc5a7f0377ea1860113adc851f0aad81feb852d27d45a65a11f` |
| [pilot-p3-reference-results.json](pilot-p3-reference-results.json) | 17,648 | `73d21c0f1006b05b184d8d26e5ef5f92ab4724a78f339e24fe3716da7d251d68` |
| [P3_REFERENCE_EVALUATOR.md](P3_REFERENCE_EVALUATOR.md) | 9,039 | `7622434d498cf4885a5d4dabc2c94b2fa7c3233e69c697e94d9bb5a4357b3ad5` |
| [pilot-p3-independent-check.py](pilot-p3-independent-check.py) | 8,673 | `dfc2bca3421cab6fee6b578bcba2a54a89f750a25a6a761b944d78e8092bdb47` |

The accompanying [pilot specification](PILOT_STUDY_SPEC_V1.md) was inspected at SHA256 `f439d6df16f5437ce6bf996fefe1df891927f5539ece368d44cbe9098bf971f8`. Its fixed coefficient interval, one-feature/no-intercept construction, positive forecast requirement, zero-target treatment, last-60/minimum-40 scaler, and supplied-clock rules informed this review. This report does not substitute for review of the entire empirical study runner.

The final author artifact reports **52/52 synthetic cases passing**, `empirical_fit_performed:false` and `availability_attested:false`; its source digest matches the reviewed script. The independent checker completes **346 assertions**, alongside those author cases. The checker verifies that source bytes do not change during execution and defaults to refusing a different source digest.

## 2. Mathematical contract

For positive incumbent variance `v1`, nonnegative variance target `y`, a signed dimensionless feature `z`, positive observation weights and `β∈[−1,1]`, the link

\[
v_2=v_1e^{\beta z}
\]

is positive wherever the declared floating-point operations remain representable. `β=0` nests the supplied incumbent forecast exactly. The feature residual itself is never treated as a variance forecast, and there is no extra intercept or smearing adjustment.

The weighted QLIKE objective is the mean of

\[
L_i(\beta)=\log v_{1i}+\beta z_i+\frac{y_i}{v_{1i}}e^{-\beta z_i}.
\]

Its derivative and second derivative are

\[
D(\beta)=E_w\!\left[z_i\left(1-\frac{y_i}{v_{1i}}e^{-\beta z_i}\right)\right],\quad
Q(\beta)=E_w\!\left[z_i^2\frac{y_i}{v_{1i}}e^{-\beta z_i}\right]\ge0.
\]

Thus the one-dimensional objective is convex; it is strictly convex if any positive-weight row has both `y>0` and `z≠0`. Otherwise it is affine, with an unidentified flat case when the weighted feature sum is zero. Zero targets are legitimate: their loss contribution is `log(v1)+βz`, without evaluating `log(0)`.

The final code's stable positive-target representation, with `d=log(y/v1)−βz`, is algebraically equivalent:

\[
L=\log y+1+\bigl(\operatorname{expm1}(d)-d\bigr),\qquad
D_i=-z_i\operatorname{expm1}(d).
\]

The near-zero series avoids subtracting nearly equal terms in the curvature part. Exact binary-rational accumulation of original weights times already-computed row derivatives avoids the normalized-weight sign reversal described below. It does not make the row exponentials or entire optimizer arbitrary precision.

## 3. Findings discovered independently and their final disposition

All findings below were reported to the principal before source repair. The reviewer kept the source unchanged.

| Finding | Independent discriminating input and original behavior | Final disposition |
|---|---|---|
| F1. Tiny curved objective incorrectly certified at a boundary | One row `y=v1=1,z=1e-20,w=1` has analytic optimum β0. The original returned β−1, `constrained_optimum=true`, after derivatives rounded to zero. `z=1e-16` also produced a false lower-bound result. | Closed. Stable `log1p`/`expm1` evaluation returns β0 for the retained tiny-feature case; unresolved derivative cases refuse. |
| F2. Affine slope sign reversed by normalized-weight rounding | All `y=0,v1=1`; `(w,z)=(1,5),(5,−1),(1,−1e-18)`. Exact original-weight slope is `−1e-18/7`, so β+1 is optimal. The first implementation returned β−1 with derivative `+1.1087944531965851e-16`. | Closed. Exact original-weight derivative accumulation returns β+1 and a negative derivative. |
| F3. Nonzero RZ silently underflowed to zero | `transform(±1e-300,{median:0,scale:1e100})` returned signed zero, although the mathematical transformed values are `±1e-400`. | Closed. Both signs return typed `NONZERO_UNDERFLOW`; an observed input exactly equal to the median still transforms to a valid zero. |
| F4. Missing scaler scope admitted | Forty eligible rows with `root=None,clock_bin=None`, called with the same missing scope, returned `SCALER_FIT`. | Closed. Missing/blank scope is refused; the final independent probe receives `INVALID_SCALER_SCOPE`. |
| F5. Exact target-revision availability was not fully ordered | Initially a future exact label revision was outside the minimal checker's fields. After the upper-bound repair, `label_mature=2000,label_revision_available=1999,fit=3000` still passed. | Closed. The checker now requires `maturity ≤ exact final revision availability ≤ augmentation fit`. A provisional value is not that final revision. Early final-revision availability returns `LABEL_REVISION_BEFORE_MATURITY`; late availability also refuses. |
| F6. Subnormal derivatives created a false exact interior root | Rows `(y=v1=1,z=1e-160,w=1)` and `(y=0,v1=1,z=−1e-321,w=1)` returned β`0.099609375`, derivative0 and bracket width0. A 400-digit Decimal calculation gives β`0.0998012604599318`, error about `1.9189e-4`, far larger than the declared bracket tolerance. | Closed conservatively. The final code refuses nonzero derivative underflow and subnormal row/weighted derivatives with `NUMERICALLY_UNIDENTIFIED`, rather than certifying that root. |

For F6, the independent closed form is

\[
\beta_*=-\frac{\log(1+z_{affine}/z_{curved})}{z_{curved}}.
\]

The initial source observed at review entry had SHA256 `72ef24d714da1b5c1b973842156089ee1b25213a934b92b52c493771817d9d5b`. The subnormal-root counterexample was explicitly reproduced against intermediate SHA256 `f5abcfcdd7b672454d983732cd602c79325c0cf871131d9ca66c5cd31a3b11dc`. These historical findings are retained as failure provenance; the acceptance disposition applies only to the final digest in §1.

## 4. Independent checks beyond the author's fixtures

The independent batch used seed `623107` to create 64 synthetic weighted datasets, each containing two through eight rows, features in [−4,4], baseline variances between approximately `1e-3` and `10^-0.5`, varied positive weights, positive targets and selected genuine zero targets. It did not load market observations.

For each dataset, an independent **75-digit Decimal** objective/gradient used the exact binary-float input values converted into Decimal. A separate 140-iteration high-precision derivative bisection or boundary test supplied the comparison optimum. The checks covered coefficient agreement, original-row permutation, common weight scaling, and independent loss/gradient values at β0.37.

| Measurement | Observed result |
|---|---:|
| Weighted datasets checked | 64 |
| Boundary optima among those datasets | 3 |
| Maximum absolute β difference from independent optimizer | `2.8610461222378092e-11` |
| Maximum absolute gradient difference at β0.37 | `7.105427357601002e-15` |
| Loss/gradient comparison tolerance | Relative `2e-12`, absolute `1e-12` |
| Coefficient comparison tolerance | `5.1e-11`, consistent with a `1e-10` midpoint bracket |

The scaler checks independently constructed a 90-session census with ineligible rows and verified the latest 60 eligible selections, order-statistic median/MAD, permutation invariance, the exact 40-observation boundary, 39-observation refusal and future ineligible-row refusal. The expected final selected interval was `s020` through `s089`, with median54.5 and MAD17.5. These are synthetic session labels, not assertions about an exchange calendar.

Clock probes separately challenged future feature input, late consumer receipt, upstream baseline/nuisance fit order, immature labels, late and premature final target revisions, duplicate identities and fit/test equality. A valid chronology continues to return both availability and consumer-capture attestation flags as false.

## 5. Reproduction and preservation details

The final executed independent command was:

```bash
PYTHONDONTWRITEBYTECODE=1 python /workspace/scratch/304dc2fae6f2/options-research/pilot-p3-independent-check.py
```

It returned `PASS`, the source/checker digests in §1, `independent_assertions:346` and `baseline_cases:52`. The checker writes only stdout, executes the digest-checked reference as an isolated module, and verifies source bytes again after the probes. No JSON or bytecode was written by the review runs.

For portability, the saved checker locates the reference beside itself, accepts `--source`, and has an explicit expected-source-digest guard. It preserves the original independent batch's seed, generated-data rules and Decimal comparisons. It is **not byte-for-byte the original shell transcript**: the absolute source path was parameterized, the previously observational early-label-clock probe became a required refusal assertion, and the independently discovered closed numeric/scope witnesses were assembled into explicit regression probes. These changes reproduce completed review work; they add no empirical fitting or wider research search.

## 6. Limits and owner boundary

This review establishes agreement on the finite tested domain and closure of the concrete failures above. It does not prove correct certification for every possible float64 input or guarantee practical conditioning for a future population. Subnormal derivative refusal is intentionally conservative. The source still uses finite-precision row calculations and loss aggregation; differences at rounding scale cannot support economic claims. A fixed [−1,1] bracket may be numerically unavailable for a very large unclipped RZ value even if an interior coefficient would be representable; the source explicitly refuses instead of silently shrinking the domain or substituting B1.

The scaler assumes an already qualified census for one declared feature scope. Its last-60/minimum-40 arithmetic does not verify missing sessions, eligibility authenticity, root mapping, horizon consistency or the data owner's selection rule. The optimizer similarly accepts supplied positive weights; the study runner must implement the actual equal-date/within-date policy.

Chronology acceptance is only the ordering of supplied clocks and revision strings. It cannot authenticate a revision, prove historical delivery, establish actual model-training membership, verify source clock calibration, or link every training row to original evidence without the incumbent custody mechanisms. The final RZ transform is correctly allowed to fit the training fold rather than being falsely required to predate all historical training rows; upstream raw features and baseline forecasts retain their separate as-of obligations.

No physical-variance HAR, incumbent-information adapter, point-in-time universe, train/validation/test manifest, power analysis or empirical predictive result was created here. Existing-owner adaptation, source qualification and the separately sealed empirical protocol remain necessary before a Fable implementation or model-policy decision can rely on real observations.
