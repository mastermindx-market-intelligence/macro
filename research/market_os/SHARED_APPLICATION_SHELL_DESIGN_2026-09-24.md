# Mastermind shared application shell — design review 01

Status: DESIGN CANDIDATE / NOT ACCEPTED FOR RELEASE.
Parent mission complete: false.
Operation: `market-os-shared-shell-design-20260924-sol-001`.
Existing organizational owner: `WS:MARKET-OS`; coordinate shared experience with existing Market Ontology integration carrier Macro #6819. This is not a new workstream, lifecycle, router, auth or state owner.

## Chairman intent and ownership

On 2026-09-24 the Chairman approved Sol taking end-to-end leadership of the shared application-shell direction, with Paper.design mockups first and collaborative refinement before site-wide release. The objective is consistent navigation and page geometry across Macro and eventual deeper Terminal convergence, not a blanket rewrite of working intelligence or a second application. Sol retains product architecture, visual adjudication and integration responsibility. Existing page/program writers retain their source custody.

The current bounded phase is design exploration. Implementation, deployment and acceptance are distinct later gates. This document and its branch do not authorize production changes or displace another writer.

## Canonical design carrier

- Paper file: MASTERMIND PAGES, `01M2WGNCX9475G79JRKJTCM08P`.
- Review page: `p-D-0`, Mastermind · Shared Shell · Review 01 · 2026-09-24.
- URL: https://app.paper.design/file/01M2WGNCX9475G79JRKJTCM08P/p-D-0
- Existing China (`p-7-1`), Sector Central (`p-9-0`), International (`p-C-0`), and other reference pages are preserved. Shared token hash observed: `5ae876bc`; no token mutation.
- US Overview: `TUD-0`, 1440 x 900; primary study exists, lower disclosure fit remains held.
- Terminal focus: `U19-0`, 1440 x 900; existing study preserved.
- Sector shared shell: `UBT-0`, 1440 x 900; composed and visually reviewed in the second pass.
- Market-switcher scaffold: `UJ4-0`; an uncomposed copy of the new Sector study, explicitly renamed NOT COMPOSED. It is not a completed popup.
- Mobile shell header: `UP4-0`, 390 x 844; status bar, header, workspace tabs and primary-read study exist. The local controls/list and full mobile journey are incomplete.
- Mobile global drawer scaffold: `UQL-0`, 390 x 844; empty artboard, explicitly renamed NOT COMPOSED. It is not a completed drawer.

The artboards are editable Paper nodes, not flat image imports. Creation, composition, visual review, interaction proof and acceptance are separate. See the cumulative Agent OS handoff for exact effects, screenshots and blocked operations.

Procedure: protected Mastermind `819abc8c23609cdded2b33f6e1bfc7854bd5c847`, skillpack 1.0.1 / bootstrap 1 compatible. INDEX, COLD_START, ACTIVE_EXECUTION, WEB_CEO_DELEGATION and CLOSEOUT were loaded at this pin; the second-pass fresh master/INDEX read returned the same commit. Initial Macro design base: `8a55040f204cd0f1c92320bae1d44e1cfd21d212`. Second-pass source inspection pins are recorded below. Direct design reason: PRINCIPAL_JUDGMENT. No worker dispatch or background execution is claimed.

## Product contract proposed for review

### Four distinct navigation responsibilities

1. Global sidebar: stable product areas, with restrained grouping and a separate All tools entry; never the entire current mega menu permanently expanded.
2. Top market selector: current viewing context, not a mutation of followed markets, enabled universe, portfolio membership, or selected security identity.
3. Workspace tabs: views inside the current area. Sector Central's page-local sidebar should converge here rather than create two permanent sidebars.
4. Local controls: filters, horizon, view and sorting; never masquerade as global navigation.

Provisional primary areas: Overview, Markets, Sectors & themes, Stocks & setups, Options, Research. Personal destinations: Watchlists, Portfolio, Alerts. Final labels and complete route disposition remain subject to inventory and Chairman design feedback; no existing tool is removed by this sketch.

### Market switching

Preserve the equivalent workspace/subview when supported. When unsupported, explain the missing equivalent and offer a relevant destination; do not silently redirect. Distinguish unsupported, access-required, missing data, stale data and transport failure. Global comparison and International are not automatically synonymous. Explicit route context should win over default market preference; Back, reload, bookmarks and multiple tabs must be predictable. Selecting a different market never silently substitutes another listing or modifies holdings/watchlists.

### Shared frame, different working modes

Overview mode favors readable synthesis. Analysis mode permits dense tables/maps with intentional internal scrolling. Focus mode collapses global navigation and maximizes the Terminal canvas. Keep one recognizable navigation language across modes without forcing the chart into a dashboard card grid.

### Visual candidate

Reuse existing Paper tokens and Inter rather than add a second design system. Graphite surfaces, subdued separators, a blue active-navigation treatment, 14–15px body text, 28px page headings, and 24–32px structural spacing. Semantic market colors remain separate from navigation. The first mockups use dark mode; existing Macro light/Chinese support is not removed or declared complete. No left-edge accent is required on every panel. Avoid repeated global/page titles and stacked competing headers.

Every sample market state, score, curve and event in the review is illustrative and must be labeled. It is not current market evidence, validated financial advice, a new signal, or approval of the represented domain semantics.

## Second-pass design decisions

### Consume the incumbent Sector design, do not create a rival redesign

The current Paper Sector reference `OOM-0` on `p-9-0` exposes Rotation / Discover / Market Breadth, a sector/theme/subsector selector, Map/List, a selected-group inspector and member drill-down. The new shared-shell Sector study adopts that structure and its clearly illustrative sample semantics. The reference remains untouched.

The first six-tab experiment on the new study was replaced with the incumbent three-view grouping. The provisional legacy mapping to prove before migration is:

| Existing job/view | Proposed home | Preservation requirement |
|---|---|---|
| Overview, map, recent rotation changes | Rotation | Keep summary, selection, map/list and changes accessible; no new ranking method. |
| Explore and discovery | Discover | Preserve filter/search and selected group on return. |
| Money & Breadth | Market breadth | Preserve participation as an independent dimension. |
| Confluence | Explicit Discover entry or retained named subview | Keep `sector_central.html#confluence` working; the exact integration is NOT settled by a mockup. |

The desktop map and inspector were reviewed together at 1440 x 900. A new inspector overflow was corrected by adjusting only that new study's spacing. The footer disclosure fits in the final Sector screenshot. Screenshot SHA256: `de4d4cc46ed62a6ed14e1433fa55beff7785fb9ede34f53306f06c9266836897`.

For mobile, prefer a readable list as an initial small-screen presentation, with Map available and the same selected group retained. This remains a proposed interaction: only the mobile shell/header/summary has been composed, not the list or drawer. Desktop-to-mobile selection preservation has not been implemented or tested.

## Source-grounded market routing — second pass

### Inspection scope and limitations

Macro source pin: `b9d23ca4bce4308fa7466c4e0f5d318168a50f6f`.
Read: `templates/nav_market.js`, lines 145–470; blob `4edee693e1e6d4391de3482b2a618057df686e56`.
Terminal source pin: `145bfbe4c8ea0da04658cbbe05879c84c990721b`.
Read: `terminal/lib/markets.ts`, lines 1–100; blob `6168662381b7d0a32af90eb262ae2c8862883a1b`.

These are source-navigation observations, not live route, entitlement, subview or data-coverage proof. This is not the completed all-page inventory.

| Workspace family | US | China | Hong Kong | Canada | International |
|---|---|---|---|---|---|
| Market overview | `macro.html` | `china.html` | `hk.html` | `canada.html` | `intl.html` |
| Stock dashboard | `us_stocks.html` | `china_stocks.html` | `hk_stocks.html` | `canada_stocks.html` | `intl_stocks.html` |
| Sector/theme destinations declared in the inspected menu | `sector_central.html` | `sector_central_china.html` | `baskets_hk.html`, `allocation_hk.html` | `baskets_canada.html`, `allocation_canada.html` | `baskets_intl.html` |

**Critical distinction:** the presence of thematic baskets or narrative rotation is not proof of the same Sector workspace or subview. Do not synthesize a `sector_central_hk.html` or `sector_central_canada.html` URL, and do not call either market unsupported merely because the inspected menu lacks a same-named page. Qualify the actual equivalent through the owning route and consumer.

`china.html` and `china_intel.html` are separately declared destinations. The shell migration must preserve their distinct jobs until their owners explicitly reconcile any consolidation; the attractive China Intelligence mockup alone does not replace the China macro dashboard.

The International menu names `intl.html` as the World Dashboard, with `markets.html` separately named Global Market Cycles and `country_cycles.html` separately named Country Cycles. Preserve those jobs and current International redesign ownership. Do not create a duplicate global landing page or move the accepted `intl.html` work to `markets.html`.

### Existing preference semantics must survive

Terminal's shared contract distinguishes `market_focus`/followed markets, enabled markets and a derived compatibility home. `MarketId` includes `intl` and `crypto`; `FollowId` uses `global` rather than `intl`, and crypto is not a followed-country target. Critically, `global` maps to the international ranking bucket, not automatically the whole universe. The market selector must never write those preferences just to display a different country.

A view of one security is not equivalent to a market-filtered discovery page. Changing surrounding market context must not replace the selected listing or silently pick another cross-listing. An intentional request to switch security must be separate and owner-resolved.

### Proposed navigation behavior, not a new state service

The following is a UI/route contract for the existing navigation owners, not a lifecycle, database or second router:

- Supported equivalent: navigate to the admitted target workspace, preserve only compatible subview/filter values, and expose the new market and fresh loading state together.
- No qualified equivalent: keep the current view until the user chooses from named alternatives. A basket, overview and stock board are not interchangeable fallbacks.
- Equivalent but access required: retain the target identity and show the existing entitlement gate; do not substitute another country's data.
- Target data unavailable or stale: show its typed state. Never paint old-country content under a newly changed flag.
- Capability lookup failed or unknown: retain current context and disclose that the destination could not be confirmed; unknown is not unsupported.
- Personal workspace: holdings and watchlists stay global unless an explicit local view filter is selected. No membership mutation occurs.
- Direct URL/Back/reload: explicit route context wins over a default market preference. Independent tabs must not overwrite one another's viewing context through a new global preference write.

No extra confirmation is required for a qualified ordinary market switch. An additional choice is justified only when the requested equivalent is absent or unresolved. Country options should carry destination context before selection where the owning route metadata can provide it.

## First useful vertical after design approval

Market overview -> sector/theme -> one canonical security in the existing Terminal -> save through the existing watchlist owner -> return to the exact originating workspace. Include market switching, direct entry, reload/back, mobile navigation and stale/access-required states. Preserve the distinction between attention and ownership. Existing Market OS, identity, watchlist, portfolio, origin-navigation and Terminal shell owners are consumed, not replaced.

## Migration boundaries

Inventory source template families and interactive exceptions rather than equating rendered URL count to rewrite count. Every existing destination receives an explicit retained/consolidated/redirected/exception disposition. The inventory denominator must include shared template links, adaptive JavaScript menus, conditional rows, contextual entry points and existing redirect/hash routes; the inspected `MARKET_MENU` alone is insufficient. Keep working legacy URLs during rollout.

Introduce shared frame adapters into current Macro and Terminal stacks before deciding whether runtime consolidation is justified. Navigation descriptions should be reconciled through the existing owning source and rendered consistently, not copied into a third manually maintained registry or database. Public marketing/editorial entry points need not adopt the workspace shell.

One source writer owns shared chrome during implementation. Existing China, International, Sector Central, Prophet, mobile, options and Terminal programs keep their content/model scope. Reconcile their exact active paths before any implementation commission. No full-site cutover until real production-path/browser proof and rollback are accepted.

## Discriminating acceptance cases — specified, not executed

| Case | Required outcome |
|---|---|
| US Sector -> China | Use the admitted China destination; preserve a subview only after equivalence is proven. |
| Sector -> HK/Canada with no qualified equivalent | Explicit destination choice, no fabricated URL or silent basket substitution. |
| US Options -> another country | Preserve actual capability/rights limits; do not relabel US options data as local. |
| User follows US and HK, then views China | Followed set, enabled set and watchlist/portfolio membership remain unchanged. |
| Two tabs view different countries | Back and refresh retain each tab's explicit route context. |
| Open a member in Terminal and return | Exact listing and originating workspace/selection survive through existing owner paths. |
| Saved `#confluence` link | Still reaches the preserved job after the three-view regrouping. |
| Country switched while target data is delayed | New country never labels old country's cached content. |
| Country capability/entitlement unknown | Unknown/access states remain explicit, never collapsed to unsupported or empty success. |
| Mobile drawer keyboard/assistive use | Focus enters, Escape/close returns to trigger, background is not focusable while open; browser proof is owed. |
| Narrow EN/ZH and both supported themes | Long labels, focus indicators, controls and errors fit without changing domain semantics. |

## Review criteria

- Can users tell which workspace and market they are in?
- Does switching market preserve the task without changing investments or preferences?
- Does Terminal retain selected listing, return path and usable chart space?
- Do workspace tabs replace rather than compound competing navigation?
- Are keyboard focus, mobile navigation, text contrast and realistic long labels usable?
- Are missing, stale, denied and unsupported states explicit?
- Are sample data and design-only status unmistakable?

The current phase delivers reviewable mockups and the integration contract. It does not complete the parent mission. The market popup, complete mobile set and China shared-shell composition remain unaccepted/unbuilt as documented in the cumulative handoff. A final implementation plan follows accepted design and fresh source-custody reconciliation.
