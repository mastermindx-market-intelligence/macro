# Q12 — When context earns a change in stock selection

Scientific result and proposed research direction · 29 September 2026

Operation `prophet-frontier-hypotheses-20260926-sol-001`; recovery `prophet-frontier-successor-1-20260928`. Scientific-design successor reporting to parent Sol. Cumulative return: Macro #6805/5861635963. Parent: #6817.

**Disposition: recommend the decision-specific identification and uncertainty framework below, and one future return × share-turnover interaction as a falsifiable Q12 candidate. Analytical results and fictional tests are complete at the stated scope; empirical validity, source feasibility, independent review, registration, and product promotion are NOT established.**

## 1. The result that matters

The useful question is not whether a context variable predicts returns. It is whether its incremental information supports a better *particular decision* than the existing alternative, after accounting for what the data cannot identify, estimation error, model error, and applicable costs.

This unit connects five statements:

1. The same observed price movement can reflect incompletely incorporated information or transitory pressure, with opposite remaining-return implications.
2. Those mechanisms can operate at different speeds. Short-horizon reversal and longer-horizon continuation need not be contradictory.
3. Even a perfect improvement in return-level forecasting can have zero value for a fixed-size, same-date shortlist if it changes no optimal selection.
4. Data adequacy and uncertainty should be assessed for the *difference between competing selections*, not by raw sample size, a generic regime badge, or uncertainty in each forecast separately.
5. Better evidence is most useful when it resolves a supported, consequential selection boundary. More rows in an irrelevant direction may contribute nothing to that decision.

These are derived applications of established probability, linear-model estimability, robust optimization, and information-matrix algebra. The project-specific contribution is their connection to one falsifiable financial mechanism and the exact Prophet research decision. No claim of global mathematical priority or discovered profitable alpha is made.

The current assignment fixes Leadership/Sector Rotation, Earnings/Expectation Revision, and Cycle Capture as economic sleeves; entry patterns, holding policy, and research horizons remain separate. This report supports that mission without modifying H1, building another evaluator, or taking native-source custody.

## 2. What the literature supports — and what it does not

**Competing explanations, not a volume slogan.** Campbell, Grossman and Wang [M1] study daily index returns and trading volume using liquidity demand and intermediary risk bearing. Their model distinguishes information-driven price changes from price pressure that changes required expected returns. Medhat and Schmeling [M2] document a different, stock-level monthly pattern: low-turnover reversal and high-turnover continuation. Their suggested information-processing interpretation is not a directly observed decomposition of every price move. Different aggregation, horizons, and conditioning prevent treating these papers as one universal volume rule.

**An adverse replication matters.** Yue, Li and Ruan [M3] reproduce the US pattern but do not find the same short-term momentum in their Chinese replication. That rejects a blanket transport assumption; it does not prove that all possible Chinese momentum constructions fail. Share turnover is a candidate measurement, not a market-invariant certificate of informed buying.

**Expected return is not automatically mispricing.** Nagel [M4] interprets reversal returns through time-varying compensation for liquidity provision. Kelly, Pruitt and Su [M5] model characteristics as instruments for changing risk loadings. These motivate a serious rival explanation: a context-conditioned signal may select risk exposure rather than exploit slow information incorporation. A forecasting gain alone cannot settle the structural mechanism.

**Neither simplicity nor sophistication wins by decree.** Kozak, Nagel and Santosh [M6] motivate economic shrinkage in a high-dimensional pricing model. Moreira and Muir [M7] find value in volatility management; Cederburg and coauthors [M8] distinguish positive spanning-regression alphas from less favorable real-time investment comparisons and highlight instability. These are different tests, not a license to ignore either result. The NBER record for Kelly, Kuznetsov, Malamud and Xu [M9], revised June 2026, reports transformer-based conditional pricing improvements. That is a legitimate high-capacity research direction, but pricing errors are not Prophet top-five net outcomes. The appropriate response is strong matched baselines and honest evaluation, not a ban on advanced models.

**Uncertainty-aware choice has an established lineage.** Goldfarb and Iyengar [M10] formulate robust portfolio selection under parameter uncertainty. Section 6 derives the relevant support function directly and applies it to incumbent-relative research selections; it does not claim to invent robust optimization or grant portfolio authority.

Access depth: official abstracts, publisher excerpts, and author-repository descriptions were reviewed for M2–M10; M1's author-hosted paper and a relevant page screenshot were also inspected. Some full-paper fetches failed. No unavailable table, coefficient, trading-cost estimate, or sample result is supplied by inference. No literature result is used as an observed Prophet result.

## 3. Economic derivation: why the same move can mean continuation or reversal

### 3.1 A deliberately small model

Condition on decision-known context z and a fixed market/strategy. Let s be centered fundamental news and u centered temporary price pressure. At the observation time, the centered log-price move is

`x = λs + u`, with `0 < λ <= 1`.

Here λ is the fraction of the news already reflected in price. By future horizon H, let a_H be the fraction of the remaining news incorporated and φ_H the fraction of the original temporary pressure still present. Define the remaining log-price change

`y_H = a_H(1−λ)s − (1−φ_H)u + η_H`.

Assume initially that s and u are conditionally uncorrelated, η_H is uncorrelated with x, and all variances are finite. The best linear prediction slope of y_H on x is

`θ_H(z) = [a_H λ(1−λ) σ_s² − (1−φ_H) σ_u²] / [λ² σ_s² + σ_u²]`.

**Derivation:** expand Cov(x,y_H) and divide by Var(x). This is a linear-projection identity. It is the exact conditional-mean slope only with further assumptions ensuring linear conditional means, such as centered jointly Gaussian innovations. A Gaussian assumption is not asserted for real equity returns.

The sign depends on the balance between unincorporated information and pressure unwinding. When the relevant coefficients are positive, continuation requires

`σ_s² / σ_u² > (1−φ_H) / [a_H λ(1−λ)]`.

At λ=1, pure information is already incorporated and creates no remaining-information slope. Pure decaying pressure instead predicts reversal. High business quality, a large price rise, or a clear historical story does not establish that information remains unpriced.

With `c = Cov(s,u | z)` nonzero, the denominator gains `2λc`, and the numerator gains `[a_H(1−λ) − (1−φ_H)λ]c`. C26 verifies these terms using exact enumerated moments. Ignoring endogeneity between news and trading pressure is a substantive assumption, not a harmless simplification.

### 3.2 Identical observed movements, opposite opportunities

Set λ=1/2, a_H=1, φ_H=0. In an information-dominated world, use `(σ_s²,σ_u²)=(3,1/4)`; in a pressure-dominated world, use `(1,3/4)`.

Both have `Var(x)=1`. Their remaining-return slopes are respectively `+1/2` and `−1/2`. With independent centered Gaussian s and u, both observed x distributions are exactly N(0,1). Identical observed price-move distributions therefore do not identify opposite latent mechanisms. C06 checks the exact variances and slopes; the Gaussian distribution equality is an analytical consequence, not a simulated empirical result.

A useful context feature must help distinguish those mechanisms or their decision-relevant consequences beyond information already in the baseline. Turnover may help empirically, but the model does not prove which direction turnover maps to λ, pressure variance, or information variance. That is precisely the falsifiable claim.

### 3.3 One mechanism, two timescales

Let `a_H=1−(9/10)^H`, `φ_H=(1/10)^H`, λ=1/2, and `(σ_s²,σ_u²)=(3,1/4)`. Pressure dissipates rapidly while information diffuses more slowly.

| Stipulated horizon H | Remaining-return slope |
|---|---:|
| 1 | −0.150000 |
| 2 | −0.105000 |
| 3 | −0.046500 |
| 4 | +0.007950 |
| 8 | +0.177150 |

The limiting slope is +1/2. C25 checks all eight finite horizons exactly. This is an existence result: one unchanged mechanism can generate early reversal followed by later continuation. It does not identify real time constants, authorize a four-session holding rule, prove a profitable pullback policy, or allow a failed tactical case to be renamed a longer-term success. Entry feasibility and path risk remain separate from expected endpoint return, as established in Q09.

## 4. A precise distinction between forecast improvement and decision improvement

### Proposition A — Information has selection value only through a consequential choice

Fix base information X, additional information Z, one finite feasible set W of equal-K selections, one universe, and the same outcome definition. Let `μ(X,Z)` be the true conditional mean vector and `μ_bar=E[μ(X,Z)|X]`. Let `w_bar` maximize `w'μ_bar` over W.

The ideal gross value of the additional information is

`V = E[max_w w'μ(X,Z) | X] − max_w w'μ_bar >= 0`.

**Proof:** the conditional chooser can always retain w_bar, so its gain is a nonnegative pointwise gap. Taking conditional expectations proves the inequality. Equality holds exactly when w_bar is also optimal for almost every Z, apart from null-probability cases. This assumes the information is correctly interpreted and free; learned-model error and acquisition costs can erase the gain.

If every score becomes `a(z)+b(z)s_i` with the same a and strictly positive b for all candidates, the ranking is unchanged. The same conclusion holds for any common strictly increasing transformation. C01 checks positive-affine invariance; C03 checks the value and equality condition in 4,374 finite worlds.

**Counterexample:** baseline scores `(3,2,1)` receive a perfectly observed common shift of +10 or −10. Adding context cuts return-level mean squared error from 100 to zero but leaves the selected name unchanged and creates zero fixed-K selection value (C02). Context can still matter for calibration, absolute risk, cash, exposure, or a different feasible set. Those are different decisions, not evidence that the stock ranker improved.

### Proposition B — Selection boundaries determine relevant precision

For one candidate interaction coefficient θ and scores `μ_i=b_i+θh_i`, a fixed selected set S is optimal for equal-K mean ranking when every selected/unselected pair satisfies

`(b_i−b_j)+θ(h_i−h_j) >= 0`, for `i in S, j not in S`,

with equality handled by the predeclared tie rule. The intersection is an interval in one dimension and a polyhedron with several coefficients. Thus some parameter uncertainty changes no decision, while uncertainty near a boundary is consequential.

For `(b_A,b_B,b_C,b_D)=(100,90,80,70)` and interaction loading only on C, the original two-name set A,B stays optimal for `θ <= 10` under the declared tie rule. Knowing θ more precisely within [5,9] has zero ideal selection value for this choice. C27 verifies the boundary over 201 integer values plus a just-over-boundary case. More generally, a top-K boundary gap strictly greater than `2ε` preserves the selected set under a coordinatewise score-error bound ε (C28).

This is not an invitation to ignore probabilistic calibration. It defines which precision matters for *this* decision and prevents spending effort on forecast precision unrelated to the claimed user benefit.

## 5. The harder gate: is the proposed comparison identifiable?

### Proposition C — Identify contrasts, not merely parameters or regimes

Within a declared linear conditional-mean model, let training design F have positive fixed weights W and information matrix `J=F'WF`. Let d be the coefficient loading of a proposed selection's mean payoff minus the baseline selection's mean payoff.

That contrast is identifiable from this design exactly when

`d is in Range(J)`, equivalently `d'v=0 for every v with Fv=0`.

**Proof:** any θ and θ+av with Fv=0 have identical fitted conditional means on every training observation. Their decision contrasts differ by `a d'v`. If d'v is nonzero, the contrast is unrestricted as a varies. Conversely, if d is orthogonal to the null space, it is a linear functional of the identified design image. This is standard estimable-function reasoning applied to the actual research decision, not causal identification.

A ridge penalty can choose a point along an unsupported direction; it cannot make that direction empirically identified. A singular design does not imply that *every* comparison is impossible: a contrast orthogonal to its null space can remain estimable. C08–C11 demonstrate both sides.

**Concrete failure:** observe only `(x,z)=(-1,-1)` and `(1,1)` with features `(1,x,z,xz)`. Every coefficient vector `(1−a,0,0,a)` fits observed means `(1,1)`. Yet the predicted contrast between `(1,-1)` and `(-1,-1)` is `−2a`. Identical training fit supports arbitrarily opposed extrapolated rankings. Twelve months in each observed context and 2,400 duplicated rows do not repair the missing contrast (C09).

The native estimability meter's per-axis coverage, state and month gates remain useful necessary screens in their declared scope. They are not a proof of independent months, overlap of exposure and context, stable identification across eras, or predictive value. Its current rules are not modified here.

### Dependence and nuisance structure

An interaction must be distinguished from own-price, context main effects, ordinary industry, coverage, and applicable era structure. Diagnose the candidate product against the joint training design, using only training information. A context constant within one era can masquerade as an era-specific slope; support across actual transitions is material. Name masking alone does not remove issuer memorization from characteristics or pre-trained representations.

Date-weighting prevents populous dates from taking more objective mass; it does not prove independence. C13 constructs four independent date shocks copied across 1,000 perfectly correlated stocks per date. Treating 4,000 rows as independent understates mean variance by a factor of 1,000. Actual dates may also be serially dependent, especially with overlapping horizons. These counts are fictional, not a new census of Prophet data.

## 6. Derivation: a defensible change should beat the same baseline under shared uncertainty

Let w0 be the existing research selection, not the user's portfolio. Use one jointly uncertain coefficient vector θ for both selections, including uncertain baseline and interaction components. Define `d=F_new'(w−w0)` and an uncertainty set

`C = { θ_hat + V^(1/2)u : ||u||_2 <= r }`.

Let c(w,w0) be the declared cost or decision hurdle, with c(w0,w0)=0. Let B(w) bound adverse model misspecification in the *same comparison*, with B(w0)=0. The following lower bound is immediate:

`L(w) = d'θ_hat − r sqrt(d'Vd) − c(w,w0) − B(w)`.

**Proof:** minimize `u'V^(1/2)d` on the radius-r Euclidean ball using Cauchy–Schwarz; the aligned opposite-direction vector attains the bound. Add the separate adverse-error allowance. If `|e_i|<=κ`, then `B(w)=κ||w−w0||_1` is exact for an unrestricted coordinatewise error box. Pure common-level error cancels for equal-total-weight selections (C23).

For the stated parameter set, choosing the largest L with w0 feasible cannot produce a negative *model-relative lower-bound objective*, because retaining w0 gives zero. This is NOT a guarantee of positive realized return, correct future parameter coverage, harmless tail risk, or a safe trade. C20 explicitly demonstrates negative absolute payoffs despite positive relative modeled improvement.

### Three requirements that prevent false reassurance

**Use joint uncertainty.** Shared errors cancel in a comparison. With mean estimates `(10,9)` and covariance shape `[[1,7/8],[7/8,1]]`, the difference has standard-deviation scale 1/2. A radius-one joint lower bound is +1/2; subtracting unrelated marginal worst cases gives −1 (C18). Conversely, ignoring uncertain baseline parameters can be falsely optimistic.

**Do not turn lack of identification into zero variance.** If the uncertainty set is unbounded along a direction that changes d, the lower bound is −infinity. A pseudoinverse or a prior must not silently set unsupported-direction uncertainty to zero. Finite prior bounds are assumptions that need disclosure.

**Separate statistical coverage from algebra.** The formula is exact for the stipulated set; it does not establish a 95% confidence region. Simultaneous coverage, dependence, adaptive model selection, parameter drift, and misspecification must be qualified. Pointwise intervals do not become simultaneous because a ranker searches many candidate changes. Under singular or nonstandard models, a suitable bounded set must be justified directly rather than automatically invoking a normal approximation.

### A decision-level example

Use the four fictional expected payoffs from Proposition B, measured in basis points, a two-name equal-weight research comparison, and a stipulated one-basis-point charge for changing the basket.

If θ has point estimate 30, replacing B with C appears to add 9 basis points after the charge. But compatible θ in [5,55] makes its lower gain −3.5 basis points; retaining A,B gives zero. Narrowing the *justified* interval to [25,35] raises the lower gain for A,C to +6.5 basis points (C19). Narrowing cannot be achieved by declaring confidence; it needs evidence or an explicitly changed assumption. This is not an observed fee, executable portfolio, risk limit, or modification of H1.

### Classification accuracy is the wrong economic hurdle

Suppose changing the selection earns +30 basis points in state A and loses 90 in state B, before a fixed cost of 5. With conditional probability p of A for this actual decision group,

`expected incremental gain = 120p−95`, so break-even requires `p>19/24`, about 79.17%.

At p=70%, the expected increment is −11 basis points. A point p=80% yields +1, but p in [60%,85%] permits gains from −23 to +7 (C15–C16). These are invented payoff states. The probability is decision-conditional, not a classifier's pooled accuracy. A model can classify regimes well yet make the wrong economic changes because the error costs are asymmetric.

## 7. Where further research and data acquisition have value

Under a fixed-design homoskedastic linear model with coefficient covariance proportional to J inverse, adding an independent design observation v with positive weight a gives

`d'J^(-1)d − d'(J+a vv')^(-1)d = a[d'J^(-1)v]^2 / [1+a v'J^(-1)v]`.

This follows by direct substitution of the rank-one inverse-update identity. It is an established information-matrix result, not a newly invented experimental-design theorem. It tells us which observation reduces uncertainty in a particular selection contrast.

With `J=diag(10000,1)` and `d=(0,1)`, another observation along `(1,0)` reduces relevant variance by zero; one along `(0,1)` halves it. C21–C24 check this and related rank/monotonicity cases. Closing one rank gap is not proof of adequate power. Under correlated observations, the relevant update is conditional information, not the naive independent-row formula.

**Research consequence:** prioritize missing *contrasts*, original information clocks, and mechanism-discriminating measurements—not just data volume. The acquisition policy must be source-blind and predeclared; this does not authorize selecting favorable realized labels, ignoring original denominators, or opening a protected store.

Partial pooling can reduce noise but is not a cure for unsupported transport. In the exact four-outcome toy model of C14, the true interaction is ±1/2 and independent estimation error ±1. Shrinking the observed estimate by 1/5 gives coefficient mean-squared error 1/5, versus 1/4 under complete pooling and 1 under no pooling. Those are coefficient-risk units, not profits. The shrinkage strength depends on assumed heterogeneity and noise; neither is known for Prophet. In particular, one country's coefficient cannot be used as a guaranteed center for another country with a different empirical pattern.

## 8. One prioritized Q12 candidate — not a list of new studies

**Hypothesis:** in the US Leadership research population, a decision-known share-turnover interaction changes the remaining-return implication of recent own-price movement beyond the same information's additive effects, and improves selection at a fixed review burden. The economic interpretation is a test of information assimilation versus pressure, with risk compensation retained as a rival—not an assertion that volume identifies either mechanism.

**Recommended future construction, subject to native binding and preregistration:**

| Element | Proposed definition and boundary |
|---|---|
| Price signal x | Log change across 21 completed native sessions using the existing accepted price/return basis; no unsupported mixing of total-return and raw-close series. |
| Context z | Mean daily raw shares traded / compatible point-in-time shares outstanding over those sessions; declared venue and share-class scope. Not dollar liquidity, an unqualified volume percentile, current shares applied backward, or automatically free-float turnover. |
| Interaction | One product of training-standardized x and a predeclared training-transformed turnover measure. Main effects retained. Missing or ambiguous source means unavailable, not zero. |
| Primary endpoint candidate | H20 native-session excess return, using an explicitly accepted benchmark and fill/mark convention. This is a future proposal, not H1's H10 and not a holding recommendation. |
| Decision | Same original supported candidate-date population; top-five fixed research workload with original one-fifth weights and a predetermined tie rule. No new-entry permission, cash policy, or variable K. |
| Baseline | Coverage-matched strong additive own-price, turnover, volatility/liquidity, and ordinary-industry model; predeclared nonlinear main effects allowed so the interaction does not merely compensate for a weak baseline. |
| Challenger | The identical information and construction plus the single x×z interaction, shrunk toward zero. No new market-regime composite or hidden expert search. |
| Main empirical comparison | Paired original-date-weighted full-selection outcome difference, with qualified costs when an executable claim is made; retain selected missingness and all original exclusions. Forecast loss, rank changes, coverage, and conditional risk exposures are separate diagnostics. |
| Transport claim | US first. China/HK/Canada require their own source/market qualification and evidence; no universal sign or pooled numerical score. |

The proposed 21-session/H20 construction is an adaptation, not a literal replication of monthly portfolio sorts. There is no claim the required historical shares-outstanding and market-volume rights are currently available. The existing native source owner must establish that. The next empirical packet must fix literal calendars, transforms, penalties, comparator flexibility, cost assumptions, formal-look rule, useful-gain tolerance, uncertainty procedure, trial budget and rejection criteria before outcomes; none is inferred from the fictional examples.

The robust lower-bound comparison in Section 6 is a **research diagnostic and potential later decision layer**, not a second simultaneously launched policy arm. It must not secretly alter the primary interaction comparison or create a new production ranker. The existing B10/B11 owners decide any later implementation and promotion.

### What would falsify the intended claims?

The interaction loses scientific priority if its apparent gain disappears against comparable additive flexibility, depends on changed coverage or later source vintages, requires unsupported price/share-class combinations, vanishes under honest date/issuer generalization, or is concentrated in an unrepeatable era. An apparent premium explained by conditional risk may remain descriptive or useful for a risk-aware claim, but does not validate slow-information mispricing. A stable nonzero coefficient that never improves relevant selections does not earn a selection-improvement claim.

A high-capacity model remains eligible for a later correctly bounded comparison when it has a reason to improve these decisions. It receives no exemption from information timing, market-specific support, strong controls, or selected-cohort evaluation. We do not infer that simple models always win from a successful toy shrinkage calculation.

## 9. Evaluation and implementation boundaries

Chronological train/calibration/test periods must be bound to the actual source manifest and purged by true label and feature support. Keep issuer-disjoint evaluation separate from future-date evaluation: they test different transfer claims. Repeated observations of one case are not independent discoveries. Scalers, industry residualization, representation learning, model selection and source imputation cannot use protected future information.

Rank/identification diagnostics use the proposed representation and declared comparison; a full-rank matrix is not proof of structural stability or causal validity. Dates, issuers and economic groups can remain dependent after algebraic residualization. Negative controls need their own justified dependence-preserving design; a random shuffle is not automatically a valid significance test. Current-only context and LLM model-vintage contamination stay separately labeled.

Existing `engine/regime_conditioning_coverage.py` was read at aeb754133a52822f6677890e0d99969610d3a1f4, blob60cc734539ac40d1c86e6d00bd2977f2b06fff9d. Its measurement-only gates are retained. `engine/seasonality/regime.py` at e8b1db3b86f9c893928447e4c228ef8d0ac2d50e, blob76dad50683b49e8e2f6adfbc2907ca0b4b83fa7f, supplies evidence of standing composite/reliability restrictions and its own exact-axis/PIT/registration admission. That biopharma module does not grant universal Prophet access. This proposal neither reopens those killed constructions nor changes their code.

| Existing owner | Owed result before a stronger claim |
|---|---|
| Data OS / native price and security owners | Compatible PIT price, shares, volume, identities, calendars, rights and original request/capture inventory; exact unavailable reasons. |
| Q12 / existing conditioning owner | One accepted interaction and scope, actual admissible support/estimability, economic rivals and registered rejection criteria. |
| B06 / Evaluation | Original outcomes and denominators, lawful access stages, fixed comparisons, dependence and selected-cohort evidence. |
| B10 / Conditional Fusion | Exact model/control representation, full uncertainty and support in relevant contrasts, reproducible admitted comparison. |
| B11 / model release and product | Only the specifically qualified forecast/ordering claim; no probability, entry, sizing or management permission inferred from a research score. |

H1 remains fixed at C2−C1/K5/H10 with its accepted eleven controls, fits, weights, missingness rules and 50/25/25 policy. Q09's joint events, original/current forecast distinction and partial-label results remain intact. Native adoption, economic #8069, Cycle #7868/#7871, Paper/Fable, and other scientific seats retain their current assignments. No protected outcome access or actual experiment was performed to prepare this report.

## 10. Executed evidence, novelty limit and disposition

Command: `python q12_exact_checks.py`, executed in an isolated conversation evidence directory. Final result: **28 named checks PASS, 0 FAIL**, Python3.13.5, standard library and exact rational arithmetic. Earlier 24- and 26-check drafts are superseded, not added together.

The checks include 4,374 finite value-of-information/equality worlds, 317 feasible ellipsoid points plus an exact minimizer, 147 information updates, a 201-value selection-boundary check, exact low-rank counterexamples, a four-point shrinkage calculation and the eight-horizon economic illustration. These are constructed mathematical cases, not independent market samples, a power analysis, a fitted model, a registered trial, or independent review. Universal claims rest on the stated proofs; finite checks only validate representative implementations and counterexamples.

| Evidence file | SHA256 |
|---|---|
| q12_exact_checks.py | 934cb736d2afd8b07bc2662693cc54f58c5e1a93ce94e30fb3cba4c94c095484 |
| Q12_EXACT_RESULTS.json | a24e9150e38aa246139777f3e4755ce2f239bb68c489eae2b24f83d403cab4ab |

**Recommended parent decision:** adopt or request a bounded repair of the Q12 analytical direction: mechanism-conditioned, horizon-specific research; decision-contrast support; selection-boundary precision; shared-uncertainty comparison. Prioritize source feasibility for the single return × turnover candidate before commissioning its separately frozen experiment. Do not commission a global regime router, relabel ranks as probabilities, or re-open H1. The empirical conclusion remains unknown.

The next scientific step is a source-bound feasibility/adversarial assessment of this specific interaction and its strongest additive/risk-exposure rivals, or interpretation of an actual H1 return when delivered. A testable analytical result is a contribution to the central mission, not completion of the empirical/build disposition owed by the assignment.

Protected procedure: Mastermind a8350c522e4ad034f69d1c5909626dbddb685605, INDEX94d1af402598894372858793a5b1931019c5fa77, Skillpack1.0.1/bootstrap1; required same-pin skills loaded. Existing science branch only. No incumbent source, new worker/watcher, financial policy, merge or deployment effect. MISSION_COMPLETE:false.

## Primary references

Sources checked 29 September 2026. Dates below identify the cited publication/version, not an exhaustive claim about the newest literature. The NBER record for M9 explicitly reports June2026; other circulating manuscript versions are not silently treated as the same artifact.

[M1] Campbell, J. Y., Grossman, S. J., and Wang, J. (1993). Trading Volume and Serial Correlation in Stock Returns. Quarterly Journal of Economics108(4),905–939. NBERw4193,1992. https://www.nber.org/papers/w4193 ; author-hosted paper https://web.mit.edu/wangj/www/pap/CampbellGrossmanWang93.pdf

[M2] Medhat, M., and Schmeling, M. (2022). Short-term Momentum. Review of Financial Studies35(3),1480–1526. https://openaccess.city.ac.uk/id/eprint/31278/ ; doi10.1093/rfs/hhab055.

[M3] Yue, T., Li, T., and Ruan, X. (2023). Does short-term momentum exist in China? Pacific-Basin Finance Journal77,101920. https://www.sciencedirect.com/science/article/pii/S0927538X22002153 ; doi10.1016/j.pacfin.2022.101920.

[M4] Nagel, S. (2012). Evaporating Liquidity. Review of Financial Studies25(7),2005–2039. NBERw17653,2011. https://www.nber.org/papers/w17653

[M5] Kelly, B. T., Pruitt, S., and Su, Y. (2019). Characteristics are covariances: A unified model of risk and return. Journal of Financial Economics134(3),501–524. https://www.sciencedirect.com/science/article/abs/pii/S0304405X19301151

[M6] Kozak, S., Nagel, S., and Santosh, S. Shrinking the Cross Section. NBERw24070,2017; published Journal of Financial Economics135(2),2020,271–292. https://www.nber.org/papers/w24070 ; doi10.1016/j.jfineco.2019.06.008.

[M7] Moreira, A., and Muir, T. (2017). Volatility-Managed Portfolios. Journal of Finance72(4),1611–1644. NBERw22208,2016. https://www.nber.org/papers/w22208

[M8] Cederburg, S., O'Doherty, M. S., Wang, F., and Yan, X. S. (2020). On the performance of volatility-managed portfolios. Journal of Financial Economics138(1),95–117. https://www.sciencedirect.com/science/article/pii/S0304405X2030132X

[M9] Kelly, B. T., Kuznetsov, B., Malamud, S., and Xu, T. A. Artificial Intelligence Asset Pricing Models. NBERw33351,January2025; NBER revision June2026. https://www.nber.org/papers/w33351

[M10] Goldfarb, D., and Iyengar, G. (2003). Robust Portfolio Selection Problems. Mathematics of Operations Research28(1),1–38. https://pubsonline.informs.org/doi/abs/10.1287/moor.28.1.1.14260
