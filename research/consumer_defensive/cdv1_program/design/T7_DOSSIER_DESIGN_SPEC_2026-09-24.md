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

TODO

## 5. Copy

TODO

## 6. Behavior

TODO

## 7. Evidence matrix

TODO

## 8. Open questions for the seat

TODO
