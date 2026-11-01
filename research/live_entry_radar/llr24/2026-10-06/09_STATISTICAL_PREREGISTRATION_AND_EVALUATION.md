# 09 — Preregistration, evaluation and falsification

**Status:** complete proposed protocol for later owner ratification. No market-wide census, model training, holdout test, quote-fill study or prospective trial was run by this commission. Existing results are attributed to their original experiments. Analysis arithmetic in this package is not market evidence.

## 1. Lock order and trial accounting

1. Reserve development, calibration, validation and a sealed final chronological holdout **before outcome exploration**. Qualify source/clock/label feasibility on declared development-only or already-consumed history. Record every inspected date and source version. Only a frozen, label-blind source-integrity audit may inspect the sealed interval; accidentally viewed outcomes consume that interval.
2. Register eligible universe, landmark/candidate rules, target, horizon, features, preprocessing, comparator, fill policy, practical effect bar, split calendar, exclusion/censoring treatment, multiplicity and trial budget in the existing registry.
3. Seal training/calibration/test manifests and content hashes. Only then run fitted models.
4. Carry every attempted feature family, threshold, universe variation, stopping decision and inspected chart into the trial ledger. Register abandoned candidates too.
5. Preserve the final holdout untouched until one champion, comparator and analysis script are frozen. No “quick look” at it to choose parameters.

Across waves, default to a common final holdout kept sealed through the selected R3/R4/R5 feature/source tournament. An intermediate R3 comparison is then development/validation evidence only. If a standalone R3 final test is opened earlier, its dates immediately become consumed history; later feature/source selection needs genuinely fresh final evaluation. Freezing another budget or reusing the same baseline predictions does not restore holdout status.

The prior R1-B 60-cell/60-minute/25bp study is already consumed and parked. The F4 repair/hazard dates, leaked bottom backtest, S7 holdout, Trend Persistence eras and October options grid are also known evidence, not fresh confirmation. A new model name does not reset the number of trials. [R25–R27; PR7274; P08–P18, P38]

## 2. Market-wide low/high census before ML

The census is **specified for R2**, not asserted complete. All outcome-bearing atlases and exploratory tables use development or explicitly consumed dates; sealed final-test outcomes remain unopened. Build an as-of-date eligible U.S. universe including entries, exits, delistings and mapping failures; never backfill today's liquid survivors into history. Produce both equal-security and opportunity-weighted summaries. Date-specific minimum price and liquidity screens must use information available before the evaluated day.

For each security/economic day with adequate coverage, compute raw, midpoint and supported-executable low/high where each basis is available. Report:

- time of first and final meaningful low/high by session and elapsed-time quantile;
- number and materiality of successive lows; time since prior low; reclaim latency, failure and later re-breach;
- proximity of every eligible landmark to final and forward-available lows;
- MAE/MFE and cost of waiting 5/15/30 minutes; no-fills, missed moves and common-terminal wealth;
- raw-print versus supported-quote extreme disagreement, spread, depth/size, conditions and source gaps;
- overnight share of eligible opportunities, trading activity and executable support; transition gaps into premarket/RTH;
- price/liquidity/size/sector/ETF/earnings/macro-day/regime strata, including negative and unavailable strata.

Deliver a coverage matrix, low/high atlas, conditional base-rate table, event-count table, raw-to-label witnesses, distributional plots with uncertainty and a source/cost manifest. A data availability failure is a useful result. Do not fit a model to compensate for an undefined label.

## 3. Population, landmarks and dependence

Two populations are distinct. A market-wide fixed-grid sample estimates where lows and highs occur. A canonical Radar/Prophet candidate-landmark sample estimates improvement for the intended consumer. Neither substitutes for the other. Use all qualified landmarks for prediction scoring with explicit weights; use first eligible episode/candidate observations and paired policies for entry economics. Additional observations from one episode do not become independent opportunities.

Group all records sharing a security/economic day, Radar episode, catalyst episode or overlapping outcome window as appropriate. Cross-sectional market shocks also correlate different securities. The primary inference unit is an economic-day/calendar block with all contemporaneous names retained; two-way security/day clustering or a prespecified block bootstrap is a robustness check. Report raw rows, unique securities, days, episodes and effective event support separately. Do not equate 100,000 landmarks with 100,000 independent trades.

## 4. Splits, purging and known history

For sufficiently deep daytime history, use expanding chronological training windows, a following calibration block, and a later validation block. Purge any training/calibration observation whose **outcome interval** intersects the next evaluation block. Embargo at least the longest evaluated economic horizon plus finalization/availability lag; whole-day targets require entire economic-day separation. Purely past feature lookback can overlap as real deployment would, but any fitted normalization, universe selection or label-derived feature must remain training-only.

Reserve a final contiguous terminal holdout before exploration; open it only after model, comparator, thresholds and script are frozen. Propose at least 60 eligible economic sessions for the first broad daytime final test, subject to event-based power. For overnight, Databento's documented start in August 2025 limits historical breadth; do not pretend it contains several independent market cycles. If training/calibration/holdout cannot all have adequate events, reduce model complexity and extend prospective collection. Do not invent extra holdout years.

Same-time-of-day normalization uses earlier eligible days only, by session/calendar era, with shrinkage for sparse slots. A 60-day historical research replay cannot use the final plotted day's RVOL baseline to normalize its earlier days. Adjustments, peer membership, market-cap bins and catalysts must also be as-of their recorded known times. [T15; P51]

## 5. Baseline and ablation matrix

| Comparison | Required purpose |
|---|---|
| Time/session/liquidity only | Base-rate and survivorship-of-the-day effects |
| Price path + volatility + time | Core nontechnical reference |
| + all accepted Terminal technical families | Whether existing transformations improve the task |
| + each family separately; remove one family | Attribution and redundancy, without counting correlated transforms as independent evidence |
| + L1 to price; + L1 to price+technical | Source-grain increment beyond a stronger baseline |
| + L2/L3 to matched L1 | Deeper data value at identical symbols/dates/coverage/latency |
| + options; + relative; + catalysts; interactions | Independent contextual contribution and source-known-time control |
| Global versus supported session specialists | Added specialization versus sample fragmentation |
| Simple versus neural | Same inputs/trials/splits/costs; complexity must earn a practical gain |

For every added-source comparison report two effects: the **matched-coverage** increment on the shared computable cohort and the **full intended-universe** coverage/utility change. Complete-case performance alone can reward a feed for dropping hard observations. The richer model must be compared to a baseline evaluated on the same dates, not an easier epoch.

## 6. Evaluation rulers

**Prediction:** proper scores (Brier/log loss), base-rate-relative skill, precision/recall at prespecified coverage, survival and competing-incidence calibration, quantile pinball/interval coverage, support counts and reliability by session. AUROC is secondary: a locator with high AUC can still fail adverse-tail or economic utility gates, as the existing F4-free hazard demonstrates. [P14]

**Entry location and timing:** premium above finalized low, forward-available opportunity, lead/lag from meaningful low, reference-low durability, price paid for confirmation and missed-opportunity rate. Do not reward a rule solely for waiting until most of the horizon has elapsed.

**Path and economics:** executable MAE/MFE, adverse-barrier-before-favorable-barrier risk, terminal net wealth at common E, implementation shortfall, fill ratio, spread/slippage/impact sensitivities and a cost/risk/coverage frontier. Include no-entry and simple waiting policies. Report tail metrics and losing episodes, not just mean return.

**Robustness:** per-session, liquidity, price, sector, ETF/single stock, trend/chop, market stress/calm, earnings, macro announcement, gap and catalyst support. These are preregistered heterogeneity reports; the worst cohort is not removed after inspection to rescue a headline.

## 7. Proposed acceptance bars and sample support

The initial forecast claim is the exact `PRICE_L30M_30M_v1` target in chapter06. For R3, freeze baseline B0 as the training-only event rate within 30-minute RTH clock buckets × three prior-dollar-volume liquidity strata, shrunk toward the training global rate with 50 pseudocounts: p₀=(events+50×p_global)/(n+50). Stratum boundaries and all bucket mappings are frozen from training. R4 and later additions compare with the frozen accepted price/volatility model, not this weaker B0. Each final evaluation has one primary champion and comparator selected before the sealed test is opened.

The following are **proposed exact ratification gates**, not current production permission. Fractions are returns, so 0.0005=5bp and 0.01=1 percentage point. Use paired day-block confidence intervals, retaining all contemporaneous securities.

| Claim / gate | Estimand and comparator | Exact proposed pass rule |
|---|---|---|
| Primary forecast skill | Mean Brier loss of B0 minus champion on the same eligible landmarks | Lower bound of paired 95% CI >0 |
| Calibration | Observed breach rate minus mean predicted probability in each admitted display bin | Simultaneous 95% day-block intervals are wholly inside [−0.05,+0.05]; overlap alone fails |
| Investor policy risk | ΔA=mean(A_champion−A_buy_now), where A is all-candidate wealth-path excursion in chapter06 | Lower bound of paired 95% CI ≥0.0005 |
| Investor wealth noninferiority | ΔR=mean(R_champion−R_buy_now), common capital and terminal | Lower bound of paired 95% CI ≥−0.0005 |
| Severe-path noninferiority | ΔP=P(A_champion≤−0.005)−P(A_buy_now≤−0.005) | Upper bound of paired 95% CI ≤0.01 |
| Exposure/coverage guard | Sum of champion filled shares / sum of buy-now filled shares over the same eligible candidate cohort | Lower bound of day-block 95% CI ≥0.70; a tiny partial fill is not a completed opportunity |
| Day-trading alpha, if separately commissioned | ΔR versus the frozen buy-now/accepted trading comparator | Lower bound of paired 95% CI >0 plus the separately frozen practical-effect bar and risk/coverage requirements |

Start calibration bins at fixed deciles of predicted probability; merge adjacent bins using calibration-set support only, then freeze boundaries. A proposed display bin needs at least 400 resolved labels across 20 distinct days **and** the interval-containment gate; these counts alone do not prove sufficient independent support. Sparse or failed final-test bins abstain under the predeclared rule and are reported, never merged after seeing test outcomes to rescue calibration. A broad claim must also pass for the predeclared supported session; pooling away a failed overnight cohort is not allowed.

The exposure comparison additionally requires buy-now fills on at least 20 distinct days and 400 candidate opportunities. If total comparator filled shares are zero, the ratio is NON_EVALUABLE. In the frozen day-block bootstrap, a zero-denominator replicate is conservatively assigned ratio0 for the lower-bound gate and its frequency reported; it is not dropped or treated as infinite success. If more than5% of replicates are undefined before this convention, classify support inadequate and defer the claim. These are explicit proposed support rules, not measured counts.

As an IID illustration, a proportion near 0.5 requires about **385 observations** for a 95% half-width near five points; a five-point difference with 80% power needs approximately **1,570 per arm** under simple independent equal-size assumptions. The reproducible arithmetic is in `analysis/storage_scenarios.json`. Dependence, rare outcomes, many bins and changing regimes can require far more. Neither number is a universal gate or a claim that clustered support already exists. Use blocked pilot estimates to size the actual fixed study before the holdout is opened.

The investor policy must clear **all four** risk, wealth, severe-path and exposure gates above. There is no post-hoc alternative “equivalent tail benefit” route. A different user objective or practical margin requires its own frozen protocol before outcomes. Fill-conditioned MAE, location and time invested remain diagnostics and cannot replace the all-candidate risk denominator. Report the cost/risk frontier even if a gate fails.

A **day-trading profit** claim is a different registered objective: its net incremental common-terminal wealth must have a positive lower confidence bound after realistic friction and practical magnitude, in addition to risk/coverage checks. It cannot borrow the investor noninferiority margin to claim alpha. A calibrated forecast that fails policy utility remains a descriptive forecast, not an entry-opening rule.

## 8. Multiplicity and overfit control

Propose a bounded first tournament of B0, B1 and one shallow booster; at most twelve preregistered fitted configurations before the first holdout, with technical families charged as a declared family rather than “free” confirmations. Record all manual choices and data-driven exclusions. Discovery families may use BH at 10% with discovery status explicit. The one frozen primary forecast and one frozen primary policy each require their intersection of gates; none can pass by choosing its best metric. Additional separately claimed horizons, sessions, policies and feature-family increments form a Holm family at 5%. Report all tests, including failures. A single untouched final test does not reset the exploratory trial count.

The first tournament admits at most twelve fitted configurations **in total across selected A00–A11 comparisons, not twelve per arm**. An arm is a research comparison, not a tuning allowance. Every distinct searched feature set, learner/hyperparameter setting, fitted calibration or selected threshold variant consumes the declared configuration ledger. Predeclared fold/seed replications are evaluation executions of a registered configuration; record actual fit count and compute cost separately. Selecting among seeds or adding outcome-informed variants creates additional search trials. Enumerate configurations, arm mappings and the full fit schedule before evaluation. Reusing an identical frozen baseline in paired comparisons need not duplicate its configuration and grants no extra tuning. Later waves receive separately frozen budgets while retaining all prior trial history.

White's Reality Check, backtest-overfit probability and deflated Sharpe are diagnostic tools with assumptions, not licenses to reuse an exhausted holdout. PBO over alternative configurations reveals selection instability; its resampling must respect the time-dependence question. Deflated Sharpe is relevant to a sufficiently meaningful strategy return series and trial count, not to an arbitrary classifier AUC. For prediction heads use proper-score uncertainty and the actual trial family. [M08, M06, M07]

Report interval estimates and practical effects; a nonsignificant estimate is inconclusive at its precision, not proof of zero. Distinguish **NON_EVALUABLE** (source/protocol not qualified), **NULL/NO_PROMOTION** (tested construction misses gates), and **UNSUPPORTED_COHORT** (insufficient transfer support).

### Censoring and full-cohort bounds

Freeze missingness handling before tests. A witnessed breach resolves the any-breach target despite a later gap; a no-breach prefix followed by source loss is censored after the last qualified observation. First-event labels are unresolved if a missing interval could hide the first competing event. Native halts, administrative close/expiry, genuine no-trade periods with continuous quotes, and missing feed coverage are separate statuses.

Complete-case scores are labelled observed-coverage estimates only. For unresolved binary labels, compute lower/upper full-cohort Brier, event-rate and calibration bounds by assigning each missing outcome 0 or 1 as appropriate; a paired score difference uses the **same** unknown outcome for champion and comparator. Promotion requires that the asserted gate survives the prespecified conservative bounds, or an independently accepted missingness model/sensitivity envelope. IPCW or censor-aware survival scoring is secondary unless its conditional independent-censoring assumption is supported. Gap-related adverse moves can violate that assumption.

For economic outcomes, carry source gaps into wealth-path/terminal uncertainty. Use an independent qualified source if legitimately available under the frozen policy; otherwise provide defensible bounds or mark NON_EVALUABLE. Do not use a stale last print as a terminal fill. If missing prices leave the proposed utility bound unidentified, the full-population claim cannot pass; a narrower observed-coverage result may still be reported with its selection limits. Report attrition by session, liquidity and adverse-event context.

## 9. Leakage and negative controls

Required tests: append future bars; remove leading history; alter only future data; introduce a late correction; swap raw/adjusted corporate-action vintages; move a timestamp across midnight/DST/early close; erase a source interval; replay snapshots through actual known times; and attempt to pass an outcome field into a feature. Previously emitted causal state must not change except via an explicit newly-known revision.

Negative controls include day-block shuffled outcomes that preserve within-day dependence; permuted event times within carefully matched session/liquidity strata; randomized entry times with matched coverage; and an intentionally future-shifted feature expected to be rejected by the clock validator. A wrong sector is not automatically a valid negative control because cross-sector market information can be real. A randomized label test checks pipeline behavior, not market efficiency.

Use matched early-return, volatility, location and time controls to distinguish “absorption” from merely selecting a favorable return path. Source/venue substitution controls must retain quote semantics. A delay/survival placebo asks whether a supposed exhaustion benefit is explained by having waited without a new low. Recheck every proposed mechanism against chapter 02's kill comparison before registration.

## 10. Prospective and production acceptance

The initial prospective horizon is at least 60 eligible sessions **and** enough independent events for the frozen precision requirement; a calendar duration alone is insufficient. Predictions must be durably timestamped before their outcomes, with source/version/known-time parity, delivery delay and missed predictions counted. No manual edits, selective alerts, after-the-fact feature reconstruction or unlogged model replacement.

The first R3 offline minute cutoff is not a historical delivery receipt. Chapter06's prospective lead-time variant freezes inputs before its reserved window and must be reconstructed/calibrated under that same cutoff. A live decision's simulated order arrival also includes actual consumer delay. Neither a new label version nor operational latency permits moving outcome windows after observing them.

Evaluate drift in source coverage, quote age/continuity, feature distribution, base rate, calibration and policy costs. Drift is an investigation trigger, not automatic permission to retrain into a fresh success claim. A scheduled source or exchange-clock change starts a versioned evidence era. Independent scientific review decides accepted/revise/null/kill; a separate real-path verifier establishes delivery and UI correctness. Neither proves the other.

**Stop the affected claim** if it depends on hindsight, corrected-history availability masquerading as PIT, unresolved executable labels, reused holdout, unsupported probabilities, killed-mechanism rebranding, duplicate ownership or net benefits that disappear under plausible friction. Continue narrower qualified research when possible, recording the precise limitation.
