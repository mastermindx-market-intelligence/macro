---
key: NEWS-IMPACT-CONTINUATION-ROUTING-GATES
question: >
  The w2 routing check (seed 20261016, 40 of the 157 graded cases plus the three cases
  behind malformed cards M3, M7 and M9) found 25 of 40 cases off-event: 15 headlines with
  no issuer event, 7 resolved to the wrong issuer and 3 real events whose attached filing
  reports something else (DSC:NEWS-IMPACT-W2-ROUTING-MOSTLY-OFF-EVENT). The template was
  not the fault in any motivating case. What happens to the accepted w2 results, and what
  must the draw do before the 600-case continuation labels anything?
answer: >
  (1) W2 STANDS, NARROWED. The w2 labels, audits and summary.json are not re-scored or
  redrawn. Their reading is narrowed to extraction from the attached 8-K; no w2 figure is
  read as event-level recall or accuracy.
  (2) THREE DRAW GATES BEFORE LABELING. The continuation draw adds, in this order: a
  non-event headline filter (commentary, market reports, lists, quote pages,
  solicitations); an issuer-resolution guard (one-letter and common-word tickers, name
  collisions with private companies, and headlines whose subject is a partner or another
  company); and a body-to-event match that keeps a case only when an attached filing
  reports the headline's event. The gate rules and their code are frozen in a commit
  before any validation sample is drawn.
  (3) PRE-REGISTERED VALIDATION. On a fresh seed 20261017, 40 gated-in cases are classed
  under the four routing-check classes; the gates are accepted when MATCH is at least 34
  of 40. A gated-out audit of about 20 cases prints the share of real events the gates
  dropped, with a bar of 0.20 or less; a miss is printed, not hidden.
  (4) REJECTS ARE GOLD. Gated-out non-events and wrong-issuer cases are kept as labelled
  reject material for routing recall and reject-audit miss rate. Routing labels live in a
  seat verdict file, because label_return.v1 has no routing_label field; routing_label is
  a next-contract-version candidate and the v1 contracts stay byte-frozen.
  (5) SCORING ON-EVENT ONLY. Critical-numeric scoring of the continuation counts only
  cases classed MATCH. For w2 that population is about 59 of 157 (38 to 83) and is printed
  wherever a w2 figure is cited next to a continuation figure.
  (6) THIRD FAMILY ON GATED-IN CASES. The GLM third family (after 2026-10-19 05:16Z, under
  prompt-v1.2) labels the disputed slots of gated-in cases only.
  (7) WIDER FRAME, SAME OWNERS. To reach 600 the source frame is widened inside the
  existing owners (engine/news_events.py, the event ledger and the SEC body owners). No
  new vendor and no second EDGAR client.
rationale: >
  A two-family agreement figure on a filing about something else is a measurement of
  reading, not of the event, and 4 of the 10 sampled agreed-present slots were exactly
  that. The three failure classes map one to one onto three draw steps, so each gets its
  own gate. The code-only flags reach precision 0.85 but recall 0.68 and leave 8 of 25
  off-event cases through, so they can feed a gate but cannot be one. Freezing the gates
  before the validation draw keeps the 34 of 40 bar honest, and the gated-out audit
  prices what the gates cost in lost events. Keeping rejects as gold turns the draw's
  failure into the reject set the routing-quality metrics in endpoints.v1 need.
alternatives:
  - option: Re-score w2 on the MATCH cases now.
    why_not: >
      Only 43 cases carry a routing verdict, so a re-score would rest on 15 MATCH cases
      and replace an accepted result with a thinner one. The narrowed reading costs
      nothing and the continuation measures on-event cases properly.
  - option: Discard non-events and wrong-issuer cases from the draw.
    why_not: >
      They are the only labelled material for routing recall and the reject-audit miss
      rate, both of which endpoints.v1 names.
  - option: Rely on two-family agreement to screen off-event cases.
    why_not: >
      Families agree on what the attached filing says; 4 of 10 agreed-present slots in
      the sample sat on off-event cases.
  - option: Fix only the template regex.
    why_not: >
      The template was right in all three motivating cases. The faults are in event
      detection, issuer resolution and body attachment.
  - option: Add a news-body vendor to find on-event text.
    why_not: >
      DEC:NEWS-IMPACT-BENCHMARK-BODY-SOURCE settles bodies on issuer 8-Ks through the
      existing SEC owners, and masterplan §13 forbids new source licenses.
evidence:
  - "results_w2/audit/routing_check.json: class counts MATCH 15, NO_EVENT 15, WRONG_ISSUER 7, OTHER_EVENT 3; non_match 0.625 [0.470, 0.758]."
  - "results_w2/audit/routing_check.json flags_vs_verdicts: any_flag precision 0.85, recall 0.68, 8 missed; population flag rate 0.446."
  - "results_w2/audit/routing_check.json slot_classes_by_verdict: agree_present slots MATCH 6, NO_EVENT 2, WRONG_ISSUER 2."
  - "results_w2/audit/routing_verdicts.json: M3 OTHER_EVENT, M7 NO_EVENT, M9 WRONG_ISSUER."
  - "contracts/news_impact/label_return.v1.schema.json: no routing_label field; contracts/news_impact/endpoints.v1.json routing_quality metrics are qa_only and need a gold routing label."
affects:
  - "WS:PROPHET-NEWS-IMPACT"
  - "engine/news_impact/tape_draw.py"
  - "research/prophet_v4/news_to_business_impact_20261006/benchmark/**"
confidence: medium
reversibility: easy
decided_by: "fable-meta-ceo-seat-0e739467 (recovered fork 959095da) under the Chairman delegation of 2026-10-10"
decided_at: 2026-10-14
---

# Routing gates before the 600-case continuation

The w2 results stand, read as extraction from the attached filing. The continuation draw
gets three frozen gates (non-event filter, issuer guard, body-to-event match), validated
on seed 20261017 against a 34 of 40 MATCH bar and a printed gated-out loss rate. Rejects
are kept as gold, scoring counts on-event cases only, and the third family labels gated-in
cases only.
