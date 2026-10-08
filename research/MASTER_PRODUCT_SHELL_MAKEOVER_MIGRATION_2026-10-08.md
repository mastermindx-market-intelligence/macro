# Mastermind full-site makeover and shared-shell adoption

Status: CHAIRMAN-SCOPE CORRECTION / DESIGN + IMPLEMENTATION CHARTER / NOT PRODUCTION ACCEPTANCE.
Date: 2026-10-08.
Protected procedure: Mastermind master `c7e47c859eb2925c5626931fd511800773ba09ac`,
`mastermind.sol_skillpack.v1`, version 1.0.1 / bootstrap 1.
Current continuity carrier: Macro PR #7949, `sol/market-os-shared-shell-design-20260924`,
operation `market-os-shared-shell-design-20260924-sol-001` (shared-shell design lane only).
Governing migration mechanism: `research/MASTER_PRODUCT_DESIGN_SYSTEM_V1.md`,
`research/DESIGN_MIGRATION_FACTORY_V1.md`, `research/REFERENCE_INTEGRITY_GATE_V1.md`,
`data/product_experience/page_registry.json`.
`WS:MARKET-OS` remains a product-consumer workstream; it does NOT acquire the whole
website makeover or displace other design/implementation owners.

## 1. Chairman outcome: redesign the *entire* relevant site, then integrate it

The September shared-shell prototype and the first Jinja/China feasibility plan are
SUBSETS, not the full commission. The outcome is a cohesive, visually redesigned
Mastermind product spanning the current Macro website and native Terminal capabilities.
Use the current Paper direction to decide which existing elements are retained, refined,
recomposed, merged, demoted or rebuilt. The added global left sidebar shrinks the
available workspace canvas, so page-level layout redesign is mandatory. Preserve strong
working panels and intelligence where appropriate, but never freeze the old composition
merely because its renderer is Jinja.

All current customer-facing routes are in the migration inventory. Generated route
families count by owning template/archetype; do NOT spawn one unrelated migration for
each generated ticker. Public marketing/editorial pages also get the design makeover,
but an authenticated workspace sidebar is NOT automatically appropriate on public
SEO/marketing routes. Internal/admin/utility/fragment routes require explicit
classification, not silent exclusion or blanket shell injection.

10/10 DONE_WHEN: every eligible current route/family is mapped to an approved
Paper/reference archetype and a verified landing or explicit justified exception;
the redesigned interface fits actual shell content widths across devices/themes/locales;
end-to-end user journeys across Macro and Terminal remain functional; no data,
signal, calculation, state, access or publication regressions; each migrated family
has RIG/design, CI, browser and production receipts; full rollout and navigation
availability are separately verified. Neither a beautiful Paper board nor green
source tests alone satisfies this outcome.

## 2. Grounded inventory and design authority

The current `page_registry.json` snapshot (generated 2026-09-04; refresh at first
implementation admission, do not assume it is still exhaustive) has 331 entries,
314 marked live, including 296 Macro, 13 Terminal and 5 Mastermind entries.
These are route and generated-family records, NOT 314 independent page templates.
Families span marketing, editorial, command centers, discovery boards, regime
dashboards, instrument analyzers, intelligence desks, monitors, utilities and
chart workspaces. Preserve per-route deep links and payload/access boundaries.

Observed Paper reference families (candidate designs, NOT auto-approved):
- `Mastermind OS` file `01M3NRCX55B452A12819WNE1RH`;
  `p-8-0` Global Shell + Navigation; current shell boards
  `H7R-0` desktop and `IOE-0` mobile; older
  `REF-SHELL-*` studies are reference, not newer design authority.
- `MASTERMIND PAGES` file `01M2WGNCX9475G79JRKJTCM08P`;
  `p-5-0` archetype/component/coverage/link maps, `p-D-0` legacy shared-shell
  study, plus current/refinement pages for China, Intelligence Hub, Bonds,
  Forex, Commodities, Crypto, News, Sector, Earnings, Confluence and more.
  The existing legacy desktop specimen has 216px sidebar and 1224px workspace
  in a 1440px artboard: a feasibility datum, NOT an unconditional current
  shell dimension.
- `International Markets` file `01M3P1TW5Y3XWQC37ADDS8K5AG`,
  `p-1-0` R10 current build and explicit responsive/state specs.

**Source disagreement to adjudicate before global nav migration:** the older
Market-product IA uses Today / Discover / Analyze / Monitor / Research / Portfolio,
while the current Mastermind OS app shell uses Today / Projects / Inbox /
Conversations / Knowledge for a different principal job. Reuse a shared visual
shell and product grammar without accidentally replacing investor navigation
with executive/CEO navigation. Identify the correct market-user shell and any
intentional cross-product context switch from actual current designs; no
Paper document name silently wins this semantic decision.

The `p-5-0` Paper link map explicitly says its legacy Shared Shell page is
reference-only and points global shell/navigation to Mastermind OS; do not
treat `p-D-0` as present final approval. RIG approval is per reference/family,
not inferred from board names, asset presence or Paper visual polish.

## 3. Product architecture (one coherent shell, multiple existing owners)

Conceptual shell:
```text
Mastermind customer shell
  global navigation / sidebar / account / search / market context
  page heading + context actions
  workspace content viewport (width after shell chrome)
    Macro/Jinja pages transformed per approved archetype
    Terminal-native Next.js workspaces (chart, analysis, options, portfolio)
    context-dependent inspector / panels / dialogs
  global overlay and accessible feedback plane
```

This is a product-composition contract, NOT permission to create a new identity,
router, navigation registry, auth store, watchlist, alert, portfolio, data or
signal owner. Preserve incumbent Macro Jinja builders, Terminal AppShell,
`originNav.ts`, the guarded `MDXTerminalOverlay`, existing route inventory,
theme/i18n ownership and `site_access` boundaries until a specific replacement
has separate proof and approved source custody.

**Critical engineering architecture gate:** resolve HOW Jinja joins the actual
shared-shell host with a bounded working spike, not a declaration that Jinja must
host the whole product. Compare:
A. shell chrome composed around full Jinja responses using existing shared Jinja
   partial/source contracts (route transitions may initially reload);
B. shell-owned workspace slot / SSR-fragment adapter with legacy script/chart
   lifecycle isolation and first-party deep-link handling;
C. an iframe fallback for genuinely unported content only.
The target is ONE visible navigation shell, no nested duplicate header, and real
container-width-aware content. Permanent blanket cross-origin iframe wrapping
is *not* a foregone conclusion: measure CSP/auth, focus, history, keyboard,
internal scroll, height, plot/chart resize, locale/theme propagation, SEO,
postMessage security and portal placement. A native Next.js rewrite of every
Jinja page is likewise not a prerequisite. Select the composition lane only
after desktop/mobile interactive prototype evidence; record one design/technical
decision in the existing governance owners.

Public marketing pages retain their existing public-chrome family, redesigned to
the same visual system, without accidentally requiring investor login.

## 4. The non-negotiable viewport/recomposition contract

Design against the **workspace container** after the left rail, padding,
local toolbar and any right inspector, never `100vw` or browser window width.
Choose actual expanded/collapsed rail widths from the current approved shell,
not the 216px legacy specimen by default. Validate at shell states, not simply
1280px/1440px breakpoints.

Every migrated page gets a before/after module-disposition table and explicit
layout for these space classes:
- wide workspace: multi-column scan and linked inspector where justified;
- reduced desktop workspace: prioritize decision panel, compress/stack
  secondary panels, never shrink text into illegibility;
- tablet/compact: collapse navigation, preserve accessible local tools and
  convert side inspectors to an intentional panel/sheet;
- phone 390/320: purposeful vertical narrative, bottom/drawer navigation as
  approved, readable charts and scroll-contained tables;
- enlarged type / zoom: component reflow, no clipped buttons, tooltip traps,
  hidden actions or global horizontal scroll.

Responsive CSS must use page/workspace container queries or equivalent actual
available-width measurement. Grids need `minmax(0, 1fr)` and bounded intrinsic
minimums; data tables may scroll *inside their panel* while the whole document
must not horizontally overflow. Charts/Plotly/SVG have resize and hidden-tab
activation lifecycles. Floating panels cannot render under a rail, fixed header
or parent `overflow:hidden`. Avoid creating a second root scroll owner:
the existing Terminal portal records document scroll and body lock.

Maintain two deliberately designed themes, native EN/ZH, directional color
semantics, chronology/as-of, data stale/partial/denied states, keyboard/focus,
`prefers-reduced-motion`, direct URLs/bookmarks, and user-owned filters.

## 5. Design-system-driven family dispositions

Use the existing registry and Design Migration Factory, not a new route ledger.
Each named row/family receives one of RETAIN, REFINE, RECOMPOSE,
REBUILD, MERGE-INTO, DEMOTE-TO, or EXCLUDE-WITH-REASON, with the exact target
and accepted reference. This is **component/region-level**, not a single yes/no
on an entire page. Key starting families:

| Family | Representative destinations | Design intent |
|---|---|---|
| Command / macro regime | US Macro, China, HK, Canada, Intl, Bonds, Forex, Commodities, Crypto | Retain verified data logic; redesign page hierarchy, risk/decision panels, sidebar-compatible charts; adopt region-specific Paper references |
| Discovery / setups | Prophet/US stocks, China stocks, Confluence, allocation, heatmaps, sector screens | Recompose dense controls, cards, tables and local refinements for sidebar/inspector widths; preserve distinct signal populations |
| Sector / themes | Sector Central, China Sector, baskets, theme/rotation details | Use native view count, lazy consumers and scoped filters; avoid fake US/China equivalence |
| Intelligence / research | Intelligence Hub, China Intelligence, News, Earnings/Dossiers, Policy, Market Memory, reports | Redesign deep-reading vs decision modes, evidence inspector and source states; preserve actual provenance/data contracts |
| Instrument / chart | per-security dossiers/lookup, Terminal charts, options, company analysis | Deep-link and exact listing handoff to native owner; retain chart/quote and user-state truth; no copied trading engine |
| Monitor / personal | alerts, watchlists, portfolio, notification/attention desks | one authenticated persistence owner; typed prepared/denied/saved/failed/uncertain states |
| Public / editorial | landing, about, learning, methodology, marketing/SEO pages | redesign public chrome; preserve canonical URLs and crawlability; do not force the signed-in left rail |

An approved Paper design governs LOOK and deliberate hierarchy, but is not a
new source for calculated values, state authority or backend behavior.

## 6. Implementation waves: design and code together

**Wave A — design mapping and source census (blocking for bulk rollout).**
Refresh the registry and current Paper file/page/board names, record exact
reference-integrity status and source ownership, classify whole-site families,
flag unavailable/unfinished boards, and map every Tier-1 product journey.
Independently assess incumbent PR/file collisions. Result: existing-registry
coverage and migration packets; no duplicated control plane.

**Wave B — shell primitive and reduced-canvas proof.**
Confirm market-user IA versus Executive OS IA and inspect current SH1/Mobile
Paper boards. Choose geometry, collapse behavior, page-slot boundaries and
route/context contracts. Implement ONE constrained real-code sandbox for the
approved shell, with one Jinja regime surface and one dense
discovery/chart surface. It must prove reduced-canvas reflow, shell overlay,
search, theme, locale, deep links, account/denied states and exact return.
Do not widen to the estate until both archetypes pass.

**Wave C — flagship family migration.**
Approve first-of-family RIG reference and packet before coding. Prioritize
Today/US Macro, China/Asia and World regimes; stocks/Prophet, Sector,
Confluence, Intelligence Hub and Terminal handoff. Keep source owners
exclusive by template/selector region; use separate PRs per family.

**Wave D — research and asset-class expansion.**
Migrate News, Earnings, reports/evidence reading, Bonds, Forex,
Commodities, Crypto, International deep pages, specialty intelligence
desks and per-instrument analyzers using accepted archetype references.
Generated routes migrate by common owning template and one exemplar
per unique state.

**Wave E — full customer estate, personal actions, public pages.**
Migrate remaining eligible families and public-chrome redesign,
verify authenticated watchlist/alert/portfolio and account/entitlement
effects via their existing owners, close nav orphanage and explicit
route exceptions. No page is counted finished because its parent menu
looks redesigned.

**Wave F — canary, parity, progressive publication.**
Feature-flag or route-family gate individual new experiences, preserve
old presentation as bounded rollback, verify exact published bundle and
rendered HTML/Next build, real browser behavior and production identity.
Complete only after registry/RIG coverage and end-to-end journeys are proven.

## 7. Every builder receives the existing migration packet

Use `research/DESIGN_MIGRATION_FACTORY_V1.md` §2, one packet/PR per
route or template family:
- exact route/template/builder + governing selectors and region IDs;
- current Paper artboard and RIG-RECEIPT, dark/light/EN/ZH references;
- primary user question and full module dispositions (KEEP/CHANGE/MOVE);
- chosen shell geometry and wide/compact/phone compositions;
- existing features, state data, access, as-of, action ownership MUST-NOT-CHANGE;
- four degraded states + dense stress + 320 and enlarged-type treatment;
- exact code paths, prohibited sibling paths and current competing PRs;
- visual, interaction, perf, semantic and rollback acceptance.

Builders execute accepted packets; they do not invent a new look. The same
owner must compare live output with Paper and reject visuals that merely render.
Do not use Paper as a source-code generator whose JSX supersedes working Jinja
or native state ownership. Approved components/tokens and native DOM keep
their appropriate runtime owners.

## 8. Acceptance is product proof, not source presence

Mandatory evidence for each first-of-family migration:
- desktop 1600/1440/1280 with rail expanded/collapsed and inspector open/closed;
- compact 1024/768, mobile 390/320, native accessibility/text enlargement;
- EN/ZH and distinct deliberate light/dark appearances;
- sidebar, content and overlays do not collide; no global horizontal scroll;
- deep-link, refresh, Back/Escape, focus restore, screen-reader labels,
  mobile gestures and sticky-scroll preservation;
- real populated, dense, empty, stale, partial, error, loading, guest,
  access-denied and unavailable states;
- data-vintage/count/content parity and no unauthorized signal logic mutation;
- exact authenticated persistence readback where user effects are involved;
- chart/Plotly layout resize, hidden-tab/lazy consumer readiness, chart return;
- production URL proof tied to merged/prerendered bytes, no synthetic-only PASS;
- performance + no generated render-budget regression.

Use existing capture harness, design-system ratchets and RIG review. Existing
CI/green tests prove only their observed scenario; a Paper board proves static
design intent, not a usable shipped page. Same-day automated rollout should not
skip independent review/flagship approval.

## 9. Existing live implementation carriers — no duplicate builders

Current source-custody reconnaissance (2026-10-08) found real overlapping
implementation work already in motion. These are **not** new authorizations,
worker starts or accepted design references:

| Carrier | Current status and affected family | Rule |
|---|---|---|
| Macro #7949 | DRAFT/HOLD, shared nav / shell candidate, conflicted with main | existing shell design carrier; no Ready/merge/deploy |
| Macro #8527 | DRAFT, International Paper workspace / Compare / Inspector inside existing Jinja | potential first regime-family implementation adopter; consume/review its existing work, do not open a second `intl.html.j2` builder |
| Macro #8241 | DRAFT/HOLD, Paper Bonds R11 duration interaction | preserve Bonds owner; inspect accepted source and browser gaps before shell reflow |
| Macro #7618 | DRAFT, China mobile control-target work | incumbent `china.html.j2` writer |
| Macro #8196 | DRAFT, China economy + dialog integration | additional China source collision; reconcile scope before a broad China remake |
| Macro #8428 | DRAFT, Confluence empty-source/share-card consumer fix | do not overlap Confluence template/builder until this consumer repair is reconciled |

**Pilot-selection implication:** International is a high-value existing Paper-to-Jinja
source candidate. Test the shell composition against that live carrier *with its
original owner* after admission; do not replay its implementation on #7949.
For the dense discovery archetype choose a qualified nonconflicting target or
wait until the Confluence writer is reconciled; the global shell can be tested
using a bounded fixture without modifying its incumbent content engine.
The first template families `dashboard.html.j2` (US Macro + US Stocks modes)
and `china.html.j2` (China Macro + China Stocks modes) must be verified in
**both** their output modes. A single-regime screenshot does not accept the
paired stocks route.

Before each migration wave, recheck live GitHub PR state and the existing
`docs/ACTIVE_BUILD_MAP.md`. Neither the 2026-09-04 registry snapshot nor
this census is a durable source lease. UI changes can be implemented by
admitted owners in independent template scopes; source overlap or unresolved
effects requires original-carrier reconciliation, not another session taking
over the same files.

## 10. Immediate frontier and explicit holds

- **Done now:** Chairman broad-scope ruling; whole-site framing; Paper roster
  and source registry census recovered; portal focus-boundary source hardening
  separately present on held PR #7949.
- **Not done:** approved end-to-end market-shell composition, full Paper/RIG
  reference qualification, final responsive shell sizing, family rebuilds,
  browser proof, migration PR merges, production/customer acceptance.
- **Current engineering blocker:** PR #7949 is DRAFT/HOLD-FOR-SOL and
  `mergeable_state=dirty` against moving Macro main. Do NOT reinterpret
  this charter as release permission. Its candidate contains historical
  files that require fresh-main conflict reconciliation. China mobile PR
  #7618 is another incumbent source writer.
- **Paper scope blocker:** the current Mastermind OS SH1 global shell includes
  a different user/job IA than the market-only navigation; adjudicate
  semantic composition before adopting its labels wholesale.

**Next bounded action:** capture the current SH1 desktop/mobile layout
contract and one dense Macro/Jinja plus one Terminal-native user journey,
then freeze a first-of-family Paper/RIG migration packet with exact
available-width reflow specs. Reconcile existing PR/file custody before
making implementation edits. Let independent inventory/review progress
without pretending the held branch is shipped.

This plan is a design/build charter under the existing migration factory,
not an alternative governance, job, route, memory or publication owner.
