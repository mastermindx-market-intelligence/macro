# B01 independent native verification after scoped SVG correction

## Result

**PASS — native B01 matrix postcondition proven.** This finding applies to the corrected B01 Paper artboard and does not establish browser or production acceptance.

Parent reported operation `d08b-live-b01-svg-contrast-correction-20261104-c3` as APPLIED_RESPONSE_OBSERVED. This independent verifier issued only catalog and Paper reads. No mutation, finish call, focus transition, operation retry, cleanup, move or deletion was performed.

## Exact observed placement

| Node | Parent | Observation |
|---|---|---|
| New SVG `1SDU-0` | `1ONX-0` | Visible; artboard `1NZL-0` |
| Inner frame `1ONX-0` | `1ONW-0` | Same title, controls and legend siblings; new SVG occupies its prior sibling slot |
| Matrix `1ONW-0` | `1NZL-0` | 824 × 514 at x248, y336 |
| B01 `1NZL-0` | `root_node_p-12-0` | 1440 × 1050 at x0, y0 |
| File | `01M3NSZGE8JWN2EZCSF0DT05RM` | Terminal |

Live catalog: Paper 0.5.18, digest `16e6b93f0c51a1574ba8acee4df732052898707a04731d3817530971a88fdefd`.

## Cell and contrast proof

Actual full-artboard JSX was read after the reported correction. The verification script extracted the live SVG and compared all 54 cells with frozen B01 `matrix` HTML in `d08b-work/source/paper-compositions.json`.

- **54 / 54 cells match.** Zero differences in label value/sign, foreground, fill RGB, quantized alpha byte, selection stroke, cell position and dimensions, text position and font size.
- Native coordinate rounding was allowed only to the observed three decimal places (absolute tolerance 0.00051).
- Foregrounds: **51 white `#FFFFFF`; 3 black `#000000`**. Black labels are +128, +268 and −201.
- The before/after native SVG trees are identical after excluding only the root node ID and the 54 cell-label fill attributes. Every other native SVG attribute, text string, shape, cell fill, alpha, coordinate, row total, header, spot line and selection stroke is preserved.
- Native color alpha is read from the actual eight-digit SVG fill; it is not taken from the unquantized HTML payload.
- Minimum contrast: **4.655805166721768:1**, at +128, foreground `#000000`, fill `#65CCD291`, alpha `145/255`, over panel `#181B21`.
- **Zero labels below 4.5:1.**
- Prior actual-native minimum was 4.2446401522598105:1. The original failure remains recorded in FINDINGS.md and the before evidence.

The contrast calculation composites native fill in sRGB over the actual panel, then applies WCAG relative luminance. It is a matrix-label contrast check, not a claim that all product accessibility requirements are satisfied.

## Actual visual inspection

Fresh native screenshot `B01-live-after-repair.jpg` was displayed and inspected at 1440 × 1050. The black labels on the brightest positive and negative cells are visible and distinct. All nine strike rows, six expiry columns, row totals, dashed spot reference, selected cell outline and matrix legend fit within the panel.

The screenshot retains the full advanced-control row, selected-node inspector, “Inspect 2 contracts,” session comparison controls, source/coverage row, fixture indicator and source clock. The six lower view controls, including “3D / exact 2D,” and the book-history row remain visible without clipping. This screenshot verifies the desktop B01 composition only.

## Evidence and preservation

| File | SHA-256 |
|---|---|
| B01-live-before-repair.jpg | `7beedaab37baf59eca08ffd8c400d253e61af45614f3fda74faeb2554f715859` |
| B01-live-after-repair.jpg | `c1f8abd9772e043ede31567379a82c2270a5a5b7424a98f8593818e66cc6d143` |
| B01-after-1NZL-0.jsx | `48d12dd0ece7856d494419aba121132aef008367a0df93a4802b65b0b5aa59ae` |

- B01-after-observation.json: exact live parent-chain responses and catalog metadata.
- B01-after-verification.json: all 54 expected/native checks, contrast results and artifact hashes.
- verify_b01_after.py: reproducible local comparison and contrast calculation.
- B01-after-image-part-*.b64: local transport chunks of the same native screenshot; not additional captures.

Earlier B01 JSX, screenshots, mismatch findings, target-snapshot diagnostic and separate-frame evidence remain intact. This task did not read or modify the separate `1S2W-0` frame.

