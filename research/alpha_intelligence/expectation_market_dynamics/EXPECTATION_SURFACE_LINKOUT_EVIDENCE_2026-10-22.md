# Expectation Surface link-out — visual evidence record (2026-10-22)

Commission: `itp-es-linkout-20261022-r1` (Information→Price Wave 3a — per-security
company-page link-out from the explorer card). Lane branch
`lane/itp-es-linkout-20261022-r1`, base `ce93903889ea50056e9f4890422dad044c31c65a`.

## What changed (user-visible)

Inside the explorer card heading row (`#es-card` → `.es-card-h`), a new
`#es-card-link` anchor (`Company page` / `公司页面`, `.es-link` idiom) renders
between the ticker `<h3>` and the identity pill. It is `hidden` at render time;
`updateCard()` un-hides it only when the ticker doc carries
`company_page: "stocks/<T>.html"` — a value the builder sets only for tickers
whose `stocks/<T>.html` page actually ships (`lib.pages.rendered_ticker_pages`).
A JS guard (`^stocks\/[A-Z0-9.\-]{1,12}\.html$`) re-validates the value before
any `href` is set (defense in depth against a malformed JSON doc). The h3's id,
class, tabindex and text are untouched; the link is a real `<a href>`, so it is
keyboard-reachable and carries the `.es-link` focus/underline idiom.

## How the evidence was produced

1. Builder + template edits applied on the lane branch; module suite green.
2. Evidence site built in a scratch dir OUTSIDE the repo
   (`/tmp/es_linkout_site`) with `tests.test_build_expectation_surface`'s
   synthetic fixture (`_write_fixture(root, _main_obs_rows())`), a fake
   `site/stocks/AAA.html`, and the real templates/ symlink; then
   `scripts.build_expectation_surface.build(write=True, root=...)`.
   Result: `tickers/index.json` = AAA→`stocks/AAA.html`, BBB/CCC/DDD/EEE→`null`;
   `AAA.json["company_page"] == "stocks/AAA.html"`.
3. Site chrome (theme.css, shared_shell.css, navigation-refresh.css, theme.js,
   shared_shell_bridge.js, logo/stock-logos/live config+js, favicons) extracted
   from the COMMITTED base tree (`git show <base>:site/<file>`) into the scratch
   site only — the sparse lane worktree omits site/, and the repo working tree
   was never touched under site/.
4. Bounded receipt capture (browser, anonymous):
   `python3 scripts/capture_page_evidence.py --routes expectation_surface.html
   --site-dir /tmp/es_linkout_site/site
   --output-dir mockups/evidence/expectation-surface-linkout
   --manifest mockups/evidence/expectation-surface-linkout/manifest.json
   --smells mockups/evidence/expectation-surface-linkout/smells.json
   --viewports desktop,mobile --locales en,zh --themes dark,light
   --as-of 2026-10-22T13:00:00Z`
   → `outcome: captured`, `pages: 1  states: 8/8 captured`.
5. Lane screenshots (Playwright + chromium) against the same scratch site served
   on localhost: `expectation_surface.html?t=AAA#es-explorer`, waiting for
   `#es-card-link:not([hidden])`; theme set via
   `document.documentElement.setAttribute('data-theme', …)` and language via
   `setAttribute('data-lang', …)` — the page's own toggle mechanism. The first
   attempt used port 8765, which is occupied by a foreign process serving a
   stale page; the lane re-served the scratch site on 8791 and re-ran.

## PNG set (this directory)

| file | state |
|---|---|
| es_linkout_1440_dark_en.png | desktop 1440×900, dark, EN — link visible |
| es_linkout_1440_dark_zh.png | desktop 1440×900, dark, ZH — 公司页面 visible |
| es_linkout_1440_light_en.png | desktop 1440×900, light, EN |
| es_linkout_1440_light_zh.png | desktop 1440×900, light, ZH |
| es_linkout_390_dark_en.png | mobile 390×844, dark, EN |
| es_linkout_390_dark_zh.png | mobile 390×844, dark, ZH |
| es_linkout_390_light_en.png | mobile 390×844, light, EN |
| es_linkout_390_light_zh.png | mobile 390×844, light, ZH |
| es_linkout_card_2x.png | card element crop, device scale 2, dark EN |
| es_linkout_hidden_1440.png | `?t=BBB` (no stocks page) — link NOT shown |

Overflow guard: at 390 the shot script asserted
`document.documentElement.scrollWidth === clientWidth` in all four theme/lang
passes before shooting — no horizontal overflow.

Hidden-case proof (programmatic, from the shot run):
`?t=BBB` → card heading text became `BBB`, then
`{'hidden': True, 'href': None}` on `#es-card-link` — the link stays hidden and
href-less for a security without a rendered page.

## Design ratchet + receipt outputs

- `git diff --unified=0 <base> -- templates` → `scripts/check_design_system.py
  --mode enforce-added --diff-file` → **blocking=0**
  (`estate pre-existing, non-blocking: 25372`).
- `EVIDENCE.yml` (schema `mastermind.page_evidence_receipt.v1`,
  changed_paths `[templates/expectation_surface.html.j2]`) +
  `scripts/check_ui_visual_evidence.py --diff-file` → **rc 0** (no findings).

## Test evidence

- `python3 -m pytest -q tests/test_build_expectation_surface.py` → **25 passed**
  (22 baseline + 3 new; baseline recorded as 22 passed pre-change).
- `tests/test_render_builder_ownership.py` → **7 passed**.
- `tests/test_public_chrome.py` → 5 passed, 2 failed — both failures are the
  sparse lane worktree missing generated `site/*.html` pages
  (`site/about-research.html` not checked out); environmental, unrelated to this
  diff (which touches nothing under site/).

## GAPS

- GAP (visual semantic confirmation): the lane's guarded visual-judgment helper
  refused with `GLM_VISION_DELEGATION_REFUSED reason=controller_minimax_lease_required`
  (preserved verbatim; not retried around). The PNG set above plus the capture
  tool's own 8/8 state matrix, the programmatic hidden/href/overflow assertions,
  and the receipt/rc-0 checks stand in as evidence; no independent model-based
  visual judgment of the PNGs was performed in this lane.
- GAP (minor): the receipt capture ran on the scratch evidence site (synthetic
  fixture + committed chrome), not on the production nightly site — same
  template, same builder path; the production page re-renders on the next
  nightly.

## Positioning note (descriptive only)

The link is navigation, not a signal: it exposes an existing company page, adds
no rank, no gate, no recommendation, and every emitted document keeps
`financial_influence: false` / `k3e_admissible: false`.
