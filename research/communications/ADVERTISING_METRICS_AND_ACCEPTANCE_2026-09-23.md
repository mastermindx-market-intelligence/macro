# Communications Phase 2 — Metric Definitions and Acceptance Research

**Operation:** `gmi-communications-research-20260923-sol-001`. **Carrier:** Macro #7794. **Research date:** 2026-09-23.

This is an original research/design companion to `ADVERTISING_PROFIT_CAPTURE_RESEARCH_2026-09-23.md`. Its source identifiers resolve to that chapter's primary-source register. Requirements below are proposed for the existing owner contracts, not an installed schema, a new data store, a finalized implementation plan or executed application tests. The shared sector template remains with its incumbent owner.

## 1. Comparison eligibility before arithmetic

Before interpreting a change, compare entity/business scope, metric definition, unit/currency, fiscal period, consolidation perimeter, accounting basis, geography, denominator and information vintage. A calculation can be arithmetically correct and economically invalid.

For research purposes, describe a comparison as exact, explicitly bridged, directionally informative, or unavailable. These are descriptive proposal labels, not new runtime enums. A directional peer observation must not appear as an exact same-company surprise. A bridge must show its assumptions and unresolved components. A missing field is not evidence of equality.

The candidate observation requirements are: existing issuer/security identity references; business/activity scope; source/locator; value and unit; period start/end; publication time; observation time; source revision; definition version; denominator population; geography basis; reported/forecast/model status; original-versus-revised status; and any rights/display restrictions supplied by the existing owner. Do not mint a second identity or clock authority to satisfy this list.

## 2. Thirty metric contracts to resolve

| ID | Metric / business question | Required interpretation and denominator | Principal failure to reject |
|---|---|---|---|
| AM01 | Advertising revenue | Disclosed business scope, net/gross basis, currency and quarter | Whole-company revenue called advertising revenue |
| AM02 | Gross media spend | Advertiser spending executed through a defined platform | Confused with net platform revenue or market size |
| AM03 | Gross billings | Amount billed/collected for defined obligations | Treated as economically retained fees |
| AM04 | Net economic fees | Contracted/platform revenue after explicitly relevant pass-throughs | Every revenue increase called pricing power |
| AM05 | Reported take rate | Exact numerator and eligible spend denominator; presentation history | An accounting reclassification interpreted as higher bargaining power |
| AM06 | Ad impressions | Served/displayed population and counting method | Assumed viewable attention or unique people |
| AM07 | Search paid clicks | Disclosed property scope and counting method | All queries treated as paid clicks |
| AM08 | Average price per ad | Issuer-defined revenue divided by delivered ads | Called the price of a comparable unchanged unit |
| AM09 | CPC / CPI | Matching revenue and click/impression population | Google Search and Network metrics combined |
| AM10 | Audience MAU / DAU / DAP | Accounts versus people; average versus ending period; eligible activities | Cross-company audience sums treated as unique people |
| AM11 | ARPU | Geographic revenue divided by the issuer-defined average population | Quarter-end users substituted for average users |
| AM12 | Engagement | Time/activity cohort, population and session definition | Monetizable impressions assumed without evidence |
| AM13 | Ad load | Ads per specified unit of eligible engagement | Ad load multiplied again after impression growth already embeds it |
| AM14 | Customer-count retention | Starting cohort and definition of a retained customer | Confused with dollar retention or stable expenditure |
| AM15 | Comparable-cohort spend | Same clients, reporting scope and observation window | New-client growth conceals incumbent cohort weakness |
| AM16 | Attributed conversion / ROAS | Attribution model, window, outcome and revenue basis | Attributed conversions called incremental customers |
| AM17 | Incremental outcome / return | Experimental or identified counterfactual, uncertainty, spend and contribution basis | Observational association presented as causal proof |
| AM18 | Marginal return | Increment from additional expenditure, not the original campaign average | Average ROAS extrapolated indefinitely |
| AM19 | Traffic acquisition cost | Specific distribution/partner payments and accounting definition | All content and serving costs assumed included |
| AM20 | Contribution ex-TAC | Issuer's non-GAAP reconciliation and period | Compared directly with another firm's revenue or gross profit |
| AM21 | Platform operations expense | Supplier components, hosting, depreciation and other inclusions | Entire increase equated to one reclassified component |
| AM22 | Operating income | Reported scope including shared/unallocated costs where applicable | Segment margin assigned to undisclosed product lines |
| AM23 | Adjusted EBITDA | Issuer-specific reconciliation; stock compensation and other exclusions | Treated as GAAP operating income or cash flow |
| AM24 | Cash from operating activities | Statement-of-cash-flows definition and quarter/YTD basis | EBITDA-minus-capex metric substituted under a similar label |
| AM25 | Capex and capitalized development | Cash/noncash, lease principal, software and asset coverage | Every issuer assumed to use identical FCF deductions |
| AM26 | Depreciation / useful life | Estimate vintage, affected assets, current benefit and cash distinction | Lower depreciation called a cash saving |
| AM27 | Working-capital conversion | Gross collection/payment obligations and timing | Receivables divided by net revenue used as a universal collection metric |
| AM28 | Diluted per-share economics | Matched attributable earnings and diluted instrument claims | Buyback authorization treated as executed dilution reduction |
| AM29 | Guidance / consensus | Kind, source, original/revised vintage, same metric and horizon | Floor given a fictitious midpoint; GAAP versus adjusted surprise |
| AM30 | Product/catalyst milestone | Announced, test, available, adopted, paid, financially material | Later product launch used to explain earlier results |

These definitions define a research diligence queue. They do not assert all thirty measures are disclosed for each company or already collected by Mastermind. Unreported quantities remain unavailable. Proposed models may use scenarios, but scenario outputs must never be stored as reported facts.

## 3. Twenty-four checked arithmetic fixtures

Amounts below are USD millions unless a dimension is explicitly a rate. Values are research calculations rounded to six decimals where useful for reproducibility, not estimates precise to six decimals. Sources are the same chapter's register. The downloadable JSON is an export of these research examples, not a live dataset or competing state owner.

| Case | Inputs / operation | Checked result | Required label / limitation |
|---|---|---:|---|
| P2-01 | Meta 59363 / 60801 × 100 [M1] | 97.634907% | Advertising revenue share, not AI exposure |
| P2-02 | (1.14 × 1.12 − 1) × 100 [M1] | 27.680000% | Rounded price/volume reconstruction |
| P2-03 | Meta 18775 + 2400 + 1180 [M1] | 22355 | Mechanical add-back sensitivity |
| P2-04 | (22355 / 20441 − 1) × 100 [M1] | 9.363534% | Sensitivity versus prior reported profit, not normalized growth |
| P2-05 | 22355 / 60801 × 100 [M1] | 36.767487% | Sensitivity margin only |
| P2-06 | (60801 / 59500 − 1) × 100 [M1,M3] | 2.186555% | Midpoint reference; actual inside 58000–61000 range |
| P2-07 | (63271 / 54190 − 1) × 100 [G1] | 16.757704% | Search & other reported growth |
| P2-08 | (1.13 × 1.03 − 1) × 100 [G2] | 16.390000% | Rounded paid-click/CPC bridge |
| P2-09 | (7303 / 7354 − 1) × 100 [G1] | −0.693500% | Network reported revenue change |
| P2-10 | (0.88 × 1.13 − 1) × 100 [G2] | −0.560000% | Higher CPI with falling impressions |
| P2-11 | Alphabet 39069 − 44924 [G1] | −5855 | Consolidated CFO less PP&E cash; not Search-only |
| P2-12 | 16179 / 81629 × 100 [G1,G2] | 19.820162% | Blended TAC ratio, not gross margin |
| P2-13 | (715.057 / 750 − 1) × 100 [T1,T3] | −4.659067% | Below original guide floor, not consensus surprise |
| P2-14 | (241.279 / 260 − 1) × 100 [T1,T3] | −7.200385% | Versus approximate original EBITDA guide |
| P2-15 | 715.057 − 184.333 [T1] | 530.724 | Research subtotal, not reported gross profit |
| P2-16 | (530.724 / (694.039 − 150.980) − 1) × 100 [T1] | −2.271392% | Subtotal change, not isolated organic economics |
| P2-17 | (694.039 / 682 − 1) × 100 [T1,T4] | 1.765249% | Q2 2025 result versus original 2025 guidance |
| P2-18 | 101.577 − 4.6 [T1,T2] | 96.977 | Reverse depreciation-estimate benefit sensitivity |
| P2-19 | (189.595 / 161.956 − 1) × 100 [MG1] | 17.065746% | Company-defined ex-TAC growth |
| P2-20 | (189.595 / 181 − 1) × 100 [MG1,MG2] | 4.748619% | Above original guide ceiling, not consensus surprise |
| P2-21 | 97.133 / 189.595 × 100 [MG1] | 51.231836% | CTV share of company ex-TAC, not market share |
| P2-22 | 880 / 1180 × 100 [P1] | 74.576271% | Approximate U.S./Canada revenue share from rounded values |
| P2-23 | 106 / 640 × 100 [P1] | 16.562500% | Ending MAU share, not the ARPU denominator |
| P2-24 | 762 / 805 × 100 [R1] | 94.658385% | Rounded ad share; other revenue not all AI licensing |

The local arithmetic check initially rejected a hand-entered expected value for P2-16. Independent Decimal arithmetic confirmed −2.271392242831810...%; the expected value was corrected and all twenty-four cases rerun. Source inputs and tolerance were not weakened. Twelve additional synthetic boundary sanity checks cover range/floor semantics, unlike cash labels, missingness, basis mismatch, average versus ending populations, pure reclassification cancellation, event chronology, budget conservation and post-campaign leakage. These checks do not execute Mastermind product behavior.

## 4. Thirty-two proposed adversarial acceptance cases

Each case below is a required design behavior to map into existing owners and later test on the real path. **None is marked as an executed application PASS in this research.** The cases are grouped by investor harm rather than implementation file.

### Meaning and arithmetic

| ID | Input / challenge | Required result |
|---|---|---|
| APA-01 | “AI beneficiary” plus only whole-company revenue | No invented AI revenue share; disclose missing allocation |
| APA-02 | Matching price/volume growth rounded to whole percentages | Qualified bridge with rounding tolerance, no fabricated exact match |
| APA-03 | Price rises while volume falls | Explain both; do not auto-label pricing strength |
| APA-04 | Gross billings and net revenue appear together | Preserve separate meanings and units |
| APA-05 | Supplier cost moves from netted revenue to expense | Flag comparability; no automatic take-rate-power conclusion |
| APA-06 | Depreciation falls after useful-life change | Separate accounting benefit from cash saving and business growth |
| APA-07 | Legal/severance add-back sensitivity | Clearly modeled sensitivity; no silent normalized EPS |
| APA-08 | Receivables reflect gross collections but sales are net | Do not apply a naive peer DSO comparison |

### Population and scope

| ID | Input / challenge | Required result |
|---|---|---|
| APA-09 | Retained customers with lower same-client expenditure | Count retention and spend direction remain separate |
| APA-10 | Audience ending count and average ARPU denominator | Use actual definition; do not force ending-count reconciliation |
| APA-11 | User geography differs from client billing geography | Preserve both bases; no false geographic comparison |
| APA-12 | One issuer has Search, video, Cloud and other businesses | No Search-only interpretation of consolidated equity cash flow |
| APA-13 | Overlapping platform audience counts | No unique-person sum without a qualified deduplication basis |
| APA-14 | Content licensing discussed but financial amount undisclosed | Document relationship; materiality remains unknown |
| APA-15 | Buying and selling intermediaries report different measures | Role-aware context, no unsupported share-transfer claim |
| APA-16 | Public company classifications or securities unresolved | Existing identity owner or explicit unresolved state; no fuzzy admission |

### Expectations and chronology

| ID | Input / challenge | Required result |
|---|---|---|
| APA-17 | Actual above midpoint but inside guidance range | “Within original range,” not “beat guidance” |
| APA-18 | Guidance says “at least” | Lower-bound comparison; no fictitious upper bound/midpoint |
| APA-19 | Adjusted expectation versus GAAP actual | Withhold beat/miss until a valid basis bridge exists |
| APA-20 | Newly refreshed cache contains carried estimate | Sweep timestamp does not become original estimate publication |
| APA-21 | Original and revised guidance both exist | Preserve both vintages and identify the comparison used |
| APA-22 | Result period ends before a product launch | Launch cannot explain the prior result; forward catalyst only |
| APA-23 | Updated article postpones one feature but not others | Supersede exact affected scope, not entire program or no scope |
| APA-24 | No dated consensus record | Useful business analysis continues; consensus surprise unavailable |

### Causality, rights and investor workflow

| ID | Input / challenge | Required result |
|---|---|---|
| APA-25 | Attributed conversions rise | No causal incrementality claim without identification evidence |
| APA-26 | Post-campaign feature used in a forecasting study | Exclude from ex-ante cohort or label the task retrospective |
| APA-27 | Model trained on privileged experimental targets | No claim public-company data can reproduce its validity |
| APA-28 | Multiple articles repeat one issuer disclosure | One underlying evidence family, not repeated confirmation |
| APA-29 | Restricted/private evidence reaches a public mirror | Refuse publication through existing rights owner; no second store |
| APA-30 | Missing expectations or thin geography coverage | Visible qualified state, not neutral zero or blanket product failure |
| APA-31 | Research salience appears beside stock-entry context | No propagation into rank, sizing or trading without accepted authority |
| APA-32 | Source and explanation exist but user cannot drill to company | End-to-end acceptance fails until real route/browser workflow works |

## 5. Falsifiable models for the next research passes

### Operating forecast

Choose one target before model selection: comparable next-quarter advertising revenue, a specified segment margin, a retained-client spend measure, or another observable quantity. Freeze currency, accounting perimeter, forecast horizon and knowledge cutoff. An earnings target cannot silently change to a revenue target when the first test fails.

Start with transparent baselines: prior-year seasonal behavior, the company's dated guidance where comparable, and a model using only already-reported financials. Add a proposed leading indicator only when historical availability and release lags are established. Report incremental out-of-sample improvement, error distribution, missingness and regime failure rather than highlighting one impressive fit.

For cohort tests, prevent correlated events and overlapping targets from producing fictitious sample size. Separate issuer-level observations from aggregate industry series that several issuers share. Compare against the same baseline population and keep failures, withdrawn guidance, acquired issuers and missing-data abstentions where appropriate.

### Economic sensitivity

For a transparent scenario, model incremental unlevered operating cash as incremental operating profit after tax, plus incremental noncash charges, less required capital expenditure and working-capital investment. This is a modeling framework, not a measured series. Keep maintenance/replacement capital, expansion capital, cash timing and depreciation separate. Do not subtract capex twice or call EBITDA net cash available to common shareholders.

A per-share equity scenario then requires financing, non-operating claims and dilution. Unknown financing requirements can dominate a small operating upside. Scenario ranges should be anchored to observed businesses or explicitly labeled assumptions, not chosen to produce an attractive target price.

### Rerating study

A business forecast study is not a stock-return study. A later authorized rerating analysis needs historical prices/total returns, the correct instrument identity, point-in-time membership and estimates, corporate actions, market/sector controls and a prespecified event/holding horizon. Separate revisions to the same forecast period from roll-forward to a new fiscal year. No such return panel was built here.

Avoid generating a universal Communications score before testing the component jobs. The research can prioritize unresolved questions without ranking securities. The user-facing explanation should remain valuable even when predictive promotion fails.

## 6. Consumer and owner mapping

| Need | Existing owner / source anchor | What this phase establishes | Evidence still required before build acceptance |
|---|---|---|---|
| Theme/company semantic identity | GMI / existing identity readers | Shared ownership must remain intact | Exact accepted identifiers and exposure assertion mapping |
| Financial and operating facts | Existing evidence/filing owners | Primary-source examples and definition requirements | Native storage/read round-trip, corrections and rights |
| Earnings expectation context | `collectors/equity_earnings.py` and existing earnings owner | Selected cache path and clock limitations inspected | Exact estimate basis/vintage and current live coverage |
| Filing/result transport | Existing earnings-release/wire path | Native source/acceptance references observed | Real financial pair through the accepted reader |
| Descriptive sector product | Shared sector template / F04 composition | Proposed economic change card and drilldown | Accepted adapter contract and actual browser journey |
| Entry/selection/portfolio | Existing specialist owners | Research has no promotion authority | Separate accepted validation and authorization |
| Outcomes | Existing evaluation owners | Distinct operating, causal and investment study designs | Real cohorts, baseline/out-of-sample results and review |

The matrix is not source-writer permission or a commission to repair these systems. Fable's eventual task packet must use current owners and current accepted contracts. It must name the source input, observable consumer outcome, scope limits, unavailable states and real-path proof. A schema-only change that does not unlock the named investor job is insufficient.

## 7. Suggested first user comparison

Begin with a question, not a league table: **“Is advertising growth converting into better economics, and did it deliver against the company's original outlook?”**

The read view can contrast Meta, Alphabet and The Trade Desk, then expose Magnite or Pinterest where the user investigates inventory role or geography. It should show different metrics side by side without pretending they are interchangeable. A common visual grammar does not require identical calculations.

Use a compact current interpretation followed by expandable evidence, scope, timing and comparability details. Preserve investment intuition: the user should leave understanding the important economic driver and the next observable test, rather than navigating a compliance-only source catalog. Missing consensus should remove the consensus verdict, not the whole dossier.

This comparison is a proposed research prototype. Final UX, accepted specification, implementation sequencing, data-rights admission, production/browser proof and predictive qualification remain unfinished. No Fable receiver or runtime operation was started by these records.
