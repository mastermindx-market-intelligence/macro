# PB-D — Power, dependence and limitations

Operation `PB-D-T2-EVENT-QUALITY-20261007`. Research only. The historical results are a selected discovery; the future protocol is frozen but not enrolled.

## 1. What the present evidence can support

The strongest current cell is first-T2 plus at least two legacy categories: 5/5 H5 SPY and sector wins, 4/5 absolute wins, with a positive repeated-row same-date comparison. Those facts are reproduced, but five issuers cannot establish a reliable 100% success probability. The exact two-sided 95% IID interval for 5/5 extends down to 47.82%. Even this interval assumes a prespecified rule and independent trials, conditions not supplied by the discovery process.

The repeated 10/12 count contains five ADM and four PRIM rows. Those are repeated issuer exposures during overlapping return windows. Same-date observations share market shocks; source roots can also be shared. The source's first-T2 Fisher p≈.01281 and a one-sided binomial p=.03125 for 5/5 against .5 are conditional calculations, not confirmation after trying several rules, horizons and selectors. A two-sided 5/5 binomial result is .0625. Choice of a one-sided test after observing a favorable sign is not a repair.

The exact intervals in the reproduction use the [binomial inversion method described by NIST](https://itl.nist.gov/div898/handbook/prc/section2/prc241.htm). The empirical counts and numerical calculations come from the pinned parquet and PB-D script. Their interpretation does not rely on a claim that the historical observations actually satisfy IID sampling.

## 2. Three different questions require different sample sizes

### A. Is a success probability above a known .50 baseline?

For a fixed, prespecified Bernoulli outcome with independent observations and an actually known p0=.50, the script enumerates n and the smallest critical success count k satisfying `P[X>=k | n,.50] <= .05`. It then computes power under p1 and finds the first integer n reaching the target. These are **one-sided** designs. No fitted historical edge is used.

| True success rate p1 | First n for 80% power | Critical successes | First n for 90% power | Critical successes |
|---|---:|---:|---:|---:|
| .55 | 620 | 331 | 866 | 458 |
| .60 | 158 | 90 | 213 | 119 |
| .65 | 69 | 42 | 93 | 55 |

Attained powers are approximately .801775/.900338, .805655/.902845 and .802056/.901025, respectively. Independent review reproduced the binomial tails using log-gamma enumeration rather than the script's SciPy functions. Exact-test power is locally nonmonotonic because the critical threshold changes discretely: evaluate the final locked n directly, rather than assuming every n above a first crossing has precisely the stated power.

This table does **not** justify using 158 nightly rows for a .60-versus-.50 news-quality claim. The .50 baseline may be wrong for the selected T2/sector/date population; the relevant control rate is estimated; observations may be dependent; and the principal estimand is incremental mean return. The [NIST proportion-power guidance](https://itl.nist.gov/div898/handbook/prc/section2/prc242.htm) supplies the standard design context, not a validation of this selected sample.

### B. Does one group's success rate exceed another's?

When both rates must be estimated, an approximate two-sided .05 comparison with equal independent arms requires substantially more observations. For p0=.50 and the same alternatives:

| p1 versus p0 | Approximate n per arm, 80% power | Approximate n per arm, 90% power |
|---|---:|---:|
| .55 versus .50 | 1,565 | 2,095 |
| .60 versus .50 | 388 | 519 |
| .65 versus .50 | 170 | 227 |

The calculation uses the normal approximation with pooled-null variance and separate alternative variance. It is a planning approximation, not an exact two-sample design. Matching can reduce variance when controls are informative; concentration, dependence, missingness and unequal arms can raise requirements. A hit-rate difference also does not describe loss severity. The historical generic convergence sample demonstrates why: 7/11 SPY-positive outcomes coexist with a mean SPY excess close to zero.

### C. Is the incremental mean economically useful, and is it specific to T2?

For a two-sided .05 test with 80% power, an assumed mean increment of 2 pp and known independent-observation standard deviation sigma, the basic quantity is `(z_.975 + z_.80)^2 * sigma^2 / .02^2`. For equal-variance, independent two-arm means, double that quantity per arm; for a four-cell difference of differences, multiply it by four per cell. The [standard mean-power formula](https://www.itl.nist.gov/div898/handbook/prc/section2/prc222.htm) is a planning approximation; actual event-return tails and calendar aggregation require design-specific assessment.

| Assumed SD | One-sample n | Two-arm n per arm | Four-cell interaction n per cell |
|---|---:|---:|---:|
| 3 pp | 18 | 36 | 71 |
| 5 pp | 50 | 99 | 197 |
| 8 pp | 126 | 252 | 503 |

These SDs are scenarios, **not estimates of a stable prospective event-return distribution**. No claim is made that 99 events per arm powers the actual matched calendar design. The main protocol weights dates equally; its information depends on date-level variation and temporal dependence as well as the issuer count. A paired difference has its own variance; it is not automatically the same sigma as an individual issuer return.

The within-T2 contrast is `mu[T2,Q1] − mu[T2,Q0]`. Technical specificity is the four-cell difference `(mu[T2,Q1] − mu[T2,Q0]) − (mu[T1,Q1] − mu[T1,Q0])`. They are different hypotheses. A positive within-T2 effect and a noisy/negative T1 sample do not establish a statistically reliable interaction. Four-cell requirements cannot be replaced by the one-sample column.

## 3. The prospective n-floor is an operational gate

The frozen design requires at least **200 complete first-T2 Q1/Q0 pairs: 200 distinct treated issuers and 200 distinct controls**, at least 50 complete-pair decision dates across four fixed enrollment quarters, 70% matching support, 80% primary exposure coverage and 95% complete-pair H5 outcome coverage. Enrollment lasts a fixed 252 trading sessions, with 21 more for final maturity. It does not continue until a favorable p-value appears.

These requirements establish minimum breadth and reviewable coverage. They are not a power guarantee. In the simple 5-pp-SD two-arm scenario, about 99 independent observations per arm suffice for a 2-pp mean difference; the 200-pair operational floor leaves room for some loss of precision without asserting a particular design effect. At 8-pp SD, even 200 independent observations per arm fall below the approximate 252 requirement. A rare, strict two-fresh-root quality definition may not reach 200 eligible issuers in one year. That would be a useful feasibility finding, not permission to weaken the label.

A four-cell specificity claim would need adequate counts in all four cells—roughly 197 per cell in the illustrative 5-pp-SD case before dependence—and a separately prospective inference/error-allocation plan. This cohort's T1 interaction stays descriptive even if a count threshold happens to be reached. No floor automatically promotes a research label to a signal.

## 4. Why familiar small-sample fixes are insufficient

**Issuer deduplication** prevents counting an issuer's repeated rows as separate primary trials. It does not remove market/sector/root dependence or selection of the first favorable conjunction. The prospective first-T2 rule consumes the first observation even when event quality is unknown, avoiding a later favorable replacement.

**Same-date and sector controls** address shared conditions but do not create random assignment. They may have poor support, and the published board itself is selected. Matching additional technical/entry variables can reduce support and may condition on downstream state. Historical date+sector+entry matching leaves two rows; a large mean gap in those two observations is not more convincing simply because the matching sounds stricter.

**Bootstrapping five issuers** cannot recover issuers or economic states that were never observed. A row bootstrap would reproduce the original dependence error. Conventional cluster standard errors also need adequate cluster information; few or uneven clusters can yield misleading precision. [Cameron and Miller](https://cameron.econ.ucdavis.edu/research/Cameron_Miller_JHR_2015_February.pdf) discuss these limitations, including few-cluster and multiway cases. No universal small-sample correction removes the prior model search.

**Permutation tests** are not automatically exact for observational quality labels. Exchangeability/equal-distribution assumptions differ from equality of means; ordinary label shuffling can answer the wrong null under heterogeneity. [Chung and Romano](https://arxiv.org/abs/1304.5939) explain that distinction. The prospective protocol therefore declares a calendar-block approximation and its assumptions, rather than describing observational permutations as randomized evidence.

**Several outcomes** are not several replications. SPY and sector wins share the same issuer return; H5/H10/H21 are nested cumulative paths. In exact matched same-date mean comparisons, a shared benchmark cancels algebraically. Equal fixed transaction-cost deductions also cancel in the pair mean difference. Report individual cell performance and differential execution uncertainty rather than claiming multiple confirmations of the same subtraction.

## 5. Dependence and prospective uncertainty

The primary design freezes a full 252-session calendar vector, retains the matched cross-section within each date and uses circular moving blocks of 21 sessions, with 10 and 42 as fixed sensitivity lengths. It specifies PCG64, seed, start-index sampling, truncation, active-date weighting, quantile interpolation and valid-draw gates. It never inserts zero returns for dates without pairs. Incomplete pairs remain in the missingness ledger and are not rematched after outcomes.

There are only about twelve 21-session block lengths in a 252-session cohort. Fifty active dates and 200 pairs do not guarantee that temporal variation is adequately sampled. The protocol requires all three intervals to have positive lower bounds for a research-positive result, but that is a robustness rule, not proof of nominal coverage. Persistent common shocks, event-root connections and nonstationarity can still make the approximation weak. Publish the intervals and support rather than hiding uncertainty behind a pass/fail flag.

Observed-range imputations for missing returns are prespecified stress scenarios. They are not worst-case identification bounds: unobserved returns can lie beyond observed minima/maxima. Passing the scenarios does not prove that missingness is ignorable. With inadequate exposure/outcome coverage, unstable prices or source-clock violations, the classification must remain inconclusive.

The primary outcome and four secondary endpoint family are fixed. All economic subtypes, directions, alternative technical comparisons and root/issuer sensitivities are disclosed, but no unplanned favorable subgroup can rescue a failed primary. The value of preregistration is separating questions selected before outcomes from explanations developed afterward; see [Nosek et al.](https://pmc.ncbi.nlm.nih.gov/articles/PMC5856500/). It cannot make poor measurements or an underpowered design valid by declaration.

## 6. Limitations that remain after this commission

| Limitation | Consequence and required next evidence |
|---|---|
| Historical economic/root labels absent | Cannot estimate event-quality or independence increment. Obtain exact-cut, source-backed labels through existing owners. |
| Discovery selection and unknown search breadth | Nominal historical p-values are not confirmatory. Keep this cohort out of prospective evidence. |
| Five treated issuers and overlapping windows | Wide uncertainty and shared shocks. Collect distinct issuer/event receipts across calendar regimes. |
| H10 deterioration; H21 n=1; H1 absent | Restrict the present hypothesis to H5 discovery. Measure all horizons prospectively with maturity accounting. |
| Native T2 provisional buckets and versioned anchors | Preserve emitted, truncated-time classification; a full-future replay is not the same signal. |
| Source-publication, ingestion and annotation clocks differ | Do not treat an as-of date, old-source re-fetch or later revised grade as information known at decision time. |
| Board and era selection | The current estimand is conditional on the published v3 buy board. July and other populations need separate versioned analysis. |
| Close-only historical path fields | Intraday MFE/MAE, barrier ordering and true drawdown remain unmeasured. |
| Structured human materiality judgment | Report disagreement and unknowns; do not imply a universally objective materiality threshold. |
| Hypothetical close fills and fixed cost scenarios | No executable alpha, capacity or entry permission has been shown. |

The strongest present interpretation is an interesting, selected H5 technical-context conjunction deserving a prospective audit. The strongest apparent false lead is generic convergence/“more categories always helps.” PB-G's immediate contribution should be trustworthy event/clock/root receipts and an offline evaluation path through existing owners, not a new score or production promotion.
