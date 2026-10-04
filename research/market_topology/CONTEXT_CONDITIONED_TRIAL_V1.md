# Price, business and macro context: conditional study v1

DESIGN LOCK BEFORE THIS STUDY'S NUMERICAL RESULTS; EXECUTION HELD ON INPUT QUALIFICATION. Not external preregistration, a production contract, accepted alpha or a Fable commission. This is a NEW research family under `market-topology-research-20260923-astra-001` / draft PR #7812. It does not replace, rescue or silently amend the earlier industry tests or the unexecuted ORDER_TRANSITION_TRIAL_V1.

## 1. Question and rationale

Primary question: after controlling for price history, contemporaneously known earnings information and specified macro interactions, do order/cohort features still improve ranking of genuinely future 20-session security returns?

Secondary questions: does operating/expectations information help beyond price-only controls; do specified context interactions help beyond additive fundamentals; and is any benefit in subsequent holding-path risk rather than return rank? These are different claims, not alternative opportunities to rename whichever result wins.

The selected current case demonstrates why this comparison matters descriptively: negative BROS, KRUS and MCD price paths coexist with different reported operating metrics. It does not establish that any combination predicts returns. Novy-Marx's earnings-momentum research (NBER w20984) motivates controlling for earnings information; Daniel and Moskowitz's Momentum Crashes (w20439, JFE 2016) motivates conditional momentum risks. Their reported historical strategy results are not acceptance of this model, and long-short momentum crashes do not imply identical long-only leader outcomes.

Primary research references: https://www.nber.org/papers/w20984 and https://www.nber.org/papers/w20439 . The NBER abstracts were reviewed; full PDFs were inaccessible in this session, so this is not a literal replication.

## 2. Data profiles and no hidden population narrowing

Profile P is the original stock trial's qualified historical S&P 500 common-share panel. It still requires correct identity, economic returns, historical industry/size/liquidity, terminal outcomes and availability. The request to existing owners is issue #7858. This new enriched study must NOT turn extra consensus requirements into a new prerequisite for running the already frozen P-versus-PT trial.

Profile E is the subset of P with all enriched fields below. Its coverage/exclusion report is mandatory for every formation date and sector. Results on E are conditional on coverage and cannot be generalized to all market securities. Report the P-model's performance on both P and E to expose selection effects, but make the enriched-model comparisons only on the SAME E observations. Financial-sector accounting differences, loss-making firms, recent listings and missing analyst coverage are disclosed strata, not quietly dropped successes/failures.

Existing earnings source contracts: `engine/group_earnings.py` at Macro `1177cf84ffa46fa3e049ebe785aa1b391e42102d` describes `group_earnings_pulse.v1`, context-only. Its latest revisions snapshot, last-four-quarter surprises and coarse guidance classifications are not automatically the historical, timestamped data required here. Consume existing owners; do not create another earnings, identity, graph or data plane.

Required enrichment records have security_id, fiscal target, accounting basis, currency, split/share basis, actual publication time, source revision and system readiness. Every analyst consensus used as an expectation predates the announcement it is compared with. Restated actuals enter only from their actual release times. A generic latest-consensus table is insufficient.

## 3. Fixed feature groups

P: all baseline numerical and industry features in ORDER_TRANSITION_TRIAL_V1, with its definition of training-only preprocessing, comparable economic returns and fixed ridge penalty.

T: exactly the original five augmented features: trailing maximum/root-mean-square drawdown, time since the latest closing peak, top-quintile membership persistence and changes in sign of relative momentum. No extra efficiency leg or renamed indicator is added to hide the negative industry result.

F: four explicitly distinct observations, not a fundamental-quality score:

F1. Most recently available quarterly diluted-EPS surprise: (reported actual minus pre-release consensus) divided by the last observed pre-announcement share price, on the SAME share/currency/accounting basis. Source actual and consensus definitions must match; non-GAAP consensus is not subtracted from GAAP actuals. Negative actual/expected EPS is allowed. A matched price normalization avoids dividing by a near-zero prior EPS.

F2. Mean change over 21 trading sessions in estimates from COMMON analysts for the SAME next unreported fiscal-year EPS target, divided by the raw formation share price on a compatible basis. Choose that fixed target at the formation anchor and look back on that same target; do not compare two different rolling 'next-year' labels. Report incumbent revisions, coverage/composition and fiscal-roll effects separately. At least three common analyst identities are required; this is a declared initial research support rule, not an optimized threshold. If contributor histories do not exist, F2 is unavailable and this full E profile cannot run as specified.

F3. Latest reported quarterly revenue divided by the comparable prior-year quarter revenue minus one. Require positive denominators, matching fiscal-quarter conventions and accounting/currency treatment. This is reported growth, not consensus surprise or constant-currency organic growth unless the source actually says so.

F4. The same-quarter year-over-year change in operating income/revenue, on matched reporting definitions. Non-comparable financial-sector or special reporting conventions are unavailable rather than forced into a corporate operating-margin identity. A distinct financial-sector profile would be a separately specified extension; no all-financial-sector performance claim follows from this E profile.

C: four predeclared interactions, with both components available at formation:
- 63-session stock momentum x prior-21-session change in the 10-year real yield;
- prior-126-session stock market beta x prior-21-session change in a specified broad US high-yield option-adjusted credit spread;
- 63-session stock momentum x market drawdown from its trailing-252-session closing high;
- F1 x prior-63-session market volatility.

Data IDs for the real yield and credit spread must resolve through the existing registry/source owners BEFORE execution. The economic series are the 10-year Treasury inflation-indexed constant-maturity yield (DFII10) and ICE BofA US High Yield Index Option-Adjusted Spread (BAMLH0A0HYM2); the vendor/redistribution and as-of conventions remain hard gates. A source substitution or maturity change requires an explicit pre-result amendment, not an implicit fallback.

Standardize each constituent using training-only statistics before taking its product; standardize resulting interactions using training-only statistics as well. Market-context training statistics weight each unique formation date once rather than repeating a market observation for every covered stock. Stock-feature preprocessing retains the original trial definition. Constant training variables contribute zero; unavailable required fields do not become zeros.

A macro value common to every security at an anchor is not, by itself, a different cross-sectional ranking: a common additive term cancels. C therefore specifies interactions, not a new macro score attached as a second independent stock-selection vote. These are observational interactions, NOT causal rate-shock estimates.

## 4. Models, primary contrast and outcomes

Estimate the same fixed ridge specification (unpenalized intercept, lambda=10 under sum-of-squares plus coefficient penalty), on identical complete E observations:

- P;
- PT;
- PF;
- PFC;
- PFCT.

Primary comparison: PFCT versus PFC on genuinely future 20-session total-return rank IC. Secondary comparisons: PF versus P; PFC versus PF; and PT versus P on E. The last is a conditional-sample diagnostic related to the original trial, not a newly untouched replication of it.

Use the original 2024 and 2025 expanding annual evaluation schedule, training only on fully matured earlier outcomes. The sample's short duration remains an initial screen, not a final regime-general result. A longer qualified dataset needs a dated extension specified before its outcome analysis. Identical holding horizons, universe formation, timing, missing-outcome and block inference rules from the original trial remain in force.

Known total losses remain -100% simple-return observations in future ranking, with tied ranks; log(0) cannot delete them. Unknown terminal outcomes prevent an unqualified full-cohort rank verdict. Subsequent maximum drawdown and time below formation wealth remain separate secondary endpoints. The original recovery/competing-event analysis is not retroactively relabelled to suit these features.

The 5- and 63-session horizons remain secondary. Any familywise significance claim across contrasts/horizons/endpoints must disclose the complete family and apply its predeclared correction. No favourable subgroup rescues a failed primary comparison. Report economic effect, uncertainty, coverage and cross-era support, not only a p-value.

## 5. Macro interpretation boundary

Jarocinski and Karadi's ECB WP2133 distinguishes policy and information components using narrow announcement-window rate/equity responses. Its US surprise window starts ten minutes before and ends twenty minutes after the event. Reading the method and rendered pages supports a crucial scope rule: a daily real-yield change is not that identified shock. Source: https://www.ecb.europa.eu/pub/pdf/scpwps/ecb.wp2133.en.pdf .

A separate causal event study would require correctly timestamped announcements, matching intraday instruments, ex-ante exposures, competing-news exclusions, and its own identification assumptions. Do not infer cause from the sign of yields, relabel C as causal, or import a later full-sample shock decomposition as information a historical forecaster knew at the time.

## 6. Economic links and neural representations

The existing time-stamped economic graph may eventually contribute supplier/customer or shared-exposure context. That is a distinct research extension, not part of this fixed v1 feature bundle. It must compare against industry/size exposure controls and degree/exposure-preserving edge placebos, using only relationships known before formation. Today's graph cannot be backfilled across history. Cohen and Frazzini's Economic Links and Predictable Returns motivates the question, not acceptance: https://doi.org/10.1111/j.1540-6261.2008.01379.x .

No neural encoder is selected by this protocol. A later encoder must be compared with the accepted deterministic representation on the same information and outcome budgets. Autoencoder reconstruction or attractive nearest neighbours do not establish forecasting skill. Future-outcome-based contrastive pairs are supervised labels and must remain entirely inside training; they cannot be called label-free.

Modern language-model background knowledge is a potential historical evaluation contaminant even when the supplied document is old. Source-bounded extraction requires reproducible fields and citations; later-known company outcomes must not enter historical descriptions. Entity/date masking controls and truly prospective frozen outputs can test the risk; they do not make an unverified historical LLM forecast point-in-time correct by assertion.

## 7. Readiness and current exposure

No PF/PFC/PFCT model has been fitted. No new earnings or macro data acquisition occurred under this protocol. The original stock trial remains held on its core input requirements, and E has additional unmet historical expectations/operating-data requirements.

Already examined: industry 2000-2025 experiments; selected September 2026 BROS/KRUS/MCD/SMH/SPY prices and operating releases. These examples inform hypotheses, so they are not pristine validation. A prospective evidence period starts only after real model/data/feature freezes and timestamped predictions exist in the current evaluation owner's system. No prospective recording process or automatic wake was started here.

Before Fable handoff, the research lead must adjudicate the actual input support, execute the admitted comparisons, preserve accepted/rejected methods, and specify exact consumer fields and authority. Implementation helpers should not be asked to discover which hypothesis was meant. A well-written protocol is not a successful experiment or completed parent mission.
