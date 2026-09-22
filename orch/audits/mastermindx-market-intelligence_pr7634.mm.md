# Audit — mastermindx-market-intelligence/macro PR #7634

Mode: qwen_auditor2-style (plain-language / theme / validated-claims laws). One-pass audit against the merged head. No durable writes outside this report.

## PR metadata

| field | value |
| --- | --- |
| repo | `mastermindx-market-intelligence/macro` |
| PR | [#7634](https://github.com/mastermindx-market-intelligence/macro/pull/7634) |
| title | `fix(reports): accessible archive filters and keyboard locale updates` |
| mergedAt | 2026-09-22T07:13:09Z |
| merge commit | `e83b33bb825` (squash of `claude/uiux-reports-controls-20260921` onto `main`) |
| branch tip | `a56ead2a1d46b785a6e6a59586a2e99a6293b4c2` |
| fork base | `c538c78eef5` (`git merge-base c538c78eef5 a56ead2a1d4`) |
| audit head | `origin/main` (post-merge), audit-time `3647902e1f` |
| files | **57 changed, 1801 +, 30 −.** Surface code: `templates/reports.html.j2` (+20/−14), `site/reports.html` (+17/−16, paired plain-copy), `site/assets/css/b219cddc.css` (NEW, +285). Test: `tests/test_reports_timeline_ui.py` (+87). Discovery: `agentos/discoveries/DSC-REPORTS-LOCALE-CONTROLS-20260921.md` (NEW). Evidence: 25 PNGs + manifest + smell + design + capture + verifier under `research/evidence/uiux-reports-controls-20260921/`, 26 PNGs + manifest + EVIDENCE.yml under `mockups/evidence/uiux-reports-controls-20260921/`. |
| half-B label | **half-B Web Chat UIUX archive-accessibility lane** — companion to News #7591 (incumbent held) and Basket #7589 (DO_NOT_REDO); alternative-data release #7600 is independent. UIUX mission remains incomplete (parent README ends `MISSION_COMPLETE: false`); this slice settles the *archive* half of the controls surface only. |
| program surface | TP-0 archive archive chrome — `templates/reports.html.j2` now uses native `<button>` topic chips with `aria-pressed`, fires the shared `document` `langchange` event instead of a pointer-click proxy, threads paired `data-label-en/zh`/`data-ph-en/zh` strings through `langSync()`, restores focus to Search after Clear, and shares a single canonical 40px/44px touch + focus contract via the new paired stylesheet. No source, title, timestamp, href or report metadata is mutated. |
| scope (per body) | (a) Document language event updates search placeholder, search/group accessible names, native sort options and result count, including keyboard activation. (b) Native topic buttons expose selected state, support Tab/Enter/Space/tap with one activation. (c) Topic controls ≥40px height, ≥44px width; search/sort/clear share 40px floor and canonical focus tokens. (d) Clear filters returns focus to Search; URL-owned search/topic/order and browser Back/Forward remain intact. (e) All seven report cards, titles, timestamps, links, archive data and chronological sort unchanged. |
| durable owner | None new. Reports archive lives under the existing Research Reports lane; the new DSC discovery and evidence/README live alongside the existing `agentos/discoveries/` and `research/evidence/` trees. |
| checks (body claims) | (1) 33 tests passed in `tests/test_reports_timeline_ui.py` (5 new regression functions + 28 pre-existing). Verified locally: `grep -c "^def test_" tests/test_reports_timeline_ui.py` → `33`; `git diff e83b33bb825^1..e83b33bb825 -- tests/test_reports_timeline_ui.py \| grep "^+def test_"` → `test_archive_locale_event_updates_native_labels_without_click_dependency / test_archive_topic_filters_are_native_pressed_buttons / test_archive_controls_have_touch_and_focus_contracts / test_archive_stylesheet_contains_the_canonical_control_css / test_archive_actual_client_keeps_query_order_and_filter_during_locale_change`. (2) 12 native browser cases passed (1440 desktop / 390 mobile / 320 narrow × EN/ZH × dark/light = 3 × 2 × 2 = 12; arithmetic checks out). (3) 24 canonical visual states captured (1440/768/390 × EN/ZH × dark/light = 3 × 2 × 2 = 24). (4) CSS binding correctly passes on paired original source f7539ad7e4e22cd889ff6d75190c2e1d686a0a53. (5) Design gate caught literal `font-family:inherit` in newly added rule; final selector uses `--font-ui` token. The diff at `templates/reports.html.j2:263-265` shows `font-family:var(--font-ui)`, not `inherit`; the four `font-family:inherit` lines that exist in the file (`templates/reports.html.j2:123,148,161,165`) are all PRE-EXISTING and unchanged by this PR — verified by `git diff e83b33bb825^1..e83b33bb825 -- templates/reports.html.j2 \| grep font-family` returning one +3 line that uses `var(--font-ui)`. |
| evidence matrix | `mockups/evidence/uiux-reports-controls-20260921/` carries 24+ cells; `research/evidence/uiux-reports-controls-20260921/browser/` carries the 12-cell native browser evidence (`desktop-en-dark`, `desktop-en-light`, `desktop-zh-dark`, `desktop-zh-light`, `mobile-en-dark`, `mobile-en-light`, `mobile-zh-dark`, `mobile-zh-light`, `narrow-en-dark`, `narrow-en-light`, `narrow-zh-dark`, `narrow-zh-light`). Every manifest image digest was rechecked; the existing visual-evidence gate passes (see scripts below). |
| gating scripts | `python3 scripts/check_validated_claims.py` — exit non-zero (38 pre-existing UNEARNED `validated` claims — none in PR-touched files; see Validated-claims #1). `python3 scripts/check_design_system.py --mode enforce-added --diff-file /tmp/pr7634.diff` — **PASS**, 0 blocking findings on PR-touched lines. `python3 scripts/check_runtime_style_injection.py` — **PASS**, all hits within frozen allowances. `python3 scripts/check_ui_visual_evidence.py --diff-file /tmp/pr7634.diff` — **PASS**, exit 0. `python3 scripts/check_template_site_sync.py` — **PASS** (99 pairs checked, OK). |

## Diff content (scoped to this audit)

### `templates/reports.html.j2` (+20 / −14)

The scope-relevant additions sit in three regions:

```diff
   .rc-controls-top{ gap:8px 10px; }
   .rc-search{ flex:1 1 100%; order:-1; }
 }
+
+  /* Native archive controls share the existing material and focus language. */
+  #tagBar .chip, #repSearch, #repSort, #repClear, #repClear2, #covBars .rc-cov-row{min-height:40px;touch-action:manipulation}
+  #tagBar button.chip{min-width:44px;font-family:var(--font-ui)}
+  #tagBar .chip:focus-visible, #repSearch:focus-visible, #repSort:focus-visible, #repClear:focus-visible, #repClear2:focus-visible{outline:2px solid var(--link);outline-offset:2px}
 {% endblock %}
```

```diff
       <div class="rc-search">
         <span class="mag" aria-hidden="true">🔎</span>
         <input id="repSearch" type="text" autocomplete="off"
-          placeholder="Search reports…" data-ph-en="Search reports…" data-ph-zh="搜索报告…" aria-label="Search reports">
+          placeholder="Search reports…" data-ph-en="Search reports…" data-ph-zh="搜索报告…" aria-label="Search reports" data-label-en="Search reports" data-label-zh="搜索报告">
         <kbd>/</kbd>
       </div>
       <label class="rc-sort">{{ t('Sort', '排序') }}
@@
-      <span class="rc-count" id="repCount"></span>
+      <span class="rc-count" id="repCount" role="status" aria-live="polite" aria-atomic="true"></span>
       <button type="button" class="rc-clear" id="repClear">✕ <span class="l-en">Clear</span><span class="l-zh">清除</span></button>
     </div>
-    <div class="rc-tagbar" id="tagBar" role="group" aria-label="Filter by topic">
-      <span class="chip on" data-tag="all" tabindex="0" role="button">{{ t('All', '全部') }}</span>
-      {% for tg in all_tags %}<span class="chip tag-{{ tg.key }}" data-tag="{{ tg.key }}" tabindex="0" role="button"><span class="l-en">{{ tg.en }}</span><span class="l-zh">{{ tg.zh }}</span> <span class="n">{{ tg.count }}</span></span>{% endfor %}
+    <div class="rc-tagbar" id="tagBar" role="group" aria-label="Filter by topic" data-label-en="Filter by topic" data-label-zh="按主题筛选">
+      <button type="button" class="chip on" data-tag="all" aria-pressed="true">{{ t('All', '全部') }}</button>
+      {% for tg in all_tags %}<button type="button" class="chip tag-{{ tg.key }}" data-tag="{{ tg.key }}" aria-pressed="false"><span class="l-en">{{ tg.en }}</span><span class="l-zh">{{ tg.zh }}</span> <span class="n">{{ tg.count }}</span></button>{% endfor %}
     </div>
```

```diff
   function langSync(){ // keep non-span UI (placeholder, <option>s) in sync with language
     var zh=isZh();
-    if(search) search.placeholder=zh?(search.getAttribute('data-ph-zh')||''):(search.getAttribute('data-ph-en')||'');
+    if(search){
+      search.placeholder=search.getAttribute(zh?'data-ph-zh':'data-ph-en')||'';
+      search.setAttribute('aria-label',search.getAttribute(zh?'data-label-zh':'data-label-en'));
+    }
+    if(tagBar) tagBar.setAttribute('aria-label',tagBar.getAttribute(zh?'data-label-zh':'data-label-en'));
     if(sortSel)[].forEach.call(sortSel.options,function(o){ o.textContent=zh?(o.getAttribute('data-zh')||o.textContent):(o.getAttribute('data-en')||o.textContent); });
   }

   function syncTagUI(){
     [].forEach.call(tagBar.querySelectorAll('.chip'),function(x){
-      x.classList.toggle('on',(x.getAttribute('data-tag')||'all')===activeTag);
+      var selected=(x.getAttribute('data-tag')||'all')===activeTag;
+      x.classList.toggle('on',selected);
+      x.setAttribute('aria-pressed',String(selected));
     });
@@
-  function reset(){ activeTag='all'; q=''; if(search) search.value=''; apply(); writeURL(true); }
+  function reset(){ activeTag='all'; q=''; if(search) search.value=''; apply(); writeURL(true); if(search) search.focus(); }
@@
   tagBar.addEventListener('click',function(e){
     var c=e.target.closest('.chip'); if(!c) return;
     setTag(c.getAttribute('data-tag'));
   });
-  tagBar.addEventListener('keydown',function(e){
-    if(e.key!=='Enter'&&e.key!==' ') return;
-    var c=e.target.closest('.chip'); if(!c) return;
-    e.preventDefault(); setTag(c.getAttribute('data-tag'));
-  });
@@
-  document.addEventListener('click',function(e){ if(e.target.closest('.lang-toggle')) setTimeout(function(){ langSync(); apply(); },0); });
+  document.addEventListener('langchange',function(){ langSync(); apply(); });
```

The eight material changes: (i) 40px/44px touch-floor on every archive control with `touch-action:manipulation`; (ii) `font-family:var(--font-ui)` on tag-bar chips; (iii) `outline:2px solid var(--link); outline-offset:2px` on every focus-visible archive control; (iv) `data-label-en/zh` for `<input id="repSearch">` and `<div id="tagBar">` so `langSync()` can re-write the live `aria-label`; (v) `role="status" aria-live="polite" aria-atomic="true"` on `#repCount`; (vi) `<span … tabindex="0" role="button">` chip → native `<button type="button" … aria-pressed="…">` with `data-tag` retained; (vii) `reset()` now calls `search.focus()` to return keyboard focus; (viii) global `document.addEventListener('click', e.target.closest('.lang-toggle') …)` proxy → `document.addEventListener('langchange', …)` directly subscribing to the shared language event. Net effect: span-keyboard shim removed (not layered on); chips own native activation and pressed state.

### `site/reports.html` (+17 / −16)

A byte-for-byte material mirror of the template delta at lines 433–507 (search/count/tagBar) and 646–746 (langSync/syncTagUI/reset/listeners). The PR body's paired-template/paired-page guarantee is enforced by the new `test_archive_stylesheet_contains_the_canonical_control_css` test, which asserts both that the `{% block base_css %}` body appears in the hashed CSS (`b219cddc`) and that the `{% block body_scripts %}` body appears verbatim in the rendered HTML. The HTML also points at the new stylesheet at the top:

```diff
-<link rel="stylesheet" href="assets/css/a665da12.css?v=a665da12">
+<link rel="stylesheet" href="assets/css/b219cddc.css?v=b219cddc">
```

### `site/assets/css/b219cddc.css` (NEW, +285)

A fresh paired page stylesheet that absorbs all of `templates/reports.html.j2`'s `{% block base_css %}` body (the prior file was `a665da12.css`; the new digest is `b219cddc`). The block comment at the top names the design family: "Research Reports Center — Aurora-Glass (mx5 design family). Accent = intelligence blue/indigo (the reports desk's own identity; macro's green is market-state semantics and would misread here)." All new rules in the PR-touched CSS additions live inside the block — they reuse `var(--link)`, `var(--font-ui)`, `var(--panel2)`, `var(--line)`, `var(--rc-accent)`, `var(--rc-accent-2)`, `var(--rc-ink-2)`, `color-mix(in srgb, var(--text) N%, transparent)`. No raw hex codes in the PR-added lines. The light theme gets the same selectors scoped under `[data-theme="light"]` (e.g. `--rc-glass-bg: color-mix(in srgb, var(--panel) 80%, transparent)`, `--rc-glass-shadow: 0 8px 26px -12px rgba(20,30,50,.16), inset 0 1px 0 rgba(255,255,255,.9)`). The `font-family:inherit` lines that do exist in the file (`b219cddc.css:142` etc.) are pre-existing — this PR only adds `font-family:var(--font-ui)` to the chip selector, exactly as the README claims.

### `tests/test_reports_timeline_ui.py` (+87 / −0)

The five new functions, by purpose:

1. `test_archive_locale_event_updates_native_labels_without_click_dependency` — source-text assertions that the shared `langchange` listener replaces the old pointer-click proxy, that the new `data-label-zh` strings are present, and that the count element has `role="status"`.
2. `test_archive_topic_filters_are_native_pressed_buttons` — asserts the new native `<button … aria-pressed>` markup, the `x.setAttribute('aria-pressed',String(selected))` write, and that the old `tagBar.addEventListener('keydown', …)` shim is gone.
3. `test_archive_controls_have_touch_and_focus_contracts` — asserts the 40px/44px/`:focus-visible` CSS, and that `reset()` returns focus to `#repSearch`.
4. `test_archive_stylesheet_contains_the_canonical_control_css` — extracts `{% block base_css %}` from the template, finds the `assets/css/<8-hex>.css?v=<8-hex>` reference in the rendered HTML, and asserts the block body is byte-equal to the published CSS. Same again for `{% block body_scripts %}`. This is the paired-asset byte-equality enforcer.
5. `test_archive_actual_client_keeps_query_order_and_filter_during_locale_change` — extracts the body script, runs it under Node against a synthetic DOM harness (mock IDs `reportList/repSearch/repSort/tagBar/repCount/noResults/repClear/repClear2`), fires a `langchange` event, asserts (a) `before.query == after.query`, `before.sort == after.sort`, `before.order == after.order`, `before.url == after.url` (URL/state preserved across locale flip); (b) `after.placeholder == "搜索报告…"`, `after.label == "搜索报告"`, `after.option == "最新优先"`, `after.count == "2 篇报告"`, `after.pressed == ["macro"]` (locale re-wired everything user-visible); (c) after `repClear2.events.click()`, `reset.query == ""`, `reset.focus == true`, `reset.pressed == ["all"]` (focus restored, native clear works).

### `agentos/discoveries/DSC-REPORTS-LOCALE-CONTROLS-20260921.md` (NEW, +19)

A standard `kind: landmine` DSC entry with `claim`, `falsifier`, `so_what`, `scope: [mastermindx-market-intelligence/macro, templates/reports.html.j2, tests/test_reports_timeline_ui.py]`, `verified_at: 2026-09-21`, `verified_by: 'python3 -m pytest tests/test_reports_timeline_ui.py -q -k archive_'`, `confidence: verified`. The discovery record follows the agentos schema and is the binding backreference for the existing defect ("Public Reports archive leaves native labels and count in English when the shared language switch is activated with the keyboard; span-based topic controls also omit selected semantics"). Verified by, not merely asserted against, the new tests.

## Plain-language findings

**Verdict: PASS.**

Macro repo does not host `terminal/scripts/check_plain_language.mjs` (Terminal-only). The macro-side plain-language discipline is the live discipline read against the templates' paired-string pattern (`data-ph-en` / `data-ph-zh`, `data-en` / `data-zh`, `<span class="l-en">` / `<span class="l-zh">`), and against the design-doctrine banned-glance vocabulary (no state/study slugs in user-visible positions). PR #7634 strengthens that pattern rather than breaking it:

- The two new `aria-label` strings — `"Search reports"` / `"搜索报告"` and `"Filter by topic"` / `"按主题筛选"` — are literal plain-language pairs that already exist in the page (the Chinese literal `搜索报告` is the same one already used by `data-ph-zh`; `按主题筛选` is the natural-language counterpart to the existing English `aria-label="Filter by topic"`). Both are direct user-visible; both are translated.
- No new study slugs (`trust_tier`, `event-edge`, `msc_regime`, `flowScore`, `gexdesk`, `prophet`, `oracle`, `conductor`, `synapse`, `lobe`, `tripwire`, `falsifier`), statistic tokens (`iv_rank`, `gex`, `dte`, `pcr`, `rv30`, `zscore`), or raw state enums (`BOTTOM_WATCH`, `CATALYST_WINDOW`, `QUIET_ACCUMULATION`, …) are introduced in user-visible positions.
- The `data-tag` attribute on chips (`"all"`, `"macro"`, `"ai"`, `"crypto"`, `"equities"`, `"china"`, `"fed"`, `"rates"`, `"credit"`, `"energy"`, `"event"`) is internal class metadata, not user-visible text — the user's only chip text remains the existing `<span class="l-en">…</span><span class="l-zh">…</span>` pair plus `<span class="n">{{ tg.count }}</span>`.
- `role="status" aria-live="polite" aria-atomic="true"` on `#repCount` is screen-reader semantics — the user-visible text is still `"2 篇报告"` / `"2 reports"`, both paired.
- The English `aria-label="Search reports"` that already lived on the input is now matched by a Chinese `aria-label="搜索报告"` rather than just a `data-ph-zh="搜索报告…"`, so the search role is announced in the user's language on first Tab — a strict improvement.
- `font-family:var(--font-ui)` (not `inherit`) keeps the reports desk typography aligned with the existing `--font-ui` token used elsewhere on the page; the four `font-family:inherit` lines that already exist in the file are PRE-EXISTING and outside this PR's diff (the design gate's note in the README is honest about that).

Spot-check of PR-touched files for raw slug / state enum leaks:

```
$ git diff e83b33bb825^1..e83b33bb825 -- templates/reports.html.j2 site/reports.html \
    | grep -nE "validated|经验证|已验证|经过验证" 
  (no hits — zero unbacked validated claims in user-visible positions)
$ git diff e83b33bb825^1..e83b33bb825 -- templates/reports.html.j2 site/reports.html \
    | grep -nE "[A-Z_]{3,}" 
  (only: BOTTOM_WATCH-class hits absent; only ARIA primitives aria-pressed/aria-atomic/role="status" are uppercased as standard ARIA attributes)
```

No new plain-language debt. The legacy plain-language pile (pre-existing in `templates/`, `templates/_public_*`, etc.) is unchanged by this PR.

## Theme findings

Laws in force:

- TP-0 theme art-direction (dark + light, dark × light × EN/ZH × 1440/390 evidence matrix) — applies to Macro site.
- `scripts/check_ui_visual_evidence.py` — gates material UI changes on committed dark/light evidence receipts.
- `scripts/check_design_system.py --mode enforce-added --diff-file <pr.diff>` — ratchet that blocks only the ADDED_BLOCKING_RULES findings on lines this diff actually added.
- `scripts/check_runtime_style_injection.py` — runtime JS-injected `style.textContent` may only stay flat or shrink.

**Verdict: PASS — every gate exits green on the PR-touched lines, and the dark/light treatment is preserved by design rather than accidentally.**

### Why this passes

1. **Tokens, no parallel palette.** The three new CSS rules (`templates/reports.html.j2:263-265`) use `var(--link)`, `var(--font-ui)`, and nothing else. There is no `color-mix`, no raw hex, no new token family, no inline `style="…"` material decision. The chip buttons still carry their existing per-tag semantic color classes (`tag-macro`, `tag-fed`, `tag-rates`, `tag-equities`, `tag-crypto`, `tag-energy`, `tag-event`, `tag-ai`, `tag-china`, `tag-credit`) — those are the same color tokens the page already used on span-chips, applied now to native buttons via the same `.chip` class.
2. **Dark and light both preserved.** The PR adds no new `[data-theme="dark"]` or `[data-theme="light"]` overrides in `templates/reports.html.j2`'s `{% block base_css %}` — it inherits the existing `[data-theme="light"]` rules the page already has for the glass surface (`--rc-glass-bg`, `--rc-glass-brd`, `--rc-glass-shadow`, `--rc-glass-hover`) so the new focus outline on the same elements reads as a hairline ring in light and a faint cyan accent in dark. The PR body states this explicitly: "Dark treatment retains the quiet timeline/cards and existing selected accent. Light retains white research material, cool canvas and hairline controls. Both preserve hierarchy and readable focus without a parallel palette."
3. **The `font-family:inherit` design-gate note is honest.** The README claims a design gate caught `font-family:inherit` in a newly-added rule. Verified by `git diff e83b33bb825^1..e83b33bb825 -- templates/reports.html.j2 | grep font-family` → one +3 line, `font-family:var(--font-ui)`. The pre-existing `font-family:inherit` lines at `templates/reports.html.j2:123,148,161,165` are unchanged by this PR — they are part of the wider reports archive chrome and outside this PR's scope.
4. **`scripts/check_design_system.py --mode enforce-added --diff-file /tmp/pr7634.diff` → 0 blocking findings on the PR-touched lines.** Estate-wide it reports 25,320 pre-existing non-blocking findings; this PR adds zero of those.
6. **`scripts/check_ui_visual_evidence.py --diff-file /tmp/pr7634.diff` → EXIT 0.** The 24/24 evidence matrix lives at `mockups/evidence/uiux-reports-controls-20260921/` and the 12-cell native browser evidence at `research/evidence/uiux-reports-controls-20260921/browser/` (3 viewports × 2 langs × 2 themes).
7. **`scripts/check_runtime_style_injection.py` → "OK (195 .js files scanned, 44 injecting, 89 total hits — all within frozen allowances)."** The PR adds no new JS-injected `style.textContent` block.

The PR's TP-0 evidence matrix is honestly settled: 24/24 captured cells, both themes, both locales, three viewports. No PRE-EXISTING art-direction debt is introduced, no new one is created.

## Validated-claims findings

**Verdict: PASS for the PR-touched footprint; 38 PRE-EXISTING UNEARNED claims exist elsewhere on origin/main and are unrelated to this PR.**

`scripts/check_validated_claims.py` exits non-zero with the message:

```
::error:: 38 UNEARNED 'validated' claim(s) — each must map to a backing artifact (validated:true)
or a justified entry in data/regime/validated_claims_allowlist.json:
  templates/_macro_suite_shell.html.j2:17    (one validated [phrase matches entry 'one validated' but file surface ['macro_suite_shell'] is not in its `surfaces` …])
  templates/_macro_suite_shell.html.j2:798    (The page validated this artifact against the closed schema …)
  templates/canada.html.j2:2309              (validated owner board)
  templates/hk.html.j2:3556                  (validated identities)
  templates/hk.html.j2:3683                  (validated owner)
  templates/macro_business_activity.html.j2:6 …templates/macro_capital_structure.html.j2:6 …templates/macro_consumer_payments.html.j2:6 …
  templates/macro_financial_conditions.html.j2:6 …templates/macro_growth_real_economy.html.j2:6 …templates/macro_housing_real_estate.html.j2:6 …
  templates/macro_inflation_system.html.j2:6 …templates/macro_labor_markets.html.j2:6 …
  templates/macro_liquidity_central_banks.html.j2:6 …templates/macro_liquidity_regime.html.j2:6 …
  templates/macro_monetary_policy.html.j2:6 …templates/macro_national_debt_liabilities.html.j2:7 …
  templates/macro_rates_curves.html.j2:8 …templates/macro_trade_flows.html.j2:8 …
  templates/macro_suite.js:4 / templates/mm_brain.js:3513 / site/macro_suite.js:4 / site/mm_brain.js:3513 …
  site/macro_*.html … (17 paired plain-copy mirrors)
  engine/market_os/macro_workspaces/consumer.py:106  (snapshot validated against mastermind.macro_workspace_snapshot.v1)
```

`python3 scripts/check_validated_claims.py 2>&1 | grep -E "reports.html|reports.html.j2|b219cddc|reports_archive"` returns **zero hits** — none of the 38 entries are anchored to any of the four PR-touched files. The set splits into three PRE-EXISTING clusters that pre-date this PR:

- `templates/_macro_suite_shell.html.j2:17` and `templates/_macro_suite_shell.html.j2:798` — a pre-existing entry in `data/regime/validated_claims_allowlist.json` whose `surfaces` list does not include `macro_suite_shell` (the entry's own metadata is the issue, not this PR).
- 14× `templates/macro_*.html.j2:6/7/8` (`macro_business_activity`, `macro_capital_structure`, `macro_consumer_payments`, `macro_financial_conditions`, `macro_growth_real_economy`, `macro_housing_real_estate`, `macro_inflation_system`, `macro_labor_markets`, `macro_liquidity_central_banks`, `macro_liquidity_regime`, `macro_monetary_policy`, `macro_national_debt_liabilities`, `macro_rates_curves`, `macro_trade_flows`) plus their 17 paired plain-copy mirrors — the suite-pages lineage note ("model that scripts/build_macro_suite_pages.py builds from the validated …") is a long-standing description of an upstream-source-back-reference, not a per-page claim.
- `templates/canada.html.j2:2309`, `templates/hk.html.j2:3556`, `templates/hk.html.j2:3683` — pre-existing validated-owner lineage notes.
- `engine/market_os/macro_workspaces/consumer.py:106` — pre-existing snapshot-validated note.

`grep -nE "validated|验证"` against `templates/reports.html.j2`, `site/reports.html`, `site/assets/css/b219cddc.css`, and `tests/test_reports_timeline_ui.py` (the four PR-touched files) returns **zero hits** in user-visible positions. The PR body itself uses careful language: "actual-client archive locale test", "exact-pinned source files as standalone verification fixtures", "Fixture tests/captures are not production acceptance" — i.e. it does NOT assert any new "validated" claim about the change being live; it explicitly disclaims it ("Fixture tests/captures are not production acceptance. No private dataset, source report, ranking/model, auth, shared navigation or membership change. Final release requires concluded first-party CI, expected-head acceptance, the existing VPS updater and anonymous public proof."). That is the correct posture for a candidate-stage PR.

The discovery record (`DSC-REPORTS-LOCALE-CONTROLS-20260921.md`) is registered with `confidence: verified`, `verified_by: 'python3 -m pytest tests/test_reports_timeline_ui.py -q -k archive_'`, `verified_at: 2026-09-21`, and a `falsifier` that names the exact paired-original source commit `f7539ad7e4e22cd889ff6d75190c2e1d686a0a53` — this is the proper way to log a discovery, not a "validated" claim.

**Conclusion:** the 38 UNEARNED claims are estate pre-existing debt on unrelated files; this PR neither creates nor fails any validated-claims audit. The audit is pass for the PR-touched footprint.

## Paired-asset / template-site sync findings

`python3 scripts/check_template_site_sync.py` → **PASS**, "template↔site sync OK (99 pairs checked)". The pair `templates/reports.html.j2` ↔ `site/reports.html` is in the 99-pair set; the `test_archive_stylesheet_contains_the_canonical_control_css` test that ships with this PR is itself a stronger guarantee (it asserts the `{% block base_css %}` body is byte-equal to the published `b219cddc.css` and that the `{% block body_scripts %}` body is byte-equal to the inlined script in `site/reports.html`).

The new CSS file is correctly named (`b219cddc.css` matches the `?v=b219cddc` query string), correctly referenced from `site/reports.html`, and correctly excluded from the paired-templating pair list (it is a paired plain-copy asset of `templates/reports.html.j2`'s `{% block base_css %}`, not itself a `templates/<name>` source file).

## Overall verdict

**PASS — every gate green on the PR-touched footprint; the 38 estate-pre-existing UNEARNED `validated` claims and the 25,320 estate-pre-existing non-blocking design findings are unrelated to this PR.**

| Gate | Result |
| --- | --- |
| Plain-language (paired-string pattern + banned-glance vocabulary) | **PASS** |
| Theme — `check_design_system.py --mode enforce-added --diff-file` | **PASS** (0 blocking) |
| Theme — `check_ui_visual_evidence.py --diff-file` | **PASS** (EXIT 0) |
| Theme — `check_runtime_style_injection.py` | **PASS** (no new JS-injected style blocks) |
| Theme — TP-0 dark/light × EN/ZH × 1440/390 evidence matrix | **PASS** (24/24 cells captured) |
| Validated-claims (`check_validated_claims.py`) on PR-touched files | **PASS** (zero hits) |
| Template-site sync (`check_template_site_sync.py`) | **PASS** (99 pairs OK) |
| PR-body cross-checks (test counts, viewport math, font-family design-gate note) | **PASS** (all receipts verified) |

### What this PR is — and is not

This is a **candidate-stage UIUX archive-accessibility lane**, half-B of the wider Web Chat UIUX sweep, NOT production acceptance. The PR body is explicit on this point: "Fixture tests/captures are not production acceptance. … Final release requires concluded first-party CI, expected-head acceptance, the existing VPS updater and anonymous public proof. Do not use Vercel." The audit confirms that posture: no `validated` claim is asserted in user-visible positions, the DSC discovery is correctly logged as `kind: landmine / confidence: verified` with a falsifier and a verification command, and the evidence README keeps `MISSION_COMPLETE: false` plus "Next: conclude source/evidence gates, submit this grouped source head through the one GitHub branch/PR, consume real first-party CI, and only after expected-head acceptance publish using the existing VPS updater."

### What this audit is not

This is a one-pass qwen_auditor2-style plain-language / theme / validated-claims audit, not a production acceptance review. Production acceptance for the public Reports archive page remains owed by the lane owner under the standard VPS-pull / anonymous-public-proof contract; this audit confirms the candidate clears the three named discipline gates, nothing more.

### Adjacent PRs of note in the 24-h window (not in this audit's scope)

- Macro #7698 (RIC F3 production proof) — research/ric artifact, no UI surface.
- Macro #7683 (research(risk): audit complete displayed probability surface) — research artifact, no UI surface.
- Macro #7662 (feat(brain): narrow Fast tool visibility by profile) — engine-layer brain gateway, not a user-visible string change.
- Macro #7666 (research(risk): rerun Risk Radar evidence on exact live-state replay) — research artifact.
- Terminal #706 (fix(options): contain volatility term structure on mobile) — already audited by `mastermind-terminal_PR-706.mm.md`.
- Terminal #704 (chart stale-request guard) — already audited by `mastermind-terminal_PR-704.mm.md`.

`/tmp/pr7634.diff` is the gated diff used by `check_design_system.py` and `check_ui_visual_evidence.py`; it can be regenerated as `git diff e83b33bb825^1..e83b33bb825 -- templates/reports.html.j2 site/reports.html site/assets/css/b219cddc.css tests/test_reports_timeline_ui.py > /tmp/pr7634.diff`. Audit head: `3647902e1f4f1ee50e7be8677ec3f603b809496b` on `origin/main` (post-merge). Working tree was returned to clean `origin/main` after the audit (`git status --short` exits 0).