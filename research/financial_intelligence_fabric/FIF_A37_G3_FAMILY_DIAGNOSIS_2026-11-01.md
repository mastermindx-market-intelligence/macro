# FIF A37 — g3 family diagnosis for PK11 and PK12 (2026-11-01)

Workstream `WS:FINANCIAL-INTELLIGENCE-FABRIC` · acceptance case **A37**. Protocol
`fif-q0-quality-protocol/v1` (`FIF_Q0_QUALITY_PROTOCOL.json`). Source: the third Q1 generation,
`research/financial_intelligence_fabric/reports/q1_held_out_20261031_g3/`, evaluator commit
`30359c741f1f`, `evaluated_at` 2026-11-01T09:21:05Z, role `independent_q1`.

This record is a **diagnosis**, not a Q1 report and not acceptance evidence. It changes no
disposition: PK11 and PK12 stay `underpowered`, every failed family stays
`unavailable_research_only`, and nothing is relabeled or dropped from a denominator (protocol §10,
§13). Under `DEC-FIF-PACK-GENERALIZATION-DEV-CORPUS` the seat plans repairs from family-level
`failed_families` rows and aggregate cell counts only. The seat did not read label values, the
false-positive rows or the held-out stage to write this record.

## PK11 — financial-institution credit/capital/liquidity

| family | recall | precision | abstention | FP rate on negatives | reason codes |
|---|---|---|---|---|---|
| `cet1_or_stated_ratio` | 0/36 | — (no predictions) | 78/78 | 0/42 | precision_below_floor |
| `credit_loss` | 7/60 | 7/12 (Wilson lower 0.32) | 48/60 | — | precision_below_floor |
| `lcr_or_stated_liq` | 4/12 | 4/4 (Wilson lower 0.51) | 48/52 | 0/40 | precision_below_floor, underpowered |

Aggregate cells: BAC holds 108 positives. AAPL, SNOW, CAT and GOOGL hold 82 negatives (20, 20, 20, 22),
so the §6 cell "PK11 × non-bank issuers, at least 1 negative each" is met. Forms are 10-K and 10-Q,
as §5 allows. The label set conforms to the protocol.

**Diagnosis: a recall defect in pack code.** The pack produced no CET1 prediction at all, and it
abstained on most credit-loss and LCR positives. Non-bank leakage stayed at zero (0/82). The root
cause is in `engine/fundamental_forensics/specialist_packs/pk11_bank.py`, read from the source and
not from labels:

- The six disclosed-table fields (`cet1_ratio_disclosed`, `regulatory_minimum_disclosed`,
  `lcr_disclosed`, `nsfr_disclosed`, `liquid_assets_disclosed`, `npl_or_npa_disclosed`) map to bare
  `TableMapping()` placeholders (lines 162–167). They always resolve to typed absence.
- The undimensioned-fact filter can drop bank facts that issuers report only with a dimension.

Typed absence lands in the evaluator's `not_applicable:N` bucket (`pack_evaluation.py` folds
`missing` into it). The g3 report therefore counts this recall defect as abstention, not as error.
That is consistent with the report's numbers.

The five false-positive rows behind credit-loss precision 7/12 are not used for repair design.

**Repair route.** The repair is the dev-corpus build lane `fif-pk11dev-20261101-r1`, running now. It
captures public-EDGAR filings of five SIC-6021 banks disjoint from the held-out five and from the
AAPL gold (JPM, WFC, C, USB, PNC). It commits only a digest-only manifest, writes its own dev
assertions, and resolves the disclosed ratios from standard-taxonomy XBRL with a documented
dimension rule. The pack's non-bank gate is kept. Its probe numbers are a dev-corpus measurement
and never an A37 claim.

## PK12 — biotech cash/R&D/financing disclosures

| family (as labeled) | in PK12's protocol family ids? | recall | abstention | FP rate on negatives |
|---|---|---|---|---|
| `cash_flow` | no | 0/56 | 66/66 | 0/10 |
| `cash_investments` | no | 0/44 | 44/44 | — |
| `liquidity` | no | 0/18 | 18/18 | — |
| `rd_expense` | yes | 0/22 | 22/22 | — |

The protocol's PK12 families are `cash_runway_disclosure`, `rd_expense` and
`going_concern_or_financing`. PK12 forms are `10-K` only. Applicability is `negative` on all five
issuers. Section 5 says: "PK12 positives among these five issuers would be a labeling error;
A37 on this issuer list is satisfied by negative examples."

Aggregate cells: SNOW 82 positives and 3 negatives; GOOGL 58 positives and 13 negatives; AAPL, CAT
and BAC no labels; 111 of 156 labels on 10-Q.

**Diagnosis: the g3 PK12 label set does not conform to Q0. The pack does not fail.** The pack
returned typed absence on every trial, which is the protocol's expected behavior on five
non-biotech issuers, and it predicted no false positive (0/10). The label set has four conformance
defects:

1. It holds 140 positives on issuers whose applicability is `negative` (§5).
2. Three of its four families are outside PK12's family vocabulary.
3. It holds 10-Q labels for a 10-K-only pack.
4. AAPL, CAT and BAC have no negatives, so the §6 cell "PK12 × all five issuers, at least 1
   negative each" is unmet.

Protocol §10 and §13 forbid fixing this after the fact. The seat does not relabel, does not drop
the 140 positive cells from the denominator, and does not harmonise the labeler's interpretation.
PK12 stays `underpowered` for g3.

## Q0 conformance across all g3 packs

The PK12 defect classes are not PK12-only. The same aggregate census, run over every g3 pack report
(cells only: `n_labeled` by pack, issuer, form, section family and polarity), gives:

| pack | labels | under a family outside the pack's §5 ids | on a form outside the pack's §5 forms | positives on a `negative` issuer |
|---|---|---|---|---|
| PK01 | 424 | 0 | 0 | 0 |
| PK02 | 205 | 205 | 0 | 0 |
| PK03 | 158 | 158 | 0 | 0 |
| PK04 | 199 | 199 | 0 | 11 |
| PK05 | 324 | 226 | 123 (10-Q) | 0 |
| PK06 | 231 | 0 | 0 | 0 |
| PK07 | 160 | 142 | 70 (10-Q) | 0 |
| PK08 | 208 | 208 | 0 | 0 |
| PK09 | 201 | 0 | 0 | 0 |
| PK10 | 0 | — | — | — |
| PK11 | 190 | 0 | 0 | 0 |
| PK12 | 156 | 134 | 111 (10-Q) | 140 |

PK01, PK06, PK09 and PK11 conform on all three axes. For PK02, PK03, PK04 and PK08 every label
sits under a family name that is not one of the pack's protocol family ids. For PK05, PK07 and PK12
most labels do: only `utp`, `goodwill_rollforward` and `rd_expense` respectively match a protocol id.

What this means for g3:

- The per-family `failed_families` rows for PK02, PK03, PK04, PK05, PK07, PK08 and PK12 are keyed by
  the labeler's family names. The protocol's own families for those packs (§10: a disposition family
  is `(pack_id, section_family)`) are largely unmeasured in g3.
- These rows still describe pack behaviour on real filing sections. For example, PK08 recall is 0/75
  on sections labeled `legal_proceedings` and PK03 recall is 1/130 on `segments`. They are valid
  repair signals, but they are not protocol-family verdicts.
- Nothing changes in g3. The pack dispositions, the failed-family dispositions and the reports stand
  as published. Nothing is relabeled, renamed or dropped from a denominator.

What this means for repair and reopening:

- Dev-corpus repair lanes target the pack's protocol families and field semantics, not the g3
  labeler's family names.
- A family reopens only as a protocol family id, on fresh labels under a new split decision.
- The conformance gate's `section_family_outside_pack` and `form_outside_pack` checks catch every
  non-conforming cell in this table before a future seal. `positive_on_negative_issuer` catches the
  PK04 and PK12 cells.

## What follows

- **Conformance gate before any future seal.** Build lane `fif-q0conf-20261101-r1` adds
  `scripts/fif_q0_label_conformance.py`. It is a counts-only pre-seal check and it flags:
  - positives on `negative` issuers;
  - families outside a pack's protocol family ids;
  - forms outside a pack's protocol forms;
  - issuers or label classes outside the protocol;
  - §6 shortfalls (required-issuer positives, pack negatives, and the PK11/PK12
    negative-issuer rows).

  A labeler runs the gate on its own unsealed set; the seat never sees label values.
- **Reopening.** A failed family reopens only on fresh held-out labels under a new Q0 split
  decision (§10). Split decision 2 (`DEC-FIF-Q0-SPLIT-DECISION-2-SECOND-LABELING-WAVE`) is
  already merged and is not redone. Two preconditions apply to a further split decision:
  - PK11: it needs at least 16 BAC positives per family to make the 0.80 Wilson floor reachable at
    perfect precision (n=16 → 0.806). It should be cut only after the dev-corpus repair lands, so
    held-out labels are not spent on a known recall defect.
  - PK12: on these five issuers, A37 is satisfied by one conforming negative per issuer, and a
    positive cell needs an explicit later biotech issuer (§5, §6). Both are a new split's scope,
    never a g3 relabel.
- **Unchanged.** The 0.80 floor, the A37 per-pack dispositions in
  `FIF_A37_HELD_OUT_Q1_RECORD_2026-10-31.md`, and the g3 reports themselves.
