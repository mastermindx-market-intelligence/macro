# Plain-language / theme / validated-claims audit — mastermind-terminal PR #695

Auditor: qwen_auditor2-style pass (one-shot, half-B scope). Date: 2026-09-21.

## PR metadata

| field | value |
|---|---|
| repo | `mastermindx-market-intelligence/mastermind-terminal` |
| number | #695 |
| title | `fix(chart): repair mobile analysis hub focus and tools` |
| merge head | `c574ce937827a84fd02586b4b41b25b5a23e4d37` (squash of `sol/web-terminal-mobile-upgrade-20260920-sol-001-b-chart-hub` onto `master`); semantic head `6978dba570eaeaa8672ce45fb8f00dfb29d3efed`; integrated head `f48d50046ed6072c50f5c9e7d547b41000a87306` (byte-identical on the five owned blobs against the merged head). |
| merged | 2026-09-21T08:46:43Z via squash-merge to `master`. Selected as the most-recent merged half-B non-audit-record PR in the 24-h window that has not already been audited (`ls orch/audits/mastermind-terminal_PR-*.mm.md` confirms no audit for #695; #700 is a 1-line symlink fix that fails the "half-B with theme/plain-language impact" filter; #698 / #696 / #693 / #689 are pre-existing audits). |
| files | **5 paths, +413 / −39.** `terminal/components/TerminalShell.tsx` (+1/−0), `terminal/components/mobile/AnalysisHubSheet.module.css` (+18/−0 NEW), `terminal/components/mobile/AnalysisHubSheet.tsx` (+147/−36), `terminal/e2e/mobile-chart-chrome.spec.ts` (+6/−3), `terminal/e2e/mobile-chart-hub-upgrade.spec.ts` (+241/−0 NEW). |
| half-B label | **half-B mobile-chart focus/disclosure upgrade (Session B of the Terminal mobile programme).** Closes MM-005 (modal focus cycle, Shift+Tab containment, Escape/scrim/drag dismissal, return-to-trigger) and MM-006 (Object tree + Templates removed from actionable grid; chart type wired to the canonical picker and existing `mm.ct` state). PR body §"Summary" enumerates owned paths and explicitly excludes shared `i18n.tsx`, `globals.css`, `MobileNav`, `RollerStrip`, `SeasonalityCard`, `ChartPanel`, and the shared `MobileSheet` primitive. No scoring, signing, filtering, data source, or transport change. |
| scope | (a) Real focus containment for the mobile Analysis hub: opener captured on every presentation, initial focus lands on Close, Tab and Shift+Tab cycle within the sheet, Escape + scrim + drag dismissal return focus to the More trigger; (b) cross-overlay handoff (`indicators` / `compare` / `chartType`) places focus on the receiving overlay without racing back to the dismissed hub; (c) `chartType` action routes through `setCtOpen(true)` → the existing canonical Chart-type picker, persisting into `mm.ct` localStorage; (d) Object tree and Templates demoted from actionable tiles into a single honest EN/ZH availability note rendered outside the primary tool grid; (e) `TerminalShell.tsx` gains one surgical `chartType` action branch. |
| durable owner | None new. The hub sheet remains owned by the mobile-programme lane (`#483` / `#622` own release; this PR does not deploy independently). The new `mm.ct` persistence is the existing Terminal contract — no new storage plane introduced. |
| checks | Body reports: focused Session B regression — `12/12` Playwright PASS; cross-viewport hub compatibility slice — `3/3` PASS with 3 expected viewport skips; full `npm test` — `376/376` files, `6,027` tests passed, 4 todo, 0 failed; `npx tsc --noEmit` exit 0; owned-path ESLint exit 0; `git diff --check origin/master...HEAD` exit 0; touch/dark/EN/ZH visual capture PASS at 320×568, 360×800, 390×844, 430×800; canonical chart-type picker captured at 390×844. Workflow-dispatch run `35573380321` completed success; required-status run `35573384058` completed success and satisfied branch protection before merge. Repository-wide `npm run lint` retains pre-existing debt (**1,445 errors / 240 warnings**); owned files have no diagnostics. |
| evidence matrix | `mockups/evidence/` PNGs are not required for this PR (no redesigned visual surface; the change is interaction design — focus containment + one new note panel that uses tokens). Body points to `/Volumes/Mastermind/agent-evidence/terminal-mobile-upgrade-20260920-sol-001-b-chart-hub/` for the actual visual capture. The TP-0 dark/light × EN/ZH × 1440/390 matrix only applies to redesigned surfaces; this PR ships none — it modifies an existing bottom-sheet surface (`AnalysisHubSheet.tsx`) and adds one inline note row inside it. |
| gating scripts | `terminal/scripts/check_plain_language.mjs --json` — exists on terminal, runs against the merged head. `terminal/scripts/check_validated_claims.py` — **DOES NOT EXIST** on terminal; the discipline is read against the macro precedent and the design-doctrine banned-glance vocabulary. `scripts/check_design_system.py` / `scripts/check_runtime_style_injection.py` / `scripts/check_ui_visual_evidence.py` — macro-only (TP-0 art-direction gate); terminal-side discipline is read against the same standing rules. `scripts/check_template_site_sync.py` — does not apply (no plain-copy `templates/<name>` + `site/<name>` pair was edited). |

## Diff content (scoped to this audit)

### `terminal/components/TerminalShell.tsx` (+1 / −0)

A single new `else if` branch inside the existing hub-action dispatcher (around the existing `indicators` / `compare` / `alerts` / `symbolDetails` branches):

```tsx
else if (action === "chartType") setCtOpen(true);
```

This wires `chartType` into the canonical chart-type picker (the existing `setCtOpen` setter that drives the `<ChartTypePop />` overlay used on the desktop `chart-tabs`). No new contract. The four sibling branches are unchanged.

### `terminal/components/mobile/AnalysisHubSheet.module.css` (NEW, +18 / −0)

A single `.unavailable` rule block plus its `.unavailable strong` modifier. Read of the file:

```css
.unavailable {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 4px 8px;
  margin: 10px 16px 2px;
  padding: 10px 12px;
  border: 1px solid var(--pop-edge);
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.025);  // <-- one hardcoded alpha overlay (see §Theme #2)
  color: var(--text-dim);
  font: 500 11px/1.35 var(--font-ui);
}

.unavailable strong {
  color: var(--text-2);
  font-weight: 700;
}
```

Tokens used: `--pop-edge`, `--text-dim`, `--text-2`, `--font-ui`. Theme-discussion #2 below.

### `terminal/components/mobile/AnalysisHubSheet.tsx` (+147 / −36)

The substantive change. Five logical moves:

1. **Capability map replaces tile arrays.** The old `TOOL_TILES` (six entries, two of them ghost tiles for Object tree / Templates with `action: undefined`) and `INFO_TILES` (one entry for Symbol details) are replaced by a single `CAPABILITIES` object with three fields: `tools: ActionTile[]` (Indicators, Compare, Alerts, Chart type), `unavailable: UnavailableCapability[]` (Object tree, Templates), `info: ActionTile[]` (Symbol details). The new `ActionTile` type makes `action` required (every action is backed by an existing Terminal capability); `UnavailableCapability` has only `id` and `labelKey`, no `path`, no `action` — surfaces the audit did not establish stay truthful and noninteractive.

2. **Focus containment loop.** A new `useEffect` keyed on `[mounted, open]` (replacing the old body-scroll-lock + keydown + single rAF focus effect that landed focus on the sheet container instead of the close button):
   - Captures `previousFocusRef.current = document.activeElement instanceof HTMLElement ? document.activeElement : null` at presentation.
   - Sets `restoreFocusRef.current = true` so the cleanup returns focus to the captured opener by default.
   - On the first rAF, focuses `focusableElements(sheet)[0] ?? sheet` (the Close button — the first focusable element in the sheet DOM order).
   - On `Tab` / `Shift+Tab`, computes `focusable = focusableElements(sheet)`, then either wraps from first to last, last to first, or pulls focus back into the sheet if it has escaped (the `focusEscaped` branch — the safety net for screen-reader virtual cursors).
   - On `Escape`, `event.preventDefault()` + `event.stopPropagation()` + `onCloseRef.current()` — Escape now stops propagation so it does not race with any other modal listening at the document level.
   - On cleanup, `previousFocus?.isConnected && restoreFocusRef.current` → restore focus; otherwise leave it where it is (action handoff path).

3. **`handOff(action, event)` helper.** When an action tile is clicked, the helper:
   - Reads the current `previousFocusRef.current` as the return target.
   - Sets `restoreFocusRef.current = false` (so the hub's cleanup does NOT pull focus back).
   - Sets `previousFocusRef.current = null` (no stale return target).
   - Focuses the return target synchronously, then calls `onAction(action)`. The receiving overlay captures its own focus on mount from this stable return target without a cleanup race.

4. **Ghost tiles demoted to a single availability note.** The old `<i className="mhub-ghost-tag">{t("hubSoon")}</i>` ("Not in this alpha" / `此版本暂未提供`) inside each ghost button is removed; the Object tree and Templates surfaces are removed from the actionable grid entirely; in their place, a single new row:

   ```tsx
   <div className={styles.unavailable} data-testid="hub-unavailable-tools" role="note">
     <strong>{t("wsPanelUnavailable")}</strong>
     <span>{CAPABILITIES.unavailable.map((capability) => t(capability.labelKey)).join(" · ")}</span>
   </div>
   ```

   renders between the Tools grid and the Info grid. The rendered text is `<strong>This panel isn't available in this version</strong> Object tree · Templates` (EN) / `<strong>此面板在当前版本中不可用</strong> 对象树 · 模板` (ZH). All visible copy routes through `t()`; no raw literal.

5. **Minor accessibility / event-hygiene fixes.** Every action tile now has `type="button"` (the React default would be `"submit"` inside a form); the SVG inside the close button gains `aria-hidden="true"` (the close button's `aria-label={t("sheetClose")}` is the accessible name); the sheet's outer `<div>` gains `onClick={(event) => event.stopPropagation()}` so a stray click inside the sheet body does not bubble to any future scrim handler (the scrim is a sibling node in the same portal, so this is a defensive belt — the existing portal layout already prevents it, but it costs one line and removes the surprise).

### `terminal/e2e/mobile-chart-chrome.spec.ts` (+6 / −3)

Existing "phone: ••• opens the analysis hub at 60% and drags to full" test is updated to match the new hub layout. The old assertions were:

```ts
await expect(page.getByTestId("hub-tile-objectTree")).toHaveAttribute("aria-disabled", "true");
await expect(page.getByTestId("hub-tile-objectTree")).toContainText("Not in this alpha");
```

Replaced by:

```ts
await expect(page.getByTestId("hub-tile-chartType")).toBeEnabled();
await expect(page.getByTestId("hub-tile-objectTree")).toHaveCount(0);
await expect(page.getByTestId("hub-unavailable-tools")).toContainText("Object tree");
await expect(page.getByTestId("analysis-hub")).not.toContainText("Not in this alpha");
```

Three observations:
- The first old assertion encoded the buggy contract: a tile that is keyboard-focusable but `aria-disabled="true"` is a dead keyboard stop. The new contract moves the disabled tile out of the tab order entirely (`hub-tile-objectTree` has `count: 0`).
- The second old assertion pinned the retired `hubSoon` copy ("Not in this alpha"); the new assertion explicitly forbids it (`not.toContainText("Not in this alpha")`).
- The third assertion pins the truthful replacement: the unproven capabilities are listed inside the new `hub-unavailable-tools` row. This is the standing plain-language principle in test form: the test now says what the surface says.

### `terminal/e2e/mobile-chart-hub-upgrade.spec.ts` (NEW, +241 / −0)

The regression coverage for Session B. Five tests, each scoped to a specific behaviour claim:

- **`MM-005: the hub owns the complete keyboard cycle and returns focus on dismissal`** — opens the hub, asserts Close is initially focused, then Tab through the five supported controls (Close, Indicators, Compare, Alerts, Chart type, Symbol details — six elements total), then Tab wraps back to Close, Shift+Tab wraps to Symbol details, Escape dismisses, More trigger is focused again.
- **`MM-005: scrim click and drag dismissal return focus to the trigger`** — open hub, click scrim at `(4, 4)`, expect hub gone and trigger focused; open hub again, drag the grip down 170px, expect hub gone and trigger focused.
- **`MM-005: focus hands into supported overlays without racing back to the dismissed hub`** — open hub → Indicators → expect `#indicator-library-dialog` visible and activeElement inside it, trigger NOT focused; Escape → trigger focused. Reopen → Compare → expect `.smodal-cmp` visible, trigger NOT focused.
- **`MM-006: only supported tools are actionable and chart type uses canonical persistent state`** — asserts `.mhub-grid .mhub-tile` count is 5 (no ghost tiles in the grid); Object tree and Templates are NOT in the grid (`toHaveCount(0)`); `hub-unavailable-tools` contains "This panel isn't available in this version", "Object tree", "Templates"; "Not in this alpha" is absent. Then opens chart-type picker, taps "Line", expects `localStorage.mm.ct` to be `"line"`, reopens the picker, expects Line to be marked `.on`; the same is asserted at 820×1180 (tablet) and 1440×900 (desktop) by inspecting `.chart-tabs .pophost .chart-type-pop`; then back at 390×844, reopens the picker and asserts Line is still marked `.on` (persistence across viewport changes).
- **`MM-006: Alerts and Symbol details act on the current symbol`** — open `/terminal?symbol=AAPL`, asserts `.detail-board` contains "AAPL"; tap Symbol details, asserts hub gone and detail board scrolled into the viewport (`top < 96`); reopen, tap Alerts, expects URL transition to `/alerts?sym=AAPL` and `searchParams.get('sym') === 'AAPL'`.
- **`MM-006: EN and ZH expose the same truthful capability decisions`** — open `/terminal?symbol=NVDA` with `mm.lang=zh`, asserts `hub-unavailable-tools` contains `此面板在当前版本中不可用`, `对象树`, `模板`; the retired `此版本暂未提供` is absent; tapping chart type opens the picker titled `图表类型`.
- **`MM-005/MM-006: hub controls stay nonoverlapping and reachable across phone widths`** — loops 320×568 / 360×800 / 390×844 / 430×800; asserts `document.scrollWidth ≤ clientWidth` (no horizontal overflow); no pair of `button.mhub-tile, button.mhub-close` rectangles overlap by more than 0.5px on either axis; every control's effective hit area (rect plus `::before` inset) is ≥ 44×44; every control's left edge ≥ 0; every control's right edge ≤ viewport.width.

Test names are plain English. Test comments are plain English. Test assertions route user-visible expectations through `page.getByTestId` / `page.getByRole` / `page.getByText` — the checker enumerates these as test code, not as inline user-visible copy.

## Plain-language findings

The standing terminal-side plain-language discipline (`terminal/scripts/check_plain_language.mjs`, packet B-PL-5) gates raw state enums, internal study/organ slugs, and untranslated statistic tokens from user-visible positions (`title`, `aria-label`, `placeholder`, `alt`, JSX text, JSX child literals). Direct user-visible copy inside `terminal/components/**` is expected to route through `t(...)` LEX keys, declared `terminal/lib/plainLabels.ts` helpers, or the `LEX[…]` array lookup.

**Headline: PASS on plain-language for all PR-introduced user-visible copy.** The PR is a net positive: it removes one user-visible string class ("Not in this alpha" / `此版本暂未提供`) and replaces it with a more truthful, more specific EN/ZH pair.

Specific findings:

1. **Every visible string added by this PR routes through `t()`.** Grep of the `+` diff (extracted via `gh pr diff 695`) returns the following visible-position string literals and helper calls:
   - `t("hubTitle")`, `t("hubTools")`, `t("hubInfo")`, `t("hubChartType")`, `t("hubObjectTree")`, `t("hubTemplates")`, `t("wsPanelUnavailable")`, `t("sheetClose")` — all LEX keys.
   - `CAPABILITIES.unavailable.map((capability) => t(capability.labelKey)).join(" · ")` — the `· ` (middle-dot with spaces) is the standard intra-phrase separator already used elsewhere on the sheet (e.g. `t("seasonalityFoot").replace("{sym}", symbol)`); ZH `·` punctuation is mirrored by `、 ` in the Chinese punctuation convention, but the LEX-disclosed separator here is intentional — ZH phrases that contain `对象树` / `模板` are short noun compounds that read cleanly separated by `· `, matching the convention in `t("seasonalityFoot")`.
   - `aria-label={t("sheetClose")}` — Close button accessible name.
   - **No raw English literal in any user-visible position in the PR-introduced code.**

2. **The retired `hubSoon` copy is fully removed.** Old string `"Not in this alpha"` / `此版本暂未提供` (`hubSoon: ["Not in this alpha", "此版本暂未提供"]`) does not appear in any visible position in the new diff. The updated `mobile-chart-chrome.spec.ts` even asserts `await expect(page.getByTestId("analysis-hub")).not.toContainText("Not in this alpha");` — the test now actively forbids the old copy. The replacement is `t("wsPanelUnavailable")` → `"This panel isn't available in this version"` / `"此面板在当前版本中不可用"` (already declared in `terminal/lib/i18n.tsx`), with the unavailable capabilities listed inside the same note. **The new copy is more truthful** ("isn't available in this version" names the constraint explicitly) and is bilingual-paired.

3. **No banned vocabulary introduced.** Grep of the `+` diff for the terminal-side banned list (`trust_tier / event-edge / msc_regime / mscRegime / flowScore / gexdesk / prophet / oracle / conductor / synapse / lobe / tripwire / falsifier / quiet_accumulation / bottom_watch / trustTierLabel / regimeLabel / planTierLabel / classicCategoryLabel / macroChipLabel / mappedOrNeutral / notClassified / iv_rank / ivr / gex / dex / vanna / charm / dte / oi / pcr / rv30 / hv20 / atr14 / zscore / z_score / pctl / yoy / qoq / ttm / cagr`) returns zero matches. The `wsPanelUnavailable` text is plain English ("This panel isn't available in this version"), and the listed capability names (`Object tree`, `Templates`) are user-facing product nouns — neither is on the banned list.

4. **`title=` attributes: zero added.** Grep for `title="…"` in the `+` diff returns zero matches. The existing `aria-label={t("sheetClose")}` is the accessible name for the close button; no `title=` tooltip is added (the standing design-doctrine ban on translated `title=` attributes is honored).

5. **ZH parity holds.** Test `"MM-006: EN and ZH expose the same truthful capability decisions"` explicitly verifies ZH: `await expect(hub.getByTestId("hub-unavailable-tools")).toContainText("此面板在当前版本中不可用")`, `.toContainText("对象树")`, `.toContainText("模板")`, `await expect(hub).not.toContainText("此版本暂未提供")`, and `.getByRole("dialog", { name: "图表类型" })` — the picker dialog title is also bilingual-paired.

6. **No new helper / overlay term added.** The PR does not touch `terminal/lib/i18n.tsx` (verified by `git diff --stat c574ce93~1..c574ce93 -- terminal/lib/i18n.tsx` returning no entry) or `terminal/lib/plainLabels.ts`. The new `wsPanelUnavailable` key is pre-existing in the LEX (`grep` returns `wsPanelUnavailable: ["This panel isn't available in this version", "此面板在当前版本中不可用"]`). The `hubSoon` key remains in the LEX (unused now); retiring it from the LEX would be a separate PR — this PR's body explicitly notes that the change is to "the visible copy", not the LEX declaration.

7. **Plain-language residual issues: none.** No banned vocabulary, no raw literals, no translated `title=` attributes, no ZH/EN drift. The PR is a strict net positive against the plain-language gate.

**Plain-language verdict: PASS.**

## Theme findings

The TP-0 standing rule ("dark and light share information architecture, component semantics, spacing/type scales, state meanings, user actions, data contracts, ordering/density law and interaction behavior — they do **not** have to share material treatment. Dark = command center; light = research workspace. Token substitution alone is never proof of a light design…") and the runtime-style-injection rule ("JS may mount/recompose canonical DOM, set state classes, select variants, and apply genuinely data-dependent inline geometry; governed CSS owns the material decisions") bind this PR.

**Headline: PASS on theme. THEME-CLOSURE preserved.** The only thematic concern is one hardcoded `rgba(255, 255, 255, 0.025)` literal in the new `.unavailable` background — a 2.5% white overlay that does not have a matching token in the design system. See advisory #2 below.

Specific findings:

1. **Token discipline is clean in the PR-introduced CSS.** The new `AnalysisHubSheet.module.css` references four existing design tokens: `var(--pop-edge)` (border), `var(--text-dim)` (unavailable text colour), `var(--text-2)` (strong modifier colour), `var(--font-ui)` (typeface). No hardcoded hex, no `hsl()`/`oklch()` literals, no `font-family` redefinitions, no spacing-scale redefinitions. The PR does NOT touch `globals.css`, the shared `MobileSheet` primitive, or the `:root` token declarations. THEME-CLOSURE is preserved — switching the document-level `data-theme` attribute flips the new note row through the same shared tokens.

2. **One hardcoded `rgba()` literal: `rgba(255, 255, 255, 0.025)` on `.unavailable` background.** This is a 2.5% white overlay intended to add a subtle background tint to the unavailability note. The same pattern is used elsewhere in the codebase for similar subtle surface treatments (the `mobile/AnalysisHubSheet.module.css` is new in this PR — verified — but the rgba pattern is consistent with how other "translucent panel" surfaces in the mobile repo are written). **Trade-off discussion:** the literal is theme-conditional by construction (white at 2.5% over a dark base yields a faint brightening; over a light base it is barely perceptible). Two alternative routings exist:
   - **Token-add path:** add a `--surface-unavailable` (or `--panel-2-alpha`) token to `:root` so light and dark can both express their own intent (light = `rgba(0, 0, 0, 0.025)` for a faint darkening, dark = `rgba(255, 255, 255, 0.025)` for a faint brightening). This is the more theme-correct path and aligns with TP-0's "dark and light do not have to share material treatment".
   - **Literal-as-is path:** the rgba is in a single-rule stylesheet that targets a single edge case (an unavailability note inside one bottom sheet); the visual impact is small enough that the literal is acceptable for now. This matches what PR #698 did with `#2a2a2a` for the active-state surface background.

   The PR author chose the literal-as-is path. The auditor's call: **PASS but advisory.** This is not a violation of TP-0 — TP-0 forbids "token substitution alone is never proof of a light design" in the context of a wholesale light redesign; this is a single rgba overlay on one note row, not a light-mode treatment. But it is also the second time in three consecutive audits that the mobile-chart lane has shipped a hardcoded colour literal in a new module stylesheet (the first was `#2a2a2a` in `RollerStrip.module.css` from #698). The pattern warrants a future-token PR, ideally before Session D or whichever lane next touches the mobile bottom-sheet primitives.

3. **No inline `style="…"` attributes introduced in the new JSX.** Grep of the `+` diff for `style=` (excluding style imports) returns zero matches. The component's existing inline-styled attributes (the `mhub-tile` ghost class, the `<i className="mhub-ghost-tag">` element) are removed; the new `hub-unavailable-tools` row uses a module class plus an inline `<strong>` for the emphasis. No layout geometry is being shifted into the JSX. The runtime-style-injection rule is honored.

4. **Focus-management changes are interaction design, not material design.** The new `useEffect` keyed on `[mounted, open]`, the `focusableElements()` helper, the `handOff()` helper, the `previousFocusRef` / `restoreFocusRef` refs, and the keyboard-cycle logic do not touch any visual material. The `aria-modal` (pre-existing) is the contract for the keyboard containment; the `role="note"` on the new unavailable row is a semantic aria role, not a visual treatment. The dark/light behavior of the hub is unchanged — focus is invisible to the theme system by construction.

5. **No evidence matrix required.** The TP-0 dark/light × EN/ZH × 1440/390 matrix applies to redesigned visual surfaces. This PR is interaction design plus one inline note row that uses existing tokens. The body explicitly notes "Chromium emulation is not claimed as full native-mobile certification" and points to `/Volumes/Mastermind/agent-evidence/terminal-mobile-upgrade-20260920-sol-001-b-chart-hub/` for visual capture. The token discipline, the absence of inline styles, and the bounded scope of the visual change all argue against requiring a fresh matrix. A reviewer who wants to inspect the dark/light parity can open the existing capture and verify the new `.unavailable` row visually (the row is small, sits below the Tools grid, and uses tokens for border / text colour / typeface).

6. **The `wsPanelUnavailable` copy is not theme-conditional.** It is the same string in both themes (and the same ZH phrase in both themes). The unavailability note is a content signal, not a material signal — the same is true of every other note-style affordance in the mobile sheets.

7. **Theme residual issues: one advisory (rgba literal), no blockers.** The PR does not regress THEME-CLOSURE (no shared token redefined, no `globals.css` touched, no Material token system extended). The advisory on the rgba literal is the kind of small, repeatable debt that benefits from a future-token PR — not from blocking this PR.

**Theme verdict: PASS with one advisory on the `rgba(255, 255, 255, 0.025)` literal.**

## Validated-claims findings

The standing validated-claims discipline (BC-2) gates any affirmative use of `validated` / `confirmed` / `已验证` / `经验证` / `经过验证` against an allowlist. The terminal repo does not have a `check_validated_claims.py` script; the discipline is read against the macro precedent and the standing design-doctrine "validated is CI-enforced" rule.

**Headline: PASS on validated-claims. No new affirmative claim. The change is honest about what is and isn't shipped.**

Specific findings:

1. **Zero affirmative `validated` / `confirmed` / `proven` / `verified` vocabulary introduced in PR-introduced user-visible copy.** Grep of the `+` diff for `validated / confirmed / proven / asserted / verified` returns zero matches on PR-introduced lines. The new copy is `t("wsPanelUnavailable")` ("This panel isn't available in this version" / `此面板在当前版本中不可用`) — this is a NEGATIVE capability disclosure, not an affirmative claim. The shape is "this isn't here yet", which is the opposite of a validation claim.

2. **Pre-existing `validated` / `confirmed` / `verified` vocabulary in the Terminal is inherited unchanged.** The Terminal carries a number of pre-existing strings that use the `verified` / `confirmed` vocabulary (e.g. cross-checked data labels in the alerts cockpit and the company-intelligence panel). This PR does not touch any of them — verified by the bounded-path list in the PR body (`TerminalShell.tsx` gains one branch; the existing strings are in unrelated components).

3. **No new engine contract invented.** The `mm.ct` localStorage key is the existing Terminal contract for chart-type persistence (the canonical picker writes to it on selection; the desktop `.chart-tabs` chart-type pop reads from it on mount). PR #695 does not introduce a new storage plane — it wires the existing `chartType` action through `setCtOpen(true)`, which is the same setter that the desktop chart-type pop uses. The test `await expect.poll(() => page.evaluate(() => JSON.parse(localStorage.getItem("mm.ct") || "null"))).toBe("line")` verifies the existing contract, not a new one.

4. **No new study or claim introduced.** The PR moves two surfaces (Object tree, Templates) from "ghost tiles with a 'coming soon' hint" to "single honest unavailability note". This is a DOWNGRADE in claim level — the old contract promised that these surfaces were on the way; the new contract says they aren't in this version. The PR is a falsifier-discipline improvement (the old "Soon" label was aspirational and unverifiable; the new label is honest about what shipped).

5. **The `mm.ct` persistence test is falsifier-discipline-positive.** The new test `"MM-006: only supported tools are actionable and chart type uses canonical persistent state"` explicitly asserts the round trip: tap "Line" → `mm.ct === "line"` → reopen picker → Line is `.on`. This is the right shape — the test proves what the user sees, not what the code intends.

6. **No allowlist extension needed.** No PR-introduced phrase names a study, a signal, or a validation claim. The only new copy is `wsPanelUnavailable`, which is a plain-English capability disclosure — it does not require allowlisting.

7. **Validated-claims residual issues: none.** The PR introduces no new affirmative validation claim. The shared terminal vocabulary is inherited, not introduced.

**Validated-claims verdict: PASS.**

## Overall verdict

| dimension | verdict |
|---|---|
| plain-language | **PASS** (net positive — retires `hubSoon` "Not in this alpha" copy) |
| theme (TP-0 art direction + THEME-CLOSURE) | **PASS** with one advisory on the `rgba(255, 255, 255, 0.025)` literal in `.unavailable` background |
| validated-claims (BC-2) | **PASS** (no new affirmative claim; honest capability disclosure) |

**PR #695 ships clean across the three standing audits, with one small theme advisory to surface for the future-token lane.**

The PR is a strict net positive against the plain-language gate: it retires the vague `hubSoon` / "Not in this alpha" / `此版本暂未提供` copy from two ghost tiles, demotes Object tree and Templates from the actionable grid into a single honest EN/ZH unavailability note, and adds regression coverage that actively forbids the old copy. The theme gate has one small advisory: the new `.unavailable` background uses `rgba(255, 255, 255, 0.025)` rather than a token, which is the second consecutive mobile-chart PR (#698 had `#2a2a2a`, this PR has the rgba) to ship a hardcoded colour literal in a new module stylesheet. Neither literal is a violation of TP-0 — both are single-rule, single-surface, low-impact overrides that the design system could route through tokens in a future refactor PR. The validated-claims gate has zero findings — the new copy is a negative capability disclosure ("isn't available in this version"), which is the opposite of an affirmative claim and aligns with the standing falsifier-discipline principle (don't promise what isn't shipped).

**Audit result: PASS — no blocking findings, one advisory on the rgba literal.**

---

**Auditor's note (one-shot, half-B scope).** This audit was a single pass against the standing plain-language + theme-art-direction + validated-claims laws, in the shape of the prior `qwen_auditor2` audits (`mastermind-terminal_PR-698.mm.md`, `mastermind-terminal_PR-696.mm.md`, `macro_PR-7607.mm.md`, `macro_PR-7603.mm.md`). The PR is a half-B interaction-design lane — the only file with substantive new content is `terminal/components/mobile/AnalysisHubSheet.tsx` (+147/−36) and the sibling `.module.css` (+18 new). The plain-language audit was lighter than the prior display-tier audits: the PR does not touch any text-rich component, and the only user-visible copy changes are (a) the removal of two ghost-tile labels, and (b) the addition of one inline unavailability note that routes through the pre-existing `wsPanelUnavailable` LEX key. The theme audit picked up one advisory on the rgba literal — the kind of small, repeatable debt that benefits from a future-token PR, not from blocking this PR. The validated-claims audit was a strict pass — the change is honest about capability gaps rather than making any affirmative claim.
