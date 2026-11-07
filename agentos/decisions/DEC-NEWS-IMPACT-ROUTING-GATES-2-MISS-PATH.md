---
key: NEWS-IMPACT-ROUTING-GATES-2-MISS-PATH
question: >
  The pre-registered fresh-seed validation of the frozen routing gates ni-routing-gates-2
  (seed 20261018) found 31 of 40 gated-in cases on-event against a bar of 34, and an
  estimated real-event drop share of 0.208 against a bar of 0.20: both bars missed
  (DSC:NEWS-IMPACT-ROUTING-GATES-2-VALIDATION). A paired comparison on the same pool, with
  its rule fixed before any of its cards was read, found gates-2 right on all 11 cases where
  the two gate sets disagree and gates-1 right on none. Which filter does the draw use, and
  does the gate line continue?
answer: >
  (1) NOT ACCEPTED AS A GUARANTEE. ni-routing-gates-2 is not accepted as an on-event
  guarantee, and neither is ni-routing-gates-1.
  (2) GATES-2 REPLACES GATES-1 AS THE DRAW FILTER. Under the paired rule (gates-2 when right
  on more disagreement cases, a tie keeps gates-1), the draw uses ni-routing-gates-2 through
  tape_draw --gate-frame. Gates-1 stays frozen at a8f98d21 and byte-reproducible; it is
  retired from the draw, not deleted.
  (3) PER-CASE ROUTING VERDICT STAYS. Every scored continuation case carries its own routing
  verdict in a seat verdict file, gated in or not (DEC:NEWS-IMPACT-ROUTING-GATES-1-MISS-PATH
  item 2). Scoring counts MATCH cases only.
  (4) NO FURTHER HEADLINE-GATE REVISION ON THIS POOL. After the two validations and the
  paired cards, 66 of the 132 pool cases remain uncarded and 15 of them are gated in under
  gates-2, too few for another 40-case gated-in sample. A gates-3 checked on cards the seat
  has read would be fitted to them. The dominant residual miss (commentary on a standing
  fact, 6 of 9) is the shape a gates-2 design probe showed could not be cut from the
  headline without dropping events. It is left to the per-case verdict.
  (5) THE NEXT LEVER IS THE FRAME. The frame widens inside the existing SEC owners
  (DEC:NEWS-IMPACT-CONTINUATION-ROUTING-GATES item 7), filing first: start from the issuer
  8-Ks in the window and attach the candidates that report them, using the candidate's seen
  date against the filing date to separate a preview from a report. Any new gate rule that
  comes out of that work is frozen and validated on cases from the widened frame no card
  has shown, under the same two bars.
  (6) T3 PRINTED AT ZERO. Gates-2 gates in no T3 case on 8-K bodies and none of the 6
  sampled gated-out T3 cases is on-event. T3's shortfall against 200 is printed, never
  filled with off-event cases.
  (7) SECOND AUDITOR WHEN A LANE OPENS. The seat wrote both gate sets and classed every
  card. When a labeling lane is available (GLM after 2026-10-19 05:16Z), an independent
  auditor classes the 60 gates-2 validation cards and the 11 disagreement cases, and the
  DSC falsifier decides whether this ruling stands.
rationale: >
  Gates-2 missed its gated-in bar by three cases and its drop bar by 0.008. Both are misses,
  and moving a bar after the result is what pre-registration forbids. The filter question is
  narrower and has a clean answer: cases where the two sets agree enter both draws alike, so
  the 11 disagreement cases decide the comparison exactly, and gates-2 wins all 11. A filter
  that is right more often is worth keeping even when neither is a guarantee. Another
  headline revision cannot be validated honestly on the remaining pool, and its main target
  is a shape the headline does not carry. The frame is the binding constraint for all three
  families anyway: the gated pool holds about 17 T1, 38 T2 and 0 T3 on-event cases against
  200 each.
alternatives:
  - option: Accept gates-2 as passing because 0.208 rounds to 0.2 and 34 sits inside the Wilson interval.
    why_not: >
      Both bars were fixed on the point value before any card was read. Bending them after
      the result is the failure pre-registration exists to stop.
  - option: Keep gates-1 in the draw because neither set passed.
    why_not: >
      Gates-2 is right on every case where the two disagree. Keeping the worse filter when
      both miss costs on-event cases and admits off-event ones.
  - option: Build gates-3 with a commentary rule and validate it on the 66 uncarded cases.
    why_not: >
      Only 15 of them are gated in, under half a 40-case sample, and a commentary rule cut
      in-sample events when it was probed during the gates-2 design.
  - option: Relax G3 for T3 so some T3 cases are gated in.
    why_not: >
      None of the 6 sampled gated-out T3 cases is on-event. Relaxing the gate admits
      off-event cases; it does not find T3 bodies.
  - option: Add a news-body vendor so T3 events are reported somewhere.
    why_not: >
      DEC:NEWS-IMPACT-BENCHMARK-BODY-SOURCE settles bodies on issuer 8-Ks through the
      existing SEC owners, and masterplan §13 forbids new source licenses.
evidence:
  - "results_w2/audit/gates2_validation.json gated_in: MATCH 31, NO_EVENT 8 (commentary 6, template_family_mismatch 2), OTHER_EVENT 1, WRONG_ISSUER 0; verdict MISS against MATCH >= 34 of 40."
  - "results_w2/audit/gates2_validation.json gated_out: MATCH 3, NO_EVENT 6, OTHER_EVENT 6, WRONG_ISSUER 5; real_events_dropped share 0.208, bound [0.074, 0.439]; verdict MISS against share <= 0.2."
  - "results_w2/audit/gates2_validation.json pool: 235 body-available, 103 carded excluded, 132 pool, 56 gated in (T1 19, T2 37, T3 0), 76 gated out (T1 24, T2 27, T3 25)."
  - "results_w2/audit/gates2_validation.json families: on-event estimate T1 17.2, T2 38.3, T3 0.0 against 200 each."
  - "results_w2/audit/gates_paired.json: pool cross-tab g1_in/g2_in 51, g1_in/g2_out 6, g1_out/g2_in 5, g1_out/g2_out 70; right gates_1 0, gates_2 11; filter_pick ni-routing-gates-2."
  - "results_w2/audit/gates_paired.json paired_cells: g1_out/g2_in MATCH 5, g1_in/g2_out NO_EVENT 3, g1_in/g2_out OTHER_EVENT 3."
affects:
  - "WS:PROPHET-NEWS-IMPACT"
  - "engine/news_impact/routing_gates_2.py"
  - "engine/news_impact/routing_gates.py"
  - "engine/news_impact/tape_draw.py"
  - "research/prophet_v4/news_to_business_impact_20261006/benchmark/**"
confidence: medium
reversibility: easy
decided_by: "fable-meta-ceo-seat-0e739467 (recovered fork 959095da) under the Chairman delegation of 2026-10-10"
decided_at: 2026-10-14
---

# Routing gates 2 missed both bars: it becomes the draw filter, and the gate line stops here

Neither gate set is an on-event guarantee, and every scored case keeps its own routing
verdict. Gates-2 replaces gates-1 in the draw because it is right on all 11 cases where
the two disagree. The pool is too thin to validate another headline revision, and the main
residual miss is a commentary shape the headline cannot separate, so the next lever is a
filing-first frame widening inside the existing SEC owners. T3 is printed at zero, and a
second auditor re-reads the cards when a lane opens.
