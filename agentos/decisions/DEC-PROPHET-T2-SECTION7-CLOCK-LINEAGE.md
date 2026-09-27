---
key: PROPHET-T2-SECTION7-CLOCK-LINEAGE
question: May a genuine T2 event precede the independent section-7 hold/formation anchor without changing
  either date or breaking later corrections?
answer: New reversed T2 records preserve both dates only with closed producer-derived temporal_lineage
  validated by the existing integrity owner and bound to immutable plan clocks. Origination, correction,
  forward-ledger and index projections reuse that relation. Legacy/unbound records retain conservative
  checks; correction allowlists cannot add or rewrite lineage, identity or geometry.
rationale: The real EBAY/PG/CPRI source replay proves an independent September-11 T2 event and September-14
  section-7 hold anchor. The original consumers incorrectly assumed both dates described one event.
alternatives:
- option: Clamp event or formation date
  why_not: Fabricates recency or changes immutable identity meaning.
- option: Delete formation ordering globally
  why_not: Silently upgrades unbound historical and other-tier records.
- option: Change only origination
  why_not: The existing later-correction reader would still reject a valid unrelated annotation.
affects:
- WS:PROPHET-US-ENTRY-TIMING
- engine/prophet_integrity.py
- engine/prophet_bridge.py
- scripts/build_prophet.py
evidence:
- '#7180 comments 5710341615, 5710423319, 5711161027'
- research/us_prophet_availability/2026-09-17-independent-t2-clocks/actual-board-proof.json
confidence: high
reversibility: costly
decided_by: ceo-sol
decided_at: '2026-09-17'
---

Candidate source ruling under current Chairman continuation, not permission to merge, activate or publish an unreviewed branch. The evidence object is a structural projection, not a new authentication plane. Existing source/plan receipts still carry authenticity. Full new-session product acceptance remains owed.
