---
key: STEWARD-ATTENTION-JOIN-DROPS-REAL-EXECUTIVE-DEMAND
claim: >
  The protected Executive Steward's `get_attention()` returns `QueryStatus.DEGRADED` with
  `data == ()` when an attention obligation has no exactly-joining Agent OS responsibility: the
  obligation is reported as a typed `attention_responsibility_unknown` issue and dropped from the
  returned rows. That is correct for the Steward, which refuses to guess an identity. It is fatal
  for any attention consumer that reads only `.data`: verified against the Control Room's own
  fixture sources, two genuine obligations existed — including `eia-bbbbbbbbbbbb`, a
  `ceo_decision_pending` targeting the CEO seat — and the consumer saw zero. A live CEO decision
  disappeared entirely, with no interrupt, no card and no omission receipt. Separately, F0G section
  17 states the corrected Steward carries a known presentation-filtering integrity defect that
  gates A1 integration; that statement is STALE against the protected bytes at merge
  `dcce6f7ab6efad360f4854d748ad0d65dc9e0f7c`, which group complete canonical identity families
  BEFORE presentation filtering and pin the behaviour with ten regression tests in
  `tests/test_executive_steward_filter_integrity.py`.
falsifier: >
  Falsify by showing that `ExecutiveStewardSnapshot.get_attention()` returns an obligation whose
  `responsibility_ref` matches no `ResponsibilityFact`, or that some other protected owner
  independently republishes such obligations so no consumer can lose them. Re-run
  `python3 -m pytest tests/test_executive_steward.py tests/test_executive_steward_filter_integrity.py`
  in Mastermind and construct a snapshot with an unjoinable `AttentionFact`. To falsify the second
  half, exhibit a filter-before-grouping path still present in `control_plane/executive_steward.py`
  at the protected merge.
so_what: >
  An attention consumer must admit from the caller-supplied obligation facts and consume the
  resolver's verdict ALONGSIDE them, never INSTEAD of them. An unjoinable or identity-conflicted
  obligation is admitted and marked BLOCKED with a typed reason, never deleted; a conflicted
  identity yields authority UNKNOWN rather than a trusted seat claim, so authority still never
  defaults upward. `DEGRADED` plus an empty `data` is not an empty desk. Because the section 17
  defect is already repaired, the A1/A2 integration gate it describes is clear on current protected
  bytes and should be amended rather than treated as blocking.
verified_at: 2026-09-20
verified_by: >
  Direct execution against the protected Mastermind Steward at merge
  dcce6f7ab6efad360f4854d748ad0d65dc9e0f7c: constructed an ExecutiveStewardSnapshot from the
  Control Room's own fixtures in tests/test_chairman_control_room.py and observed
  get_attention() return status=degraded with data=() while snapshot.attention held two genuine
  obligations (eia-aaaaaaaaaaaa job_failed/coo and eia-bbbbbbbbbbbb ceo_decision_pending/ceo).
  Repaired in control_plane/executive_attention_shadow.py and re-verified: both obligations now
  admitted and rendered BLOCKED with typed reasons. The F0G section 17 staleness was verified by
  reading control_plane/executive_steward.py list_responsibilities/get_attention at the protected
  merge (group-before-filter) and running
  `python3 -m pytest tests/test_executive_steward_filter_integrity.py` (10 passed).
scope:
  - WS:EXECUTIVE-ATTENTION-ECONOMICS
  - mastermind:control_plane/executive_steward.py
  - mastermind:control_plane/executive_attention_shadow.py
  - mastermind:research/MASTERMIND_EXECUTIVE_ATTENTION_ECONOMICS_F0G_CONSOLIDATED_V1_CONTRACT_2026-08-30.md
confidence: verified
kind: constraint
---

Verified 2026-09-20 against Mastermind `dcce6f7ab6efad360f4854d748ad0d65dc9e0f7c` (Steward, PR #228)
and the Control Room fixtures in `tests/test_chairman_control_room.py`. Implemented in
`control_plane/executive_attention_shadow.py`.
