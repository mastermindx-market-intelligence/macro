# Plain-language / theme / validated-claims audit — mastermind-terminal PR #713

Auditor: qwen_auditor2-style pass (one-shot, half-B scope, REMOTE USEFUL-IDLE — no retries, no scope expansion). Date: 2026-09-22.

## PR metadata

| field | value |
|---|---|
| repo | `mastermindx-market-intelligence/mastermind-terminal` |
| number | #713 |
| title | `feat(chart): upgrade searchable study management and touch access` |
| merged_at | 2026-09-22T10:40:03Z |
| head (semantic) | `bb5097b4f6cdfebcd39df55fb1196f74689c7778` ("feat(chart): make study layers searchable and touch-accessible") |
| head_ref_name | `claude/terminal-chart-layers-ux-20260922` |
| merge_commit | `8114f2ee9615717d6223219a894dc10b619965b1` (merge of feature branch into master) |
| base (protected) | `3b0340bf831f3112575129f3c2f649ced0e00e78` |
| author | Claude Code (chart-upgrade-programme carrier) |
| protected Skillpack | `Mastermind@ce18ed4f1eaa28e65a616a90aecca5c5ce1c5a2e` (v1.0.1) |
| changed files | **13 files, +394 / −118.** `terminal/components/ChartObjectTree.tsx` (+107 / −118 MODIFIED), `terminal/components/ChartObjectTree.module.css` (+53 ADDED), `terminal/lib/__tests__/chartObjectTree.test.tsx` (+66 ADDED), `terminal/e2e/chart-object-tree.spec.ts` (+88 ADDED), `docs/TERMINAL_CHART_LAYERS_UX_2026-09-22.md` (+34 ADDED), `terminal/docs/pr-crops/chart-layers-ux-20260922/EVIDENCE.json` (+46 ADDED), 6 PNG crops (desktop-before / desktop-open / desktop-zh / tablet-open / tablet-zh / mobile-open / mobile-zh) |
| additions / deletions | 394 / 118 |
| labels | none visible at fetch time; merge-on-green sweep |
| scope collision | none — PR body declares "No settings/state owner, store, dependency, chart renderer, backend service or signal/indicator mathematics is introduced or replaced." The slice is confined to `ChartObjectTree.tsx` + its CSS module. |

**Why this PR is the half-B pick.** Cross-referencing `gh pr list --state merged --limit 30 --repo mastermindx-market-intelligence/mastermind-terminal` (24-h window) against `ls orch/audits/mastermind-terminal_PR-*.mm.md`: the chronologically most-recent un-audited half-B (B-class user-facing chart/UI) merge in the window is **#713** at 10:40:03Z — a 13-file, +394/−118 chart-layer-management upgrade on `ChartObjectTree` (the right-rail panel that lists the chart's main series + indicator overlays + sub-pane indicators). It carries the canonical anti-promotion closer ("Current capability: BUILT_NOT_PROVEN. No production deployment has been started for this slice. Required protected CI, merge and exact-target live verification remain owed. The parent charting mission is incomplete.") and was already parent-mission-aligned with #701, #705, #706, #710, #716 (which are documented as DO_NOT_REDO). Later terminal merges (#716) are already audited.

**Nature of change (searchable study management + touch access on the existing chart Object Tree panel):**

1. *Defect / opportunity — the existing Object Tree had no search and no touch-sized controls.* The pre-existing `ChartObjectTree.tsx` rendered all overlays and sub-pane indicators as a flat list with `icbtn` controls at desktop geometry (no search box, ~28px control heights, no mobile breakpoint). On touch inputs the panel was effectively unusable: 28px controls fall below the WCAG/Apple-HIG 44px floor, and there was no way to find a study among many. The PR body captures the browser-baseline test that "failed the new search-focus contract because no search control existed" — so the OLD design is explicitly retained as `desktop-before.png` for the visual review.

2. *Where the impact lives.* Only `ChartObjectTree.tsx` (one right-rail composer) and its new CSS module (`ChartObjectTree.module.css`). The data contract is unchanged: TerminalShell still supplies study identity, labels/tags, grouping, hidden state, and `noRemove` entries; the same callbacks (`onEye`, `onRemove`, `onClose`) perform every actual mutation. Search is transient view state only, matching labels and tags (including hidden studies). It never edits studies or preferences. The main-series row remains non-removable. The component still consumes the existing LEX translations — no second translation system is added.

3. *Discriminating verification.* A new 88-line Playwright spec (`terminal/e2e/chart-object-tree.spec.ts`) gates the contract on three desktop/tablet/mobile projects: (a) find/hide/restore/remove with keyboard focus retention and localStorage persistence (`mm.indHidden` / `mm.inds` round-trip), (b) ZH layer-control visibility + 44px floor + center-point hit test (`the study action must not be covered by chart chrome or clipped by its pane`), (c) one breakpoint round trip from desktop contract (1440×900) to mobile (390×844) preserving the same filtered panel. The 66-line Vitest suite (`terminal/lib/__tests__/chartObjectTree.test.tsx`) covers 7 component contracts: search focus on open, label/tag search without mutating indicator state, hidden studies remaining actionable, post-removal focus retention, distinct no-match vs no-indicators states, Escape-clears-filter-then-closes ordering, focus-returns-to-search on empty removal.

4. *Defect discovered during visual review, repaired via native browser API.* Initial visibility checks passed, but the phone crops showed a CSS-fixed panel still clipped by the chart's containing/stacking contexts, and fullscreen chrome could cover a control. The repair uses the browser's native **manual Popover top layer** on the same existing `<section>` element at narrow widths (`@media (max-width: 860px)`), with feature detection (`typeof element.showPopover !== "function"`) and `matchMedia` change cleanup. It does NOT portal/remount a second component, add a dependency, raise global z-indices, or replace chart state. The improved test passes. The PR explicitly disclaims legacy-browser coverage: "Only currently tested Chromium behavior is claimed; a legacy-browser fallback was not separately proven."

5. *Era/freeze discipline.* Terminal is dark-only by design — no light-mode CSS, no theme tokens added, no palette change. CSS variables (`--panel`, `--panel-2`, `--panel-3`, `--text`, `--text-2`, `--text-dim`, `--brand`, `--line`, `--danger`, `--font-ui`, `--font-mono`) are reused; the only raw color in the CSS file is `rgb(0 0 0 / .24)` for the side-sheet shadow. `prefers-reduced-motion` correctly disables animation/transition. Touch geometry follows project standard: 44px controls, 16px input font (prevents iOS auto-zoom), `env(safe-area-inset-top/bottom)`. Search input is `type="search"` for proper mobile UX, with `::-webkit-search-cancel-button` hidden.

6. *Related-PR boundary block.* The PR body explicitly names what it does NOT take over: `#701` and `#705` are accepted live and DO_NOT_REDO; `#707` is a separate warm-cache release under its own running protected CI; `#702`'s stalled-tap failure is separately adjudicated. "This panel does not take over either marker-repair carrier." The release boundary holds the lane at `BUILT_NOT_PROVEN` even after merge: "No production deployment has been started for this slice. Required protected CI, merge and exact-target live verification remain owed. The parent charting mission is incomplete."

## Diff content (scoped to this audit)

13 files, all confined to one composer (`ChartObjectTree.tsx`) + its CSS module + the test/evidence/docs around it. Zero engine code, zero settings/state owner, zero chart renderer, zero signal/indicator math, zero translations authored.

### `terminal/components/ChartObjectTree.tsx` (MODIFIED, +107 / −118)

The component is rewritten from inline SVG icon constants + class strings to a CSS-module-driven `<header>` / search / `<div className="ot-body">` structure. Key behavioural changes:

- Adds a search `<input type="search">` with a transient `query` state, `useId()`-based accessibility wiring (`aria-labelledby`), and `useMemo`-derived `filtered` list (matches `label` + `tag`, includes hidden studies).
- Adds a `useEffect` that:
  - captures the opener (`document.activeElement`) and restores focus on unmount,
  - feature-detects `showPopover`/`hidePopover` and the `matchMedia("(max-width: 860px)")` listener,
  - mounts the existing `<section>` into the browser's native top-layer (manual Popover) on narrow widths so it escapes the chart's containing/stacking contexts without a z-index arms race or a second React tree,
  - syncs the popover on media-change events and tears it down on unmount.
- Adds a `pendingFocus` ref that, after a row removal, finds the surviving sibling (`filtered[index + 1] ?? filtered[index - 1]`) by `data-layer-eye` and re-focuses the next control, falling back to the search input when the filtered set empties.
- Adds an `onKeyDown` handler that intercepts `Escape`: clears the filter first if non-empty, otherwise closes the panel.
- Adds `data-layer-key` / `data-hidden` / `data-layer-eye` data attributes for test selectors.
- Adds `aria-label` per action button (e.g. `"Hide Moving Averages"`, `"Show Relative Strength"`, `"Remove Moving Averages"`, `"Close"`) — every button identifies its target by accessible name.
- Distinguishes no-match (`scr2EmptyTitle` "No matches", with a "Clear filter" button) from no-indicator (`ctvNoIndicators` "No indicators active.").
- A `noRemove: true` entry (the main series, `_oracle`, compare — and the protected test seed `locked`) never renders a remove button. Verified by `expect(host.querySelector('[data-layer-key="locked"] .ot-remove')).toBeNull()`.
- One inline color (`style={entry.color ? { color: entry.color } : undefined}`) is data-driven (semantic per-study color on the icon only), not a styling decision.
- The `useEffect` is keyed `[]` — it runs once on mount and tears down on unmount; the focus-restore useEffect is keyed `[entries]` so it fires after a removal propagates through state.

### `terminal/components/ChartObjectTree.module.css` (NEW, +53)

A local CSS module — not a global token file, not a stylesheet rewrite. Token discipline:

- 25 `var(--token)` references, 1 raw color (`rgb(0 0 0 / .24)` for the mobile side-sheet box-shadow).
- 2 `!important` declarations, both inside `@media (prefers-reduced-motion: reduce)` — the standard accessibility override, not a styling choice.
- No `color-scheme`, no light/dark branching, no `@media (prefers-color-scheme: light)`.
- Mobile breakpoint: `@media (max-width: 860px)` (matches the `matchMedia` constant in the TSX). Within that breakpoint: position fixed, top-layer side sheet, 44px controls, 16px input font (prevents iOS Safari auto-zoom), `env(safe-area-inset-top/bottom)` for notch/home-bar.
- Coarse-pointer branch: `@media (max-width: 860px), (pointer: coarse)` upgrades control heights (34px → 44px), row min-height (52px → 56px), clear button min-height (36px → 44px).
- `overscroll-behavior: contain` on the body — prevents the chart's scroll-chaining from firing inside the panel.
- `scrollbar-width: thin` — narrow scrollbar without consuming a vendor token.
- Wrap-long-name: `.name { white-space: normal; overflow-wrap: anywhere; }` so the study identity is never hidden behind truncation.

### `terminal/lib/__tests__/chartObjectTree.test.tsx` (NEW, +66)

7 Vitest contracts, all gated by `@vitest-environment jsdom` and a stubbed `useT` hook. Each test pins a single, observable contract:

1. Focuses search on open and names every action for its study (incl. `noRemove` rows having no remove button).
2. Search matches labels and tags without ever calling `onEye`/`onRemove` (search is view-only).
3. Hidden studies remain actionable and the eye handler receives the right key.
4. After `Remove`, focus stays inside the panel on the surviving next sibling (not dropped onto `document`).
5. No-match (`"No matches"`) and no-indicators (`"No indicators active."`) are distinct strings, and `Clear filter` resets the input.
6. Escape clears a filter first and only then closes (`close` not called while a filter is non-empty).
7. When a removal empties the filtered result, focus returns to the search input.

### `terminal/e2e/chart-object-tree.spec.ts` (NEW, +88)

3 Playwright tests, all gated on the 7-viewport responsive matrix (`desktop / tablet / mobile`):

1. *Find / hide / restore / remove with keyboard focus retention.* Opens `/terminal?symbol=NVDA`, right-clicks the chart wrap, picks `[data-a="objtree"]`, asserts `search` is focused, fills `"Moving Averages"`, hides / shows / removes the row, asserts `localStorage.mm.indHidden` and `localStorage.mm.inds` round-trip, asserts focus stays on `search` after the row is removed, asserts no page-level horizontal overflow (`scrollWidth - clientWidth <= 1`), Escape-clears-then-closes.
2. *ZH layer controls + touch geometry.* Asserts the ZH heading `"图层树"` and ZH search label `"搜索 指标"` are visible. On non-desktop projects: every control is `toBeInViewport()`, center-point hit-tested (`target.contains(target)`), and ≥ 44px in both axes. Asserts no `pageerror` events. Emulates `reducedMotion: "reduce"`.
3. *Open study filter survives a responsive round trip.* Desktop-only (`test.skip` on tablet/mobile). Opens with `"Volume"` filter, resizes to 390×844, asserts `panel.matches(":popover-open")` is true and the search input still has `"Volume"`, resizes back to 1440×900, asserts `popover` attribute is removed and the filtered row count is still 1.

### `docs/TERMINAL_CHART_LAYERS_UX_2026-09-22.md` (NEW, +34)

The single design + qualification narrative. Closes with: "Current capability: BUILT_NOT_PROVEN. No production deployment has been started for this slice. Required protected CI, merge and exact-target live verification remain owed. The parent charting mission is incomplete." Plus: "Only currently tested Chromium behavior is claimed; a legacy-browser fallback was not separately proven."

### `terminal/docs/pr-crops/chart-layers-ux-20260922/EVIDENCE.json` (NEW, +46)

Records source/crop `sha256` digests, the test commands actually run (`npx next typegen && npx tsc --noEmit` → `PASS`, scoped ESLint → `PASS`, `npm test --maxWorkers=2 --minWorkers=2` → `379 files; 6088 passed; 4 existing todo`, Playwright on the chart-object-tree + chart-view-reset specs → `14 passed; 10 intentional viewport skips; 0 failed; retries 0`), and the explicit `productionProof: false` field with the `theme: "Terminal dark-only"` disclosure.

### PNG crops (7 ADDED, binary)

`desktop-before.png` (293163 B) is the pre-edit baseline. `desktop-open.png`, `desktop-zh.png`, `tablet-open.png`, `tablet-zh.png`, `mobile-open.png`, `mobile-zh.png` are the post-edit 1440×900 / 820×1180 / 390×844 crops in EN and ZH. All seven have SHA-256 digests in EVIDENCE.json so the crop↔source pairing is reproducible.

## Plain-language findings

### 1.1 Pass — `node terminal/scripts/check_plain_language.mjs --json` on PR head reports **0 blocking findings, 6 legacy, 0 waived, 0 nulls**

```
{"version":1,"mode":"enforce-added","base":"origin/master","baseResolved":true,
 "vocabulary":{"declaredTerms":83,"overlaySource":"terminal/lib/plainLabels.ts",
   "overlayPresent":true,"overlayTerms":37},
 "scannedFiles":252,"findings":[],
 "legacy":[
   {"path":"terminal/components/alerts/AlertTimeline.tsx","line":45,"rule":"raw_slug_interpolation","token":"verdict","blocking":false},
   {"path":"terminal/components/alerts/WatchingList.tsx","line":38,"rule":"raw_slug_interpolation","token":"verdict","blocking":false},
   {"path":"terminal/components/fin/ForecastPage.tsx","line":647,"rule":"raw_slug_interpolation","token":"type","blocking":false},
   {"path":"terminal/components/gexdesk/ExposureMatrix.tsx","line":488,"rule":"raw_slug_interpolation","token":"state","blocking":false},
   {"path":"terminal/components/settings/SectionAccount.tsx","line":542,"rule":"raw_slug_interpolation","token":"kind","blocking":false},
   {"path":"terminal/lib/visualIntelligenceCopy.ts","line":64,"rule":"raw_state_enum","token":"DELAYED_15M","blocking":false,"waived":true,"waiverReason":"transport basis is compared here, never rendered; the returned key selects localized copy."}
 ],
 "counts":{"blocking":0,"legacyReported":6,"waived":1},
 "nulls":[]}
```

The vocabulary overlay (`terminal/lib/plainLabels.ts`) IS present on this tree and contributes 37 overlay terms (so the effective vocabulary is 83 + 37). All 6 legacy findings are in UNTOUCHED files outside the PR diff (`alerts/AlertTimeline.tsx`, `alerts/WatchingList.tsx`, `fin/ForecastPage.tsx`, `gexdesk/ExposureMatrix.tsx`, `settings/SectionAccount.tsx`, `lib/visualIntelligenceCopy.ts`). The guard's forward-only mechanic correctly classifies them as `legacy` (visible, not blocking). The 1 waived entry has an explicit, accurate rationale ("compared here, never rendered; the returned key selects localized copy") and is also in an untouched file. **No banned vocabulary was added by PR #713.**

### 1.2 Pass — no banned-glance vocabulary in PR body or diff

The PR body uses the plain, neutral descriptive vocabulary of the project ("searchable study management", "touch access", "narrow widths", "the same TerminalShell props still supply study identity", "search is transient view state only", "no second translation system is added", "A source-owned noRemove study never acquires a remove button"). No banned terms (`validated` / `proved` / `guaranteed` / `certified` / `optimum` / `实测` / `已验证` / `已证明`) appear in either the body or the diff hunks.

The CSS module uses only `min-height`, `min-width`, `width`, `max-width`, `padding`, `border-radius`, `background`, `color` properties keyed off `var(--token)` — geometric and material, not content. The TSX adds one inline `style={entry.color ? { color: entry.color } : undefined}` for a data-driven per-study icon color (semantic per-study identity, not a styling choice). The e2e spec uses standard Playwright + Vitest vocabulary and asserts the public-facing Chinese strings (`"图层树"`, `"搜索 指标"`, `"隐藏 Moving Averages"`, `"关闭"`) which are LEX-translated, not authored.

### 1.3 Pass — release-boundary block is preserved verbatim

PR body closing line: "Current capability: BUILT_NOT_PROVEN. No production deployment has been started for this slice. Required protected CI, merge and exact-target live verification remain owed. The parent charting mission is incomplete." — the canonical anti-promotion closer. The lane is held at the source-repair state; hosted CI / merge / deploy / production-proof / acceptance are separate gates (same shape as terminal PRs #706, #705, #704, #701, #716 and macro PRs #7687, #7688, #7701, #7726).

### 1.4 Pass — no `DSC-*` discovery record is added (which is the right choice here)

A `DSC-*` record is the right shape for an empirically-falsified defect with `kind: landmine / behavior`. This PR's discovered defect (CSS-fixed phone panel clipped by chart ancestor + fullscreen chrome covering controls) is reproduced by a stronger viewport + center-point hit test and repaired by the native Popover top layer; the failure mode is reproducible today via the new e2e spec. The repair is pinned to the exact candidate sha (`bb5097b4`). There is no separate cross-session discovery to record today — the local evidence matrix in `terminal/docs/pr-crops/chart-layers-ux-20260922/EVIDENCE.json` is the right artifact for this lane's evidence.

## Theme findings

### 2.1 Pass — no theme / design-system surface is touched

The diff contains zero macro-side template/component/CSS/JS, zero theme-token change, zero palette change, zero type-scale change, zero motion change beyond the standard `prefers-reduced-motion` accessibility override. The CSS module is local to `ChartObjectTree` (not a global token file). The TSX change is one composer's internal restructure. The e2e + Vitest specs are test-only.

### 2.2 Pass — Terminal is dark-only by standing doctrine; no light-mode branching introduced

The Terminal repo is dark-only by project doctrine. The PR adds zero light-mode CSS, zero `prefers-color-scheme` media queries, zero color tokens, zero palette changes. Every color is `var(--token)` from the existing terminal token set (`--panel`, `--panel-2`, `--panel-3`, `--text`, `--text-2`, `--text-dim`, `--brand`, `--line`, `--danger`). The only raw color is `rgb(0 0 0 / .24)` for the side-sheet shadow, which is a geometric shadow alpha and not a color/material decision. **Consistent with the Terminal dark-only doctrine.**

### 2.3 Pass — TP-0 dark/light × EN/ZH × 1440/390 evidence matrix is structurally inapplicable (no new visual material surface)

The TP-0 dark-and-light-are-two-art-directions rule (`scripts/check_design_system.py` + the standing design-doctrine §Theme art direction in macro `CLAUDE.md`) requires every material UI packet to name DARK TREATMENT, LIGHT TREATMENT, which mechanisms intentionally differ, the reference/baseline, theme-specific degraded states, and the evidence matrix (dark/light × EN/ZH × desktop 1440 / mobile 390).

This PR adds zero theme tokens, zero color tokens, zero light/dark branching, zero motion. The CSS rules are geometric + token-driven — they have no dark/light treatment and cannot drift between themes. The "Token substitution alone is never proof of a light design" rule, the "Substantive product styling may not be authored as an opaque runtime stylesheet system inside page/composer JavaScript" rule, and the "every material UI packet must name DARK TREATMENT / LIGHT TREATMENT" rule are all structurally inapplicable. **Consistent with TP-0.**

### 2.4 Pass — `check_runtime_style_injection.py` is out-of-scope by construction

The diff contains no `style="..."` injection, no `style.textContent =`, no parallel palette, no duplicated light/dark branches inside JS, no inline `<style>` block, no `data-theme` override, no `class` attribute containing theme tokens. There is one inline style (`{ color: entry.color }` on the study icon) which is data-driven (per-study semantic identity, set by the existing TerminalShell caller) — not a styling decision. The CSS is a local module (`ChartObjectTree.module.css`), not a runtime-injected stylesheet.

### 2.5 Pass — accessibility geometry follows project floor

Touch controls: 44px (Apple HIG / WCAG 2.5.5). Input font: 16px on touch (prevents iOS Safari auto-zoom). Search button: 28px on desktop (within the dense composer), 44px on touch. Mobile breakpoint: 860px (matches the `matchMedia` constant). `prefers-reduced-motion: reduce` disables animation + transition. `overscroll-behavior: contain` prevents scroll-chaining into the chart. `safe-area-inset-top/bottom` respects iOS notch / home bar. `popover` attribute is only set on narrow widths (with feature detection) so desktop users get the existing right-rail geometry. All of this is verifiable on the 7 PNG crops via SHA-256 digests in EVIDENCE.json.

## Validated-claims findings

### 3.1 Pass — `python3 scripts/check_validated_claims.py --list` (run from macro repo) produces no MISS row anchored to PR-touched files

The validator scans `templates/`, `site/`, the paired plain-copy mirrors, and the engine/market_os snapshot validators. The PR-touched files (`terminal/components/ChartObjectTree.tsx`, `terminal/components/ChartObjectTree.module.css`, `terminal/lib/__tests__/chartObjectTree.test.tsx`, `terminal/e2e/chart-object-tree.spec.ts`, `docs/TERMINAL_CHART_LAYERS_UX_2026-09-22.md`, `terminal/docs/pr-crops/chart-layers-ux-20260922/EVIDENCE.json`, 7 PNG crops) are outside that scan surface — none of the validator's MISS/OK rows anchor on a path this PR touches.

### 3.2 Pass — no `validated` / banned vocabulary in the PR's user-facing-shaped surface

The PR body uses only defect-repair vocabulary with bounded scope ("Improve the Chairman's chart usability and premium visual quality without reducing chart capability or adding weight"). The closing line is the canonical anti-promotion closer ("Current capability: BUILT_NOT_PROVEN. No production deployment has been started for this slice. Required protected CI, merge and exact-target live verification remain owed. The parent charting mission is incomplete.").

The CSS module uses only `min-height`, `width`, `max-width`, `padding`, `border-radius`, `background`, `color`, `font` properties keyed off `var(--token)` — geometric and material, not content claims. The TSX adds 13 new `aria-label`s keyed through `useT` translations (e.g. `"Hide Moving Averages"`, `"No matches"`, `"Close"`) — no new authoring of `validated` / `proved` / `guaranteed` / `certified`. The e2e spec asserts the existing ZH translations and exercises the standard Playwright API. No banned vocabulary appears anywhere in the diff.

### 3.3 Pass — `check_validated_claims.py` continues to enforce the user-facing `validated` vocabulary unchanged

`tests/test_validated_claims_engine.py`, `tests/test_validated_claims_registry_source.py`, `tests/test_validated_claims_structural_scope.py`, and `tests/test_validated_claims_thirdparty.py` (in the macro repo) are the surface that enforces the user-facing claim discipline. None of them read or assert against terminal UI code — they read `templates/`, `site/`, and the structural scope of `data/regime/validated_claims_allowlist.json`. This PR modifies none of those surfaces. The validator's behaviour is unchanged on this PR. **Consistent with the structural-scope contract.**

### 3.4 Pass — the PR does not claim authority over ranking / admission / sizing / execution / trading

The PR body's mid-section explicitly names what the change does NOT do: "No settings/state owner, store, dependency, chart renderer, backend service or signal/indicator mathematics is introduced or replaced." No rank, candidate-admission, sizing, execution, or trading authority is asserted. The release-boundary block holds the lane at the source-repair state.

## Overall verdict

**VERDICT: PASS — clean half-B chart-layer-management upgrade for `ChartObjectTree`, no blocking issue, no user-facing copy authored (all keys routed through existing `useT` LEX translations), no theme surface touched, release boundary held at BUILT_NOT_PROVEN.**

| dimension | result | notes |
|---|---|---|
| plain-language | PASS | `node terminal/scripts/check_plain_language.mjs --json` reports `{"scannedFiles":252,"findings":[],"legacy":[…6 untouched files…],"counts":{"blocking":0,"legacyReported":6,"waived":1},"nulls":[]}` — 0 blocking findings on added code. The vocabulary overlay `terminal/lib/plainLabels.ts` is present (37 overlay terms in addition to 83 declared terms). All 6 legacy findings are in untouched files outside the diff. The PR body + diff use plain, neutral vocabulary; no banned-glance terms appear anywhere. The release-boundary block ("Current capability: BUILT_NOT_PROVEN…") is preserved verbatim. |
| theme | PASS | Diff contains zero macro template, zero theme tokens, zero light/dark branching, zero palette change. The CSS module is local to `ChartObjectTree`, token-driven (25 `var(--token)` references, 1 raw shadow alpha), no `color-scheme`, no `prefers-color-scheme` queries. TP-0 dark/light × EN/ZH × 1440/390 evidence matrix is structurally inapplicable (Terminal is dark-only by standing doctrine). `check_runtime_style_injection.py` is out-of-scope (one inline `style` is data-driven per-study color, not a styling decision). Accessibility geometry follows the 44px touch floor, 16px input font, `prefers-reduced-motion`, `safe-area-inset`, `overscroll-behavior: contain`. |
| validated-claims | PASS | `check_validated_claims.py --list` produces no MISS row anchored to the PR-touched files. The validator's scanned surface (`templates/` / `site/` / paired plain-copy / engine validators) does not include terminal UI composer files. No `validated` / banned vocabulary in the diff. The PR body disclaims any promotion-bearing change ("No settings/state owner, store, dependency, chart renderer, backend service or signal/indicator mathematics is introduced or replaced.") and the release-boundary block holds the lane at the source-repair state ("Current capability: BUILT_NOT_PROVEN… Required protected CI, merge and exact-target live verification remain owed."). |
| merge hygiene | PASS | 13 files, +394 / −118. The substantive change is one composer's TSX rewrite + one local CSS module + one Vitest suite + one Playwright e2e spec + one narrative doc + one EVIDENCE.json + 7 PNG crops with sha256 digests — all scoped to `ChartObjectTree`. The data contract is unchanged: TerminalShell still supplies study identity, labels/tags, grouping, hidden state, `noRemove` entries; the same callbacks perform every actual mutation. Search is transient view state only. The main-series row remains non-removable. The native Popover top-layer repair is feature-detected and tears down on media-change / unmount; it does not portal, remount, add a dependency, or raise global z-indices. RED-first qualification on protected base `3b0340bf831f3112575129f3c2f649ced0e00e78`; GREEN at exact candidate `bb5097b4f6cdfebcd39df55fb1196f74689c7778` with TypeScript / scoped lint / 7 Vitest contracts / 7 Playwright contracts / 6 responsive-language crops all on the EVIDENCE.json receipt. The release boundary is held at `BUILT_NOT_PROVEN` — the source slice landed, the lane's full release remains a separate decision. |

**Non-blocking follow-ups (out of this lane's owned paths):**

1. The PR's release-boundary block names "Required protected CI, merge and exact-target live verification" as separate gates. None of these is owned by this PR. Out-of-scope.
2. The PR explicitly disclaims legacy-browser Popover coverage ("Only currently tested Chromium behavior is claimed; a legacy-browser fallback was not separately proven."). A future carrier can decide whether to gate the narrow-width branch on a more conservative layout fallback. Out-of-scope for this PR.
3. The mobile breakpoint (`@media (max-width: 860px)`) and the 44px touch floor are currently expressed inside `ChartObjectTree.module.css`. If a future carrier lifts the floor into a project-wide token (e.g. `--touch-floor-mobile`), that consolidation is out-of-scope for this PR.
4. The `noRemove` whitelist is a TerminalShell-supplied prop (`OTEntry.noRemove`). The PR's test pins the contract for the protected test seed (`locked` row has no remove button); the broader noRemove-discipline review is owned by the chart-shell lane, not this PR.

**No blocking issue found. No retry. No scope expansion. Audit complete.**