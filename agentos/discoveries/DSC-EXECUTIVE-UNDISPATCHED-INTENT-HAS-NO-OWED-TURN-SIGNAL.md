---
key: EXECUTIVE-UNDISPATCHED-INTENT-HAS-NO-OWED-TURN-SIGNAL
claim: >
  On Mastermind #950 head 145c42d2 (derive_work_producers_v1 wired into the workspace work read),
  a freshly submitted CEO intent that has not been dispatched to any worker projects in the
  autonomy control room with owed_turn.seat "unknown" (reason no_owed_turn_signal),
  placement_state not_observable/no_canonical_producer, current_worker None and
  is_actionable False, so the joined work-queue row for that root is honestly UNKNOWN with
  reason no_producer for accountability, placement and effects. The producers only populate once a
  dispatched attempt exists on the installed E1 composition; the joined-fixture proof therefore
  pins the boundary, not a populated row.
falsifier: >
  control_plane/autonomy_control_room_projection.py emitting an owed_turn seat other than
  "unknown" for a root with zero attempts; or tests/test_workspace_work_joined.py asserting a
  populated next_actor for an undispatched intent and passing.
so_what: >
  A populated Work row is proof of E1 execution, not of projection wiring: do not read an empty
  producer as a projection bug, and do not fake a producer at the edge to make the row look
  live. The first populated row must come from a real dispatched attempt after the ruled
  install and readiness path.
kind: runtime
verified_at: 2026-09-24
verified_by: >
  Fable delivery principal, 2026-09-24 07:5xZ, scratch reproduction diag_joined_card.py over a
  real Runtime and the real autonomy projection at #950 head 145c42d2
  (control_plane/autonomy_control_room_projection.py:823-836 worker presence vs owed turn,
  :1678 qualified_at, :1731-1738 presentation gate; control_plane/work_queue_projection.py
  derive_work_producers_v1 eligibility); joined proof committed in
  tests/test_workspace_work_joined.py on that branch.
scope:
  - Mastermind
  - agent-fabric-end-to-end-fable-integration-20260913-sol-001
  - control_plane/work_queue_projection.py
  - control_plane/autonomy_control_room_projection.py
confidence: verified
---

# An undispatched intent carries no owed-turn signal, so its Work row is honestly empty

The producer wiring is correct and the row stays `no_producer` because the control room has
nothing to say about a job no worker has touched. Populated rows need a real dispatched attempt.
