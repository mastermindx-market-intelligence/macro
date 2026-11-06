# Nightglass public populations, attribution and grading audit

**Date:** 2026-09-11  
**Parent:** `WS:OPTIONS-ALPHA-INTELLIGENCE-RECOVERY`  
**Carrier:** existing Macro draft PR `#7027`  
**State:** records-only research; no implementation, model admission, data purchase, subscription, trade or runtime modification.

## 1. Why this follow-up was necessary

The earlier reconstruction recovered many mechanics, but it still left a strategic ambiguity: public Nightglass examples and performance pages describe several different populations and several different outcome rulers. Without separating them, it is easy to make an invalid leap from “this page shows successful calls” to “the live options-flow engine created profitable, executable trades.”

This audit asks four narrower questions:

1. Which public observations belong to the same population and policy version?
2. Which product layer plausibly originated a showcased candidate: options flow, price structure, editorial/AI selection, or a human trade add-on?
3. Does the published ruler measure a level, a contract path maximum, a first-passage bracket, or an executable position?
4. Which fields must Mastermind retain so that these layers can be evaluated without another score, lifecycle, outcome store or Issue Desk?

The answer is that Nightglass’s public product presents a coherent journey, but the public evidence does **not** collapse into one comparable “model track record.” The useful competitive lesson is to make the journey coherent while preserving population, clock, policy, attribution and execution distinctions.

## 2. Authority, pins and rights boundary

Protected Mastermind Skillpack was atomically loaded from protected `master` at `e61f2951136bdc03a7ec2f5f12f960af26656a4c`: `INDEX.md`, `COLD_START.md`, `RECONCILE_STATE.md` and `CLOSEOUT.md`, schema `mastermind.sol_skillpack.v1`, version `1.0.1`, bootstrap major `1` compatible.

Current source context used for integration analysis:

- Macro `main`: `2051ac78c0fae30d21e799996a09285453fe045f`.
- Terminal protected `master`: `a4be9a3f4b51246200cb1b7c4f1d44730066a9a9`.
- Existing research carrier before this addendum: `61b858e9ef8876571f1e143c5164dfdf3126861a`.

Current Nightglass terms distinguish personal from business/team use and restrict competitive reuse, reverse engineering and automated extraction. This addendum therefore uses already-observed public pages and the earlier source-pinned offline evidence. It performs no new Nightglass application/API/member automation, no login, no subscription purchase and no competitor corpus acquisition. Further authenticated or programmatic comparative study requires an appropriate written permission/rights gate. This is a practical product-research boundary, not legal advice.

## 3. Four public populations that must not be merged

### 3.1 Public-X alert audit

The public audit covers 443 single-contract alerts over 15 trading sessions, or **29.53 alerts per session**. It reports 420 observations that became positive at some later print, a median best move of about 61%, 93 observations that at least doubled, a median worst drawdown around -31%, and about four days to the best print. Multi-leg alerts were excluded. The reference entry was described as the triggering institutional order’s average execution price, while the favorable endpoint was the best later option print through the audit cutoff.

That is a descriptive path-maximum audit with unequal observation windows. It is not the same population or ruler as a fixed target/stop first-passage study, a level scorecard, a subscriber fill study or a quantity-aware managed position.

### 3.2 Matured flow-contract record

The source-pinned public performance response generated on 2026-09-10 reports:

- 7,343 tracked observations;
- 6,389 matured;
- 954 still open;
- 3,968 target-before-stop successes;
- 957 tickers;
- 155 trading days;
- source data through 2026-09-01 with a five-trading-day lag.

The tracked count is **47.37 per trading day**. The ruler is +30% before -50% using intraday first-passage ordering through expiry, with unresolved/open contracts omitted from the matured denominator. It is therefore different from the public-X “ever positive / best print” population.

### 3.3 Current marketing description

The current homepage describes roughly 75 alerts in a typical day. This is a marketing description, not an observed cohort and not an outcome ruler. It is roughly 2.54 times the older public-X audit rate and 1.58 times the source-pinned tracked-record rate. That need not be a contradiction: product admission rules, channels, dates and product mix can change. It is evidence that **policy and population versioning are mandatory** before cross-period performance comparisons.

### 3.4 Weekly Flow Map editorial population

The first three public Weekly Flow Map issues each provide a market-structure/breadth/flow report, a notable-flow list, and a five-name focus list. Those focus lists are editorial research candidates, not simply the output rows of the live-alert engine. Their grade tables use level-specific rules rather than exact-option position P&L.

### Population ledger

| Population | Count | Sessions | Rate/session | Ruler | Key exclusion/limit |
|---|---:|---:|---:|---|---|
| Public-X audit | 443 | 15 | 29.53 | Best later print / ever positive | Multi-leg excluded; unequal horizons |
| Matured flow record | 7,343 tracked | 155 | 47.37 | +30 before -50 through expiry | 954 open excluded from matured denominator |
| Current “typical day” marketing | ~75 | 1 illustrative day | ~75 | None | Not an observed outcome cohort |
| Weekly focus lists, issues 001–003 | 15 focus names | 3 weekly issues | 5/issue | Level scorecard/editorial follow-up | Small, selected sample; not exact-option P&L |

A valid Mastermind result must carry at least `population_id`, `admission_policy_version`, `channel`, `decision_at`, `available_at`, `horizon`, `quote_policy_version`, `outcome_ruler_version` and `terminal_state`. “Nightglass track record” is not a sufficiently specific population identity.

## 4. Exact first-passage audit: the 62.1% headline does not identify expectancy

For the idealized no-drift continuous-martingale bracket used in the earlier research, with upper target `a`, lower stop magnitude `b`, eventual barrier arrival, no overshoot and no cost:

\[
P(\text{target first}) = \frac{b}{a+b}.
\]

For +30% and -50%, the no-edge reference is **62.5%**, not 50%.

The public matured count is:

\[
\hat p = 3968/6389 = 62.106746\%.
\]

An exact two-sided binomial test against 62.5% gives `p = 0.5182568601`. The 95% Wilson interval is **60.9103%–63.2887%** and the exact Clopper–Pearson interval is **60.9041%–63.2984%**. Under the deliberately simplified assumption that every winning observation exits at exactly +30% and every non-winner loses exactly 50%, the observed rate implies approximately **-0.3146% of initial premium per observation before costs**.

That calculation does **not** establish Nightglass unprofitability. Non-winning observations need not all finish at -50%; some expire, recover, are managed or have different short-side economics. The loss magnitude that would make a 62.1067% win rate break even if all wins were exactly +30% is about **49.1698%**, not 50%. Therefore the hit count alone does not determine expected return. It establishes that the public rate is not, by itself, evidence of an edge over this bracket geometry.

The proper economic endpoint requires the exact instrument, entry availability, bid/ask convention, fees, latency, deadline handling, capital/risk denominator and quantity-aware management policy.

## 5. Rule-table concentration: the public record is mostly one rule family

The five published matured rule cells exhaust 6,389 observations and 3,968 wins. Four exact integer win counts are uniquely implied by their one-decimal rates; the repeated-interest win count is the exact residual.

| Rule | n | Wins | Exact rate | Share of matured | Exact two-sided p vs 62.5% |
|---|---:|---:|---:|---:|---:|
| Far-strike premium positioning | 36 | 28 | 77.78% | 0.56% | 0.05997 |
| Low-open-interest activity | 258 | 164 | 63.57% | 4.04% | 0.74816 |
| Urgent sweep activity | 221 | 139 | 62.90% | 3.46% | 0.94466 |
| Repeated directional interest | 5,579 | 3,464 | 62.09% | **87.32%** | 0.53379 |
| Floor participation | 295 | 173 | 58.64% | 4.62% | 0.18575 |

The rule-count Herfindahl concentration is **0.7675**, equivalent to only **1.303 equally sized rule families**. In practical terms, the aggregate headline is overwhelmingly a repeated-interest result.

No individual cell rejects the 62.5% idealized bracket null at the conventional 5% level; the far-strike cell is closest but tiny and becomes even less persuasive after accounting for five inspected cells. A descriptive Pearson equal-rate test gives `Q = 5.5521`, four degrees of freedom and `p = 0.2352`. This is not proof the rule families are identical; dependence, multiple searches, policy evolution and vendor-reported inputs remain unresolved. It shows that the public table does not establish a statistically differentiated family of proprietary rule alphas.

Mastermind should not build five badges and treat them as five independent validated strategies. Rule-family counts, dependence and policy revisions must be explicit.

## 6. Why “went green” is not an economic metric by itself

The public audit’s 420/443 “went green” rate is **94.8081%**. Its 95% Wilson interval is approximately 92.33%–96.52%. The sample proportion is precise, but the economic meaning is not.

For a symmetric zero-drift ±1 random walk observed for `n` steps, the probability of being strictly positive at least once is:

\[
1 - \binom{n}{\lfloor n/2 \rfloor} / 2^n.
\]

This probability is already 92.04% by 100 observations, 94.81% around 236 observations, 96.43% by 500 observations and 97.48% by 1,000 observations—even though the process has no positive expected return. Actual option paths are not this model: they jump, expire, have volatility smiles, selection, unequal clocks and executable spreads. The counterexample demonstrates a measurement fact: **a path-maximum event with no minimum threshold, fixed horizon or executable quote convention can be extremely common without providing an edge**.

The same problem applies to a perfect-exit thought experiment that buys every alert and sells each at its best later print. It describes hindsight opportunity, not a deliverable policy. A useful outcome must say what exit rule was knowable and executable at the time.

## 7. Public Weekly Flow Maps reveal substantial structure/editorial attribution

Across the first three public weekly focus lists:

- Issue 001: ARKG carried notable-flow context and FCX a radar/flow context; EWT, AFRM and DXCM were explicitly structure-only.
- Issue 002: CSX, ABCL, EWY, CXW and DBA were structure-only.
- Issue 003: GILD carried radar/flow context; FTEC, JNJ, BBY and DK were structure-only.

That is **12 of 15 focus names (80%) explicitly structure-only** and three with named flow context. The 95% Wilson interval for 12/15 is wide—about 54.8%–93.0%—because this is a tiny, editorially selected sample. It must not be generalized into a universal percentage.

It does establish a narrower and important fact: the showcased weekly workflow cannot be attributed solely to options-flow detection. Price structure and editorial selection are first-class product contributors. Any comparison claiming “their flow algorithm outperformed ours” without decomposing those layers is mis-specified.

The appropriate attribution taxonomy is:

1. raw live-flow event detection;
2. measured execution/opening/package interpretation;
3. settled OI/position confirmation;
4. price-structure and plan geometry;
5. editorial/AI promotion and narration;
6. human trade selection and management.

A candidate may use several layers, but each outcome must retain which layer originated it and which layers only supplied context.

## 8. Their public flow-map gate itself shows policy evolution or clarification

Issue 001’s prose describes persistence across at least three sessions, while its table includes two-session bursts. Later issues state the exception explicitly: either three sessions, or a two-session burst when activity is at least five times baseline and mostly one-way. The notable-flow baseline is described relative to the preceding four weeks; call selling is treated primarily as income context rather than straightforward bearishness.

This may represent a documentation correction, a methodology revision or an exception that was present but initially under-specified. Public pages alone cannot distinguish those explanations. The safe conclusion is that every decision and performance row needs a `candidate_policy_version` and a frozen human-readable admission receipt. A later prose update must not silently rewrite the rules attributed to an earlier alert.

The same applies to enriched-session timing: public flow sections describe four enriched sessions, with Friday’s completed data arriving into the Monday report while chart context can already include Friday’s close. The report is a multi-clock composition, not one synchronous observation.

## 9. Weekly level grading is useful—but asymmetric

The weekly grade pages use different event definitions for different roles:

- target success can be credited when price trades through the target intraday;
- support/invalidation are evaluated using closing prices;
- a later target touch and an earlier close-based support failure can both remain true in the scorecard.

A synthetic path makes the distinction explicit:

| Day | High | Close |
|---|---:|---:|
| 1 | 100.00 | 98.50 |
| 2 | 104.00 | 102.00 |

With target 103 and support 99, the target was traded through, but support did not hold on all closes. Neither observation erases the other.

This is a legitimate editorial level-use ruler: targets answer whether price reached an area, while support asks whether price accepted below a line. It is **not** a symmetric +target/-stop trade backtest and must not be aggregated with exact-option first-passage performance without a translation policy.

Mastermind should keep at least three scorecards separate:

- **level quality:** touch, reaction, close acceptance, break/retest and time-to-event;
- **plan viability:** entry window, objective, defense, thesis line and reward/risk at decision/availability;
- **instrument performance:** executable quote-to-quote P&L, fees, quantity, capital and management.

## 10. A better Mastermind evaluation matrix

The first useful comparison should be factorial rather than a single fused score:

| Arm | Candidate source | Context allowed | Authority |
|---|---|---|---|
| Existing policy | Current Mastermind baseline | Current governed inputs | Existing only |
| Flow-only | Measured live campaign evidence | No price-plan promotion | Research candidate |
| Structure-only | First-available price structure | No options-flow promotion | Research candidate |
| Flow + structure | Both, with explicit dependence | Conditional plan/abstention | Research candidate |
| Editorial/AI promoted | Same evidence plus named promotion | Explanation/ranking only | No trade authority |
| Human add-on analog | Explicit operator selection/management | Quantity and fill ledger | Existing Issue Desk boundary only |

The shared-candidate analysis asks whether additional context improves decisions on the same opportunities. A full-policy analysis separately includes new opportunities, rejections and no-entry states. Both are needed.

### Primary endpoint

Use exact-option executable return under a preregistered quote/entry/exit policy after fees and modeled latency, with no-entry and unresolved states retained. Do not substitute midpoint, final underlying return or best print when the exact option quote is missing.

### Supporting endpoints

- calibration and Brier/log score for any separately admitted probability;
- coverage versus abstention;
- precision at actual capacity;
- target/stop/deadline cumulative incidence;
- drawdown and tail loss;
- fill eligibility and spread/quote-age sensitivity;
- level touch/reaction/close-acceptance quality;
- entry-window expiry and anti-chase decisions;
- performance by policy version, source, liquidity, event/catalyst, horizon and regime;
- campaign/session-clustered uncertainty rather than alert-row independence.

### Minimum durable fields

`population_id`, `admission_policy_version`, `candidate_id`, `campaign_id`, `channel`, `event_at`, `decision_at`, `available_at`, `client_consumed_at`, `entry_policy_version`, `quote_policy_version`, `outcome_ruler_version`, `horizon`, `instrument_identity`, `structure_context_source`, `flow_context_source`, `editorial_or_model_promotion_source`, `entry_eligible`, `entry_expired_reason`, and `terminal_state`.

These are fields on existing owners or a reviewed projection. They do not justify another event, campaign, outcome, queue, risk or authority plane.

## 11. Current Mastermind delta after this audit

The approved OA architecture remains directionally correct. It already separates measured event truth, existing exact-contract episodes/campaigns, a derived zero-authority candidate feed, prospective calibration, separately promoted signal authority and the existing Issue Desk.

Current canonical state remains:

- OA-1T-Macro implementation was merged as `dbd654edb0fb47449b969b7dcb4fbafc2e0fe3ef` but is `BUILT_NOT_PROVEN` pending natural RTH measured evidence.
- Earlier native research located the scheduled live-flow checkout before that accepted implementation and observed 570 decisions without the new measured block.
- Source-host topology and outcome-publication integrity have distinct unresolved blockers; neither should be hidden by rerunning the implementation or weakening checks.
- Current Terminal master still contains the old shadow Options Alpha consumer and no `options.alpha_candidate_feed` implementation search result. A successful mounted view is not continuously subscribed to candidate updates. The existing `statusTone` helper can also color `not_ready` as ready because it matches a positive substring; no live browser false-green has been proven.
- OA-1T-Terminal/OA-1C and later exact-option/statistical/Issue Desk waves retain their current admission gates. This audit creates no exception.

The new attribution finding makes the desired first vertical sharper: a real measured campaign must render as a candidate with explicit uncertainty and first-available structural-plan context, while preserving whether the flow or structure layer originated the opportunity. Strong flow with poor geometry should remain visible but non-actionable; strong structure without flow should remain a structure-only research candidate, not be retroactively called a flow win.

## 12. Exact continuation

### Production priority under existing ownership

Qualify controlled adoption of the already-accepted OA-1T measured source on the actual scheduled host, preserving the sole writer and rollback boundary, then obtain one natural RTH event-to-existing-consumer proof. Do not fabricate the event, rerun the old implementation wave or turn OI-store completeness into a prerequisite for disjoint available NBBO evidence.

### Research priority

The prepared delivery-conditioned measurement contract needs evidence-owner review of rights, fields, population, clock joins, quote convention, missingness and acceptance before acquisition or fitting. Add the population/policy/attribution fields from this report to that preregistration through existing owners. No model is admitted merely because public benchmark arithmetic has been completed.

### Held work

AD-1T2 EOD availability, OA-1C composition, OA-3 exact-option outcome extension, OA-4 directional-family promotion and OA-5 Issue Desk integration remain separately gated. Current DNR restrictions still prohibit unreviewed LLM origination, fused probability authority and later-settled positioning leakage.

## 13. Verification and limits

The companion offline audit generated `PUBLIC_POPULATION_AUDIT.json` with no network fetch, market-row ingestion or model fitting. `test_public_population_audit.py` passes **34 tests**. A mutation probe detects **10 of 10 deliberately wrong variants**. These checks cover arithmetic, population identities, intervals, concentration, a path-maximum null and grading asymmetry. They are not a market backtest, source-data reproduction, independent vendor audit, product test or alpha proof.

Artifact identities at this checkpoint:

- `public_population_audit.py` SHA-256 `5ca1f8996604604bdf314c55a3b7b1679b6f6180e0398457290036ae26840807`.
- `PUBLIC_POPULATION_AUDIT.json` SHA-256 `a32733789d503bee96520f54b9d3bc1d297d3c628c4ead5ec8a8ccb09d0a7e70`.
- `test_public_population_audit.py` SHA-256 `b4077e9b08b3bd755c3cfeb928d3cecb0ec6bb599092987117dc6473835c20de`.
- test output SHA-256 `209acabb193cb4571b4798302b32fcae1120dbdb0fa96c587360c6a70bba4f03`.
- mutation probe SHA-256 `ccf84e90d5682f61a107c56ba62e0d71d456101881c22ab9e133a456ee2cae52`.
- mutation output SHA-256 `a05f5340f765706b1f07dc246b94ff7197c7fb7d447fd635aa460809568c8462`.

No production code, source data, model, service, scheduler, mount, registry, generated Agent OS state, Linear projection or trade changed in this research addendum. PR `#7027` remains the one records-only carrier and must remain draft until repository validation and independent review are actually complete.

## 14. Source index

Public source observations, previously retrieved and now analyzed without further competitor automation:

- Nightglass methodology: `https://nightglass.trade/methodology/`
- Nightglass performance: `https://nightglass.trade/performance/`
- Nightglass public alert audit: `https://nightglass.trade/alerts`
- Nightglass homepage/product description: `https://nightglass.trade/`
- Nightglass Weekly Flow Map overview and issues 001–003: `https://nightglass.trade/map/`
- Nightglass current terms: `https://nightglass.trade/terms`
- Source-pinned aggregate response identity remains recorded in the earlier research checkpoint; this addendum does not fetch or redistribute it.

Internal source ownership and continuity:

- `agentos/workstreams/WS-OPTIONS-ALPHA-INTELLIGENCE-RECOVERY.md`
- `docs/superpowers/specs/2026-08-27-options-alpha-intelligence-recovery-design.md`
- `terminal/components/prophet/OptionsAlphaView.tsx`
- existing `#7027` research/discovery records.
