---
key: NEWS-IMPACT-TWO-FAMILY-AGREED-ABSENCE-HOLDS
claim: >
  In the w2 benchmark, when both inexpensive families (fam_a MiniMax-M3, fam_b
  qwen3.7-plus) mark a critical slot absent, the absence was right in every audited slot.
  An addendum audit (seed 20261015) judged 20 of the 129 agree_absent slots: 20 correct
  absences and 0 shared misses, meaning no body stated a value that both families failed
  to find. The error rate is 0 with Wilson 95% upper bound 0.161. The card procedure that
  certified the absences showed every keyword window holding a number; as a positive
  control it covered the agreed span in 40 of 40 agree_present slots. A correct absence
  is not always a correct reason: in 2 of the 20 (cards 8 and 17) both families wrote
  not_stated where annotation guide-v1.1 gives stated_without_number.
falsifier: >
  An independent audit of agree_absent slots that finds 2 or more shared misses out of 20.
  Or a third family that finds a stated value in agreed-absent slots at a rate above 0.161.
so_what: >
  A third family can skip agreed absences as well as agreed present values, so its cost
  scales with the disputed rate (0.423 of critical slots in w2), not with the population.
  Absence reasons are less reliable than absences, so reasons should not be scored as
  correct until labels follow the guide-v1.1 rules. This is a routing input, not a
  promotion: n is 20, the auditor was the seat model, and a value stated with none of the
  window keywords nearby would not appear on a card.
kind: data
verified_at: 2026-10-14
verified_by: >
  benchmark/results_w2/audit/audit_absent.json (sha256 14e63889…). The sample reproduces
  byte for byte from PYTHONPATH=. python3 results_w2/tools/build_audit_absent.py
  SCRATCH_W2 OUT (audit/sample_absent.json sha256 819911e4…), and the positive control
  from build_audit_absent.py SCRATCH_W2 --control (hit 40, miss 0); seat run, 2026-10-14.
scope:
  - "research/prophet_v4/news_to_business_impact_20261006/benchmark/results_w2/**"
  - "research/prophet_v4/news_to_business_impact_20261006/phase1_designs/A6_labeler/annotation_guide.md"
confidence: probable
---

# Two-family agreement on an absence was right in every audited slot

Agreed absences: 0 shared misses out of 20 (Wilson 95% upper bound 0.161). The reason
attached to an agreed absence was wrong in 2 of the 20 under guide-v1.1. A third family
pays off on disputes, not on agreement of either kind.
