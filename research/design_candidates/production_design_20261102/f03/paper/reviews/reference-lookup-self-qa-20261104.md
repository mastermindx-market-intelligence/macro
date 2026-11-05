# F03 returned-reference lookup — scoped native self-QA

Status: **three editable native compositions implemented and visually checked; not product or input-path acceptance.** Root inspected the actual r1 and r2 screenshots, not an HTML prediction. The [final capture manifest](../continuations/reference-lookup-20261104-captures-final.json) binds the exact JPEG/JSX bytes. The [first-pass manifest](../continuations/reference-lookup-20261104-captures-r1.json) preserves the before-repair evidence.

## Exact target and useful journey

Original carrier: Mastermind Paper direct app. File `01M2WGNCX9475G79JRKJTCM08P`, page `p-1P-0`. These F03-owned boards illustrate finding a returned Read me by exact ID, distinguishing it from a candidate, and tracing the original source without losing the query/filter context.

| Board | Composition | Actual inspected result |
| --- | --- | --- |
| `72K0-0` | 1440px board / 1344px content; dark EN | Clear search-first hierarchy, 198px assignment selector, exact returned page and source provenance; no visible clipping |
| `72K1-0` | 390px board / 350px content; dark EN | Stacked search/selector, visible dropdown affordance, readable exact IDs and provenance, complete footer |
| `72K2-0` | 390px board / 320px content; light ZH | Chinese hierarchy and source distinctions retained; long identifiers wrap without clipping; official 390px status bar. This is a 320px **content column**, not a 320px-device claim |

## Findings and actual repairs

1. The assignment selector looked like another text field. Added a small original SVG dropdown chevron in all three boards; the mobile dark chevron reuses the created dark component.
2. The desktop selector consumed half the toolbar instead of matching the source artifact's 198px control. Set the selector to 198px with no flex growth/shrink.

Both findings were checked in the r2 screenshots. The [four exact repair operations](../continuations/reference-lookup-visual-repairs-20261104.json) are APPLIED. All source/pin/time/identity text remained present. Main and Terminal older directory boards were not edited by this lookup slice.

The [fit operation](../continuations/reference-lookup-fit-20261104.json) avoids hiding the long content. The [completion receipts](../continuations/reference-lookup-completion-20261104-operations.json) and [wide footer receipt](../continuations/reference-lookup-wide-footer-20261104.json) retain the distinct applied components. After the final captures and JSX extraction, only these three owned boards' working indicators were released: [exact release receipt](../continuations/reference-lookup-finish-20261104.json).

## Reconciled transport interruption

The first `f03-20261104-lookup-wide-provenance-01` response was uncertain. No duplicate write or alternate carrier was used while it was unknown. After the original transport recovered, exact JSX readback found precisely the 31 pre-attempt nodes and four direct components, with the intended provenance absent. [Original-target reconciliation](../../evidence/reference-lookup-reconciliation-20261104.json) records **RECONCILED_NO_TARGET_EFFECT_OBSERVED**, not an invented NOT_DISPATCHED receipt. The same logical operation was then deliberately completed with a fresh qualified guard on the original carrier. Its APPLIED response and exact subsequent heading/pin/time/identity readback are retained in [the completion receipt](../continuations/reference-lookup-provenance-reconciled-20261104.json).

The cumulative native ledger now records 142 unique APPLIED operations and zero unresolved F03 effects. That number includes earlier implementation and working-indicator releases; it is not a board, transfer or approval count.

## Proof limits and preserved work

The screenshot pass checked visible hierarchy, density, line breaks, labels, exact IDs, geometry and clipping. It did not activate native links, type into controls, execute browser keyboard/touch/Back paths, measure contrast/hitboxes, run assistive technology, or prove zoom/reflow/reduced-motion behavior. Drawn controls are static editable specimens. The separate HTML implementation has source-logic tests, not real-browser acceptance. The earlier denied data-URL preview was not retried through another scheme or carrier.

The earlier six final r4 pairs and their closed visual findings remain retained; they do not substitute for these three r2 captures. F01/F02/D08 held effects, the 301 undispatched resource actions, original census and original identity/ownership planes are unchanged. Optional review was not made a stopping gate; formal reference/release requirements remain separate.
