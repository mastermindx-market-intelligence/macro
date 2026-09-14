---
key: W6C2-RUNTIME-ORDER-BLOCKS-GROK-RETURN
claim: >
  Mastermind PR #615 exact head 8e9a8f62c84fcb4234c67f26fe3cbc479030a763
  still admits impossible or stale consultation receipt facts: INTENT-only restart is
  classified EFFECT_UNKNOWN, NATIVE_ACCEPTED does not require DISPATCH_ATTEMPT,
  dispatch accepts a changed/stale frame without rebinding it to stored INTENT/current
  RuntimeBinding, and recipient consumption can credit the same stale frame.
falsifier: >
  Inspect the current protected/PR-head control_plane/consultation_runtime.py and run
  fail-first discriminators proving: INTENT-only remains not dispatched; native acceptance
  requires an exact prior dispatch; dispatch and recipient consumption bind to stored
  consultation identity and revalidate the current recipient; sticky EFFECT_UNKNOWN begins
  only after an actual unsettled dispatch. A newer exact head with those controls and green
  current CI supersedes this discovery.
so_what: >
  W6-C2 remains the critical-path blocker for Grok Operations and any later Workspace
  consultation return. Do not implement or activate Grok return, helper, Wake promotion,
  or operational-principal waves against the current draft interface. Repair #615 on its
  existing carrier, then re-review the exact new head before downstream source binds to it.
kind: architecture
verified_at: 2026-09-14
verified_by: >
  Direct source read of mastermind:control_plane/consultation_runtime.py at
  8e9a8f62c84fcb4234c67f26fe3cbc479030a763; Mastermind PR #615 review
  5195521810 submitted as REQUEST_CHANGES on that exact head; current PR metadata and
  hosted CI state read on 2026-09-14.
scope:
  - mastermind
  - "mastermind:control_plane/consultation_runtime.py"
  - "mastermind:tests/test_w6c2_consultation_runtime.py"
  - "mastermind:pull/615"
  - "mastermind:pull/624"
confidence: verified
expires: 2026-09-21
---

## Exact blocking behavior

1. `resolve_restart()` checks for INTENT and then returns `EFFECT_UNKNOWN` when no
   terminal dispatch state exists, without first requiring a persisted
   `DISPATCH_ATTEMPT`. An INTENT-only state has crossed no external effect boundary.
2. `native_accepted()` delegates order checking to `_require_fact_order()`, whose current
   implementation checks only for INTENT. It therefore does not enforce the required
   `INTENT -> DISPATCH_ATTEMPT -> NATIVE_ACCEPTED` order.
3. `dispatch_attempt()` finds a stored INTENT but does not compare the supplied frame's
   semantic fingerprint, actors, evidence digest or binding to that INTENT and does not
   revalidate the current recipient immediately before the effect boundary.
4. `consumed_by_recipient()` checks native thread/turn IDs but neither binds the supplied
   frame to the stored INTENT/native binding nor revalidates current RuntimeBinding before
   awarding semantic recipient consumption.

These are capability-truth and effect-safety defects. A fluent answer, passing happy-path
test, or provider/native success cannot repair the stored receipt order after the fact.

## Same-carrier repair boundary

The existing #615 writer should add fail-first tests for the four exact states, preserve
one canonical Executive event plane and all frozen W6-C budgets/names, repair ordering and
binding checks without creating another adapter/store, update the PR body to one immutable
head, and return current focused/importer/isolated-entrypoint/hosted evidence.

Protected Mastermind movement to
`d07689b7737f324c16b142d03bffc89cdcf7a27d` changes only two C1 trusted-team/security
records relative to #615's source base. It is path-disjoint from the seven W6-C2 files and
does not waive these runtime blockers. The proportional-security ruling does confirm Grok
is an approved team principal; it does not grant consultation receipt or provider authority.

## Continuation

The first downstream source waves remain the versioned `grok-bot` consultation identity and
provider-free Grok Wake adapter with transport disabled, as specified in Mastermind PR #624.
They begin only after the current #615 blockers are closed and the W6-C2 interface is
protected or explicitly superseded.
