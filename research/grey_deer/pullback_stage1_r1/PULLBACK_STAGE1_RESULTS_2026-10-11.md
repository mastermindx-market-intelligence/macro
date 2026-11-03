# Pullback stage-1 results (Grey Deer W3, 2026-10-11)

- schema: `grey_deer_pullback_stage1/v1`; run commit `fbeff30d34ed7a8280f8dc9ca1a13d21b8db4c24`
- prereg blob `49a68b5e9c6543d662044b0aa391c4b6e6e6052e`; manifest v1.0.0 blob `38925409555d046eb9d3ad38ddaba33e2159a3d3`
- sample: 1321 rows 2021-07-06..2026-10-07, `subframe_content_sha256` matches
- trial budget: family `grey_deer_pullback_v1`, budget 69, basis `itemized`

## Gates (12 claims; prereg SS11 verdict words only)

| claim | statistic | point | lower bound | verdict | flags |
|---|---|---|---|---|---|
| h5/P-all/binary | delta_v@alpha=b_h | 0.0746888 | -inf | underpowered/blocked claim | FRAGILE, UNDERPOWERED_DISCLOSED |
| h5/P-all/quantile | pinball_skill | 0.00941956 | -0.0392484 | underpowered/blocked claim | UNDERPOWERED_DISCLOSED |
| h10/P-all/binary | delta_v@alpha=b_h | -0.428528 | -5.28919 | underpowered/blocked claim | FRAGILE, UNDERPOWERED_DISCLOSED |
| h10/P-all/quantile | pinball_skill | -0.0124126 | -0.0816254 | underpowered/blocked claim | FRAGILE, UNDERPOWERED_DISCLOSED |
| h21/P-all/binary | delta_v@alpha=b_h | -0.201975 | -2.27147 | underpowered/blocked claim | FRAGILE, UNDERPOWERED_DISCLOSED |
| h21/P-all/quantile | pinball_skill | -0.0616467 | -0.165336 | underpowered/blocked claim | FRAGILE, UNDERPOWERED_DISCLOSED |
| h5/P-active/binary | None | — | — | underpowered/blocked claim | OBSERVER_NOT_ON_MAIN |
| h5/P-active/quantile | None | — | — | underpowered/blocked claim | OBSERVER_NOT_ON_MAIN |
| h10/P-active/binary | None | — | — | underpowered/blocked claim | OBSERVER_NOT_ON_MAIN |
| h10/P-active/quantile | None | — | — | underpowered/blocked claim | OBSERVER_NOT_ON_MAIN |
| h21/P-active/binary | None | — | — | underpowered/blocked claim | OBSERVER_NOT_ON_MAIN |
| h21/P-active/quantile | None | — | — | underpowered/blocked claim | OBSERVER_NOT_ON_MAIN |

## Episodes and honest-N (prereg SS8)

| h | family | origins | events | clusters | episodes | event months | power floor |
|---|---|---|---|---|---|---|---|
| h5 | binary | 1001 | 11 | 4 | 4 | 5 | UNDERPOWERED_DISCLOSED |
| h5 | quantile | 1000 | 11 | 4 | 4 | 5 | UNDERPOWERED_DISCLOSED |
| h10 | binary | 996 | 36 | 8 | 6 | 9 | UNDERPOWERED_DISCLOSED |
| h10 | quantile | 991 | 36 | 8 | 6 | 9 | UNDERPOWERED_DISCLOSED |
| h21 | binary | 985 | 117 | 9 | 7 | 16 | UNDERPOWERED_DISCLOSED |
| h21 | quantile | 985 | 117 | 9 | 7 | 16 | UNDERPOWERED_DISCLOSED |

## Comparison sets (descriptive; prereg SS7/SS9)

- h5 binary: N_common 1001, base rate 0.010989; candidate Brier 0.0148616 vs reference 0.0124097, BSS -0.197578, V@b_h 0.0746888

- h5 quantile: N_common 1000, base rate —; candidate Brier — vs reference —, BSS —, V@b_h 0.0119563

- h10 binary: N_common 996, base rate 0.0361446; candidate Brier 0.0526998 vs reference 0.0483925, BSS -0.0890081, V@b_h -0.428528

- h10 quantile: N_common 991, base rate —; candidate Brier — vs reference —, BSS —, V@b_h 0.0180386

- h21 binary: N_common 985, base rate 0.118782; candidate Brier 0.14364 vs reference 0.138174, BSS -0.0395559, V@b_h -0.201975

- h21 quantile: N_common 985, base rate —; candidate Brier — vs reference —, BSS —, V@b_h 0.0280189

## Negative control (prereg SS12; never a gate)
- h5: shifted M3 BSS -0.289024, V@b_h -1.9272; shifted Q3 pinball skill -0.149725 — expected at or below 0
- h10: shifted M3 BSS -0.513368, V@b_h -1.4652; shifted Q3 pinball skill -0.176464 — expected at or below 0
- h21: shifted M3 BSS -0.195811, V@b_h -0.623517; shifted Q3 pinball skill -0.191576 — expected at or below 0

## INC (incumbent replay; own CURRENT_VINTAGE table, never a gate)
- h5: covers 1001/1001 evaluation origins (1); Brier vs native label 0.0108829
- h10: covers 996/996 evaluation origins (1); Brier vs native label 0.0353746
- h21: covers 985/985 evaluation origins (1); Brier vs native label 0.102132

## Deviations
- `CODE_DEFECT_RERUN`: original output kept at commit dd67262e7ab8; INC_LABEL_INDEX: run_inc read native_forward_labels date as a column (KeyError); fixed at fbeff30d34ed7a8280f8dc9ca1a13d21b8db4c24 to align on the index

## Blocked
- none (completed run)
