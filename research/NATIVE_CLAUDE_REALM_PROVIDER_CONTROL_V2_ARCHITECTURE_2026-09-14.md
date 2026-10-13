# Native Claude Provider Capability + Realm Capacity V2 Architecture — OCR-2C Family B

**Date:** 2026-09-15  
**Owner:** Shared AI Provider Control / `WS:EXECUTIVE-CAPACITY-FABRIC`  
**Operation:** `ocr2c-family-b-native-claude-realm-capacity-architecture-20260914-sol-001`  
**Status:** `CHAIRMAN-APPROVED DIRECTION / ARCHITECTURE CANDIDATE / RECORDS ONLY / SPEC_ONLY / PRODUCTION INERT`  
**Current protected Mastermind reconciliation basis:** `8e25bb32601ef5f40a689da6d6f24149e79e31fa`, Skillpack `mastermind.sol_skillpack.v1` 1.0.1 / bootstrap major 1.  
**Paired consumer candidate:** Mastermind PR #662.

## 1. Outcome

Make direct native `claude.ai` Claude Code subscription capacity visible to the **existing** Shared AI Provider Control owner so canonical Capacity can later select among governed native Claude realms without:

- matching native realms to `claude_code_oauth_N` by ordinal/name/path;
- persisting provider account PII or credential fingerprints;
- adding a Mastermind-side account/quota store;
- multiplying provider quota because one subscription is executable on several Macs;
- creating a second provider realm, scheduler, claim ledger, retry plane or lifecycle system.

The architecture has three distinct owner coordinates:

```text
Provider Control provider-capability domain
  capacity_capability_id + capability_generation

Mastermind host realm enrollment
  host_ref + capacity_capability_id + realm_generation

Mastermind subscription-canary Capacity fact
  CapacityOwnerFact.generation / public capacity_generation
  (canary fact only; not provider identity and not production CF2 claim authority)
```

Provider Control remains the only provider-capacity normalizer/semantic-hash owner. Mastermind remains the realm/claim consumer and lifecycle owner.

## 2. Current canonical source

Current Macro `engine/provider_capacity.py` produces strict `mastermind.provider_capacity.v1` with:

```text
schema
generated_at
producer
audit
snapshot_hash
slots[]
degraded[]
```

Each V1 slot includes:

```text
capability_id
provider
account_label
host_ref
billing_mode
credential_kind
execution_surface
present
enabled
health
cooling
quota_horizons[]
last_outcome
```

V1 already enforces laws Family B preserves: unknown is explicit; percentage does not invent absolute remaining quota; health/cooling/quota freshness is typed; provider outcome is not Executive completion; semantic identity excludes display/audit churn.

Current V1 source observations are still effectively single-host, but accepted F0 slot identity is `(host_ref, capability_id)` and explicitly allows future multi-host execution semantics.

Current Macro `config/capability_manifest.yml` is `capability_manifest.v1`, owner `metabolism-phase0`, and brokers secret-ref names plus lane/tier policy. It is an existing V1 source, **not** the semantic native attached-login registration registry.

## 3. Family A refusal remains binding

Native Claude auth evidence does not establish a rotation-safe equality relationship to numbered existing Macro OAuth slots. Reject joins by:

- ordinal;
- app/Slack/account nickname;
- config path;
- provider/model name;
- plan type/reset time/usage percentage;
- secret hash/fingerprint;
- operator intuition.

Family B therefore extends Provider Control with a native provider-capability domain rather than aliasing a current OAuth capability.

## 4. Ruling A — Provider Control owns the single provider-capability identity

A native Claude provider-capability domain receives exactly one opaque:

```text
capacity_capability_id
capability_generation
```

owned by Shared AI Provider Control.

`capacity_capability_id` is opaque, non-ordinal and non-PII. It must not derive from email, provider account/org id, token, Keychain label, app clone, config path, Slack identity, host name, Worker id or `claude_code_oauth_N`.

`capability_generation` advances only when the **logical provider-capability domain** is deliberately replaced/redefined or its registration is revoked/re-enrolled as a new provider-domain generation. Ordinary token refresh, binary update, host reboot, local realm repair or canary Capacity fact refresh does not advance it.

The term is deliberately not `capacity_generation`: protected Mastermind already uses that field for a different canary fact.

## 5. Ruling B — exact B1 durable source is secret-free Provider Control config

The architecture freezes this B1 source path/schema candidate for independent review:

```text
Macro path: config/provider_native_capabilities.v1.json
schema: mastermind.provider_native_capability_registry/v1
owner_program: shared-ai-provider-control
```

Closed top level:

```json
{
  "schema": "mastermind.provider_native_capability_registry/v1",
  "owner_program": "shared-ai-provider-control",
  "capabilities": []
}
```

Closed capability row contract:

```text
registration_state = registered | revoked
```

Concrete registered row:

```json
{
  "capacity_capability_id": "<opaque non-ordinal company id>",
  "capability_generation": 1,
  "provider": "claude",
  "billing_mode": "subscription",
  "credential_kind": "attached_login",
  "execution_surface": "native_cli",
  "registration_state": "registered"
}
```

Exactly one current row exists for each previously registered `capacity_capability_id`. A revoked row uses the same closed shape with `registration_state = revoked` and is retained as the terminal current-state tombstone for that generation; row disappearance is not revocation.

```text
never registered -> registered(g)
registered(g) -> revoked(g)
revoked(g) -> registered(g2), where g2 > g
```

Provider Control compares the candidate registry with the immediately preceding accepted source release. It refuses generation decrement or generation reuse, rollback or source reversion, same-generation resurrection, duplicate current identity or a conflicting current row, row removal after registration, caller-selected generation/state, and caller-selected identity. Re-enrollment never rewrites a revoked generation.

No host, OS principal, Worker, raw config path, secret-ref name, provider PII, provider credential, quota number, scheduler state or lifecycle state belongs in this registry.

This checked-in deterministic source is intentionally small. It is not a mutable provider account database. Registration/generation correction occurs through reviewed source change, producing a new material-source identity. If independent review finds a current accepted Provider Control configuration owner with strictly better semantics, it may request a bounded replacement before architecture protection; implementation may not improvise another runtime store.

V2 material-source identity must include this registry. V1 material-source identity and V1 output remain unchanged.

## 6. Ruling C — typed Provider Control registration export

Macro exposes one secret-free fact for a current provider-capability domain:

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

There is deliberately **no `host_ref`** in this owner export. Host realm enrollment belongs to Mastermind.

The receipt digest is deterministic evidence of the validated Provider Control source fact, not a credential and not an Executive lifecycle token.

## 7. Ruling D — Mastermind provider-realm enrollment reuses incumbent `realm_generation`

Protected Mastermind already owns sealed `ProviderRealmEnrollmentReceipt.generation`, consumed as `realm_generation`. Family B V2 extends that owner; it does not create `binding_generation`.

Paired Mastermind V2 wire:

```text
schema = mastermind.provider_realm_enrollment/v2
capacity_capability_id
capability_generation
realm_generation
provider_family = anthropic
product = claude-code
execution_surface = native_cli
auth_family = claudeai_subscription
host_ref
os_principal_ref
config_custody_ref
enrollment_state = enrolled | unenrolled
registration_receipt_digest
source_receipt_digest
receipt_id
receipt_digest
```

`registration_receipt_digest` is the canonical B1 registration digest. The withdrawn `capacity_identity_receipt_digest` name has no alias or mapping and must be rejected.

`config_custody_ref` is an opaque execution/config coordinate. Under current protected PF1/OCR-1 law it is **not** proof of macOS credential independence and cannot substitute for the dedicated OS-principal/Keychain boundary.

A local realm repair may advance `realm_generation` without changing the provider domain. A provider-domain replacement may advance `capability_generation` and invalidate old realm enrollments without pretending every host independently changed provider identity. An ordinary host reboot advances neither generation: B2 enrollment remains stable, while B3/B4 readiness becomes current only for the exact incumbent FP1B `boot_ref`.

## 8. Ruling E — native realm observation wire is source evidence, not Worker authority

After a current provider-capability registration and provider-realm enrollment exist, the fixed source-owned Mastermind B2/B3 producer may emit one provider-facing observation fact for Macro acquisition:

```text
schema = mastermind.provider_native_realm_observation/v1
capacity_capability_id
capability_generation
host_ref
boot_ref
realm_generation
enrollment_receipt_digest
observed_at
realm_auth = {
  state: ready | not_ready | unknown,
  method: claudeai | non_native | unknown,
  source_quality
}
provider_health = {
  state: available | degraded | unavailable | unknown,
  error_class,
  scope: realm | provider_domain | unknown,
  observed_at
}
cooling = {
  active,
  kind,
  reset_at,
  evidence,
  scope: provider_domain | realm | unknown,
  observed_at
}
quota_horizons[] = {
  ...existing V1 quota evidence fields...,
  scope: provider_domain | unknown
}
last_provider_outcome = {
  class,
  observed_at,
  scope: provider_domain | realm | unknown
}
source_receipt_digest
```

The exact closed nested field vocabulary must reuse current V1 health/cooling/quota classes wherever semantics match; B4 may add only the scope/generation/boot-provenance identity required by Family B.

This wire is acquired only through Macro's fixed source-owned `build_snapshot() -> collect_current_observations()` adapter; it is not a public request body, V2 CLI payload, Worker/model output or caller-submitted JSON. `source_receipt_digest` is content-integrity evidence, not producer authentication. The wire cannot create a provider capability, rank workers, set another domain cooling, assert Executive completion or replace claim-time worker/realm readiness.

Reject raw config paths, account/org/email, tokens, fingerprints, Keychain labels/content, Worker prompts/results, Job/Attempt ids, Slack identities and provider conversation ids.

## 9. Ruling F — Provider Capacity V2

`mastermind.provider_capacity.v1` remains unchanged.

V2 retains the current top-level semantic model and existing slot fields, adding one closed identity extension:

```text
realm_binding = null
  | {
      capability_generation,
      boot_ref,
      realm_generation,
      enrollment_receipt_digest
    }
```

Native Claude row:

```text
capability_id = capacity_capability_id
provider = claude
billing_mode = subscription
credential_kind = attached_login
execution_surface = native_cli
host_ref = exact accepted opaque host
realm_binding != null
```

Existing V1-style slots in V2 use `realm_binding = null` unless separately versioned evidence supplies equivalent semantics.

V1 and V2 are separate closed schemas. Existing V1 consumers remain on V1 until explicitly migrated. Do not accept V1 as V2 by structural similarity and do not change V1 output merely because V2 definitions exist.

## 10. Ruling G — multi-host quota domain law

Same provider-capability domain on several hosts:

```text
quota evidence key = (capacity_capability_id, capability_generation)
execution realm key = (host_ref, capacity_capability_id, realm_generation)
current readiness provenance key = (host_ref, boot_ref, capacity_capability_id, realm_generation)
```

Host rows are never summed to estimate entitlement.

Different `capacity_capability_id` values are not assumed numerically additive/independent merely because provisioning intended different Max logins. Family B V2 makes no fleet-total numeric Max entitlement claim without a separately accepted relationship source.

Provider-domain usage-limit/cooling propagates across current host realms only when source semantics prove provider-domain scope. Binary, local auth/config/transport/recovery/resource failures remain realm-local. Unknown scope remains unknown/degraded.

The earlier per-row `capacity_independence` proposal is rejected.

## 11. Ruling H — production B5 reuses accepted CF2 acquisition/join/claim

Protected source search shows `CapacityOwnerFact` is a subscription-canary fact, not the accepted production CF2 claim path. Family B must not promote it into a second placement contract.

B5 production flow is:

```text
strict Provider Capacity V2 snapshot
        +
current provider-realm V2 / boot-bound realm-local readiness evidence
        +
incumbent FP1B physical qualification + fresh host-capacity/pressure evidence
        |
        v
immutable (host_ref, capacity_capability_id) join
+ exact capability_generation + realm_generation validation
+ byte-exact host_ref == host_id and boot_ref == boot_id
+ current capacity_pool_ref + qualification_revision validation
        |
        v
strict Mastermind V2 consumer
+ deterministic ranking of already-lawful candidates
        |
        v
existing Executive atomic claim / ResourceBroker BEGIN path
+ separately bound provider V2 and FP1B physical evidence
+ historical replay without current provider/physical re-read or rerank
```

The claim evidence successor must bind at minimum:

```text
provider_capacity_schema = mastermind.provider_capacity.v2
capacity_snapshot_hash
capacity_snapshot_generated_at / accepted freshness identity
capacity_capability_id
capability_generation
host_ref
boot_ref
realm_generation
enrollment/source receipt digest(s)
current capacity_pool_ref + host_qualification_revision
host-capacity snapshot digest/freshness + BEGIN pressure digest
existing physical request/policy binding
deterministic capacity reason codes / policy version already owned by CF2
```

Use the existing event/placement/claim and FP1B/ResourceBroker owners. Provider Capacity carries `boot_ref` only as readiness provenance; it never becomes physical admission authority. No new capacity ledger, physical qualification store, host sampler, selection database, receipt owner or replay plane.

Current `CapacityOwnerFact.generation` / subscription-canary `capacity_generation` keeps its current canary semantics. If later native canary admission needs V2 provenance, version that canary admission explicitly.

## 12. Ruling I — authentication source law remains separate

Family B capacity identity does not authorize credential mechanisms.

Protected Mastermind PF1/OCR-1 still controls first production auth:

```text
native /login
+ dedicated OS principal
+ macOS Keychain
+ current worker-context native-auth preflight
```

Current provider support for setup-token and stronger `CLAUDE_CONFIG_DIR` keying is evidence for a future auth-source requalification, not authority to weaken this boundary inside B1-B5.

## 13. Exact implementation owner surfaces after architecture protection

B1/B4 Macro source target:

```text
CREATE config/provider_native_capabilities.v1.json
MODIFY engine/provider_capacity.py with shared V2 logic while preserving all V1 behavior/bytes semantics
CREATE scripts/build_provider_capacity_v2.py
ADD focused Provider Capacity V2/native registration/observation tests
```

Do **not** mutate `scripts/build_provider_capacity.py` semantics for existing V1 consumers unless a discriminator proves a source-neutral refactor is necessary and V1 golden vectors remain exact.

Mastermind B2/B3/B5 target owners remain existing provider-realm, Claude preflight, Capacity source-acquisition and CF2 claim paths; exact source paths are selected at the later reviewed implementation child after current protected re-pin.

## 14. Acceptance falsifiers

Independent review and later tests must kill at least:

```text
native realm aliases claude_code_oauth_N by ordinal/name/path
provider capability id encodes account PII or host/Worker identity
caller chooses/forges capability id or capability_generation
new binding_generation created beside realm_generation
Macro capability_generation confused with canary capacity_generation
same provider domain on two hosts counted twice as quota
host-local auth failure cools all replicas without provider-domain evidence
provider-domain usage-limit cools only reporting host
stale realm generation accepted under current capability generation
stale capability generation accepted under current realm generation
host B enrollment substituted for host A
Provider Capacity V1 output changes because V2 definitions exist
V1 structurally accepted as V2
CapacityOwnerFact substituted for production V2 claim evidence
current provider state re-read on historical replay
provider observation asserted Executive Job success
raw path/secret/account PII enters either cross-repo wire
config_custody_ref treated as macOS auth-isolation proof under current source law
```

## 15. Production ladder

```text
B0 architecture protected
-> B1 secret-free provider-capability registry/export
-> B2 provider-realm enrollment v2
-> B3 current preflight bridge
-> B4 native observation + provider_capacity.v2
-> B5 V2 acquisition + existing CF2 join/claim/replay evolution
-> B6 one managed /login OS-principal realm + restart/cold-boot proof
-> B7 one bounded real native Claude Worker
-> B8 four provider domains, one realm each
-> B9 Capacity-selected multi-realm bounded Jobs
-> later multi-host replication
-> B10 persistent Operator Harness
-> B11 browser/computer use
```

Each step has its own acceptance and current-source START gate.

## 16. No effects in this architecture wave

No provider credential was read/copied/rotated. No provider call/login/logout occurred. No capability registration file exists yet. No host config, service, Runtime, Capacity snapshot, Executive claim, route, browser, GUI permission, Slack lifecycle or Worker execution state was changed by this records architecture. It authorizes no implementation START by itself.