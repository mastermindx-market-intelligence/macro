# FIF A37 — Q1 held-out evaluation: qualified abstain per pack (2026-10-20)

Workstream `WS:FINANCIAL-INTELLIGENCE-FABRIC` · acceptance case **A37** ("previously
unseen issuer/report format or negative example"; required behavior: untouched
held-out tests, false-positive/abstention report and failed-family disposition).
Protocol `fif-q0-quality-protocol/v1` frozen at `5267c66846e7733bc1eb30edc1524daff51598ca`
(`research/financial_intelligence_fabric/FIF_Q0_QUALITY_PROTOCOL.json`).

Evaluated tree: `d59b99b9afbe99ef528ce80db0ff66f0d9846abc` (twelve-pack fold, PR #9872). Record author: the FIF seat.
This record is **not** a Q1 pack quality report and is **not** acceptance evidence
(operator rule A34: acceptance needs twelve Q1-authored report paths; operator rule
"Q1 is an independent evaluator" — the seat and the pack lanes never author Q1).

## Precondition census (held-out root, read-only listing — no file opened)

`tests/fixtures/fundamental_forensics_held_out` at `d59b99b9afbe99ef528ce80db0ff66f0d9846abc` contains exactly:

```
README.md
```

No `packs/`, no `negatives/`, no `unseen_formats/`, no `labels/`, no `_SEALED` marker.
The Q0 freeze shipped the root and README only ("No corpus, no labels"), and the
held-out corpus and labels are produced by the independent labeler — never by the
pack lanes or the seat (DEC: held-out labels are labeler-owned). Nothing has been
delivered since the freeze.

## Per-pack disposition

| pack | name | required issuers | held-out package | label files | `_SEALED` | Q1 | disposition |
|---|---|---|---|---|---|---|---|
| PK01 | Debt, liquidity, covenants and maturities | CAT, BAC | no | 0 | no | not runnable | **qualified abstain** |
| PK02 | Stock compensation and dilution | SNOW | no | 0 | no | not runnable | **qualified abstain** |
| PK03 | Segments and geographic/product dimensions | CAT, GOOGL | no | 0 | no | not runnable | **qualified abstain** |
| PK04 | Revenue recognition and contract balances | SNOW | no | 0 | no | not runnable | **qualified abstain** |
| PK05 | Tax and uncertain tax positions | — | no | 0 | no | not runnable | **qualified abstain** |
| PK06 | Leases and off-balance commitments | CAT | no | 0 | no | not runnable | **qualified abstain** |
| PK07 | M&A, goodwill, intangibles and impairments | GOOGL | no | 0 | no | not runnable | **qualified abstain** |
| PK08 | Legal contingencies | — | no | 0 | no | not runnable | **qualified abstain** |
| PK09 | Controls, auditor and going concern | — | no | 0 | no | not runnable | **qualified abstain** |
| PK10 | Proxy compensation and governance | AAPL, SNOW, CAT, BAC, GOOGL | no | 0 | no | not runnable | **qualified abstain** |
| PK11 | Financial-institution credit/capital/liquidity | BAC | no | 0 | no | not runnable | **qualified abstain** |
| PK12 | Biotech cash/R&D/financing disclosures | — | no | 0 | no | not runnable | **qualified abstain** |

"Qualified abstain" means: the pack ships gold-calibrated code (builder CI green on
gold + isolation), its held-out false-positive/abstention report and failed-family
disposition **cannot be produced** at this head because the held-out split holds no
labels, and the pack's A37 cell therefore stays **PARTIAL** — not "accepted", not
"held_out_measured", not a silent omission from the denominator.

## Evidence that the independent evaluator path is intact and would refuse to overstate

A seat scratch probe (not a report; not committed under `reports/`) ran the independent
CLI `scripts/fif_pack_quality_report.py` for PK01 on split `held_out` with an **empty**
label list and an **empty** prediction list, head `d59b99b9afbe99ef528ce80db0ff66f0d9846abc`:

- exit 0, `quality_label` = `underpowered`; `failed_families` = [];
  `false_positives` = []; GAP printed: `precision_floor_not_predeclared`.
- power rows (all unmet): pack, applicable issuer, polarity=positive [BAC]: observed 0 < minimum 2; pack, applicable issuer, polarity=positive [CAT]: observed 0 < minimum 2; pack, polarity=negative: observed 0 < minimum 1; pack, format_class != ixbrl_inline: observed 0 < minimum 1.

So an empty held-out split cannot yield `held_out_measured` for any pack; the vocabulary
guard holds. The probe output lives only in the seat scratchpad.

## What unblocks A37 (owner-named, no seat action available)

1. **Independent labeler** delivers, per pack, `packs/PKxx/<package>/` (manifest schema
   `fundamental_forensics.golden_filing_package/v1`), `negatives/`, at least one
   unseen-format or negative cell (operator rule A37), and `labels/*.json` together with
   `labels/_SEALED`. Issuer roles and splits: Q0 protocol §3.
2. **Independent Q1 evaluator lane** (never the pack builder, never the seat) runs
   `scripts/fif_pack_quality_report.py --split held_out` per pack at the accepted head and
   files the twelve report paths plus failed-family records.
3. The seat then re-adjudicates A37 per pack from those twelve reports.

Until (1) lands, every A37 cell is a qualified abstain by construction; no amount of
builder work, re-running gold suites, or seat authorship can move it, and none was attempted.
