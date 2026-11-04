# B01 native contrast correction — 2026-11-04

**Disposition: scoped native postcondition verified.** This update corrects the original design return's claim that the final B01 contrast payload had reached its live matrix. It does not replace the frozen evidence, approve the full design package, or establish product acceptance.

## Why this correction was needed

Resume inspection found that frozen `evidence/B01.jpg` was byte-identical to the still-visible native B01 before this repair. Its matrix had 52 off-white labels and two dark-gray labels, with minimum measured contrast **4.2446401522598105:1**. The original payload verifier had evaluated the intended corrected colors; the original operation's observed APPLIED response had not established the intended live-target postcondition.

The original operation `d08b-b01-matrix-contrast-a11y-r5-20261104-c3` addressed detached/empty `1O7B-0`. A separate frame `1S2W-0` on `p-1-0` matched the corrected payload, but its writer was unknown and it was left untouched. This was a **POSTCONDITION_MISMATCH**, not authority to retry or move that operation.

## Exact target and completed effects

| Item | Binding / outcome |
| --- | --- |
| File | Terminal `01M3NSZGE8JWN2EZCSF0DT05RM` |
| Candidate page | `p-12-0` |
| Artboard | B01 `1NZL-0`, 1440 × 1050 |
| Matrix | `1ONW-0`, 824 × 514 at (248, 336) |
| Inner frame | `1ONX-0` |
| Original live SVG | `1OOC-0` |
| Corrected live SVG | `1SDU-0` |
| Distinct repair operation | `d08b-live-b01-svg-contrast-correction-20261104-c3` — APPLIED_RESPONSE_OBSERVED |
| Exact-board finish | `d08b-finish-live-b01-contrast-correction-20261104-c3` — APPLIED |
| Writer / carrier | Root D08B session, existing native Paper carrier; one writer |

Before this repair, an attempted binding preparation using the foreground PROPHET snapshot was refused with `DOCUMENT_CHANGED`, `retry_allowed:false`, and no effect. That operation (`d08b-resume-bind-terminal-b01-20261104-c3`) was not retried. The same-pin `PAPER_DIRECT_CHATGPT.md` explicit-file contract provided `get_basic_info(fileId)` to obtain the actual Terminal guard. The repair used fresh exact-file and live-inner-frame evidence; it did not switch carriers, force foreground focus, or bypass a denial.

The verified parent chain is `1SDU-0 → 1ONX-0 → 1ONW-0 → 1NZL-0 → root_node_p-12-0`. Only the root SVG identity and 54 label foregrounds changed. Values, signs, cell fills/alpha, geometry, selected outline, totals, source clocks and advanced controls remain identical.

## Independent result

- **54/54** native cells match the intended corrected payload.
- **51 white / 3 black** labels; black labels are +128, +268 and −201.
- Native alpha bytes were used in the calculation, including +128's `#65CCD291` over `#181B21`.
- Minimum contrast **4.655805166721768:1**; **zero** matrix labels below 4.5:1.
- A fresh 1440 × 1050 native screenshot was independently inspected: all rows, expiry columns, totals, spot line, selection, source information and advanced controls fit.

[Before screenshot](B01-live-before-repair.jpg) · [Verified after screenshot](B01-live-after-repair.jpg) · [Independent verification](B01-AFTER-VERIFICATION.md) · [Native export](B01-after-1NZL-0.jsx) · [Machine-readable checks](B01-after-verification.json) · [Initial mismatch finding](FINDINGS.md)

Run `python updates/20261104-b01-contrast/verify_b01_after.py` from the D08B package, with Pillow available. The portable verifier reads the original committed `source/paper-compositions.json` and the before/after native exports, checks unchanged non-ink content, recomputes native contrast and validates screenshot hashes. It does not call Paper or a product API.

The original frozen B01 screenshot and original operation ledger remain unchanged so the mismatch is auditable. This update supersedes only their B01 contrast-placement claim. B02 and the sampled B04/B08/B14 informational-text corrections were independently checked during resume and needed no further mutation. Broader WCAG, formal RIG, F01/F02 release and product acceptance remain separate gates.
