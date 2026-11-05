---
key: STEWARD-ATTENTION-JOIN-DROPS-REAL-EXECUTIVE-DEMAND
claim: >
  The September 20, 2026 reproduction constructed attention obligations
  from Control Room fixtures against protected Steward
  dcce6f7ab6efad360f4854d748ad0d65dc9e0f7c. The report observed
  get_attention() return DEGRADED with empty data for obligations without an
  exactly joining responsibility. A consumer reading only data therefore
  lost a fixture obligation modelling a CEO decision; this is not a verified
  production incident. The same report found that the protected Steward
  already grouped identity families before presentation filtering, contrary
  to the stale F0G section 17 integrity-gate description.
falsifier: >
  Falsify by showing that `ExecutiveStewardSnapshot.get_attention()` returns an obligation whose
  `responsibility_ref` matches no `ResponsibilityFact`, or that some other protected owner
  independently republishes such obligations so no consumer can lose them. Re-run
  `python3 -m pytest tests/test_executive_steward.py tests/test_executive_steward_filter_integrity.py`
  in Mastermind and construct a snapshot with an unjoinable `AttentionFact`. To falsify the second
  half, exhibit a filter-before-grouping path still present in `control_plane/executive_steward.py`
  at the protected merge.
so_what: >
  The #888 candidate admits caller-supplied obligation facts and consumes
  the resolver verdict alongside them, marking unresolved or conflicted
  obligations BLOCKED without granting authority. Its presence on an open
  draft branch does not establish protected or installed consumer behavior.
  Retain the fixture finding and source-law correction as dated evidence;
  complete current source and real-path acceptance through the existing
  carrier rather than inferring completion from the old report.
verified_at: 2026-09-20
verified_by: >
  Historical report at Macro #7517 head
  f239ba0aab29bde02e84230436bd394a82dd4f77 describes a fixture
  ExecutiveStewardSnapshot against protected
  dcce6f7ab6efad360f4854d748ad0d65dc9e0f7c: empty degraded query
  data despite two fixture obligations, including ceo_decision_pending.
  It reports candidate shadow repairs and ten passing
  test_executive_steward_filter_integrity.py tests. The November 5
  reconciliation verified source/custody references; those tests and the
  fixture reproduction were not freshly rerun.
scope:
  - WS:EXECUTIVE-ATTENTION-ECONOMICS
  - mastermind:control_plane/executive_steward.py
  - mastermind:control_plane/executive_attention_shadow.py
  - mastermind:research/MASTERMIND_EXECUTIVE_ATTENTION_ECONOMICS_F0G_CONSOLIDATED_V1_CONTRACT_2026-08-30.md
confidence: verified
kind: constraint
---

Verified 2026-09-20 against Mastermind `dcce6f7ab6efad360f4854d748ad0d65dc9e0f7c` (Steward, PR #228)
and the Control Room fixtures in `tests/test_chairman_control_room.py`, as reported
in the original dated candidate evidence.

## Source qualification — 2026-11-05

The shadow repair is present in the existing [Mastermind #888](https://github.com/mastermindx-market-intelligence/Mastermind/pull/888)
OPEN / Draft candidate at `ff147c8c1efdccf5608ce8414ff1b7e7c3be1cbd`, not in
protected Mastermind `49c2e1d93e5e080b1671c98087a845e5beb09dd5`.
No production incident, installed repair, new test execution or current EAF
acceptance is established by this records reconciliation.
