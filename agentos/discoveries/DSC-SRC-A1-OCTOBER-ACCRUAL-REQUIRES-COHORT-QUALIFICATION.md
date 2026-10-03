---
key: SRC-A1-OCTOBER-ACCRUAL-REQUIRES-COHORT-QUALIFICATION
claim: >
  At Macro ff420e6841a2468e4b718340cff240abbef114f1, SRC-A1 retains
  473200 observations and 8583 attempts, including 27 known August 26
  empty-consensus defects and substantial exercised re-observation lineage,
  while semantic identity, basis and use remain unresolved.
falsifier: >
  Run python3 research/alpha_intelligence/expectation_market_dynamics/information_to_price_audit.py
  --as-of 2026-10-03T06:31:51Z --repo . --revision ff420e6841a2468e4b718340cff240abbef114f1
  --git-observations-path data/revisions/expectation_observations.parquet
  --git-attempts-path data/revisions/expectation_attempts.parquet and compare the
  reported input SHA-256 values, row counts and integrity reasons.
so_what: >
  Resume the existing K3E SRC-A1 owner acceptance audit using qualified
  post-repair cohorts and actual producer receipts. Do not rebuild a new
  Information-to-Price owner, treat long-form rows as independent episodes,
  rewrite historical defects, infer absent metadata, or advance EXP-1 from
  the raw row count. The August claim that no re-observations exist is stale.
kind: data
verified_at: 2026-10-03
verified_by: >
  python3 research/alpha_intelligence/expectation_market_dynamics/information_to_price_audit.py
  at ff420e6841a2468e4b718340cff240abbef114f1;
  research/alpha_intelligence/expectation_market_dynamics/VERIFICATION_AND_NEXT_GATE_2026-10-03.md;
  Macro #8309
scope:
  - research/alpha_intelligence/expectation_market_dynamics/
  - collectors/equity_revisions.py
  - data/revisions/expectation_observations.parquet
  - data/revisions/expectation_attempts.parquet
confidence: verified
---

# Current source accrual changes the next action

The executed report is
`research/alpha_intelligence/expectation_market_dynamics/INFORMATION_TO_PRICE_AUDIT_2026-10-03.json`,
SHA-256 `9191e344d4d10b211a66ccb22f5b5a0a07aa2180aaa2b0ddb08503239a704e36`.
It retains all supplied rows and reports independent partitions and nonexclusive
reasons. Its 400482 structurally eligible rows and 66860 central rows with
declared capture support are not historical-availability, rights or economic
eligibility certifications.

All 27 empty-consensus measurement defects belong to the pre-repair C2
cohort, for BRK-B, COKE and CRVL. The literal zero covering counts remain valid.
No later cohort violates that specific criterion. The immutable source history
must not be rewritten to make the diagnostic green.

Native body witnesses now exist for unchanged observations, changed-value
supersession, partial-after-good preservation, fiscal rollover and repeated
raw-horizon shape. The current verification receipt distinguishes selected
field checks, full-row retention checks, source-run bindings and still-missing
acceptance evidence. A session hash is a consistency binding, not independent
attestation; run-level success and unrelated job failure are both inadequate
substitutes for examining the actual source component.

This evidence updates source knowledge without promoting the collector.
K3E remains the existing derived semantics owner; MAS-119 retains common
expectation-baseline federation and existing DRL/residual owners retain
residual computation. No predictive or portfolio authority is created.
