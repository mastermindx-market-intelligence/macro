---
workstream: WS:EXECUTIVE-CAPACITY-FABRIC
session: sol/ocr2c-family-b-current-source-reconciliation-20260915
model: sol
ended_because: ci_handoff
mission: >
  Continue the Chairman-approved migration of Claude/Fable orchestration from cloned macOS apps into
  canonical Agent Fabric by freezing OCR-2C Family B against current protected owners: one
  Provider-Control provider-capability identity/generation, one incumbent provider-realm generation,
  one accepted CF2 production claim path and honest multi-host quota semantics.
state_before: >
  Family A had safely refused ordinal/native-to-OAuth equality. The first Family-B records correctly
  kept Macro as provider/capacity owner but contained stale architecture assumptions discovered by
  current-source archaeology: they overloaded generation names, introduced `binding_generation`
  beside protected `realm_generation`, treated the metabolism secret-ref capability manifest as a
  likely native registration owner, implied `CapacityOwnerFact` could bridge production V2 placement,
  and treated newer Claude auth options as more authoritative than protected PF1/OCR-1 source law.
changed:
  - path: research/NATIVE_CLAUDE_REALM_PROVIDER_CONTROL_V2_ARCHITECTURE_2026-09-14.md
    what: >
      Reconciled primary architecture defining `capacity_capability_id + capability_generation`, exact
      secret-free B1 registry/export, incumbent provider-realm V2, scoped native observations,
      Provider Capacity V2, canonical CF2 B5 join/claim reuse, protected first-production auth boundary,
      exact implementation owner surfaces and hostile falsifiers.
  - path: agentos/decisions/DEC-NATIVE-CLAUDE-REALM-CAPACITY-FAMILY-B-V2.md
    what: >
      Reconciled durable decision preserving Macro provider identity, provider-realm `realm_generation`,
      canary `capacity_generation`, accepted CF2 production claim ownership and `/login` OS-principal law.
  - path: research/NATIVE_CLAUDE_MULTIHOST_QUOTA_DOMAIN_AMENDMENT_2026-09-14.md
    what: >
      Multi-host amendment freezes quota-domain deduplication, provider-domain vs realm-local evidence
      scope, B1 registration ownership and B5 production claim reuse.
  - path: agentos/decisions/DEC-NATIVE-CLAUDE-MULTIHOST-QUOTA-DOMAIN.md
    what: >
      Durable rejection of host-row quota multiplication, new binding generation, provider-domain use
      of canary capacity generation, CapacityOwnerFact production promotion and row-level independence.
  - path: mastermind PR #662
    what: >
      Paired Mastermind primary design plus narrow amendments now preserve the same owner/generation,
      B5 CF2 claim path and protected first-production auth rules.
  - path: agentos/decisions/DEC-NATIVE-CLAUDE-FAMILY-B-BOOT-CURRENTNESS-PHYSICAL-COMPOSITION.md
    what: >
      Corrects B3/B4 readiness to bind exact current boot_ref and makes B5 separately consume incumbent
      FP1B host/boot/pool qualification plus fresh capacity/pressure evidence without a duplicate physical owner.
verified:
  - claim: "Current protected Mastermind exposes distinct provider-realm and subscription-canary Capacity generations."
    command: "git show 8e25bb32601ef5f40a689da6d6f24149e79e31fa:control_plane/subscription_canary_admission.py && git show 8e25bb32601ef5f40a689da6d6f24149e79e31fa:ops/executive_os/provider_realm_facts.py && git show 8e25bb32601ef5f40a689da6d6f24149e79e31fa:ops/executive_os/capacity_owner_facts.py"
    result: >
      Subscription canary admission binds `realm_generation=realm_receipt.generation` and separately
      `capacity_generation=capacity_fact.generation`; the facts have different canonical owners.
  - claim: "Accepted production CF2 law is Provider Capacity plus realm readiness joined at `(host_ref, capacity_capability_id)` before the existing atomic claim/replay path."
    command: "git show 8e25bb32601ef5f40a689da6d6f24149e79e31fa:research/MASTERMIND_EXECUTIVE_CAPACITY_CF2F_CLAIM_EVIDENCE_AND_ACQUISITION_FREEZE_2026-08-25.md"
    result: >
      The frozen architecture keeps Macro as sole provider normalizer and joins strict provider-capacity
      evidence with realm-local readiness before deterministic ranking and existing JOB_CLAIMED evidence.
  - claim: "Current Macro capability_manifest is not the native attached-login registration owner."
    command: "git show 142c8f6123b2a5da50e1ec95b6d0f7cb2167a009:config/capability_manifest.yml | head -20"
    result: >
      It remains `capability_manifest.v1`, owner `metabolism-phase0`, with secret-ref and lane/tier
      semantics; Family B therefore freezes a separate secret-free Shared AI Provider Control registry.
  - claim: "Current Macro Provider Capacity V1 implementation stayed byte-stable through the inspected main movement."
    command: "git show 142c8f6123b2a5da50e1ec95b6d0f7cb2167a009:engine/provider_capacity.py | git hash-object --stdin"
    result: "Material file identity remained the previously inspected blob `68eda49254003956dd43193ad1284959a0a14593`; Family B does not patch V1 semantics in place."
  - claim: "Protected first-production Claude auth law remains dedicated OS principal/Keychain with native /login and stronger auth sources denied by preflight."
    command: "git show 8e25bb32601ef5f40a689da6d6f24149e79e31fa:ops/executive_os/claude-worker-preflight.py"
    result: >
      Preflight isolation vocabulary includes `OS_PRINCIPAL_KEYCHAIN` and denies
      `CLAUDE_CODE_OAUTH_TOKEN`, API keys and cloud-provider auth sources; it performs no login/model work.
  - claim: "Current exact candidates remain records-only Draft/HOLD carriers."
    command: "gh pr view 662 -R mastermindx-market-intelligence/Mastermind --json state,isDraft,headRefOid && gh pr view 7162 -R mastermindx-market-intelligence/macro --json state,isDraft,headRefOid"
    result: >
      Both remain OPEN/Draft. Exact heads continue to advance only through this same records carrier as
      reconciliation edits land; final current heads must be re-read before independent review START.
unverified:
  - claim: "The paired Family-B architecture is independently accepted/protected."
    what_would_verify: >
      One independent current-head cross-repository review of Mastermind #662 + Macro #7162, fresh
      latest-base/material compatibility, exact-head repository validation and explicit Sol release.
  - claim: "One real native Claude realm is unattended-production ready."
    what_would_verify: >
      Later B6 real `/login` realm under a dedicated OS principal/Keychain with restart, cold-boot,
      auth-precedence and realm-isolation proof composed with canonical host recovery readiness.
  - claim: "Different provider-capability ids represent numerically independent/additive Max quota."
    what_would_verify: >
      A separately accepted provider-safe relationship source; Family-B V2 intentionally makes no
      fleet-total numeric entitlement claim.
unresolved:
  - "Independent R2 review remains PRE_START on carrier C0BSBM78V1N/1789588297.647319. Replacement exact heads require fresh hosted/current-base gates after the boot-currentness correction; no reviewer has ACKed/STARTed."
  - "Exact B4 implementation decomposition of scoped provider health/cooling/quota normalization remains implementation work after B0 acceptance; architecture already fixes source scope and forbids a second normalizer."
next_actions:
  - >
    Stop architecture churn. Run exact-head Macro fences/CI and Mastermind CI on the final records heads,
    repairing only deterministic candidate-owned failures.
  - >
    Publish the boot-currentness/FP1B composition correction on the existing paired branches, run fresh
    exact-head/current-base gates, then refresh the SAME R2 review carrier; do not create another child
    or manually choose a numbered account.
  - >
    If the independent reviewer returns PASS and latest-base compatibility is clear, Sol may explicitly
    release/protect B0 and record `FAMILY_B_ARCHITECTURE_FROZEN`; only then commission B1.
  - >
    B1 implements the secret-free `config/provider_native_capabilities.v1.json` registry/export only;
    no Claude login/provider call/route/browser/computer-use effect belongs in B1.
do_not_redo:
  - "Do not map native realms to claude_code_oauth_N by ordinal/name/path/plan type."
  - "Do not mint a second Mastermind account/capacity id."
  - "Do not create binding_generation beside protected realm_generation."
  - "Do not repurpose canary CapacityOwnerFact capacity_generation as provider identity or production claim evidence."
  - "Do not use metabolism capability_manifest.v1 as the native attached-login registry."
  - "Do not patch mastermind.provider_capacity.v1 in place."
  - "Do not sum host replicas as provider entitlement."
  - "Do not silently admit setup-token or same-user multi-config auth under current first-production source law."
  - "Do not create a Claude scheduler, account DB, quota DB, retry plane, session registry or second claim ledger."
danger_areas:
  - "Provider-domain, provider-realm and canary Capacity generations intentionally have different owners; integer equality is not provenance."
  - "One provider domain replicated across Macs adds execution locality/concurrency but not provider quota."
  - "Provider-domain usage-limit and realm-local auth/host failure require different propagation semantics."
  - "Historical replay must return accepted claim evidence without re-reading current provider capacity."
exact_next_action: >
  Reconcile the incumbent source writer, publish the boot-currentness/FP1B composition correction on
  the existing paired branches, obtain fresh exact-head/current-base proof, then bind one independent
  reviewer to the existing R2 operation. Do not start B1 or any live Claude effect before B0 protection.
---
