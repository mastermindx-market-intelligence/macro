# Brain scenario illustrations — 2026-11-04

Workstream: WS:MASTERMIND-AI-ILLUSTRATIONS.
Operation: brain-scenario-illustrations-20261104-c4; original program root mastermind-ai-illustrations-20261015-c1.
Procedure: Mastermind@700eef54bca4a2dc4e30d94a6b30dcfa733ad57c.
Implementation base: macro@affa0fd2e68723efc9e2cbc0e7c791ab70f5a53d.

## Customer outcome and completion

Chairman supplied an illustrative spot-by-volatility directional heatmap beside a hedge equation.
Brain must choose and emit reusable native illustrations through its existing render_inline_visual tool,
render them within ordinary answers on Macro and Terminal, and restore them through the existing
authorized conversation history. The screenshot is a design reference, never market evidence.
DONE_WHEN: compiler and model guidance, real shared renderer and history/stream integration,
responsive bilingual dark/light proof, normal required source/release gates and actual served
model-to-illustration proof. A fixture, PR or passing CI is not production acceptance.

## Incumbent boundaries

Extend the existing eleven-template v1 compiler, native DOM renderer, KaTeX presentation,
same-turn observation binding, final answer guards and private message metadata.
PR10069 is canonically merged as 7c71612a4c25f84c10d25f56a179102c9eab0c21.
PR9447 and the separate candle/ChartBus work in PR10208 remain untouched.
No new service, model provider, auth/data grant, chart bus, history store or source calculator.
No dealer inventory, hedge-notional, probability, uncertainty interval or market-impact model is inferred.
The parent owns its isolated source carrier; no other workspace is reset or adopted.

## Contract extension

Add two distinct names to the existing closed template enum:
- heatmap: numeric observations or an explicitly requested numeric teaching example.
- scenario_matrix: qualitative teaching assumptions only, with no claim of measured direction.

Preserve every old v1 wire byte/shape. Only the two new templates carry an additional required
matrix object. Existing retained v1 snapshots remain valid. Unknown fields fail closed.

Both matrices use columns[0] as a display row header, remaining columns as X categories,
and rows as [Y label, cell, ...]. Bound dimensions to 1..12 rows and 2..6 columns.
Row labels must be unique nonempty text. Column headers are unique. Each label is <=80 characters.
Matrix fields:
- x_label and y_label: nonempty plain text, <=80 characters.
- value_label: nonempty plain text, <=80 characters, identifying what cells represent.
- assumptions: 0..6 nonempty plain-text strings, each <=240 characters; at least one for
  illustrative matrices; source matrices may use an empty array.

heatmap additionally requires matrix.scale = sequential or diverging.
Cell values after the Y label are finite bounded numbers or null, never numeric strings/booleans.
At least one numeric observation is required. Diverging color range is symmetric about actual zero.
Sequential range uses actual min/max; a constant series gets a stable single intensity.
Values are never normalized or altered in the data table/CSV. Null is missing, never zero.

scenario_matrix additionally requires matrix.legend with exactly increase, decrease, neutral,
uncertain: nonempty plain text <=64 characters each. Cells after the Y label accept only those four
closed string tokens or null. No numeric surrogate, magnitude, confidence or probability.
Neutral means the assumption says no change; uncertain means direction unresolved; null means
not supplied. These states have different glyphs and accessible names. Labels such as Hedge buying
and Hedge selling explain the measure, not a trade instruction. This template requires
basis=illustrative and cannot manufacture a source-backed forecast.

All added labels, legend and assumptions pass the existing text and final-copy screens.
All source numeric cells retain exact prior-tool equality, call identity and failed-ancestor refusal.
Display labels/units are model-authored and never certified by value equality. No new source fetch.
Retained replay validates the identical closed matrix shape before rendering.

## Model selection and admission

The existing tool description explains when to choose every template family, including these two.
Use heatmap for numeric comparisons across two axes; scenario_matrix for explicitly requested
hypothetical directional mechanisms; scenarios for a short narrative case list. Use existing bar,
line, area, scatter, donut, table, metrics, status, timeline and flow where they communicate better.
Lead with the answer, normally one useful visual, no raw JSON or model markup in prose.
Keep equations in the existing Markdown/math owner.
Qualitative matrices require explicit teaching/hypothetical intent even though their cells are text.
Reuse the existing current/latest/historical-request refusal: fictional matrices cannot stand in for
missing actual data. General tool/source errors preserve a readable answer, no fabricated replacement.
Do not globally loosen financial signals, advice, source, quota or topic-scope controls.

## Interaction and visual design

Use the supplied screenshot as the matrix composition reference: short title, explanatory line,
clear axes, roomy cells, compact visible legend and assumption disclosure.
Dark: quiet integrated reading surface, restrained direction tints, high-contrast ink and neutral
spacing. Light: white research surface, pale direction tints, explicit neutral 1px cell separation
and track border. All color derives from existing host/theme tokens; arrows and text carry meaning
independently. Direction colors follow the existing EN/ZH up/down mapping. No colored edge stripe,
new palette root or runtime stylesheet injection.
Use native table semantics with row/column headers and an accessible caption.
Every cell has an accessible row + column + value/state description. No hover-only information.
A keyboard/touch-operable selected-cell detail may add clarity, but must not create dozens of
tiny mandatory tab targets. Default state is understandable without interaction.
At 390px (also robustness at 320px), preserve legible cells inside a contained horizontal scroller;
keep axis labels, full values and the legend reachable, never page overflow or silently hidden rows.
Desktop target is a calm 720px reading column. Reduced motion remains static.
Local chrome has EN/ZH twins; dynamic model labels retain their original response language.
The current data/source disclosure, exact-value table, safe CSV, deduplication and clear/retract
behavior continue to apply. Illustrative status and assumptions are visible before the matrix
can be mistaken for current market output.

## Ordered tasks in the incumbent plan

HM1: persist this contract and reconcile actual source custody.
HM2: extend compiler/schema/retained validator plus specific adversarial tests.
HM3: extend native matrix renderer and governed CSS; preserve asset delivery/hash ownership.
HM4: wire teaching-intent guard and practical model guidance; test real preparation/stream/history.
HM5: real-browser integrated widget captures across dark/light x EN/ZH x 1440/390 plus 320 robustness.
HM6: independently adjudicate security/semantic risks, qualify exact candidate CI and normal release;
verify actual served assets and ordinary model selection/history when access permits.

## Discriminating proof

Contract parity across Python and browser; old snapshots unchanged; reject ragged/over-limit,
duplicate labels, unknown state/fields, unsafe text, NaN/Infinity/bools, empty numeric matrix,
missing assumptions and any source basis on scenario_matrix.
Prove zero, negative, constant, missing and uncertain cases; no color-only meaning.
Prove exact source mismatch/failed ancestor/repeated-call rejection still operates.
Prove current/historical requests cannot admit text-only fictional matrix via the numeric-only gate.
Prove duplicate SSE/history mounts create one figure, clear retracts it and malformed saved input
cannot execute HTML/URLs/styles. Keep authenticated ownership behavior unchanged.
Prove cell inspection and scroll operate by keyboard/touch, EN/ZH chrome, no console errors or
page overflow, both theme compositions, exact CSV values and formula escaping.
All captures and API seams label synthetic inputs explicitly; real product proof stays separate.

## Initial recovery evidence

Studio workspace acquisition first returned WORKSPACE_ACQUISITION_UNQUALIFIED / EFFECT_UNKNOWN.
Same-operation publication status reconciled branch sol/web-brain-scenario-illustrations-20261104-c4
at the exact base, clean with no remote ref. Original-host git worktree readback confirmed the
registered locked path /Volumes/Mastermind 2/agent-workspaces/macro/web/brain-scenario-illustrations-20261104-c4.
No retry or second workspace was created. Executive state read returned backend_unavailable;
no runtime admission is asserted. Source work is independently authorized by the current assignment.
