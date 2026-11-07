# Catalyst-to-Opportunity Intelligence
## CEO research synthesis, architecture and execution masterplan

Version 1.0 | Research cutoff: 17 October 2026 | Status: research/design package, not deployed capability or predictive validation

**Commission.** Chris commissioned the extensive research, architectural decisions and complete implementation plan in this CEO session, before commissioning Fable to orchestrate the build with suborchestrators. This package completes the planning deliverable; it does not dispatch Fable, authorize a purchase, activate a source, deploy production, or place a trade. The selected chat reasoning mode was not independently observable; no mode-switch receipt is claimed.

**Program relationship.** This is an implementation-oriented extension of the existing Catalyst Intelligence program in Mastermind PR #1181, not a replacement intelligence platform or a second program control plane. It connects that program with the existing News-to-Business-Impact, Theme/Group Reads, Company Intelligence, Defense/GovRev, Entry Radar, Prophet, Terminal, and evaluation owners. Existing sector obligations survive. [I01]

### Package map

- `01_MASTERPLAN.md`: executive decisions, scope, current estate and architecture.
- `02_INTELLIGENCE_METHODS.md`: event reasoning, market discovery, economic transmission, timing and all specialist domains.
- `03_DATA_PRODUCT_OPERATIONS.md`: exact interface boundaries, source rights, clocks, UX, reliability, security and cost.
- `04_SCIENCE_ACCEPTANCE.md`: falsifiable hypotheses, historical/forward evaluation, adversarial acceptance catalog and release criteria.
- `05_FABLE_EXECUTION.md`: dependency-ordered work packages, orchestration, ownership, integration and ready-to-deliver commission.
- `06_EVIDENCE_REGISTER.md`: immutable internal sources, primary research, source limitations and correction ledger.

The design choices below are proposals adopted for this research specification. They are not retrospective statements about what Mastermind already does. Source and runtime facts are explicitly labeled. The evidence register explains every bracketed source ID.

## 1. The outcome we are building

Mastermind should notice a consequential opportunity outside the user's current attention, explain why the relevant companies may benefit or suffer, identify whether price behavior is beginning to confirm the thesis, and present a realistic decision window before the setup is already exhausted.

The primary user is an active discretionary investor who can analyze several ideas deeply but cannot continuously monitor every sector. The machine job is not merely collecting more headlines. It is continuous coverage, change detection, economical investigation, disconfirmation, security routing, timely delivery and learning.

The target question is:

> Across the markets actually covered, what important change am I overlooking, which securities are exposed through a defensible mechanism, what is the market doing about it, and is a qualified entry or risk-review window forming now?

Three outcomes must remain distinct:

1. **Attention advantage:** the user learns about a relevant development sooner or with less monitoring effort than a simpler scanner would permit.
2. **Decision advantage:** the explanation, selection and timing improve decisions relative to explicit alternatives.
3. **Trading advantage:** an executable, cost-adjusted policy has demonstrated incremental value on unseen and prospective observations.

A release can honestly achieve the first without the third. It must not advertise a profitable predictive system merely because the interface works. Conversely, withholding all useful factual discovery until every forecast is qualified would unnecessarily delay value and prospective observation.

### North Star acceptance

A complete bounded release must demonstrate an ordinary source-to-user-to-outcome path: a real source observation or market anomaly; preserved source and identity versions; a derived assessment; correct nomination into existing timing machinery; an authenticated, understandable user alert; a frozen issued record; and an independently observed later outcome. The declared coverage, permitted claims and failures must be visible.

The October defense/oil episode is a motivating development case, not a prequalified winner. We have not reconstructed its complete historical news-arrival tape, intraday executable prices or original Mastermind outputs. Earlier conversation percentages, carrier-position claims and claims about a planned attack are not accepted evidence in this package. No claim is made that an exact profitable entry was available. This quarantine is a scientific correction, not a rejection of the opportunity thesis.

## 2. The central architectural decision: two discovery paths

**Event-first:** a material new fact, allegation or revision changes a scenario or economic channel. Relevant themes and securities enter surveillance before meaningful price confirmation.

**Market-first:** a theme or security develops unusual relative strength, participation, volume or structure. It enters surveillance even when the explanation is not yet known. The analyst investigates competing causes rather than inventing a geopolitical story.

These paths join only after retaining their separate evidence and provenance. Neither path is a prerequisite for the other. Requiring news, broad participation, several technical indicators and a full financial model before noticing anything would recreate the late-entry problem.

The subsequent stages are **watch**, **investigate**, **setup observed**, and **qualified decision review**, with separate **stale**, **disputed**, **extended**, **invalidated** and **resolved** dimensions. These are proposed presentation labels mapped onto incumbent owner records, not a new organizational lifecycle or trade authorization ladder.

A high event-risk assessment can coexist with a poor trade setup. A good price setup can exist without an identifiable news catalyst. An expected event can occur with no positive stock response. A geopolitical risk premium can rise and fall without war occurring. The product must make all four cases intelligible.

## 3. What the current estate actually supports

Source inspection used protected Mastermind `a552a5e506ae808efa575c2e13cb56f478c72b87`, Macro `1aeaf6874e4d3ed8d4f76205c236994ec7a3bcb9`, and Terminal `a0b8c735062cb6ff8ebe13f9e3aef19e845450b8`. These are repository observations, not deployment attestations. The Catalyst paper remains at `2e23f73d8cd85fb082be567602fd743bbb3be213`. [I01, I02]

| Capability | Verified evidence and limitation | Consequence for this program |
|---|---|---|
| Defense investor product | Macro #9066 merged on 15 October; substantive financial, program, source and interface work exists. Its current handoff still separates installed-byte evidence from real entitled investor acceptance. [I03, I04] | Reuse and close actual proof gaps; do not rebuild procurement or overwrite the incumbent follow-ups. |
| Low-latency ticker news | The operator runbook describes Macro #8454 / Terminal #831, a single qbus writer and explicit source/retention/display rights. It is documented dark by default; live activation was not inspected here. [I05] | Treat runtime availability as unverified, not as either absent code or guaranteed live coverage. |
| News revisions | `qbus.news_revision.v1` preserves source, transport, receipt and revision clocks. Its transport enum has five admitted routes, not a generic GDELT/official-source route. [I06] | Extend through the owner or consume existing legacy outputs honestly; never spoof a provider identity. |
| Company event identity | Current `company_event.v1` is issuer/fiscal-period/event-type keyed. [I07] | A global incident cannot be assigned an invented company or earnings quarter. |
| Theme intelligence | Theme Scoring, Group Reads, Sector Pulse and Theme Tape provide useful owned outputs. Their source contracts distinguish descriptive reads from validated return forecasts. [I08, I09] | Consume existing calculations, then implement a specifically tested discovery policy through the relevant owner. |
| Theme alert latency | Constructive confirmation advances at most once per session date, with `N_STREAK=2`. Same-day rebuilds do not satisfy persistence. [I10] | Add an early research-attention channel within the alert owner; preserve existing confirmed and risk channels. |
| News-to-business-impact research | The retained W2 record has 157 of 600 planned cases, incomplete adjudication and an unaudited agreed-absence stratum. [I11] | Reuse accepted labels and repair the specific benchmark gaps; model agreement is not independent truth. |
| Entry Radar | The frozen nomination contract has thirteen fields, an explicit membership-expansion boundary and no ranking/sizing authority. [I12] | Route surveillance into the existing bus without smuggling a trade score into coverage records. |
| Common Catalyst Terminal projection | #811 remains draft and explicitly excludes the authenticated BFF/product seam. [I13] | Adopt useful projection semantics, then build and prove the real product connection. |
| Economic graph | The Theme Graph disposition map assigns company exposure, group-flow, alerts and evaluation to existing owners; some older helpers are documented dormant. [I09] | Verify callers before reuse. An importable helper is not a live dependency. |

The integrated early-opportunity capability is **PARTIAL**, not PROVEN_LIVE. Individual source files may be BUILT_NOT_PROVEN for this new consumer. The review did not establish that every required field is currently available, licensed, timely or empirically useful.

### Material corrections to the previous outline

First, two-session confirmation is a specific timing constraint, not merely an occasional delay. Second, the current Defense implementation is more advanced than its older parent comment suggests. Third, ticker-news ingestion, model processing and SaaS redistribution have separate permissions. Fourth, the Radar and qbus interfaces are closed contracts, not generic sockets into which arbitrary new objects can be placed. Fifth, the existing CompanyEvent identity cannot represent global conflict directly. Sixth, retrospective LLM analysis remains vulnerable to future knowledge even with timestamp-filtered retrieval. These corrections change the work packages, not the user's objective. [I03-I07, I10, I12, X12]

## 4. Research conclusions that change the design

### 4.1 An open data foundation is plausible, but not a free institutional wire

GDELT publishes event, mentions and knowledge-graph updates on a fifteen-minute cadence. That can support broad discovery and inexpensive historical observation. It does not establish that every underlying article is licensed for retention, model processing or customer display, nor that a fifteen-minute dataset wins a sub-second news race. The public update manifest was readable in this research session; operational ingestion and historical completeness remain separate tests. [X01, X02]

Official incident notices, issuer releases, SEC filings and energy statistics add complementary evidence. Their own clocks and coverage differ. A slow but reliable outcome dataset belongs in evaluation; a fast, fallible report belongs in discovery. UCDP's candidate releases are monthly rather than an intraday alert feed. ACLED has contractual use restrictions that must be checked for the proposed product. [X03-X07]

### 4.2 Geopolitical risk measurement is not the same as event forecasting

The AI-GPR research demonstrates a structured way to distinguish threatening language, realized acts and oil-related risk in news. The inspected public index page was updated through September 30, not proven live for October 16. It is a benchmark and methodological input, not an operational weekend-warning dependency. Its normalized index is not a probability of an attack. [X08, X09]

The geopolitical module therefore starts with explicit, source-backed scenario changes and simple calibrated baselines. Numerical forecasts require a defined event, risk set, horizon, independent outcome policy and prospective evidence. A persuasive geopolitical paragraph is not a calibrated forecast.

### 4.3 Economics is the bridge from events to securities

A company being mentioned in a defense theme does not prove incremental orders, revenue, margin or shareholder value. A shipping disruption may affect crude supply, freight, insurance and operating costs differently. Customer-supplier research supplies a reason to investigate delayed transmission across actual economic links, but does not validate this particular strategy. [X10]

The graph must retain sign, lag, attributable role, baseline, capacity constraint, uncertainty and falsifier. Numerical economic weights remain unavailable where the upstream evidence cannot support them. Scenario arithmetic and observed market co-movement must not be confused.

### 4.4 Sophisticated reasoning must beat simpler detectors

LLM forecasting research supports testing retrieval and structured reasoning, not assuming an ensemble is superior to a crowd or to price-based baselines in every setting. Financial LLM research also identifies contamination from model weights and modern retrieval. The program will compare simple scanners, structured extraction and deeper reasoning under matched information and cost conditions. [X11, X12]

For rare events, precision, recall, calibration and false-alert burden matter more than headline accuracy. A detector that predicts no conflict almost always can be accurate and useless. A detector that alerts constantly may catch every rally and still be a poor product. [X13]

### 4.5 Existing commercial products establish a feature baseline, not a shortcut to our moat

LSEG advertises structured news analytics including relevance, novelty, sentiment and event metadata. Those are capabilities to benchmark against, not proof of trading performance. Workspace news explicitly disallows redistribution and server-side use under that desktop service. Dataminr's public financial-services material emphasizes early risk awareness; it does not establish qualified equity entry timing. [X14-X16]

Our differentiation hypothesis is the closed investor workflow: event or market discovery, attributable exposure, contrary evidence, causal timing, user attention and measurable follow-through. Buy source coverage only where measured incremental value and an appropriate contract justify it; retain our original implementation and do not copy proprietary models, taxonomies or assets.

## 5. Logical capability architecture

These are responsibilities, not fourteen new microservices.

| ID | Responsibility | Incumbent integration home |
|---|---|---|
| C01 | Coverage universe, identities and market calendars | Data OS, breadth/PIT membership and market-data owners |
| C02 | Source intake, rights, revisions and health | Existing collectors, qbus/news-vector and their runtime |
| C03 | Claim extraction, incident clustering and source independence | qbus/news-to-business-impact, with owner-approved incident projections |
| C04 | Geopolitical scenario and hazard assessment | Specialist Catalyst read composition over admitted evidence |
| C05 | Domain catalyst semantics and company economics | Existing Bio, GovRev, MedTech, semiconductor, energy and resources owners |
| C06 | Exposure and transmission graph | Company Theme Exposure, Theme Graph, Company Intelligence and FIF |
| C07 | Market/theme discovery | Group Reads, Theme Scoring, Sector Pulse and their approved extension seams |
| C08 | Cross-asset context | Commodity, macro and market-data owners |
| C09 | Expectations, options and extension context | Existing expectation/Options/valuation owners |
| C10 | Security timing and entry assessment | Entry Radar and actual entry/decision owners |
| C11 | Opportunity composition and attention policy | Derived Catalyst/Terminal read model; no trade allocation authority |
| C12 | User delivery, research continuity and revisions | Terminal, existing notification preferences and thesis/watchlist owners |
| C13 | Evaluation and learning | Existing Eval OS, TrialLedger, qledger and specialist stores |
| C14 | Runtime, security, cost and operating acceptance | Existing deployment, service, rights and observability owners |

### Data flow

```text
Existing source owners ------------------- Existing market-data owners
        |                                          |
Source revisions / claims                 Closed-bar / group observations
        |                                          |
Event-first WATCH                         Market-first WATCH
        |                                          |
        +-------- Derived opportunity case --------+
                           |
            Native economic-exposure witnesses
                           |
             Existing Radar nomination contract
                           |
             Existing timing / decision consumer
                           |
         Authenticated Terminal + existing alerts
                           |
         Frozen issued record + independent outcome
```

Every arrow requires an explicit, versioned interface and an acceptance test. It is not satisfied by two files existing in the same repository. The product composer references owner-native IDs and generations; it does not become their canonical writer.

## 6. Key decisions fixed for the build

**D01 - Discovery is an OR condition.** Material event change or qualifying market anomaly can create a watch. A fused trade endorsement requires its separate qualified path.

**D02 - Whole declared universe, not only user watchlists.** Personal interests affect delivery ordering and budgets, not whether covered defense or energy is observed. Coverage must be visible and measured.

**D03 - No universal Catalyst Score.** Expose evidence quality, scenario change, economic relevance, market confirmation, timing and uncertainty separately. A research-priority ordering has no right to reorder Prophet or size positions.

**D04 - Extend owners, not platforms.** No new authoritative event database, security master, provider router, scheduler, publication authority, forecast registry or organizational queue.

**D05 - Separate incident and company identities.** qbus-owned incident references compose with actual company events. Do not mint fake fiscal identities or assume a theme member is an event participant.

**D06 - Earliest knowable time is dependency-bound.** All raw facts, identity mappings, model versions and feature windows must be eligible before an assessment is issued. Later corrections do not rewrite the original historical view.

**D07 - Preserve source-lineage dependence.** Ten syndicated articles are not ten witnesses. Five correlated stocks are not five independent geopolitical experiments. Price and news may share a common cause.

**D08 - Qualified timing uses causal observations.** No centered indicators, hindsight pivot labels, future universe membership, reconstructed first-seen clocks or same-bar impossible fills.

**D09 - Early attention is not a weakened trade gate.** Preserve the current two-session confirmed-theme behavior. Add a separate, explicitly provisional discovery event through the same alert owner.

**D10 - Start prospective observation before complex models.** Use existing admitted stores. Do not wait for all domains, a giant common-schema rewrite or a high-capacity language model.

**D11 - Free-first does not mean rights-blind.** Field-level use rights and vendor limitations are part of the design. Retail access does not imply SaaS redistribution or model-processing rights.

**D12 - Fable owns delivery, not a second scientific charter.** The later commission supplies goals, methods, interfaces, tests and rejection conditions. Fable resolves ordinary implementation details and owns integration; material changes to claims, economic scope or authority return to the CEO/Chairman.

## 7. Scope, sequencing and preserved work

The full target includes geopolitical/defense/oil discovery and reusable discovery across the seven specialist Catalyst domains. It retains adjacent earnings, policy, healthcare and staples as native-owner inputs. It does not commission a new brokerage, automated capital execution, military-operational intelligence, global surveillance system, or replacement financial-data platform.

Build three connected vertical releases rather than fourteen isolated engines:

**Release A - Market attention.** A covered theme outside the user's watchlist develops unusual participation/relative behavior; the real user receives a concise, timestamped discovery alert with an explanation or an honest unexplained state. Existing technical context is attached without claiming unearned alpha.

**Release B - Catalyst context.** A real official or licensed report creates/revises an incident, maps through evidenced exposure, nominates securities correctly, and updates the same user case. Corrections and de-escalation work as well as escalation.

**Release C - Qualified decision support.** A predeclared timing/market-response method demonstrates incremental value under valid evaluation and receives its bounded permission from the existing decision owner. A source-backed, measurable product remains useful if a particular model is rejected.

Prospective observation, negative-case testing, rights review and baseline construction proceed alongside A and B. They are not a final cleanup phase. Existing source or carrier denials are lane-specific; they do not authorize replay under a new plan.

### Existing-program mapping

This package extends #1181 P0 through a more precise source/coverage map; P2 through geopolitical context rather than a second procurement engine; P4 through actual opportunity delivery; P5 through earlier compatible observation; P6-P9 through native economics, expectations and graph composition; P10 through carefully distinct occurrence hypotheses; and P11 through operating and scientific acceptance. It does not absorb or supersede the specific Bio, evaluator, MedTech, Defense or Terminal repair carriers. [I01]

The known original #8468 refused publication and #8258 held repair must not be repackaged as new source work to evade those constraints. #9066's accepted implementation and #9456's closed duplicate must not be rebuilt. Terminal #778 and #811 need their actual source/custody checks before integration, not an assumption that their authors are still live approvers. [I04, I13, I14]

## 8. Completion boundaries

**This research package:** complete when the architecture, methods, interfaces, all component work packages, source evidence, falsifiers and acceptance rules are internally coherent, published with immutable references, and usable by a fresh Fable session without this chat. Static package validation is not repository CI or a live market test.

**Implementation:** complete only at the declared release's real source, publication, entitlement, browser, correction, outage and operating proofs. A mockup, fixtures, a green suite or a merge is not enough.

**Predictive qualification:** complete only for the exact target, market, horizon, information policy and costs tested. KEEP_SHADOW is not success disguised as a delay; it needs a named information obligation. REJECT is a valid scientific result with explicit product consequences.

**Whole North Star:** not proven by this document. No live predictor, October replay, market-profit result, provider entitlement or Fable execution is asserted. The next action after deliberate commissioning is the first dependency-ready work package, not another broad architecture census.
