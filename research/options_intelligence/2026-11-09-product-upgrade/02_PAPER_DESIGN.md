# Options Suite — Paper Design and Build Contract
## Round 2 of 4 · 2026-11-10 UTC

**Round-5 reading note:** the exact original OPT/OPR packet is recovered. [10](10_ROUND5_SOURCE_READINESS.md) and [11](11_RELEASE_AND_DESIGN_CONTRACT.md) now govern source truth and the next Paper work. No Paper nodes or the historical manifest changed in Round 5. Besides B04, correct aggregate-versus-child Flow detail, Volatility tenor/percentile/history labels, strict sampled price-condition wording, unsupported watch expiry/consent copy, selected-firing stability and bounded history. Core Trade Lab pre-expiry comparison and the Opportunities/Monitor jobs remain required; 1280/1920 obligations also survive. The synthetic fixture remains design evidence only.

**Historical round-2 status: Paper candidate complete for that round.** The current programme baseline is [05_IMPLEMENTATION_MASTERPLAN.md](05_IMPLEMENTATION_MASTERPLAN.md); later architecture decisions are in [04_ARCHITECTURE_HARDENING.md](04_ARCHITECTURE_HARDENING.md).

**Round-4 source adjudication — read before implementation:** protected master still has the preparation-only Plan host, while original held #804 at `27df56d997df0ae94a17b6b8e2d14867431bb394` already implements the native bridge. Its admission is **new research draft only**, and the first save is revision 1 of a new case. B04's depicted Plan attachment as revision 2 of an existing Exposure case is not supplied by that bridge. Preserve this document and the manifest as the historical Paper artifact; use 04 §7.2 for the current implementation contract, and revise B04/its fixture in the next Paper round unless the incumbent owner explicitly qualifies same-case attachment. No Paper nodes were changed in round 4. Also retain the corrected route distinction: `?tab=0dte` is current URL syntax; `zero_dte` is an internal key.

**Canonical carrier:** [Macro draft PR #10898](https://github.com/mastermindx-market-intelligence/macro/pull/10898), branch `claude/options-suite-production-plan-20261109`. This is an additive companion to [01_MASTERPLAN.md](01_MASTERPLAN.md), within the existing Terminal #599 / #603 and WS-ADVANCED-DATA-OPTIONS programme. It creates no replacement task hierarchy, runtime owner, implementation dispatch or release permission.

## 1. Outcome and reading order

Round 2 produced **34 new editable boards in the existing Terminal Paper file**, grouped into four pages: 10 desktop product boards, 14 phone boards, two tablet boards, four state atlases, and four build/reference boards. The atlases contain **44 named state components**. A consistent synthetic SPY investigation connects the screens. English and Chinese examples preserve the same dates, numbers, qualifications, source boundaries and action meanings.

The design turns the round-1 proposal into a reviewable product: six primary destinations; a concise answer before detailed evidence; one contextual pane at desktop width; focused detail on a phone; explicit source dates and units; a clear distinction between observations, modeled exposure, authored payoff and research claims; and usable save, watch and review recovery states.

Start in [Build contract](https://app.paper.design/file/01M3NSZGE8JWN2EZCSF0DT05RM/p-1R-0), B01. Inspect [Product](https://app.paper.design/file/01M3NSZGE8JWN2EZCSF0DT05RM/p-1O-0) for the desktop journey, [Responsive](https://app.paper.design/file/01M3NSZGE8JWN2EZCSF0DT05RM/p-1P-0) for phone/tablet and the Chinese path, then [States & help](https://app.paper.design/file/01M3NSZGE8JWN2EZCSF0DT05RM/p-1Q-0) for failure, recovery, accessibility and concurrency.

The original 245-board census remains in the masterplan. This round made no edits to those original boards. It adds a candidate beside the existing Options group and preserves the relative order of every other page and divider. The held D08D target `p-2-0 / 1N2L-0` was read and remained untouched. The adjacent Returns / #804 and company heatmap targets also remained untouched.

**What is proven:** editable Paper nodes exist; exact page/node identities were read back; rendered screens were inspected; the numerical fixture is internally consistent; the source-linked integration boundaries below were checked; JSX was extracted for all 34 boards.

**What remains owed:** actual routing, keyboard and touch behavior, authenticated source admission, live contract joins, persistence, deployed-consumer proof, performance and empirical model qualification. A Paper screenshot is design evidence. It is not a successful application transaction.

### 1.1 Source discipline

The governing Mastermind source pin remains `9e6659c4a49ee6f11a6f6ee690d222ce81d67b09`. The round-1 Macro source cut remains `9a13c64bf69f782332afa29efb09fe48ee30b857`; the round-1 Terminal census cut remains `1c0bf028cf72539a4d3fcb17fa137ee474d764f9`.

Round 2 refreshed only affected Terminal files at **`2fe2f02f07d1df8c855388bc556383cd74de44fd`**: the Flow aggregate/projector/consumer, Investigation manifest/review, exact Plan draft lifecycle and preparation-only host, and the alert outbox migration. This targeted read does not claim a new full-repository census or refresh every PR/release state from round 1.

The current schema proves several UI limits. Flow's existing contract has aggregate fields, not child-print observations or NBBO. Review assessments already use a new immutable Investigation revision. The exact Plan host remains preparation-only. Investigation horizon and Plan horizon have different limits. Outbox delivery status is a real required field. These facts are bound in B02 and §8 below. [R2-S01] [R2-S02] [R2-S03] [R2-S04] [R2-S05] [R2-S06] [R2-S07] [R2-S08] [R2-S09] [R2-S10]

## 2. Exact editable inventory

File: **Terminal**, `01M3NSZGE8JWN2EZCSF0DT05RM`.

| Page | Exact page ID | New boards | Purpose |
|---|---|---:|---|
| [Options · R3 candidate · Build contract](https://app.paper.design/file/01M3NSZGE8JWN2EZCSF0DT05RM/p-1R-0) | p-1R-0 | 4 | Start here, source bindings, interactions, future Plan-save preview |
| [Options · R3 candidate · Product](https://app.paper.design/file/01M3NSZGE8JWN2EZCSF0DT05RM/p-1O-0) | p-1O-0 | 10 | Main desktop investigation and comparison path |
| [Options · R3 candidate · Responsive](https://app.paper.design/file/01M3NSZGE8JWN2EZCSF0DT05RM/p-1P-0) | p-1P-0 | 16 | 14 phone screens, two tablet screens, complete primary Chinese path |
| [Options · R3 candidate · States & help](https://app.paper.design/file/01M3NSZGE8JWN2EZCSF0DT05RM/p-1Q-0) | p-1Q-0 | 4 | 44 state components and narrow specimens |

The new pages appear together immediately after the original Options divider `p-1J-0`. They do not rename, archive or replace the earlier D08A/B/C pages. The page name “R3 candidate” identifies the design iteration; this document is still **session round 2 of 4**.

### 2.1 Product boards

| Board | Exact node | Theme / width | Question answered and primary action |
|---|---|---|---|
| O01 Overview | 29HR-0 | Light EN / 1440 | What deserves investigation, and what saved work can I resume? Inspect activity or open the exact saved case. |
| O02 Flow | 28VF-0 | Dark EN / 1440 | What was observed in the selected activity group? Inspect source children, or explicitly continue with independent SPY Exposure context. |
| O03 Exposure | 2918-0 | Light EN / 1440 | Which contracts explain the dated known sensitivity? Inspect the selected 600 Call, compare the baseline, or save supported Exposure evidence. |
| O04 Volatility | 2973-0 | Dark EN / 1440 | How do expiry and skew observations differ? Inspect the selected expiry with source dates and missing fields. |
| O05 Research | 29LI-0 | Dark EN / 1440 | Which research families are accumulating evidence, and what claims are permitted? Open evidence maturity or the Lab. |
| O06 Saved research | 29PH-0 | Light EN / 1440 | What exactly was saved, when, and what remains a draft? Open the requested case/revision or manage its watch. |
| O07 Plan | 29BT-0 | Light EN / 1440 | What does this authored two-leg expression pay at expiry? Recalculate or compare assumptions. |
| O08 Case review | 29T4-0 | Dark EN / 1440 | Which price condition fired, and what remains to assess? Choose an assessment before saving a new revision. |
| O09 Compare assumptions | 2AEX-0 | Light EN / 1440 | What changes when only the long-leg premium changes? Compare exact, aligned expiry outcomes. |
| O10 Matched book comparison | 2AIS-0 | Dark EN / 1440 | Which matched members explain the known-subtotal change? Filter All / Matched / Unknown and inspect both source rows. |

### 2.2 Responsive boards

| Board | Exact node | Theme / width | Role |
|---|---|---|---|
| M01 Flow | 29XA-0 | Dark EN / 390 | Compact scan with a selected activity group |
| M02 Flow inspector | 29ZH-0 | Dark EN / 390 | Focused source inspection and exact return |
| M03 敞口 | 2A1T-0 | Light ZH / 390 | Chinese Exposure reading with explicit known subtotal |
| M04 合约详情 | 2A48-0 | Light ZH / 390 | Exact selected contract, dated observation and save boundary |
| M05 Plan | 2A5P-0 | Light EN / 390 | Authored legs, expiry sample, payoff and unsaved boundary |
| M06 复盘 | 2A81-0 | Dark ZH / 390 | Trigger observation, unselected assessment and revision save |
| M07 导航 | 2A9S-0 | Light ZH / 390 | Six destinations and direct saved/watch/review entries |
| M08 Watch preview | 2ADC-0 | Dark EN / 390 | Supported price condition, cadence, expiry and explicit arm |
| M09 概览 | 2BGP-0 | Light ZH / 390 | Chinese assessment, source clocks and saved-case return |
| M10 成交检查 | 2BII-0 | Dark ZH / 390 | Six-child synthetic Flow evidence, quote uncertainty and root-only handoff |
| M11 波动率 | 2BKM-0 | Light ZH / 390 | Exact expiry/DTE basis, skew, RV/VRP and unavailable IV rank |
| M12 计划 | 2BMJ-0 | Light ZH / 390 | Chinese parity for exact authored Plan and expiry payoff |
| M13 已保存研究 | 2BOO-0 | Light ZH / 390 | Exact revision, original evidence, armed watch and excluded Plan |
| M14 观察条件预览 | 2BQK-0 | Dark ZH / 390 | Chinese condition preview before the separate arm operation |
| T01 Volatility | 2ANC-0 | Light EN / 820 | Tablet term/expiry comparison with readable source context |
| T02 研究实验室 | 2AQC-0 | Dark ZH / 820 | Exact table, selected contract and same-data 2D/3D transition |

### 2.3 State and build boards

| Board | Exact node | Contents |
|---|---|---|
| S01 Evidence & selection | 2ATC-0 | E01–E12: evidence absence, corrections, access, source identity and unsupported terms |
| S02 Drafts, save & revisions | 2AWP-0 | P01–P12: authored inputs, dirty results, save uncertainty, conflict and exact reopen |
| S03 Watch, delivery & return | 2B0G-0 | W01–W12: arming, evaluator, firing, delivery and explicit temporal return |
| S04 Narrow, locale & accessibility | 2B49-0 | A01–A08: 320px components, EN/ZH semantics, focus, motion and invalid input |
| B01 Start here & preservation map | 2B8P-0 | Four-round sequence, six destinations, retained aliases and held scope |
| B02 Source, action & authority bindings | 2BAQ-0 | Current owners, required extensions and maturity boundaries |
| B03 Interaction & acceptance contract | 2BCJ-0 | Context carried, result, recovery and remaining runtime proof |
| B04 Exact Plan save: target preview | 2BEJ-0 | Future admitted save preview, included/excluded content and existing dependencies |


## 3. Product and visual decisions

### 3.1 Six destinations, existing depth

The primary navigation is **Overview / Flow / Exposure / Volatility / Research / Plans & review**. Its Chinese labels are **概览 / 资金流 / 敞口 / 波动率 / 研究 / 计划与复盘**. This is a presentation consolidation of existing capabilities, not a route rewrite.

The incumbent aliases retain their meanings. In particular, legacy `vol` still means the Flow screener; it must not route to the Volatility family. Flow Surface remains the current Flow-family surface. Research keeps Statistics, the separate Prophet Macro/Options/Issue lanes and Research Lab. Plans & review gives saved investigations, Watching and Review direct entry without forcing a user to open a new Plan editor.

| Existing entry / alias | Proposed destination and subview | Clear label | Context that must survive |
|---|---|---|---|
| desk | Overview | Overview | Root, session, originating case or scan |
| tape | Flow / Tape | Options tape | Filters, exact row, sort, focus, source revision |
| tide | Flow / Tide | Flow over time | Root, population, time basis |
| 0dte / zero_dte | Flow / 0DTE | 0DTE activity | Exact session, expiry and source |
| largest | Flow / Largest | Largest events | Sort basis, population, selected observation |
| surface | Flow / Surface | Flow surface | Original Flow-family source and metric; never substituted with IV terrain |
| vol / screener | Flow / Screener | Screener | Existing filters and eligible universe; the legacy vol alias must not open Volatility |
| tickers | Flow / Tickers | Activity by ticker | Universe, root and scan return |
| gex | Exposure / Map or ladder | Exposure | Book, metric, expiry population, selected node |
| positioning | Exposure / Positioning | Positioning | Inventory/sign model, source and population |
| levels | Exposure / Levels | Structural levels | Exact level, source, metric and baseline |
| structure | Exposure / Structure | Structure | Existing structure source and chart/companion context |
| volatility | Volatility / Expiry or tenor | Volatility | Exact expiry or tenor, selected smile, spot/IV clocks |
| statistics | Research / Statistics, with contextual Flow entry | Observed statistics | Observed population, exclusions and time basis |
| prophet → options lane | Research / Options Alpha | Options Alpha research | Candidate, family, original formation, permitted claim |
| prophet → macro lane | Research / Macro Plans context | Macro Plans | Original broader Prophet assessment and source; no implied option expression |
| prophet → issue lane | Research / Issue Desk | Research Issue Desk | Exact research issuance/review identity; no broker order meaning |
| Research Lab | Research / Lab; contextual Exposure and Volatility launch | Options Research Lab | Root, lens, qualified selection, comparisons, source epoch |
| Exact Plan and Compare | Plans & review / Plan or Compare | Research Plan / Compare plans | Authored terms, calculation identity, source references, case revision |
| Existing saved investigations | Plans & review / Saved | Saved research | Exact requested case/revision and original evidence |
| Existing watch/review entry | Plans & review / Watching or Review | Watching / Review | Exact condition, firing receipt, linked revision and return |
| /options/futures?pair=ES | Exposure / Futures contextual workspace | Futures context | Native pair/contract/session/cutoff grammar and mapped-exposure basis |
| /options/equity-replay?symbol=SPY | Exposure / Equity replay contextual workspace | Equity replay | IEX artifact, sample, admission and native time selection |


The original router/workspace owns the migration. A receiving surface accepts exact context, explicitly narrows it to root-only context, or refuses the transfer with a reason. It never chooses a nearby strike, different expiry or newest revision to make the interface look successful.

### 3.2 A short answer, then inspectable evidence

The first reading layer answers a concrete question. Flow says activity clusters in the 600 Call. Exposure says the known sensitivity increased across matched rows. Plan says it is an expiry payoff from authored assumptions. Review says the price condition fired while the research question still needs assessment.

Each answer is bounded by the evidence. A $224,000 activity group is not an independent predictive signal. A +$50m matched sensitivity change is not a full-book change or velocity. A +$280 expiry scenario is not a current option valuation. An armed price watch is not a continuously observed market condition. An accruing research book is not a live strategy.

The second layer contains the actual table, plot or comparison. The third layer contains source detail, terms, methods, correction lineage and exact identities. A limitation that changes interpretation stays beside the result; source implementation IDs stay in source detail or explicitly marked Build notes.

### 3.3 One contextual pane

Desktop uses the existing shared Terminal shell: 64px header, 224px global rail, and the Options workspace. At 1440px the principal evidence and one 320px contextual pane fit together. Inspector and Case, or Scenario and Case, are named modes of that pane. There is no second permanently open case rail.

The table/plot remains the main workspace. Selected rows use neutral whole-row fill and text emphasis. The Exposure chart now marks the selected 600 Call and places the unit and current/prior legend above the bars. O10's selected cohort is **All 6**, because the table visibly includes its unknown sixth member. Matched 5 is a different filter.

Tablet stacks or simplifies the evidence while preserving data identity. Phone opens focused detail with a defined Back route, source context and original selection. Vertical scrolling is intentional; critical data is not squeezed into a horizontally unreadable desktop table.

### 3.4 Shared visual system

The designs reuse the canonical Inter / PingFang SC typography, spacing vocabulary and existing light/dark tokens. Inter is explicitly assigned to English and numeric text; Chinese copy uses PingFang SC. Mobile status bars use the prescribed system treatment. The final JSX check found explicit font assignment in all 1,604 examined text leaves across 34 boards.

Dark uses controlled luminance depth for an instrument workspace. Light uses clear neutral surfaces, restrained borders and strong numeric hierarchy. Semantic ink and data marks carry meaning. No decorative colored edge stripes are introduced. Full keyboard focus outlines remain visible and are distinct from selection and health.

English positive/negative market-direction colors and Chinese red-up/green-down conventions are documented separately from source-health colors. The Chinese A04 example labels both sign and meaning; its ±1.20% is an isolated semantics specimen, not an additional SPY return observation.

Menu controls were refined to a consistent 20px line icon in a 44px target across all sixteen responsive boards. Other compact visual controls may be 40px high; implementation must provide an accessible touch hit area of at least 44px without overlapping adjacent controls. A03 shows the full focus treatment. This is a product target, not a claim of executed browser accessibility testing.

### 3.5 Useful capabilities made easier to reach

The designs expose deep capabilities through a short path: inspect a coalesced activity group; see source children when actually available; distinguish unclassified activity; open an independently qualified Exposure book; compare a matched contract population; examine exact expiry and skew observations; inspect research maturity; author exact legs; compare one assumption at a time; save supported evidence; preview a supported watch; and return to a firing with the original case intact.

Existing specialized capabilities remain accessible through subviews or contextual entry: 0DTE, largest events, Flow Surface, ticker scans, screener, structural levels, positioning, Statistics, 3D and exact tables, source receipts, scenario comparison, Futures and equity replay. This round does not replace their existing detailed designs with generic cards or claim to finish every prior programme obligation.

## 4. One coherent synthetic case

**Every numerical market observation in this round is design fixture data.** Product boards visibly label the example as synthetic. The dates connect the screens; they are not claims that production emitted these records.

### 4.1 Source clocks and chronology

| Item | Fixture time / identity | Interpretation |
|---|---|---|
| Original research snapshot | 9 Nov 2026, 10:20 ET | Flow remains pinned to this observation window |
| Original spot observation | $598.40 at 10:19:58 ET, 9 Nov | An observation clock, not an undated current quote |
| Exposure current book | 6 Nov EOD; spot $596.20 | Chain and OI position date 6 Nov; OI reported 9 Nov |
| Exposure current availability | 9 Nov, 03:52 ET | Independent availability clock |
| Exposure baseline book | 5 Nov EOD; spot $594.80 | OI reported 6 Nov; available 6 Nov, 03:52 ET |
| Volatility book | 6 Nov EOD | First availability time is not recorded |
| Plan authoring | 9 Nov, 10:25 ET | User-authored assumptions, not inferred trade fills |
| Investigation revision 1 saved | 9 Nov, 10:28 ET | Exposure evidence and selection; exact Plan excluded |
| Watch preview | 9 Nov, 10:29 ET | Separate, not-yet-armed operation |
| Watch armed | 9 Nov, 10:30 ET | Price-touch condition, one shot, five-minute evaluator |
| Saved/Overview reading | 9 Nov, 10:35 ET | Can show the already armed condition |
| Watch firing recorded | 10 Nov, 10:06:02 ET | Firing value $605.10; underlying source timestamp absent |
| Review reading | 10 Nov, 10:15 ET | Pending delivery, no assessment selected |

A later observation of $598.40 does not reprice the historical Exposure book. DTE in the Volatility view is counted from 6 Nov, not the 9 Nov research session. A receipt's firing time does not manufacture a missing source price timestamp.

### 4.2 Flow arithmetic and interpretation

The selected exact contract is `SPY261120C00600000`: 20 Nov 2026, 600 Call, ordinary 100 multiplier. The six synthetic source children all have $5.60 premium per unit.

| Event time ET | Contracts | Premium | Qualified quote category |
|---|---:|---:|---|
| 10:17:50 | 100 | $56,000 | At ask |
| 10:18:03 | 80 | $44,800 | At ask |
| 10:18:11 | 70 | $39,200 | At ask |
| 10:18:20 | 50 | $28,000 | At ask |
| 10:18:31 | 60 | $33,600 | Unknown |
| 10:18:42 | 40 | $22,400 | Unknown |
| **Selected group** | **400** | **$224,000** | **300 contracts / $168,000 at ask; 100 / $56,000 unknown** |

The selected group's 75% / 25% split happens to be identical by contracts and premium in this fixture because every child has the same price and multiplier. The timeline's vertical quantity and the inspector's visible 300/100 counts are contracts. An implementation must name the denominator for every share and retain both eligible and unclassified amounts; it must not generalize that the two measures always match.

The visible scan also contains 70 contracts of the 610 Call at $2.40 ($16,800), last event 10:16:33, quote unclassified; and 50 contracts of the 590 Put at $3.00 ($15,000), event 10:12:09, at bid with intent unknown. The three displayed groups therefore comprise 520 contracts, eight source prints and $255,800. That is a **displayed subtotal**, not a market-universe total, three independent signals or a proven package.

Filters are SPY, 20 Nov expiry and premium at least $15,000. Opening Exposure carries only qualified root context into an independent dated book. Back retains the exact Flow group, snapshot, filters, sort and originating focus.

**Source dependency:** the current Flow owner does not supply these six children, their individual clocks or quote/NBBO evidence. The detailed timeline is a target design for a typed extension through the incumbent producer/API. Until that evidence is available and reconciled, E01 shows the available aggregate and omits the child timeline and quote split. Existing side-estimate coverage must not be relabeled as at-ask evidence. [R2-S01] [R2-S02] [R2-S03]

### 4.3 Exposure arithmetic and matched population

Metric: modeled Gamma sensitivity in **USD millions per +1% underlying move**, with assumed call-positive / put-negative OI signs. This is not observed dealer inventory.

| Contract, 20 Nov expiry | 5 Nov book | 6 Nov book | Matched difference |
|---|---:|---:|---:|
| 590 Call | +35 | +40 | +5 |
| 590 Put | −25 | −30 | −5 |
| 600 Call | +140 | +180 | +40 |
| 600 Put | −60 | −70 | −10 |
| 610 Call | +60 | +80 | +20 |
| 610 Put | Unknown | Unknown | Unavailable |
| **Known matched subtotal** | **+150** | **+200** | **+50** |

Five of six contracts are known in both books. The full-book total remains unavailable. The sixth member is not zero and does not enter the matched sum. The selected 600 Call shows +$180m / 1% and +$40m matched change.

The comparison records both source spots and warns that spot and model inputs can contribute to the difference. The +50 is not a percentage change, acceleration or a causal result of the Flow group. All 6 / Matched 5 / Unknown 1 / Added 0 / Removed 0 describe distinct cohorts.

### 4.4 Volatility fixture

| Expiry | DTE at 6 Nov | ATM IV |
|---|---:|---:|
| 13 Nov | 7 | 23.5% |
| 20 Nov | 14 | 22.0% |
| 18 Dec | 42 | 21.0% |

For the selected 20 Nov expiry, 25-delta Call IV is 20.0%, Put IV is 23.0%, and the stated Call-minus-Put risk reversal is **−3.0 volatility percentage points**. Twenty-day realized volatility is 18.0%; the separately source-published VRP is +4.0 points. Preserve that published measure's identity rather than recomputing a different metric in the browser.

IV rank is unavailable. First availability time is unknown. Missing wings remain missing. These observations do not supply a probability, position size or pre-expiry valuation for the authored Plan.

### 4.5 Exact Plan and comparison

The Plan uses a separately qualified exact-contract shortlist fixture. Exposure aggregates or source fingerprints do not themselves become admitted Plan pins.

- Buy one ordinary SPY 600 Call at an **authored** $5.60 per unit.
- Sell one ordinary SPY 610 Call at an **authored** $2.40 per unit.
- Common expiry: 20 Nov 2026. Multiplier: 100. Currency: USD.
- Net debit: $320. Worst expiry P/L: −$320. Best expiry P/L: +$680.
- Analytic breakeven: $603.20.

For underlying expiry price S:

```text
P/L(S) = 100 × [max(S − 600, 0) − max(S − 610, 0) − 3.20]
```

The response axis contains 103 source samples: 101 evenly spaced prices from 480 through 732, with the 600 and 610 breakpoints retained. Focus mode displays the existing subset between 580 and 625. It changes the view, not the backend request or result.

The twenty visible samples are 580.80, 583.32, 585.84, 588.36, 590.88, 593.40, 595.92, 598.44, 600.00, 600.96, 603.48, 606.00, 608.52, 610.00, 611.04, 613.56, 616.08, 618.60, 621.12 and 623.64. The selected $606 sample gives +$280. $603.48 gives +$28; $608.52 gives +$532. No $605 or $603.20 curve point is fabricated. Breakeven is shown as a separate analytic result.

O09 changes only the long-leg authored entry from $5.60 to $6.10. Scenario B has $370 debit, −$370 worst expiry P/L, +$630 best expiry P/L, $603.70 breakeven and +$230 at $606. Every otherwise aligned result is $50 lower. Currency, quantity, expiry, model and cost basis stay identical.

These are deterministic expiry intrinsic-payoff scenarios. Fees, slippage, exercise and assignment are excluded. The designs do not imply probability of profit, realistic fills, actual returns, current option P/L or a pre-expiry volatility/time model.

### 4.6 Case, watch and review

The case question is authored: “What evidence would support or weaken a move through $605?” Its continuation is independently authored: reassess below $595 or when later evidence contradicts the case. Its review horizon is 13 Nov; the option expiry remains 20 Nov.

Revision 1 contains supported Exposure evidence and selection. It does not contain the Flow children, a Volatility snapshot or the unsaved exact Plan. Numeric original-book values are displayed only when the exact saved reference resolves. E09 is the identity-only fallback if it cannot resolve.

The supported watch is `price_touch` at $605, one shot, checked every five minutes, ending 13 Nov at 16:00 ET. The cadence is user-facing because scheduled evaluation cannot guarantee observing every touch between checks.

The review fixture has a matching readable outbox event with status `pending`, `delivered_at=null` and `source_asof=null`. The UI says **Queued for delivery** and **Source price time: not supplied**. Its synthetic, schema-shaped event identity is `e4f7a0c923d681b59a50fe3d2c8b74a1f6985bd027ea0f31c46d9218a7b05e63`; it is never presented as a production receipt.

A firing at $605.10 does not confirm the research thesis or measure option return. Assessment starts unselected; Save is disabled until the user chooses confirmed, contradicted or inconclusive. A valid assessment creates a new immutable revision through the existing owner.

B04 is an **alternative future branch from revision 1** in which an admitted exact Plan is saved as revision 2. O08 / P10–P11 illustrate a separate assessment revision 2. These are alternative design fixtures, not two competing writes to one revision; runtime uses the actual expected/latest revision.


## 5. Interaction contract

The table specifies the destination and retained context of the visible actions. It is a design contract for the incumbent workspace/router and command owners. It does not mint parallel routes, global state stores, evaluators or queues.

| Action / source | Receiving surface or named state | Context and required return |
|---|---|---|
| Overview: Inspect activity | O02 / M01, then M02 or M10 | Exact selected group and pinned Flow snapshot; preserve originating Overview/case context |
| Flow: select or Inspect row | Shared Inspect pane; M02/M10 focused detail | Exact group ID, filters, sort, source revision, scroll and focus; closing restores the original row |
| Flow: Inspect 6 source prints | Selected group's child evidence in M02/M10; E01 if unavailable | Stable child identities, original aggregate and qualified clocks; never invent an array from n_prints |
| Flow: Source & corrections | Incumbent source detail; retained D08A 21FC-0 grammar plus E02/E03 | Exact source and correction lineage; correction review does not silently replace selection |
| Flow: Filters / no matching activity | Retained filter draft 21Y1-0, E04 | Keep applied and draft filters separate; Apply requalifies the population; Cancel retains prior scan |
| Flow: Largest / Unusual / 0DTE / More views | Existing Largest, filtered Tape, zero_dte and remaining Flow views | Original alias semantics; selected category/filter is not a new predictive signal |
| Flow: OI changes | Incumbent admitted ΔOI/shortlist capability | Bind the source/route in round 3; unavailable or unqualified source uses a named evidence state, not a synthetic result |
| Flow: See all observations | Existing Tape observation list | Keep current filter/population and selection; an expanded list is not a changed universe total |
| Flow: Open Exposure | O03 / M03 via E08 root-only handoff | Carry SPY root only into independent Nov 6 book; retain Flow group as return origin |
| Exposure: inspect bar/row / exact contract | Shared Inspect pane / M04 | Exact expiry, strike/right, source epoch, metric/units and baseline; no nearby-contract substitution |
| Exposure: Compare 05 Nov | O10 | Match exact members and metric basis; return to O03 with selected 600 Call and current source book |
| O10: cohort tabs | All 6 / Matched 5 / Unknown 1 / Added 0 / Removed 0 | Filter is explicit; totals label their cohort; preserve source identities and selection where still present |
| O10: inspect both source rows / method | Existing source detail for both pinned books | Keep both spots, dates, sign/valuation model and comparison definition |
| Exposure: Matrix / By strike / Price context / 3D-exact 2D | Existing retained Exposure/Lab subviews | Same qualified dataset and selection; exact table always available; A06 if 3D cannot render |
| Exposure: Open Volatility | O04 / T01 / M11 | Carry root and exact expiry only if the receiving source qualifies them; preserve independent clocks |
| Exposure: Save investigation | Existing Investigation admission/preview, then S02/P03–P07 and O06/M13 | Include only supported evidence refs and explicit authored case intent; Flow children and exact Plan excluded |
| Volatility: expiry/tenor selection | Existing expiry and tenor owners; T01/M11 | Date/tenor basis and selected smile stay explicit; E10 for missing wings, retained B08 for missing expiry |
| Volatility: source/method / exact table | Existing source detail and exact table | Method, units, clocks and missing values survive; no inferred first-availability timestamp |
| Volatility / Research: qualified shortlist or Lab | Existing shortlist or Research Lab; T02 | Source admission precedes exact Plan creation; no pin manufactured from an Exposure aggregate |
| Research: evidence maturity / family | Existing Alpha/Prophet evaluation and campaign detail; E11 | Family and candidate identity, formation, sample/outcome maturity and permitted claim; no new authority |
| Plan: edit authored inputs | Existing exact-leg editor; retained C09 1RQJ-0 | Preserve source terms, side, whole quantity and premium per unit; changed inputs trigger P02 |
| Plan: Recalculate | Existing deterministic payoff endpoint | Qualification and terms precede calculation; E12 blocks the whole expression if one leg is refused |
| Plan: Focus strikes / Full range | O07 display mode | Use only the returned sample axis; selected sample remains a real response point |
| Plan: selected expiry-price sample | Existing sample selector | $606 maps to the actual response sample; analytic breakeven is not added to the sampled curve |
| Plan: Compare | O09; retained C02 and scenario-picker references | Align root, expiry, quantity, currency, model and cost basis; preserve baseline and dirty state |
| Plan: Open saved Exposure case | P09 before O06/M13 if leaving can discard draft | Keep editing or explicitly leave; do not imply Resume draft after unmount/reload |
| Saved: Open case / revision / original evidence | Exact O06/O08 revision and qualified original source | P12 if requested revision cannot load; E09 if exact source cannot resolve; never silently open latest bytes |
| Saved: Create new Plan | Existing qualified shortlist / new authored draft | Do not represent the excluded old Plan as a persisted object |
| Saved: Manage watch | Existing watch detail; W03/W08/W10 | Show real owner/evaluator state; preview a new condition separately if needed |
| Watch preview: Arm | Existing price-watch command; W02 → W03 | Saved case identity, one-shot condition and expiry; no Armed label before owner confirmation |
| Watch: Review case / exact firing | O08 / M06 with selected qualified receipt | Preserve firing ID where available, value, firing time and missing source time; W06 fallback cannot claim exact-event binding |
| Review: Load comparable book | Existing comparable-source resolver | Keep original pinned evidence visible; a price firing cannot replace an Exposure book |
| Review: delivery receipt history | Existing alert/outbox receipt detail; W05/W06/W07 | Pending delivery differs from no firing and unreadable history; do not use latest alert stamp for an older event |
| Review: choose assessment / Save as revision | Existing revise command; P10 → P03 → P11, or P04/P05/P06 | Latest revision only, explicit assessment, note limit, frozen selected firing; original evidence remains pinned |
| Review: later firing exists | W09 | Keep current firing or switch explicitly; a background update cannot alter the assessment target |
| Flow: later observations available | W12 | Keep pinned snapshot or explicitly enter latest mode; original return context survives |
| Global/Options navigation | Existing Terminal shell; M07 | Stable aliases and direct saved/watch/review entry; Escape closes navigation and returns focus |
| Root/account/source epoch switch | Existing workspace and draft owners | Atomically requalify or clear dependent selection, request and draft; reject late results from prior identity |
| Narrow/unsupported/invalid input | S04/A01–A08, E12, P01 | Retain user text; describe exact invalid field; provide legitimate next action without fabricating a result |

### 5.1 Keyboard, touch and asynchronous behavior

Selection, navigation and mutation must be separate actions. Selecting a contract changes the inspector; opening another workspace is an explicit navigation; Save and Arm invoke separate existing commands.

Tab order follows the visible reading order. A chart-selected node has a keyboard/table equivalent. Escape closes a transient pane, modal or navigation layer without deleting the selection. Closing detail restores focus and scroll to its originating control. If a withdrawn row no longer exists, focus returns to a stable Tape heading/control and announces the absence; the original identity remains retained, with no automatic neighboring selection.

The selected row cannot disappear merely because new observations arrived. Pinned history remains pinned; W12 offers an explicit transition to latest data. Source corrections and withdrawals have separate states. Root, account, expiry and source-epoch changes requalify dependent work together so late responses cannot render under a different header.

Loading uses stable geometry; reduced motion removes animated shimmer while retaining progress meaning. Partial data retains available rows and missing-state explanations. A failed refresh preserves the older book with its original date; an unpublished book, denied source and readable empty result are not interchangeable.

### 5.2 Exact Plan save target

B04 makes the desired future interaction reviewable. It previews the case question and review horizon, the original Exposure reference, the exact two authored Plan legs, their terms, entry assumptions and expiry-payoff basis. It explicitly excludes unsupported Flow-child and Volatility capture. Save does not arm a watch.

The target remains dependent on native admission, exact capture and embedded history in the existing #804 / D23 work. The preparation-only host cannot be mounted as if those interfaces already existed. The original hold remains binding. Round 3 must bind the precise admitted schema and source/capture/reopen contracts; round 4 must place the resulting work on the existing task graph. [R2-S06] [R2-S08] [R2-S09]

The expected result is a new immutable revision through the incumbent Investigation command with an expected revision. Known committed success with unreadable contents retries only the exact revision read. Unknown write outcome reconciles the original operation. Concurrent changes preserve the draft and require an explicit comparison/rebase. No new retry queue or duplicate draft owner is introduced.

## 6. State coverage

The identifiers below are **local Paper component IDs scoped to their atlas**. They do not replace the inherited R2 P01–P76 requirements, AC01–AC60 matrix or any existing task/acceptance namespace. Exact component nodes are in the companion design manifest.


### Evidence and selection

| Local component | User-facing state | Available action | Required behavior |
|---|---|---|---|
| S01/E01 | Source prints unavailable | Open available aggregate | Keep the $224,000 group; omit the six-print plot and quote split. |
| S01/E02 | Activity was corrected | Review correction | Original identity and return context stay visible. |
| S01/E03 | Activity was withdrawn | Return to Tape | Keep its identity. Do not select a neighboring row automatically. |
| S01/E04 | No matching activity | Edit filters | Scope: SPY · 20 Nov · premium ≥ $15k. |
| S01/E05 | Not published yet | Choose an available session | A missing publication is not a zero-exposure book. |
| S01/E06 | Refresh failed | Retry source read | Preserve the selected contract and visible source date. |
| S01/E07 | Access unavailable | View access details | Do not replace denied data with a different source silently. |
| S01/E08 | Independent SPY book | Continue with SPY context | The selected Flow group remains the origin for Back. |
| S01/E09 | Saved source unavailable | View saved reference | Keep the fingerprint and identity; do not show invented original values. |
| S01/E10 | Wing data missing | Open exact table | No fit or interpolation is implied by the empty region. |
| S01/E11 | Research only | Inspect evidence maturity | Candidate formation does not establish calibration or live authority. |
| S01/E12 | Terms unresolved | Check contract terms | One refused leg blocks the complete expression. |


### Drafts, save and revisions

| Local component | User-facing state | Available action | Required behavior |
|---|---|---|---|
| S02/P01 | Complete both legs | Calculate payoff (disabled) | No dated mark or net debit pre-fills authored inputs. |
| S02/P02 | Inputs changed | Recalculate | The prior curve is labeled as an older calculation. |
| S02/P03 | Saving revision | Saving… (disabled) | One admitted command and operation identity; no second write. |
| S02/P04 | Saved, still loading | Load saved revision | Commit is known. Retry only the revision read. |
| S02/P05 | Save result unknown | Check save status | Reconcile the original operation and target; no blind retry. |
| S02/P06 | A newer revision exists | Open latest revision | Compare revisions and rebase explicitly; no overwrite. |
| S02/P07 | Open the latest revision | Open revision 2 | A superseded revision cannot create an assessment. |
| S02/P08 | Plan saving unavailable | Keep editing Plan | Held exact-Plan capture remains a separate integration dependency. |
| S02/P09 | Leave this draft? | Keep editing / Leave draft | Use the existing draft owner. Never promise unproven reload recovery. |
| S02/P10 | Assessment: inconclusive | Save as revision 2 | Latest revision only; note ≤2,000 characters; selected event bound explicitly. |
| S02/P11 | Assessment saved | Open revision 2 | Success requires exact-revision readback from the existing command owner. |
| S02/P12 | Revision unavailable | Retry revision read | Keep its identity. Never silently substitute the latest revision. |


### Watch, delivery and return

| Local component | User-facing state | Available action | Required behavior |
|---|---|---|---|
| S03/W01 | Watch not armed | Review condition | Save and arm are separate existing commands. |
| S03/W02 | Arming watch | Arming… (disabled) | Do not show Armed before the owner confirms it. |
| S03/W03 | Watch armed | Manage watch | Existing five-minute evaluator; no new watcher service. |
| S03/W04 | Price condition met | Review case | Bind the exact selected firing when an event ID exists. |
| S03/W05 | Queued for delivery | Delivery receipt history | Matching outbox row: pending; delivered_at is null. |
| S03/W06 | Firing history unavailable | View available firing details | Fallback fire_event_id is null; do not claim exact-event binding. |
| S03/W07 | No firing recorded | Open watch condition | An empty result differs from an unreadable history. |
| S03/W08 | Watch expired | Review a new watch | A research horizon does not automatically extend a watch. |
| S03/W09 | A later firing exists | View later firing / Keep this firing | Freeze selected event identity for the assessment revision. |
| S03/W10 | Evaluation unavailable | View watch status | Never infer a working evaluator from a saved condition alone. |
| S03/W11 | No active saved case | Open Exposure investigation | Do not imply unsupported print or Volatility capture. |
| S03/W12 | Later observations available | View latest / Keep snapshot | Changing temporal mode preserves the original return context. |


### Narrow, locale and accessibility

| Local component | State | Required behavior |
|---|---|---|
| S04/A01 | Chinese revision conflict | Full explanation and two readable actions; compare revisions or retain the current draft |
| S04/A02 | Chinese exact source unavailable | Retain the exact contract identifier; show no invented original values and no latest-source substitution |
| S04/A03 | Keyboard return | Full outline and 44px target; restore original row focus/scroll or stable heading with an absence announcement |
| S04/A04 | Chinese direction and health semantics | Red-up / green-down uses text and signs; source health meaning does not flip |
| S04/A05 | Loading and reduced motion | Stable content geometry and static placeholders when motion is reduced |
| S04/A06 | 3D unavailable | Exact table remains usable with the same source, selection, units and missing values |
| S04/A07 | Invalid whole quantity | 1.5 is invalid; preserve input and require a whole quantity from 1 through 1,000,000 |
| S04/A08 | Review note too long | 2,001-character specimen exceeds the 2,000 limit; retain full text and ask for an edit, never silently truncate |

All 44 specimens were rendered and inspected. The final atlas review corrected user-facing evaluation cadence, ambiguity between firing history and delivery history, and focus return when an activity row has disappeared. Implementation notes in S01–S03 are explicitly labeled **Build note** rather than mixed into product copy.


## 7. Preservation, language coverage and original-node disposition

### 7.1 Original design ownership

Every original page and board in Appendix A of the masterplan remains a retained reference unless its pre-existing hold says otherwise. No original board was renamed, archived or deleted by this round. The new boards refine the composition and compose one common fixture; they do not certify every retained reference as production-ready.

| Original page / nodes | Disposition | New candidate and retained purpose |
|---|---|---|
| D08A p-16-0: 1SIB-0, 1Y3I-0 | Retain; refine in new owned boards | O01/O02 and M01/M02/M09/M10 provide the new shell and coherent activity case |
| D08A 21FC-0, 21KT-0 | Retain source-detail and exact-return grammar | Source inspection and return remain explicit; S01 adds correction/withdrawal and B03 binds focus behavior |
| D08A 21Y1-0 | Retain filter draft | Applied/draft filters, Apply/Cancel and source-default behavior remain part of the Flow build |
| D08A 1SO0-0, 1Y9X-0, 1YJQ-0, 1YLD-0 | Retain state/navigation references | S01/S03, M02/M07 and the source/default navigation contract refine without replacing these references |
| D08B p-12-0: 1NZL-0, 1OD3-0, 1OD4-0 | Retain Exposure exact-node semantics | O03/M03/M04 improve selection, units, dated source and save boundary |
| D08B 1PBQ-0, 1REL-0 | Retain matched/cohort comparison | O10 adds a coherent five-known/one-unknown example; added/removed cohorts remain existing obligations |
| D08B 1P0P-0, 1P85-0, 1QC6-0 | Retain 3D and exact table | T02 and A06 make the same-data table fallback explicit; no claim that the original Lab programme is complete |
| D08B 1Q0P-0, 1Q35-0, 1QA0-0, 1QXD-0, 1RIU-0 | Retain controls, selection, state and terms references | New state atlases supplement their source qualification and exact-identity requirements |
| D08B 1OMF-0, 1PG1-0; Volatility p-D-0 UM6-0, URH-0, UT6-0 | Retain expiry-led/source/missing behavior | O04, T01, M11 and E10 compose the new fixture and source clocks |
| Volatility XFO-0, XHI-0, XJA-0, XKM-0, XLX-0, XMP-0 | Retain EN/ZH picker/source/missing variants | These remain detailed expiry-source and unavailable-reference screens |
| Research Lab p-H-0: 18G0-0, 18OH-0, 18TJ-0, 18XX-0, 192N-0, 196F-0, 199N-0 | Retain original A–G-style deep research programme | O05/T02/E11/A06 clarify entry, maturity, exact tables and limitations; source retention/admission work remains owed |
| D08C p-13-0: 1NZZ-0, 1OGC-0, 1OL8-0, 1OUZ-0, 1OXF-0 | Retain deterministic Plan / Compare / revisit semantics | O06–O09, M05/M06/M12/M13 compose a single fixture and make unsaved scope explicit |
| D08C 1PU1-0, 1RQJ-0, 1RV0-0 | Retain input editor/details | Authored assumptions, source terms and narrow editing remain incumbent behavior |
| D08C 23BH-0, 23K7-0, 23DM-0, 23FL-0, 23IV-0, 243N-0, 2478-0, 24AK-0 | Retain provisional scenario and dirty-payoff semantics | O09/P02 do not override a source provisional disposition or silently promote it |
| D08C 1PXO-0, 1Q8U-0 | Retain save/watch/research state references | S02/S03 and B04 add source-checked current/target distinctions |
| Build p-P-1: CVN-0, FN2-0, FPC-0, G6A-0, KOX-0, LIJ-1, M89-1, OND-1, HD6-0, V0K-0 | Retain Build and science/source references | B01–B04 link the new candidate to existing owners and proof requirements |
| Build p-P-1: EJ5-0, KOW-0 | Preserve original hold / not-for-build disposition | A newer attractive candidate does not remove these holds |
| D08D p-2-0 / 1N2L-0 | **Held; read-only, no edit** | Preserve Futures / IEX temporal grammar and original refused-effect disposition; no substitute target replay |
| Adjacent p-Q-0 / 1B5H-0 and p-1-0 / 189S-0 | Preserve adjacent custody / holds | No overlap from this design round |

The earlier Plans/Save/Review/Scenarios/Compare pages and the twelve related reference pages remain covered by the original 245-board inventory. No blanket cutover or archive was performed.

### 7.2 Language and theme path

| Journey step | English representative | Chinese representative | Shared meaning |
|---|---|---|---|
| Overview and return | O01 | M09 | Material observed activity, independent source clocks, direct saved-case entry |
| Flow and source detail | O02, M01/M02 | M10 | Exact selected aggregate/children, unknown quote category, root-only Exposure handoff |
| Exposure and contract | O03 | M03/M04 | Known subtotal, selected contract, source/observation separation and supported save scope |
| Volatility | O04, T01 | M11 | Exact expiry, DTE source date, skew definition, missing IV rank and availability time |
| Research and Lab | O05 | T02 plus S04/A06 | Research maturity and same-data exact table; no invented authority |
| Plan | O07, M05 | M12 | Authored legs, expiry-only model, actual sampled price and unsaved draft |
| Saved case | O06 | M13 | Exact revision and original refs; excluded Plan is not a saved object |
| Watch preview | M08 | M14 | Separate arm, five-minute cadence, one-shot mode and explicit end time |
| Review | O08 | M06 | Observed firing, delivery state, missing source time and unselected assessment |
| Narrow/error behavior | S01–S04 | S04/A01/A02/A04/A05/A06/A08 | Full copy, retained input and identity; no semantic change under localization |

Both light and dark families are deliberately represented. This is targeted coverage of changed journeys, not an indiscriminate product of every screen, language, theme and viewport. Existing 768px references remain retained even though the new tablet boards use 820px. The 320px specimens are components, not full phone screens; full phone boards include the prescribed status bar.

Chinese translation is semantic. “Gamma · 净敞口” replaces the misleading “净值.” The original observed price has an explicit 9 Nov 10:19:58 ET clock; it is not labeled as an undated current quote. Risk reversal names Call-minus-Put. Source unavailability, save uncertainty and assessment are translated as distinct concepts.

## 8. Source bindings and design-driven architecture requirements

These are concrete findings for round 3. They are not a second architecture programme or permission to activate held work.

### 8.1 Flow detail requires actual child-print evidence

At the targeted source pin, `FeedPane.FlowEvent` exposes an aggregate timestamp, `n_prints`, size, average price, premium, side and signing source. `projectFlowPrint` explicitly leaves receipt time, conditions, lineage and quote null. Its current coverage function classifies eligible premium by estimated buy/sell/mixed side, not by a qualified NBBO/at-ask classification. [R2-S01] [R2-S02]

Therefore the six-print timeline, individual clock list and at-ask/unknown partition must be admitted through a versioned extension to the existing Flow producer/API. It needs stable parent/child identities, original and corrected versions, a qualifying quote method and clock, unclassified reasons, and reconciliation of child counts/contracts/premium to the aggregate. Its UI projection must distinguish aggregate availability from child availability.

`FlowDeskView` already imports and uses the incumbent `useFlowStream` and shared Flow cache. Extend that ownership; do not create a second collector, streaming loop, cache plane or global selection store. This review inspected the consumer's binding; it did not recertify the internals of every imported transport module. [R2-S03]

The new child evidence must not be inferred from chain-heat categories, estimated side, relative volume or adjacent events. E01 is a useful degraded state while that data is absent. A source correction preserves original identity and requires explicit review; a withdrawal must not select a replacement row.

### 8.2 Saved evidence is a qualified reference

The original saved-case machinery retains evidence refs and digests; a reference is not a durable copy of arbitrary source values. The original +$200m book can be displayed only when its exact qualified source resolves. If it does not, E09 keeps the saved identity and explains the absence. Round 3 must bind retention, resolver, correction and first-availability behavior to the existing evidence owner. [01_MASTERPLAN.md, §§4, 8.5](01_MASTERPLAN.md)

Original evidence, latest evidence and comparable evidence are three separate reads. A latest price trigger cannot fill a missing Exposure comparison. A current source response cannot silently stand in for the original pinned book.

### 8.3 Exact Plan draft and persistence remain different

`OptionsShortlistPlan` owns a local draft session keyed by account/scope and retained pins. Close clears the draft; unmount signals its absence. The current source does not support a promise that the exact Plan will survive switching to Saved, closing the editor or reloading. P08/P09 and O06/M13 state that honestly. [R2-S09]

`OptionsPlanInvestigationHost` is preparation-only, explicitly unmounted until native admission and embedded-history interfaces are delivered. B04 is the target experience after those interfaces are admitted and the original work's release conditions are resolved. It must use the existing draft, admission, command and history owners. [R2-S06]

The field mapping is not a simple copy. Plan research thesis/invalidation accept up to 4,000 codepoints and its single-line horizon up to 160. The existing Investigation horizon is limited to 64; question/continuation limits depend on the existing manifest version. Investigation has authored continuation fields rather than a dedicated Plan invalidation field. No silent truncation, renaming or repurposing is allowed. Case question, horizon and reassessment/next-observation intent need an explicit authored mapping and validation. [R2-S07] [R2-S08]

### 8.4 Assessments reuse the existing revision pathway

The current Review panel accepts confirmed, contradicted or inconclusive, optional notes and a firing identity. `assessmentRevision` copies the original manifest and adds the review block for the existing revise command. The original revision is not edited in place. The UI already gates a superseded revision and requires an assessment before saving. [R2-S04] [R2-S05]

The target hardening is precise event selection: a new firing must not silently change the event being assessed while the user writes. Freeze an explicit selected qualified firing identity, and offer W09 when a newer firing appears. The current projector chooses the latest firing; that is not automatically an explicit older-event review capability. [R2-S05]

The current textarea uses native `maxLength`, while its visible counter uses codepoints. Round 3 must reconcile Unicode counting and the target A08 preserve-text error behavior; do not assume that a native input limit already implements the designed over-limit state. [R2-S04] [R2-S07]

The manifest expects a 64-hex firing identity where present and caps notes at 2,000. The fixture uses a synthetic valid-shape identity. The implementation must use a real qualified event from the incumbent receipt owner, not copy the fixture ID or manufacture an ID for a trigger-stamp fallback. [R2-S07]

### 8.5 Firing and delivery states have different evidence

The outbox migration makes status non-null with the allowed values pending, deferred, sent, failed and suppressed. A readable matching row with no status is not a normal valid fixture for “delivery unknown.” Main Review therefore uses a matching pending row and no delivered timestamp. [R2-S10]

If receipt history cannot be read, `receiptsFrom` can project an available trigger stamp, but no exact event ID or delivery state is invented. W06 explicitly calls this firing history unavailable and exposes only available firing details. Readable empty history is W07. A saved watch with unconfirmed evaluator behavior is W10. [R2-S05]

Save, Arm, evaluation, firing, queued delivery, actual delivery and human assessment remain distinct operations/statuses. Scheduled evaluation cadence and one-shot/expiry semantics stay visible. No new watcher or retry service is introduced by the UI.

### 8.6 Research authority stays with its existing owners

O05 presents two Flow research books as accruing and Options Alpha v2 as inactive according to the retained programme status. The eight broader Prophet families remain research taxonomy; they are not eight activated Options sleeves. Formation, source freshness, sample coverage, outcome maturity, calibration and permitted claims are separate.

All six original pilots, registered losses/horizons, family correction, staged validation/test separation, formation policy, OA3's narrower evaluator domain and promotion gates remain as recorded in the masterplan. No attractive card, confidence ring, combined frontend score or profitable synthetic payoff supplies trading authority. Round 3 must map each desired signal to a specific admitted claim and observable evidence state.

### 8.7 Matrix and temporal work remain separate dependencies

Research Lab's Matrix-specific source binding and source-use/admission decision remain an existing frontier. The exact table makes degraded rendering useful, but it cannot grant an absent source admission. Wrong-account, wrong-root and unqualified epoch results must be withdrawn before display.

Futures mapped exposure and IEX equity replay retain their native contract/session/artifact/sample/cutoff grammars. A common shell does not mean a common unqualified global replay cursor. The original D08D hold is not cleared by B01–B04 or by any new candidate page. Refresh only affected custody/hold facts before overlapping implementation in a later round.

## 9. Verification performed and its limits

### 9.1 Actual design verification

- Exact file identity and four new page identities were read back. Counts are 10 Product, 16 Responsive, four States and four Build boards: **34**.
- All new root nodes returned JSX. The final text-leaf inspection covered **1,604** leaves with no missing explicit font assignment in the examined leaves.
- Actual Paper screenshots were inspected for the main desktop journey, two comparison boards, all responsive screens, four atlases and four build boards. Newly changed Chinese screens were checked after refinement.
- The state atlas review found no clipped headings, body copy or actions. Necessary cadence/history/focus corrections were applied and visually read back.
- Exposure current/prior values, known subtotals, selected contract and matched differences were checked. O10's All 6 filter matches the six displayed rows.
- The 20-point focused payoff SVG was checked against the existing source sample subset and the deterministic formula. The comparison's $50 shift and analytic summary values were checked.
- Chinese net-exposure wording and observation clocks were corrected. Language paths now share the same fixture and current/target limits.
- Parent font inheritance did not reliably produce the intended imported Paper text. Explicit font assignments were applied, then JSX was re-read; the final result does not rely on assumed inheritance.
- Every edit in the retained operation ledger returned an observed-applied response. Exact owned boards were finished through Paper's working-indicator operation. No ambiguous edit effect remains recorded.
- Other page/divider relative order was compared before and after grouping the four new pages. Held D08D was read only and was not a mutation target.

Inactive Paper pages can return null layout/world coordinates until measured in the active page context. This is a known read limitation; null coordinates were not treated as evidence that the board was absent. Individual screenshots and node/JSX readback supplied the design verification.

### 9.2 Corrections incorporated

| Finding | Applied correction |
|---|---|
| Side-estimate coverage could be mistaken for quote evidence | Explicit target child-print extension, source binding and E01 aggregate fallback |
| Unknown sixth Exposure member shown under Matched 5 | O10 now selects All 6; cohorts remain separately named |
| Exposure selected-contract context was not clear on chart | Neutral whole-row selection and Selected label; units/legend moved beside chart heading |
| Observation could be read as a current reprice | Explicit observation date/time and independent historical book copy |
| Chinese 净值 changed the meaning of net exposure | Corrected to 净敞口 |
| Plan sample could look like an arbitrary new model input | Labeled selected existing expiry-price sample; actual 103/20 sample contract retained |
| Save/reopen might imply a retained exact Plan | Current Plan-saving limitation and leave-draft warning; no Resume promise |
| Review might allow save without assessment | Explicit unselected assessment and disabled Save |
| Missing delivery status on a readable fixture contradicted schema | Valid pending outbox row with null delivered timestamp; separate unreadable fallback |
| A later firing could change the assessment target | Explicit selected-event requirement and W09 |
| Atlas implementation instructions could be mistaken for product copy | Build note prefixes |
| Evaluation cadence hidden in build annotation | User-facing five-minute cadence in armed/preview states |
| Withdrawn row had no focus-return target | Stable Tape heading/control fallback and absence announcement |
| New Chinese primary path depended on older screens | Added M09–M14 with the same fixture and complete primary language path |
| Responsive menu glyph was too small | Consistent 20px icon in a 44px target on all responsive boards |

### 9.3 Not claimed

No application source implementation, database migration, runtime installation, broker action, model activation, deployment or Fable dispatch occurred in this round. No browser transaction, CI result, live data provenance or scientific performance result is inferred from Paper. No requirement is marked complete merely because a design card exists.

The original 130 OPR competitor requirements, 123-claim supersession register, AC01–AC60, R1 journeys, R2 P01–P76, OPT obligations and G/D/F/M/V/N/Q/U/R graph remain intact. This round does not certify competitor parity or exhaust the entire inherited research programme.


## 10. Round 3 continuation and final-plan obligations

Round 3 begins from this actual design, not a renewed blank-page census. Read the same canonical PR, the four Paper pages and only changed source/custody/hold facts.

### 10.1 Decisions to close in the architecture hardening round

| Priority | Decision / work product | Existing owner / constraint | Required evidence for the final plan |
|---|---|---|---|
| 1 | Typed Flow child-print evidence and aggregate fallback | Existing producer/API, Flow transport/cache, source/entitlement owner | Versioned shape, stable correction identity, quote qualification, declared denominator and reconciliation fixtures |
| 1 | Exact Plan admission, capture and reopen | Existing Plan draft, Investigation admission/command/history; #804 / D23 hold | Exact field mapping, input limits, retained terms/calculation, expected revision and success/unknown/conflict pathways |
| 1 | Source reference resolver and historical availability | Existing evidence/retention owner | Original unavailable versus corrected/latest source; lawful first availability; reproducible original book |
| 1 | Explicit firing selection for assessment | Existing Review projector, alert receipts and revise command | Latest versus selected event, unreadable/absent history, null identity fallback, no event switch during edit |
| 1 | Scope/epoch invalidation and async result binding | Existing Options workspace/router and draft owners | Wrong-root/account/revision and late-response counterexamples with retained return context |
| 2 | Route and subview implementation crosswalk | Existing fifteen view keys and stable aliases | Every button in §5 maps to an actual source path, state owner, admitted action or explicit unavailable state |
| 2 | Matrix/Lab source binding and exact-table behavior | Existing research source-use/admission contracts | Real dependency/source decision and same-data 2D/3D/table proof; no generic cache substitute |
| 2 | Performance and accessibility budgets | Existing product targets in masterplan §10 | Critical path and virtualized tables; focus/zoom/touch/locale proof on actual supported browsers |
| 2 | Per-claim signal and sleeve maturity | Existing formation/evaluation/campaign/promotion owners | Named signal claim, population, clocks, cost assumptions, uncertainty, falsifiers and permitted actions |
| 2 | Deployed acceptance and existing graph mapping | Existing AC/OPR/OPT/R1/R2 and G/D/F/M/V/N/Q/U/R requirements | Owner/path/test/production-proof/dependency mapping for each deliverable; preserve unrelated release holds |

The final architecture must remain useful when a lane is unavailable. A missing child feed leaves an honest aggregate. A missing wing leaves an exact partial table. An unavailable saved source leaves its original identity. A held Plan save leaves an explicit draft. Inactive research leaves inspectable maturity and descriptive evidence.

### 10.2 Round 4 final handoff requirements

The final Fable-led T3 packet should contain the consolidated masterplan, exact Paper bindings, implementation graph with incumbent owners and dependencies, typed interface deltas, source/authority gates, numerical and failure fixtures, required affected tests, authenticated production proof, rollout/recovery expectations and explicit DONE_WHEN.

It must preserve the original 130 OPR requirements, 123-claim supersession ledger, AC01–AC60, R1 journeys, R2 P01–P76 and original research pilot programme. Every deferred capability needs a real owner and admission/proof condition; “later” without a binding is not a finished plan.

This turn does not send that handoff, start workers, authorize spend or release held implementation. The four-turn commission remains the governing session structure: round 2 finishes the Paper candidate; round 3 hardens the architecture; round 4 finalizes the implementation commission.

### 10.3 Continuity record

- **Mission:** complete the Chairman's four-turn Options census/design/architecture/final-masterplan programme.
- **Current result:** round-2 Paper candidate and build contract complete, with 34 boards and 44 local state components.
- **Canonical sources:** this document, [01_MASTERPLAN.md](01_MASTERPLAN.md), [03_PAPER_MANIFEST.json](03_PAPER_MANIFEST.json), and draft PR #10898.
- **Mutation scope:** fresh Paper pages p-1O-0 through p-1R-0 and this existing documentation carrier. No application/runtime/source-data/model mutations.
- **Do not redo:** original census, original accepted work, original 245-board inventory, completed numerical fixture, read-back design inventory, targeted source reads absent relevant changes.
- **Preserve:** exact original holds/custody from round 1, especially D08D 1N2L-0, Plan #804, Matrix and scientific promotion boundaries. A new design board does not clear any hold.
- **Children:** bounded visual, quantitative and acceptance reasoning reviews completed; no implementation workers are running.
- **Tool state:** Paper and GitHub-native source/document authoring were serviceable at closeout. The transient local executor was unavailable; no local filesystem test or artifact save is claimed for this closeout.
- **Next action:** round 3 reads this package and hardens the actual owner/schema/dependency/acceptance map, starting with §10.1.
- **Finalization:** PROVEN_OUTCOME is scoped to this round-2 design deliverable after canonical readback. The full four-round programme and production implementation remain incomplete.

## 11. Evidence and source register

Paper page and node links are in §2; exact observations, state IDs and verification results are also recorded in the companion manifest. The following source links are pinned to the affected Terminal cut, not moving main.

| Ref | Source | Finding supported |
|---|---|---|
| R2-S01 | [FeedPane.tsx][R2-S01] | Aggregate FlowEvent fields and side semantics |
| R2-S02 | [flowPrintInspector.ts][R2-S02] | Null child/quote/lineage fields and estimated-side premium coverage |
| R2-S03 | [FlowDeskView.tsx][R2-S03] | Existing stream/cache consumer bindings |
| R2-S04 | [InvestigationReviewPanel.tsx][R2-S04] | Assessment choices, disabled save, superseded revision and note UI |
| R2-S05 | [investigationReview.ts][R2-S05] | Receipt projection/fallback, latest firing and immutable assessment manifest |
| R2-S06 | [OptionsPlanInvestigationHost.tsx][R2-S06] | Preparation-only host pending native admission/history |
| R2-S07 | [investigationContracts.ts][R2-S07] | Case fields, horizon limit, review note limit and firing identity shape |
| R2-S08 | [optionsPlanDraft.ts][R2-S08] | Authored assumptions, terms, text/quantity validation and horizon limit |
| R2-S09 | [OptionsShortlistPlan.tsx][R2-S09] | Local draft lifetime, account/selection binding, close and unmount behavior |
| R2-S10 | [0013_alert_runs_outbox.sql][R2-S10] | Non-null outbox status and allowed delivery states |

The retained broader census, accepted progress, source contracts, science programme, design doctrine and historical carrier states are sourced in [01_MASTERPLAN.md, §14 and Appendices A–C](01_MASTERPLAN.md). Do not interpret this targeted source refresh as reacceptance or release of all historical carriers.

[R2-S01]: https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/2fe2f02f07d1df8c855388bc556383cd74de44fd/terminal/components/flowdesk/FeedPane.tsx
[R2-S02]: https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/2fe2f02f07d1df8c855388bc556383cd74de44fd/terminal/lib/flowPrintInspector.ts
[R2-S03]: https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/2fe2f02f07d1df8c855388bc556383cd74de44fd/terminal/components/flowdesk/FlowDeskView.tsx
[R2-S04]: https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/2fe2f02f07d1df8c855388bc556383cd74de44fd/terminal/components/workspaces/InvestigationReviewPanel.tsx
[R2-S05]: https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/2fe2f02f07d1df8c855388bc556383cd74de44fd/terminal/lib/investigationReview.ts
[R2-S06]: https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/2fe2f02f07d1df8c855388bc556383cd74de44fd/terminal/components/options/OptionsPlanInvestigationHost.tsx
[R2-S07]: https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/2fe2f02f07d1df8c855388bc556383cd74de44fd/terminal/lib/investigationContracts.ts
[R2-S08]: https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/2fe2f02f07d1df8c855388bc556383cd74de44fd/terminal/lib/optionsPlanDraft.ts
[R2-S09]: https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/2fe2f02f07d1df8c855388bc556383cd74de44fd/terminal/components/options/OptionsShortlistPlan.tsx
[R2-S10]: https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/2fe2f02f07d1df8c855388bc556383cd74de44fd/supabase/migrations/0013_alert_runs_outbox.sql
