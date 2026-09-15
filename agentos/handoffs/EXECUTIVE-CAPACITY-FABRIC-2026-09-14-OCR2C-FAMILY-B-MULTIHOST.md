---
workstream: WS:EXECUTIVE-CAPACITY-FABRIC
session: sol/ocr2c-family-b-multihost-hardening-20260915
model: sol
ended_because: ci_handoff
mission: >
  Harden the pending OCR-2C Family-B native Claude architecture for the coming multi-Mac fleet so
  one direct subscription can have several host-local executable realms without multiplying its
  provider quota, while reusing the generation owners already protected in Mastermind and preserving
  one Provider-Control capacity identity plus the accepted F0 `(host_ref, capability_id)` slot law.
state_before: >
  The paired Draft/HOLD architecture had already separated a logical provider quota domain from one
  host-local custody, but the multi-host amendment introduced names that collided with current protected
  Mastermind: it called the Macro provider-domain epoch `capacity_generation` even though Mastermind
  already exposes `CapacityOwnerFact.generation` as `capacity_generation`, and it invented a new
  `binding_generation` although `ProviderRealmEnrollmentReceipt.generation` already exists and is
  consumed as `realm_generation`. Current-source archaeology also confirmed Macro
  `capability_manifest.v1` is a metabolism secret-reference broker rather than the correct native
  attached-login registration owner.
changed:
  - path: research/NATIVE_CLAUDE_MULTIHOST_QUOTA_DOMAIN_AMENDMENT_2026-09-14.md
    what: >
      Narrow-precedence correction now uses Provider-Control `capability_generation`, preserves the
      existing provider-realm `realm_generation`, keeps Mastermind Capacity `capacity_generation`
      independent, preserves `(host_ref, capability_id)` slot identity and quota deduplication, and
      freezes B1 as a secret-free Shared AI Provider Control registration rather than a metabolism
      capability-manifest reuse.
  - path: agentos/decisions/DEC-NATIVE-CLAUDE-MULTIHOST-QUOTA-DOMAIN.md
    what: >
      Durable three-owner generation ruling and rejection of `binding_generation`, provider-domain
      `capacity_generation`, host-row quota summation and per-row `capacity_independence`.
  - path: mastermind PR #662 / docs/superpowers/specs/2026-09-14-ocr2c-family-b-multihost-quota-domain-amendment.md
    what: >
      Paired consumer/custody amendment with the same incumbent-owner alignment, Provider Capacity V2
      field correction, B1 registration-owner correction, first four-domain proof boundary, later
      multi-host replication proof and mutation falsifiers.
verified:
  - claim: "Protected Mastermind already has distinct Capacity and provider-realm generations consumed together by subscription canary admission."
    command: "git show 8e25bb32601ef5f40a689da6d6f24149e79e31fa:control_plane/subscription_canary_admission.py && git show 8e25bb32601ef5f40a689da6d6f24149e79e31fa:ops/executive_os/provider_realm_facts.py && git show 8e25bb32601ef5f40a689da6d6f24149e79e31fa:ops/executive_os/capacity_owner_facts.py"
    result: >
      `subscription_canary_admission` seals both `capacity_generation=capacity_fact.generation` and
      `realm_generation=realm_receipt.generation`; provider-realm receipts are owner-sealed and
      CapacityOwnerFact generation is separately owned by Capacity/Model Router.
  - claim: "Accepted Capacity F0 defines slot identity as `(host_ref, capability_id)` and says capacity is observed on a host."
    command: "git show 142c8f6123b2a5da50e1ec95b6d0f7cb2167a009:research/MASTERMIND_EXECUTIVE_CAPACITY_FABRIC_F0_ARCHITECTURE_2026-08-22.md"
    result: >
      The accepted architecture states `capability_id` comes from canonical Provider Control,
      `host_ref` is opaque, duplicate `(host_ref, capability_id)` refuses, provider/account capacity
      is observed on a host, and a login on Mac A is not assumed callable on Mac B.
  - claim: "Current Macro Provider Capacity V1 owner bytes remain materially unchanged through current main despite large unrelated main movement."
    command: "git show 142c8f6123b2a5da50e1ec95b6d0f7cb2167a009:engine/provider_capacity.py"
    result: >
      Current `engine/provider_capacity.py` remains blob `68eda49254003956dd43193ad1284959a0a14593` and is still the strict read-only
      `mastermind.provider_capacity.v1` normalizer; V1 is not patched in place by Family B.
  - claim: "Current Macro capability_manifest is not a native attached-login registration registry."
    command: "git show 142c8f6123b2a5da50e1ec95b6d0f7cb2167a009:config/capability_manifest.yml | head -20"
    result: >
      The file remains `capability_manifest.v1`, owner `metabolism-phase0`, and explicitly brokers
      `secret_ref` names plus lane/tier policy. B1 therefore needs a secret-free native registration
      surface inside Shared AI Provider Control rather than semantic reuse by convenience.
  - claim: "Protected Mastermind movement since the prior Family-B compatibility pin is materially disjoint from Family-B source owners but adds current ACTIVE_EXECUTION procedure law."
    command: "git diff --name-status 42c2688df57007319cb0af231cf5ed29da505ad4..8e25bb32601ef5f40a689da6d6f24149e79e31fa"
    result: >
      Four protected commits add Fabric Job View, ACTIVE_EXECUTION Skillpack law and Portfolio V3
      records plus a Claude settings edit; no Family-B candidate path, provider-realm owner,
      subscription admission or Capacity owner source is changed by that interval.
  - claim: "Exact-head hosted checks were green before the incumbent-generation correction."
    command: "gh api repos/mastermindx-market-intelligence/Mastermind/actions/runs/34939732300 --jq '.conclusion' && gh api repos/mastermindx-market-intelligence/macro/actions/runs/34940128340 --jq '.conclusion' && gh api repos/mastermindx-market-intelligence/macro/actions/runs/34940128671 --jq '.conclusion'"
    result: >
      Returned success for Mastermind CI and success for Macro fences plus Macro CI at the predecessor
      heads. New exact-head checks after this correction remain required; historical green is not reused
      as exact-head acceptance.
unverified:
  - claim: "The paired Family-B architecture, including the corrected generation vocabulary, is independently accepted or protected."
    what_would_verify: >
      Fresh independent cross-repository review of the exact current heads, current merge-ref/material
      compatibility, exact-head CI and Agent OS validation, followed by explicit Sol source release.
      The candidates remain Draft/HOLD.
  - claim: "A `/login` credential on every future Mac survives real unattended reboot/headless security-session access."
    what_would_verify: >
      Installed-version, per-host `COLD_BOOT_AUTH_PASS` composed with canonical host-recovery readiness.
      Provider issue history shows credential isolation/restart behavior has varied, so docs and
      pre-reboot auth status are insufficient.
  - claim: "Different native Claude capacity ids are independent/additive Max quota pools."
    what_would_verify: >
      A future separately accepted safe relationship source. Family-B V2 explicitly makes no numeric
      cross-domain fleet entitlement claim.
unresolved:
  - "Exact V2 public representation of domain-scoped provider observations versus effective host-row health remains a B4 implementation-contract detail; scope preservation and quota dedup are frozen, but no second quota store is allowed."
  - "B5 must decide the smallest reviewed bridge from Provider Capacity V2 provenance to the existing CapacityOwnerFact without repurposing its `capacity_generation`; if existing owner facts cannot bind required provenance, use a versioned successor."
  - "The canonical Executive review ingress still returns 401 Manual reauthentication required. The same existing Slack Capacity placement child remains pre-START and no numbered account is substituted."
next_actions:
  - >
    Run fresh exact-head Macro Agent OS/fence/CI and Mastermind CI on the corrected records; repair only
    deterministic candidate-owned failures.
  - >
    Continue the same independent-review placement child on carrier `C0BSBM78V1N/1789456126.495979`.
    Any reviewer must attack the three-generation owner separation, quota dedup/cooling scope,
    secret-free B1 registration owner, unattended auth/reboot behavior and no-rebuild boundaries.
  - >
    Only after FAMILY_B_ARCHITECTURE_FROZEN, start B1 with a secret-free Shared AI Provider Control
    `capacity_capability_id + capability_generation` registration/export contract. Keep one host realm
    per domain for the first four-domain canary; multi-host replication is later.
do_not_redo:
  - "Do not create one capability/account id per Mac for the same logical provider quota domain."
  - "Do not create binding_generation beside the protected provider-realm realm_generation."
  - "Do not repurpose Mastermind CapacityOwnerFact capacity_generation as Macro provider-domain identity."
  - "Do not sum provider quota across host rows."
  - "Do not broaden a host-local auth/binary/transport failure to all replicas without domain-scoped evidence."
  - "Do not keep the old row-level capacity_independence boolean; the amendment supersedes it."
  - "Do not put native attached-login registrations into metabolism capability_manifest.v1 by convenience."
  - "Do not merge/rebase current main into the records carrier merely to remove behind state."
danger_areas:
  - "Three generation names now intentionally represent three owners; equality of integer values is not identity or provenance."
  - "One account replicated across several Macs increases execution locality/concurrency but not provider quota; the scheduler must never learn the opposite from row count."
  - "A usage-limit response can be provider-domain scoped while an auth/keychain failure may be host-local; incorrect scope propagation either wastes healthy fleet capacity or overloads a cooled account."
  - "A provisioning operator moving one host from logical account A to B must rebind that host to B's capacity id; treating it as an A realm refresh corrupts provider-capacity identity."
exact_next_action: >
  Validate the corrected exact heads, then obtain independent paired architecture review; do not start
  provider registration, account enrollment or B1 implementation until the review/protection gate is satisfied.
---
