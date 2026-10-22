# Expectation Surface — Research mega-menu reachability: evidence record (2026-10-22)

Lane `itp-es-nav-20261022-r1` (pool glm, model glm-5.3-flash), commissioned by the
Meta-CEO seat 2fc05761 (Information→Price program, WS:ALPHA-INTELLIGENCE-INTEGRATION).
The page itself is live on production; this lane only adds the menu row that makes it
reachable from the shared authenticated header.

## Head / base

- Commissioned base (worktree HEAD at start and at push): `8c23f6b26a36ce20f5842590e41bb9d78bff1bac`
- Branch: `lane/itp-es-nav-20261022-r1` (local); pushed to `claude/itp-es-nav-2026-10-22` (see PUSH below)
- origin/main at fetch time: `ce93903889ea50056e9f4890422dad044c31c65a` (ahead of base; NOT merged — containment forbids it)

## The row (templates/_navlinks.html.j2, one insertion)

Immediately after the Macro Weather row inside the Research drill panel (the Global
Cycles drill), last row of the list:

```html
<a class="nav-mega-item" href="{{ NP }}expectation_surface.html"><span class="nm-ic research-icon research-icon-expectation-surface" aria-hidden="true"></span><span class="nm-tx"><span class="nm-t">{{ t('Expectation Surface', '预期曲面') }}</span><span class="d">{{ t('How consensus estimates moved', '一致预期如何变动') }}</span></span></a>
```

`git diff --stat templates/_navlinks.html.j2` → exactly `1 insertion(+), 0 deletions`.

## The icon (templates/product-nav-icons.css, four insertions)

Decoded mask SVG (24×24, stroke 1.5, round caps/joins, fill none — family idiom;
two consensus polylines — prior from above, current from below — converging on a
small target dot):

```svg
<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'><g fill='none' stroke='black' stroke-width='1.5' stroke-linecap='round' stroke-linejoin='round'><path d='M3.5 8 8.5 10.6 14 11.9'/><path d='M3.5 16 8.5 14 14 12.5'/><circle cx='18' cy='12.2' r='1.6'/></g></svg>
```

- Rule `.research-icon-expectation-surface{ --research-icon-mask:url("data:image/svg+xml,…") }` inserted directly after the `.research-icon-macro-weather` rule.
- `.research-icon-expectation-surface` appended to the `.nav-mega :is(…)` accent group that lists `.research-icon-macro-weather` (the `#42a9b7` / `inset(0 48% 52% 0)` group), immediately after the macro-weather selector.
- `git diff --numstat templates/product-nav-icons.css` → `4 0` (3 rule lines + 1 group line).
- Live render check (Playwright, local build): `::before` mask = the data URI above, `background: rgb(174,185,202)` (--nav-icon-ink, dark); `::after` paints the accent layer. Pixel census of the icon box in the 2× crop: 602 ink px + 130 accent px — both layers paint.
- Note (pre-existing page behaviour, not this lane): on the expectation_surface page the page-level `--nav-icon-accent` token (#5877e9) overrides the family accent groups for ALL statically-drawn research icons alike — verified with JS disabled: macro-weather, cycle-intelligence and expectation-surface all resolve to the same accent var and clip. The commissioned group membership is in place and test-pinned; sibling drill icons are additionally rewritten to inline SVGs by nav_market.js at runtime (a family behaviour this lane does not touch).

## Pairs + chat sync

- `cp templates/product-nav-icons.css site/product-nav-icons.css` → `cmp` silent (byte-identical).
- `python3 -m scripts.sync_chat_nav --fix` → `chat nav sync OK (templates/chat.html header == _site_nav.html.j2)`; check mode → same OK.
- `cmp templates/chat.html site/chat.html` → silent.
- `python3 -m scripts.check_template_site_sync` → `template↔site sync OK (139 pairs checked)`.
- (The chat_nav_regen_guard hook also regenerated the chat pair at edit time; `sync_chat_nav --fix` confirmed idempotent.)

## Tests

New: `tests/test_expectation_surface_nav.py` — 5 tests, all pass:
- `test_row_is_last_research_drill_row_right_after_macro_weather`
- `test_six_preexisting_research_drill_rows_unchanged`
- `test_icon_rule_and_accent_group_membership`
- `test_site_icon_pair_is_byte_copy`
- `test_rendered_nav_carries_the_row_without_banned_word` (jinja2 render of `_site_nav.html.j2`, nav_prefix `""` and `"../"`; asserts the prefixed href and no 申报)

Parity set (7 suites): `python3 -m pytest -q tests/test_expectation_surface_nav.py tests/test_nav_submenu_icons.py tests/test_chat_nav_sync.py tests/test_subdir_nav_prefix.py tests/test_build_product_page_registry.py tests/test_public_chrome.py tests/test_render_builder_ownership.py` → **89 passed, 3 failed** — the 3 failures are pre-existing at base (see GAPS G1).

Full pinned battery: `grep -rl _navlinks tests | grep '\.py$' | sort` → 41 suites
(42 grep hits incl. one fixture JSON); `python3 -m pytest -q $(…)` → **2111 passed, 34 failed, ~8 min**.

Failure attribution (base vs this lane's content, decided by running the same 10
failing suites in a /tmp copy of the tree twice — once with base's 5 changed files,
once with this lane's — and diffing the FAILED sets):
- 33 failures: identical under base content → pre-existing at 8c23f6b (support/unsubscribe public-chrome drift, SEO length pins, sector redirect stubs, policy-watch record guards, state-of-themes claims check, bonds bytes guard — all outside this lane's owned files).
- 1 failure added by the row: `test_research_screener.py::test_fresh_bake_matches_committed_site_html` — pure render lag: the fresh bake contains exactly the new row (`+ …href="expectation_surface.html"…`), the committed page refreshes in the post-merge render. Committing other site/ pages is forbidden to this lane, so this red is the documented source-PR state (same doctrine as the comment in tests/test_nav_submenu_icons.py).
- `test_macro_rates_curves_bonds_guard.py::test_10_bonds_hub_page_builds_to_the_committed_bytes`: drifts OUTSIDE the masked nav span (`T10 masked span sizes: nav=46865 …`), so a nav row cannot reach its compared bytes; failed identically under base content in the copy comparison.

## Design ratchet

`git diff --unified=0 8c23f6b26a36ce20f5842590e41bb9d78bff1bac -- templates site > /tmp/es_nav.diff`
(38 lines; regenerated against the same commits after commit — identical content)
`python3 scripts/check_design_system.py --mode enforce-added --diff-file /tmp/es_nav.diff` →
**blocking=1** (estate pre-existing, non-blocking: 25372):

```
templates/product-nav-icons.css:390 [literal-custom-property] --research-icon-mask: url("data:image/svg+xml,%3Csvg …
```

Structural: the rule `literal-custom-property` (rule 4, `scripts/check_design_system.py:303-312`) flags ANY literal-valued custom property on an added line; `VALUE_LITERAL_RE` matches any `[A-Za-z]{2,}`/quote, so every data-URI icon mask trips it. All ~50 sibling icons in `templates/product-nav-icons.css` are the identical pattern (pre-existing findings, non-blocking only because the estate census never re-reads them). The seat's R4 explicitly mandates this exact line shape ("the mask data-URI SVG uses stroke='black' like its siblings — that is the mask, not a colour"), so the commissioned content is kept and the blocking finding is recorded here and in GAPS (G3) rather than the icon being dropped or the mask moved to a file this lane doesn't own. No waiver mechanism exists in the checker (only SANCTIONED_LITERAL_FILES, which does not include product-nav-icons.css and is not this lane's to edit).

## Evidence receipt (CI pack)

- Receipt: `mockups/evidence/expectation-surface-nav/EVIDENCE.yml` — exactly three keys (`schema: mastermind.page_evidence_receipt.v1`; changed_paths: templates/_navlinks.html.j2, templates/product-nav-icons.css, templates/chat.html; manifest path).
- Page built locally: `python3 -c "from scripts.build_expectation_surface import build; build(write=True)"` → `state: LIVE` (687,456 observations, 1,508 securities, source_revision = base 8c23f6b). Derived site pages (`site/expectation_surface.html`, `site/expectation_surface/summary.json`) were restored to HEAD after capture — never staged.
- Capture: `python3 scripts/capture_page_evidence.py --routes expectation_surface.html --site-dir site --output-dir mockups/evidence/expectation-surface-nav --manifest … --smells … --viewports desktop,mobile --locales en,zh --themes dark,light --as-of 2026-10-22T12:00:00Z` → `outcome: captured; pages: 1; states: 8/8 captured` (desktop 1440×900 + mobile 390×844 × en/zh × dark/light; no :hover/:focus added by this diff, so no force-state cells required).
- Gate: `python3 scripts/check_ui_visual_evidence.py --diff-file /tmp/es_nav.diff` → recorded in the PUSH section below (run against the committed tree).

## Open-menu screenshots (seat judgment artifacts)

`python3 -m http.server 8931 --directory site` on the local build; Playwright driving
the site's own mechanism: `localStorage.theme`/`localStorage.lang` (+ `themeAuto`
removed) set before load; head bootstrap applies `html[data-theme]`/`html[data-lang]`
— verified per shot. Desktop 1440: hover the Research `.nav-link` (href ends
`intelligence_hub.html`) → `.nav-dd:hover > .nav-dd-menu` shows the mega; click the
Global Cycles drill trigger (`[data-nav-drill-open]`). Mobile 390: click the
theme.js-injected `.nav-toggle` → `.nav-open`, click the Research link → `.nav-dd.open`,
open the drill. Row scrolled into view in every shot.

scrollWidth == clientWidth with the menu open: **1440 == 1440** and **390 == 390**
(all 8 combos; zero horizontal overflow).

PNGs (all < 600 KB), under `research/alpha_intelligence/expectation_market_dynamics/evidence/es_nav_2026-10-22/`:

| file | bytes | sha256 (first 16) |
|---|---|---|
| es_nav_1440_dark_en.png | 138274 | b52bdfdd2063e30c |
| es_nav_1440_dark_zh.png | 142676 | baa648f881a7879d |
| es_nav_1440_light_en.png | 137758 | fa2ce53916561ec2 |
| es_nav_1440_light_zh.png | 144298 | 251c143a41fb3bac |
| es_nav_390_dark_en.png | 57011 | 8e332072d83334f4 |
| es_nav_390_dark_zh.png | 56113 | 36fd379c8aa9ea3e |
| es_nav_390_light_en.png | 57397 | 40ba94f69dc00391 |
| es_nav_390_light_zh.png | 56785 | 7284571acd394dad |
| es_nav_icon_2x.png | 44489 | a5d2aa99db5d2ac6 |

- Theme/lang reality checks: dark vs light mean luminance 27 vs 248 (1440) and 32 vs 249 (390) — the shots are genuinely different themes; EN vs ZH files byte-differ — genuinely different languages.
- `es_nav_icon_2x.png`: device_scale_factor=2 crop (1252×182 CSS px → 2504×364 px) covering the new row AND Cycle Intelligence AND Macro Weather. Deviation from the packet's "≈320×120 CSS px": the Research drill list renders as a TWO-COLUMN grid (measured live: left column x=171 — markets, sector_cycles, cycle, expectation_surface; right column x=797 — country_cycles, sector_cycles_china, macro_context), so Cycle Intelligence and Macro Weather sit side-by-side (both y=360), with the new row below-left (y=444, 78-px rows). The three named rows' bounding union is 1252×182 CSS px; a 320×120 crop cannot contain them. Crop = the union plus 12/10 px padding.

## GAPS

1. **G1 (pre-existing at base, not caused by this lane):** `tests/test_nav_submenu_icons.py` — `test_research_mega_menu_uses_complete_semantic_icon_set`, `test_jinja_nav_partial_preserves_research_icon_markup_on_rerender`, `test_jinja_nav_partial_preserves_submenu_icon_markup_on_rerender` fail at the commissioned base 8c23f6b with a clean tree. Root cause: template-vs-test drift committed on main before this lane — the Research drill/capital sections carry 4 destinations the test's frozen `EXPECTED_PUBLIC_RESEARCH_DESTINATIONS` lacks (theme_tree.html, am_edition.html, ontology.html, reference.html) and 22 icon-drawing spans vs the pinned 18 (23 after this lane's row — the test's own docstring says rendered counts may move while families persist). Both sides of the contract are outside this lane's owned files (the test file and all pre-existing template rows), so per the commission ("never edit a test that fires — record it under GAPS") they are recorded, not fixed.
2. **G2 (render lag, expected source-PR red):** `test_research_screener.py::test_fresh_bake_matches_committed_site_html` fails only because the fresh bake now contains the new row while committed pages await the post-merge render. Resolves at the nightly render after merge; committing the re-rendered pages is forbidden to this lane.
3. **G3 (design ratchet, structural):** `check_design_system.py --mode enforce-added` reports blocking=1 on the commissioned mask line (see Design ratchet above). Unreachable "0 blocking" for any new icon in the family idiom; kept the commissioned content, recorded the finding.

## DEVIATIONS

1. The 2× crop is 1252×182 CSS px instead of ≈320×120 — the drill list is a two-column grid; the packet's three named rows span both columns (measured boxes recorded above).
2. Screenshot server ran on port 8931 instead of 8765 — port 8765 was already bound by another session's process (my server's bind failed with EADDRINUSE; the other listener was left untouched).
3. `capture_page_evidence.py` ran against a locally built page (data was available on the host, so no live-origin fallback was needed); the two build-derived site files were restored to HEAD after capture and never staged.

## Round 2 (bridge repair)

Lane `itp-es-nav-20261022-r2` (pool glm, model glm-5.3-flash), commissioned by the
Meta-CEO seat 2fc05761 (same program/WS). Round 1's deliverables all stay; this
round adds the missing client-side icon-drawing bridge entries and re-captures the
open-menu proof.

### Head / base

- Base (round 1's head, worktree HEAD at start, and `origin/claude/itp-es-nav-2026-10-22` at fetch): `9b14fba35cc8993d083eef0a02358f8a91f3c371`
- origin/main at fetch time: `7abe860f0ab79f206ea846d7ffe6df0fdc2579d0` (NOT merged — containment forbids it)
- Branch: `lane/itp-es-nav-20261022-r2` (local); pushed to `claude/itp-es-nav-2026-10-22`
- Feat commit: `0cd460195c1a2596a6ed465e865ab278ed660be6`; test commit: `07b9ad985c3a0d95d52158ba4f530a3cd8a19392` (evidence commit sha in `ES_NAV_RECORD.md`, untracked)

### The two bridge lines (templates/nav_market.js, exactly 2 insertions / 0 deletions)

Immediately after the `MOCKUP_ICON_PATHS.earnings_wire = …` line:

```js
  MOCKUP_ICON_PATHS.expectation_surface = '<path class="ghost" d="M6 40h36M8 8v32"/><path d="M10 31c8-1 14-6 26-8"/><path d="M10 15c8 1 14 6 26 8"/><path class="accent" d="M10 23h22"/><circle class="soft-fill" cx="36" cy="23" r="4"/><path d="M36 15v4M36 27v4M30 23h2M40 23h2"/>';
```

Immediately after the `'macro_context.html': ['macro_weather', 'cyan'],` entry in `MOCKUP_RESEARCH_ICON_BY_FILE`:

```js
    'expectation_surface.html': ['expectation_surface', 'violet'],
```

`git diff --stat 9b14fba35cc… HEAD -- templates/nav_market.js` → `2 insertions(+)`, 0 deletions. `node --check templates/nav_market.js` → OK. `site/nav_market.js` is the byte-copy (`cmp` silent); `scripts.check_template_site_sync` → OK (139 pairs); `scripts.sync_chat_nav` check mode → OK (partial unchanged this round, no `--fix` run).

### Tests

`tests/test_expectation_surface_nav.py` extended with 4 bridge-contract tests (round 1's 5 kept untouched): drawing assignment unique with `ghost`/`accent`/`soft-fill` classes and no `fill=`/`stroke=`/`#`/`rgb(`/`style=`; map entry unique, after `macro_context`, before the closing `};`; `site/nav_market.js` byte-equals the template; the six drill files still present exactly once in the map. Suite: **9 passed**.

Pinned parity set (7 suites, base vs lane): base **68 passed / 4 failed**, lane **72 passed / 4 failed** — the failure-id sets are EQUAL under `comm` (lane set ⊆ base set, no new failure). The 4 are: the 3 known `test_nav_submenu_icons.py` failures (round-1 G1) plus `test_nav_hover_bridge.py::test_nav_release_key_moves_with_the_payload_it_busts` — **pre-existing at base 9b14fba with a clean tree, recorded verbatim per commission** (a 4th pre-existing failure beyond round 1's known-3 list; not caused by this lane's two added table lines — see GAPS G4).

### Design ratchet (CI pack)

- Round-2 diff (`9b14fba…` → HEAD, templates+site, 16 lines): `check_design_system.py --mode enforce-added` → **blocking=0**.
- Full PR diff (`8c23f6b26a36…` → HEAD, 54 lines): **blocking=1** on `templates/product-nav-icons.css:390 [literal-custom-property] --research-icon-mask` — round 1's G3 structural finding, expected here, not this round's to fix.

### Evidence receipt (CI pack)

`check_ui_visual_evidence.py` → rc 0 on BOTH the round-2 diff and the full PR diff (the two JS table entries are not material runtime JS). First branch of item 6b applied: `mockups/evidence/expectation-surface-nav/` left byte-identical, no receipt regeneration.

### Open-menu screenshots (re-captured; bridge verified in-page)

Local build path: `site/expectation_surface.html` rebuilt locally (`scripts.build_expectation_surface.build(write=True)`, exactly 2 derived site files written, both restored to HEAD after capture — never staged), served via `python3 -m http.server 8933 --directory site`; the page loaded is the local build running THIS round's `site/nav_market.js` (the derived pair), no route injection needed. Bridge before/after: the built page carries **7** server-rendered `.research-icon` tiles (six siblings + this row); after load `document.querySelectorAll('.research-icon').length === 0` on every captured page (assert per shot) — the bridge converted every row including this one.

Captured row markup from the live page:

```html
<span class="icon-drawing nm-ic violet" aria-hidden="true"><svg viewBox="0 0 48 48" aria-hidden="true"><path class="ghost" d="M6 40h36M8 8v32"></path><path d="M10 31c8-1 14-6 26-8"></path><path d="M10 15c8 1 14 6 26 8"></path><path class="accent" d="M10 23h22"></path><circle class="soft-fill" cx="36" cy="23" r="4"></circle><path d="M36 15v4M36 27v4M30 23h2M40 23h2"></path></svg></span>
```

Tile parity in the captured menu (desktop 1440): all three tiles **58×58 CSS px**, rows 602×78 @ x=171 (left column: Cycle Intelligence y=360, Expectation Surface y=444) and x=797 (right column: Macro Weather y=360) — same geometry round 1 measured. Pixel census of the ES tile in the 2× crop: std 29.8, top-colour share 0.78 (family: cycle 0.727, macro 0.757 — a flat mask square would be >0.9) and 742 blue-dominant (violet accent) px: the tile is a line drawing with the violet accent, not the grey mask square.

scrollWidth == clientWidth with the menu open: **1440 == 1440** and **390 == 390** (all 8 combos; the mobile 390 shots were re-captured with an explicit in-viewport row-visibility assert: row box y=536/541, h=68).

PNGs (all < 600 KB), overwriting round 1 in place under `evidence/es_nav_2026-10-22/`:

| file | bytes | sha256 (first 16) |
|---|---|---|
| es_nav_1440_dark_en.png | 138519 | 2d18e2aba3a3a245 |
| es_nav_1440_dark_zh.png | 196046 | 5a88e4d667066c2a |
| es_nav_1440_light_en.png | 205458 | 40cf8d66f4e59eb2 |
| es_nav_1440_light_zh.png | 220420 | c5b580b38278dfe7 |
| es_nav_390_dark_en.png | 57425 | c20e9875fe6cde63 |
| es_nav_390_dark_zh.png | 56463 | 2e640e3efbf0020c |
| es_nav_390_light_en.png | 57788 | 8953a8259fabeb14 |
| es_nav_390_light_zh.png | 57174 | ec9ed39225a15098 |
| es_nav_icon_2x.png | 46199 | de1dbf30b0bd5a65 |

`es_nav_icon_2x.png`: 2× device-scale crop, 2504×364 px = 1252×182 CSS px (union of the three rows + 12/10 px padding — same box round 1 used; the drill is a two-column grid, deviation D1 from round 1 applies unchanged).

### Round 2 GAPS

4. **G4 (pre-existing at base, not caused by this lane):** `tests/test_nav_hover_bridge.py::test_nav_release_key_moves_with_the_payload_it_busts` fails at base `9b14fba35cc…` with a clean tree. It is outside this round's known-3 list, so it is recorded verbatim; the parity comm shows the lane adds no failure beyond the base four, and the test file is not this lane's to edit.

Round 1's G1–G3 stand unchanged.

### Round 2 DEVIATIONS

4. The seat's R1/R2 line positions ("currently line 136/line 164") matched the file exactly; no deviation in the edit itself. The four numbered items here continue round 1's DEVIATIONS numbering: D4 is that the guarded visual-delegation helper returned a typed refusal (`GLM_VISION_DELEGATION_REFUSED reason=controller_minimax_lease_required`), so the crop's same-family judgment rests on DOM facts (identical 58×58 tiles, identical `icon-drawing` markup shape) and deterministic pixel statistics instead of a second model's visual read.
5. D5: the first 390 capture pass ran against the correct built page and passed its own assertions, but did not assert row visibility; all four 390 shots were re-captured with an explicit visibility/in-viewport assert (values above) before commit. The 1440 shots from the first pass needed no re-capture (their row facts were already asserted and recorded).

## VERDICT

See `ES_NAV_RECORD.md` at the worktree root (untracked, per commission). Copy appended below at commit time if not already present.
