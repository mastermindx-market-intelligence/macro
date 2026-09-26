---
key: VISIBLE-TURN-PROJECTION-IS-THE-EXISTING-READ-SEAM
claim: >
  The authorized visible content for Executive dialogue is the EXISTING
  `control_plane/visible_turn_projection.py:419` `VisibleTurnProjection.read` (real cursors, dual
  ordering, retention, upsert-correction, viewer-grant revocation). At Mastermind
  `8ba7deedde164c90298d3e88785d98e02fa5e2d2` it is an IN-PROCESS HOT WINDOW with
  `MAX_VIEWERS = 2` that explicitly "is not history", reachable only from
  `codex_operator_adapter.py:685`, and no MCP tool, service handler or HTTP route exposes it. The
  bounded mission/root/child observation is a separate `control_plane/executive_dialogue_observation.py:1685`
  `read_canonical_terminal_wake`, already consumed by `chairman_control_room.py:1572`. The
  missing contract for any UI to read this content is an out-of-process AUTHORIZED READ RESOURCE
  over the EXISTING projection, not a second transcript store.
falsifier: >
  At the then-current protected Mastermind master, run a runnable read that would flip the claim.
  Any ONE of the following flips it: (a) `git grep -n 'VisibleTurnProjection.read' master` resolving
  to a different path or line than `control_plane/visible_turn_projection.py:419`; (b) `git grep -n
  'read_canonical_terminal_wake' master` resolving to a different path or line than
  `control_plane/executive_dialogue_observation.py:1685`; (c) `MAX_VIEWERS` no longer equals `2` in
  `control_plane/visible_turn_projection.py`; (d) `git grep -nE 'mcp\\.|@router\\.|@app\\.\\(get\\|post\\).*visible_turn|@tool\\(|FastAPI\\(|http\\.route' master control_plane/` returning
  an MCP tool, FastAPI/ASGI handler, or HTTP route that exposes the projection out-of-process.
  Discovery of any MCP/service/HTTP route exposing the projection out-of-process is itself the
  falsification result.
so_what: >
  A future session needing UI-visible Executive dialogue content builds a read resource over the
  EXISTING `VisibleTurnProjection` and takes the retention and viewer-budget decisions to Sol —
  never stands up a second transcript store. Treat `MAX_VIEWERS = 2` and the explicit "is not
  history" framing as binding on every read seam built on top of this projection. The read-seam
  retention and viewer-budget choice are Sol's, not this record's. The secondary gap — frozen
  `DISPATCH_STATES` distinguishing RETURNED from DELIVERY_UNCONSUMED but carrying no
  company-"accepted" token — is now DECIDED and no longer open: no accepted token is added to the
  frozen transport vocabulary; acceptance is a separate source-qualified facet owned elsewhere, and a
  missing value renders `NOT_PROJECTED` (product decision recorded 2026-09-16 under
  `WS:CHAIRMAN-CONTROL-ROOM`, cross-referenced from
  `agentos/handoffs/EXECUTIVE-CAPACITY-FABRIC-2026-09-16-POST-7181-FOLD.md` §7). The retention and
  viewer-budget half remains Sol's.
kind: architecture
verified_at: 2026-09-16
verified_by: >
  Mastermind `8ba7deedde164c90298d3e88785d98e02fa5e2d2`. Anchors:
  `git grep -n 'VisibleTurnProjection.read' origin/master` (the production anchor at
  `control_plane/visible_turn_projection.py:419`); `git grep -n 'read_canonical_terminal_wake'
  origin/master` (the consumption anchor at `control_plane/executive_dialogue_observation.py:1685`,
  with `chairman_control_room.py:1572` as the known consumer); `git show origin/master:control_plane/visible_turn_projection.py`
  read for `MAX_VIEWERS = 2` and the explicit "is not history" framing; `git grep -nE
  'mcp\.|@router\.|@app\.(get|post).*visible_turn|@tool\(|FastAPI\(|http\.route' origin/master control_plane/`
  read for any out-of-process exposure. Verified by the seat on 2026-09-16 (sha256[:12]
  `8c44a0671291`, ~/.claude/projects/-Users-chriswong-Documents-Cluade-Macro-Dashboard/handoff_kits/meta-ceo-b-2026-09-08/orch/fabric/OS_INTAKE_OBSERVATION_CENSUS.md, line carrying `VERDICT: BOTH
  PRODUCERS EXIST AND ARE UNCONTESTED AT 8ba7deed`). No MCP tool, service handler or HTTP route
  exposes the projection out-of-process at this pin.
scope:
  - mastermind
confidence: verified
---

## Evidence

The Executive dialogue has two distinct authorized visible surfaces at
`8ba7deedde164c90298d3e88785d98e02fa5e2d2`, both uncontested at that pin:

1. **Bounded mission/root/child observation.**
   `control_plane/executive_dialogue_observation.py:1685` `read_canonical_terminal_wake` —
   already consumed by `chairman_control_room.py:1572`. This is the existing read for the
   Control Room surface.
2. **Authorized visible content.**
   `control_plane/visible_turn_projection.py:419` `VisibleTurnProjection.read` — real cursors,
   dual ordering, retention, upsert-correction, viewer-grant revocation. It is an IN-PROCESS
   HOT WINDOW with `MAX_VIEWERS = 2` and an explicit "is not history" framing. Reachable only
   from `codex_operator_adapter.py:685`; no MCP tool, service handler or HTTP route exposes
   it out-of-process at this pin.

## Gap

A UI cannot reach either surface today: the first is consumed by `chairman_control_room.py`,
and the second is in-process only. The missing contract is therefore not a new transcript
store. It is an out-of-process AUTHORIZED READ RESOURCE over the EXISTING
`VisibleTurnProjection`, plus an owner decision on retention and viewer budget. Both
decisions are Sol's, not this record's.

A secondary gap is named for completeness: frozen `DISPATCH_STATES` distinguishes RETURNED
from DELIVERY_UNCONSUMED but has no company-"accepted" token. This is a separate admission
gate and is not closed by building the read resource above.