---
key: EXECUTIVE-PROVENANCE-GATE-IS-SCHEMA-ONLY
claim: >
  The Executive CEO provenance gate is SCHEMA-ONLY: in Mastermind
  `control_plane/executive_runtime.py:928-942`, `_has_executive_provenance(provenance, target="ceo")`
  returns True whenever `provenance["schema"] == "mastermind.ceo_intent.v1"` — it reads the actor and
  discards it, unlike the chairman branch, which checks schema AND actor — while the single mutation
  sink `control_plane/ceo_intent.submit_intent` (`ceo_intent.py:731-735`) stamps exactly that schema on
  EVERY admitted v1 intent regardless of actor. A stamp obtained by a non-CEO principal therefore
  admits `owner_seat="ceo"` Jobs (and `escalation_target="ceo"`, and child Jobs), while
  `owner_seat="chairman"` is refused.
falsifier: >
  On protected Mastermind master `320f586126b7c82c843ef17612f12d40d20a42e0`,
  `python3 -c "from control_plane.executive_runtime import _has_executive_provenance;
  print(_has_executive_provenance({'schema': 'mastermind.ceo_intent.v1', 'actor':
  'svc-site-maintenance'}, target='ceo'))"` printing `False` refutes the claim. A second read that
  refutes it: `sed -n '928,942p' control_plane/executive_runtime.py` showing the `ceo` branch no longer
  keyed on `provenance["schema"]` alone, i.e. having gained an actor check like the chairman branch.
so_what: >
  An actor-aware CEO branch — the A2 slice, owned by `executive_runtime.py` and colliding with open
  Mastermind PR #699 — is a SECURITY PREREQUISITE before any non-CEO principal is armed beyond
  READ/RESEARCH, and the A1 module's restraint does not substitute for it: because the A1 module never
  passes a seat, ITS Jobs stay `coo`, but the hole is stamp REUSE by any later runtime holder, not the
  module's own call sites. Two further consequences: do not plan the fix in a non-owner carrier (the
  A1 carrier #804 could not fix it by fence, its owned file is `executive_service_principal.py`), and do
  not treat the sink's `v2` schema (`mastermind.ceo_intent.v2`) as the alternative seam — `v2` admits
  the actor as a full `executive_coo_cycle` but carries no typed provenance and no `task_kind`.
kind: landmine
verified_at: 2026-09-18
verified_by: >
  Mastermind PR #804 head `3b5182e2545cab671f2da2db6735b51c926baf18` (passing
  `tests/test_executive_service_principal.py`, `tests/test_ceo_intent.py` and the D8 scanner test), a
  2026-09-18 reproduction on a temporary runtime by a NON-AUTHOR reviewer, and reads of
  `control_plane/executive_runtime.py:928-942` and `control_plane/ceo_intent.py:731-735`.
scope:
  - mastermind
  - control_plane/executive_runtime.py
  - control_plane/ceo_intent.py
  - control_plane/executive_service_principal.py
confidence: verified
---

# The CEO door checks the envelope, not the sender

A Job in the Executive runtime is admitted to CEO ownership through
`_has_executive_provenance(provenance, target="ceo")`. Read at `320f5861`, that function's CEO branch
asks one question: is `provenance["schema"] == "mastermind.ceo_intent.v1"`? The `actor` field is
present, readable and ignored. The sibling chairman branch does the opposite — it checks the schema
AND the actor — which is why the same stamp that opens the CEO door is refused at the chairman door.

That would be survivable if the schema were hard to obtain. It is not. `provenance` is minted at the
single mutation sink `control_plane/ceo_intent.submit_intent`, and the sink stamps
`mastermind.ceo_intent.v1` on every intent it admits, whoever the actor was. The schema is therefore a
property of the ENVELOPE FORMAT, not of the sender.

## What was actually reproduced

Reproduced 2026-09-18 on a temporary runtime by a non-author reviewer, and pinned by passing tests in
Mastermind PR #804:

1. The non-CEO service principal `svc-site-maintenance` (owner_seat `coo`, READ/RESEARCH only) submits
   a Job through the sink and receives a durable provenance stamp.
2. Replaying that stamp — `create_job(owner_seat="ceo", provenance=<stamp>)` — is ADMITTED. So is
   `escalation_target="ceo"`, and so are child Jobs.
3. The same stamp aimed at `owner_seat="chairman"` is REFUSED, because only the chairman branch
   consults the actor.

The blast radius is bounded by who holds the runtime, not by who holds CEO intent. The A1 module
(`control_plane/executive_service_principal.py`) never passes a seat, so the Jobs IT creates stay
`coo` — but the module is a restraint on its own call sites, not a fence on the stamp. Any later
runtime holder that obtains one admitted v1 intent can mint durable CEO-owned work.

## Two things not to try

**Do not fix it from the A1 carrier.** PR #804 could not close this by fence: the defect lives in
`executive_runtime.py`, which that PR does not own. The fix is A2's, and A2 collides with open PR #699
on the same file, so A2 is a coordination act, not a green-field edit.

**Do not use the v2 schema as the seam.** `mastermind.ceo_intent.v2` admits the actor as a full
`executive_coo_cycle`, which looks like the actor-awareness this claim asks for, but it carries no
typed provenance and no `task_kind`. It is a different admission path, not a stronger CEO gate.

Confidence is `verified` for the reproduction and the cited reads. The behavioral consequence for any
NOT-YET-ARMED principal remains a property of the current protected master, and the falsifier above is
what re-testing it costs.
