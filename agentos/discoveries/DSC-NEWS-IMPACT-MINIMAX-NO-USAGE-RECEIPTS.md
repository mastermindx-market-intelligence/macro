---
key: NEWS-IMPACT-MINIMAX-NO-USAGE-RECEIPTS
claim: >
  The external-lane kit's MiniMax-M3 lane mode writes no token usage file. In w2, all 10
  fam_b (qwen3.7-plus, codex-native session) lanes wrote a *.usage.json receipt and none of
  the fam_a (MiniMax-M3) lanes did. So fam_a's per-case token cost cannot be measured from
  lane output. summary.json reports fam_a cost as null with reason USAGE_RECEIPT_MISSING.
  fam_b receipts cover 141 of 157 cases (one receipt was excluded because it mixed several
  session ids), at a pooled 300,318 total tokens per case, of which 279,232 are cached input.
falsifier: >
  After a MiniMax-mode lane run under the same kit, `ls <lane usage dir>/*fam_a*.usage.json`
  lists a receipt with observed token counts, or a provider-side usage export can be joined
  to lane run ids. Either one makes
  `PYTHONPATH=. python3 research/prophet_v4/news_to_business_impact_20261006/benchmark/results_w2/tools/score_benchmark.py`
  report a non-null fam_a cost.
so_what: >
  Any recall-versus-cost comparison that uses MiniMax lanes will have a null cost column
  until the lane mode writes receipts or a provider export is joined. Do not estimate
  MiniMax cost from the qwen receipts; the two run different tool loops. Report the gap as
  USAGE_RECEIPT_MISSING.
kind: runtime
verified_at: 2026-10-14
verified_by: >
  Seat scratch usage directory for w2 held 10 *.usage.json files, all W2_L_fam_b_*, and 0
  for fam_a (ls count, 2026-10-14). benchmark/results_w2/tools/score_benchmark.py costs()
  reads only observed receipts and sets fam_a null_reason USAGE_RECEIPT_MISSING; the
  committed summary.json carries that value.
scope:
  - "research/prophet_v4/news_to_business_impact_20261006/benchmark/results_w2/**"
confidence: verified
---

# MiniMax lanes leave no token receipts

fam_a cost is unmeasured because its lane mode writes no usage file. fam_b receipts give a
pooled 300k tokens per case, most of it cached input.
