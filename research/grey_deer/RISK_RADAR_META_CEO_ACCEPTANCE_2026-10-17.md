# Risk Radar / Risk On–Risk Off / Grey Deer — Meta-CEO findings and action map

**Prepared 2026-10-17 for Chairman Chris Wong.** This is a continuation of WS:GREY-DEER-RISK-INTELLIGENCE / MAS-258.

**Disposition: the new descriptive census is accepted within its declared scope; no predictive claim or new policy authority is promoted. The programme has not reached final backend-to-user acceptance.** Useful market evidence exists. Source clocks, warning translation, exact forecast qualification and some consumer semantics prevent the programme from consistently delivering that evidence as an executable, correctly scoped decision.

The existing [continuation masterplan](GREY_DEER_CONTINUATION_HANDOFF_2026-10-11.md) carries the revised sequence. This findings document does not replace the architecture freeze, active carriers, accepted GD-3 evidence or established Portfolio/Prophet policy owners.

## 1. What the dated evidence supports now

The price reconstruction is frozen to Macro **3ab3382af89242c7b7fe8c65360bd883a7dd3504**, with prices through **2026-10-15**. DIA, BIL, SGOV and ARKK end October 14. These are revised current-vintage daily ETF observations, not reconstructed contemporaneous vendor receipts.

At the separately recorded October 16 snapshot, Market State is **40 / RISK_OFF**. The public Macro dashboard inspected October 17 displays that state, “Risk building 83 / Partial read,” and an October 14 sector reading awaiting update. That newer headline does not establish a complete October 16 price, leadership and Envelope bundle. The pinned Envelope remains October 15; its required leadership source is October 14, so hazard is unavailable. Native source dates and the current public display must remain distinguishable. See the [source audit](risk_radar_source_consumer_audit_20261017.md).

At the later main refresh **ab5156a4b2c336181f3c5256e7c0766f04f99598**, the Envelope has advanced to **October 16**, produced October 17 at 04:01:23Z. It still reports **40 / RISK_OFF** with null hazard: leadership remains October 14 and rotation October 15. Its four authority flags remain false. The frozen price/replay evidence above is unchanged; the later source update does not fill its unavailable historical receipt clocks. The [current-source addendum](risk_radar_source_consumer_audit_20261017.md#current-source-compatibility-addendum--october-17) also records another W5 BACKFILL_ASOF refusal.

The current Radar's displayed **22%** 21-session number is accompanied by thin, reconstructed historical evidence: 16 outcomes among 66 overlapping matched origins, with a source-reported 90% interval about **5%–45%** and precision_grade:false. Its separate state-only rate is 16% versus a 17.8% base. Preserve those different targets and qualifications; neither the score nor a copied percentage establishes a precise, executable forecast.

### Dated exposure comparison

Returns are total return; drawdowns use split-adjusted, dividend-unadjusted price. All percentages below are from the pinned census, rounded; trailing drawdown uses 63 reference sessions.

| Exposure | 5-session return | 20-session return | Drawdown | Evidence interpretation at October 15 |
|---|---:|---:|---:|---|
| SPY | −0.28% | +1.46% | −0.94% | Broad capitalization-weighted price damage remains small. |
| RSP | +1.48% | +1.17% | −3.49% | Improving relative participation; incomplete evidence of healthy broadening. |
| DIA — October 14 | +0.90% | +0.31% | −5.01% | Separate stale date; do not fill October 15. |
| IWM | −0.90% | −3.63% | −9.84% | Material small-cap damage; slightly below its own 200-session average. |
| QQQ | −2.62% | +1.65% | −4.17% | Acute deterioration coexists with positive monthly performance. |
| XLK | −4.34% | +0.72% | −6.34% | Technology damage has crossed the descriptive 5% threshold. |
| SMH | −7.98% | −0.32% | −11.84% | Semiconductor damage is substantially greater than SPY damage. |
| SOXX | −8.62% | −0.85% | −12.69% | A second ETF shows the same semiconductor pattern; this is not an independent market episode. |
| XLP | +3.91% | +4.50% | −0.88% | Recent absolute gains and relative defensive strength. |
| XLV | +5.37% | +5.37% | 0.00% | Recent absolute gains; at its 63-session high. |
| XLU | +1.41% | +0.64% | −10.02% | Deep residual damage; the defensive label does not establish preservation. |
| HYG | −0.01% | −1.58% | −3.49% | Credit ETF price context; not a credit-spread or funding-stress measurement. |
| TLT | +2.70% | −1.82% | −5.07% | Recent duration rebound with residual loss and rate sensitivity. |
| GLD | +1.08% | −3.93% | −10.60% | Recent rebound has not repaired substantial prior damage. |

Source: [all case origins](all_date_census/v1/september_october_origins.csv), [relative comparisons](all_date_census/v1/september_october_rotation.csv), [immutable input and output hashes](all_date_census/v1/manifest.json).

The October 13–15 contrast is particularly informative: SPY −0.80%, SMH −4.98%, XLK −3.61%, XLP +2.96% and XLV +4.44%. XLU lost 0.52% while outperforming XLK by 3.20% on the ratio. That utilities comparison is “falling less.” Price ratios establish neither subscriptions/redemptions nor investor transfers.

The most defensible description is **selective defensive divergence alongside acute technology/semiconductor damage and continuing weakness elsewhere**. Healthy broadening is not established while small caps and utilities remain damaged. A concentrated-deleveraging mechanism is unproven without positioning, leverage and transaction evidence. Systemic contagion is unproven without suitably timed cross-exposure, credit/funding and common-factor controls. These alternatives remain testable pathways rather than labels selected from the desired narrative.

### Ranked action map

This ranking is the urgency of an evidence review, not a Prophet score or numerical allocation. It is dated to the sources above. Numerical allocation, trade admission, hedging instruments and execution remain with the existing policy owners. A forecast withheld for lack of evidence cannot be replaced by a guessed allocation.

| Priority / exposure | Horizon | Supported action | Entry or continuation condition | Invalidation / what changes the view |
|---|---|---|---|---|
| 1 — SMH, SOXX, XLK and directly verified holdings exposed to them | Next session to 5 sessions | **Protect; review reductions under the existing concentration and exit rules. Avoid unqualified averaging down.** Damage and short-horizon acceleration are observed. | Fresh member-level and price evidence; an existing owner-authorized entry rule must qualify any new capital. A recovered average or rebound alone is insufficient. | Further closing lows, wider member damage and funding/credit deterioration strengthen the defensive case. Durable price repair, improved internal breadth and a cost-qualified recovery signal would weaken it. |
| 2 — IWM and other damaged cyclical/high-beta exposures | 5–21 sessions | **Reduce or hold cautiously as existing mandates require; watch propagation.** Small-cap damage undermines an indiscriminate broadening thesis. | Verify company, factor and liquidity exposure rather than treating the ETF label as a complete holding map. | Repair across several distinct exposures supports containment; expansion of damage supports escalation. |
| 3 — SPY / QQQ broad exposure | Next session to 21 sessions | **Review broad exposure against the owner's currently admitted policy state. Apply the existing hold/reduce rule only if its exact trigger and freshness qualifications pass; protect concentration under applicable standing rules.** The October 16 measured state and October 15 price structure answer different questions. | Reconcile the current source bundle before applying a fresh broad-market instruction. Do not infer a calibrated crash probability from Radar intensity. | Broad price/breadth breaks plus timely credit/funding stress strengthen systemic escalation. Sector repair without broad deterioration supports containment. |
| 4 — Cash, bills and short-duration parking choices | Immediate to 21 sessions | **Consider the existing liquidity reserve route for risk removed elsewhere.** It does not require an unvalidated claim that a risky defensive asset will rise. | Confirm current quotes, instrument/mandate suitability and the owner's cash policy. BIL/SGOV observations stop October 14; their 20-session returns are approximately +0.30%/+0.29%. | Source staleness, liquidity/vehicle constraints or a qualified re-entry opportunity change the choice; no allocation fraction is inferred here. |
| 5 — XLV and XLP | 5–21 sessions; reassess over 20–63 | **Watch for qualified additions or defensive rotation.** They have both recent positive absolute returns and relative strength. | Fresh absolute trend, exposure concentration and execution-cost checks; the existing entry owner must admit the trade. This case alone does not validate the strategy. | New closing lows, loss of recent repair, earnings impairment or widening credit damage weakens the view. A ratio that rises while price falls loses the preservation interpretation. |
| 6 — RSP / DIA | 5–21 sessions | **Hold/watch as broadening comparators.** RSP improvement is useful; DIA needs a current observation. | Confirm breadth across sectors and small caps with consistent clocks. | Broadening fails if the equal-weight improvement reverses or remains an isolated rebound within damaged exposures. |
| 7 — XLU | 5–21 sessions | **Avoid treating utilities as automatic capital protection.** Relative strength is currently weaker evidence than the sector name implies. | Require absolute repair and rate-sensitive exposure qualification before a defensive addition. | Continued absolute losses invalidate a preservation claim even if XLU continues to beat technology. |
| 8 — TLT, IEF, LQD, HYG | 5–21 sessions; macro context 20–63 | **Use only the existing rate/credit-specific hedge or holding policy.** Separate duration, credit and cash-like instruments. | Verify current real yields, curve, spread/funding and liquidity evidence; ETF prices do not substitute for those series. | Inflation/rate repricing can damage duration; spread/funding deterioration can damage credit. A broad defensive basket is not assumed. |
| 9 — GLD | 5–21 sessions | **Watch; avoid claiming preservation from a rebound.** Its 63-session drawdown is still about 10.60%. | Fresh absolute repair, currency/rate context and existing mandate admission. | A new low or renewed adverse real-yield/currency condition weakens the hedge thesis. |
| 10 — China/HK and other country exposures | Local session to 21 sessions | **Respect native country warnings; reconcile them with the traded vehicle.** FXI/MCHI/EWH can rebound while native local risk remains high. | Local calendars, currency, benchmark, rights and release clocks must match. EWC/EWJ/INDA/EEM are USD-traded proxies, not native country market states. | Broader regional damage, funding/FX stress or failed repair raises concern. Native-source improvement with independent price repair supports a qualified reassessment. |

No company-specific reduction/addition is authorized here without current holdings, member-level source qualification and existing policy admission. Historical country, factor, theme and company coverage beyond this declared ETF census remains incomplete.

### Existing company and theme evidence

The existing Leadership Crack monitor gives finer detail than the ETF census. Its **October 14** snapshot reports **CRACKING**, median drawdown **−20.86%**, and **90.48%** of its 42 tracked AI-hardware members at least 10% below their 63-row highs. Its six deepest native drawdowns are ICHR −50.07%, CBRS −46.01%, UCTT −45.99%, CRWV −38.94%, CRDO −36.63% and WDC −34.76%.

These values use auto-adjusted basket closes and today's tracked cohort, unlike the ETF census's price-only drawdown basis. The loader permits short forward fills before its freshness test; **42 fresh does not establish 42 raw same-session observations**. It does not export per-member raw source dates, and missing drawdown support can dilute its share denominator. These are dated observations that justify checking directly exposed holdings, not remaining-loss forecasts or company-specific trade admission.

The undated subsector state has **269** keys that exactly match the producer's companion payload: declared observation **October 14**, rebuilt **October 16 at 23:23 UTC**. That establishes a recoverable declared date, not original availability. Its return quadrants do not establish flows or historical theme membership. Existing quarantined weekend-derived records and four July ledger gaps remain preserved. Exact formulas, blob pins, qualifications and producer references are in the [company/theme audit addendum](risk_radar_source_consumer_audit_20261017.md#additional-company-and-theme-qualification--october-17).

## 2. September–October reconstruction: what existed and what could have been said

The case contains two different phases. On September 1, semiconductor drawdown was already severe. A strong September rebound followed. October then brought a renewed break, while staples and health care improved. Treating September–October as one uninterrupted warning-success story would erase the rebound and produce hindsight bias.

| Price origin | Revised price facts | Artifact versions selected by Git committer timestamp at or before the next-session 09:30 New York research cutoff | Defensible communication |
|---|---|---|---|
| Sep 1 | SPY drawdown −2.07%; SMH −18.49%; XLK −6.42%; XLU −8.06%. | Market State 74 / Risk On; Radar 56 / watch, ungated watch. | Broad strength coexists with pre-existing exposure damage. This is acute recognition, not evidence of advance warning. |
| Sep 15 | SPY −2.63%; SMH −18.96%; IWM −6.54%; XLU −10.74%. | Market State 61 / Risk On; Radar 51.4 / caution, unclamped. | Damage is uneven and extends beyond technology. Keep broad regime and exposure impairment separate. |
| Sep 30 | SMH 20-session return +11.70%; 63-session drawdown −0.33%. RSP/IWM/XLU drawdowns are −6.62%/−8.92%/−14.80%. | Market State 54 / Mixed; Radar 93 / caution, ungated risk-off, clamped. | A semiconductor rebound does not establish broad repair. The selected artifact exposes high Radar intensity while the selected legacy-banner artifact contains alert:null; publication and subscriber visibility are unverified. |
| Oct 8 | SPY −0.66%; SMH −4.20%; XLK −2.09%; IWM −9.02%; XLU −11.28%. | Market State 51 / Mixed; Radar 72.9 / caution, ungated risk-off, clamped. | Weakness in breadth and damaged exposures deserves scoped observation even without a broad-index break. |
| Oct 12 | SMH crosses the descriptive 5% damage threshold again, at −6.77%. | Radar 70.3 / caution, ungated risk-off, clamped. | A renewed semiconductor rolling-threshold damage reading is observable at the close; the older anchored drawdown remains unresolved. A next-open user warning would recognize existing damage; preemptive credit requires an earlier issued signal. |
| Oct 13 | SMH drawdown −7.22%, five-session return −7.02%, but 20-session return +8.49%; SPY drawdown −0.14%. | Market State 50 / Mixed; Radar 73.9 / caution, ungated risk-off, clamped. | Short-horizon deterioration and positive monthly momentum coexist. Show the horizon explicitly. |
| Oct 14 | SMH −10.91%; XLK crosses 5% damage at −5.73%; SPY −1.22%; IWM −11.05%. | Market State 44 / Mixed; Radar 87.9 / caution, ungated risk-off, clamped. | Escalating sector damage deserves actionable owner review. Systemic spillover remains a separate hypothesis. |
| Oct 15 | SMH −11.84%, XLK −6.34%, SPY −0.94%; XLP/XLV strengthen. | Market State 46 / Mixed; Radar 88.2 / caution, ungated risk-off, clamped. | Describe selective defensive divergence and the competing containment/escalation conditions. Do not infer fund flows or remaining downside. |

The selected legacy banner versions have **alert:null** at all these anchors. The replay contains 128 artifact/date records over 32 case dates and 122 distinct artifact versions. It preserves exact commits, blobs and content hashes. The initial extraction selected the wrong native spelling for ungated state; a dated addendum recovers **state_ungated** from the exact same blobs. The original output is retained.

**Knowledge limit:** a recorded Git committer clock is not a push receipt, data-ingestion receipt, subscriber delivery time or executable price. Those clocks are null in this reconstruction. The next-open cutoff is an analytical convention. Revised prices establish what a properly sourced descriptive system could calculate; they do not prove what Mastermind or a subscriber actually knew then. Current-vintage data also cannot reconstruct historical constituent membership. No claim of executable warning lead time is accepted.

The October 15 window is right-censored for subsequent broad-market damage. “Sector damage appeared before an observed SPY threshold crossing in the available case” cannot become “the model led a subsequent crash by N days.”

### A rolling peak is not an episode recovery

SMH's 63-session drawdown fell from **8.52% on September 28 to 0.33% on September 30**, while price rose approximately 1.50%. Part of that improvement came from older highs leaving the lookback. SMH remained **8.96% below its 252-session high** on September 30. On October 15 the corresponding 252-session drawdowns were **16.46% for SMH and 21.42% for SOXX**.

Retain rolling-lookback damage for its declared purpose, and separately preserve the anchored episode peak, recovery hurdle, underwater duration and failed-recovery history through the existing lifecycle owners. Rolling-window clearance cannot itself authorize re-entry. See the peak-aging records under [all_date_census](all_date_census/).

![September–October exposure paths](all_date_census/risk_radar_september_october_2026.png)

## 3. The missing historical census now has a reproducible first vertical

The protocol was committed before the new outcome calculation: **ea26bc964314a80badcb29d836acfde06475f8d4**; protocol SHA-256 **317cd3b906438aa30995fb6a7bd24854af4c0cc83d094eb0726be35c045d3153**. The real run used code commit **4a06cd4a6b323312d2a59d6130efdb60997fe149**, executed October 17 at 05:26:04 UTC.

### Scope and denominators

- **36 declared ETFs**, spanning broad US indexes, all 11 SPDR sectors, selected subsectors/themes, rates/credit/bill/gold instruments and country proxies.
- **8,486 SPY-reference sessions**, January 29, 1993 through October 15, 2026.
- **305,496 exposure/date rows**, including 213,005 observed rows, 92,487 pre-source rows and four post-source rows. Pre-inception/unavailable history is retained, not backfilled.
- No within-coverage gap on the declared reference lattice; no common-intersection-only deletion or forward fill. Eligibility requires valid support in both declared price bases.
- The existing rule calendar differs by seven historical dates; the separate calendar qualification memo explains the closure evidence and its custody limits. The original lattice and outcomes are unchanged. This is not an independently certified census of every exchange worldwide.
- One large-return audit observation is retained: XLE on March 9, 2020, approximately −20.14%. The audit threshold is not evidence that the market move was a data error.

Five-, ten- and 21-session outcomes use the existing adverse-excursion implementation and T12 sampling method. The target is at least 5% maximum future total-return-close loss from the origin over the stated future window; recipient-event annotations are known only after their outcome support exists.

| Horizon | Eligible origins | Positive outcome origins | Negative outcome origins | Recipient episodes | Pooled overlap-support groups |
|---|---:|---:|---:|---:|---:|
| 5 sessions | 212,825 | 13,480 | 199,345 | 1,403 | 68 |
| 10 sessions | 212,645 | 27,920 | 184,725 | 1,400 | 19 |
| 21 sessions | 212,249 | 50,100 | 162,149 | 1,018 | 4 |

**None of these columns establishes an independent crisis count.** Recipient episodes cannot be summed as independent market events. Pooled support groups also do not prove independence. Every output explicitly leaves verified independent episodes unavailable.

Across this mixed 36-exposure universe, 74,964 observed dates meet the descriptive 5% damage definition. **41,142 of those damage-days, or 54.9%, occur while the SPY-below-200-session-average component is off.** This is evidence that a broad-price gate can omit existing exposure damage. It is not evidence that removing the full incumbent gate improves trading outcomes: the actual gate also uses a breadth percentile-rank condition, and its live/historical missing-data behavior differs.

The 21-session comparison further exposes the tradeoff. Among 209,880 comparable origins, requiring damage plus the SPY component reduces flagged dates from 74,552 to 33,822 and flagged dates without further 5% loss from 48,385 to 19,498. It also increases unflagged positive-loss origins from 23,399 to 35,242. These are overlapping historical associations, not calibrated warning precision, costed policy results or independent event counts.

The simple stabilization candidate is not a validated entry rule. Its competing-path labels include 16,331 gain-first, 12,715 loss-first, 20,707 neither and 144 immature observations. Repeated daily origins, costs, gaps and path definition prevent interpreting those counts as independent profitable trades.

### What this census still lacks

Every eligible date is covered **within the declared proxy universe and reference history**. The census does not complete historical company membership, native country calendars, factor portfolios, intraday executable prices, macro release vintages, historical options/positioning depth, actual flows or prospectively issued warnings. It does not automatically label a long-lived leadership change. The existing five-episode atlas and historical studies remain explanatory evidence rather than an independent predictive test.

All inspected history is now development/exploratory evidence. There is no untouched historical final holdout left by declaration. Newly fitted models: **zero**. Promoted predictive claims: **zero**. Stage-1 and stage-1b were not rerun; stage-1b's **0/12** passing claims and the previously rejected downside/probability challengers remain intact.

## 4. Real system gaps, ordered by decision consequence

| Capability | Status and consequence | Required next proof |
|---|---|---|
| Independent measured state, Envelope qualifications and authority flags | **Working with explicit limits.** Preserve raw measured blend, caps, null hazard and four false authority flags. There is no V0 competent TRANSMITTING/BREAKDOWN source. | Additive exposure semantics must preserve existing consumers and all independent field qualifications. |
| Source clocks and publication bundle | **Material gap.** October 16 Market State, October 15 Envelope/prices and October 14 leadership can coexist. A build timestamp cannot make them synchronous. | Source session and availability survive every hop; unsupported joint inference is withheld without erasing valid dated facts. |
| Broad confirmation gate | **Working as a gate; exposure adequacy unproven.** The breadth condition is a 40th-percentile rank of percentage-above-200 over a rolling history, not “40% of members.” History/live fallbacks differ. | Compare systemic escalation and exposure alerts separately at matched warning burden, using exact incumbent rules. |
| Warning publisher and long-open Macro banner | **Broken or lossy for the requested scope.** Main is US risk-off only; alert:null conflates calm, suppression, missing data and failure. Held #8132 also has a native projection/client seam. Boot fetch does not refresh an open page. | Original owner repairs one publisher, qualifications, expiry, focus/visibility refresh and authenticated paint; no duplicate publisher. |
| Asia delivery | **Source exists; subscriber delivery unproven.** The inspected source/upload schedules imply a minimum configured wait near 5h57m after an October 13 Git source point. This is not measured delivery latency. | Native region/calendar entitlement, actual artifact availability and browser receipts. No public exposure of premium feeds. |
| Portfolio consumers | **Working advisory Envelope; legacy semantic losses remain.** Family validation is not exact forecast calibration. Intensity becomes a field called confidence; native elevated is omitted in held-risk mapping; some paths lose clocks. | An unchanged-policy comparison receipt, then owner-qualified corrections and prospective parity. Runtime entry-gate activation remains unattested. |
| Terminal | **Working source bridge and refreshing disclosure; incomplete current production proof.** Copilot drops some admitted null-hazard failure/date details. | Preserve reasons through explanation and witness real current production. Existing local-synthetic proof is labelled as such; prior accepted GD-3 natural proof remains accepted. |
| Prophet / GD-9A / GD-10 | **Specified or census-only.** No live board-hash-bound eligibility sidecar or new Portfolio adapter is established. | Build through the existing ownership and cutover gates while preserving raw ranks, numerical outputs and counterfactuals. |
| Forecasting and re-entry | **Unproven for new claims.** Forward log absent at the source pin; refusal records include BACKFILL_ASOF and CLOCK. | Legitimate prospective issuance, maturity, independent evidence, calibrated incremental value and costs. No backfill masquerading as foresight. |
| Paper product | **Existing craft inspected; current writes unavailable.** p1 1-0 and p6 A5I-0 remain the design references. The adapter catalog is not accepted for write. | Restore actual adapter qualification before editing; then use the existing designs and complete live evidence, not a new mockup. |

The [source audit](risk_radar_source_consumer_audit_20261017.md) supplies exact functions, formulas, source links and consumer consequences. The [proposed contract annex](risk_radar_architecture_contract_20261017.md) separates environment, vulnerability, current damage, propagation, future loss, recovery and action eligibility per exposure and horizon. It grants no new authority.

## 5. Research and execution decisions

The [research programme](risk_radar_research_protocol_20261017.md) is a proposed protocol awaiting an immutable execution packet from the existing owners. It is not a claim that unspecified inputs, utility thresholds or trial permissions are already accepted. It preserves the frozen Grey Deer studies, T12, existing T13/T14/T19 drafts and their unspent budgets.

The primary-source review supports a restrained ladder: empirical-frequency and price/volatility baselines; limited, timely breadth/credit additions; then a small number of declared interactions. Change points and connectedness can be useful diagnostic challengers, but do not acquire causal or predictive authority by their sophistication. Proper scoring, calibration, dependent uncertainty, actionable lead time and decision costs remain separate acceptance gates. See the [methods review](risk_radar_turning_point_methods_20261017.md) for primary academic and institutional references and limitations.

The highest-value safe next work has already progressed from the census to exact recorded-version recovery, calendar qualification and the rolling-peak recovery counterexample. The next programme verticals are source-clock/bundle qualification, exposure descriptors, original-owner warning delivery and authenticated Macro/Terminal proof. Predictive data readiness must not indefinitely delay qualified descriptions of existing damage. Conversely, descriptive usefulness cannot be used to promote a predictive or execution claim.

### Preserved custody and refusals

No work was transplanted from the active #9428 branch. Its documented commit, CSS and findings-write refusals remain in force, as do the QLedger/nightly owners of the GH001 publication blockage. #8721 remains a live original writer; #8132 remains the original warning carrier; #9440 and #9457 retain their own scopes. The held incident note and the old China recovery carrier are not overwritten or blindly retried.

The native scientific review found and the parent repaired dual-basis support, invalid-SPY-history handling, outcome-origin naming and imported-method hash binding in the new census. Twelve targeted tests passed. A separate Fabric worker proposed invalid independence and availability interpretations; those recommendations were rejected and its packet was **not accepted**. Test success does not imply scientific promotion or product delivery.

The final source/release receipt is recorded separately after repository checks. Full programme acceptance still requires correctly qualified intelligence reaching entitled users and relevant consumers at measured clocks, plus genuinely prospective evidence for any new predictive or recovery policy.


## T13 admission result — 17 October 2026

The next safe research phase has been executed as a metadata-only intake, with [full result and bindings](all_date_census/T13_METADATA_ADMISSION_2026-10-17.md). The pinned initial-release store contains both H1/H2 series, but STLFSI4 is absent for the first **348 of 1,321 reference sessions**; the first admissible session is November 18, 2022. Term-premium data arrive in multi-observation release batches, so the next executable protocol must select the latest eligible release and latest observation within that batch. Source bytes and the collector are hash-bound; no feature–outcome join or fit occurred.

**Research execution remains unadmitted.** The upstream FRED model-use disposition is unresolved despite a downstream “recorded” label; the actual Massive RAW SPY bytes and T12 canonical sample digest are not reverified; and the daily-origin/estimator/calibration packet is not frozen. Current Sol owns methodological decisions. These are specific source and execution gaps, not an absent external methodology owner. The original T13/T14/T19 drafts and budgets remain unchanged. Historical leave-one-episode-out cannot by itself prove chronological executable lead.
