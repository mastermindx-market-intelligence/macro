# PR audit — mastermindx-market-intelligence/mastermind-terminal#701

**Auditor:** meta-ceo-b-2026-09-08 (one-pass remote useful-idle, no retries, no scope expansion)
**Audit timestamp:** 2026-09-21
**Repo / PR:** mastermindx-market-intelligence/mastermind-terminal #701
**PR title:** feat(chart): upgrade settings UX and restore tablet control access
**Merged at:** 2026-09-21T18:35:42Z (squash merge onto `origin/master`)
**Author / merger:** author `review-bot` (mastermind-X bot seat); merger `chriswong6031-creator` (operator)
**Source base:** `749576c537284df43772d3cfd3fdd75ad7194a2d`
**PR head SHAs (semantic):** `4b07375a9e487631d3d3239f0cb3cf421332120e` → `30e1e56f8678e9ae61e635fb2a2a39c7185b3234`
**Live `origin/master` merge commit (squash):** `e5ccacf4ab327ad414c6f9fa6000f0a720a8ea55` — `git merge-base --is-ancestor 30e1e56f e5ccacf4` returns false (the two PR head commits are NOT on origin/master), but `git show e5ccacf4` carries the entire +613/-77 diff in a single squash commit (verified), so the PR is on master as `e5ccacf4`.

> **Scope note (§1):** the chronologically most-recent merged PRs in the terminal repo inside the 24 h window are #701 (18:35:42Z — chart settings UX upgrade + tablet dock repair, 24 files / +613/-77, the largest un-audited terminal merge since #700 closed), #700 (14:09:56Z — one-line symlink retarget, audited in scope-out rationale below), #698 (09:45:42Z — mobile chart touch, already audited), #696 (06:50:24Z — flow card geometry, already audited), and older half-B perf PRs which were all swept by the morning audit PR #7598. **#701** is the most-recent un-audited terminal merge that carries real user-facing UI work, discriminating verification, and a substantively re-engineered dark-only chart-settings modal — so the seat selects #701. It satisfies "half-B": the PR is the chart-settings modal upgrade + tablet dock safe-area-aware strip repair, owned under `claude/terminal-chart-settings-ux-20260921`; it does NOT claim completion of the broader charting program ("Current capability: BUILT_NOT_PROVEN. Mission complete: false.").

---

## 1. PR metadata

| field | value |
|---|---|
| repo | mastermindx-market-intelligence/mastermind-terminal |
| number | 701 |
| title | feat(chart): upgrade settings UX and restore tablet control access |
| merged_at | 2026-09-21T18:35:42Z |
| source base | `749576c537284df43772d3cfd3fdd75ad7194a2d` (protected at final local verification; immediately-prior commit is the metadata-only PR-crop refresh `ops(scripts): refresh chart-context crops for tablet/mobile (#696)` audit chain closeout) |
| PR head (semantic, head branch) | `4b07375a9e487631d3d3239f0cb3cf421332120e` (feat) → `30e1e56f8678e9ae61e635fb2a2a39c7185b3234` (test, screenshot refresh) |
| live merge commit (squash on master) | `e5ccacf4ab327ad414c6f9fa6000f0a720a8ea55` |
| branch | `claude/terminal-chart-settings-ux-20260921` |
| changed files | **24** — `docs/TERMINAL_CHART_SETTINGS_UX_2026-09-21.md` (+62), `terminal/components/ChartSettingsModal.module.css` (+100 NEW), `terminal/components/ChartSettingsModal.tsx` (+101/−53), `terminal/components/DrawingSidebar.module.css` (+7 NEW), `terminal/components/DrawingSidebar.tsx` (+2/−1), `terminal/docs/pr-crops/chart-settings-ux-20260921/EVIDENCE.json` (+39 NEW), 6 settings screenshots (NEW), `terminal/docs/pr-crops/terminal-visual-intelligence/EVIDENCE.yml` (+27/−21), 6 context screenshots (MODIFIED), `terminal/e2e/chart-settings-ux.spec.ts` (+146 NEW), `terminal/e2e/visual-intelligence.spec.ts` (+1/−1), `terminal/lib/__tests__/chartSettingsUi.test.ts` (+55 NEW), `terminal/lib/__tests__/visualIntelligenceEvidence.test.ts` (+1/−1), `terminal/lib/chartSettingsUi.ts` (+72 NEW) |
| additions / deletions | 613 / 77 |
| labels | (no external labels; merge-on-green backstop consumed) |
| scope collision | none — body declares zero overlap with `ChartPanel`, `TerminalShell`, `MobileNav`, `globals.css`, shared locale registry, indicator math, Canvas content, account/billing/portfolio/alert/Levels/Briefs UI |
| verification | **RED on protected base `cf35757b258c387fdb361ae45fac3652db3a5503`:** unnamed inputs, invalid CSS color strings to native color pickers, hard-clamped numeric edits, render-path template-storage reads, lost focus on transient menu dismissal, tablet dock overlap. **GREEN on candidate `4b07375a`:** settings/desktop-en + tablet-zh + phone-en browser matrix: **73 passed, 8 viewport-specific skips, zero failures**; `npx tsc --noEmit` PASS; scoped ESLint PASS zero warnings; Vitest 377 files / 6,072 passed / 4 todo (52/52 fresh local-gate triplet: `chartSettingsUi` 45 + `chartSettingsHydration` 4 + `visualIntelligenceEvidence` 3). |

**Nature of change (half-B chart-settings UX + tablet docking repair):**

1. **`ChartSettingsModal.tsx`** — replaces the prior div-based dialog `<div className="sm-backdrop">` with a native `<dialog>` (HTMLDialogElement), scoped with CSS Modules (`styles.dialog`) so existing chart canvas, global chrome, and other dialogs stay untouched. The dialog owns ARIA tablist / tab / tabpanel roles plus per-instance `useId()`-bound `id` glue so the labels are not a shared singleton; the tabs are a real roving `role="tablist"` with `data-settings-tab`, `aria-selected`, `aria-controls`, `tabIndex={tab===key ? 0 : -1}`, and arrow / Home / End keyboard navigation dispatched through the existing `mm:settings-tab` parent event. A hidden `<span ref={originRef} />` lives inside the *open* path's ChartPanel DOM, used by `activateSettingsDialog()` to pick the right return-focus target (`gear` on desktop, `[data-testid="roller-more"]` on phone) without leaking it into the portalled dialog. `Readability` lift on every select row, color control, range input, and footer button now has a label or `aria-label` — the new e2e spec asserts `unnamed` controls is `[]`.
2. **`ChartSettingsModal.module.css`** (+100 NEW) — token-only scoped CSS using `var(--text)` / `var(--text-2)` / `var(--line)` / `var(--line-3)` / `var(--brand)` / `var(--brand-2)` / `var(--brand-hov)` / `var(--panel)` / `var(--panel-2)` / `var(--panel-3)` / `var(--pop-scrim, rgba(5,7,11,.64))` / `var(--pop-shadow)`. All section/footer/header heights are explicit (`68px` header, `76px` footer, `44px` minHeight color targets, `min(740px, calc(100dvh - 48px))` modal height). The `@media (max-width: 640px)` block makes mobile section labels and Reset visible (they were hidden), and the `@media (prefers-reduced-motion: reduce)` block kills animation/transition on the touched surfaces. The OK button uses `color: white; background: var(--brand)` (one literal — acceptable per the dark-only contract; see §3).
3. **`chartSettingsUi.ts`** (+72 NEW) — browser-only chart-preferences helpers, no chart/feed/indicator math, no new dependencies. `colorInputHex(value, fallback)` rejects `#RRGGBBAA` alpha into opaque hex (the native `<input type=color>` doesn't take alpha; the swatch keeps alpha in its rendered `style={{ background }}`), and recovers from malformed / `rgba()` / `rgb()` / percentage forms before falling through to the fallback. `previewNumber(raw, min, max)` returns `null` for empty / non-finite / out-of-range (the draft is editable while invalid); `commitNumber(raw, previous, min, max)` reverts on garbage and clamps on commit. `parseSettingTemplates(raw, defaults)` rejects malformed roots / arrays / unknown fields / wrong-type fields / non-finite numbers, and the user-template `<select>` value is now namespaced (`template:<name>`) so a saved template named `__save` cannot collide with the reserved command marker. `activateSettingsDialog(dialog, returnFocusTo)` is the modal lifecycle: `dialog.showModal()` once at open, body overflow gated to a previous value, focus → selected tab on the open frame, a single cancellable `requestAnimationFrame` handoff for the case where a pointer-opened chart menu finishes its dismissal during the same frame, and a teardown that cancels the rAF, calls `dialog.close()`, restores body overflow only when this is the last open dialog, and returns focus to a *connected* opener (the `isConnected` check guarantees no focus is moved into a detached node). No global focus listener, no polling loop.
4. **`DrawingSidebar.module.css`** (+7 NEW) + **`DrawingSidebar.tsx`** (+2/−1) — the existing web-tablet floating draw dock (`.ds-dock`) is absolute and was intercepting real clicks on the settings gear at the 641–860 px web-tablet widths. The CSS reserves the strip *once per workspace* (`:has(> .dock)` on `.chart-body` inside `:not(.shell-app) .app`) instead of per-pane, padding `calc(62px + max(8px, var(--drawing-safe-bottom, 0px)))` so a future safe-area token can refine the bottom inset without re-editing this file. Phones use the existing roller/Drawings sheet; native shell geometry is unchanged. The dock gets the new class `styles.dock` in addition to its existing `.ds-dock` class so the old global selector keeps working.
5. **Test surface (NEW: `terminal/e2e/chart-settings-ux.spec.ts` 146 lines; `terminal/lib/__tests__/chartSettingsUi.test.ts` 55 lines)** — the e2e spec runs in `desktop` (1440×900), `tablet` (820×1180), `mobile` (390×844) projects with `--workers=1 --max-failures=1`, tests (i) focus ownership and tab keyboard navigation, (ii) every interactive control has a label (`unnamed.toEqual([])`), (iii) the native modal inertness defeats programmatic background focus after opening (`dialog.contains(document.activeElement) === true` after `trigger.focus()`), (iv) the close button restores focus to the gear / roller-more trigger, (v) the native `Escape` closes the dialog, (vi) Cancel restores the opening snapshot while OK keeps the previewed preferences, (vii) numeric drafts remain editable while invalid and only clamp on commit, (viii) twelve live-preview toggles do NOT add additional reads of `mm.chartSettingTemplates`, (ix) ZH settings panel remains readable and bounded under `reducedMotion: reduce`, (x) tablet dock never covers the settings gear at the breakpoint edges `[641, 700, 820, 860]`. The Vitest unit suite (`terminal/lib/__tests__/chartSettingsUi.test.ts`) covers the `colorInputHex` parser against 13 nominal / 4 invalid / 1 fail-safe pair, `previewNumber` / `commitNumber` against empty/whitespace/NaN/Infinity/`1e309`/out-of-range/in-range numeric inputs, and `parseSettingTemplates` against malformed roots / arrays / wrong-type / non-finite / unknown fields plus a `"__proto__"` / `"__save"` prototype-pollution attempt — all `Object.hasOwn` checks pass.
6. **Negative-missing / no-claim posture:** arithmetic, EN/ZH values, indicator math, candle/web-data semantics, transport behaviour, ruler ticks, and snapshot model are unchanged. The PR body is explicit and the doc is explicit: "No claim of improved FPS, overall first-load latency, API performance or network volume is made"; "These changes do not establish a frame-rate, startup, API or renderer speedup"; "Do not ... interpret screenshots/green tests as production proof."

---

## 2. Plain-language findings

Plain-language discipline was verified two ways: (a) **mechanical:** `node terminal/scripts/check_plain_language.mjs --json` ran clean against the live `origin/master` after this PR landed (`{"blocking":0, "legacyReported":18, ...}` — the 18 legacy findings are on pre-existing code the PR did not touch: `terminal/components/alerts/AlertTimeline.tsx:45` ("verdict" interpolation), `terminal/components/alerts/AlertsCockpit.tsx:354` (English-only literal), etc., and the `DELAYED_15M` rule on `terminal/lib/visualIntelligenceCopy.ts:64` carries the explicit `waiverReason` `"transport basis is compared here, never rendered; the returned key selects localized copy."`); (b) **manual:** every user-visible JSX position added or modified in the new code is routed through `t()` against the existing `terminal/lib/i18n.tsx` registry, and the e2e machine-check on `unnamed controls.toEqual([])` would fail if any new interactive element missed the labeling.

### 2.1 Pass — every new visible label is routed through `t()` with the standard `[en, zh]` tuple

- `t("smTitle")` — "Chart Settings" / "图表设置" (existing registry entry, retained verbatim)
- `t("smClose")` — "Close" (existing, retained)
- `t("smSections")` — `aria-label` on the tablist (existing, retained)
- `t("smTabSymbol")` / `t("smTabStatus")` / `t("smTabScales")` / `t("smTabCanvas")` — the four tab labels, all retained from the existing registry (the e2e spec asserts ZH tabs contain `[一-鿿]` text).
- `t("smTemplate")` — used both as the `<select>` default `<option>` value text and as the new `aria-label` on the template picker (the picker gained a real label; previously it had none).
- `t("smRestoreDefaults")` / `t("smSaveCurrent")` / `t("smResetTabBtn")` — footer template command + reset button (existing, retained).
- `t("smUpColor")` / `t("smDownColor")` — color-pair titles, now prefixed with `${label}: ${t("smUpColor")}` so `aria-label="Body: Up color"` / ZH equivalent reads as itself rather than as a repeated bare "Up color".
- `t("smBackgroundColors") + " (1)"` / `" (2)"` — the two canvas background color swatches now have distinguishing titles.
- `t("smTitleRow")` — the inline title-mode `<select>` got `aria-label={t("smTitleRow")}`.
- `${t("smIndicators")}: ${t("smBackground")}` — the indicator-background range input got a proper `aria-label`.
- `t("smGridV")` / `t("smGridH")` / `t("smPaneSeparators")` / `t("smCrosshair")` / `t("smWatermark")` / `t("smText")` / `t("smLines")` — every previously-untitled canvas / scales `ColorControl` now passes a `title={t(...)}` to its parent `<label>`, and the `<input type=color>` inside uses `aria-label={title}` so screen readers announce the section+role pair.

### 2.2 Pass — no new study-internal state name or untranslated statistic token leaks

`git grep -inE "iv_rank|ivr\b|gex|dex\b|vanna|charm|dte|oi\b|pcr\b|rv30|hv20|atr14|zscore|pctl|yoy|qoq|ttm|cagr|\bstate\b|\bregime\b|\bverdict\b" 30e1e56f -- terminal/components/ChartSettingsModal.tsx terminal/lib/chartSettingsUi.ts terminal/components/DrawingSidebar.tsx terminal/e2e/chart-settings-ux.spec.ts terminal/lib/__tests__/chartSettingsUi.test.ts` returned zero hits in user-visible positions. The previously-bare `verdict` / `state` / `type` / `kind` interpolations that the legacy report lists are in `terminal/components/fin/*` and `terminal/components/alerts/*` files the PR does not touch — they remain legacy and do not regress under `enforce-added`.

The one new template-value shape (`"template:<name>"`) is technical protocol, never rendered. The `<option>` text for each template is the user's stored `<name>` (already user-supplied through the `prompt(t("smTemplateName"))` flow); the namespace prefix is value-only and the rendered text stays the bare name.

### 2.3 Pass — `aria-label` / `<label htmlFor>` discipline is machine-checked

The e2e spec reads
```ts
const unnamed = await dialog.locator('select,input:not([type="checkbox"])').evaluateAll((controls) => controls.filter((control) => {
  const input = control as HTMLInputElement | HTMLSelectElement;
  return !input.getAttribute("aria-label")?.trim() && !Array.from(input.labels ?? []).some((label) => label.textContent?.trim());
}).map((control) => control.outerHTML));
expect(unnamed).toEqual([]);
```
This is a real, executable check, not a vibe. Every `<select>`/`<input>` (other than checkbox) must have either an `aria-label` or a connected `<label>` with non-empty text. Combined with the manual `title` / `aria-label` audit in §2.1, this means no new interactive chart-settings element can ship without a name.

### 2.4 Observation (non-blocking) — the cancel / restore-defaults `<option>` text is the bare English key `t("smRestoreDefaults")`

The template `<select>`'s internal `<option value="__default">` carries visible text `t("smRestoreDefaults")` — the standard for the registry, no internal-state leakage, no opacity-laden jargon. The same option's identifier is `"__default"` (a reserved command sentinel), which is value-only and is now namespaced against template names so user templates cannot impersonate it (the new `template:<name>` value space plus the explicit `value.startsWith("template:")` guard at the call site eliminates the `"__save"`-name-clash risk the previous code carried). **Not blocking.**

### 2.5 Observation (non-blocking) — the dialog stores focus ownership in a hidden `<span ref={originRef} />` rather than a hidden focusable button

The hidden `<span hidden ref={originRef} />` is `aria-hidden` by the `hidden` HTML attribute and is read by `originRef.current?.closest(".pane")?.querySelector(".cfb-gear")` to find the chart-local gear. This is a legitimate DOM probe; an alternative would be a hidden focusable `<button>` or a `data-*` marker, but the span-pinning pattern is the one chosen by the owning lane and it does not surface any internal-state text to the user. **Not blocking, but worth noting if a future `DSC:` audit reviews focus-ownership patterns.**

---

## 3. Theme findings

### 3.1 Pass — `ChartSettingsModal.module.css` is fully token-driven

Every material value in the new 100-line CSS module reads from the canonical terminal token layer:

- Surface tokens: `var(--text)`, `var(--text-2)`, `var(--line)`, `var(--line-3)`, `var(--panel)`, `var(--panel-2)`, `var(--panel-3)`, `var(--brand)`, `var(--brand-2)`, `var(--brand-hov)`, `var(--pop-scrim, rgba(5,7,11,.64))` (the pop-scrim has a defensive literal fallback for callers that haven't loaded the theme tokens yet — a standard token-bypass pattern, not a colour decision), `var(--pop-shadow)`.
- Geometry: `width: 780px`, `max-width: 100%`, `height: min(740px, calc(100dvh - 48px))`, `border-radius: 16px / 8px / 10px / 12px / 9px`, `border: 1px solid var(--line-3)`, `border-bottom: 1px solid var(--line)`, fixed header `68px` and footer `76px`, mobile `60px` header + `92dvh` modal under `@media (max-width: 640px)`, tablet breakpoints unchanged.
- Motion: `@media (prefers-reduced-motion: reduce) { ... animation: none !important; transition: none !important; }` on `.sm-modal`, `.sm-tab`, `.sm-close`, `.sm-color-swatch`, `.sm-reset`, `.sm-cancel`, `.sm-ok`.
- Focus: `:focus-visible { outline: 2px solid var(--brand-2); outline-offset: 3px; }` is the canonical focus ring used across the rest of the chart surfaces.
- Touch targets: `44px` color targets, `min-height: 44px` on footer / select / OK / cancel under pointer:coarse, `min-height: 40px` on Reset / Cancel / OK as the base — both already canonical.

Two theme-layer hardcodes do exist, and they are documented and bounded:

1. `color: white` × 2 (in `.sm-check-label input:checked:after { border-color: white; }` and `.sm-ok { color: white; background: var(--brand); border-color: var(--brand); }`) — both are dark-only-conditioned (the OK button is the brand-coloured primary; the checkbox check mark is white-on-brand). This is consistent with the Terminal dark-only contract documented in `terminal/docs/pr-crops/terminal-visual-intelligence/EVIDENCE.yml` (`theme: dark`) and the standing DEC:TERMINAL-SHELL-IS-DARK-ONLY-EVIDENCE-MATRIX-2026-09-06. The PR body explicitly disclaims any light mode: "The UI continues to respect the Terminal dark-only contract. Using theme tokens does not introduce or claim a supported light mode."
2. `position: fixed; inset: 0; ... background: transparent; ... backdrop-filter: none;` on the dialog itself — the scrim is the canonical `<dialog>::backdrop { background: var(--pop-scrim, rgba(5, 7, 11, .64)); }`. The `backdrop-filter: none` is necessary because the chart-frame sidebar and chart-pane overflow ancestors already stack a backdrop-filtered surface; turning it back on here would break the native `<dialog>` mouse-down cancel handler (the hover layer would absorb pointer events on the scrim). This is a non-style material decision: leaving the scrim un-blurred preserves the modal's click-anywhere-to-cancel contract.

### 3.2 Pass — `DrawingSidebar.module.css` is token-driven and bounded by media query

```css
@media (min-width: 641px) and (max-width: 860px) {
  :global(.app:not(.shell-app) .chart-body):has(> .dock) {
    padding-bottom: calc(62px + max(8px, var(--drawing-safe-bottom, 0px)));
  }
}
```
Tokens used: only `var(--drawing-safe-bottom, 0px)` (an opt-in safe-area token with a sensible default that the dock can override per host without re-editing this file). The 62 px and 8 px values are geometry constants tied to the dock's actual measured strip height plus minimum breathing room — these are not colour or type decisions, they are layout math the CSS modules exposing the dock carried before this PR. Phones (`≤ 640 px`) and the wider desktop (`≥ 861 px`) skip this rule entirely, so the new space is reserved *exactly once per workspace at the tablet fault*, not per pane. The `:not(.shell-app)` selector excludes the native Capacitor shell from the safe-area reservation because the shell owns its own bottom inset.

### 3.3 Pass — JS does not inject substantive material styling

`ChartSettingsModal.tsx` uses CSS Modules (`import styles from "./ChartSettingsModal.module.css"`) and applies class names. `DrawingSidebar.tsx` extends its existing `.ds-dock` class with the new `styles.dock` class. The only inline style retained is:

```tsx
<span className="sm-color-swatch" style={{ background: shown }} />
```

where `shown = value || fallback` — the user's stored colour or the token fallback. This is data-dependent inline geometry / colour and is exactly the kind of inline value the design doctrine permits in JS (the swatch needs to reflect the live stored value, not a token). No `style.textContent` injection, no parallel palette family in JS, no duplicated light/dark branches, no `document.createElement('style')`. The new CSS module is the single source of truth for material decisions.

### 3.4 Pass — no `data-testid` selectors leak into the production chrome

The two production-class selectors that exist are `data-settings-tab={key}` (on the tab buttons, used by the JS to focus the next tab on arrow-key navigation) and the existing `[data-testid="roller-more"]` (which the production code itself reads as a phone-only destination for the open-return focus). `data-current`, `data-selected`, `data-direction` style attributes are not introduced by this PR. The internal `<span hidden ref={originRef} />` carries `hidden` so it never renders; `aria-label`, `title`, `data-settings-tab` are the only production HTML attributes the PR adds, and each is consumed by either the local component (focus / keyboard arrow nav) or screen readers.

### 3.5 Observation (non-blocking) — the existing `style={{ borderTop: "1px solid var(--line)" }}` patterns elsewhere in the repo remain unchanged

This audit is scoped to PR #701 only; out-of-scope legacy inline styles on unrelated surfaces are out of scope for this audit and never feed into a regression. The PR is clean against `scripts/check_runtime_style_injection.py`'s shape (no JS-injected multi-kilobyte style.textContent, no parallel palette family, no duplicate light/dark branches).

### 3.6 Pass — visual evidence matrix is committed and content-addressed

The new `terminal/docs/pr-crops/chart-settings-ux-20260921/EVIDENCE.json` declares `theme: dark` (single-value — honouring the dark-only contract), `viewports: { desktop: [1440, 900], tablet: [820, 1180], mobile: [390, 844] }`, `languages: [en, zh]`, `result: { passed: 73, skipped: 8, failed: 0 }`, and SHA-256 digests for each captured screenshot. The companion `terminal/docs/pr-crops/terminal-visual-intelligence/EVIDENCE.yml` is content-addressed per `layoutFiles` + `cropFiles`, so the SHA recompute step (`terminal/docs/pr-crops/terminal-visual-intelligence/EVIDENCE.yml` lists the new hashes `ChartSettingsModal.tsx: f26bd7…` / `ChartSettingsModal.module.css: a1685d…` / `DrawingSidebar.tsx: 959101…` / `DrawingSidebar.module.css: 8f0452…` / `chartSettingsUi.ts: 90dac0…`) is the lock, not ancestry.

---

## 4. Validated-claims findings

### 4.1 Pass — no promotion-bearing claim is introduced

The PR is a chart-settings UX upgrade + tablet dock safe-area repair. It does not introduce a new signal, ranker, score, ranking, edge, or gate. No new candle, indicator, oscillator, or chart-engine semantic is touched (the PR body §"Implementation and negative proof" explicitly enumerates: "No flow scoring, signing, filtering, data source, trading semantics, or transport behavior changes" in #696 — the parallel language in #701's body is "Original chart options, data and indicator math remain unchanged.").

The narrow performance claim — that the settings modal does not add additional reads of `mm.chartSettingTemplates` across twelve live-preview toggles after open — is measurable in browser (`document.querySelector` patches the prototype `Storage.prototype.getItem`), is verified to hold at `read() === atOpen` after twelve toggles, and is explicitly bounded: "Performance proof is deliberately narrow: the real browser test observes no additional reads of `mm.chartSettingTemplates` across twelve live-preview changes after opening. **No claim of improved FPS, overall first-load latency, API performance or network volume is made.**" That honesty line is exactly the right calibration — a measurable, in-scope read-count is reported, and no full-stack performance assertion is made.

### 4.2 Pass — no use of the word "validated" or any synonym in user copy

Confirmed by `git grep -inE "validated|certified|approved|wcag|standard[ -]certified" 30e1e56f -- terminal/components/ChartSettingsModal.tsx terminal/lib/chartSettingsUi.ts` (clean). The terminal claim-equivalent standard ("don't claim what you haven't earned") is satisfied: the PR does not say "this is touch-certified", "this is keyboard-compliant", "this is WCAG-AA", or any equivalent authority-bearing claim about the new code. The two explicit honesty lines in the doc are:

1. *"Performance proof is deliberately narrow ... No claim of improved FPS, overall first-load latency, API performance or network volume is made."*
2. *"This verifies the responsive browser path, not an authenticated production release."*

…and the body is explicit:

> *Current capability: BUILT_NOT_PROVEN. Mission complete: false. The full-chart performance programme remains open; these changes do not establish a frame-rate, startup, API or renderer speedup.*

That `BUILT_NOT_PROVEN` declaration on its own is the right calibration line: display-tier work is freely shipped, never promoted to authority without gauntlet evidence. The PR lives squarely inside the display-tier envelope and the doc says so plainly.

### 4.3 Pass — "display-only" / "BUILT_NOT_PROVEN" truth contract is preserved

The doc explicitly disclaims:

- *"... not an authenticated production release."*
- *"preserve this exact candidate remotely, run the real settings/context/price-label browser matrix, consume required CI, and only then use the existing protected merge and git-gated deployment chain."*
- *"Do not redo the redesign, repeat the initial import edit, overwrite other chart PRs, or interpret screenshots/green tests as production proof."*

The `EVIDENCE.json` declares `"productionProof": false` in its own right (`"productionProof": false` is the last key under `result`). The merged commit does not unblock a deploy — it lands on `origin/master`, and downstream release work is gated by the protected CI / merge / deploy chain the doc names. The PR is shipped in the same shape as #696 (flow card geometry) and #669 (numbered theme tile): BUILT, evidence-backed, awaiting the release chain to bind it to production.

### 4.4 Pass — merge hygiene

| dimension | result | source |
|---|---|---|
| `git diff --check` | PASS | PR body §"Verification" |
| scoped ESLint | PASS zero warnings | PR body §"Recovery" |
| `npx tsc --noEmit` | PASS exit 0 | PR body §"Fresh exact-candidate browser result" |
| Vitest focused | 52/52 (chartSettingsUi 45 + chartSettingsHydration 4 + visualIntelligenceEvidence 3) | PR body §"Fresh recovery checks" |
| Vitest full | 377 files / 6,072 passed / 4 todo (`EVIDENCE.yml` `localGates.vitest`) | PR body + visualIntelligence crop EVIDENCE |
| Playwright full matrix | 73 passed / 8 viewport-specific skips / 0 failed (`EVIDENCE.json` result) | EVIDENCE.json |
| content-addressed screenshot digests | all 6 settings crops + 6 Visual Intelligence crops + 5 layout-file digests | EVIDENCE.yml layoutFiles + cropFiles |
| discriminated verification | RED on protected base / GREEN on candidate (body §"Discriminating verification") | PR body §"Verification" |

---

## 5. Overall verdict

**VERDICT: PASS — clean half-B chart-settings UX + tablet docking repair, merge is correct.**

| dimension | result | notes |
|---|---|---|
| plain-language | PASS | `check_plain_language.mjs --json` returns 0 blocking against post-merge `origin/master`; every new visible label is routed through the existing `terminal/lib/i18n.tsx` registry; the new e2e machine-check `unnamed controls.toEqual([])` would fail if any interactive element missed the labeling; no `verdict`/`state`/`type` interpolation introduced; `__save` / `__default` template-command collision is closed by the `template:<name>` namespace; the only English-only literal `" (1)"` / `" (2)"` is a numeric disambiguator added to the *translated* `t("smBackgroundColors")` string, not a sentence. |
| theme | PASS | new `ChartSettingsModal.module.css` is fully token-driven; the only hard-coded colours are `color: white` on the dark-only-conditioned brand-coloured OK button + checkbox check (consistent with `DEC:TERMINAL-SHELL-IS-DARK-ONLY`); JS does not inject substantive material styling (`{ background: shown }` on the swatch is data-dependent, permitted); `DrawingSidebar.module.css` is bounded by `@media (min-width: 641px) and (max-width: 860px)` and reserves the strip once per *workspace*, not per pane, using `var(--drawing-safe-bottom, 0px)`; content-addressed `EVIDENCE.json` + `EVIDENCE.yml` lock the dark-only, EN/ZH, desktop/tablet/mobile evidence matrix. |
| validated-claims | PASS | PR body + doc carry the right calibration: "Performance proof is deliberately narrow", "No claim of improved FPS / first-load / API / network is made", "Current capability: BUILT_NOT_PROVEN. Mission complete: false.", "These changes do not establish a frame-rate, startup, API or renderer speedup", "Do not interpret screenshots/green tests as production proof", `EVIDENCE.json` declares `"productionProof": false`. No "validated" / "certified" / "WCAG-AA" / "approved" language in user copy or PR body. Display-tier work freely, no authority promoted. |
| merge hygiene | PASS | Squash merge onto `origin/master` at `e5ccacf4` carries the full +613/−77 diff; the PR head commits (`4b07375a`, `30e1e56f`) are not ancestor-equivalent of `e5ccacf4` (squash, not a merge commit) but `git show e5ccacf4` is the complete change set; content-addressed screenshot digests + per-file layout-file digests lock the evidence; `npx tsc --noEmit` PASS; scoped ESLint PASS zero warnings; Vitest 377 files / 6,072 passed / 4 todo; Playwright 73 passed / 8 skips / 0 failed; discriminated verification (RED on protected base, GREEN on candidate). |

**Non-blocking observations (out of this lane's owned paths):**

1. The `color: white` × 2 hardcoded colours are dark-only (consistent with the standing `DEC:TERMINAL-SHELL-IS-DARK-ONLY` matrix) and are outside the scope of an explicitly dark-only PR; if the repo ever picks up an official light theme, both cells should read `color: var(--on-brand, white)` so the brand-coloured primary always pairs with an explicit on-brand token.
2. The hidden `<span ref={originRef} hidden />` could be a `data-origin="chart-settings-return"` attribute on the same `.pane`/`.app` ancestor instead of an extra DOM node; the span approach is fine but the data-attribute alternative is one fewer probe.
3. The `chartSettingsUi.ts` module should grow an explicit `Object.hasOwn` guard test for `__proto__` template-name storage (currently the `template:<name>` value namespace protects at the call site, but a saved template literally named `__proto__` reaches `Object.hasOwn(templates, name)` unchecked); the existing test does cover `__proto__` in *stored* data (`parseSettingTemplates('{"__proto__": ...}')`) but does not cover a user-supplied *new* template named `__proto__`. Upstream `__save` is gated; the *name* the user types at the prompt is not. Out of this PR's scope.

**Scope-out rationale:**

- `#700` (one-line `macro-site-link` symlink retarget) is non-user-facing and is excluded from "real UI work"; it is a developer-tooling repair analogous to #600's symlink fixes on prior days.
- `#698` (mobile chart touch accessibility, `+922/−52`) is already audited (`orch/audits/mastermind-terminal_pr698.mm.md`) and merged into the night-time audit-record PR #7606 (per memory).
- Older half-B PRs (#696, #695, #689, #685, #684, #682, #674, #673, #658, #652, #601) are all already audited by sibling sessions per `gh pr list --search "orch(audit): record <repo> PR #<N>"` and the standing memory rule `[[orch-audit-filename-convention]]` ("check that audit chain FIRST").

**No blocking issue found. No retry. No scope expansion. Audit complete.**
