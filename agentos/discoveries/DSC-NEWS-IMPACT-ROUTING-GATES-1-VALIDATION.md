---
key: NEWS-IMPACT-ROUTING-GATES-1-VALIDATION
claim: >
  The frozen routing gates ni-routing-gates-1 (engine/news_impact/routing_gates.py, commit
  a8f98d21) lift the on-event rate of the w2 draw from 15 of 40 to 32 of 40 (0.80, Wilson
  95% [0.652, 0.895]). That misses the pre-registered bar of at least 34 of 40. No gated-in
  miss is WRONG_ISSUER. Of the 8 misses, 2 headlines report an event of another family (a
  product offering routed to capital allocation, a non-product launch routed to
  strategic/product), 3 are headline shapes G1 misses (a market report, a quote page, a
  solicitation) and 3 carry family language about a different event. The gates drop an
  estimated 0.155 of real events (bound interval [0.054, 0.351]), which passes the 0.20
  bar. All 3 sampled dropped events are T2 cases cut by g3_no_family_language because the
  filing words the event outside the family pattern. T3 is the weak family: 2 of 5 gated-in
  T3 cases are on-event, and 3 of 6 gated-out T3 cases are real events no attached 8-K
  reports. Pool: 192 body-available cases outside the 43 that trained the gates; 97 gated
  in, 95 gated out; 40 and 20 sampled on seed 20261017.
falsifier: >
  An independent auditor classing the same 60 cards under the four routing-check classes
  and finding 34 or more of the 40 gated-in cases MATCH (the gates pass), or 7 or more of
  the 20 gated-out cases MATCH (the drop share rises past 0.20).
so_what: >
  The gates are a draw-efficiency filter, not an on-event guarantee: a gated-in case still
  needs its own routing verdict before it is scored (DEC:NEWS-IMPACT-ROUTING-GATES-1-MISS-PATH).
  The misses name the next gate revisions: the sense of "offering" and "launch", the three
  headline shapes, a body event that differs from the headline's, and G3's T2 cuts. The
  frame binds harder than the gates: on 8-K bodies the gated pool holds about 35 T1, 56 T2
  and 4 T3 on-event cases, so 200 per family needs a frame about 6×, 4× and 50× wider, and
  T3 cannot reach 200 on 8-K bodies.
kind: data
verified_at: 2026-10-14
verified_by: >
  PYTHONPATH=. python3.12 results_w2/tools/build_gate_validation.py SCRATCH_W2 results_w2
  OUT results_w2/audit/gate_verdicts.json reproduces results_w2/audit/sample_gates.json
  (sha256 12f39ab5…) and results_w2/audit/gate_validation.json (sha256 0564c762…) byte for
  byte; verdicts results_w2/audit/gate_verdicts.json (sha256 66ad7bd3…), seat read of the
  60 shuffled cards with gate status hidden, 2026-10-14.
scope:
  - "engine/news_impact/routing_gates.py"
  - "engine/news_impact/tape_draw.py"
  - "research/prophet_v4/news_to_business_impact_20261006/benchmark/results_w2/**"
confidence: probable
---

# Routing gates 1 lift the draw to 0.80 on-event but miss the 34 of 40 bar

The gates more than double the on-event rate and drop about one real event in seven, all
of them T2 events the family pattern does not match. They fall two cases short of the
pre-registered bar, so a gated-in case still carries its own routing verdict. T3 is weak
under the gates and thin in the frame. The auditor also wrote the gates; no second
auditor read the cards.
