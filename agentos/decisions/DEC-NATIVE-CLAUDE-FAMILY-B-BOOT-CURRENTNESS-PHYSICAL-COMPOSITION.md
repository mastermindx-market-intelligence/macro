---
key: NATIVE-CLAUDE-FAMILY-B-BOOT-CURRENTNESS-PHYSICAL-COMPOSITION
question: >
  How must Family B prevent pre-reboot native readiness from remaining eligible after FP1B advances
  the host to a new boot/pool qualification, without turning boot identity into provider enrollment
  or creating another physical-resource authority?
answer: >
  Keep B2 enrollment stable across ordinary reboot. Bind B3/B4 readiness and the native observation
  to exact current boot_ref, and carry boot_ref in Provider Capacity V2 only as readiness provenance.
  At B5, separately consume incumbent FP1B host qualification and fresh host-capacity/pressure evidence;
  require byte-exact host_ref==host_id and boot_ref==boot_id plus current capacity_pool_ref and
  qualification_revision before the existing claim/ResourceBroker BEGIN path. Bind provider and
  physical evidence separately. Old-boot readiness becomes ineligible for new execution; reboot does
  not advance capability_generation or realm_generation. Physical failures stay host-local, and
  historical replay does not reread current physical state. Add no host sampler, policy, store,
  receipt owner, scheduler, generation, transaction or claim plane.
rationale: >
  Protected FP1B qualifies an exact host/boot/pool generation and refuses wrong host, stale boot, wrong
  pool, stale/incomplete host capacity and mismatched BEGIN pressure. Pending Family-B records carried
  host_ref and realm_generation but omitted boot_ref from B3/B4 and did not require the FP1B result at
  B5, so structurally valid pre-reboot readiness could survive a physical-generation change. The
  correction composes the existing owners rather than duplicating either one.
alternatives:
  - option: Advance realm_generation on every reboot
    why_not: Reboot changes physical readiness, not provider enrollment/custody, and would overload the incumbent realm owner.
  - option: Put boot_ref into B2 enrollment identity
    why_not: It would make a stable enrollment churn on every reboot and confuse physical generation with credential/config custody.
  - option: Let Provider Capacity boot_ref authorize physical admission
    why_not: Macro is provider-capacity authority, not FP1B host qualification or ResourceBroker authority.
  - option: Add a Family-B host qualification receipt/store
    why_not: FP1B already owns host_id, boot_id, capacity_pool_ref, qualification_revision and fresh physical evidence.
  - option: Reread current physical state during historical replay
    why_not: Replay must return accepted historical evidence and cannot rewrite an old placement with current host state.
evidence:
  - "Mastermind@5ee11ab1e993616f3568cfca4069cb21fa61fd8f control_plane/executive_physical_resources.py: FP1B host qualification binds host_id, boot_id, capacity_pool_ref and qualification_revision and validates fresh host-capacity/pressure evidence."
  - "Mastermind #662@4ea5ce6ae56d45bb90ff5dbcd4dc5f8896830eeb: B3/B4/B5 records omitted boot_ref and FP1B composition before this correction."
  - "Macro #7162@a43596c0d7a2428dc9d68bc79256a8068af9165d: observation, realm_binding and B5 claim records omitted boot currentness before this correction."
affects:
  - WS:EXECUTIVE-CAPACITY-FABRIC
  - shared-ai-provider-control
  - mastermind/OCR-2C
  - mastermind/FP1B
confidence: high
reversibility: costly
decided_by: ceo-sol
decided_at: 2026-09-16
---

## Candidate precedence and gate

This decision and paired Mastermind correction supersede only conflicting boot-currentness and physical-composition clauses in pending Family-B records. B0 remains records-only `SPEC_ONLY / HOLD`. The existing R2 review operation stays PRE_START until replacement exact heads have fresh hosted checks and current-base/material compatibility. B1+ remains unstarted.

## Frozen composition

```text
B2 enrollment key = (host_ref, capacity_capability_id, realm_generation)
B3/B4 current readiness = enrollment key + boot_ref
B5 = Provider Capacity V2/readiness AND incumbent FP1B qualification/evidence
```

B5 requires exact host/boot equality with FP1B, current pool/qualification identity and fresh capacity/pressure evidence. Provider Capacity carries no physical grant. FP1B carries no provider quota/domain authority. Both are consumed by their existing claim/BEGIN owners.

## No effect

This decision creates no provider registration, login, realm enrollment, observation adapter, Capacity snapshot, physical qualification, claim, RuntimeBinding, Worker, host/browser effect, Ready transition or merge authority.
