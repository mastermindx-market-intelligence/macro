# Macro Dashboard interaction polish — 2026-11-09

## Intended experience

Make the existing Jinja dashboard feel predictable and responsive in its frequently used search and detail-panel journeys. Keep the present renderer, navigation, access, market data, and dialog owners. This is a concrete interaction and presentation upgrade, not a framework migration or a claim that every historical UI defect is resolved.

Authority: current Chairman request for Macro Dashboard SaaS polish. Governing Mastermind pin: `494d095813dad415938800fa0e4d2719497738fa`. Acquired Macro base: `73bbade8efdb464279a1693a6e2c72a39c1790c9`. Owned operation/branch: `macro-saas-polish-20261109-astra-01` / `sol/web-macro-saas-polish-20261109-astra-01`.

## Reproduced friction

The existing authenticated live Macro page reproduced two search defects: Enter on the page-2 button left page 1 selected, and Escape while pagination held focus left search open. Source inspection found that results, paging, and retry activated on mousedown alone. Result names were 8.5px in the approved search material. Dialog interiors could remain hidden for up to 520ms through staggered entrances, and both the panel and its body owned scrolling.

The first 17-case Chromium regression set was also run against the exact acquired source base: 16 failed and one passed. That historical negative run precedes three additional delayed-arrival cases and the fixture's authored base-CSS inclusion; it is not presented as a final-suite baseline count.

## Changes

- Search has one native click activation path for keyboard, pointer, touch, and assistive activation. Secondary presses do not navigate and pressing down alone does not navigate.
- Escape works throughout search, focus departure closes it without pulling focus back, and a repaint preserves the focused result or page control.
- A result's market/ticker identity survives delayed libraries, even when the result crosses a pagination boundary. Explicit pagination wins over retained selection. Keyboard reveal scrolls the result surface without moving the underlying page.
- Combobox/listbox semantics, active descendant, selected options, current page, busy state, and result/failure announcements expose the same interaction to assistive technology.
- Retry stays on the existing fetch/retry owner, is keyboard operable, and cannot queue duplicate user retries while requests are pending. The original click event path prevents a replaced retry/page button from dismissing its own popup.
- Search names, headings, and market/status labels are readable; rows no longer replay entrance animations on typing or asynchronous updates. The header and 44px pagination stay reachable inside one scroll surface. Narrow layouts wrap company names and move status below them.
- Dialogs keep one scrolling body, a stable header, 44px close targets, readable titles, dynamic viewport bounds, and safe-area padding. The panel enters once in 200ms, with a shorter exit; content is immediately available. Reduced-motion behavior remains supported. The close glyph uses theme-aware ink in light mode.
- Three existing Where Next dialog links preserve Ctrl/Meta/Shift/Alt native navigation while ordinary activation continues through the existing dialog owner.

Spacing/radius tokens use the design system's documented fallbacks because those token scales are not yet globally defined. No new runtime stylesheet injection, router, auth owner, data owner, or lifecycle controller was introduced. `site/theme.js` is emitted with `lib.site_assets.emit_theme_js`; the navigation CSS pair is synchronized.

## Verification

`final-focused-tests.txt` records **139 passed in 227.26s** on the final authored source, covering all five affected suites. `browser-tests.txt` separately records 45 passing checks: 20 real Chromium interaction cases and 25 existing navigation contracts. The browser cases cover native Enter/Space/click/tap, release-only pointer activation, secondary-button rejection, Escape and focus departure, active selection/scroll geometry, four asynchronous focus/page-boundary combinations, retry recovery, IME/fullwidth input and Chinese locale, desktop/mobile/short-viewport dialogs, reduced motion, readable result text, and modified native links.

The first existing focused run covered navigation, Chinese ticker search, dashboard rendering, and Macro Risk dialog contracts: 117 passed and two implementation-specific navigation assertions failed. Those assertions were updated for the valid 44px target floor and box-level Escape owner, and all 25 navigation tests then passed. No test assertion was disabled. The final combined 139-case rerun passed; CI receipts are recorded alongside this file.

CI catalog parity and declared-scope coverage passed. The first global closure census stopped at this new untracked suite because discovery uses the Git inventory. Registering the two owned test files resolved discovery; `ci-suite-closure.json` records the existing planner deriving the new job, 12 concrete dependency paths, zero uncovered paths, and its explicit font scope. The initial census result is retained as a diagnostic, not reported as a final global pass.

Design-system added-line ratchet, frozen runtime-style-injection allowance, JavaScript syntax, visual-evidence receipt validation, and whitespace checks passed. CI job `macro-interaction-browser` is registered in the existing catalog with required Chromium, complete declared component/font inputs, and unchanged exclusive-scope parity/closure checks. A bounded read-only native reasoning audit identified and helped resolve the asynchronous page-boundary case and CI registry/font-input omissions; it did not approve the PR or execute tests.

## Visual evidence

Canonical capture owner: `scripts/capture_page_evidence.py` (manifest records its exact module hash). Evidence: `mockups/evidence/macro-polish-20261109/`.

- Search: 8 cells, dark/light × EN/ZH × 1440×900 desktop/390×844 mobile.
- Dialog: the same 8-cell matrix.
- Retry: the same 8 base cells plus 8 actual keyboard-focus cells.
- Receipts map the changed CSS/template paths to those manifests. PNG hashes and dimensions are validated by the existing guard. Obsolete owned captures were removed.
- Representative actual images were visually inspected, including dark desktop search, light Chinese mobile search, dark English mobile search, light desktop and dark Chinese mobile dialogs, and dark/light retry focus. No horizontal overflow was measured in either viewport.

These are explicitly synthetic offline component fixtures using shipped Jinja chrome, authored dashboard base styles, exact component controllers, and actual fonts. Library contents and external navigation/access integrations are fixture boundaries. Normal search/dialog capture has no console errors; retry deliberately serves five library 404s to capture its genuine error and focus states. The manifests honestly record uncaptured production access tiers. Lab timing fields are not production performance claims.

The capture manifest's HEAD is the acquired ancestry, not a claim of a clean full render. `source-hashes.json` records the dirty authored input hashes. The only later template edit at this checkpoint terminates two existing inline custom properties with semicolons, leaving the captured component assets unchanged. Live acceptance remains a separate post-merge obligation.

## Ownership and release

Existing held/draft navigation lanes (#7601, #10261, #10879), the focus-helper lane (#10389), and #8721's dialog lifecycle/hidden-origin focus repair retain their owners. This change does not release their holds or duplicate their controller changes. Unified Dashboard and Ignition composition holds remain intact.

Latest fetched main at local review: `7bdfb249486d409ee8634501842c31f51af74c7c`. Its changes on our two shared CI files are in separate hunks: existing Shared Shell suite accounting and its protected packing provenance. Preserve them through ordinary integration; no production component changed since the acquired base.

Publication uses the original managed workspace's exact-head commit/push carrier, then a ready PR and the existing merge-on-green owner armed last. Macro main is currently unprotected, so native auto-merge must not be used as a CI wait. After merge, verify a successful covering render for the Jinja change, served paired bytes and restamped references, and real live search/dialog journeys. Do not cancel or duplicate the shared render lane. Source/CI/merge/deployment/live acceptance are separate states.
