# Risk Radar: proposed research design — execution bindings outstanding

**Date:** 17 October 2026 UTC. **Status:** proposed protocol awaiting an immutable execution packet; not an executable preregistration. Zero new fits or forecast promotions. Integrate into the existing Grey Deer programme. This document changes neither stage-1/stage-1b nor T13/T14/T19 protocols, custody or accepted results. It creates no TrialLedger or new publication/policy owner.

## 1. Evidence boundary

The completed census covers 36 ETFs and 8,486 SPY-reference dates, 1993-01-29–2026-10-15. Its dual `close` / `close_price` inputs are revised current-vintage history. At 21 sessions it contains 212,249 eligible origins, 50,100 positive 5%-loss **origins**, 1,018 recipient episodes and four pooled overlap groups. Independent episode count is unestablished. These are parent-reported census results, not newly computed here.

All scanned history and outcomes are **development/exploratory evidence**. They cannot become an untouched final test through a new split or episode definition. Preserve the stage-1b 0/12 passing-claim result. The absent `forward_log` and `BACKFILL_ASOF` / `CLOCK` refusals supply no prospective observations and must not be bypassed or relabeled.

Keep seven independent competence fields: environment, vulnerability, current damage, propagation, future loss, recovery and action policy. Evidence for one cannot authorize another. Macro context does not establish near-term loss; leadership damage does not establish transmission; a price rebound does not establish a validated entry. Existing numerical allocation/execution owners retain authority.

## 2. Endpoints proposed for the next execution packet

Let C denote the existing total-return-basis close, P the price-basis close, and h an exposure's reference-session horizon. Require valid origin and complete future support under the census's declared joint-source eligibility; retain every excluded origin and reason.

| Task | Endpoint and permitted interpretation |
|---|---|
| Current damage | Existing 63-session price drawdown D=P/max(P over the current/past 63 sessions)−1; damage D≤−5%; onset is a known false→true crossing. This is rolling-window damage, not an independent-crisis definition. |
| Further loss | Inherit T12 exactly: Y(h)=1 when min(C[t+j]/C[t], j=1…h)≤0.95, h=5,10,21; retain its original maximum-future-loss output. Primary fitted horizon is 21. |
| Preemption | Evaluate the future-loss warning among origins not already damaged. A rolling-threshold crossing is covered only if its first executable warning precedes that crossing by 1–21 reference sessions. Count late/missed crossings explicitly; persistent old warnings outside the window do not qualify. This is recall before a new rolling-threshold crossing, not prevention of an independent crisis. |
| Propagation | For an origin exposure already damaged and a recipient not damaged, predict recipient Y(21). Test incremental information over recipient-only conditions. Same-time losses remain co-damage; predictive sequencing alone is not causal contagion. |
| Stabilization | Retain the census candidate: damage within the past 21 sessions, price above SMA20 and positive five-session total return. This is an observed candidate. |
| Repair | Among stabilization candidates: a +5% total-return closing barrier is reached within 21 sessions, no −5% closing barrier occurs during all 21 sessions, and terminal C[t+21]>C[t]. Call this the **21-session repair criterion**, not a timeless bottom. |
| Defense/re-entry | Separate absolute/cash-relative wealth from performance relative to the damaged exposure. Grade actual entry paths, adverse excursion, recovery captured, failed entry, invalidation and costs; closing-barrier labels alone prove none of these. |

For the new measured-damage endpoint, a **rolling-threshold damage spell** starts at the first known crossing and clears after five consecutive known non-damaged sessions; missing sessions cannot establish clearance. Peak aging can produce this clearance. Separately bind a persistent anchored-drawdown identity through the existing lifecycle owners, and distinguish origins still underwater in that episode from repaired exposures. Rolling clearance or a new spell cannot reset anchored recovery history or authorize re-entry. Retain common-shock families separately. This is a new forward-test definition, not a revision of T12 episodes or a claim of independence. T12 recipient episodes remain post-outcome annotations. Do not relabel their future-loss origin dates as contemporaneously observed damage onsets.

## 3. Finite candidate budget

Three fitted tasks: further loss, propagation and repair, each at 21 sessions. Preemption evaluates the further-loss output on its separate risk set; acute recognition is deterministic. Five- and ten-session census/incumbent comparisons remain secondary descriptive checks, with no new fitted-horizon promotion.

Exactly four specifications per task:

1. **B0:** training-window exposure-specific empirical event frequency; unavailable without eligible training outcomes.
2. **B1:** ridge logistic using five-/20-session total returns, 63-session price drawdown, 20-session log-return standard deviation (`ddof=1`, annualized by √252) and price/SMA200 gap; propagation uses recipient fields.
3. **C1:** B1 plus one native breadth/leadership scalar and one credit/funding scalar. Propagation additionally uses the origin's five-session return and 63-session drawdown depth, not a constant “damaged” flag within an already-damaged risk set; repair uses the same native blocks.
4. **C2:** C1 plus two interactions only: damage×credit/funding and trend×breadth/leadership.

Bind native scalar IDs, formulas, constituent coverage, units, publication clocks and missingness rules to immutable existing-owner references **before execution**. An unbound/unavailable feature blocks that challenger, not B0/B1. No substitute proxy may silently take its place. Proposed propagation pairs are SMH→QQQ, QQQ→SPY, KRE→XLF and XLF→SPY; any unavailable pair remains unavailable, without substitution.

For B1/C1/C2 allow ridge penalties {0.1,1,10} after training-only standardization; B0 has no tuning. This defines **12 task/specification templates and 30 task/parameter templates**, not a total fitted-attempt count. Before execution, freeze whether estimation, penalty selection, calibration and challenger selection are pooled, exposure-specific or pair-specific; enumerate every eligible fitting unit and retain every attempt. Independently fitting 36 loss exposures, 36 repair exposures and four propagation pairs would create up to 760 unit/configuration combinations before fold refits and calibration. The executable budget must count those units, not only templates. Fold refits must also be recorded. No additional windows, feature subsets, transformations, change-point models, networks or model families enter this evaluation. A replacement needs a new prospective freeze, with old attempts retained in existing programme evidence.

## 4. Historical development and forward confirmation

**Historical nested development:** annual outer reporting blocks 2013–2026, with the final block ending 2026-10-15. For outer year y, use the preceding three complete calendar years as inner annual validation folds, each trained on all earlier available history. Respect exposure coverage; no backfilled membership. Select by mean proper loss across the inner folds, with equal exposure weights. Fit calibration only on predictions produced out of fold, and assess calibrated performance on a distinct outer fold whose labels were never used to fit the calibrator. Freeze the calibration algorithm and nesting explicitly; out-of-fold base predictions alone do not prevent calibration leakage. The outer reports remain exploratory because their outcomes were already scanned.

**Purging/embargo:** every training/calibration origin's entire outcome support must end before the next validation/test block. Apply a 21-reference-session origin purge at each boundary, plus any additional source-publication delay. If a fold permits later-side training, exclude the first 21 sessions after its validation block as well; the default expanding-window design does not use later-side training. Purging addresses overlap, not hidden common-shock independence.

**Forward holdout:** starts at the first real eligible decision strictly after immutable protocol, feature, model and calibration freezes **and** successful admission through the existing issuance owner. Calendar passage or a fabricated backfill is insufficient. Record original information availability, computation, publication, consumer visibility and first executable price timestamps; retain refusals, gaps, corrections and abstentions. Preserve original forecasts alongside any corrections. No forecast can be generated after seeing its outcome and then assigned an earlier as-of time.

Use 12-month fixed-model evaluation vintages. The first is the primary confirmatory vintage; later scheduled vintages use only outcomes mature before their freeze and remain separately reported. Monthly operational/coverage checks cannot trigger early efficacy promotion or adaptive model selection. At the fixed annual review, insufficient evidence yields NO_PROMOTION; another vintage requires a pre-outcome freeze and explicit treatment of accumulated testing.

PIT qualification requires historical membership where used, unrevised or archived source vintages, release delays and training outcomes actually knowable at each cutoff. Current-vintage reconstructions remain separately labeled even when all calculations are one-sided. The original Vulnerable Growth evaluation itself distinguishes recursive estimation from real-vintage data. [1]

## 5. Warning, cost and recovery experiment

Compare incumbent raw/gated attention, an ungated market-wide policy and an exposure-qualified lane; bind actual incumbent semantics and freeze each comparator. The SPY SMA200 component alone is not the complete Radar gate. Test recipient and systemic endpoints separately. The attention-policy and systemic-versus-exposure comparisons are **exploratory only, with no policy promotion**, until a separate execution packet binds the exact systemic target, horizon, gates, thresholds, expiry, common-availability risk set, abstentions and any additional confirmatory hypotheses/multiplicity. Equal weighting across heterogeneous ETFs is not a systemic-event definition.

**Proposed attention budget, requiring owner ratification before issuance:** primary operating point ≤10% of eligible exposure-days under warning and ≤4 new incidents/exposure-year. Coalesce uninterrupted warnings; a new incident requires five warning-free sessions. Freeze expiry, escalation and threshold selection in development. Show 5%/20% warning-day operating points descriptively; they cannot replace the primary point after results.

Report false-warning incidents/year, warning-days, toggles, preemptive episode recall, missed/late damage and executable-lead distribution. “Flag without further 5% loss” is not automatically a false alarm when damage already exists. Recognition and preemption need their own denominators. Decision-dependent timing/stability follows BIS methodology; its banking-crisis horizons are not adopted. [2]

For research-only policy comparison use one-unit exposure paths, without live sizing authority. Hold exit times fixed when comparing re-entry rules; hold exit/re-entry times fixed when comparing defensive destinations. Include hold-exposure and cash/bills comparators. Freeze eligible defensive instruments and existing policy rules before execution; no future-best destination or hindsight trough entry.

A close-only data set cannot qualify execution. Require executable prices after actual availability, admissible market sessions, observed spreads/commissions, stated slippage, gaps, cash accrual and a doubled-cost sensitivity. Report net wealth, drawdown, 21-session tail loss, missed upside, cash drag, turnover, post-entry adverse excursion and failed entries. “GAIN_FIRST” can precede later severe damage and must not be called durable repair. Rebound-related leadership reversals are a required counterexample family. [3]

## 6. Inference and promotion

For each of the three fitted tasks, choose at most one globally defined challenger specification using development data; the execution packet must say whether that specification estimates pooled or separate unit models. A collection of independently selected exposure-specific winners would be a different search and claim family. Primary statistical endpoint is the equal-exposure-weighted paired mean **Brier-loss improvement over B1** on the forward vintage; B0 remains a mandatory difficulty check. Log loss and calibration are secondary. Freeze calibration bins [0,.1), [.1,.2), [.2,.4), [.4,.6), [.6,1]; report weighted |mean probability−observed frequency|, bin support and uncertainty. Use the underlying proper loss, not optimization of a sample-dependent normalized skill ratio. [4]

Record eligible origins, positive origins, recipient episodes and independent/common-shock evidence separately. Estimate uncertainty using predeclared calendar-block resampling across the whole exposure panel; do not resample tickers as independent trials. Select block length using development dependence diagnostics, then freeze it. Episode leave-one-family sensitivity is mandatory; neither bootstrap draws nor four overlap groups establish four independent crises.

Apply Holm control at familywise 5% to exactly three predefined pooled forward superiority claims at the fixed review, provided selection occurs entirely in development under the bound estimation design. This family does not include ticker/pair-specific, systemic escalation or policy utility claims; such confirmatory claims require their own predeclared family and multiplicity treatment. Subgroups, 5/10-session outcomes, mechanisms and alternative attention budgets are exploratory; no selective promotion from a favorable slice. A pooled result does not qualify every ticker, country or theme. Economic/lead/recovery claims additionally require their own predeclared endpoints and uncertainty, not an inference from statistical forecast significance.

**Working acceptance proposals—not existing accepted thresholds:** Brier improvement ≥0.005 with multiplicity-adjusted evidence of positive improvement; fixed-bin calibration absolute error upper bound ≤0.05 where support permits; warning budget respected; positive executable lead; and positive net decision benefit with no deterioration in the policy owner's frozen loss/cost limits, including doubled-cost stress. Owners must ratify values and utility weights before issuance; absent ratification means no action-policy qualification. Do not optimize tolerances on the holdout.

Before execution, bind estimation units, ridge implementation, native features, missingness/abstention handling, comparator availability, paired risk sets, calibration algorithm/nesting, resampling method and block length, uncertainty construction, warning threshold/expiry and minimum evidence. Calculate power for the minimum useful effect under development dependence and freeze the evidence requirement. Missing policy utility/instrument/cost bindings block economic/action qualification, not already authorized descriptive work. At review, **NO_PROMOTION** applies to insufficient independent information, calibration failure, absent incremental value, missed timing, excessive burden, adverse costs, unstable common-shock sensitivity or unqualified data. Do not change episode rules to pass power. Preserve measured/descriptive capabilities regardless of failed predictive claims.

## References

[1] Adrian, Boyarchenko & Giannone, [Vulnerable Growth](https://www.newyorkfed.org/medialibrary/media/research/staff_reports/sr794.pdf), §4.1 revised-data qualification.

[2] Drehmann & Juselius, [BIS WP421](https://www.bis.org/publications/working-paper-421-evaluating-early-warning-indicators-banking-crises-satisfying-policy-requirements.pdf), decision timing, stability and error tradeoffs.

[3] Daniel & Moskowitz, [Momentum Crashes](https://www.kentdaniel.net/papers/published/jfe_16.pdf), rebound exposure and ex-ante/ex-post distinctions.

[4] Gneiting & Raftery, [Proper Scoring Rules](https://sites.stat.washington.edu/people/raftery/Research/PDF/Gneiting2007jasa.pdf), proper loss and skill-score qualifications.

Propagation must retain the assumptions and counterexamples in [Forbes–Rigobon](https://mitsloan.mit.edu/shared/ods/documents?PublicationDocumentID=5001) and [Corsetti–Pericoli–Sbracia](https://cepr.org/publications/dp3310). Correlation changes alone do not settle contagion.
