# Mastermind production design audit and Astra Pro handoff programme

**Commission:** 2026-11-02. **Observation window:** November 2–3, 2026 UTC. **Disposition:** ready to distribute the bounded design-session briefs; current designs are not collectively certified for production implementation.

## Outcome

The recommended programme preserves the strongest existing designs, completes missing workflows and specifications, and composes every product inside a qualified shared-shell system. Rebuilding everything would discard substantial useful work. Applying the current beta shell unchanged would also miss the user's goal: the shell itself needs a serious visual, navigation and interaction redesign.

This package contains **36 ready-to-deliver handoffs**: one Paper capability prerequisite, three foundation/stewardship sessions, 27 product/integration sessions, four bounded Options design slices and one independent re-audit. It includes a complete assignment of the **348 canonical route records**, a separate annex for **nine verified source additions/exclusions**, and a proposed destination/owner for every expanded product Paper page. The user will deliver the sessions, then return for re-audit before implementation.

The existing [whole-estate makeover charter](https://github.com/mastermindx-market-intelligence/macro/blob/design/paper-production-audit-20261102-ryan/research/MASTER_PRODUCT_SHELL_MAKEOVER_MIGRATION_2026-10-08.md) remains the programme's source task tree. The package is attached through [draft PR #10617](https://github.com/mastermindx-market-intelligence/macro/pull/10617). It does not create another umbrella workstream, merge product code or launch the redesign sessions.

### One unresolved execution prerequisite

**Physical Paper reorganization has not been applied.** Direct reads work, but `paper-desktop` 0.5.18 reports `accepted_for_write=false` and `catalog_compatible=false`. The observed catalog digest differs from the approved digest. The allowed catalog also lacks folder/move/archive operations and contains conflicting language around file creation. The Paper workflow requires qualified schemas before writing. P00 supplies the exact original-owner repair assignment; F03 supplies the complete organization plan and action ledger. This is a narrow tool qualification issue, not a request for the user to re-authorize routine design work.

No Paper edit, rename, move, archive or deletion was attempted by this audit. Reading, product analysis, source documentation and handoff creation were completed despite that gate. No alternate carrier was used to bypass it.

## What was inspected

The connected MastermindX team returned **29 files and three folders**, including one archived file and one archived folder. File metadata lists **299 pages** across those files. The **17 primary product/design-system files** were expanded into **193 pages, 2,450 artboards and 375,177 reported nodes**. These counts include historical studies, specification boards, redirects, captured references, duplicates and rejected/held work. They are not a count of unique production-ready screens.

The initial pass was 298 listed pages / 192 expanded pages / 2,449 boards. An active Options Research Desk page appeared during the audit and was read explicitly before freezing this package. A Forex listing was capped at 100 of 101 boards; its final board `6NKK-0` was recovered through the page tree and an exact node read. The census is a bounded live observation, not an atomic lock against concurrent designers.

All listed files/pages and all expanded artboard identities are available in [the census](census/PAPER_FILE_CENSUS.md), [page crosswalk](census/PAPER_PAGE_CROSSWALK.md) and machine-readable JSON. The remaining 12 copy/test/archive files received complete page-list/default-page inspection, not a full artboard-by-artboard expansion. They remain review candidates rather than being declared disposable.

Visual review was a representative subset across shared shell, Macro/Risk, Company, Chart Context, Options, Prophet, News, GMI, Bonds, Crypto and International. Exact observed targets and findings are in [the evidence register](evidence/OBSERVATIONS.md). No claim is made that every one of the 2,450 boards received a visual or interactive review.

The live beta review covered guest `/today`, All Tools, `/us_stocks.html` and `/macro.html`, including a 390px Macro composition. `/today` required sign-in, so the authenticated personal workspace was not validated. The review did not measure Core Web Vitals or test all authenticated mutations. Source and Paper evidence supplement those observations; they do not replace production task proof.

## Main findings and design decisions

### 1. There is substantial design value to retain

Company R3 has a purposeful thesis, revenue/guidance chart, salient metrics, invalidation and source access. Chart Context preserves the chart as the central object and adapts the explanation below it on mobile. Options Exposure uses a meaningful strike-by-expiry matrix with an inspector, compare and replay. Prophet preserves readiness, quote/assessment freshness, invalidation and comparison. News R3 uses a clearer typographic ledger. Bonds R32, Forex R26 and International R14 contain deep mechanisms and useful evidence patterns.

These should start as **retain and upgrade** assignments. Each receiving session must still qualify the exact current revision, interaction/state coverage and shell composition. A strong screenshot does not automatically pass the reference gate.

### 2. Some apparent coverage is incomplete or misleading

Company R3's mobile board `1D9K-0` is an empty 390×844 frame with no children. It cannot count as responsive coverage. Older R2 mobile/Chinese screens do not prove the successor is complete.

GMI's earlier issuer reference contains a raster rectangle named “Dark webpage screenshot.” Those captures are valuable implementation evidence, but they are not fully editable production mockups. GMI also needs a completed legitimate issuer experience alongside its held/unknown example. Its Round 2 hierarchy and sticky-index improvements should be retained.

Page titles lag actual work: Bonds R32 lives beneath an R18–R25 title; Crypto R4 beneath an R3 title. “Refined vase” is the real Intelligence Hub. The canonical Design System resides in Others. “Masterpiece”, “current build”, “canonical” and “copy” are unreliable acceptance or disposal signals. Organization must use exact identity, content, lineage and approval evidence.

### 3. The shell is a product design problem, not a border around old pages

Current references disagree about global headers, icon rails, local tabs, bottom navigation and account/context controls. The live beta All Tools directory exposes 291 destinations with verbose labels, duplicate-looking names and weak grouping; the inspected projection has 182 ungrouped entries. The live US composition is cramped at the shell's actual width. Macro mobile gives substantial first-fold space to gauge and metadata before its path chart.

F01 must redesign navigation, taxonomy, composition, context and transitions. F02 must reconcile the system and reusable patterns. Product sessions then compose at the **real available content width**, including rail, expanded navigation, inspector and zoom. Focused Terminal, public pages and internal OS require related but distinct compositions. The existing `/terminal` chart chrome and Brain singleton must not be double-wrapped.

The starting investor IA is Today / Discover / Analysis / Monitor / Research / Portfolio, with region separate. It is an input for task evaluation, not a prohibition on improvement. The new shell should make primary work easy to find without requiring users to search a giant directory every time. Destination search, entity search and actions need understandable distinctions.

### 4. Useful diagnostics sometimes displace the main task

The expanded News R2 rail spends almost its entire 900px height on coverage/methodology before the first headline. Keep coverage visible, but make reading primary and put deeper diagnostics in accessible disclosure. Prophet's long mobile repeated cards need a better scan/expand rhythm without losing fields. International needs hierarchy among its many meaningful clocks and mechanisms. Existing doctrine already calls for a clear main answer and limited supporting material above the fold; it also prohibits colored container borders/accent stripes.

The intended improvement is better prioritization and visual compression, not less useful functionality. Charts, matrices and aligned tables should stay when they help users compare or understand relationships.

### 5. Data truth must be resolved alongside visual design

The live Macro Fed panel displayed contradictory “cut expectations” and “~2 hikes” copy. A Risk Radar Paper specimen prominently displayed a 13% probability while calibration was unverified. These require producer/clock/model-status contracts and truthful interim states. A designer must not make a number appear trustworthy by polishing its presentation.

Every session must specify source fields, identity, units, timestamps, freshness, zero/null/unknown, partial coverage, calculations, access and mutation ownership. Proposed features may be designed, but must be labeled as proposals with actual backend dependencies. A missing producer is `BLOCKED_DATA`, not permission to fabricate an endpoint or outcome.

### 6. The route registry is useful but not a fresh exhaustive denominator

The committed registry has 348 records: 314 Macro, 27 Terminal and seven Mastermind; lifecycle counts are 322 live, 15 internal, five lab and six dev-only. It was generated October 21. Ninety-seven source-template entries are unknown. All 348 design-compliance flags are false; that records unqualified migration coverage, not proof that all pages are visually poor.

The fresh source check reconciled Terminal's complete 29-page-module tree and Macro's 293 root HTML documents. It found seven Macro pages absent from the registry—six GMI pages and Expectation Surface—and two Terminal modules: equity replay and a dev-only options-plan harness. No canonical IDs were invented for them. `/index.html` is the existing `/` alias, not another design.

The current projection had 13,123 legacy paths, 17 native paths and 291 directory entries. Pending Terminal #1226 proposed 13,987/17/290, primarily adding 863 earnings articles and two company pages and removing one withdrawn synthetic fixture. It still did not admit the six GMI pages, Expectation Surface or equity replay. The fresh nested-document inventory was not certified: a recursive read failed and a commit comparison reached GitHub's 300-file limit. F03 must obtain the existing exporter's complete inventory at frozen source pins before implementation acceptance.

The appropriate split is by product family and reusable archetype, not by every generated document. [Route coverage](census/ROUTE_COVERAGE.md) assigns every canonical record and separately records the nine source deltas. Exact URL/query/hash contracts and representative instance tests remain mandatory.

### 7. Route names can conceal the actual product

Independent architecture review corrected five important boundaries. `/markets.html` is Global Market Cycles and belongs with International/country analysis. `/ontology.html` is WTI Live Path and needs Commodities ownership with ontology-pattern consultation. `/allocation.html` is Narrative Rotation, not personal holdings. `/analysis` has real company/thesis/investigation views and needs a product owner under one existing route parser. `/x/<slug>` is a chart-sharing family, owned with Terminal and consulted by public/access designers.

Shared templates also need explicit coordination. D02 owns integration of `dashboard.html.j2`; Macro governs `body.page-macro`, US Stocks `body.page-stocks`. D12 owns common strategy/model-evidence archetypes, while asset/regional sessions own their semantics. D05 owns rotation patterns with D19's China variant. These boundaries prevent concurrent design sessions from creating incompatible future implementation instructions.


## Product-file concentration

| Primary Paper file | Expanded pages | Artboards | Implication |
| --- | --- | --- | --- |
| MASTERMIND PAGES | 58 | 888 | Split mixed current/history families; keep exact lineage |
| Terminal | 36 | 412 | Split mixed current/history families; keep exact lineage |
| Mastermind OS | 20 | 306 | Split mixed current/history families; keep exact lineage |
| PROPHET | 12 | 203 | Retain useful work; qualify current revision and shell coverage |
| International Markets · R10 · Current Build | 17 | 172 | Retain useful work; qualify current revision and shell coverage |
| Mastermind · Market Dashboard Popups · Redesign | 6 | 99 | Retain useful work; qualify current revision and shell coverage |
| MarketOntology | 6 | 98 | Retain useful work; qualify current revision and shell coverage |
| Refined vase | 8 | 68 | Retain useful work; qualify current revision and shell coverage |
| Mastermind AI | 9 | 64 | Retain useful work; qualify current revision and shell coverage |
| Mastermind · Market Guide · Re-envisioning | 6 | 49 | Retain useful work; qualify current revision and shell coverage |
| Mastermind Product Design System — Canonical | 8 | 48 | Retain useful work; qualify current revision and shell coverage |
| GMI Explorer 2026-10-21 | 1 | 16 | Retain useful work; qualify current revision and shell coverage |
| News Intelligence · Decision Rail · R2 · 2026-10-21 | 1 | 10 | Retain useful work; qualify current revision and shell coverage |
| Terminal · Options R1 · Design Upgrade · 2026-10-21 | 2 | 7 | Retain useful work; qualify current revision and shell coverage |
| Expectation Surface · R1 · 2026-10-21 | 1 | 5 | Retain useful work; qualify current revision and shell coverage |
| GMI Explorer 2026-10-22 — Round 2 | 1 | 4 | Retain useful work; qualify current revision and shell coverage |
| Terminal · Options R1 · Design Upgrade · W3 mobile · 2026-10-21 | 1 | 1 | Retain useful work; qualify current revision and shell coverage |

## Session responsibility summary

| Group | Sessions | Purpose |
| --- | --- | --- |
| Capability and foundations | P00; F01–F03 | Qualified writes; redesigned shell; design system; organization and coverage |
| Core analytical workspaces | D01–D08 plus D08A–D08D | Today, Macro, US/Prophet, Discover, Sectors, Terminal, Company/Earnings, Options integration and four bounded slices |
| Research and intelligence | D09–D14 | Flows/Ownership, News, Hub/Library, Memory/Strategies, GMI/Ontology, AI |
| Asset classes and regions | D15–D21 | Bonds, Forex, Commodities/WTI, Crypto, China, HK/Canada, International/Cycles |
| Personal and supporting products | D22–D27 | Portfolio, Monitor/Alerts, Account/Guide, Specialist Intelligence, Public, Internal OS |
| Independent re-audit | QA01 | Cross-product retention, design, data, accessibility and builder qualification |

## How to run the programme

Start with [SESSION_INDEX.md](SESSION_INDEX.md). Copy one complete handoff file into each selected Astra Pro session, or attach that file with the package. Each brief contains its own mission, exact Paper inputs, assigned routes, retained strengths, concrete changes, data/build obligations, overlaps, acceptance conditions and return format. The [combined handoff document](COPY_PASTE_HANDOFFS.md) contains the same prompts in one searchable file.

**Foundation wave:** P00 restores qualified Paper writing through the existing owner. F01 designs shell/IA; F02 designs system/components; F03 establishes organization and coverage. F01/F02 should freeze a useful v1 early rather than wait for the entire website. F03 can prepare metadata and source contracts while Paper writes remain blocked.

**Concurrent product wave:** D01–D27 can inspect source/live/Paper, produce capability ledgers and formulate backend/build contracts immediately. Their final visual compositions depend on the frozen shell and system. Start with demanding representative consumers—Macro, US/Prophet, Company, Terminal and Options—to expose foundation weaknesses early. Other markets, research, personal, public and internal sessions can proceed concurrently on their scoped work. No account concurrency capacity is assumed by this plan.

Options has been split after independent review: D08 owns the common contract and integration; D08A owns Overview/Flow, D08B Exposure/Volatility/3D, D08C Plan/Compare/Review, and D08D Futures/Replay. Existing page targets are disjoint. The user may deliver these separately; D08 does not automatically spawn them. This avoids leaving a large platform half-finished after one strong Exposure composition.

**Integration wave:** QA01 checks complete cross-product journeys after representative returns and again at final re-audit. F03 updates the directory and references after review. A material foundation change triggers re-review of affected domain compositions, not indiscriminate restarting of accepted work.

This programme is not authorization to launch sessions automatically. The user explicitly intends to deliver the handoffs. It is also not a product-code implementation wave. Each design session must finish its product/backend/build instructions so the later builders have a concrete contract.

## Organization that will remain understandable

Use the folder structure and exact page allocation in [ORGANIZATION_RULES.md](ORGANIZATION_RULES.md). Separate foundations, workspaces, markets, research, personal, public, internal, archives and QA. Large assignments have named subfiles; historical references are linked from active files rather than copied into every working canvas.

Every active file starts with a useful read-me/build-contract page. Its directory shows the current candidate, exact IDs, predecessor/successor, owner, route scope, shell/system version, full specification and real RIG state. Design acceptance, implementation, release and served proof are separate fields.

The proposed operating budget is about eight active pages and 60 active boards per file, adjusted to actual responsiveness and density. This is an organizational convention, not a Paper platform claim. Split earlier when a workflow or canvas becomes unwieldy. Do not rename or move a shared container while another writer is using its affected descendants; coordinate at exact target scope rather than inventing a file-wide lease.

Archive only after the successor/retention decision, comments/specifications/assets, backlinks and readback are preserved. Never archive by age, title, folder or copy suffix alone. Preserve rejection reasons and source-only captures. No permanent deletion is part of this programme. Existing test/copy files get an explicit review before moving to QA/archive; Refined vase is specifically protected as real product work.

## What each session must leave for its builder

The [common contract](COMMON_SESSION_BRIEF.md) and [fillable source template](templates/PRODUCT_BUILD_CONTRACT.md) require seven connected deliverables: product brief, capability ledger, route/object map, interaction/state contract, real backend/data contract, editable design/component map, and builder/review package.

The contract answers practical questions: which user problem is solved; what exists today; what is retained, relocated or proposed; where each metric comes from; which object is saved; which action writes; what happens on stale data or an uncertain response; how filters/history/focus survive navigation; how the component changes at narrower content widths; which source files are reused; and what the builder must verify before release.

Require intentional light/dark and EN/ZH compositions. Evaluate 320/390/tablet/narrow-desktop/wide-desktop classes with actual shell widths and inspectors, keyboard/touch and zoom. A house 44px target for important mobile controls is stronger than WCAG 2.2 AA's 24px target-size minimum/spacing rule. Complex charts/tables may need scoped 2D interaction; that does not excuse application-wide horizontal overflow. Proposed future Core Web Vitals targets are LCP ≤2.5s, INP ≤200ms and CLS ≤0.1 at p75; no current values were measured here. [W3C target guidance](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html), [reflow](https://www.w3.org/WAI/WCAG22/Understanding/reflow.html), [Web Vitals](https://web.dev/articles/vitals).

Normal-data task completion and truthful exceptional states are both required. Distinguish loading, no-results, empty-by-filter, partial, stale, unsupported, unavailable, denied, guest, expired session and pending/failed/uncertain writes. Beautiful error specimens do not replace a complete working primary experience.

## Re-audit and acceptance

Use [RE_AUDIT_CHECKLIST.md](RE_AUDIT_CHECKLIST.md) after the sessions return. The review asks whether users can complete real journeys across products, whether existing features remain reachable, whether backend contracts are implementable, whether current candidates are correctly organized, and whether source/route/Paper deltas are reconciled.

Independent product-regression and visual/taste critics review before/after artifacts and tasks with designer rationale quarantined during the first pass. Apply existing RIG states—draft, in_review, approved, revise, rejected, superseded—and bind acceptance to exact frozen references. A changed candidate invalidates affected receipts. This package is an audit and commissioning plan, not formal approval of the designs.

The future implementation stage begins with qualified references and actual RIG-backed migration packets. It must still prove functional behavior, source/data correctness, accessibility, performance, route reachability and served release state. A page is not ready merely because its Paper file looks complete.

## Evidence, pins and limits

- Protected Mastermind procedure: `7f1242bfa90f0f0448e66e400e054bd5aa5fa15a`.
- Initial Macro observation/branch base: `5234bf95bfe8cf0b72ed5da29afec1fb43f0f4e0`.
- Fresh bounded Macro delta: `143bdfe08ac2444fde9fcb2263aa0c1d3d03dcc0`; registry IDs unchanged.
- Terminal protected master: `e0ae63e43965ec1d1c93405ee903fd92b63e3470`.
- Pending Terminal #1226 inspected head: `880418fa7ac1fc9f914c1cb8db5f57f3fcb59a40`; not merged at observation.
- Paper identities and findings: [evidence register](evidence/OBSERVATIONS.md), [machine census](census/paper-artboards.json), [source-delta annex](census/source-delta.json).
- Independent principal reviews: [review record](evidence/INDEPENDENT_REVIEW.md). They are audit-package critique, not fabricated design-approval receipts.

The remaining limits are precise: physical Paper changes are blocked pending qualified writing/resource management; authenticated workflows were not fully exercised; every artboard was not visually reviewed; route-to-board approval is not yet established for every page; and the latest complete nested generated-document denominator still requires the existing exporter. Those tasks have explicit owners and return conditions rather than being hidden behind an “all production ready” label.
