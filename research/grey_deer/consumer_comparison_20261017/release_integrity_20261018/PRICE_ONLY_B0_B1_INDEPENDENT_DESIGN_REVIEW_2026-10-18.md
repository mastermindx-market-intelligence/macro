# Independent review of the proposed price-only B0/B1 design — 18 October 2026

Reviewer: `/root/forward_activation_review`, independently assigned by Sol; not the amendment's author. Intended repository location: `research/grey_deer/consumer_comparison_20261017/release_integrity_20261018/PRICE_ONLY_B0_B1_INDEPENDENT_DESIGN_REVIEW_2026-10-18.md`.

**Disposition: accept the bounded mathematical core as a proposed development design; make the single reporting-weight clarification R1 below before adopting it as a fully specified evaluation contract.** I found no material defect in the stated date purge, common-support comparison, equal-exposure training objectives or 532-unit ceiling. Annual and damage-stratum calibration weighting is not yet uniquely specified. R1 changes deterministic reporting definitions, not the estimator, fit budget, programme, trial registry or admission gates.

**UNKNOWN / NOT_ADMITTED and zero actual fits remain unchanged.** This review neither reinterprets source rights nor supplies an estimator/runtime admission. No efficacy, live probability, warning, policy or release acceptance follows.

## Evidence and review scope

| Reference | Exact cloud copy read | Bytes | SHA256 |
|---|---|---:|---|
| A | [Proposed amendment](../../all_date_census/PRICE_ONLY_B0_B1_ADMISSION_AMENDMENT_2026-10-18.md), local `research_notes/all_date_census/PRICE_ONLY_B0_B1_ADMISSION_AMENDMENT_2026-10-18.md` | 24,836 | `687bfed7c3cae90b350c7fd33f5301dc9c33bd09596553566790d131f77ebd67` |
| S | Executed census source, local `research_notes/all_date_census/admission_source/grey_deer_exposure_census.py`; logical source `scripts/research/grey_deer_exposure_census.py` at `4a06cd4a6b323312d2a59d6130efdb60997fe149` | 19,930 | `d6240027cd15fadfec4511a3be42203dba6df87095bd65b50a049394abf6abce` |
| P | [Prior proposed research protocol](../../risk_radar_research_protocol_20261017.md), local frozen copy `research_notes/all_date_census/admission_source/risk_radar_research_protocol_20261017.md` | 21,078 | `8ae117d52ac575f1d281f8c015137efac84da7c441b3ac9933c75ae2b3acc463` |

I read A in full and the relevant source/protocol sections. Source references below are exact line locations in these hashed copies. Only local document/source reads and standard-library identity/text operations occurred. I did not open price or origin rows, run a model, compute features, execute tests, import first-party source, use a native tool/network/provider, or edit A. The numerical examples below are hypothetical arithmetic counterexamples, not empirical results. This review does not independently reverify the stored label vector or the delegated T12 label implementation.

## 1. Accepted mathematical and population protections

### Date purge and common support

For the first reference index `b` of a test year, `i + 21 < b` is the correct strict boundary under the stated origin-through-endpoint label support. An origin at `b-21` ends at `b` and must be excluded; one at `b-22` ends at `b-1` and may be used if otherwise eligible. Exactly the last 21 pre-block origins are purged. There is no later-side training in this design, so an additional later-side embargo is not needed to implement this rule. Feature lookbacks overlapping earlier training dates are permitted past information; they do not by themselves require another label purge. These facts do not repair unknown historical publication delays or revised source vintages. [A:49–53; S:`future_labels`,92–110; P:54–62.]

The paired comparison correctly restricts all three predictions to the same feature-complete training/scoring support, while retaining label-eligible attrition and non-scored rows. B0 therefore answers the same conditional sample question as B1; it is not being credited with a broader or easier scoring population. An exposure with no supported exposure-B0 estimate cannot enter a three-model comparison through pooled extrapolation. A failed pooled fit can leave a year without common scores; the retained refusal/count tables are essential to prevent that subset from being described as complete-universe performance. No removal or replacement of such failures is authorized. [A:47–53,71–77,91,98–102.]

This support remains a revised-history, complete-case population. Requiring valid future support can condition scoring on eventual source availability. The design appropriately retains those exclusions and does not claim to recreate what was available at the historical decision time. Source code confirms the stricter dual-basis future-support rule: `origin_states` requires both price bases valid, and `future_labels` uses those states throughout the origin-to-endpoint window. [S:79–110; A:31,49,106.]

### B0, pooled constant and B1

For supported exposure `e`, let `n_e` be its common training count and `p_e` its empirical event rate. The B1 weights `w_i = 1/(m n_e)` sum to one and give each supported exposure total mass `1/m`. Consequently:

`sum_i w_i y_i = (1/m) * sum_e p_e = p_pool`.

With every slope zero, the weighted logistic objective is `softplus(a) - p_pool*a`. Its intercept derivative is `sigmoid(a) - p_pool`. Thus the specified pooled B0 is exactly the intercept-only optimum for the same weighted training population when both classes occur. This supplies the appropriate constant comparator for the added feature specification. Exposure B0 remains non-nested with the pooled model, as A explicitly states. Improvement against one comparator cannot replace the other. [A:73–87.]

The objective fixes the normalization and ridge penalty: weighted mean logistic loss plus `0.5*sum(beta_j^2)`, with an unpenalized intercept. A library's unspecified `C=1` is not interchangeable with that definition. Training uses log loss while evaluation uses Brier loss; no theorem here promises a Brier improvement, especially out of sample. A zero-feature pooled model can lose to exposure B0 simply because persistent exposure frequencies differ. Conversely, a feature model can beat the pooled constant by recognizing persistent exposure differences without timing a turning point. The proposed interpretation boundary already handles both cases. [A:79–87,102,106.]

### Transforms, precision and convergence

Training-only, equal-exposure weighted means and population variances are consistent with the fitted loss. Preserving a constant column with scale one avoids undisclosed feature selection. The volatility construction correctly needs 20 saved one-session log returns covering 21 underlying closes; computing on the complete reference lattice before filtering prevents compression across missing sessions or fold boundaries. Saved eight-significant-digit values and the full-precision saved damage Boolean are correctly distinguished. [A:59–77; S:`strict_return`,40–42; `observed_features`,45–58; `write_csv_gz`,368–372.]

With positive row weights, both outcome classes and positive ridge on every slope, the stated mathematical problem has a finite unique solution. Ridge controls the slopes; the two classes prevent an unpenalized intercept from escaping to infinity. With only zero outcomes, for example, the loss approaches its infimum as the intercept tends to minus infinity, so a finite maximum-likelihood intercept does not exist. The B1 refusal is therefore justified while zero-event exposure-B0 and pooled-B0 probabilities remain valid. [A:73–85.]

The optimizer, stable logistic-loss/probability evaluation, initialization, convergence criterion, tolerance, iteration cap and runtime are still to be pinned before a first fit. A library success flag alone would not prove conformity to this objective. That is part of the amendment's already stated executable/runtime dependency, not a new methodology gate introduced by this review. Do not silently rescue non-convergence with another solver, regularization, clipping-based pseudo-solution or retry. [A:83–85,112.]

### Finite units

The count is correct: `36*14 + 14 + 14 = 532` planned units, comprising 504 exposure-frequency estimates, 14 pooled constants and 14 optimized pooled fits. Counting the derived pooled constant is conservative and explicit. Preflight refusal, attempted failure and successful estimation are different dispositions; a refusal does not become an executed fit, and an interrupted attempt cannot disappear. Report strata and fixed-bin summaries add no new fitted model. The earlier 518-unit recommendation remains superseded planning history. [A:11,91–99.]

## 2. R1 — bind reporting weights and calibration aggregation

**Material ambiguity:** A:102 precisely defines the overall Brier average, but A:100–104 does not fully define how that weighting transfers to each annual/damage report population and its calibration bins. In particular, an implementation could retain overall row weights inside a damage subset and normalize them, or re-equalize exposure weights inside that subset. It could also calculate unweighted within-bin means and apply weights only to bin mass. These yield different summaries with identical predictions and no extra fit. Merely requesting raw counts, weight mass and a “weighted absolute bin error” does not uniquely resolve the choices.

**Concrete counterexample:** one exposure contributes 100 scored origins with `p=.09, y=0`; a second contributes one origin with `p=.09, y=1`. All predictions occupy the same `[0,.1)` bin. The raw-origin event frequency is `1/101`, giving absolute bin error about `0.08010`. Equal exposure mass gives event frequency `0.5`, giving error `0.41`. A table can display the same 101 raw origins and two exposures while reporting either answer if its within-bin weighting is not fixed.

**Smallest compatible amendment:** append explicit formulas to the existing reporting section; no estimator or new reporting family is needed. One consistent choice is:

1. For each already-required reporting population `G`—overall, a declared year, or a declared damage stratum—use only common-scored rows. Let `E_G` be exposures with at least one such row and `n[e,G]` their counts. Set evaluation weight `q_i = 1/(|E_G| * n[e,G])` for a row of exposure `e`. The same `G` and row weights apply to all three models. Empty populations have unavailable metrics, not zero error.
2. Define `Brier(model,G) = sum_i q_i*(p_i-y_i)^2` and each paired improvement as the difference of these losses. This reproduces A:102 for the overall population and makes the other declared populations deterministic.
3. For a model's fixed bin `k`, define mass `M_k = sum_{i in bin k} q_i`, `pbar_k = sum(q_i*p_i)/M_k` and `ybar_k = sum(q_i*y_i)/M_k`. Report absolute bin error `abs(pbar_k-ybar_k)` and weighted contribution `M_k*abs(pbar_k-ybar_k)` separately. Raw origins, raw positives and exposure counts remain separate counts. If a total weighted-bin error is reported, it is the sum of those contributions. Empty bins retain null means/errors and zero mass; they are not evidence of calibration.
4. State that weights are re-equalized within each declared reporting population under this choice. Annual or damage panels therefore need not recombine into the overall score by their raw row counts; differences between strata can reflect their exposure/date composition. Freeze the exact already-required panel list with the runner. Do not choose alternative weighting after seeing results.

Keeping the overall weights and conditionally normalizing them for strata is also a coherent estimand, but it answers a different question and would need equally explicit formulas. The amendment should select one. This review recommends the equal-exposure-per-report-population version above because it directly extends the stated overall convention. R1 does not add fits, inference, eligibility thresholds or another approval owner.

## 3. Counterexamples and limits to preserve in interpretation

**Raw-origin dependence remains substantial by construction.** A single sharp fall after a flat period can make many adjacent 21-session origins positive, and correlated proxies can repeat the same market event across exposures. Annual blocks, strict purging and equal exposure weights do not convert those rows into independent trials. Retaining `independent_episode_count = null`, omitting significance/confidence/power claims and preserving the four overlap groups without calling them independent crises is appropriate. [A:33,104; P:80.]

**Marginal bin agreement is weaker than conditional calibration.** Hypothetically, a constant prediction of `0.1` across two equally sized origin groups with event fractions `0.2` and `0` has perfect pooled bin agreement. It is wrong for each group's conditional frequency. A favorable coarse-bin table therefore cannot qualify every exposure, damage state, recent year or operating threshold. Brier and the unfavorable cells must remain visible, and there is no precise calibration grade or fitted calibrator in this slice. [A:100–106.]

**“Undamaged” is the saved rolling-window state, not recovery from an anchored loss.** If a price falls from 100 to 80 and then stays near 80 long enough for the older peak to leave the 63-session window, the rolling drawdown can become zero while the exposure remains 20% below the old peak. The saved Boolean can correctly be false without an economic repair. Preserve its original full-precision classification; do not relabel rounded drawdowns or interpret this stratum as demonstrated preemptive warning or re-entry. A already discloses peak expiry and excludes those claims. [A:9,55,106; S:53–61; P:19–27.]

**A favorable comparison would remain development evidence.** The history was already scanned, the archive is revised rather than a historical publication record, common support can omit difficult/unavailable periods, and no executable price, threshold, warning expiry, cost or publication/consumer clock is evaluated. Lower origin-level Brier error can be useful diagnostic evidence but cannot establish early warning, contagion, capital preservation, defensive rotation or recovery capture. Heterogeneous equal-weight ETF proxies do not define a systemic event or broad country/company competence. [A:9,31,45–55,87,102–106; P:9,62,66.]

## 4. Bounded disposition and next dependency

Retain the proposed five-feature pooled estimator, both baselines, strict annual purge, common-support rules, fixed 532-unit ceiling and failure preservation. Clarify R1 in the existing amendment before treating reporting as completely frozen. The deterministic optimizer/runtime specification remains the already acknowledged later executable dependency; its implementation would still require independent source verification under the existing owner.

The recorded source-purpose **UNKNOWN / NOT_ADMITTED** is unaffected and remains the first stated execution blocker. No rights conclusion, empirical estimation, additional trial, provider acquisition or policy promotion occurred. This independent review accepts mathematical coherence subject to R1; it supplies **no efficacy result** and authorizes **zero real fits**.
