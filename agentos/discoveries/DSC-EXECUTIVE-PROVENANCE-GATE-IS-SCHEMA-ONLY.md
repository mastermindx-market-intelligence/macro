---
key: EXECUTIVE-PROVENANCE-GATE-IS-SCHEMA-ONLY
claim: >
  The Executive CEO provenance gate remains SCHEMA-ONLY for RAW
  `mastermind.ceo_intent.v1` stamps: in Mastermind
  `control_plane/executive_runtime.py:928-942`, `_has_executive_provenance(provenance, target="ceo")`
  returns True whenever `provenance["schema"] == "mastermind.ceo_intent.v1"` — it reads the actor and
  discards it, unlike the chairman branch, which checks schema AND actor. Mastermind #804 A2
  (repaired head `4c4139b2`) now stamps service Jobs with
  `mastermind.executive_service_intent.v1` on the existing `ceo_intent.submit_intent` sink; that
  service schema does NOT satisfy the schema-only CEO branch
  (`create_job(owner_seat="ceo"|"chairman", provenance=service_stamp)` → StateConflict), reproduced
  and pinned by tests. The residual hole is confined to CEO-origin v1 stamps and stays owned by
  `executive_runtime.py` / open PR #699. The sink still stamps RAW v1 on every admitted CEO-origin
  v1 intent regardless of actor, so a RAW v1 stamp still admits `owner_seat="ceo"` work.
falsifier: >
  On protected Mastermind master `320f586126b7c82c843ef17612f12d40d20a42e0`,
  `python3 -c "from control_plane.executive_runtime import _has_executive_provenance;
  print(_has_executive_provenance({'schema': 'mastermind.ceo_intent.v1', 'actor':
  'svc-site-maintenance'}, target='ceo'))"` printing `False` refutes the claim. A second read that
  refutes it: `sed -n '928,942p' control_plane/executive_runtime.py` showing the `ceo` branch no longer
  keyed on `provenance["schema"]` alone, i.e. having gained an actor check like the chairman branch.
so_what: >
  The service-intent schema on the existing sink closes the A1 path's own stamp (service Jobs no
  longer mint a CEO-admitting envelope), but it does NOT close the CEO-origin RAW-v1 hole. An
  actor-aware CEO branch — still owned by `executive_runtime.py` and colliding with open Mastermind
  PR #699 — remains a SECURITY PREREQUISITE before any holder of a RAW v1 stamp is treated as safe,
  and a future session must not "fix" that residual from a non-#699 PR (including #804). Do not
  broaden `executive_inbox.ceo_intent_provenance`. Do not let a service intent use the v2
  orchestration branch — `mastermind.ceo_intent.v2` admits the actor as a full `executive_coo_cycle`
  and is misclassified as CEO-origin by the inbox reader. See
  `DEC:EXECUTIVE-SERVICE-INTENT-SCHEMA-ON-EXISTING-SINK`.
kind: landmine
verified_at: 2026-09-18
verified_by: >
  Mastermind PR #804 immutable repaired head `4c4139b2d30f78a3884c777b144aadf32bfc69ec`
  (A1 head `a2acae36` APPROVE + hosted CI `35328140960` SUCCESS; A2 tests
  `tests/test_executive_service_principal.py` 160 rows, `tests/test_ceo_intent.py` 66 collected,
  D8 scanner green; non-author R4 APPROVE), a 2026-09-18 reproduction that a service stamp is
  refused at `owner_seat="ceo"|"chairman"`, and reads of
  `control_plane/executive_runtime.py:928-942` and `control_plane/ceo_intent.py`. A2 hosted CI
  run `35331412994` was in progress at record time and is NOT claimed green.
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
runtime holder that obtains one admitted RAW v1 intent can mint durable CEO-owned work.

## Qualification (checkpoint 2, 2026-09-18 14:00Z)

Mastermind #804 A2 (immutable repaired head `4c4139b2d30f78a3884c777b144aadf32bfc69ec`) changed
the SERVICE path, not the CEO-origin RAW-v1 path. Service Jobs now stamp
`mastermind.executive_service_intent.v1` on the existing sink
(`DEC:EXECUTIVE-SERVICE-INTENT-SCHEMA-ON-EXISTING-SINK`). That schema does not satisfy the
schema-only CEO branch: `create_job(owner_seat="ceo"|"chairman", provenance=service_stamp)`
raises StateConflict. The refusal is reproduced and pinned by tests on that head. CEO v1/v2
bytes are unchanged.

The original claim therefore still holds for RAW `mastermind.ceo_intent.v1` stamps and is
narrowed for service work: a service principal no longer obtains a CEO-admitting envelope
from the sink. The residual is confined to CEO-origin v1 stamps and stays owned by
`executive_runtime.py` / open PR #699. The falsifier on the RAW v1 stamp still stands.

## Two things not to try

**Do not fix the residual RAW-v1 hole from #804.** PR #804 owns the service schema on the existing
sink, not `executive_runtime.py`. The residual CEO-origin v1 gate is #699's, and it collides with
that open PR on the same file, so it is a coordination act, not a green-field edit.

**Do not use the v2 schema as the seam.** `mastermind.ceo_intent.v2` admits the actor as a full
`executive_coo_cycle`, which looks like the actor-awareness the residual hole asks for, but it
carries no typed provenance and no `task_kind` and is misclassified as CEO-origin by the inbox
reader. It is a different admission path, not a stronger CEO gate.

Confidence is `verified` for the RAW-v1 reproduction, the service-stamp refusal, and the cited
reads. The behavioral consequence for any holder of a RAW v1 stamp remains a property of the
current protected master, and the falsifier on that stamp is what re-testing it costs.
