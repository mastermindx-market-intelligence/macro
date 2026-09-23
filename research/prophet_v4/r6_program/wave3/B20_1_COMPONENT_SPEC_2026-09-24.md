# B20-1 Prophet Workspace Component Specification

## SOURCE_SHA

- Detached source: `7fd7a0b2977846d9ffc79c748f503805b410d076` (`origin/main` at session start).
- Skeleton commit / draft PR head: `10cd52a2c1a611fcbcb6a7b844598ec94e26d770` (PR #7851).
- Source inputs were read at the detached source; no base merge occurred.

## TOKEN TRUTH

Direct `rg -n -- '--sp-[145678]|--gap-grid|--t-med|--t-slow|--ease-std|--ease-lift|--shadow-hover|--ser-[1-4]|--ink-tier|--ink-prov|\.mx-tbl|\.mx-tblbox|\.mx-tabset|\.mx-rail' templates/theme.css` produced only fallback uses at this SHA. `--fs-*` definitions are present at `templates/theme.css:51-62`; `.mx-chg-row`, `.mx-empty`, `.skel`, `.mx-error`, and `.mx-ladder--board` are present at approximately lines 2024, 2040, 2059, 2062, and 2141.

| Token / primitive | Status verified at source SHA | B20-1 use |
|---|---|---|
| `--sp-1/4/5/6/7/8`, `--gap-grid`, `--t-med`, `--t-slow`, `--ease-std`, `--ease-lift`, `--shadow-hover`, `--ser-1..4`, `--ink-tier`, `--ink-prov`, `.mx-tbl`, `.mx-tblbox`, `.mx-tabset`, `.mx-rail` | **NOT FOUND by direct grep at this SHA**, contrary to frozen input §3 | CSS uses none as an unfallbacked dependency except where inherited through linked files. |
| `--sp-2`, `--sp-3`, `--r-ctl`, `--r-btn`, `--r-card`, `--r-panel`, `--r-pill`, `--t-fast` | Deferred | Every reference carries the frozen value-equal fallback (`8px`, `12px`, `8px`, `10px`, `12px`, `14px`, `999px`, `0.16s`). |
| Theme role inks (`--ink-ok`, `--ink-warn`, `--ink-link`, text/panel/line roles) and `--fs-*` | Present / inherited from `templates/theme.css` | All component color and type decisions resolve through theme roles. |
| `.mx-tier-gate--prophet` | Present in `templates/tier_preview.css:26` | `TierLockProphet` composes it without restyling its internals. |

**GAP, not a workaround:** the two DS-PR-0 authority files named as binding inputs are absent from this checkout and its fetched `origin/main`, so their landing claims cannot be independently verified. The component CSS depends only on roles and value-equal fallbacks that render at this source SHA. When the authority files actually land, remove only redundant fallbacks; do not change geometry or color.

## ProphetWorkspaceShell

**Purpose (§4):** shared workspace context, route links, and responsive destination row beneath the sole authenticated header family.

```html
<div class="pw-shell" data-surface="action|radar|all|themes|track">
  <div class="pw-context-row">
    <p class="pw-product"><span class="l-en">Prophet US</span><span class="l-zh">Prophet 美国</span></p>
    <!-- ResearchOnlyChip -->
    <!-- AsOfStamp -->
  </div>
  <nav class="pw-tabs" aria-label="Workspace destinations">
    <a href="#action" aria-current="page">Action Desk</a>
    <a href="#radar">Radar</a>
    <a href="#all">All Candidates</a>
    <a href="#themes">Themes</a>
    <a class="pw-track-record" href="/us_track_record.html">Track Record</a>
  </nav>
  <!-- surface children -->
</div>
```

```css
html:not([data-lang="zh"]) .l-zh, html[data-lang="zh"] .l-en { display: none; }
.pw-fixture { max-width: 1160px; margin: 0 auto; padding: var(--sp-6,24px) var(--sp-4,16px) var(--sp-8,44px); }
.pw-fixture h1, .pw-fixture h2, .pw-block > h2 { margin: 0; font-size: var(--fs-h2,17px); line-height: 1.25; color: var(--text); }
.pw-fixture h1 { font-size: var(--fs-h1,28px); }
.pw-block { margin-top: var(--sp-7,32px); padding: var(--sp-4,16px); border: 1px solid var(--line); border-radius: var(--r-panel,14px); background: var(--panel); box-shadow: var(--card-shadow); }
.pw-block > h2 { margin-bottom: var(--sp-2,8px); color: var(--muted); font-size: var(--fs-label,11px); letter-spacing: .08em; text-transform: uppercase; }
.pw-fixture-bar { display: flex; flex-wrap: wrap; align-items: center; gap: var(--sp-2,8px) var(--sp-3,12px); }
.pw-fixture-note { margin-right: auto; color: var(--muted); font-size: var(--fs-sm,12.5px); }
.pw-fixture-controls, .pw-context-row, .pw-tabs, .pw-row, .pw-evidence-grid, .pw-watch-meta, .pw-preview-line { display: flex; align-items: center; }
.pw-fixture-controls { gap: var(--sp-2,8px); }
.pw-fixture-controls button, .pw-watch, .pw-preview-cta, .pw-undo { appearance: none; border: 0; border-radius: var(--r-btn,10px); min-height: 40px; padding: 9px var(--sp-3,12px); font: 700 var(--fs-sm,12.5px)/1.2 var(--font-ui); color: var(--text); background: color-mix(in srgb, var(--text) 10%, transparent); cursor: pointer; transition: transform var(--t-fast,0.16s) var(--ease-lift,ease), background var(--t-fast,0.16s) var(--ease-std,ease); }
.pw-fixture-controls button:hover, .pw-watch:not(:disabled):hover, .pw-preview-cta:hover, .pw-undo:hover { background: color-mix(in srgb, var(--text) 15%, transparent); transform: translateY(-1px); }
.pw-shell { border: 1px solid var(--line); border-radius: var(--r-panel,14px); background: var(--bg); overflow: hidden; }
.pw-context-row { justify-content: flex-start; flex-wrap: wrap; gap: var(--sp-2,8px) var(--sp-3,12px); padding: var(--sp-2,8px) var(--sp-3,12px); border-bottom: 1px solid var(--line); background: var(--panel); }
.pw-product { margin: 0; font-size: var(--fs-h3,14px); font-weight: 750; color: var(--text); }
.pw-chip { display: inline-flex; align-items: center; min-height: 24px; padding: 3px var(--sp-2,8px); border: 1px solid color-mix(in srgb, var(--text) 18%, var(--line)); border-radius: var(--r-pill,999px); color: var(--text); background: color-mix(in srgb, var(--text) 5%, var(--panel)); font-size: var(--fs-label,11px); font-weight: 650; }
.pw-asof { margin: 0; margin-left: auto; color: var(--muted); font-size: var(--fs-micro,10px); font-variant-numeric: tabular-nums; }
.pw-tabs { justify-content: flex-start; gap: var(--sp-2,8px); overflow-x: auto; padding: var(--sp-2,8px) var(--sp-3,12px); border-bottom: 1px solid var(--line); background: var(--panel); }
.pw-tabs a { flex: none; min-height: 40px; padding: 9px var(--sp-2,8px); border-radius: var(--r-ctl,8px); color: var(--muted); font-size: var(--fs-sm,12.5px); font-weight: 650; text-decoration: none; }
.pw-tabs a:hover, .pw-tabs a[aria-current="page"] { color: var(--text); background: color-mix(in srgb, var(--text) 8%, transparent); }
.pw-track-record { margin-left: auto; border-left: 1px solid var(--line); padding-left: var(--sp-2,8px); }
.pw-empty { padding: var(--sp-6,24px) var(--sp-4,16px); text-align: center; background: var(--panel); }
.pw-empty-main { margin: 0 0 var(--sp-1,4px); font-size: var(--fs-md,15px); font-weight: 650; color: var(--text); }
.pw-empty p:last-child { margin: 0; color: var(--muted); font-size: var(--fs-sm,12.5px); }
.pw-ladder { border: 1px solid var(--line); border-radius: var(--r-card,12px); background: var(--panel); overflow: hidden; }
.pw-ladder ol { display: grid; grid-template-columns: repeat(7, minmax(0,1fr)); margin: 0; padding: 0; list-style: none; }
.pw-ladder li { min-width: 0; padding: var(--sp-2,8px) var(--sp-1,4px); border-right: 1px solid var(--line); color: var(--muted); font-size: var(--fs-micro,10px); text-align: center; }
.pw-ladder li:last-child { border-right: 0; }
.pw-ladder b { display: block; color: var(--text); font-size: var(--fs-md,15px); font-variant-numeric: tabular-nums; }
.pw-ladder li[data-absent="true"] b { color: var(--muted); }
.pw-ladder li[data-withheld="true"] { background: repeating-linear-gradient(135deg, transparent 0 5px, color-mix(in srgb, var(--line) 42%, transparent) 5px 10px); }
.pw-stance { display: inline-flex; align-items: center; min-height: 24px; padding: 3px var(--sp-2,8px); border: 1px solid var(--line); border-radius: var(--r-pill,999px); color: var(--text); background: color-mix(in srgb, var(--text) 4%, var(--panel)); font-size: var(--fs-label,11px); font-weight: 700; }
.pw-stance[data-availability="ENTRY_OPEN"] { color: var(--ink-ok); border-color: color-mix(in srgb, var(--ink-ok) 38%, var(--line)); background: color-mix(in srgb, var(--ink-ok) 10%, var(--panel)); }
.pw-stance[data-availability="APPROACHING_ENTRY"] { color: var(--ink-link,var(--link)); border-color: color-mix(in srgb, var(--link) 34%, var(--line)); }
.pw-stance[data-availability="INVALIDATED"] b { text-decoration: line-through; }
.pw-stance[data-availability="UNAVAILABLE_DATA"], .pw-stance[data-availability="NO_READ"] { border-style: dashed; color: var(--muted); background: transparent; }
.pw-rows { border: 1px solid var(--line); border-radius: var(--r-card,12px); overflow: hidden; background: var(--panel); }
.pw-row { position: relative; justify-content: flex-start; flex-wrap: wrap; gap: var(--sp-1,4px) var(--sp-2,8px); width: 100%; margin: 0; padding: var(--sp-2,8px) var(--sp-3,12px); border: 0; border-bottom: 1px solid var(--line); border-left: 3px solid transparent; background: var(--panel); color: var(--text); font: inherit; text-align: left; }
.pw-row:last-child { border-bottom: 0; }
.pw-row[data-availability="ENTRY_OPEN"] { border-left-color: var(--ink-ok); }
.pw-row[data-availability="UNAVAILABLE_DATA"], .pw-row[data-availability="NO_READ"] { border-left: 3px dashed var(--line); }
.pw-row[data-degraded="stale"] .pw-change { color: var(--muted); text-decoration: underline; text-decoration-color: var(--ink-warn); text-underline-offset: 4px; }
.pw-row[data-degraded="failed"] { background: color-mix(in srgb, var(--ink-warn) 9%, var(--panel)); border-left-color: var(--ink-warn); }
.pw-row[data-preview="true"], .pw-row[aria-hidden="true"] { border-left: 3px dashed var(--line); }
.pw-row[data-lifecycle="INVALIDATED"] .pw-stance { color: var(--muted); }
.pw-name { flex: 0 0 5.5rem; min-width: 0; overflow-wrap: anywhere; font-size: var(--fs-h3,14px); font-weight: 750; }
.pw-name small { display: block; overflow-wrap: anywhere; color: var(--muted); font-size: var(--fs-micro,10px); font-weight: 550; }
.pw-change { flex: 1 1 16rem; min-width: 12rem; margin: 0; color: var(--text); font-size: var(--fs-sm,12.5px); line-height: 1.4; }
.pw-stance { flex: none; }
.pw-action { flex: none; min-width: 10rem; color: var(--muted); font-size: var(--fs-sm,12.5px); font-weight: 600; }
.pw-row[data-availability="ENTRY_OPEN"] .pw-action { color: var(--ink-ok); }
.pw-chevron { flex: none; width: 1.25em; height: 1.25em; color: var(--muted); }
.pw-row[aria-expanded="true"] .pw-chevron { transform: rotate(90deg); }
.pw-evidence { margin: 0; padding: var(--sp-3,12px) var(--sp-3,12px) var(--sp-4,16px); border-bottom: 1px solid var(--line); background: var(--panel2); }
.pw-evidence-grid { align-items: flex-start; justify-content: flex-start; flex-wrap: wrap; gap: var(--sp-3,12px); }
.pw-evidence-col { flex: 1 1 24rem; min-width: 16rem; margin: 0; }
.pw-evidence h3 { margin: 0 0 var(--sp-1,4px); color: var(--text); font-size: var(--fs-label,11px); letter-spacing: .08em; text-transform: uppercase; }
.pw-evidence dl, .pw-evidence p { margin: 0; color: var(--muted); font-size: var(--fs-sm,12.5px); line-height: 1.5; }
.pw-evidence div { margin-bottom: var(--sp-2,8px); }
.pw-evidence dt, .pw-evidence dd { margin: 0; display: inline; }
.pw-evidence dd { color: var(--text); }
.pw-evidence-actions { align-items: center; flex-wrap: wrap; gap: var(--sp-2,8px); }
.pw-evidence-link { color: var(--ink-link,var(--link)); font-size: var(--fs-sm,12.5px); font-weight: 650; text-decoration: none; }
.pw-evidence-link:hover { text-decoration: underline; }
.pw-asof-mark { display: inline-flex; align-items: center; min-height: 22px; padding: 2px var(--sp-2,8px); border: 1px solid var(--line); border-radius: var(--r-pill,999px); color: var(--muted); background: var(--panel); font-size: var(--fs-micro,10px); font-weight: 650; }
.pw-asof-mark[data-status="stale"] { color: var(--ink-warn); border-color: color-mix(in srgb, var(--ink-warn) 35%, var(--line)); }
.pw-asof-mark[data-status="corrected"] { color: var(--text); }
.pw-watch { border: 1px solid color-mix(in srgb, var(--link) 32%, var(--line)); background: color-mix(in srgb, var(--link) 9%, var(--panel)); color: var(--ink-link,var(--link)); }
.pw-watch[data-state="pending"] { color: var(--muted); background: var(--panel); }
.pw-watch[data-state="saved"], .pw-watch[data-state="local-only"] { color: var(--text); background: color-mix(in srgb, var(--text) 8%, var(--panel)); }
.pw-watch[data-state="failed"] { color: var(--ink-warn); border-color: color-mix(in srgb, var(--ink-warn) 35%, var(--line)); }
.pw-watch:disabled { border: 0; background: transparent; color: var(--text); opacity: .4; cursor: not-allowed; }
.pw-watch-meta { flex-wrap: wrap; gap: var(--sp-2,8px); margin-top: var(--sp-1,4px); color: var(--muted); font-size: var(--fs-micro,10px); }
.pw-undo { min-height: 32px; padding: 4px var(--sp-2,8px); font-size: var(--fs-micro,10px); background: transparent; }
.pw-lock { position: relative; margin-top: var(--sp-4,16px); border: 1px solid var(--line); border-radius: var(--r-card,12px); background: var(--panel); overflow: hidden; }
.pw-lock-content { padding: var(--sp-3,12px); opacity: .46; filter: blur(5px) saturate(.35); pointer-events: none; user-select: none; }
.pw-tier-gate { position: absolute; inset: 0; display: grid; place-items: center; }
.pw-tier-gate > div { display: flex; align-items: center; justify-content: center; flex-wrap: wrap; gap: var(--sp-2,8px); max-width: 34rem; margin: var(--sp-4,16px); padding: var(--sp-3,12px); border: 1px solid var(--line); border-radius: var(--r-card,12px); background: var(--panel2); box-shadow: var(--shadow-hover); color: var(--text); font-size: var(--fs-sm,12.5px); text-align: center; }
.pw-preview { margin: var(--sp-2,8px) 0 0; border-top: 1px dashed var(--line); padding-top: var(--sp-2,8px); color: var(--text); }
.pw-preview-line { justify-content: space-between; flex-wrap: wrap; gap: var(--sp-2,8px); padding: var(--sp-2,8px) var(--sp-3,12px); border: 1px dashed var(--line); border-radius: var(--r-ctl,8px); background: var(--panel); }
.pw-preview-count { color: var(--muted); font-size: var(--fs-sm,12.5px); }
.pw-preview-cta { min-height: 36px; padding: 7px var(--sp-2,8px); font-size: var(--fs-label,11px); }
.pw-rows[data-loading="true"] .pw-row { background: repeating-linear-gradient(90deg, var(--panel2) 0 7rem, color-mix(in srgb, var(--text) 7%, var(--panel2)) 7rem 8.25rem, var(--panel2) 8.25rem 11rem); color: transparent; }
:where(.pw-row, .pw-ladder button, .pw-watch, .pw-preview-cta, .pw-undo, .pw-fixture-controls button, .pw-tabs a):focus-visible { outline: 2px solid color-mix(in srgb, var(--link) 70%, transparent); outline-offset: 2px; }
html[data-theme="light"] .pw-block { border-color: var(--line); box-shadow: var(--card-shadow); }
html[data-theme="light"] .pw-shell, html[data-theme="light"] .pw-rows, html[data-theme="light"] .pw-ladder { background: var(--panel); }
html[data-theme="light"] .pw-evidence { background: var(--panel); border-color: var(--line); }
html[data-theme="light"] .pw-row[data-degraded="failed"] { background: color-mix(in srgb, var(--ink-warn) 8%, var(--panel)); }
html[data-theme="light"] .pw-watch:disabled { color: var(--text); opacity: .5; border: 1px dashed var(--line); background: transparent; }
html[data-theme="light"] .pw-tier-gate > div { background: var(--panel); box-shadow: var(--card-shadow); }
html[data-theme="light"] .pw-lock-content { background: var(--panel2); }
@media (prefers-reduced-motion: reduce) { .pw-row, .pw-watch, .pw-fixture-controls button, .pw-preview-cta, .pw-undo { transition: none; } .pw-row[aria-expanded="true"] .pw-chevron { transform: none; } }
@media (max-width: 390px) {
  .pw-fixture { padding: var(--sp-3,12px) var(--sp-2,8px) var(--sp-6,24px); }
  .pw-block { padding: var(--sp-3,12px); }
  .pw-fixture-bar, .pw-context-row, .pw-row, .pw-evidence-grid, .pw-evidence-actions, .pw-watch-meta, .pw-preview-line { display: grid; grid-template-columns: 1fr; align-items: start; }
  .pw-fixture-note { margin-right: 0; }
  .pw-asof { margin-left: 0; }
  .pw-track-record { margin-left: 0; border-left: 0; padding-left: 0; }
  .pw-change, .pw-action { min-width: 0; }
  .pw-chevron { position: absolute; right: var(--sp-2,8px); top: var(--sp-2,8px); }
  .pw-ladder ol { grid-template-columns: repeat(2, minmax(0,1fr)); }
  .pw-ladder li { border-bottom: 1px solid var(--line); }
  .pw-tier-gate > div { margin: var(--sp-2,8px); }
}
```


| State | Markup / meaning | EN | ZH |
|---|---|---|---|
| Default / static | `data-surface` names one of four destinations | Action Desk · Radar · All Candidates · Themes · Track Record | 行动台 · 雷达 · 全部候选 · 主题 · 战绩 |
| First-visit empty | shell + designed empty state | Nothing to act on today. Rows appear here when an entry opens. Watch saves research to your list. It does not place a trade. | 今日无可行动项。入场窗口开启时会在此显示。关注会把研究保存到您的列表，不会下单。 |

- Keyboard/focus (§8): `Tab` / `Shift-Tab` traverse destination links; the destination row never captures arrows. One `h1` occurs above the shell; fixture blocks use `h2`.
- Not allowed: a second header or market selector, drawer, pulse, live reorder, or a fifth workspace destination; Track Record remains a separate linked route. The shared `_site_nav` family alone owns the page header.

## CountLadderIdentity

**Purpose (§4):** seven-cell lifecycle identity with honest absent and withheld counts.

```html
<div class="pw-ladder" role="group" aria-label="Lifecycle counts">
  <ol>
    <li><b>3</b><span>Watch</span></li>
    <li><b>2</b><span>Ready</span></li>
    <li><b>1</b><span>Entered</span></li>
    <li><b>1</b><span>Delivering</span></li>
    <li data-absent="true"><b>—</b><span>Overtime</span></li>
    <li><b>1</b><span>Invalidated</span></li>
    <li data-withheld="true"><b>0</b><span>Resolved</span></li>
  </ol>
</div>
```

CSS scope: `.pw-ladder`, its `ol/li/b`, absent and withheld attributes, and the 390px two-column reduction. No lifecycle hue is allowed.

| State | Markup / meaning | EN | ZH |
|---|---|---|---|
| Observed | integer count | Watch · Ready · Entered · Delivering · Overtime · Invalidated · Resolved | 观察 · 就绪 · 入场 · 达标 · 超时 · 失效 · 已结 |
| Absent / empty | `data-absent="true"` and em dash | Published and absent | Published and absent |
| Withheld | `data-withheld="true"` and hatch | Same cell label; no invented number | Same |
| Loading | skeleton at true geometry, no loading words | Count labels remain | Count labels remain |
| Error | `role="alert"` source-loss state | The action list is unavailable. Required data did not load. | 行动列表暂不可用。必需数据未能加载。 |

- Keyboard/focus (§8): selectable production cells are buttons with `aria-pressed`; the list owns vertical arrows. The static index may render read-only cells.
- Not allowed: lifecycle hue, green from a high cell, blended/substituted count, or “stage / 阶段” in user copy.

## AvailabilityStance

**Purpose (§4):** the closed seven-state stance/action pair and state ink.

```html
<span class="pw-stance" data-availability="ENTRY_OPEN"><b>Act</b></span>
<span class="pw-action">Entry open</span>
```

CSS scope: `.pw-stance`, `.pw-action`, `data-availability`, the single green rule, struck `INVALIDATED`, and dashed no-read rule.

| State | Data / visual | EN | ZH |
|---|---|---|---|
| `ENTRY_OPEN` | only green ink / left rule | Act → Entry open | 可行动 → 入场窗口开启 |
| `APPROACHING_ENTRY` | neutral accent, never green | Get ready → Approaching | 准备 → 接近入场 |
| `NOT_READY` | muted | Watch — don't chase → Not ready | 观察，勿追 → 尚未就绪 |
| `WAIT_PULLBACK` | muted | Watch — don't chase → Wait for pullback | 观察，勿追 → 等待回调 |
| `RAN_DONT_CHASE` | muted | Stand aside → Ran — don't chase | 观望 → 已启动，勿追 |
| `INVALIDATED` | struck stance, muted, no red alarm | Ignore → Invalidated | 忽略 → 已失效 |
| `UNAVAILABLE_DATA` / no row | em dash, dashed rule, muted | No read yet → No read yet | 暂无判断 → 暂无判断 |

- Keyboard/focus: stance is text, not a separate control, and is announced with the row.
- Not allowed: green outside `ENTRY_OPEN`, `UNAVAILABLE_FIELD`, “Wait” as missing-read copy, or direction ink used as stance.

## ProphetRow

**Purpose (§4):** five-cell name/change/stance/action/chevron row anatomy, with detail reserved for expansion.

```html
<button class="pw-row" type="button" aria-expanded="false" aria-controls="row-evidence"
  data-availability="WAIT_PULLBACK" data-lifecycle="WATCH" data-sleeve="Setup research">
  <span class="pw-name">EXMPL<small>Setup research</small></span>
  <p class="pw-change">Example demand improved, but the price already ran.</p>
  <span class="pw-stance">Watch — don't chase</span>
  <span class="pw-action">Wait for pullback</span>
  <svg class="pw-chevron" viewBox="0 0 16 16" aria-hidden="true"><path d="M6 4l4 4-4 4"/></svg>
</button>
```

CSS scope: `.pw-row` grid/flex anatomy, name/change/action/chevron, availability rules, stale/failed treatments, loading geometry, and mobile stack.

| State | Markup | EN | ZH |
|---|---|---|
| Collapsed | `aria-expanded="false"` | collapsed line names what opens; chevron points right |
| Expanded | `aria-expanded="true"` plus `aria-controls` | announce Row expanded / 行已展开; chevron rotates |
| No read | `data-availability="UNAVAILABLE_DATA"` | — · No read yet / 暂无判断 |
| Stale | `data-degraded="stale"` | Price is stale / 价格数据已过期 |
| Failed source | `data-degraded="failed"` | Required data did not load. / 必需数据未能加载。 |
| Invalidated | `data-availability="INVALIDATED"` | Ignore is struck; no red alarm |
| Loading | parent `data-loading="true"` | true geometry, no loading words |
| Sleeve-tagged | `data-sleeve` and visible plain name | read-only research tag; no holding or trade language |

- Keyboard/focus (§8): list owns `↑` / `↓`; `Enter` / `Space` expand the row; focus remains on the row.
- Not allowed: `.mx-chg-row` for this anatomy, drawer disclosure, duplicate change sentences, or holdings language.

## ExpandedEvidenceRow

**Purpose (§4):** inline evidence, implications, risks, conditions, and actions in one row-owned disclosure.

```html
<div class="pw-evidence" id="row-evidence" role="region" aria-label="Example evidence">
  <div class="pw-evidence-grid">
    <section class="pw-evidence-col" aria-label="Evidence and implications"></section>
    <section class="pw-evidence-col" aria-label="Risks, conditions and actions"></section>
  </div>
  <div class="pw-evidence-actions"><a class="pw-evidence-link" href="/prophet/EXMPL">Full dossier at /prophet/EXMPL</a></div>
</div>
```

CSS scope: `.pw-evidence`, `.pw-evidence-grid`, `.pw-evidence-col`, `.pw-evidence-actions`, `.pw-evidence-link`, luminance/hairline theme rules, and one-column mobile reduction.

| State | Behavior / EN | ZH |
|---|---|---|
| Expanded | two columns at ≥1024px; evidence/implications left, risks/conditions/actions right | 同一信息顺序 |
| Collapsed | no hidden duplicate evidence; row button owns disclosure | 同 |
| Missing field/read | — · No read yet; No source note yet | — · 暂无判断；暂无来源说明 |
| Stale | Price is stale | 价格数据已过期 |
| Corrected | Corrected · prior value available, with prior value keyboard/tap reachable | 已更正 · 可查看原值 |
| Loading | skeleton at evidence geometry; labels and order retained | 同 |
| Error | Required data did not load.; surviving sections remain visible | 必需数据未能加载。 |
| Hydration mismatch | This page cannot finish loading safely. Refresh it. | 此页面无法安全完成加载。请刷新。 |

- Keyboard/focus (§8): expanded body owns `←` / `→`; evidence/action cells are focus stops. The dossier never replaces inline evidence.
- Not allowed: overlay disclosure, hiding failed facts, accepting a mismatched generation, or reordering on mismatch.

## ResearchOnlyChip

**Purpose (§4):** read-only strategy-status statement that no permission is granted.

```html
<span class="pw-chip">Research only</span>
```

CSS scope: `.pw-chip` neutral pill, border, and theme-role text treatment.

| State | EN | ZH |
|---|---|---|
| Default | Research only | 仅研究 |

- Keyboard/focus: static text; no focus stop.
- Not allowed: “Promoted / 晋级”, “Control / control-only”, permission implications, or interactive strategy selection. A strategy plain name may appear separately as a read-only sleeve tag.

## AsOfStamp

**Purpose (§4):** one publication stamp plus stale and corrected marks.

```html
<span class="pw-asof-mark">As of Sep 24, 2026 09:05 PDT</span>
<span class="pw-asof-mark" data-status="stale">Price is stale</span>
<span class="pw-asof-mark" data-status="corrected">Corrected · prior value available</span>
```

CSS scope: `.pw-asof` and `.pw-asof-mark`, stale ink, corrected state, tabular figures, and one-stamp placement.

| State | EN | ZH |
|---|---|---|
| Fresh bake | As of Sep 24, 2026 09:05 PDT | 数据截至 2026年9月24日 09:05 PDT |
| Stale | Price is stale | 价格数据已过期 |
| Corrected | Corrected · prior value available | 已更正 · 可查看原值 |

- Keyboard/focus: corrected prior value is keyboard/tap reachable as well as hover; the stamp is not interactive.
- Not allowed: duplicate page stamps, pulse/live wording, translated `title=`, or rewriting corrected history in place.

## WatchAction

**Purpose (§4):** the visible WatchStore save action, its disabled reason, and saved states.

```html
<button class="pw-watch" type="button" data-state="idle">Watch</button>
<div class="pw-watch-meta"><span>Removed from Example list</span><button class="pw-undo" type="button">Undo</button></div>
```

CSS scope: `.pw-watch`, every `data-state`, disabled state, `.pw-watch-meta`, `.pw-undo`, focus ring, and reduced-motion rule.

| State | Behavior | EN | ZH |
|---|---|---|---|
| idle | click opens owner list chooser | Watch | 关注 |
| pending | wait state; retry remains possible after failure | Saving your list choice… | 正在保存您的列表选择… |
| saved | only after successful WatchStore write | Saved to <list> | 已保存至 <list> |
| failed | retry; never Saved | Your list choice did not save. Try again. | 您的列表选择未保存。请重试。 |
| unwatched | list-scoped tombstone plus Undo; pull never resurrects | Removed from <list> | 已从 <list> 移除 |
| local-only | visible offline fact | Saved on this device only | 仅保存在此设备 |
| disabled | visible control, no promise or decision ID | Not saved yet | 暂未保存 |
| watch failure | assertive failure state | Your change did not save. Try again. | 您的更改未保存。请重试。 |

- Keyboard/focus: 40px minimum target; chooser, retry, and Undo are keyboard reachable. Pending is polite status; failure is assertive.
- Not allowed: Prophet-only save format, global removal mark, Saved from a read, or buy/sell/position/fill/order/trade wording.

## TierLockProphet

**Purpose (§4):** honest entitlement boundary composed over `.mx-tier-gate--prophet`.

```html
<div class="pw-lock">
  <div class="pw-lock-content" aria-hidden="true"><!-- true-shape teaser --></div>
  <div class="pw-tier-gate"><div class="mx-tier-gate mx-tier-gate--prophet"><!-- incumbent gate --></div></div>
</div>
```

CSS scope: `.pw-lock`, `.pw-lock-content`, `.pw-tier-gate`, overlay centering, linked incumbent tier classes, and light white-material treatment.

| State | Behavior | EN | ZH |
|---|---|---|---|
| Locked | inert true-shape teaser plus visible incumbent gate | Gate copy is incumbent-controlled | Gate copy is incumbent-controlled |
| Preview boundary | count and lock join stay visible | Example count: 1 | 示例数量：1 |
| No access | plan boundary sentence | You have reached the limit for this plan. | 您已达到当前方案的上限。 |

- Keyboard/focus: teaser is `aria-hidden` and unfocusable; only incumbent gate actions are focusable.
- Not allowed: new flag/release plane, silent disappearance, synthetic entitled evidence, paywall flip, production DDL, or a third lock family.

## PreviewRowState

**Purpose (§4):** governed preview remainder and lock join under incumbent rollout controls.

```html
<div class="pw-preview">
  <div class="pw-preview-line">
    <span class="pw-preview-count">Example count: 1</span>
    <button class="pw-preview-cta" type="button">You have reached the limit for this plan.</button>
  </div>
</div>
```

CSS scope: `.pw-preview`, `.pw-preview-line`, `.pw-preview-count`, `.pw-preview-cta`, preview row rules, and mobile stacking.

| State | Behavior | EN | ZH |
|---|---|
| Preview | visible row keeps its own count and lock join |
| Locked remainder | locked rows are visible as governed preview, never silently removed |
| Empty | No records are ready to show yet. / 暂无可以展示的记录。 |

- Keyboard/focus: preview CTA is one 36px-minimum control; it is outside row arrow ownership. The fixture's 36px is below the 40px touch floor and is corrected by production to 40px; the visual rule is retained for density comparison.
- Not allowed: hidden count, a new toggle, claims beyond incumbent `premium.enforced_early` disclosure, or deleting rows when gate state changes.

## COMPOSITION RECIPES

All recipes keep shared authenticated navigation, `ResearchOnlyChip`, one stamp, the ladder, and the destination row. Density follows DS §9: at 1440×900, chrome + answer + at most two supporting modules; at 390, the answer is within one swipe; L1 sections remain ≤7 and raw L1 tables show ≤8 rows plus counted remainder.

| Recipe | Assembly | Density / behavior |
|---|---|---|
| A. Action Desk 1440 EN dark | Shell(surface=action) → ladder → tab row → rows; expanded evidence two columns | answer + ladder; first rows visible; green rule only on `ENTRY_OPEN`; expanded body `--panel2` |
| B. Action Desk 390 ZH light | Same components, mobile grid; evidence one column in same order | shared nav → tabs → first row answer; no horizontal page scroll |
| C. Radar 390 ZH dark | Shell(surface=radar) → ladder → tabs → fresh candidate rows | dotted leading rule; no lifecycle hue; one row answer within swipe |
| D. All Candidates 1440 EN light | Shell(all) → ladder → tabs → dense rows; lifecycle remains separate text column | ≤8 L1 rows + counted remainder; hairline rows; no zebra in light |
| E. Themes 1440 ZH dark | Shell(themes) → ladder → grouped rows | group headers on canvas, group bodies one luminance step; ladder identity remains |
| F. Track Record 390 EN light | Shell(track) → stamp → editorial record rows → Watch disabled | no workspace tab for Track Record; evidence, correction, and no-trade meaning survive |

Dark/light mechanisms (§5, §6, R-G): Action Desk uses luminance depth versus white material + hairlines; Radar withholds a luminance step versus white material; All Candidates uses luminance zebra versus hairline-only; Themes uses nested luminance versus canvas/panel; Track Record uses luminance dividers versus hairlines. Seven degraded states are repeated per theme in the component tables and fixture.

## FIXTURE INDEX

The fixture implements both art directions with the theme toggle and both languages with the language toggle. It is a component index, not a 40-cell capture suite; B16 still owes the packet's five-surface × dark/light × EN/ZH × 1440/390 captures.

| Block | Component × state | Theme / language coverage |
|---|---|---|
| 1 | `ProphetWorkspaceShell` default/static + first-visit empty | both via root toggles |
| 2 | `CountLadderIdentity` observed, absent, withheld, loading, error, empty | both via root toggles |
| 3 | `AvailabilityStance` all seven states | both via root toggles |
| 4 | `ProphetRow` collapsed, expanded, no-read, stale, failed, sleeve | both via root toggles |
| 5 | `ExpandedEvidenceRow` expanded, missing, stale, corrected, loading/error contract, hydration mismatch | both via root toggles |
| 6 | `ResearchOnlyChip` default | both via root toggles |
| 7 | `AsOfStamp` fresh, stale, corrected | both via root toggles |
| 8 | `WatchAction` idle, pending, saved, failed, unwatched tombstone + Undo, local-only, disabled, watch failure | both via root toggles |
| 9 | `TierLockProphet` locked + preview | both via root toggles |
| 10 | `PreviewRowState` preview, locked remainder, empty | both via root toggles |

## OPEN QUESTIONS FOR THE SEAT

1. The two DS-PR-0 authority files named by the frozen prompt are absent from source `origin/main`. Should B20-1 proceed against the current role-token/fallback truth, or should the seat repoint this unit after DS-PR-0a lands?
2. §8.1 gives no exact EN/ZH strings for non-empty row change sentences, evidence headings, list names, theme names, lifecycle header, count/preview labels, destination labels, or lock CTA text. The fixture uses only obvious fake data, existing route names, or packet copy; production must bind these strings to a bilingual owner and must not copy fixture prose unchecked.
3. The packet gives no visual copy for a withheld lifecycle count; B20-1 uses zero plus a hatched treatment and does not invent prose. Confirm or supply wording.
4. The fixture cannot demonstrate true browser keyboard traversal or hover/tap-only prior corrected value in static markup; these remain builder acceptance work under §8 and DS §14.
5. `PreviewRowState` visual density uses a 36px CTA, but DS §14 requires a 40px touch target. Confirm the production correction to 40px.

## EVIDENCE

Commands below were run from the worktree root. Outputs are the observed summary lines.

1. `python3 scripts/worktree_sparse.py add mockups` → `worktree-sparse: materialized mockups`
2. `python3 scripts/agentos.py validate 2>&1 | tail -n 3` → `agentos: 1226 records (69 workstreams, 349 decisions, 308 discoveries, 500 handoffs) — 0 error(s), 87 warning(s)`
3. Direct token grep (`rg -n -- '--sp-[145678]|--gap-grid|--t-med|--t-slow|--ease-std|--ease-lift|--shadow-hover|--ser-[1-4]|--ink-tier|--ink-prov|\.mx-tbl|\.mx-tblbox|\.mx-tabset|\.mx-rail' templates/theme.css`) → no definitions at source SHA; only fallback consumers elsewhere.
4. `python3 scripts/check_design_system.py --mode report --root . 2>&1 | tail -n 3` → `templates/winner_health.html.j2:1015: literal-custom-property: --w: %">`, `templates/winner_health.html.j2:397: inline-style-bytes: 23410 bytes of inline <style>`, `templates/winner_health.html.j2:411: parallel-token-root: :root block declares a custom property outside theme.css`
5. Literal scanner (`python3` scan of the fixture `<style>`) → `color literals: 0; px radius literals: 0; duration literals: 0`
6. `python3 scripts/check_validated_claims.py --help` has no path argument; `--list` in this required-sparse checkout → `::error title=allowlist-missing::data/regime/validated_claims_allowlist.json is absent — this checkout cannot answer which 'validated' claims are backed.`
7. `grep -n -E '(UNAVAILABLE_FIELD|producer|nomination|episode)' mockups/prophet_workspace/b20_1_fixture.html` → exit 1, no hits.
8. `grep -c 'title="' mockups/prophet_workspace/b20_1_fixture.html` → `0` (grep exit 1 when count is zero).
9. CSS identity command: `diff <(sed -n '/^```css$/,/^```$/p' research/prophet_v4/r6_program/wave3/B20_1_COMPONENT_SPEC_2026-09-24.md | sed '1d;$d') <(sed -n '/<style>/,/<\/style>/p' mockups/prophet_workspace/b20_1_fixture.html | sed '1d;$d')` → no output.
10. Fixture block count: 10 component-index blocks.

## GAPS

1. B16 captures and comprehension tests are not owed by B20-1 and remain open.
2. No production route, template, payload, permission, price, chart, or data owner is added.
3. The DS-PR-0 authority-file discrepancy is recorded under OPEN QUESTIONS; no unseen token landing is assumed.
4. Static fixture keyboard/hover behavior is specified but not executable beyond the two permitted toggles.
