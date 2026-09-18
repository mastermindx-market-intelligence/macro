---
key: EXECUTIVE-RECEIPTS-HAVE-NO-ANTI-REPLAY-BINDING
claim: >
  Executive OS sealed state receipts carry no epoch or anti-replay binding, so restoring a
  matched (config, receipt) pair from a backup silently reverses a later legitimate DISARM -
  architecture-wide and inherited, not a W1-H3 regression.
falsifier: >
  Run the CEO-submit flow on the in-repo FakeCeoSubmitHost at Mastermind PR #677 head
  6dc2ea83: execute_ceo_submit_arm -> snapshot (control_config, receipt) -> execute_ceo_submit_disarm
  -> restore both snapshots byte-for-byte -> main(["ceo-submit-status","--expected-sha",SHA]).
  The discovery is DISPROVED if that readback returns CEO_SUBMIT_DISARMED or
  CEO_SUBMIT_ARMED_UNBOUND, or exits non-zero. Observed at this head: CEO_SUBMIT_ARMED, exit 0,
  writes=(0,0,0). Equivalently, disproved if a future receipt binds a monotonic counter,
  nonce, or freshness window that a restored pair cannot satisfy.
so_what: >
  A future session must not treat "the sealed receipt binds the transaction-produced state" as
  implying "the state was produced by a transaction in the current epoch". Any DR/backup restore
  of the Executive config root can silently re-grant CEO-submit authority that was deliberately
  removed, with no adversary and no tampering. W1-H4 must not assume receipt presence proves a
  live, current grant, and the DR runbook must treat config-root restore as an authority-changing
  operation requiring an explicit post-restore re-attestation, not a neutral recovery step.
  This is NOT to be repaired inside W1-H3; it needs its own architecture adjudication because the
  COO autonomy receipt shares the property and a fix touches both domains.
kind: architecture
verified_at: 2026-09-16
verified_by: >
  Mastermind PR #677 head 6dc2ea83bc738c2532745ef71dcde6c170c58d91; read-only probe
  sha256 1c01bfdc7ae7d058cbe319dbdf33bbc504250c24ad0c689342b0e24f3346c5e6 against a clean
  `git archive` export; published as PR #677 comment 5706016890.
scope:
  - mastermind/ops/executive_os/autonomy_control.py
  - mastermind/ops/executive_os/DR_RUNBOOK.md
  - mastermind/control_plane/executive_service.py
  - WS:EXECUTIVE-CAPACITY-FABRIC
confidence: verified
---

## Status

`OPEN / architecture-wide / NOT an H3 regression / separate adjudication owed.`

## Mechanism

`validate_ceo_submit_receipt_document()` checks `observed_at` for canonical FORMAT only - there is
no freshness window, no ordering constraint, and no comparison against any other durable fact.
`tool_version` is the static constant `"1.0.0"` in `control_plane/executive_autonomy.py:27` and is
not bumped per release, so it supplies no epoch either. Every remaining projection field is a
restatement of current evidence, which a restored pair satisfies by construction because the pair
was captured together and is internally consistent.

The COO autonomy receipt (`autonomy-state-v1.json`) has the same shape and the same property.
That is why this is recorded as inherited architecture rather than as a defect introduced by the
CEO-submit domain.

## Why it is filed separately from DEC:R81-AUTHORITY-VALIDATION-LAW

R81 closes the class where an artifact is minted in an UNAUTHORIZED state. This discovery is the
adjacent case where the artifact was legitimately produced in an AUTHORIZED state and is simply
replayed into a later epoch. R81's scoped laws do not close it: a restored pair genuinely satisfies
every authority invariant asserted from current evidence. Closing it requires an epoch or
anti-replay binding, which is an architecture change across both receipt domains and therefore its
own decision.
