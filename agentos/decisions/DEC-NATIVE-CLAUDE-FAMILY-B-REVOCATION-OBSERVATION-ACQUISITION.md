---
key: NATIVE-CLAUDE-FAMILY-B-REVOCATION-OBSERVATION-ACQUISITION
question: >
  How must Family B represent current registration revocation, authenticate native-realm
  observations acquired by Provider Control, and preserve one registration digest identity after
  independent review found the pending paired records incomplete?
answer: >
  Keep the existing Shared AI Provider Control and provider-realm owners. The checked-in native
  capability registry carries exactly one current row per capacity_capability_id with
  registration_state registered or revoked. registered(g) may become revoked(g); re-enrollment must
  become registered(g2) with g2 greater than g. Removal, generation reuse, rollback and resurrection
  are refused against the preceding accepted source release. Use registration_receipt_digest
  end-to-end from the Macro registration export into Mastermind realm enrollment; the draft
  capacity_identity_receipt_digest name is withdrawn. B4 observations are not caller input: extend
  the incumbent provider_capacity build_snapshot -> collect_current_observations source-owned seam
  with a fixed native-realm adapter that acquires the exact current B2/B3 owner fact, binds current
  registration/realm/boot/principal/custody/release/freshness evidence, and fails closed to unknown or
  degraded on stale, forged, cross-host, unavailable or lower-quality input. A public digest proves
  content identity only. Create no account database, observation store, daemon, second normalizer,
  scheduler, claim plane or retry plane. This is records-only author repair; B0 remains HOLD and B1+
  remains unstarted pending fresh checks, new independent paired review and explicit Sol acceptance.
rationale: >
  The prior closed registry allowed only registered while its export and currentness law required
  revoked, so a revoked domain had no truthful current source representation. The B4 wire contained
  source_receipt_digest but did not bind an authenticated acquisition owner, allowing arbitrary
  caller JSON to look structurally valid. B2 also renamed registration_receipt_digest without an
  identity-preserving mapping. The corrected law uses checked-in current state plus accepted release
  history, the current Provider Control source-owned collection seam, and one canonical digest. It
  closes the review findings without adding another authority or persistence plane.
alternatives:
  - option: Remove a registry row to mean revoked
    why_not: Absence cannot distinguish never registered from revoked and destroys deterministic current state.
  - option: Re-register the same capability_generation after revocation
    why_not: It resurrects a terminal generation and makes stale enrollment indistinguishable from current enrollment.
  - option: Add a mutable account or revocation database
    why_not: Checked-in Provider Control source plus accepted release history already owns this fact; another store duplicates authority.
  - option: Accept observation JSON when its source_receipt_digest matches
    why_not: A caller can hash its own content; a public digest does not authenticate producer, scope, host, generation or freshness.
  - option: Mint capacity_identity_receipt_digest in Mastermind
    why_not: Macro already owns registration_receipt_digest; a second digest name creates an unnecessary receipt owner or ambiguous mapping.
  - option: Add a native-observation daemon or receipt ledger
    why_not: The existing provider_capacity source-owned collection seam can acquire the fact without another control or persistence plane.
evidence:
  - "Independent paired review report eda93658073085edb41aa562fc899fac72d5cfe1ff0f39b25b29841256988115; Mastermind comment 5696076603 and Macro comment 5696081725."
  - "Mastermind paired correction docs/superpowers/specs/2026-09-16-ocr2c-family-b-revocation-observation-acquisition-correction.md."
  - "Current Macro engine/provider_capacity.py: build_snapshot() owns current observation collection through collect_current_observations(); callers cannot inject observations into the production builder."
  - "Currentness decision DEC-NATIVE-CLAUDE-FAMILY-B-CURRENTNESS-REALIZATION: public hashes detect content change but do not authenticate callers; current realm execution needs owner-current state."
affects:
  - WS:EXECUTIVE-CAPACITY-FABRIC
  - shared-ai-provider-control
  - mastermind/OCR-2C
  - mastermind/PF1
confidence: high
reversibility: costly
decided_by: ceo-sol
decided_at: 2026-09-16
---

## Candidate precedence

This decision and the paired Mastermind correction supersede only:

1. B1 source rows being fixed to `registration_state = registered`;
2. B2 use of `capacity_identity_receipt_digest` instead of the canonical registration digest;
3. B4 language that leaves observation acquisition open to caller-supplied documents or treats a digest as authentication;
4. B1/B4 test lists that omit the hostile transitions and source-acquisition failures below.

All other Family-B ownership, generation separation, V1/V2, quota-dedup, auth, no-rebuild, CF2 reuse, currentness and no-effect boundaries remain controlling. B2 still returns `REALM_OWNER_REALIZATION_REQUIRED` until the incumbent per-realm current state/write/read boundary is frozen and built.

## B1 current registry contract

The current source remains:

```text
config/provider_native_capabilities.v1.json
schema = mastermind.provider_native_capability_registry/v1
owner_program = shared-ai-provider-control
```

Each closed row contains:

```text
capacity_capability_id
capability_generation
provider = claude
billing_mode = subscription
credential_kind = attached_login
execution_surface = native_cli
registration_state = registered | revoked
```

Exactly one current row exists for each previously registered identity. A revoked row is the terminal current-state tombstone for that generation; row removal is invalid.

```text
never registered -> registered(g)
registered(g)   -> revoked(g)
revoked(g)      -> registered(g2), where g2 > g
```

Provider Control compares the candidate registry to the immediately preceding accepted registry/release identity. It rejects generation reuse/decrement, rollback, source reversion, duplicate or conflicting current rows, missing previously registered identities and resurrection of an older registered generation. Git and accepted release evidence preserve history; no runtime account database is created.

The owner export mirrors the current row and remains:

```text
mastermind.provider_native_capability_registration/v1
capacity_capability_id
capability_generation
provider/billing/credential/execution classification
registration_state = registered | revoked
material_source_digest
registration_receipt_digest
```

A revoked current export is non-executable for new enrollment or work. Historical accepted evidence remains historical and is not rewritten.

Required B1 discriminators:

```text
registered(g) -> revoked(g)
revoked(g) -> registered(g2 > g)
same-generation resurrection refusal
generation decrement/reuse refusal
row-removal refusal after accepted registration
duplicate/conflicting current-row refusal
source-reversion refusal
caller id/generation/state override refusal
deterministic revoked export
V1 Provider Capacity unchanged
```

## One registration digest owner

The canonical field is `registration_receipt_digest` in both repositories. Mastermind B2 consumes the exact current Macro registration document and digest through the approved owner/source-acquisition boundary.

`capacity_identity_receipt_digest` is withdrawn and must be rejected. No alias, mapping table or second digest owner is authorized. B2 tests reject alternate field names, digest/document mismatch, wrong capability generation, revoked current registration and caller-computed substitution.

## B4 fixed source-owned acquisition

The production observation path extends the current Provider Control builder:

```text
build_snapshot()
  -> collect_current_observations()
     -> fixed native-realm observation adapter
  -> strict Provider Capacity V2 normalization
```

`mastermind.provider_native_realm_observation/v1` is a contract between accepted owners, not a public submission API. Production callers may select only the existing builder's reviewed inputs; they cannot provide observation JSON, choose identity/scope/freshness fields or invoke an internal normalization helper as acquisition authority.

The producer is the composed Mastermind B2/B3 owner boundary. Before emission it binds and validates:

```text
current capacity_capability_id + capability_generation
current registration_receipt_digest
current host_ref + boot_ref + realm_generation
enrollment_receipt_digest
os_principal_ref + config_custody_ref
preflight/source receipt identity
producer release/commit + material_source_digest
observed_at + stale_after/freshness
```

Macro's fixed adapter acquires that owner-produced fact from its approved deployment/source boundary and validates every coordinate before normalization. Source/deployment custody and accepted owner receipts authenticate the producer. `source_receipt_digest` is content-integrity evidence only.

On unavailable, ungrounded, stale, wrong-host, wrong-generation, wrong-release or lower-quality source evidence, Provider Control emits the applicable existing unknown/degraded state. It never guesses provider-domain scope or availability.

No new daemon, file/receipt database, mutable observation store, normalizer, scheduler or cross-repository transaction is authorized. Safe fixtures may call internal normalization for tests, but production cannot expose that test seam as caller input.

Required B4 discriminators:

```text
arbitrary caller observation refused
public-digest self-authentication refused
caller-selected provider/host/realm/principal/custody/release refused
registration/enrollment/preflight mismatch refused
cross-host substitution refused
missing/stale/wrong boot_ref and pre-reboot readiness refused
Provider Capacity boot provenance cannot substitute for FP1B admission
stale source/release refused or degraded
producer unavailable -> unknown/degraded
source-quality downgrade cannot become exact/domain-scoped
realm-local failure cannot widen to provider-domain scope
proven domain cooling cannot remain isolated to one host
```

## Corrected gate and next action

The implementation ladder remains B0 through B11. B1 is still the smallest source-only implementation step only after the repaired paired records obtain:

1. fresh exact-head repository checks;
2. fresh current-base/material compatibility;
3. a newly originated independent paired review PASS; and
4. explicit Sol `FAMILY_B_ARCHITECTURE_FROZEN`.

No B1 implementation, capability registration, provider call, login, host mutation, Capacity snapshot, claim, Worker or browser effect is authorized by this decision.