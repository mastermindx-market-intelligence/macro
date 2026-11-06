---
key: NEWS-IMPACT-ROUTING-GATES-2-VALIDATION
claim: >
  The frozen routing gates ni-routing-gates-2 (engine/news_impact/routing_gates_2.py, commit
  5baa4b10) miss both pre-registered bars on a fresh seed. Gated in: 31 of 40 cases are
  on-event (0.775, Wilson 95% [0.625, 0.877]) against a bar of 34. Gated out: an estimated
  0.208 of real events are dropped (bound interval [0.074, 0.439]) against a bar of 0.20.
  Of the 9 gated-in misses, 6 are commentary headlines on a standing fact, 2 route a product
  sense of "offering" to the capital family and 1 names an event no attached filing reports.
  No gated-in miss is WRONG_ISSUER. The 3 sampled dropped events are cut by the issuer guard
  (2) and by the results-without-2.02 rule (1). Gates-2 gates in no T3 case: all 25 T3 pool
  cases are gated out, and none of the 6 sampled is on-event. Pool: 132 body-available cases
  no card had shown, 56 gated in and 76 gated out; 40 and 20 sampled on seed 20261018.
  On the same pool the two gate sets disagree on 11 cases. Gates-2 is right on all 11 and
  gates-1 on none: it gates in 5 on-event cases gates-1 cut for missing family language,
  and gates out 3 no-event and 3 other-event cases gates-1 let through.
falsifier: >
  An independent auditor classing the same 60 validation cards and finding 34 or more of
  the 40 gated-in cases MATCH (gated-in passes), or 2 or fewer of the 20 gated-out cases
  MATCH (the drop share falls to 0.20 or less); or classing the 11 disagreement cases so
  that gates-1 is right on at least as many as gates-2 (the filter pick reverses).
so_what: >
  Neither gate set is an on-event guarantee, so every scored case keeps its own routing
  verdict (DEC:NEWS-IMPACT-ROUTING-GATES-2-MISS-PATH). Gates-2 is still the better filter:
  it wins every disagreement, so the draw uses it. The dominant gated-in miss is now a
  commentary shape the headline cannot separate from an event without losing events, and
  the pool left to validate another revision holds only 15 uncarded gated-in cases. The
  next lever is the frame, not the headline. T3 reaches no on-event case under gates-2 on
  8-K bodies.
kind: data
verified_at: 2026-10-14
verified_by: >
  PYTHONPATH=. python3.12 results_w2/tools/build_gates2_validation.py SCRATCH_W2 results_w2
  OUT results_w2/audit/gates2_verdicts.json reproduces results_w2/audit/sample_gates2.json
  (sha256 eaaa4985…) and results_w2/audit/gates2_validation.json (sha256 611afca2…) byte for
  byte; verdicts results_w2/audit/gates2_verdicts.json (sha256 a32a9a29…). PYTHONPATH=.
  python3.12 results_w2/tools/compare_gates_paired.py SCRATCH_W2 results_w2 OUT
  results_w2/audit/paired_verdicts.json writes results_w2/audit/gates_paired.json (sha256
  31e1914c…; verdicts sha256 0925d701…). Seat read of the shuffled cards with gate status
  hidden, 2026-10-14.
scope:
  - "engine/news_impact/routing_gates_2.py"
  - "engine/news_impact/routing_gates.py"
  - "research/prophet_v4/news_to_business_impact_20261006/benchmark/results_w2/**"
confidence: probable
---

# Routing gates 2 miss both bars, but beat gates 1 on every case where they disagree

Gates-2 lands at 31 of 40 on-event and drops about a fifth of real events, so it misses
the gated-in bar by three and the drop bar by a hair. It is still the better filter: on
the 11 pool cases where the two gate sets disagree, gates-2 is right every time. Six of
its nine gated-in misses are commentary headlines. It gates in no T3 case. The auditor
also wrote the gates; no second auditor read the cards.
