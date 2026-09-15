---
workstream: WS:EXECUTIVE-CAPACITY-FABRIC
session: sol/ocr2c-family-b-multihost-hardening-20260914
model: sol
ended_because: ci_handoff
mission: >
  Harden the pending OCR-2C Family-B native Claude architecture for the coming multi-Mac fleet so
  one direct subscription can have several host-local executable bindings without multiplying its
  provider quota, while preserving one Provider-Control capacity identity and the accepted F0
  `(host_ref, capability_id)` slot law.
state_before: >
  The paired Draft/HOLD architecture had already corrected the primary identity owner: Macro Shared AI
  Provider Control owned `capacity_capability_id + realm_generation`, and Mastermind only bound native
  custody. Deeper F0 archaeology then exposed a future fleet ambiguity: F0 slot identity is the pair
  `(host_ref, capability_id)`, so the same logical capacity can appear on several Macs, but the Family-B
  draft still overloaded one generation for provider capacity and host-local credential custody and had
  an underspecified per-row `capacity_independence` boolean.
changed:
  - path: research/NATIVE_CLAUDE_MULTIHOST_QUOTA_DOMAIN_AMENDMENT_2026-09-14.md
    what: >
      Narrow-precedence owner amendment splitting `capacity_generation` from host-local
      `binding_generation`, preserving `(host_ref, capability_id)` slot identity, scoping quota/cooling
      evidence, and prohibiting host-row quota aggregation.
  - path: agentos/decisions/DEC-NATIVE-CLAUDE-MULTIHOST-QUOTA-DOMAIN.md
    what: >
      Durable two-axis ruling: one Provider-Control logical quota domain may have multiple host bindings;
      binding generation is a correction epoch, not a second account identity; the old row-level
      `capacity_independence` proposal is superseded.
  - path: mastermind PR #662 / docs/superpowers/specs/2026-09-14-ocr2c-family-b-multihost-quota-domain-amendment.md
    what: >
      Paired consumer/custody amendment with the exact provider-realm V2 field correction, placement law,
      first four-domain proof boundary, later multi-host replication proof, and mutation falsifiers.
verified:
  - claim: "Accepted Capacity F0 already defines slot identity as `(host_ref, capability_id)` and says capacity is observed on a host."
    command: "git show b65dba67cfe7835c6200f6054d958d2bc1a16022:research/MASTERMIND_EXECUTIVE_CAPACITY_FABRIC_F0_ARCHITECTURE_2026-08-22.md"
    result: >
      The accepted architecture states `capability_id` comes from canonical Provider Control, `host_ref`
      is opaque, duplicate `(host_ref, capability_id)` refuses, provider/account capacity is observed on
      a host, and a login on Mac A is not assumed callable on Mac B.
  - claim: "Current V1 implementation final slot uniqueness is `(host_ref, capability_id)` even though its current source-observation builder is still single-host/capability keyed."
    command: "git show b65dba67cfe7835c6200f6054d958d2bc1a16022:engine/provider_capacity.py"
    result: >
      `_build_snapshot_from_observations` currently indexes source observations by capability id, while
      normalized slot identity includes `host_ref` and final duplicate checking uses `(host_ref, capability_id)`.
      Family B therefore requires a versioned V2 source evolution rather than changing V1 in place.
  - claim: "Protected Mastermind remained 42c2688df57007319cb0af231cf5ed29da505ad4 during this hardening pass."
    command: "gh api repos/mastermindx-market-intelligence/Mastermind/git/ref/heads/master --jq '.object.sha'"
    result: "Returned 42c2688df57007319cb0af231cf5ed29da505ad4."
  - claim: "Macro main is moving independently of this records carrier, so compatibility must use an action-time read rather than a frozen 'current main' assertion."
    command: "gh api repos/mastermindx-market-intelligence/macro/git/ref/heads/main --jq '.object.sha'"
    result: >
      A fresh re-read returned 1ab0f35ca4d3eac45c5983bb91742a68dd898513 after earlier reads had already
      observed intervening main heads. Current protected procedure therefore requires action-time material-source/
      latest-merge-ref compatibility evidence; the candidate branch was not rebased or merged merely to erase behind state.
unverified:
  - claim: "The paired Family-B architecture, including the multi-host amendment, is independently accepted or protected."
    what_would_verify: >
      Fresh independent cross-repository review of the exact current heads, current merge-ref/CI and Agent OS
      validation, followed by explicit Sol source-release/protection. The candidates remain Draft/HOLD.
  - claim: "A `/login` credential on every future Mac survives real unattended reboot/headless security-session access."
    what_would_verify: >
      Installed-version, per-host `COLD_BOOT_AUTH_PASS` composed with canonical host-recovery readiness.
      Provider issue history shows config-directory namespacing shipped but Keychain ACL/restart behavior has
      varied, so docs and pre-reboot auth status are insufficient.
  - claim: "Different native Claude capacity ids are independent/additive Max quota pools."
    what_would_verify: >
      A future separately accepted safe relationship source. The current Family-B V2 explicitly makes no
      numeric cross-domain fleet entitlement claim.
unresolved:
  - "Exact V2 public representation of domain-scoped provider observations versus effective host-row health remains an implementation-contract detail for B4; the architecture requires scope preservation and dedup but does not add a second quota store."
  - "The approved Executive research-review ingress is currently inaccessible from this session because the canonical plugin returned 401 Manual reauthentication required. No manual numbered-Claude review placement is substituted."
next_actions:
  - >
    Re-run exact-head Macro Agent OS/fence validation on the new multi-host records and exact-head Mastermind CI
    on the paired amendment; repair only candidate-owned records if a deterministic source/schema failure appears.
  - >
    Obtain independent review through a lawful principal/canonical placement path once available. Review must
    explicitly attack quota deduplication, capacity-vs-binding generation, host-local vs account-domain cooling,
    unattended auth/reboot behavior, and no-rebuild boundaries.
  - >
    Only after FAMILY_B_ARCHITECTURE_FROZEN, start B1 with Provider-Control native capacity identity/generation
    contract. Keep one-host-binding-per-domain for the first four-domain canary; multi-host replication is later.
do_not_redo:
  - "Do not create one capability/account id per Mac for the same logical provider quota domain."
  - "Do not use binding_generation as a second capacity/account id or quota multiplier."
  - "Do not sum provider quota across host rows."
  - "Do not broaden a host-local auth/binary/transport failure to all replicas without domain-scoped evidence."
  - "Do not keep the old row-level capacity_independence boolean; the amendment supersedes it."
  - "Do not merge/rebase current main into the records carrier merely to remove behind state."
danger_areas:
  - "One account cloned across several Macs increases execution locality/concurrency but not provider quota; the scheduler must never learn the opposite from row count."
  - "A usage-limit response can be account-domain scoped while an auth/keychain failure may be host-local; incorrect scope propagation either wastes healthy fleet capacity or overloads a cooled account."
  - "A provisioning operator moving one host from logical account A to B must rebind that host to B's capacity id; treating it as an A binding refresh corrupts provider-capacity identity."
exact_next_action: >
  Validate the new exact heads, then hold at independent paired architecture review; do not start provider
  enrollment or B1 implementation until the review/protection gate is satisfied.
---
