# R5 — distinguish information speed from trading speed

Date: 2026-10-17. Same research commission, root `rotation-intelligence-census-20261016-sol-c1`, and PR #9507. This design is published before the new simulation. It is not native LR V3, an empirical study, a new detector, or product implementation. The prior R4 blocked source/metadata action and R1 final-review provider403 remain unretried. Discussion readback found no new source-owner disposition. No archive, source-rights flag, trial/seal or production state is changed.

## Consumer question

The user wants to adapt to sector rotation early, before the opportunity is crowded. R3 supplies a fixed-baseline rehearsal; R4 shows that good mean estimates can still make poor decisions under relationship changes. The next independent question is **which part of total delay actually limits an actionable change, and whether faster action earns its extra turnover**. Refresh frequency, information age, signal memory, confirmation and execution are not interchangeable.

No claim of crowding anticipation is made by this experiment. A retrospective price signal can only respond to evidence already reflected in observed prices. A separate forward-looking source must prove incremental information before this conclusion can change.

## A. Exact mathematical witnesses

For a deterministic relative log return that changes from -d to +d, with d>0 and an L-interval trailing sum, the sum after k new intervals is d*(2*k-L) for 0<=k<=L. A strict positive crossover first occurs at floor(L/2)+1. It needs L+1 price observations, not L. This is a property of the specified signal, not a universal market pivot delay.

With source lag D and reviews at a+C*j, first eligible review is the smallest such date no earlier than k+D. For Q confirmations of distinct reviewed source versions, execute at the session after the Qth qualifying review. Repeated polling of a single source version cannot add evidence. A one-session execution delay is separate from each of these delays.

For W=1 invested in A, switching the entire position to B at proportional cost c per traded security dollar leaves V=(1-c)/(1+c). With identical final sale cost, constant relative log advantage delta and H remaining periods, switching beats holding only if H*delta > log((1+c)/(1-c)). These are exact invented-price/cost witnesses, not estimated spreads, an investment recommendation or a sizing formula.

## B. Frozen sequential experiment

### Population, dates and generation

Eleven anonymous synthetic sector assets S00..S10, one synthetic bill-fund proxy and one synthetic equity benchmark. There is no mapping to actual sector returns or price files. Settlement cash is separate from the bill security. Price grid begins at session0; 252 prior observations plus the current session provide warmup. First decision anchor is252, first execution close253, terminal close453 (200 elapsed investment intervals). Review origins end451 for an execution by452; no entry/rebalance at terminal453, only liquidation.

Use 512 independently generated paths with seed20261017, common random numbers across scenarios and policy/cost/lag comparisons. Common daily log noise is stationary Gaussian AR(1), phi=.15 and unconditional standard deviation .006. Sector-specific independent daily log noise has standard deviation .008. Bill-fund log return is .00008 per interval, a synthetic assumption. The equity benchmark's daily simple return is the equal-weight mean of the eleven sector simple returns; it is not a real index.

Base sector log drift is .0001. In the three rotation worlds S00..S02 have an additional +.0012 and S03..S05 -.0006 before the change. The all-equal world has no group additions. From session313 (60 elapsed investment intervals after entry), the switched vector gives S00..S02 -.0006 and S03..S05 +.0012. Other sectors retain the base drift. These are controlled signal-to-noise choices, not fitted effect estimates.

Four complete worlds, none discarded: `no_edge` (all groups equal); `durable` (instant permanent switch at313); `gradual` (linear interpolation from old to new drift over40 intervals beginning313); `headfake` (new drift for12 intervals then old drift returns). No policy sees the latent drift vector or scenario identity.

### Four fixed policies

All use the observed trailing log return of each sector relative to the common equity benchmark, choose the top three (lexicographic index ties), and replace each selected slot with the bill fund unless the sector's trailing return strictly exceeds the bill fund's return. Aggregate bill slots before trading. This is a B4-inspired policy comparison, **not a rewrite or claimed exact replication of the earlier B0..B4 twenty-session study**.

| ID | Return intervals | Review cadence | Distinct consecutive confirmations |
|---|---:|---:|---:|
| slow_review |63|20|1|
| same_signal_fast_review |63|1|1|
| short_signal_fast_review |20|1|1|
| short_signal_confirmed |20|1|3|

At the initial decision each policy establishes its portfolio without an additional confirmation wait. Later candidate targets must satisfy the stated confirmation. All policies use the same twenty-session maintenance grid for rebalancing existing accepted targets; off-grid trades require a changed accepted instrument target. Thus merely looking every day does not force a daily rebalance of unchanged holdings. The reference keeps actual drifted holdings, real trade costs, and common initial/terminal treatment.

Signals use only prices through source anchor t-D; source lag D is either0 or5 sessions. A review after close t sets an order for close t+1. Returns for that next interval accrue to the old holdings before the pending order is executed. Source lag means an observed outdated signal in this controlled experiment, not permission for a production reader to accept stale sources. Unknown/invalid sources in real use remain under the existing source policy.

One-way proportional costs c in {.0005,.0025}, applied per actual traded security dollar, including the bill fund but not settlement cash. These two cases are sensitivity assumptions, not measured transaction costs. Use the R2 self-financing equation and verify any vectorized numerical implementation against the unchanged R2 scalar reference. No impacts, taxes, leverage, shorts, discrete lots or execution slippage are represented.

Total fixed grid: four worlds × two lags × two costs × four policies =64 rows;512 paths per row. No tuning or selecting a winner after the outcomes. Zero-cost/constant-path examples may be used only as additional deterministic software checks, not extra empirical cells.

### Metrics and comparison

Primary diagnostic: mean log terminal wealth difference versus `slow_review` within the same world, lag and cost, with paired Monte Carlo standard error over independently generated paths. Also report mean net terminal wealth, mean maximum drawdown, cumulative security turnover divided by initial wealth, membership-change count and bill occupancy. These Monte Carlo errors describe precision under the declared synthetic generator, not financial statistical significance.

For the two durable/gradual worlds, report first execution-time target placing at least two-thirds in S03..S05 after the known synthetic onset, capped to the end and with non-arrival fraction shown. This is scenario-defined exposure response, not a predicted real pivot. Report delay among arrivals together with censored rate; do not drop failures from the main economic result. For no_edge/headfake the response statistic is not interpreted as successful detection. All no-edge membership changes are reported as churn, not proof every real-world switch would have been a mistake.

## C. Required falsifiers before interpreting results

1. Modify any price after an origin: its signal/accepted target cannot change. Modify the execution interval return: the chosen target is unchanged and old holdings receive that interval.
2. Source delay shifts source anchor, not the execution/valuation clock; later timestamps cannot backdate knowledge.
3. With the same constant ranking, faster review cannot create daily security churn beyond common maintenance.
4. Repeated same source version does not count toward confirmation; an intervening different target resets the streak.
5. Strict cash hurdle, ties, 63 intervals/64 prices, distinct bill and settlement cash, terminal liquidation, and no late entry remain explicit.
6. The vectorized cost solver matches the unchanged reference and conserves wealth; a flat-price round trip cannot create profit.
7. Future scenario labels are used only in evaluation. No function choosing targets accepts world, latent means, onset or future returns.
8. Results remain synthetic/research-only, with no probability calibration, source admission or trading authority.

## D. Architecture implication to test, not assume

A useful live journey should distinguish when new evidence became available, when the evidence changed a view, when a review occurred, and when a permitted action could execute. It should not claim that a minute-level price refresh implies a minute-level long-horizon allocation edge. Confirmation is a noise/delay trade-off, not automatically greater accuracy; repeated stale observations are not repeated independent confirmations. Rebalancing and review cadence are different controls under the incumbent portfolio/evaluation owners.

The initial research remains technical by design so that future macro, revisions, flows and industry-cycle information face a fair benchmark. Faster information must earn its incremental predictive contribution; faster trading must earn net decision value. Neither permits building prohibited rotation×cycle-position gates, RS-dispersion gates, new signal services, alternate evaluators or source replays.

## Primary research anchors and transfer limits

Gârleanu and Pedersen, Dynamic Trading with Predictable Returns and Transaction Costs (Journal of Finance2013; NBER working paper15205). The primary abstract describes partial adjustment with predictors of differing decay speeds. It motivates separating signal lifetime from trading frequency, but this diagnostic neither implements their optimization nor inherits their commodity-futures results. https://www.nber.org/papers/w15205

Novy-Marx and Velikov, A Taxonomy of Anomalies and Their Trading Costs (RFS2016; NBER20721). The primary abstract reports buy/hold spreads as a useful simple mitigation in its tested anomaly strategies. This is motivation for testing delayed/inertial actions, not a sector-specific performance guarantee or a supplied cost estimate. https://www.nber.org/papers/w20721

Ross, Moskowitz, Israel and Serban, Implementing Momentum: What Have We Learned? (AQR2017). The firm's primary summary uses live implementation evidence and makes clear that turnover does not imply impossibility. We therefore test net outcomes rather than assume fast strategies fail. Its specific portfolio results are not imported. https://www.aqr.com/insights/research/working-paper/implementing-momentum-what-have-we-learned

Review depth for these anchors: primary abstracts/summaries. No copyrighted implementation or underlying datasets copied. This document fixes the new diagnostic; substantive deviations discovered before execution must be recorded rather than silently changing the design.
