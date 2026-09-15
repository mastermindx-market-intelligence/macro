---
key: NATIVE-CLAUDE-MULTIHOST-QUOTA-DOMAIN
question: >
  When one direct Claude subscription is intentionally executable from multiple Macs, how should
  Provider Control represent shared quota/cooling versus host-local native credential/runtime health
  without double-counting capacity or creating a second account identity?
answer: >
  Preserve the accepted Capacity F0 tuple slot identity `(host_ref, capability_id)` and split
  correction epochs, not account identities. Macro Shared AI Provider Control owns one opaque
  `capacity_capability_id + capacity_generation` for the logical provider capacity/quota domain.
  Each host-local native custody has its own `binding_generation` under the existing provider-realm
  binding owner, keyed by `host_ref + capacity_capability_id`; binding generation is not another
  account/capacity id. Provider/account-wide quota and proven usage-limit cooling are scoped to the
  capacity domain and apply to every current host binding. Binary/auth/config/transport/host failures
  remain binding-local unless evidence proves provider-domain scope. Consumers must never sum host
  rows for the same capacity domain, and Family-B V2 makes no numeric cross-domain fleet entitlement
  claim until a separately accepted relationship source exists.
rationale: >
  The existing Capacity architecture was explicitly designed for multiple Macs and defines slot
  identity as `(host_ref, capability_id)`. Overloading one generation for both provider-capacity
  identity and local custody would either make host repairs invalidate the whole account or make an
  account replacement look like a harmless host refresh. Separating capacity generation from binding
  generation preserves correction semantics while retaining one canonical provider/capacity identity.
  It also allows future M1/M6/Studio replicas to add execution locality without pretending that one
  Max login copied to three Macs creates three times the quota.
alternatives:
  - option: Give each host replica a new capability/account id
    why_not: >
      Duplicates one provider quota domain as several company capacity identities and invites quota
      double-counting/cooling divergence.
  - option: Keep one realm_generation for both account and host custody
    why_not: >
      A local host repair would invalidate unrelated healthy replicas, while replacing the logical
      subscription on one host could be mistaken for an ordinary binding refresh.
  - option: Sum every host row because F0 slot identity includes host_ref
    why_not: >
      Slot identity is an execution coordinate, not proof of independent provider entitlement.
      The same capability can legitimately appear on multiple hosts.
  - option: Keep a per-row capacity_independence boolean
    why_not: >
      Independence is relational. A boolean does not identify what another domain is independent
      from and can be misused as permission to add unrelated rows.
evidence:
  - "Accepted Capacity F0 architecture: slot identity is `(host_ref, capability_id)` and provider/account capacity is observed on a host; Mac A login is not assumed callable on Mac B."
  - "Current V1 normalizer sorts and validates final slot uniqueness by `(host_ref, capability_id)` even though the current implementation's source observations are still single-host/capability keyed."
  - "Chairman-approved fleet direction adds M6/other Macs, so Family B must not freeze a single-host-only Claude account model."
  - "Paired Family-B Mastermind amendment records capacity_generation versus binding_generation and rejects host-row quota aggregation."
affects:
  - WS:EXECUTIVE-CAPACITY-FABRIC
  - shared-ai-provider-control
  - mastermind/OCR-2C
  - mastermind/PF1
  - mastermind/MH1
confidence: high
reversibility: costly
decided_by: ceo-sol
decided_at: 2026-09-14
---

## Consequences

Family-B producer/consumer schemas use `capacity_generation` for the Provider-Control logical quota
domain and `binding_generation` for a specific host/principal/config custody. A stale value in either
dimension independently refuses current placement.

For native V2 rows, `capability_id` remains the Provider-Control capacity id and `host_ref` remains the
accepted execution-host dimension. The binding extension carries both generations plus the enrollment
receipt. The earlier candidate `capacity_independence` row boolean is superseded and should not ship.

Provider Control must retain evidence scope so an account-domain usage-limit can cool all replicas,
while a host-local binary/auth/transport/recovery defect cannot poison healthy replicas by default.
No Claude adapter owns propagation or quota deduplication.

The first four-account canary stays deliberately one-binding-per-domain. Multi-host account replication
is a later bounded proof after the core provider-domain contract works. This decision is source law only;
it creates no registration, credential, provider turn, host binding or runtime capability.