# Crypto science R5 — what spot participation adds to an observable price response

Date: 2026-09-28. Parent WS:CRYPTO-INTELLIGENCE / draft PR #8050, operation crypto-vector-r2-20260926-sol-001. Baseline `bf879ff6a26d2369d970dc583d89ba2aadab5e62`; protocol committed before outcomes at `3cc4e46d2b7827ba5fce746d5b4bcd1875fb80c6`; implementation candidate `065f29376d82db77342a634496ccd2f4d97d0ab0`. R5 changes research code, tests and continuity only. No live allocation, model default, gate, collector or UI changed.

## Executive decision

No tested policy earns promotion. The study produces a useful distinction between information and redundant confirmation:

- After an hourly breakdown continues for six hours, above-normal spot volume is already present in almost every price-qualified case. The volume condition filters only seven of 171 potential exits and catches no additional downside-first events. Its average incremental economic effect is approximately zero and slightly negative.
- A first hourly recovery pattern reduces waiting materially versus R4's slow daily confirmation, but does not establish better common-endpoint performance than immediate entry or the corrected incumbent.
- Requiring above-normal volume at that SAME first recovery entry improves the paired mean by about 0.72 percentage points, with wide uncertainty and substantial period dependence. It also leaves many more cases in cash. This is a weak research lead, not a high-accuracy recovery model.

A high-volume candle is not evidence of net buying or of limit-order absorption. This study measures same-venue unsigned spot participation plus observable price behavior. It does not measure aggressor-side spot flow, book replenishment or market-wide causal absorption. The next scientific unit must add genuinely distinct information or a better specified probability/decision model, not promote more checked boxes.

## 1. Frozen experiment and measurement boundary

The common parents are exactly R4's 588 hourly D0 breakdowns and 59 daily washouts. Existing hourly/daily source hashes and freshly recomputed parent lists match R4. The corrected incumbent targets are reused from R4's immutable replay sidecar with all its input/source identities checked; they are not a new live signal store or a historical publication certificate.

Primary source is Coinbase BTC-USD hourly OHLCV. Candle t starts at t; its contents cannot be used before t+1h. The official candle documentation distinguishes first trade, last trade, extrema and total bucket volume, and warns that historical intervals may be absent [1]. We use assumed 1h execution delay after information completion, with 6h sensitivity, exact stored opening prices and the same 0/10/25bp turnover-cost assumptions as R4. These are idealized reference executions, not evidence of achievable order fills.

The existing OKX taker collector was inspected. Its request is `instType=CONTRACTS`, `ccy=BTC`, `period=1H`, and it stores buy/sell taker amounts. Thus it is genuine derivatives aggressor data, not Coinbase spot pressure. Its 2,957 observations are not combined with 94,063 Coinbase spot candles or represented as long-history spot absorption. The true-flow extension remains a separate qualification/research task.

### Downside landmark

Six completed hourly bars FOLLOW the breakdown candle. At that landmark, PERSISTENT means price remains below the original prior-72h low and the last-three-hour minimum is below the first-three-hour minimum. RECLAIMED and STALLED_BELOW remain separate; missing required prices are UNKNOWN.

The volume ratio is the average follow-up volume divided by the median of 72 PRE-parent volumes. The trigger candle and follow-up bars cannot raise their own comparison baseline. The single fixed threshold is ratio >=1. It is not optimized. Invalid/missing/negative volume or a nonpositive reference median gives UNKNOWN; genuine zero current volume remains observable.

All accounts begin at R4's original executable origin and share its original 24h endpoint. The new landmark action starts six hours later, leaving 18h for the new first-passage target. Following incumbent until that time versus delaying to cash for all cases isolates waiting from selection. PRICE moves to cash only if persistent. PRICE_VOLUME moves to cash only if persistent AND participation qualifies. Non-actions continue the incumbent. Pre-landmark losses are not credited to R5's predictive ability.

### Early recovery and same-time volume control

After each daily washout becomes observable, search the first 48h for the earliest completed hourly close above the preceding six hourly highs, accompanied by a nonlower recent-three-hour low versus the previous-three-hour low. The first possible issue is seven hours after daily completion. Missing intervening price evidence prevents skipping to a later attractive rebound.

PRICE enters at that first pattern plus the assumed delay. PRICE_VOLUME evaluates volume at EXACTLY the same candidate time: recent three-hour mean divided by the preceding 72-hour median, excluding those three hours. Failing the volume test means staying in cash for the whole parent, not searching for a later successful confirmation. Unknown volume is unavailable rather than a failed signal. Every policy shares R4's 14-day endpoint, so waits and no-entry cases remain in the economic comparison.

## 2. Sample and source integrity

The 647 distinct parent observations generate 1,294 event rows and 3,882 account-scenario rows across delays and costs. Those rows are not independent market events. The 48 fixed period/family/delay/cost summaries all remain in the outputs. Periods are full history, 2016–2019, 2020–2023 and already-used 2024 onward; none is an untouched holdout.

After six hours, downside parents classify as 171 persistent, 227 reclaimed, 189 stalled below and one unknown. There are 586 complete comparable 24h account paths at the primary delay. The early hourly recovery condition confirms 55 of 59 parents; four produce no entry. The volume gate accepts 27 of those 55, rejects 27 and has one unknown measurement. Five washout parents lack complete common 14-day prices, as already recorded in R4.

The matched recovery volume comparison therefore has 53 parents: 49 price entries and 22 volume-approved entries, with the rest retaining cash. The price-only versus immediate/daily/incumbent comparison can use 54 parents. DO NOT subtract means from these different samples and label the result a paired volume effect.

## 3. Downside result: mostly redundant participation

At the primary 1h lag, among 171 persistent price-qualified cases, the subsequent 18h contains 30 downside-first outcomes, 40 upside-first outcomes and 101 neither. Volume qualification retains 164 cases: the SAME 30 downside-first outcomes, 39 upside-first and 95 neither. The fraction rises from 17.5% to 18.3% without identifying an extra true event. These target fractions are neither winning-trade rates nor calibrated crash probabilities.

At 10bp one-way costs, over the SAME 586 complete parent accounts:

| Policy contrast | Mean difference, percentage points of initial event equity |
| --- | ---: |
| Delayed cash for every parent minus incumbent | -0.07556 |
| Price-continuation cash rule minus incumbent | -0.06521 |
| Price + volume cash rule minus incumbent | -0.06699 |
| **Volume incremental effect: price+volume minus price** | **-0.00178** |

The volume contrast's descriptive 90-day-block 95% interval is approximately -0.00452 to +0.00001 percentage points. Magnitude is about -0.18 basis points per parent, not a meaningful positive improvement. Its mean remains negative at both delays and all three costs: roughly -0.00207 to -0.00073pp. In reused 2024+ its primary increment is essentially zero. The paired mean is negative when any one year is omitted; that is sensitivity, not independent replication.

Price progression is a narrower description than the initiating break, but the cash policies still do not establish net value over the incumbent on these assumptions. Their reduced marked drawdown is partly mechanical exposure reduction. We do not conclude that discretionary or risk-averse protection has no value, only that these tested policies have not earned general forecast or sizing authority.

## 4. Recovery result: faster does not automatically mean better

Among complete common-endpoint price entries, median waiting falls to 15h, versus 120h for R4's daily confirmation. The current range is 7–47h. This is a material timing change, not proof of an improved entry.

Over all 54 price-comparable parents, at 1h lag and 10bp cost:

| Price-only early rule versus reference | Mean paired difference |
| --- | ---: |
| Versus immediate entry | -0.98174pp |
| Versus R4's daily confirmation | +0.88536pp |
| Versus corrected incumbent | -1.83246pp |

The early-versus-daily block interval spans roughly -1.15 to +2.87pp. It is not defensible to advertise the positive average as established superiority. The actual seven-day first-passage results after early entries are 11 upper-first, 41 lower-first and three censored windows, plus four no-entry parents. A visibly faster reclaim still frequently precedes further adverse movement.

### What adding volume changes on the SAME 53 parents

| Measure | Price only | Price + volume |
| --- | ---: | ---: |
| Entered parents | 49 | 22 |
| Mean 14-day event-account return | -1.35147% | -0.63144% |
| Mean difference versus incumbent on those parents | -1.62685pp | -0.90681pp |

The co-primary paired volume increment is **+0.72003pp**, with an approximate block95 range of **-1.51734 to +3.13450pp**. It remains a positive mean under both delays and all three cost assumptions (about +0.619 to +0.884pp), but a positive sensitivity mean is not statistical or economic acceptance. The volume policy itself still trails the incumbent on average in the full matched cohort.

Regime dependence is substantial. The primary volume increment is -0.95179pp in 2016–2019, +1.99036pp in 2020–2023, and +2.03924pp in reused2024+. That last cell has only seven complete parents. Removing 2020 from the full calculation changes the mean to approximately -0.00759pp, essentially flat. The remaining-year estimates are not independently sampled replications.

A misleading headline would be 'median drawdown fell to zero.' It did—because the volume policy stays in cash in 31 of the 53 matched parents. In the 22 parents where it actually buys, median within-account marked drawdown is still approximately **13.42%**. Price-only entered cases have about14.67% median marked drawdown. These are different selected entry subsets and not a causal matched proof of safer entry. Cash frequency must accompany any drawdown summary.

The gate also reduces the conditional favorable-first count: across all originally confirmed candidates it has three upper-first versus21 lower-first complete volume-approved windows, with three censored and one unknown volume measurement. Conditional hit fractions alone and common-parent economics answer different questions. Neither supports a 'laser-accurate bottom' claim.

## 5. What this means scientifically

The hypotheses were not rescued by changing volume thresholds, search windows, parent dates, costs or delay after seeing outcomes. The candidate separates a fixed observation from its interpretation: a six-hour stalled/reclaimed state is not automatically absorption; high unsigned volume is not buying; an earlier reclaim is not a confirmed durable recovery.

The next research direction should treat the information blocks differently rather than make the checklist longer. In these downside episodes, typical-volume confirmation is almost always true, so it adds little independent discrimination. In recovery, the gate changes participation in the opportunity set substantially, so its return gain must be separated from simply not buying. Neither result supports a one-number risk score or independent volume-derived sizing authority.

The volume ratio uses a trailing72h reference; that reference can itself contain washout activity and has no hour-of-week adjustment. These are fixed definition limits, not reasons to choose a better-looking reference after the results. A separate experiment could test normalization/continuous information without claiming this threshold was optimized or accepted.

Next substantive scientific phase: qualify actual signed-flow instrument/venue/time semantics, then freeze a continuous-information, regime-aware continuation/recovery model versus these transparent baselines. Require forward probability calibration and a separately specified action-utility test. Coinbase unsigned spot history and OKX CONTRACTS flow must remain separate domains unless a cross-market transmission hypothesis is explicitly defined and qualified. Do not claim unseen resting-liquidity absorption from OHLCV or assign a forecast probability to these observed hit fractions.

Any learner must use chronological training-only selection, mature targets, lagged availability and genuinely fresh issued-forward evaluation before production promotion. Already examined2016–2026 data cannot become a new untouched holdout. A public-data or existing collector qualification step is not authority to change account credentials, buy data or start a second collector/forecast plane. Funding-history equivalence, independent science/code review and release gates remain outstanding.

## 6. Verification and limits

The generating study completed with process51214 exit0. It produced one fixed result set; no market-outcome rerun or hypothesis amendment was needed. Original protocol was committed before outcome calculations. The five first R5 tests failed for the absent module, then passed after implementation; they cover prefix stability, reference-window exclusion, zero/unknown/invalid volume, fixed first-entry behavior, missing chronology and delayed action.

The current combined Vector/Crypto/science suite passed **261 tests,27 warnings**. Compilation, source-scope affirmative-claim checker and diff checks passed. The existing CI step already invokes the test file; no runner or gate was added. Existing warnings remain, not claimed repaired. The larger PR's prior exact-head CI and fences had passed at recovery; this does not establish the R5 head's CI or a live strategy.

An independently expressed condition/account verifier checks every647 parent observation,1,279 mature first-passage paths,3,843 usable scenario-account comparisons, every48 policy summary and the event-group counts. Inventory accounting reuses the independently written cash/coin implementation from R4 rather than the generating weight recurrence. Its extended version also recomputes every reported block interval and checks inherited R4 engine/config identities. This is independent arithmetic by the SAME session, not an independent reviewer.

All54 inherited input identities,18 existing gate files,58 earlier research artifacts and the tested source identities are unchanged. R1 artifacts also remain unchanged in git. No raw price dataset, credentials, font or user portfolio data were published. Research outputs contain derived observations, timestamps and economic diagnostics only. The incumbent sidecar is inherited immutable replay evidence, not new live state.

One recovery parent (2018-05-11) has a price-qualified entry but insufficient volume-reference history; it is UNKNOWN for PV, not a no-buy signal. Five common recovery paths remain incomplete as in R4. Missingness near market stress could be informative, so complete-case results must not be extrapolated to outages. A bounded endpoint diagnostic found zero cases where only the terminal open would cross a barrier after a 'neither' held-bar label. Labels preserve the R4 held-hour convention; terminal open marks the account, not future intrabar extrema.

Operational errors are disclosed: the first long protocol write returned Session terminated; same-carrier readback proved no target file, then one smaller technical write and append succeeded before the protocol commit. An optional gh metadata read encountered a TLS timeout. A later read-only summary-print lambda assumed pandas groupby retained the grouping column and failed; using the explicit group key corrected the display without changing source study or result bytes. None was reclassified as a clean scientific pass or a provider permission grant.

**Disposition:** retain both policies as evaluated research, with no live promotion. The modest full-sample recovery increment deserves investigation only as a fragile, exposure-changing association. The highest-leverage next work is qualified independent information plus calibration/utility, not optimizing a threshold around these few episodes. The parent Crypto/Vector scientific moat and production mission remain incomplete.

[1] Coinbase official candle semantics, reviewed2026-09-28: https://docs.cdp.coinbase.com/api-reference/exchange-api/rest-api/products/get-product-candles . No market/API or account endpoint was called in this document review.
