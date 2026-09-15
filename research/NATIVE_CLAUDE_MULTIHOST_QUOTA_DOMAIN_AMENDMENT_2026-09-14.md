# Native Claude Multi-Host Quota-Domain Amendment — OCR-2C Family B

**Date:** 2026-09-14  
**Owner:** Shared AI Provider Control / `WS:EXECUTIVE-CAPACITY-FABRIC`  
**Parent operation:** `ocr2c-family-b-native-claude-realm-capacity-architecture-20260914-sol-001`  
**Status:** `RECORDS ONLY / SPEC_ONLY / PRODUCTION INERT`  
**Narrow precedence:** this amendment supersedes the parent Family-B records where one generation was overloaded for both a provider-capacity domain and a host-local credential binding, and where the draft `capacity_independence` row boolean was underspecified.

## Recovered incumbent law

The accepted Capacity F0 contract already makes slot identity `(host_ref, capability_id)`. It also says provider/account capacity is observed on a host, a login on Mac A is not assumed callable on Mac B, and future host admission owns whether a host can execute work. Therefore Family B must allow one Provider-Control capacity capability to have several host-local execution rows without making those rows separate quota entitlements.

Current V1 implementation remains effectively single-host (`HOST_REF=local-unbound` and source observations are keyed by `capability_id`). Family B V2 may evolve the source/normalizer, but it must preserve the accepted tuple identity and may not patch V1 in place.

## Two-axis contract

```text
capacity domain
  key: capacity_capability_id + capacity_generation
  owner: Macro Shared AI Provider Control
  meaning: one logical provider capacity/quota domain

execution binding
  key: host_ref + capacity_capability_id + binding_generation
  owner: existing Mastermind provider-realm/custody binding owner
  meaning: one executable native Claude custody of that domain on one host
```

`binding_generation` is not another account/capacity id. It is a correction epoch for a host-local relationship.

The public V2 executable slot identity remains the accepted pair:

```text
(host_ref, capability_id)
```

where `capability_id == capacity_capability_id`. At most one current `binding_generation` exists for a pair.

## Capacity generation

`capacity_generation` advances only when the logical Provider-Control capacity domain is deliberately replaced/redefined. It does not advance for a host reboot, binary upgrade, token refresh, or replacement of one local custody that still belongs to the same logical domain.

A deliberate change of one replica from logical subscription A to logical subscription B is not an A-domain generation change. That host's A binding is revoked/superseded and a new binding is created under B's `capacity_capability_id/current capacity_generation`.

Only if the company redefines logical capacity domain A itself to mean a replacement subscription does A's `capacity_generation` advance, invalidating all old A-generation bindings at once.

## Binding generation

`binding_generation` advances when a specific host/capability relationship is deliberately re-provisioned, including replacement of OS principal, config custody, or native login custody that must invalidate prior local execution authority.

A current capacity generation cannot rescue a stale binding generation. A fresh binding generation cannot rescue a stale capacity generation.

## Native registration and enrollment wires

Macro owner export should expose the domain coordinate:

```text
schema = mastermind.provider_native_realm_registration/v1
capacity_capability_id
capacity_generation
provider = claude
billing_mode = subscription
credential_kind = attached_login
execution_surface = native_cli
registration_state = registered | revoked
material_source_digest
registration_receipt_digest
```

Host binding belongs to Mastermind's provider-realm successor and references both generations:

```text
schema = mastermind.provider_realm_enrollment/v2
capacity_capability_id
capacity_generation
binding_generation
host_ref
os_principal_ref
config_custody_ref
...
```

Macro does not own the raw local config path or host principal; Mastermind does not invent the capacity id/generation.

## Provider Capacity V2 row

Native rows keep the normal slot coordinate and add a closed binding:

```text
capability_id = capacity_capability_id
host_ref = opaque accepted host
realm_binding = {
  capacity_generation,
  binding_generation,
  enrollment_receipt_digest
}
```

The earlier Family-B candidate field `capacity_independence = verified | unknown` is withdrawn from `realm_binding`. Independence between two different capacity domains is relational; one unqualified boolean on one row cannot state which other domain it is independent from.

Family B V2 therefore makes no fleet-total numeric Max entitlement claim. If a later accepted source can represent cross-domain quota relationships safely, add them through a separately reviewed relationship contract rather than overloading this binding.

## Shared-domain vs host-local evidence

Provider Control must keep observation scope explicit internally/source-side even if final row eligibility is combined.

### Domain-scoped

Apply to every current host binding of `capacity_capability_id + capacity_generation` when the source is genuinely provider/account-domain scoped:

- provider-reported quota horizons;
- account/provider usage-limit cooling;
- domain-wide provider account revocation/auth failure when proven at that scope;
- provider-wide health evidence.

### Binding-scoped

Apply only to one `(host_ref, capacity_capability_id, binding_generation)`:

- native binary/install readiness;
- local credential/auth readability;
- config/principal mismatch;
- local broker/transport/runtime state;
- physical host recovery readiness;
- host-local resource failure.

Unknown error scope stays unknown/degraded. The normalizer may not broaden a host error into account cooling because doing so is convenient.

## Quota aggregation law

If the same capacity domain is projected on multiple hosts, any repeated quota evidence is the same evidence domain.

```text
quota evidence key = (capacity_capability_id, capacity_generation)
execution key      = (host_ref, capacity_capability_id, binding_generation)
```

A consumer may never sum host rows to estimate fleet entitlement. For the initial V2, no numeric cross-domain fleet quota total is required at all.

Different `capacity_capability_id` values are likewise not assumed additive merely because the Chairman intentionally provisioned different Max logins. They can still be separate executable capacity domains and can be scheduled/fair-shared independently; numeric aggregate entitlement remains unclaimed until an accepted source proves a safe relationship.

## Cooling propagation

```text
domain-scoped usage_limit/account cooling
  -> every current binding of that domain is ineligible for new work

host A native-auth/binary/transport failure
  -> only host A binding degrades; host B may remain eligible

unknown scope
  -> preserve unknown/degraded; do not propagate by guess
```

Provider Control owns this classification; the Claude adapter never propagates cooling itself.

## Placement consequence

Capacity conceptually evaluates:

```text
eligible capacity domain
  using provider health/cooling/quota/fairness

eligible host binding within that domain
  using host/binding/runtime/resource evidence
```

This may be implemented as one deterministic ranking pass under the existing placement owner. It is not a new two-stage scheduler.

Before START, definite host unavailability may allow lawful selection of another binding when no effect/effect uncertainty exists. After START, RuntimeBinding remains sticky; existing reconciliation law governs host/account/domain changes.

## Initial and later proof

Initial four-account B8 should keep one accepted host binding per intended capacity domain. Later multi-host replication can attach M1/M6/Studio bindings to an accepted domain only after the core four-domain proof.

A multi-host replication canary must prove:

```text
same capacity id/generation on two host refs
separate binding generations and custody receipts
host-local failure remains local
proven account-domain usage-limit propagates to both replicas
quota evidence is not counted twice
stale capacity or binding generation is refused independently
```

## No effect

This is an additive architecture amendment. It registers no capacity capability, creates no host binding or credential, runs no provider call, changes no Provider Capacity snapshot, and modifies no Executive/Worker/route/browser/GUI state.