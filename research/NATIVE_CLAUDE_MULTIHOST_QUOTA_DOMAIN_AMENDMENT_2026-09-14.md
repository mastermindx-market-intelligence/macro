# Native Claude Multi-Host Quota-Domain Amendment — OCR-2C Family B

**Date:** 2026-09-14  
**Owner:** Shared AI Provider Control / `WS:EXECUTIVE-CAPACITY-FABRIC`  
**Parent operation:** `ocr2c-family-b-native-claude-realm-capacity-architecture-20260914-sol-001`  
**Status:** `RECORDS ONLY / SPEC_ONLY / PRODUCTION INERT`  
**Narrow precedence:** this amendment supersedes the parent Family-B records where one generation was overloaded for provider-capacity domain and host-local realm custody, where a new `binding_generation` owner was introduced beside the protected provider-realm `realm_generation`, where Macro's domain epoch was called `capacity_generation` despite that name already belonging to Mastermind's Capacity owner fact, and where the draft `capacity_independence` row boolean was underspecified.

## Recovered incumbent law

The accepted Capacity F0 contract already makes slot identity `(host_ref, capability_id)`. It also says provider/account capacity is observed on a host, a login on Mac A is not assumed callable on Mac B, and future host admission owns whether a host can execute work. Therefore Family B must allow one Provider-Control capacity capability to have several host-local execution rows without making those rows separate quota entitlements.

Current V1 implementation remains effectively single-host (`HOST_REF=local-unbound` and source observations are keyed by `capability_id`). Family B V2 may evolve the source/normalizer, but it must preserve the accepted tuple identity and may not patch V1 in place.

Fresh protected Mastermind archaeology also finds two generation owners already present and consumed together: `ProviderRealmEnrollmentReceipt.generation` is the sealed provider-realm `realm_generation`, while `CapacityOwnerFact.generation` is the Capacity/Model Router generation surfaced as `capacity_generation` by `mastermind.subscription_canary_admission/v1`. Family B must not create a third host-binding generation or reuse `capacity_generation` for a different Macro epoch.

## Three-owner contract

```text
provider-capability domain
  key: capacity_capability_id + capability_generation
  owner: Macro Shared AI Provider Control
  meaning: one logical provider capacity/quota domain

host realm enrollment
  key: host_ref + capacity_capability_id + realm_generation
  owner: existing Mastermind provider-realm owner
  meaning: one executable native Claude custody/enrollment of that domain on one host

Capacity owner fact
  key includes existing CapacityOwnerFact.generation
  public canary field: capacity_generation
  owner: Mastermind Capacity/Model Router
  meaning: current worker-capacity fact generation, not provider subscription identity
```

`realm_generation` is not another account/capacity id. It is the existing provider-realm owner's correction epoch, extended in V2 to seal host/principal/config custody. `capability_generation` is the Provider-Control provider-domain epoch. The existing Mastermind `capacity_generation` remains unchanged.

The public V2 executable slot identity remains the accepted pair:

```text
(host_ref, capability_id)
```

where `capability_id == capacity_capability_id`. At most one current `realm_generation` exists for a pair.

## Provider capability generation

`capability_generation` advances only when the logical Provider-Control capacity domain is deliberately replaced/redefined. It does not advance for a host reboot, binary upgrade, token refresh, or replacement of one local custody that still belongs to the same logical domain.

A deliberate change of one replica from logical subscription A to logical subscription B is not an A-domain generation change. That host's A realm enrollment is revoked/superseded and a new enrollment is created under B's `capacity_capability_id/current capability_generation`.

Only if the company redefines logical provider-capability domain A itself to mean a replacement subscription does A's `capability_generation` advance, invalidating all old A-generation enrollments at once.

The name is intentionally not `capacity_generation`: protected Mastermind already uses that field for the independent `CapacityOwnerFact.generation`. Cross-repository implementation must preserve both meanings rather than aliasing equal-looking integers.

## Realm generation

`realm_generation` remains owned by the existing provider-realm owner. Current protected source already seals that generation into `ProviderRealmEnrollmentReceipt` and validates it again through `subscription_canary_admission`.

Family-B provider-realm V2 extends that owner to bind exact host/principal/config custody. `realm_generation` advances when a specific host/capability realm is deliberately re-provisioned, including replacement of OS principal, config custody, or native login custody that must invalidate prior local execution authority.

A current capability generation cannot rescue a stale realm generation. A fresh realm generation cannot rescue a stale capability generation. Neither is the same as the current Capacity owner's `capacity_generation`.

## Native registration and enrollment wires

Macro owner export should expose the provider-domain coordinate:

```text
schema = mastermind.provider_native_realm_registration/v1
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

Host enrollment belongs to Mastermind's provider-realm successor and references both cross-owner generations:

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

Macro does not own the raw local config path or host principal; Mastermind does not invent the provider capability id/generation.

Existing provider-realm V1 receipts remain valid for current consumers. V2 extends the existing owner; it does not reinterpret V1's sealed bytes or mint a separate `binding_generation` system.

## B1 registration owner boundary

Current `config/capability_manifest.yml` is a `capability_manifest.v1` secret-reference broker owned by `metabolism-phase0`; it carries `secret_ref` plus lane/tier policy. It is an input to existing Capacity projection, but that does not make it the semantic owner for native attached-login realm registration.

B1 must therefore use a reviewed versioned **secret-free native Provider-Control registration surface** inside `shared-ai-provider-control` (or an exact current successor shown to own the same fact). The minimal record may contain only provider-capability id/generation, provider/billing/credential-kind/execution-surface classification, registration state and material-source receipt. It must contain no credential value, secret-ref name, host binding, local path, provider account PII, Executive Worker identity or scheduler state.

This is not a provider account database. It is the smallest deterministic registration necessary for the existing Provider Control normalizer to own native provider-capability identity and correction.

## Provider Capacity V2 row

Native rows keep the normal slot coordinate and add a closed binding:

```text
capability_id = capacity_capability_id
host_ref = opaque accepted host
realm_binding = {
  capability_generation,
  realm_generation,
  enrollment_receipt_digest
}
```

The earlier Family-B candidate field `capacity_independence = verified | unknown` is withdrawn from `realm_binding`. Independence between two different provider-capability domains is relational; one unqualified boolean on one row cannot state which other domain it is independent from.

Family B V2 therefore makes no fleet-total numeric Max entitlement claim. If a later accepted source can represent cross-domain quota relationships safely, add them through a separately reviewed relationship contract rather than overloading this binding.

## Shared-domain vs host-local evidence

Provider Control must keep observation scope explicit internally/source-side even if final row eligibility is combined.

### Provider-capability-domain scoped

Apply to every current host realm of `capacity_capability_id + capability_generation` when the source is genuinely provider/account-domain scoped:

- provider-reported quota horizons;
- account/provider usage-limit cooling;
- domain-wide provider account revocation/auth failure when proven at that scope;
- provider-wide health evidence.

### Realm/host scoped

Apply only to one `(host_ref, capacity_capability_id, realm_generation)`:

- native binary/install readiness;
- local credential/auth readability;
- config/principal mismatch;
- local broker/transport/runtime state;
- physical host recovery readiness;
- host-local resource failure.

Unknown error scope stays unknown/degraded. The normalizer may not broaden a host error into account cooling because doing so is convenient.

## Quota aggregation law

If the same provider-capability domain is projected on multiple hosts, any repeated quota evidence is the same evidence domain.

```text
quota evidence key = (capacity_capability_id, capability_generation)
execution key      = (host_ref, capacity_capability_id, realm_generation)
```

A consumer may never sum host rows to estimate fleet entitlement. For the initial V2, no numeric cross-domain fleet quota total is required at all.

Different `capacity_capability_id` values are likewise not assumed additive merely because the Chairman intentionally provisioned different Max logins. They can still be separate executable provider-capability domains and can be scheduled/fair-shared independently; numeric aggregate entitlement remains unclaimed until an accepted source proves a safe relationship.

## Capacity-owner fact boundary

A Mastermind consumer of Provider Capacity V2 may later export/consume the existing owner-minted Capacity fact required by placement. That fact's existing `generation`/`capacity_generation` remains a **Capacity-owner observation generation**. It is not the Macro `capability_generation` and must not be copied from it by convention.

The B5 bridge must first validate the accepted V2 provider-domain coordinate, realm generation, host, snapshot digest/freshness and source quality. If existing Capacity owner facts cannot carry the required provider-domain provenance without ambiguity, use a reviewed versioned successor rather than silently changing the meaning of `capacity_generation`.

## Cooling propagation

```text
domain-scoped usage_limit/account cooling
  -> every current realm of that provider-capability domain is ineligible for new work

host A native-auth/binary/transport failure
  -> only host A realm degrades; host B may remain eligible

unknown scope
  -> preserve unknown/degraded; do not propagate by guess
```

Provider Control owns this classification; the Claude adapter never propagates cooling itself.

## Placement consequence

Capacity conceptually evaluates:

```text
eligible provider-capability domain
  using provider health/cooling/quota/fairness

eligible host realm within that domain
  using realm/host/runtime/resource evidence
```

This may be implemented as one deterministic ranking pass under the existing placement owner. It is not a new two-stage scheduler.

Before START, definite host unavailability may allow lawful selection of another realm when no effect/effect uncertainty exists. After START, RuntimeBinding remains sticky; existing reconciliation law governs host/account/domain changes.

## Initial and later proof

Initial four-account B8 should keep one accepted host realm per intended provider-capability domain. Later multi-host replication can attach M1/M6/Studio realms to an accepted domain only after the core four-domain proof.

A multi-host replication canary must prove:

```text
same capacity id/capability_generation on two host refs
separate realm generations and custody receipts
host-local failure remains local
proven account-domain usage-limit propagates to both replicas
quota evidence is not counted twice
stale capability or realm generation is refused independently
Macro capability_generation is not confused with Mastermind capacity_generation
```

## No effect

This is an additive architecture amendment. It registers no provider capability, creates no host realm or credential, runs no provider call, changes no Provider Capacity snapshot or Capacity owner fact, and modifies no Executive/Worker/route/browser/GUI state.