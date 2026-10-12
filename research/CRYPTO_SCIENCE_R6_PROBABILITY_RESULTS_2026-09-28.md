# Crypto science R6 — continuous forecasts improve description, not yet decisions

Programme date: 2026-09-28. Existing WS:CRYPTO-INTELLIGENCE, operation crypto-vector-r2-20260926-sol-001, draft Macro PR8050. Baseline `3d656d97f8935bccac81299b786e54e3d9868de4`. Protocol committed before outcomes at `067f0fb76f7fc20239aa4cdeae03b6cf5b279b85`; tested research implementation `7b63e8ab2608a4c280e410d5dfaab7df04042127`. Research/test changes only; no production allocation, signal default, gate, collector, UI, model promotion or live forecast issued.

## Executive disposition

The small continuous price/trend/volatility model provides a more promising forecast representation than another confirmation checkbox: it improves average chronological Brier and log loss relative to an expanding historical-rate baseline, with an AUC around0.70 on the primary scored sample. But the full-sample uncertainty interval for the Brier gain crosses zero, probabilities overestimate the observed event frequency, recent-period ranking deteriorates, and the separately specified cash policy still underperforms the incumbent on average. **Do not promote it as a calibrated crash probability or an accepted exit strategy.**

Adding unsigned spot participation slightly worsens primary probability scores. It is not consistently incremental information after price. Some alternative-delay economic cells are positive on a handful of actions; they are retained and do not override the primary result.

The actual signed-flow feed is real derivatives aggression, but its stored aggregate units/mix, exact timestamp convention and publication history are not adequately established for this predictive join. No signed-flow model or proxy relabeling was performed. The recovery candidate population is too small under the precommitted fit minimum; the learner returns unavailable rather than fitting an overconfident bottom predictor.

## 1. What was frozen and actually tested

This study reuses all647 R5parent observations (588hourly breakdowns and59daily washouts), R5 timing and common-parent accounting. The downside forecast is made AFTER six completed follow-up hours, not before the initiating selloff. Target: another5% decline before a3% rise in the remaining18hours, from the delayed action reference. One-hour action delay is primary; six hours is sensitivity. Ambiguous and incomplete targets stay unscored.

M0 is an expanding smoothed event-rate forecast. M1 is a fixed ridge-logistic model using six continuous quantities: volatility-normalized short response, distance from the known broken/reclaimed structure, progression of recent lows,24h return,720h slow trend, and log volatility. M2 adds log1p of the same unsigned spot-participation ratio used in R5. Both models are fit on the SAME complete price/volume cohort. These are transformations of observed price and total volume, not six independent causal witnesses or net buyer flow.

Each calendar quarter from2018 onward fits only data whose full target/account horizon plus24h embargo ended BEFORE the quarter. Feature centering/scaling and class-conditional economic estimates are training-only. Coefficients are fixed during that quarter. Ridge penalty0.05, clipping at five training standard deviations, optimizer settings, minimum80observations and15of each class were frozen. No hyperparameter grid, threshold search, retrospective reweighting or test-set recalibration was used. Existing SciPy/NumPy were sufficient; no host dependency installed or CI runner added.

This is chronological OUT-OF-TRAINING replay on history already examined in earlier research. It is NOT a newly untouched research holdout, a live-issued forecast ledger or source-publication-time proof.

## 2. Source and sample qualification

### Signed flow: a useful feed with unresolved measurement gates

The existing collector calls OKX's aggregate taker-volume endpoint with BTC, CONTRACTS and1H. Official documentation confirms the sell/buy ordering and instrument-type separation. It does not, in that aggregate endpoint's response description, establish the absolute unit, contract-mixture weighting, whether ts marks bucket start or end, or original publication latency/revision history. A different instrument-specific endpoint documents unit selection, but those semantics cannot be imported into the old aggregate source [1].

The file contains2,957rows, nine missing hourly labels, no negative volumes or zero totals, and no attached frame metadata. The nine gaps occur near the beginning of the stored period,2026-05-26 01:00–09:00. There are2,951complete six-row observed windows under a simple hourly-bin census; that count is not an availability certificate. Only21downside candidate times and ZERO recovery candidate times in this fixed experiment overlap its stored date range. Even qualified units would not magically provide a decade of independent aggressor-flow observations.

Its dimensionless buy-minus-sell share could remove a common scalar unit, but not unknown mixture, incomplete interval or publication timing. The source remains EXCLUDED_FROM_FORECASTS. The current result does not prove that signed flow lacks value; it establishes that these semantics and matched samples are not ready for this claim. No provider market/account endpoint, backfill, credential or subscription was touched. Only public documentation was fetched.

### Price/regime measurement coverage

The long price/regime feature requires721contiguous valid hourly OHLC bars. Of588downside parents,499have complete features and89are price-unknown. Of59recovery parents,44have complete features,11fail price-history completeness and four have no candidate. These cases are retained as abstentions, not filled or scored safe. This strict thirty-day history requirement changes coverage; results cannot be extrapolated to the gaps it excludes.

Quarter fitting produced122family/lag snapshots:70downside snapshots,65eligible;52recovery snapshots,none eligible. Those65snapshots produce130fitted M1/M2 likelihoods, not130independent experiments. Maximum checked gradient residual is approximately2.70e-7; no optimizer failure occurred.

For the primary downside delay there are506candidate rows from2018 onward:406receive predictions,68have unavailable features and32lack training support. Two predicted targets are ambiguous/unavailable, leaving404scored episodes. Prediction support begins2018-10-03. For six-hour delay,419predictions leave417scored episodes, with a different initial training-eligibility date. Delay columns therefore are scenario sensitivity, not a perfectly matched causal intervention across all scored rows.

Recovery cannot pass the predeclared minimum80fit observations with only55historical candidate times before even applying feature completeness and maturity. We did not reduce that minimum after seeing poor sample availability. No-entry episodes are not negative recovery labels. A future recovery model needs a scientifically justified population or additional evidence, not a low-data confidence badge.

## 3. Primary forecast result: information, with calibration limitations

All three forecasts below are scored on the SAME404eligible primary-delay downside episodes, with45target events (11.14%). Lower Brier/log loss is better; AUC is pairwise ranking, not a hit rate or winning-trade percentage. The official calibration guide warns that Brier mixes calibration and discrimination; a lower total score alone does not establish reliable probabilities [2].

| Forecast | Brier | Log loss | AUC | Mean predicted probability |
| --- | ---: | ---: | ---: | ---: |
| M0 historical rate |0.103774|0.366442|0.5719|18.53%|
| M1 continuous price/state |0.098027|0.338833|0.6997|15.85%|
| M2 plus spot participation |0.098824|0.341478|0.7010|16.51%|

The paired M1-minus-M0 Brier difference is **−0.005747**, approximate calendar-block95range **−0.012220 to+0.000522**. Average improvement is real in the descriptive arithmetic, but this full-period interval does not exclude no improvement. It is not correct to call AUC0.70 '70% accurate crash prediction'.

M2-minus-M1 Brier is **+0.000797** (worse), range **−0.002711 to+0.004001**. Its slightly larger aggregate AUC does not offset poorer primary proper scores. The report retains both metrics rather than selecting whichever favors volume.

### Reliability and recent regime

Mean M1probability15.85% exceeds the actual11.14% event fraction. Its fixed10–20% bin contains186episodes, mean forecast14.33%, observed9.14%. Its20–30% bin contains82episodes, mean forecast23.70%, observed18.29%. This is not calibrated enough to label the UI's risk number as an empirical crash probability.

In reused2024+, the common scored set has145episodes and only10events. M1Brier0.067681 improves over M0's0.071006, but its AUC0.5815 is below M0's0.6211. M1mean probability12.02% remains well above the observed6.90%. The lower current event base rate and weak recent ranking deserve attention; we did not repair them by calibrating against these test outcomes.

The strongest primary Brier increment occurs in2020–2023: −0.008512, with a block interval below zero in this retrospective slice.2018–2019 and reused2024+ gains have intervals crossing zero. Omitting any one calendar year retains a negative mean M1-minus-M0 Brier difference, while volume's M2-minus-M1 mean remains positive. These are useful stability diagnostics, not independently replicated trials or multiplicity-adjusted proof.

At six-hour delay,417scored episodes/43events give BrierM0=0.095412, M1=0.091403 and M2=0.090579. M1-minus-M0 and M2-minus-M1 block intervals both cross zero. This alternate result is preserved; the delay was not selected because it makes volume look better.

## 4. A better probability ranking is not automatically a better cash decision

The economic diagnostic was frozen separately. For each quarter/lag/cost, the same prior mature training episodes estimate the cash-minus-incumbent gain for event/non-event classes, each shrunk toward the training overall mean with10pseudo-observations. A forecast's weighted expected gain is compared with zero; positive means cash at the landmark, otherwise incumbent. No fitted threshold is selected on test outcomes. This intentionally simple class-payoff projection may be misspecified; it is a hypothesis to evaluate, not a theorem connecting a5% barrier to portfolio utility.

All paths follow the incumbent until the six-hour landmark and restore its requested target at the original24h endpoint. Account drift, turnover costs and unavailable periods retain R5 semantics. No losses before observation are credited to foresight.

Primary1h/10bp comparison on the same404unambiguous mature accounts:

| Forecast used for policy | Cash decisions | Mean marginal return versus incumbent | Approximate block95 interval, pp |
| --- | ---: | ---: | --- |
| M0 expanding rate |27|−0.02499pp|−0.07325 to0|
| M1 continuous price/state |67|−0.04916pp|−0.11860 to+0.00890|
| M2 plus participation |80|−0.03503pp|−0.11342 to+0.03139|

These are per-event percentage points of initial equity, not annualized returns. Cash decisions are not necessarily actual exchange orders: an incumbent may already be in cash. For M1,28cash decisions produce a positive marginal account gain,34negative, and five zero; the remaining337parents retain the incumbent. We do not advertise a win rate without denominator and economic magnitude.

Both learned policies are slightly less bad than R5's specified price/volume cash rules ON THIS SAME restricted cohort, but neither beats the incumbent mean. Removing a compared policy's losses is not proof of a new profitable policy. No-shift M0 actually loses less than either learner under the primary mapping.

All registered cost/delay cases remain available. Under1h delay, both learned policies' mean increments are negative at0/10/25bp. Under6h/10bp, M2has a small positive mean around+0.00910pp, but only10cash decisions across417scored parents. Under6h/25bp, M1is positive with only TWO decisions, while M2is negative. These sparse favorable cells do not rescue the primary hypothesis or justify selecting the six-hour delay after inspection.

The objective here is mean costed account wealth. It does not prove that risk-averse drawdown reduction is worthless. A protective policy must instead specify and measure its drawdown/tail-loss preference and opportunity cost against an equal-risk incumbent. We did not retroactively replace the loss function with whichever metric makes the tested cash policy look attractive.

## 5. Scientific interpretation and next action

There is now an evidence-backed distinction between better information representation and policy promotion. The continuous measurements outperform a rate-only forecast on average without adding more sources, but the probability scale is still too high and regime-dependent. The binary downside-first target omits loss magnitude, recovery speed and exposure already taken by the incumbent; its coarse conditional-payoff mapping has not delivered positive net utility. Volume contributes little dependable primary score improvement after these price features.

The next substantive unit should freeze a TRAINING-ONLY calibration/decision comparison that explicitly models the asymmetry of tail protection, missed rebounds and turnover at a specified risk budget. Start by reviewing the existing R1–R6 timing, data eligibility and arithmetic with an independent eligible reviewer before any promotion. Do not simply lower probability thresholds, shrink the training window, pick a better ridge coefficient, change barriers or adopt the favorable6h cells after these results. A new calibration or economic loss function is a new experiment with a preregistered baseline and fresh issued-forward acceptance requirement.

Signed-flow integration remains source-dependent. First establish the exact existing aggregate measurement and publication contract through its owner, or use a separately approved instrument-specific collection with explicit units. Do not add a second collector/forecast store or assume permission for paid data. Recovery needs enough independently observable situations to support its degrees of freedom, rather than treating thousands of correlated hourly bars as thousands of washouts.

A further limitation is the comparator: an expanding historical rate can adapt too slowly when the event base rate changes. Part of M1's gain may reflect correcting that stale average, not precise episode discrimination. R6 did not test a recently calibrated rate-only baseline or decompose the Brier improvement into calibration/resolution terms. Those belong in the next frozen comparison; do not assign all measured score improvement to a new timing edge.

This R6 work is not a global forecast for all Bitcoin hours, pre-crash warning, exact-top/bottom locator, accepted re-entry engine, calibrated live probability or deployed action. It provides a reproducible chronological comparison and identifies the next measurement/decision gaps precisely.

## 6. Verification, immutability and operational record

The generating study completed once with process35418 exit0. No outcome-driven rerun or hypothesis change occurred. Seven initial core tests failed because the R6 module did not exist; the implemented helpers then passed. Two intermediate errors were pandas3 rejecting NaN/float assignment into a BOOLEAN test fixture; changing that synthetic fixture target to floating point fixed the setup, not a model threshold or market result.

The final combined Crypto/Vector/science pack passed **268tests,27warnings**; compilation, the existing source-claim checker and diff check passed. The existing Vector CI dependency set already includes scikit-learn (which depends on SciPy) and the test file; no new runtime job, runner, install line or validator exception was introduced. The host used its already-present SciPy library.

An independently expressed verifier rechecked543valid-price feature records, all122quarter training memberships and80/15eligibility decisions,130fitted likelihood gradients/objectives/scalers, every1,100prediction row, and every7,425policy-scenario row. It independently recomputed forecast Brier/logloss/AUC/reliability bins, paired block intervals and all72action-summary cells, including training-only payoff shrinkage and leave-one-year-out means. It confirmed that no recovery learner passed the fit gate. This is numerical verification by the SAME session, not independent scientific/code review.

All55input identities,18existing gate files,72earlier R2–R5 evidence files,8inherited R4engine/config/protocol identities and6current source/protocol/test identities remained unchanged during and after computation. R1 evidence is unchanged in git. The independently recounted six-hour flow coverage agrees with the generation census. No raw price/parquet data, credentials or font assets were published.

Results and allfit/scaler parameters are in research/crypto_science/r6/. Results SHA256 `b24832969f5758d0884dcbd85e75931f9fa5aaf20a23cab9182a760607cf3f54`. Per-parent features, target masks, fit dates, exclusions, probabilities, expected gains, decisions and costs are retained. The1,100prediction rows repeat underlying events across two lag assumptions; the7,425policy rows repeat predictions across models/costs. These are NOT8,525independent market events.

Operational observations: one bounded collector-source print exceeded the file length by one line; a corrected bounded read recovered the intended text without modifying source. The web reader refused oversized official docs, so the already allowed host read extracted the exact relevant public endpoint section; no account or market API was called. Original explicit modification denials from other programme lanes remain fences, not erased by these permitted research calls. The prior R5exact-head CI/fences were successful; R6publication requires its own receipts and no live-release acceptance is claimed.

[1] OKX official API guide, aggregate taker-volume and separate contract taker-volume sections, reviewed for instrument/array/time/unit contract: https://www.okx.com/docs-v5/en/ . Only the public document was read. Its full response digest is recorded in the qualification evidence; unasserted historical units/availability remain unknown.

[2] Scikit-learn official probability-calibration guide, especially proper-score versus calibration distinction: https://scikit-learn.org/stable/modules/calibration.html . R6uses explicit SciPy logistic likelihood, not an installed sklearn learner; documentation supports evaluation semantics, not predictive efficacy.
