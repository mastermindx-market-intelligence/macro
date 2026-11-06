---
key: NEW-PAGE-SHELL-DEFECTS-HIDE-FROM-TESTS-THEME-JS-CANVAS-AND-RENDER-TIME-ARIA-NAMES
claim: >
  A new bilingual page shell that includes `templates/_site_nav.html.j2` can pass its whole test
  suite and a not-connected production check and still be broken in EN/中文 or dark/light in a
  real browser, in four independent ways. (1) The nav include does not load `theme.js`, which is what wires the
  nav's theme switch and EN/中文 toggle. Unless the page adds `<script src="theme.js" defer>`
  (biocatalyst.html.j2 does, finance_intelligence.html.j2 did not), both controls render and do
  nothing. (2) A frozen design spec's instruction placeholders, such as `{common_as_of}` or
  `{§D.12 label of freshness.state}`, transcribed into `data-aria-en/zh` ship literally and are
  announced beside the correct visible value. (3) A page-local inline aria swapper applies
  `data-aria-*` at parse and on `langchange` BEFORE the runtime hydrates or re-renders. Rendered
  controls with a hard-coded English `aria-label` therefore stay English in 中文; the runtime must
  emit each name in the current language at render time. (4) `theme.css` does not paint `body`.
  A shell that paints its canvas token only on a max-width container leaves every gutter, the
  nav band and the area below the content on the browser's white default in dark mode.
  Light mode hides this because the default canvas is also light. The page must paint
  `body.<page> { background: var(--canvas-token) }` itself, as biocatalyst.css does.
evidence:
  - >
    Finance T8 shell #7952 went live 2026-09-24 with neither nav toggle working; the page loaded
    logo_config, stock-logos, live_config, live and finance_intelligence.js but no theme.js. Fix
    #7968 adds the include in the template and splices `theme.js?v=3ffc953f` (sha256[:8] of
    site/theme.js) into the render-stamped site copy.
  - >
    Node hydration harness on the pre-fix runtime, VALID_DOC fixture with lang=zh, yields
    `['Open evidence', …]` for all 8 evidence controls
    (`tests/test_finance_intelligence_hydration.py::test_hydrated_controls_are_named_in_the_page_language`,
    red before #7969 and green after).
  - >
    A real-browser pass over a connected fixture copy of the page found the hero chips announcing
    "Evidence freshness: {§D.12 label of freshness.state}". After #7969 (ariaPair / nameChip at
    render time, placeholder pairs dropped), the same pass read 打开证据 / 合同流 / 证据新鲜度：新鲜 on an EN→中文
    toggle and on a fresh 中文 load, with zero placeholder-brace labels.
  - >
    Live proof of #7968 at 390 dark on 2026-09-25: only the Finance panel was dark. html and
    body computed `rgba(0,0,0,0)` while `--bg` was #0d1018. #7974 adds
    `body.fi-page { background: var(--fi-canvas); }`, and its 8-cell evidence reads
    left-gutter luminance 18 dark / 236 light.
  - >
    (3) also applies to static, server-rendered markup. The Theme Tracker entry card (#7957) and its
    section carried literal English `aria-label`s. Live on 2026-09-25, all four 中文 cases returned
    Chromium `getByRole('link', {name: '金融情报'})` = 0 while the card visibly read 金融情报.
    #7977 names them with `aria-labelledby`/`aria-describedby` over the l-en/l-zh spans. The inactive
    span is display:none, so it drops out of the name, and the name follows the toggle without script.
    This is the house idiom in `_market_regime_strip.html.j2`.
falsifier: >
  A page that includes `_site_nav.html.j2` without loading `theme.js` whose nav theme/language
  toggles still work refutes (1). A swapper that re-runs after every runtime render without the
  runtime's help, leaving hydrated controls correctly named in 中文 with hard-coded English
  `aria-label`s, refutes (3). A page with no body/html background rule whose dark-mode
  gutters render dark refutes (4).
so_what: >
  Every GMI sector vertical builds its dossier shell from a frozen spec plus an inline swapper,
  so a shell packet must require four things. First, the `theme.js` include beside the nav
  include. Second, a test that rejects `{` inside any static `data-aria-*` value. Third,
  render-time names chosen with the page-language check rather than a hard-coded English label,
  and in static markup `aria-labelledby` over the bilingual spans, never a literal `aria-label`.
  Fourth, a body canvas rule painted from the page's own canvas token.
  The browser proof must read the `aria-label`s of HYDRATED controls after a 中文 toggle and on a
  fresh 中文 load, and must look at dark-mode gutters and the area below the content, because
  visible text, light mode and the not-connected state cannot show any of the four.
kind: landmine
confidence: verified
verified_at: 2026-09-25T00:41:00Z
verified_by: >
  python3 -m pytest tests/test_finance_intelligence_hydration.py -q -k named_in_the_page_language
  (red on the pre-#7969 runtime, green after); browser probe over the repo's `site-static` preview
  of a connected fixture copy reading `[aria-label]` values after an EN→中文 toggle and a fresh 中文
  load; live `document.scripts` listing on https://www.mastermind-x.com/finance_intelligence.html
  before #7968.
scope:
  - macro
---

The not-connected shell hides items (2) and (3). Its hero meta is `display:none`, and the
runtime's `langchange` handler is registered inside `hydrate()`, so neither the static test
suite nor a production check of an unbound page ever renders a hydrated control. Item (1) hides
because every test renders the template in isolation, and no test asserts that the page's
scripts include the runtime the shared nav depends on.
