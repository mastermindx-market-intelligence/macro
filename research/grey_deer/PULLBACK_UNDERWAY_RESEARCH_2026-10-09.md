# Risk Radar: pullback underway, remaining downside and repair

**Commission:** `risk-radar-pullback-20261009` — Chairman requested research, native Paper designs and initiation of the US/China popup replacement. **Status:** research/design specification plus tested, unconnected depth-arithmetic slice. No fitted or accepted forecast, production integration, merge, or deployment is claimed.

## 1. Product decision

Risk Radar must answer a different question after a decline begins. Before an episode, the primary question is whether a meaningful decline might start. During one, lead with what has happened, the distribution of possible further losses over a named horizon, and evidence of deterioration or repair. Existing hazard and capital-policy outputs remain visible in secondary evidence; neither is rewritten by a new headline.

The three headline quantities are **current distance below the episode peak**, **possible additional loss from today's price**, and **implied total episode drawdown**. Show the worst depth already reached, time below peak, and rebound from the low. Displaying only a falling risk score while actual damage grows is not an acceptable state transition. A rebound is not synonymous with confirmed recovery.

This is an additive consumer capability under `WS:GREY-DEER-RISK-INTELLIGENCE`, not a second risk engine, episode ledger, recovery classifier, probability publisher or position-sizing policy. Observations may be built before predictive promotion. Statistical nulls do not block measurement; they do block unsupported predictive claims.

## 2. What was recovered and what it proves

Protected Mastermind Skillpack: `326c8469a21d7f50fc9ecb1848196bf1c6e66685`. Macro investigation: `b29ba7102d35bebf6f322c1d6fadf8309726bf4e`. The existing `engine/risk_envelope.py` separates measured state, transition hazard and capital policy. Its V0 does not mint episodes; that is not evidence that the broader application has no pullback observer.

**Late collision recovery changed the integration decision.** Existing Draft/HOLD **PR #8188** already implements `lib/pullback_observation.py`, `lib/china_pullback_view.py`, China builder wiring, `_pullback_observation` partials and the existing shared Risk Radar dialog. Exact recovered head: `ff27a268abaacfdb50534a60d1ca4ffe7a119938`; final semantic source `2270b9f43dbc6b8e015adb1a00b950eb46533a5c`. Reuse this observer and its original source carrier; do not replace it with a newly normalized snapshot service. Its native PR state was open, Draft/HOLD and not mergeable. The historical test/browser receipts in its body are not current-base proof, not new-Paper-design proof, and not a production release.

The observer is a causal, re-derivable raw-close projection, not a forward ledger. The China snapshot uses the existing CN calendar and raw price stores, with primary benchmark `000001.SS` (Shanghai Composite), `source_digest`, settlement clock and `valid_until`. Its presenter already feeds the hero, rack and shared dialog. Its `loss_recovered_pct` measures the fraction of the peak-to-low price loss recovered; that must not be mislabeled as the rebound return `P/T-1`.

The workstream record preserves the single-envelope and single-history rulings. #8648 contains the October 8 alertful Risk Radar masterplan. #7029 owns recovery safety/local liquidity; #8132 warning delivery; #7875 and #7592 retain their semantic/breadth holds. This additive slice changes none of those files, takes no source custody from #8188, and releases no hold. Its production candidate is only a pure additional-loss-to-total-depth arithmetic helper. An earlier 78-test normalized observation prototype remains unpublished scratch and is superseded for integration; it is not counted as a new production observer.

A relevant earlier study, `research/RRI_S3_DRAWDOWN_VELOCITY_LEG_PREREG.md`, explicitly studies continuation after fast declines, distinguishes coincident damage from leading warnings, and addresses the risk of pressure measures relaxing during a crash. Its frozen scope is KR/JP/TW/IN/AU/GB/EZ. It explicitly does not supply US/CN transfer authority or a probability statement. Reuse its lessons and study provenance, not its weights or apparent probabilities. `reports/drawdown-risk-pit-validation.md` also warns about overlapping observations and sparse deep-drawdown episodes; do not count every day of one crash as a new independent crisis.

Native Paper was found in **Mastermind · Market Dashboard Popups · Redesign**, not MASTERMIND PAGES. File `01M38EVF74SJWG1GANN5VP380Z`, page `p-1-0`. Original Risk Radar primary `1-0`, evidence and EN/ZH dark/light mobile states remain intact. This commission adds US `9TH-0`, China unavailable `9WB-0`, and mobile stabilization watch `9ZG-0`. All prices and forecasts on these boards are marked illustrative. Native screenshots were reviewed and the metrics' JSX was read back; no screenshot tracing was used.

## 3. Research foundation and limits

Goldberg and Mahmoud formalize maximum drawdown as peak-to-trough path-dependent loss and study conditional expected drawdown, including sensitivity to serial dependence [1]. This supports measuring a path's low rather than substituting volatility or endpoint return. It does **not** validate a forecast of today's remaining decline.

Mahmoud separately treats drawdown duration as time spent below a running maximum [2]. Our implication is to keep severity, age and recovery duration distinct; a short sharp drop and a long shallow decline should not be forced into one severity number.

Engle and Manganelli's CAViaR estimates conditional quantiles and tests exceedance behavior [3]. It is a useful methodological starting point for a conditional-tail model, not an off-the-shelf drawdown-bottom predictor. Our target below is a bounded-horizon future minimum, different from ordinary single-period return VaR.

Gibbs and Candès provide an adaptive conformal wrapper targeting coverage frequency under distribution shift over long time intervals [4]. That is not a guarantee that an interval contains this particular episode's bottom, nor proof of conditional coverage for China, a stress regime or a sparse severity cell. Such a wrapper is optional evaluation work after a baseline, not a substitute for honest holdouts.

**Evidence boundary:** this session reviewed primary research descriptions and current internal source/ownership. It did not conduct a licensed historical-data extraction, fit a predictive model, run a real-market backtest, or establish predictive accuracy. The numerical prototype is deliberately not a live market assessment.

## 4. Detecting and retaining an episode without hindsight

Consume the existing `observe()` result in #8188 rather than infer a decline from `risk_score > X`. Its recovered candidate uses exactly 63 settled closes including current for the reference, confirms after a 2% decline on two consecutive qualifying closes, or a 5% one-close shock, then freezes the reference until explicit resolution. It rejects invalid or conflicting raw closes; a missing expected session cannot manufacture persistence. An earlier failed one-day dip cannot contaminate the trough of a later confirmed episode.

These are **existing held candidate contracts**, not newly validated predictive thresholds or automatically promoted protected law. This commission proposes no replacement 3% onset rule and does not retune their thresholds. Reconcile and review the existing carrier. Peak date, first detected state and reconstructed historical transitions remain distinct; retrospective dates are not evidence that a warning was issued then. Intraday observations must not pass as settled closes.

Once an episode starts, retain its peak through the canonical history mechanism. Do not let an old peak aging out of a rolling window appear as a recovery. A full peak reclaim is an observation; a recovery confirmation, re-entry permission or position size remains with the existing owner. In an established bear market, a smaller secondary sell-off may be a nested observation with an explicit parent/reference; do not silently reset the parent drawdown or double-count both as independent crises.

Presentation states should be orthogonal:

- **Episode:** inactive / active / prior peak reclaimed / unavailable.
- **Trajectory:** worsening / stabilization watch / repair evidence / unknown, supplied by qualified existing sources.
- **Data:** current / partial / stale / invalid / missing.
- **Forecast:** unavailable / research-only / accepted for exact market, benchmark, basis and horizon.

These are presentation distinctions, not a new company lifecycle. The existing observer owns observed price phases; the first new code slice only converts loss quantiles. Neither its arithmetic nor a short bounce can confirm a policy recovery or combine these axes into another score.

## 5. Exact quantities and prediction target

Let H be the retained episode peak, P the current price on the same basis and T the lowest observed price after that peak. During an active unreclaimed episode:

```
current drawdown d = 1 - P/H
worst drawdown so far m = 1 - T/H
rebound from low = P/T - 1
F_h = min(P_t, P_(t+1), ..., P_(t+h))
additional loss A_h = 1 - F_h/P_t
D_h = max(m, 1 - (1-d)*(1-A_h))
```

h means **5, 10 or 21 local trading sessions**, not calendar days. F includes today's price, so additional loss can be zero. D retains the worse of the past trough and future minimum. Losses compound: a further 10% decline after a 20% drawdown yields a 28% total decline, not 30%. A bounce from an earlier deep trough must not erase the damage already experienced.

Illustration only: H=100, P=93.2, T=92.6. Current drawdown is 6.8%, worst so far 7.4%. Future lows of 91 and 88 imply another 2.36% and 5.58% from today, corresponding to total depths of 9% and 12%. The UI rounds the additional range to 2.4–5.6%.

The model should estimate a distribution of A_h, optionally mapping each loss quantile to D_h. Display Q25–Q75 as a **middle 50% predictive range**, not a confidence interval around an exact bottom. The stress estimate can be Q90 of loss with an explicit explanation that more extreme losses remain possible. Do not label a quantile a support level, floor or maximum possible loss. Percentiles must not cross; for a fixed forecast origin, cumulative-loss quantiles cannot improve merely because the horizon grows.

The chart must distinguish observed prices from **projected total episode trough depth**. A projection of total episode depth begins at the worst loss already observed, not at the current rebounded price. This avoids drawing a false recovery into a curve of cumulative worst damage. A fan of future minima is not a predicted tradable price path.

“Chance of a further 5% decline from today's close” is a new conditional event, not the probability that an already-observed 5% episode occurred. The product must show the anchor and horizon beside any probability. Do not convert a 97/100 intensity score into 97% odds.

## 6. Estimation strategy

### Baselines first

Start with an unconditional country/benchmark forward-minimum distribution and a volatility-conditioned historical baseline. A matched historical-state baseline can then condition on current drawdown depth, episode age, recent loss velocity and realized volatility. Every match uses information available at that historical origin; eventual troughs, final episode duration and later-known crash categories cannot select the neighbors.

A volatility-filtered block bootstrap is a useful candidate for preserving local sequences instead of independently shuffling single returns. Treat block length and volatility normalization as training-only choices. It is a benchmark to beat, not evidence of calibrated crash tails. Avoid extrapolating a precise extreme quantile from a handful of crises.

### Candidate conditional model

Fit regularized conditional quantiles for A_h on a small preregistered feature set. Candidate inputs: drawdown depth, age and velocity; realized volatility; current breadth deterioration or repair; credit/rates/liquidity stress; and existing market-specific risk-organ states. Every input needs source owner, observation clock, availability clock, history span and missingness policy. Features may be omitted when not historically reconstructible; do not fill yesterday's missing reading with today's value.

Use a two-part specification only if a zero-additional-loss mass materially improves validation: probability of a meaningful new low, then severity conditional on a new low. Compare its full distribution with direct conditional quantiles, including calibration at zero. A neural sequence model, change-point model or synthetic crisis generator is not the first production dependency; extra flexibility must earn incremental held-out value.

Do not publish invented causal attributions. A rates or breadth feature's contribution describes the model's association, not proof that it caused the market's decline. Where model disagreement, data gaps or an out-of-distribution state are material, widen the disclosed uncertainty or withhold the numeric estimate according to preregistered rules. A deterministic list of named unknowns is preferable to an unvalidated numeric “confidence score.”

### US and China are separate release decisions

Resolve each page's existing benchmark rather than silently changing its target: the US Paper example uses SPY and still requires exact production-source qualification; the existing China adapter uses `000001.SS`, Shanghai Composite. Aliases must come from the existing instrument owner. Use a consistent index-close, split-adjusted-close or total-return-close basis and label it. A total-return series is not interchangeable with a price-index level.

Train and validate China separately. Local session calendars, source clocks, domestic liquidity, historical breadth coverage, suspension/limit-state information and constituent history need their own admission. Foreign stress can be contextual evidence; it does not constitute a domestic recovery confirmation. A model admitted for US/SPY/21 sessions cannot self-qualify as CN by replacing its country field. Missing China calibration renders measured damage plus **estimate unavailable**, not copied US odds or zero risk.

## 7. Historical evaluation and release evidence

Register hypotheses, targets, cohort definitions, feature availability rules, folds and candidate families before comparing outcomes. Use rolling-origin out-of-sample evaluation; purge training labels that overlap each evaluation origin, with the longest horizon controlling the overlap boundary. Parameter selection happens within the training span, never on the final test period.

For bounded h-session minima, an origin is labeled only after all h future sessions exist. Keep immature origins explicitly censored rather than filling them with the low observed so far. Eventual bottom depth or time to full recovery would require a separate censored-duration study and is not the first release target.

Report forecast-origin count **and distinct episodes**. Cluster uncertainty by episodes and calendar blocks where the markets overlap. Specify whether model training weights represent a random forecast day or a random episode: weighting long episodes away changes the estimand. Report both day-level use and episode-balanced robustness; do not equate hundreds of correlated days with hundreds of crises.

Evaluation includes pinball loss at each quantile, coverage and width of the middle interval, Q90 exceedances, and performance by market, volatility, current depth, episode age and stress regime. Include comparison with the baseline and the actual incumbent, not only an attractive standalone hit rate. Retain false stabilization and false new-low alarms; assess how often a projection stayed unavailable and why.

Numerical promotion requires an accepted, immutable receipt for the exact target and origin policy: data/version and license evidence; train/test cutoffs; distinct-episode counts; baseline comparison; interval/tail calibration with uncertainty; monotonicity and availability tests; and reviewers' conclusions. No universal magical sample size is asserted here. A proposed minimum-N/coverage tolerance must be justified and frozen before fitting; small or unstable cells abstain rather than presenting narrow ranges.

Adaptive conformal calibration, if evaluated, must update only when labels mature. Its long-run target must be described honestly [4]. Do not call it a guarantee of episode-specific, stress-conditional, or cross-country coverage. Live forward accrual belongs to the existing history/publication owners, not a new tracking database.

## 8. Paper information architecture and replacement path

Desktop leads with phase and one-sentence assessment, then the three numeric columns. The depth chart is primary evidence, with current price and worst depth clearly distinguished. A side-by-side checklist shows what would support repair and what would indicate further deterioration. Existing risk drivers, clocks, method receipts and same-country return remain available, but do not compete with the main answer.

Mobile stacks current damage ahead of the two projected quantities, moves the full chart/method into evidence, and preserves a large close control and same-context return. Forecast unavailable is a designed first-class state, not an empty skeleton; current observations remain visible only when current. Stale observations can appear as last-known, dated evidence, never as today's state.

New native boards: `9TH-0` US range illustration; `9WB-0` China forecast unavailable; `9ZG-0` mobile stabilization watch. They extend the existing `1-0` primary and its evidence states. This commission must not replace only the active-pullback case while abandoning pre-pullback, partial-data and return behavior.

The build should replace the **content inside the existing shared Risk Radar popup** on both US and China pages, preserving its opener, focus trap, Escape/close, scroll, backdrop behavior, country context, evidence drawer and routes. Reuse existing tokens and static presentation CSS. Do not invent a second modal framework, opaque injected style system, endpoint, navigation family or publisher.

Dark treatment: graphite surface, restrained damage red, white numeral hierarchy and amber unknowns. Light treatment must be intentionally composed as a cool research canvas with white material, hairlines and controlled shadow, not a token-swap claim. New pullback light designs and dark/light × EN/ZH × desktop/mobile evidence remain to be completed before production UI acceptance. The three new dark English artboards are not that full matrix.

## 9. First implementation and remaining gates

`lib/pullback_depth_projection.py` supplies `project_total_drawdown(peak, current, trough, additional_loss_fractions)`. It validates finite real inputs, positive coherent prices, and nonempty ordered loss fractions in [0,1], then applies the exact compound-loss formula while retaining prior worst damage. It has no I/O, clock reads, episode detection, country classifier, source feed, calibration claim or capital-policy authority. The caller must separately qualify observation scope/clocks and model evidence through existing owners.

Its dedicated suite contains **39 passing synthetic arithmetic tests**, following an observed missing-module RED run. Tests cover the Paper example, compounded losses, past-trough floor, zero/total additional loss, repeated quantiles, scale invariance and invalid/domain/order inputs. These prove arithmetic only. They do not prove actual source values, forecast skill, repository CI, modal integration or deployment. The broader 78-test observation prototype is not published or used to inflate this source slice's verification.

Integration sequence: (1) preserve and reconcile #8188 on its original carrier, including current-base conflicts, exact-head CI and admitted independent review; (2) qualify a US raw-price/calendar/basis adapter to the same existing observer, not a copied detector; (3) extend the existing China/shared presenter and modal content with observed metrics and the designed unavailable forecast state; (4) complete the new dark/light, EN/ZH, desktop/mobile design and browser matrix; (5) fit and qualify exact country-specific forecasts off the render path; (6) release through the existing publisher with served-page and canonical machine-artifact proof. Measurement/UI need not wait for forecast promotion if their own gates pass.

Do not change envelope V0's forbidden lifecycle fields or mint episode identities in the helper. Existing Chronicle/Reflex/QLedger systems remain issued-event history owners; the re-derived observer remains an observation, not historical issued-warning evidence. #8188/#7029/#8132/#7875/#7592 holds remain in force. The new source is an additive draft arithmetic/research carrier, not a replacement for any held implementation.

## Primary research references

[1] Lisa R. Goldberg and Ola Mahmoud, *Drawdown: From Practice to Theory and Back Again*, arXiv:1404.7493, revised 2016. https://arxiv.org/abs/1404.7493 ; author institution: https://cdar.econ.berkeley.edu/publications/drawdown-practice-theory-and-back-again.html

[2] Ola Mahmoud, *The Temporal Dimension of Risk*, arXiv:1501.01573. https://arxiv.org/abs/1501.01573

[3] Robert F. Engle and Simone Manganelli, *CAViaR: Conditional Value at Risk by Quantile Regression*, NBER Working Paper 7341; published version JBES 2004. https://www.nber.org/papers/w7341

[4] Isaac Gibbs and Emmanuel Candès, *Adaptive Conformal Inference Under Distribution Shift*, arXiv:2106.00170. https://arxiv.org/abs/2106.00170

All external sources accessed 2026-10-09. Method adaptations, thresholds and release sequence above are proposals specific to this commission, not claimed results of those papers.
