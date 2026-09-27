# Analogue support and shrinkage: research trial v1

NEW RESEARCH DESIGN; NO EMPIRICAL MARKET RESULT UNDER THIS PROTOCOL. Operation `market-topology-research-20260923-astra-001`, draft PR #7812. This does not replace or rehabilitate the completed negative analogue trial. The 2000-2025 sample has already been inspected; reuse is exploratory development, not an untouched confirmatory holdout. No forecasting authority or Fable commission is created.

## 1. The actual question

Can a fixed rule that declines weak historical matches and shrinks noisy analogue forecasts toward an unconditional baseline improve on that baseline across the SAME complete set of queries?

The test must not confuse a lower error on easy covered queries with a better overall method. It must also distinguish refusing to make a context match, declining an analogue increment, and serving a separately accepted forecast. The current production analogue owner is context-only; this research cannot grant it a probability output by changing terminology.

## 2. Preserve the original source and representations

The base empirical design is `INDUSTRY_ANALOGUE_TRIAL_V1.md`: the exact archived French 49-industry dataset, 252-session feature histories, candidate s satisfying s+20 < t-252, K=20, 126-session separation, ten conventional features and eight added fields with the same weights and standardization. No feature search, new horizon, favourable era selection or K tuning is introduced here. Both representations are separate profiles with distinct calibration histories; their distance scales cannot be pooled.

The baseline b(t) is the mean of all causally eligible candidate outcomes. The raw analogue a(t) is the same mean of the selected 20 historical outcomes. The primary target is the fraction of 49 industries with genuinely positive NEXT-20-session performance. Source date, actual availability, predictor time and outcome-maturity time remain distinct. Current-vintage historical research must be labelled as such.

For retrospective exploratory development, build prequential forecasts from the first anchor at which the original technical matching rules can be satisfied, with the original candidate history starting in January 1980. At each historical query, generate that query's baseline, raw analogue and nearest RMS distance using only its then-eligible history. Do not fit a current model once and call its predictions for earlier dates prequential. Store actual original source/profile/query identity, issue time and outcome availability.

A query without the original complete feature/target requirements is a reported input exclusion, not a support-rule success. A query with no K=20 set receives an explicit technical-match refusal. Do not relax separation or impute missing features to recover coverage.

## 3. Fixed past-only support rule

The rule requires at least 60 UNIQUE earlier technically valid prequential queries for the SAME representation whose outcomes became available STRICTLY before the current decision. Queries with outcomes arriving exactly at the cutoff are conservatively not included. No future query's distance or target participates in this v1 calibration, even though a more elaborate unsupervised-distance design could use some unmatched distances; that is not this protocol.

Let d(t) be the nearest-neighbour RMS standardized distance under the current profile. Let q95(t) be the linearly interpolated 95th percentile of those earlier query distances, at index (n-1)*0.95 in the sorted sample. Support is accepted only when d(t) <= q95(t). Equality is accepted. Before n=60, the rule is cold and contributes no analogue increment. Invalid distance, a missing profile or a technical-match failure is an explicit refusal.

This is a fixed heuristic novelty screen, NOT a calibrated confidence level, a claim that a historical state is economically equivalent, or proof of adequate regime diversity. Sixty monthly observations are not sixty independent regimes. The values 60 and 95% are declared research choices, not thresholds selected from the new results. Report distance distributions, feature mismatches, era concentration and coverage; do not rename the 95th distance percentile as a 95% forecast interval.

## 4. Fixed shrinkage rule

For every eligible past prequential query j, define delta(j)=a(j)-b(j) and error(j)=y(j)-b(j). Use ALL eligible earlier technically valid raw analogue forecasts, including cold-start/support-refused queries whose raw forecasts were nevertheless actually fixed before their outcomes. This avoids a self-starting policy that can never acquire calibration observations because it refused its first forecasts. It does not permit post-outcome prediction reconstruction.

Let S=sum(delta(j)^2), C=sum(error(j)*delta(j)), n=number of eligible queries. Define:

  alpha(t) = clip(C / [S*(1+20/n)], 0, 1).

If S=0, alpha=0. The 20 pseudo-query penalty is fixed in this v1, not selected after outcomes. If fewer than 60 observations exist, alpha used is zero. If the current match fails the support rule, alpha used is also zero even when a fitted alpha is available. Otherwise:

  forecast(t) = b(t) + alpha(t)*(a(t)-b(t)).

Because b and a are participation fractions and alpha lies in [0,1], the result remains a fraction. This does not make it a calibrated probability. The model predicts a population share, not the probability that a particular security wins.

Exact finite-sample squared-error identity, for a fixed alpha evaluated on a declared sample:

  MSE(b)-MSE(b+alpha*delta)
    = 2*alpha*mean((y-b)*delta) - alpha^2*mean(delta^2).

An analogue increment must align with errors left by the baseline; merely varying more or sounding more contextually detailed is not skill. Estimating the coefficient on evaluation outcomes would be leakage. The rule above uses earlier matured predictions only and is still not guaranteed to improve future results.

## 5. Comparisons and honest coverage accounting

Compare, on identical query/outcome support:

1. Baseline only.
2. Original forced raw analogue where technically available, with baseline fallback otherwise.
3. Shrinkage only, ignoring the distance-refusal rule but retaining cold-start and technical-match rules.
4. Support plus shrinkage, the primary new candidate.

Run the conventional and augmented profiles separately. The primary contrast is the augmented support-plus-shrinkage policy versus the baseline across ALL admitted queries. The conventional profile and other variants are secondary diagnostics, not replacements for a failed primary result. Report cold, technical-no-match, distance-refused, zero-alpha and positive-alpha counts separately.

On the supported subset, compare candidate and baseline ON THAT SAME SUBSET. Also evaluate the whole fallback policy over all admitted queries, including refused dates. Do not compare the candidate's favourable covered cases with the baseline's harder full universe, and do not drop crashes because the new rule declined them.

A completed synthetic counterexample establishes why: outcomes [0,0,1,1], baseline [0,0,0.5,0.5], candidate [0.1,0.1,missing,missing]. The candidate has MSE 0.01 on its two covered queries, apparently better than the baseline's full-sample 0.125. But baseline MSE on the SAME covered queries is 0, and candidate-plus-baseline-fallback full-sample MSE is 0.13, worse than 0.125. Coverage is 50%. This is a mathematical counterexample, not a market result.

A fallback used for research comparison is not permission for an unaccepted product to serve a forecast. The real product may remain context-only/no-forecast even when the harness records a baseline prediction.

## 6. Inference, calibration and prospective limits

For an exploratory rerun on the already viewed historical period, report every admitted date, per-query predictions, all four policies, coverage and paired MSE/MAE differences. Use the original 12-month circular block-bootstrap convention with 5,000 draws and a new recorded seed 2026092308. Disclose approximate dependence handling, small effective regime count and all secondary profiles/targets. No corrected p-value can undo the fact that this sample influenced the new design.

Secondary outcomes may include future industry dispersion and proxy volatility, but their scale and calibration are separate. The fraction-valued reference implementation does not pretend to handle those unbounded targets. A target-specific implementation is needed before they run, not a silent reuse of [0,1] checks.

Historical neighbour quantiles remain descriptive. Any prediction interval must be calibrated from genuinely earlier prequential residuals and evaluated on later data for width and empirical coverage, including market regimes and missingness. This v1 supplies no distribution-free coverage guarantee under market dependence or shifts. A distance percentile is not a residual quantile, and neither is causal similarity.

Confirmatory evidence requires a newly frozen, actually timestamped prospective output path or an honestly unexposed validation source/time block. Selected September 2026 case observations and the prior 2000-2025 studies are exposed. No automatic prediction recorder, watcher or future evaluation process was started here. The existing research/evaluation owner must record predictions before outcomes before prospective accrual can be claimed.

## 7. Executable semantic evidence, not market validation

`selection_and_shrinkage_checks_v1.py` already verified the above selection example and the exact shrinkage identity on 1,000 random synthetic samples, max arithmetic error 1.39e-16. Script SHA256: 7eb94b9819f2d698c494c8885d20f40f56cc936d5eecb85d7b5ed7030754fa0e. Result SHA256: 278801a2b5f045f4e9a3a6893d7851c1d678dff9b5552695ad9a78e0f3c7efe8.

A separate pure reference and 20 unit tests were then executed locally: `selective_analogue_reference_v1.py` and `test_selective_analogue_reference_v1.py`. They test exact cold-start support, future/maturing-record exclusion, profile segregation, duplicate query refusal, shrinkage limits, past-distance refusal, missing forecasts and full-policy evaluation. All 20 passed. They use synthetic inputs only and create no production reader, identity, store or forecast authority.

These reference tests settle semantics for the later builder. They do not demonstrate that support/shrinkage improves the failed historical model. The empirical protocol remains unexecuted pending access to the existing causal feature/prediction artifacts in a lawful research execution path. No blocked R2 request, remote source refresh or provider credential operation was repeated.
