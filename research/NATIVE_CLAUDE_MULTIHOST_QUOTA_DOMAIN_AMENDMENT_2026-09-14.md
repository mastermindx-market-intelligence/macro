# Native Claude Multi-Host Quota-Domain Amendment — OCR-2C Family B

**Date:** 2026-09-15  
**Owner:** Shared AI Provider Control / `WS:EXECUTIVE-CAPACITY-FABRIC`  
**Parent operation:** `ocr2c-family-b-native-claude-realm-capacity-architecture-20260914-sol-001`  
**Status:** `RECORDS ONLY / SPEC_ONLY / PRODUCTION INERT`  
**Narrow precedence:** this amendment supersedes parent Family-B records where one generation was overloaded for provider domain and host realm, where `binding_generation` was introduced beside protected `realm_generation`, where Macro's provider-domain epoch was called `capacity_generation` despite that name already existing in Mastermind canary facts, where B5 was routed through `CapacityOwnerFact`, or where the draft `capacity_independence` row boolean was underspecified.

## Recovered incumbent law

Accepted Capacity F0 defines executable slot identity as `(host_ref, capability_id)` and keeps provider capacity normalization in Macro. Accepted CF2-F production source law then joins one strict Provider Capacity snapshot to realm-local readiness at exact `(host_ref, capacity_capability_id)` and stores immutable claim evidence through the existing Executive atomic claim path.

Current V1 remains effectively single-host (`HOST_REF=local-unbound`; source observations keyed by `capability_id`). Family B V2 may evolve source/normalizer shape but may not patch V1 in place.

Fresh protected Mastermind archaeology finds:

- `ProviderRealmEnrollmentReceipt.generation` is the sealed provider-realm `realm_generation`;
- `CapacityOwnerFact.generation` is a separate canary Capacity/Model Router generation exposed by `mastermind.subscription_canary_admission/v1` as `capacity_generation`;
- `CapacityOwnerFact` references are confined to its owner/minting seam, subscription canary admission and tests; it is not the accepted CF2 production claim contract.

Family B must therefore preserve the existing CF2 join/claim plane rather than promote the canary fact into a second placement contract.

## Three-owner generation contract

```text
provider-capability domain
  key: capacity_capability_id + capability_generation
  owner: Macro Shared AI Provider Control
  meaning: one logical provider capacity/quota domain

host realm enrollment
  key: host_ref + capacity_capability_id + realm_generation
  owner: existing Mastermind provider-realm owner
  meaning: one executable native Claude custody/enrollment on one host

subscription-canary Capacity fact
  field: CapacityOwnerFact.generation / public capacity_generation
  owner: Mastermind Capacity/Model Router
  meaning: current canary activation fact generation
  production placement authority: none by itself
```

No two generations are equal by convention.

## Provider capability generation

`capability_generation` advances only when the logical Provider-Control domain is deliberately replaced/redefined or its native registration is revoked/re-enrolled as a new provider-domain generation. Host reboot, binary update, token refresh, canary Capacity fact refresh or replacement of one local realm does not advance it.

A host moved from logical subscription A to B revokes/supersedes the A realm and enrolls under B's `capacity_capability_id/current capability_generation`; this does not redefine A itself.

The name is intentionally not `capacity_generation`, which already means something else in protected Mastermind.

## Realm generation

`realm_generation` remains the existing provider-realm owner's correction epoch. Family-B V2 extends that owner to seal host/principal/config custody. It advances when that local executable enrollment is deliberately replaced/re-provisioned.

A current capability generation cannot rescue a stale realm generation; a fresh realm generation cannot rescue stale provider-domain identity.

## Native registration and enrollment wires

Macro native provider-domain registration:

```text
schema = mastermind.provider_native_capability_registration/v1
capacity_capability_id
capability_generation
provider = claude
billing_mode = subscription
credential_kind = attached_login
execution_surface = native_cli
registration_state = registered | revoked
material_source_digest
registration_receipt_digest
```

Mastermind host realm enrollment:

```text
schema = mastermind.provider_realm_enrollment/v2
capacity_capability_id
capability_generation
realm_generation
host_ref
os_principal_ref
config_custody_ref
...
```

Existing provider-realm V1 receipts remain valid for current consumers. V2 extends the incumbent owner; no `binding_generation` plane is created.

## B1 registration owner boundary

Current `config/capability_manifest.yml` is `capability_manifest.v1`, owned by `metabolism-phase0`, and carries `secret_ref` plus lane/tier policy. It is an input to current Capacity projection, not the semantic native attached-login registration owner.

B1 therefore needs the smallest reviewed versioned **secret-free** native registration surface inside `shared-ai-provider-control` (or an exact successor proven to own the same fact). It may contain provider capability id/generation, classification, registration state and material-source receipt. It must not contain credential bytes, secret-ref names, host bindings, local paths, provider PII, Worker identity or scheduler state.

This is not a provider account database.

## Provider Capacity V2 row

```text
capability_id = capacity_capability_id
host_ref = opaque accepted host
realm_binding = {
  capability_generation,
  boot_ref,
  realm_generation,
  enrollment_receipt_digest
}
```

The earlier `capacity_independence` row field is withdrawn. Different provider-capability domains are not assumed numerically additive; Family B V2 need not publish a fleet-total Max entitlement.

## Evidence scope

Provider-domain evidence applies to all current host realms only when source semantics prove domain scope:

- quota horizons;
- account/provider usage-limit cooling;
- domain-wide provider account revocation/auth failure;
- provider-wide health evidence.

Realm enrollment evidence stays local to `(host_ref, capacity_capability_id, realm_generation)`; current readiness additionally binds exact incumbent FP1B `boot_ref`:

- binary/install readiness;
- local credential/auth readability;
- config/principal mismatch;
- broker/transport/runtime state;
- host recovery/resource failure.

Unknown scope stays unknown/degraded.

## Quota aggregation law

```text
quota evidence key = (capacity_capability_id, capability_generation)
execution realm key = (host_ref, capacity_capability_id, realm_generation)
current readiness key = (host_ref, boot_ref, capacity_capability_id, realm_generation)
```

Repeated domain evidence on several host rows is the same evidence domain. Consumers never sum host rows.

## B5 production consumer/claim boundary

Family B production placement must extend the accepted CF2 contract, not substitute `CapacityOwnerFact`.

B5 target:

```text
Provider Capacity V2 snapshot
        +
provider-realm V2 / boot-bound realm-local readiness
        +
incumbent FP1B physical qualification + fresh host-capacity/pressure evidence
        |
        v
immutable (host_ref, capacity_capability_id) join
+ independent capability_generation and realm_generation verification
+ exact host_ref == host_id and boot_ref == boot_id
+ current pool/qualification/freshness verification
        |
        v
strict Mastermind V2 consumer
+ rank only already-lawful candidates
        |
        v
existing Executive atomic claim / ResourceBroker BEGIN path
+ separately bound provider V2 and FP1B physical evidence
+ historical replay without current provider/physical re-ranking
```

The accepted claim evidence successor must bind at minimum the exact Provider Capacity V2 snapshot digest/version/freshness, selected `capacity_capability_id + capability_generation`, selected `host_ref + boot_ref + realm_generation`, deterministic reason codes and existing source/realm receipts. It must separately bind the incumbent FP1B request/result identities—current `capacity_pool_ref`, `host_qualification_revision`, host-capacity snapshot digest/freshness and BEGIN pressure digest—through the current CF2/physical claim owners rather than a second ledger or Family-B physical receipt.

`CapacityOwnerFact` may remain useful to the current interactive subscription-canary admission. Its `capacity_generation` keeps its existing canary semantics. If a later B6/B7 canary must include Provider Capacity V2 provenance, evolve canary admission explicitly rather than pretending its fact generation is the provider-domain generation.

## Cooling propagation

```text
provider-domain usage_limit/account cooling
  -> every current realm of that provider-capability domain ineligible for new work

host A native-auth/binary/transport/recovery failure
  -> only host A realm degrades; host B may remain eligible

unknown scope
  -> preserve unknown/degraded; no guessed propagation
```

Provider Control owns provider-scope normalization; the Claude adapter does not.

## Boot-currentness and physical-authority consequence

An ordinary reboot does not change provider or realm enrollment generation. Old-boot readiness becomes ineligible for new work. Provider Capacity's `boot_ref` is provenance only; B5 must separately consume current FP1B qualification and evidence before claim/BEGIN. Wrong boot/pool/qualification or stale physical evidence remains host-local and never becomes provider-domain cooling. Historical replay keeps the evidence accepted at the historical claim without current physical reread.

## Placement consequence

Capacity may conceptually evaluate provider-domain eligibility and host-realm eligibility as two dimensions inside the **existing** deterministic placement owner. This is not a two-stage scheduler.

Before START, a definite unavailable realm may permit another current realm when no effect/effect uncertainty exists. After START, RuntimeBinding remains sticky and existing reconciliation law governs changes.

## Initial and later proof

Initial B8 keeps one host realm per intended provider-capability domain. Later M1/M6/Studio replication must prove:

```text
same capacity_capability_id + capability_generation on multiple host refs
separate realm generations/custody receipts
host-local failure remains local
proven provider-domain usage-limit propagates to replicas
quota evidence is not counted twice
stale capability or realm generation independently refused
canary Capacity generation cannot substitute for either
```

## Required falsifiers

Kill at least:

```text
host rows summed as quota
host-local auth failure widened to all replicas without evidence
provider-domain usage-limit scoped to only reporting host
stale realm generation accepted with current capability generation
stale capability generation accepted with fresh realm generation
host B receipt substituted for host A
host moved to B while retaining A capability identity
capability generation forces unrelated realm generation increment
realm generation creates a new quota domain
Macro capability_generation confused with canary capacity_generation
CapacityOwnerFact substituted for Provider Capacity V2 claim evidence
replay re-reads current Provider Capacity state
caller forges provider capability id/generation
```

## No effect

This additive architecture amendment registers no capability, creates no host realm/credential, runs no provider call, changes no Provider Capacity snapshot or Executive claim, and modifies no Worker/route/browser/GUI state.