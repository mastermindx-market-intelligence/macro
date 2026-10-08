# Shared Shell + Jinja surfaces — implementation plan

Status: ACTIVE DESIGN/IMPLEMENTATION PLAN / SAME CARRIER / DRAFT-HOLD.
Date: 2026-10-08.
Parent: `WS:MARKET-OS`.
Operation: `market-os-shared-shell-design-20260924-sol-001`.
Carrier: Macro PR #7949 / `sol/market-os-shared-shell-design-20260924`.
Paper: MASTERMIND PAGES `01M2WGNCX9475G79JRKJTCM08P`, page `p-D-0`.

## Chairman ruling

The product boundary is the **Mastermind shared application shell**, not a frontend
framework. Mature Jinja research surfaces may remain Jinja and appear as first-class
workspaces inside the same user journey as Terminal capabilities. A good existing
dashboard is not rewritten merely to make its implementation technology uniform.

The China Macro Dashboard is the first reference surface for this rule: preserve its
existing information design and intelligence semantics, put it under the shared shell,
and let Terminal-owned capabilities open in-place without forcing the user into a
second product or losing the originating research context.

This ruling does not transfer data, signal, auth, alert, watchlist, portfolio, route,
or persistence ownership. It establishes composition and navigation mechanics only.

## Target architecture

```text
Mastermind shared shell
  |
  +-- Macro/Jinja research surface (host document)
  |     +-- China / US / HK / Canada / International dashboards
  |     +-- existing page-local JS + Plotly + bilingual/theme behavior
  |     +-- shared global chrome / All tools / search
  |
  +-- Terminal portal (in-shell capability layer)
        +-- chart
        +-- analysis
        +-- options
        +-- other qualified Terminal routes
        +-- existing Terminal auth/user-state owners
```

For the first adoption the Jinja page is the host document. Terminal remains isolated
at `app.mastermind-x.com` and is projected through the existing
`MDXTerminalOverlay` bridge. This avoids a Jinja-in-iframe wrapper, avoids CSS
reimplementation, preserves the mature dashboard exactly, and still gives the user one
continuous application experience.

A later native React composition is permitted only when it removes a real product
constraint. It is not a prerequisite for shared-shell adoption.

## Existing mechanisms to reuse

1. **Shared product chrome:** `_site_nav.html.j2`, `_navlinks.html.j2`,
   `navigation-refresh.css`, `nav_market.js`, `theme.js`.
2. **All tools shell:** the opt-in shared-shell controller already carried by PR #7949.
3. **Terminal portal:** `theme.js -> MDXTerminalOverlay -> terminal_overlay.js`.
   The bridge already preserves the Macro document, scroll position, same-document Back
   behavior, desktop warm iframe, mobile remount behavior and strict postMessage origin.
4. **Terminal origin navigation:** Terminal already understands `from=macro` and
   `ret=<origin>`; the shell does not mint a second return router.
5. **Existing page registry:** `data/product_experience/page_registry.json` remains the
   route census. No shared-shell route database is added.
6. **Existing user-state owners:** auth, watchlist, saved work, alerts, portfolio and
   entitlements stay with their incumbent owners.

## New shared-shell contract

### A. Jinja surface contract

A Jinja page is eligible for shared-shell adoption when:

- its existing content/view-model remains authoritative;
- it uses the shared product chrome rather than a page-local third header;
- shared-shell enablement changes the outer frame, not the intelligence calculation;
- existing deep links and page-local state remain valid;
- dark/light and EN/ZH behavior remain intact;
- unsupported destinations are shown as unsupported/unavailable rather than synthesized.

No fragment renderer or duplicate React component tree is required merely to qualify a
Jinja surface.

### B. Portal launch contract

Every in-shell Terminal launch carries two separate concepts:

- **launch origin** — visual animation geometry;
- **return focus** — the control that must regain keyboard focus when the portal closes.

They must not be inferred from the same mutable DOM state. Search is the discriminating
case: closing search intentionally blurs/collapses the search UI before Terminal mounts,
so `document.activeElement` is not the originating control.

The bridge therefore accepts an explicit `returnFocus`. It captures that target before
locking the dashboard and resolves it only after `inert` / `aria-hidden` have been
removed. If the original node no longer exists or cannot receive focus, it selects a
visible shared-navigation fallback. It never restores to BODY or a hidden iframe.

Mobile keeps its existing no-refocus close behavior because WebKit scroll restoration is
the stronger invariant there.

### C. Research-context contract

The shell transports context; it does not own a second persisted context store.

Use existing route/URL and portal state for:

- originating route / return URL;
- selected market where already represented;
- exact security/listing when opening Terminal;
- locale/theme from the existing UI owners;
- exact scroll/focus restoration in the host document.

Additional context fields are admitted only when a real consumer requires them. Never
duplicate market preference, enabled markets, watchlist membership, portfolio state,
alert state or saved-research state in the shell.

### D. Action contract

Jinja controls may progressively invoke shell-owned capabilities without becoming owners
of those effects. The long-term declarative vocabulary may include actions such as:

- open chart / instrument;
- open analysis;
- ask Brain with exact page context;
- save research;
- create alert;
- open evidence.

Each action delegates to the existing canonical owner. A `data-*` attribute is a
presentation/event binding, not a new lifecycle or persistence plane.

## Delivery phases

### Phase 0 — harden the existing portal return boundary

Implement the explicit return-focus contract in the existing bridge and pin it in the
existing overlay contract tests. This phase is source-only and does not broaden the
pilot or release the PR hold.

DONE WHEN:
- ticker-search -> Terminal has an explicit search-trigger return target;
- normal links preserve their invoking control by default;
- restoration happens only after background inert/aria-hidden is removed;
- disconnected/hidden targets cannot be focused;
- desktop restores focus; mobile preserves its incumbent no-refocus path;
- existing Back, scroll, warm-desktop and mobile-remount contracts remain unchanged.

### Phase 1 — China shared-shell canary, no redesign

Adopt `/china.html` into the same shared chrome/All-tools family while preserving the
existing China composition pixel-for-pixel except for the shared outer shell.

The current open China mobile-control PR #7618 touches `templates/china.html.j2`.
Reconcile that incumbent before changing the template. Prefer builder/context opt-in
when it avoids a content-template collision, but still regenerate and visually prove the
actual emitted page before release.

DONE WHEN:
- China is reachable as a first-class market workspace in the shared shell;
- no duplicate nav/header appears;
- the existing China risk/regime/index/event composition is unchanged semantically;
- desktop 1440, tablet, 390 and 320 remain usable;
- EN/ZH and light/dark remain accepted;
- direct URL, reload and bookmarks remain valid.

### Phase 2 — China -> Terminal -> exact return

Use existing Terminal-covered China security links as the first end-to-end workflow.

DONE WHEN:
- a China security opens Terminal in-shell;
- the exact listing, not a translated label, is handed off;
- Escape, close control and browser Back return to the same China document;
- scroll and desktop keyboard focus are restored;
- query/filter state is not silently reset;
- warm reopen is correct.

### Phase 3 — contextual Terminal capabilities

Add only qualified routes/actions: chart first, then Analysis/Brain and other capabilities
where their existing owner can consume the context. No blanket route exposure.

DONE WHEN each capability proves:
- exact context handoff;
- owner/auth/entitlement behavior;
- loading/denied/unavailable states;
- exact return;
- no duplicate persistence or action owner.

### Phase 4 — personal effects

Connect save/watchlist/alert/portfolio actions only through the existing authenticated
owners and authoritative readback. Prepared is not Enabled. Unknown write outcome is
reconciled on the original record before retry.

### Phase 5 — estate rollout

Roll out by existing page-registry archetype/template family, not one URL at a time and
not by rewriting pages into React. Keep public/editorial surfaces on their appropriate
frame where the application shell adds no value.

## Acceptance matrix

For every adopted surface prove at minimum:

- desktop dark EN;
- desktop light ZH;
- mobile 390 dark EN;
- mobile 390 light ZH;
- 320 narrow stress;
- doubled application typography / enlarged text;
- direct entry + reload + bookmark;
- Terminal open + Escape + close + Back;
- exact scroll return;
- desktop focus return and next-Tab order;
- target removed/hidden while portal is open;
- auth required / denied / unavailable;
- stale or partial Macro data remains visibly stale/partial;
- no market-preference, watchlist, portfolio or alert mutation from navigation alone.

## Non-goals

- no China visual rewrite;
- no second Macro engine or data contract;
- no second application router;
- no second auth/session owner;
- no shell-local saved-work/watchlist/alert database;
- no copied Terminal chart implementation in Macro;
- no forced repository/framework consolidation;
- no site-wide opt-in before the first canary is proven;
- no merge/deploy from this document alone.

## Current release boundary

PR #7949 remains DRAFT / HOLD-FOR-SOL. Current Macro main has advanced beyond the
candidate and the existing branch has merge conflicts in historical fixture receipts and
`site/research_screener.html`; these are integration/reconciliation work, not permission
to overwrite fresher main artifacts.

The first independent source lane is the portal return-focus hardening above. China
opt-in follows after its incumbent #7618 collision and emitted-page proof are reconciled.
