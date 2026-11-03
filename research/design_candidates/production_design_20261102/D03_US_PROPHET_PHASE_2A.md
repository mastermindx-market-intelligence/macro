# D03 — US Equities and Prophet: Phase 2A product, data and implementation specification

## 0. Delivery status and custody

**Phase 2A source/research package: complete for the inspected scope. Full D03 design acceptance: PARTIAL / blocked by named dependencies. Formal reference state: draft.**

This is the Chairman-delivered D03 assignment in the existing Production Design programme, not a new Prophet workstream. The specification records observed source behavior, proposed design behavior and unresolved interfaces separately. It does not implement product code, approve a reference, grant a Paper write, settle an uncertain operation, or authorize release.

The durable carrier is [programme Draft PR #10617][PR10617], branch design/paper-production-audit-20261102-ryan, at this existing D03 source path. The original commissioning files and shared SESSION_RETURNS.md are preserved. The latter has a documented parent/child reconciliation collision; the programme owner should consume this bounded return rather than replace that ledger wholesale. The existing rich-opportunity writer remains on [PR #9495][PR9495]. No new branch, product PR, engine, registry, persistence service or competing product session was created.

### Exact inputs

| Input | Immutable revision / observed state |
| --- | --- |
| Assignment, common instructions, launch index, shared-shell contract, acceptance checklist and route census | Macro **6e1862867193ec6486a22001a0e4fb515da20448**; all commissioning inputs read at this same commit [A1][A2][A3][A4][A5][A6] |
| Current protected Mastermind procedure | **b2326bbe30e9988d26199f5e774a482b9c09068a**, protected master; skillpack schema mastermind.sol_skillpack.v1, version 1.0.1, bootstrap major 1 compatible [LAW] |
| Current Macro source observation | **fc85b0428cf8b0ca4f2fbbc5a415b2871f15a1c9**; source snapshot, not a beta release identity |
| Existing rich-opportunity work | #9495 **128ab198769a5cc2bd180d7f8eeae07924238d32**, branch claude/ssd-prophet-opportunity-system-20261015-5ba805642dd9aece; observed open and non-draft, left unchanged [R1] |
| F01 continuation | #10645 **34b4a52ddf9b56e6a1d3eed7816cbf5feed2d985**, Draft; work in progress, RIG draft, no released joint contract [F01PR] |
| F02 continuation | #10630 **c6eb32e1212ff22a1e3e6e8fe00b08e94bb31d82**, Draft. Native repairs/review ongoing; formal RIG draft, joint F01 release and consumer proof pending [F02] |
| Paper | PROPHET file **01M3NT5Y3G5HTJHVR0K5W2MDJM**. Explicit file/page reads; no page switch or mutation. Observation date 2026-11-03 UTC |
| Initial D03 checkpoint | **b913f808d56703c5bf45ec682361bd9f8027c69e**, same path; this complete specification replaces its IN_PROGRESS contents |

The bootstrap and paper-design-workflow procedures were applied before the D03 documentation write. Protected INDEX, COLD_START, SESSION_RELIABILITY, applicable ACTIVE_EXECUTION, delegation, routing, continuity, Paper integration and CLOSEOUT procedures were read at the protected pin. Native child consultations were bounded principal semantic analysis of existing source and an adversarial reasoning pass; they were not extra product sessions, Fabric execution, cross-model independent RIG review or reviewer approval. WHY NOT FABLE: these consultations did not require a new principal policy ruling, scarce continuity recovery or a separate commissioned implementation worker.

### Scope tree and return boundary

| Task | Result |
| --- | --- |
| D03.2A.1 — baseline, lineage, source and overlaps | Inspected all six route sources, all eleven assigned Paper pages at inventory level, selected native screenshots/trees, real beta shell, public production baseline and current #9495 drift. Beta body interaction remains unproven. |
| D03.2A.2 — product and retention | Product brief, normal and degraded journeys, complete bounded capability ledger and successor locations below |
| D03.2A.3 — data and interaction | Source-bound contracts, temporal/identity rules, controls, access, comparison and mutation boundaries below |
| D03.2A.4 — future builder package | Source integration sequence, responsive/accessibility contract, meaningful acceptance cases, performance and rollback requirements below |
| D03.2B — final editable compositions | Not attempted: verified joint F01/F02 v1 is absent from inspected evidence. Exact overlapping #9495 effects remain held. |
| D03.REVIEW — canonical reference qualification | Not submitted; full material-change review and immutable candidate freeze remain owed |
| Parent D03 mission complete | **false**. No approved new Prophet reference, production implementation or served proof is claimed. |

## 1. Product brief and success criteria

### Primary job

A self-directed investor needs to understand the US market backdrop, find a small number of worthwhile research candidates, challenge each candidate using evidence and explicit conditions, compare alternatives, and deliberately retain an investigation for later. On return, the user must be able to distinguish a changed price from a changed assessment and understand why a candidate, plan or historical observation changed.

The first useful view should answer: **What is worth investigating, what is the current published entry read, what evidence is missing, and what would change that read?** The product must remain useful when no entry is cleared. A source failure is a reason to explain availability, not a reason to manufacture a reassuring empty board.

This is research and model-plan presentation. Candidate selection, entry assessment, plan management, quote observation, saved research, holdings and order execution are different objects with different owners. The UI must not manufacture a trade instruction, fill, position, probability or new ranking from their visual proximity. Existing producer-authored action text remains attributable to its producer; a redesign does not silently re-adjudicate it. [M1][M2][R2][R3]

### Intended normal-data journey

1. Open /us_stocks.html in the shared shell. Read the market/session context and source date, then see the opportunity workspace without traversing a large decorative hero.
2. Scan Today in producer order. A card exposes company identity, source entry read, quote/price basis, chart, next condition, invalidation and a leading caution. “All candidates” makes the broader eligible set reachable with denominators.
3. Use Screener to search/filter and optionally switch to the existing table. Counts explain the difference among source population, eligible candidates, entitled rows, current filter and shown page.
4. Select two candidates in the same current board for a comparison of published facts. A third is optional. Compare each object's own dates, missing inputs, conditions and evidence. There is no calculated winner.
5. Open a setup from either card. Inspect structure, evidence, research links and Sources. A related model plan is explicitly a same-security record until an exact candidate/plan relation is supplied.
6. Visit the confirmed plan record and return to the same candidate, section, source generation, focus and scroll when still valid. If the source or authorization changed, explain why return cannot restore the old object and offer the current board.
7. Save research or request a watch through D23's existing owner only after a deliberate action. Read back the actual result. A pending or uncertain operation stays attached to its original identity.
8. Revisit. A fresh quote is labeled separately from the prior assessment and plan. Review new owner-issued facts without rewriting historical evidence or silently renewing entry permission.

Steps 1–4 partly exist in current main/source; richer comparison and return behavior have additional work in #9495. Steps 7–8 require D23's released object/write contract for this candidate binding. This document specifies the intended complete journey; it does **not** report that the journey was exercised successfully in a signed-in beta session. [M1][M4][R4][R5]

### Empty and unjudgeable journey

A filter that finds zero matching rows says “No candidates match these filters” and offers Clear filters; it retains the full entitled count where known. A confirmed zero admission count says “No candidates were admitted to this published board.” “No entries cleared” is reserved for an actual owner-supplied entry-readiness result with its evaluated denominator and observation date. A missing assessment says “Current entry read cannot be verified”; research facts remain accessible. A failed full-board request preserves the dated public preview and says “Full board could not load. Showing the dated preview.” These are four different states, with different recovery actions.

### Proposed hierarchy

The product proposal is a **compact rich-card workspace with an optional table**, not reinstatement of the rejected text-row-only direction. Preserve visual price history and decision conditions; shorten repeated chrome and repeated prose. Keep one principal analytical object above the fold with at most two supporting modules where useful. A compact market/session strip supports the workspace; full regime/breadth and sector context follow and remain reachable through local navigation.

Local sections: Opportunities; Market context; Sector timing; existing record/research destinations. Inside Opportunities, preserve Today / Screener / Plans as source views. These are not global navigation destinations or synonyms for one another. Inspectors show Structure, Evidence, Research and Sources with stable identity and a deliberate return action. F01 owns global navigation, global search, account/theme/language and overlay composition. F02 owns common primitives and formatting. [A4][R1]

**New or strengthened proposals, not current services:** an owner-supplied assessment timestamp/receipt; durable listing and candidate identity for cross-session persistence; exact candidate/plan relationship; aligned strategy/horizon comparison; source-vintage mismatch notices; explicit availability reasons on satellite loaders. Do not make those features appear operational using illustrative Paper data.

### Measurement plan

Future evaluation should measure successful completion of scan → compare two → setup/evidence → return at 390px and narrow desktop; correct user distinction between fresh quote and old assessment; ability to recover from zero matches and unavailable reads; absence of lost focus/source context; and persistence readback accuracy. Instrumentation names and collection belong to existing analytics owners and require normal product implementation review. No usability rate, conversion lift or production performance result is asserted here.

## 2. Route, object and access map

### Assigned canonical routes

| Canonical ID | Exact route | Source and builder at inspected main pin | Boundary |
| --- | --- | --- | --- |
| macro:us_stocks | /us_stocks.html | templates/dashboard.html.j2; scripts/build_site.py; mode stocks / body.page-stocks [M1][M2] | Live anonymous HTML shell; paid rows are separately served. D02 integrates the common template; D03 owns the US region. |
| macro:foresight | /foresight.html | templates/foresight.html.j2; scripts/build_foresight.py [F1][F2] | Live theme research, not a stock-ready board |
| macro:leader_radar | /leader_radar.html | templates/leader_radar.html.j2; scripts/build_leader_radar.py [L1][L2] | Live leadership/recovery surveillance with its declared universe |
| macro:winner_health | /winner_health.html | templates/winner_health.html.j2; scripts/build_winner_health_page.py; engine/top_maturation.py [W1][W2][W3] | Live descriptive wear/cohort history; no exit/short authority |
| macro:us_stocks_lab | /us_stocks_lab.html | templates/us_stocks_lab.html.j2; scripts/build_pick_lab.py → engine.pick_lab.render; nightly caller scripts/ci/daily_engine_regime_dashboard.sh [B1][B2][B3] | Existing lab lifecycle. This is Pick Lab, not a newly exposed private Prophet Lab API. |
| macro:us_stocks_v2 | /us_stocks_v2.html | templates/us_stocks_v2.html.j2; scripts/build_stock_board_v2.py [V1][V2] | Unlinked shadow/lab preview; not promoted to the live product |

The commissioning census classifies these HTML route shells as anonymous. The actual access configuration states that HTML shell access and asset/API access are separate: non-public static assets are default-deny; /premiumdata/ is enforced before the general paywall switch; APIs gate themselves. Therefore this document does not infer that a route's raw JSON is anonymously available just because its HTML is reachable. Deployment enforcement still requires actual HTTP checks. [A6][ACCESS]

### Existing route/query/hash contracts to retain

| Contract | Observed behavior / requirement |
| --- | --- |
| /us_stocks.html?life=watch, ready, entered, delivering, overtime, invalidated or resolved | Plan lifecycle filter. Query wins over legacy inbound #life=. Existing code normalizes to query with replaceState; invalid values clear the filter. The existing implementation drops the fragment during this normalization even though a nearby comment says otherwise. Preserve observed compatibility until F01/owner adjudicates fragment coexistence; do not silently “repair” it in a CSS migration. [M1] |
| Today / Screener / Plans | setSrc(mode) sets data-prophet-src to today, candidates or plans. “mode” is a JavaScript parameter, **not an established URL query**. Today falls back to Candidates if its section is absent. Table is Candidates-only; switching to Today or Plans leaves table mode. [M1][R4] |
| Grid / table | Existing mdx_stocktable2_us_view preference; columns/order/widths use the same market-scoped owner. Filtering/sorting are local state unless an existing owner explicitly serializes them. Do not invent ?compare=, ?strategy= or a universal history date query. [M4] |
| US board / Radar stock destination | stock.html#<ticker>, as emitted by those owners. Preserve fragment and modified/new-tab clicks; resolve company/listing context through D07/F01 rather than replacing it with a guessed /analysis mapping. [M4][L1][R3] |
| Winner Health company destination | Consume producer row.href, currently /stocks/<ticker>.html only when that rendered page exists. With no href, preserve plain-text identity; do not manufacture a stock.html hash link. [W1][W3] |
| Terminal | Live beta shell observation included /terminal?from=macro&ret=https%3A%2F%2Fbeta.mastermind-x.com%2Fus_stocks.html&symbol=NVDA. Existing table uses the shared Terminal handoff; do not raw-navigate a native app into an embedded legacy slot. Preserve admitted return bytes and origin checks. [M4] |
| Market Memory | /market_memory.html?mm_issuer_input=<ticker>&view=memory, with mm_lang=en or zh in #9495. This is symbol research using recomputed history, not an exact candidate/episode replay. Existing link opens a new tab and keeps the setup open. [R2][R3] |
| Theme context | /baskets.html#theme-<validated-id> where producer context exists; D05 owns the destination. No invented theme when linkage is absent. [R2] |
| Plan detail | Existing DOM target #pv-<plan-id>, newer-episode links and selectPlan behavior; do not replace by a ticker-only newest-plan lookup. Missing/withheld target does not establish a successful return journey. [M1][R3][R4] |
| US context anchors | #us-standouts, #size-style, #breadth, #advanced-breadth, #sectors, #holdings and existing What changed/detail controls remain reachable. Shared shell anchor ownership must be verified before changing scroll containers. [M1] |
| Pick Lab controls | scoreboard, velocity, allbooks, beta, longhold, accountability, method are existing local tabs; book-drill selects the matching All Books or Long-Hold panel and opens its fire history. No historical replay endpoint is implied. [B1] |

Do not change canonical IDs, route aliases, SEO inclusion, audience or generated registry through a domain design document. F03 and the existing exporter own those projections. D04 discovery, D05 sectors/themes, D06 Terminal, D07 Company, D12 historical research, D14 assistant, D20 regional consumers and D23 saved state retain their ownership.

## 3. Feature retention ledger

Disposition applies to the future D03 design, not to whether an implementation has shipped. RETAIN keeps meaning and reachability; IMPROVE changes presentation/interaction with the same owner; BLOCKED_DATA preserves the need with an explicit source gap and useful interim behavior. **No feature is authorized for removal or relocation in this package.** Material reductions need a separate product decision.

All rows have reviewer decision **pending**; no row is independently approved by this author. The successor is within the same route unless explicitly named as an existing cross-product destination.

| ID | Capability and baseline | Disposition | Successor / implementation requirement / dependency |
| --- | --- | --- | --- |
| U01 | Global shell, title, regional context, search, language/theme/account [A4][M1] | IMPROVE | F01 shell slots; retain exact US context and route. Remove duplicate legacy global chrome only through shared composition. |
| U02 | Market posture, regime path, session/as-of context [M1] | IMPROVE | Compact summary above Opportunities; full dated context remains in Market context. D02 keeps interpretation. |
| U03 | Risk/regime research and chart/assistant entry points [M1][R1] | RETAIN | Existing destinations and source context; D14 owns assistant actions. Preserve the held assistant/focus overlap. |
| U04 | Group/action board, five lanes, counts and preview [M1][M2] | IMPROVE | Adapt columns to actual available width; same group membership, lane meaning and entitled rows. |
| U05 | Today / Screener / Plans [M1] | RETAIN | Same source views, defaults/fallbacks and source distinctions |
| U06 | Screener grid/table, sort, filters, columns, resizing, pagination [M1][M4] | IMPROVE | Same table owner and preferences; keyboard controls and narrow-width reflow; null-last sorting |
| U07 | Name, ticker, sector/industry, geography [M1][R2] | RETAIN | Visible identity plus known currency; missing taxonomy remains missing |
| U08 | Durable listing/candidate identity for compare/save across generations [R2][M5] | BLOCKED_DATA | Producer binding + D07/F01 resolver + D23 object contract required; use current exact occurrence/source only meanwhile |
| U09 | Price, price change, sparkline/daily closes, source geometry [M1][R2] | IMPROVE | Keep useful chart and separate clocks; no fabricated flat history or synthetic change |
| U10 | Assessment timestamp and first-visible time [R2][R3] | BLOCKED_DATA | Presenter currently emits assessment_asof=None; show date unavailable and preserve signal/board/quote dates separately |
| U11 | Entry read, next condition, zone, stop/base invalidation/chase boundary [R2][R3] | IMPROVE | Concise headline + source detail; preserve distinct levels and source authority |
| U12 | Relative priority and evidence families [M3][R2] | RETAIN | Producer order and definition; no probability or return interpretation |
| U13 | Full eligible pool, Featured and other intake lanes, archive status [M2][M3] | IMPROVE | Full entitled roster reachable, lane/count denominators explicit; no rescore or readmission |
| U14 | Passed/refused candidates and reason receipts [M2] | RETAIN | Same board's refusal shelf; distinguish producer refusal from user dismissal and previous membership |
| U15 | What changed, reason deltas and prior source date [M1][M3] | IMPROVE | Explain entry/exit/change with exact before/after basis; do not infer new state from price |
| U16 | Board outcome history [M2] | RETAIN | Existing 21-board-date lookback and first-surfaced basis; not model-plan performance |
| U17 | Leader observations / early observations / coverage [M1][M2] | RETAIN | Separate source date and unavailable/degraded states; context only, protected names preserved |
| U18 | Seven plan lifecycle cells and filter counts [M1][M2] | RETAIN | watch/ready/entered/delivering/overtime/invalidated/resolved; use producer totals, not visible DOM |
| U19 | Model terms, targets, horizon, original plan basis and episode links [R3][R6] | RETAIN | Immutable terms and current management read side by side; model records never personal holdings |
| U20 | Management-date/last-close coherence and price-frame state [R6] | IMPROVE | Separate dated management observation; withhold inconsistent or undated observation |
| U21 | Exact candidate → plan relationship [R3] | BLOCKED_DATA | Source says related_security / data-plan-exact=unavailable; label same-security relation; do not assert “this candidate's plan” |
| U22 | Sources → Plans → same candidate/section/focus/scroll [R4][R5] | IMPROVE | Reuse existing transient return owner; source/auth invalidation clears safely; signed-in proof owed |
| U23 | Compare two or three setups [PA][PC][R5] | IMPROVE | Reuse #9495 source-bound compare, not a second selection store; main lacks that newer study workflow |
| U24 | Strategy/horizon aligned comparison [PA][R2] | BLOCKED_DATA | Strategy and horizon absent in candidate presenter; published-facts comparison remains useful with explicit limits |
| U25 | Setup detail, previous/next, structure/evidence/research/sources sections [R3][R5] | IMPROVE | Same source object, accessible modal/inspector, section and focus return |
| U26 | Supporting evidence, cautions and abstaining families [R2][R3] | IMPROVE | Keep positive, contrary and absent evidence distinguishable; evidence drilldown is not a new signal |
| U27 | Breadth, size/style, advanced breadth and sector timing [M1] | IMPROVE | Meaningful charts/tables below main workspace; all anchors and detail controls reachable |
| U28 | Turn setups and leaders / fresh-trigger links [M1][M2] | IMPROVE | Distinguish zero qualifiers from source failure. Existing uncertain refinement remains held. |
| U29 | Fund moves / holdings context [M1] | RETAIN | Existing institutional context and D09/D22 destinations; no false personal position |
| U30 | Market Memory and theme/company/Terminal investigation [R2][R3][M4] | RETAIN | Exact existing links, current/recomputed history qualification and return context |
| U31 | Save/list/watch/alert/revisit Paper workflows [PA][PC] | BLOCKED_DATA | D23 existing write/readback/dedup owner required for candidate binding; navigation does not save or activate |
| U32 | Gate, first-use, loading, empty, stale, partial, failed and expired states [M1][ACCESS] | IMPROVE | Preserve public/protected split and distinct reasons; no “healthy empty” substitution |
| U33 | Plan-book dense Table and Grid parity, P-MP1-DENSE [MP1] | IMPROVE | Owed under the existing separate commission/review boundary; same canonical plan identities/lifecycle filters, complete table population; do not substitute candidate StockTable or impose an arbitrary cap. |
| U34 | Ready/waiting/unjudgeable summary [PC] | BLOCKED_DATA | Entry-assessment/board owner must supply authoritative mapping, denominator and clock. Until then show individual published labels and aggregate unavailable; never derive it from eligible/Featured or plan-ready counts. |
| F01 | Foresight early shortlist and complete theme stages [F1][F2] | RETAIN | Theme-stage vocabulary, unknown state and technical receipt remain reachable |
| F02 | Supply/demand/guidance/revision relay and provisional evidence [F1] | IMPROVE | Text/fingerprint qualifiers, member floors, source dates and numeric absence explicit |
| F03 | Entry-ready stop and global dislocation observation [F1] | IMPROVE | Separate observations; no stock entry authority |
| F04 | Missing dislocation availability reason [F1] | BLOCKED_DATA | Current absent object can render Closed. Producer availability/reason needed; interim “not available” design, never infer a negative |
| F05 | Glut risk, caps/score details, context and discovery shelves [F1] | RETAIN | Same domain calculations and reachable secondary content |
| F06 | Thesis mechanism, confidence category, kill criteria, monitor [F1][F2] | IMPROVE | Attribute analyst thesis and deterministic monitoring separately; no model price forecast |
| F07 | Divergence / narrative-money cross-sectional ranks [F1] | RETAIN | Percentile rank with thin/exclusion handling, not event probability |
| F08 | Forward grading, controls, horizons, intervals, FDR and pending outcomes [F1] | RETAIN | Keep membership at flag time; controls are not skill hits |
| F09 | Per-leg health and CONFIRMER-ONLY mode [F1][F2] | IMPROVE | No verified-early claim while leading supply inputs are dark |
| F10 | Event logs and artifact/render vintage [F2] | IMPROVE | Existing history retained; show/document mixed vintage without treating exit zero as freshness |
| L01 | Radar universe/regime/coverage receipts [L2] | RETAIN | Selected baskets + pinned Dow/NDX intersected with issuer tape, excluding ETFs; no whole-US claim |
| L02 | Confirmed lifecycle, raw read, hysteresis, changes/fires [L1][L2] | IMPROVE | Frozen stale state and missing prior history explicit; suppress stale/first-observation fires |
| L03 | Near-trigger, entry and early-entry context [L1] | RETAIN | Distinct from lifecycle and RS-high observations |
| L04 | RS highs and relative-strength histories [L1][L2] | RETAIN | Separate pullback/entry evidence; disclosed clock |
| L05 | Recovery states, reasons, search/sort/show-all [L1][L2] | IMPROVE | Same filters, cap behavior, unavailable/history-incomplete and revision reasons |
| L06 | Analyst revision coverage and held-out options factor [L1][L2] | RETAIN | Missing vs false vs held-out remain distinct; held-out never counts |
| L07 | Handoff, rerating and main lifecycle board [L1] | RETAIN | Preserve source sections and stock.html#ticker destinations |
| L08 | Historical fires, lockout, history_since/gaps and grading [L2] | RETAIN | Retain session-based mechanics and same-day rerun behavior |
| L09 | Dual clocks, additive lineage and schema/coverage disclosure [L2] | IMPROVE | Incumbent and majority-issuer clocks do not overwrite each other; truncated names do not define denominator |
| W01 | Three overlapping Winner Health cohorts [W1][W3] | RETAIN | Fixed cohort order; no tier severity hue or summed unique total |
| W02 | Wear states and off-ladder “Not enough to compare” [W1][W3] | IMPROVE | Four descriptive states, separate unreadable read; no sell/short directive |
| W03 | Recent qualification window and changed-character retention [W1][W3] | RETAIN | Display declared duration only; never refit thresholds in UI |
| W04 | Same-cohort shape/age analogues [W1][W3] | RETAIN | Episode count, horizon, threshold, track and survivorship limitations adjacent |
| W05 | Thin history and track-specific disclosures [W1] | RETAIN | N<12 shows count without rate; no inferred independent-company sample |
| W06 | Artifact age vs tape lag; tier zero/unreadable/all-clear [W1][W2] | IMPROVE | Loader rejects age >6 calendar days; separate tape warning at >5 sessions |
| W07 | Typed missing/stale/unreadable loader reason [W2] | BLOCKED_DATA | Handled loader failures collapse to wh=None; export their reasons. Reuse existing producer null_state/null_reason. Invalid calendar dates can raise outside the parsing handler. |
| B01 | Pick Lab Scoreboard and engine drilldown [B1][B2] | IMPROVE | Preserve engine/entry definition, sample counts and own grading horizons |
| B02 | 1D Velocity [B1] | RETAIN | Daily-trigger velocity books with their declared forward grading horizons; not current opportunity readiness |
| B03 | All Books and individual fire histories [B1][B2] | RETAIN | Stable engine IDs, provenance and pending grades |
| B04 | Beta/T0 panel [B1][B2] | RETAIN | Separate experimental semantics and missing data; no promotion into Prophet |
| B05 | Long-Hold Grid [B1][B2] | RETAIN | Separate books/horizons; no blending with entry scoreboard |
| B06 | Record/accountability and coverage [B1][B2] | RETAIN | Existing audit scoreboard, underlying fire/grade basis and denominators |
| B07 | Method and first-accrual/empty states [B1] | IMPROVE | Accessible tabs and honest not-yet-graded versus no-fire copy |
| B08 | Lab renderer and artifact freshness [B2][B3] | IMPROVE | Keep lab route and nightly ownership; no live grading or builder execution on page navigation |
| V01 | V2 shadow candidate board and filters [V1][V2] | RETAIN | Remains separate unlinked preview and schema; never replaces live us_standouts |
| V02 | Shadow source inputs and context readers [V2] | RETAIN | Reuse actual artifact inputs; no alteration of live selection |
| V03 | Shadow methodology/uncertainty and empty states [V1][V2] | IMPROVE | Explain shadow status and source age, no implied validation |
| V04 | SEO/route/lifecycle exclusion [A6][V2] | RETAIN | Existing registry owner controls any future admission |
| P01 | Original daily brief, no-entry, change log, no-prior-history [P1] | RETAIN | Preserve task/state semantics as reference; no automatic adoption of original hero or global chrome |
| P02 | Quote refresh and assessment review separation [P8] | RETAIN | AN9-1/AU9-1, failure/health/review families remain reference obligations |
| P03 | Setup/evidence/playbook and return details [P7] | RETAIN | Preserve conditions and source identity; a playbook preview is not a live assessment API |
| P04 | Regional and shared state contracts [P5] | RETAIN | Consume semantics with D20; do not export US currency/session behavior wholesale |
| P05 | Rejected R6 text-row lineage and rationale [PB] | RETAIN | Retain as rejected archive and negative comparison; no revival by renaming |
| P06 | R7/R8, successor and flagship references [PA][P9][PC] | IMPROVE | Qualify a future canonical composition against F01/F02 and RIG; preserve all originals |

**Ledger totals: 78 capabilities — 38 RETAIN, 32 IMPROVE, 8 BLOCKED_DATA, 0 RELOCATE, 0 REMOVE.** The blocked rows are U08, U10, U21, U24, U31, U34, F04 and W07. BLOCKED_DATA is a retained obligation, not a deletion. Counts are verified in the artifact validation receipt below.

## 4. Real data and backend contracts

### 4.1 Owners, artifacts and responsibility

| Surface | Existing producer / transport | Actual consumed contract | Cadence, cache and failure |
| --- | --- | --- | --- |
| US candidate board | scripts/build_stock_library.py; engine/us_board_rank.py; scripts/build_site.py [M2][M3][M6] | site/factordata/us_standouts.json. Envelope includes as_of, board_definition, ranking, eligible, universe, lane_counts, staleness, candidate_pool, delta, emit and w3c_source. It is not a newly invented universal opportunity API. | Nightly/source publication. Build_site binds raw source bytes before decoration and public/protected split; rebuilds and re-splits after library refresh to avoid one-build lag. |
| Today native binding | app/prophet_daily_brief.py → scripts.build_stock_library.read_today_candidate_projection [M5] | Authenticated GET /api/prophet/daily-brief/v1; exact source_sha256, pair_id, selection_receipt; optional candidate_generation_id | Same-origin no-store; site_full authentication before query parsing/owner read. One in-process admitted read; overlap fails privately rather than queues. No independent selection or quote/plan receipt. |
| Entitled hydration | scripts/build_site.py plus dashboard gate loader [M1][M2][ACCESS] | /premiumdata/us_stocks.json; Today/candidate/plan/adjacent-panel HTML and metadata slices; independent gate switches over one payload | credentials same-origin, cache no-store. Preserve dated preview on denied/offline/error; withhold stale native context. Auth generation and source binding must still match when a response lands. |
| Model plans | scripts/build_prophet.py and engine/us_board_rank.py [M7] | site/prophet/index.json; lifecycle_counts, model records, original terms, source-board/plan/management dates | Existing plan publication. Absent book and corrupt existing book are distinct loading/error conditions. This session's full index blob retrieval failed with Transport closed; its current row completeness was not certified. |
| Model-plan presentation | engine/prophet_plan_presentation.py in #9495 [R6] | plan id, asset, lifecycle_state, plan_asof/recorded_at, price_basis_date, board_read, entry/entry_zone/invalidation/targets/horizon_days, management and last-price fields | Read-only projection. Metadata can fill company descriptors but cannot invent management dates, quotes, fills or terms. |
| Quote/forming overlay | existing dashboard live overlay; live/prophet_live.json [M1] | Separate delayed/forming read; own source status/time and session logic | Current client fetches every 120s while visible, visibility retry floor 30s; one-minute rail tick causes no network. PLV_MAXAGE=15min. The plane is described as 15-minute delayed; do not label it real time. |
| Board-state interpretation | existing lib/board_state.board_state_view consumed by build_site/template [M1][M2] | ahead/provisional, behind, closed, confirmed, complete receipt counts | This interpreter remains the single authority. confirmed + adjusted + dropped must equal n_total before a combined receipt is shown; dropped is not a sell instruction. |
| Leader observation shelf | engine.us_leader_pullback_coverage; site/anticipationdata/us_leader_pullback.json [M2][ACCESS] | Full active population, available/empty/degraded/unavailable and its own date | Context only; paid roster remains protected; preview and full totals are different quantities |
| Theme tape/context | existing engine.theme_tape presentation joins [M2] | Existing artifact context and own as-of, sometimes a nightly generation behind | No rank/gate/score/size authority. Empty/stale input cannot be promoted into a current theme signal. |
| Board outcomes | nightly grade_us_board output site/factordata/us_board_outcomes.json [M2] | Names leaving prior 21 board dates; return since first surfaced | Historical board record, not plan return, current recommendation, forecast or full strategy backtest |
| Foresight | scripts/build_foresight.py → engine.foresight_cascade and existing health/grader/shadow/ENB/convergence/thesis monitor [F2] | site/basketdata/foresight_cascade.json contains dict(cascade) plus optional health. HTML also receives separate grading/track-record, analyst/monitor and research contexts, with render-time generated_utc; not all HTML data is in the JSON. | Empty/failed cascade may preserve prior HTML and return success. JSON precedes HTML render; mixed generations are possible. Builder writes ledgers; it was not executed as a “preview.” |
| Leader Radar | scripts/build_leader_radar.py → engine.leader_lifecycle and additive RS/recovery owners [L2] | site/leaderradar/radar.json, main schema leader_radar.v2; disabled stub has v1 shape and enabled=false | Nightly histories and session clocks; stale suppresses fires. HTML/JSON can diverge after render failure. Main header's v1 description is not the emitted v2 schema. |
| Winner Health | engine/top_maturation.py → data/top_maturation/latest.json; scripts/build_winner_health_page.py [W2][W3] | Actual SCHEMA winner_health.v2; asof, data_last_day, tape_lag_sessions, universe_n, tiers, null_state, macro_backdrop | Nightly context; loader rejects artifact age strictly >6 calendar days, using builder-host date.today(); tape warning separately >5 sessions. Age six passes, age seven fails. Actual code supersedes stale v1 module prose. |
| Pick Lab | scripts/build_pick_lab.py; engine.pick_lab snapshot/ledger/book/render owners [B2][B3] | site/labdata/pick_lab.json, pick_lab_longhold.json, pick_lab_fires.json. Entry has as_of,built_at,scoreboard,books,lanes,regime,authority=display_only. Long-hold has horizon_role=hold_thesis. Beta additionally reads factordata/t0_indicator.json; Record reads factordata/us_audit_scoreboard.json through engine.pick_lab.render._load_audit_scoreboard. [B4] | Nightly enrichment, fire lockout and matured grading; builder writes snapshots and ledgers. Rendering can fail after valid JSON and main returns zero under its never-break policy. Not run here. |
| Security save / list membership | site/watchstore.js (matching template source); shared Supabase client and MDXAuth [SAVE] | WatchStore.lists.*, WatchStore.symbols.saveChecked(listId,tickers,opts), symbols.inspect(listId,symbol); watchlists and watchlist_symbols | Existing account/list-scoped owner, 12s configured read deadline. Checked save serializes per list, reads before/after and reports waiting/saved/rejected/uncertain. A membership read is not a receipt for an earlier insert and never authorizes a retry. |
| V2 shadow | scripts/build_stock_board_v2.py [V2] | Reads us_standouts.json + setups.json and context artifacts; writes us_standouts_v2.json and unlinked us_stocks_v2.html | Separate shadow output; no live consumer/selection mutation. Failure returning zero is not freshness proof. |

### 4.2 Exact native daily-brief binding and access

The existing API accepts exactly four names: required source_sha256 and selection_receipt match sha256: plus 64 lowercase hex characters; required pair_id is 32 lowercase hex; optional candidate_generation_id matches peg: plus 64 lowercase hex. Unknown, repeated, empty, malformed or path-shaped values return 400 after authentication and before owner read. Requests cannot choose a filesystem path. The source owner's returned envelope passes through without a new selection/provenance authority. [M5]

AVAILABLE or PARTIAL returns 200; UNAVAILABLE returns 503 except SOURCE_BINDING_MISMATCH or SELECTION_BINDING_MISMATCH, which returns 409 carrying the original envelope. An optional candidate-generation mismatch stays 503. Unexpected runtime/import/serialization failures produce generic private DAILY_BRIEF_UNAVAILABLE, without internal paths. Auth denial retains private headers. The frontend makes one native query on admitted full-roster metadata; missing session makes no query, and 409/503 is not a license to retry or silently substitute the newest generation. [M1][M5]

A successful candidate binding is **not** a complete daily brief. Plan, assessment, evidence and quote owners must supply their own real records. Render typed absence if they have not. Do not use the route's 200 response to grant entry readiness.

### 4.3 Candidate field contract

| Field / object | Type and units | Meaning / missing behavior |
| --- | --- | --- |
| ticker, name, industry, sector | Source strings; US view | Ticker is navigation/display identity, not proof of permanent listing identity or same candidate episode |
| occurrence_id | Caller-owned string: ASCII letter followed by up to 95 ASCII letters, digits, underscores or hyphens in the rich presenter | DOM occurrence; currently prefix + row index. It is not durable across reranking, regeneration or another view. |
| Source pins | SHA256, pair id, selection receipt, optional native generation | Bind exact published roster. Retain source order and occurrence; never join a candidate merely by matching a ticker. |
| entry_signal.status | Producer categorical value | Renderer maps known statuses; missing/unknown means Assessment unavailable, not zero, wait or avoid. |
| entry_signal.headline / action | Producer EN/ZH text | Attribute as published assessment detail. No generated “current advice” from price arithmetic. Missing ZH can be visibly labeled original-source text rather than pretending translated equivalence. |
| assessment_asof | **None in current #9495 presenter** | Do not fill with board_asof, signal_asof, price time or page render time. The source gap blocks verified-current claims. |
| signal_asof | Source session date string | Signal session, distinct from assessment creation/review date |
| price / price_as_of | Presenter accepts finite numeric value; USD / supplied source clock | Price without time may be shown as an undated snapshot with explicit qualifier; never presented as fresh/live |
| quote.change | None in read-only presenter | Current change may come from existing quote owner; absent change is not 0.00% |
| spark_svg / spark_as_of | Valid source geometry / chart observation date | Presenter extracts permitted numeric SVG geometry, validates monotonic x and bounded points; absent/invalid history gets no chart, not a flat substitute. Do not redraw zone against a later quote. |
| entry_signal.buy_zone.low/high | Finite positive USD numbers, low ≤ high | Zone snapshot uses board as_of only as zone-source date; that date does not timestamp the assessment |
| entry_signal.stop | Source numeric USD when supplied; positivity not established by the setup formatter | Entry-method stop, distinct from base invalidation |
| hold.invalidation | Source USD when supplied | Base invalidation; do not relabel as exact close-based execution logic without the owner's comparator/session rule |
| entry_signal.chase_above | Source USD when supplied | Chase boundary, not a price target |
| prophet.score / conviction.score_edge | Finite relative score with its actual definition | Priority uses prophet.score first, fallback conviction.score_edge. Relative evidence-family strength for us_prophet_v3; not calibrated win probability or return forecast. |
| prophet.fusion | Versioned known family contributions and active/abstain sets | Rich presenter requires valid family keys and finite 0–100 values; missing family abstains, never becomes zero evidence |
| lane / stage / candidate_pool lane | Separate enumerations | Setup form, current stage and pool admission/display lane must remain separate |
| strategy / horizon | **None in current candidate presenter** | Do not infer Early leadership, Earnings quality or Cycle capture from a chip, ticker or momentum measure |
| plan relation | related_security / none / unknown in current template | Same-security relation only; exact candidate-plan relation explicitly unavailable |
| auth / entitlement | Current session and server-enforced feature | Never a CSS-only visibility rule. Do not leave protected rows/selection/source data after revocation. |

Source: rich presenter and setup adapter [R2][R3]. **Observed validation versus proposed requirement:** only the entry-zone pair explicitly enforces 0 < low ≤ high here. The rich money formatter accepts finite values, including zero/negative, and setup terms are directly formatted. For future usability, nonpositive US equity quotes/stops/invalidation/chase levels must not become usable price geometry or automatic crossing evidence without domain-valid producer support. That is a required validation gap to resolve, not a claim that current code already rejects them.

The current source artifact was directly inspected, not just the template: its first buy row had a price and signal session but no price_as_of or spark_as_of fields; therefore the missing-clock design is an actual data condition. This sample is evidence of a contract gap, not a recommendation about the sample security.

### 4.4 Counts and sorting: concrete observed example

At main pin fc85…, the inspected us_standouts.json has board as_of 2026-10-30, eligible=172 and universe=1580. universe_sources.total=3072 describes a different source-universe inventory. candidate_pool lanes are Featured 9, More actionable 112, Late/unfillable 39 and Forming 12, summing to 172. ranking.featured_count=12 is a different selection/display concept; candidate_pool records three explicit divergences. These are not contradictory values to “fix” by forcing them into one badge. [DATA]

The same source has staleness.price_through=2026-10-30, expected_session=2026-11-02, sessions_behind=1, delayed=false, basis=panel_majority, plus an observation timestamp. Calendar age, session lag and the delayed flag are not interchangeable. Main source uses the older of the panel majority and board as-of; unknown fails closed; its delayed threshold is at least two NYSE sessions behind. [DATA][M2]

Display each count with its noun and denominator: source universe; scored universe; eligible; source-selected; entitled; matching filters; shown on this page. Keep zero when measured; use unknown/unavailable when the relevant population is unreadable. A list of uncovered tickers truncated for display does not establish the uncovered population total. The main StockTable keeps nulls last in either sort direction, counts the complete filtered set rather than the current page, and resets pagination on filter/sort/column change. Retain those behaviors. [M4][L2]

## 5. Readiness, momentum, invalidation and time

### 5.1 Keep the six meanings separate

| Meaning | Source / reading | UI rule |
| --- | --- | --- |
| Selection priority | Rank source, evidence-family breadth and original order | “Priority” with definition; not probability, target return or position weight |
| Setup maturity | lane/stage / source structural progression | Describes development. A mature/trending setup can still have a blocked or missing entry read. |
| Entry assessment | entry_signal and any future real assessment receipt | Display the published status and actual date/availability. Missing current evidence cannot be upgraded by quote proximity. |
| Momentum | Source price/relative-strength/extension measures with window and as-of | Label the metric, window, benchmark and basis. A positive day does not mean Buy; a negative day does not cancel a valid owner read. |
| Invalidation / lifecycle change | Source-owned condition or adjudicated plan-management event | A threshold, observed crossing and issued invalidation are different facts. UI never becomes the management engine. |
| Freshness | Per-object observation/publication/review availability | Fresh quote, old chart, old assessment and current page can coexist. No single green “live” badge certifies them all. |

Known rich-presenter status labels include buy_now→Buy, partial→Buy · partial, buy_soon→Near, await_confluence→Awaiting confirmation; hold, topping, exit, avoid, extended, blocked, wait, watch, wait_pullback and bounce_wait retain their source meanings. These are not a new D03 model or permission to execute. Unknown stays Assessment unavailable. [R2]

A source might publish action-oriented text or a field named confidence; do not silently convert it into a validated outcome probability or user-specific sizing advice. The current presenter explicitly supplies no strategy/horizon or reward/risk calculation for candidate comparison. Keep unqualified legacy fields inside an attributed source view until their owner provides the definition required for a product summary. [R2][R3]

### 5.2 Operational truth table for the design

This table is proposed presentation behavior; it does not overwrite producer states.

| Evidence condition | Primary presentation | Available action / prohibited inference |
| --- | --- | --- |
| Source assessment present with an actual valid owner clock and required inputs current | Published entry read + reviewed/observed time | Open setup/evidence; show source conditions. No order/fill is created. |
| Source says Buy/Near but assessment clock is absent | “Published entry read: Buy” or source label; “Assessment date unavailable; current readiness unverified” | Research remains available. Do not label this a fresh assessment. |
| Fresh quote, older or stale assessment | Both dates; “Quote updated; entry read unchanged” | Review conditions. A refresh does not renew the assessment. |
| Stale/missing quote, prior known assessment | Historical published read plus “Current quote unavailable/stale” | Do not claim current zone membership. Do not relabel as invalidated or revoked solely because freshness failed. |
| Known wait / confirmation required | Exact unmet condition from source | Inspect evidence or request an explicitly defined watch; no invented countdown |
| Required evidence missing | “Cannot judge the current entry read” plus missing input | Keep candidate research and recovery; unknown is not waiting, failed score or no opportunity |
| Optional evidence absent/abstaining | Show available core read and absent leg | Do not silently fail the whole object or add zero to a score |
| Actual owner-issued invalidation/revocation | Status, event/review time, reason, retained prior terms | Preserve history; do not substitute a later quote as proof |
| Historical-only record | “Historical model record” with original dates and known management observation | Investigate history; no current entry claim |
| Different generation arrives during detail/compare | Announce changed source and invalidate unsafe context | Do not replace one compared assessment in place under an unchanged title |

**Paper contradiction to resolve:** R7 SYI-0 uses “Entry revoked” alongside stale quote language. R8 YW1-0 improves this to “Entry unverified” and explains that a stale quote cannot confirm entry. Preserve the distinction, but verify whether any actual owner-issued revocation exists before reusing either label for real data.

**Aggregate-readiness guard:** R7's ready/waiting/unjudgeable summary needs an authoritative entry-assessment mapping, evaluated population and timestamp. eligible counts candidate admission; Featured counts presentation selection; plan lifecycle ready describes a plan. None can populate that summary by itself. If the mapping is not supplied, keep individual published labels and mark the aggregate unverified. Producer status partial / “Buy · partial” is also unrelated to partial network payloads or missing evidence.

### 5.3 Five clocks plus publication

1. **Quote observation time:** provider/market timestamp and any declared delay; not the time JavaScript received it.
2. **Signal and chart session:** dated daily signal and final chart observation; they may differ.
3. **Assessment issue/review time:** real owner timestamp; currently absent in the candidate presenter.
4. **Plan terms and management time:** original plan date/price basis and later management evaluation, each retained.
5. **Evidence observation/availability time:** when the economic/event fact occurred and when that version was available.
6. **Publication/build time:** when the site artifact was emitted. Useful operational provenance; it does not replace any of the above.

Use exchange-session policy from the producer. Do not count weekends/holidays by subtracting browser dates. The forming overlay's existing ET schedule has its own pre-open/active/closed/settled logic and close-pass requirement; late/stale producer output must not become a confident closed receipt simply because the local clock passed 16:20. Current PLV constants and comments include cadence/calendar assumptions that the original source owner must revalidate at implementation; D03 does not invent a market calendar or TTL. [M1][M2]

### 5.4 Invalidation and comparison rules

An actionable condition must ultimately identify subject listing, comparison operator, threshold/units, price adjustment basis, observation kind (intraday/close), session/calendar, condition window, source/version and authority that evaluates it. The existing source supplies some numeric levels but not a universally complete typed condition. Until those fields are supplied, show the source's wording and number; do not generate an automatic alert evaluator or client-side invalidation event.

Equality at a boundary is only meaningful if the operator is known. A daily close below a level differs from an intraday tick below it. Split-adjusted history differs from raw current prices; an unknown adjustment/currency basis blocks automatic geometric interpretation. Entry stop, base invalidation, chase boundary, target and plan expiry are different fields. “Dropped from board” is a membership event; “invalidated plan” is a management event; “saved item removed” is a user mutation.

Comparison has two useful levels:

- **Published-facts study:** two or three source-bound cards from one existing grid. Show identity, price basis, published entry read, dates, zones, cautions and source links. Missing strategy/horizon is disclosed; no relative-return or winner calculation. This is the concrete workflow present in #9495 theme.js, not current main's newer study implementation.
- **Aligned strategy comparison:** a future owner-backed contract must establish compatible strategy definition, horizon, currency/adjustment basis, decision date and evidence methodology. Paper NFW-0 keeps incompatible earnings/cycle ideas available for separate study rather than scoring them against early leadership. No new aligned-comparison API is claimed.

Current #9495 study selection binds row, grid, details, href, ticker and source stamp; requires two selections to start and permits at most three; switching grids clears the selection. Hidden/withheld/disconnected rows or changed bindings become unusable. Source hydration and auth/tier changes clear unsafe context. Reuse this owner rather than mounting the presenter's optional checkbox as a second independent selection system. Improvements should explain selection loss and preserve harmless filter preferences, never preserve unauthorized content. [R4][R5]

### 5.5 Historical and real-time boundaries

| History surface | What it can support | What it cannot establish |
| --- | --- | --- |
| Board delta / outcome shelf | Dated published membership/verb/reason changes and specified first-surfaced outcome window | Continuous entry eligibility, plan fills or all-time strategy performance |
| Model plan | Original terms, lifecycle, exact episode id and dated management observation | User holdings, broker orders or a new plan for a same-ticker candidate |
| Market Memory link | Recomputed research using currently available history for the security | Exact retained candidate evidence, point-in-time availability or an episode-specific replay |
| Foresight forward grading | Declared 30/60/90-day windows, control arms, pending outcomes, flag-time membership | Validated current stock probability or treating controls as successful directional calls |
| Radar history | Confirmed transitions/fires with history_since, gaps, lockout and separate source clocks | A fire from a first observation or a current event from stale inputs |
| Winner Health analogues | Same-cohort shape/age episode comparison, declared track/history/denominator | Independent-company trials, guaranteed continuation or survivorship-free evidence on every track |
| Pick Lab | Existing forward-accrual fire/grade record and descriptive entry/long-hold scoreboards | A promoted live entry engine; long-hold records are firewalled from entry authority |
| V2 preview | Shadow candidate/context exploration | Released replacement of current Prophet, validated alpha or current production proof |

Any future “as known then” view must retain availability/revision time, membership and identity from that period. Recomputing with today's survivors, revised fundamentals, newly admitted symbols or today's split/currency basis must be labeled reconstructed. Keep withdrawn/delisted/renamed names and missing history explicit. An old record is not a failure merely because its future grading horizon has not matured.

## 6. Satellite product requirements

### Foresight

Preserve theme stages Early, Confirming, Late, Fading and Watching with their technical mapping in receipts; lifecycle color does not represent price direction or invert simply because the locale changes. Separate text-based and annual-fingerprint evidence from measured supply confirmation, retaining reporting count, fiscal year and member-floor status. CONFIRMER-ONLY health means leading signals are dark; downstream confirmation cannot certify a truly early thesis. [F1][F2]

Keep supply/demand/guidance/revision legs, their dates, the entry-ready stop and the global dislocation observation distinct. The current template can treat an absent dislocation object as Closed; design three states—known open, known closed, unavailable—and require a typed producer reason. Resolve action-sounding “buy waits”/“exit clock” copy against the existing display-only contract with the source owner; do not grant new execution authority.

Retain thesis mechanism, confidence category, kill criteria and deterministic monitoring, along with cross-sectional narrative/money ranks and their thin/exclusion rules. Keep forward grading's sample denominators, intervals, multiple-testing/FDR disclosure, control arms, horizons and pending outcomes. Builder success or new JSON alone cannot prove the HTML current because the output order permits mixed vintage. [F1][F2]

### Leader Radar

Preserve confirmed lifecycle beside raw observation, relative-strength highs, recovery and entry evidence. Inputs have three-valued semantics: false, true and missing/stale; a held-out options factor is additionally distinct from missing data. A new name with no prior history does not fire merely because its first classification is interesting. Stale inputs preserve the last confirmed state where available and suppress fresh fires; refires retain the existing 21-session lockout/de-escalation rules. [L1][L2]

The incumbent clock follows SPY; the additive RS/recovery layer uses the majority completed issuer session capped at the incumbent. An issuer ahead of the cap is read at its latest observation at or before the cap, not discarded. This additive clock must not rewrite incumbent as_of/stale. Preserve price/breadth/RS/regime/revision/state-history/build clocks, history_since and missing-session disclosure.

Recovery search uses ticker prefix, sorting exposes correction depth/ticker/time below trend/recent change, and show-all/fewer retains its existing cap behavior. Keep revision-reason, unavailable and history-incomplete states. Real output is leader_radar.v2; the disabled v1 stub and capped uncovered-name lists need explicit handling. [L1][L2]

### Winner Health

The three tiers define alternative winner cohorts, not severity or confidence. Preserve their fixed order and cohort-specific measurement/qualification; the same name can appear with different reads in more than one cohort. Never sum tier counts into a unique-stock total or collapse to the “worst” read. Four wear states are descriptive; Not enough to compare sits outside that progression. [W1][W3]

engine/top_maturation.py owns the winner_health.v2 construction. It consumes frozen cohort-specific thresholds and analogue libraries, delegates underlying shape/episode derivation to engine.top_anatomy, and does not retune thresholds nightly. Its primary forward ledger is keyed to (asof,ticker); widened tiers must not be appended into that same key space without a separately authorized schema change. The currently declared membership window is the basis for recently-qualified retention, not today's threshold alone. An off-band name is retained only when its current readable state is breaking; unreadable or nonbreaking off-band names are dropped, not manufactured into Character changed. [W3]

A row is readable only with total counting checks >0 and evaluated checks ≥ceil(total/2), using the existing engine rule. Preserve checks.evaluated/checks.total. no_read means insufficient evaluable checks, not no close analogue or N<12. A readable wear-state row may have no analogue, and a found analogue may have thin history; those three states remain independent.

Historical match is within the same cohort on shape/age, not a match of company or sector. Show N as episodes. For N<12, preserve the existing thin-record count without rate. Track W includes later delistings; curated long-history tracks carry their survivorship limitation. The loader rejects artifact age >6 calendar days; tape lag >5 sessions is a separate warning. Missing file, JSON read/parse failure, non-object JSON, handled as-of parse failures and handled stale input collapse to wh=None. An impossible date such as 2026-99-01 can raise at date(y,m,d) outside the parsing exception handler and fail the build instead; this is a static source counterexample, not an executed test. The producer already supplies null_state:true and null_reason for its own null contexts. Reuse that reason; differentiated loader-failure copy still requires its own contract. [W1][W2]

### Pick Lab and V2

Preserve all seven Pick Lab tabs and engine drilldown, pending/matured outcomes and methodology. Entry payload says display_only and accrual requirements of at least 25 fires, three months and six distinct fire dates; do not turn that declaration into a claim that a particular book has qualified. Long-hold output uses 126/252-day sector-relative and SPY-excess descriptive rulers and is explicitly firewalled from entry surfaces. Dates copied into a template are not a live “first maturation” forecast. “1D Velocity” names the daily trigger, not the outcome horizon: Family A keeps its 21-trading-day SPY-excess primary ruler and predeclared 10-day secondary ruler. Preserve the full 5/10/21/63-day ladder, resolved denominators and capture/path metrics. Family C uses absolute reversion capture and MFE/MAE, while Book 19 retains inverse/avoid-accuracy meaning; a universal positive-excess verdict would be wrong. AWAITING DATA denotes a structural feed gap, distinct from ACCRUING. Random-name control, universe base rate and timing lift remain separate; no best-looking horizon chosen after outcomes may acquire verdict language. [B1][B2]

Record/accountability additionally distinguishes raw-row N from cluster-unit effective N using entry-date clusters over 21-day windows. Its data is the committed site/factordata/us_audit_scoreboard.json loaded by engine.pick_lab.render._load_audit_scoreboard; Beta/T0 consumes site/factordata/t0_indicator.json. Neither is inferred from the fire-export file. [B1][B2][B4]

The pipeline invokes build_pick_lab after the snapshot-producing live build and shadow build. It enriches/persists snapshots, fires/grades books and writes outputs before rendering. Page navigation cannot trigger this mutation pipeline. V2 remains its separate unlinked shadow board with tolerant artifact readers, without changes to live us_standouts.json or setups.json. [B2][B3][V2]

## 7. Interaction and state contract

All behavior below is a future acceptance requirement unless explicitly identified as existing source behavior. Local selection is not persistence. No navigation, theme/language change, filter, compare or evidence expansion writes a watchlist, holding, alert or model plan.

### 7.1 Controls and transitions

| Control | Preconditions and result | URL / write | Focus, scroll, feedback and recovery |
| --- | --- | --- | --- |
| Global destination / region | F01-admitted route and exact context; show unsupported state if destination lacks that regional capability | Existing navigation only | Preserve back/forward and listing identity. Never relabel cached US rows as another market. |
| Today / Screener / Plans | Existing source mode; unavailable Today falls back to Candidates with reason | Local data-prophet-src, no new query/write | Correct selected semantics and keyboard tablist behavior; retain last valid local preference only if owner supports it. Unrelated navigation clears candidate→Plan return. |
| Grid / Table | Candidates source; same entitled rows | Existing localStorage preference, no saved-object write | Focus remains on toggle; announce view change. Detail/actions remain accessible in table. Layout changes do not select a candidate. |
| Search/filter | Real data loaded or honest preview subset | Local state, no invented share URL | Label which population is searchable. Debounce only expensive rendering; clear restores source order/filter defaults. Empty message offers clear, not “refresh” as a false equivalent. |
| Sort/column choice/resize | Existing StockTable fields and preferences | Existing market-scoped preferences only | aria-sort and equivalent non-drag controls; null last both directions. Resize gesture must not trigger sort. Preserve actual source order as reset. |
| Show more / all / fewer | Known filtered entitled population | Local expansion | Correct full filtered count and shown count. Return after collapse to a visible section control, with reduced-motion behavior. |
| Compare pick | Current usable source-bound card in one grid | Transient existing study owner; no save | Button/checkbox has accessible selected state and company name. At three, explain limit before selection; do not silently add a fourth or drop the first. |
| Compare selected | Two or three still-usable cards | Local study state in #9495, no new comparison endpoint | Focus goes to comparison heading/return control. Cards retain individual clocks and cautions. Return restores original scroll and selection trigger if still valid. |
| Open setup / Sources | Exact current card/detail source and authorized access | Existing detail/inspector owner | Trap focus only while modal; set accessible title, Escape/Close, no hover-only action. Restore origin and scroll. Sources opens its intended section. |
| Previous/Next setup | Current visible entitled ordering within same source | No model mutation | Announce item position and name; do not silently browse hidden premium or unrelated-source rows. |
| View in Plans | Related record exists and exact pv-id can be selected | Existing Plans source + lifecycle selection | Snapshot origin before closing detail, establish return only after target confirmation. Missing/withheld target: “This plan record is not available in this view.” No false success. |
| Return to candidate | Source/auth/DOM target still valid | Existing transient PVSetupReturn owner | Restore candidate, source mode, grid/table where supported, section, dialog scroll and original page position. Invalid binding: explain “The source changed; open the current board.” |
| Stock/Company/Terminal | Valid exact destination and listing context | Existing link or shell handoff | Support modified/new-tab click. Do not place a full-card link over compare/details controls. Terminal closes/releases prior modal according to existing owner. |
| Market Memory | Valid existing ticker link | New-tab current-history research | Label recomputed history and separate-study scope; preserve source setup. Do not promise matched episode evidence. |
| Retry failed read | A known read failed; same authorized source binding still applicable | Same existing read owner | Distinguish retry from re-evaluation. Native daily-brief conflict has no automatic substitute/retry. Keep last safe dated display. |
| Refresh quote | Existing quote owner supports refresh | Quote read only | “Quote updated; entry read unchanged.” No refresh-all authority or copied assessment timestamp. |
| Assessment review | A real assessment owner offers a supported action | No endpoint asserted here | Until supplied, show unavailable capability and source explanation; never implement Paper review buttons as invented API calls. |
| Save / watch / alert | User deliberate action, current entitlement, D23 typed object and mutation contract | Existing D23 owner only | Show exact target/list/condition before mutation. Keep compare selection distinct. Activate alert only when explicitly requested, not when saving a view. |
| Export/share | Existing feature and source/access contract only | No new public URL for protected data | Retain access checks and snapshot/clock labels; never leak withheld rows through export or copied markup. No new export feature is proposed by this specification. |
| Language/theme | Existing shell preference owner | Existing presentation preference only | No changed source interpretation, ranks or colors of lifecycle. Preserve usable focus; labels wrap. Existing detail dismissal on language change must be explicitly tested and restored safely. |
| Pick Lab tab/book drill | Existing local tab or engine id | Local view | Add full keyboard/selected-panel semantics without altering book/history semantics. Respect reduced motion for scrolling. |

### 7.2 Required state copy and recovery

EN copy is a proposed product specification, not a claim that current strings all match. ZH examples are semantic drafts and require the existing language review; do not claim native-speaker approval.

| State | EN / draft ZH | Useful recovery / invariant |
| --- | --- | --- |
| Initial load | “Loading the published board…” / “正在加载已发布的榜单…” | Reserved layout and readable shell; no fake data chart |
| Loaded | “Published board · prices through [date]” / “已发布榜单 · 价格截至[日期]” | Date source-specific; assessed time separately displayed |
| Zero matches | “No candidates match these filters.” / “没有符合这些筛选条件的候选。” | Clear filters; keep source/entitled counts where known |
| Confirmed zero admitted candidates | “No candidates were admitted to this published board.” / “本次发布的榜单没有纳入候选。” | Show admission basis/date; do not infer an entry-readiness verdict |
| Owner-reported zero cleared entries | “No entries cleared in this published board.” / “本次发布的榜单没有已满足入场条件的候选。” | Requires actual owner mapping, evaluated denominator and time; not eligible=0 |
| No current assessment | “Current entry read cannot be verified.” / “当前入场判读无法核验。” | Show missing input/date; research facts still available |
| Date missing | “Assessment date not supplied.” / “来源未提供评估日期。” | No copied quote/signal/build timestamp |
| Quote stale | “Quote is stale; current zone membership is unverified.” / “报价已过时，无法确认当前是否处于区间内。” | Preserve prior dated read, no fabricated revoked status |
| Pagination/filter | “Showing [shown] of [matching] matching records.” / “显示[matching]条匹配记录中的[shown]条。” | Shown rows are not a missing-source count |
| Incomplete payload | “[loaded] of [expected] records loaded.” / “已加载[expected]条记录中的[loaded]条。” | Use expected only when known and entitled; distinguish incomplete transport from pagination |
| Partial evidence | “Some records have unavailable evidence.” / “部分记录的证据暂不可用。” | Explain per-record reason; this is not the producer's partial-entry status |
| Full hydration failure | “Full board could not load. Showing the dated preview.” / “完整榜单加载失败，当前显示带日期的预览。” | Same-source retry when supported; source date retained |
| First use / no history | “No earlier published record is available.” / “暂无更早的已发布记录。” | No invented prior close, return or change arrow |
| Known no plan | “No open same-security model record found.” / “未找到同一证券的未平仓模型记录。” | No plan created; exact candidate relation still unavailable |
| Plan source unreadable | “Plan records could not be read.” / “无法读取计划记录。” | Separate from known none; retry/read owner only |
| History not comparable | “Historical comparison is unavailable for this basis.” / “该口径暂无可比历史。” | State cohort/window/source reason; keep current research |
| Guest | “Sign in to continue with your account.” / “登录后继续使用账户功能。” | Existing auth path and exact safe return; no new session implementation |
| Plan required | “Your current plan does not include this data.” / “当前方案不包含此数据。” | Existing entitlement path; no hidden premium payload in source |
| Session expired | “Your session expired. Sign in to continue.” / “会话已过期，请重新登录后继续。” | Clear protected content/context; preserve only safe navigation and original operation identity |
| Save pending | “Saving to [list]…” / “正在保存到[列表]…” | Disable duplicate submit; read original operation |
| Save confirmed | “Saved to [list].” / “已保存到[列表]。” | Only after acknowledged result/readback with stable object id |
| Save failed, known not applied | “Could not save. Nothing was added.” / “保存失败，未添加内容。” | Offer retry only when known not applied; retain user choices |
| Save uncertain | “We couldn’t confirm whether this was saved.” / “暂时无法确认是否已保存。” | Offer Check the list only through the existing supported membership read/destination. Membership is not a prior-write receipt; absence does not authorize retry. Candidate-episode status needs D23's released contract; no nonfunctional status button. |
| New generation during study | “The board changed. Review the current records before comparing again.” / “榜单已更新，请查看当前记录后重新对比。” | Clear invalid selection; never swap one comparison silently |
| Unsupported regional feature | “This research view is not available for [market].” / “[市场]暂不支持此研究视图。” | Offer existing supported destination; no US-parity fiction |
| Satellite mixed vintage | “Data and page were published at different times.” / “数据与页面发布时间不同。” | Show actual dates only if supplied; otherwise state freshness unknown |

A read-only satellite has no save-pending state unless it actually invokes the shared save owner. Its ordinary navigation is not assigned artificial mutation states. Conversely, the complete D03 save journey cannot be accepted by presenting a static success mockup without the D23 readback contract.

### 7.3 Persistence handoff to D23

D03 supplies domain meaning: exact candidate/source generation, listing identity if proven, visible snapshot dates, intended list, and any explicit condition's source semantics. D23 supplies object identity, authorization, mutation request identity, duplicate handling, operation status and readback. The actual current security-membership implementation is WatchStore in site/watchstore.js, using the shared Supabase client, watchlists and watchlist_symbols. WatchStore.symbols.saveChecked(listId,tickers,opts) normalizes/de-duplicates tickers, serializes per list, checks membership, writes once in its checked path and reads back; ws-save-outcome distinguishes waiting/saved/rejected/uncertain. WatchStore.symbols.inspect validates list ownership and current auth epoch, then reports present/not-confirmed/unavailable with writeRetryAllowed=false. It does not certify the result of an earlier insert; absence cannot justify blind retry. The source notes no unique (watchlist_id,symbol) index, so do not assume server-enforced idempotency. Its local When you saved decision snapshot is not a durable exact Prophet episode. [SAVE]

Reuse this real security-save owner and label the result “security in list” when that is what was saved. The missing contract is cross-session, source-bound investigation/condition persistence, not the existence of all watchlist functionality. No new endpoint, database table, idempotency-key field or polling job is invented here.

The minimum future D23 handoff must answer: what is saved (security, candidate episode, view or condition); whether a historical snapshot is retained; how a renamed listing resolves; whether a later generation is linked rather than replacing history; what counts as duplicate; how a timed-out request is reconciled; how access revocation affects cached content; and how an alert differs from a passive saved item. Until this is released, a source-backed save affordance can navigate to the existing owner or explain unavailability, but cannot assert persistence from localStorage.

## 8. Responsive, accessibility and component contract

### Real shell width is the input

Let available content width be the viewport minus the actual F01 navigation width, page gutters and any persistent inspector plus gap. F01 must publish those values and overlay/scroll ownership; no numeric shell width is frozen by D03. A 1440px artboard with a 1440px standalone content area is not proof of fit inside the real shell.

**Provisional domain sizing proposal for composition testing, not a released F02 token:** rich cards require about 288px usable width for identity, price, small chart and two-column term pairs; use a roughly 16px inter-card gap. Select the number of columns from actual content width and reduce columns before truncating evidence or shrinking controls. Re-test the threshold using long Chinese text and long prices; if it fails, raise the minimum rather than squeeze. A persistent study inspector is allowed only if the remaining board retains its minimum useful card/table width. Otherwise use F01's full-height overlay treatment with explicit return.

| Evaluation viewport | Composition requirement after actual shell deductions |
| --- | --- |
| 320 | One compact rich card at a time; title/price/conditions wrap; primary actions 44px house target; no whole-page horizontal overflow. Evidence and terms are not silently deleted. |
| 390 | Fast vertical scan with identity, published read/availability, small chart, next condition and primary action visible; deliberate expansion exposes secondary facts. Compare by question with pinned identities, not three squeezed columns. |
| 768 | Test drawer navigation, one/two useful card columns and full-height detail. Do not assume portrait tablet can host a persistent inspector. |
| 1024 | Test expanded navigation plus inspector, then compact rail; prove source tabs and first useful candidates remain accessible. |
| 1280 | Test narrow desktop including 400% zoom/reflow equivalent; five-lane action board must collapse or become a scoped section list before labels become cramped. |
| 1440 | Test full shell and content inspector; columns derive from available width. Retain comparison, context and full-card detail. |
| 1600 | Avoid excessively long evidence lines and arbitrary stretched cards; align numerical columns and use extra width for meaningful comparison, not empty decoration. |

On phone, collapse repetitive secondary metadata deliberately, with “More facts” or section navigation. Keep quote/assessment availability, current published read, key condition and source access visible. R8's 390px full-page composition is long; its stacked richness is a reference, not proof of acceptable scanning. Use the final composition to validate shorter scan time without reviving the rejected text-row-only main direction.

### Component roles and source mapping

| Role | Existing source reuse | F01/F02 dependency |
| --- | --- | --- |
| Page frame, global nav, context/search, account/theme/language | Shared-shell owner, existing navigation bridge | Exact slots, widths, route/return and overlay contract |
| Product heading / local navigation | dashboard US region; satellite headings | Shared hierarchy and selected-state patterns; no duplicate global header |
| Opportunity card | #9495 _prophet_opportunity_card.html.j2 + read-only presenter | F02 card/metric/status/spacing; no new score or data join |
| Grid/table toolbar | existing StockTable, source toggle and filter owners | Accessible toggle/select/filter/empty patterns |
| Setup inspector/dialog | existing theme.js and _prophet_setup_detail.html.j2 | F01 focus/scroll/stacking; F02 tabs/disclosure/receipt |
| Price history / condition overlay | source geometry and existing chart owners | Chart axes/units/contrast/text alternatives, reduced motion |
| Lifecycle/count strip | current plan owner and producer totals | Distinguishable count nouns, semantics independent of up/down |
| Compare selection / study | #9495 study functions in theme.js | Selection/limit/return, question-by-question mobile comparison |
| Evidence / source receipt | current source dictionaries and timestamps | Status/availability formatting; expose useful evidence before technical audit details |
| Group action board / sector timing / breadth | current US includes and D02/D05 shared content | Container queries and table/chart patterns; same full destinations |
| Satellite stage / cohort / history | each existing producer/template | Reusable styling without merging different domain meanings |
| Save/watch/uncertain result | D23 | Shared mutation/readback state and consentful activation |

No token values or F02 component IDs are fabricated. Map these roles to the released system during D03.2B. Decorative colored container borders/accent stripes in older references do not carry forward under the current programme doctrine; legitimate focus outlines remain. Up/down market colors and lifecycle/readiness colors are distinct semantics. [A2][A4]

### Accessibility requirements

Use semantic headings/landmarks, real buttons/links, labeled controls, visible focus and non-color status text. Keyboard access must reach every source tab, filter, table sort/column control, compare pick, setup section, source disclosure, plan link and return. Modal focus must be trapped/restored correctly, Escape must dismiss the active layer according to F01, and sticky controls must not cover focus or the final action at zoom.

Important mobile controls use the programme's **44×44 CSS px house target**. WCAG 2.2 AA target-size minimum is **24×24 CSS px** or its applicable spacing/exceptions; 44 is not misrepresented as the AA minimum. At 400% zoom, ordinary content must reflow at 320 CSS px equivalent; necessary two-dimensional table/chart interaction stays scoped to the component, with readable cells and a useful accessible alternative. [WCAG_TARGET][WCAG_REFLOW]

Require WCAG AA contrast checks for text/status/focus and chart marks in light/dark; status must remain understandable in grayscale. Graphs need meaningful labels/units/date/basis and a text/table route to the same decision-relevant information. For small sparklines, expose the observed period and change/shape only when derivable from the actual source; do not invent explanatory statistics.

Honor reduced motion. Do not animate numerical values or reorder the board while the user reads. Use polite, bounded announcements for load/filter/selection state, not every quote tick. Long EN/ZH labels, names, minus signs, missing values, price precision, dates/timezones and currency all need specimens. Fixed-height cards cannot clip Chinese evidence or hide controls. Locale changes do not invert theme lifecycle colors or change financial semantics.

### Performance and loading

Future field targets are LCP ≤2.5s, INP ≤200ms and CLS ≤0.1 at p75, evaluated separately for mobile and desktop. These are proposed acceptance budgets, not measurements in this session. The old #9495 offline loading evidence includes a reported mobile session-strip shift around 0.113; that is a carried item to remeasure, not a current beta performance result. [A2][R1][VITALS]

Keep the public shell and bounded preview readable without waiting for all research modules. Reserve meaningful loading geometry; mount hidden inspectors/charts on demand; reuse one quote subscription and one current source loader, pause appropriate polling while hidden, and release handlers when a view is disposed. Do not eagerly request every satellite or plan detail. Protected data must never be rendered into an anonymous HTML capture as a convenience for performance testing.

## 9. Paper lineage and actual observations

### Assigned file/page map

All links below point to the actual existing PROPHET file. Board IDs are exact observed identifiers; a title is not acceptance evidence.

| Page | Observed boards | Role / decisive references |
| --- | ---: | --- |
| [PROPHET p-1-0][P1] | 19 | Original daily-brief family. DAZ-0 R4.5 desktop visually inspected; E36-0 entry-cleared, EUE-0 health, G9H-0 compare, GJP-0 change log, HY5-0/HY6-0 first failure, I2B-0/I46-0 unknown history remain references. DAY-0 is an empty 100×100 frame, not coverage. |
| [R7/R8 workspace p-C-0][PC] | **31** | Census had 27; four R8 boards added. SYI-0 R7 desktop and YW1-0 R8 desktop plus ZRL-0 R8 phone visually inspected. T8V-0/TZJ-0/V1X-0/YMJ-0 retain earlier dark/phone/320/tablet coverage, not new shell proof. |
| [Rejected text-row p-B-0][PB] | 23 | J58-0 screenshot inspected; K2S-0 direction/review tree read. Retain rejected status and useful interaction lessons without resurrecting the visual direction. |
| [Rich successor p-A-0][PA] | 36 | L3E-0/LPF-0 cards, PCL-0/Q9K-0 full-strategy proposals, NFW-0 compare tree inspected, NMN-0 uncertain save, P8J-0 320 stress, Q1Z-0/Q3W-0/Q5S-0/Q7O-0 decision unavailable. |
| [R6 flagship p-9-0][P9] | 8 | IJW-0 and theme/locale/phone variants; case-for/case-against/history study reference, not approval of the main grid |
| [Quote/assessment reviews p-8-0][P8] | 10 | AN9-1 refreshed quote/unchanged assessment tree read; AU9-1 phone, AZL-1/B5I-1 failures, BAM-1/BMW-1 health, BWF-1/C8Q-0 review, CKY-0/CY9-0 outcomes |
| [Setup/evidence/playbooks p-7-0][P7] | 23 | 8KA-0/8OM-0 setup/evidence, 8XB-0 source return, 93W-0 and 9IF-1 contracts, quote-health family; preserve reference lineage |
| [Source-only p-6-0][P6] | 1 | GR4-0 baseline capture; source evidence, not editable composed reference proof |
| [Shared contracts p-5-0][P5] | 8 | 1-0 shared contract tree read; 5ZG-0 engineering, 7WZ-0 coverage, 5U5-0 degraded, 51Q-0 regional. Explicitly provisional. |
| [Screener p-4-0][P4] | 8 | 2Z0-0 table, 3AI-0/3NO-0 grid, 6RE-0/6Y0-0 mobile, 79J-0 compare, IDX-0 scenario proposal |
| [R2 Today/Setup/Plans p-3-0][P3] | 21 | Today mobile/tablet variants, 2E6-0 no entries, 4DB-0 setup, 4MM-0/4U6-0 plans, I8J-0 history unavailable |

Total assigned-page inventory observed: **11 pages / 188 boards**, including history/specification/source-only/rejected work. It is not a count of approved screens. Inactive-page dimensions sometimes return null; these reads do not establish final geometry.

### What actual screenshot inspection established

- **DAZ-0 original:** strong no-entry restraint, separate clocks, case-for/against, rich queue and source/return contract. The large hero and standalone legacy navigation should not dictate the new shell composition.
- **J58-0 rejected R6:** text-row scan plus persistent study, deliberate compare and evidence concepts. Its rejected direction remains rejected even though the page's historical rationale calls one architecture selected. Source adjudication outranks a self-described selected design.
- **SYI-0 R7:** useful ready/waiting/unjudgeable summary, timing/invalidation columns, compare and passed shelves. The stale-quote “Entry revoked” copy needs correction to a source-backed availability distinction. Table-only scanning is not sufficient authority to discard rich cards.
- **YW1-0 R8:** rich cards with price/chart/entry zone/invalidation, source access, market context, theme action map, sector timing, Turn Setups unavailable and research exits. “Entry unverified” is semantically stronger for stale quote absence. It still uses standalone older global chrome and illustrative data.
- **ZRL-0 R8 mobile:** real stacked mobile hierarchy observed at 390×5210. It preserves information but remains long. A screenshot cannot prove touch, focus, comparison, save or real shell fit.

R8 1092-0 (390 dark ZH) exists in the observed page inventory and in #9495's committed artifact set. It was not independently screenshot-inspected in this session. **ZE5-0 dark desktop remains held** under original operation prophet-r8-20261103-desktop-dark-colors-200. No edit/retry was made.

Paper returned snapshot guard 41dd4fd9efb0e77d78ab067f381684e592972c986b9b79a1c36ab68b30e72970 and token hash 640746f9 during relevant reads. These are drift diagnostics, **not immutable document revisions or approvals**. The direct catalog was accepted_for_write at observation with TOOL_SCOPED_CONTRACT_V1; that technical state does not grant an overlapping edit or settle P00/F01/F02/owner conditions. No Paper mutation was requested or performed by D03.

### Composition packet for the next admitted phase

Do not create another visual direction in parallel with the original #9495 owner. Once the joint foundation release is verified and exact effect scope reconciled, qualify reuse of the rich-card successor/R8 lineage against this ledger, then compose in the actual F01 slots.

The future editable set must cover: full US normal-data workspace; scan→compare two→setup/Sources→related Plan→return; empty/unjudgeable recovery; divergent clocks and actual invalidation; save pending/confirmed/failed/uncertain; phone compact scan and question-by-question comparison; tablet/narrow desktop with inspector; light/dark and EN/ZH; satellite stage/cohort/history distinctions. Reuse unchanged genuinely approved reference areas only when their approval receipt is found. Screen counts or old locale variants do not substitute for affected composition evidence.

Prepare a **00 · Read me & Build contract** page in the admitted existing file/organization, with the following text and links once target scope is qualified:

> D03 helps a user scan US research candidates, compare published facts, inspect evidence and conditions, and revisit without confusing quotes, assessments and plans. The current source specification is this D03 document on #10617. Candidate lineage: original p-1-0; rich successor p-A-0; rejected p-B-0; R7/R8 p-C-0. No new canonical reference is approved. Shell/system versions must cite the actual joint F01/F02 release. Known missing interfaces: assessment time, exact candidate-plan relation, stable save identity and D23 persistence. Full user journey and exceptional-state obligations are §§1,5,7–8. RIG state draft; original held effects and release exclusion remain controlling.

Add concise annotations adjacent to comparison, dates, plan relation, save and return controls. This text is **prepared in source, not applied in Paper**. F03's “20 Markets / MM · US Equities & Prophet” remains proposed placement; no files/pages were moved or archived by this assignment.

## 10. Evidence ledger and limits

| Evidence ID | Actual work and result | Limit |
| --- | --- | --- |
| E01 | Read all five user-linked commissioning documents at 6e186… plus organization/route ownership; scoped six D03 rows | Later foundation inputs separately versioned; no whole-estate census repeated |
| E02 | Verified current protected Mastermind procedure pin and loaded applicable bootstrap/execution/reliability/continuity/Paper/closeout law | Source law, not evidence of company implementation |
| E03 | Opened real beta /us_stocks.html in the permitted browser. Observed shared navigation, US market context, company search, account/theme/EN controls, exact Terminal return URL and “Opening your workspace” | Full body not loaded in first snapshot; subsequent DOM read timed out at 3000ms Runtime.evaluate, then bounded screenshot alternative timed out at 10000ms Emulation.setFocusEmulationEnabled. No authenticated journey proved, no alternate browser bypass. |
| E04 | Public www /us_stocks.html was independently readable: dated board, market context, action lanes, source tabs and dated-preview load-failure copy | Separate public baseline, not beta, protected payload or release equivalence. [PUBLIC] |
| E05 | Read source templates/builders for all six routes, common table/quote/source/plan logic and #9495 adapters/return/study implementation | Read-only inspection; builders were not executed and no source behavior was represented as a browser pass |
| E06 | Retrieved and inspected actual us_standouts source bytes at main pin, including counts, publication ids, clocks and a missing-clock row | Historical immutable artifact observation, not current live signal or user advice |
| E07 | Read all eleven assigned Paper page inventories; inspected five native screenshots and selected direction/compare/quote/shared trees | Source-only/rejected/illustrative references stay qualified as such; no after-candidate freeze |
| E08 | Reconciled #9495 head drift and read its current research, MP-1 inherited conditions and evidence manifest | Manifest reports anonymous offline site_dir with no resolved Git SHA; not signed-in beta proof [R7][MP1] |
| E09 | Read current F01 #10645 and F02 #10630 returns; both Draft and no released joint contract | No inference that either owner is idle or unassigned |
| E10 | Two bounded native semantic consultations: satellite source review and counterexample critique | Author-side advisory reasoning, not formal first-pass product/taste/RIG review |
| E11 | Persisted first checkpoint on existing programme branch with exact readback | Final commit/readback supersedes checkpoint's IN_PROGRESS content |
| E12 | Completed document consistency validation: ledger counts, route rows, reference definitions, source pins and forbidden acceptance inflation | Artifact consistency only, not production tests |

### Existing #9495 evidence remains separate

Its current research reports three R8 native boards and an anonymous offline verification set. The inspected canonical-final manifest is mastermind.p0_evidence.v2; generated_at 2026-11-03T05:09:59Z; access=anonymous; 16 states attempted/captured across us_stocks.html and chat.html, desktop 1440×900 and phone 390×844, light/dark, EN/ZH. The target is a local site_dir, timing_basis=lab, resolved_sha_or_none=null. This session inspected that manifest; it did not independently rerun the captures. [R7]

The #9495 source reports full-build and public/protected pair hashes, public/protected row counts and a remaining mobile shift. Those reports must be validated at the eventual exact implementation head. They do not establish accepted new visual direction, eligible operator release, loaded beta behavior or protected Sources→Plan→return success. The full plan index fetch failure in this session also means no fresh G-D-1 availability denominator was remeasured. Keep that inherited gate open rather than inherit an older “MET” measurement.

## 11. Future implementation guidance

**Implementation is not authorized in this phase.** This section is a builder contract for a later commissioned implementation.

### Source boundaries

| Area | Intended source treatment | Owner / safeguard |
| --- | --- | --- |
| Shared dashboard | Coordinate common integration through D02; change only mode stocks / body.page-stocks composition | Render Macro and non-US consumers to prove no unintended regression; no unscoped global CSS |
| Rich opportunity anatomy | Reuse #9495 read-only presenter and card/setup templates when its original owner/effects are reconciled | No new rank/quote/plan engine; do not cherry-pick around an unresolved effect |
| US hierarchy | Existing _regime_read_panel, _sector_prophet_context, _us_act_now_board, _us_board_cards and Prophet workspace/page styles | Preserve group/sector/plan/count boundaries and data split |
| Setup/compare/return | Existing site/theme.js, PVSetupReturn, USProphetSource, USProphetLife and #9495 study owner | One transient selection/return context; no second store or competing checkbox workflow |
| Screener/table | site/stocktable.js and current template data island | Preserve preference keys, null-last sort, row order, exact link/Terminal bridge and actions |
| Source/gate hydration | build_site split/write helpers, existing private loader and app/prophet_daily_brief.py | Source hash/pair/receipt admission, auth response generations, no stale native carryover |
| Plan view | Existing build_prophet, _prophet_card/_prophet_receipts and plan presenter | Original terms vs management clocks; exact plan ids; no ownership joins from ticker alone |
| Foresight/Radar/Health | Each existing template and producer/loader | Presentation reuse only; typed missing reasons/version coherence need explicit owner changes |
| Pick Lab/V2 | Existing render/build pipeline and lifecycle metadata | Do not run on user request/navigation; no promotion to live/SEO |
| Shared saved research | D23 existing implementation | Real readback and uncertain-operation reconciliation before success UI |
| Route/organization | Existing registry/exporter and F03 | No separate route catalogue or unilateral archive/move |

### Ordered implementation-entry sequence

1. **Foundation intake:** consume exact F01/F02 jointly released versions, geometry, tokens and stress-test artifacts; map the component roles above. Preserve current source pins as historical input; refresh only changed relevant files.
2. **Original-owner reconciliation:** #9495's owner/canonical operator resolves the exact Fabric/Paper effects through their original carriers. A successor must be lawfully assigned if no live receiver exists; historical authorship alone is not a handoff. Never replay EFFECT_UNKNOWN.
3. **Reference composition:** D03 uses the qualified existing Paper lineage, applies actual shell widths and completes annotated normal/degraded journeys. Do not change the source ranking, held effects or access boundaries to make examples easier.
4. **Reference freeze and review:** commit the supported native exports/captures, annotations and verification screenshots with file/page/board IDs, time and required hashes as one immutable artifact set. Obtain real product-regression and visual/taste first-pass findings on the closed input set, then disclose rationale and fix/review affected evidence.
5. **Future authorized build:** only after reference acceptance and a new implementation commission, adapt composition and data adapters through existing owners. Keep public/protected publication paired and compare/return logic singular.
6. **Validation:** run existing relevant unit/render/access tests plus the counterexamples below; prove the full journey using an eligible signed-in real path. Neither screenshots nor source checks replace that proof.
7. **Release/rollback:** use the already authorized release owner/process only if later commissioned. Design acceptance, code merge, deployment and served proof remain separate facts.

### Compatibility, migration and rollback

Preserve route identities and admitted query/hash bytes, semantic field definitions, source generations, table preference namespace and population boundaries. Any preference schema change needs a versioned read/normalize path and safe default; it must not erase saved objects or create a new persistence owner. Existing plan lifecycle query behavior needs explicit test coverage during shell integration.

Publish the HTML, protected payload and binding metadata as a coherent generation. Rollback must restore the exact matched prior set and auth/route compatibility, not only CSS. Clear invalid transient state on generation/auth change; never serve old protected rows under a new session. Preserve immutable history and original save-operation identity through rollback. Retain the previous accepted reference and its conditions; a design rollback cannot itself roll back producer facts.

For the satellites, a render failure must be distinguishable from successfully emitted data. A future producer/loader improvement may add typed availability and generation receipts, but this document does not invent existing fields. Until then, render qualified “freshness not established” behavior rather than compare unrelated timestamps as though atomic.

## 12. Acceptance cases and verification plan

These are **specified tests, not executed passes**. Existing test names are observed in #9495's changed-file list and should be inspected/refreshed by its owner before use: test_prophet_opportunity_presentation.py; test_prophet_opportunity_card.py; test_prophet_opportunity_integration.py; test_prophet_plan_presentation.py; test_prophet_candidate_plan_return.py; test_prophet_setup_list_navigation.py; test_prophet_setup_sections.py; test_prophet_table_opportunity_parity.py; test_prophet_memory_handoff.py; test_us_board_gate.py; test_us_board_hydration_merge.py; test_prophet_page_composition.py; test_dashboard_template_render.py. Names alone are not test results. [PR9495]

| Test ID | Discriminating case | Required observable result |
| --- | --- | --- |
| T01 | All six canonical routes / lab variants | Correct route, lifecycle, source, region and audience; no V2 promotion or private Lab conflation |
| T02 | Current shared dashboard renders Macro and US | US changes stay scoped; unchanged non-US/ Macro behavior preserved or separately approved |
| T03 | Today absent, candidate artifact absent, plan book absent/corrupt | Correct independent fallbacks; absent vs error not conflated |
| T04 | ?life=valid, invalid, legacy #life=, both present, unrelated fragment | Preserve query precedence and actual compatibility; no silent unrelated anchor regression |
| T05 | Source toggle while table mode / detail return pending | Table only for Candidates; unrelated navigation clears return safely |
| T06 | Filter zero, zero admitted, owner-reported zero cleared, partial preview, pagination and unknown total | Distinct populations/messages; no readiness aggregate from eligible/Featured/plan-ready. Payload incompleteness, evidence absence and shown-page count never conflated. |
| T07 | Null, zero, negative, NaN/Infinity, long number, equal sort keys | Zero retained for valid counts/metrics; nonpositive US equity price/level is not usable geometry without valid domain basis. Null last both directions; stable source order. |
| T08 | Column resize zero movement / drag / keyboard | Resize does not sort; equivalent accessible non-drag control; preference state sane at mobile |
| T09 | Two candidates, third, attempted fourth, deselect to one | Compare enabled only at two or three; explicit limit; no silent replacement |
| T10 | Same ticker in two occurrences/generations/strategies | Distinct source objects, no aliasing by ticker; compatible identity required for persistence |
| T11 | Sort/filter after selection | No unintended change of selected object; hidden/unreachable/withheld selection follows one documented safe owner rule |
| T12 | Source changes while comparison/detail is open | Announce changed board, invalidate unsafe context; no mixed-generation comparator |
| T13 | Fresh quote + stale/undated assessment | Quote timestamp updates alone; current readiness not renewed |
| T14 | Stale quote + prior Buy label | Historical published label remains attributable; no current zone claim or fabricated revocation |
| T15 | Required evidence absent vs optional abstention vs producer Buy-partial | Unjudgeable, partial evidence, partial payload and partial entry status stay distinct; no zero substitution/reweight in UI |
| T16 | Negative daily move with source entry open; positive move with source wait | Market color never becomes entry status |
| T17 | Equal price to threshold; intraday breach vs close condition | Apply only known comparator/observation rule; no client-created invalidation |
| T18 | Split, currency mismatch, adjustment unknown, out-of-order quote | No false geometric crossing or historical rewrite; disclose unsupported basis |
| T19 | Holiday/weekend, mixed-vintage panel, one member newer | Producer session policy/majority basis retained; newest member does not certify board |
| T20 | Forming overlay stale before close and local clock passes close | No stale-to-confident closed transition; close-pass and owner status respected |
| T21 | Score zero/null, family absent, unknown definition, inert family | Correct definition, no probability claim, no fake evidence contribution |
| T22 | Candidate terms missing vs plan terms present for same ticker | Do not borrow plan targets/horizon or assert exact relation |
| T23 | management_asof absent, last_price_asof after management, inconsistent frame | Withhold incoherent management observation; original terms remain visible |
| T24 | Sources → exact plan → return with valid source | Same candidate, section, view, focus and scroll; actual signed-in proof required |
| T25 | Plan target missing/withheld, source removed, auth changed mid-return | No success receipt; safe current-board recovery and no protected leakage |
| T26 | Company/Terminal/Memory modified clicks and new tab | Exact routes/return bytes; Memory labeled separate recomputed research |
| T27 | Save pending timeout, auth expiry, duplicate click, unknown result | Original D23 operation retained; no false failure/success or blind retry |
| T28 | Save confirmed versus passive watch versus activated alert | Distinct actions/object result; navigation alone does not mutate |
| T29 | API unknown/repeated/malformed pins, unauthenticated request | Auth before owner read; 400/401/403 private response as appropriate; no path override |
| T30 | API stale source/selection binding or candidate-generation mismatch | Correct 409 vs 503, no substitute generation or automatic refresh |
| T31 | Delayed response after logout/account/tier/source change | Reject stale response and erase protected native context; preserve safe public preview |
| T32 | Public HTML, page source, direct protected JSON and cached return | Same entitlement boundary by all channels; required independent paid-boundary review |
| T33 | Historical view with revised data/current membership | Reconstructed label or true historical availability evidence; no point-in-time claim by default |
| T34 | Pending history outcome / no prior record / delisting | No failed grade for pending; no fabricated history; retained identity/lifecycle |
| T35 | Foresight missing dislocation vs explicitly closed | Unavailable distinct from known negative; typed reason gap remains visible |
| T36 | Foresight confirmer-only and below-floor fingerprint | No early promotion; provisional/member qualifier remains |
| T37 | Foresight control arm, pending 90-day result, changed membership | Controls/pending/flag-time membership remain correctly defined |
| T38 | Foresight/Radar/Lab new JSON, failed HTML render | Mixed vintage detected/documented; exit zero is not proof of current page |
| T39 | Radar first observation, stale previous state and refire lockout | No manufactured fire; frozen state/reason and existing lockout retained |
| T40 | Radar SPY/majority issuer clock divergence and ahead issuer | Additive cap correct; ahead issuer read at/before cap, incumbent unchanged |
| T41 | Radar held-out vs false vs missing factor; >50 uncovered names | Distinct semantics and true coverage denominator |
| T42 | Winner overlapping tiers; off-band unreadable or nonbreaking | Separate cohort reads; no summed unique/worst state, no manufactured retained Character changed row |
| T43 | Winner unreadable/empty/healthy/no-read, no analogue, thin analogue, stale tape, age six/seven and impossible date | Keep readability/analogue/null states separate; age >6 rejects, >5-session tape warns independently. Impossible date static failure gets a real producer test before any warm-state claim. |
| T44 | Winner analogue N=11 vs 12 and W vs curated track | Existing thin threshold and track-specific history disclosure |
| T45 | Pick Lab AWAITING DATA vs ACCRUING, 1D trigger/21d ruler, Family C, inverse Book19, horizon ladder and long-hold | Preserve predeclared per-family rulers/controls, raw vs cluster-effective N and pending/resolved denominators; no best-horizon selection or live-entry promotion |
| T46 | V2 error/missing inputs/valid shadow | Honest shadow availability; live board/files unchanged |
| T47 | Keyboard-only full primary journey | Visible focus, ordered tab traversal, modal trapping/return, complete action access |
| T48 | 320/390 touch, long ZH, long prices, light/dark | Meaningful scan, no clipping/whole-page overflow, 44px important targets |
| T49 | 768/1024 expanded nav + inspector; 1280 at 400% | Real content-width fit, scoped table/chart scroll, unobscured controls |
| T50 | Reduced motion and frequent quote/source updates | No distracting reorder/animation or announcement flood; usable stability |
| T51 | Prior preference version and back/forward deep link | Safe defaults, actual route semantics and restoration; no saved-object mutation |
| T52 | Public/protected paired release and rollback | Exact coherent generation, source binding and entitlement; no mixed old/new rows |
| T53 | Future authorized P-MP1-DENSE Grid/Table across all seven lifecycle filters and multi-episode ticker | Same complete canonical plan-id population; candidate StockTable separate; no arbitrary cap without genuine full-table escape path |

Tests T24, T27–T32 and T47–T50 require real runtime evidence under the eventual exact head; they cannot pass from these source reads. Test fixtures should expose the listed failure mode rather than mirror implementation internals.

## 13. Inherited conditions, review and acceptance

### Accepted predecessor rules retained

The actual C8 verdict is REVISE at its own reference identity, not approval of this D03 candidate. Its b8 Overtime question is **CLOSED BY CITATION**: plan_clock_date(), not retired age_days, is authoritative; do not reopen that resolved question. Its b1 display stance uses entry_status, else board_read.fields.status, discloses stance_basis, and shows No read only when both are absent; do not replace that accepted plan display rule with the candidate presenter's different adapter. Its n1 ruling preserves the canonical seven-cell lifecycle/count grammar. [RIGV]

MP-1's later P0 amendment delivers distinct Candidates and Plans and makes the dense follow-up **PLANS ONLY**. Candidate StockTable needs a density audit, not reconstruction. **P-MP1-DENSE OWED:** a real plan-book table must show the same canonical plan identities as Grid under every lifecycle filter, distinguish plan IDs from tickers/multiple episodes, and expose the complete active population. The arbitrary 40-card cap stays retired; the specifically contemplated lifecycle-aware dense Grid requires the full table escape path first. Neither B1 closure nor P-LAB-UI completion closes this obligation; its existing separate Sol review/commission boundary remains. [MP1]

### Continuity dispositions

No predecessor condition is silently resolved, overridden or superseded by this specification.

| Condition / source | Disposition | Concrete closure evidence / owner |
| --- | --- | --- |
| Rejected enlarged legacy-card and R6 text-row directions [R1][PB] | CARRIED_BLOCK against revival as accepted direction | D03/original Prophet owner must qualify a materially improved rich-card composition through actual review; naming is insufficient |
| RIG predecessor MP-1/R4 composition conditions [MP1] | CARRIED_BLOCK for applicable unresolved conditions | Existing reference-integrity receipts and current remeasurement, not self-certification |
| MP-1 G-D-1 current availability | CARRIED_BLOCK | Remeasure current nightly board_read/entry availability using adjudicated Reading A and actual exclusions. Old 2026-08 “MET” is not new proof. |
| MP-1 paid-boundary / independent adversarial review | CARRIED_BLOCK | Named eligible reviewer on exact split/payload diff; same anonymous/Free/paid reachability by every channel |
| MP-1 C8-B reference repair / C8-D completion and separately owned C8-C token change | CARRIED_BLOCK where applicable | Locate actual later dispositions; shared token retune needs its own non-US parity or separately accepted diff. Do not silently make shell depend on it. |
| P-MP1-DENSE plan-book table / Grid parity | CARRIED_BLOCK — OWED unless a later reviewed closure is produced | Existing separate Sol review/commission; full plan IDs under lifecycle filters, complete table population and no arbitrary cap. Candidates table is not the missing Plans table. |
| Fabric prophet-page-revamp-20261102-ux-refinement EFFECT_UNKNOWN, retry denied [R1] | CARRIED_BLOCK | Original-carrier reconciliation of exact operation; do not redispatch or overlap page/assistant/Turn Setups changes |
| Paper prophet-r8-20261103-desktop-dark-colors-200 on ZE5-0 [R1] | CARRIED_BLOCK | Original-carrier effect reconciliation and readback; no palette retry or replacement board to evade hold |
| Signed-in eligible Sources → Plan → same-candidate/focus/scroll [R1] | CARRIED_BLOCK | Actual eligible authenticated execution at exact implementation head, including negative cases |
| Connected mastermindx-2 excluded from protected release [release ruling][RELEASE] | CARRIED_BLOCK / unchanged authority | Preserve original eligible release-owner path if separately commissioned. No release action requested here. |
| F01/F02 joint v1 absent [F01PR][F02] | CARRIED_BLOCK | Exact jointly released version, actual widths/slots/tokens and reviewed stress-test artifacts |
| Original related carriers #9369 / #9294 / #9272 [PR9369][PR9294][PR9272] | CARRIED_BLOCK for adoption/release; all observed open Draft, unmerged | Preserve each original review/effect/CI path. #9369 native batch read head 858e11a4d17f2d9387af720d01c6d84dcc80b49d; #9294 study head a11fe5028a1a8130ab3d15ea624efd22b187b283; #9272 WatchStore head d220b76f6ebb1eb54ec401347c74f36d4b911b0b. Security Save is membership, not original Prophet episode preservation; lost-response duplicate risk remains noted by its owner. |
| Candidate assessment clock / exact plan relation / save identity [R2][R3] | CARRIED_BLOCK | Real producer/resolver/D23 interfaces, not illustrative values |
| #9495 reported mobile shift and remaining source/runtime proof [R1][R7] | CARRIED_BLOCK | Recheck actual accepted head and real signed-in route; offline anonymous captures remain supporting evidence only |

The actual C8 verdict and product-regression receipt were read at the #9495 pin; the expected approval.yml path returned 404. That absence is not proof that no later receipt exists elsewhere, so acceptance continuity must locate any subsequent authoritative disposition rather than infer one. C8-A's amendment text is present; this document does not undo it or reopen b8. The remaining checks carry their original scope, and C8-C does not gate the shell.

The MP-1 packet contains dated accepted technical conditions and subsequent amendments. It is an inherited source, not permission to commission this new design. Existing accepted compact work at 296f3b58c47b1c465c71a33b15a61dd17522fc7d is retained as historical evidence; it does not automatically approve #9495's current head or a future shared-shell composition. [R1][MP1]

### Required independent review sequence

No formal D03 product-regression or visual/taste first-pass review was commissioned because there is no final shell-composed after candidate. The native reasoning consultations informed this specification and are explicitly author-side advisory work.

When the candidate exists, provide only: user/business job, production-before artifact, proposed-after artifact and capability/task manifest for first pass. Freeze separate product-regression and visual/taste findings before revealing rationale, source limitations and constraints. Then record amendments/remediation, regenerate affected immutable exports and use the actual RIG mechanism and admitted reviewers. Full review applies to this material hierarchy/canonical-reference change; the author cannot self-approve it. CARRIED_BLOCK cannot coexist with approved. [A2][A5]

### Acceptance projection

| Re-audit gate | Current state | What remains |
| --- | --- | --- |
| Source and scope | Phase 2A evidence complete with explicit browser/source-read limits | Loaded beta body and exact served release identity |
| Capability retention | 78 bounded ledger rows specified; zero removals/relocations | Independent regression review against final candidate |
| Primary task | Normal and degraded journeys fully specified | Interactive composed/reachable proof, including save contract |
| Shell integration | Blocked by named dependency | Verified joint F01/F02 v1 and real content widths |
| Interaction truth | Source-backed contract and tests complete | Real keyboard/touch/return/auth/save execution |
| Data/backend | Actual owners and gaps mapped | Typed missing interfaces and exact current availability measurements |
| Responsive/access | Complete requirements/evaluation matrix | Actual new shell-composed variants, contrast/focus/400% evidence |
| Builder feasibility | Exact sources, sequence, compatibility and rollback specified | Later implementation commission after reference approval |
| Reference review | draft; no approved new D03 reference | Immutable after freeze and real independent RIG receipts |
| Organization | Existing IDs preserved; no new placement applied | F03 reconciliation and admitted in-Paper Read me/annotations |

### Author-side correction record

The bounded semantic checks found and repaired: admission versus entry readiness; finite versus positive-price validation; pagination versus partial payload/evidence; actionable uncertain-save recovery; the meaning of 1D Velocity; Winner Health's actual link destination, strict >6-day cutoff, impossible-date failure, readability/analogue/null distinctions and off-band admission; separate Foresight HTML/JSON contexts; Pick Lab's additional inputs/rulers. Root verification also retained the owed plan-book dense view and the already-closed b8 clock ruling. These corrections improve the specification; they are not formal reference review or executed production tests.

### Exact next action and return point

**Primary continuation:** when F01 #10645 and F02 #10630 publish their verified joint v1, the existing assigned D03/Prophet owner consumes that exact release plus this source specification, verifies #9495's current writer and original effect state, and qualifies the rich-card lineage for editable shell composition. The ZE5-0 and Fabric effect scopes remain frozen until original-carrier reconciliation; a new session or carrier cannot inherit custody by reading this document.

Independent owner work can resolve the real assessment-clock, candidate-plan and D23 saved-object contracts, and typed satellite availability reasons. That work must stay within its authorized owner/source and does not require a competing D03 design session. QA01 consumes the later frozen composition and actual receipts for re-audit before implementation.

**Do not redo:** the immutable commission read; invent a second Prophet engine; restore rejected R6 as approved; count old Paper variants as new shell proof; change public/protected population; infer current entry from quote/score/momentum; replay either uncertain effect; overwrite shared return ledger wholesale; merge/un-draft/Ready/enqueue/relabel/deploy from this return.

**Capability delta:** before, D03's lineage, route/producer boundaries and temporal gaps were dispersed across the audit, current main, Paper and held #9495. After, one source-bound D03 contract explains the complete retained product and future implementation/test obligations, with concrete gaps and preserved conditions. This is a documentation/research outcome. Full D03 mission and production proof remain incomplete.

Finalization at this boundary: ALL_SCOPED_LANES_BLOCKED for the remaining composition/acceptance actions after completed Phase 2A source work. Blocking evidence is the current F01/F02 unreleased status, original held effects and the documented real-browser read failure; it is not an invented file-wide Paper lock or a claim of absent general tools. No background job, watcher or autonomous wake is claimed.

## 14. Immutable source references

The following links bind factual statements to inspected sources. Branch/PR links identify current carriers; source-file links identify immutable content. Later branch drift must be reconciled without rewriting this observation into a claim about a newer release.

[A1]: https://github.com/mastermindx-market-intelligence/macro/blob/6e1862867193ec6486a22001a0e4fb515da20448/research/design_candidates/production_design_20261102/handoffs/D03-us-prophet.md
[A2]: https://github.com/mastermindx-market-intelligence/macro/blob/6e1862867193ec6486a22001a0e4fb515da20448/research/design_candidates/production_design_20261102/COMMON_SESSION_BRIEF.md
[A3]: https://github.com/mastermindx-market-intelligence/macro/blob/6e1862867193ec6486a22001a0e4fb515da20448/research/design_candidates/production_design_20261102/SESSION_INDEX.md
[A4]: https://github.com/mastermindx-market-intelligence/macro/blob/6e1862867193ec6486a22001a0e4fb515da20448/research/design_candidates/production_design_20261102/SHARED_SHELL_CONTRACT.md
[A5]: https://github.com/mastermindx-market-intelligence/macro/blob/6e1862867193ec6486a22001a0e4fb515da20448/research/design_candidates/production_design_20261102/RE_AUDIT_CHECKLIST.md
[A6]: https://github.com/mastermindx-market-intelligence/macro/blob/6e1862867193ec6486a22001a0e4fb515da20448/research/design_candidates/production_design_20261102/census/route-ownership.json
[LAW]: https://github.com/mastermindx-market-intelligence/Mastermind/blob/b2326bbe30e9988d26199f5e774a482b9c09068a/docs/sol_skills/INDEX.md
[PR10617]: https://github.com/mastermindx-market-intelligence/macro/pull/10617
[PR9495]: https://github.com/mastermindx-market-intelligence/macro/pull/9495
[F01PR]: https://github.com/mastermindx-market-intelligence/macro/pull/10645
[F02]: https://github.com/mastermindx-market-intelligence/macro/pull/10630
[RELEASE]: https://github.com/mastermindx-market-intelligence/macro/pull/9495#issuecomment-6577632524
[M1]: https://github.com/mastermindx-market-intelligence/macro/blob/fc85b0428cf8b0ca4f2fbbc5a415b2871f15a1c9/templates/dashboard.html.j2
[M2]: https://github.com/mastermindx-market-intelligence/macro/blob/fc85b0428cf8b0ca4f2fbbc5a415b2871f15a1c9/scripts/build_site.py
[M3]: https://github.com/mastermindx-market-intelligence/macro/blob/fc85b0428cf8b0ca4f2fbbc5a415b2871f15a1c9/engine/us_board_rank.py
[M4]: https://github.com/mastermindx-market-intelligence/macro/blob/fc85b0428cf8b0ca4f2fbbc5a415b2871f15a1c9/site/stocktable.js
[M5]: https://github.com/mastermindx-market-intelligence/macro/blob/fc85b0428cf8b0ca4f2fbbc5a415b2871f15a1c9/app/prophet_daily_brief.py
[M6]: https://github.com/mastermindx-market-intelligence/macro/blob/fc85b0428cf8b0ca4f2fbbc5a415b2871f15a1c9/scripts/build_stock_library.py
[M7]: https://github.com/mastermindx-market-intelligence/macro/blob/fc85b0428cf8b0ca4f2fbbc5a415b2871f15a1c9/scripts/build_prophet.py
[DATA]: https://github.com/mastermindx-market-intelligence/macro/blob/fc85b0428cf8b0ca4f2fbbc5a415b2871f15a1c9/site/factordata/us_standouts.json
[ACCESS]: https://github.com/mastermindx-market-intelligence/macro/blob/fc85b0428cf8b0ca4f2fbbc5a415b2871f15a1c9/config/site_access.yml
[R1]: https://github.com/mastermindx-market-intelligence/macro/blob/128ab198769a5cc2bd180d7f8eeae07924238d32/research/PROPHET_PRODUCT_IMPLEMENTATION_20261015.md
[R2]: https://github.com/mastermindx-market-intelligence/macro/blob/128ab198769a5cc2bd180d7f8eeae07924238d32/engine/prophet_opportunity_presentation.py
[R3]: https://github.com/mastermindx-market-intelligence/macro/blob/128ab198769a5cc2bd180d7f8eeae07924238d32/templates/_prophet_setup_detail.html.j2
[R4]: https://github.com/mastermindx-market-intelligence/macro/blob/128ab198769a5cc2bd180d7f8eeae07924238d32/templates/dashboard.html.j2
[R5]: https://github.com/mastermindx-market-intelligence/macro/blob/128ab198769a5cc2bd180d7f8eeae07924238d32/site/theme.js
[R6]: https://github.com/mastermindx-market-intelligence/macro/blob/128ab198769a5cc2bd180d7f8eeae07924238d32/engine/prophet_plan_presentation.py
[RIGV]: https://github.com/mastermindx-market-intelligence/macro/blob/128ab198769a5cc2bd180d7f8eeae07924238d32/research/reference_integrity/prophet-board-5514-r4-composition/verdict.yml
[SAVE]: https://github.com/mastermindx-market-intelligence/macro/blob/fc85b0428cf8b0ca4f2fbbc5a415b2871f15a1c9/site/watchstore.js
[PR9369]: https://github.com/mastermindx-market-intelligence/macro/pull/9369
[PR9294]: https://github.com/mastermindx-market-intelligence/macro/pull/9294
[PR9272]: https://github.com/mastermindx-market-intelligence/macro/pull/9272
[R7]: https://github.com/mastermindx-market-intelligence/macro/blob/128ab198769a5cc2bd180d7f8eeae07924238d32/mockups/evidence/prophet-opportunity-workspace/full-page-20261103/canonical-final/manifest.json
[MP1]: https://github.com/mastermindx-market-intelligence/macro/blob/128ab198769a5cc2bd180d7f8eeae07924238d32/research/migration_packets/MP-1-prophet-board.md
[F1]: https://github.com/mastermindx-market-intelligence/macro/blob/fc85b0428cf8b0ca4f2fbbc5a415b2871f15a1c9/templates/foresight.html.j2
[F2]: https://github.com/mastermindx-market-intelligence/macro/blob/fc85b0428cf8b0ca4f2fbbc5a415b2871f15a1c9/scripts/build_foresight.py
[L1]: https://github.com/mastermindx-market-intelligence/macro/blob/fc85b0428cf8b0ca4f2fbbc5a415b2871f15a1c9/templates/leader_radar.html.j2
[L2]: https://github.com/mastermindx-market-intelligence/macro/blob/fc85b0428cf8b0ca4f2fbbc5a415b2871f15a1c9/scripts/build_leader_radar.py
[W1]: https://github.com/mastermindx-market-intelligence/macro/blob/fc85b0428cf8b0ca4f2fbbc5a415b2871f15a1c9/templates/winner_health.html.j2
[W2]: https://github.com/mastermindx-market-intelligence/macro/blob/fc85b0428cf8b0ca4f2fbbc5a415b2871f15a1c9/scripts/build_winner_health_page.py
[W3]: https://github.com/mastermindx-market-intelligence/macro/blob/fc85b0428cf8b0ca4f2fbbc5a415b2871f15a1c9/engine/top_maturation.py
[B1]: https://github.com/mastermindx-market-intelligence/macro/blob/fc85b0428cf8b0ca4f2fbbc5a415b2871f15a1c9/templates/us_stocks_lab.html.j2
[B2]: https://github.com/mastermindx-market-intelligence/macro/blob/fc85b0428cf8b0ca4f2fbbc5a415b2871f15a1c9/scripts/build_pick_lab.py
[B3]: https://github.com/mastermindx-market-intelligence/macro/blob/fc85b0428cf8b0ca4f2fbbc5a415b2871f15a1c9/scripts/ci/daily_engine_regime_dashboard.sh
[B4]: https://github.com/mastermindx-market-intelligence/macro/blob/fc85b0428cf8b0ca4f2fbbc5a415b2871f15a1c9/engine/pick_lab/render.py
[V1]: https://github.com/mastermindx-market-intelligence/macro/blob/fc85b0428cf8b0ca4f2fbbc5a415b2871f15a1c9/templates/us_stocks_v2.html.j2
[V2]: https://github.com/mastermindx-market-intelligence/macro/blob/fc85b0428cf8b0ca4f2fbbc5a415b2871f15a1c9/scripts/build_stock_board_v2.py
[PUBLIC]: https://www.mastermind-x.com/us_stocks.html
[P1]: https://app.paper.design/file/01M3NT5Y3G5HTJHVR0K5W2MDJM/p-1-0
[PC]: https://app.paper.design/file/01M3NT5Y3G5HTJHVR0K5W2MDJM/p-C-0
[PB]: https://app.paper.design/file/01M3NT5Y3G5HTJHVR0K5W2MDJM/p-B-0
[PA]: https://app.paper.design/file/01M3NT5Y3G5HTJHVR0K5W2MDJM/p-A-0
[P9]: https://app.paper.design/file/01M3NT5Y3G5HTJHVR0K5W2MDJM/p-9-0
[P8]: https://app.paper.design/file/01M3NT5Y3G5HTJHVR0K5W2MDJM/p-8-0
[P7]: https://app.paper.design/file/01M3NT5Y3G5HTJHVR0K5W2MDJM/p-7-0
[P6]: https://app.paper.design/file/01M3NT5Y3G5HTJHVR0K5W2MDJM/p-6-0
[P5]: https://app.paper.design/file/01M3NT5Y3G5HTJHVR0K5W2MDJM/p-5-0
[P4]: https://app.paper.design/file/01M3NT5Y3G5HTJHVR0K5W2MDJM/p-4-0
[P3]: https://app.paper.design/file/01M3NT5Y3G5HTJHVR0K5W2MDJM/p-3-0
[WCAG_TARGET]: https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html
[WCAG_REFLOW]: https://www.w3.org/WAI/WCAG22/Understanding/reflow.html
[VITALS]: https://web.dev/articles/vitals

## 15. Artifact consistency receipt

Validation performed on 2026-11-03 UTC against this complete source document:

- Six canonical assigned route rows, eleven exact assigned Paper page references and the observed 188-board inventory are recorded with their evidence limits.
- 78 unique capability IDs: 38 RETAIN, 32 IMPROVE, 8 BLOCKED_DATA; no removals or relocations.
- 53 unique acceptance cases in sequence T01–T53; all are explicitly requirements rather than executed product tests.
- 62 defined HTTPS source/carrier/standard/Paper references; all coded internal references resolve.
- Commission, protected procedure, main source, held implementation and separate F01/F02 revisions remain distinct.
- The initial D03 source blob was re-read before replacement and remained a36ae8f7feb4284d9d2dcbc35653602c72c339e8. #9495's head remained 128ab198769a5cc2bd180d7f8eeae07924238d32 at the final scoped refresh.
- Author-side semantic findings were repaired and the decisive source counterexamples re-read. No formal review, Paper write, implementation test, merge, release or served-production pass was manufactured.

The resulting Git commit and content blob returned by the canonical source write identify the delivered artifact. The same immutable commit is read back after saving and compared byte-for-byte with the authored content; that external receipt is reported with the return. This document is a source/specification freeze, not an approved visual-reference freeze.
