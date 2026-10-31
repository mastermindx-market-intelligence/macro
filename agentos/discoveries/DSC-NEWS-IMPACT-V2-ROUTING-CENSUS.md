---
key: NEWS-IMPACT-V2-ROUTING-CENSUS
claim: >
  Of the 99 gated_v2 continuation cases, 30 had never been shown on any routing card. Seat
  routing verdicts on those 30 (census seed 20261020, tool build_v2_routing.py sha256
  b6aac488…) class 17 MATCH, 7 NO_EVENT (5 commentary, 2 market report), 5 OTHER_EVENT
  (4 where the event's filing is absent from the attached bodies, 1 where the graded v1
  body lacks the event and only a v2-added filing reports it) and 1 WRONG_ISSUER. MATCH
  share is 0.567, Wilson 95% [0.392, 0.726]. By graded status: of 8 graded cases 7 are
  MATCH and 1 OTHER_EVENT; of 22 never-graded cases 10 are MATCH. Combined with the prior
  routing verdicts, the routing map over all 99 drawn cases is 74 MATCH, 15 NO_EVENT, 9
  OTHER_EVENT and 1 WRONG_ISSUER. 74 cases score (T1 34, T2 36, T3 4); 62 already carry a
  two-family grade and 12 are new to labeling. The scorable shortfall against 600 is 526.
falsifier: >
  Re-running the committed build_v2_routing.py on the committed v2_routing_verdicts.json
  producing v2_routing_spec.json or v2_routing.json bytes that differ from the committed
  files; or an independent second auditor classing more than 5 of the 30 census cases
  differently from the seat on the MATCH / not-MATCH split.
so_what: >
  The filing-first widening yields 74 scorable cases, not 99: about one drawn case in
  four still reports no event, another event, or another issuer, even after gates-2.
  Labeling is now 12 cases, not 26. The gap to 600 is 526 and the continuation draw cannot
  close it; the levers are the 113 open windows (a v2 re-run after 2026-10-19, recorded
  as a new draw) and issuer resolution for the 1,271 no-CIK candidates, which belongs to
  the event-ledger owner. A gated-in draw still needs a routing verdict per case before
  it scores.
kind: data
verified_at: 2026-10-14
verified_by: >
  PYTHONPATH=.:research/prophet_v4/news_to_business_impact_20261006/benchmark/results_w2/tools
  python3.12 research/prophet_v4/news_to_business_impact_20261006/benchmark/results_w2/tools/build_v2_routing.py
  SCRATCH_W2 research/prophet_v4/news_to_business_impact_20261006/benchmark/results_w2
  AUDIT_OUT research/prophet_v4/news_to_business_impact_20261006/benchmark/results_w2/audit/v2_routing_verdicts.json
  reproduces audit/v2_routing_spec.json (sha256 33fa9e36…) and audit/v2_routing.json
  (401e8bbc…) byte for byte, and its cards match the cards the verdicts were written from
  (cmp, 2026-10-14). The verdicts file is sha256 9cd6895b….
scope:
  - "research/prophet_v4/news_to_business_impact_20261006/benchmark/results_w2/audit/v2_routing*.json"
  - "research/prophet_v4/news_to_business_impact_20261006/benchmark/results_w2/tools/build_v2_routing.py"
  - "research/prophet_v4/news_to_business_impact_20261006/benchmark/gated_v2/**"
confidence: probable
---

# The 99-case continuation draw holds 74 scorable cases and 12 to label

A routing census of the 30 continuation cases no card had shown finds 17 that report the
headline's event in the issuer's filing. Across all 99 drawn cases that gives 74 MATCH
cases, 62 of them already graded. Labeling now needs 12 cases, and the scorable set is
526 short of 600. The census is one seat's reading; a second auditor extends it when a
labeling lane opens.
