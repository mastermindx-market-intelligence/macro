# Responsive, theme, locale and accessibility requirements

Final values await qualified F01/F02. The following consumes **F01-F02-SHELL/1.0.0-candidate.4** geometry as a testable proposal, not a released foundation. Do not redraw global navigation or create new token aliases.

## Measured content rule

Use actual useful content width C after shell rail, both gutters and additional reserved local chrome. A320px inspector dock plus24px gap is eligible only if C−344≥640 **and** the active domain's qualified minimum is met. A larger required primary width wins. No automatic compact-rail switch to force eligibility.

| Viewport CSS px | Default rail | Each gutter | C with no extra local chrome | Candidate inspector |
| ---: | ---: | ---: | ---: | --- |
|320|0|16|288|Full-width overlay|
|390|0|16|358|Full-width overlay|
|600|0|16|568|Full-width overlay|
|600.5|0|20|560.5|Constrained overlay; evaluate content|
|768|0|20|728|440px modal|
|860|0|20|820|Modal|
|860.5|196|20|624.5|Modal|
|1024|196|20|788|440px modal; docking would leave444 and fail|
|1199.5|196|20|963.5|Modal|
|1200|224|24|928|Modal|
|1255|224|24|983|Modal; primary639 fails|
|1256|224|24|984|320px dock, primary640 if domain fits|
|1280|224|24|1008|Dock eligible; primary664|
|1440|224|24|1168|Dock eligible; primary824|
|1600|224|24|1328|Dock eligible; primary984|

Header64 above860,56 at/below860; safe areas additional. Explicit user-selected compact rail72 first permits dock at1096 in its20px-gutter class, without additional local chrome. Fractional widths are intentional tests. Screen dimensions or device names cannot substitute for measuring the rendered container.

The complete11-field Tape can exceed a640px primary width; use a qualified compact column preset plus accessible full-row inspector/local horizontal scroll, or request a larger domain minimum. Do not squeeze text to satisfy arithmetic. No domain-specific final minimum is falsely claimed qualified here.

## Phone320/390

- One current view title, compact source session/state, one primary filter/action row, then useful results. At390×844 target a visible first result without dismissing an overlay; validate against actual text, safe areas and longest locale. This is an acceptance task, not a fixed pixel promise.
- Keep category/local-view access through existing Tabs with clear overflow cues or an owner-approved view menu. Every named view, including Statistics and Prophet, is keyboard/touch reachable. Do not depend only on horizontal swipe.
- Compact result order: exact root/contract → primary metric → predicate/grain → clock/qualification → Inspect. Expiry/right/strike remain visible; details preserve all other fields.
- Filters open a named full-width sheet with44px important controls, Apply/Reset and close. Keep applied filters separate from editable draft. No nested sheets.
- Investigation is the same single contextual inspector in a full-width overlay presentation, with persistent close/back, selected identity and source session. Background inert/focus contained; content scrolls vertically with action reachable above device safe area.
- Local horizontal overflow is allowed for genuinely two-dimensional charts/comparisons; provide all-field details or accessible table. Body overflow fails.

## Tablet and narrow desktop

At768 and1024 use440px modal constrained to effective viewport. Do not consume comparison width with a dock. Filters can wrap or use the same disclosed sheet; they must not occupy most of the results region. Keep selected identity behind/above modal so return orientation is clear. Landscape phone and short viewport test scrolling action reachability and software-keyboard obstruction.

## Wide and density

At1280/1440/1600 measure actual C; dock only when permitted. Use neutral selected-row emphasis and clear inspector relationship. Maximum information compression comes from column alignment, concise labels and consistent units, not tiny text. Exact contract/date/root are not ellipsized without a reachable full label. Dense mode, if present under existing preference ownership, must not shrink touch controls or keyboard focus indicators below requirements.

## Themes and language

F02 owns semantic roles and actual scope-specific aliases. Its observed dark palette and proposed light palette are not globally interchangeable. Preserve existing preference ownership and focused-Terminal exceptions. No new storage key for theme/language.

Require light and dark examples of loaded Tape, selected evidence, stale/partial data and access/error. Check text contrast4.5:1 for normal text,3:1 for large text and applicable non-text controls, using the final rendered colors. No contrast pass is claimed for these uncomposed specifications.

EN/ZH labels must wrap naturally. Use 权利金 for option premium, 未平仓量 for OI, 估算成交方向 for estimated side. Keep exact source root, record ID, ISO date and currency unchanged. Distinguish source exchange timezone from locale formatting. Test long Chinese preset names and English source strings at200%text/400%zoom. Never map language to bullish/bearish or invert sign colors because of translation.

## Keyboard, assistive technology and motion

Use actual buttons/links for row actions. Table headers have scope/aria-sort; accessible name includes exact identity and action. Selection state is announced without reading every feed update. Filter errors are associated with controls. Charts expose their selected data and an equivalent table/summary using actual values, gaps and units.

Modal: named dialog, visible close, initial focus on heading/close as appropriate, inert background, contained Tab, Escape and exact conditional focus return. Dock: complementary region, no trap or background inertness. When presentation changes there is still one selection/inspector, no hidden focused duplicate. Existing global layer priorities remain F01/D14/host owned.

House target44px for important mobile controls; WCAG2.2AA minimum is24×24CSSpx or applicable spacing/exceptions. Preserve focus at every zoom; status/color alone never signals access or inferred side. Reduced motion removes transitions and count/rank animation. No flashing, auto-dismissed critical errors or forced tutorial completion.

## Required evidence grid

| Evidence family | Width/content | Theme/locale/state | Status now |
| --- | --- | --- | --- |
| Baseline native Tape |1585×1180 and390×844|Light/EN, stale loaded|Actual before captures |
| Baseline public Paper |Brief1440, Flow captured1269wide|Light/EN andDark/EN, mixed dated sources|Actual before captures; not candidate acceptance |
| Candidate primary flow |320/390,768,1024,1280/1440/1600 measuredC|EN/ZH +light/dark representative|NOT_COMPOSED |
| Candidate exceptional flow |Narrow+wide, overlay↔dock|S03/S06/S07/S10/S11/S14/S16/S18/S29|NOT_COMPOSED |
| Candidate keyboard/touch/zoom |320effective,400%zoom,short landscape|Focus/long labels/reduced motion|NOT_RUN |
| Real implemented journey |Exact accepted build and auth/source fixtures|Normal,negative,race,return/save recovery|NOT_COMMISSIONED |

Reference standards: [WCAG target size](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html), [WCAG reflow](https://www.w3.org/WAI/WCAG22/Understanding/reflow.html), [Web Vitals](https://web.dev/articles/vitals). Applicable final color/contrast and focus behavior require actual rendered measurement.
