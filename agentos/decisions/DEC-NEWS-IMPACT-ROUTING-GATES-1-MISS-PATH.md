---
key: NEWS-IMPACT-ROUTING-GATES-1-MISS-PATH
question: >
  The pre-registered validation of the frozen routing gates ni-routing-gates-1 (seed
  20261017) found 32 of 40 gated-in cases on-event, two short of the 34 of 40 bar, and an
  estimated real-event drop share of 0.155, inside the 0.20 bar
  (DSC:NEWS-IMPACT-ROUTING-GATES-1-VALIDATION). T3 is weak under the gates and the 8-K
  frame holds far fewer on-event cases than 600. What does the continuation do with the
  gates, and how does it reach a validated gate set?
answer: >
  (1) NOT ACCEPTED AS A GUARANTEE. ni-routing-gates-1 is not accepted as an on-event
  guarantee. It stays in the draw (tape_draw --gate-frame) as an efficiency filter, because
  it raises the on-event rate from 0.375 to 0.80 at an estimated real-event cost of 0.155.
  (2) PER-CASE ROUTING VERDICT. Every scored continuation case carries its own routing
  verdict in a seat verdict file, gated in or not. This enforces item (5) of
  DEC:NEWS-IMPACT-CONTINUATION-ROUTING-GATES: scoring counts MATCH cases only.
  (3) GATES-2, FROZEN BEFORE A FRESH VALIDATION. A revised gate set targets the failure
  kinds the validation found: a product sense of "offering" under T1, a launch of
  something other than a product under T3, the market report, quote page and solicitation
  shapes G1 missed, a body event that differs from the headline's, and G3 cutting T2
  events worded outside the family pattern. It is frozen in a commit before a validation
  sample is drawn on a fresh seed from pool cases no card has shown, under the same bars
  (MATCH at least 34 of 40 gated in; drop share 0.20 or less).
  (4) T3 SHORTFALL PRINTED. T3 cannot reach 200 on 8-K bodies. The frame widens inside the
  existing owners (DEC:NEWS-IMPACT-CONTINUATION-ROUTING-GATES item 7), and T3's shortfall
  is printed rather than filled with off-event cases.
  (5) SECOND AUDITOR WHEN A LANE OPENS. The seat wrote the gates and audited them. When a
  labeling lane is available, an independent auditor classes the same 60 cards, and the
  DSC falsifier decides whether this ruling stands.
rationale: >
  A miss of two cases on a pre-registered bar is still a miss, and accepting it would
  teach every later bar that it bends. The gates are also clearly useful: 0.80 against
  0.375, with no wrong-issuer case surviving them. Keeping them as a filter while requiring
  a per-case verdict costs one routing read per scored case and keeps the on-event-only
  scoring rule honest. The failure kinds are specific enough to target, so a revision is
  cheaper than a redesign. A fresh seed on uncarded cases is the only validation the
  revision cannot have been fitted to, since the seat has now read all 60 gated cards and
  the 43 training cards.
alternatives:
  - option: Accept ni-routing-gates-1 as passing because 34 sits inside the Wilson interval.
    why_not: >
      The bar was fixed on the count, not the interval, before any card was read. Moving
      it after the result is the failure pre-registration exists to stop.
  - option: Drop the gates and go back to the ungated draw.
    why_not: >
      The ungated draw is 0.375 on-event. Labeling it would spend most of the third
      family's budget on off-event cases.
  - option: Revise the gates and re-score the same 60 cards.
    why_not: >
      The seat has read those cards. A revision checked on them is fitted to them and
      proves nothing about the pool.
  - option: Fill T3 to 200 by relaxing G3 for T3.
    why_not: >
      3 of 6 gated-out T3 cases are real events no attached 8-K reports. Relaxing G3
      admits off-event cases; it does not find T3 bodies.
  - option: Add a news-body vendor for T3.
    why_not: >
      DEC:NEWS-IMPACT-BENCHMARK-BODY-SOURCE settles bodies on issuer 8-Ks through the
      existing SEC owners, and masterplan §13 forbids new source licenses.
evidence:
  - "results_w2/audit/gate_validation.json gated_in: MATCH 32, NO_EVENT 5, OTHER_EVENT 3, WRONG_ISSUER 0; verdict MISS against MATCH >= 34 of 40."
  - "results_w2/audit/gate_validation.json gated_out: MATCH 3, NO_EVENT 6, OTHER_EVENT 6, WRONG_ISSUER 5; real_events_dropped share 0.155, bound [0.054, 0.351]; verdict PASS against share <= 0.2."
  - "results_w2/audit/gate_validation.json classes_by_gate_code: g3_no_family_language MATCH 3, NO_EVENT 2, OTHER_EVENT 3."
  - "results_w2/audit/gate_validation.json pool: 235 body-available, 43 training excluded, 192 pool, 97 gated in, 95 gated out."
  - "results_w2/audit/routing_check.json: ungated MATCH 15 of 40 (0.375)."
affects:
  - "WS:PROPHET-NEWS-IMPACT"
  - "engine/news_impact/routing_gates.py"
  - "engine/news_impact/tape_draw.py"
  - "research/prophet_v4/news_to_business_impact_20261006/benchmark/**"
confidence: medium
reversibility: easy
decided_by: "fable-meta-ceo-seat-0e739467 (recovered fork 959095da) under the Chairman delegation of 2026-10-10"
decided_at: 2026-10-14
---

# Routing gates 1 missed its bar: keep it as a filter, revise, revalidate fresh

ni-routing-gates-1 stays in the draw as a filter, not a guarantee, and every scored case
keeps its own routing verdict. A revised gate set aimed at the found failure kinds is
frozen before a fresh-seed validation on uncarded cases, under the same bars. T3's
shortfall on 8-K bodies is printed, and a second auditor re-reads the 60 cards when a lane
opens.
