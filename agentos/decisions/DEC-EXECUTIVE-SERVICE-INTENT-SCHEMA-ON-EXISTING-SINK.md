---
key: EXECUTIVE-SERVICE-INTENT-SCHEMA-ON-EXISTING-SINK
question: >
  How does a non-CEO service principal obtain an admitted Executive Job without
  impersonating the CEO?
answer: >
  One strict non-CEO schema on the EXISTING `ceo_intent.submit_intent` sink —
  `mastermind.executive_service_intent.v1` (plus `RECEIPT_SCHEMA_SERVICE`) — on the
  non-v2 branch only. The typed block carries explicit `owner_seat="coo"` and
  `escalation_target="coo"`, a READ/RESEARCH ceiling enforced in the sink validator
  and in a belt check before `create_job`, `write_authorities=[]`, domain-separated
  intent ids (`svc-` prefix; keys = v1 + `principal_id` + `task_kind`), reserved
  actors refused, and no orchestration/binding. `executive_inbox.ceo_intent_provenance`
  is NOT broadened and stays CEO-only. The first service Job therefore needs no
  Runtime edit and no collision with Mastermind #699.
rationale: >
  Sol A2 correction 1789700503.345129: a service Job is admitted by a distinct
  envelope schema on the sink that already exists, not by teaching the Runtime to
  trust a non-CEO actor on the CEO schema, and not by opening a second writer.
  The schema-only CEO branch in `executive_runtime.py` still admits RAW
  `mastermind.ceo_intent.v1` stamps and discards the actor; stamping service work
  with a schema that branch does not accept (`create_job(owner_seat="ceo"|"chairman",
  provenance=service_stamp)` → StateConflict) confines the residual hole to
  CEO-origin v1 stamps, which stay owned by `executive_runtime.py` / #699. Reusing
  the CEO v2 path would admit the actor as a full `executive_coo_cycle` and be
  misclassified as CEO-origin by the inbox reader. A second Job writer or submit
  service is `duplicate_control_planes`.
alternatives:
  - option: Actor-aware Runtime gate first (widen `_has_executive_provenance` to consult actor on the CEO branch)
    why_not: owned by executive_runtime.py / open PR #699; unnecessary for coo/coo seats that the service schema already admits on the existing sink
  - option: Reuse the CEO v2 schema (mastermind.ceo_intent.v2) for service principals
    why_not: v2 admits the actor as a full executive_coo_cycle, carries no typed provenance and no task_kind, and is misclassified as CEO-origin by the inbox reader
  - option: A second Job writer or submit service beside ceo_intent.submit_intent
    why_not: duplicate_control_planes is a standing prohibition; the first service Job must land on the existing sink
evidence:
  - "Sol A2 correction 1789700503.345129 plus census 1789717957: INTENT_SCHEMA_SERVICE on the existing sink, non-v2 branch only"
  - "Mastermind PR #804 immutable repaired head 4c4139b2d30f78a3884c777b144aadf32bfc69ec (branch claude/executive-service-principal-20260918, DRAFT + HOLD body)"
  - "A1 head a2acae36 = APPROVE + hosted CI run 35328140960 SUCCESS; A2 hosted CI run 35331412994 in progress at record time (not claimed green)"
  - "Non-author review R4 APPROVE; tests/test_ceo_intent.py 66 collected; tests/test_executive_service_principal.py 160 rows; D8 scanner green"
  - "Service stamp does NOT satisfy the schema-only CEO branch — create_job(owner_seat=ceo|chairman, provenance=service_stamp) → StateConflict; CEO v1/v2 byte-identical"
  - "executive_inbox.ceo_intent_provenance untouched and pinned CEO-only"
affects:
  - "WS:EXECUTIVE-CAPACITY-FABRIC"
  - control_plane/ceo_intent.py
  - control_plane/executive_service_principal.py
  - control_plane/executive_inbox.py
confidence: high
reversibility: easy
decided_by: ceo-sol
decided_at: 2026-09-18
---

A non-CEO service principal gets an admitted Job by presenting a schema the CEO
door does not open, on the sink that already exists.

`INTENT_SCHEMA_SERVICE = "mastermind.executive_service_intent.v1"` (and
`RECEIPT_SCHEMA_SERVICE`) is added as a constant on `ceo_intent.submit_intent`.
The v2 orchestration branch is not used. `submit()` fails closed unless the
intent is ADMITTED. Effective authorities are `[READ, RESEARCH]`; write
authorities are empty; reserved actors are refused; `_provenance()` stores the
service schema plus evidence fields. The inbox reader's
`ceo_intent_provenance` helper is left CEO-only on purpose.

This is additive and removable: delete the service schema constant and the
service branch of the existing sink and the path is gone. It does not authorize
Ready/merge of Mastermind #804. That carrier stays DRAFT + HOLD until an
explicit Sol acceptance ruling. Residual RAW-v1 CEO-origin stamps remain
`executive_runtime.py` / #699 work, not this decision.
