---
key: NATIVE-CLAUDE-REALM-CAPACITY-FAMILY-B-V2
question: >
  After Family A refused unsafe equality between native Claude realms and numbered Macro OAuth slots,
  how should direct claude.ai Claude Code subscriptions acquire canonical provider-capacity identity,
  host-realm custody and production placement evidence without provider PII, secret fingerprints,
  ordinal guessing, quota multiplication or a second control plane?
answer: >
  Use Family B with incumbent owners. Macro Shared AI Provider Control owns one opaque
  `capacity_capability_id + capability_generation` per logical native provider-capability/quota domain
  through a secret-free versioned registration source. Mastermind extends its existing provider-realm
  owner, preserving `realm_generation`, to bind that provider domain to exact `host_ref`, OS principal
  and opaque config custody; no `binding_generation` or second account id is created. Existing
  `CapacityOwnerFact.generation` / subscription-canary `capacity_generation` remains a separate canary
  fact and is not provider identity or production placement authority. Native observations flow into
  Macro through a secret-free scoped source wire and Macro alone normalizes them into
  `mastermind.provider_capacity.v2`, while v1 remains unchanged. Production B5 extends the accepted CF2 Provider Capacity + boot-bound realm-readiness
  `(host_ref, capacity_capability_id)` join, separately consumes incumbent FP1B physical qualification
  and fresh host evidence, and reuses existing atomic claim/ResourceBroker BEGIN/replay evidence rather
  than creating a new placement or physical bridge. Same provider-capability domain
  across several hosts shares quota; host rows are never summed. First production auth remains the
  protected `/login` + dedicated OS principal/Keychain boundary; alternative auth/isolation needs a
  separate source-law requalification.
rationale: >
  Current protected source already owns provider-realm generation and a distinct canary Capacity
  generation, so inventing a binding generation or repurposing `capacity_generation` would duplicate
  authority. Accepted CF2-F already owns production acquisition/join/claim evidence, so promoting
  `CapacityOwnerFact` would create a parallel placement contract. Macro's current
  `capability_manifest.v1` is a metabolism secret-ref broker rather than the correct native attached-
  login registration owner. The corrected architecture therefore extends each incumbent owner at the
  narrowest seam while preserving Family A refusal, V1 behavior, secret law and lifecycle separation.
alternatives:
  - option: Map native realms to claude_code_oauth_N by ordinal/name/path
    why_not: Family A falsified the required provider-supported equality and rotation witness.
  - option: Let Mastermind mint a native account/realm id
    why_not: Creates competing provider-account identity owners and another mapping problem.
  - option: Add binding_generation beside realm_generation
    why_not: Protected provider-realm receipts already own the local enrollment correction epoch.
  - option: Call Macro provider-domain epoch capacity_generation
    why_not: Protected Mastermind already uses that name for subscription-canary CapacityOwnerFact generation.
  - option: Use CapacityOwnerFact as production Provider Capacity V2 placement evidence
    why_not: Accepted CF2-F owns production snapshot acquisition, realm join, ranking, atomic claim and replay separately.
  - option: Use capability_manifest.v1 for native attached-login registrations
    why_not: It is a metabolism secret-reference broker with different semantics and ownership.
  - option: Treat CLAUDE_CONFIG_DIR or config_custody_ref as account identity/isolation proof
    why_not: Local config custody is not provider subscription identity and does not supersede protected OS-principal/Keychain auth law.
  - option: Sum every host row as independent quota
    why_not: Host is an execution coordinate; replicas of one provider domain consume one quota domain.
  - option: Patch mastermind.provider_capacity.v1 in place
    why_not: Violates the protected closed contract and existing CF2 consumers; V2 must coexist explicitly.
evidence:
  - "Protected Mastermind `ProviderRealmEnrollmentReceipt.generation` is consumed as realm_generation."
  - "Protected Mastermind `CapacityOwnerFact.generation` is separately consumed by subscription canary admission as capacity_generation."
  - "Accepted CF2-F joins strict Macro Provider Capacity to realm-local readiness at `(host_ref, capacity_capability_id)` before existing atomic claim/replay evidence."
  - "Current Macro capability_manifest.v1 is owner metabolism-phase0 and stores secret-ref names plus lane/tier policy."
  - "Accepted Capacity F0 slot identity is `(host_ref, capability_id)` and explicitly does not make host rows independent provider entitlement."
  - "Protected Claude preflight reports OS_PRINCIPAL_KEYCHAIN isolation and denies higher-precedence token/API/cloud auth for the first production path."
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

B1 begins only after paired architecture acceptance. Its source target is the reviewed secret-free
`config/provider_native_capabilities.v1.json` / `mastermind.provider_native_capability_registry/v1`
contract in Shared AI Provider Control, plus typed
`mastermind.provider_native_capability_registration/v1` export. No login/provider call is needed.

Provider-realm V2 reuses `realm_generation` and binds `capacity_capability_id + capability_generation`
to host/principal/config custody. Provider Capacity V2 adds closed `realm_binding` containing
`capability_generation`, `boot_ref`, `realm_generation` and enrollment receipt digest. `boot_ref` is
readiness provenance only; reboot does not advance provider or realm enrollment generation. The earlier
`binding_generation` and row-level `capacity_independence` proposals are rejected.

B5 extends accepted CF2 acquisition/join/atomic-claim/replay evidence and separately composes current
FP1B evidence with byte-exact `host_ref == host_id` and `boot_ref == boot_id`, current `capacity_pool_ref`/qualification, plus fresh host-capacity/pressure evidence. Subscription-canary
`CapacityOwnerFact` remains canary-only unless a separately versioned canary admission is later needed.

The first real B6 realm uses protected native `/login` under a dedicated OS principal/Keychain and must
prove restart/cold-boot/auth-precedence/realm-isolation behavior. Setup-token and same-user multi-config
fanout remain future requalification candidates.

This decision remains `SPEC_ONLY / RECORDS_ONLY / PRODUCTION_INERT` until independent paired review,
current-base validation and explicit Sol source release.