# Native Paper inputs: state, mobile and dock specimens

**Prepared inputs, not applied Paper designs.** Root owns the actual Paper mutations, returned IDs, screenshots, readbacks and review. These JSON entries contain no invented Paper node ID. `parent` refers to the local key of a previously created root frame; `board` means the created artboard. The native write should use the one root node returned for each step.

`mobile-state-boards.json` contains six boards:

| Key | Existing page | Size | Purpose |
| --- | --- | --- | --- |
| `states-matrix` | p-4-0 Components | 1440 × 2800 initial | Sixteen comparison rows, each with matching dark/light specimens; two combined read/save cases; independent direction/side/exposure/selection/focus semantics |
| `macro-dark-en-390` | p-5-0 Patterns | 390 × 1510 initial | English dark comparison with ten sectors, 44px evidence actions and gap-preserving history |
| `macro-light-zh-390` | p-5-0 Patterns | 390 × 1510 initial | Simplified Chinese light counterpart using the verified available Noto Sans SC family |
| `company-eps-overlay-320` | p-5-0 Patterns | 320 × 1740 initial | Missing FY2026 EPS while retaining four earlier values, full field identity and source clocks |
| `company-dividend-overlay-320` | p-5-0 Patterns | 320 × 1740 initial | Actual zero in five fiscal periods, absolute zero change and undefined percentage growth from a zero baseline |
| `macro-docked-1280` | p-5-0 Patterns | 1280 × 1300 initial | Full ten-sector comparison and 320px complementary dock at the proposed minimum-width boundary |

All heights are initial construction bounds. Inspect actual Paper layout and set the final artboard to `height: fit-content` when required. Do not mistake an initial bound for measured fit or responsive behavior. Read the `artboardStyles` field; each board is a flex column using the appropriate candidate background. No new tokens are installed. Dark designs reuse existing `--noir-*` tokens; other semantic/light values come from the reviewed local specimen palette.

## Design decisions

The phone table keeps its complete native row width of 650px inside a 358px named clip region. The initial 358px shows sector identity, a 44px evidence action, the percentage value and percentage-point change. Coverage and definition columns remain in each native row. This is a design representation of local horizontal scrolling, not a claim that the Paper canvas is an interactive table. Expected table top is y329; first row top y365 and text baseline approximately y398, matching the reviewed hierarchy. The hint appears before the table. Ten rows precede the history chart.

The line chart represents an explicitly categorical eight-session fixture with seven data points. It contains two separate line segments and no interpolation through 23 October. Labels are native HTML text around an editable SVG mark layer. The selected sector's own coverage is separate from the universe-history coverage; the dock states that their denominators cannot be combined.

The Company overlays are separate instances because EPS and dividends are distinct fields and source identities. They preserve five annual columns as vertical rows rather than mixing unrelated fields into one evidence receipt. Bilingual field names exercise actual CJK text, while source identities and fiscal/publication/retrieval clocks remain exact. No nonexistent source URL or recovery endpoint is invented.

The 1280px specimen calculates `1280 − 224 − 48 = 1008` usable width, then `1008 − 320 − 24 = 664` for the primary comparison. The 664px area exceeds the proposed 640px minimum. This is a **provisional F01 shell**; it does not establish a shell release. Below the minimum, use an overlay instead of automatically changing F01's navigation state.

The state matrix supports comparison across rows and themes without a grid of boxed cards. Each native row has a 184px state/condition column, a 600px dark specimen cell and a 600px light specimen cell; quiet neutral separators divide rows. Both theme cells retain the same actual copy and action. All sixteen outcomes remain present, including the confirmation condition for Saved and the proof-before-send condition for expired sessions.

The two combined specimens keep meaningful retained data. Expiry after a pending save produces an unknown outcome and the existing-request reconciliation path. Neither case changes stale or partial read caveats. Source clocks remain dated. Selection uses neutral fill, while focused controls have a separate accessible outline. Focus outlines are not decorative accent borders.

## Construction and visual inspection

Each JSON step is one native visual group and has a stable local key. Each state comparison row is one step; its native label, copy and actions stay aligned in fixed columns. Repeated data/state rows have `checkpoint_after` markers after meaningful groups, including the third row. Use them to inspect vertical lanes and clipping before continuing. The two combined specimens remain incremental: shell, heading/receipt, retained-value row, caveat/save feedback, action and note. Preserve those semantics; do not flatten the whole board into an image.

The refined package has **171 steps**: 40 state-matrix, 23 per phone, 21 per Company overlay and 43 dock-pattern steps. Container/header pairs and coherent chart/footer action groups are combined; each repeated data row and each independent source fact remains its own meaningful group. No table or multisection component is submitted as one whole write. The refinement preserves phone/dock density, control sizes, table data and geometry.

Prioritize these actual Paper checks:

1. Inter and Noto Sans SC render correctly; Chinese is legible without tofu and wraps naturally.
2. The 390px first table view retains the complete Source control and both numeric columns; focus outlines are not cut by the clip region.
3. Unknown Energy values and actual-zero Health care change remain visibly different.
4. The two 320px long source keys wrap within 280px; the Close target and return action remain 44px.
5. The dock keeps 664px of primary content, without shifting the primary into the inspector or trapping focus by contract.
6. State-column text and control edges do not overflow. Final heights follow measured native content.

Browser keyboard, touch, zoom, screen reader and service behavior remain separate qualification gates. These prepared inputs do not claim any such tests passed.

## Reproduction

Run `python3 build_mobile_inputs.py` from this directory or by its absolute path. It reads the current F02 specimen and typed Company fixture, then deterministically emits the JSON. This script never connects to Paper or modifies product code. `validate_inputs.py` checks source equality, parent ordering, single-root markup, allowed style structure, row counts, chart gaps and arithmetic; it does not render or visually approve the result.
