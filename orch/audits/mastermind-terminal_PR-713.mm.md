# PR audit — mastermindx-market-intelligence/mastermind-terminal#713

**Auditor:** meta-ceo-b-2026-09-08 (one-pass remote useful-idle, no retries, no scope expansion)
**Audit timestamp:** 2026-09-22
**Repo / PR:** mastermindx-market-intelligence/mastermind-terminal #713
**PR title:** feat(chart): upgrade searchable study management and touch access
**Merged at:** 2026-09-22T10:40:03Z
**Head sha (integration):** `3b488ce96f2633613e1bd9d873e96693aef20314` ("feat(chart): make study layers searchable and touch-accessible (#713)")
**Source base:** `7f98bfd9868a7a71dfd7a0b90c482793dc13f1b6` (the prior #716 head on `origin/master` immediately before this merge)
**Branch:** `claude/terminal-chart-layers-ux-20260922`
**Author:** chriswong6031-creator (Claude Skillpack lane; PR body declares `Mastermind@ce18ed4f1eaa28e65a616a90aecca5c5ce1c5a2e` (v1.0.1 compatible) protected pack + operation id implicitly the chart-layer upgrade wave)
**Repo root verified:** `/Users/chriswong/lanes/repos/mastermind-terminal`, sparse-checkout (worktree-scoped). `terminal/components/ChartObjectTree.tsx`, `terminal/components/ChartObjectTree.module.css`, `terminal/lib/__tests__/chartObjectTree.test.tsx`, `terminal/e2e/chart-object-tree.spec.ts` and `terminal/lib/i18n.tsx` are all fetched via `git show origin/master:<path>` (the local sparse filter excludes `terminal/**` directories so diff + e2e + i18n were obtained by direct blob resolution against `origin/master`).

> **Scope note (§1):** the chronologically most-recent merged PRs in either repo inside the 24 h window are terminal #713 (10:40:03Z — this PR), terminal #716 (07:45:29Z — `fix(options): enlarge mobile workspace navigation`, 0 audits in repo), terminal #710 (06:53:44Z — `fix(options): keep mobile flow receipts readable`, 0 audits), macro #7701 (07:50:16Z — `[MO F07] event -> AssumptionChange: typed proposal, typed abstention, shadow scenario`, backend F-class), macro #7688 (07:34:06Z — `feat(prophet): own B4 session eligibility policy`, audited under `orch/audits/macro_PR-7688.mm.md`), macro #7687 (07:39:39Z — `fix(prophet): keep optional structural overlay from deadlocking B4`, audited under `orch/audits/macro_PR-7687.mm.md`), macro #7699 (07:28:34Z — audit recording PR), macro #7698 (07:23:25Z — `docs(ric): RIC F3 production proof`, research-doc only), macro #7634 (07:13:09Z — `fix(reports): accessible archive filters and keyboard locale updates`, F-class infrastructure repair, no user-visible new copy). Cross-repo, the chronologically newest un-audited **half-B** (B-class user-facing chart/UI) merge is **#713** at 10:40:03Z — `feat(chart): upgrade searchable study management and touch access` on Terminal. The audit covers it directly.

---

## 1. PR metadata

| field | value |
|---|---|
| repo | mastermindx-market-intelligence/mastermind-terminal |
| number | 713 |
| title | feat(chart): upgrade searchable study management and touch access |
| merged_at | 2026-09-22T10:40:03Z |
| head (integration) | `3b488ce96f2633613e1bd9d873e96693aef20314` |
| base | `7f98bfd9868a7a71dfd7a0b90c482793dc13f1b6` (prior #716 head on `origin/master`) |
| branch | `claude/terminal-chart-layers-ux-20260922` |
| changed files | 13 — `docs/TERMINAL_CHART_LAYERS_UX_2026-09-22.md` (+34 ADDED), `terminal/components/ChartObjectTree.module.css` (+53 ADDED), `terminal/components/ChartObjectTree.tsx` (+107 / -118 MODIFIED), `terminal/lib/__tests__/chartObjectTree.test.tsx` (+66 ADDED), `terminal/e2e/chart-object-tree.spec.ts` (+88 ADDED), 7 PNG crops under `terminal/docs/pr-crops/chart-layers-ux-20260922/` + 1 `EVIDENCE.json` |
| additions / deletions | 394 / 118 |
| labels | (none external; merge-on-green backstop consumed by sweeper) |
| scope collision | none — body declares "No worker or watcher was commissioned. No settings/state owner, store, dependency, chart renderer, backend service or signal/indicator mathematics is introduced or replaced." and lists parent-mission siblings (#701 chart settings, #705 chart view/reset, #707 warm-cache release, #702 stalled-tap carrier) as adjacent but explicitly out of scope; this PR upgrades the existing Object Tree panel only |
| operation id | `TERMINAL-CHART-LAYERS-UX-20260922` (implicit chart-upgrade programme slice) |
| protected pack | `Mastermind@ce18ed4f1eaa28e65a616a90aecca5c5ce1c5a2e` (v1.0.1 / bootstrap 1) |

**Nature of change (chart-layer Object Tree upgrade, half-B UI expansion):** the PR rewrites the existing right-rail "Object Tree" panel so the Chairman can find indicators quickly via search, see visibility counts, and operate hide/show/remove on both desktop and touch without losing keyboard focus or hiding meaning behind truncations. The implementation reuses the existing `TerminalShell` props (`OTEntry`, `onEye`, `onRemove`, `onClose` — the existing callbacks and the source-supplied `noRemove` protected-flag are unchanged), introduces transient view-state search only (never edits studies or preferences), and replaces the inline-style layout with a dedicated `ChartObjectTree.module.css`. On narrow viewports the panel is escalated to the browser's native manual Popover top layer to escape the chart's containing/stacking context — feature-detected and cleaned up on media change, no portal, no remount, no second component.

**Repair of an actual discovered defect (PR body, §"Completed local qualification and discovered clipping defect"):** an initial mobile CSS-fixed side panel was still clipped by the chart's ancestor at the 390×844 viewport, and fullscreen chrome could cover a control. A stronger viewport plus center-point hit test reproduced that failure. The native-Popover repair passes the improved test; only currently tested Chromium behavior is claimed, and the PR body is explicit that "a legacy-browser fallback was not separately proven." This is a known-claimed scope boundary, not a hidden one.

---

## 2. Plain-language findings

### 2.1 PASS — guard run on the integration head

The guard was executed against the PR head against the prior #716 base on `origin/master`:

```
$ cd ~/lanes/repos/mastermind-terminal && \
  git diff --unified=0 7f98bfd9868a7a71dfd7a0b90c482793dc13f1b6 \
  3b488ce96f2633613e1bd9d873e96693aef20314 \
  -- 'terminal/app' 'terminal/components' 'terminal/lib' > /tmp/pr713.diff

$ node terminal/scripts/check_plain_language.mjs \
    --diff-file /tmp/pr713.diff --json \
    --root /Users/chriswong/lanes/repos/mastermind-terminal
```

Result:

```json
{"version":1,"mode":"enforce-added","base":"origin/master","baseResolved":true,
 "vocabulary":{"declaredTerms":83,"overlaySource":"terminal/lib/plainLabels.ts",
               "overlayPresent":false,"overlayTerms":0},
 "scannedFiles":2,"findings":[],"legacy":[],
 "counts":{"blocking":0,"legacyReported":0,"waived":0},"nulls":[]}
exit=0
```

**Note on the `scannedFiles: 2` figure (sparse-worktree disclosure):** the local `mastermind-terminal` checkout is sparse — the `WorktreeCreate` hook applies `config/sparse_worktree.json` and excludes `terminal/app`, `terminal/lib`, `site/`, `data/`, `mockups/`. `listScanFiles` therefore walked only the files present on disk: `terminal/components/ChartObjectTree.tsx` (the only file in SCAN_GLOBS that the diff touches) and `terminal/components/vol/VolTermPanel.tsx` (the only other `.tsx` file in the components subtree of this sparse checkout). `terminal/lib/i18n.tsx` (EXTRA_FILES) was not present locally — fetched via `git show origin/master:terminal/lib/i18n.tsx` for the LEX parity audit below. `terminal/lib/__tests__/chartObjectTree.test.tsx` and `terminal/e2e/chart-object-tree.spec.ts` are in the guard's `EXCLUDE_RE` and never contribute findings; the new `terminal/components/ChartObjectTree.module.css` is not in `SCAN_GLOBS` and never would. Forward-only `enforce-added` blocking semantics: no `added`-line violation ⇒ guard exits 0.

**Coverage statement:** the diff's only user-visible JSX surface in the guard's scan scope is `terminal/components/ChartObjectTree.tsx`; that file was scanned, produced zero findings (R1 raw_state_enum / R2 internal_study_slug / R3 raw_slug_interpolation / R4 untranslated_stat_token / R5b missing_zh all clean), and `nulls: []` because the touched file has visible added lines (`visibleAddedCount > 0`) — there is no `not evaluable` null to disclose.

### 2.2 All new visible strings route through `t()` with confirmed EN+ZH LEX parity

Every user-visible string in the new `ChartObjectTree.tsx` is a `t("…")` call against a key whose LEX entry carries an `[en, zh]` tuple. Verified by `git show origin/master:terminal/lib/i18n.tsx | grep` over the 14 keys touched by the PR:

| key | EN | ZH | where used |
|---|---|---|---|
| `objectTree` | "Object tree" | "图层树" | panel heading `<h2 id={`${id}-title`}>` |
| `drawSearch` | "Search" | "搜索" | search `aria-label` / `placeholder` |
| `smIndicators` | "Indicators" | "指标" | header subtitle ("`{entries.length} 指标`"), search label concatenation |
| `smClose` | "Close" | "关闭" | close button `aria-label` / `title` |
| `lgShow` | "Show" | "显示" | eye-toggle `aria-label` / `title` (when entry.hidden) |
| `lgHide` | "Hide" | "隐藏" | eye-toggle `aria-label` / `title` (when not hidden) |
| `remove` | "Remove" | "移除" | remove button `aria-label` / `title` |
| `clearFilter` | "Clear filter" | "清除筛选" | clear-filter button + empty-state CTA |
| `scr2EmptyTitle` | "No matches" | "没有匹配结果" | empty-state body when filter returns no rows but entries exist |
| `ctvMainSeries` | "Main series" | "主图序列" | main-series small label |
| `ctvOverlays` | "Overlays" | "叠加指标" | overlay group `<h3>` |
| `ctvSubPanes` | "Sub-pane indicators" | "副图指标" | sub-pane group `<h3>` |
| `ctvNoIndicators` | "No indicators active." | "暂无活跃指标。" | empty-state body when no entries exist at all |
| `isTabVisibility` | "Visibility" | "可见性" | visibility-count `aria-label` ("`可见性: {visible}/{entries.length}`") |

**No new LEX entry is added by this PR** — every key already existed on the integration base; the upgrade is purely a UI rewire of keys that were already declared. Bilingual parity therefore holds by inheritance; no zh routing change is owed.

### 2.3 No raw slugs, state enums, or stat tokens reach a user-visible position

- **R1 raw_state_enum:** the `enumRe` (`/\b([A-Z][A-Z0-9]+(?:_[A-Z0-9]+)+)\b/g`) walk over visible text spans in `ChartObjectTree.tsx` returns zero matches. The only UPPER_SNAKE identifiers in the file are TypeScript-side (`OTEntry`, `noRemove`, `useId`, `useEffect`, `useMemo`, `useRef`, `useState` etc.) — none ever renders as visible text. `PLAIN_VOCABULARY.allowTokens` (`RSI`, `MACD`, `ETF`, `NAV`, `AI`, `API`, `USD`, `HKD`, `CNY`) is irrelevant: no token from the surface ever reaches user-visible text.
- **R2 internal_study_slug:** the slug set (`trust_tier`, `event-edge`, `msc_regime`, `mscRegime`, `flowScore`, `gexdesk`, `prophet`, `oracle`, `conductor`, `synapse`, `lobe`, `tripwire`, `falsifier`, `quiet_accumulation`, `bottom_watch`) never appears in a visible span. The PR does not introduce any new slug-bearing visible copy; the indicator labels are supplied by the parent's `OTEntry.label`/`OTEntry.tag` (source of truth for study identity) and are rendered as plain English / Chinese study names, never as internal study slugs.
- **R3 raw_slug_interpolation:** the visible `{row.regime}` / `{cfg.type}` / `{row.kind}` family of patterns does not appear in this file. The only interpolation in visible spans is `{symbol}`, `{entries.length}`, `{visible}`, `{entry.label}`, `{entry.tag}` — all rendered text or counts, not slug fields. The `PLAIN_VOCABULARY.slugFields` set (`state`, `regime`, `status`, `tier`, `slug`, `code`, `kind`, `category`, `type`, `bucket`, `classification`, `verdict`, `urgency`) is not surfaced as a visible interpolation in this PR.
- **R4 untranslated_stat_token:** the stat token set (`iv_rank`, `ivr`, `gex`, `dex`, `vanna`, `charm`, `dte`, `oi`, `pcr`, `rv30`, `hv20`, `atr14`, `zscore`, `pctl`, `yoy`, `qoq`, `ttm`, `cagr`) is absent from visible text spans. The visibility count is rendered as `{visible}/{entries.length}` (a ratio, no token name); the search box is filtered on `${entry.label} ${entry.tag ?? ""}` (label / tag text only); no raw statistic token name ever reaches a user-visible position.
- **R5a/R5b missing_zh:** every visible literal in `ChartObjectTree.tsx` is wrapped in `t("…")` with a confirmed LEX pair above; no added English literal in a user-visible position without zh routing. `terminal/lib/i18n.tsx` itself was not modified by the PR, so the LEX-arity check is unchanged.

---

## 3. Theme findings

### 3.1 PASS — Terminal dark-only, no new theme primitives

Per the integration base and `terminal/docs/pr-crops/chart-layers-ux-20260922/EVIDENCE.json` (`"theme": "Terminal dark-only"`), Terminal remains a single-theme product; the new `ChartObjectTree.module.css` introduces **no new color token, no new type ramp, no new spacing scale, no new rounding scale, no new motion grammar**.

**Token usage (existing terminal design-system tokens only — full inventory referenced from `terminal/app/globals.css` token layer):**

- `var(--panel-2)` — root background
- `var(--panel)`, `var(--panel-3)` — surfaces (search, main-series card, clear button)
- `var(--text)`, `var(--text-2)`, `var(--text-dim)` — type ramp colors
- `var(--line)` — borders / separators
- `var(--brand)` — focus outline + main-series icon accent
- `var(--danger)` — remove hover state
- `var(--font-ui)` — UI text
- `var(--font-mono)` — count badge + tag small text

**No new CSS variable is added.** Every visual value resolves through the existing token graph; the new rules read the same design system the surrounding panel already reads.

**Two inline values are introduced (intentional, narrowly scoped, dark-art-direction-consistent):**

- `.root:global(.ot-root) { … box-shadow:-12px 0 32px rgb(0 0 0 / .24); }` on the `@media (max-width:860px)` side-sheet variant. This is the same dark-only inline RGB shadow the existing Terminal dark direction uses elsewhere (e.g. dialog backdrops) — a single hardcoded shadow rather than a new `--shadow-*` token. Reasonable for a one-off side-sheet; flagged for consistency only, not as a violation. If a `--shadow-side-sheet` token existed on the integration base, the author would have used it; introducing one in this slice would be scope-creep against the bounded half-B fix. **Recommended follow-up (non-blocking):** if a future PR touches more side-sheet surfaces, promote this value to a token in the same PR — keeping the inline value here is the lower-risk choice for an isolated UI fix.
- `z-index: 35` on the same `@media (max-width:860px)` rule. This sits above the chart's stacking context but is owned by the native Popover top layer when activated, so the z-index is a fallback for browsers without Popover support (the feature-detection block in `ChartObjectTree.tsx`). Single value, no other z-index reassigned, no global z-index arms race introduced. **Consistent with the existing Terminal layering convention** (`--z-*` tokens are not used here either; the surrounding options-flow / chart-settings panels likewise use small integer z-indices for fixed surfaces).

**Type ramp / spacing / rounding:** all font / size / weight declarations use the existing `var(--font-ui)` and `var(--font-mono)` tokens with concrete weights / sizes that match the surrounding `.ot-row` family the file replaces — no new size scale, no new weight ramp, no new letter-spacing, no new line-height scale. `border-radius` values (5/7/8/9px) are concrete values used in the existing panel family and do not introduce a new rounding scale.

**Motion grammar:** `@media (prefers-reduced-motion: reduce) { .root *, .root *::before, .root *::after { animation:none!important; transition:none!important; } }` is the same `prefers-reduced-motion` block the existing Terminal panels use to disable incidental transitions. No new animation, no new transition, no new easing curve is introduced.

**Breakpoints:** one new media query `@media (max-width:860px), (pointer:coarse)` for touch sizing (44 px controls), and one new `@media (max-width:860px)` for the side-sheet layout — both adjacent to the existing terminal breakpoint convention (the surrounding chart settings and flow-board panels already use 860 px as the phone boundary). No new breakpoint introduced; the new queries live within the existing breakpoint family.

### 3.2 East-Asian up/down convention (`html[data-updown="east"]`) preserved

The new CSS touches no token that the East-Asian red-up convention flips (`--up`, `--down`, `--buy`, `--sell`, `--regime-up`, `--up-rgb`, `--down-rgb`, `--rebuy`, `--cut`). The only color tokens used (`--text`, `--text-2`, `--text-dim`, `--line`, `--brand`, `--danger`, `--panel`, `--panel-2`, `--panel-3`) are convention-invariant. A CN/HK/JP viewer therefore sees the exact same Object Tree panel as an EN viewer.

### 3.3 `prefers-reduced-motion` parity

The new `@media (prefers-reduced-motion: reduce)` block uses the same blanket `animation:none!important; transition:none!important;` pattern as the surrounding Terminal panels. Motion on this surface under reduced-motion preference is fully suppressed.

---

## 4. Validated-claims findings

### 4.1 PASS — no `validated` / `falsifier` / `证伪` claim in a user-visible position

- **PR body** uses the conventional carrier-cohort language: "BUILT_NOT_PROVEN", "Current capability", "production deployment has not been started", "Required protected CI, merge and exact-target live verification remain owed" — all of which are honest status statements, not the words `validated` / `falsifier` / `证伪` / `thesis refuted` / `proof`. These are GitHub-only markdown and never reach the rendered UI.
- **Commit message** (`feat(chart): make study layers searchable and touch-accessible (#713)`) is conventional — no `validated`, no `falsifier`, no `证伪`, no `proof`, no `thesis refuted`, no `peak` claim. Conventional commit subject only.
- **`docs/TERMINAL_CHART_LAYERS_UX_2026-09-22.md`** (new masterplan/qualification file) is a maintainer-internal document — not under `terminal/app/`, not under `terminal/components/`, and not in `SCAN_GLOBS`. It carries the words "discriminating verification", "RED on protected base", "GREEN on candidate" (all of which are conventional carrier language naming the test harness), but it is never rendered to a user.
- **`ChartObjectTree.tsx`** contains zero user-visible string literals that name a validation or falsifier outcome. Every visible string routes through `t("…")`; the keys audited above (`objectTree`, `drawSearch`, `smIndicators`, `smClose`, `lgShow`, `lgHide`, `remove`, `clearFilter`, `scr2EmptyTitle`, `ctvMainSeries`, `ctvOverlays`, `ctvSubPanes`, `ctvNoIndicators`, `isTabVisibility`) all carry EN+ZH lexicon entries that name UI affordances, never a verdict.
- **`chartObjectTree.test.tsx`** (component test, in `terminal/lib/__tests__/` — `EXCLUDE_RE`) uses the English labels `objectTree, drawSearch, smIndicators, smClose, lgShow, lgHide, remove, clearFilter, scr2EmptyTitle, ctvMainSeries, ctvOverlays, ctvSubPanes, ctvNoIndicators, isTabVisibility` in the `vi.mock("@/lib/i18n")` fixture only — these are key names, not display copy.
- **`chart-object-tree.spec.ts`** (Playwright e2e, in `terminal/e2e/` — `EXCLUDE_RE`) uses English / Chinese test-side assertions ("Hide Moving Averages", "Show Relative Strength", "Remove Moving Averages", "Close", "图层树", "搜索 指标", "隐藏 Moving Averages", "关闭") that are the rendered UI text, not validation claims.

### 4.2 Discriminating verification (PR body) is concrete and reproducible

The PR body's §"Completed local qualification and discovered clipping defect" names a real RED/GREEN pair:

- **RED base:** initial mobile CSS-fixed panel — clipped by the chart's ancestor at 390×844 viewport, fullscreen chrome covering a control. Reproduced via a stronger viewport plus center-point hit test.
- **GREEN candidate:** integration head `3b488ce9` — the native-Popover side-sheet repair passes the improved test; final phone/tablet crops show the full panel with every study action reachable. **Claim scope:** "Only currently tested Chromium behavior is claimed; a legacy-browser fallback was not separately proven." This is an explicit, narrow, reproducible claim — not a vague "validated".

**Word-budget / glance-tier check (parity with `research/MASTER_PRODUCT_DESIGN_SYSTEM_V1.md`):** the Object Tree panel does not introduce a glance-tier surface of its own; it is a settings / management surface. The PR introduces no new glance-tier copy, no new stat tile, no new front-facing claim. The visibility count (`{visible}/{entries.length}`) is an in-panel operator indicator with a full `aria-label` ("Visibility: …" / "可见性: …"); it is not a glance-tier stat.

### 4.3 LEX additions = 0

This PR does **not** add a new LEX entry. The 14 keys used all existed on the integration base. The bilingual layer is unchanged in scope — only a UI surface that was already declared is now wired.

---

## 5. Overall verdict

**PASS** — clean, bounded, well-evidenced chart-layer Object Tree upgrade; no plain-language / theme / validated-claims violations.

The PR replaces the existing inline-styled Object Tree panel with a module-CSS + dedicated tsx rewrite that adds transient search, accessibility-grade focus management (Escape clears the filter before closing; removal restores focus inside the surviving controls/search rather than dropping it onto the document; search receives focus on open), 44 px touch targets on `pointer:coarse` / `(max-width:860px)`, a native-Popover side-sheet at narrow widths (feature-detected, cleanup on media change), and an explicit `prefers-reduced-motion: reduce` block. Every visible string routes through `t("…")` against an existing LEX key with confirmed EN+ZH parity; no new copy, no new tokens, no new motion, no new breakpoint. The guard ran clean on the integration head against the prior #716 base on `origin/master`: 0 blocking findings, 0 legacy findings, 0 waived, 0 nulls, 2 scanned files (sparse-worktree disclosure; the only in-scope user-visible JSX file in the diff was scanned). The single inline shadow `rgb(0 0 0 / .24)` and the single z-index `35` are dark-art-direction-consistent narrowly-scoped values, not new tokens — flagged as a non-blocking consistency note only. The PR body correctly classifies the slice as `BUILT_NOT_PROVEN` with "protected CI, merge and exact-target live verification remain owed"; that is honest, not a validated-claims violation. Recommended next: live-verify the merged `master` on the Terminal at https://app.mastermind-x.com/terminal right-rail Object Tree at 1440×900 desktop and 390×844 mobile viewports, confirming the search box receives focus on open, the visibility count reads `visible/total`, the eye / remove buttons carry EN + ZH labels per active language, and a real hide/show/remove action through the panel mutates `localStorage["mm.indHidden"]` / `["mm.inds"]` per the e2e assertions — that is the live step the terminal `AGENTS.md` "Definition of done" requires and which the integrated merge-on-green backstop alone does not satisfy.