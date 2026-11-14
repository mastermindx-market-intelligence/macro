# D03 T48 — native Paper mobile visual matrix (8 states; provisional)

2026-11-04 UTC. Existing Draft Macro PR #10617, D03 US Equities & Prophet. Protected Mastermind pin `700eef54bca4a2dc4e30d94a6b30dcfa733ad57c`; immutable commission `6e1862867193ec6486a22001a0e4fb515da20448`. This extends the original two-board frozen evidence in the sibling README; it does **not** replace or alter those originals.

Paper file `01M3NT5Y3G5HTJHVR0K5W2MDJM`, page `p-D-0` (D03 Read me / Build contract). [Open native page](https://app.paper.design/file/01M3NT5Y3G5HTJHVR0K5W2MDJM/p-D-0). Every row below was confirmed by native `get_basic_info` and actual board-bound screenshot/JSX readback.

| Width | Theme | Locale | Native artboard | Canvas height | Proof files |
|---:|---|---|---|---:|---|
| 390 | light | EN | `11OT-0` | 1950px | `board-390-light-en.jpg`, `board-390-light-en.paper.jsx` |
| 390 | dark | EN | `11Y9-0` | 1950px | `board-390-dark-en.jpg`, `board-390-dark-en.paper.jsx` |
| 390 | light | ZH | `127F-0` | 1800px | `board-390-light-zh.jpg`, `board-390-light-zh.paper.jsx` |
| 390 | dark | ZH | `122U-0` | 1800px | `board-390-dark-zh.jpg`, `board-390-dark-zh.paper.jsx` |
| 320 | light | EN | `11TO-0` | 2110px | `board-320-light-en.jpg`, `board-320-light-en.paper.jsx` |
| 320 | dark | EN | `12C0-0` | 2110px | `board-320-dark-en.jpg`, `board-320-dark-en.paper.jsx` |
| 320 | light | ZH | `12L6-0` | 1900px | `board-320-light-zh.jpg`, `board-320-light-zh.paper.jsx` |
| 320 | dark | ZH | `12GL-0` | 1900px | `board-320-dark-zh.jpg`, `board-320-dark-zh.paper.jsx` |

## Verified design deltas

- Reused the accepted light-English 390 and 320 foundations. Six additional real editable Paper artboards were deep-cloned **on disjoint targets**, named, styled and/or localized by stable node mappings under guarded `APPLIED_RESPONSE_OBSERVED` writes; no original R7/R8 and no held T49 row were edited.
- Added designed dark colors for surfaces, CTA contrast, muted metadata, invalidation boxes and comparison; the 390/320 native status-bar SVGs were explicitly corrected for dark-mode visibility. All dark states were actually rendered.
- Localized 57 consumer-facing text nodes per Chinese board while preserving tickers, quantitative fixtures and separate quote versus assessment clocks. Native screenshots of the narrower 320px Chinese variants show readable card controls, source notes and no clipped footer; Chinese artboard heights were shortened after visual inspection (390: 1800px, 320: 1900px).
- Each card retains independently dated quote and assessment, condition and invalidation; compact compare keeps both theses without selecting a computed winner, followed by separate Sources and Save actions. Controls remain **design-only** until actual route, identity, entitlement, state and readback integration.
- Illustrative INTC/MSFT names, prices, percentage changes, market backdrop and dates are **design fixtures**, not assertions of measured/live markets or trade recommendations. The UI states that saving requires explicit account-list confirmation and readback and that Sources/related Plans do not execute trades.

## What was and was not proved

**Proved in native Paper:** eight actual editable width/theme/locale compositions; board identity/dimensions; native screenshot and JSX extraction; manual visual QA of scan hierarchy, wrapping, controls, footer visibility, dark status-bar contrast and translated copy. This is screenshot inspection, **not** automated responsive accessibility acceptance.

**Static text-contrast follow-on:** 568/568 native text-node foreground/nearest-background pairs across the eight state exports pass the conservative AA thresholds (4.5:1 normal, 3:1 large); minimum light contrast **5.02:1**, dark **5.93:1**. An initial audit found 18 failures per light-state board, all repaired via guarded Paper edits and re-captured in the final evidence here. See `CONTRAST_AUDIT.md` and `.json`. This is a deterministic JSX-style audit, not full WCAG certification.\n\n**Still owed:** F01/F02 jointly released shared-shell contract v1 and real content geometry, real-data entitlement and provenance binding, touch/keyboard/focus/reduced-motion and complete WCAG (including non-text contrast), empty/loading/stale/error/permission states, authenticated account Save/reopen and signed-in Sources→Plan→same-candidate return, live-browser proof, RIG sign-off and user acceptance. D03 T49 original Paper operation remains `EFFECT_UNKNOWN` on row `11OR-0`; do not retry that edit. Other Fabric T45/T51 unknown effects are not settled by this independent T48 work.

The unrelated Prophet #9495 native publication pair was repaired to exact-head `7eda300a` with 12 checks and 16 offline captures, and its inherited test-contract failures were corrected to `94bb0c06`; this does not turn these Paper designs into deployed code or satisfy #9495 exact-head full hosted pack CI. Both #9495 and #10617 remain Draft/HOLD. No merge, merge-queue enqueue, Ready/un-draft, label, deploy, purchase or account/trade effect occurred.

`matrix.json` provides the exact stable mapping and qualification limits. The `.paper.jsx` exports include native node IDs for provenance; they are not served production JSX.
