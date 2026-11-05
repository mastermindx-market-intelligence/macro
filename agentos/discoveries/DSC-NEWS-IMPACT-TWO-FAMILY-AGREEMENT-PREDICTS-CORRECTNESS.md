---
key: NEWS-IMPACT-TWO-FAMILY-AGREEMENT-PREDICTS-CORRECTNESS
claim: >
  In the w2 benchmark, when the two inexpensive families (fam_a MiniMax-M3, fam_b
  qwen3.7-plus) agree on a present critical value, the value was right in every audited
  slot that could be decided. The 40-slot stronger-model audit (seed 20261014) judged 20
  agree_present slots: 19 correct, 0 wrong and 1 ambiguous per family, an error rate of 0
  with Wilson 95% upper bound 0.168. When they dispute, both sides are mostly wrong. Over
  20 disputed slots, fam_a was 3 correct, 11 wrong and 6 ambiguous (error 0.786 of decided,
  Wilson 95% 0.524–0.924). fam_b was 5 correct, 8 wrong and 7 ambiguous (0.615, Wilson 95%
  0.355–0.823). Agreed absences (129 slots) are not part of this claim; the addendum audit
  covers them in DSC:NEWS-IMPACT-TWO-FAMILY-AGREED-ABSENCE-HOLDS.
falsifier: >
  A fresh audit of agree_present slots, by an independent auditor, that finds 2 or more
  wrong out of 20 for either family. Or a third family that rejects agreed present values
  at a rate above 0.168.
so_what: >
  A third family is needed mainly where the first two dispute. Third-family cost should
  scale with the disputed rate (0.423 of critical slots in w2), not with the whole
  population. Agreed absences, the largest class (129 of 293 slots), were audited
  separately (DSC:NEWS-IMPACT-TWO-FAMILY-AGREED-ABSENCE-HOLDS: 0 shared misses in 20). This is a
  routing input, not a promotion: n is 20 per stratum and the auditor was the seat model.
  Scope: "right" means faithful to the attached filing, not to the headline's event; 4 of
  the 10 agreed-present slots in the routing-check sample sat on off-event cases
  (DSC:NEWS-IMPACT-W2-ROUTING-MOSTLY-OFF-EVENT).
kind: data
verified_at: 2026-10-14
verified_by: >
  benchmark/results_w2/summary.json audit block and benchmark/results_w2/audit/audit.json,
  reproduced byte for byte by PYTHONPATH=. python3 results_w2/tools/score_benchmark.py
  (seat run, 2026-10-14). Audit sample reproduced by tools/build_audit.py
  (sample.json sha256 868ce66e…).
scope:
  - "research/prophet_v4/news_to_business_impact_20261006/benchmark/results_w2/**"
  - "engine/news_impact/agreement.py"
confidence: probable
---

# Two-family agreement on a present value was right in every decided audit slot

Agreed present values: 0 wrong out of 19 decided per family. Disputed values: most of both
sides were wrong. A third family pays off on disputes, not on agreement. Agreed absences
are covered by DSC:NEWS-IMPACT-TWO-FAMILY-AGREED-ABSENCE-HOLDS.
