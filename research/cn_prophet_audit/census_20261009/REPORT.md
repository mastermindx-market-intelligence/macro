# China Prophet: deep census, performance autopsy and upgrade decision

**Research commission completed: 9 October 2026. Candidate-quality improvement remains unproven.**

Canonical implementation observed: `mastermindx-market-intelligence/macro` at **`3d90aad6d83152dfeeaf8345bc995826ac9d3139`**. Protected Mastermind procedure: **`326c8469a21d7f50fc9ecb1848196bf1c6e66685`**. Macro's main branch was reported `protected:false`; this report does not describe it as protected. The isolated research carrier is **[Draft/HOLD #8714](https://github.com/mastermindx-market-intelligence/macro/pull/8714)**. Existing R0 safety replay **[#6871](https://github.com/mastermindx-market-intelligence/macro/pull/6871)** retains its ownership and unresolved gates.

## A. Executive diagnosis

China Prophet has substantial working infrastructure, but the inspected product has **not demonstrated dependable stock-selection advantage**. Its current output is a technically qualified, mostly reversal-oriented priority list. A high displayed score is not a calibrated forecast of excess return or a probability of success. The intended intelligence ordering is inactive in the October 9 artifact, the historical comparison does not establish that activating it improves returns, and several data and recording seams prevent a stronger causal verdict.

The public-data H10 result can be reproduced: **133 benchmark-relative winners out of 289 matured V4 episodes, 46.02%, with mean excess −0.2221 percentage points**. A descriptive date-cluster 95% interval is **[−1.2233, +0.6719] pp**, over only **21 admission dates**. This supports “advantage not demonstrated.” It does not establish statistically significant underperformance, prove zero alpha, or identify the percentage of losses caused by each defect. The arithmetic and limitations were independently reviewed. [Historical evaluation](HISTORICAL_EVALUATION.md), [review](HISTORY_REVIEW.md).

The most consequential proven selection mechanism is a global coverage fallback. **Four unavailable intelligence observations among 1,601 scored names force the entire board back to the V3 heuristic.** All 164 names counted as signal-buyable are intelligence-covered; the four blockers cannot currently compete for a featured slot. On the same 125 names already qualified before caps, preserving the 24-name and four-per-sector caps, the intended intelligence order shares only **four of the current 24 featured names**. This is a large, reproduced effect on selection. Its return effect remains unknown. [Ordering experiment](ordering_diagnostics.json), [independent review](ORDERING_REVIEW.md).

The evaluation record has equally material weaknesses. V4 and V3-shadow contain **683 identical date/ticker/rank/score observations**, so their matching performance is not a test of distinct rankers. **39 of 683 V4 board rows** disagree with the same-date candidate featured lane, with **21 score disagreements**. Re-deriving entries from the current price files changes the win/loss sign of **16 of the 289 matured V4 episodes**. Date-only historical records do not certify what a user could see before an assumed entry. These defects need repair before any new score is awarded investment authority. [Historical evidence](historical_evidence.json).

**Decision: repair the existing foundation and selectively replace its unvalidated scoring assumptions after controlled evaluation.** Rebuilding the collectors, intelligence bus, theme system, candidate store, grader or publication machinery would duplicate useful owners. Adding a larger language model would leave the demonstrated faults intact.

The five highest-priority corrections are:

1. **Bind every published recommendation to one immutable decision snapshot.** Reconcile original candidate, board, entry and outcome vintages through the existing R0 and tracking owners. Preserve the original record and name corrections separately.
2. **Make the evaluation clock and execution assumptions explicit.** Stock and benchmark intervals must match; signal marks, feasible fills and unresolved trades need distinct labels. Acquire the missing benchmark opening-price history through the existing price owner.
3. **Repair the actual nightly-to-intraday roundtrip.** The canonical path, lane schema, score/rank fields and scheduled reconciler inputs currently disagree. Prove the repaired behavior with the real artifact and one recorded event through the existing ledger.
4. **Qualify intelligence by decision time, then evaluate the coverage policy and intended order.** Retain valid measured zeros, legitimate slow-moving facts and explicit unavailable evidence. Do not switch ranking policy merely because a missingness repair changes the shortlist.
5. **Establish a prospective, comparable ranking and abstention evaluation.** Test the current score against simple alternatives on identical admissible names and dates. Let release count be evidence-dependent, including zero, while measuring opportunity cost and coverage as well as hit rate.

Items 1–3 and the publication-error repairs can improve correctness immediately after implementation and verification. Better candidate returns, improved timing, event alpha and calibrated abstention require evidence that this commission does not manufacture.

## B. How the product actually selects and publishes stocks

### The funnel is narrower than “Chinese stocks”

The configured search universe unions the top 800 Sina A shares above a 30亿元 market-cap floor, CSI300 and CSI1000 constituents, and eight explicit extras. It covers Shanghai and Shenzhen suffixes; Beijing is deliberately excluded. The current membership file has **1,716 names**, of which **910 have an exact 30亿元 placeholder**, not a measured capitalization. Full scoring normally requires at least **300 valid daily observations**. Less seasoned names can remain searchable with limited records but cannot enter the normal board. These are real coverage constraints; no recovered historical universe proves how much return they exclude. [Census](MECHANISM_CENSUS.md), [source refs C1–C4](SOURCE_INDEX.md).

The responsibility screen rejects recognized ST names, measured cap below the floor, measured low liquidity, stale price histories and non-stock instruments. Unknown cap or liquidity can pass the broad screen; featured qualification subsequently requires measured ADV of at least **0.5亿元, or CNY50 million**. This distinction matters when interpreting “eligible.” The October 9 artifact reports **1,601 scored**, **180 raw eligible**, and **164 signal-buyable** names. The final lanes contain **24 featured**, **124 more-actionable**, **16 late-or-unfillable** and **16 forming**. Its 156-name `watch` field aliases the last three lanes; it is not another 156 unique opportunities. [Pipeline evidence](pipeline_evidence.json).

### Raw signals are technical state machines

The signal gate combines a latest marker/quality path with a separate multi-timeframe confluence cascade. A valid cascade can restore eligibility after a blocked quality marker; these are not two cumulative filters. RSI, RSI-MACD and StochRSI conditions on native two- and three-session buckets establish T1–T4 states. T3 projects the current negative two-day MACD histogram slope toward zero within 1.5 native bars and requires persistence. It is a deterministic extrapolation, not a learned expected-return forecast. T4 can be raw eligible without being buyable. [Census, raw-gate addendum](MECHANISM_CENSUS.md), [C5–C7](SOURCE_INDEX.md).

Quality confirmation may require later bars. A centered swing definition also needs its later confirmation bars. Those mechanisms do not prove live look-ahead when the decision waits until confirmation; replaying them at the earlier marker date would leak future information. Marker time, last input session, confirmation time and first actionable time must remain separate. The current China builder explicitly stamps the full `input_asof`; a compact serializer omission elsewhere does not establish that today's featured names all have stale signal dates.

### The displayed priority is a fixed weighted score

The V3 score is the sum of six bounded components:

| Component | Maximum points | What it rewards |
|---|---:|---|
| Signal | 30 | Tier, provisional status and limited native-bar age adjustments |
| Entry | 20 | A fixed status ladder; `bounce_wait` and `wait_pullback` outrank `buy_now` |
| Runway | 15 | Fuel and limited extension |
| Bottom quality | 10 | Star/coiled/washout classifications |
| Reversal membership | 10 | Sector-relative reversal membership |
| Theme timing | 15 | Membership and early/late cycle or oscillator state |

Component points are rounded to four decimals, summed and clipped, then the total is rounded to two. V3 orders descending by total and then ticker. The entry ladder gives `bounce_wait` 1.0, `wait_pullback` 0.95, `hold` 0.8 and `buy_now` 0.7. It reflects older exploratory cohort findings; it is not a current calibrated preference estimate. Quality, residual alpha, setup, low volatility and risk sizing have **zero direct score authority** in this formula. [Exact formula and qualification](MECHANISM_CENSUS.md), [C8–C12](SOURCE_INDEX.md).

V4 retains admission but intends to order by intelligence interest, then V3 score, then ticker. Its intelligence score combines existing alternative-data or radar evidence, remaining edge, a falsifier adjustment and a bounded desk-gap modifier. It deliberately excludes the board's own score and membership as evidence. The input is the full alternative-data population, not just the displayed top 30. Some underlying alternative-data family weights adapt through validation scorecards, so the whole estate is not wholly static. No fitted, calibrated end-to-end stock-return predictor was found in this path. [C13–C18](SOURCE_INDEX.md).

The October 9 effective mode is `v3_coverage_fallback`, because 1,597 of 1,601 scored names have valid measured intelligence. Measured zero is valid; missing or malformed evidence disables the entire intelligence order. The present four blockers are 600606.SS, 000069.SZ, 600038.SS and 603899.SS. Three are not raw eligible; one is forming and not buyable. The behavior follows the current written coverage contract. Changing its scope is a versioned policy decision, even though the counterexample exposes an undesirable coupling to non-competing rows. [Ordering controls](ordering_diagnostics.json).

### Publication is a constrained shortlist with a secondary lane

Featured admission also requires a fresh signal, an accepted entry status, confirmed-late safeguards, liquidity, known extension state, current microstructure and positive fillability/no-chase evidence. Extended or non-entry candidates are routed away. A late relay position has a specific featured demotion; the previously rejected blanket chase veto is not reinstated. The first qualified names under the chosen order fill at most 24 slots with at most four per sector. **Twenty-four is a cap, not a compulsory quota**; the current score has no calibrated confidence-to-release-count policy.

At **21:08:14 UTC on October 9**, the actual public dashboard returned HTTP200. Its **24 featured cards matched the pinned artifact's names and order**, and its **124 overflow cards matched the template's V3-score order**. Thus the observed featured page is not a manually selected alternative to this artifact. The template re-sorts the overflow by heuristic score, which could conflict with producer intelligence order after activation. This one receipt establishes server-rendered membership/order only. The authenticated JSON routes returned HTTP401; page JavaScript, installed intraday version and actual live-event writes were not observed. [Publication receipt](publication_probe.json).

## C. What the history can and cannot establish

### The reliable conclusion is weak demonstrated evidence

The accessible board ledger contains **5,108 rows across 60 recorded dates and eight definitions**. The candidate ledger contains **67,731 rows across 42 dates**. Long price files exist, but they do not create a long point-in-time recommendation history. V4 spans August 18–October 9, with 683 board rows and 431 contiguous-membership episodes. The public October 8 header contains 413 episodes; October 9 adds 18 new, unmatured episodes, leaving 289 matured. [Historical evaluation §1](HISTORICAL_EVALUATION.md).

| Production H10, same 289 matured V4 episodes | Positive benchmark excess | Mean excess |
|---|---:|---:|
| Stored entry latch | **46.02% — 133/289** | **−0.2221 pp** |
| Current price-file entry re-derivation | **44.64% — 129/289** | **−0.2131 pp** |

Sixteen individual signs change despite the nearby aggregate means. Across all definitions, current entry re-derivation differs on 933 of 2,632 latch-bearing episode rows, covering 656 unique date/ticker pairs. This proves a vintage/basis disagreement; it does not identify the vendor or corporate-action cause. Original latches must remain intact. Both rows above still use current-at-pin exit data, so reproducing the header does not certify the whole original economic record. [Latch reconciliation](historical_evidence.json).

A separately defined diagnostic enters at the next benchmark-session close and exits **h sessions after entry**, requiring the stock and benchmark on exact matching dates. The benchmark is the stored **510300.SS CSI300 ETF proxy**, not the index's own total-return series.

| Elapsed sessions after next-session-close entry | Episodes | Admission dates | Mean stock return | Mean benchmark excess | Positive excess |
|---:|---:|---:|---:|---:|---:|
| 1 | 398 | 28 | −0.0261% | +0.2014 pp | 48.49% |
| 3 | 365 | 26 | −0.7286% | −0.0223 pp | 45.21% |
| 5 | 345 | 25 | −0.7807% | +0.2332 pp | 47.54% |
| 10 | 288 | 21 | −1.3820% | +0.1637 pp | 49.31% |
| 20 | 158 | 11 | −2.0490% | +1.0607 pp | 46.84% |
| 60 | 0 | 0 | Unavailable | Unavailable | Unavailable |

The H10 excess interval is **[−0.4612, +0.8430] pp**. The direct numerical-rank IC is **+0.0778**; because rank 1 is best, a negative value would be favorable. It is not evidence of useful current ordering. Using the CSI500 ETF proxy instead reduces H10 mean excess to **+0.0168 pp**, also with an interval spanning zero. A same-158-episode comparison across all supported horizons also produces intervals spanning zero. Higher H20 means do not establish the right holding period. [Historical evaluation §2](HISTORICAL_EVALUATION.md).

Production H10 uses a different entry and endpoint convention. The two H10 results cannot be subtracted to measure benchmark-clock bias. The pinned 510300 file has **3,491 rows with close and volume only**; a controlled opening-price benchmark correction has no usable opening observations. HL2 entries also lack a unique intraday timestamp. This is a precise missing-data gate, not permission to invent corrected alpha.

### The fairer ranking experiment rejected an attractive premature story

Five rankers were compared on identical cap-qualified, feature-complete names and **11 common dates**, selecting **six names per date** under the same sector cap. Selection was frozen before checking outcomes. An unresolved selected name was not replaced. These are fixed-six research comparisons, not the actual full 24-name portfolio or executed trades.

| Ordering | Mean CSI300-proxy excess | Difference from score | Paired descriptive 95% interval for difference |
|---|---:|---:|---:|
| Current score | −0.3162 pp | Reference | — |
| Stored intelligence baseline | −0.5631 pp | −0.2469 pp | [−2.9316, +2.5478] |
| Momentum | −0.0030 pp | +0.3132 pp | [−2.3039, +2.9634] |
| Reversal | +0.5177 pp | +0.8339 pp | [−1.1930, +2.6146] |
| Quality | −0.5851 pp | −0.2689 pp | [−3.1329, +2.4673] |

Each arm has **66 selected observations**. Every paired interval crosses zero. This stored-intelligence baseline breaks ties by ticker; the exact intended production policy additionally breaks ties by V3 score. A separate historical check of that intended tie-break changes no selected name or order on these 11 dates, so the 29/66 wins and −0.5631 pp mean are unchanged. The current-artifact permutation also uses the exact source policy. A broader incomplete-feature reversal comparison appeared stronger, but the stricter common-cohort comparison does not confirm a stable gain. No alternative earns promotion from this commission. Date-cluster intervals are descriptive: they do not fully account for serially overlapping returns, repeated issuers, multiple testing or the scarcity of different regimes. [Historical evaluation §3](HISTORICAL_EVALUATION.md), [review](HISTORY_REVIEW.md), [rank-metrics addendum](RANK_METRICS_ADDENDUM.md).

Precision@6 on the same 11 complete-selection dates is **42.42% for score, 43.94% for intelligence, 50.00% for momentum, 50.00% for reversal and 46.97% for quality**. The separate top-decile diagnostic selects `ceil(0.1 × original pool size)` without a sector cap. It uses ten complete-pool dates, 35 selected observations per arm and 320 full-pool observations. The score's date-weighted mean excess is **−0.1273 pp**, versus **+0.2012 pp** for the same full pools: **−0.3285 pp return lift**, with descriptive paired interval **[−2.8919, +2.1094] pp**. Score, intelligence, momentum and reversal intervals span zero. The quality decile has **−1.3127 pp lift**, with interval **[−2.2262, −0.2421] pp**: an adverse result to retain, subject to the same overlap, small-cohort and unadjusted multiple-comparison limitations. Precision lift and return lift are reported separately; none of these tests demonstrates a reliable positive improvement. September 1 remains valid for the six-name comparison but is excluded from full-pool lift because one original pool member has an unresolved outcome. These K, cap and date differences prohibit a direct aggregate league table between the six-name and decile results. [Full selection receipts and metrics](RANK_METRICS_ADDENDUM.md).

Other requested analyses are bounded explicitly. Sector/liquidity matching could populate 82 of 102 top-six alternative slots, with complete six-slot coverage on nine of 17 dates; no distinct-name matched-random strategy result is claimed. Current quality and trailing-return missingness reduces comparable coverage. A certified point-in-time valuation baseline is unavailable. Close-based adverse excursion is reported as a nonpositive close-path mark, not intraday MAE or portfolio drawdown. Portfolio volatility, net execution returns and terminal delisting recovery cannot be reported without a defined accounting policy and the missing execution/security histories. Current V4 H10 regime labels are overwhelmingly one state: 269 of 288 observations in `Q4`. No credible bull/bear/crisis league table is supported.

The four case autopsies deliberately show extremes: rank-one Henan Yuneng on September 14, Fuerjia on August 18, Apeloa on September 16 and Wankai on August 20. Their stored features, entries and subsequent paths are preserved. The latched H10 excesses range from **−19.1701 pp** to **+25.2415 pp**. No contemporaneous event archive was joined, so company news or policy is not asserted as the cause. Representative causal attribution would require that archive and original publication snapshots. [Cases and limits](HISTORICAL_EVALUATION.md#5-four-selected-extreme-candidate-autopsies), [full case records](selected_case_records.json).

## D. Ranked root-cause register

Priority below reflects confidence, scope and dependency value. It is not a regression-derived allocation of investment losses. “Verified” means the stated mechanism or record condition was observed; future return improvement can still be unproven.

| Priority / failure | Evidence and affected population | Selection or measurement effect | Remedy, isolating test and confidence |
|---|---|---|---|
| **P0 — Decision snapshots are not coherently joined** | 39/683 V4 board rows outside same-date candidate featured lane; 21 score differences; no historical UTC publication timestamp | Candidate features can describe a different bake; apparent alternatives and replay knowability become unreliable | W0/E0: one immutable publication identity, reconcile original rows and quarantine unresolved periods. **Verified integrity defect; return contribution unidentifiable.** |
| **P0 — Entries and label clocks are inconsistent** | 16/289 V4 win/loss flips; 933 changed latch-bearing rows across definitions; benchmark has no opening data | Reported hit rate and individual outcomes depend on basis; executable alpha cannot be certified | W1/E1: preserve originals, explicit corrected view, identical stock/benchmark intervals, raw legal inputs. **Verified measurement effect; isolated benchmark bias unavailable.** |
| **P0 — Nightly-to-live integration breaks** | True artifact reader gives zero frozen rows at both actual and expected paths; wrong lane and score/rank schema; scheduled pack argument unused; committed live ledger has zero rows | Frozen context and intended confirmation feedback are not demonstrated through the scheduled source path | W2/E2: real canonical artifact through pack/evaluator/reconciler and existing durable sink. **Verified source failures; deployed frequency and financial harm unmeasured.** |
| **P1 — Global intelligence fallback depends on non-competing names** | Four unavailable out of 1,601; all 164 signal-buyable covered; controlled overlap 4/24 | Intended order is wholly disabled; 20 featured names change under fixed qualification/caps | W4/E3: preregister coverage population and compare same-basis shadows. **Verified large selection effect; superior outcomes unproven.** |
| **P0/P1 — Intelligence lacks a decision-time contract** | 1,210/1,637 valuation observations older than seven calendar days, 793 older than 30; 15/23 matched featured valuations older than seven | Latest joins erase clocks and cannot support historical availability claims; legitimate slow facts and stale fast facts are mixed | W3/E4: per-source publication/first-seen/revision/expiry, decision cutoff, weight vintage. **Verified contract gap; age alone is not invalidity and current fallback limits rank harm.** |
| **P1 — Priority assumptions lack current independent validation** | Fixed 30/20/15/10/10/15 weights; raw states mainly technical; positive direct H10 rank IC; common comparison inconclusive | Attractive technical setup is not proven relative-return quality; point scale can be overinterpreted | W4/E5: source-faithful one-term omissions, common-cohort baselines, future untouched evaluation. **Mechanism verified; which term harms returns remains unresolved.** |
| **P1 — Universe and seasoning constrain discovery** | 1,716 search names; 910 placeholder caps; 300-bar scoring floor; Beijing excluded | Some younger/smaller opportunities never reach ranking; missing cap can distort size interpretations | W5/E6: contemporaneous funnel/miss audit and status-aware matched coverage test. **Coverage constraints verified; opportunity cost unquantified.** |
| **P2 — Company intelligence is present but not earned as ranking evidence** | Full alternative-data path exists; visits explicitly cannot feed Prophet/rank; contracts metadata lacks verified materiality; communiqué wiring remains draft | A sophisticated estate does not imply a qualified stock-level predictive feature | W6/E7: one sourced first-disclosure event family, lineage and extraction tests before incremental return tests. **Capability/authority boundaries verified; alpha hypothetical.** |
| **P3 — Regime-conditioned selection and calibrated abstention unvalidated** | Small, concentrated V4 regime sample; release capped at 24 without calibrated risk/coverage mapping | A fixed heuristic may be inappropriate across regimes, but current history cannot identify a better conditional policy | W7/E8: simple prespecified regime interactions and coverage/quality curves, including no-release states. **Hypothesis, not proven failure.** |
| **P0/P4 — Degraded publication can misstate freshness or ordering** | Fallback accepts schema/definition without age admission; overflow re-sorts score; some HTTP errors can retain prior chips | Users can see an old or differently ordered state on those source paths | W8/E2: current-time fallback check, payload-to-DOM order, autonomous chip expiry under HTTP500. **Source behavior verified; current featured HTML was fresh and matched.** |

The individual score omissions also show structural sensitivity without claiming improved returns: deleting signal, entry, runway, bottom quality, reversal membership or theme timing leaves respectively **23, 21, 20, 23, 20 and 18** of today's 24 names. Removing the sector cap leaves 18 and raises Basic Materials from four to ten. These tests verify how constraints change membership. They do not justify deleting the cap or a feature. The independent review caught and corrected component-rounding differences before acceptance. [Ordering results](ordering_diagnostics.json).

### Hypotheses the investigation does not endorse

The current official calendar owner already prioritizes complete exchange notices. The current raw microstructure owner already implements the July 6, 2026 main-board ST limit change. The China builder already stamps current signal input dates. The intelligence join already uses full rows. There is some indirect feature-family feedback. These are positive findings; assigning the present disappointment to their absence would be wrong. The intentional context-only CIE firewalls are evidence boundaries, not broken wiring to bypass.

The current public featured page matched its producer. Stale valuations alone do not demonstrate stale current ranking, because intelligence ordering is inactive. A deterministic technical score is not inherently incapable of alpha. These distinctions prevent an upgrade program from spending effort on disproven or overgeneralized diagnoses.

## E. China-native requirements and the proposed V2 architecture

“V2 architecture” here is the commission's conceptual next design. It does not rename or roll back the existing `cn_prophet_v4` record definition.

### China-specific corrections and constraints

Use effective-date raw reference rules for the board and security status. The SSE notice raises main-board risk-warning stock limits from 5% to 10% effective July 6, 2026; the current source already reflects that change. The 2026 SZSE rules distinguish main-board 10%, ChiNext 20% and relevant no-limit listing periods. Adjusted prices are not a lawful substitute for raw price-limit references. Current ST exclusion must be shared with the live path, whose driver does not presently invoke the intended nightly tradability screen. [Official mechanics M1–M4](CHINA_MARKET_AND_RESEARCH.md), [C29](SOURCE_INDEX.md).

T+1 limits resale of newly purchased A shares; it does not make all midday purchases equivalent to next-open entry. The timing system must distinguish detection, permitted purchase, earliest lawful sale, suspension and actual fill feasibility. A limit-up print is not proof that a purchase order would fill. Corporate actions and basis changes require consistent vintage accounting. Existing price, calendar, microstructure and R0 owners should implement these contracts together.

Domestic sessions and Stock Connect access are separate calendars. The actual universe excludes Beijing, so adding it is a separate scope decision with 30% mechanics and suitable historical data, not an assumed current defect. Stock Connect eligibility and investor access need to be explicit when making an accessibility claim. HKEX's public northbound holdings publication is quarterly following its August 2024 change; it cannot support an invented current daily net-flow factor. A/H and supply-chain relationships should be timestamped explanatory or experimental features with exchange/security identities, not automatic return forecasts. [Market memo M5–M12](CHINA_MARKET_AND_RESEARCH.md).

Official Chinese-language disclosures, earnings updates, IRM replies, contract events, operating indicators and policy announcements are useful source capabilities. They need first-publication time, issuer identity, reporting period, correction chain, economic denominator and an explicit distinction between observation and inference. “Company disclosed a contract” is not yet a material positive surprise. Public visits and attention are not verified institutional positioning. The settled private TuShare compliance decision remains satisfied; technical entitlement, schema, lag and quota checks still apply without requesting private paperwork again.

### Reuse seven responsibilities through existing owners

| Responsibility | Existing implementation to reuse | Repair or introduce inside it |
|---|---|---|
| **Discovery** | China universe and price collectors; library builder; existing setup/continuation owners | Contemporaneous membership/status and funnel receipts; explicit history/coverage limits; separately evaluated continuation versus reversal opportunity families |
| **Intelligence** | China extras, alternative data, Hub, CIE bus, Special Situations, IRM and disclosed-event producers | One decision-time source contract; one initially context-only event family; preserve provenance and negative evidence; no board self-feedback |
| **Ranking** | `engine/china_board_rank.py` and existing candidate shadow store | Explicit horizon/objective, versioned coverage basis, simple benchmark models; preserve score versus predicted return distinctions |
| **Timing** | Signal/entry engines, China microstructure, existing Prophet-live CN path | First-known/first-actionable clocks, raw feasibility, T+1-aware exits and actual scheduled reconciliation |
| **Qualification** | Current signal and featured safeguards | Refuse unsupported inputs; measured missingness and uncertainty; evidence-qualified release count, with neutral zero-candidate states |
| **Explanation** | Existing China builder, templates and card work | Source-backed thesis, why now, entry status, invalidation, freshness and uncertainty; keep company quality separate from stock price and trade timing |
| **Evaluation** | Board/candidate/latch/track/audit owners and #6871 | Immutable publication lineage, corrected views without overwrite, real distinct shadows, matched controls, delayed labels and outcome/coverage monitoring |

No new service, feature platform, candidate database, grader, queue, ownership hierarchy or tactical portfolio engine is needed. Use the existing China-system, thematic and Prophet responsibilities; Prophet stops before position sizing.

### Which research is worth applying

The primary-source review covers cross-sectional factors, learning-to-rank, conditional/regime methods, document event extraction, earnings response, company graphs, uncertainty and abstention. It does not transfer a paper's backtest into a product promise. Historical China factor results and a 2026 preregistered follow-up warn that market segment, sample and economic explanation matter; institutional abstracts were accessible for those sources, not their full texts. Author-reported data-pipeline corrections in MASTER also reinforce why preprocessing and validation custody need explicit checks. [Research memo R1–R14](CHINA_MARKET_AND_RESEARCH.md).

The most plausible next research is inexpensive and falsifiable: simple sector-relative reversal/momentum/quality controls; one source-time-qualified earnings or material-event feature; and abstention evaluated on a coverage-versus-quality curve. Their advantage is operational fit and testability, not demonstrated alpha. Learning-to-rank and modest nonlinear interactions follow only when the baselines and leakage controls work. Temporal routing, graph models and large multilingual predictors have greater data, maintenance and leakage burdens; introduce them only against the same frozen controls after the simpler alternatives earn or fail their case. Modern language models may know events after a historical test date; historical news replay needs original source snapshots and explicit model-knowledge controls.

## F. Experiment and acceptance program

[EXPERIMENTS_AND_ACCEPTANCE.md](EXPERIMENTS_AND_ACCEPTANCE.md) defines E0–E8 with hypotheses, datasets, methods, thresholds, leakage controls, shadow evidence and rejection conditions. The ordered evidence gates are:

1. **Integrity:** all accepted publication rows join one decision generation; unresolved history remains explicitly ungraded. No old entry is overwritten.
2. **Semantics and execution:** same stock/benchmark interval, declared endpoint convention and earliest lawful exit; unavailable fills are not wins or substituted candidates.
3. **Real integration:** the actual canonical JSON survives pack and scheduled reconciliation with exact frozen fields, one idempotent durable event and truthful degradation.
4. **Scientific comparison:** freeze selection before labels; identical candidate/date/feature coverage; retain missing selections; use primary horizon and controls chosen before observing the next holdout; purge overlapping horizons and account for repeated issuers and clustered dates.
5. **Promotion:** improvement must exceed a pre-agreed economically meaningful net hurdle with uncertainty and downside/coverage constraints, reproduce across time blocks, and survive prospective shadowing. The suggested +0.25 pp H10 hurdle is a **proposal for ratification**, not a measured effect. Ten/thirty/sixty-basis-point drags are **cost scenarios**, not claims about actual fees or fills.

All present history has now been examined. It cannot be relabeled as an untouched holdout. A future chronological interval or a separately reserved, documented dataset is required. No arbitrary “80% win rate” or guaranteed return target is adopted. Negative results are part of acceptance: the comparable baseline experiment is a reason to withhold promotion, not to silently change the hypothesis.

## G. Engineering handoff and continuous proof

[IMPLEMENTATION_HANDOFF.md](IMPLEMENTATION_HANDOFF.md) specifies W0–W8, concrete source paths, current owners, existing PR dependencies, observability, release gates and rollback. Its sequence is **W0/W1 integrity → W2 actual delivery and P0 portions of W8 → W3 source clocks → W4 comparable ranking → W5/W6 discovery and one event family → W7 adaptation and calibrated abstention**. Source capture for W6 can proceed context-only while evaluation is repaired.

The first pickup is the existing R0 carrier #6871 at its freshly re-read head, using this dossier to reconcile publication and entry vintages. Its rejected 172/172 and healthy-shadow assertions remain rejected; the `.SZ` original-basis dispute is unresolved. Current CIE/TOI and card carriers are listed with observed states in the handoff. This work extends the earlier global-fallback/leadership discovery rather than claiming first discovery. Existing killed constructions and source-authority limits remain intact.

Continuous improvement should be visible in the existing telemetry: counts at each funnel stage; source coverage and age; effective order and fallback reasons; identical-versus-distinct shadow membership; release/entry/outcome timestamps; unresolved and corrected labels; common-cohort excess returns, precision at fixed K, rank quality, downside, concentration, churn and coverage; and actual intraday confirmation consumption. Separate data unavailability, abstention, unfillable opportunities and genuinely poor predictions. Review new definitions on fixed chronological cohorts instead of mixing versions and regimes into a more flattering headline.

### Commission closure against the eight required questions

| Question | Evidence-backed answer |
|---|---|
| How are stocks chosen today? | A restricted SS/SZ universe, technical gate/cascade, fixed priority score, intended but currently disabled intelligence order, hard qualification and 24/four-sector caps; actual featured HTML matches. |
| How poor is performance fairly measured? | Production-latch H10 is 46.02% positive relative outcomes and −0.2221 pp mean; intervals span zero. Matched close diagnostics and simple comparable alternatives do not establish dependable advantage. Full executable PIT alpha is unavailable. |
| What specifically causes disappointment? | Global fallback demonstrably changes selection; record, fill and integration defects demonstrably impair evaluation or delivery. The fraction of poor returns caused by each cannot be identified from these vintages. |
| Which China properties are mishandled or ignored? | Execution/benchmark clocks, original adjustment basis, live screen parity and source publication/availability need repair. Current holiday and ST-rule owners already handle the specific inspected updates. Scope/access/Connect and disclosure-vintage distinctions must remain explicit. |
| Which existing capabilities may help? | Existing price/calendar/microstructure owners, full alternative-data and CIE producers, native setup/timing paths, candidate/track stores and product infrastructure. Reuse them under measured source-time and promotion contracts. |
| Which upgrades demonstrably improve quality? | **None demonstrates robust return improvement here.** Structural corrections and exact arithmetic/integration failures are demonstrated; candidate-quality proposals remain hypotheses. |
| What is the highest-confidence sequence? | Preserve/reconcile originals, fix clocks and actual delivery, qualify source time, then evaluate coverage/rank alternatives, one event family and conditional abstention through existing owners. |
| How will real improvement be measured? | Immutable issue records, distinct same-cohort shadows, frozen selection before labels, realistic execution/cost bounds, chronological holdouts, uncertainty, coverage and downside gates, and existing continuous outcome monitoring. |

The commission's A–G investigation, evidence, negative results, limits and implementation program are complete. The carrier remains Draft/HOLD for research review and repository checks. No live selection algorithm, production dataset, published recommendation, deployment or trading action was changed by this investigation. Better future candidate quality remains an outcome to earn through the specified repairs and experiments.
