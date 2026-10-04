---
key: OPTIONS-ALPHA-CANDIDATE-FEED-V2-SOURCE-ONLY
question: >
  How can the Options Alpha candidate core preserve first lawful formations when
  caller-supplied availability and publication clocks cannot prove durability or
  remote publication?
answer: >
  Add inactive policy v2 and a source-only feed core. Formation uses the actual
  composer decision clock, freezes physical campaign and microstructure evidence,
  retains every historically lawfully formed candidate through degraded recovery,
  and separates current revision and disposition. A strict future publication
  receipt binds exact payload bytes and R2 metadata; its first consumer clock is
  external metadata and pure validators never claim provider effects. No v1 live
  identity is migrated and no publisher, activation, capture, fit, or trade path
  is added.
rationale: >
  Caller-supplied available and published timestamps conflate observation with
  unproven storage and network effects. Dropping a candidate when later evidence
  is missing or stale destroys the first receipt that proved formation. Reusing
  the canonical campaign verifier and retaining immutable formation prefixes
  preserves the existing architecture while making durability and publication a
  separately receipted IO concern.
alternatives:
  - option: Continue v1 caller clocks and repair their ordering only
    why_not: >
      Better ordering still treats assertions as effects and keeps publication
      claims inside a source-only artifact.
  - option: Persist a candidate ledger before publication
    why_not: >
      Creates a second lifecycle store despite the canonical campaign ledger and
      bounded derived payload already carrying the necessary history.
  - option: Let Terminal infer first publication from served_at
    why_not: >
      Request time is not object publication time and cannot preserve the first
      consumer clock across overwrites.
evidence:
  - "PR #8310 review at a15ba9ae77826bf6a1d6fcb40022b6816b705e43 found current-final versus frozen-formation replay breakage."
  - "research/options_estate/options_alpha_candidate_formation_policy_v1.json remains unchanged."
  - "META-CEO ruling dated 2026-10-03 commissioned source-only v2 and superseded unlaunched receipt packets."
affects:
  - "WS:OPTIONS-ALPHA-INTELLIGENCE-RECOVERY"
  - "contracts/options/options.alpha_candidate_formation_policy.v2.schema.json"
  - "contracts/options/options.alpha_candidate_feed.v2.schema.json"
  - "contracts/options/options.alpha_candidate_feed_publication_receipt.v1.schema.json"
  - "engine/options_alpha_candidate_feed.py"
confidence: high
reversibility: costly
decided_by: meta-ceo
decided_at: 2026-10-03
---

Policy v2 is registered inactive. Activation still requires the same four exact
prerequisites and the next NYSE boundary. The four real proofs, publication, and
Terminal consumption remain root-owned release gates.
