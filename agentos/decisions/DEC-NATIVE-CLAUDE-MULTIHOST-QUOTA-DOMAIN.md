---
key: NATIVE-CLAUDE-MULTIHOST-QUOTA-DOMAIN
question: >
  When one direct Claude subscription is intentionally executable from multiple Macs, how should
  Provider Control represent shared quota/cooling versus host-local native credential/runtime health
  without double-counting capacity, duplicating an incumbent generation owner, or creating a second
  account identity?
answer: >
  Preserve the accepted Capacity F0 tuple slot identity `(host_ref, capability_id)` and preserve the
  generation owners already protected in Mastermind. Macro Shared AI Provider Control owns one opaque
  `capacity_capability_id + capability_generation` for the logical provider capacity/quota domain.
  Each host-local native custody extends the existing provider-realm owner's sealed `realm_generation`,
  keyed by `host_ref + capacity_capability_id`; no new `binding_generation` owner is created. The
  existing Mastermind `CapacityOwnerFact.generation`, exposed by subscription canary admission as
  `capacity_generation`, remains an independent Capacity/Model Router fact generation and is not the
  Macro provider-domain epoch. Provider/account-wide quota and proven usage-limit cooling are scoped
  to `capacity_capability_id + capability_generation` and apply to every current host realm. Binary,
  auth, config, transport and host failures remain realm-local unless evidence proves provider-domain
  scope. Consumers never sum host rows for the same provider domain, and Family-B V2 makes no numeric
  cross-domain fleet entitlement claim until a separately accepted relationship source exists.
rationale: >
  Protected Mastermind already seals `ProviderRealmEnrollmentReceipt.generation` as `realm_generation`
  and separately seals Capacity/Model Router facts with their own generation. Introducing a new
  `binding_generation` or repurposing `capacity_generation` would duplicate or overload canonical
  semantics. The existing Capacity architecture was also explicitly designed for multiple Macs and
  defines slot identity as `(host_ref, capability_id)`. The corrected three-owner model lets a local
  realm repair advance only realm generation, a provider-domain replacement advance capability
  generation, and an ordinary Capacity fact refresh advance only the existing Capacity generation.
  It also allows future M1/M6/Studio replicas to add execution locality without pretending that one
  Max login copied to three Macs creates three times the quota.
alternatives:
  - option: Give each host replica a new capability/account id
    why_not: >
      Duplicates one provider quota domain as several company capacity identities and invites quota
      double-counting and cooling divergence.
  - option: Introduce a new binding_generation beside existing realm_generation
    why_not: >
      Protected provider-realm receipts already own the local enrollment correction epoch. A second
      binding epoch would force future consumers to reconcile two truths for the same host realm.
  - option: Call the Macro provider-domain epoch capacity_generation
    why_not: >
      Protected Mastermind already uses `capacity_generation` for CapacityOwnerFact generation. Reuse
      would make two independent owner facts look equal by name and invite unsafe aliasing.
  - option: Keep one realm_generation for both provider domain and host custody
    why_not: >
      A local host repair would invalidate unrelated healthy replicas, while provider-domain replacement
      could be mistaken for an ordinary local enrollment refresh.
  - option: Sum every host row because F0 slot identity includes host_ref
    why_not: >
      Slot identity is an execution coordinate, not proof of independent provider entitlement. The same
      capability can legitimately appear on multiple hosts.
  - option: Keep a per-row capacity_independence boolean
    why_not: >
      Independence is relational. A boolean does not identify what another domain is independent from
      and can be misused as permission to add unrelated rows.
evidence:
  - "Accepted Capacity F0 architecture: slot identity is `(host_ref, capability_id)` and provider/account capacity is observed on a host; Mac A login is not assumed callable on Mac B."
  - "Protected Mastermind `ProviderRealmEnrollmentReceipt` already owns a sealed `generation`, and `subscription_canary_admission` exposes it as `realm_generation`."
  - "Protected Mastermind `CapacityOwnerFact` separately owns a generation exposed by subscription canary admission as `capacity_generation`."
  - "Current V1 Provider Capacity normalizer validates final slot uniqueness by `(host_ref, capability_id)` even though current source observations remain single-host/capability keyed."
  - "Current Macro `capability_manifest.v1` is a metabolism secret-reference broker, so B1 native attached-login registration needs a secret-free Shared AI Provider Control surface rather than semantic reuse by convenience."
  - "Chairman-approved fleet direction adds M6/other Macs, so Family B must not freeze a single-host-only Claude account model."
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
domain and the incumbent `realm_generation` for a specific host/principal/config enrollment. A stale
value in either dimension independently refuses current placement.

The existing Mastermind Capacity fact generation remains `capacity_generation`; it is neither copied
from nor assumed equal to `capability_generation`. A later B5 bridge must validate Provider Capacity V2
and realm evidence first, then mint/consume the Capacity owner's fact under its existing law. If the
current owner-fact schema cannot bind required provenance safely, a versioned successor is required.

For native V2 rows, `capability_id` remains the Provider-Control capacity id and `host_ref` remains the
accepted execution-host dimension. The `realm_binding` extension carries `capability_generation`,
`realm_generation` and the enrollment receipt. The earlier candidate `binding_generation` and
`capacity_independence` row fields are superseded and should not ship.

Provider Control must retain evidence scope so an account-domain usage-limit can cool all replicas,
while a host-local binary/auth/transport/recovery defect cannot poison healthy replicas by default.
No Claude adapter owns propagation or quota deduplication.

B1 native provider-domain registration must be secret-free and owned by `shared-ai-provider-control`;
the metabolism `capability_manifest.v1` secret-ref registry is not reused as the native account/domain
registry merely because it is an existing Capacity input.

The first four-account canary stays deliberately one-realm-per-domain. Multi-host account replication
is a later bounded proof after the core provider-domain contract works. This decision is source law
only; it creates no registration, credential, provider turn, host realm or runtime capability.