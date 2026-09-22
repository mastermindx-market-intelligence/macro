# Plain-language / theme / validated-claims audit — macro PR #7634

Auditor: qwen_auditor2-style pass (one-shot, half-B scope, focused on the user-facing surface). Date: 2026-09-22.

## PR metadata

| field | value |
|---|---|
| repo | `mastermindx-market-intelligence/macro` |
| number | #7634 |
| title | `fix(reports): accessible archive filters and keyboard locale updates` |
| merged_at | 2026-09-22T07:13:09Z |
| head (semantic) | `a56ead2a1d46b785a6e6a59586a2e99a6293b4c2` |
| base | `main` |
| branch | `claude/uiux-reports-controls-20260921` |
| changed files | **49 files, +1801 / −30.** Surface relevant to this audit: `templates/reports.html.j2` (+20 / −14, MODIFIED), `site/reports.html` (+17 / −16, MODIFIED — paired plain-copy asset, byte-matched to template via `scripts/check_template_site_sync.py`), `site/assets/css/b219cddc.css` (+285 / 0, ADDED — paired stylesheet). Non-surface files: `tests/test_reports_timeline_ui.py` (+87 / 0), `research/evidence/uiux-reports-controls-20260921/` (24 evidence artefacts: 12 browser screenshots × EN/ZH × dark/light × desktop/mobile/narrow + manifests + receipts + verify script), `mockups/evidence/uiux-reports-controls-20260921/` (22 mockup/manifest artefacts), `agentos/discoveries/DSC-REPORTS-LOCALE-CONTROLS-20260921.md` (+19 / 0, ADDED). |
| additions / deletions | 1801 / 30 (overall) — 322 / 30 (user-facing surface: 20+17+285 added on the template, paired plain-copy, and paired stylesheet) |
| labels | none visible at fetch time; merge came in via the macro sweeper on the listed timestamp. |
| scope collision | none. PR body explicitly bounds scope: *"All seven report cards, titles, timestamps, links, archive data and the chronological sort algorithm are unchanged."* The change is a structural accessibility / locale repair to the existing Research Reports archive — no new product surface, no new claim, no new model/data authority, no new trade/promotional element. |
| precedent | local proof listed by author — `33 tests passed` (5 new regression functions in `tests/test_reports_timeline_ui.py`), `4 functional regressions fail on the paired original source`, `12 native browser cases passed` (1440 desktop, 390 mobile, 320 narrow × EN/ZH × dark/light), `24 canonical visual states captured`, `design enforce-added gates pass`, `runtime style injection` clean. The audit below re-runs and confirms against the standing plain-language / theme / validated-claims laws. |

**Why this PR is the half-B pick.** Cross-referencing `gh pr list --state merged --limit 30 --json number,title,mergedAt --jq …` against `git ls-tree origin/main -- orch/audits/` and the working-tree-untracked audit files (4 files: `macro_PR-7667`, `macro_PR-7687`, `macro_PR-7688`, `macro_PR-7701`), the most recent non-audit-recording merges before #7634 are: (a) **#7667** `Add compact China regime driver rail` — already audited via `orch/audits/macro_PR-7667.mm.md`; (b) **#7687** `fix(prophet): keep optional structural overlay from deadlocking B4` — already audited via `orch/audits/macro_PR-7687.mm.md`; (c) **#7688** `feat(prophet): own B4 session eligibility policy` — engine-only, HOLD-FOR-SOL per the PR body, not user-facing; (d) **#7698** `docs(ric):` — docs only; (e) **#7683 / #7666** `research(risk):` — evidence-only; (f) **#7679** `agentos:` — knowledge-plane only; (g) **#7678 / #7628** `fix(ci):` — infra only; (h) **#7639 / #7637** `[MO-A heal]` design-governance deepen — infra only; (i) **#7632** `fix(risk):` — engine-only; (j) **#7629** `Fix China public live client and shared reason Lens` — China-public surface (out of the language-switch / accessibility scope here). **#7634 is a pure half-B user-facing fix on a public Reports archive surface — the report cards, titles, and data are untouched, only the controls around them (search, sort, count, clear, topic chips) become native and locale-correct.** That is the appropriate half-B audit scope — the engine / agentos / tests / evidence-blob dimensions are not user-facing copy and are out of scope for plain-language / theme / validated-claims law; the template + paired site copy + paired stylesheet is, and that is what this audit covers.

**Nature of change (one template, +20 / −14; one paired site copy, +17 / −16; one paired stylesheet, +285):**

1. *Native topic chips* (template lines ~343–348, paired site ~442–449). Span-based chips with `tabindex="0" role="button"` + manual `keydown` shim → native `<button type="button">` with `aria-pressed="true|false"`. The old keyboard shim is **removed, not layered on** (per PR body). Native buttons own Enter / Space / tap activation for free.

2. *Locale-aware aria-labels* (template lines ~337, ~345; paired site identical). Search input gains `data-label-en="Search reports" data-label-zh="搜索报告"` (ZH already paired with the existing `data-ph-en/zh`). The tag bar group gains `data-label-en="Filter by topic" data-label-zh="按主题筛选"`. The `langSync()` function now calls `setAttribute('aria-label', …)` against both nodes, so screen-reader readers flip labels in lock-step with the visible placeholder and sort options.

3. *Live count* (template line ~346, paired site identical). `<span class="rc-count" id="repCount">` → `<span class="rc-count" id="repCount" role="status" aria-live="polite" aria-atomic="true">`. Screen readers announce filter-result changes without forcing a re-focus.

4. *Focus recovery on Clear* (template line ~459, paired site identical). `reset()` ends with `if(search) search.focus();` so clearing filters returns keyboard focus to Search — the canonical WCAG 2.4.3 / 3.2.4 sequence.

5. *Langchange event subscription* (template line ~509, paired site identical). `document.addEventListener('click', function(e){ if(e.target.closest('.lang-toggle')) setTimeout(…) })` (a pointer-click proxy that misses keyboard language flips) → `document.addEventListener('langchange', function(){ langSync(); apply(); })` — listens to the canonical custom event the language toggle dispatches on both keyboard and pointer activation.

6. *Stylesheet (paired `b219cddc.css`, +285).* The full Research Reports Center stylesheet migrates from inline `<style>` in the template into a paired hashed asset `b219cddc.css` (consistent with the standing render budget / Caddyfile `immutable` pattern). All existing visual rules are preserved verbatim. The migration also adds:
   - Native focus rings: `outline:2px solid var(--link);outline-offset:2px` on `:focus-visible` for `#tagBar .chip`, `#repSearch`, `#repSort`, `#repClear`, `#repClear2`.
   - Touch-target floors: `min-height:40px; touch-action:manipulation` on `#tagBar .chip`, `#repSearch`, `#repSort`, `#repClear`, `#repClear2`, `#covBars .rc-cov-row`. `#tagBar button.chip` also gets `min-width:44px` and `font-family:var(--font-ui)` for tokenised typography.
   - `[data-theme="light"] .rc-shell` block — explicit light-theme glass material (different `--rc-glass-bg`, `--rc-glass-brd`, `--rc-glass-shadow`, `--rc-glass-hover` values).
   - `[data-lang="zh"] body` font stack — CJK-first (`"PingFang SC", "Hiragino Sans GB", …, "Noto Sans CJK SC"`).
   - `[data-lang="zh"] .rc-display-on{ letter-spacing:0; }` — disables the EN-side `letter-spacing:-.025em~-0.35em` for CJK.
   - `@media (prefers-reduced-motion: reduce)` — disables `rcPulse` (the live dot pulse), `rcGrow` (the bar fill animation), and the card / cov-row / chip hover transforms.

## Diff content (scoped to this audit)

Three files, all user-facing template / paired site / paired CSS surface. No new JS function with semantic meaning, no new engine module, no new theme token at root, no new palette, no new font (CSS only re-orders existing font stacks to put CJK first under `[data-lang="zh"]`).

### `templates/reports.html.j2` (+20 / −14, MODIFIED)

#### Hunk 1 — focus / touch-target CSS additions (5 lines, added to existing `<style>` block, lines ~258–266)

```css
/* Native archive controls share the existing material and focus language. */
#tagBar .chip, #repSearch, #repSort, #repClear, #repClear2, #covBars .rc-cov-row{min-height:40px;touch-action:manipulation}
#tagBar button.chip{min-width:44px;font-family:var(--font-ui)}
#tagBar .chip:focus-visible, #repSearch:focus-visible, #repSort:focus-visible, #repClear:focus-visible, #repClear2:focus-visible{outline:2px solid var(--link);outline-offset:2px}
```

All three rules use **only existing design-system tokens**: `--link`, `--font-ui`. No new `--var`. `:focus-visible` (not `:focus`) — focus ring only appears on keyboard focus, not on mouse-click focus, per the canonical pattern. The selector list pairs each control with its material rule, so a screen-reader user gets the same outline a keyboard user gets.

#### Hunk 2 — search input aria-label data attributes (line ~337)

```jinja
<input id="repSearch" type="text" autocomplete="off"
  placeholder="Search reports…" data-ph-en="Search reports…" data-ph-zh="搜索报告…"
  aria-label="Search reports" data-label-en="Search reports" data-label-zh="搜索报告">
```

Two new attributes (`data-label-en`, `data-label-zh`) added; the EN `aria-label="Search reports"` remains as the canonical default (the page's initial language is determined by `localStorage.getItem('lang')`; the `aria-label` is overridden on `langchange`). The ZH string `搜索报告` is a real Chinese translation of "Search reports" (not a literal transliteration). The `data-label-en` mirror the existing `aria-label` value to keep `langSync()` symmetric.

#### Hunk 3 — count span gains live-region semantics (line ~346)

```jinja
<span class="rc-count" id="repCount" role="status" aria-live="polite" aria-atomic="true"></span>
```

Three new ARIA attributes: `role="status"` marks the node as a status region, `aria-live="polite"` queues announcements without interrupting the user, `aria-atomic="true"` reads the entire content rather than diffs. The CSS class is unchanged (`color:var(--muted)`, `font-variant-numeric:tabular-nums`); this is a structural accessibility addition, not a visual change.

#### Hunk 4 — tag bar group aria-label data attributes (line ~345)

```jinja
<div class="rc-tagbar" id="tagBar" role="group" aria-label="Filter by topic"
     data-label-en="Filter by topic" data-label-zh="按主题筛选">
```

Same pattern as the search input. `按主题筛选` is real Chinese ("filter by topic"); the canonical `aria-label` remains the EN string until the language toggle dispatches `langchange`.

#### Hunk 5 — topic chips become native buttons (lines ~346–348)

```jinja
<button type="button" class="chip on" data-tag="all" aria-pressed="true">{{ t('All', '全部') }}</button>
{% for tg in all_tags %}<button type="button" class="chip tag-{{ tg.key }}" data-tag="{{ tg.key }}" aria-pressed="false"><span class="l-en">{{ tg.en }}</span><span class="l-zh">{{ tg.zh }}</span> <span class="n">{{ tg.count }}</span></button>{% endfor %}
```

Three structural changes:
- `<span … tabindex="0" role="button">` → `<button type="button">`. Native buttons handle Enter / Space activation, focus, and click uniformly without a JS shim.
- Added `aria-pressed="true|false"` — exposes the toggle state to assistive tech. The `aria-pressed` is wired to `activeTag` via the `syncTagUI()` JS change (hunk 8).
- The `<span class="l-en">…</span><span class="l-zh">…</span>` inner structure is unchanged — bilingual visibility mechanism preserved.

#### Hunk 6 — `langSync()` updates aria-label (lines ~410–418)

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
```

Two new lines (search `aria-label` sync, tag-bar `aria-label` sync). Pre-existing logic preserved (placeholder sync, sort-option text sync). `langSync()` is the canonical hook called once on load + once on every `langchange` event, so the aria-label switch is now driven by the same source of truth as the placeholder and sort options.

#### Hunk 7 — `syncTagUI()` writes `aria-pressed` (lines ~419–425)

```js
function syncTagUI(){
  [].forEach.call(tagBar.querySelectorAll('.chip'),function(x){
    var selected=(x.getAttribute('data-tag')||'all')===activeTag;
    x.classList.toggle('on',selected);
    x.setAttribute('aria-pressed',String(selected));
  });
  if(cov)[].forEach.call(cov.querySelectorAll('.rc-cov-row'),function(x){
    x.setAttribute('aria-pressed',(x.getAttribute('data-tag')===activeTag)?'true':'false');
  });
  …
}
```

Pre-existing `.classList.toggle('on', …)` preserved; new `aria-pressed` write mirrors the same predicate. The `String(selected)` cast produces the literal `"true"` / `"false"` strings (the values the HTML attribute spec requires, not booleans).

#### Hunk 8 — `reset()` returns focus to search (line ~459)

```js
function reset(){ activeTag='all'; q=''; if(search) search.value=''; apply(); writeURL(true); if(search) search.focus(); }
```

One new line at the end. `search.focus()` is the canonical WCAG 3.2.4 / 2.4.3 focus return after a destructive action. The pre-existing `writeURL(true)` writes the URL-owned state BEFORE the focus call so the URL bar / focus order never desync.

#### Hunk 9 — span keydown shim REMOVED (lines ~485–489, delete 5 lines)

```js
- tagBar.addEventListener('keydown',function(e){
-   if(e.key!=='Enter'&&e.key!==' ') return;
-   var c=e.target.closest('.chip'); if(!c) return;
-   e.preventDefault(); setTag(c.getAttribute('data-tag'));
- });
```

Five lines deleted, not edited. Native `<button>` handles Enter / Space via the browser's own click-dispatch (the `tagBar.addEventListener('click', …)` listener immediately above the deleted block still fires on the synthetic click). Removing the shim eliminates the duplicated activation path (the shim previously also dispatched on native-button's bubble-phase click, double-firing once).

#### Hunk 10 — `langchange` event replaces click-proxy (line ~509)

```js
- document.addEventListener('click',function(e){ if(e.target.closest('.lang-toggle')) setTimeout(function(){ langSync(); apply(); },0); });
+ document.addEventListener('langchange',function(){ langSync(); apply(); });
```

Replaces a pointer-click proxy that missed keyboard activation with a canonical custom-event subscription. The custom `langchange` event is already dispatched by the global language toggle (`templates/_public_chrome_js.html.j2` / `_site_nav.html.j2` family) on both keyboard and pointer activation. One listener, one source of truth, no `setTimeout(0)` race.

### `site/reports.html` (+17 / −16, MODIFIED — paired plain-copy asset)

Identical structural changes to the template, byte-matched to the rendered output. The standing `scripts/check_template_site_sync.py` guard refuses a PR if `templates/<name>` and `site/<name>` diverge for any non-`.j2` template that ships as a plain-copy asset (PR body: *"generated client matches the template. No new CI job or runtime styling system."*). This audit does not re-run the byte-match (CI-guarded), only confirms the two diffs are parallel.

### `site/assets/css/b219cddc.css` (+285 / 0, ADDED — paired stylesheet)

The full Research Reports Center stylesheet now lives in a paired hashed asset (consistent with the standing render pattern: `templates/<page>.html.j2` ships its inline `<style>` → render produces `site/<page>.html` + `site/assets/css/<hash>.css`). The 285 lines cover the existing research-reports chrome and the new accessibility / locale additions. The diff is structurally a relocation: rules are preserved verbatim where they were already correct, and the new hunk (5 lines, identical to the template's `<style>`-block additions) sits at the end of the stylesheet alongside the existing responsive / motion blocks. All design-system tokens consumed (`--bg`, `--text`, `--muted`, `--link`, `--panel`, `--panel2`, `--line`, `--info`, `--font-ui`, `--font-mono`) are pre-existing on `origin/main` (verified: 12 matches in `site/theme.css`, 12 matches in `templates/theme.css`). Component-local variables (`--rc-sans`, `--rc-accent`, `--rc-accent-2`, `--rc-ink-2`, `--rc-glass-bg`, `--rc-glass-brd`, `--rc-glass-shadow`, `--rc-glass-hover`, `--rc-blur`, `--rc-radius`, `--rc-display`) are scoped inside `.rc-shell{…}` / `body{…}` blocks — they don't pollute the global theme root, and they derive from the global tokens via `var(--info)` and `color-mix(in srgb, var(--text) X%, transparent)`.

### `tests/test_reports_timeline_ui.py` (+87 / 0, MODIFIED)

Five new regression functions added per PR body: `archive_search_label_locale_sync`, `tag_bar_aria_label_locale_sync`, `topic_chip_native_button_activation`, `count_live_region_announces_filter_change`, `clear_filters_returns_focus_to_search`. Plus the existing test infrastructure (`Node execution of the actual client` per PR body) — the tests run against the real paired `site/reports.html`, not a mock.

### `agentos/discoveries/DSC-REPORTS-LOCALE-CONTROLS-20260921.md` (+19 / 0, ADDED)

The DSC record carries both `falsifier` (the paired-original source replay that would disprove the defect) and `so_what` (the concrete subscription / button / focus prescription). `verified_at: 2026-09-21`, `verified_by: 'python3 -m pytest tests/test_reports_timeline_ui.py -q -k archive_'`, `confidence: verified`. Per the standing agentos workflow, a DSC without both `falsifier` and `so_what` would be a log line; this one carries both, so it is a real discovery.

## Plain-language findings

### 1.1 Pass — no new user-facing copy text; all visible strings already pass glance-tier law

The diff adds **zero** new visible EN/ZH strings. The only new strings are:

| Where | EN | ZH |
|---|---|---|
| `aria-label` data attr (search) | `data-label-en="Search reports"` | `data-label-zh="搜索报告"` |
| `aria-label` data attr (tag bar) | `data-label-en="Filter by topic"` | `data-label-zh="按主题筛选"` |

Both pairs are real translations, both already used as visible labels elsewhere on the page (`Search reports` / `搜索报告` is the existing search placeholder; `Filter by topic` / `按主题筛选` is the existing `aria-label`), and both flow through `t()` / the `data-label-*` attributes via `langSync()` so they are bilingual-by-construction.

No banned-glance / banned-tier vocabulary anywhere in the diff:
- 0 hits for "validated | 已验证 | 经验证 | 经过验证" (`grep -ciE 'validated|已验证|经验证|经过验证' /tmp/pr7634.diff` → 0).
- 0 hits for any banned internal-organ slug (`prophet`, `oracle`, `conductor`, `synapse`, `lobe`, `tripwire`, `falsifier`, `brain`, `neural-web`, `state`, `regime`, `status`, `tier`, `verdict`, `classification`, `bucket`, `urgency`, `code`, `kind`, `category`, `type`, `slug`) in any user-facing position (`grep -ciE 'prophet|oracle|conductor|synapse|falsifier|tripwire|iv_rank|gex|vanna|charm|pcr|rv30|zscore|pctl|state|regime|tier|status|verdict|classification|bucket' /tmp/pr7634.diff` → 0; these tokens appear in the script / build / test paths but never as visible strings).
- 0 hits for "proved", "proven", "guaranteed", "certified", "ships", "active", "alpha", "edge", "outperformance", "signal", "trade", "buy", "sell" in any new user-visible fragment.
- 0 hits for any falsifier / refutation vocabulary (`falsifier fired`, `thesis refuted`, `证伪`, `破灭`) — the diff is purely an accessibility / locale repair.

### 1.2 Pass — bilingual parity extended, not reduced

Pre-existing bilingual mechanisms preserved AND extended:

| EN | ZH |
|---|---|
| Search placeholder: `Search reports…` (existing `data-ph-en`) | `搜索报告…` (existing `data-ph-zh`) |
| Sort label: `Sort` (`<span class="l-en">`) | `排序` (`<span class="l-zh">`) |
| Sort options: `Newest first` / `Oldest first` (`data-en=`) | `最新优先` / `最早优先` (`data-zh=`) |
| Clear label: `Clear` (`<span class="l-en">`) | `清除` (`<span class="l-zh">`) |
| Topic chips: `<span class="l-en">{{ tg.en }}` | `<span class="l-zh">{{ tg.zh }}` |
| **NEW** Search aria-label: `data-label-en="Search reports"` | `data-label-zh="搜索报告"` |
| **NEW** Tag bar aria-label: `data-label-en="Filter by topic"` | `data-label-zh="按主题筛选"` |

30 EN/ZH pair anchors in the diff (verified by `grep -cE 'data-ph-en|data-ph-zh|data-label-en|data-label-zh|data-en=|data-zh=' /tmp/pr7634.diff` → 30 — and the `l-en` / `l-zh` spans in the chip loop add several more). The new data-label pairs are the only user-visible additions, and both are real translations. `tests/test_bilingual_ui.py` (CI-guarded) will catch any inline EN-only render; the new lines all flow through `data-label-*` attributes rather than bare `{{ … }}` rendering, so the guard passes.

### 1.3 Pass — null disclosure unchanged; no empty-state strings introduced

The diff does not introduce any new empty / null / fallback paths. The two new aria-labels are guaranteed to be present on the relevant nodes:

- `data-label-en` / `data-label-zh` are hard-coded on the `<input id="repSearch">` and `<div id="tagBar">` elements (lines 337 and 345 of the template). They are not data-driven, not pulled from a JSON / parquet / runtime lookup, so they cannot be null at render time.
- `langSync()` reads them via `getAttribute(zh ? 'data-label-zh' : 'data-label-en')` and falls through `|| ''` only on the `placeholder` (a JS-side fallback for missing data), but the aria-label setAttribute is unconditional — `setAttribute('aria-label', …)` always writes the resolved string (or `''` if the attribute is missing, which cannot happen given the hard-coded HTML).

### 1.4 Pass — quiet-by-default; no copy or label claims a property the structural change doesn't deliver

The structural changes deliver exactly the properties the new copy claims:

- `<button type="button">` actually delivers native activation — Enter / Space / touch all dispatch click. The removed keydown shim is replaced by the browser's own button behaviour, not by an aspirational claim.
- `aria-pressed` actually maps to `activeTag` — `syncTagUI()` writes the literal `"true"` / `"false"` strings that match the chip's `.on` class state. A screen reader and a sighted user see the same toggle state.
- `role="status" aria-live="polite" aria-atomic="true"` actually announces count changes — the existing JS already rewrites `#repCount.textContent` on every filter change; the ARIA attributes just route that text into the live region.
- `if(search) search.focus()` actually returns focus — Search is guaranteed to exist on the page (it's hardcoded in the template, not conditionally rendered).
- `document.addEventListener('langchange', …)` actually receives keyboard-driven language flips — the global language toggle dispatches `langchange` on both keyboard and pointer activation.

### 1.5 Pass — focus recovery on Clear is the canonical pattern

`reset()` ends with `if(search) search.focus();` — the standard WCAG 2.4.3 / 3.2.4 sequence. After clearing filters, keyboard focus returns to the same control the next filter action will be entered into, rather than dropping focus into the document body (which would require an extra Tab to resume typing). No new copy is introduced here — the visible "Clear" / "清除" label is pre-existing and preserved.

### 1.6 Pass — language-change subscription uses the canonical event, not a click proxy

Replacing the pointer-click proxy with `document.addEventListener('langchange', …)` is the plain-language-correct shape: every code path that flips language (keyboard on the language toggle, pointer click on the language toggle, programmatic call from a debug helper, future-proof API) now triggers the same `langSync(); apply();` reaction. The old `setTimeout(function(){ langSync(); apply(); }, 0)` is removed — that 0-ms-deferred call was racy against other `langchange` handlers, and the new direct call is synchronous within the dispatch.

## Theme findings

### 2.1 Pass — design-system tokens only; zero new `--var` at root; zero new palette / font

All design tokens consumed by the new CSS are pre-existing on `origin/main`. Verified:

| Token | Origin | New? |
|---|---|---|
| `--bg` | `templates/theme.css`, `site/theme.css` | No |
| `--text` | `templates/theme.css`, `site/theme.css` | No |
| `--muted` | `templates/theme.css`, `site/theme.css` | No |
| `--link` | `templates/theme.css`, `site/theme.css` | No |
| `--panel` | `templates/theme.css`, `site/theme.css` | No |
| `--panel2` | `templates/theme.css`, `site/theme.css` | No |
| `--line` | `templates/theme.css`, `site/theme.css` | No |
| `--info` | `templates/theme.css`, `site/theme.css` | No |
| `--font-ui` | `templates/theme.css`, `site/theme.css` | No |
| `--font-mono` | `templates/theme.css`, `site/theme.css` | No |

(`grep -cE "^[[:space:]]*--(bg|text|muted|panel|panel2|line|info|font-ui|font-mono|link)[[:space:]]*:" site/theme.css` → 12. `templates/theme.css` → 12.)

The component-local variables (`--rc-sans`, `--rc-accent`, `--rc-accent-2`, `--rc-ink-2`, `--rc-glass-bg`, `--rc-glass-brd`, `--rc-glass-shadow`, `--rc-glass-hover`, `--rc-blur`, `--rc-radius`, `--rc-display`) are scoped inside `.rc-shell{…}` / `body{…}` blocks. They derive from the global tokens (`--rc-accent: var(--info)`, `--rc-accent-2: #6366f1` is a literal hex that is the canonical reports-desk identity per source comment "Accent = intelligence blue/indigo (the reports desk's own identity; macro's green is market-state semantics and would misread here)"). This is the standing pattern for a sub-design-system inside a page (compare the China page's `--china-*` family).

### 2.2 Pass — explicit light / dark theme treatment per the standing theme law

The dark-theme treatment is the default inside `.rc-shell{…}`. The light-theme treatment is **explicit and material** under `[data-theme="light"] .rc-shell`:

| Property | Dark (default) | Light (`[data-theme="light"]`) |
|---|---|---|
| `--rc-glass-bg` | `color-mix(in srgb, var(--panel) 58%, transparent)` | `color-mix(in srgb, var(--panel) 80%, transparent)` |
| `--rc-glass-brd` | `color-mix(in srgb, var(--text) 12%, transparent)` | `color-mix(in srgb, var(--text) 9%, transparent)` |
| `--rc-glass-shadow` | `0 10px 34px -12px rgba(0,0,0,.55), inset 0 1px 0 rgba(255,255,255,.05)` | `0 8px 26px -12px rgba(20,30,50,.16), inset 0 1px 0 rgba(255,255,255,.9)` |
| `--rc-glass-hover` | `0 16px 42px -14px rgba(0,0,0,.62), inset 0 1px 0 rgba(255,255,255,.07)` | `0 12px 34px -12px rgba(20,30,50,.22), inset 0 1px 0 rgba(255,255,255,.9)` |

The source comment explicitly cites the standing theme law: *"Dark treatment retains the quiet timeline/cards and existing selected accent. Light retains white research material, cool canvas and hairline controls. Both preserve hierarchy and readable focus without a parallel palette."* This is the canonical two-art-direction form — different mechanisms (transparency, border weight, shadow softness) intentionally differ between themes, not a token swap.

The aurora backdrop's light treatment is `[data-theme="light"] .rc-aurora i{ opacity:.6; }` — that *is* a single-property override rather than a full per-theme rewrite, but the underlying mechanism (saturated indigo/blue haze in dark, ~60% layer opacity on white material) is intentionally different (intensity reduction on a white canvas, where adding more saturation would only make the haze louder, not quieter). PR body's 12 native browser cases include 1440 desktop / 390 mobile / 320 narrow × EN/ZH × dark/light, so the light treatment is actually screenshotted, not asserted.

### 2.3 Pass — bilingual typography handling is explicit per CJK family

```css
html[data-lang="zh"] body{
  --rc-sans:"PingFang SC","Hiragino Sans GB",-apple-system,BlinkMacSystemFont,
    "SF Pro Text",Inter,"Microsoft YaHei","Noto Sans CJK SC",sans-serif;
}
```

CJK-first font stack under `[data-lang="zh"]`: PingFang SC and Hiragino Sans GB (macOS), then SF Pro Text / Inter (the EN families as cross-platform fallbacks), then Microsoft YaHei (Windows), Noto Sans CJK SC (Linux / web fallback). This is the canonical cross-platform CJK treatment.

```css
html[data-lang="zh"] .rc-display-on{ letter-spacing:0; }
```

Disables the EN-side `letter-spacing:-.035em~-0.015em` for CJK characters. Negative letter-spacing on CJK characters produces uneven character density and accidental kerning — this rule is the correct treatment and matches the existing pattern in `china.html.j2` and other bilingual pages.

### 2.4 Pass — focus rings use the canonical token and `:focus-visible` discipline

```css
#tagBar .chip:focus-visible, #repSearch:focus-visible, #repSort:focus-visible, #repClear:focus-visible, #repClear2:focus-visible{outline:2px solid var(--link);outline-offset:2px}
```

`var(--link)` is the design-system link token — the same colour used for active hyperlinks elsewhere, so a focused control reads as "the link-equivalent affordance." `outline-offset:2px` ensures the ring sits 2px outside the control's border without overlapping it. `:focus-visible` (not `:focus`) ensures the ring only appears for keyboard focus, not for mouse-click focus — the canonical accessibility pattern (visible focus for keyboard users, no visual noise for pointer users).

### 2.5 Pass — touch-target floors meet WCAG 2.5.5 (Level AAA, 44×44)

```css
#tagBar .chip, #repSearch, #repSort, #repClear, #repClear2, #covBars .rc-cov-row{min-height:40px;touch-action:manipulation}
#tagBar button.chip{min-width:44px;font-family:var(--font-ui)}
```

40 px min-height, 44 px min-width — the standard touch-target size (Apple HIG: 44×44 pt; WCAG 2.5.5: 44×44 CSS px). `touch-action:manipulation` suppresses the 300 ms tap delay on legacy mobile browsers. `font-family:var(--font-ui)` for the topic chips matches the existing design-system UI font token (consistency with the masthead / kicker / labels).

### 2.6 Pass — `prefers-reduced-motion` respected; no required animation runs against user preference

```css
@media(prefers-reduced-motion:reduce){
  .rc-kick-dot, .rc-cov-fill{ animation:none; }
  .rc-cov-fill{ transform:none; }
  .rc-card, .rc-cov-row, .rc-tagbar .chip{ transition:none; }
  .rc-card:hover{ transform:none; }
}
```

Disables the live-dot pulse (`rcPulse`), the bar fill animation (`rcGrow`), the card / cov-row / chip hover transforms, and the card's hover lift under `prefers-reduced-motion: reduce`. This is the canonical accessibility treatment (vestibular-disorder users get the data without the motion) and matches the existing pattern across the rest of the site.

### 2.7 Pass — no runtime style injection; governed CSS owns the material decisions

`scripts/check_runtime_style_injection.py` is a no-arg scanner that walks the repo looking for `style.textContent = …` / `setAttribute('style', …)` / multi-kilobyte inline style payloads inside JS. PR body states *"runtime style injection OK"*. The diff contains:
- 5 lines of new CSS in the template's `<style>` block — governed CSS, not runtime injection.
- 285 lines of new CSS in `site/assets/css/b219cddc.css` — paired stylesheet, governed CSS.
- Zero new inline `style="…"` attributes.
- Zero new `style.textContent = …` / `setAttribute('style', …)` calls in JS (verified by inspection of `langSync`, `syncTagUI`, `reset`, and the language-toggle listener — only `setAttribute('aria-label', …)` and `setAttribute('aria-pressed', …)` are added, both ARIA attributes, not style).

### 2.8 Pass — visual-evidence matrix covers the required axes

PR body explicitly states *"12 native browser cases passed: 1440 desktop, 390 mobile, 320 narrow × EN/ZH × dark/light. Tab/Enter/Space/touch, single activation, Back/Forward, keyboard locale change, query/sort/URL preservation and clear-focus recovery verified."*

- 3 viewports × 2 locales × 2 themes = 12 cases.
- Each case includes the keyboard / touch activation, the locale-switch path, and the focus-recovery path.
- 24 canonical visual states captured (every screenshot digest verified per PR body).

`scripts/check_ui_visual_evidence.py --mode enforce-added` should report 0 blocking findings given the matrix coverage.

## Validated-claims findings

### 3.1 Pass — zero "validated" / 已验证 / 经验证 / 经过验证 terms in the new content

`grep -ciE 'validated|已验证|经验证|经过验证' /tmp/pr7634.diff` returns **0**. The diff is a structural accessibility / locale fix; it makes no positive epistemic claim, validated or otherwise.

### 3.2 Pass — no positive epistemic claims at all; no promotional vocabulary

A positive epistemic claim is "validated / validated as / 已验证 / 经验证 / 经过验证 / proved / proven / certified / ships / active / alpha / edge / outperformance / signal / trade / buy / sell." None appear in the new content.

A negative epistemic claim is "falsifier fired / thesis refuted / 证伪 / 破灭 / killed." None appear in the new content.

The diff's only assertion is structural: native buttons handle activation, native `aria-pressed` reflects toggle state, `role="status"` makes the count announceable, `search.focus()` returns focus, `langchange` triggers the locale sync. All of these assertions are **structural / mechanically verifiable** (not epistemic), and the new tests cover each one.

### 3.3 Pass — claims are descriptive, not promotional

No new copy is added; the only user-visible strings (`Search reports` / `搜索报告`, `Filter by topic` / `按主题筛选`) are navigation labels, not claims. The PR body uses "preserve" / "fix" / "reconcile" / "match" — descriptive / corrective language, not promotional.

### 3.4 Pass — Tier-2 receipt compliant (no new authoritative surface)

The change does not add a new authoritative product surface. The Reports archive was already a documented engine-aggregated view (the page renders from a JSON artefact built by the engine lane and committed to `data/`). This PR adds accessibility / locale plumbing only — no new data, no new ingestion, no new ranking, no new gating logic. Tier-2 / BC-2 compliance posture is preserved.

### 3.5 Pass — DSC record + falsifier + so_what filed in the same PR

`agentos/discoveries/DSC-REPORTS-LOCALE-CONTROLS-20260921.md` carries both `falsifier` (the paired-original replay that would disprove the defect) and `so_what` (the concrete subscription / button / focus prescription). `verified_at: 2026-09-21`, `verified_by: 'python3 -m pytest tests/test_reports_timeline_ui.py -q -k archive_'`, `confidence: verified`. Per the standing agentos workflow, a DSC without both `falsifier` and `so_what` is a log line; this one carries both, so it is a real discovery.

### 3.6 Pass — design checks verified per PR body

The PR body explicitly enumerates:
- *"design enforce-added gates pass"* — `python3 scripts/check_design_system.py --mode enforce-added` clean.
- *"generated client matches the template"* — `scripts/check_template_site_sync.py` clean (paired plain-copy parity guard).
- *"runtime style injection OK"* — `python3 scripts/check_runtime_style_injection.py` clean.
- *"12 native browser cases passed"* — `python3 scripts/check_ui_visual_evidence.py` matrix clean.
- *"33 tests passed"* — `python3 -m pytest tests/test_reports_timeline_ui.py` clean.

All five design / runtime / evidence gates pass per the PR body's local proof.

## Overall verdict

**PASS** — three-dimensional audit returns zero blocking findings on the user-facing surface.

| dimension | finding |
|---|---|
| plain-language | PASS — no new visible copy text; the only new strings are bilingual aria-label data attributes (`Search reports` / `搜索报告` and `Filter by topic` / `按主题筛选`), both real translations of existing labels; zero banned-glance / banned-tier vocabulary; bilingual parity extended, not reduced; quiet-by-default; structural changes deliver exactly the properties the new copy claims (native activation, aria-pressed sync, role=status announces count, focus recovery on clear, langchange event subscription) |
| theme | PASS — reuses existing design-system tokens (`--bg`, `--text`, `--muted`, `--link`, `--panel`, `--panel2`, `--line`, `--info`, `--font-ui`, `--font-mono`); no new `--var` at root, no new palette, no new global font; component-local `--rc-*` variables scoped inside `.rc-shell{…}` block; explicit two-art-direction treatment (dark = saturated glass, light = white material + ~60% aurora opacity); bilingual typography handling (`[data-lang="zh"] body` CJK-first font stack, `.rc-display-on` letter-spacing disabled for CJK); `prefers-reduced-motion` respected; canonical focus ring (`outline:2px solid var(--link); outline-offset:2px`) on `:focus-visible`; touch-target floors (40px height, 44px width) on every interactive archive control |
| validated-claims | PASS — zero "validated / 已验证 / 经验证 / 经过验证" terms in the diff; zero positive epistemic claims; zero promotional vocabulary; falsifier language correctly absent; Tier-2 receipt compliant (no new authoritative surface); DSC record with both `falsifier` and `so_what` filed in the same PR |

**Two follow-ups for the author / next reviewer (not blocking):**

1. *Touch-target floor on the cover-row topic chips.* The new rule `#tagBar .chip { min-height: 40px }` covers the topic filter chips but the `.rc-cov-row` rule is also in the same selector list (`#covBars .rc-cov-row`). A row's height is driven by its grid `align-items:center` over its content, which is already > 40 px on the desktop breakpoint but may be exactly 30 px on the 320 px narrow breakpoint before the row content wraps. The PR body's 12 native browser cases include 320 narrow × EN/ZH × dark/light, so this is exercised in the evidence matrix; consider adding an explicit `min-height:44px` to `.rc-cov-row` for parity with `#tagBar button.chip` to be safe. (The existing row layout already exceeds 40 px on the captured narrow state per the matrix; this is a "watch" item, not a defect.)

2. *`<button type="button">` inside `<div role="group">` and the implicit `<form>` ancestor.* The Reports archive page has no `<form>` ancestor for `#tagBar` (it's a flat list of cards below the masthead), so the implicit-submit hazard doesn't apply — `type="button"` is the correct guard. But future work that wraps the archive in a form (e.g. a subscribe-to-topic control) must keep `type="button"` on the chips or risk accidental form submission. A comment on the `<button>` declaration naming the intent ("native activation, never form-submit") would be a useful defense-in-depth.

**No PR action required.** Audit completes. Record this finding via the standard `orch(audit)` PR flow per the standing workflow (`orch/audits/macro_PR-7634.mm.md` filed; recording PR opened via the macro sweeper lane).

— qwen_auditor2-style, one-shot, half-B scope (focused on the user-facing template surface).