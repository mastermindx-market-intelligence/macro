---
key: NATIVE-CLAUDE-REALM-CAPACITY-FAMILY-B-V2
question: >
  After OCR-2C Family A proved that native Claude realms cannot be safely equated to existing
  numbered Macro claude_code_oauth_N slots, how should direct claude.ai Claude Code subscription
  realms acquire canonical capacity identity so Executive Capacity Fabric can eventually route
  among them without provider PII, secret fingerprints, ordinal guessing or a second quota plane?
answer: >
  Use OCR-2C Family B. Extend the existing Shared AI Provider Control owner with one opaque
  Provider-Control-owned capacity_capability_id plus owner-issued realm_generation for each
  managed native Claude capability. Mastermind consumes that exact coordinate and binds it to
  one host_ref, OS-principal and opaque config-custody reference through a versioned successor
  of the existing provider-realm receipt pattern; Mastermind does not mint another capacity/account
  realm id. Native host observations flow back into Macro through one secret-free versioned source
  wire, and Macro alone normalizes them into mastermind.provider_capacity.v2. Preserve
  mastermind.provider_capacity.v1 unchanged for existing consumers. Distinct capability/custody
  realms do not imply independent Anthropic quota pools; capacity independence stays unknown unless
  separately accepted evidence proves it, so realm count cannot inflate aggregate quota.
rationale: >
  Family A's refusal is the correct result: config paths, app labels, plan names and numbered OAuth
  slots are not provider-supported rotation-safe subscription identity. Family B avoids that join
  entirely by making the company capacity owner issue the opaque capability coordinate. This keeps
  the current ownership law intact: Macro owns provider/capacity identity and normalization, Model
  Router owns suitability, Executive OS owns lifecycle/claim/effect reconciliation, and HF1/OCR-4A
  own execution mechanics. Current Claude Code config-directory-specific credential/Keychain
  isolation is useful for custody but cannot prove provider-account identity or quota independence.
  Versioning the projection rather than patching v1 preserves existing consumers and the accepted
  unknown/null/freshness semantics.
alternatives:
  - option: Map claude-pro-01..04 to claude_code_oauth_1..4
    why_not: >
      Family A falsified the needed equality and rotation-invalidation witness. Ordinal equality is
      operator convention, not provider capacity identity.
  - option: Let Mastermind mint a separate native realm id and have Macro map it later
    why_not: >
      Creates competing provider/account identity owners and forces a second cross-owner mapping.
      Provider Control already owns capacity_capability_id; native Claude should reuse that coordinate.
  - option: Use CLAUDE_CONFIG_DIR or a hash of its path as the realm id
    why_not: >
      A config directory identifies local credential custody, not an Anthropic subscription. Raw or
      reversible path identity also leaks host-local structure and still cannot prove quota independence.
  - option: Persist account email/id or a token fingerprint to prove distinct accounts
    why_not: >
      Violates the secret/PII boundary and creates sensitive durable identity state solely to support
      routing. Provider account identity may remain opaque while company capability identity stays safe.
  - option: Patch mastermind.provider_capacity.v1 in place
    why_not: >
      Changes a protected closed contract and its material-source semantics underneath existing H0/P0/
      CF2-I consumers. Native realm generation requires an explicit versioned evolution.
evidence:
  - "Mastermind OCR-2C plan on protected 36f74c02: Family A refusal requires Family B versioned Shared AI Provider Control evolution; v1 stays unchanged."
  - "Mastermind native-Claude-capacity identity amendment: native Worker realm is not automatically a Macro claude_code_oauth_N capability; Provider Control remains the normalizer."
  - "Macro engine/provider_capacity.py at current main ancestry: v1 slot identity is capability_id + host_ref with explicit health/cooling/quota/outcome evidence and strict unknown/freshness laws."
  - "Claude Code current authentication documentation: CLAUDE_CONFIG_DIR changes credential-file location and macOS Keychain key, establishing local custody isolation but not provider account identity."
  - "Mastermind PR #662 candidate head 8ed986a814b1eef9e4818c900683fd27fa1a35f1: consumer architecture preserves Provider Control identity ownership and separates persistent Operator/browser/GUI work."
affects:
  - WS:EXECUTIVE-CAPACITY-FABRIC
  - shared-ai-provider-control
  - mastermind/OCR-2C
  - mastermind/PF1
confidence: high
reversibility: costly
decided_by: ceo-sol
decided_at: 2026-09-14
---

## Consequences

The first implementation step after this decision is protected and independently reviewed is the
Provider-Control identity/generation contract, not a provider login and not a Claude adapter rewrite.
The owner should use the existing capability-definition/config family or a reviewed successor instead
of creating a runtime account registry. A typed registration receipt may export the owner-issued
capability coordinate to Mastermind; it is an owner fact, not lifecycle state.

`mastermind.provider_capacity.v2` should retain the V1 top-level semantic model and existing slot
fields while adding a closed native `realm_binding` containing only generation, enrollment-receipt
digest and capacity-independence state. For native Claude rows, the normal `capability_id` is the
Provider-Control native capability key; there is no second realm/account identifier.

This decision does not mark Family B implemented, installed, routed or production-proven. Until the
cross-repository architecture is independently accepted and protected, capability state remains
`SPEC_ONLY / RECORDS_ONLY / PRODUCTION_INERT`.
