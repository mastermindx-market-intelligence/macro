---
key: NEWS-IMPACT-W2-ROUTING-MOSTLY-OFF-EVENT
claim: >
  Most cases in the w2 graded draw do not pair a material issuer event with a filing that
  reports it. In a 40-case sample of the 157 (seed 20261016), 15 are MATCH (0.375, Wilson
  95% [0.242, 0.530]) and 25 are not (0.625, [0.470, 0.758]): 15 NO_EVENT (commentary,
  market reports, a list, a quote page, a solicitation), 7 WRONG_ISSUER (another company,
  a partner or a private company as the subject, a name collision, a one-letter ticker, a
  common-word ticker) and 3 OTHER_EVENT (a real event with no attached filing about it).
  The template is not the fault in any of the three malformed-audit cases (M3
  OTHER_EVENT, M7 NO_EVENT, M9 WRONG_ISSUER); the failures sit in event detection, issuer
  resolution and body attachment. Three code-only flags (no template-family pattern in
  the body, issuer absent from the headline, a T1 or T3 case whose only qualifying item
  is 2.02) together flag 20 of 40 with precision 0.85 and recall 0.68, and the cases they
  let through are still 12 of 20 MATCH. Of the 10 sampled slots where both families
  agreed on a present value, 4 sit on cases that are not MATCH.
falsifier: >
  An independent routing audit of a fresh sample of the same 157 cases, under the same
  four class definitions, finding MATCH at 0.6 or above; or a re-read of the 43
  committed verdicts that moves 8 or more of the 25 non-MATCH cases to MATCH.
so_what: >
  The w2 labels measure extraction from the attached 8-K, not the headline's event, and
  only about 59 of the 157 cases (38 to 83 at the interval ends) are on-event. The 600-case
  continuation needs gates in the draw before any labeling, and the code-only flags are
  too weak to be those gates on their own (DEC:NEWS-IMPACT-CONTINUATION-ROUTING-GATES).
  Two-family agreement says the families read the same filing the same way; it does not
  say the filing is the event (scope note on
  DSC:NEWS-IMPACT-TWO-FAMILY-AGREEMENT-PREDICTS-CORRECTNESS).
kind: data
verified_at: 2026-10-14
verified_by: >
  PYTHONPATH=. python3.11 results_w2/tools/build_routing_check.py SCRATCH_W2 BENCH OUT
  results_w2/audit/routing_verdicts.json reproduces results_w2/audit/sample_routing.json
  (sha256 718916f5…) and results_w2/audit/routing_check.json (sha256 43ae79bc…) byte for
  byte; verdicts results_w2/audit/routing_verdicts.json (sha256 24fdb18c…), seat read of
  the 43 routing cards, 2026-10-14.
scope:
  - "research/prophet_v4/news_to_business_impact_20261006/benchmark/results_w2/**"
  - "engine/news_impact/tape_draw.py"
confidence: probable
---

# The w2 graded draw is mostly off-event

25 of 40 sampled cases pair no material issuer event with a filing that reports it. The
template was never the fault; the draw's event detection, issuer resolution and body
attachment were. The w2 labels stand, read as extraction from the attached filing.
