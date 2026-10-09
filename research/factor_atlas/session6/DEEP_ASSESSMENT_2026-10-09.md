# Factor Atlas S6 - deeper scientific and instrument assessment

**Decision: REVISE BEFORE EMPIRICAL FREEZE.** Preserve the measurement product, but do not activate the original ten-test proposal unchanged. This assessment found defects in S6's own validation code and scientific design, repaired the bounded software defects, and measured statistical failure modes on synthetic data. It did not evaluate new market outcomes or independently certify its own work.

## 1. Scope, source and evidence boundaries

Current commission: the Chairman requested deeper assessment after the original Session 6 report. Source carrier remains Macro draft PR #8696, `research/factor-atlas-s6-empirical-20261009`. Audited predecessor: `fbaa3812510a67e879c17defa270e16f717d3ce3`. Protected procedure: Mastermind `7d82b9adb839d54e4ab25378ca333e498dd83fcc`, skillpack 1.0.1/bootstrap 1. INDEX, COLD_START, ACTIVE_EXECUTION, SESSION_RELIABILITY, WEB_CEO_DELEGATION and CLOSEOUT were consumed at that pin. Direct work is principal scientific judgment plus bounded low-overhead verification. There was no worker dispatch, runtime or deployment action.

This is a **self-audit**, not independent acceptance. All numeric results below are either explicit mathematical examples or generated synthetic observations. Historical negative priors remain in the original `../06_EMPIRICAL_VALIDATION_AND_ACCEPTANCE.md`; they were not rerun. Existing Factor Intelligence, Trend Persistence, K3E, options and GMI ownership remains intact. No source entitlement, market cohort, scoring authority or research activation is conferred by this file.

The original guard was reconstructed from connector-returned UTF-8 and matched its exact Git blob `f7a595cf330da68276f9eb6522c2fa96bd910625`, SHA-256 `4962c6dedca08d2b4558c224125f9e5b1228c46a0535445e8acd04f9f8d72594`. This is stronger than the predecessor's whitespace-stripped comparison: whitespace is executable structure in Python. The unchanged 36-test suite also matched its Git blob. Snapshot copies in `source/` are immutable historical test targets, not new production owners.

### What this addendum revises

| Predecessor provision | Disposition |
|---|---|
| Generic 2% Brier/QLIKE loss gate | Revise exact score and materiality test; a QLIKE percentage without normalization is not invariant. |
| Month blocks plus 12-month minimum | Not sufficient by itself; test finite-sample interval coverage and label overlap across blocks. |
| 80% classified-dollar coverage | Coverage screen only, never proof that total signed direction is identified. |
| H09 requires already-qualified single features | Qualification means source/math eligibility, not mandatory standalone predictive significance; interactions may contain information. |
| All ranking/alerts treated as predictive | Separate observed-value sorting and factual change notifications from predicted-opportunity ranking or action recommendations. No feature is authorized here. |
| All scoped lanes blocked | Too broad for the previous boundary: safe evaluator repair and deeper methodological work were available. |
| Existing H1-H5, K3E and Trend Persistence freezes | Unchanged. This addendum does not reopen spent data or amend any protected registration. |

The original inactive JSON is preserved as proposal history. The existing Evaluation OS must incorporate the explicit revisions below into an accepted source-bound successor before any novel empirical result is examined. This report is not a second registration owner.

## 2. The product contains different mathematical objects

A constituent basket return, a long-short style portfolio, a regression exposure, traded notional, signed-pressure estimate, economic relationship and narrative explanation are not interchangeable factors. The comparison UI must first establish comparable units, weights, clock and source scope. A long-short factor's net weights may sum to zero; normalizing by that sum or applying long-only concentration formulas would be invalid.

For a long-only basket, declare the rebalance rule, pre-return weights, corporate-action cash treatment and total-return convention. Contribution arithmetic must reconcile to the index. A current-roster historical chart answers a different question from a contemporaneously investable PIT basket. Both may be useful, but they need different labels. A price gap must not silently reweight surviving constituents.

For portfolio risk, use the incumbent full covariance representation: variance is `w' Sigma w`, or `beta_p' F beta_p` plus residual risk. Factor contribution is `beta_p[j] * (F beta_p)[j]`, not the sum of standalone factor volatilities. Sequential orthogonalization removes sample correlation in a chosen order; it does not prove economically independent sources of evidence. Positive-semidefinite checks, residual risk, conditioning and estimation uncertainty remain separate requirements.

## 3. What estimated flow can identify

### 3.1 An identifiability limit, not an argument to abandon BVC

The same minute OHLCV can be generated by executions at an ask or a bid under different unobserved quotes. For example, 1,000 shares printing at $100 can occur with ask=$100 or bid=$100. The bar values alone cannot uniquely recover aggressor side, beneficial owner, or a fund's net subscription. A single institution can split or hedge orders; every secondary-market execution also has a buyer and seller.

If BVC is `g(X)` of a complete observed price/volume history X, then `I(Y; g(X) | X)=0`. This is a mathematical statement about source information. A compact nonlinear transform may still materially help a restricted forecasting model or human user. Accordingly, distinguish **new source information**, **useful representation**, and **useful presentation**.

A controlled demonstration used `Y=tanh(X)+noise`, not market data or actual BVC. Adding the known transform reduced held-out MSE by **52.9171%** against a weak linear baseline, but only **0.0158%** against a fixed degree-nine polynomial baseline. The transform supplied no new source. This does not establish that BVC lacks practical value; it establishes why baseline capacity and input history matter.

The literature also separates classification accuracy from information detection. Chakrabarty, Pascual and Shkilko (2015) report better equity aggressor classification using conventional rules [P1]. Easley, Lopez de Prado and O'Hara (2016), and Panayides, Shohfi and Smith (2019), examine links to information proxies [P2-P3]. These are different estimands and populations. A failure to beat a quote classifier does not logically kill a representation hypothesis; a favorable information-proxy association does not certify investor identity or a future-return edge.

### 3.2 Missing-sign bounds should replace a false reliability threshold

On an exactly matched eligible universe, let Q be classified signed notional and U the gross notional whose sign is unknown. Conditional on the classified signs being correct:

`total signed notional is in [Q-U, Q+U]`.

With $100m gross, $80m classified, Q=+$5m and U=$20m, the full signed amount can be **-$15m to +$25m**. Thus 80% coverage is consistent with either net direction. Sign is identified under these assumptions only when `abs(Q)>U`. If quoted signs are themselves uncertain, these bounds are not sufficient: add classification-error uncertainty or label only quote-proxy pressure.

The product should distinguish gross activity, classified proxy pressure, unknown notional and sign stability. If the total eligible denominator is not known, even the coverage percentage is unavailable. Similar gross amounts across two providers do not prove identical sale-condition populations. A factor-overlap sum is not total market capital: retain both per-factor exposure and a deduplicated security-minute union.

## 4. The evaluation method itself needs qualification

### 4.1 QLIKE: the proposed percentage gate can flip without a forecast change

For realized variance `y=1`, baseline forecast `fA=2`, challenger `fC=1.8`:

| Equivalent-ranking loss expression | Baseline | Challenger | Relative improvement |
|---|---:|---:|---:|
| `log(f)+y/f` | 1.19314718 | 1.14334222 | 4.1743% |
| `y/f-log(y/f)-1` | 0.19314718 | 0.14334222 | 25.7860% |
| First expression plus 10 | 11.19314718 | 11.14334222 | 0.4450% |

The paired gain is **0.0498049601** in every row, but the 2% pass/fail rule changes. A percentage is meaningful only after an exact normalization is frozen. For H06, prefer the dimensionless paired difference `log(fA/fC)+y*(1/fA-1/fC)`, with positive forecast variances and an explicit `y=0` policy; this expression remains defined at zero realized variance. Fix units, annualization, missing-data and observation-noise assumptions. Patton's research explains why the loss/proxy pairing matters [P4]; this counterexample is independently derived arithmetic, not a quoted result from that paper.

For Brier loss, a claim of at least epsilon relative improvement can test the paired quantity `(1-epsilon)*L_baseline-L_challenger`. A confidence interval excluding zero for ordinary gain plus a point estimate over the practical floor does **not** establish that the true gain exceeds the floor. Distinguish evidence for any gain from evidence for economically material gain. The actual practical margin remains a pre-freeze owner decision, not something selected after a favorable run.

### 4.2 Controlled null tests expose pseudoreplication

Protocol `prototype/synthetic_design.json` fixed a Gaussian zero-mean loss-difference panel: 252 sessions, 40 factor rows per session, 60% common component, loss scale .03, and overlapping horizons of 1, 5 and 21 sessions. There were 1,000 independent synthetic replications per horizon. These are deliberately controlled method diagnostics, not market observations or estimates of production false-positive rates.

At nominal two-sided 5% rejection:

| Synthetic horizon | Treat all 10,080 rows as IID | Cluster to dates but ignore time dependence | 12 blocks of 21 sessions, Student interval | Oracle covariance control |
|---|---:|---:|---:|---:|
| 1 | 69.7% | 5.3% | 4.6% | 5.4% |
| 5 | 86.8% | 39.8% | 7.7% | 5.4% |
| 21 | 94.5% | 66.3% | 11.4% | 5.1% |

For H=21, the 252 overlapping dates contain approximately **12.34 independent-date equivalents under this particular covariance model**, not 252 independent windows. Date grouping fixes cross-sectional duplication but does not remove forward-label overlap. Adjacent month blocks still share future returns. The oracle uses the known simulation covariance and is not an implementable production prescription.

A separately specified follow-up tested actual whole-block percentile resampling: 2,000 resamples of 12 equal 21-session blocks, 1,000 new synthetic replications, seed 2026100917. The true-zero mean was excluded **9.0%** of the time at H=1 and **15.2%** at H=21; the latter Monte Carlo 95% interval is **13.1%-17.6%**. H21 oracle and nonoverlapping-origin controls rejected 3.9% and 3.3%, respectively. Those are controls, not a search-selected winning estimator.

The follow-up approximates equal-length market months. It does not reproduce the full incumbent five-hypothesis workflow, its FDR rule, outcome distribution or effect-size gate. It therefore cannot invalidate any historical incumbent result by itself. It does refute the assumption that a monthly percentile bootstrap plus a 12-month floor is automatically adequate for S6. Cluster inference depends on independent-cluster structure and finite-cluster behavior [P5]. Multiple-testing correction cannot repair miscalibrated individual tests [P6].

**Required repair before empirical inference:** specify the exact resampling algorithm, estimand, label-overlap policy and calendar-block length using source-known structure and development data; qualify it with null and injected-effect simulations; retain cross-sectional dependence inside time blocks; use nonoverlapping origins as a prespecified sensitivity; distinguish finite-universe inference from generalization to unseen factor families. A vague instruction to cluster by date and graph is not an executable statistical method. Do not choose a block length by which one preserves significance.

### 4.3 Power is not a row-count or calendar-date promise

Illustrative normal-theory sample requirements to detect a true paired Brier gain .005 against zero at 80% power:

| Assumed independent-unit SD | Two-sided alpha .05 | One-sided first discovery in a 10-test BY family, q=.10 |
|---|---:|---:|
| .02 | 126 | 202 |
| .05 | 785 | 1,258 |
| .10 | 3,140 | 5,032 |

These are assumed effect/noise scenarios, not observed Atlas power or a time-to-launch forecast. The ten-test BY illustration uses threshold .00341417; it does not activate or change the original proposed 2+8 families. To establish a practical margin delta, power depends on the true gain **minus delta**, not merely the gain against zero. If both validation and holdout must pass, joint power is also lower than each test's separate power. Minimum 60 sessions or 12 months can be a coverage screen, never a sufficient power guarantee.

## 5. Confluence requires two opposite safeguards

**Avoid duplicated confidence.** If five engines repeat the same observation supporting probability .70, treating them as five independent likelihood updates can inflate probability to .985748. Under a true .70 event rate, expected Brier loss worsens from .21 to .291652. This is a mathematical toy illustrating double counting, not a statement about any live Mastermind probability.

**Do not forbid useful interactions.** In a balanced XOR example, each of two inputs alone has zero predictive information, yet their combination determines the outcome. Requiring every component to pass an independent univariate prediction gate would reject this useful combination. H09 should require each source to be lawful, timely and numerically qualified, not individually significant. Test a frozen joint model against the strongest baseline and frozen drop-one variants, count all attempted interactions, and measure held-out incremental utility. Feature correlation or a VIF number is a diagnostic, not a final prediction verdict.

A-E must be a **target-specific matrix**, not one staircase mixing incompatible endpoints. Options variance at five sessions, catalyst direction at 21 sessions and factor direction at five sessions are different labels. Use the same target, cutoff, eligibility and fitted budget within each comparison. A later source's broader input history must not masquerade as a better estimator of identical information.

## 6. Required hypothesis revisions before owner activation

All ten original IDs remain inactive. This table is a revision proposal, not registration or permission to inspect results.

| ID | Required discriminating revision | Falsifier or stop |
|---|---|---|
| H01 activity | Exactly 30 **scheduled** eligible RTH minutes after a fixed source-qualified landmark; missing minutes censor the window, never extend it until 30 observed bars arrive. Baselines include matched minute-of-session, activity persistence and the full raw input history. | No matched out-of-time gain; result relies on extending windows, post-bar availability or weak linear controls. |
| H02 flow-return | A five-session endpoint alone does not answer the short-horizon question. Allocate a separately declared short-horizon test or replace the primary **before** activation, counting all attempted horizons. Keep next executable entry explicit. | Gain disappears after concurrent returns, liquidity and latency controls; intraday close used before known. |
| H03 signing | Match actual eligible prints, not merely minute gross totals. Separate quote-proxy disagreement from exchange-scoped aggressor truth; report unknown-sign bounds. | Inconsistent trade support, future/stale quotes, ambiguous conditions or falsely identified full sign. |
| H04 participation | New PIT multi-theme participation transition with focal-member exclusion, fixed leader definition, prior-known roster and fresh post-freeze dates. Existing Mastermind research owner must adjudicate the Trend Persistence collision. | Mere relabeling of closed C1/B2 features; no improvement over stock/group return and volatility controls. |
| H05 resilience | Choose absolute drawdown or benchmark-relative drawdown explicitly; current wording mixes relative resilience with a fixed absolute -5% label. Retain all members, including terminal/delisted cases. | Apparent value is only lower beta, lower volatility, concentration or selective price coverage. |
| H06 options | Exact variance units and QLIKE paired-loss convention, positive forecasts, zero-realized-variance rule, OI posting/expiry/multiplier and source coverage. Signed dealer inventory excluded unless independently observed. | No gain over options-volume/OI and underlying-volatility baselines; clocks or sign assumptions supply the result. |
| H07 catalysts | Distinct release, Q&A, filing reconciliation and expectation-update landmarks, with compatible accounting basis and issuer-event identity. Later-trained models cannot be assumed historically ignorant merely because prompts contain old documents. | Future consensus, model knowledge or later graph revisions required; simple industry/momentum baseline explains result. |
| H08 propagation | Prior-known directed economic links; leave shared constituents and focal issuers out of purported independent peer evidence; compare with beta/industry/leader-shock and degree-preserving placebo links. | Co-movement, duplicated news or changing membership explains apparent transmission. |
| H09 confluence | Frozen same-target joint and reduced models; source qualification not mandatory standalone significance; baseline selection only in development. | Duplicated evidence, unmatched cohorts, hidden trial search or no incremental loss/utility gain. |
| H10 regimes | Frozen interaction and fixed regime vintages; no selection of favorable eras after outcomes; compare with the unconditional model on the identical sample. | One stress episode or retrospective regime labeling explains the effect. |

### Executable sampling and evaluation contract

A successor must bind: exact source and code digests; permitted population/listing IDs; GMI definition and weight versions; cutoff and calendar landmarks; label start/end and loss formula; fit window and retraining schedule; named numeric tuning budget; all comparison IDs; missingness and fallback; practical margin; dependence algorithm and its synthetic calibration; date partitions; holdout access and a single final decision rule. Unfilled fields are **NOT_READY**, not discretionary parameters for the next builder.

For the first source-qualified pilot, prefer a single predeclared regular-session landmark and a small fixed source cohort for **metrology**, then a separate representative-universe study for forecast claims. Four highly liquid technology names cannot establish general theme predictability. More clocks, horizons or regimes are additional searches, even when they share one notebook.

Preserve paired complete-case results but also score the **full eligible deployed policy**: on unsupported rows use a frozen incumbent fallback, or score declared abstention cost. Otherwise a challenger can appear superior merely by refusing difficult cases. Neither inverse-probability weighting nor imputation rescues nonignorable missing outcomes without additional assumptions. Print coverage, unknown outcome bounds and adverse/unpriced cohorts first.

H01 is activity prediction, not merely metrology. The owner must justify the proposed metrology/prediction family split and its aggregate discovery accounting before freeze. Do not shrink a family after missing or unfavorable outcomes. Existing locked families retain their own rules; this file does not retroactively replace their BH procedures with BY.

## 7. Instrument defects, repair and verification

Twenty-nine targeted counterexamples against the exact predecessor exposed invalid NaN, float and bool clocks; whitespace/numeric identities; impossible empty-history parameters; exceptions instead of typed refusal; empty observations becoming zero; conflicting shared corporate-action/pressure claims; rounded absolute-value comparisons; and order-dependent high-precision Decimal totals. These are selected tests across defect classes, **not 29 independent production incidents** or a measured field defect rate. All financial/publication authority flags remained false. No customer exposure was established.

The repaired S6-only guard validates exact bounded integer nanoseconds and finite Decimal representations, bounds collection size, rejects malformed identity and conflicting cutoffs/vintages, preserves null empty populations, and uses precision sufficient under explicit numeric resource limits. It retains the original public dataclasses and functions. Negative or malformed input does not acquire source rights or financial authority.

**Local verification in the isolated conversation container (not M2 or production):** all 36 unchanged original tests pass. The expanded suite passes **197 tests plus 3 subtests**. Eight independently broken code variants were all detected through semantic test failures, not syntax/import failures: clock bypass, identity truthiness, rounded absolute value, removed action/sign conflict, reduced precision, disabled future-baseline gate, equal-clock quote inclusion and enabled publication authority.

This remains a bounded research guard, not the final input adapter. It cannot authenticate caller references, prove roster completeness, reconstruct every source-specific clock, establish quote-receipt history, certify data rights, or prove supplied episode IDs independent. Native JSON names and a SHA-shaped string do not supply those facts. The Brier routine deliberately computes **no p-value, interval or promotion**. The selected mutation result is not exhaustive coverage.

## 8. Production and human acceptance without an alpha bottleneck

The previous broad no-go language should not imply that a useful information product needs a proven trading strategy. Separate four uses:

| Use | Required evidence | Does it need a predictive edge? |
|---|---|---|
| Accurate current/historical measurement and source navigation | Source/math/rights/PIT/correction acceptance; authenticated real browser and comprehensible wording | No |
| User-selected sort by observed return/breadth, or factual change notification | Correct specified event/ordering, entitlement, freshness, duplicates and correction handling; no implied future recommendation | No, but still separate product/release authority |
| Predicted opportunity rank or forecast alert | Source qualification plus registered incremental prospective evidence, calibration, coverage and independent adjudication | Yes |
| Automated position action or sizing | Additional explicit decision authority, risk/cost/execution evidence and portfolio integration | Yes, and prediction alone is insufficient |

No such release or alert is activated here. This is a proposed clarification of the acceptance rubric, not a permission bypass.

The human study must ask whether investors understand **more useful things**, not merely remember a disclaimer. Use matched tasks such as identifying whether a move is broad or megacap-led, resolving overlapping themes, distinguishing historical from current evidence, explaining contradictory pressure and navigating the correct issuer. Compare baseline UI and Atlas using identical source information to isolate presentation value; separately test added-source information under the same UI. Randomize/counterbalance order and score answers blind to condition. Report time, correctness, provenance recall, incorrect causal attribution and confidence calibration. Several tasks from one user are clustered, not independent participants.

Thirty independent users making zero critical interpretation errors still permit a true error rate as high as **9.50%** at a one-sided 95% bound. At n=60 the bound is 4.87%; n=300 gives 0.99%. These are binomial calculations, not participant results or a mandate to recruit a fixed N. A small formative study can reveal usability failures but cannot establish an extremely low failure rate. Recruiting or collecting customer data remains outside this session's effects.

The original real-path matrix remains required: authenticated discovery, exact factor/detail reconciliation, two-factor comparability, correct stock identity/deep links, replay/current separation, missing/conflicting evidence, entitlements/export boundaries, user saves, correction/freshness, desktop/mobile, realistic population load and evidence-preserving rollback. Bind each receipt to source head, deployed release, real account scope, source generation and browser environment. Merge, component tests, fixture browser, production browser and independent acceptance remain different evidence classes.

## 9. Feature decisions and next actions

**Continue** numerical factor measurement, breadth/concentration explanations, activity magnitude, bounded pressure visualization and investor research workflow. **Revise** the S6 instrument and proposed experimental design as above. **Hold** all new empirical forecast claims until exact sources and owner-accepted registration exist. **Stop** claims that BVC uniquely identifies institutional buying, quote signing proves dealer inventory, shared observations are independent confirmations, or old negative results may be reset under a new name.

Historical nulls narrow constructions, not the entire scientific possibility space. In particular, closed Trend Persistence C1/B2 prevents cloning its hypothesis or reusing its spent formation dates; it does not establish a theorem that every properly specified PIT economic group feature is useless. A genuine new construction needs the existing owner's fresh protected preregistration and new data. Similarly, weak bar-only options signing is not a measured rejection of all equity BVC forecasting or all magnitude-based options context.

**Immediate next validation action:** independent reviewer examines the exact S6 repaired source and these counterexamples, then the existing Evaluation OS incorporates the revised loss, sampling, dependence, full-coverage and trial-budget contract into one source-bound accepted specification. In parallel, original data/price/GMI/options owners may supply their already-owned admitted cohorts; S6 adds no collector or admission service. Only an actual positive source decision unlocks real tape replay. The first market pilot is metrology/coverage, followed by the preregistered target-specific incremental tests when sufficient honest information accrues.

The deeper assessment is delivered with falsifiable findings and executable synthetic evidence. The parent market-prediction and customer acceptance mission remains **incomplete**. Independent scientific review, source admission, prospective performance and authenticated production/human acceptance are not claimed. No background execution, new account, source denial bypass, held-out data use, merge or deployment occurred.

## 10. Primary-source context and reproducibility

Only the following bounded literature claims are used; abstracts/author records or publisher previews were inspected, not full unpublished methods or underlying datasets:

- **[P1]** Chakrabarty, Pascual and Shkilko (2015), *Evaluating trade classification algorithms*, Journal of Financial Markets 25, 52-79. DOI `10.1016/j.finmar.2015.06.001`. Publisher abstract: https://www.sciencedirect.com/science/article/abs/pii/S1386418115000415 . Aggressor classification comparison, not Atlas market evidence.
- **[P2]** Easley, Lopez de Prado and O'Hara (2016), *Discerning information from trade data*, Journal of Financial Economics 120, 269-285. DOI `10.1016/j.jfineco.2016.01.018`. Publisher preview: https://www.sciencedirect.com/science/article/abs/pii/S0304405X16000246 ; author publication record: https://quantresearch.org/Publications.htm . Information detection and trade-side classification are distinct.
- **[P3]** Panayides, Shohfi and Smith (2019), *Bulk Volume Classification and Information Detection*, Journal of Banking & Finance 103, 113-129. Author abstract: https://papers.ssrn.com/abstract%3D2503628 . Study-specific informed-trading proxies are not beneficial-owner truth.
- **[P4]** Patton (2011), *Volatility forecast comparison using imperfect volatility proxies*, Journal of Econometrics 160, 246-256. DOI `10.1016/j.jeconom.2010.03.034`. Author institution: https://scholars.duke.edu/publication/792433 . Proxy noise can affect forecast comparisons; no claim that the paper supplies this session's numeric example.
- **[P5]** Cameron and Miller (2015), *A Practitioner's Guide to Cluster-Robust Inference*, Journal of Human Resources 50, 317-372. Journal abstract: https://doi.org/10.3368/jhr.50.2.317 . Dependence and few clusters affect precision.
- **[P6]** Benjamini and Yekutieli (2001), *The control of the false discovery rate in multiple testing under dependency*, Annals of Statistics 29, 1165-1188. DOI `10.1214/aos/1013699998`. Author institution: https://cris.tau.ac.il/en/publications/the-control-of-the-false-discovery-rate-in-multiple-testing-under/ . Dependency assumptions matter; changing correction does not repair invalid p-values.

Software source hashes, exact synthetic specifications and measured outputs are in `evidence/DEEP_AUDIT_RECEIPT.json`. The Python files are research-only and execute no market or network request. Detailed raw test/counterexample outputs are included in the conversation proof package; they can be regenerated from the committed source snapshots and scripts. Use `README_DEEP_AUDIT.md` for exact commands. No numerical hypothesis result in this addendum is based on a protected market holdout.
