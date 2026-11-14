# Research Explore — engine and implementation blueprint

Status: DESIGN CANDIDATE / IMPLEMENTATION NOT STARTED
Owner: Chairman's 14 November 2026 Research Explore assignment.
Parent: [Research Explore migration record](../RESEARCH_EXPLORE_SHARED_SHELL_2026-11-14.md).
Detailed contracts: [Policy Watch R6](POLICY_WATCH_R6_BUILD_SPEC_2026-11-14.md) · [Policy Watch R7](POLICY_WATCH_R7_BUILD_SPEC_2026-11-14.md) · [BioCatalyst R11](BIOCATALYST_R11_BUILD_SPEC_2026-11-14.md) · [Alternative Data R2](ALTERNATIVE_DATA_R2_BUILD_SPEC_2026-11-14.md) · [Research Hub R6](RESEARCH_HUB_R6_BUILD_SPEC_2026-11-14.md) · [Special Situations R2](SPECIAL_SITUATIONS_R2_BUILD_SPEC_2026-11-14.md).

## 1. Objective and source binding

Give every Explore destination a useful shared-shell journey: identify the subject, understand what changed, inspect the exact supporting record, compare a meaningful alternative and return without losing context. Preserve advanced capabilities through named destinations and progressive disclosure. The design must improve the quality of an answer, not merely its presentation.

Procedural pin: Mastermind@199fd4f91ecc426b1d974eb3bf47f5162476cf24.
Product pin: macro@e856ef0200a0c508c78ef9a6666116020e4835d1.
Terminal pin: mastermind-terminal@fe49f3b5765dd4e10721928716a6a730e78c7ae1.
Git carrier: sol/research-explore-paper-20261114-c4.
Native design mutations: exclusively the qualified M1 Paper v20 bridge, additive owned pages.

This blueprint proposes consumer adapters and upgrade work. It does not assert that every API field below currently exists. Existing producers, authenticated routes, persistence owners and release holds remain authoritative. Reconcile their current state before implementation. Do not create another collector, research database, ranking engine, alert scheduler or identity system to make a design appear functional.

New Paper values are synthetic fixtures unless a layer explicitly says it uses curated seed dates for a layout specimen. They are not current market claims, validated forecasts, clinical conclusions or evidence that an endpoint works. In particular, the fictional companies/cases/NCT9 trial IDs and the RIVT scenario are not instruments to act on.

## 2. Shared shell and interaction system

### 2.1 Reuse the actual application owner

Terminal's terminal/components/chrome/AppShell.tsx, SharedShellPresentation, existing navigation catalogue, auth and context providers own the application frame. The design uses the inspected 224px expanded rail, 72px collapsed rail and 64px desktop topbar. At 1440px, the body begins at x=256 and has 1152px usable width. The mobile topbar is 60px; most phone views use 20px side gutters.

The Research navigation admission must be added through the incumbent route catalogue. Legacy .html paths below are known; proposed native route slugs are deliberately not invented here. Map each legacy route to the admitted native destination and preserve incoming deep links, entitlement checks and return context. The shared shell owns company search, locale, theme, account, global notifications and navigation. A desk may expose a scoped record filter, but it must not install another global search or account owner.

### 2.2 One coherent visual vocabulary

Use a neutral background, neutral panel borders, legible Inter type and one purposeful action color. The light specimens use #F7F8FA canvas, white panels, #1C2430 primary text, #5D6B7E secondary text and #285FFF actions. The dark specimens use #0F1115 canvas, #181B21 panels, #D7DCE3 primary text, #8B93A1 secondary text and #7AA7E0 analytical emphasis. Map these to the canonical token system during implementation; do not hardcode a second theme owner.

Page titles are usually 28px; section titles 17–20px; primary body 13–16px; secondary data 11.5–12.5px. A caption must answer an actual interpretation or timing question. Avoid colored card rails, large empty introductions, repeated live badges and explanatory paragraphs that restate a title.

A compact badge is reserved for consequential status: Proposed, Partial coverage, Frame, Revised record or an unresolved identity. Do not make every row into a badge collection. Put full formulas, source ingestion details and implementation notes in Build or evidence detail.

### 2.3 Interaction contract

- Row click or Enter opens its exact source-owned record. A selected row and its detail pane share the same stable identity.
- Desktop supporting panes become full-width sheets or pages on phones. Close/Escape returns to the triggering control and restores the selected record, filters, sort, clock, range and scroll.
- Browser Back/Forward and deep links preserve the same state. An evidence source may open separately without discarding the desk.
- Chart selection synchronizes the roster, highlighted line or interval, selected date and inspector. Keyboard users get an equivalent list/table and explicit previous/next controls.
- Filters expose the active value. Changing an issuer, basis, universe or historical cutoff makes incompatible prior data visibly pending instead of relabeling it.
- A numeric input is editable text with a unit; assumptions are distinguishable from source facts. A change can create a dirty draft, but displayed results keep their prior request identity until the canonical recalculation returns.
- Save confirmation follows a confirmed effect. Preserve a draft on failure. Clearly distinguish device-local, account-saved and unsupported persistence.
- A source failure is not an empty result. A stale record is not a fresh zero. A missing amount is not 0. Use the smallest useful explanation next to the affected answer.
- Touch targets should meet the existing accessibility standard. Phone action rows must wrap or change composition rather than shrink text. Avoid page-level horizontal overflow; comparison matrices may have a deliberately bounded scroll region with sticky identity.

### 2.4 Proposed projection envelope

A Terminal read adapter should preserve, rather than replace, the owner envelope. It needs:

| Field family | Meaning |
|---|---|
| Owner and schema | Existing producer, contract version and source route |
| Record identity | Canonical entity and domain case/trial/policy/award ID |
| Request identity | Entity, mode, cutoff, clock, basis/universe and scenario; preserve each domain's exact request key |
| Evidence clocks | Event/effective date, publication/filing date, first observation, revision and snapshot cutoff |
| Source lineage | Exact original record, source version, derived-from relationship and correction/supersession chain |
| Coverage | Covered, partial, unsupported, unavailable, stale, conflicting, withheld or not yet observed |
| Values | Typed unit, currency, basis, date precision and null reason |
| Capabilities | Which actions exist and are permitted for this user and record |
| Navigation | Exact source desk destination, focus/selection and reversible return context |

These are adapter requirements, not permission to rename existing fields without compatibility. Domain-specific types are mandatory. A generic “score/value/status” object is insufficient for legal policy stage, registered dollars, obligations, trial dates and cycle position.

## 3. Policy Watch

### Source owners and retained feature map

Use engine/policy_watch_current.py, engine/policy_intent_desk.py, engine/transmission_chains.py, scripts/build_policy_watch.py and their current source artifacts. Preserve policy_watch_current.v1 and policy_lifecycle.v1. The dedicated R6 specification contains the full contract and state matrix.

| Existing capability | New named destination | Disposition |
|---|---|---|
| Current official decision/calendar/headlines | Now and decision detail | Improve ordering and source clocks |
| Policy stage and lifecycle history | Policy pipeline and change dossier | Retain legal-stage semantics |
| Statements and comparisons | Central banks / Compare statement wording | Separate recorded decision from interpretation |
| World / Influence / Exposure | Policy detail / transmission / company exposure | Relocate into inspectable drill paths |
| Market Memory | Market memory | Preserve regime and historical comparison boundaries |
| Research, calls and outcomes | Research / evidence history | Preserve issued-call and outcome ownership |

### Advanced work to build

The change dossier is the central interaction: before/after clause or field, issuing authority, legal stage, effective dates, known scope and unresolved exemptions. A proposal cannot acquire an in-force treatment because it is important or recent. Transmission edges should reveal their evidence and status one edge at a time; an affected industry does not establish a company's reported exposure.

Central-bank pricing and policy decisions have different meanings. The R6 specimen uses an observed target range and a market-implied expected midpoint. Production must name the actual derived quantity, meeting, pricing timestamp and inputs. Do not connect a futures-implied midpoint as though it were a decided policy path. “Our read” is dated interpretation and remains visibly distinct from the official action.

Policy pipeline, Market Memory and Research need their remaining destination-specific compositions and responsive/theme/locale checks before design completion. Keep this debt visible rather than treating the four primary R6 screens as the entire product.

### Engine and proof work

Validate deterministic lifecycle transitions, corrections, superseded records, event cancellation and unavailable comparisons. Source publication time and page build time must stay separate. If a source has not provided the next statement, the view explains what is missing and retains the last known record with its timestamp. Prove actual official source → normalized record → native decision/diff → exact source → return, plus policy exposure and calls/results ownership.

### Authored deeper Policy journeys

R6 now includes the lifecycle pipeline, a 41-trading-session Market Memory comparison, research calls, an evidence-linked transmission path and company exposure. The pipeline's All dates filter retains an undated next step without making up a calendar date. Historical comparison uses ±20 sessions and distinct solid/dashed series with matching keys; an episode comparison is not causal attribution.

Calls retain the original proposition, resolution event, recorded horizon or review date, observed evidence and evaluation. A resolution event such as final-rule publication is not itself a review deadline. If the original call has no review date, show that absence instead of inventing a deadline or treating the pending state as a scored success.

Transmission selects a particular edge and opens its exact policy-version span. Keep the edge's evidence class and legal dependency: source wording, conditional interpretation and unresolved company exposure are different states. Company exposure follows reported business → product definition → destination → revenue effect, retaining the unavailable links. A sector label or issuer-wide geographic revenue cannot establish a shipment's product classification or a license outcome.

The native implementation should retain policy_id, policy_version, selected_edge_id, issuer_id and return state through source navigation. These are proposed consumer identity requirements; map them to incumbent owner fields rather than create a second graph database. Changing the legal stage or selected version must invalidate dependent interpretation while preserving its dated history.

## 4. Government Revenue

### Source scope

This is procurement research, not tax revenue. Preserve app/government_revenue.py's thirty authenticated read routes over precomputed data and require_site_full_user. Reuse the existing procurement producers and research_state owner. The masterplan is research/GOVERNMENT_REVENUE_FORESIGHT_MASTERPLAN_FOR_FABLE.md.

The existing workbench has nine modes: Candidate Radar, Changes, Award Activity, Opportunities, Recompete, Budget/Programs, Program Dossier, Companies and FMS Notifications. The new top-level groups Changes / Companies / Programs / Calendar / Saved are navigation, not a license to remove those modes.

### Product and capability map

| New group | Required reachable work |
|---|---|
| Changes | Source changes, candidate radar, award activity, exact transaction diff |
| Companies | Recipient → public issuer evidence, company funding history, relevant filings |
| Programs | Budget/program changes, program dossier, FMS notifications and their distinct legal meaning |
| Calendar | Opportunity deadlines, recompetes, contract end dates and relevant dated actions |
| Saved | Saved filters, research references and truthful change-check scope |

R13's entry screen prioritizes a short funding-change queue and an exact selected award. Amounts are individually typed: obligations, de-obligations, potential contract ceiling, bookings, funded backlog, issuer-reported backlog and recognized revenue. Never sum them into a generic government-revenue figure. A large ceiling is not an appropriation, obligation, order, backlog or recognized revenue.

The evidence view follows official award → recipient → public issuer. Unknown or ambiguous mapping stays visible and can be investigated without fabricating a ticker. An issuer match does not resolve revenue timing or materiality. The user's useful next step is the relevant filing or programme evidence, not an inferred percentage of future revenue.

### Upgrade requirements

1. Carry exact award/IDV/order/modification identity, not only company and amount. Preserve original recipient IDs, hierarchy, parent mapping evidence and effective dates.
2. Model source revisions and withdrawals explicitly. Before/after values identify the measure and unit; preserve the predecessor. A correction is not a new independent bullish event.
3. Freeze a consistent snapshot for paging. If the source changes mid-page, explain that a refresh is needed rather than mixing generations.
4. Attach the materiality denominator only when its definition, period and source are known. Keep missing denominators distinct from immateriality.
5. Preserve source-owned candidate research state. The inspected research_state.py reports not_started/is_running=false/zero outcomes; do not invent efficacy cards or issued forecasts.
6. Respect the Prophet integration ruling: procurement can annotate an already selected candidate; it cannot mint or size picks through this migration.
7. Saved views and refresh-only alert behavior remain browser-local until an authorized canonical account migration is implemented. The R13 state sheet explicitly confirms “Saved on this device” and checks on open/refresh. Do not promise background monitoring.

### Acceptance proof

Use actual award records, a correction, an unresolved recipient and a known issuer link. Verify record-time versus first-observed time and a snapshot no earlier than its included observations. Open the exact award, inspect its transaction, preserve access and paging, save within the actual supported scope, reload, and return to the same filter and selected award. Revenue timing must remain unresolved unless actual issuer evidence establishes it.


## 5. Alternative Data

### Source and feature map

Reuse altdata.py, altdata_models, altdata_signals, altdata_emit, altdata_alerts, altdata_ledger and altdata_brain. Preserve the by_ticker.v2 and mastermind.v1 compatibility surfaces. The inspected co-firing event-cluster logic groups channel taxonomy; it is a dependence heuristic and does not establish record-level independence. Primary-origin and derived-record identities are still required.

Companies is the investigation list. A row explains the observed reason it surfaced, event groups, primary sources and reporting date. Evidence detail groups a transaction, filing and derived provider row together. Relationships opens one inspectable edge at a time. Change tape and Evidence history retain source revisions and evaluation history. Preserve insider, congressional, contracts, lobbying, off-exchange, institutions, apps, patents, retail and corporate-event channels through scoped channel filters.

### Advanced capabilities and boundaries

- **Evidence grouping:** carry event_group_id, primary source identity, related-record identity and derived-from lineage. Two providers quoting one filing are not two independent confirmations. Count event groups and primary sources separately.
- **Three clocks:** show event date, public reporting/filing date and first observation. A delayed disclosure is new information about an older event, not new underlying activity.
- **Relationship inspection:** issuer, subsidiary, executive, legislator, agency and patent assignee links need dated evidence and unresolved identity states. Do not turn a co-occurrence into a causal relationship.
- **Research outcomes:** expose existing source-family/cohort/horizon definitions, outcomes and adverse results. Respect article3/is_context_only and historical maturity findings. The redesign cannot silently promote contextual research to a validated predictive signal.
- **Coverage inspector:** distinguish 401/403, provider outage, schema failure, no matching records, empty payload and delayed records. Only describe a channel as current when its relevant observation supports that status.
- **Question-led investigation:** the fixture's “Was this purchase prearranged?” and “Does the patent change the business?” are next checks, not asserted answers. A patent family's publication alone does not establish commercial impact.

### Engine work and proof

Strengthen lineage and source-family state normalization in the existing producer rather than starting a second aggregation service. Establish deterministic duplicate grouping, preserve correction chains and reject incompatible schema changes explicitly. Native UI reads owner-issued order or user-selected sort; it does not create a blended ranking.

Prove one actual event appearing through multiple records, an older transaction reported later, a correction, an unresolved relationship and an unavailable channel. Ensure the context-only gate survives every view, export and deep link. Any proposed predictive upgrade has a separate point-in-time evaluation with costs, dependence and adverse-result review; this build does not authorize it.

## 6. Special Situations

### Source owners

Reuse engine/special_situations.py, special_situations_premium.py and build_special_situations.py. The roadmap research/SPECIAL_SITUATIONS_ROADMAP_V2.md is useful context, but old “not built” entries cannot override the inspected implementation: terms, lifecycle, arbitrage arithmetic, activism/international lanes, reviewed extraction and technical gates already exist.

### Product structure

Events answers what corporate action exists and the next known milestone. A case opens Terms / Timeline / Conditions / Sources / Market context. Calendar and Tracked retain case identity. The design preserves cash/stock consideration, exchange ratio, collars, tender range, expiration, shareholder vote, distribution date, outside date, company closing guidance and conditions where supported.

Terms, expected closing guidance and legally defined outside dates are different fields. A scheduled vote is not approval. An agreement's financing condition cannot be inferred from a short news summary. The source action remains available beside the unresolved condition. A repurchase authorization is not executed repurchases.

### Case identity upgrade

The inspected grouping by CIK/category and issuer-wide terminal flags may contaminate distinct same-issuer cases. This is a hypothesis requiring reproduction, not a declared production defect. Design the repair around stable case identity derived from the actual transaction and evidence chain: issuer, counterparty or subject, agreement or event identifier, relevant filing lineage and effective history. Maintain explicit links between related events without merging their lifecycle automatically.

Use a reproduction with multiple mergers and a separate repurchase for one issuer. A termination or completion can close only the matching case. An amendment belongs to its original agreement. Preserve correction and supersession relationships. Keep ambiguous cases unresolved rather than guessing which event a filing closes.

### Typed consumer and calculations

The paid payload currently contains rows_html/setups_html. Provide a typed owner projection for native rendering with the same entitlement checks; do not scrape the markup into a parallel truth engine. Preserve source timestamps and completeness. A thin local store must not overwrite richer published data; pure rerenders retain the underlying evidence as-of.

Unaffected-price premium uses the trading-day close strictly before the first relevant filing and refuses ambiguous issuer joins. Spread arithmetic must identify currency, consideration, price time and assumptions. A spread is not a close probability, an assured annualized return or a recommendation.

### Proof

Verify exact case deep links, a terms amendment, a condition update, a scheduled event becoming known, a terminal event and a same-issuer unrelated case. Check paid access on list and detail, source identity, pre-filing price basis, stale market prices and return state. A scenario or market-context panel cannot change the factual lifecycle.

## 7. BioCatalyst Intelligence

### Source and factual views

Reuse app/biocatalyst.py: catalyst-radar, trials:screen/facets, trial-peer-sets:resolve, trials/change-tape, prospective-changes and trials/{nct}. The five factual views are Milestones, Trial screen, Peer matrix, Changes and First-seen. No probability, score, materiality rank, composite or implied efficacy assessment is added.

R10's milestone timeline uses a full date interval for month precision and a day marker only for day precision. Trial detail displays changed registry fields beside the prior version and separate update/publication/observation clocks. The explicit peer matrix compares selected trial characteristics and exposes differences in treatment setting, endpoint and assessment timing.

### Advanced capabilities

1. **Precision-aware chronology.** Carry source text, precision, inclusive bounds, estimated/actual flag, registry version and event kind. Do not replace a month or year with a midpoint. A passed estimate with no update remains an expired estimate, not a failed trial.
2. **Version inspection.** Diff primary completion, study completion, status, enrollment, endpoints and study design neutrally. An increased enrollment or changed endpoint is not automatically favorable.
3. **Explicit peer construction.** Resolve 2–100 user-specified NCT IDs; preserve IDs and order. Record selection criteria. The matrix supports field selection, difference inspection and a bounded mobile comparison region; it does not choose a “best” peer universe.
4. **Clinical comparability.** Phase and indication alone are insufficient. Retain population, line of therapy, comparator, endpoint definition and assessment time. Not reported, not applicable, unavailable and zero have distinct semantics.
5. **First-seen research.** Preserve when a change first became available here. A current registry version cannot backfill a historical research snapshot before observation.
6. **Domain links.** Company Intelligence owns sponsor-announced/regulatory disclosures. Capital owns financing facts. The existing capital adapter supplies event state and does not establish runway.

### Meaning and proof

Primary completion, study completion, recruitment status, posted results and sponsor-announced readout are different events. The mobile and desktop designs say the registry milestone is not a results announcement. “Not posted in this snapshot” does not claim that no external publication exists.

Prove actual partial-date records, a before/after revision, a suspended/terminated/withdrawn state, missing results, explicit peer IDs and historical exclusion. The previously accepted four-NCT cohort is not evidence for the entire universe. Retain exact NCT/source version through detail, source and Back. All NCT9 IDs and assets in the R10 specimens are fabricated design fixtures.

## 8. Capital Structure

### Journey and holds

The accepted journey is governed by research/capital_structure/e2e_20261013/U0_JOURNEY_FREEZE.md. Lead with the dominant limiting condition and keep Today / On a date / Scenario. Do not restore a giant capacity hero or animated history scrubber. The historical Z0 closure covered W0 and recorded zero evaluable issuers with unresolved W3/W4 and #8673 holds. That is historical source evidence, not a statement of today's runtime. Reconcile current receipts and protect the existing held carrier before implementation.

Reuse issuer_state_contracts, state_bundle, capacity_joint, scenario_composition, scenario_inputs, saved_scenarios and state_changes. The server remains the sole solver.

### Today

Show the established limit or missing input before a number. Registered dollar room, potential common shares, available borrowing, reported cash and net proceeds are distinct quantities. Do not sum route maxima. “No open financing route” is allowed only with complete positive coverage of all relevant routes. With partial coverage, name what remains unexamined or unresolved.

Each route opens its operands, binding constraint, rule and exact permitted evidence span. The RIVT fixture demonstrates an unknown authorization, $80m registered room, 18.4m potential warrant shares and separately dated $36m reported cash. These figures are not additive and do not establish current issuability.

### On a date

The calculation request identity is (issuer_id, mode, cutoff, clock, scenario_id). The URL also preserves focus as navigation state; moving between drilldowns updates focus through replaceState without changing the calculation request or invalidating its response. The default historical clock is system availability at New York end of day, converted to UTC. A later-observed filing cannot appear in the answer merely because the document's nominal filing date is earlier. Later corrections are a separate comparison with their own availability time.

The fixture deliberately places an Oct 28 filing first observed Nov 2 outside the Oct 31 historical snapshot. It shows $10m of registered room from then-known operands, while retaining unknown authorization. “What came later” is clearly excluded from the historical answer.

### Scenario

Assumptions have drafted/dashed treatment and an explicit record anchor. They never change source facts. The fixture's user assumptions are 160m authorized common shares, $4 issue price, $60m gross transaction and 2% fees. Its arithmetic is 15m new shares, $1.2m fees and $58.8m net proceeds. It shows separate registered-dollar utilization and assumed share headroom.

These are explanatory operands, not client-side capacity authority. The result still says feasibility is unresolved because sale conditions were not verified. Unknown values cannot default to zero; assumptions cannot make unsupported routes supported.

### Robust state and proof requirements

Render only a response matching the current complete request identity. Changing issuer or mode must not relabel an earlier result. Preserve conflict, stale, withheld, unsupported, partial, unknown and not-yet-observed separately. Save/restore distinguishes unchanged inputs, changed inputs and unavailable inputs; a restored scenario must not silently recompute against a different anchor.

Prove real issuer coverage, unit integrity, constraints, historical availability, later corrections, scenario isolation, rapid request races, saved restoration and exact evidence. A green frontend test cannot substitute for evaluable real issuer state.


### Authored evidence and saved-version interactions

The constraint inspector opens a selected operand's precise source document, locator and available-at time. The $120m registered amount and $40m utilization produce $80m registered dollar room in the fixture; 95m issued shares and 24m reserved shares remain share quantities. Missing authorization still blocks total issuability. Opening or closing this inspector updates navigation focus only; it must not change the calculation request key.

The saved-version view deliberately presents a newer usage record ($40m → $52m) separately from the unchanged saved anchor. The derived registered room changes from $80m to $68m in the available record. The original scenario retains its saved inputs and output. “Create version 2” proposes a new scenario version with copied assumptions and the explicitly selected new anchor; it must not silently rewrite version 1.

Use the existing saved_scenarios/scenario_inputs owners for persistence, version identity, optimistic concurrency and effect receipts. If a save response is uncertain, reconcile that same scenario/version before retry. For an unavailable operand, retain the saved snapshot and name the missing input; do not fill it with zero or recompute a plausible-looking result. A saved-screen fixture does not prove an account effect.

## 9. Global Cycles — five distinct destinations

### 9.1 Markets

scripts/build_markets.py maps eleven labels: US and Europe have null country-engine mappings; UK, Japan, Hong Kong, Canada, China, India, Taiwan, Korea and Australia map to country records. Its USD-investor path selects usd_record when present and extracts canonical pos_v2 / phase_v2, basis, slope, recent confirmed turns and timing fields.

The new market roster shows current measured positions on a common 0–100 oscillator scale and opens an inspector. US/Europe analyst estimates are a separate section. The builder's summary is not a full oscillator history: do not interpolate a smooth history from one position and several turns. Open the country owner's actual series when a user requests measured history.

Preserve dated valuations, definitions and curated interpretation separately from measurements. A P/E observation is not fresh merely because the cycle series is current. Never create a single cycle-attractiveness league table mixing measured and analyst records.

### 9.2 Countries — material basis correction

The current W3.9 path in templates/sector_cycles.js makes the primary country view local equity: a native local index or synthetic ETF divided by FX. usd_record contains the USD ETF cycle; fx supplies currency context. The older template/builder introductory prose still describing USD is not the current consumer contract.

Local / USD / Both must bind actual distinct records. Label lc_source as native index or ETF / FX and show the relevant currency and ETF identity. The selected country, date range and cursor stay synchronized; the inspector shows each basis separately. Do not call the difference between two oscillator positions a return attribution. Reuse existing owner-provided FX contribution fields only with their definition, leg and evidence.

Preserve countries and regional blocs, price history, relative strength versus its named benchmark, currency cycle, local-versus-USD divergence and peg context where supported. Do not imply that every regional bloc has the same single-country FX decomposition.

### 9.3 U.S. sectors

Keep Sector ETFs, thematic baskets, Nasdaq-100 and Russell-2000 as distinct universes. Switching universe changes the roster, selected identities, denominator and benchmark together. Begin with two or three selected series and use explicit selection limits rather than drawing a tangled overlay.

Preserve independent lazy loading of core measurements, explanatory narrative and heavy histories. A failed narrative request must not remove available price history. Retain existing owner-issued component disagreement and rotation records, with dated detail. The product says “Sector components are moving differently”; implementation terminology belongs in Build.

Cycle position, price and relative strength are distinct chart modes. The mode changes the axis, unit, anchor and benchmark. An indexed price of 125 means 25% above its chosen 100 anchor; it is not a 125/100 oscillator. A chart's selected series must match the roster and legend exactly.

### 9.4 China sectors

Use scripts/build_china_sector_cycles.py, templates/sector_cycles_china.html.j2 and the shared renderer. Preserve 31 Shenwan L1 sectors and curated baskets. The inspected renderer consumes actual osc[] history on 0–100, price[] rebased to the visible-window start, confirmed turns and proj.low/high/central_x.

The proposed chart ends the measured line at the last observation. A separately labeled vertical date band shows the typical turn window. Do not draw a sloping future oscillator or price trajectory; the inspected renderer's plotted projection series is empty. Name both calendar years when a window crosses year-end.

Separate measured position, typical historical rhythm and evidence-gated historical conditional outcomes. An eligible outcome view must reveal setup definition, baseline, sample, interval and horizon. If no eligible cohort exists, show that state rather than a fabricated probability or zero success rate. “Past the typical window” does not mean “reversal imminent.”

### 9.5 Long Cycles

The registry is data/cycle_ontology/proxy_registry.json; scripts/build_cycle.py assembles measured bands and historical Frames, using site/cycle_data.js for curated history seeds.

| Actual representative band | Source meaning | Required treatment |
|---|---|---|
| Credit / intermediate | FRED HY spreads, inverted | Label inversion; higher cycle position is not raw spread widening |
| Gold / intermediate | Continuous gold futures | Preserve futures basis and source identity |
| Gold / secular | Frame | Dated historical turns and leg lengths only |
| Memory / intermediate | MU equity timing proxy; position_gauge=false | Do not call it a DRAM/NAND price measure or show a position gauge |
| Housing / secular | Frame with monitored series | Monitors do not become measured Frame position |
| Shipping / secular | Frame; BDRY monitor | Do not fabricate a measured Baltic Dry oscillator |

FRAME can show turns, up/down leg lengths in years, last turn, elapsed years and a typical calendar window when supplied. It has no oscillator, scalar position, dial or uncertainty cone. The new design uses a flat historical event axis with distinct peak/trough markers and duration spans. Selected turning points receive a visible focus ring and a separate inspector.

Measured Long Cycle bands reuse the underlying producer; this bounded audit did not establish a universal amplitude formula for every band. Do not label them standard deviations, percentage returns or a universal oscillator range without that producer binding. position_gauge=false also applies to some measured proxies.

### Family-wide build and proof

Bind canonical versus legacy position explicitly. Markets reads pos_v2 while older cards may use pos; the chart's actual osc[] endpoint must be reconciled with its chosen latest-value field. A mismatch is an integrity issue to investigate, not a value to silently average.

Comparison lines use pattern as well as color: USD and XLI are dashed, with matching legend samples. China names Electrical Equipment in the series key rather than the Shenwan classification universe. Maintain per-series stale/missing coverage, confirmed versus provisional turns, observation date, frequency, basis, inversion and projection eligibility. Prove cross-page consistency for the same (ticker, basis), exact Local/USD selection, universe switching, bounded compare selection, shared cursor, source detail, mobile behavior and return state. Keep all forecasting/strategy claims outside this design unless separately validated.

## 10. Research / Intelligence Hub

### Existing owner

Browse all research maps to intelligence_hub.html, not research_screener.html. Reuse engine/intel_hub.py, build_intel_hub, the incumbent template and site/intel_hub/hub.json. The new structure is Discover / Following / All desks / Evidence history, with named Models & cohorts and calendar destinations.

### Discovery and directory

Discover is an investigation queue. “Recently observed” sorts by defensible first observation, not event date or page-build time. Each item retains originating desk, canonical record identity, original evidence class, relevant status and a direct action into the source desk. Cross-desk echoes are linked, not counted as independent confirmation.

The first Government Revenue item is first observed on 14 Nov even though the award was recorded on 13 Nov. This deliberate distinction must survive the native adapter. The calendar shows scheduled or estimated milestone precision and never converts completion into readout.

All desks provides eleven source destinations: five company/event desks and six macro/cycle desks. The Research Hub itself is the twelfth destination in the original screenshot. Scoped directory search filters desk names and purposes; global entity search remains the shell owner's function.

### Existing advanced research remains available

Models & cohorts retains existing model outputs, cohort membership and owner-issued ordering. Evidence history retains family, horizon, benchmark, eligible denominator and evaluation status. Source disagreement exposes the dated paths rather than averaging conflicting values into a new “truth.” Policy is contextual and does not acquire voting/ranking authority through cross-desk presentation.

Preserve catalyst chronology, sector context, research risk/coverage, source history and originating desk actions. Where an outcome cohort is empty, not started, incomplete or ineligible, show the actual state. Pending, missing, corrected and losing outcomes are not interchangeable exclusions.

Following and saved views use canonical user owners where supported. Legacy device-local behavior must retain its scope. No new watchlist, notification scheduler or account database should be created for this migration. Confirmed persistence, reload and account/device boundaries require actual proof.

### Authored Following, History and locale states

Following visibly selects MU while preserving the canonical company/desk list and an evidence-type filter. Evidence History separates source activity from a Government Revenue evaluation that has not started; it does not render zero outcomes as a 0% success rate. The Chinese dark directory uses verified available Noto Sans SC and translated shared-shell navigation. It is a single authored locale/theme specimen, not whole-product localization proof.

## 11. Feature disposition and build sequencing

### Common disposition rules

- RETAIN: a useful existing capability with a source owner and coherent journey.
- IMPROVE: source meaning stays intact while its interaction, contract or clarity is strengthened.
- RELOCATE: the capability receives a named, reachable destination; hiding it behind an unstructured “More” bucket is insufficient.
- REMOVE: only a redundant presentation, misleading label or obsolete duplicate. Do not remove the underlying intelligence because it is hard to display.
- BLOCKED_DATA: useful capability whose producer, coverage, entitlement or validation is insufficient. State the gap and next proof; do not populate it with invented confidence.

### Ordered implementation graph

| Stage | Concrete work | Exit evidence |
|---|---|---|
| D1 Design closure | Finish destination-specific deep views, state flows, theme/locale and responsive composition | Reviewed native Paper pages and explicit feature/state coverage |
| C1 Route/contract admission | Reconcile current writers/holds; bind twelve native destinations to existing shell, auth and source owners | Exact route/owner map, typed read contracts and compatibility examples |
| C2 Read-only vertical slice | Implement one coherent producer → authenticated native consumer → source → Back journey | Real data identity, dates, access and browser proof |
| C3 Domain hardening | Correct source identity, chronology, lineage, basis and coverage gaps in their existing owners | Targeted real reproductions and regression evidence |
| C4 Canonical persistence | Implement only supported saves/following/scenarios through existing owners | Confirmed effect, reload/restore and failure behavior |
| C5 Responsive and accessibility | Keyboard/touch, focus, locale/theme, matrices and charts | Actual narrow/desktop browser journeys without clipping or lost state |
| C6 Protected release | Owned diff, affected tests, binding CI, permitted release path | Deployed bytes plus real consumer acceptance, not CI alone |

Stages are dependencies, not invented approval ceremonies. Routine authorized edits and repair can proceed inside the assignment once the Chairman's design-before-implementation sequence is met. Existing security/CODEOWNERS/release holds still bind. A pending PR or CI blocks only its release lane; continue useful disjoint work.

### Meaningful verification

Test real invariants, not copies of the implementation: cross-deal isolation, first-observed historical exclusion, duplicate-source dependence, partial-date bounds, unit/basis mismatches, request races and persistence scope. Use actual source records for acceptance. Synthetic fixtures support reproducible layout and state checks only.

For each route retain evidence of:
1. Exact input identity and source record/version.
2. Actual action and response identity.
3. Correct rendered state and units.
4. Source drill, focus and browser return.
5. Supported persistence effect and reload, if any.
6. Deployed implementation and authenticated browser path.

## 12. Remaining design work and completion falsifier

This is an engineering blueprint for the current candidate set, not a declaration that the design phase or migration is complete. The [native Paper inventory](PAPER_DESIGN_INDEX_2026-11-14.md) identifies the exact authored pages. The current set contains 50 native pages: 40 product/viewport/theme/locale views, eight Build boards and two state sheets. All twelve destinations have a new primary composition. There are eight mobile family treatments, two English dark views and a Chinese dark directory. These examples do not establish systematic theme, language or breakpoint parity.

Pipeline, Market Memory, research calls, transmission and company exposure are now authored in Policy R6; Following and Evidence History are authored in Research R5. Capital includes exact operand/source inspection and changed-source scenario restoration. Before implementation, close the remaining domain-specific advanced destinations, full interaction/state transitions, Models & cohorts/disagreement, route-specific keyboard/return behavior, and systematic EN/ZH, dark/light and intermediate-width composition. The next bounded design unit is BioCatalyst Trial screen and First-seen, preserving explicit NCT selection and observation-time semantics. Government Programs/recompete, Alternative Data relationships and Special Situations advanced event branches follow through the existing owner contracts. Do not duplicate accepted screens without a concrete reason.

A screen may be clean while an engine is incomplete. A correct typed adapter may exist while real coverage is insufficient. A PR can be ready while release remains held. Completion requires truthful source inputs, useful intelligence, coherent interaction, supported saved effects, actual production/browser proof and the original acceptance—not a frame count, green CI or this document.

## 13. Source references

All paths below were used at the pinned repository generation unless explicitly described as future work.

- [Master shared-shell migration](https://github.com/mastermindx-market-intelligence/macro/blob/e856ef0200a0c508c78ef9a6666116020e4835d1/research/MASTER_PRODUCT_SHELL_MAKEOVER_MIGRATION_2026-10-08.md)
- [Design doctrine](https://github.com/mastermindx-market-intelligence/macro/blob/e856ef0200a0c508c78ef9a6666116020e4835d1/docs/DESIGN_DOCTRINE.md)
- [Product design system](https://github.com/mastermindx-market-intelligence/macro/blob/e856ef0200a0c508c78ef9a6666116020e4835d1/research/MASTER_PRODUCT_DESIGN_SYSTEM_V1.md)
- [Government Revenue masterplan](https://github.com/mastermindx-market-intelligence/macro/blob/e856ef0200a0c508c78ef9a6666116020e4835d1/research/GOVERNMENT_REVENUE_FORESIGHT_MASTERPLAN_FOR_FABLE.md)
- [Special Situations roadmap](https://github.com/mastermindx-market-intelligence/macro/blob/e856ef0200a0c508c78ef9a6666116020e4835d1/research/SPECIAL_SITUATIONS_ROADMAP_V2.md)
- [BioCatalyst API](https://github.com/mastermindx-market-intelligence/macro/blob/e856ef0200a0c508c78ef9a6666116020e4835d1/app/biocatalyst.py)
- [Capital journey freeze](https://github.com/mastermindx-market-intelligence/macro/blob/e856ef0200a0c508c78ef9a6666116020e4835d1/research/capital_structure/e2e_20261013/U0_JOURNEY_FREEZE.md)
- [Markets builder and exact mappings](https://github.com/mastermindx-market-intelligence/macro/blob/e856ef0200a0c508c78ef9a6666116020e4835d1/scripts/build_markets.py)
- [Shared cycle consumer and Local/USD path](https://github.com/mastermindx-market-intelligence/macro/blob/e856ef0200a0c508c78ef9a6666116020e4835d1/templates/sector_cycles.js)
- [China cycles builder](https://github.com/mastermindx-market-intelligence/macro/blob/e856ef0200a0c508c78ef9a6666116020e4835d1/scripts/build_china_sector_cycles.py)
- [Long-cycle builder](https://github.com/mastermindx-market-intelligence/macro/blob/e856ef0200a0c508c78ef9a6666116020e4835d1/scripts/build_cycle.py)
- [Cycle proxy registry](https://github.com/mastermindx-market-intelligence/macro/blob/e856ef0200a0c508c78ef9a6666116020e4835d1/data/cycle_ontology/proxy_registry.json)
- [Curated cycle history seeds](https://github.com/mastermindx-market-intelligence/macro/blob/e856ef0200a0c508c78ef9a6666116020e4835d1/site/cycle_data.js)
- [Intelligence Hub engine](https://github.com/mastermindx-market-intelligence/macro/blob/e856ef0200a0c508c78ef9a6666116020e4835d1/engine/intel_hub.py)


## 14. C7 advanced-workflow additions

C7 adds seven BioCatalyst R11 pages and five Government Revenue R14 pages; the set now has 62 native pages. These extend the design candidate only. The [index](PAPER_DESIGN_INDEX_2026-11-14.md) and [inventory](PAPER_INVENTORY_2026-11-14.json) hold exact roots and reviewed screenshots. [BioCatalyst R11](BIOCATALYST_R11_BUILD_SPEC_2026-11-14.md) supplies the detailed contract.

### BioCatalyst: literal screening and prospective observation

Trial screen uses eight literal AND filters, fixed completion-interval/NCT ordering and explicit peer selection. Its date rule is full source-interval containment: March 15–31 excludes a source value of March 2027. Unknown dates are excluded by an active bound. Phase facets are non-additive, ignore their own dimension and cannot be summed into the result count.

First-seen uses the server's UTC observation window and current-record filters. “Primary completion” selects the exact change kind; there is no unimplemented completion-kind union. A matching event retains all its changes and total/displayed/omitted counts. The upper and lower observation bounds are visible; neither is promoted to effective time or clinical outcome.

**Required engine/consumer upgrade:** per-NCT prospective coverage is internal only. The current public prospective endpoint returns aggregate coverage; trial detail does not expose the per-NCT object. Add a bounded projection from the same committed bundle, retaining exact NCT identity, accrual state and available observation/baseline clocks. Never infer coverage from event rows or substring-search fanout. Rows/facets also need a tested coherent-cut contract; matching response clocks alone are insufficient proof.

The new states preserve filters and selected IDs through generation changes, separate baseline-only from valid emptiness, and distinguish unavailable projection from account access. The 768px date control uses the canonical 72px rail; 390px selected-event reading has explicit return and source actions. Real focus, navigation and source interaction proof remains owed.

Source: [Bio API](https://github.com/mastermindx-market-intelligence/macro/blob/e856ef0200a0c508c78ef9a6666116020e4835d1/app/biocatalyst.py), functions trial_screen, trial_screen_facets, trial_prospective_changes, _prospective_model_events and trial_detail; [screen engine](https://github.com/mastermindx-market-intelligence/macro/blob/e856ef0200a0c508c78ef9a6666116020e4835d1/engine/biocatalyst/trial_screen.py), _matches/_row_order/_facet_for_dimension.

### Government Revenue: programs, dates and exact relationships

**Programs.** Use budget-programs, program/{program_key} and budget-line/{line_key}. Preserve content_id, receipt, native identifier, line_family_key, fiscal year, document_stage, units, provenance and all relevant source clocks. The specimen compares FY2026 request280 to FY2027 request312: +32 and +11.4%. Its separately shown enacted265 is not the comparison denominator. Implementation must retain source versions and compare only compatible line families/units/stages; no source snapshot may be guessed from a current API response.

Source inspection must resolve the exact document/page/line and conversion (312,000 USD thousands →312m). Program links retain edge_id, edge_type, review_state, effective/known clocks and evidence. Null economic_weight displays allocation not established. A documented company link does not assign a program amount to a ticker. Unsupported or uncovered programs remain explicit, and a newer request does not replace older enactment evidence.

**Calendar.** Current /recompetes returns deterministic period-of-performance end watches. It is not an official recompete or solicitation forecast. The design labels these **Expiry watch**, separately from **Response due** and **Performance ends**. Current and potential end dates remain separate, including unexercised-option meaning. No linked follow-on notice means none in the shown coverage, not that none exists. Preserve undated and withdrawn items for inspection outside dated sorting.

Reuse the prebuilt events ledger and its critical-date ordering. Filters, selected event and date basis must survive source navigation. Construct a typed, coherent agenda from the committed cut, with source date kind and precision; retain versioned deadline corrections before presenting a before/after view. Bound cursors cannot mix cuts. Save view continues the existing device-local/check-on-open contract; it does not enroll a backend watcher.

**Company and award connections.** Exact source-generated award/order and IDV parent IDs bind the source-native vehicle relationship, with direct/grandchild depth and selection provenance. This establishes no seat, utilization, vehicle-value allocation or issuer revenue. Award amounts stay on their original records. The /dossier/company route gives collection-scope metadata, not issuer attribution. Use the existing dated entity/issuer evidence owner for actual recipient mapping, with joint ventures and unresolved entities preserved.

The relationship inspector keeps effective date unknown when the source does not supply it. Unavailable subaward coverage degrades that section while a valid award/vehicle path remains usable. Historical identity selection requires retained time-bound evidence before exposing a cutoff control.

**Implementation proof.** Exercise compatible versus incompatible budget comparisons, null allocations, uncovered programs, ambiguous entities, missing/partial IDV publication, exact parent bridging, unavailable subawards, changed deadlines and undated items. Prove authenticated source → API → shared-shell consumer → exact original evidence → Back, including mobile and supported saved-state restoration. Account/entitlement, canonical company state and publication remain their current owners.

Source: [Government API](https://github.com/mastermindx-market-intelligence/macro/blob/e856ef0200a0c508c78ef9a6666116020e4835d1/app/government_revenue.py), _public_budget_line/_program/_edge, budget_programs/budget_program, dossier_company, award_idv_relationships, recompetes and events. The [Government masterplan](https://github.com/mastermindx-market-intelligence/macro/blob/e856ef0200a0c508c78ef9a6666116020e4835d1/research/GOVERNMENT_REVENUE_FORESIGHT_MASTERPLAN_FOR_FABLE.md) remains ambition, while the current implementation controls the supplied date/evidence meaning.

### Preserved next work

Next is Alternative Data relationship, provider and maturity-state design. Preliminary source review identifies approximate channel grouping instead of event identity, empty/error conflation and seed-derived control edges that cannot be promoted to verified ownership. These findings require a concrete source-grounded design and upgrade contract in D1-ALT. Remaining Special Situations, Policy, Hub, Capital and systematic cross-product states remain scoped; C7 does not close the design phase.

## 15. C8 — Alternative Data R2

Six additional Paper views bring the native set to 68. The detailed [R2 contract](ALTERNATIVE_DATA_R2_BUILD_SPEC_2026-11-14.md) specifies relationship evidence, source-state receipts, exact cohort identity, progressive disclosure and consumer proof.

- Record counts and primary-origin counts remain distinct. Unknown lineage never becomes independent confirmation.
- Existing feed defaults collapse missing/empty/error states. Add typed receipts to the incumbent collector/producer before presenting valid-empty, delay, provider access or unknown coverage.
- Seed CONTROLS labels/confidence do not establish documentary control. Unsupported associations stay unresolved; officer status and effective date are separate facts.
- Consume Article 3 dynamically for its exact family/horizon/vintage. Its independent n_dates sample floor is one requirement; neither a historical HOLD nor a five-day verdict transfers to another selection. Evidence and evaluation clocks remain separate.
- The Sources inspector follows the selected row. Advanced definitions are behind Coverage scope; technical details remain collapsed. Other horizons are explicit navigation without a conflicting verdict in the active scope.

All six compositions were visually inspected. Three reviewer findings (horizon mixing, ambiguous sample wording, unselected source details) were corrected and affected final screenshots reinspected. This establishes design refinement, not runtime readiness. Next: D1-HUB models/cohorts, evaluation and disagreement using the incumbent ledger and evaluator owners.

## 16. C9 — Research Hub R6

Eight new views bring the native set to 76. The [R6 contract](RESEARCH_HUB_R6_BUILD_SPEC_2026-11-14.md) binds cohorts, source snapshots, owner rank, evaluation denominator and source return. Thirteen mobile specimens and three intermediate-width specimens are now present across the family; systematic parity remains open.

Preserve the existing Hub score/rank and section stamps. Missing historical stamps mean unknown membership. Early MU may remain Command rank 2 while its recorded gate excludes it from Emerging. A source-capped score is labeled explicitly; it is not a probability.

Legacy evaluation uses calendar-day offsets; the unified grader uses trading bars. The current adapter drops cohort/source/rank, and public hub.json strips track_rows. Cohort/date/version-filtered daily/HAC results and immutable intraday snapshots therefore need additive projections from the incumbent ledger. Existing pooled engine-version summaries cannot stand in for filtered daily statistics.

Rows considered is the age-prefilter denominator, including some immature windows. Show covered, price-missing, immature and benchmark-missing counts. Preserve each metric's daily sample and velocity history sample. Ten usable pairs per date are required for daily IC: the Top 5 mobile state correctly displays no daily statistic despite accumulated graded rows. Error/accrual conflation and historical price-cutoff proof remain engine gaps.

The four desk directions remain separate. Alt neutral is explicitly a neutral score range; absent sources remain unavailable. Policy stays outside the four-reading tally and remains accessible through a mobile disclosure. A Policy fallback/tie-break concern is recorded for a focused owner invariance test, not claimed repaired.

Visual/source review corrected score units, neutral-versus-absent wording, missing mobile Policy access, shell-height parity and redundant lower-panel copy. All eight final compositions were inspected and owned roots finished through the guarded M1 adapter. Next: D1-SPECIAL activist, international and amended-consideration workflows.


## 17. C10 — Special Situations R2 identity, sources and consideration

The [R2 detailed contract](SPECIAL_SITUATIONS_R2_BUILD_SPEC_2026-11-14.md) binds seven additional native pages to incumbent owners. The cumulative inventory is 83: 65 product/responsive/theme/locale views, thirteen Build boards and five state sheets; fourteen mobile and three intermediate compositions. Source baseline and design-first acceptance remain unchanged.

Add exact campaign/transaction identity to current CIK/category and ticker/category projections. One issuer may have two agreements; one termination must not close the other. An ownership-only 13D/A amendment must not become campaign escalation. Preserve reporting-person identity, joint holdings, holding date, filing/observation clocks and objective evidence. The current activist record counts filing rows and absolute 60-trading-row target returns; it is not independent campaign success or benchmark alpha.

International discovery remains within the incumbent UK/Canada lanes. Preserve original publisher/type, URL, publication and observation clocks, entity-resolution provenance and typed coverage receipts. Possible offer, firm intention, satisfied condition and completion require distinct evidence; listing market does not prove cross-border parties. No collection or market-enable change occurred.

Retain original and amended agreement terms at their source cuts. Outside date, company guidance, vote and actual completion remain different date types. USD22 + 0.5 acquirer shares at USD40 yields USD42 per target share; against USD39 the gross spread is 7.69%. Ratio, security, quote units and times are explicit. Unknown pence/pounds, elections, collars, proration and month-only closing guidance must withhold unsupported values or annualization. Fee payer, recipient and trigger remain source-bound; an USD85m fixture fee is not necessarily owed or per-share consideration.

Implement through existing special_situations, activist, special_arb, international collector/classifier, premium and build owners. Preserve premium typed refusals, distinguish its pre-announcement price basis from the 30-row proxy, preserve thin-store protection and replace paid HTML fragments with an authenticated typed consumer projection. Static source risks require focused real-path proof; none was claimed reproduced in production.

The principal and bounded read-only reviewers inspected final compositions and checked fixture meaning/arithmetic. All seven roots received observed guarded finish receipts. Draft documentation and Paper design do not establish runtime interactions, entitlement proof, source coverage or production readiness. Continue D1-POLICY and the remaining family/cross-product design states before product implementation.


## 18. C11 — Policy R7 regional sources, roles and dated evidence

The [R7 detailed contract](POLICY_WATCH_R7_BUILD_SPEC_2026-11-14.md) binds nine additional native pages. Cumulative inventory: 92 pages, comprising 72 product/responsive/theme/locale views, fourteen Build and six state sheets; sixteen mobile and four intermediate compositions. New parity specimens include 1024px source coverage, English mobile People and Chinese dark mobile Treasury.

World uses Region = Europe and an explicit publication-date filter. UK, EU and central-bank documents stay separate, with source-specific clocks and lifecycle evidence. The Treasury document remains readable without analysis. Current known_at_iso is assigned at evaluation, so the UI says Recorded; it does not assert immutable first observation. Missing prior bytes mean comparison unavailable.

The selected fictional person authored a paper before an effective adviser appointment and is a former adviser at the selected date. Announcement and effective start are distinct; a separate membership has an unverified end. Each role/relationship needs its own source-bound interval and identity. Shortest paths, seed-generated control labels, co-firing and graph confidence cannot establish authority, adoption or documentary relationships.

The dated brief preserves three original source dependencies and its July analysis while a November source revision remains separate. Fresh rendering or model evaluation cannot refresh the dated intel substrate. Preserve Fed profiles/task forces, administration/theaters, rotation, monitors and calls through named Research destinations; do not restore fixed template claims or Moves in force fallbacks when lifecycle coverage is missing.

Keep the incumbent current/lifecycle, UK, regional/qbus, influence and publication owners. event_id, item_id and event_key remain distinct; RSS-description hashes are not full-document hashes. Source eligibility and fetch outcomes require separate consumer meanings. Not collected is not a transient outage or evidence that no related event exists. Render from published artifacts without triggering collection/model work or graph writes.

All nine final compositions were reviewed and received observed guarded finish receipts. The final Chinese mobile root is 5J4-1 after a qualified owned-root font repair; the inventory points to its final screenshot. No held/foreign pages were repurposed. Design-state coverage, systematic parity and runtime acceptance remain open. Continue Capital conflict/restore design next.
