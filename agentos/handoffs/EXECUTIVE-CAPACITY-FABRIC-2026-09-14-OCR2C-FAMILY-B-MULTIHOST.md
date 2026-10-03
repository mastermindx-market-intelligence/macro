---
workstream: WS:EXECUTIVE-CAPACITY-FABRIC
session: sol/ocr2c-family-b-current-source-reconciliation-20260915
model: sol
ended_because: ci_handoff
mission: >
  Reconcile the pending OCR-2C Family-B native Claude architecture with current protected generation
  owners and the accepted production CF2 claim path before independent review, while preserving one
  Provider-Control provider identity, one provider-realm owner, one Executive claim plane and honest
  multi-host quota semantics.
state_before: >
  The paired Draft/HOLD architecture had separated provider quota domain from host custody, but used
  names/bridges that current source proves unsafe: Macro provider-domain epoch was called
  `capacity_generation` even though Mastermind already uses that for `CapacityOwnerFact.generation`;
  a new `binding_generation` duplicated protected provider-realm `realm_generation`; and the B5 plan
  implied `CapacityOwnerFact` should become the production Provider Capacity V2 placement bridge even
  though accepted CF2-F owns production acquisition/join/claim evidence separately.
changed:
  - path: research/NATIVE_CLAUDE_MULTIHOST_QUOTA_DOMAIN_AMENDMENT_2026-09-14.md
    what: >
      Narrow-precedence correction now uses Provider-Control `capability_generation`, incumbent
      provider-realm `realm_generation`, preserves canary `capacity_generation`, keeps quota dedup at
      provider-domain scope, freezes a secret-free B1 registration owner and routes B5 through the
      accepted CF2 V2 acquisition/join/atomic-claim path.
  - path: agentos/decisions/DEC-NATIVE-CLAUDE-MULTIHOST-QUOTA-DOMAIN.md
    what: >
      Durable ruling rejecting new `binding_generation`, provider-domain reuse of `capacity_generation`,
      production placement through `CapacityOwnerFact`, host-row quota summation and per-row
      `capacity_independence`.
  - path: mastermind PR #662 / docs/superpowers/specs/2026-09-14-ocr2c-family-b-multihost-quota-domain-amendment.md
    what: >
      Paired consumer/custody correction with the same incumbent generation-owner and CF2 claim-path
      alignment, B1 registration-owner correction, later multi-host proof and hostile falsifiers.
verified:
  - claim: "Protected Mastermind already has distinct provider-realm and canary Capacity generations."
    command: "git show 8e25bb32601ef5f40a689da6d6f24149e79e31fa:control_plane/subscription_canary_admission.py && git show 8e25bb32601ef5f40a689da6d6f24149e79e31fa:ops/executive_os/provider_realm_facts.py && git show 8e25bb32601ef5f40a689da6d6f24149e79e31fa:ops/executive_os/capacity_owner_facts.py"
    result: >
      Subscription canary admission seals `capacity_generation=capacity_fact.generation` and
      `realm_generation=realm_receipt.generation`; the two facts have separate owner seams.
  - claim: "CapacityOwnerFact is not the protected production CF2 claim contract."
    command: "git grep -n 'CapacityOwnerFact' 8e25bb32601ef5f40a689da6d6f24149e79e31fa -- '*.py'"
    result: >
      References are confined to the fact definition, Model Router mint/verify seam,
      subscription_canary_admission and tests. No accepted CF2 production placement path consumes it.
  - claim: "Accepted CF2 production source law joins Macro provider capacity to realm-local readiness at `(host_ref, capacity_capability_id)` and persists evidence through the existing atomic claim path."
    command: "git show 8e25bb32601ef5f40a689da6d6f24149e79e31fa:research/MASTERMIND_EXECUTIVE_CAPACITY_CF2F_CLAIM_EVIDENCE_AND_ACQUISITION_FREEZE_2026-08-25.md"
    result: >
      The frozen architecture explicitly shows strict CF1 Provider Capacity + relevant worker-broker
      realm observations -> immutable `(host_ref, capacity_capability_id)` join -> strict consumer/rank
      -> existing atomic JOB_CLAIMED evidence, with Macro remaining the sole normalizer.
  - claim: "Current Macro Provider Capacity V1 and related material owner files remain byte-stable through the inspected current main despite large unrelated movement."
    command: "git show 142c8f6123b2a5da50e1ec95b6d0f7cb2167a009:engine/provider_capacity.py && git show 142c8f6123b2a5da50e1ec95b6d0f7cb2167a009:config/capability_manifest.yml"
    result: >
      `engine/provider_capacity.py` remains blob `68eda49254003956dd43193ad1284959a0a14593`; capability manifest remains blob
      `14cb9f81545de02f596f49f36f3f48e02d7851ce` and is still the metabolism secret-reference broker.
  - claim: "Protected Mastermind movement since the prior Family-B compatibility pin is candidate/owner-path disjoint while adding current ACTIVE_EXECUTION procedure law."
    command: "git diff --name-status 42c2688df57007319cb0af231cf5ed29da505ad4..8e25bb32601ef5f40a689da6d6f24149e79e31fa"
    result: >
      The four commits add Fabric Job View, ACTIVE_EXECUTION Skillpack law, Portfolio V3 records and a
      Claude settings edit without changing Family-B candidate docs, provider-realm facts,
      subscription canary admission or Capacity owner facts.
  - claim: "Pre-correction candidate heads had green hosted checks, but current corrected heads require new exact-head checks."
    command: "gh api repos/mastermindx-market-intelligence/Mastermind/actions/runs/34939732300 --jq '.conclusion' && gh api repos/mastermindx-market-intelligence/macro/actions/runs/34940128340 --jq '.conclusion' && gh api repos/mastermindx-market-intelligence/macro/actions/runs/34940128671 --jq '.conclusion'"
    result: >
      Historical exact-head checks returned success; corrections advanced both heads, so those greens
      are evidence history only and cannot authorize current-head acceptance.
unverified:
  - claim: "The paired Family-B architecture is independently accepted or protected."
    what_would_verify: >
      Fresh independent cross-repository review of exact current heads, latest-base/material
      compatibility, fresh exact-head CI/fences and explicit Sol source release. Candidates remain Draft/HOLD.
  - claim: "A `/login` credential on every future Mac survives real unattended reboot/headless security-session access."
    what_would_verify: >
      Installed-version per-host `COLD_BOOT_AUTH_PASS` composed with canonical host-recovery readiness.
  - claim: "Different native Claude provider-capability ids are independent/additive Max quota pools."
    what_would_verify: >
      A future accepted relationship source. Family-B V2 intentionally makes no numeric fleet-total claim.
unresolved:
  - "Exact V2 public representation of provider-domain observations versus effective host-row health remains a B4 implementation detail; scope preservation and quota dedup are frozen without a second quota store."
  - "Exact additive fields/version for the existing CF2 claim evidence successor are a B5 implementation-contract detail, but its owner/path are now frozen: existing source acquisition + `(host_ref, capacity_capability_id)` join + existing atomic claim/replay plane."
  - "Canonical Executive review ingress still returns 401 Manual reauthentication required. The same Slack Capacity placement child remains pre-START; no numbered account is substituted."
next_actions:
  - >
    Run fresh exact-head Macro Agent OS/fence/CI and Mastermind CI on the corrected records; repair only
    deterministic candidate-owned failures.
  - >
    Continue the same independent-review placement child on carrier `C0BSBM78V1N/1789456126.495979`.
    Reviewer must attack the three-generation owner separation, B5 CF2 claim-path reuse, quota
    dedup/cooling scope, B1 secret-free registration owner, unattended auth/reboot and no-rebuild law.
  - >
    Only after FAMILY_B_ARCHITECTURE_FROZEN, start B1 with secret-free Shared AI Provider Control
    `capacity_capability_id + capability_generation` registration/export. Keep one host realm per domain
    for the first four-domain canary; multi-host replication remains later.
do_not_redo:
  - "Do not create one capability/account id per Mac for one provider quota domain."
  - "Do not create binding_generation beside protected realm_generation."
  - "Do not repurpose canary CapacityOwnerFact capacity_generation as Macro provider-domain identity."
  - "Do not promote CapacityOwnerFact into the production CF2 placement contract."
  - "Do not sum provider quota across host rows."
  - "Do not broaden host-local failures across replicas without domain-scoped evidence."
  - "Do not keep row-level capacity_independence."
  - "Do not put native attached-login registrations into metabolism capability_manifest.v1 by convenience."
  - "Do not merge/rebase current main merely to remove behind state."
danger_areas:
  - "Provider capability generation, provider-realm generation and canary Capacity generation intentionally have different owners; equality of integer values proves nothing."
  - "One account replicated across Macs adds execution locality/concurrency, not provider entitlement."
  - "Incorrect provider-domain vs realm-local failure scope either wastes healthy replicas or overloads a cooled domain."
  - "A new placement/evidence bridge would duplicate accepted CF2 authority; B5 must extend the existing claim plane."
exact_next_action: >
  Validate corrected exact heads, then obtain independent paired architecture review; do not start B1,
  provider enrollment or any live Claude effect until review/protection gate passes.
---
