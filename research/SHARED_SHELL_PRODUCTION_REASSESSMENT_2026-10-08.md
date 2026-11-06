# Shared product shell — production reassessment and migration decision

Date: 2026-10-08. Status: DESIGN / ARCHITECTURE CANDIDATE; implementation and release remain HOLD.

## 1. Commission, decision and acceptance boundary

The Chairman commissioned a reassessment of the complete investor-product shell, a Paper census, actual design refinement, native-web architecture and an engine-preserving, low-downtime migration plan. Actual application construction is the NEXT stage; this document does not silently enroll a production build, deploy, DNS change or runtime worker.

**Decision:** evolve the existing product into one coherent investor experience. Use the existing Next.js/React application and shell as the native-web starting point, retain existing Macro pages behind compatible shared chrome while they migrate by route family, and preserve every existing engine, identity, entitlement and user-state owner. Develop locally with fixtures AND validate on a protected hosted preview. Release through the current public origin in reversible route-sized waves, not a big-bang domain or framework replacement.

**Navigation decision:** retire redundant global top-menu destinations on enrolled application pages. Keep one contextual top bar, page-owned tabs/actions and one left primary navigation. Do not delete controls simply because they appear near the top. Do not substitute the internal CEO's Projects/Inbox/Conversations/Knowledge navigation for investor workflows.

**Not accepted yet:** a production-grade executable prototype, a complete account-wide artboard audit, accessibility/browser qualification, production performance, release readiness, or an award-winning outcome. Paper screenshots demonstrate a visual candidate, not working navigation or successful deployment.

Existing continuity: Macro PR #7949, branch `sol/market-os-shared-shell-design-20260924`, operation `market-os-shared-shell-design-20260924-sol-001`. Preserve the original charter at `2cf7577524f9df9653e619ba770c38383c2c6079`. This companion is not a replacement programme, route registry, permission plane or lifecycle. This session's write scope is this document and its new disjoint Paper page/boards; incumbent implementation paths and prior design boards are untouched.

## 2. Evidence and procedure

Protected procedure read at Mastermind `c7e47c859eb2925c5626931fd511800773ba09ac`: INDEX, COLD_START, ACTIVE_EXECUTION, SESSION_RELIABILITY, WEB_CEO_DELEGATION and the same-pin Paper workflow/connection. Skillpack 1.0.1 / bootstrap 1 compatible. Installed mastermind-pro-execution used beneath canonical law. Direct work reason: PRINCIPAL_JUDGMENT / UNIQUE_APPROVED_ACCESS for concentrated design and architecture review. No child dispatch, provider work, Executive job, watcher or scheduled delivery is claimed. Actual selected UI mode/runtime identity is unobserved.

Source reads used for this decision:

| Evidence | Exact source / observation | What it establishes |
|---|---|---|
| Starting commission | `research/MASTER_PRODUCT_SHELL_MAKEOVER_MIGRATION_2026-10-08.md` at `2cf7577524f9df9653e619ba770c38383c2c6079` | Investor-shell intent, existing route-family programme, old pilot boundaries |
| PR #7949 | Open, draft, unmerged, not mergeable at initial read; comment `6069275699` | No release acceptance; old PR-body R41 identity is not the newest charter identity |
| Macro implementation/design basis | `744a5b75e8d19db9ec6e0df0542c3123f67d6866` | Source snapshot, not a claim that the live estate still runs this exact commit |
| Product design system | `research/MASTER_PRODUCT_DESIGN_SYSTEM_V1.md`, lines 1–155, same Macro pin | Answer-first hierarchy, Inter, semantic data colors, theme.css ownership |
| Investor IA | `research/MASTER_PRODUCT_INFORMATION_ARCHITECTURE_V1.md`, lines 1–160, same pin | Six investor jobs, scope-vs-destination distinction, existing auth/Brain ownership; document itself was proposed architecture |
| Migration factory | `research/DESIGN_MIGRATION_FACTORY_V1.md`, lines 1–135, same pin | Per-family source/behavior/visual evidence, rollback and independent qualification |
| Serving boundary | `app/deploy/Caddyfile`, lines 1–420, same pin; blob `aad04daf807a056a9ce8f2a0012fdcce8938f9bc` | EdgeOne/Caddy, static publishing, existing API/WebSocket/Supabase paths, public HTML vs protected payload |
| Existing native shell | Terminal `terminal/components/chrome/AppShell.tsx`, lines 1–180 at `d660d98b1ebc0bdf0d1b16d66202b1760f6cc94a` | Existing AppNav/MobileNav, identity context, error isolation, non-chart shell and origin navigation |
| Existing frontend dependencies | Terminal `terminal/package.json`, lines 1–115, same Terminal pin | Declared Next 16.2.9 / React 19.2.4, TypeScript, fixture and test infrastructure; not proof of executed tests |
| Newer search index | Macro search later returned `c65a4b0be4390052a60d1e7a0b191511a3b7d829`, then `8a35d8b62494a84b2448182aaa561edea83fe54f` | The repository moved during investigation; re-admit current implementation sources before coding |

The generated ACTIVE_BUILD_MAP at the initial Macro pin was dated September 29 and is explicitly advisory. Neither it nor historical PR tests proves October 8 custody, deployment or acceptance. Reconcile overlapping current work before implementation, including the charter's International, Bonds, China/mobile, China dialog and Confluence surfaces. Do not modify that generated projection manually.

## 3. Paper census — coverage, identity and disposition

### Coverage statement

**11 exact files were reached and identified; their complete returned page directories contain 107 pre-existing pages, plus this session's one candidate page = 108 known pages.** This is a file/page census of the connected project reference graph, NOT an account-wide enumeration or a claim that every artboard/descendant was visually inspected. Board inventories and visual review were deeper on shell-relevant targets. Terminal's company page reports 121 boards but the first basic-info response listed only 100; its entire 121-board inventory is not claimed.

The initial unresolved Prophet and Mastermind AI links were recovered from the canonical design-system Working Files navigator `42T-0`. The same navigator also exposed Market Guide and Popups/Risk Radar. Those exact targets were then read. Missing references were not guessed.

Carrier: existing guarded Studio Direct Paper actions, server 0.5.14, accepted catalog `ac18857df0aa6323646333368e5798e7c28de7b4d5f5dc3cb320276e3535daa9`. Account enumeration (`list_resources`) and native prototype-link editing are not available in the approved catalog. No file-focus emulation or alternate carrier was used. Snapshot guards are not document revisions or collaboration locks.

### File-level decisions

| File | Exact file ID | Existing pages | Reuse / disposition |
|---|---|---:|---|
| Mastermind OS | `01M3NRCX55B452A12819WNE1RH` | 14 | Global shell/search/recovery interaction references; internal CEO product remains separate. New investor candidate is isolated on p-F-0, not adopted into the CEO Atelier. |
| MASTERMIND PAGES | `01M2WGNCX9475G79JRKJTCM08P` | 27 | Governed starters, legacy product studies and retained shell state library. Preserve archives and extract specific behavior, not indiscriminate visual copying. |
| International Markets | `01M3P1TW5Y3XWQC37ADDS8K5AG` | 7 | Reuse cross-market context, compare, history, scenario and small-screen contracts. |
| Intelligence Hub working file, actually named “Refined vase” | `01M2VWK62FA5S4VVF6G7SBPE5J` | 8 | R4 working commands/evidence/locale states; source and held QA are distinct. Incorrect display name is a discoverability defect, not permission to recreate the file. |
| Terminal | `01M3NSZGE8JWN2EZCSF0DT05RM` | 17 | Native company/options/heatmap work; retained Stocks + Setups references. Keep chart-workspace behavior separate from ordinary page chrome. |
| MarketOntology | `01M3P1X4FR6BRTB13KA736Y1HT` | 5 | Company comparison/evidence, connected thesis, source association and return behavior. Preserve NOT FOR BUILD and duplicate-transfer holds. |
| Product Design System — Canonical | `01M312VSDSZFVT45674GDVJVZN` | 8 | Foundations/components/patterns and live workspace navigator. Noir OS styling is not automatic investor-IA authority. |
| PROPHET | `01M3NT5Y3G5HTJHVR0K5W2MDJM` | 6 | Today/setup/playbook, regional and screener flows; quote health must remain separate from assessment freshness. |
| Mastermind AI | `01M3P1QEHS5XXQY85BJT6QR2E1` | 7 | Existing popup/expanded/mobile conversation continuity and retained research-reading/evidence. Do not add another chat or answer renderer. |
| Market Guide | `01M32XYWDYSFTNDZVJKQ5QHT33` | 4 | Score explanations, contextual help, aliases/search/recovery; reuse rather than inventing tooltips with conflicting definitions. |
| Dashboard Popups / Risk Radar | `01M38EVF74SJWG1GANN5VP380Z` | 4 | Risk, China and news progressive disclosure; preserve source scope, partial-data state and same-context return. |

### Complete observed page-directory inventory

IDs below are file-local. Titles are abbreviated for navigation; this is not a claim of build acceptance.

**Mastermind OS:** p-1-0 Directory; p-2-0 Noir experience/build guides; p-3-0 Conversations/message states; p-4-0 Missions/work/fleet; p-5-0 Connected company journeys; p-6-0 Chairman daily; p-7-0 Access/loading/recovery; p-8-0 Global shell/navigation; p-9-0 All Tools/research drawer; p-A-0 Search/recovery; p-B-0 SOURCE signed-in home; p-C-0 Chat Atelier; p-D-0 Canonical Atelier; p-E-0 Daily experience/flow. New p-F-0 Investor Shell Production Candidate.

**MASTERMIND PAGES:** p-5-0 Governed starters; p-Q-0 Earnings/dossiers; p-3-1 News; p-D-0 Legacy shared shell; p-13-1 Breadth; p-A-0 Confluence governed; p-H-1 Confluence R2; p-O-1 Bonds; p-N-1 Forex; p-J-1 Policy; p-8-1 SOURCE live baselines; p-T-0 SOURCE Hub R4; p-10-0 Crypto current; p-L-0 Commodities; p-Y-0 Sector current; p-S-1 Government revenue; p-K-0 BioCatalyst; p-Z-0 ARCHIVE Sector; p-V-0 ARCHIVE Company; p-11-0 ARCHIVE Crypto; p-X-0 ARCHIVE Hub; p-W-0 ARCHIVE International; p-E-1 Sector vNext study; p-6-1 Sector unified detail; p-I-1 SOURCE Hub R1; p-9-0 Sector redesign; p-7-1 China intelligence.

**International:** p-1-0 R10 current-build contracts; p-2-0 Overview/compare/navigation; p-3-0 Macro/policy/risk; p-4-0 History/scenarios; p-5-0 Research library/search; p-6-0 China intelligence; p-7-0 Returns/calendar/Terminal dossier.

**Hub / Refined vase:** p-1-0 bridge-canary Page 1; p-2-0 Hub R4 working; p-3-0 Desktop commands/evidence; p-4-0 Mobile commands/evidence; p-5-0 Research/risk; p-6-0 Loading/filter/locale; p-7-0 Transfer QA held; p-8-0 SOURCE Hub alt-data.

**Terminal:** p-1-0 Company intelligence; p-2-0 Options structure; p-3-1 Options plan; p-4-1 Options save/watch; p-5-1 Options review; p-6-1 Options scenario/assumptions; p-7-1 Options compare; p-8-1 Heatmaps; p-9-1 Navigation/interaction; p-A-1 Research/results/sources; p-B-1 Financial/market/ownership; p-C-0 ARCHIVE company; p-D-0 Options volatility; p-E-0 Retained shell Stocks/Setups; p-F-0 Company earnings; p-G-0 SOURCE Terminal baselines; p-H-0 Options 3D.

**MarketOntology:** p-1-0 Joined journey; p-2-0 Answers/context/evidence; p-3-0 Thesis changes/receipts; p-4-0 Retained company comparison/evidence; p-5-0 QA HOLD duplicate shell transfer.

**Canonical system:** p-1-0 Cover/directory; p-2-0 Getting started; p-3-0 Foundations; p-4-0 Components; p-5-0 Patterns; p-6-0 Reference screens; p-7-0 Utilities; p-8-1 Source imports/assets pending review.

**Prophet:** p-1-0 Prophet current journey; p-2-1 Hong Kong/Canada; p-3-0 R2 Today/setup/plans; p-4-0 Screener/table/grid/compare; p-5-0 Shared contracts/state coverage; p-6-0 SOURCE US live baseline.

**Mastermind AI:** p-1-0 Chat Workbench vNext; p-2-0 Interaction/recovery R2; p-3-0 Answer craft R7–R8; p-4-0 Legacy references/assets; p-5-0 Retained research reading/evidence; p-6-0 QA HOLD duplicate shell transfer; p-7-0 SOURCE chat live baseline.

**Market Guide:** p-1-0 Re-envisioning; p-2-0 Score reading/themes/locales; p-3-0 Contextual help/visual explanations; p-4-0 Search/aliases/recovery.

**Popups:** p-1-0 Risk Radar; p-2-0 Program handoff; p-3-0 China progressive disclosure; p-4-0 Events/news briefing-to-evidence.

### Reusable references and concrete defects

- OS p-8-0 has 13 boards. `H7R-0` and `AMP-0` were visually inspected: the former is CEO-oriented, the latter investor-oriented. The newer OS directory points to Atelier AT90 for internal OS chrome; neither supersedes investor-product semantics.
- MASTERMIND PAGES p-5-0 has 22 starter/specification boards. Its `5G0X-2`, `5G1H-2` and `5G1Z-2` directories/coverage were read. Old links still reference moved/absent local p-R-0, p-M-0 and p-2-1. New focused-file references must replace those pointers only after destination/source joins are checked.
- Legacy shared shell p-D-0 retains R40 comparison, R41 search and R42 watchlist saving/saved/undo/failed/access states. Reuse their behavior. In particular, unknown save outcome is not an invitation to blindly retry a mutation.
- Terminal p-E-0, MarketOntology p-4-0 and Mastermind AI p-5-0 are retained product-shell references. Their adjacent QA HOLD duplicate-transfer pages are not alternative build sources.
- Prophet p-1-0 lists 50 boards, including R4/R5 quote-health, unchanged-assessment, no-prior-brief and history-unknown states. Those distinctions must survive restyling. `DAY-0` is a listed empty 100×100 frame, not a product state or customer route.
- International's 12 boards on p-1-0 are largely contracts/directories, not 12 independent routes. Board counts are not an implementation-progress denominator.
- The canonical navigator `42T-0` explicitly says its addresses are editable references, not live buttons. A Paper design directory is not an executable navigation test.
- Historical R8 AI recovery comment `5850098623` preserves unresolved old operation/indicator obligations. This census did not replay, release or claim to resolve those old writes. Only this session's new nodes may be finished.
- Token sets differ across files: Noir, market `--mx-*`, and Market Guide's unprefixed dark/light aliases. This is evidence of projection drift, not a reason to install a new global token system. Map semantic roles back to the existing owner and test the projections.

**Priority repair order:** exact reference graph and status labels; one investor-shell source; navigation and context ownership; two representative page compositions; access/loading/recovery; responsive and theme projections; then motion and final visual refinement. Do not clean archives or manufacture hundreds of counterpart boards to make a matrix look complete.

## 4. Actual design improvements and production design contract

### New editable candidate

Paper file `01M3NRCX55B452A12819WNE1RH`, new page `p-F-0`, title “14 · Investor Shell · Production Candidate · 2026-10-08”. It is an isolated cross-product review candidate, not the CEO Atelier's current source. Existing directories disagree between OS-only product organization and retained shared global shell; resolve final library placement before canonical publication, without duplicating the boards.

- **IS01 `UO2-0`:** 1440×1024 dark desktop. 224px rail, 64px contextual bar, one content title, local tabs, answer-first backdrop brief, inspectable evidence and onward product links. Existing investor rail/brief components were reused and refined. Screenshot checked after composition; no visible page clipping or horizontal overflow at that size.
- **IS02 `USV-0`:** 390×1000 dark mobile. 56px header, drawer/search launchers, explicit market scope, overflow-aware local tabs, stacked brief/metrics/evidence journey. Screenshot checked after content completion; no visible page clipping or horizontal overflow at that size.

Numbers, chart and statements are illustrative fixtures, clearly labeled. They are not October 8 market findings and cannot be promoted into a recommendation.

### Navigation anatomy

| Layer | Contents | Explicit exclusions |
|---|---|---|
| Left primary rail | Today, Discover, Analyze, Monitor, Research, Portfolio; existing pinned destinations; All Tools; account/settings | Internal CEO projects/inbox/fleet; duplicated country trees; every individual route at top level |
| Contextual top bar | Rail control, one search entry, applicable market scope, Terminal handoff | Second global destination menu; duplicate Ask/search box; page-specific filters |
| Page header | Title, necessary freshness/scope and primary action | Four stacked header layers; meaningless marketing hero on every dense page |
| Page-local navigation | Overview/Breadth/Sectors/Risk/History or family-specific tabs | Another implementation of global navigation |
| Optional context panel | Existing assistant/evidence inspector under its current owner | New chat, parallel source store or always-open panel reducing usable chart width |

The six jobs are the proposed investor IA adopted for this design candidate under the current commission; production rollout remains subject to findability and route mapping. Familiar routes such as Market Overview, Prophet and Sectors stay pinned/quickly accessible. Search supports their established aliases. Public marketing, pricing, legal and acquisition pages retain appropriate public chrome rather than inheriting a signed-in application rail indiscriminately.

On mobile, use one drawer for primary destinations. Put Terminal/account/tools there rather than squeezing desktop utilities into the bar or introducing a competing bottom navigation. Menus expose selected destination and current scope. Unsupported markets display an honest unsupported-scope state, not a fabricated empty dataset or a silent country change.

### A production-quality visual system, not one universal page template

Use existing typography and semantic tokens. Inter is the approved investor foundation; platform-like restraint does not require distributing Apple's font files or adding a font CDN. Preserve the current CN-reachable asset posture. Dense data, editorial reading and chart workspaces need different internal compositions while sharing chrome, spacing rhythm, focus behavior and controls.

The candidate uses graphite market surfaces, clear type hierarchy, fine separators and restrained accents. Do not inherit every luminous surface from an old mockup. Reserve directional colors for data and distinguish action, risk, source-health, provisional and entitlement states. Language-dependent market-up/down color preferences must not invert error/health semantics.

Proposed layout contract: expanded rail 216–240px (candidate 224), compact rail only where labels remain discoverable; desktop top bar 64px, mobile 56px; content padding 24–32px desktop and 16–20px mobile. Reflow at actual content breakpoints, not device names alone. Reading pages may constrain line length; charts and dense tables can use available width. Controls target 44px hit areas as a product choice. Do not claim WCAG AA universally requires 44px.

Keep default motion brief and purposeful; respect reduced-motion preferences. Avoid automatic count-up numbers, breathing risk indicators and layout-shifting first-load animations. A shell's luxury is confidence, speed and legibility, not persistent visual activity.

### Required interactive prototype coverage before final design acceptance

The next native-web prototype must prove: rail expanded/collapsed and mobile drawer; keyboard search/open/no-results/unavailable; country switch with unchanged supported route; local tab/deep link/back; native-to-legacy-to-native handoff; assistant popup/expand/return preserving draft and evidence; logged-out/locked/expired account states; initial load, stale/partial and route failure; saving/saved/failed/unknown outcome through the existing write owner. Do not represent unimplemented controls as functional simply because their Paper labels exist.

Dialogs/drawers require correct initial focus, Tab containment where modal, Escape handling, background inertness and focus return. Page navigation uses normal navigation semantics, not inappropriate ARIA menu roles. A route change moves focus sensibly and announces loading without trapping users in an endless skeleton.

## 5. Native-web architecture — reuse boundaries

### Recommended structure

`Current edge / Caddy -> route allowlist -> existing Macro static page OR existing Next application -> existing APIs, authorized artifacts and user-state owners`.

Within the Next application, extend the existing AppShell and shared primitives rather than create a third application from scratch. Existing non-chart shell already owns AppNav, MobileNav and identity context outside page-level error boundaries. `/terminal` has a separate chart shell: share tokens and compatible controls, but do not nest AppShell around it, remount chart providers, duplicate sockets or intercept its keyboard shortcuts blindly.

Derive navigation for both Next and legacy chrome from the current canonical route/destination owner. A generated TypeScript projection and a Jinja/static projection may be appropriate; two hand-maintained competing navigation registries are not. Match the existing source schema before adding fields. Required contract information includes destination identity, established URL/aliases, parent job, applicable market scope, layout mode, access semantics, renderer family and rollout eligibility. These are needed fields, not permission for a new runtime registry.

Use React/TypeScript for shell and new interactive page composition; keep server/client boundaries deliberate. Charts, grid interactions and assistant streaming can remain client components under their existing owners. Do not make the entire application a heavy client-only bundle merely to keep the rail visible. Do not make a framework-version upgrade part of the design migration unless a proven requirement needs it.

### Three integration paths

**A — Retained full-document route, preferred first bridge.** Keep the existing Python/Jinja-built HTML and page scripts/data loaders. Render compatible shell chrome at build time and remove only the old global menu for that enrolled template. Navigate with real same-origin URLs; a full document navigation is acceptable during migration. The page keeps its local controls, data clocks, charts, filters and access behavior.

**B — Native page, preferred long-term for interactive workspaces.** Compose the page in the existing Next application and consume the same authorized API/artifact contracts. Port view logic gradually, with source/output parity; do not rewrite the engine in TypeScript. Keep user state in its present owner. Existing React components should be adapted rather than recreated.

**C — Temporary isolated embed, exception only.** An iframe is justified only for a specifically reviewed isolated legacy surface with a defined origin, focus, sizing, accessibility, auth and context contract, an expiry/disposition and no permission widening. Do not make cross-origin iframes the default integration architecture.

Reject arbitrary runtime fetching of complete legacy HTML followed by innerHTML insertion/script execution. It creates ambiguous lifecycle, CSS, auth, focus, script and cleanup ownership. A content-slot adapter is permitted only after the page's initialization/teardown and data dependencies have been proved, not assumed from its appearance.

### Retain these owners and behaviors

- Python engines, scoring, signals, model versions, historical results, regime/taxonomy definitions, collectors and publication schedules.
- Existing authorized API/data outputs and freshness/provenance. Missing data stays missing; styling cannot interpolate a score into apparent availability.
- Supabase identity, macro-api entitlement authority, existing regwall/paywall/RLS and payment ownership. No new user database or session store.
- Existing watchlists, portfolio state, preferences, saved research and optimistic-write reconciliation. No migration-side dual write or shadow source of truth.
- Existing Brain/assistant request, stream, history, rendering and quota owners. One conversation may expand into a new layout; it must not become a second chat session.
- URL/query/fragment semantics, browser history, source clocks and locale/currency/market identity. Validate outbound/return URLs with existing allowlists; do not create open redirects.

A green rendering test proves rendering. Engine retention must be demonstrated with unchanged inputs/outputs and contract tests; no historical result may be silently recalculated as part of a visual migration.

## 6. Hosting, preview and data-security decision

**Choose both local development and a protected hosted preview.** Offline-only development misses real cookies, redirects, CDN caching, stream behavior, TLS and cross-origin navigation. A public staging subdomain with live customer data is also unacceptable.

Suggested hostname: `preview.mastermind-x.com` or an approved existing equivalent. This is a proposed name, not a claim that DNS, TLS or hosting exists. Reuse the current infrastructure/deployment owners; no Vercel migration or new gateway is required by the shell design.

The source inspected uses EdgeOne in front of Caddy, static output under `/opt/macro/site.served`, FastAPI under `/api/*`, same-origin tape under `/ws/tape`, and the `/sb/*` Supabase proxy. Those routes and their trust/cache rules must be preserved. Confirm actual deployed configuration, certificates and hosting capacity before an effectful change; repository comments alone do not prove live infrastructure.

Preview requirements: access-gated host, noindex/noarchive plus actual authentication, exact approved OAuth callback/return origins, secure host-scoped cookies, no assumption that browser localStorage/session cookies automatically cross subdomains. Use a test identity/data environment for write flows. Fixtures or explicitly authorized read-only production data may be used, with the same server-side entitlement checks. Billing, email, portfolio orders, collectors, schedules and mutations must not accidentally run from the preview. Never widen production cookie domains or copy production browser tokens to solve staging login.

**Critical payload boundary:** the inspected Caddy configuration deliberately serves many HTML page shells publicly while protecting paid payloads. A Next server-rendered page must not inject premium rows into public HTML, serialized component payloads, prefetched data or CDN caches. Navigation visibility is not authorization. Preserve default-deny protected assets, early premium enforcement, private/no-store user responses, and required cache variation. Existing public/SEO/indexing decisions remain separate from cosmetic redesign.

The current `@never_site` rule explicitly blocks internal mockups and research tools. Do not publish the new prototype into the customer static directory and rely only on robots.txt. Mount preview through an explicitly admitted protected route/host, without weakening the existing deny rules.

## 7. Low-downtime release and rollback

### Fix the release-unit problem before moving traffic

The current publisher's rsync uses per-file atomic rename. That prevents partial writes of an individual file; it does NOT prove that HTML, JavaScript, CSS and data references change as one coherent release. A modern shell migration needs a matched release artifact and compatibility across open tabs.

Build the candidate separately from the served directory. Use versioned/hashed assets and a release manifest linking code, route configuration and compatible public assets. Validate an immutable candidate bundle before routing any traffic to it. Keep the previous bundle and its referenced assets available during rollout and rollback. Proposed release directories/service slots must be allocated by the existing deployment owner, not guessed here.

For native routes, run the approved candidate instance beside the current one and perform health/readiness checks before routing. Do not stop the current service first. Configuration can be validated and loaded with Caddy's graceful reload mechanism; a graceful proxy reload alone does not prove the application, caches and WebSockets are interruption-free.

### Progressive rollout sequence

1. **Local fixture qualification:** fast visual/interaction tests, deterministic data contracts, no production effects.
2. **Protected preview:** all critical journeys through production-like auth, edge/proxy and assets; desktop/mobile, English/Chinese, dark/light; failure tests.
3. **Private same-origin pilot:** explicit eligible users and route allowlist, default off. Selection occurs before serving/cache lookup or bypasses shared caching safely. A query parameter is not authorization and must not contaminate shared CDN objects.
4. **Controlled route-family canary:** increase only after observed acceptance. Suggested steps such as staff -> small customer cohort -> broader cohort -> all eligible traffic are decisions under the release owner, not a pre-authorized rollout or a guaranteed schedule.
5. **Family completion:** all routes in that admitted family accounted for, no undocumented fallback, verified rollback and production receipts. Only then advance the next family.

Keep the public host and established URLs stable. A new subdomain is a preview environment, not a prerequisite customer-domain switch. Native routes and retained legacy routes can coexist behind the existing routing owner. Native-to-native transitions can be client-side; cross-application/legacy transitions may use a normal document navigation. Do not promise seamless client-state preservation across independent apps without an explicit contract.

Protect long-lived sessions: verify an old tab loading lazy chunks after a new deployment; back/forward caches; old prefetched payloads; interrupted stream; socket reconnect; session refresh; remembered filters and unsaved drafts. Verify locked framework support before using version-skew/deployment-ID features from newer documentation. A forced hard reload can lose component-local state, so it is not a complete recovery strategy.

### Rollback and operational gates

Rollback is a route/flag/config switch to the retained known-good UI artifact, followed by focused cache handling and verification. It must NOT roll back the live engine data plane, customer data, collector clocks or account database. Keep schema evolution out of the initial shell waves; any later data migration requires its own backward-compatible expand/contract plan.

Preserve `/api/*`, `/sb/*`, `/ws/tape` and the independently published `/var/lib/macro-live/public` artifacts. Do not restart engines or rsync older repository data over the live artifact plane. Never respond to a new-route auth error by falling through to an unguarded legacy asset.

Pause or roll back on unauthorized data exposure, broken login/entitlement, incorrect market/entity scope, missing saved state, broken core navigation, blank pages/chunk errors or materially worse agreed performance. Latency/error thresholds must be agreed against a measured baseline; this review has not measured live p75 metrics or downtime. The target is no planned customer outage, not an unproven guarantee of zero failed requests.

## 8. Migration waves and route-family acceptance

| Wave | Named customer capability | Retention and acceptance |
|---|---|---|
| 0 — Source/reference join | Trustworthy build inputs | Current route inventory, exact Paper references/dispositions, incumbent custody, no duplicate lifecycle; reconcile #7949 conflict rather than rebasing over others |
| 1 — Foundation + two representative routes | Navigate coherently between market overview and an existing native analysis page | Native AppShell refinement plus one retained Macro page; choose within current pilot authority or obtain the applicable expansion gate; auth/data/URLs unchanged |
| 2 — Overview, sectors and report reading | Market backdrop -> leadership -> evidence | Apply distinct overview/dense-table/reading layouts. Preserve the US/China shared-template blast radius and reports' access/export behavior |
| 3 — Discovery and company research | Prophet/screener -> company -> comparison | Reuse focused Prophet/Terminal/MO references; preserve quote-vs-assessment health, filter/selection and return state; engine programme changes remain separate |
| 4 — Cross-asset research | International, Bonds/FX, Crypto, Commodities, China and policy | Integrate admitted route families with their current owners; no new scoring or taxonomy under a shell ticket |
| 5 — Monitoring, portfolio, assistant | Save -> monitor -> return to the same evidence | Highest write/state risk: only after identity, persistence and unknown-outcome tests. Preserve account, portfolio, watchlist and Brain owners |
| 6 — Broad rollout and retirement | One coherent supported product | Every route disposition resolved; production proof and rollback accepted; remove old global menu/unused assets only when no supported route needs them |

These are dependency-based waves, not date promises or independent parallel queues. Build enough native architecture to unlock the named customer journey, not infrastructure without a consumer. Public marketing/help/legal routes and admin-only research tools require explicit dispositions; they must not accidentally inherit customer-shell scope or become exposed.

For each family, use the existing migration packet mechanism: route/template/source owner; current and desired UI; Paper source IDs; RETAIN/REFINE/RECOMPOSE/REBUILD/MERGE/DEMOTE/EXCLUDE disposition; source and data contracts; MUST NOT CHANGE list; device/theme/locale; accessibility; tests; production receipts; rollback. This document does not add a second registry.

## 9. Production-quality checklist and concrete next build packet

### Design and behavior gate

One global navigation, one active destination and one market scope; every visible action has an implemented destination/state and a return contract. Keyboard-only navigation works, modal focus is contained/restored, errors are recoverable and selected/focused/hovered states differ. No unsupported-market masquerading as an empty list. No misleading LIVE label over a delayed snapshot. No success toast before the owning write's success is known.

Test 1440 and 390 layouts plus 320 CSS-pixel reflow; 200% text enlargement and zoom/reflow behavior are different tests. English/Chinese content and real long names must fit. Genuine two-dimensional tables/charts may have controlled inner scrolling; the entire shell should not require horizontal scrolling. Sticky bars must not obscure focus or substantive content. Verify contrast with the actual composed colors, not token names alone.

### Engineering and security gate

Current locked build succeeds; existing unit/integration checks remain; route parity and authoritative payload checks pass; anonymous/free/paid/expired and outage states do not leak data. Current origin/return allowlists and CSP remain effective. Asset failures do not blank the whole shell. Heavy charts are not bundled into every ordinary page. Inspect real console/network output and distinguish allowed missing data from defects.

### Operations and acceptance gate

Current-source review and applicable independent qualification, exact candidate artifact identity, preview receipts, stable route allowlist, CDN/cache tests, oldest-supported open-tab test, rollback rehearsal and actual production checks. Field-performance targets should be measured against the existing app; no performance result is claimed by this design work. Keep #7949 Draft/HOLD until these gates, not until the document looks complete.

### Next implementation packet

Start with the existing shell owner and one isolated source worktree after current custody/admission reconciliation. Implement the minimum shared primitives (rail, contextual bar, local-page header and responsive drawer) by extending existing components, then one retained Macro overview route and one already-native non-chart route. Read their exact source dependencies before changing them. Reuse current test/fixture tools; no new auth, API, renderer, persistent state, watcher or routing control plane. Prove both directions of navigation and rollback before adding more pages.

This is the first vertical slice, not the full programme's completion. Continue through the admitted family waves until every route is accounted for and the requested customer experience is proven.

## 10. Primary technical references

External guidance was checked for the architecture review. Framework documentation may describe a newer version than the locked Terminal source; verify feature compatibility before using it.

- Next.js multi-zones: https://nextjs.org/docs/app/guides/multi-zones — same-domain coexistence, asset isolation, cross-zone document navigation.
- Next.js self-hosting: https://nextjs.org/docs/app/guides/self-hosting — proxying, caching, multi-instance/version-skew and build/runtime configuration considerations.
- Caddy command line and API: https://caddyserver.com/docs/command-line and https://caddyserver.com/docs/api — validate/adapt and graceful configuration reload; not application-level zero-error proof.
- W3C WCAG reflow: https://www.w3.org/WAI/WCAG22/Understanding/reflow.html — 320 CSS-pixel reflow and appropriate two-dimensional exceptions.
- W3C WCAG 2.2 additions: https://www.w3.org/WAI/standards-guidelines/wcag/new-in-22/ — focus not obscured and target-size requirements.
- WAI modal dialog pattern: https://www.w3.org/WAI/ARIA/apg/patterns/dialog-modal/ — modal keyboard, focus and return behavior.

## 11. Effects, recovery and remaining frontier

Confirmed effects: this companion document on existing #7949 branch; one new Paper page p-F-0; IS01 UO2-0 and IS02 USV-0 plus their owned children. Existing source/design boards, live app, data engines, DNS, services, permissions and auth were not modified. No unresolved modifying effect is known in this session. Paper working-indicator release is still pending at this checkpoint; release only these owned nodes when authoring is finished.

Paper operation prefix `investor-shell-reassessment-20261008-`: 001 page; 002 desktop; 003–005 investor rail; 006 empty workspace; 007 header insertion failed because the empty element was a Rectangle, not a Frame. Tree/node readback confirmed no children/effect from 007. Operation 008 replaced that owned empty node with a proper populated frame; 009–011 completed desktop; 012 mobile board; 013 chrome; 014 mobile content. Do not replay 007 or recreate existing boards. Current owned-node guard observed `3eb30a5646a50876344a58ba37eeaca78f85e681cd6b9351afff1188c1b65a12`; it is not a content revision.

A read-only local Git probe process 55621 timed out and was reconciled as exit 1. A later host batch for Macro root listing and Terminal repository metadata was blocked before dispatch by a safety determination. That exact action was not retried or rerouted; no general GitHub/Paper outage is inferred. Independent native source-file and Paper reads succeeded. Earlier sessions' AI/Options unknown effects were not adopted or replayed.

DO_NOT_REDO: original charter, old shell/CEO boards, existing R40–R42 states, old AI R8 writes, held duplicate transfers, denied host metadata/listing, completed 11-file identity recovery. Current remaining work in this design turn: finish the light/navigation-state specimen refinement, inspect the final owned boards and release their working indicators; update this frontier with exact results. The executable prototype/browser acceptance, route-level engineering census and production rollout belong to the next construction stage and remain explicitly unproven.
