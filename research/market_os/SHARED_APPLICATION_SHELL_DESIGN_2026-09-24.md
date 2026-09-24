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
- New review page: `p-D-0`, Mastermind · Shared Shell · Review 01 · 2026-09-24.
- URL: https://app.paper.design/file/01M2WGNCX9475G79JRKJTCM08P/p-D-0
- Existing China (`p-7-1`), Sector Central (`p-9-0`), International (`p-C-0`), and other reference pages are preserved. Shared token hash observed: `5ae876bc`; no token mutation.
- First overview artboard: `TUD-0` (US Market Overview, 1440 x 900).
- Independent focus-mode artboard: `U19-0` (Terminal focus, 1440 x 900).
- Both artboards are editable Paper nodes, not flat image imports. Their completeness and final screenshots are recorded in the continuation handoff, not inferred from creation.

Procedure: protected Mastermind `819abc8c23609cdded2b33f6e1bfc7854bd5c847`, skillpack 1.0.1 / bootstrap 1 compatible. INDEX, COLD_START, ACTIVE_EXECUTION, WEB_CEO_DELEGATION and CLOSEOUT read at this pin. Source reference: Macro `8a55040f204cd0f1c92320bae1d44e1cfd21d212`. Direct design reason: PRINCIPAL_JUDGMENT; this iteration determines shared architecture and visual behavior and has not been frozen into routine build tasks. No worker dispatch or background execution is claimed.

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

## First useful vertical after design approval

Market overview -> sector/theme -> one canonical security in the existing Terminal -> save through the existing watchlist owner -> return to the exact originating workspace. Include market switching, direct entry, reload/back, mobile navigation and stale/access-required states. Preserve the distinction between attention and ownership. Existing Market OS, identity, watchlist, portfolio, origin-navigation and Terminal shell owners are consumed, not replaced.

## Migration boundaries

Inventory source template families and interactive exceptions rather than equating rendered URL count to rewrite count. Every existing destination receives an explicit retained/consolidated/redirected/exception disposition. Keep working legacy URLs during rollout. Introduce shared frame adapters into current Macro and Terminal stacks before deciding whether runtime consolidation is justified. Public marketing/editorial entry points need not adopt the workspace shell.

One source writer owns shared chrome during implementation. Existing China, International, Sector Central, Prophet, mobile, options and Terminal programs keep their content/model scope. Reconcile their exact active paths before any implementation commission. No full-site cutover until real production-path/browser proof and rollback are accepted.

## Review criteria

- Can users tell which workspace and market they are in?
- Does switching market preserve the task without changing investments or preferences?
- Does Terminal retain selected listing, return path and usable chart space?
- Do workspace tabs replace rather than compound competing navigation?
- Are keyboard focus, mobile navigation, text contrast and realistic long labels usable?
- Are missing, stale, denied and unsupported states explicit?
- Are sample data and design-only status unmistakable?

The current phase delivers reviewable mockups and the integration contract. It does not complete the parent mission. A final implementation plan follows the accepted design and fresh source-custody reconciliation.
