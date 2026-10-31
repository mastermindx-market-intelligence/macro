---
key: NEWS-IMPACT-MINIMAX-V10-NULL-PERIOD
claim: >
  Every malformed_value slot in the w2 benchmark comes from one return shape. Under the
  lane packet prompt-v1.0, fam_a (MiniMax-M3) wrote the period of a present quantity as
  null in 11 of 60 present quantities. The frozen grader cannot use a null period (rule
  Q1), so each of those slots scored malformed_value; there are 11 such slots and no other
  cause. Under prompt-v1.1, whose QUANTITY SLOTS block spells out the period object, fam_a
  wrote 0 null periods in 83 present quantities. fam_b (qwen3.7-plus) wrote no null period
  under either version. Read as a field_absence.v1 not_stated period, the 11 slots
  re-grade as 6 agree_present, 3 present_value_differs and 2 present_vs_absent, and the
  seat audit found all 6 counterfactual agreements correct.
falsifier: >
  A null period in a prompt-v1.1 or later return, or a malformed_value slot whose cause is
  not a null period. tools/build_audit_malformed.py --census prints the period shapes by
  family and prompt version and would show either.
so_what: >
  The malformed class is a prompt artifact, not a model-quality signal, and prompt-v1.1
  and later already remove it, so future waves should expect zero malformed slots and
  treat any as a regression. The grader should keep rejecting null periods rather than
  coercing them. The counterfactual is diagnostic only: summary.json is not re-scored, and
  the 3 disputes it exposes are T1 guide gaps ruled in
  DEC:NEWS-IMPACT-GUIDE-V12-T1-AMOUNT-RULES.
kind: data
verified_at: 2026-10-14
verified_by: >
  PYTHONPATH=. python3 results_w2/tools/build_audit_malformed.py SCRATCH_W2 BENCH --census
  (fam_a prompt-v1.0 null 11 of 60, prompt-v1.1 null 0 of 83, fam_b null 0), and the OUT_DIR
  run reproducing results_w2/audit/regrade_malformed.json byte for byte (sha256
  fb37207e…); verdicts in results_w2/audit/audit_malformed.json (sha256 82819ab2…); seat
  run, 2026-10-14.
scope:
  - "research/prophet_v4/news_to_business_impact_20261006/benchmark/results_w2/**"
confidence: verified
---

# The malformed slots are one prompt-v1.0 return shape

All 11 malformed_value slots are fam_a prompt-v1.0 returns that wrote a quantity period as
null. Prompt-v1.1 removed the shape (0 of 83). The class measures the prompt, not the model.
