---
key: MI-BUILDOUT-I-ROUTE-WAITS-FOR-ALL-FOUR-LEGS
question: >
  I1 §8 Q7 (Mastermind #1258 package I): is the I0 gate status OPEN_FOR_READ_ONLY_COMPOSITION
  sufficient to authorize building the §7 smallest slice, GET /api/integrated-answer/v1/{ticker},
  before any thesis mutation and before all four legs (H01/H04/H05/H06) are ACCEPTED?
answer: >
  No. The §7 route is not buildable until H04 and H06 carry acceptance records from their
  workstreams and H05 exists as an addressable read-only artifact. A read-only composition
  status cannot stand in for a leg that has no artifact to read.
rationale: >
  I1 §0 freezes "not buildable unless" all four legs are ACCEPTED, and the I0 census on main
  found H01 ACCEPTED, H04/H06 BUILT_NOT_ACCEPTED and H05 ABSENT (Capital-Structure W4/W6 still
  to do). A handler shipped today would compose a glance with a permanently refused leg — the
  "substitute root evades a hold" shape the package forbids — and would create a second answer
  surface that other owners must later reconcile. Thesis mutation stays separately gated on the
  Alpha Intelligence / event owner (I0 Q6). H05 ABSENT is a data/artifact absence, not an
  administrative block, so the Meta-CEO seat's authority to overrule administrative holds
  (Chairman 2026-10-06) does not reach it.
alternatives:
  - option: Build the §7 route now with H05 rendered as a permanent "unavailable" leg.
    why_not: Ships a composed answer whose contract can never be satisfied on today's main; the refused leg would read as product behaviour, not as a gate, and the route would become a de-facto second answer warehouse.
  - option: Build the route behind a feature flag and flip it when the legs are accepted.
    why_not: A flagged handler is still code on the render path for a product that has no accepted inputs; it invites "turn it on" pressure without the acceptance records I1 §0 requires, and the flag itself is the kind of parallel gate the package forbids.
evidence:
  - "research/product_intelligence_local_delivery/I0_INTEGRATED_ANSWER_GATE_CENSUS_2026-10-06.md (merged #8512 5dc3aaf93827): H01 ACCEPTED, H04 BUILT_NOT_ACCEPTED, H05 ABSENT, H06 BUILT_NOT_ACCEPTED"
  - "research/product_intelligence_local_delivery/I1_INTEGRATED_ANSWER_COMPOSITION_SPEC_2026-10-06.md (merged #8517 f1cd5d9cbd5f): §0 'not buildable unless' table, §7 smallest slice, §8 Q7 addressed to the Meta-CEO / package I seat"
  - "Mastermind #1258 package I text: no second canonical answer warehouse; no thesis mutation without owner acceptance"
affects:
  - WS:MARKET-INTELLIGENCE-INSTITUTIONAL-BUILDOUT
  - WS:CAPITAL-STRUCTURE-INTELLIGENCE-V2
  - WS:EARNINGS-INTELLIGENCE-OS
confidence: high
reversibility: easy
decided_by: "session fd47d431 (Fable Meta-CEO seat, Chairman handoff 2026-10-05 on Mastermind #1258)"
decided_at: 2026-10-06
---

Reopen when the I0 §0 table changes (an acceptance record for H04/H06, an H05 artifact on
main). The I0 census and the I1 spec are DO_NOT_REDO; the next act is a build packet against
the frozen I1 contract, not a new census.
