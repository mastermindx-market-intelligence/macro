---
key: NEWS-IMPACT-EDGAR-BODY-2-FRAME
claim: >
  Widening the 8-K body band from (a-1, a+1) to (a-1, a+4) (ni-edgar-body-2, frozen at
  f0ba5795, run --as-of 2026-10-14) raises the body-available frame from 235 to 364 of
  2,837 candidates: T1 77 to 121, T2 115 to 169, T3 43 to 74. 137 candidates gain a body
  and 8 v1 bodies move to window_open. The rest have no body: 1,271 issuers resolve to no
  CIK, 1,089 filed no qualifying 8-K in the band, and 113 windows were open on the run
  date (they close 2026-10-14 to 2026-10-19). ni-routing-gates-2 gates in 135 of the 364
  (T1 54, T2 74, T3 7). The ni-sampler-1 draw over that gated frame (seed 20261014, one case
  per holdout group) holds 99 cases: T1 49, T2 46, T3 4, a shortfall of 501 against 600.
  73 of the 99 already carry a grade from the 157-case graded draw (15 of those now attach
  filings beyond the graded body); 26 have never been graded and 21 of those had no v1
  body. Re-running gates-2 on the v2 bodies of v1 body-available cases changes 5 statuses,
  all from g3_no_family_language to gated_in.
falsifier: >
  Re-running the committed routing_gates_2 and tape_draw commands on the committed
  status_map.json producing a gate map or a gated_v2 file that differs from the committed
  bytes; or a v2 re-run with --as-of on or after 2026-10-20 resolving the 113 open windows
  into more than 60 new bodies, which would mean the 2026-10-14 frame understates the band
  by more than the open windows explain.
so_what: >
  The band widening is worth one wave: it adds 129 net bodies and 26 new continuation
  cases, but it does not close the gap to 600. T3 stays at 4 of 200 because gates-2 drops
  most T3 bodies. The largest remaining lever is issuer resolution: 1,271 candidates name no
  ticker the ledger maps to a CIK. That belongs to the event-ledger owner, not the body
  fetch. The open windows settle on a re-run after 2026-10-19.
kind: data
verified_at: 2026-10-14
verified_by: >
  PYTHONPATH=. python3.12 -m engine.news_impact.routing_gates_2 --candidates
  candidates_all.jsonl --bodies bodies_v2/bodies.jsonl --texts bodies_v2/texts --out
  gates2_map.json --report gates2_report.json, then PYTHONPATH=. python3.12 -m
  engine.news_impact.tape_draw ... --seed 20261014 --body-frame
  body_frame_v2/status_map.json --gate-frame gates2_map.json, reproduce
  body_frame_v2/gates2_map.json (sha256 83af8bf1…), gates2_report.json (7e24829e…) and
  gated_v2/{manifest.json (8ac625b3…), cases.jsonl (d88f2d84…), draw_report.json
  (d8b02b0c…)} byte for byte (cmp, 2026-10-14). status_map.json sha256 1234ebb1…,
  body_report.json f90c740c…. Graded overlap from gated_v2/cases.jsonl against
  graded/cases.jsonl and the w2 grade files.
scope:
  - "engine/news_impact/edgar_body.py"
  - "research/prophet_v4/news_to_business_impact_20261006/benchmark/body_frame_v2/**"
  - "research/prophet_v4/news_to_business_impact_20261006/benchmark/gated_v2/**"
confidence: probable
---

# A four-session 8-K band adds 129 bodies and 26 new cases, and T3 stays at 4 of 200

Widening the body band finds an 8-K for 364 candidates instead of 235. After gates-2 and
the one-per-group sampler, that gives a 99-case continuation draw, 26 of them never
graded. The draw is reproducible byte for byte from committed code and the committed
status map. It does not reach 600: issuer resolution, not the band, is the larger lever.
