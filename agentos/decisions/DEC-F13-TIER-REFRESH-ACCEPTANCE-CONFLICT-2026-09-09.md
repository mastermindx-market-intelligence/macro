---
key: F13-TIER-REFRESH-ACCEPTANCE-CONFLICT-2026-09-09
type: decision
status: active
workstream: MARKET-OS
question: >
  B-F13-B5-1's acceptance sentence on MO-PAID-057 asks that a PRO-tier refresh
  measurably complete first and be logged. The merged F13 product spec
  (macro#6919) refused a tier-differentiated refresh as a source scheduler
  banned by the F13 do_not_redo. Does the build go ahead, or is the
  acceptance test in conflict with a ruling that already landed?
answer: >
  HOLD the B-F13-B5-1 build. The acceptance test conflicts with the merged
  spec. Rewrite the acceptance test to a measurable PRO-first checkpoint on
  an existing PRO-exclusive surface, or record refusal under #6919. No tier
  scheduler is built. MO-PAID-057's next_bounded_child carries that one
  sentence; no other cell on the row moves.
rationale: >
  The merged product spec research/MARKET_ONTOLOGY_F13_PRODUCT_SPECS_057_058_2026-09-06.md
  (macro#6919) states, verbatim: The tier-differentiated refresh in the ledger
  row is REFUSED. A priority queue over .github/workflows/daily.yml is a
  source scheduler, banned by the F13 do_not_redo. Selling a faster refresh
  also manufactures the false-green danger_areas failure — a paying user
  believing their data is fresher than it is. The census packet for
  B-F13-B5-1 (records_queue/specs/B-F13-B5-1_priority_tier_refresh.md,
  §BLOCKER 1-2) asked for a PRO-exclusive nightly-built surface that would
  let a PRO refresh complete first; no such surface exists. Building a
  tier scheduler to satisfy the ledger sentence would violate a do_not_redo
  that already landed. Holding the build and rewriting the sentence (or
  recording the refusal on the row) is the only path that does not fight
  #6919.
alternatives:
  - option: "Build a PRO-first refresh scheduler anyway, because the ledger acceptance sentence still asks for it."
    why_not: "A priority queue over daily.yml is the source scheduler the merged spec refused and the F13 do_not_redo bans. The ledger sentence is the thing in conflict, not a licence to override a landed refusal."
  - option: "Close MO-PAID-057 as REJECTED_BY_DESIGN in this packet."
    why_not: "Seat ruling R9 is record-only on next_bounded_child. Changing disposition or state here would exceed the ruled columns for this row and would pre-empt the rewrite-or-refuse choice the child is being asked to make."
evidence:
  - "research/MARKET_ONTOLOGY_F13_PRODUCT_SPECS_057_058_2026-09-06.md §A2, macro#6919: 'The tier-differentiated refresh in the ledger row is REFUSED. A priority queue over `.github/workflows/daily.yml` is a source scheduler, banned by the F13 `do_not_redo`.'"
  - "Census / spec research records_queue/specs/B-F13-B5-1_priority_tier_refresh.md §BLOCKER 1-2: no PRO-exclusive nightly-built surface exists to anchor 'a PRO refresh completes first'."
  - "MO-PAID-057 acceptance_test: 'a PRO-tier refresh measurably completes first, logged'; real_producer: nightly pipeline with no priority tiers."
affects:
  - "MO-PAID-057"
  - "B-F13-B5-1 (held)"
  - "WS:MARKET-OS"
confidence: high
reversibility: costly
decided_by: "Meta-CEO B successor seat, harness session d640f3ef, under DEC:CHAIRMAN-OVERRIDE-CLAUDE-META-CEO-REGIME-2026-09-06"
decided_at: 2026-09-09
review_by: 2026-12-09
related:
  - "DEC:CHAIRMAN-OVERRIDE-CLAUDE-META-CEO-REGIME-2026-09-06"
  - "WS:MARKET-OS"
---

B-F13-B5-1 is held. The merged F13 product spec (macro#6919) refused a
tier-differentiated refresh as a source scheduler banned by the F13
do_not_redo. Quote, verbatim from that spec: **The tier-differentiated refresh
in the ledger row is REFUSED.** The census packet asked for a PRO-exclusive
nightly-built surface that would let a PRO refresh complete first; no such
surface exists. Rewrite the acceptance test, or record the refusal under
#6919. No tier scheduler is built.
