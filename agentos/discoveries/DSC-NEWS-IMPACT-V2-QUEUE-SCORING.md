---
key: NEWS-IMPACT-V2-QUEUE-SCORING
claim: >
  The 12 gated_v2 label-queue cases (DSC:NEWS-IMPACT-V2-ROUTING-CENSUS) now carry two-family
  labels under prompt-v1.2. Both families replay every span they cite against the
  ni-edgar-body-2 bodies (family A 125 of 125, Wilson 95% [0.970, 1]; family B 119 of 119,
  [0.969, 1]; no injection flag). On the 24 critical numeric slots the two families agree
  on 12 (0.50, Wilson [0.31, 0.69]): 6 agree present, 6 agree absent, 3 value differs and 9
  present versus absent. All 12 cases end routed_pending_third. The disagreement
  concentrates in one slot: on T1 executed_amount the families split present versus absent
  on all 6 cases (0 of 6, Wilson [0, 0.39]), family A reporting a value and family B none
  on 5 of the 6. T1 remaining_authorization agrees absent on all 6, and T2 stated_amount
  agrees on 2 of 5. Joined to the 62 graded MATCH cases, the scorable view is 74 cases and
  142 slots at agreement 0.535 (Wilson [0.453, 0.615]): T1 0.598 over 102 slots, T2 0.361
  over 36, T3 0.5 over 4. The scorable set stays T1 34, T2 36, T3 4, a shortfall of 526
  against 600.
falsifier: >
  Re-running results_w2/tools/score_v2_queue.py on the same canonicalised returns, bodies
  and agreement summary and getting a critical_slots.jsonl whose sha256 is not 4efe674a…,
  a summary.json whose sha256 is not 99fd23b2…, or any count above that differs. Or a
  third family, run on the 12 cases, reading T1 executed_amount as absent where family A
  reported it, on most of the 5 cases, which would move the error from family B to family A.
so_what: >
  The queue adds 12 cases to the labeled set but no adjudicated case yet: every one waits
  on a third family, which is GLM after 2026-10-19 05:16Z (Grok and Codex are exhausted).
  The executed_amount split is the slot to aim that third read at, and it is a candidate
  prompt-contract defect (what counts as an executed amount on a buyback disclosure)
  rather than a reading error, because one family reports it and the other does not on
  the same span-valid bodies. T2 remains the weakest template at 0.361 and gets no help
  from the queue (2 of 5). Agreement is not accuracy: these are two-family rates, and the
  adjudicated case count against 600 does not move until a third family resolves the
  disputed slots.
kind: data
verified_at: 2026-10-14
verified_by: >
  PYTHONPATH=.:research/prophet_v4/news_to_business_impact_20261006/benchmark/results_w2/tools
  python3.12 research/prophet_v4/news_to_business_impact_20261006/benchmark/results_w2/tools/score_v2_queue.py
  --w2q SCRATCH_W2Q --results research/prophet_v4/news_to_business_impact_20261006/benchmark/results_w2
  --bench research/prophet_v4/news_to_business_impact_20261006/benchmark --out
  research/prophet_v4/news_to_business_impact_20261006/benchmark/results_w2/v2_queue; the
  committed v2_queue/critical_slots.jsonl (sha256 4efe674a…) and summary.json (sha256
  99fd23b2…) carry every count above.
scope:
  - "research/prophet_v4/news_to_business_impact_20261006/benchmark/results_w2/tools/score_v2_queue.py"
  - "research/prophet_v4/news_to_business_impact_20261006/benchmark/results_w2/v2_queue/**"
confidence: verified
---

# The 12-case v2 queue labels cleanly but splits on T1 executed amount

Both label families cite only text that is in the filings. They agree on half of the 24
critical numeric slots, and most of the disagreement is one slot: on every T1 case one
family reports an executed buyback amount and the other reports none. Every queue case
waits on a third family. Joined to the 62 graded cases, the 74 scorable cases agree on
just over half their critical slots. T2 is lowest. The set is still 526 short of 600.
