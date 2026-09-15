# Native Claude Realm Provider Control V2 Architecture — OCR-2C Family B

**Date:** 2026-09-14  
**Owner:** Shared AI Provider Control / `WS:EXECUTIVE-CAPACITY-FABRIC`  
**Operation:** `ocr2c-family-b-native-claude-realm-capacity-architecture-20260914-sol-001`  
**Status:** `CHAIRMAN-APPROVED DIRECTION / ARCHITECTURE CANDIDATE / RECORDS ONLY / SPEC_ONLY / PRODUCTION INERT`  
**Macro basis:** `22f6759fe6529b4768309332309d52a8ee20526a`  
**Cross-repo consumer candidate:** Mastermind PR #662, corrected head `8ed986a814b1eef9e4818c900683fd27fa1a35f1` at authoring time.

## Outcome

Make direct native `claude.ai` Claude Code subscription realms visible to the **existing** Shared AI Provider Control owner so canonical Capacity can later choose among them without:

- matching native realms to `claude_code_oauth_N` by ordinal/name;
- persisting provider account PII or credential fingerprints;
- adding a Mastermind-side account/quota store;
- treating `CLAUDE_CONFIG_DIR` as an Anthropic account identity;
- multiplying aggregate quota merely because multiple credential custodies exist.

The machine result of this architecture is one versioned producer/consumer contract in which Macro owns the opaque provider-capability identity and capacity normalization, while Mastermind binds that owner-issued capability generation to an exact native host/principal/config custody and returns bounded source observations.

## Current canonical source

Current `engine/provider_capacity.py` produces strict `mastermind.provider_capacity.v1` with top-level:

```text
schema
generated_at
producer
audit
snapshot_hash
slots[]
degraded[]
```

Each current V1 slot includes:

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

V1 already enforces the laws Family B must preserve: unknown evidence is explicit; exact remaining capacity is not inferred from a percentage without a denominator; health/cooling/quota freshness is typed; provider outcome is distinct from Executive completion; semantic snapshot identity excludes unrelated audit churn.

OCR-2C Family A already refused the unsafe shortcut: native Claude auth evidence cannot establish a rotation-safe equality relationship to a numbered existing Macro OAuth slot. Family B therefore extends Provider Control directly.

## Ruling 1 — Provider Control owns the only native capacity identity

A native Claude capacity realm receives exactly one opaque:

```text
capacity_capability_id
realm_generation
```

owned by Shared AI Provider Control.

There is no separate Mastermind `realm_id` for capacity placement. Mastermind realm/custody receipts consume this coordinate; they do not mint another account key.

The id must be opaque and non-ordinal. It must not encode or derive from email, provider account/org id, token, Keychain label, app clone name, config path, Slack identity, or `claude_code_oauth_N`.

### Durable source

Capability identity/generation must extend the existing Provider Control capability-definition/config owner (currently including `config/capability_manifest.yml` in the V1 material-source family) or a reviewed versioned successor. Do **not** add a mutable runtime account database solely to register native realms.

The implementation may expose a typed, secret-free owner receipt for one registered native capability generation so Mastermind can bind custody. That receipt is a cross-repository fact/export, not a new lifecycle or identity plane.

## Ruling 2 — registration, custody, subscription identity and capacity are different facts

For a native capability C/G:

```text
Provider Control registration
    C/G exists as a company capacity capability

Mastermind native custody binding
    C/G is bound to exact host_ref + os_principal_ref + config_custody_ref

provider subscription identity
    may remain opaque/unknown

current capacity observation
    fresh health/cooling/quota facts for C/G
```

Registration does not mean logged in. Custody distinctness does not mean independent provider quota. Auth readiness does not mean quota headroom. Provider success does not mean an Executive Job succeeded.

## Ruling 3 — native registration/export contract

The eventual implementation needs one typed owner export from Macro for exact registered native capability generation. Proposed wire:

```text
schema = mastermind.provider_native_realm_registration/v1
capacity_capability_id
realm_generation
provider = claude
billing_mode = subscription
credential_kind = attached_login
execution_surface = native_cli
host_ref
registration_state = registered | revoked
material_source_digest
registration_receipt_digest
```

The exact capability id/generation/state come only from Provider Control source. `host_ref` remains the accepted opaque host identity; it is not an endpoint or credential.

No provider call, account PII or secret is needed to issue registration. A new generation is an owner-controlled provisioning/correction event, not a provider token refresh counter.

## Ruling 4 — Mastermind native observation input

After Mastermind binds registered C/G to exact native custody, it may return a bounded source observation:

```text
schema = mastermind.provider_native_realm_observation/v1
capacity_capability_id
realm_generation
host_ref
provider_family = anthropic
product = claude-code
execution_surface = native_cli
auth_state = ready | not_ready | unknown
auth_method = claudeai | non_native | unknown
health_state = available | degraded | unavailable | unknown
health_error_class
last_provider_outcome_class
last_provider_outcome_at
cooling = {active, kind, reset_at, evidence, observed_at}
quota_horizons[]
capacity_independence = verified | unknown
observed_at
stale_after
source_quality
source_receipt_digest
```

This is an input to Provider Control, not a second normalizer. The observation producer cannot create C/G, rank capabilities, mutate another capability, or report Executive lifecycle success.

Rejected values include raw config paths, emails/account/org ids, credential values/fingerprints, Keychain labels/content, Worker prompts/results, Executive Job/Attempt ids, Slack identities and provider conversation ids.

## Ruling 5 — Provider Capacity V2

`mastermind.provider_capacity.v1` remains unchanged. Native Claude enters only a separately versioned `mastermind.provider_capacity.v2` after implementation/review.

V2 retains the current top-level shape and all V1 evidence semantics. Existing slot fields remain recognizable. V2 adds exactly one closed identity extension:

```text
realm_binding = null
  | {
      realm_generation,
      enrollment_receipt_digest,
      capacity_independence = verified | unknown
    }
```

For native Claude rows:

```text
capability_id = Provider-Control capacity_capability_id
provider = claude
billing_mode = subscription
credential_kind = attached_login
execution_surface = native_cli
realm_binding != null
```

Existing V1-style slots projected into V2 use `realm_binding = null` unless and until separately versioned evidence gives them an equivalent generation contract.

`account_label` remains only an opaque display/correlation value. For native Claude it may equal the opaque `capability_id`; it never contains provider PII.

### V1 coexistence

V1 and V2 are separate closed schemas. Existing V1 consumers continue to receive V1 until explicitly migrated. Do not make V1 output change because V2 native definitions exist. Do not accept V1 as V2 by structural similarity or silently project native realms into a V1 snapshot.

## Ruling 6 — evidence/null/freshness semantics

The V2 implementation must preserve:

```text
unknown != false
unknown quota != unlimited
stale != fresh
present != authenticated
authenticated != healthy
healthy != independent quota
provider outcome != Executive completion
```

A direct Max realm may have:

```text
present = true
enabled = true
health = available
quota_horizons = unknown
capacity_independence = unknown
```

and still be eligible for ordinary placement under a policy that permits unknown headroom. Unknown headroom cannot rank as “100% available.”

Provider-reported usage percentage may be retained as percentage evidence, but absolute `remaining` remains null when `limit` is unknown, preserving the existing V1 invariant.

## Ruling 7 — capacity independence

Multiple native capability ids are **not automatically independent quota pools**.

`capacity_independence=verified` requires a separately accepted evidence source. Distinct:

- capability ids;
- host/principal pairs;
- `CLAUDE_CONFIG_DIR` roots;
- Keychain entries;
- plan type;
- reset time;
- successful turns

are individually insufficient to prove different Anthropic subscriptions.

When independence is unknown, Provider Control may still publish each execution capability’s own fresh health/cooling observations. It may not sum their numeric quota into a larger “fleet remaining capacity” claim or use realm count as an absolute multiplier.

## Ruling 8 — generation and correction semantics

Generation changes when Provider Control deliberately re-registers/re-provisions a capability such that its managed native login/custody may represent a different provider subscription or trusted custody binding.

A V2 current snapshot contains at most one current generation for a `capacity_capability_id`. Older observations remain historical evidence but cannot make current placement eligible. An observation naming the wrong generation is rejected/degraded rather than merged.

Ordinary provider OAuth/token refresh under the same managed login does not advance the company generation.

Out-of-band human credential replacement behind an unchanged custody cannot be safely identified by current provider account evidence. The production trust boundary therefore requires managed login/logout/replacement. An out-of-band mutation invalidates the management assumption and requires explicit re-enrollment before the capability is trusted again.

## Ruling 9 — placement boundary

Provider Control V2 answers only what is known about native capability C/G. Model Router still chooses acceptable execution class. Executive placement still chooses an already-eligible Worker/realm and atomically binds claim evidence.

A Mastermind FPH0 `work_placement_union` can state that a host composition admits a provider realm/quota class. It does not establish Provider Control registration, generation, auth readiness, cooling or capacity.

Before START, a definite unavailable/rate-limit observation can remove C/G from new placement. After START, RuntimeBinding/effect law governs; Provider Control does not move a modifying Attempt to another capability.

## Ruling 10 — browser/operator/GUI excluded

Persistent Claude background sessions, OCR-4A rich Operator Harness, Chrome/native browser integration and computer-use leases are downstream consumers. They do not enter the Provider Capacity identity contract except through ordinary host/resource eligibility owned elsewhere.

Family B core can become production-useful for headless `claude -p` workers without waiting for browser/GUI proof.

## Source implementation boundary

Likely implementation surfaces after current-head archaeology:

```text
Macro:
  config/capability_manifest.yml or reviewed successor
  engine/provider_capacity.py or versioned sibling owner
  existing provider health/cooling source seams
  scripts/build_provider_capacity.py or versioned serializer
  tests/test_provider_capacity.py + new V2/native observation tests

Mastermind consumer:
  existing provider-realm fact owner
  existing Claude preflight family
  versioned Capacity acquisition/validator
  HF1 adapter only after identity/capacity contracts are accepted
```

Exact paths are not implementation authority until the later child re-pins current source and collision ownership.

## Acceptance matrix

Architecture acceptance requires independent proof that:

1. Family A refusal remains intact.
2. Macro owns the single `capacity_capability_id + realm_generation` coordinate.
3. Mastermind does not mint a second capacity/account realm id.
4. V1 stays semantically unchanged.
5. V2 null/freshness/quota relations preserve V1 laws.
6. capability/custody distinctness cannot forge quota independence.
7. provider PII/secret/path material cannot enter either cross-repo wire.
8. generation correction invalidates stale placement evidence.
9. FPH0/HF1/OCR-4A/RuntimeBinding owners are consumed, not rebuilt.
10. merge/protection is still only source capability; no provider/login/runtime effect is claimed.

## Production ladder

```text
architecture protected
-> Macro native capability registration + owner receipt
-> Mastermind v2 custody binding
-> native observation + provider_capacity.v2
-> Mastermind V2 acquisition
-> one managed real realm
-> one bounded real Claude CLI Worker
-> four managed realms
-> Capacity-selected multi-realm bounded Jobs
-> persistent Operator Harness
-> browser
-> computer use
```

Each step has separate acceptance/proof.

## No effects in this architecture wave

No credential was read, copied, rotated or exposed. No provider call/login/logout occurred. No host config, service, Runtime, Capacity snapshot, route, browser, GUI permission, Slack, Linear or Agent execution state was modified. This record authorizes no implementation START by itself.