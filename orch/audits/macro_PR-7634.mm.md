# Plain-language / theme / validated-claims audit — macro PR #7634

Auditor: qwen_auditor2-style pass (one-shot, half-B scope). Date: 2026-09-22.

## PR metadata

| field | value |
|---|---|
| repo | `mastermindx-market-intelligence/macro` |
| number | #7634 |
| title | `fix(reports): accessible archive filters and keyboard locale updates` |
| merged_at | 2026-09-22T07:13:09Z |
| head (squash-merge SHA on `origin/main`) | `e83b33bb8254d7e973efa74f4d6e89d3cfd453eb` |
| author-stated exact head | `a56ead2a1d46b785a6e6a59586a2e99a6293b4c2` (parent `35a6ed64d3ab8e5d0ad5436d5da41f2c260071f8`) |
| base | `main` |
| branch | `claude/uiux-reports-controls-20260921` |
| changed files | **57 files**, +1,801 / −30. Source-surface changes: `templates/reports.html.j2` (+20 / −14, MODIFIED), `site/reports.html` (+17 / −16, MODIFIED), `tests/test_reports_timeline_ui.py` (+87, MODIFIED — five new regression tests including a Node harness that actually executes the client), `site/assets/css/b219cddc.css` (NEW, +285). Rest is evidence: `agentos/discoveries/DSC-REPORTS-LOCALE-CONTROLS-20260921.md` (NEW, +19), `research/evidence/uiux-reports-controls-20260921/{README.md, source.diff, verify_reports.py, capture.txt, design.txt, final-*.txt, visual-gate.txt, red-tests-paired-baseline.txt, before.json, candidate.json, browser/*.png, browser/results.json}` (NEW), `mockups/evidence/uiux-reports-controls-20260921/{manifest.json, smells.json, EVIDENCE.yml, *.png}` (NEW). |
| labels | none visible at fetch time; merge via macro sweeper. |
| scope collision | none. Author explicitly bounds: "All seven report cards, titles, timestamps, links, archive data and the chronological sort algorithm are unchanged." Title `Grouped Reports archive repair` — local repair of a known landmine (`DSC:REPORTS-LOCALE-CONTROLS-20260921`), no model/score/data/auth surface. Skillpack `Mastermind@a3bcfdbb4d99f6af7c3a86a7fed730cbd0184465 / 1.0.1` invoked. Author notes the parent UIUX mission is incomplete and that this is an independent operation using native Git carriers. |

**Why this PR is the half-B pick.** Cross-referencing `gh pr list --state merged --limit 30 --json number,title,mergedAt --jq …` against `git ls-tree origin/main -- orch/audits/` (per the standing workflow memo `orch_audit_filename_convention.md`): the most recent macro merges before #7634 that fit the audit-on-merged-half-B scope are (a) **#7707** `orch(audit): record macro PR #7687 …` — filing-only; (b) **#7703** `orch(audit): record macro PR #7701 …` — filing-only; (c) **#7701** `[MO F07] event -> AssumptionChange` — F-series feature, NOT half-B; (d) **#7699/#7689/#7686/#7682/#7673/#7671/#7659/#7651/#7644/#7636/#7627** — all `orch(audit)` record-keeping; (e) **#7698** `docs(ric)` — research-governance; (f) **#7688/#7687** — engine-only prophet features, no template/JS/CSS user-facing surface; (g) **#7683/#7666** — research-only; (h) **#7679** `agentos` — knowledge-plane; (i) **#7678/#7628** `fix(ci)` — infra-only; (j) **#7662** `feat(brain): narrow Fast tool visibility by profile` — backend/auth, not user-visible template. PR **#7634** is the next-merged half-B candidate — a tightly bounded public archive-controls UI repair on `templates/reports.html.j2` (+20 / −14) + paired site copy (+17 / −16) + 5 new accessibility regression tests with a Node harness that actually executes the inline client, +1 new CSS asset (285 lines, derived from the `base_css` block of the template). All scope is in the user-visible Reports archive controls, where design system + bilingual + glance-tier + retrospective-evidence chain must read every line — appropriate half-B scope for this pass.

**Nature of change (six bounded repairs on the Reports archive):**

1. *Subscribe to `langchange`, not a click proxy.* Old `document.addEventListener('click', …)` filtered on `.lang-toggle` (only updates if the user *clicks* the language toggle — keyboard-activated language switching leaves the archive's `placeholder`/`aria-label`/`<option>` text stale in `zh`). New `document.addEventListener('langchange', …)` subscribes to the existing global event, so keyboard and pointer paths converge. The `t()` translation helper is reused; no new string table is introduced.

2. *Native `<button>` topic chips with `aria-pressed`.* Old: `<span class="chip" tabindex="0" role="button">` plus a manual `keydown` handler intercepting `Enter` / `Space`. New: `<button type="button" class="chip" aria-pressed="…">` — one owner for every control/state (browser handles click + keyboard + touch for free, and `aria-pressed` exposes selected state to assistive tech without a separate handler). The redundant `tagBar.addEventListener('keydown', …)` is removed, not layered on top.

3. *Translation attributes on the search input and tag bar.* Adds `data-label-en="Search reports" data-label-zh="搜索报告"` to `#repSearch` and `data-label-en="Filter by topic" data-label-zh="按主题筛选"` to `#tagBar`; `langSync()` now writes `aria-label` from these attributes alongside `placeholder`. Same EN/ZH pair that the inline `<span class="l-en">/<span class="l-zh">` blocks use elsewhere on the page.

4. *Result count is now a live region.* `<span class="rc-count" id="repCount">` → `<span class="rc-count" id="repCount" role="status" aria-live="polite" aria-atomic="true">`. Screen readers announce the count after filtering without needing focus to move.

5. *Native control sizing + canonical focus token.* New CSS in `{% block base_css %}` (which test `test_archive_stylesheet_contains_the_canonical_control_css` proves is byte-identical to the new `site/assets/css/b219cddc.css` asset):
   - `#tagBar .chip, #repSearch, #repSort, #repClear, #repClear2, #covBars .rc-cov-row { min-height:40px; touch-action:manipulation }`
   - `#tagBar button.chip { min-width:44px; font-family:var(--font-ui) }`
   - `#tagBar .chip:focus-visible, #repSearch:focus-visible, … { outline:2px solid var(--link); outline-offset:2px }`
   All four tokens are pre-existing (`--font-ui`, `--link`, `min-height:40px` is the standing tap-target floor from `docs/DESIGN_DOCTRINE.md`, `min-width:44px` matches the standing minimum). No new theme token is minted.

6. *Clear filters returns keyboard focus to Search.* `function reset(){ … if(search) search.focus(); }` — so after `Clear`, Tab starts at Search, not at the document body.

All six repairs share one design posture: native semantics first, custom JS handlers second, new CSS only where canonical tokens don't already cover it.

## Diff content (scoped to this audit)

### `templates/reports.html.j2` (+20 / −14, MODIFIED)

Four hunks:

#### Hunk 1 — new CSS in `{% block base_css %}` (`reports.html.j2:262–266`)

```css
/* Native archive controls share the existing material and focus language. */
#tagBar .chip, #repSearch, #repSort, #repClear, #repClear2, #covBars .rc-cov-row{min-height:40px;touch-action:manipulation}
#tagBar button.chip{min-width:44px;font-family:var(--font-ui)}
#tagBar .chip:focus-visible, #repSearch:focus-visible, #repSort:focus-visible, #repClear:focus-visible, #repClear2:focus-visible{outline:2px solid var(--link);outline-offset:2px}
```

All three rules reference pre-existing tokens (`--font-ui`, `--link`) and the standing sizing floor (`min-height:40px`, `min-width:44px`). Focus ring uses the canonical focus-token recipe (2px solid `--link`, 2px offset). No new token.

#### Hunk 2 — translation attrs + live region on the search/sort/count row (`reports.html.j2:334–348`)

```jinja
<input id="repSearch" type="text" autocomplete="off"
  placeholder="Search reports…" data-ph-en="Search reports…" data-ph-zh="搜索报告…" aria-label="Search reports" data-label-en="Search reports" data-label-zh="搜索报告">
…
<span class="rc-count" id="repCount" role="status" aria-live="polite" aria-atomic="true"></span>
<button type="button" class="rc-clear" id="repClear">✕ <span class="l-en">Clear</span><span class="l-zh">清除</span></button>
…
<div class="rc-tagbar" id="tagBar" role="group" aria-label="Filter by topic" data-label-en="Filter by topic" data-label-zh="按主题筛选">
  <button type="button" class="chip on" data-tag="all" aria-pressed="true">{{ t('All','全部') }}</button>
  {% for tg in all_tags %}<button type="button" class="chip tag-{{ tg.key }}" data-tag="{{ tg.key }}" aria-pressed="false"><span class="l-en">{{ tg.en }}</span><span class="l-zh">{{ tg.zh }}</span> <span class="n">{{ tg.count }}</span></button>{% endfor %}
</div>
```

Replaces the `<span class="chip" tabindex="0" role="button">` shim with native `<button>` chips carrying `aria-pressed`. The `data-label-en/zh` pair matches the established pattern used by the existing `data-ph-en/zh` / `data-en/zh` translation attributes elsewhere in the file. The `role="status" aria-live="polite" aria-atomic="true"` is the standard live-region recipe for a count that updates without focus movement.

#### Hunk 3 — `langSync()` + `syncTagUI()` + `reset()` JS (`reports.html.j2:410–460`)

```js
function langSync(){ // keep non-span UI (placeholder, <option>s) in sync with language
  var zh=isZh();
  if(search){
    search.placeholder=search.getAttribute(zh?'data-ph-zh':'data-ph-en')||'';
    search.setAttribute('aria-label',search.getAttribute(zh?'data-label-zh':'data-label-en'));
  }
  if(tagBar) tagBar.setAttribute('aria-label',tagBar.getAttribute(zh?'data-label-zh':'data-label-en'));
  if(sortSel)[].forEach.call(sortSel.options,function(o){ o.textContent=zh?(o.getAttribute('data-zh')||o.textContent):(o.getAttribute('data-en')||o.textContent); });
}

function syncTagUI(){
  [].forEach.call(tagBar.querySelectorAll('.chip'),function(x){
    var selected=(x.getAttribute('data-tag')||'all')===activeTag;
    x.classList.toggle('on',selected);
    x.setAttribute('aria-pressed',String(selected));
  });
  …
}

function reset(){ activeTag='all'; q=''; if(search) search.value=''; apply(); writeURL(true); if(search) search.focus(); }
```

`langSync()` collapses the ternary to a single read with a default empty string (the placeholder/aria-label pattern now matches the existing `<option>` textContent pattern below it). `syncTagUI()` now mirrors selection state into `aria-pressed` after every tag change so the live DOM matches the canonical chip selection. `reset()` adds `search.focus()` to return keyboard focus after Clear. The existing `tagBar.addEventListener('keydown', …)` shim is deleted (no longer needed; native `<button>` handles Enter/Space).

#### Hunk 4 — `langchange` event subscription (`reports.html.j2:506`)

```js
// re-sync non-span UI + count when the global language toggle flips
document.addEventListener('langchange',function(){ langSync(); apply(); });
```

Replaces the prior `document.addEventListener('click',function(e){ if(e.target.closest('.lang-toggle')) setTimeout(function(){ langSync(); apply(); },0); });` with a direct event subscription to `langchange` (the same event the rest of the page already fires from the global handler). Fixes the landmine — keyboard-activated language switch no longer leaves the archive's `placeholder`/`aria-label`/`<option>` text stale in `zh`.

### `site/reports.html` (+17 / −16, MODIFIED)

Pure byte-match of the template change, plus the CSS asset reference update `assets/css/a665da12.css?v=a665da12` → `assets/css/b219cddc.css?v=b219cddc`. The paired-template-site-sync check is enforced (`scripts/check_template_site_sync.py`); the build + post-render flow keeps these two in lockstep.

### `site/assets/css/b219cddc.css` (NEW, +285)

Carries the entire page CSS bundle. Test `test_archive_stylesheet_contains_the_canonical_control_css` asserts that the `{% block base_css %}` body from `templates/reports.html.j2` appears byte-identical inside this asset, and that the inline `<script>` from `{% block body_scripts %}` appears byte-identical inside `site/reports.html`. So the new native-control CSS in Hunk 1 is shipped to users via the bundled asset, not via a parallel runtime stylesheet.

### `tests/test_reports_timeline_ui.py` (+87, MODIFIED — five new regression tests)

1. `test_archive_locale_event_updates_native_labels_without_click_dependency` — pins `'document.addEventListener(\'langchange\''` in template, negative-asserts `'e.target.closest(\'.lang-toggle\')'` is gone, both bilingual translation attrs (`data-label-zh="搜索报告"`, `data-label-zh="按主题筛选"`), and `id="repCount" role="status"`.
2. `test_archive_topic_filters_are_native_pressed_buttons` — pins the new `<button type="button" class="chip on" data-tag="all" aria-pressed="true">` markup, the `<button type="button" class="chip tag-{{ tg.key }}"` pattern, the `x.setAttribute('aria-pressed',String(selected))` JS write, and negative-asserts `tagBar.addEventListener('keydown'` is gone.
3. `test_archive_controls_have_touch_and_focus_contracts` — pins `min-height:40px;touch-action:manipulation`, `#tagBar button.chip{min-width:44px`, the `:focus-visible` rule, and `writeURL(true); if(search) search.focus();`.
4. `test_archive_stylesheet_contains_the_canonical_control_css` — byte-equality test: the `base_css` block lands in the CSS asset, the inline `<script>` lands in the paired HTML. The hash on the `<link rel="stylesheet" href="assets/css/<8hex>.css?v=<8hex>"` is the asset's actual digest (no fake `?v=`).
5. `test_archive_actual_client_keeps_query_order_and_filter_during_locale_change` — Node-executed actual client test. Builds a DOM harness (`repSearch` / `repSort` / `tagBar` / `repCount` / `repClear2` mocks with `attrs`, `events`, `options`, `addEventListener`, `focus`, `classList`, etc.), seeds three reports with `data-date`/`data-tags`/`data-search`, primes `?q=policy&tag=macro&sort=old#archive`, runs the actual client from the template, then asserts (a) `query`/`sort`/`order`/`url` are unchanged before/after `langchange → zh`, (b) `placeholder == "搜索报告…"`, `aria-label == "搜索报告"`, `option[0].textContent == "最新优先"`, `count == "2 篇报告"`, `aria-pressed == ["macro"]`, and (c) `repClear2` click produces `query==""`, focus moves to Search, `aria-pressed == ["all"]`.

Local re-run: `python3 -m pytest tests/test_reports_timeline_ui.py -q -k archive` → **6 passed, 27 deselected in 0.77s**.

## Plain-language findings

### 1.1 Pass — all visible copy is bounded plain-language, no internal study slug / state enum / untranslated stat token at user-visible position

- **Search placeholder / aria-label.** `Search reports…` (EN) / `搜索报告…` (ZH). Bounded noun phrase; no jargon.
- **Sort options.** `Newest first` / `Oldest first` (EN) / `最新优先` / `最早优先` (ZH). Both EN/ZH pairs are plain-language ordering cues; no stat token or study slug.
- **Result count.** `2 篇报告` (the value tested in the Node harness). The existing render path formats via `t('%d 篇报告', …)`; the PR does not touch the format string. Count is a number + a plain-language noun.
- **Clear.** `Clear` (EN) / `清除` (ZH). Plain-language action verb.
- **Topic chips.** `All / Macro / AI / Crypto / Equities / China / Fed / Rates / Credit / Energy / Midterms` (EN) ↔ `全部 / 宏观 / AI / 加密 / 股票 / 中国 / 美联储 / 利率 / 信用 / 能源 / 中期选举` (ZH). All eleven pairs are plain-language category names; none is an internal study slug (`prophet`, `oracle`, `conductor`, `synapse`, `lobe`, `tripwire`, `falsifier`, etc. — none present in the diff). None is a raw state enum. None is an untranslated stat token (`iv_rank`, `gex`, `vanna`, `charm`, `dte`, `oi`, `pcr`, `rv30`, `zscore`, `pctl`, `yoy`, `qoq`, `ttm`, `cagr` — none present in the diff).
- **Tag bar aria-label.** `Filter by topic` (EN) / `按主题筛选` (ZH). Plain-language action label.
- **Search aria-label.** `Search reports` (EN) / `搜索报告` (ZH). Plain-language action label.

The PR's entire user-visible copy surface is bounded plain-language under the glance-tier word cap; no state-name, study-slug, or stat-token leakage.

### 1.2 Pass — bilingual parity is intact (EN/ZH pairs everywhere)

Every visible string in the diff has a paired EN/ZH form, via either `t('EN','ZH')` (search label / topic chips), the `<span class="l-en">/<span class="l-zh">` pattern (Clear button), or `data-label-en`/`data-label-zh` / `data-ph-en`/`data-ph-zh` / `data-en`/`data-zh` attributes (search input, tag bar, sort options). The `langSync()` writer subscribes to the global `langchange` event (Hunk 4) so both pointer-click and keyboard-activated language switches flip all of `placeholder`/`aria-label`/`<option> textContent` together. CI guard `bilingual_parity_check` is unaffected.

### 1.3 Pass — null disclosure: no empty / `N/A` / `—` rendered by this PR

The PR does not add a new conditional render path that could produce an empty string. The result count is empty at initial load (live region), and is populated by the existing `apply()` path that the PR does not touch. No `'null'`, `'None'`, `'N/A'`, `'—'`, or empty Jinja literal is rendered by the new code.

### 1.4 Pass — keyboard / activation contract uses one native control/state owner

The PR's design posture is the **opposite** of a keyboard shim: it *removes* the manual `tagBar.addEventListener('keydown', …)` handler and the `tabindex="0" role="button"` span pattern, replacing both with native `<button type="button">`. The browser now owns Enter/Space/tap/click semantics; the PR owns only the canonical `aria-pressed` state mirror in `syncTagUI()`. One control, one state, one owner. The landmine in `DSC:REPORTS-LOCALE-CONTROLS-20260921` (`falsifier:` "all labels must already switch and native selected state must already be present to disprove the defect") is closed at the source — the negative-assert tests pin that the old shim is gone, not layered on top.

### 1.5 Pass — focus, sizing, and tap-target floors are within standing doctrine

- `min-height:40px` on every archive control — matches the standing tap-target floor in `docs/DESIGN_DOCTRINE.md` and the `40px floor` mentioned in `templates/_public_chrome_css.html.j2` (and the same floor the new CSS bundles alongside).
- `min-width:44px` on `#tagBar button.chip` — matches the standing WCAG-recommended 44px target floor for tap targets.
- `touch-action:manipulation` — disables double-tap zoom on archive controls without disabling pinch or pan; correct for an interactive archive.
- `:focus-visible { outline:2px solid var(--link); outline-offset:2px }` — canonical focus ring recipe (2px solid, 2px offset). Uses the pre-existing `--link` token.

### 1.6 Pass — keyboard recovery after Clear

`reset()` now ends with `if(search) search.focus();` so a keyboard user pressing `Clear` lands back on Search, not on the document body. This is the standard post-action focus return for a search interface and matches the focus-return contract used in other archive/repo surfaces.

## Theme findings

### 2.1 Pass — no new theme token, no parallel palette, no opaque runtime stylesheet system

The new CSS in `{% block base_css %}` references exactly four existing tokens (`--font-ui`, `--link`) and the standing 40px / 44px sizing floors. No new variable is declared in `b219cddc.css` (verified — the only `:root` definitions in the asset are pre-existing `--bg`, `--text`, `--muted`, `--line`, `--panel2`, `--link`, `--font-ui`, `--ink-link`). The change is a **binding of canonical tokens to native-control sizing and focus**; no material decision is being authored here.

The PR does not introduce any inline `style.textContent` block, `document.head.appendChild(styleEl)` block, or JS-driven palette swap. The new `:focus-visible` rule is declarative CSS, the live region (`role="status"`) is a DOM attribute, the `aria-pressed` mirror is an attribute setter — none is a parallel palette or runtime-stylesheet family. The runtime-stylesheet-injection guard `scripts/check_runtime_style_injection.py` is unaffected.

The design-system ratchet (`scripts/check_design_system.py --mode enforce-added --diff-file <(git diff origin/main -- templates/reports.html.j2)`) reports `0 blocking finding(s)`. The visual-evidence guard (`scripts/check_ui_visual_evidence.py`) was satisfied by the captured manifest (12 states × EN/ZH × dark/light × desktop 1440 / mobile 390 / narrow 320, all SHA-256-digested in `mockups/evidence/uiux-reports-controls-20260921/manifest.json`).

### 2.2 Pass — light/dark parity preserved (no parallel palette, no token-substitution-only failure)

The Reports page renders correctly in both themes both before and after this PR. The new CSS uses canonical tokens (`--link`, `--font-ui`) that already have dark and light treatments; no new theme-family is created. The visual evidence pack contains desktop-EN-dark, desktop-EN-light, desktop-ZH-dark, desktop-ZH-light, mobile-EN-dark, mobile-EN-light, mobile-ZH-dark, mobile-ZH-light, narrow-EN-dark, narrow-EN-light, narrow-ZH-dark, narrow-ZH-light — both themes are captured, and the dark/light difference is in material treatment (the `--bg`/`--text`/`--muted` tokens) not in the new CSS.

The TP-0 law (`docs/DESIGN_DOCTRINE.md` — "dark and light share IA/component/state semantics but may differ in material treatment") is satisfied: the new CSS does not assert a material difference, it asserts an accessibility contract (sizing + focus + touch + selection state) that holds in both themes identically.

### 2.3 Pass — `:focus-visible` is the canonical focus recipe, not a new visual language

`outline:2px solid var(--link); outline-offset:2px` is the standing focus-token recipe used throughout the public chrome (see `_public_chrome_css.html.j2` `:focus-visible` block and the same recipe in `_public_nav.html.j2`). The PR does not invent a new focus treatment; it applies the canonical one to the archive controls that previously lacked it. The rule is wrapped in `:focus-visible` (not `:focus`), so mouse clicks do not leave a focus ring — only keyboard navigation does, which is the correct modern focus convention.

### 2.4 Pass — typography uses `var(--font-ui)` for the chips, matching existing UI typography

`#tagBar button.chip { font-family: var(--font-ui); }` is added because the new `<button>` element defaults to the user-agent's button font (a system serif on most platforms), which would visually drift from the rest of the archive's chip styling. The rule explicitly re-binds to the existing `--font-ui` token, so the chips render with the same type as before. No new font family is introduced.

### 2.5 Pass — paired template/site CSS is byte-identical (CI-guarded)

`scripts/check_template_site_sync.py` enforces that any non-`.j2` `templates/<name>` paired with `site/<name>` ships with a byte-matching `site/` copy. The build extracts the `{% block base_css %}` body from `templates/reports.html.j2`, bundles it into `site/assets/css/b219cddc.css?v=b219cddc`, and the paired `site/reports.html` references the asset via a self-referential hash digest (the `<link rel="stylesheet" href="assets/css/b219cddc.css?v=b219cddc">` — the hash matches the filename, so caches bust correctly on change). The new `test_archive_stylesheet_contains_the_canonical_control_css` test pins this byte-equality contract from the test side; the build-side `check_template_site_sync.py` enforces it from the build side.

## Validated-claims findings

### 3.1 Pass — no new "validated" / "proven" / "已验证" claims authored by this PR

`scripts/check_validated_claims.py --list | grep reports.html` returns no MISS for `templates/reports.html.j2` or `site/reports.html`. The PR's diff does not add any new occurrences of the `validated` / `proven` / `已验证` vocabulary. All five new tests in `tests/test_reports_timeline_ui.py` use the test-side `assert` keyword, which the claim-list gate is scoped to ignore (test code is not user-visible copy).

### 3.2 Pass — `aria-pressed` is a control-state attribute, not a validated-edge claim

`aria-pressed="true"` / `aria-pressed="false"` is the W3C ARIA state for a toggle button's selection state. It is a control-state assertion (this button is selected / this button is not selected), NOT an "edge validated" / "signal validated" / "OOS validated" claim. The validated-claims gate's affirmative vocabulary (`validated`, `proven`, `已验证`, `verified`, `gauntlet`, `passed`, `OOS`, `cone validated`, `risk · validated`, `direction (validated)`, `cone validated`, `whichever horizon validated`) is not used in the diff. The state assertion is appropriately scoped to the chip's local selection, not to a model/signal/ranking.

### 3.3 Pass — `role="status"` does not assert validated/score/ranking provenance

The live-region attribute `role="status" aria-live="polite" aria-atomic="true"` is the standard ARIA pattern for a count that updates without focus movement. It does not assert that the underlying reports are validated/proven/scored; it announces the count (`2 篇报告` or `Showing all 7 reports`) as a status update. The narrative is "the count of currently-matching items is N", which is observationally true by definition (the count is derived from `apply()` after every filter change).

### 3.4 Pass — copy-law: "what we're watching" pattern, not "falsifier fired / thesis refuted / 证伪"

The PR's copy surface does not introduce any tripwire/falsifier/refutation language. The standing copy law (`AGENTS.md` §Design — "Falsifier/refutation language is never front-facing… user cycle surfaces show projection windows ('windows, not certainties — re-drawn nightly'), quiet 'read being updated' chips, and 'what we're watching' conditions — never 'falsifier fired / thesis refuted / 证伪'") is satisfied by absence: no new "fired" / "broken" / "invalidated" / "证伪" / "反证" / "失效" tokens appear in the diff. The archive's existing "no results" state, the existing `repClear2` label, and the existing sort options are unchanged.

### 3.5 Pass — instrument verdicts vs market verdicts invariant

The PR's `aria-pressed` mirror in `syncTagUI()` reflects the **chip selection state** (which topic filter the user clicked), not a market verdict. The instrument-verdict vs market-verdict invariant ("Instrument verdicts are NOT market verdicts — a chain/tripwire terminal state means its declared WINDOWS failed — never 'the thesis is false'") is satisfied by the local scope of `aria-pressed`: it asserts "this chip is the currently selected topic filter", nothing more. No new window/tripwire/chain terminal state is being surfaced to the user.

## Overall verdict

**PASS — all three dimensions green; ship.**

- **Plain-language (1.1–1.6):** PASS. All user-visible copy is bounded plain-language under the glance-tier cap. No state enum, study slug, or untranslated stat token. Bilingual parity intact. Native `<button>` semantics replaces the keyboard shim. Focus, sizing, tap-target floors, and keyboard-recovery contract all match standing doctrine.
- **Theme (2.1–2.5):** PASS. No new theme token. No parallel palette or opaque runtime stylesheet system. Dark/light parity preserved (canonical tokens used identically in both themes). `:focus-visible` recipe matches the standing focus-token pattern. Paired template/site CSS is byte-identical (CI-guarded). Typography re-binds to `var(--font-ui)` so the new `<button>` chips render with the same type as before.
- **Validated-claims (3.1–3.5):** PASS. No new `validated` / `proven` / `已验证` claims. `aria-pressed` is a control-state attribute, not a validated-edge claim. `role="status"` announces a count, not a provenance. No front-facing falsifier language. Instrument verdict vs market verdict invariant preserved.

**Evidence summary.** Author-ship local re-runs all green: 33 tests passed in `tests/test_reports_timeline_ui.py` (5 new functions, all passing), 6 archive-tagged tests passed under `-k archive`, 12 native browser cases passed (3 viewports × 2 locales × 2 themes), 24 canonical visual states captured, design-system ratchet reports 0 blocking findings on the diff, validated-claims gate has no new misses, paired template/site CSS is byte-identical. CI runs on `origin/main` for the squash-merge head `e83b33bb8254d7e973efa74f4d6e89d3cfd453eb` are the next check; PR body asserts "Final release requires concluded first-party CI, expected-head acceptance, the existing VPS updater and anonymous public proof."

**Audit posture.** This is the standard half-B scope: public archive controls + paired CSS + paired site copy + five regression tests including a Node harness that actually executes the inline client. The PR closes a known landmine (`DSC:REPORTS-LOCALE-CONTROLS-20260921`) without layering on the old shim, without inventing a parallel system, and without authoring a new claim. The repair is honest, scoped, and tested end-to-end.

**Session classification:** `PROVEN_OUTCOME` — audit complete, file written, no follow-up work surfaced.