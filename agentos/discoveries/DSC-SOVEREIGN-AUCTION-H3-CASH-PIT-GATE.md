---
key: SOVEREIGN-AUCTION-H3-CASH-PIT-GATE
claim: >
  The retained October 6 2026 funding case cannot supply an ex-ante private-auction
  settlement cash predictor: all 12 audited official captures are ineligible at the
  stated S-minus-one cutoff and the certified net private cash value remains null.
falsifier: >
  Produce independently retained, source-qualified receipts available by that same
  cutoff and a complete matching private proceeds/redemptions/funded-buyback inventory
  with SOMA treatment, units and cohort provenance. Run `python3
  research/sovereign_auction_pressure/funding_audit/outcome_blind_funding_audit.py --check`
  against the retained receipt manifest to challenge the recorded eligibility verdict.
so_what: >
  Keep H3 INSUFFICIENT_PIT. Preserve the accounting reconciliation as descriptive evidence,
  acquire the missing qualified inputs and baseline vintages before registering execution,
  and never substitute aggregate par debt or TGA change for net private auction cash.
kind: data
verified_at: 2026-10-08
verified_by: >
  python3 research/sovereign_auction_pressure/funding_audit/outcome_blind_funding_audit.py --check;
  OUTCOME_BLIND_FUNDING_VERIFICATION.json; OUTCOME_BLIND_FUNDING_CASEBOOK.json
  SHA256 f64acecce2414726448fcfc9214431ce782cbb8090283e4b96af4c09606b544d.
scope:
  - WS:RATES-INFLATION-COMMAND
  - sovereign-auction-pressure/H3
  - macro/collectors/treasury_auctions.py
  - macro/engine/treasury_auction_primitives.py
confidence: verified
---

The October 6 descriptive accounting separates bill par net USD11,035m, marketable
debt accounting USD11,258m, a restricted discount/indexation adjustment USD9,025m,
broader public-debt cash net USD10,998m and TGA change USD2,079m. These are different
universes. The USD9,025m inference is expressly not certified private cash.

H1–H5 design adoption does not declare a completed statistical registration, a new
out-of-sample result or a running prospective epoch. Existing SLF-006 NO-GO, D2 FAIL
and Terminal confirmation/exit-modulation KILL remain operative evidence.
