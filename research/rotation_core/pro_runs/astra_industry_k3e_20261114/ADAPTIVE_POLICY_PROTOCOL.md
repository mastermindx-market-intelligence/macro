# Adaptive follow-up: context as protection around industry momentum

Status: ADAPTIVE EXPLORATORY, not untouched confirmation. The original fixed model experiment has been read and remains unchanged in BASELINE_RESULTS.json (SHA256 72eea568180075f75276af078a831af51331be8d69853ea8188a0e56468d5f92). No new model, feature, threshold grid, fitting window or post-2002 outcome will be selected by this follow-up.

Motivation: the context model reduced selected downside relative to price-only, but did not beat the fixed126-session industry momentum ranking. Test the narrower hypothesis that momentum is a useful ranking backbone while probabilistic context is a risk filter. Distinguish information value from merely avoiding high volatility.

## Fixed policies before reading their results

Use the exact existing out-of-time prediction rows from the a93214df184d29001470a1fcc1f7575314fe0188 experiment. Selection may read only industry, decision_date, relative126, vol63, state and already-out-of-time predicted risk/return; never outcomes. For each month, let k=ceil(20% of eligible industries) and pool size=ceil(40%). All policies select exactly k; ties by industry identity.

1. Baseline: top k by relative126.
2. Momentum + price risk: take top40% by relative126, then lowest predicted bad_loss from the price-only model until k.
3. Momentum + context risk: same pool, then lowest context-model predicted bad_loss until k.
4. Momentum + low volatility comparator: same pool, then lowest trailing vol63 until k. This tests whether a sophisticated model adds beyond a cheap risk characteristic.
5. Momentum + expected relative payoff: same pool, then highest contextual ridge expected_excess_net until k.

Primary comparison: policy3 versus baseline1 on bad_loss and net63. Secondary comparators:3 versus2 and4;5 versus1. Print every policy, equal selection counts/coverage, all paired12-month block intervals (1000 resamples, seed20261114), all folds and state composition. No selecting a best policy and calling it validated. Additional five-policy family is disclosed alongside the original three fitted specifications.

Separate reversal question: within the observed reversal_attempt population only, compare equal-weight all candidates with selecting the better half by each of contextual expected excess, contextual bad-loss probability and price-only bad-loss probability. This is a secondary, adaptive study; print opportunity coverage and all three results, including missed-upside incidence. Comparisons must not call different coverage an equal-opportunity result; also print the simple higher-relative126 half at the same coverage. Fewer than4 available reversal candidates in a month makes that month ineligible for every reversal comparator.

Labels, executable entry, fixed +/-10% close barriers, horizon63,20bp assumed cost, overlapping-event limitations and source-vintage designation stay unchanged. No raw data or prediction rows committed, no portfolio-return/Sharpe claim, no live promotion. A useful finding must survive low-vol and momentum comparators; a negative result ends these exact configurations rather than becoming an inverse signal.
