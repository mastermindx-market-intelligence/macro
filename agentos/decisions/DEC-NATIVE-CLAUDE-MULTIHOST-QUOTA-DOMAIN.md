---
key: NATIVE-CLAUDE-MULTIHOST-QUOTA-DOMAIN
question: >
  When one direct Claude subscription is executable from multiple Macs, how should Provider Control
  represent shared quota/cooling versus host-local native health while preserving current generation
  owners and the accepted CF2 production claim path?
answer: >
  Preserve `(host_ref, capability_id)` executable slot identity and the incumbent production CF2 join.
  Macro Shared AI Provider Control owns one opaque `capacity_capability_id + capability_generation`
  for the logical provider quota domain. Each host-local native custody extends the existing
  provider-realm owner's `realm_generation`, keyed by `host_ref + capacity_capability_id`; no new
  `binding_generation` exists. Protected `CapacityOwnerFact.generation`, exposed by the subscription
  canary as `capacity_generation`, remains a canary Capacity/Model Router fact and is not provider
  identity or the production CF2 claim contract. Production B5 joins Provider Capacity V2 with boot-bound provider-realm/readiness evidence at
  `(host_ref, capacity_capability_id)`, verifies provider and realm generations, then separately
  consumes current FP1B host/boot/pool qualification plus fresh capacity/pressure evidence before the
  existing Executive atomic claim/ResourceBroker BEGIN path. Provider-domain quota/cooling applies to all current host realms only
  when source scope proves it; host-local failures remain local. Host rows are never summed for quota.
rationale: >
  Protected Mastermind already has separate provider-realm and canary-Capacity generations, and current
  usage of `CapacityOwnerFact` is confined to its owner/mint seam, subscription canary admission and
  tests. Accepted CF2-F separately freezes the real production architecture as strict Macro capacity
  snapshot plus realm-local readiness joined at `(host_ref, capacity_capability_id)` and atomically
  recorded in claim evidence. Reusing `capacity_generation` for Macro provider identity, adding a
  `binding_generation`, or routing production B5 through the canary fact would each duplicate or
  overload a canonical owner. The corrected model also lets M1/M6/Studio replicas add execution
  locality without pretending one Max login creates multiplied entitlement.
alternatives:
  - option: Give each host replica a new capability/account id
    why_not: Duplicates one provider quota domain and invites quota double-counting/cooling divergence.
  - option: Introduce binding_generation beside existing realm_generation
    why_not: Protected provider-realm receipts already own the local enrollment correction epoch.
  - option: Call Macro provider-domain epoch capacity_generation
    why_not: Protected Mastermind already uses that name for CapacityOwnerFact generation in canary admission.
  - option: Use CapacityOwnerFact as the production V2 placement bridge
    why_not: >
      It is not the accepted CF2 production claim path. Promoting it would create a parallel placement
      evidence contract and collapse worker canary state with provider-capacity truth.
  - option: Sum host rows because slot identity includes host_ref
    why_not: Host is an execution coordinate, not proof of independent provider entitlement.
  - option: Keep a per-row capacity_independence boolean
    why_not: Independence is relational and an unqualified boolean can be misused as additive quota.
evidence:
  - "Capacity F0: slot identity is `(host_ref, capability_id)` and provider/account capacity is observed on a host."
  - "Protected `ProviderRealmEnrollmentReceipt` owns sealed generation consumed as `realm_generation`."
  - "Protected `CapacityOwnerFact` owns a separate generation consumed by subscription canary admission as `capacity_generation`."
  - "Protected code search places CapacityOwnerFact only in its fact/mint seam, canary admission and tests—not the accepted CF2 claim path."
  - "Accepted CF2-F freezes strict Macro Provider Capacity + realm-local readiness -> `(host_ref, capacity_capability_id)` join -> existing atomic claim evidence."
  - "Current Macro capability_manifest.v1 is a metabolism secret-reference broker, not a native attached-login registration registry."
affects:
  - WS:EXECUTIVE-CAPACITY-FABRIC
  - shared-ai-provider-control
  - mastermind/OCR-2C
  - mastermind/PF1
  - mastermind/MH1
confidence: high
reversibility: costly
decided_by: ceo-sol
decided_at: 2026-09-15
---

## Consequences

Family-B producer/consumer schemas use `capability_generation` for the Provider-Control logical quota
domain and incumbent `realm_generation` for one host/principal/config enrollment. Existing canary
`capacity_generation` keeps its current meaning and gains no production placement authority.

Native V2 `realm_binding` carries `capability_generation`, `boot_ref`, `realm_generation` and the enrollment
receipt. `boot_ref` is readiness provenance only; ordinary reboot advances neither provider nor realm generation. The earlier candidate `binding_generation` and `capacity_independence` fields are superseded.

B1 native provider-domain registration is secret-free under `shared-ai-provider-control`; the
metabolism `capability_manifest.v1` secret-ref registry is not reused as an account/domain registry.

B5 extends the existing CF2 source acquisition, `(host_ref, capacity_capability_id)` join, deterministic
selection and atomic claim evidence with Provider Capacity V2 generation/realm/boot provenance, while
separately consuming incumbent FP1B evidence, requiring byte-exact `host_ref == host_id` and `boot_ref == boot_id`, current `capacity_pool_ref`/qualification, and fresh physical evidence. It does not
route production placement through `CapacityOwnerFact`. Historical replay returns the provider and
physical evidence accepted at the original claim without current provider or physical reread. A
versioned subscription canary admission may later bind the new provenance for a canary only if needed.

Provider Control retains evidence scope so provider-domain usage-limit can cool all replicas while a
host-local binary/auth/transport/recovery defect cannot poison healthy replicas by default. No Claude
adapter owns propagation or quota deduplication.

The first four-account canary stays one-realm-per-domain. Multi-host replication is later. This
records-only decision creates no registration, credential, provider call, host realm, claim or runtime capability.