# Shared Shell R22 — source-fed All tools adoption candidate

**BUILT_NOT_PROVEN · NOT_APPLIED_TO_PAPER · NOT_INSTALLED_ON_LIVE_PAGES**

The product decision remains mega-menu first, with full-directory browsing retained. This package closes a different gap from the R21 visual reference: the controller reads the incumbent product navigation at opening instead of shipping another manually maintained list of destinations.

Owner: existing WS:MARKET-OS / Macro PR7949 / `sol/market-os-shared-shell-design-20260924`. No new registry, router, preference store, authentication service, data pipeline or automatic retry owner.

## What is implemented and what it is not

`src/all-tools.js` is an executable source-fed controller. `src/_all_tools_menu.html.j2` is the reusable default-OFF host for the current shared product header. `src/all-tools.css` is an authored static material sheet, intended for integration through the existing navigation styling owner. `shared-header.patch` is the exact one-include hook against the inspected header; it is not applied automatically.

No production page, generated site asset, serving rule, header or feature flag is changed by this research/adoption package. No live installation, native Paper result, real browser interaction, visual acceptance or human-comprehension result is claimed. The scope is more than a fixed mockup but less than a released common-header upgrade.

## Immediately useful behavior

- Opening prepares the current source section from the actual page destination, not a hardcoded US assumption or saved market preference. Every source category remains reachable in the same panel.
- Native source groups and section headings survive. A large Research catalogue is not flattened into an undifferentiated list. The source order stays the default; no invented ranking, favorites or recency.
- Search spans eligible tool names/descriptions in English and Chinese. It is explicitly separate from the existing global stock search.
- Real source hrefs keep their relative-prefix resolution, query and task hash. Distinct country pages and deep-linked views remain distinct. No cross-market equivalent is fabricated.
- Ordinary anchors keep native same-tab, modified-click and source-requested new-tab behavior. New-tab behavior is announced in the accessible name; only approved same-product origins are accepted.
- Source-owned blueprint SVG shapes and tier text are reused. Script, image, event and reference nodes are not copied from SVGs.
- While open, withdrawn or changed destinations lose their copied href. Source updates do not silently reorder the object being inspected. Reopen refreshes the source snapshot.
- Escape/Close restore the initiating focus with preventScroll. The native dialog owns its modal focus behavior; there is no hand-written second focus-trap service. A delayed old close event cannot close a newer opening.
- Phone opening focuses the heading rather than intentionally summoning the software keyboard. IME composition does not filter half-entered Chinese text. These are tested controller intentions, not device/browser proof.
- Empty source and a legitimate no-match query have different explanations and recovery actions. A script or dialog-support failure leaves the existing navigation available.

The snapshot is a presentation projection, not entitlement enforcement. Backend access remains authoritative. Explicit disabled/withdrawn source entries are suppressed; a closed inert dropdown is not itself a denial. Current source eligibility must still be supplied by the existing nav/feature owners.

## Dark and light treatments

The sheet consumes existing `--nr-*`, `--font-ui`, type-scale, text, line and link tokens. It declares no parallel root palette and loads no fonts. Dark uses the current graphite material and restrained luminance emphasis. Light uses the shared white material, crisp strokes and an inset pale side note rather than inheriting the dark glow. The semantic information, order and actions are identical.

The panel defines wide, narrow and short-height compositions, a single normal scroll body, short-height whole-panel escape, safe-area footer padding, reduced-motion and forced-colors treatment. These declarations are NOT measured layout or accessibility acceptance. Native/browser visual comparison is still required, especially 320px, 200% text, virtual-keyboard transitions and Safari.

## Source identity

Macro inspection pin: `dea858959c6f37122fd500dd673c44b271f19fa9`.

| Existing owner | Observed Git blob |
| --- | --- |
| `templates/_site_nav.html.j2` | `9848b9366d43553f9d69997ecdb0a07e15e4ad2b` |
| `templates/nav_market.js` | `4edee693e1e6d4391de3482b2a618057df686e56` |
| `templates/navigation-refresh.css` | `276c1986f2a728ca59e0f9e0bc7fe269869fdff0` |
| `templates/theme.css` | `2c1043b3073041d16d85b61b6290b4fbb8796f9f` |

The original 3,388-byte header is included only as a hash-checked test fixture. It is not a second production header. Header tests use a small controlled navigation include: they do not validate a full-site population count or execute nav_market/theme.js.

Protected procedure: Mastermind `dcc4829a811d3f6e4fe8c16a103f813c3501f48e`; INDEX `94d1af402598894372858793a5b1931019c5fa77`. Current live Chairman direction permits the mega-menu work; current source, host, permission and release gates remain separate.

## Verification actually executed

- 70 Node projection/controller tests passed using the real candidate and a recording DOM double.
- 20 Jinja/shared-header/static-style checks passed, including exact original-header Git blob, identical default-OFF render, literal-boolean opt-in, one header/one dialog, deep prefixes, preserved source anchors, separate stock/tool search and valid label references.
- 10 deliberate broken controller variants were detected. The first run detected only eight: two count-only assertions missed equal-count but different-content errors. Their semantic assertions were strengthened; the untouched candidate and final ten-variant pass were rerun.
- Source syntax passed. Initial RED outputs and intermediate/final test reports are retained.

No actual browser was launched or workaround attempted. The earlier `ERR_BLOCKED_BY_ADMINISTRATOR` navigation gate was not reset by these simulations. No screenshots, computed-layout metrics, screen-reader audit, live account interaction, deployment or award-level claim is produced here.

## Run the bounded tests

Requirements: Node >=18, Python >=3.10 and Jinja2. No application dependency installation is required; use the existing isolated runner.

```sh
node --test tests/navigation.test.cjs tests/controller.test.cjs
python tests/template-contract.py
python tests/mutation-check.py
```

The Python code uses Jinja2 and standard-library HTML parsing, not an additional browser or DOM package. Commands run from this directory. These tests are NOT yet registered as production CI gates. Registration belongs in the existing product-chrome/navigation test owner during actual source adoption, not a new workflow.

## Exact installation sequence — not executed

1. Reconcile the then-current shared-navigation source writer and this candidate against current `_site_nav`, `_navlinks`, `nav_market`, `navigation-refresh` and `theme`. Do not overwrite another writer or replace the source catalogue with the R21 fixture.
2. Adopt the controller into the incumbent navigation owner, or its reviewed paired helper, and the stylesheet through `navigation-refresh.css` or its registered static helper. No JavaScript-injected material sheet and no third page header. If the shown helper asset form is retained, add and prove the normal template/site copy, caching and serving/access classification before enabling it; the filenames in the partial are not proof that those URLs are served.
3. Include the reusable host after the existing common header, once. The local candidate requires explicit boolean `all_tools_enabled=true`; default and string values remain OFF. No current page has that flag enabled. The runtime additionally limits this initial candidate to `/macro.html`, `/sector_central.html`, `/reports.html`; these are a pilot ceiling, not a page-route registry or proof of full-template adoption.
4. Register the behavioral and template tests with the existing product-chrome/navigation CI owner. Supply committed real dual-theme/device/locale visual evidence, not the static R21 previews. Existing build/serving rules and anonymous-public chrome remain unchanged unless their owners explicitly qualify a required asset update.
5. Prove actual pages and source populations after their incumbent navigation transforms. Verify deep links, ordinary/new-tab navigation, dialog focus/return, Terminal/auth overlays, page scroll, short screens, fonts, CSS load failure and browser back/forward. Preserve the current global stock search.
6. Only then enable the three pilot families, consume exact-head review/CI, release through the normal owner and verify the served assets/pages. Expand by existing template family after proven results, never hand-copy the header to every page.

These are real remaining adoption obligations, not an assertion that setting a flag now is production-safe. The R18 assertion, R19 three consumer failures and PR7129 persistence-before-rebind requirement remain separate; this menu work neither repairs nor waives them.

## R21 recovery discrepancy

The mounted R21 HTML is 71,244 bytes with SHA256 `c220bde0a6af76e84b980d1b8d79f259c6609a479c882a8e307b80fe8237f741`. The later program return5863765317 records a different 133,698-byte/a7070ab... artifact. Bounded file retrieval did not recover those later raw bytes. Originals were preserved and not relabeled as the later release. R22's source-fed work is independently identified rather than silently overwriting either R21 record.

## Native boundary and continuation

The requested native target remains M1, Paper file `01M2WGNCX9475G79JRKJTCM08P`, Shared Shell page `p-D-0`. Studio's current exposed connection is M2 and another active file; no content edit or focus transition was made. M1 configuration could be read, but the unchanged configuration/session is not evidence lifting the earlier exact preflight/source-staging refusal. No alternate-host edit or denied browser/command replay occurred.

Next material unit: existing-owner adoption of this exact source-fed component, serving/test registration and real three-page proof through permitted surfaces; native application uses the same existing shell boards once exact M1 action permission is available. No new Paper file, duplicate directory, route owner, worker, watcher or background run is started.
