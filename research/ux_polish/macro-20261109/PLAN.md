# Macro Dashboard interaction polish — 2026-11-09

## Outcome
Make the existing Jinja product feel immediate, legible, and predictable across mouse, touch, and keyboard. Preserve rendered intelligence, access gates, routing, navigation inventories, and the existing theme/locale owners.

Authority: Chairman's current request to upgrade Macro Dashboard to the same polished SaaS experience as Terminal and Shared Shell. Governing Mastermind pin: `494d095813dad415938800fa0e4d2719497738fa`. Source base: `macro@73bbade8efdb464279a1693a6e2c72a39c1790c9`. Operation: `macro-saas-polish-20261109-astra-01`; managed isolated branch `sol/web-macro-saas-polish-20261109-astra-01`.

## Confirmed baseline
- Live `/macro.html` search, query `a`: keyboard Enter on Results page 2 leaves page 1 active. Escape from that same button leaves search open. Existing activation is delegated only to mousedown.
- Search rerenders recreate animated result rows, and company names use 8.5px text. The visible selected row is not exposed through the input's active-descendant relationship.
- Macro detail panels animate individual sections for up to 520ms after opening; the panel and its body can both scroll. Mobile sheets use static viewport height and lack safe-area bottom padding.
- Authenticated browser opened the live Events panel. No account, portfolio, watchlist, market data, or permission mutation was performed.

## Owned work
1. Repair the existing search controller: one native click activation owner, keyboard selection and Escape throughout the component, deliberate focus after repaint, meaningful ARIA/current states, and selected-row visibility. Keep IME, partial/failure honesty, data loading/ranking, Terminal and Shared Shell destinations intact.
2. Refine existing search material: readable typography, steady rows during typing, one scroll surface, visible neutral selection, usable touch controls, matching light/dark and EN/ZH behavior.
3. Refine existing Macro detail presentation: concise coordinated motion, no child stagger, a fixed readable header and one scrolling body, responsive dynamic viewport and safe-area geometry. Preserve the current dialog lifecycle and access owner.
4. Preserve browser-native modified clicks on authored Macro dialog links while ordinary activation continues through mx5OpenDlg.

## Adjacent work preserved
- #7601 desktop menu keyboard/ARIA; #10261 held pre-hydration loader; #10879 held All Tools chooser.
- #10389 dialog Tab-stop fix.
- #8721 existing dialog replacement, return-focus and close-race repair. Its exact patch was inspected; this change will not duplicate those lifecycle functions.
- Unified Dashboard primary-composition hold and Ignition-surface hold remain intact.

## Execution and proof
Principal implements directly because source, browser observations, and the narrow shared-component changes need one tightly coupled owner. A native reasoning advisor performed a bounded read-only defect/overlap analysis; no labor worker or independent approval is claimed.

Use focused existing render/navigation/search tests plus real-browser interaction regressions that fail on the original source. Register affected automated proof with the existing CI catalog. Capture the governed dark/light × EN/ZH × 1440/390 matrix, plus reduced-motion and short-height checks, using the existing capture owner. Inspect actual screenshots. Mirror paired plain-copy assets through the existing emitter. Self-review the exact diff, publish one ready PR, use Macro's normal merge-on-green controller (never unsafe native auto-merge on unprotected main), and verify exact served bytes and real user paths after normal source landing/render.

DONE_WHEN: owned changes are source-qualified, ordinarily landed, and proven on the served product. CI, PR, merge, deploy, and browser acceptance remain distinct. Preserve the original Shared Shell PR1384 continuation; do not republish its superseded local head.

## Source verification checkpoint

139 affected checks pass on final source. Canonical visual matrix captures32 states; paired assets, syntax, design/runtime/visual guards and diff checks pass. New exclusive CI job is registered; tracked-suite discovery and complete closure are proved in ci-suite-closure.json. Next: original exact-head commit/push, ready PR, arm merge-on-green last, and verify covering render plus live journeys. No held sibling lane is released.
