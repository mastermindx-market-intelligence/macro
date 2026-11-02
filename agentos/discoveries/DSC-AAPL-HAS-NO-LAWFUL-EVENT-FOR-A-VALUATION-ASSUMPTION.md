---
key: AAPL-HAS-NO-LAWFUL-EVENT-FOR-A-VALUATION-ASSUMPTION
claim: >
  AAPL — the only issuer V1 valuation is pinned to — has no event in this repo that can
  lawfully propose a valuation-assumption change: its five chronicle events are all
  `earnings`, whose sole numeric payload is EPS measured against a CONSENSUS estimate
  (rights-blocked by DEC:F07-VALUATION-SOURCE-IS-SEC-COMPANYFACTS-V1) and whose
  `links.source` is null; its capital-structure classified spine has zero AAPL events;
  and `data/edgar/guidance_hits.parquet` has zero AAPL rows. Separately, `earnings` —
  12,208 of 14,816 chronicle rows (82%) — is absent from
  engine/valuation_event_bridge.py's closed class map entirely, so the merged B-F07-3
  bridge resolves to null for AAPL and the panel's only line was the false
  "No filing on file yet for this company."
falsifier: >
  python3 -c "from engine import valuation_assumptions as va; print(va.latest_issuer_spine_event_class('AAPL'))"
  returning a non-None class, or a non-empty AAPL slice of
  data/edgar/guidance_hits.parquet, or an `earnings` key appearing in
  engine.valuation_event_proposal.EVENT_TO_ASSUMPTION.
so_what: >
  Do not commission "wire event X to AAPL's valuation" expecting a numeric delta — the
  correct AAPL outcome is a TYPED ABSTENTION, and a session that treats abstention as
  failure will either invent a number or declare the lane blocked. Use a guidance-hit
  issuer (CTVA/ATI/ETN/TER/PTC) to exercise the positive path. Needs python3.12: the
  capital_structure import pins bytecode digests and fails closed on 3.14.
kind: data
verified_at: 2026-09-22
verified_by: "engine.valuation_assumptions.latest_issuer_spine_event_class + data/chronicle/events.jsonl + data/edgar/guidance_hits.parquet reads; PR claude/f07-event-assumption-proposal"
scope:
  - macro
  - engine/valuation_event_bridge.py
  - engine/valuation_event_proposal.py
  - F07 lane
confidence: verified
---

The five AAPL chronicle rows are quarterly earnings dated 2025-07-31 through 2026-07-30,
each carrying one fact of the shape `Jun 2025 · EPS 1.57 · est 1.42 · surprise +10.6%`.
The `est` and `surprise` legs are consensus-derived, which is exactly what the F07 source
ruling forbids as a valuation input, so the only forward-looking content AAPL has is the
one class of content the product may not use.
