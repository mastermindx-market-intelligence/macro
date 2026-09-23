## SOURCE_SHA

- **B20 v2 packet:** `origin/main` at `366533a9c21f` (`research/prophet_v4/r6_program/wave1/B20_DESIGN_PACKET_V1_2026-09-23.md`).
- **DS-PR-0a prerequisite:** PR #7849 merge ref `f6e49ea0b15315598eac18213ba7cc6b89bb2b3f` (head `4a1be688dba0ad195db909d849100fab8124becb`); this branch merges the exact merge ref. R6-B20-02 §Ruling says: “B20-1 onward may start on 0a's merge sha.”
- **This specification head is recorded in `## EVIDENCE`; `SOURCE_SHA` is immutable source lineage, not the mutable branch head.**

## TOKEN TRUTH

Verified against `templates/theme.css` **after** the prerequisite merge.

| Truth | Names / evidence |
|---|---|
| Landed tokens | `--sp-1/4/5/6/7/8`, `--gap-grid`, `--t-med`, `--t-slow`, `--ease-std`, `--ease-lift`, `--shadow-hover`, `--ser-1..4`, `--ink-tier`, `--ink-prov` (`templates/theme.css:63-75, 217-218, 502, 505`). |
| Landed primitive classes | `.mx-tbl`, `.mx-tblbox`, `.mx-tabset`, `.mx-rail`, `.mx-ladder` (including `.mx-ladder--board`), `.mx-chg-row`, `.mx-empty`, `.mx-error`, `.skel` (`templates/theme.css:2024-2205`). |
| Deferred tokens | `--sp-2`, `--sp-3`, `--r-ctl`, `--r-btn`, `--r-card`, `--r-panel`, `--r-pill`, `--t-fast`; every use below carries its value-equal fallback (`8px`, `12px`, `8px`, `10px`, `12px`, `14px`, `999px`, `.16s`, respectively). |
| Deferred classes | `.mx-vh`, `.mx-sec`, `.mx-callout`, `.mx-disc` are never used. Composition uses landed primitives plus `pw-*`. |
| Binding token ruling | `R6-B20-02_DSPR0_SPLIT_2026-09-23.md` §Ruling and `DSPR0A_LANDING_RECORD_2026-09-23.md` §WHAT LANDED / §DEFERRED. |

## ProphetWorkspaceShell

**Purpose (§4):** shared context, route links, and responsive destination row.

```html
<nav class="site-nav" aria-label="Site navigation"><!-- shared _site_nav family; no workspace header band --></nav>
<div class="pw-shell" data-surface="action-desk|radar|all-candidates|themes">
  <div class="pw-context">
    <h1 class="pw-title">Prophet US / Prophet 美国</h1>
    <span class="pw-chip">Research only / 仅研究</span>
    <span class="pw-asof">As of <bake-time> / 数据截至 <bake-time></span>
  </div>
  <nav class="pw-tabs" aria-label="Workspace destinations">
    <a href="#action-desk">Action Desk / 行动台</a>
    <a href="#radar">Radar / 雷达</a>
    <a href="#all-candidates">All Candidates / 全部候选</a>
    <a href="#themes">Themes / 主题</a>
    <a class="pw-track-record" href="/us_track_record.html">Track Record / 战绩</a>
  </nav>
  <main class="pw-main"><!-- surface components --></main>
</div>
```

```css
.pw-harness{display:flex;flex-wrap:wrap;align-items:center;gap:var(--sp-2,8px);margin:0 0 var(--sp-4,16px)}
.pw-harness button{appearance:none;border:1px solid var(--line);border-radius:var(--r-btn,10px);min-height:40px;padding:9px var(--sp-3,12px);font:650 var(--fs-sm)/1 var(--font-ui);color:var(--text);background:var(--panel);cursor:pointer}
.pw-shell{display:grid;gap:var(--sp-3,12px);color:var(--text);background:var(--bg);border:1px solid var(--line);border-radius:var(--r-panel,14px);padding:var(--sp-4,16px)}
.pw-context{display:flex;align-items:baseline;gap:var(--sp-2,8px);flex-wrap:wrap}
.pw-title{margin:0;font-size:var(--fs-h2);line-height:1.2}
.pw-context-row{display:flex;align-items:center;gap:var(--sp-2,8px);flex-wrap:wrap}
.pw-tabs{display:flex;align-items:center;gap:var(--sp-1,4px);overflow-x:auto;padding-bottom:var(--sp-1,4px);border-bottom:1px solid var(--line)}
.pw-tabs a{flex:none;min-height:40px;display:inline-flex;align-items:center;padding:9px var(--sp-2,8px);border-radius:var(--r-ctl,8px);color:var(--muted);font:650 var(--fs-sm)/1 var(--font-ui);text-decoration:none}
.pw-tabs a[aria-current="page"]{color:var(--text);background:color-mix(in srgb,var(--text) 8%,var(--panel))}
.pw-track-record{margin-left:auto}
.pw-main{display:grid;gap:var(--sp-4,16px)}
.pw-block{display:grid;gap:var(--sp-3,12px);padding:var(--sp-3,12px);border:1px solid var(--line);border-radius:var(--r-card,12px);background:var(--panel)}
.pw-block>h2{margin:0;color:var(--text);font-size:var(--fs-h3);line-height:1.25}
.pw-stack{display:grid;gap:var(--sp-2,8px)}
.mx-ladder.pw-identity{min-width:0}
.pw-lad-count{color:var(--muted)}
.pw-lad-count[data-absent="true"]{color:var(--muted);font-style:italic}
.pw-lad-count[data-withheld="true"]{background:repeating-linear-gradient(135deg,var(--panel) 0 5px,color-mix(in srgb,var(--line) 40%,var(--panel)) 5px 10px)}
.pw-stance{display:inline-flex;align-items:center;gap:var(--sp-1,4px);min-height:40px;padding:7px var(--sp-2,8px);border:1px solid var(--line);border-radius:var(--r-pill,999px);color:var(--text);font:700 var(--fs-label)/1 var(--font-ui)}
.pw-stance small{font:650 var(--fs-label)/1 var(--font-ui);color:var(--muted)}
.pw-stance[data-availability="APPROACHING_ENTRY"]{color:var(--ink-link,var(--link));border-color:color-mix(in srgb,var(--link) 35%,var(--line))}
.pw-stance[data-availability="NOT_READY"],.pw-stance[data-availability="WAIT_PULLBACK"],.pw-stance[data-availability="RAN_DONT_CHASE"]{color:var(--muted);background:var(--panel)}
.pw-stance[data-availability="INVALIDATED"]{color:var(--muted)}
.pw-stance[data-availability="INVALIDATED"] b{text-decoration:line-through}
.pw-stance[data-availability="UNAVAILABLE_DATA"]{color:var(--muted);border-style:dashed;background:var(--panel)}
.pw-stance[data-availability="ENTRY_OPEN"]{color:var(--ink-ok);border-color:color-mix(in srgb,var(--ink-ok) 38%,var(--line));background:color-mix(in srgb,var(--ink-ok) 9%,var(--panel))}
.pw-rows{display:grid;gap:var(--sp-2,8px)}
.pw-row{display:grid;grid-template-columns:minmax(72px,auto) minmax(0,1fr) auto auto 28px;align-items:center;gap:var(--sp-2,8px);min-height:44px;padding:9px var(--sp-2,8px);border:1px solid var(--line);border-left-width:3px;border-left-style:solid;border-left-color:var(--line);border-radius:var(--r-ctl,8px);background:var(--panel2);color:inherit;font:inherit;text-align:left;cursor:pointer}
.pw-row:hover{background:color-mix(in srgb,var(--text) 5%,var(--panel2))}
.pw-name{font:750 var(--fs-sm)/1.1 var(--font-ui)}
.pw-change{margin:0;color:var(--muted);font-size:var(--fs-sm);line-height:1.25}
.pw-row-action{color:var(--muted);font:650 var(--fs-label)/1.2 var(--font-ui)}
.pw-chevron{justify-self:end;color:var(--muted);font-size:var(--fs-sm);transition:transform var(--t-med,.2s) var(--ease-std)}
.pw-row[aria-expanded="true"] .pw-chevron{transform:rotate(90deg)}
.pw-row[data-availability="ENTRY_OPEN"]{border-left-color:var(--ink-ok)}
.pw-row[data-availability="UNAVAILABLE_DATA"]{border-left-style:dashed}
.pw-row[data-availability="INVALIDATED"] .pw-name{text-decoration:line-through;color:var(--muted)}
.pw-row[data-stale="true"] .pw-change{color:var(--muted);border-bottom:1px solid color-mix(in srgb,var(--ink-warn) 55%,var(--line))}
.pw-row[data-corrected="true"] .pw-name::after{content:"†";color:var(--muted);font-weight:400}
.pw-row[data-preview="true"]{border-left-style:dashed;background:var(--panel)}
.pw-row[data-loading="true"]{cursor:default;pointer-events:none}
.pw-load{display:block;height:12px;border-radius:var(--r-ctl,8px)}
.pw-load--short{width:40%}
.pw-load--long{width:82%}
.pw-evidence{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:var(--sp-3,12px);padding:var(--sp-3,12px);border:1px solid var(--line);border-radius:var(--r-card,12px);background:var(--panel2)}
.pw-evidence[hidden]{display:none}
.pw-evidence-col{display:grid;gap:var(--sp-2,8px);align-content:start}
.pw-evidence-col h3{margin:0;color:var(--muted);font-size:var(--fs-label);line-height:1.2}
.pw-evidence-col dl{margin:0;display:grid;gap:var(--sp-2,8px)}
.pw-evidence-col dt{color:var(--muted);font-size:var(--fs-micro)}
.pw-evidence-col dd{margin:0;font-size:var(--fs-sm);line-height:1.35}
.pw-evidence-link{justify-self:start;min-height:40px;display:inline-flex;align-items:center;color:var(--ink-link,var(--link));font-size:var(--fs-sm);text-decoration:none;text-decoration:underline;text-underline-offset:3px}
.pw-evidence[data-state="missing"]{border-style:dashed}
.pw-evidence[data-state="loading"] .skel{display:block;height:12px}
.pw-evidence[data-state="error"]{border-color:color-mix(in srgb,var(--ink-warn) 40%,var(--line))}
.pw-chip{display:inline-flex;align-items:center;min-height:24px;padding:4px var(--sp-2,8px);border:1px solid var(--line);border-radius:var(--r-pill,999px);color:var(--muted);background:var(--panel);font:700 var(--fs-micro)/1 var(--font-ui)}
.pw-asof{display:inline-flex;align-items:center;gap:var(--sp-1,4px);color:var(--muted);font-size:var(--fs-micro);font-variant-numeric:tabular-nums}
.pw-asof-mark{display:inline-flex;min-height:24px;align-items:center;padding:3px var(--sp-1,4px);border-radius:var(--r-pill,999px);font-size:var(--fs-micro)}
.pw-asof-mark[data-status="stale"]{color:var(--ink-warn);border-bottom:1px solid color-mix(in srgb,var(--ink-warn) 55%,var(--line))}
.pw-asof-mark[data-status="corrected"]{color:var(--muted)}
.pw-watch-panel{display:grid;gap:var(--sp-2,8px)}
.pw-watch{justify-self:start;appearance:none;min-height:40px;border:1px solid var(--line);border-radius:var(--r-btn,10px);padding:9px var(--sp-3,12px);color:var(--text);background:var(--panel);font:700 var(--fs-sm)/1 var(--font-ui);cursor:pointer;transition:background var(--t-med,.2s) var(--ease-std)}
.pw-watch:hover{background:color-mix(in srgb,var(--text) 7%,var(--panel))}
.pw-watch:disabled{opacity:.4;border-color:var(--line);cursor:default}
.pw-watch[data-state="pending"]{color:var(--muted)}
.pw-watch[data-state="saved"],.pw-watch[data-state="local-only"]{color:var(--text);background:color-mix(in srgb,var(--text) 7%,var(--panel))}
.pw-watch[data-state="failed"]{color:var(--ink-warn);border-color:color-mix(in srgb,var(--ink-warn) 40%,var(--line))}
.pw-watch-meta{color:var(--muted);font-size:var(--fs-sm)}
.pw-undo{appearance:none;min-height:40px;border:0;padding:9px var(--sp-2,8px);color:var(--ink-link,var(--link));background:var(--panel);font:700 var(--fs-sm)/1 var(--font-ui);cursor:pointer}
.pw-tier{position:relative;overflow:hidden;border-radius:var(--r-card,12px)}
.pw-tier-ghost{padding:var(--sp-4,16px);filter:blur(var(--sp-1,4px)) saturate(.35);opacity:.46;pointer-events:none;user-select:none}
.pw-tier .mx-tier-gate{margin:0}
.pw-tier[data-state="preview"] .mx-tier-gate{border-style:dashed}
.pw-preview{display:flex;align-items:center;gap:var(--sp-2,8px);min-height:44px;padding:9px var(--sp-2,8px);border-left:3px dashed var(--line);border-radius:var(--r-ctl,8px);background:var(--panel);color:var(--muted);font-size:var(--fs-sm)}
.pw-preview b{color:var(--text);font-variant-numeric:tabular-nums}
.pw-preview[data-state="locked"] .pw-tier-ghost{display:none}
:where(.pw-harness button,.pw-tabs a,.mx-ladder.pw-identity .mx-cell,.pw-row,.pw-evidence-link,.pw-watch,.pw-undo):focus-visible{outline:2px solid var(--ink-link,var(--link));outline-offset:2px}
html[data-theme="light"] .pw-shell{background:var(--bg)}
html[data-theme="light"] .pw-block{background:var(--panel);box-shadow:var(--card-shadow)}
html[data-theme="light"] .pw-row{background:var(--panel);box-shadow:var(--card-shadow)}
html[data-theme="light"] .pw-evidence{background:var(--panel)}
html[data-theme="light"] .pw-row:hover{background:var(--panel)}
html[data-theme="light"] .pw-row[data-preview="true"]{box-shadow:none;border-style:solid;border-left-style:dashed}
html[data-theme="light"] .pw-watch:disabled{opacity:.5;border-style:dashed}
html[data-theme="light"] .pw-tier-ghost{filter:blur(var(--sp-1,4px)) saturate(.3);opacity:.5}
@media (min-width:1440px){.pw-shell{padding:var(--sp-5,20px);gap:var(--sp-4,16px)}.pw-main{gap:var(--sp-5,20px)}}
@media (max-width:1023px){.pw-evidence{grid-template-columns:minmax(0,1fr)}}
@media (max-width:390px){.pw-shell{padding:var(--sp-2,8px);border-radius:var(--r-card,12px)}.pw-context,.pw-context-row{display:grid;grid-template-columns:minmax(0,1fr)}.pw-tabs{margin:0 calc(-1 * var(--sp-2,8px));padding-left:var(--sp-2,8px);padding-right:var(--sp-2,8px)}.pw-track-record{margin-left:0}.pw-row{grid-template-columns:minmax(0,1fr) auto;row-gap:var(--sp-1,4px)}.pw-name{grid-column:1}.pw-change{grid-column:1 / -1}.pw-stance{grid-column:1;justify-self:start}.pw-row-action{grid-column:2;grid-row:1}.pw-chevron{grid-column:2;grid-row:2}}
@media (prefers-reduced-motion:reduce){.pw-chevron{transition:none}.pw-row:hover{background:inherit}}
```

**State table:** default desktop; 1440+ density; 390 horizontal-scroll destination row. Four destinations are tabs on `/us_stocks.html`; Track Record is a separate-route link (§2; R-B). No drawer exists (R-B). No header band, market selector, or strategy toggle (R-C).

**Copy:** `Prophet US / Prophet 美国` is the composition title from packet §7 A–F. Destination names and Track Record are frozen by §2 and shown in §7. §8.1 supplies Research only and Publication stamp. A final production heading sentence is an OPEN QUESTION.

**Keyboard/focus (§8):** `Tab` / `Shift-Tab` traverse destinations; destination row never captures arrows. The shared site nav remains the only header. Focus-visible is specified in CSS.

**Not allowed:** a third header, drawer, workspace header band, second market selector, Promoted toggle, removed marks at 390, horizontal page scroll (R-B/R-C; design system §15).

## CountLadderIdentity

**Purpose (§4):** seven-cell lifecycle identity with honest absent and withheld counts.

```html
<div class="mx-ladder mx-ladder--board pw-identity" role="group" aria-label="Lifecycle counts / 生命周期计数">
  <button class="mx-cell" type="button" data-life="watch" aria-pressed="false">
    <span class="mx-cell-n">21</span><span class="mx-cell-l">Watch / 观察</span>
  </button>
  <!-- ready, entered, delivering, overtime follow in frozen order -->
  <button class="mx-cell mx-cell--last-live" type="button" data-life="invalidated" data-absent="true">
    <span class="mx-cell-n">—</span><span class="mx-cell-l">Invalidated / 失效</span>
  </button>
  <button class="mx-cell" type="button" data-life="resolved" data-withheld="true">
    <span class="mx-cell-n">12</span><span class="mx-cell-l">Resolved / 已结</span>
  </button>
</div>
```

**CSS:** no component-defined ladder geometry: **the ladder must reuse `.mx-ladder`**, specifically `.mx-ladder--board`; `pw-identity` may set only `min-width:0`, while `pw-lad-count` may carry absent/withheld ink and material states from the shell CSS above. A loading count uses `.skel`, never a dash or zero. Source geometry remains `templates/theme.css` `.mx-ladder--board`.

**State table:** live count; published-and-absent (`—` + `data-absent`); withheld (`data-withheld`, ghost material); loading (count skeleton); error (`.mx-error` beside the unchanged ladder). Cells and labels are Watch · Ready · Entered · Delivering · Overtime · Invalidated · Resolved, verbatim from packet §3 and MP-1 §4b. The terminal Resolved count remains outside the live sum (MP-1 §4b).

**Keyboard/focus:** native ladder buttons; focus ring inherited from `.mx-ladder--board`; static cells may be `div` when no filter is offered.

**Not allowed:** `.pw-ladder`; a second ladder family; hue as lifecycle meaning; absent/withheld conflated with zero; a loading dash (R-F; MP-1 §4b/§10; landing record §DEFERRED).

## AvailabilityStance

**Purpose (§4):** the closed seven-state stance/action pair and state ink.

```html
<span class="pw-stance" data-availability="ENTRY_OPEN">
  <b>Act / 可行动</b><small>Entry open / 入场窗口开启</small>
</span>
```

**CSS:** `pw-stance` and every `data-availability` rule in the shared CSS above.

**State table (§3, verbatim):** ENTRY_OPEN → Act / Entry open → only green; APPROACHING_ENTRY → Get ready / Approaching → accent, never green; NOT_READY → Watch — don't chase / Not ready → muted; WAIT_PULLBACK → Watch — don't chase / Wait for pullback → muted; RAN_DONT_CHASE → Stand aside / Ran — don't chase → muted; INVALIDATED → Ignore / Invalidated → struck, muted, no red; UNAVAILABLE_DATA → No read yet twice → muted, dashed rule.

**Keyboard/focus:** non-interactive disclosure; when it names a cell it is not a focus target. Copy is readable, not color-only.

**Not allowed:** green outside ENTRY_OPEN; collapsed ladder/availability axes; raw machine state words; blank missing reads; red-invalid alarm styling (R-A/R-F; §3).

## ProphetRow

**Purpose (§4):** name · ≤14-word change · stance verb · action label · chevron.

```html
<button class="pw-row" type="button" aria-expanded="false"
  aria-controls="<evidence-id>" data-availability="WAIT_PULLBACK"
  data-stale="true" data-corrected="true" data-preview="true" data-loading="true">
  <span class="pw-name">EXMPL</span>
  <p class="pw-change">No source note yet. / 此字段暂无来源说明。</p>
  <span class="pw-stance" data-availability="WAIT_PULLBACK"><b>Watch — don't chase</b></span>
  <span class="pw-row-action">Wait for pullback</span>
  <span class="pw-chevron" aria-hidden="true">›</span>
</button>
```

**CSS:** `pw-row` anatomy and all stale, corrected, invalidated, unavailable, preview, and loading rules in the shared CSS above.

**State table:** collapsed; expanded; loading (skeleton anatomy, no interaction); each of the seven availability states; stale (`data-stale`); corrected (`data-corrected` + AsOf correction mark); preview (`data-preview` + PreviewRowState); invalidated (struck stance/name, muted); no-read default (dashed rule). Fixture data is fake and uses `EXMPL` only.

**Copy:** row change examples in packet §7 A–F are compositional examples, not frozen component copy; missing field/read twins come from §8.1. Final production change sentences are OPEN QUESTIONS. Do not invent scores, prices, or returns.

**Keyboard/focus (§8):** list owns `↑`/`↓`; row is a native button; expanded row owns `←`/`→`; local expansion announces Row expanded / collapsed.

**Not allowed:** `.mx-chg-row` as row anatomy; drawer/side pane; overwriting theme cascade; blended confidence; a 36px target; page-level horizontal scroll (§4; R-B; design system §14/§15).

## ExpandedEvidenceRow

**Purpose (§4):** inline two-column evidence, risks, conditions, and actions.

```html
<div class="pw-evidence" id="<evidence-id>" data-state="fresh|missing|stale|corrected|loading|error"
  role="region" aria-label="<exact state sentence from §8.1>">
  <section class="pw-evidence-col"><p>No source note yet / 暂无来源说明</p></section>
  <section class="pw-evidence-col"><p>Entry open / 入场窗口开启</p>
    <a class="pw-evidence-link" href="/prophet/EXMPL">Full dossier at /prophet/EXMPL / 完整档案 /prophet/EXMPL</a>
  </section>
</div>
```

**CSS:** expansion grid, missing/loading/error rules, evidence link, and 1024/390 reductions in the shared CSS above.

**State table:** fresh; missing (dashed, No read yet); stale (AsOf stale mark); corrected (AsOf corrected mark, prior remains hover/tap reachable); loading (distinct skeleton, no words); error (`.mx-error`, exact failed-source sentence); collapsed (`hidden`). Two columns at ≥1024; one column in the same order below (§2).

**Copy:** only §8.1 strings shown above. Evidence field labels, opposition labels, and panel headings are not supplied by §8.1 and remain OPEN QUESTIONS; the fixture renders only exact §8.1 values plus the dossier contract. `Full dossier at /prophet/<T>` is verbatim §8.1.

**Keyboard/focus (§8):** `←`/`→` move between evidence and action cells; dossier link is reachable; expansion is local.

**Not allowed:** overlay/drawer, page hop as inline evidence, duplicated full dossier, missing-read blank, hover-only correction, or “Wait” (R-B/§1/§5/§6).

## ResearchOnlyChip

**Purpose (§4):** read-only statement that no permission is granted.

```html
<span class="pw-chip">Research only / 仅研究</span>
```

**CSS:** `pw-chip` in the shared CSS above.

**State table:** default only. It appears at the tab row trailing end and in this static fixture header; no selected, active, or disabled state exists (R-C).

**Copy:** Research only / 仅研究 (§8.1, verbatim).

**Keyboard/focus:** noninteractive; never a toggle.

**Not allowed:** Promoted toggle, Research/Promoted toggle, execution language, or hiding the chip on any surface (R-C).

## AsOfStamp

**Purpose (§4):** one publication stamp and stale/corrected marks.

```html
<span class="pw-asof"><time datetime="<ISO>">As of <date time> / 数据截至 <date time></time></span>
<span class="pw-asof-mark" data-status="stale">Price is stale / 价格数据已过期</span>
<span class="pw-asof-mark" data-status="corrected">Corrected · prior value available / 已更正 · 可查看原值</span>
```

**CSS:** stamp, stale, and corrected rules in the shared CSS above.

**State table:** fresh; stale; corrected. One stamp per panel; stale/corrected are marks, not duplicate stamps.

**Copy:** Publication stamp, Stale, and Corrected twins are verbatim §8.1. Exact `<date time>` formatting is data-owned and an OPEN QUESTION.

**Keyboard/focus:** readable text; corrected prior value must be hover- and keyboard/tap reachable in production.

**Not allowed:** pulse/live “Updated” language, duplicate timestamps, hover-only prior value, silent newer data (R-E/§8).

## WatchAction

**Purpose (§4):** visible WatchStore action, disabled reason, and saved state.

```html
<button class="pw-watch" type="button" data-state="idle|pending|saved|failed|local-only" disabled>
  Watch / 关注
</button>
<span class="pw-watch-meta">Removed from &lt;list&gt; / 已从 &lt;list&gt; 移除</span>
<button class="pw-undo" type="button">Undo / 撤销</button>
```

**CSS:** every Watch state, disabled treatment, tombstone/Undo, and focus rules in the shared CSS above.

**State table (§9):** idle; pending; saved; failed; unwatched tombstone + Undo; local-only; disabled; watch failure (same exact failed message as §8.1). Only a successful WatchStore write paints Saved. A pull never resurrects the list-scoped tombstone.

**Copy:** all seven machine-state behavior strings and disabled copy are verbatim §8.1/§9. `Undo / 撤销` is supplied by §9. A sleeve/list-chooser confirmation label is an OPEN QUESTION.

**Keyboard/focus:** 40px native button; failed retry returns to pending; status changes are announced without stealing focus.

**Not allowed:** execution words, “Saved” from a read, global removal mark, disabled arrival promises, decision IDs, or a second save format (R-D/§9).

## TierLockProphet

**Purpose (§4):** honest entitlement boundary over `.mx-tier-gate--prophet`.

```html
<div class="pw-tier" data-state="locked|preview">
  <div class="pw-tier-ghost" aria-hidden="true"><!-- desaturated layout ghost --></div>
  <div class="mx-tier-gate mx-tier-gate--prophet">
    <div class="mx-tier-copy"><span class="mx-tier-eyebrow">Research only / 仅研究</span>
      <b>You have reached the limit for this plan. / 您已达到当前方案的上限。</b></div>
  </div>
</div>
```

**CSS:** overlay/ghost join to the incumbent tier gate in the shared CSS above; visual language comes from `templates/tier_preview.css` slot contract.

**State table:** locked (ghost + gate); preview (dashed gate, no hidden count); unavailable (`.mx-error`, exact failed-source sentence). Rollout joins `config.yml: us_board_gate.panels`, `panel_preview_rows`, same-PR `premium.enforced_early`, and plans-page disclosure (`DEC-PROPHET-US-D11-RELEASE-PATH-INCUMBENT-CONTROLS` §answer/§Scope).

**Copy:** no-access, failed-source, Research only, and Watch onboarding sentences are §8.1. Locked eyebrow/title beyond that are OPEN QUESTIONS.

**Keyboard/focus:** incumbent gate controls; ghost is `aria-hidden`; underlying locked content is unreachable.

**Not allowed:** new release flag/control plane, client-side entitlement, synthetic entitled proof, disappearing preview, or unlocked data in markup (D11).

## PreviewRowState

**Purpose (§4):** governed preview remainder under incumbent rollout controls.

```html
<div class="pw-preview" data-state="preview|locked|empty" data-count="2">
  <b>2</b><span>You have reached the limit for this plan. / 您已达到当前方案的上限。</span>
</div>
```

**CSS:** preview rule, count, lock join, and empty composition in the shared CSS above.

**State table:** preview (visible count + lock join); locked; empty (packet-owned exact empty sentence for the surface). Row count comes from server split, never client re-derivation.

**Copy:** no-access and empty-candidate strings are §8.1. A preview-count sentence is absent from §8.1 and is an OPEN QUESTION; the fixture shows the number with the no-access sentence without inventing one.

**Keyboard/focus:** static disclosure; joined controls inherit focus; target remains ≥40px effective.

**Not allowed:** silent disappearance, wrong-tier count, payload leakage, client gating, or a 36px action target (§4; D11; MP-1 §8b).

## COMPOSITION RECIPES

| Recipe | Assembly | Density budget |
|---|---|---|
| A Action Desk 1440 EN dark | Shared nav → Shell → ladder → four destination row → entry-open row + inline evidence | Answer in first row; expanded row two columns; ≤5 first-level sections; only ENTRY_OPEN green. |
| B Action Desk 390 ZH light | A with ZH twins, one-column evidence, horizontally scrolling tabs | Answer within one swipe; no duplicate stamp/chip; page never scrolls horizontally. |
| C Radar 390 ZH dark | Shared nav → Shell/ladder → Radar rows, neutral/dotted leading rule | Fresh candidates are not records; no lifecycle hue; answer first. |
| D All Candidates 1440 EN light | Shell/ladder → dense table-like rows with lifecycle field separate from stance | Number changes today's action; two axes in two columns; no blended confidence. |
| E Themes 1440 ZH dark | Shell/ladder → theme group body containing rows and ladder identity | Group body one luminance step dark / white panel light; ≤5 top-level groups in view. |
| F Track Record 390 EN light | Shell destination row → separate editorial/measurement surface link; AsOf; corrected record | One answer; original and correction distinct; no execution inference. |

All recipes retain Research only, AsOf, four tabs, and Track Record separate route. Dark/light mechanisms follow §5/§6: Action Desk luminance step vs white material; Radar withheld step vs withheld white material; Candidates zebra vs hairline; Themes nested step vs panel; Track Record luminance vs hairline divider.

## FIXTURE INDEX

| Fixture block | Component × state × theme |
|---|---|
| `shell-heading` | Shell default × dark/light × EN/ZH × responsive. |
| `ladder-heading` | Ladder live, absent, withheld, loading skeleton, error × dark/light × EN/ZH. |
| `availability-heading` | Availability all seven states × dark/light × EN/ZH. |
| `row-heading` | Rows collapsed, expanded, loading, unavailable, invalidated, stale, corrected, preview × dark/light × EN/ZH. |
| `evidence-heading` | Evidence fresh, missing, stale, corrected, loading, error × dark/light × EN/ZH. |
| `chip-heading` | Research chip default × dark/light × EN/ZH. |
| `stamp-heading` | Stamp fresh, stale, corrected × dark/light × EN/ZH. |
| `watch-heading` | Watch idle, pending, saved, failed, unwatched tombstone, local-only, disabled × dark/light × EN/ZH. |
| `tier-heading` | Tier lock locked, preview, unavailable × dark/light × EN/ZH. |
| `preview-heading` | Preview preview, locked, empty × dark/light × EN/ZH. |

## OPEN QUESTIONS FOR THE SEAT

1. Production `Prophet US / Prophet 美国` heading: packet §7 shows the composition title but §8.1 does not freeze it. Is it user copy or a product-name exemption?
2. Sleeve tag and holdings residual: R-D requires both, but the packet supplies no exact sleeve tag string, tag placement, or holdings residual sentence. Please supply bilingual twins.
3. Watch list chooser: please supply exact bilingual list-selection/confirmation strings for at least two named lists.
4. Exact corrected prior-value and correction `title=`/accessible disclosure mechanism: §8.1 supplies the corrected mark but no prior-value sentence or untranslated tooltip contract.
5. Tier lock production eyebrow/title/plan action strings beyond no-access and onboarding are absent from §8.1.
6. Preview remainder needs a bilingual sentence that discloses the exact withheld count and lock without inventing a new promise.
7. Evidence section headings, region labels, and field labels (including “opposing fact” and “read”) are absent from §8.1.
8. Fixture-only controls Theme / 主题 and Language / 语言 are absent from §8.1; production does not ship this fixture control bar.
9. Final localization formats for Publication stamp `<date time>` and `time datetime` are data-owner questions.
10. Packet §7 supplies only six representative compositions; B20 §5–§7 nevertheless specifies all 40 matrix cells by theme/language/width deltas. Confirm whether B16 captures remain sufficient evidence for the unillustrated 34 cells.

## EVIDENCE

- `python3 scripts/worktree_sparse.py add mockups` → `worktree-sparse: materialized mockups`.
- `python3 scripts/check_design_system.py --mode report --root . 2>&1 | tail -n 3` → three pre-existing `templates/winner_health.html.j2` findings (`:1015`, `:397`, `:411`); exit 0, report-only.
- Fallback-aware literal scan of the fixture style (removing complete `var(...)` expressions first) → `color literals: 0; px radius literals: 0; duration literals: 0`.
- `python3 scripts/check_validated_claims.py --help` → accepts only `--list` and `--selftest`, not a path. `--list` is therefore not applicable to this two-file, no-copy-claim artifact and was not run as a path gate.
- `grep -n -E '(UNAVAILABLE_FIELD|producer|nomination|episode)' mockups/prophet_workspace/b20_1_fixture.html` → no hits, exit 1.
- `grep -n 'title="' mockups/prophet_workspace/b20_1_fixture.html` → no hits, exit 1 (`grep -c` prints `0`).
- `diff <(sed -n '/^```css$/,/^```$/p' research/prophet_v4/r6_program/wave3/B20_1_COMPONENT_SPEC_2026-09-24.md | sed '1d;$d') <(sed -n '/<style>/,/<\/style>/p' mockups/prophet_workspace/b20_1_fixture.html | sed '1d;$d')` → empty, exit 0.
- Static audit → 10/10 required fixture blocks, 0 HTML parser errors; seven availability states present; watch idle/pending/saved/failed/unwatched/local-only/disabled present; `pw-ladder` count 0; one `/us_track_record.html` link.
- RED-first pytest is ruled out by the ruling’s scope: this design-only unit changes a research specification and mockup, no production behavior or test-owned module.

## GAPS

- No production route, template, payload, data owner, permission, chart, or route implementation is added.
- B16 visual captures and comprehension tests remain outside this design-spec-first unit.
- The fixture is renderable static evidence, not an authenticated production screenshot.
