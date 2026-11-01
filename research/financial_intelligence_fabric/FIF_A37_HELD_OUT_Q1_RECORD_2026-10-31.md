# FIF A37 — Q1 held-out evaluation: per-pack re-adjudication (2026-10-31)

Workstream `WS:FINANCIAL-INTELLIGENCE-FABRIC` · acceptance case **A37** ("previously
unseen issuer/report format or negative example"; required behavior: untouched
held-out tests, false-positive/abstention report and failed-family disposition).
Protocol `fif-q0-quality-protocol/v1` (`research/financial_intelligence_fabric/FIF_Q0_QUALITY_PROTOCOL.json`).
Supersedes the 2026-10-20 qualified-abstain record
(`FIF_A37_HELD_OUT_QUALIFIED_ABSTAIN_2026-10-20.md`) for every pack listed below.

Evaluated tree: main `761e814eda8460d09ad6c53adc8ee495b4283cf1`. Q1 reports: evaluator commit
`13b043bb7812fab35fd52d6b220c29844eaa6a90` (fabric lane `fif-heldout-eval-20261031-r2`, PR #10293),
`research/financial_intelligence_fabric/reports/q1_held_out_20261031/`. Record author: the FIF seat,
who authored neither labels, seal, manifests nor reports. This record is **not** a Q1 pack quality
report and is **not** acceptance evidence; it reads the reports and states the resulting A37 cell.

## Preconditions now met (vs the 10-20 record)

- Held-out corpus and labels delivered by the independent labeler lanes: L-A (#9915), L-C (#10260),
  L-B (#10263); capture #9906; tidy #9916. 336 label trials across 11 packs; PK10 has no `labels/`
  (no held-out DEF 14A corpus).
- Precision floor **0.80** (Wilson lower bound) predeclared by the seat at 2026-10-31T07:04Z, before
  any held-out result existed (`DSC:FIF-Q1-PRECISION-FLOOR-PREDECLARED-0-80`), passed unchanged to
  all twelve reports.
- Independent Q1 evaluator ran the packs through the public pack API only; isolation suite green;
  `builders_read_held_out == false`, `aapl_golden_used_as_held_out == false` in every report.

## Per-pack disposition (read from the reports)

| pack | labels | quality_label | precision (Wilson) | recall | failed families | disposition | A37 cell |
|---|---|---|---|---|---|---|---|
| PK01 | 28 | underpowered | 17/17 [0.82, 1.00] | 17/26 | covenant_text; debt_outstanding; liquidity; maturity_schedule | unavailable_research_only | **PARTIAL** |
| PK02 | 46 | underpowered | 24/38 [0.47, 0.77] | 24/43 | eps; sbc; share_counts; share_repurchase | unavailable_research_only | **PARTIAL** |
| PK03 | 20 | underpowered | 1/6 [0.03, 0.56] | 1/19 | segments | unavailable_research_only | **PARTIAL** |
| PK04 | 28 | underpowered | 0/0 (no emissions) | 0/26 | contract_liability; revenue; rpo | unavailable_research_only | **PARTIAL** |
| PK05 | 51 | underpowered | 32/43 [0.60, 0.85] | 32/49 | income_tax; utp | unavailable_research_only | **PARTIAL** |
| PK06 | 16 | underpowered | 12/12 [0.76, 1.00] | 12/14 | lease_liability | unavailable_research_only | **PARTIAL** |
| PK07 | 28 | underpowered | 11/11 [0.74, 1.00] | 11/24 | business_combination; goodwill_intangibles; goodwill_rollforward; impairment_testing (fp_on_negative, invented_extraction) | unavailable_research_only | **PARTIAL** |
| PK08 | 28 | underpowered | 2/7 [0.08, 0.64] | 2/22 | commitments_note; legal_proceedings; loss_contingency | unavailable_research_only | **PARTIAL** |
| PK09 | 26 | underpowered | 9/9 [0.70, 1.00] | 9/22 | auditor_opinion; going_concern_wording; icfr_opinion | unavailable_research_only | **PARTIAL** |
| PK10 | none | unavailable_research_only (`no_held_out_labels`) | — | — | — | unavailable_research_only | **PARTIAL** |
| PK11 | 37 | underpowered | 0/0 (no emissions) | 0/27 | cet1_or_stated_ratio; credit_loss; lcr_or_stated_liq | unavailable_research_only | **PARTIAL** |
| PK12 | 28 | underpowered | 0/0 (no emissions) | 0/25 | cash_flow; cash_investments; liquidity; rd_expense | unavailable_research_only | **PARTIAL** |

**No pack reaches `held_out_measured`; no pack's `acceptance.state` moves to `accepted`.** The
production default path for every pack stays `display_tier`. Nothing is omitted from any denominator;
no family is relabelled; the 30 excluded trials (BAC 10-K `0000070858-23-000092`,
`package_admission_refused:primary_unparseable`) are listed in each affected pack's trials file.

## Why every pack is underpowered — three distinct causes, three distinct owners

1. **Corpus format axis empty (labeler/capture scope).** All 336 labels are `ixbrl_inline`; the
   protocol's one-non-inline-format minimum is unmet pack-wide. A37's "unseen format" column cannot be
   measured until the held-out corpus carries at least one non-inline package per pack. This is a
   corpus decision, not a pack defect, and not a reason to lower the minimum.
2. **Issuer class unbound (contract question, owner: seat ruling + labeler manifest).** The held-out
   manifests carry no SIC witness (`sic_source=unbound`), so PK04/PK11/PK12 applicability abstains
   (`issuer_class_unknown` / `sic_outside_biotech_codes`) on every trial. Two lawful resolutions, both
   outside this record: the labeler adds a SIC witness to the manifest schema (preferred; keeps the
   packs unchanged), or a reviewed scope ruling lets a pack accept an issuer-class assertion from the
   manifest. Neither may be done by a pack lane. PK12 and PK05 additionally abstain
   `form_outside_pack_forms` on labelled 10-Qs; whether those forms belong in the pack's scope is a
   contract question for the same ruling.
3. **Measured misses and false positives (pack engineering, per pack, own PR + review each).**
   PK02/PK03/PK05/PK08 false positives (36 total, all wrong-span/wrong-value families); PK01 typed
   absence on the BAC 10-Qs where labels are positive; PK07 `impairment_testing` fired on a negative
   and invented an extraction (the one `fp_on_negative` in the run). These are real pack defects and
   the ordinary repair path applies; the reports name the families.

A fourth item is kernel engineering: the BAC 10-K parser refusal ("nil fact cannot carry accuracy,
transform, sign, or scale") excludes 30 trials across six packs. A kernel fix lands under its own PR
and review; the evaluator re-run that follows is a new generation of reports, never an edit of these.

## What this record changes and does not change

- Changes: the per-pack A37 cell moves from "not runnable → qualified abstain" to "**measured,
  underpowered, failed families recorded → PARTIAL**", with Q1-authored evidence paths now existing
  for all twelve packs (operator rule A34: twelve Q1-authored report paths — present).
- Does not change: acceptance state of any pack; production binding of any pack; the 0.80 floor; the
  §6 minimums; the labels or the seal; the reports.

## Reopen conditions

A pack's A37 cell is re-adjudicated only on a new Q1 generation (new reports directory, new evaluator
lane id) after one or more of the three causes above is resolved under its owner's review. A fresh
session, a lost transcript or a repeated reading of these reports is not a reopen condition.
