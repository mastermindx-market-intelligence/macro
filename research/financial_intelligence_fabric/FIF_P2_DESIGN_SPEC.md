# FIF P2 — frozen design + build spec

**Document:** `FIF_P2_DESIGN_SPEC.md`
**Lane:** `fif-p2-design-spec-20261012`
**Base (surface cites):** `f8fd119e9a7ec3764dd0fdd9c262892403ad696e` (`origin/main` sparse worktree)
**Route:** existing `fundamental_forensics.html` (Filing Forensics). No new route. No third header family. Shared site nav stays.
**Writer job:** implement this packet with zero design judgment. Every choice below has a one-line reason.
**Out of scope:** engine/API edits; Terminal; saved research (X2); notifications; SNI/risk/Prophet/Ontology/GMI/Executive OS/Subagent Fabric.

**Branch SHAs read (do not re-fetch other remotes):**

| Alias | SHA | What P2 consumes |
|---|---|---|
| BASE | `f8fd119e9a7ec3764dd0fdd9c262892403ad696e` | templates, theme, checkers, kernel request/response at HEAD |
| P0 | `132644f7da34132bc553a9e5f27f9be4385f0744` | journeys + view contract + pinning test |
| C1 | `94d8f26487a7f8a41e20b34238bf8756ad79260f` | `CohortTable.to_dict()` + A35 exclusion codes |
| X1 | `7c0582de0bee20bd9c87d24d71649477a3e2cfc7` | `POST /api/forensics/v1/financial/query.xlsx` |
| E0 | `06e0062862591d0485189bf5b02fc88724abada2` | detector `Finding` fields |
| E1 | `3a037b064c468988d18fd66bacf00d905a406515` | bounded disclosure receipt/finding/redline |

**Seat rulings (frozen):** R1 glance, R2 ranking, R3 source, R4 cutoff, R5 peers, R6 export, R7 glossary, R8 themes, R9 i18n. Do not reopen.

**File-region ownership (P2 may touch):** `templates/fundamental_forensics.html.j2`, `templates/fundamental_forensics.js`, `templates/fundamental_forensics.css`, paired `site/fundamental_forensics.{js,css}` (CI pair), `docs/site_semantics/fundamental_forensics.md` (new), `research/financial_intelligence_fabric/FIF_P0_VIEW_CONTRACT.json` + `tests/test_fundamental_forensics_p0_view_contract.py` (same PR), UI/i18n/evidence tests listed in §10. **P2 must not edit** `app/forensics.py` (P1/X0/X1), any `engine/**` file, or nav includes.

---

## 0. Binding laws the writer implements, not interprets

- Archetype E `intelligence_desk`: desk header (one as-of) → lead brief → cards → watch table → methodology (`research/MASTER_PRODUCT_DESIGN_SYSTEM_V1.md:468-469,487`). Reason: registry already maps this route to E.
- Density: at 1440×900, chrome + the answer + ≤2 supporting modules; at 390 the answer in one swipe (`MASTER_PRODUCT_DESIGN_SYSTEM_V1.md:361-362`). Reason: A42.
- Doctrine glance: title ≤4 words, subtitle ≤14 words, one as-of per panel (`docs/DESIGN_DOCTRINE.md:25,85`). Reason: house law.
- Two header families only (`CLAUDE.md` Navigation source-of-truth). Reason: R1 / no third header.
- Dark = command centre (luminance depth, restrained glow). Light = research workspace (white material, hairlines, shadow not glow). Token substitution alone is a FAIL (`CLAUDE.md` Theme art direction; R8).
- New colour from `templates/theme.css` tokens only (`:root` `--bg/--panel/--panel2/--text/--muted/--line/--act/--warn/--ok/--info/--link`, `html[data-theme="light"]` at `theme.css:208-226`). Existing `.ff-*` classes may stay. Do not add hex. Do not inject stylesheets from JS (`scripts/check_runtime_style_injection.py:1-29`).
- Dual-span `t()` / `pair()`. No CJK in `title=`. Translated tooltips use `data-tip-en` / `data-tip-zh` (R9; `scripts/check_title_i18n.py:10-16`).
- Falsifier/refutation language never front-facing (R9).
- Public shell must not leak private receipts (A24; gate at `html.j2:107-205`; JS `setAccess` `js:684-707`).

---

## 1. First-viewport composition at 1440 and 390

### 1.1 What occupies the fold (target)

**1440×900 (`min-width: 1100px`, `css:1890,2784`):**

1. Shared site nav (`html.j2:21` include `_site_nav.html.j2`). Unchanged.
2. Desk header `.ff-desk-header` (compressed `.ff-hero` + `#ff-run-meta` + `.ff-context-card`).
3. Lead brief `#ff-overview` / `#ff-quick-signal` (what changed + why it matters + source control).
4. Supporting module 1: two glance stats (`#ff-stat-attention`, `#ff-stat-coverage`).
5. Supporting module 2: three next-step buttons (`.ff-next-steps`).

Tab bar and panels start below the fold (amended by AM7). Evidence rail is sticky on the right at ≥1100px and is not a first-viewport module.

**390 (`max-width: 700px`, `css:2023,2822`):** first swipe = nav + desk header (one band) + lead brief (`#ff-quick-signal`). Stats and next-steps may sit in the same brief card, stacked, still inside the first swipe. Hero visual stays `display:none` (`css:2827`).

Reason: R1 + archetype E + density law. Marketing deck/promise chips/document visual are demoted because they answer “what is this product”, not “what changed in this filing”.

### 1.2 Markup — replace `templates/fundamental_forensics.html.j2:25-104`

Keep ids that tests pin: `ff-run-meta`, `ff-freshness-status`, `ff-as-of`, `ff-source-snapshot`, `ff-source-label`, `ff-company-search`, `ff-company-identity`, `ff-company-action` (`tests/test_fundamental_forensics_ui.py:29-65,224-237`).

Unified-diff-ready replacement for `html.j2:25-104` at BASE `f8fd119e9a7e`:

```diff
-    <header class="ff-hero">
-      <div class="ff-hero-copy">
-        <p class="ff-eyebrow">{{ t('Filing forensics', '财报取证') }}</p>
-        <h1>{{ t('Spot the changes that matter.', '找出真正重要的财报变化。') }}</h1>
-        <p class="ff-deck">{{ t('Pick a company. We compare its latest filing with the one before it, explain what stands out in plain English, and link every result to the SEC.', '选择一家公司。我们会把最新财报与上一期逐项对比，用简单语言说明值得关注的变化，并把每项结果链接回 SEC 原文。') }}</p>
-        <div class="ff-hero-promise" aria-label="How Filing Forensics works">
-          <span>{{ t('Compare the numbers', '对比关键数字') }}</span>
-          <span>{{ t('Read wording changes', '阅读措辞变化') }}</span>
-          <span>{{ t('Verify the source', '核对原始来源') }}</span>
-        </div>
-      </div>
-      <div class="ff-hero-visual" aria-hidden="true">
-        … decorative documents …
-      </div>
-    </header>
-
-    <dl class="ff-run-meta" id="ff-run-meta" aria-label="Source freshness" data-freshness="unavailable">
-      … four cells …
-    </dl>
-
-    <section class="ff-context-card" aria-labelledby="ff-company-label">
-      … picker / identity / action …
-    </section>
+    <header class="ff-desk-header" id="ff-desk-header" aria-labelledby="ff-company-label">
+      <p class="ff-eyebrow">{{ t('Filing forensics', '财报取证') }}</p>
+      <div class="ff-desk-row">
+        <div class="ff-company-picker">
+          <label id="ff-company-label" for="ff-company-search">{{ t('Company', '公司') }}</label>
+          <!-- keep existing combobox markup from html.j2:74-90 unchanged -->
+        </div>
+        <div class="ff-company-identity" id="ff-company-identity" aria-live="polite">
+          <!-- keep existing identity markup from html.j2:93-98 unchanged -->
+        </div>
+        <div class="ff-desk-asof" id="ff-desk-asof">
+          <label for="ff-asof-input">{{ t('As of', '截止') }}</label>
+          <div class="ff-asof-controls">
+            <button type="button" id="ff-asof-latest" class="ff-asof-latest is-active" aria-pressed="true">{{ t('Latest', '最新') }}</button>
+            <input id="ff-asof-input" class="ff-asof-input" type="date" autocomplete="off"
+              data-tip-en="Rewind the filing cutoff. Both source and recorded clocks use this day, 23:59:59 UTC."
+              data-tip-zh="回拨财报截止日。来源时钟与入账时钟均使用该日 23:59:59 UTC。">
+          </div>
+        </div>
+        <dl class="ff-run-meta" id="ff-run-meta" aria-label="Source freshness" data-freshness="unavailable">
+          <div>
+            <dt>{{ t('Source status', '来源状态') }}</dt>
+            <dd id="ff-freshness-status">{{ t('Unavailable', '不可用') }}</dd>
+          </div>
+          <div hidden>
+            <dt>{{ t('Latest source filing', '最新来源披露日') }}</dt>
+            <dd id="ff-as-of">—</dd>
+          </div>
+          <div hidden>
+            <dt>{{ t('Source snapshot', '来源快照') }}</dt>
+            <dd id="ff-source-snapshot">—</dd>
+          </div>
+          <div>
+            <dt>{{ t('Built from', '数据来源') }}</dt>
+            <dd id="ff-source-label">—</dd>
+          </div>
+        </dl>
+        <div class="ff-desk-export">
+          <a class="ff-export-link" id="ff-export-link" href="#" hidden>{{ t('Export', '导出') }}</a>
+          <button type="button" class="ff-export-btn" id="ff-export-btn" disabled
+            data-tip-en="Export is unavailable until this issuer, cutoff and policy can be queried."
+            data-tip-zh="在可查询该发行人、截止日和策略之前，导出不可用。"
+            data-label-en="Export unavailable" data-label-zh="导出不可用">{{ t('Export', '导出') }}</button>
+        </div>
+      </div>
+      <p class="ff-desk-stamp" id="ff-desk-stamp">{{ t('As of — · Source —', '截止 — · 来源 —') }}</p>
+      <div class="ff-company-action" id="ff-company-action" hidden>
+        <!-- keep existing action chip markup; hidden at glance; still filled by JS for tests -->
+      </div>
+    </header>
```

Word budgets (glance, doctrine Law 4):

| Element | EN budget | EN copy | ZH copy |
|---|---|---|---|
| eyebrow | 2 words | Filing forensics | 财报取证 |
| picker label | 1 word | Company | 公司 |
| as-of label | 2 words | As of | 截止 |
| latest toggle | 1 word | Latest | 最新 |
| export | 1 word | Export | 导出 |
| desk stamp | 1 line | `As of {date} · {freshness}` | `截止 {date} · {freshness}` |

Reason: R1 “issuer picker, one as-of line and the freshness state in one band”. Hidden `#ff-as-of` / `#ff-source-snapshot` stay in DOM so `renderRunMeta` (`js:916-918`) and UI tests keep those ids; JS copies their values into `#ff-desk-stamp`. The action chip is hidden because stance lives on the lead brief, not a third chrome row.

### 1.3 Lead brief — edit `html.j2:212-269`

Keep ids `ff-overview`, `ff-overview-title`, `ff-overview-status`, `ff-quick-signal`, `ff-quick-signal-label`, `ff-quick-signal-title`, `ff-quick-signal-summary`, `ff-stat-attention`, `ff-stat-watch`, `ff-stat-coverage`, `ff-stat-sources`. Hide watch and sources stats with `hidden` (one-integer law: attention is the canonical count; coverage is the second supporting number). Keep `#ff-stat-watch` / `#ff-stat-sources` in DOM for existing JS writers (`js:990-993`).

```diff
     <section class="ff-overview" id="ff-overview" aria-labelledby="ff-overview-title">
       <div class="ff-overview-lead">
-        <p class="ff-kicker">{{ t('Latest filing snapshot', '最新财报速览') }}</p>
+        <p class="ff-kicker">{{ t('This filing', '本期财报') }}</p>
         <div class="ff-overview-heading">
           <div>
-            <h2 id="ff-overview-title">{{ t('The important changes, up front', '先看最重要的变化') }}</h2>
-            <p>{{ t('A fast read of what stands out, followed by the numbers and SEC proof.', '先快速了解值得关注的变化，再查看关键数字和 SEC 证据。') }}</p>
+            <h2 id="ff-overview-title">{{ t('What changed', '发生了什么变化') }}</h2>
+            <p>{{ t('Why it is worth reviewing, with the source one click away.', '为何值得复核，来源一键可核。') }}</p>
           </div>
           …
         </div>
         <article class="ff-quick-signal" id="ff-quick-signal" data-priority="watch">
           …
-            <span class="ff-quick-signal-label" id="ff-quick-signal-label">{{ t('First thing to understand', '首先需要了解') }}</span>
+            <span class="ff-quick-signal-label" id="ff-quick-signal-label">{{ t('Why it matters', '为什么重要') }}</span>
             <h3 id="ff-quick-signal-title">…</h3>
             <p id="ff-quick-signal-summary">…</p>
+            <p class="ff-quick-signal-magnitude" id="ff-quick-signal-magnitude" hidden></p>
           …
-          <button class="ff-quick-signal-open" type="button" data-open-primary-finding>
-            {{ t('Open signal analysis', '打开信号分析') }} <span aria-hidden="true">→</span>
-          </button>
+          <button class="ff-quick-signal-open ff-source-control" type="button" data-open-primary-finding>
+            {{ t('Open source', '打开来源') }} <span aria-hidden="true">→</span>
+          </button>
         </article>
       </div>
       <div class="ff-overview-side">
         <div class="ff-snapshot-stats" aria-label="Latest filing summary">
           <div class="ff-snapshot-stat is-attention">… Need attention …</div>
-          <div class="ff-snapshot-stat is-watch">…</div>
+          <div class="ff-snapshot-stat is-watch" hidden>…</div>
           <div class="ff-snapshot-stat is-coverage">… Metrics compared …</div>
-          <div class="ff-snapshot-stat is-source">…</div>
+          <div class="ff-snapshot-stat is-source" hidden>…</div>
         </div>
         <div class="ff-next-steps">… unchanged three buttons …</div>
       </div>
     </section>
```

Word budgets:

| Element | Budget | EN | ZH |
|---|---|---|---|
| kicker | 2 words | This filing | 本期财报 |
| h2 | 2 words (≤4) | What changed | 发生了什么变化 |
| subtitle | 14 words | Why it is worth reviewing, with the source one click away. | 为何值得复核，来源一键可核。 |
| signal label | 3 words | Why it matters | 为什么重要 |
| CTA | 2 words | Open source | 打开来源 |

Reason: A42 glance is “what changed and why it matters”; R3 makes the CTA a source control into `#ff-evidence`, not a generic analysis label.

`renderOverview` (`js:979-1032`) must also fill `#ff-quick-signal-magnitude` from `first.values[0].delta` via `formatSigned(delta, format)` when a value exists; hide the node when no delta. Ranking stays `orderedFindings` (`js:351-365`). Reason: R2 — magnitude is a value on the card, not the sort key.

### 1.4 CSS — `templates/fundamental_forensics.css`

Delete or leave inert the decorative `.ff-hero-visual` / `.ff-document*` / `.ff-hero-promise` rules (`css:2593-2632`). Add `.ff-desk-header` rules. Do not add hex. Map accents to theme tokens.

```css
/* Desk header — replaces .ff-hero geometry at css:62-88 and css:2569-2648. */
.ff-desk-header {
  display: grid;
  gap: 8px;
  padding: 12px 16px 10px;
  border: 1px solid var(--line);
  border-radius: 14px;
  background: var(--panel);
}
.ff-desk-row {
  display: grid;
  grid-template-columns: minmax(220px, 1.1fr) minmax(180px, .9fr) minmax(160px, .7fr) minmax(140px, .6fr) auto;
  align-items: end;
  gap: 12px;
}
.ff-desk-stamp {
  margin: 0;
  color: var(--muted);
  font-size: var(--fs-micro);
  font-variant-numeric: tabular-nums;
}
.ff-asof-controls { display: flex; gap: 6px; align-items: center; }
.ff-asof-latest, .ff-export-btn, .ff-export-link {
  min-height: 36px;
  padding: 0 12px;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: var(--panel2);
  color: var(--text);
  font-size: var(--fs-label);
  font-weight: 700;
}
.ff-asof-latest.is-active {
  border-color: color-mix(in srgb, var(--info) 45%, var(--line));
  color: var(--text);
}
.ff-asof-input {
  min-height: 36px;
  padding: 0 10px;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: var(--panel2);
  color: var(--text);
}
.ff-export-btn:disabled,
.ff-source-control:disabled {
  opacity: .46;
  cursor: not-allowed;
}
.ff-run-meta {
  display: grid;
  grid-template-columns: auto auto;
  gap: 8px;
  margin: 0;
  padding: 0;
  border: 0;
  background: transparent;
  box-shadow: none;
}
#ff-overview { margin-top: 12px; }
.ff-quick-signal {
  grid-template-columns: 48px minmax(0, 1fr) auto;
  min-height: 0;
}
.ff-quick-signal-magnitude {
  margin: 6px 0 0;
  font-family: var(--font-mono);
  font-size: var(--fs-md);
  font-variant-numeric: tabular-nums;
}
@media (min-width: 1100px) {
  .ff-overview { grid-template-columns: minmax(0, 1.6fr) minmax(240px, .55fr); }
}
@media (max-width: 700px) {
  .ff-desk-row { grid-template-columns: minmax(0, 1fr); }
  .ff-desk-export { justify-self: stretch; }
  .ff-export-btn, .ff-export-link { width: 100%; }
  .ff-quick-signal { grid-template-columns: 40px minmax(0, 1fr); }
  .ff-quick-signal-open { grid-column: 1 / -1; width: 100%; }
}
```

**DARK TREATMENT (command centre):** `.ff-desk-header` fill `var(--panel)` (`theme.css:63` `#181b21`) on `var(--bg)` `#0f1115`. Active as-of and selected source-control use a *restrained* `color-mix(in srgb, var(--info) 18%, var(--panel))` fill and `0 0 0 1px color-mix(in srgb, var(--info) 35%, transparent)` ring — no drop-shadow bloom, no second aurora. Freshness `current` inks `#ff-freshness-status` with `var(--ok)`; `stale` `var(--warn)`; `degraded` `var(--act)`; `unavailable` `var(--muted)` (existing `css:127-130`, keep). Lead brief `#ff-quick-signal` keeps luminance depth via `color-mix` of `var(--info)` into `var(--panel2)`, not the old `--ff-indigo` hex. Page canvas keeps the existing radial wash at `css:2552-2556` *only if* those mixes are rewritten onto `var(--info)` / `var(--act)` (R8: new colour from theme tokens). Mechanism that differs from light: glow ring + dark panel stack.

**LIGHT TREATMENT (research workspace):** `html[data-theme="light"] .ff-desk-header` is white `var(--panel)` (`theme.css:213` `#ffffff`) on canvas `var(--bg)` `#f7f8fa`, hairline `1px solid var(--line)` (`theme.css:221`), `box-shadow: 0 1px 0 rgba(28,36,48,.04), 0 8px 24px -18px rgba(28,36,48,.18)` — **shadow, not glow**. Active as-of uses `var(--info)` `#285fff` as a 1px hairline + 4% tint fill, zero box-shadow glow. `.ff-quick-signal` is a white card, hairline `var(--line)`, no cyan/indigo gradient (`css:2781` today is a FAIL if left as the only light change). Mechanism that differs from dark: hairline + shadow; no `box-shadow` colour-mix of `--info`.

Reason: R8 requires named DARK/LIGHT treatments and different mechanisms, not token swap.

Writer also updates the duplicate desktop workspace rule at `css:2784-2798` when adding the peers tab (see §4).

### 1.5 JS first-viewport behaviour

- `renderRunMeta` (`js:873-918`) still writes the four dd ids. Additionally set `#ff-desk-stamp` to `pair('As of ' + date + ' · ' + status, '截止 ' + date + ' · ' + status)`.
- Do not add a refresh button. Reload re-fetches with `cache:'no-store'` (`js:765-768`). Reason: R6.
- Gate (`html.j2:114-210`) still replaces the workbench. Desk header is inside `#ff-main` and hides with the workbench when gated (`js` `setAccess`). Anonymous users never see issuer numbers. Reason: A24.

---

## 2. Source controls (R3)

Every displayed number, statement cell, finding value, disclosure change, and redline is a **control**. It opens the existing `#ff-evidence` drawer (sheet at 390) on the exact occurrence/version/span. It never navigates to a generic EDGAR browse page when a span exists.

### 2.1 Control markup (JS-generated; classes frozen)

```html
<button type="button"
  class="ff-source-control"
  data-source-kind="cell|finding|disclosure|redline|statement"
  data-occurrence-id="rawfact_…"
  data-root-cell-id="metric_cell_…"
  data-snapshot-id="ffqsv2_…"
  data-accession="0000320193-25-000073"
  data-span-start="1234"
  data-span-end="1288"
  data-finding-id="…"
  data-disclosure-id="…"
  data-redline-id="…"
  aria-controls="ff-evidence"
  data-tip-en="Open the source span for this number"
  data-tip-zh="打开该数字的来源片段">
  <span class="ff-compact tnum">$94.9B</span>
</button>
```

Disabled when no span:

```html
<button type="button" class="ff-source-control is-unavailable" disabled
  aria-disabled="true"
  data-tip-en="Source span unavailable"
  data-tip-zh="来源片段不可用">
  <span class="ff-compact tnum">$94.9B</span>
  <span class="ff-source-unavail">{{ pair already via JS }}Source span unavailable / 来源片段不可用</span>
</button>
```

Do not fall back to `https://www.sec.gov/edgar/browse/?CIK=…` (`scripts/build_fundamental_forensics.py:183-201` at census). Timeline “Open SEC filing” (`js:1459`) stays a document-level link **only** when the user is on the Filing history tab and no span exists; it is not the number-click path.

Reason: A44 + R3. A generic home page is the named failure.

### 2.2 Where to wrap (file + function)

| Surface | Function at BASE | Change |
|---|---|---|
| Lead brief CTA | `renderOverview` `js:1026-1031` | CTA is already a button; add `ff-source-control` and span attrs from the primary finding |
| Finding cards | `renderFindings` `js:1153-1168` | wrap period/magnitude in `ff-source-control`; card button still selects; magnitude click opens drawer on that value’s occurrence |
| Finding value rows | `renderEvidence` `js:2683-2687` | wrap each `value.current` / `value.prior` / `value.delta` |
| Statements table | `renderStatements` `js:1474-1479` | each metric `<td>` becomes a control (see §2.4) |
| Compare/revision cells | `renderCompare` `js:1518-1531` | each `<strong>` becomes a control |
| Disclosure feed | `renderDisclosureFeed` `js:1334` | the change row is already a button; add span attrs from `evidence_receipts[0].source_span` |
| Redlines | `renderRedlines` `js:1390` | wrap changed tokens; span from `prior_receipt` / `current_receipt` |
| Statement tree cells | new `renderStatementTree` | wrap `cell.value` |

Do **not** wrap `#ff-stat-attention` counts (they are cardinalities, not filing numbers).

### 2.3 Span resolution order (no design fork)

1. Financial query cell: `receipt.nodes[i].provenance.selected_raw_fact.source_span` as `[start, end]` integers (`query.py:1578-1588,1485`) plus `occurrence_id` (`query.py:1466,1611`) plus `provenance.accession` (`query.py:1366`).
2. Statement cell: `cell.source_receipt.source_span` (`statement_graph.py:919-940`). Shape is a mapping with `start` (census E1 disclosure span uses `char_start`/`char_end` at E1 `disclosure_projection.py:389-394`). Writer reads `start` or `char_start`, `end` or `char_end`. If the object is a two-int list, use `[0]`/`[1]`.
3. Disclosure/redline: `evidence_receipts[].source_span` or `prior_receipt`/`current_receipt`.`source_span` (E1 `disclosure_projection.py:368-388,508-509`).
4. Finding from state: if P1 has not attached occurrence/span, match the displayed metric to the query node by `metric_id` + period label; if still none, disabled state.

Never invent a `#page=N` EDGAR URL. Drawer shows the bounded excerpt (`display_excerpt` / `source_excerpt`, E1 `:375-377`) plus accession, occurrence id (in `<code>`, English `title=` = the id string only, `js:2348` pattern), and version/snapshot id.

### 2.4 Statements cells — `renderStatements` replacement (`js:1464-1483`)

Each metric td:

```javascript
function sourceControlHtml(opts) {
  var spanOk = opts.spanStart != null && opts.spanEnd != null && String(opts.spanStart) !== '' && String(opts.spanEnd) !== '';
  var compact = esc(opts.compactText);
  if (!spanOk) {
    return '<button type="button" class="ff-source-control is-unavailable" disabled aria-disabled="true"'
      + ' data-tip-en="Source span unavailable" data-tip-zh="来源片段不可用">'
      + '<span class="ff-compact tnum">' + compact + '</span>'
      + '<span class="ff-source-unavail">' + pair('Source span unavailable', '来源片段不可用') + '</span></button>';
  }
  return '<button type="button" class="ff-source-control"'
    + ' data-source-kind="' + esc(opts.kind) + '"'
    + ' data-occurrence-id="' + esc(opts.occurrenceId || '') + '"'
    + ' data-root-cell-id="' + esc(opts.rootCellId || '') + '"'
    + ' data-snapshot-id="' + esc(opts.snapshotId || '') + '"'
    + ' data-accession="' + esc(opts.accession || '') + '"'
    + ' data-span-start="' + esc(String(opts.spanStart)) + '"'
    + ' data-span-end="' + esc(String(opts.spanEnd)) + '"'
    + ' aria-controls="ff-evidence"'
    + ' data-tip-en="Open the source span for this number" data-tip-zh="打开该数字的来源片段">'
    + '<span class="ff-compact tnum">' + compact + '</span></button>';
}
```

Compact text on the table is `formatValue`. Exact decimal lives in the drawer as `<code class="ff-exact">` with the API string unmodified (A38).

### 2.5 Focus / keyboard / drawer contract

Reuse the existing drawer (`html.j2:455-472`, `openAnalysisDrawer` `js:2881-2894`, `closeEvidence` `js:2903-2916`, trap `js:2970-2993`).

| Event | Behaviour |
|---|---|
| Activate source control (click / Enter / Space) | `state.lastFocus =` the control. `state.evidenceKind` = kind. Write URL (see §6) with `drawer=1` and the occurrence/span ids. `history.pushState`. `openAnalysisDrawer()`. Focus close button (`js:2892`). |
| Escape | `closeEvidence(true)` restores `state.lastFocus` (`js:2913-2914`). `history.back()` if this open pushed a drawer frame (see §6). |
| Tab | cycle inside `#ff-evidence` (`js:2977-2992`). |
| Scrim click | close with restore (`js:3265-3268`). |
| Close button | same. |
| Desktop ≥1100 sticky rail | drawer content still renders in `#ff-evidence`; `is-open` modal is for <1100 (`css:1945`) and the explicit analysis open (`css:1912`). Do not create a second drawer. |
| 390 | existing bottom sheet (`css:2112-2136`). |
| Cross 1100px | existing `handleViewportChange` closes without restore (`js:3020-3024`). Keep that. |

Extend `renderEvidence` / add `renderCellEvidence(node)`:

- Title: metric label via `pair(METRICS.en, METRICS.zh)` or statement `as_reported_label` (plain words). Internal slugs (`metric_id`, `occurrence_id`) go in a `<details>` labelled `pair('Technical ids', '技术编号')`.
- Section “Why this matters” stays for findings (`js:2713`). For a bare cell, use `pair('What this number is', '这个数字是什么')` + one sentence from the glossary (R7), not detector jargon.
- Exact value: `<code class="ff-exact">` = API `value` bytes.
- Compact: secondary line `pair('Compact', '简写')`.
- Excerpt: `<blockquote class="ff-span-excerpt">` from `display_excerpt` or a slice of statement source; if none, the disabled copy.
- Do not render `falsif*` / `refut*` strings.

**DARK TREATMENT:** source-control is a ghost button on `var(--panel2)` with 1px `var(--line)`; hover adds restrained `var(--info)` 12% fill. Disabled uses `var(--muted)` and no hover. Drawer keeps existing `.ff-evidence` dark panel (`css:2738-2742`) with `--info` 7% head gradient rewritten off `--ff-indigo`.

**LIGHT TREATMENT:** source-control is a white chip, hairline `var(--line)`, hover `box-shadow: 0 1px 2px rgba(28,36,48,.12)` (shadow, not glow). Disabled: 46% opacity, `cursor: not-allowed` (match receipt pager `css:1449`). Drawer is white material, hairline, `box-shadow: 0 12px 40px -24px rgba(28,36,48,.28)`.

---

## 3. Cutoff + revisions panel (R4)

### 3.1 As-of control (desk header, §1.2)

| State | URL | Request clocks |
|---|---|---|
| Latest (default) | omit `as_of` | `policy.selection` default `latest_known_as_of`; `source_snapshot_at` = health `clocks.broad_source_at`; `recorded_at` = health `clocks.composed_state_at` (`js:916-918`; `query_service.py:59,337-346`) |
| Picked day | `as_of=YYYY-MM-DD` | both clocks = `{date}T23:59:59Z` |
| Health missing | control disabled | no POST; stamp `Unavailable` / `不可用` |

Reason: one as-of line (doctrine Law 4); both PIT clocks stay equal so the writer does not invent a split-clock UX. End-of-day UTC is the only expansion rule.

`#ff-asof-latest` sets latest, clears `as_of`, `pushState`, re-queries. `#ff-asof-input` `change` writes `as_of`, deactivates Latest, re-queries. Do not query on every keystroke.

Default policy in URL omitted = `latest_known_as_of` (`query.py:196-198`). Optional `policy=` may be `as_reported` \| `latest_known_as_of` \| `latest_restated`. Invalid values fall back to default without throwing.

### 3.2 Where revisions render

Keep tab id `compare` (`html.j2:301-303`, `js:2732`) so the seven-id contract does not break until the peers tab lands. Change visible copy:

```diff
-            <span class="ff-tab-icon" aria-hidden="true">↔</span>{{ t('Compare periods', '期间对比') }}
+            <span class="ff-tab-icon" aria-hidden="true">↔</span>{{ t('Revisions', '重述对照') }}
```

Inside `#ff-panel-compare` (`html.j2:406-426`), insert **above** `#ff-compare-grid`:

```html
<section class="ff-revisions" id="ff-revisions" aria-labelledby="ff-revisions-title">
  <h3 id="ff-revisions-title">{{ t('Original, latest, restated', '原始、截止最新、重述后') }}</h3>
  <p>{{ t('Same period, three source vintages. A blank column is an absence, not a zero.', '同一期间、三种来源版本。空列是缺失，不是零。') }}</p>
  <div id="ff-revisions-table"></div>
</section>
```

Keep the existing two-period compare as a **secondary** block below (still `#ff-compare-grid`). Reason: R4 is vintage policy, not a second period picker; the old compare remains a drilldown.

### 3.3 Three-column layout

JS `renderRevisions()` builds:

```html
<table class="ff-table ff-revisions-table">
  <thead>
    <tr>
      <th>Metric / 指标</th>
      <th>Original reported / 原始披露</th>
      <th>Latest as of cutoff / 截止时点最新值</th>
      <th>Restated / 重述后</th>
    </tr>
  </thead>
  <tbody>…one row per metric_id…</tbody>
</table>
```

Each body cell is a source control whose value is the matching query node `value` (exact in drawer, compact on the face).

Column ← policy mapping (`query.py:179-198`):

| Column | `policy.selection` |
|---|---|
| Original reported | `as_reported` |
| Latest as of cutoff | `latest_known_as_of` |
| Restated | `latest_restated` |

Three POSTs to `/api/forensics/v1/financial/query` sharing `entity_id`, `metric_ids`, `periods`, `source_snapshot_at`, `recorded_at`. Plus one POST to `/api/forensics/v1/financial/revisions` with the **same body** as the latest-as-of query except `"schema": "fundamental_forensics.financial_revision_request/v1"` (`revision_service.py:50-51,258`).

### 3.4 Absence states (explicit, never zero)

| Condition | Cell face |
|---|---|
| HTTP 200, node `state` = `missing` (`query.py:209-211`) | `pair('No value at this cutoff', '该截止日无此值')` ; control disabled |
| `state` = `not_evaluable` | `pair('Cannot evaluate', '无法评估')` + `reason` in drawer only |
| Restated column and `revisions` array empty (`revision_service.py:310`) | `pair('No revision in this package', '本数据包中无重述')` |
| HTTP 400 `unknown entity` | panel empty state; do not paint zeros |
| HTTP 401 / 403 | existing gate (`js:625-641`) |
| HTTP 503 | `pair('Revisions temporarily unavailable', '重述服务暂不可用')` |
| No `entity_id` on company | `pair('Issuer identity unavailable', '发行人标识不可用')` — do not guess `ISS:` from ticker. Reason: `query_service.py` binds the supplied `entity_id`; ticker inference is forbidden. |

`visible_under_selected_policy_and_cutoffs` / `used_as_selected_value` (`financial_intelligence_packet.py:1364-1366`) are drawer facts, not glance labels.

### 3.5 Exact API request bodies and response paths

**Query POST** `app/forensics.py:841-872` at BASE; admission `query_service.py:50,58-60,286-310,500-609`.

Request (floats forbidden; decimal strings only):

```json
{
  "schema": "fundamental_forensics.financial_query_request/v1",
  "entity_id": "<company.entity_id>",
  "policy": {
    "selection": "latest_known_as_of",
    "source_snapshot_at": "2025-06-30T23:59:59Z",
    "recorded_at": "2025-06-30T23:59:59Z"
  },
  "metric_ids": [
    "revenue",
    "gross_profit",
    "accounts_receivable_net",
    "inventory_net",
    "net_cash_from_operating_activities",
    "capital_expenditures",
    "operating_income_loss",
    "net_income_loss"
  ],
  "periods": [
    { "kind": "duration", "start": "2025-03-30", "end": "2025-06-28", "label": "FY2025 Q3" }
  ]
}
```

`metric_ids` are S1 catalog ids (`FIF_S1_METRIC_REGISTRY.md:40`), **not** the UI short keys in `METRICS` (`js:54-64`). Map:

| UI `METRICS.key` (`js:55-63`) | Query `metric_id` |
|---|---|
| `revenue` | `revenue` |
| `gross_profit` | `gross_profit` |
| `receivables` | `accounts_receivable_net` |
| `inventory` | `inventory_net` |
| `cfo` | `net_cash_from_operating_activities` |
| `capex` | `capital_expenditures` |
| `op_income` | `operating_income_loss` |
| `ni` | `net_income_loss` |
| `contract_liabilities` | **do not query** (not in S1 core 40). Keep state-table only. GAP. |

Period objects on the wire may contain only `{kind, start, end, label}` (`query_service.py:60,397-398`). Writer builds them from statement `columns[]` when present; else from `company.periods` **only if** `start` and `end` both exist. If `start` is missing, skip that period and show `pair('Period start unavailable', '期间起始日不可用')`. Do not invent a start. GAP if state periods lack `start`.

Response paths (exact display):

| Face | JSON path from query body |
|---|---|
| entity | `entity.entity_id`, `entity.cik`, `entity.ticker` (`query_service.py:561-566`) |
| cutoff echo | `receipt.policy.source_snapshot_at`, `receipt.policy.recorded_at`, `receipt.policy.selection` (`query.py:644-649,3446`) |
| cell | `receipt.nodes[n]` where `nodes[n].cell_id === receipt.root_cell_ids[i]` (`query.py:3451-3452,1904-1918`) |
| exact value | `receipt.nodes[n].value` (canonical decimal text or `null`; `raw_ledger.py:260-263`; `query.py:1914`) |
| unit | `receipt.nodes[n].unit` |
| state | `receipt.nodes[n].state` ∈ `value\|missing\|not_evaluable` |
| occurrence | `receipt.nodes[n].provenance.selected_raw_fact.occurrence_id` |
| span | `receipt.nodes[n].provenance.selected_raw_fact.source_span` `[start,end]` |
| accession | `receipt.nodes[n].provenance.accession` |
| version clocks | `provenance.source_snapshot_at`, `provenance.recorded_cutoff_at` (`query.py:1362-1363`) |

**Revisions POST** `app/forensics.py:888` at BASE; envelope `revision_service.py:293-311`.

Response rows: `revisions[]` each with `metric_id`, `period`, `root_value`, `prior_value`, `revised_value`, `root_occurrence_id`, `parent_occurrence_id`, `revised_occurrence_id`, `root_accession`, `prior_accession`, `revised_accession`, `absolute_delta`, `relative_delta` (`financial_intelligence_packet.py:1345-1371`). `relative_delta` is a **ratio**, not percent (`:1389-1393`). Glance may compact `absolute_delta`; drawer shows the three decimal strings verbatim.

**Statements POST** `app/forensics.py:990`; request `{schema:"fundamental_forensics.financial_statement_request/v1", entity_id, accession}` (`statement_service.py:33-35,83-99`). Accession = current filing from disclosure `current_accession` or query `provenance.accession`. Response: `statements[]` of `{statement_type, title, columns, rows[]}`; row `as_reported_label`, `cells[]` with `value`, `unit`, `decimals`, `quality_state`, `source_receipt` (`statement_graph.py:924-942,1140-1147`). `quality_state` `available` paints a control; `missing_fact` / `nil` / `abstract` / `ambiguous` paint the explicit disabled copy.

JS fetch helper (new, next to `js:7-11`):

```javascript
var FINANCIAL_QUERY_URL = '/api/forensics/v1/financial/query';
var FINANCIAL_REVISIONS_URL = '/api/forensics/v1/financial/revisions';
var FINANCIAL_STATEMENTS_URL = '/api/forensics/v1/financial/statements';
var FINANCIAL_QUERY_XLSX_URL = '/api/forensics/v1/financial/query.xlsx';
```

`POST` + `Content-Type: application/json` + `credentials:'same-origin'` + `cache:'no-store'` + `withAuth`. Verify `X-FIF-Response-SHA256` equals hex sha256 of the **raw** response body before `JSON.parse`. On mismatch: treat as 503, do not render numbers. Reason: A38 adapter-byte equality (`FIF_P1_PLAN.md` (vii)).

**DARK TREATMENT:** three-column table on `var(--panel)`; column heads `var(--muted)` micro caps; restated column 6% `var(--warn)` tint when `revised_value !== root_value`. **LIGHT TREATMENT:** white table, hairline `var(--line)`, restated column 6% `var(--warn)` tint **and** a 1px left hairline (no glow). Differing mechanism: dark uses fill tint only; light uses hairline + tint.

---

## 4. Peer panel (R5)

Read-only. Persistence is URL state only. No `localStorage` / `sessionStorage`. Saved comparisons are X2.

### 4.1 Placement

Eighth tab in the Verify group (`html.j2:299-308`):

```html
<button class="ff-tab" id="ff-tab-peers" type="button" role="tab"
  aria-selected="false" aria-controls="ff-panel-peers" tabindex="-1" data-tab="peers">
  <span class="ff-tab-icon" aria-hidden="true">▦</span>{{ t('Peers', '同业') }}
</button>
```

```html
<section class="ff-panel" id="ff-panel-peers" role="tabpanel" aria-labelledby="ff-tab-peers" tabindex="0" hidden>
  <header class="ff-panel-head">
    <p class="ff-kicker">{{ t('Peer set', '同业组') }}</p>
    <h2>{{ t('Who is in, who is out', '谁在组内，谁被排除') }}</h2>
    <p>{{ t('Ranks use only companies that qualify. Exclusions are listed with a reason.', '排名只计入符合条件的公司。排除项均附原因。') }}</p>
  </header>
  <p class="ff-peer-policy" id="ff-peer-policy"></p>
  <div id="ff-peer-included"></div>
  <div id="ff-peer-excluded"></div>
</section>
```

Add `'peers'` to `setTab` allowed list (`js:2732`). Update both desktop workspace selectors (`css:1893-1897` and `css:2786-2793`) so peers does **not** steal the sticky evidence rail (like `statements`).

Reason: J4 is a drilldown, not a first-viewport module (masterplan `MASTERPLAN.md:106`).

### 4.2 Payload shape (C1 `94d8f264`, `peer_cohort.py:91-107,377-425`)

Read `state.payload.peer_cohort` if present (object = `CohortTable.to_dict()`):

```
cohort_id, members_n,
members[]: {issuer_id, cik, tickers[], issuer_class, sic},
emissions[]: {metric_id, emission_state, eligible_n, rows[], ranks, percentiles, mean},
exclusions[]: {issuer_id, metric_id, code, reason},
authority: {class: "context_only", display_only: true}
```

`emission_state` is `ranked` or `below_min_n` (`peer_cohort.py:232-250`). When `below_min_n`, do not paint ranks/mean; show `pair('Not enough peers to rank', '同业数量不足以排名')`.

There is **no** peer HTTP route on C1 or BASE. P2 must not add one (`app/forensics.py` is out of ownership). If `peer_cohort` is absent, render the empty state and still honour URL params so a later C1/P1 blob hydrates the same permalink.

Row values are already decimal strings (`peer_cohort.py:399`). Display compact on the face, exact in the drawer. Do not re-rank in the browser.

### 4.3 Exclusion-reason rendering

Map `code` + `reason` (C1 `:189-190,268-315`) to glance copy. Raw code stays in the drawer.

| code | reason | Glance EN | Glance ZH |
|---|---|---|---|
| A35-I1 | duplicate_share_class | Same company, another share class | 同一公司的另一类股份 |
| A35-X1 | missing_peer_observation | No observation in this package | 本数据包中无观察值 |
| A35-B1 | metric_not_applicable | This metric does not apply | 该指标不适用 |
| A35-W1 | statement_withheld | Statement not rebuilt from this filing | 未能从该财报重建此报表 |
| A35-P1 | period_misaligned | Reporting period does not line up | 报告期未对齐 |
| A35-P2 | period_shifted-and-labeled | Shifted period | 期间已平移 |

Unknown code: `pair('Excluded', '已排除')` + code in drawer. Never show `A35-*` on the glance tier (doctrine Law 2).

Included list: members whose `issuer_id` appears in the selected emission’s `rows`. Show ticker[0], compact `value`, `period_label`. Anchor issuer (`URL` or `cohort.members` matching current `entity_id`) gets `aria-current="true"` and kicker `pair('This company', '本公司')`.

### 4.4 URL parameters

| Param | Default | Meaning |
|---|---|---|
| `peers` | omitted | `1` opens the peers tab (`tab=peers` also does) |
| `cohort` | omitted | `cohort_id` to display when multiple exist; else the payload’s `cohort_id` |
| `peer_metric` | first `emissions[].metric_id` | selected metric |
| `align` | `exclude` | `exclude` \| `shift_labeled` (C1 `alignment_mode` default `:48`) |
| `peer_n` | `3` | `min_n` display of policy line |
| `peer_tol` | `45` | `period_tolerance_days` display |

Policy line `#ff-peer-policy`: `pair('Policy: exclude misaligned periods · 45-day window · at least 3 peers', '策略：排除未对齐期间 · 45 天窗口 · 至少 3 家同业')` built from those params. C1 `to_dict()` does not echo policy — URL is the authority for the line. Reason: R5 permalink; no localStorage.

**DARK TREATMENT:** included rows on `var(--panel2)`; excluded rows 8% `var(--muted)` fill, no strikethrough (strikethrough reads as deleted data). **LIGHT TREATMENT:** included white + hairline; excluded 8% `var(--muted)` + dashed hairline. Differing mechanism: dark = fill only; light = dashed hairline.

---

## 5. Export entry (R6)

### 5.1 Placement

One Export control in the desk header (markup in §1.2). No second export in tabs. No refresh control.

### 5.2 Request (X1 `7c0582de`, `app/forensics.py:889-924`, `excel_export.py:123-147`)

Enabled path: JS `fetch(FINANCIAL_QUERY_XLSX_URL, { method:'POST', headers: {Authorization, 'Content-Type':'application/json', Accept: XLSX media type}, body: JSON.stringify(queryBody), credentials:'same-origin', cache:'no-store' })` then download the blob as `Content-Disposition` filename (`{query_id}.xlsx`).

`queryBody` **byte-identical** to the JSON query for the current issuer, cutoff, and selected policy (same `schema`, `entity_id`, `policy`, `metric_ids`, `periods`). Reason: R6 “current issuer, cutoff and policy”; A38.

X1 media type: `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` (`excel_export.py:25-27`).

The visible `#ff-export-link` may be left `hidden`; the button triggers the POST. Do not GET the xlsx route (X1 registers GET as 405, `app/forensics.py:877-885` on that branch).

At BASE `f8fd119e` the xlsx route **does not exist**. Writer: if POST returns 404/405, keep the control disabled. Do not invent a JSON-download fallback.

### 5.3 Disabled / unauthorised

| Condition | Control | Copy |
|---|---|---|
| Gate signin (401) | disabled | `Sign in to export` / `登录后导出` |
| Gate upgrade (403) | disabled | `Included in Essential` / `Essential 包含` |
| 503 / xlsx missing | disabled | `Export unavailable` / `导出不可用` |
| No entity_id / no cutoff clocks | disabled | `Export unavailable` / `导出不可用` |
| Entitled + queryBody legal | enabled button | `Export` / `导出` |

Do not put licensed bytes on `#ff-gate-preview`. Reason: A24.

**DARK TREATMENT:** enabled export is a quiet `var(--panel2)` chip with `--info` 1px ring when focused. **LIGHT TREATMENT:** white chip, hairline, hover shadow `0 1px 2px rgba(28,36,48,.12)`. Differing mechanism: dark focus ring vs light hover shadow.

---

## 6. URL state schema

Today: `?symbol=` only (`js:819-865,3275-3278`). `pushState({symbol})`. `location.hash` preserved but unread (`js:865`).

### 6.1 Params

| Param | Default | Allowed | Writes |
|---|---|---|---|
| `symbol` | payload `default_symbol` | ticker in `companies` | `setCompany` |
| `tab` | `radar` | `radar\|statements\|disclosures\|redlines\|timeline\|compare\|trace\|peers` | `setTab` |
| `as_of` | omitted = latest | `YYYY-MM-DD` | as-of control |
| `policy` | omitted = `latest_known_as_of` | `as_reported\|latest_known_as_of\|latest_restated` | as-of / revisions |
| `finding` | first ranked | finding `id` | radar / overview |
| `disc` | omitted | disclosure `finding_id` | disclosures |
| `redline` | omitted | redline `op_id` | redlines |
| `drawer` | omitted | `1` | source control open |
| `occ` | omitted | `occurrence_id` | drawer |
| `cell` | omitted | `root_cell_id` | drawer |
| `snap` | omitted | `snapshot_id` | drawer |
| `span` | omitted | `start-end` two integers | drawer |
| `src` | omitted | `map\|receipt` | sources sub-tab (`sourceMode`) |
| `cohort` | omitted | C1 `cohort_id` | peers |
| `peer_metric` | omitted | metric_id | peers |
| `align` | `exclude` | `exclude\|shift_labeled` | peers policy line |
| `peer_n` | `3` | integer | peers |
| `peer_tol` | `45` | integer | peers |
| `peers` | omitted | `1` | alias to open peers tab |

Unknown params ignored. Invalid enum → default. Do not throw.

Replace `setCompany` URL writer (`js:862-865`) with `writeUrl(push)` that serialises the table. `history.pushState(stateSnapshot, '', pathname + search + hash)` on user actions. `history.replaceState` on first hydrate so the landing URL becomes shareable without an extra back stop.

### 6.2 `pushState` / `popstate` / drawer back

- Company change, tab change, as-of change, finding/disclosure/redline select, peer metric change: **push**.
- Typing in the company search: no URL write until select (`js:3224-3243` keep).
- Opening the drawer: **push** a frame with `drawer=1` plus `occ`/`cell`/`snap`/`span`.
- Closing the drawer (Escape, close, scrim): if the current frame has `drawer=1`, `history.back()`; else `replaceState` deleting drawer keys and `closeEvidence(true)`.
- `popstate`: read search params; if `drawer` absent and drawer is open, `closeEvidence(true)` **without** another `history.back`; if `drawer=1`, open drawer on those ids; then apply symbol/tab/as_of/finding. Do not call `setCompany` in a loop.

Reason: A43 “correct deep links and back state”; R3 sheet at 390 must back out to the card.

Hash: continue to preserve unused `location.hash`. Do not store state in hash (archetype text allows hash; this page already uses search — stay on search so `symbol` keeps working).

---

## 7. API-to-view field map (A38)

Rule: **UI exact-value bytes == API value bytes**. Compact is a labelled secondary. Never `Number()` a value that is shown as exact. `compactNumber` / `formatMoney` (`js:247-264`) stay for compact only. Minus sign U+2212 (`js:263`) is allowed only on compact; exact keeps the API ASCII `-` if present.

| Rendered value | Endpoint | Request | Response path | Display | Equality |
|---|---|---|---|---|---|
| Desk as-of date | `GET /api/forensics/health` | n/a | `clocks.broad_source_at` or URL `as_of` | `YYYY-MM-DD` prefix (`js:213-217`) | date prefix of API clock |
| Freshness word | health | n/a | `status` | Current/Stale/Degraded/Unavailable dual-span | enum, not a number |
| Source label | `GET /api/forensics/state` | n/a | `source.label` | as supplied | string bytes |
| Company name | state | n/a | `companies[symbol].name` | as supplied | string bytes |
| Attention count | state | n/a | count of `findings[priority=high]` (`js:986`) | integer | recount of the same array (existing; do not use `payload.summary.high`) |
| Coverage % | state | n/a | `coverage.metrics_pct` | compact percent; ratio 0–1 (`js:269-271`) | compact only |
| Finding title/summary | state / E0 | n/a | `title_en/zh`, `summary_en/zh` | `fieldPair` | string bytes |
| Finding magnitude | state | n/a | `values[0].delta` | compact `formatSigned` | compact only |
| Query compact $ | `POST .../financial/query` | §3.5 | `receipt.nodes[n].value` | `formatMoney(Number)` | compact only; labelled Compact |
| Query exact | same | same | same `.value` | `<code class="ff-exact">` innerText | **bytes == API string** |
| Query unit | same | same | `.unit` | as supplied | string bytes |
| Query state | same | same | `.state` | plain absence copy | enum |
| Occurrence id | same | same | `.provenance.selected_raw_fact.occurrence_id` | `<code title="id">` truncated | title bytes == API id |
| Source span | same | same | `.source_span` | drawer excerpt; not a number | integers as decimal text |
| Revision root/prior/revised | `POST .../financial/revisions` | §3.5 | `revisions[i].root_value` etc. | exact in drawer; compact on face | exact bytes == API |
| Statement cell | `POST .../financial/statements` | `{schema, entity_id, accession}` | `statements[s].rows[r].cells[c].value` | exact in drawer; compact on face | exact bytes == API string/number canonicalised via `String(value)` if JSON number appears — **if the payload uses a JSON number, that is a P1 bug; still print `JSON` canonical decimal by refusing to render and showing unavailable** (floats are forbidden on query; statements may still ship numbers — GAP) |
| Disclosure excerpt | state / E1 | n/a | `display_excerpt` else `source_excerpt` | blockquote | string bytes |
| Peer value | state `peer_cohort` | n/a | `emissions[].rows[].value` | exact / compact split | exact bytes == API |
| Peer exclusion | same | n/a | `exclusions[].code/reason` | mapped glance copy | code in drawer bytes == API |
| Export workbook | `POST .../query.xlsx` (X1) | same body as query | binary xlsx | download | SHA header vs blob (X1 `X-FIF-Response-SHA256` of xlsx bytes) |

Do not client-compute compare `delta` (`js:1522-1525`) for any cell that has a query node. Prefer API `absolute_delta` for revisions. The two-period compare block may keep client delta **only** when both sides are compact-labelled and the exact values remain visible in the drawer. Reason: census A38 called this the divergence.

Packet POST is not required for the page. Do not call it.

---

## 8. EN/ZH copy table

Mechanism: `t()` in `html.j2:1-3`, `pair()` in `js:185-189`. No i18n catalog. No CJK in `title=`. Tooltips: `data-tip-en`/`data-tip-zh`. `aria-label` via `data-label-en/zh` + `updateLocalizedAttributes` (`js:3027-3033`).

| EN | ZH | Location | Budget |
|---|---|---|---|
| Filing forensics | 财报取证 | desk eyebrow | 2 |
| Company | 公司 | picker label | 1 |
| As of | 截止 | as-of label | 2 |
| Latest | 最新 | as-of toggle | 1 |
| Export | 导出 | desk header | 1 |
| Export unavailable | 导出不可用 | disabled export | 2 |
| Sign in to export | 登录后导出 | 401 export | 4 |
| This filing | 本期财报 | overview kicker | 2 |
| What changed | 发生了什么变化 | overview h2 | 4 |
| Why it is worth reviewing, with the source one click away. | 为何值得复核，来源一键可核。 | overview subtitle | 14 |
| Why it matters | 为什么重要 | quick-signal label (reuse drawer `js:2713`) | 3 |
| Open source | 打开来源 | quick-signal CTA | 2 |
| Open the source span for this number | 打开该数字的来源片段 | source-control tip | 10 |
| Source span unavailable | 来源片段不可用 | disabled control | 4 |
| Exact value | 精确数值 | drawer | 2 |
| Compact | 简写 | drawer | 1 |
| Technical ids | 技术编号 | drawer details | 2 |
| What this number is | 这个数字是什么 | cell drawer heading | 5 |
| Original, latest, restated | 原始、截止最新、重述后 | revisions h3 | 4 |
| Original reported | 原始披露 | column | 2 |
| Latest as of cutoff | 截止时点最新值 | column | 5 |
| Restated | 重述后 | column | 1 |
| Same period, three source vintages. A blank column is an absence, not a zero. | 同一期间、三种来源版本。空列是缺失，不是零。 | revisions deck | 18 (subtitle-class; panel not glance) |
| No value at this cutoff | 该截止日无此值 | missing cell | 6 |
| Cannot evaluate | 无法评估 | not_evaluable | 2 |
| No revision in this package | 本数据包中无重述 | empty restated | 6 |
| Revisions temporarily unavailable | 重述服务暂不可用 | 503 | 4 |
| Issuer identity unavailable | 发行人标识不可用 | no entity_id | 3 |
| Period start unavailable | 期间起始日不可用 | no start | 4 |
| Revisions | 重述对照 | tab | 1 |
| Wording | 措辞变化 | disclosures tab (was “What changed”) | 1 |
| Peers | 同业 | tab | 1 |
| Peer set | 同业组 | peers kicker | 2 |
| Who is in, who is out | 谁在组内，谁被排除 | peers h2 | 8 |
| Ranks use only companies that qualify. Exclusions are listed with a reason. | 排名只计入符合条件的公司。排除项均附原因。 | peers deck | 14 |
| Not enough peers to rank | 同业数量不足以排名 | below_min_n | 6 |
| This company | 本公司 | anchor kicker | 2 |
| Same company, another share class | 同一公司的另一类股份 | A35-I1 | 6 |
| No observation in this package | 本数据包中无观察值 | A35-X1 | 6 |
| This metric does not apply | 该指标不适用 | A35-B1 | 6 |
| Statement not rebuilt from this filing | 未能从该财报重建此报表 | A35-W1 | 6 |
| Reporting period does not line up | 报告期未对齐 | A35-P1 | 6 |
| Shifted period | 期间已平移 | A35-P2 | 2 |
| Excluded | 已排除 | unknown code | 1 |
| Peer cohort unavailable | 同业组不可用 | missing payload | 3 |
| Rewind the filing cutoff. Both source and recorded clocks use this day, 23:59:59 UTC. | 回拨财报截止日。来源时钟与入账时钟均使用该日 23:59:59 UTC。 | as-of tip (Tier 2) | 80-word cap |

Keep existing dual-spans. Do not put “falsifier”, “refutation”, `A35-I1`, `latest_restated`, `rawfact_`, or metric slugs on glance.

Period `<option>` text stays `FY{year} Q{quarter}` in both languages (`js:300-305`). `toLocaleString('en-US')` stays. Call out in A43 evidence, do not “fix” in P2.

---

## 9. P0 contract amendments (same PR as UI)

P0 freeze (`P0:FIF_P0_ANALYST_JOURNEYS.md` §0, `FIF_P0_VIEW_CONTRACT.json`): P2 may change the surface only by editing the JSON and its pinning test in the same PR; bump `/v1` when a key is **removed or renamed**. P2 **adds** endpoints and panel copy — keep schema `fundamental_forensics.p0_view_contract/v1` and `frozen_at_commit` `5267c66846e7733bc1eb30edc1524daff51598ca`.

### 9.1 `research/financial_intelligence_fabric/FIF_P0_VIEW_CONTRACT.json`

1. **Journeys** — keep ids J1–J5. Set `status` to `exists` for J1–J3,J5 after P2 ships; J4 `status` = `partial` (URL permalink exists; saved comparison is X2). Replace each `gap` with the residual after this spec. Add `p2_ruling` (extra key allowed: pinning test uses `set >=`).

   | ID | `p2_ruling` |
   |---|---|
   | J1 | Keep review-priority-then-recency (`orderedFindings`); show magnitude on the card (R2). |
   | J2 | Every number is a source control into `#ff-evidence` on occurrence/span; disabled copy when no span (R3). |
   | J3 | Desk as-of re-queries query+revisions; three-column original/latest/restated; default latest (R4). |
   | J4 | Read-only C1 panel; URL params only; no localStorage; X2 owns saved comparisons (R5). |
   | J5 | One Export in the desk header POSTs X1 `query.xlsx` with the current query body; reload is refresh (R6). |

2. **`page_endpoints`** — keep the five GETs. **Append** (do not remove):

```json
{"method": "POST", "path": "/api/forensics/v1/financial/query"},
{"method": "POST", "path": "/api/forensics/v1/financial/revisions"},
{"method": "POST", "path": "/api/forensics/v1/financial/statements"},
{"method": "POST", "path": "/api/forensics/v1/financial/query.xlsx"}
```

3. **`api_not_called_by_page`** — remove the three POSTs the page now calls (`query`, `revisions`, `statements`). Keep packet:

```json
[{"method": "POST", "path": "/api/forensics/v1/financial/packet"}]
```

`query.xlsx` is X1-only; include it in `page_endpoints` so the test expects the JS constant even when the server 404s (disabled control).

4. **`panels`** — add:

```json
{"panel_id": "desk_header", "dom_id": "ff-desk-header", "data_source": "company picker + health clocks + as-of + export", "journeys": ["J1", "J3", "J5"]},
{"panel_id": "revisions", "dom_id": "ff-revisions", "data_source": "POST financial/query x3 policies + POST financial/revisions", "journeys": ["J3"]},
{"panel_id": "peers", "dom_id": "ff-panel-peers", "data_source": "payload.peer_cohort CohortTable.to_dict plus URL policy params", "journeys": ["J4"]}
```

Keep existing panel ids. `company_context` `dom_id` may stay `ff-company-search` (input still unique).

5. **`payload_contract`** — append to lists (do not remove):

   - `company_keys`: `entity_id`
   - `finding_keys`: `occurrence_id` (if JS contains the word)
   - new list **not allowed** without test edit of `PAYLOAD_LISTS`. Put new identifiers into existing lists or update `PAYLOAD_LISTS` in the test to add `query_cell_keys` = `["root_cell_id","occurrence_id","source_span","selected_raw_fact"]`.

6. **`first_viewport`** — rewrite:

```json
"desktop_1440": "At 1440 the first viewport is site nav, desk header (picker + as-of + freshness + export), lead brief What changed / Why it matters, then at most two supporting modules (attention/coverage stats and next-step buttons).",
"mobile_390": "At 390 the first swipe is nav + desk header + lead brief #ff-quick-signal.",
"measured": false
```

### 9.2 `tests/test_fundamental_forensics_p0_view_contract.py` (P0 SHA)

Edits required in the **same PR**:

| Test | Change |
|---|---|
| `test_manifest_parses_and_schema_frozen_commit_shape` | keep schema `/v1` and freeze sha `5267c668…` |
| `test_page_endpoints_in_js_and_registered_gets` | allow `method in {GET, POST}`; GET paths still in `@router.get`; POST paths in `@router.post` **or** (for `query.xlsx`) asserted present in JS even if absent from BASE `app/forensics.py` — split: if path ends with `.xlsx`, JS-only check |
| `test_api_not_called_by_page_are_posts_absent_from_js` | expect **one** leftover (`/packet`); assert that path is absent from JS |
| `test_panel_dom_ids_occur_once_in_template` | new panels must exist once |
| `PAYLOAD_LISTS` | add `query_cell_keys` if used |

`test_five_journeys_in_masterplan_order` still requires `p2_question`; keep the original questions, add `p2_ruling`.

P0 doc sentence “P2 must amend the JSON and this test in the same PR to start calling them” (`FIF_P0_ANALYST_JOURNEYS.md` §4) is the start gate. No financial POST in JS until this amendment lands in the same commit as the fetch helper.

---

## 10. Tests to add or change

### 10.1 Paired plain-copy site sync

`templates/fundamental_forensics.js` and `templates/fundamental_forensics.css` **are paired** with `site/fundamental_forensics.js` and `site/fundamental_forensics.css` (`scripts/check_template_site_sync.py:17-24,52-54`; tracked at BASE). `.j2` is a render input, not a pair. `site/fundamental_forensics.html` is builder output (`scripts/build_fundamental_forensics.py:914-945` per census).

Writer **must** ship byte-identical `site/` copies of the js/css in the same PR (`python3 -m scripts.check_template_site_sync --fix` after templates change). Sparse checkouts skip missing `site/` files — a full (non-sparse) tree is required for this step (§11).

### 10.2 By file

| File | Behaviour to add/change |
|---|---|
| `tests/test_fundamental_forensics_p0_view_contract.py` | §9.2 |
| `tests/test_fundamental_forensics_ui.py:29-43` | eight tabs including `ff-tab-peers` / `ff-panel-peers`; still unique ids; css/js stamps |
| `:46-65` | drop assert `"Spot the changes that matter."` and `"Pick a company. We compare…"`; assert `"What changed"`, `"Why it matters"`, `id="ff-desk-header"`, `id="ff-asof-input"`, `id="ff-export-btn"`; keep overview ids |
| `:70-80` | disclosures tab visible copy `"Wording"` / `"措辞变化"`; honesty sentence unchanged |
| `:105-110` | still ≥20 `l-en`/`l-zh`; new ids unique |
| `:115-191` | JS contract tokens: `FINANCIAL_QUERY_URL`, `FINANCIAL_REVISIONS_URL`, `FINANCIAL_STATEMENTS_URL`, `FINANCIAL_QUERY_XLSX_URL`, `ff-source-control`, `Source span unavailable`, `cache:'no-store'`, `noopener noreferrer`; **no** `localStorage` / `sessionStorage` |
| `:253-283` | desk header in first-viewport selectors; keep drawer/sheet breakpoints, `:focus-visible`, reduced motion |
| new `test_source_control_disabled_copy_is_bilingual` | template/JS contains both `Source span unavailable` and `来源片段不可用` |
| new `test_desk_header_has_one_asof_and_export` | one `#ff-asof-input`, one `#ff-export-btn`, no third `<header>` besides site nav + desk |
| `tests/test_fundamental_forensics_page.py` | public gate still has no company names; no occurrence ids in anonymous HTML |
| `tests/fundamental_forensics_cta_contract.test.mjs` | CTA still opens `#ff-evidence`; now with `ff-source-control` |
| new `tests/fundamental_forensics_url_state.test.mjs` | `writeUrl` round-trip for symbol/tab/as_of/drawer/occ; `popstate` closes drawer |
| new `tests/fundamental_forensics_a38_exact.test.mjs` | given a fixture node `value: "94936000000"`, `.ff-exact` textContent === that string |
| `tests/test_i18n_attribute_guard.py` | add `fundamental_forensics.html.j2` to `PAGES` |
| `scripts/check_title_i18n.py` | no change required if JS `title=` remains id-only; add a page test that scans `fundamental_forensics.js` for `title=` CJK |
| `scripts/check_design_system.py` | run `--mode enforce-added --diff-file` on the PR diff; no new hex, no new font stack |
| `scripts/check_runtime_style_injection.py` | count must not rise; no `document.createElement('style')` |
| `scripts/check_ui_visual_evidence.py` | new `mockups/evidence/fundamental_forensics_p2/EVIDENCE.yml` owning `templates/fundamental_forensics.css` and JS injection-free; 8-cell matrix |
| `scripts/check_template_site_sync.py` | pair green |
| `docs/site_semantics/fundamental_forensics.md` | new (R7); every glance stat defined in one plain sentence EN+ZH |

### 10.3 Glossary file (R7)

`docs/site_semantics/fundamental_forensics.md` — one heading per glance stat: What changed, Why it matters, Need attention, Metrics compared, Original reported, Latest as of cutoff, Restated, Source span, Compact vs exact, Peers in/out. No kernel names in the first sentence.

---

## 11. Evidence-capture plan

### 11.1 Full (non-sparse) checkout — required steps

Sparse worktrees omit `data/`, `site/`, `mockups/`, `verify_shots/` (`CLAUDE.md` sparse law). These P2 steps **need a full checkout**:

1. Pair `site/fundamental_forensics.{js,css}` and rebuild `site/fundamental_forensics.html` via `python3.12 scripts/build_fundamental_forensics.py`.
2. Read loopback state `data/fundamental_forensics/private/state.json.gz`.
3. Commit `mockups/evidence/fundamental_forensics_p2/` PNGs + `EVIDENCE.yml` (`scripts/check_ui_visual_evidence.py:13-21`).

Jinja/JS unit tests run on a sparse tree.

### 11.2 Local golden render

```bash
# full tree, FIF_FINANCIAL_DATASET_MODE default/golden
python3.12 scripts/build_fundamental_forensics.py
# serve site/ as today (existing preview / uvicorn app.main)
# entitled session OR loopback:
open 'http://127.0.0.1:<port>/fundamental_forensics.html?symbol=AAPL'
```

Loopback JS uses `/data/fundamental_forensics/private/state.json.gz` (`js:6-8`) with `cache:'no-store'`. Financial POSTs still need the FastAPI app + golden provider. Capture entitled and gated states separately.

### 11.3 8-cell matrix (A43)

Theme × lang × viewport, each cell exercises A42 glance, A44 source click, A43 keyboard, A24 gate (or entitled workbench), A38 exact vs compact.

| # | data-theme | data-lang | viewport | Must show |
|---|---|---|---|---|
| 1 | dark | en | 1440×900 | nav + desk header + lead brief + ≤2 modules; sticky `#ff-evidence`; exact in drawer |
| 2 | dark | zh | 1440 | ZH spans visible (`theme.css:513-514`); no CJK in `title=` |
| 3 | light | en | 1440 | white desk header, hairlines, shadow not glow |
| 4 | light | zh | 1440 | CJK unclipped in h2 / quick-signal / tabs |
| 5 | dark | en | 390×844 | lead brief in first swipe; sheet on source click; Escape restores |
| 6 | dark | zh | 390 | disabled pager/select copy correct |
| 7 | light | en | 390 | light sheet; gate signin **and** entitled workbench captured |
| 8 | light | zh | 390 | back from drawer restores tab+finding via URL |

Plus a ninth pass (same eight or extra `force_state` cells): keyboard-only tablist + drawer trap; 401/403/503 gate (`js:625-651`); export disabled; restated absence; source-span disabled.

Capture via `scripts/capture_page_evidence.py` (schema `mastermind.p0_evidence.v2`). Receipt:

```yaml
schema: mastermind.page_evidence_receipt.v1
changed_paths:
  - templates/fundamental_forensics.html.j2
  - templates/fundamental_forensics.js
  - templates/fundamental_forensics.css
manifest: mockups/evidence/fundamental_forensics_p2/manifest.json
```

A screenshot does not prove A38/A44 (`FIRST_VERTICAL_PLAN.md:102`). Pair PNGs with the Node exact-value test and a recorded network log of the POST body.

Hover/focus: `:focus-visible` already at `css:1883-1886`; capture one keyboard-focus cell per theme (`check_ui_visual_evidence.py:8-9`).

---

## 12. Writer sequencing (ordered commits)

Each commit small enough to review. No `app/forensics.py`. No `engine/**`.

| # | Commit | Files | Notes |
|---|---|---|---|
| 1 | Amend P0 contract + pinning test | `research/financial_intelligence_fabric/FIF_P0_VIEW_CONTRACT.json`, `tests/test_fundamental_forensics_p0_view_contract.py` | Gate for calling financial POSTs |
| 2 | Desk header + lead brief markup/CSS | `templates/fundamental_forensics.html.j2:25-269`, `templates/fundamental_forensics.css` desk/overview rules | A42; R8 dark/light treatments in the same CSS |
| 3 | URL state + popstate/drawer back | `templates/fundamental_forensics.js` `state`, `writeUrl`, `popstate` | No visual dependency |
| 4 | Source-control helper + wrap statements/findings/disclosures/redlines | `templates/fundamental_forensics.js` renderers; CSS `.ff-source-control` | R3; disabled copy |
| 5 | As-of control + three-policy query/revisions fetch + revisions table | JS fetch helper + `renderRevisions`; html `#ff-revisions` | R4; A38 exact node |
| 6 | Statement tree render from statements POST | `#ff-statements` | S0 as-reported labels; source_receipt spans |
| 7 | Peers tab + exclusion copy + URL params | html/js/css | R5; empty state if no blob |
| 8 | Export button POST xlsx | JS only | R6; disabled states |
| 9 | Copy/i18n + glossary | remaining `t()`/`pair()`; `docs/site_semantics/fundamental_forensics.md`; `test_i18n_attribute_guard.py` | R7 R9 |
| 10 | Tests + site pair + evidence | §10–11 | full checkout for site + mockups |

After 2, 4, 5, 7, 8: run `python3 -m scripts.check_template_site_sync --fix`.

Do not retune golden SHA literals in engine tests. Do not add `format=` on JSON routes.

---

## GAPS (P1 follow-ups and unverifiable)

1. **`company.entity_id` missing** from state (`build_fundamental_forensics.py` has no `entity_id`; P0 `company_keys` omit it). P2 cannot lawfully mint `ISS:` from ticker. P1/state must add `entity_id`.
2. **Period `start` missing** on `company.periods` (`_clean_period` census). Query admission requires `start` (`query_service.py:60`). P1 or statements columns must supply `{kind,start,end,label}`.
3. **`contract_liabilities` not in S1 core 40.** Leave on the state table; do not POST it.
4. **Statement cell `value` may not be canonical decimal text** (`statement_graph.py:926` uses `normalized_value`). If JSON numbers/floats appear, P2 shows unavailable rather than `Number()`. P1 should emit decimal text.
5. **Finding state objects lack `occurrence_id` / `source_span`** (census §4.2). P2 matches via query nodes; unmatched → disabled span. P1 should attach them.
6. **No peer HTTP route** (C1 is a pure table builder). P2 reads `payload.peer_cohort`. C1/P1 should land that blob or a later entitled GET. Policy fields are not in `CohortTable.to_dict()` — URL carries them.
7. **`query.xlsx` absent at BASE**; present on X1 `7c0582de`. Export stays disabled until X1 merges.
8. **First-viewport fold unmeasured** (`FIF_P0_VIEW_CONTRACT.json` `measured: false`; sparse, no browser in this lane).
9. **`site/` bytes** not readable in this sparse tree; pairing cited from git ls-tree + checker docstring.
10. Production health clock formats (Z vs offset) unverified live; writer must pass through the health string when Latest is selected.

---

## DEVIATIONS

None from the commissioning packet. Inferences are labeled in GAPS. Tab visible copy “What changed” on disclosures is renamed to “Wording” so glance owns A42; tab **ids** unchanged until peers adds an eighth.
)

---

## SEAT ADJUDICATION (2026-10-12 ~10:35Z, Meta-CEO seat) — FROZEN with amendments AM1–AM6

The spec above is FROZEN for the P2 writer. Writer implements; amendments below override any conflicting line above.

- **AM1 (data gaps → P1-b, never P2).** GAPS 1, 2, 4, 5, 6 (`company.entity_id`, period `start`, canonical decimal-text cell values, finding `occurrence_id`/`source_span`, `payload.peer_cohort` blob incl. policy fields) are owned by the P1-b data-contract lane, not P2. Until each lands, P2 renders the explicit unavailable/disabled state named in this spec — never mints `ISS:` from a ticker, never `Number()`s a float, never fabricates a span or a peer row.
- **AM2 (light shadow).** Prefer an existing `theme.css` shadow/elevation token for the light desk header if one exists; only if none exists may the rgba literal in §1.4 LIGHT TREATMENT ship, and it must pass `scripts/check_design_system.py --mode enforce-added`. No new hex anywhere.
- **AM3 (export).** P2 starts only after X1 #8949 merges, so `query.xlsx` exists at P2's base; the export-disabled state is for unauthorised/gated sessions only, not a standing fallback.
- **AM4 (tab rename).** DEVIATION accepted: disclosures tab visible copy "What changed" → "Wording / 措辞"; ids unchanged.
- **AM5 (evidence).** The 8-cell matrix (dark/light × EN/ZH × 1440/390) is a NOT-DONE-UNLESS for the P2 PR body; fold measurement replaces `measured: false` in `FIF_P0_VIEW_CONTRACT.json` with the measured value in the same PR.
- **AM6 (commit the spec).** Commit this frozen file as `research/financial_intelligence_fabric/FIF_P2_DESIGN_SPEC.md` in P2's first commit.
- **AM7 (1440 tab rail in the first viewport; seat ruling 10-12 18:5xZ after the P2 changed-cell re-review).** Measured at 1440×900, the glance tier (desk header 104–245, stats 321–341, lead brief 370–502, next steps ≤594) is complete above the tab rail (633–694 EN / 605–666 ZH). Moving the rail below 900px would take roughly 200px of padding or an inflated glance tier, and the density law forbids both. The §1.1 1440 clause "Tab bar and panels start below the fold" is therefore amended: at ≥1100px the tab rail and the top of the active panel MAY be visible inside the first viewport, directly below the complete glance tier, as navigation chrome. They are not first-viewport modules: they are neither counted nor required to be in or out of the fold, and every glance-tier module must be fully understandable without them. At 390 §1.1 is UNCHANGED: the tab bar and panels start below the first swipe. `FIF_P0_VIEW_CONTRACT.json` `first_viewport.measured.desktop_1440` must cite AM7 by name, must not list `tabs` as a first-viewport module, and its `meets_contract` is judged under the amended clause only.
