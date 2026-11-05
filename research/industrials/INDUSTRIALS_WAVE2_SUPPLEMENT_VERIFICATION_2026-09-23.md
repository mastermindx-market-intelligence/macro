# Industrials Wave 2 reconciliation supplement — verification

Verification date: 23 September 2026. Operation: `gmi-industrials-sector-research-20260923-sol-001`. Carrier: Macro Draft/HOLD PR #7789.

Local research integrity/arithmetic verification completed with **16 PASS, 0 FAIL**. The checks cover source/acceptance identifiers, Rockwell contribution arithmetic, Legrand cash-growth arithmetic, Yaskawa component/rounding reconciliation, valuation-scenario ordering, calculation-to-document source binding, and Fable-handoff hold language.

These are research-document and arithmetic checks. They are **not** application tests, independent factual review, source-rights admission, empirical validation, CI, deployment or browser proof.

## Immutable readback

`research/industrials/INDUSTRIALS_WAVE2_RECONCILIATION_SUPPLEMENT_2026-09-23.md`
- local verified UTF-8 bytes: 13,761
- local SHA-256: `079d6b8da91e18503d53edd46cae899055dcff22fba7309b3dc6cd1ef45908a2`
- local Git blob: `d16690d4a59f69ec69e4dd50761cb75d3e704d84`
- GitHub readback blob: `d16690d4a59f69ec69e4dd50761cb75d3e704d84`
- result: exact-byte Git blob match

`research/industrials/INDUSTRIALS_WAVE2_SUPPLEMENT_CALCULATIONS_2026-09-23.json`
- GitHub readback blob: `f3f7ede2e2b240a6926fe1803931dc393fa0baae`
- GitHub-readback reconstruction: 3,162 bytes; SHA-256 `83c96122f09582a468705fc1da94b42ae179a93a30b60925cd3dfeabc9e49aff`; calculated Git blob `f3f7ede2e2b240a6926fe1803931dc393fa0baae`
- parsed JSON was semantically identical to the locally verified calculation object; formatting differs from the pretty-printed local file only
- result: exact remote blob identity verified and calculation-object semantic equality confirmed

## Check classes passed

- 15 unique `W2X` supplemental source identifiers cited
- 16 unique supplemental acceptance cases
- Rockwell sales-share arithmetic
- Rockwell aggregate-segment-profit-share arithmetic
- Rockwell contribution to enterprise operating-profit increase arithmetic
- Legrand pre-working-capital cash growth arithmetic
- Legrand net operating cash growth arithmetic
- Legrand free-cash-flow growth arithmetic
- Yaskawa rounded component sum
- Yaskawa explicit rounding residual
- greater capital burden lowers the illustrative modeled value
- higher modeled margin/capital return raises the illustrative modeled value
- higher required return lowers the illustrative modeled value
- terminal-value shares remain explicit in the illustrative cases
- calculation source identifiers exist in the supplement
- final Fable CEO build handoff remains withheld

The supplement uses a non-conflicting `W2X` bibliographic namespace and leaves the existing canonical Wave 2 files as **DO_NOT_REDO**. It creates no new product/evidence/identity/score/publication owner.
