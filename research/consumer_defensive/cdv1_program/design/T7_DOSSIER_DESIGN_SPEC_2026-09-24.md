# CDV-1 Task 7 — Demand and Earnings Dossier Design Specification

STATUS: PROPOSED — seat adjudication pending

Operation: `gmi-consumer-defensive-research-20260923-sol-001`

Commissioned by: Fable Meta-CEO seat

## 1. Placement and mount

**Status:** fixed; no builder judgment.

### 1.1 Theme Tracker compact entry

`templates/state_of_themes.html.j2` currently renders every theme drawer from `.drawer` / `.drawer-grid` at lines 486–489, and the drawer’s full-width cell idiom is `.drawer-sec.full` (`grid-column:1/-1`) at lines 180–188. The Staples row is runtime-selected by `data-theme-id="us_sector_staples"` on `.theme-row` at lines 459–463; it is not one of the eighteen currently rendered foresight themes, so the build must add that row only through the existing theme-state owner rather than invent a display theme. The accepted writer adds one and only one full-width cell as the **final child of that row’s `.drawer-grid`**, immediately before its closing line:

```jinja
{% if th.theme_id == 'us_sector_staples' %}
<div class="drawer-sec full econ-dossier-cell">
  <button class="econ-dossier-toggle" type="button" aria-expanded="false" aria-controls="economic-dossier-staples">…copy from §5…</button>
  <section id="economic-dossier-staples" data-economic-root hidden></section>
</div>
{% endif %}
```

No other drawer cell, theme row, heading, page shell, filter, navigation, or layout may be changed. The button is a real `<button>` so drawer expansion can ignore clicks originating on interactive descendants exactly as the current handler already ignores links (`state_of_themes.html.j2:688–695`).

The collapsed cell budget is **one 40 px effective touch-target row** (`min-height:40px; padding:var(--sp-2) 0 var(--sp-3)`), containing only the button’s one-line label. It adds no dashboard height while collapsed. On expand, the nested section becomes the dossier’s only full-width read tier; on collapse it is destroyed. This is the Theme Tracker compact link called for by the design’s shared-UI section (`2026-09-23-consumer-defensive-economic-dossier-design.md:135–137`), not a second dossier host.

### 1.2 XLP-only sector slot

`templates/sector.html.j2` has no `<section>` today; its accepted panels are sibling `<div class="panel">` blocks. The XLP route is the generated `s.fund == "XLP"` render, not a new route. Immediately **after the existing chart panel that closes at `templates/sector.html.j2:309`** and before the conditional accumulation panel at line 311, add exactly this conditional wrapper:

```jinja
{% if s.fund == 'XLP' %}
  {% include "earnings_wire/_economic_dossier.html.j2" %}
{% endif %}
```

The partial’s root must be `<section class="panel econ-dossier" data-economic-root data-economic-state="unavailable" hidden>`. There is exactly one root per rendered page. The hook is absent on every other sector fund. It creates no Consumer Defensive identity, header, hero, page, score, rank, timing change, or height change while hidden. This honors the plan’s warning that `/sectors/XLP.html` must not become a global identity (`2026-09-23 CDV-1 implementation plan:491–493`). No STSI/F04 or PR #7777 path is touched.

### 1.3 Mount contract and lifecycle

The build exports one function from `templates/earnings_wire/earnings-economic.js`:

```javascript
mountEarningsEconomicDossier(root, {issuer, fetchAuthenticated, onAuthChange}) → destroy()
```

Binding and lifecycle are fixed:

- `root`: the one `[data-economic-root]` element. Reject and return a no-op `destroy` if absent, not an `Element`, or already mounted (mark with `data-economic-mounted="1"`).
- `issuer`: required object `{ticker:"PG", nativeIssuerId:"<owner-bound value>"}`. The browser never resolves ticker to issuer identity and never calls a GMI graph API.
- `fetchAuthenticated`: required `(url, init={}) => Promise<Response>`. It must use the existing site session client (`sb.auth.getSession()` → session access token → `Authorization: Bearer <token>`), the exact authenticated idiom pinned by `tests/test_earnings_api.py:258–269`. The component never imports Supabase, stores a token, refreshes auth, or creates a second client.
- `onAuthChange`: required `(listener: ({epoch}) => void) => unsubscribe`. The host supplies a monotonically increasing auth epoch. The component captures each fetch epoch and discards all results when the captured epoch differs.
- On call, remove `hidden`, set `data-economic-state="loading"`, render the fixed loading skeleton, then request `/api/earnings/v1/economic/PG`.
- **Theme Tracker:** mount on the first expansion of the Staples drawer button; destroy on collapse, drawer re-filtering that hides the row, page teardown, or logout.
- **XLP page:** mount once after DOM ready; destroy only on page teardown or logout.
- `destroy()` is idempotent. It aborts the outstanding request, increments the internal epoch, closes and removes the evidence dialog if mounted, restores focus to the invoking evidence button if that button is still connected, removes all source-derived children, restores the fixed unavailable state, removes `data-economic-mounted`, and unsubscribes. It never removes the host partial/cell on XLP and never removes the Theme Tracker cell itself.
- Logout and auth epoch change always take the destroy/clear path, then show the unentitled state. A later login remounts through the host lifecycle rather than silently reusing stale private data.

## 2. Information architecture

### 2.1 Glance tier

The first visible row is `[data-economic-state]`, containing one state chip and one plain stance sentence:

- State vocabulary and display binding: `up_to_date`, `newer_source_pending`, `currentness_unverified`, `loading`, `unavailable`, `unentitled`, `unsupported_schema`, `error`.
- Stance copy is server-owned and selected by interpretation state, never inferred in the browser. Each sentence is ≤ 14 words in EN and ≤ 20 Chinese characters in ZH.
- The neutral/default stance is **“Watch the evidence — do not chase it.” / “看证据，勿追。”** It answers the doctrine’s “so what” law without making a recommendation (`docs/DESIGN_DOCTRINE.md:40–47`).
- The compact Theme Tracker collapsed label is only the fixed action from §5, never a live financial claim.

### 2.2 Read tier: two-column facts table

The read tier has two subsections, **Demand** and **Earnings**, rendered as one semantic `<table>` each with the same five-column geometry:

| Column | Content | Fixed rule |
|---|---|---|
| Label | Plain metric label from §5 | Bilingual source-owned label |
| Period | Fiscal interval/label | `data-economic-period`; one period per row |
| Basis | `reported` / `organic` / `core` | `data-economic-basis`; fixed text from §5 |
| Value | Server-rendered value + unit | `--num`/tabular; no browser arithmetic |
| Evidence | One icon-only accessible button | `data-economic-evidence`; opens pinned drawer |

Demand rows in exact order: reported sales growth; organic sales growth (company-defined); total volume growth when the owner marks it pure; organic volume growth when the owner marks it pure; combined volume/mix only when the source names that mixed basis; price contribution; mix contribution; FX contribution; other contribution. Never relabel combined volume/mix as volume.

Earnings rows in exact order: reported diluted EPS; prior reported diluted EPS; reported EPS growth; core EPS; prior core EPS; core EPS growth; core reconciliation context. Reported and core EPS remain separate rows and separate definitions; neither is labeled better, cleaner, or recurring.

Optional segment rows are never mixed into either two-column table. They are rendered as a collapsed `<details>` after the Demand table only when admitted; the summary is “Segment detail”, and the same table columns/rules apply. Five segments do not imply sector participation.

Maximum selected display remains 24 observations, 24 comparison rows, and four source workspace revisions (`2026-09-23 CDV-1 implementation plan:13–16`). If more arrive, render unavailable rather than choosing favorites.

### 2.3 Findings

The findings list is ordered by the server’s fixed rule order and rendered as plain sentences; rule IDs are machine attributes only and never visible:

1. `reported_vs_organic_difference`
2. `positive_organic_nonpositive_pure_volume`
3. `reported_vs_core_earnings_disagreement`
4. `incomplete_margin_to_cash_bridge`
5. `segment_scope_limitation`
6. `missing_consensus`

Each `<li data-economic-rule="...">` carries the exact EN/ZH wording in §5. The browser never combines rows, selects a different wording, hides a present rule, or adds a recommendation. The findings list is visible in the read tier; it is not a tooltip, because every number needs its plain meaning (`docs/DESIGN_DOCTRINE.md:75–80`).

### 2.4 Missing context

A separate list carries each `missing_context` item using only the fixed EN/ZH labels in §5. Missing licensed consensus and optional segments are absence statements, not failures and never a beat/miss. The list may be empty; in that state show the fixed “Nothing required is missing.” line once. This follows the design rule that absent optional context remains visible without dominating the useful explanation (`2026-09-23 economic dossier design:137–139`).

### 2.5 Currentness and clocks footer

Exactly one footer at the bottom states, in order: fiscal period label; source acceptance/publication date from the source clock; accepted generation pin; currentness state from `selection`. It never repeats the same timestamp on every row. Currentness wording is fixed in §5 and follows the design’s separate-clock law (`2026-09-23 economic dossier design:115–123`).

### 2.6 Evidence drawer

Each evidence button opens one page-level dialog. Its content is the exact permitted inert context returned for that fact:

- Source span text (displayed as inert text, never a raw document).
- Header label and period label.
- Short digest, displayed in a fixed monospace receipt line.
- Generation pin plus manifest digest and record digest taken from the displayed response.
- If supplied by the owner: the bounded reconciliation context and precision note.
- Close button.

The drawer never receives an object key, credential, URL as clickable markup, whole source body, or retired/restricted evidence. Opening pins the generation/manifest/record digests from the displayed response; a changed current pointer cannot redirect it (`2026-09-23 CDV-1 implementation plan:174–181`).

## 3. Exact markup

Create only this Jinja partial: `templates/earnings_wire/_economic_dossier.html.j2`. Its initial server skeleton is fixed below. Host-specific IDs may be suffixed by Jinja only when a page has two roots; the accepted mounts here have one, so use these IDs literally.

```jinja
<section class="panel econ-dossier"
         id="economic-dossier"
         data-economic-root
         data-economic-state="unavailable"
         data-economic-mounted=""
         aria-labelledby="economic-dossier-title"
         hidden>
  <div class="econ-dossier-head">
    <div>
      <p class="econ-dossier-eyebrow"><span class="l-en">Consumer research</span><span class="l-zh">消费研究</span></p>
      <h2 id="economic-dossier-title">
        <span class="l-en">Demand and earnings evidence</span>
        <span class="l-zh">需求与盈利证据</span>
      </h2>
    </div>
    <p class="econ-dossier-stance">
      <span class="econ-state-chip" data-economic-state-chip></span>
      <span class="econ-stance-text" data-economic-stance></span>
    </p>
  </div>

  <div class="econ-loading" data-economic-loading hidden>
    <span class="skel econ-skel-title"></span>
    <span class="skel econ-skel-row"></span>
    <span class="skel econ-skel-row"></span>
    <span class="skel econ-skel-row"></span>
    <p class="sr-only"><span class="l-en">Loading the latest accepted evidence.</span><span class="l-zh">正在加载最新已采纳证据。</span></p>
  </div>

  <div class="econ-content" data-economic-content hidden>
    <section class="econ-table-group" aria-labelledby="econ-demand-title">
      <div class="econ-group-head">
        <h3 id="econ-demand-title"><span class="l-en">Demand</span><span class="l-zh">需求</span></h3>
        <p class="econ-group-note"><span class="l-en">Organic sales are a company-defined revenue measure, not household consumption.</span><span class="l-zh">有机销售额是公司定义的收入口径，不等于家庭消费。</span></p>
      </div>
      <div class="econ-table-scroll">
        <table class="econ-table">
          <thead><tr>
            <th scope="col"><span class="l-en">Item</span><span class="l-zh">项目</span></th>
            <th scope="col"><span class="l-en">Period</span><span class="l-zh">期间</span></th>
            <th scope="col"><span class="l-en">Basis</span><span class="l-zh">口径</span></th>
            <th scope="col"><span class="l-en">Value</span><span class="l-zh">数值</span></th>
            <th scope="col"><span class="l-en">Evidence</span><span class="l-zh">证据</span></th>
          </tr></thead>
          <tbody data-economic-demand></tbody>
        </table>
      </div>
    </section>

    <details class="econ-segments" data-economic-segments hidden>
      <summary><span class="l-en">Segment detail</span><span class="l-zh">分部明细</span></summary>
      <div class="econ-table-scroll">
        <table class="econ-table">
          <thead><tr>
            <th scope="col"><span class="l-en">Item</span><span class="l-zh">项目</span></th>
            <th scope="col"><span class="l-en">Period</span><span class="l-zh">期间</span></th>
            <th scope="col"><span class="l-en">Basis</span><span class="l-zh">口径</span></th>
            <th scope="col"><span class="l-en">Value</span><span class="l-zh">数值</span></th>
            <th scope="col"><span class="l-en">Evidence</span><span class="l-zh">证据</span></th>
          </tr></thead>
          <tbody data-economic-segment-rows></tbody>
        </table>
      </div>
    </details>

    <section class="econ-table-group" aria-labelledby="econ-earnings-title">
      <div class="econ-group-head">
        <h3 id="econ-earnings-title"><span class="l-en">Earnings</span><span class="l-zh">盈利</span></h3>
        <p class="econ-group-note"><span class="l-en">Reported and core EPS use different definitions.</span><span class="l-zh">报告口径与核心每股收益采用不同定义。</span></p>
      </div>
      <div class="econ-table-scroll">
        <table class="econ-table">
          <thead><tr>
            <th scope="col"><span class="l-en">Item</span><span class="l-zh">项目</span></th>
            <th scope="col"><span class="l-en">Period</span><span class="l-zh">期间</span></th>
            <th scope="col"><span class="l-en">Basis</span><span class="l-zh">口径</span></th>
            <th scope="col"><span class="l-en">Value</span><span class="l-zh">数值</span></th>
            <th scope="col"><span class="l-en">Evidence</span><span class="l-zh">证据</span></th>
          </tr></thead>
          <tbody data-economic-earnings></tbody>
        </table>
      </div>
    </section>

    <section class="econ-findings" aria-labelledby="econ-findings-title">
      <h3 id="econ-findings-title"><span class="l-en">What the numbers say</span><span class="l-zh">数字说明了什么</span></h3>
      <ul class="econ-finding-list" data-economic-findings></ul>
    </section>

    <section class="econ-missing" aria-labelledby="econ-missing-title">
      <h3 id="econ-missing-title"><span class="l-en">Context not available</span><span class="l-zh">缺失的背景</span></h3>
      <ul class="econ-missing-list" data-economic-missing></ul>
    </section>

    <footer class="econ-clock" data-economic-clock></footer>

    <nav class="econ-links" data-economic-links aria-label="Company and research links"></nav>
  </div>

  <div class="econ-state" data-economic-state-panel hidden>
    <p class="econ-state-line"></p>
    <p class="econ-state-why"></p>
  </div>

  <div class="econ-drawer-scrim" data-economic-scrim hidden></div>
  <section class="econ-drawer"
           id="economic-evidence-drawer"
           role="dialog"
           aria-modal="true"
           aria-labelledby="economic-evidence-title"
           data-economic-evidence-drawer
           hidden>
    <header class="econ-drawer-bar">
      <h2 id="economic-evidence-title">
        <span class="l-en">Source evidence</span><span class="l-zh">来源证据</span>
      </h2>
      <button class="econ-drawer-close" type="button" data-economic-evidence-close>
        <span class="l-en">Close</span><span class="l-zh">关闭</span>
      </button>
    </header>
    <dl class="econ-drawer-meta">
      <div><dt><span class="l-en">Header</span><span class="l-zh">表头</span></dt><dd data-economic-evidence-header></dd></div>
      <div><dt><span class="l-en">Period</span><span class="l-zh">期间</span></dt><dd data-economic-evidence-period></dd></div>
      <div><dt><span class="l-en">Generation</span><span class="l-zh">生成版本</span></dt><dd><code data-economic-evidence-generation></code></dd></div>
      <div><dt><span class="l-en">Manifest</span><span class="l-zh">清单</span></dt><dd><code data-economic-evidence-manifest></code></dd></div>
      <div><dt><span class="l-en">Record</span><span class="l-zh">记录</span></dt><dd><code data-economic-evidence-record></code></dd></div>
    </dl>
    <blockquote class="econ-source-text" data-economic-evidence-text></blockquote>
    <p class="econ-receipt"><code data-economic-evidence-digest></code></p>
    <p class="econ-precision" data-economic-evidence-precision></p>
  </section>
</section>
```

Dynamic rows are created only with DOM APIs and this exact shape:

```html
<tr data-economic-period="SERVER_PERIOD" data-economic-basis="reported|organic|core">
  <th scope="row" class="econ-cell-label">SERVER_LABEL</th>
  <td class="econ-cell-period">SERVER_PERIOD</td>
  <td><span class="econ-basis">SERVER_BASIS</span></td>
  <td class="econ-value">SERVER_VALUE_AND_UNIT</td>
  <td>
    <button class="econ-evidence-button"
            type="button"
            data-economic-evidence
            data-economic-fact-id="SERVER_FACT_ID"
            aria-label="OPEN_EVIDENCE_FIXED_COPY">
      <span class="l-en">Evidence</span><span class="l-zh">证据</span>
    </button>
  </td>
</tr>
```

Required finding item:

```html
<li data-economic-rule="SERVER_RULE_ID">SERVER_FIXED_EN_OR_ZH_SENTENCE</li>
```

Accessibility requirements are fixed: real table semantics; heading order is page `h1` → panel `h2` → group `h3`; `role="dialog"` plus `aria-modal="true"`; initial focus on the close button; Escape and scrim click close; focus returns to the invoking evidence button; `hidden` and `aria-expanded` stay synchronized on all disclosure triggers; every interactive target has an effective target of at least 40×40 px (`research/MASTER_PRODUCT_DESIGN_SYSTEM_V1.md:636–646`). No translated text is placed in `title=` attributes.

## 4. Exact CSS

**Owning file:** append to `templates/earnings_wire/earnings-wire.css`; import/link it only on the two accepted hosts. No token definition, page style block, third stylesheet, or runtime style text may be created.

### 4.1 Token status and allowed references

`theme.css` is the only token source (`research/MASTER_PRODUCT_DESIGN_SYSTEM_V1.md:93–109`). It directly defines the complete type scale and all color/surface/ink/font/shadow/glass/button tokens used here. DS-PR-0 proposes spacing, radius, motion, and gap tokens, but those are not yet in `theme.css :root`; therefore the CSS uses the exact shipped fallback idiom already established by `.mx-empty`, `.skel`, `.mx-error`, and canonical `theme.css` rules (`templates/theme.css:2014–2064`). A fallback is not a new token family and becomes inert when DS-PR-0 lands.

The allowed value vocabulary is exactly:

- Type: `var(--fs-h2)`, `var(--fs-h3)`, `var(--fs-md)`, `var(--fs-sm)`, `var(--fs-label)`, `var(--fs-micro)`.
- Surfaces/lines/text: `var(--bg)`, `var(--panel)`, `var(--panel2)`, `var(--line)`, `var(--text)`, `var(--muted)`.
- Semantic text: `var(--ink-ok)`, `var(--ink-warn)`, `var(--ink-act)`, `var(--ink-link, var(--link))`, `var(--ink-info)`.
- Font/numerals: `var(--font-ui)`, `var(--font-mono)`, `var(--num, var(--font-mono))`.
- Elevation: `var(--card-shadow)`, `var(--popover-shadow)`, `var(--glass-bg)`, `var(--glass-brd)`, `var(--glass-blur)`, `var(--glass-shadow)`.
- Buttons: `var(--gbtn-bg)`, `var(--gbtn-bg-hover)`, `var(--gbtn-brd)`, `var(--gbtn-brd-hover)`, `var(--gbtn-sheen)`.
- Spacing fallback values, copied verbatim from the specimen: `var(--sp-1,4px)` … `var(--sp-8,44px)` only.
- Radius fallback values: `var(--r-ctl,8px)`, `var(--r-btn,10px)`, `var(--r-card,12px)`, `var(--r-panel,14px)`, `var(--r-pill,999px)`.
- Motion fallback values: `var(--t-fast,.16s)`, `var(--t-med,.2s)`, `var(--t-slow,.55s)`, `var(--ease-std,ease)`, `var(--ease-lift,cubic-bezier(.2,.7,.3,1))`; grid gap may use `var(--gap-grid,18px)`.
- Fixed geometry: `0`, `1px`, `2px`, `3px`, `40px`, `44px`, `48px`, `50%`, `1fr`, `minmax(0,1fr)`, `100%`, `60dvh`, `72px`, `96px`, `120px`, `144px`, `168px`, `176px`, `420px`, `520px`, `640px`, `760px`, `820px`, `900px`, `1200px`, and `calc(100% - var(--sp-4,16px))`. Numeric lexical values and layout ratios are not colors or design tokens.
- Theme-specific selectors may change only which existing tokens/fallback values are selected; they may not introduce another value.

### 4.2 Exact declarations

```css
.econ-dossier{position:relative;display:grid;gap:var(--sp-4,16px);margin:var(--gap-grid,18px) 0;padding:var(--sp-4,16px);background:var(--panel);border:1px solid var(--line);border-radius:var(--r-panel,14px);box-shadow:var(--card-shadow)}
.econ-dossier[hidden]{display:none}
.econ-dossier-head{display:flex;align-items:flex-start;justify-content:space-between;gap:var(--sp-4,16px)}
.econ-dossier-eyebrow{margin:0;color:var(--muted);font:600 var(--fs-label)/1.2 var(--font-ui);letter-spacing:.08em;text-transform:uppercase}
.econ-dossier h2{margin:var(--sp-1,4px) 0 0;color:var(--text);font:700 var(--fs-h2)/1.25 var(--font-ui)}
.econ-dossier-stance{display:flex;flex-wrap:wrap;align-items:center;gap:var(--sp-2,8px);margin:0}
.econ-state-chip{display:inline-flex;align-items:center;min-height:24px;padding:var(--sp-1,4px) var(--sp-2,8px);border:1px solid var(--line);border-radius:var(--r-pill,999px);background:var(--panel2);color:var(--muted);font:600 var(--fs-label)/1.2 var(--font-ui)}
.econ-dossier[data-economic-state="up_to_date"] .econ-state-chip{color:var(--ink-ok)}
.econ-dossier[data-economic-state="newer_source_pending"] .econ-state-chip,.econ-dossier[data-economic-state="currentness_unverified"] .econ-state-chip,.econ-dossier[data-economic-state="unsupported_schema"] .econ-state-chip,.econ-dossier[data-economic-state="error"] .econ-state-chip{color:var(--ink-warn)}
.econ-dossier[data-economic-state="unentitled"] .econ-state-chip,.econ-dossier[data-economic-state="unavailable"] .econ-state-chip,.econ-dossier[data-economic-state="loading"] .econ-state-chip{color:var(--muted)}
.econ-stance-text{margin:0;color:var(--text);font:500 var(--fs-md)/1.4 var(--font-ui)}
.econ-loading{display:grid;gap:var(--sp-2,8px)}
.econ-skel-title{display:block;height:var(--fs-h2);width:72%}
.econ-skel-row{display:block;height:var(--fs-md);width:100%}
.econ-content{display:grid;gap:var(--sp-5,20px)}
.econ-table-group{display:grid;gap:var(--sp-2,8px)}
.econ-group-head{display:flex;align-items:baseline;justify-content:space-between;gap:var(--sp-3,12px)}
.econ-group-head h3{margin:0;color:var(--text);font:700 var(--fs-h3)/1.25 var(--font-ui)}
.econ-group-note{max-width:72ch;margin:0;color:var(--muted);font:400 var(--fs-sm)/1.4 var(--font-ui)}
.econ-table-scroll{overflow-x:auto;border:1px solid var(--line);border-radius:var(--r-card,12px);background:var(--panel)}
.econ-table{width:100%;min-width:120px;border-collapse:collapse;font:400 var(--fs-sm)/1.4 var(--font-ui)}
.econ-table th[scope="col"]{padding:var(--sp-2,8px) var(--sp-3,12px);border-bottom:1px solid var(--line);color:var(--muted);font:700 var(--fs-micro)/1.2 var(--font-ui);letter-spacing:.08em;text-align:left;text-transform:uppercase}
.econ-table td,.econ-table th[scope="row"]{padding:var(--sp-2,8px) var(--sp-3,12px);border-bottom:1px solid var(--line);color:var(--text);text-align:left;vertical-align:middle}
.econ-table tbody tr:last-child td,.econ-table tbody tr:last-child th[scope="row"]{border-bottom:0}
.econ-table tbody tr:hover td,.econ-table tbody tr:hover th[scope="row"]{background:var(--panel2)}
.econ-cell-label{font-weight:600}
.econ-basis{display:inline-flex;align-items:center;min-height:24px;padding:var(--sp-1,4px) var(--sp-2,8px);border:1px solid var(--line);border-radius:var(--r-pill,999px);background:var(--panel2);color:var(--muted);font:600 var(--fs-label)/1.2 var(--font-ui)}
tr[data-economic-basis="reported"] .econ-basis{color:var(--ink-info)}
tr[data-economic-basis="organic"] .econ-basis{color:var(--ink-link,var(--link))}
tr[data-economic-basis="core"] .econ-basis{color:var(--ink-warn)}
.econ-value{font-family:var(--num,var(--font-mono));font-variant-numeric:tabular-nums;font-weight:600;white-space:nowrap}
.econ-evidence-button{display:inline-flex;align-items:center;justify-content:center;min-width:44px;min-height:40px;border:1px solid var(--gbtn-brd);border-radius:var(--r-btn,10px);background:var(--gbtn-bg);color:var(--text);font:600 var(--fs-label)/1.2 var(--font-ui);cursor:pointer;transition:background var(--t-fast,.16s) var(--ease-std,ease),border-color var(--t-fast,.16s) var(--ease-std,ease),color var(--t-fast,.16s) var(--ease-std,ease)}
.econ-evidence-button:hover{border-color:var(--gbtn-brd-hover);background:var(--gbtn-bg-hover)}
.econ-evidence-button:focus-visible,.econ-dossier-toggle:focus-visible,.econ-drawer-close:focus-visible{outline:2px solid var(--link);outline-offset:2px}
.econ-segments{border:1px solid var(--line);border-radius:var(--r-card,12px);background:var(--panel)}
.econ-segments summary{display:flex;align-items:center;min-height:44px;padding:var(--sp-2,8px) var(--sp-3,12px);border-radius:var(--r-card,12px);color:var(--text);font:600 var(--fs-sm)/1.3 var(--font-ui);cursor:pointer}
.econ-segments[open] summary{border-bottom:1px solid var(--line)}
.econ-segments .econ-table-scroll{border:0;border-radius:0 0 var(--r-card,12px) var(--r-card,12px)}
.econ-findings,.econ-missing{display:grid;gap:var(--sp-2,8px)}
.econ-findings h3,.econ-missing h3{margin:0;color:var(--text);font:700 var(--fs-h3)/1.25 var(--font-ui)}
.econ-finding-list,.econ-missing-list{display:grid;gap:var(--sp-2,8px);margin:0;padding:0;list-style:none}
.econ-finding-list li{padding:var(--sp-2,8px) var(--sp-3,12px);border-left:3px solid var(--line);border-radius:0 var(--r-ctl,8px) var(--r-ctl,8px) 0;background:var(--panel2);color:var(--text);font:400 var(--fs-sm)/1.45 var(--font-ui)}
.econ-finding-list li[data-economic-rule="missing_consensus"]{border-left-color:var(--muted)}
.econ-missing-list li{color:var(--muted);font:400 var(--fs-sm)/1.4 var(--font-ui)}
.econ-clock{display:flex;flex-wrap:wrap;gap:var(--sp-1,4px) var(--sp-3,12px);padding-top:var(--sp-3,12px);border-top:1px solid var(--line);color:var(--muted);font:400 var(--fs-micro)/1.4 var(--font-ui)}
.econ-links{display:flex;flex-wrap:wrap;gap:var(--sp-2,8px)}
.econ-links a{display:inline-flex;align-items:center;min-height:40px;padding:var(--sp-1,4px) var(--sp-3,12px);border:1px solid var(--gbtn-brd);border-radius:var(--r-btn,10px);background:var(--gbtn-bg);color:var(--ink-link,var(--link));font:600 var(--fs-label)/1.2 var(--font-ui);text-decoration:none}
.econ-state{display:grid;gap:var(--sp-1,4px);padding:var(--sp-4,16px);border:1px dashed var(--line);border-radius:var(--r-card,12px)}
.econ-state-line{margin:0;color:var(--text);font:600 var(--fs-md)/1.35 var(--font-ui)}
.econ-state-why{margin:0;color:var(--muted);font:400 var(--fs-sm)/1.45 var(--font-ui)}
.econ-drawer-scrim{position:fixed;inset:0;z-index:80;background:color-mix(in srgb,var(--bg) 55%,transparent)}
.econ-drawer{position:fixed;inset:auto var(--sp-3,12px) var(--sp-3,12px);z-index:81;display:grid;gap:var(--sp-3,12px);max-height:72%;max-height:60dvh;overflow:auto;padding:var(--sp-4,16px);border:1px solid var(--glass-brd);border-radius:var(--r-card,12px);background:var(--glass-bg);box-shadow:var(--glass-shadow);-webkit-backdrop-filter:var(--glass-blur);backdrop-filter:var(--glass-blur)}
.econ-drawer[hidden]{display:none}
.econ-drawer-bar{display:flex;align-items:center;justify-content:space-between;gap:var(--sp-3,12px)}
.econ-drawer h2{margin:0;color:var(--text);font:700 var(--fs-h3)/1.25 var(--font-ui)}
.econ-drawer-close{display:inline-flex;align-items:center;justify-content:center;min-width:44px;min-height:40px;border:1px solid var(--gbtn-brd);border-radius:var(--r-btn,10px);background:var(--gbtn-bg);color:var(--text);font:600 var(--fs-label)/1.2 var(--font-ui);cursor:pointer}
.econ-drawer-meta{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:var(--sp-2,8px);margin:0}
.econ-drawer-meta div{min-width:0;padding:var(--sp-2,8px);border:1px solid var(--line);border-radius:var(--r-ctl,8px);background:var(--panel)}
.econ-drawer-meta dt{color:var(--muted);font:600 var(--fs-micro)/1.2 var(--font-ui);text-transform:uppercase}
.econ-drawer-meta dd{margin:var(--sp-1,4px) 0 0;color:var(--text);font:500 var(--fs-sm)/1.35 var(--font-ui);overflow-wrap:anywhere}
.econ-drawer-meta code,.econ-receipt code{font-family:var(--font-mono);font-size:var(--fs-micro);color:var(--muted);overflow-wrap:anywhere}
.econ-source-text{margin:0;padding:var(--sp-3,12px);border-left:3px solid var(--line);border-radius:0 var(--r-ctl,8px) var(--r-ctl,8px) 0;background:var(--panel2);color:var(--text);font:400 var(--fs-sm)/1.55 var(--font-ui);overflow-wrap:anywhere}
.econ-receipt{margin:0}
.econ-precision{margin:0;color:var(--muted);font:400 var(--fs-sm)/1.45 var(--font-ui)}
.econ-dossier-toggle{display:inline-flex;align-items:center;justify-content:space-between;gap:var(--sp-3,12px);width:100%;min-height:40px;padding:var(--sp-2,8px) 0;border:0;background:transparent;color:var(--text);font:600 var(--fs-sm)/1.3 var(--font-ui);cursor:pointer;text-align:left}
.econ-dossier-cell{display:grid;gap:var(--sp-2,8px)}
@media (min-width:900px){
.econ-dossier-head{align-items:center}
.econ-table-group,.econ-findings,.econ-missing{grid-template-columns:minmax(176px,1fr) minmax(0,3fr);align-items:start}
.econ-table-group .econ-table-scroll,.econ-findings .econ-finding-list,.econ-missing .econ-missing-list{grid-column:2}
.econ-drawer{inset:auto var(--gap-grid,18px) var(--gap-grid,18px) auto;width:min(520px,calc(100% - var(--sp-4,16px)))}
}
@media (max-width:899px){
.econ-dossier-head,.econ-group-head,.econ-drawer-bar{display:grid;grid-template-columns:1fr;gap:var(--sp-2,8px)}
.econ-drawer{left:var(--sp-3,12px);right:var(--sp-3,12px)}
}
@media (max-width:640px){
.econ-dossier{padding:var(--sp-3,12px);border-radius:var(--r-card,12px)}
.econ-table-scroll{overflow-x:auto}
.econ-table{min-width:420px}
.econ-table th[scope="col"],.econ-table td,.econ-table th[scope="row"]{padding:var(--sp-2,8px)}
.econ-drawer-meta{grid-template-columns:1fr}
.econ-dossier-toggle{padding:var(--sp-2,8px)}
}
@media (prefers-reduced-motion:reduce){.econ-evidence-button,.econ-dossier-toggle,.econ-drawer{transition:none;animation:none}}
```

The first `<section data-economic-root>` must also receive `class="panel econ-dossier"`; the sector template’s existing `.panel` supplies the page’s normal panel background/border/padding. The declarations above intentionally use the same token values so Theme Tracker gets identical geometry without relying on a different panel definition.

### 4.3 DARK TREATMENT — command center

- Panel depth is luminance-first: `--panel` resting on `--bg`, a quiet `--line` hairline, and only `--card-shadow` at rest. The XLP `<section class="panel">` uses the page’s existing panel treatment; the dossier itself adds no second enclosing box.
- Basis chips are quiet instruments: `--panel2` fills, hairline borders, and text only through existing ink rungs (`--ink-info`, `--ink-link`, `--ink-warn`). Hue carries definition, not valuation.
- Tables use hairline rows and a `--panel2` hover tint. No zebra striping in dark; zebra would make this dense dossier feel like a terminal rather than a read surface.
- The dialog uses the existing dark glass family (`--glass-bg`, `--glass-brd`, `--glass-blur`, `--glass-shadow`) with the scrim composed from `--bg`. The evidence source remains an inert luminance block (`--panel2`, 3px rail), never a glowing raw document.
- State chips use calm ink: `--ink-ok` only for accepted/current, `--ink-warn` for pending/unverified/error, `--muted` for unavailable/loading/unentitled. No animated pulse or glow.

### 4.4 LIGHT TREATMENT — research workspace

- The same geometry becomes a printed-note material: white `--panel` on cool `--bg`, disciplined `--line` hairlines, and the existing light `--card-shadow`; no glow, colored wash, or added translucency.
- Basis chips remain compact hairline pills, but the light theme’s deeper ink rungs do the work. The labels remain readable after grayscale, so definition never depends on hue alone.
- Table rows remain hairline-first; light’s `--panel2` hover tint is present but quieter. No zebra.
- The dialog intentionally differs from dark: `--glass-bg` resolves to the existing light glass block, with airy `--glass-shadow`, crisp `--glass-brd`, and no dark scrim. The evidence quote remains a paper-like `--panel2` block with a 3px rail and deep text.
- State semantics are identical, but their paints deliberately use the measured light ink twins already defined by `theme.css`; the component does not derive new percentages.
- The light design is not judged as “renders after token swap”: hierarchy, chip restraint, hairline tables, evidence depth, and dialog material must be visually reviewed as a workspace note (TP-0; `research/MASTER_PRODUCT_DESIGN_SYSTEM_V1.md:587–612`).

### 4.5 Degraded states

- **Loading:** show the true three-row skeleton plus accessible fixed sentence; keep panel height stable and do not expose stale private values.
- **Unavailable:** show the fixed heading/state line and reason; retain the compact heading but no tables, findings, links, or clock.
- **Newer source pending / currentness unverified:** retain the accepted tables and findings, use `--ink-warn` only on the state chip, and put the dated explanation once in the clock footer. Do not tint data rows or imply a failed thesis.
- **Unentitled:** show only the fixed line/why and the owner-provided sign-in action; never render a teaser or blur private data. On XLP use the existing authenticated action route; on Theme Tracker return focus to the dossier toggle.
- **Error / unsupported schema:** show the fixed warning line and reason, retain “what still works” (none of the private dossier is shown), and do not retry automatically or reveal object paths.
- **Empty optional segment detail:** omit the `<details>` entirely; the missing-context list carries the fixed segment sentence when admitted context says it is absent.

### 4.6 Density budget and responsive reduction

At **390 px**, the dossier displays without horizontal page scroll. The inner table container may scroll horizontally; mobile does **not** squeeze the table into unreadable columns. Before that inner scroll becomes necessary, the visible content budget is exactly: heading + stance row; Demand header; three Demand rows; Earnings header; one Earnings row; one finding; one missing-context line; clock; then inner rows scroll. Segment detail is collapsed. The desktop two-column section grid reduces to one column at ≤899 px, and dialog/meta reduce at ≤640 px per the declarations above. This is a deliberate demotion-with-landing reduction, not a squeezed desktop table (`research/MASTER_PRODUCT_DESIGN_SYSTEM_V1.md:652–664`).

### 4.7 Token receipts and current-main dependency

Receipt command for tokens that exist directly in `templates/theme.css`:

```text
$ rg -n -- '--(fs-(h2|h3|md|sm|label|micro)|bg|panel2?|line|text|muted|ink-(ok|warn|act|link|info)|font-(ui|mono)|num|card-shadow|popover-shadow|glass-(bg|brd|blur|shadow)|gbtn-(bg|bg-hover|brd|brd-hover|sheen)):' templates/theme.css
30:  --font-ui: -apple-system, BlinkMacSystemFont, Inter, "Segoe UI", Roboto,
33:  --font-mono: ui-monospace, "SF Mono", SFMono-Regular, "Cascadia Mono",
39:  --num: var(--font-ui);
56:  --fs-h2:17px;        /* panel section titles        */
57:  --fs-md:15px;        /* lead body / strong figures  */
59:  --fs-h3:14px;        /* subsection titles           */
60:  --fs-sm:12.5px;      /* secondary copy / table body */
61:  --fs-label:11px;     /* MONO eyebrows · caps        */
62:  --fs-micro:10px;     /* dense ticks · table heads   */
63:  --bg: #0f1115; --panel: #181b21; --panel2: #1e222a; --text: #d7dce3;
64:  --muted: #8b93a1;
69:  --line: #3a4150;
120:  --card-shadow: 0 1px 0 rgba(255,255,255,.02);
121:  --popover-shadow: 0 6px 18px rgba(0,0,0,.5);
139:  --glass-bg: color-mix(in srgb, var(--panel) 86%, transparent);
140:  --glass-brd: color-mix(in srgb, var(--text) 14%, transparent);
141:  --glass-blur: saturate(180%) blur(22px);
142:  --glass-shadow: 0 24px 64px -22px rgba(3,7,18,.74), 0 10px 26px -12px rgba(3,7,18,.55),
148:  --gbtn-bg:        color-mix(in srgb, var(--panel2) 52%, transparent);
149:  --gbtn-bg-hover:  color-mix(in srgb, var(--panel2) 76%, transparent);
150:  --gbtn-brd:       color-mix(in srgb, var(--text) 12%, transparent);
151:  --gbtn-brd-hover: color-mix(in srgb, var(--text) 24%, transparent);
152:  --gbtn-sheen:     rgba(255,255,255,.09);
190:  --gbtn-bg:        color-mix(in srgb, var(--panel2) 78%, var(--panel));
191:  --gbtn-bg-hover:  color-mix(in srgb, var(--panel2) 96%, var(--panel));
197:  --gbtn-brd:       color-mix(in srgb, #1c2430 50%, transparent);
198:  --gbtn-brd-hover: color-mix(in srgb, #1c2430 66%, transparent);
199:  --gbtn-sheen:     rgba(255,255,255,.7);
210:  --bg: #f7f8fa; --panel: #ffffff; --panel2: #eef1f6; --text: #1c2430;
211:  --muted: #5d6b7e;
218:  --line: color-mix(in srgb, #1c2430 16%, #eaecf0);
236:  --card-shadow: 0 1px 3px rgba(20,30,50,.07);
239:  --popover-shadow: 0 4px 10px rgba(20,30,50,.06), 0 12px 28px rgba(20,30,50,.14);
243:  --glass-bg: color-mix(in srgb, var(--panel) 90%, transparent);
244:  --glass-brd: color-mix(in srgb, #1c2430 9%, transparent);
245:  --glass-shadow: 0 20px 54px -24px rgba(20,32,64,.34), 0 10px 24px -14px rgba(20,32,64,.20),
372:  --ink-warn:   color-mix(in srgb, var(--warn)   var(--ink-mix-warn),   var(--text));
373:  --ink-ok:     color-mix(in srgb, var(--ok)     var(--ink-mix-ok),     var(--text));
374:  --ink-act:    color-mix(in srgb, var(--act)    var(--ink-mix-act),    var(--text));
376:  --ink-link:   color-mix(in srgb, var(--link)   var(--ink-mix-link),   var(--text));
377:  --ink-info:   color-mix(in srgb, var(--info)   var(--ink-mix-info),   var(--text));
```

The spacing/radius/motion names used with fallbacks are **not yet definitions in current `theme.css`**. The receipt proving their canonical proposed values is therefore necessarily the executable specimen, not `theme.css`:

```text
$ git show origin/main:mockups/design_system/specimen.html | rg -n -- '--sp-[1-8]:|--r-(ctl|btn|card|panel|pill):|--t-(fast|med|slow):|--ease-(std|lift):|--gap-grid:'
22:  --sp-1:4px; --sp-2:8px; --sp-3:12px; --sp-4:16px; --sp-5:20px; --sp-6:24px; --sp-7:32px; --sp-8:44px;
23:  --gap-grid:18px;
24:  --r-ctl:8px; --r-btn:10px; --r-card:12px; --r-panel:14px; --r-pill:999px;
25:  --t-fast:.16s; --t-med:.2s; --t-slow:.55s;
26:  --ease-std:ease; --ease-lift:cubic-bezier(.2,.7,.3,1);
```

This is a **build precondition, not permission to mint a local token root**: either DS-PR-0 must land those names in `theme.css`, or the seat must explicitly ratify the existing inert-fallback idiom in writing. The build lane must stop `PARTIAL/BLOCKED` if neither is true.

## 5. Copy

All source-derived labels are server-owned bilingual strings. Fixed UI strings are paired EN/ZH below and must not be paraphrased. ZH is native-shaped, not word-for-word; fiscal dates, units, “EPS”, “FX”, and established company segment names remain intact. No translated text is emitted in `title=` attributes.

### 5.1 Fixed shell and actions

| Token | EN | ZH |
|---|---|---|
| eyebrow | Consumer research | 消费研究 |
| title | Demand and earnings evidence | 需求与盈利证据 |
| compact toggle | Open P&G demand and earnings evidence | 打开宝洁需求与盈利证据 |
| compact expanded suffix | Close P&G demand and earnings evidence | 关闭宝洁需求与盈利证据 |
| default stance | Watch the evidence — do not chase it. | 看证据，勿追。 |
| loading | Loading the latest accepted evidence. | 正在加载最新已采纳证据。 |
| demand | Demand | 需求 |
| earnings | Earnings | 盈利 |
| item | Item | 项目 |
| period | Period | 期间 |
| basis | Basis | 口径 |
| value | Value | 数值 |
| evidence | Evidence | 证据 |
| evidence action | Open source evidence | 打开源证据 |
| segments | Segment detail | 分部明细 |
| findings | What the numbers say | 数字说明了什么 |
| missing title | Context not available | 缺失的背景 |
| drawer title | Source evidence | 来源证据 |
| header | Header | 表头 |
| generation | Generation | 生成版本 |
| manifest | Manifest | 清单 |
| record | Record | 记录 |
| digest | Digest | 摘要 |
| precision | Precision note | 精度说明 |
| close | Close | 关闭 |
| fiscal period | Fiscal period | 财务期间 |
| source accepted | Source accepted | 来源采纳时间 |
| accepted generation | Accepted generation | 已采纳生成版本 |
| currentness | Currentness | 时效性 |
| company link | Open the company page | 打开公司页面 |
| GMI link | Open the related research | 打开相关研究 |
| return | Return to where you were | 返回原位置 |

### 5.2 Basis chips

| Machine value | EN | ZH |
|---|---|---|
| reported | Reported | 报告口径 |
| organic | Organic | 有机口径 |
| core | Core | 核心口径 |

### 5.3 Fact labels

| Owner metric family | EN | ZH |
|---|---|---|
| reported sales growth | Reported sales growth | 报告销售额增长 |
| organic sales growth | Organic sales growth | 有机销售额增长 |
| total volume growth | Total volume growth | 总销量增长 |
| organic volume growth | Organic volume growth | 有机销量增长 |
| combined volume/mix | Volume and mix combined | 销量与结构合计 |
| price contribution | Price contribution | 价格贡献 |
| mix contribution | Mix contribution | 结构贡献 |
| FX contribution | FX contribution | 汇率贡献 |
| other contribution | Other contribution | 其他贡献 |
| reported diluted EPS | Reported diluted EPS | 报告稀释每股收益 |
| prior reported diluted EPS | Prior reported diluted EPS | 上期报告稀释每股收益 |
| reported EPS growth | Reported EPS growth | 报告每股收益增长 |
| core EPS | Core EPS | 核心每股收益 |
| prior core EPS | Prior core EPS | 上期核心每股收益 |
| core EPS growth | Core EPS growth | 核心每股收益增长 |
| core reconciliation context | Core EPS reconciliation | 核心每股收益调节说明 |
| admitted segment | Use the owner-supplied segment display name in both languages | 使用所有者提供的双语分部名称 |

### 5.4 States and currentness

| State | EN | ZH |
|---|---|---|
| up_to_date | Up to date | 已更新 |
| newer_source_pending | Newer source pending | 新来源待处理 |
| currentness_unverified | Currentness unverified | 时效性未核实 |
| unavailable | This evidence is unavailable. | 此证据暂不可用。 |
| unavailable why | The accepted private record is not available to this page. | 本页无法读取已采纳的私有记录。 |
| unentitled | Full membership is required. | 需要完整会员权限。 |
| unentitled why | Sign in with an account that includes this research. | 请使用包含此研究的账户登录。 |
| unsupported schema | This evidence needs a newer page version. | 此证据需要更新版本页面。 |
| error | This evidence could not be loaded. | 此证据未能加载。 |
| error why | The request failed before any evidence was shown. | 请求在显示任何证据前失败。 |

### 5.5 Findings, exact by rule ID

The wording below is the display wording; the machine rule ID is never shown.

| Rule ID | EN | ZH |
|---|---|---|
| reported_vs_organic_difference | Reported sales rose, but the company-defined organic measure did not. | 报告销售额增长，但公司定义的有机口径未增长。 |
| positive_organic_nonpositive_pure_volume | Organic revenue rose while pure volume did not; price or mix contributed. | 有机收入增长而纯销量未增长，价格或结构做出贡献。 |
| reported_vs_core_earnings_disagreement | Reported and core EPS moved differently because they use different definitions. | 报告与核心每股收益走势不同，因为二者定义不同。 |
| incomplete_margin_to_cash_bridge | Margin information is not enough to show operating profit or cash improvement. | 利润率信息不足以说明经营利润或现金改善。 |
| segment_scope_limitation | Segment detail describes those segments, not the whole sector. | 分部明细只描述这些分部，不代表整个行业。 |
| missing_consensus | Consensus is unavailable, so this is not a beat or a miss. | 共识数据不可用，因此这不是优于或低于预期。 |

### 5.6 Missing context

| Owner value | EN | ZH |
|---|---|---|
| consensus | Consensus is unavailable. | 共识数据不可用。 |
| segments | Segment detail is unavailable. | 分部明细不可用。 |
| reconciliation | The company’s core EPS reconciliation is unavailable. | 公司核心每股收益调节说明不可用。 |
| margin_to_cash | The margin-to-cash bridge is unavailable. | 利润率到现金的桥接不可用。 |
| empty list | Nothing required is missing. | 必需信息没有缺失。 |

### 5.7 Mandatory definition lines

These lines appear once in their group headers and are not repeated per row:

- “Organic sales are a company-defined revenue measure, not household consumption.” / “有机销售额是公司定义的收入口径，不等于家庭消费。”
- “Reported and core EPS use different definitions.” / “报告口径与核心每股收益采用不同定义。”
- “Volume and mix combined is not pure volume.” / “销量与结构合计不等于纯销量。”
- “Read the evidence in its source context.” / “请结合来源语境阅读证据。”

The combined volume/mix sentence appears only when that row exists. The source-context sentence appears in the evidence dialog. These distinctions implement the review clarifications (`2026-09-23 R5 design review:25–30`).

### 5.8 Clock templates

Templates use server-provided localized values and never calculate dates in the browser:

- Fiscal period: `Fiscal period: {period}` / `财务期间：{period}`
- Source accepted: `Source accepted: {date}` / `来源采纳时间：{date}`
- Generation: `Accepted generation: {pin}` / `已采纳生成版本：{pin}`
- Up to date: `Currentness: up to date as of {source clock}` / `时效性：截至{source clock}已更新`
- Pending: `Currentness: newer source pending since {source clock}` / `时效性：自{source clock}起新来源待处理`
- Unverified: `Currentness: latest accepted, currentness unverified` / `时效性：最新已采纳，时效性未核实`

### 5.9 Copy bans and interpretation rules

The glance stance and compact labels use no internal state, study name, machine slug, or falsifier/refutation language. “Validated” is forbidden. No front-facing string says demand is proven, core is cleaner/recurring, combined mix is pure volume, or consensus was beaten. The UI never says “buy,” “sell,” “size,” “rank,” “originate,” “entry,” or “Prophet.”

## 6. Behavior

### 6.1 Rendering-only rules

- Render source-derived text exclusively with `textContent`, `createElement`, `setAttribute`, `classList`, `hidden`, and `replaceChildren`. Never call `innerHTML`, `insertAdjacentHTML`, `eval`, `Function`, `srcdoc`, or `outerHTML` with source data.
- No browser arithmetic, rounding, aggregation, sorting beyond the fixed server order, inference, modeling, scoring, or trading-label creation.
- Reject any response whose top-level keys are not exactly `schema interpretation_id issuer event_id build selection observations comparisons findings missing_context next_evidence quality clocks authority`, whose `schema` is unsupported, or whose six `authority` booleans are missing, extra, or not all literal `false` (`2026-09-23 CDV-1 implementation plan:139–156`).
- Render only server-provided display fields. Digests and pins are opaque strings displayed verbatim; the browser does not derive a receipt.
- Unknown optional source fields are ignored only when the closed top-level contract passes; unknown fields inside closed sections render unavailable rather than being interpreted.
- Language follows the page’s existing `data-lang` and `langchange` mechanism. Both language nodes may exist server-side, but dynamic source strings use one `textContent` selected from the server’s matching language field.

### 6.2 Fetch and request lifetime

`fetchAuthenticated` is called exactly once per mounted load with:

```javascript
fetchAuthenticated('/api/earnings/v1/economic/PG', {
  credentials: 'same-origin',
  cache: 'no-store',
  headers: {Accept: 'application/json'}
})
```

The wrapper adds the current Bearer header. The component adds no other API call. AbortController, internal epoch, and auth epoch govern every response:

- Capture `requestEpoch` before the fetch; discard if it no longer equals the current internal epoch.
- Store the controller in exactly one `pending` reference.
- On a second load while one is pending, abort the first; there is never parallel private loading.
- On logout/auth epoch change or destroy, increment internal epoch, abort, clear children, and show the unentitled/unavailable state.
- A late earlier response is always discarded even if it resolves successfully.
- No automatic retry, polling, refresh timer, or page reload.

### 6.3 Evidence navigation

An evidence click does no financial fetch. It opens the existing dialog with the evidence object referenced by that displayed observation, and pins `event_id`, the fact’s native handle, selected generation, manifest digest, and record digest from the **displayed** response. If evidence content was not supplied by the owner, the button is disabled with the fixed unavailable wording rather than fabricating a source URL.

A subsequent evidence request uses the pinned values with the exact generation/manifest/record/fact bindings to `/api/earnings/v1/records/{slug}/economic-evidence/{fact_id}` only when the pinned owner binding is present. It is sent through `fetchAuthenticated`, uses `cache:'no-store'`, is abortable, and replaces only the currently open dialog. A failure closes the dialog and returns focus to the invoking button. The component never constructs this route from mutable current state.

### 6.4 Privacy, storage, and telemetry

- Write no source-derived value, response, token, digest, URL, or user state to `localStorage`, `sessionStorage`, `IndexedDB`, cookies, service-worker caches, `console`, screenshots initiated by code, analytics, or telemetry.
- Never expose a private value in a DOM attribute not required by the fixed contract. `data-economic-*` contains only state, period, basis, rule ID, fact ID, and mount/control semantics.
- Use no web worker, iframe, canvas rendering, copy-to-clipboard, print hook, or transport beyond the injected wrapper.
- Browser test fixtures use synthetic values and a synthetic private sentinel to prove none of these sinks receives private data.

### 6.5 Links

Render the company link only when the response provides a valid existing validated native issuer/listing bridge. Render the GMI link only when the response provides an admitted relationship. Both bindings must include a nonempty same-site path and owner-valid label. Set `rel="noopener"` and the fixed accessible label; do not infer a URL from ticker, company name, or GMI identity. When absent, render the fixed unresolved line: “Related company and research links are unavailable.” / “相关公司与研究链接不可用。” This implements the design’s owner-binding law (`2026-09-23 economic dossier design:141–147`).

## 7. Evidence matrix

The build lane must produce the exact browser proof below with mocked server responses and synthetic private values. It must not claim visual acceptance from syntax-only checks. Each row is a separate Playwright case or a parameterized case with an independently captured artifact; run at most one Playwright process at a time.

### 7.1 Twelve visual combinations

Use `tests/test_earnings_economic_browser.py` and the accepted real generated `templates/sector.html.j2` plus `_economic_dossier.html.j2`; no substitute page.

| # | Theme | Language | Width | Required screenshot/check |
|---|---|---|---|---|
| E01 | dark | en | 1440 | full dossier; no horizontal page scroll |
| E02 | dark | en | 820 | section reduction; no clipped labels |
| E03 | dark | en | 390 | declared density budget; inner-table scroll only |
| E04 | dark | zh | 1440 | ZH parity; fiscal/unit values intact |
| E05 | dark | zh | 820 | no EN fallback in fixed ZH strings |
| E06 | dark | zh | 390 | ≤20-character stance; no clipped basis chips |
| E07 | light | en | 1440 | judged as research-workspace design, not token swap |
| E08 | light | en | 820 | hairline hierarchy and airy depth remain distinct |
| E09 | light | en | 390 | page never scrolls horizontally |
| E10 | light | zh | 1440 | native-shaped ZH and light ink rungs |
| E11 | light | zh | 820 | evidence drawer light material |
| E12 | light | zh | 390 | mobile reduction and dialog retain meaning |

Each artifact asserts: at least one `data-economic-period`; a `reported` basis row; an `organic` basis row; a `core` basis row; reported/core rows remain visually separate; findings/missing context are plain sentences; no visible rule ID or raw slug; currentness once.

### 7.2 Behavioral and adversarial checks

| ID | Test/check | Required proof |
|---|---|---|
| B01 | Keyboard open/close | Tab reaches first evidence button; Enter opens dialog; Escape closes; focus returns exactly to invoking button |
| B02 | Dialog focus trap | Tab/Shift+Tab remains in dialog; close is first focus; scrim click closes |
| B03 | Hostile markup | Synthetic span/header contains markup, quotes, and script-like text; DOM is inert and contains no executable descendants |
| B04 | Logout during fetch | Synthetic sentinel request is aborted; response discards; private sinks remain empty |
| B05 | Late earlier response | First older response resolves after second; displayed epoch belongs to second only |
| B06 | Missing context | consensus/segments render fixed absence lines; no beat/miss text |
| B07 | Newer source pending | accepted tables remain; warning once; no row tint |
| B08 | Currentness unverified | exact footer wording; never “up to date” |
| B09 | Unsupported schema | unavailable state; private fields never rendered |
| B10 | Unentitled | sign-in/action state; no teaser/blur/private text |
| B11 | Error | exact error/reason; no object path or credential |
| B12 | Loading | true geometry skeleton; no stale private values |
| B13 | Grayscale | reported/organic/core distinguishable by text and position in both languages |
| B14 | Evidence pinning | route uses displayed slug/fact/generation/manifest/record; changed pointer cannot redirect |
| B15 | Company/GMI unresolved | fixed unavailable line; no fabricated link |
| B16 | Theme Tracker lifecycle | mount on expand; destroy on collapse; one root; no duplicate fetch |
| B17 | XLP-only mount | root exists on XLP; absent on XLK and XLY |
| B18 | Storage/console/network | no private sentinel in storage, console, analytics, service worker, or unintended route |
| B19 | Reduced motion | evidence from browser emulation; no mandatory movement |
| B20 | Asset parity | actual template/site registration and repository asset-copy guard pass |

### 7.3 Command and evidence receipt

The build lane’s required browser project is exactly:

```bash
python3 -m pytest tests/test_earnings_economic_browser.py -q
```

It must report the twelve visual combinations and B01–B20 in its test IDs/artifact names. Additional release proof with an authorized actual source is separate and must name the native event/source revision; it never substitutes for the mocked privacy/hostile tests. Visual/UI acceptance is not claimed by this docs-only lane.

## 8. Open questions for the seat

1. **Theme Tracker membership.** The current `site/neuralwebdata/theme_state.json` has no `us_sector_staples` row, although the stable theme vocabulary/crosswalk does. Should Task 7 add the row through the ThemeState owner before this mount, or should the compact cell remain conditionally absent until that owner admits it? **Recommendation:** require the owner admission first; the template condition is lawful but will never paint without that row, and inventing a display row would violate ThemeState authority.
2. **Entitlement action on Theme Tracker.** Should unentitled readers be sent to the existing plans/sign-in route, or remain in place with a sign-in action only? **Recommendation:** use the existing site sign-in action and return focus to the dossier toggle; do not deep-link directly to marketing plans.
3. **Dialog placement.** The dossier uses a bottom sheet at ≤899 px and a right sheet at ≥900 px. Confirm this is acceptable for the Staples route. **Recommendation:** keep it; it preserves source context beside wide tables and avoids covering the full mobile journey.
4. **DS-PR-0 timing.** This packet deliberately uses the established fallback idiom for spacing/radius/motion. If DS-PR-0 has landed before build, may the builder remove the fallback values mechanically? **Recommendation:** no — leave them inert unless a separate migration packet owns that sweep; this avoids unrequested repaint.
5. **Clock granularity.** The server supplies localized date/time strings, but no display rule says whether unknown time granularity should print “date unknown”. **Recommendation:** use the server’s exact phrase and never manufacture time; if the seat wants a fixed unknown-state chip, add it before build.
6. **Segment naming.** Owner-supplied bilingual segment labels are assumed but not yet frozen by the API packet. **Recommendation:** render unavailable until both labels are present; never machine-translate an admitted segment name.
7. **Actual release proof threshold.** Task 7 can prove all mocked behavior without live data. Should release additionally require one authentic accepted P&G generation, or defer that to Task 8 qualification? **Recommendation:** require it at release because the user journey explicitly needs exact evidence navigation, but keep synthetic values for CI.
