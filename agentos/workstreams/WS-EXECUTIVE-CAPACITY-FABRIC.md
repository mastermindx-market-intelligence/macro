---
key: EXECUTIVE-CAPACITY-FABRIC
title: Executive Capacity Fabric — heterogeneous provider and subscription placement
objective: >
  Let Sol/Fable/Executive OS use the company's real AI capacity as one governed workforce:
  discover usable provider/account capacity without exposing credentials, preserve provider-
  native quota/cooling truth, choose among already-eligible workers deterministically, prefer
  subscription/local capacity where policy permits, preserve frontier reserves, and continue
  safely across quota exhaustion without creating duplicate execution or another lifecycle plane.
status: active
program: shared-ai-provider-control
p0: EXECUTIVE_OS
repos: [macro, mastermind]
owner: ceo-sol
class: build
blast_radius: reversible
ambiguity: scoped
waves:
  - id: F0
    title: Ownership, contract and no-rebuild architecture freeze
    status: done
  - id: CF1
    title: Secret-free provider-capacity projection over existing Macro provider state
    status: done
    pr: 6297
    depends_on: [F0]
    next_action: >
      COMPLETED_DO_NOT_REPEAT. Sol accepted exact head
      fc12904f59a5758817aa2c76ffaa40bb1ebcbf8e after full hosted CI and fences,
      then squash-merged PR #6297 as dcdd939c45b23abce5ba04f95e330ac914a3904b.
      Reopen CF1 only for a concrete defect or material-source change; do not use it as a place
      to implement Executive placement or new providers.
  - id: CF2-F
    title: Freeze Executive claim-time capacity evidence and acquisition against landed schema v4
    status: done
    pr: 150
    depends_on: [CF1]
    next_action: >
      COMPLETED_DO_NOT_REPEAT. Mastermind PR #150 accepted the CF2-F source law and merged as
      e9cb5cbd745b36dc51f54bd83238ec38ef0c80c7. Do not reopen CF2-F merely because the production
      host later refused P0; that refusal correctly created the H0 host-preparation gate.
  - id: CF2-H0
    title: Grounded CF1 source and inert three-realm host preparation
    status: in_progress
    depends_on: [CF2-F]
    next_action: >
      SOURCE_REPAIR_RELEASED_DO_NOT_REPEAT. Mastermind PR #213 repaired the current-carrier versus
      immutable-repair provenance split on the single canonical H0 carrier and source-released the
      final authenticated v3 H0 material as protected
      229aebce5e8d0c1c7372f5fead9c24516b027cc1 after full repository test, CodeQL/static and exact-head
      Sol review. That SHA remains the immutable REPAIR_MERGE_SHA unless a later separately accepted
      H0 source-repair release supersedes it. Source transport is BUILT_NOT_PROVEN / PRODUCTION_INERT,
      not native acceptance. At every native attempt re-pin CURRENT protected Mastermind rather than
      freezing the historical release as the carrier. At the 2026-09-13 record repair protected master is
      89d890f0ae526205e762ad2924b6590f35847e8f, which sits 152 commits past the previous
      dfd69451dce5e186ce05f65446023fbe21f07a58 pin (that pin is an ancestor of it) through source merges
      including RF1 #449, CAP-C2 #415, OCR-1 #453 and HF1-A #471. Repair ANCESTRY still holds at this pin —
      229aebce5e8d0c1c7372f5fead9c24516b027cc1 is an ancestor of 89d890f0ae526205e762ad2924b6590f35847e8f —
      but the five-path mode/blob EQUALITY half of the reproof was not re-run by this records-only repair, so
      89d890f0ae526205e762ad2924b6590f35847e8f is a verified protected-master pin and NOT a proven
      CARRIER_COMMIT_SHA. REPAIR_MERGE_SHA remains
      229aebce5e8d0c1c7372f5fead9c24516b027cc1. Before any v3 build or root action, re-prove the current
      carrier is a protected descendant of the immutable repair and that all five authenticated H0
      Git mode/blob rows are exactly equal at both pins. If protected master advances again, advance
      only CARRIER_COMMIT_SHA after that same reproof; never relabel the immutable repair. Then use
      accepted Macro dcdd939c45b23abce5ba04f95e330ac914a3904b, build the final v3 carrier and run
      exactly one bounded administrator ceremony from the reviewed runbook. Require source-repair PASS,
      two verify-only H0_INSTALLED_HOST_PASS_NOT_P0_ACCEPTED receipts, empty stderr, disposable
      root-carrier absence and all three broker labels disabled/unloaded with sockets absent. STOP for
      independent CF2-P0. No OAuth/device login, provider call, routing, services, workers or CF2-I is
      authorized by H0.
  - id: CF2-P0
    title: Independent post-H0 installed-host acquisition census
    status: todo
    depends_on: [CF2-H0]
    next_action: >
      After exact H0 installed-host PASS under the repaired/current runbook, rerun the accepted read-only
      CF2-P0 census. Only an exact accepted P0 result may release capacity-aware Executive composition.
      If P0 again refuses, preserve the refusal and return to Sol; do not bypass it with a user checkout,
      stale socket, anonymous fetch or new acquisition service.
  - id: CF2-I
    title: Executive capacity-aware placement using the reviewed claim receipt
    status: todo
    depends_on: [CF2-P0]
    next_action: >
      Only after CF2-P0 accepts the grounded acquisition path, consume
      `mastermind.provider_capacity.v1` after Model Router and Executive hard eligibility filters,
      rank eligible candidates deterministically, persist accepted capacity evidence atomically
      with JOB_CLAIMED, and prove one existing-provider / multi-account canary. Do not start before
      P0 acceptance.
  - id: OCR-2C
    title: Native Claude realm to canonical Provider Control capacity identity
    status: in_progress
    depends_on: [CF1]
    next_action: >
      Family A same-subscription-twin proof has returned a successful falsifier refusal at the evidence-
      vocabulary gate: current native Claude auth evidence does not expose a documented, provider-supported,
      secret-free stable subscription/enrollment identity suitable for equality, and the existing Macro
      claude_code_oauth_N capability IDs are static owner slot identities whose credential replacement does
      not itself change the capability ID or publish a non-secret enrollment generation. Therefore record
      FAMILY_A_NO_SAFE_EQUALITY_WITNESS and FAMILY_A_NO_ROTATION_INVALIDATION; do not run a guessed one-realm
      binding and never equate native realm labels to numbered Macro OAuth slots. Family B architecture may
      be designed in parallel, but because it is a new cross-repository contract it must be explicitly
      reviewed/approved and frozen before any runtime implementation. Preserve provider_capacity.v1 and the
      current H0/P0/CF2-I contract unchanged while that architecture is developed.
  - id: RF1
    title: Provider-neutral Model Router suitability equivalence
    status: done
    pr: 449
    depends_on: [CF2-I]
    next_action: >
      COMPLETED_DO_NOT_REPEAT. Mastermind PR #449 landed the provider-neutral Model Router ordered
      suitability tiers and merged as cc03ea329148a44b048b65a4649481d637980dd3 on 2026-09-04; that merge
      commit is an ancestor of protected master 89d890f0ae526205e762ad2924b6590f35847e8f. This is SOURCE
      CAPABILITY ONLY: no capacity-ranked claim, Worker execution, provider call or production canary was
      observed, so automatic heterogeneous placement stays unproven until CF2-P0 and CF2-I accept it. Do
      not resurrect RF1 as unfinished; reopen only for a concrete defect or a material router-source
      change. Standing law it leaves behind: before any new provider is admitted to the same Executive
      task routes as an existing provider, suitability must stay provider-neutral ordered tiers or
      equivalent execution classes, capacity may rank only within the first lawful equivalence tier, and
      concrete alias/file order must never become a vendor scheduler.
  - id: HF1
    title: Provider-neutral worker harness and broker contract
    status: in_progress
    depends_on: [CF2-I]
    next_action: >
      Umbrella wave. Slice HF1-A is protected (below); slices HF1-B, HF1-C and HF1-D are the open
      Mastermind carriers #576, #578, #581 and #583 listed under "Wave 1 open carriers" in this record,
      driven by the Fable principal integration
      agent-fabric-end-to-end-fable-integration-20260913-sol-001. Continue to generalize the existing
      WorkerExecutionAdapter/broker boundary without breaking current Codex P1B/OHF semantics: extract
      truly common execution request/receipt law, keep provider homes/auth/session mechanics
      adapter-private, prove one synthetic non-Codex adapter through the same broker lifecycle, and
      create no provider-specific broker or lifecycle plane. #581 has since MERGED as
      27a5d893ca28f7006c1007dffa51e677c9c7a4ab ("[HF1-D] Add fixed-profile Claude subscription worker").
      Despite its title it is the Claude Code HARNESS for the three third-party subscription providers in
      config/subscription_provider_profiles.v1.json — glm-coding-plan, alibaba-token-plan-personal,
      minimax-token-plan — registered as adapter `claude-compatible-subscription`. It is NOT the native
      Anthropic vertical and is NOT PF1 progress (Sol R21: never treat a #581 merge as native readiness).
      #575 has since MERGED as 91dbdf876f1f1ea10d24342b9d4ea49ba081bfcc ("[ACP] Qualify provider-free
      SDK boundary and conformance"). It establishes the provider-free ACP SDK boundary; that merge
      commit is an ancestor of protected bf843961c0e1b5bd45fa481f0138c71f2a87d4e2 by 57 commits.
      Merged is not proven. #579 has since MERGED as 3a8cc8b007c4573bd01efd909bf6d0e786c71663
      ("[ACP] Bind guarded native ACP worker to common receipts"). It binds the guarded native ACP
      worker to the common worker receipts; that merge commit is an ancestor of protected
      bf843961c0e1b5bd45fa481f0138c71f2a87d4e2 by 52 commits. Merged is not proven. #576 has since
      MERGED as cb95ae8bf76382df14d1017691e4ccc0b6356f7c ("[HF1-B] Configure worker broker by
      provider-neutral adapter"). It configures the existing worker broker by provider-neutral adapter
      identity; that merge commit is an ancestor of protected
      bf843961c0e1b5bd45fa481f0138c71f2a87d4e2 by 58 commits. Merged is not proven. #578 has since
      MERGED as d6beb70f1b6278a5d656a8b88384c9e2936332ef ("[HF1-C] Add reviewed GLM, Alibaba,
      MiniMax subscription profiles"). It adds the reviewed GLM / Alibaba / MiniMax subscription
      profiles; the repaired contract REJECTS `adapter_id` / `harness_id` on provider profiles so a
      provider-plan identity does not globally select a harness; that merge commit is an ancestor of
      protected bf843961c0e1b5bd45fa481f0138c71f2a87d4e2 by 53 commits. Merged is not proven. #583
      has since MERGED as 7868e2c2727a8871f64f387de9ce00dc6a67cff9 ("[HF1-D] Bind subscription
      plans to reviewed worker harnesses"). It binds subscription plans to reviewed worker harnesses
      via control_plane/subscription_harness_bindings.py as the SINGLE plan-to-harness binding
      authority; that merge commit is an ancestor of protected
      bf843961c0e1b5bd45fa481f0138c71f2a87d4e2 by 33 commits. Merged is not proven. #577 has since
      MERGED as ef4682c8b998a9ca522b4690fadf938aa57029ad ("[PROVIDER-FABRIC][DRAFT/HOLD] Add MiniMax
      and Alibaba subscription realms to Codex worker"); that merge commit is an ancestor of protected
      bf843961c0e1b5bd45fa481f0138c71f2a87d4e2 by 60 commits. Merged is not proven. With #577, ALL SEVEN
      Wave 1 carriers are now merged and the "Wave 1 open carriers" table below is corrected to match.
      Record each remaining carrier's merge the same way, and for any carrier whose title says Claude, state in its
      row whether it is compatible-provider or native.
  - id: HF1-A
    title: Provider-neutral worker execution contract (HF1 slice A)
    status: done
    pr: 471
    next_action: >
      COMPLETED_DO_NOT_REPEAT. Mastermind PR #471 ([MAS-198] HF1-A provider-neutral worker execution
      contract) merged as 66a1125c4e0f02351f33dbf8c8583eb19ea1d2e4 on 2026-09-07; that merge commit is an
      ancestor of protected master 89d890f0ae526205e762ad2924b6590f35847e8f. Source capability only: no
      live subscription/Claude worker realm, Ready receipt, Executive Job launch or real provider turn has
      executed, and PF1's first real non-Codex vertical stays todo. Do not replay this merge, reopen its
      carrier codex/hf1a-provider-neutral-worker-contract-01a06aaf, or widen the common worker
      launch/supervisor/broker request with provider home, credential or session fields.
  - id: PF1
    title: First heterogeneous subscription provider vertical
    status: todo
    depends_on: [RF1, HF1]
    next_action: >
      Add exactly one reviewed provider/harness vertical, with Claude as the preferred first real
      non-Codex proof, and prove one bounded Executive child Job through the real adapter before
      making that provider generally routable. Cursor/Grok and other provider verticals remain V1.x
      expansion and may be researched in parallel, but do not block the first V1 operating proof.
      NATIVE OWNERSHIP AND EXACT NEXT DEPENDENCY (Sol rulings R21/R22, 2026-09-16; see
      DSC:CLAUDE-SUBSCRIPTION-HARNESS-IS-NOT-NATIVE-ANTHROPIC): native Anthropic Fable/Opus capacity is
      PF1's alone, as `claude-code` / `ClaudeCodeWorkerAdapter` under plan
      docs/superpowers/plans/2026-08-27-hybrid-workforce-pf1-claude-worker.md. It is NOT BUILT at
      protected Mastermind master 7642aea155d2817219135b24246b55c1d7611c66: no `claude-code` descriptor
      exists in control_plane/worker_adapter.py, and control_plane/claude_worker.py plus
      tests/test_executive_claude_worker.py are absent. The exact next dependency is, in order, (1)
      PF1-F0 custody and its current protocol gate — operation
      pf1f0-nested-cache-consistency-repair-20260907-sol-001, carrier C0BSBM78V1N/1788797971.486229,
      retained owner /root/wbr_f1_native_eligibility, retained candidate 545b9176…, live carrier PR #455
      "[PF1-F0][HOLD] Provider-free Claude CLI protocol falsifier" OPEN/DRAFT/HOLD at
      0a368935ece318c1b7f3301337f75d3a58d61006, which is a provider-free falsifier and not an
      implemented worker — and (2) the missing native `ClaudeCodeWorkerAdapter` carrying a dedicated
      native-auth worker principal with NO token-in-environment shortcut, through the existing common
      broker and with no provider-specific broker or lifecycle plane. Tracked in the capability matrix
      alongside the #7114 skill/profile integration and the real realm/capacity producer. Resolved only
      through the existing PF1 owner: never open a replacement worker, carrier or second native writer,
      and never satisfy this wave with the merged compatible-provider harness.
      2026-09-17 BOUNDARY (see DSC:PF1-CLAUDE-WORK-LEG-BOUNDARY and handoff
      EXECUTIVE-CAPACITY-FABRIC-2026-09-17): the native adapter is now BUILT but UNMERGED and
      UNARMED — branch claude/ssd-pf1-native-claude-worker-adapter at
      0df5e985c85ca4d3e16dcee075086d101ed0e722, no pull request, with the claude-code descriptor in
      control_plane/worker_adapter.py carrying implementation=
      "control_plane.claude_worker.ClaudeCodeWorkerAdapter" and implemented=False so the broker
      cannot execute it. PR #455 is still OPEN/DRAFT/unmerged at 0a368935 under its ratified hold,
      with its ordered repair already implemented and independently confirmed adversarially. Two
      further architecture constraints are now measured, and they collapse the remaining gap into
      ONE wall rather than two: the Executive work leg refuses every non-Codex execution surface at
      four independent sites with _EXECUTION_SURFACES a CLOSED enum, leaving a profile-less Job as
      the only lawful seam; and on that seam the fake-only PF1-F0 falsifier's fixed two-key
      sealed-evidence result can never satisfy the supervisor's twelve-key closed per-Job schema, so
      no COMPLETED Job is reachable while the effect ceiling holds. A Job-conformant result requires
      a real model turn, which is exactly what the adjudicated dedicated-principal decision
      withholds. Spend the next effort on that authority question, not on more adapter or test work,
      and do not mirror tests/test_w6b_native_round_trip.py — it proves the PLAN leg and records in
      its own source that the work leg cannot complete hermetically for any provider.
      A THIRD constraint narrows the seam further: the supervisor's complete-launch-attestation gate
      (executive_supervisor.py:1072-1075) requires the CODEX contract's
      LAUNCH_ATTESTATION_SCHEMA_VERSION, lazily imported at :85-92, and fires whenever a Job carries
      an effective grant regardless of its flag — so the lawful seam is profile-less AND grant-less,
      and no non-Codex worker can serve a Job with an effective grant. LaunchAttestation is still
      codex_worker.py-local and absent from worker_execution_contract.py. PF1 must NOT close this by
      claiming the Codex schema version; the remedy is an HF1 promotion of the type plus a
      provider-neutral schema version. One integration proof does exist and is green on the adapter
      branch at 5b461fb2 (tests/test_executive_claude_lifecycle_integration.py, 3 passed): the real
      adapter drives the live supervisor through a real subprocess to measured JobStatus.FAILED /
      AttemptStatus.FAILED on the result-content refusal, which is the designed outcome.
  - id: MH1
    title: Authenticated multi-host Executive worker transport
    status: todo
    depends_on: [HF1]
    next_action: >
      V1.x only. Before a second physical Mac/host carries real Executive work, extend the existing
      worker-broker lifecycle through one private authenticated remote transport while keeping one
      canonical Executive Runtime on the control host. Prove stable Attempt-bound operation identity,
      effect-unknown reconciliation, local-only provider credentials and zero remote queue/scheduler.
decisions:
  - DEC:EXECUTIVE-CAPACITY-FABRIC-OWNERSHIP-AND-CONTRACT
  - DEC:AUTONOMY-V1-DISPATCH-DIALOGUE-RUNTIME-SEPARATION
  - DEC:LAUNCHER-RELOCATION-IS-A-CAPABILITY-GRANT
discoveries:
  - DSC:CLAUDE-SUBSCRIPTION-HARNESS-IS-NOT-NATIVE-ANTHROPIC
  - DSC:VISIBLE-TURN-PROJECTION-IS-THE-EXISTING-READ-SEAM
  - DSC:PF1-CLAUDE-WORK-LEG-BOUNDARY
artifacts:
  - agentos/decisions/DEC-EXECUTIVE-CAPACITY-FABRIC-OWNERSHIP-AND-CONTRACT.md
  - agentos/discoveries/DSC-PF1-CLAUDE-WORK-LEG-BOUNDARY.md
  - agentos/handoffs/EXECUTIVE-CAPACITY-FABRIC-2026-09-17.md
  - agentos/decisions/DEC-AUTONOMY-V1-DISPATCH-DIALOGUE-RUNTIME-SEPARATION.md
  - agentos/discoveries/DSC-AGENT-DISPATCH-CURRENTLY-HAS-NO-WORKER-RECEIVER.md
  - agentos/discoveries/DSC-ASTRA-FABRIC-LIVE-CLIENT-AND-SUBSCRIPTION-GATES.md
  - agentos/handoffs/AUTONOMY-V1-2026-08-26-sol-operational-reconciliation.md
  - agentos/handoffs/OPERATOR-CONTINUITY-2026-08-28-SOL-CONTINUATION-CHECKPOINT.md
  - agentos/handoffs/EXECUTIVE-CAPACITY-FABRIC-2026-08-29-CF2-H0-SOURCE-RELEASED.md
  - agentos/handoffs/EXECUTIVE-CAPACITY-FABRIC-2026-09-13.md
  - agentos/handoffs/EXECUTIVE-CAPACITY-FABRIC-2026-09-16.md
  - agentos/handoffs/EXECUTIVE-CAPACITY-FABRIC-2026-09-16-POST-7181-FOLD.md
  - agentos/discoveries/DSC-CLAUDE-SUBSCRIPTION-HARNESS-IS-NOT-NATIVE-ANTHROPIC.md
  - research/MASTERMIND_EXECUTIVE_CAPACITY_FABRIC_F0_ARCHITECTURE_2026-08-22.md
  - research/MASTERMIND_EXECUTIVE_CAPACITY_FABRIC_F0_PLACEMENT_AMENDMENT_2026-08-22.md
  - research/MASTERMIND_EXECUTIVE_CAPACITY_FABRIC_F0_SEMANTIC_IDENTITY_AMENDMENT_2026-08-22.md
  - research/MASTERMIND_EXECUTIVE_CAPACITY_FABRIC_F0_OBSERVATION_NULL_AMENDMENT_2026-08-22.md
  - agentos/handoffs/EXECUTIVE-CAPACITY-FABRIC-2026-08-25.md
  - agentos/handoffs/EXECUTIVE-CAPACITY-FABRIC-2026-08-25-CF1-ACCEPTED.md
  - docs/superpowers/plans/2026-08-25-mas-126-cf1-reconciliation.md
landmines:
  - "Macro `shared-ai-provider-control` already owns provider availability, auth pools, cooling and quota state; do not create ProviderAccount/QuotaHorizon truth tables in Executive OS."
  - "Current native Claude realm identity and Macro claude_code_oauth_N capability IDs are not equivalent by ordinal/name/config path/plan type. Family A failed closed because no supported rotation-safe secret-free enrollment equality witness currently exists. Do not resurrect ordinal binding."
  - "A compatible-provider alias is never native Anthropic capacity (Sol rejection class E11). The file control_plane/claude_subscription_worker.py, the descriptor id `claude-compatible-subscription` and PR titles saying 'Claude subscription worker' all name the Claude Code HARNESS, whose providers are exactly glm/alibaba/minimax. `compatible` is load-bearing; read config/subscription_provider_profiles.v1.json before believing any file name."
  - "#581-era and #676-era fixture corpora, static check counts, killed mutants and proposed-scenario counts are engineering evidence about source. None is an executed provider canary and none may be relabelled as native capacity or production proof; proposed scenarios are not executed canaries."
  - "A protected-master descendant that leaves H0 authenticated material unchanged is not automatically the H0 source-closure repair identity. Current carrier identity and immutable repair provenance are separate concepts; do not falsify one to satisfy the other."
  - "`usage_snapshot()` is a display aggregate, not a normalized truth contract. Its numeric defaults and fail-soft joins cannot be mapped 1:1 into provider_capacity.v1."
  - "Current Claude `discover_present_keys()` applies enablement filtering/fallback, so `usage_snapshot().present` can hide a disabled-but-installed credential. CF1 obtained unfiltered secret-free presence through the existing Provider Control owner; do not regress to the display field as source truth."
  - "Current Codex `available_accounts()` intentionally returns only usable accounts and therefore combines provider enablement, executable presence and credential presence. Preserve the CF1 source-owned observation seam that separates those dimensions without changing Codex dispatch semantics."
  - "A fail-soft helper that returns []/0/False on absent, corrupt or unreadable source cannot establish an exact zero/healthy/absent fact. Capacity observations must preserve source quality or degrade the affected field to unknown."
  - "Provider-capacity `present`, `enabled`, and `cooling.active` are nullable observations: true/false means observed; null means unknown. A fail-soft fallback may never manufacture false."
  - "`usage_snapshot()` display zeros are not proof of zero usage; no source observation means unknown unless a reviewed estimator with a real budget is configured."
  - "Unknown quota is not unlimited and stale quota is not fresh. Never derive absolute remaining capacity from a percentage when the absolute limit is unknown."
  - "Provider/account presence is not authentication success, and Slack/GitHub/provider process presence is not Executive execution evidence."
  - "Host matters: attached subscription capacity is bound to an opaque reviewed host identity; do not assume accounts on different Macs are globally interchangeable."
  - "Capacity host_ref is observational identity only; it is not an authenticated endpoint or remote execution credential."
  - "ChatGPT1/2/3 Slack principals are Sol CEO communication identities, not Executive Worker IDs. The corresponding paid subscriptions may supply codex-pro worker realms, but Executive OS must claim the concrete realm rather than routing by Slack username."
  - "Current Executive control/broker path is local AF_UNIX with one configured worker. Multi-host transport remains MH1/V1.x and must not create a second Runtime/queue/scheduler or generic SSH executor."
  - "Model Router suitability and provider capacity are separate filters. Provider health/cost may rank eligible workers but may not redefine model quality, authority or required independence."
  - "Current Model Router routes are ordered concrete model aliases. Before heterogeneous providers share a route, RF1 must define provider-neutral equivalence tiers/classes so alias/file order cannot silently become provider priority."
  - "Current WorkerExecutionAdapter/v1 still imports Codex-owned types and LaunchSpec contains codex_home; before a non-Codex Executive worker is integrated, HF1 must generalize the existing harness/broker without lying about provider identity or forking lifecycle."
  - "Do not create executive_alibaba_broker/executive_grok_broker-style provider lifecycle services. One reviewed broker/adapter lifecycle must resolve immutable approved adapters; provider-private home/auth/session mechanics stay behind the adapter."
  - "Remote timeout/disconnect is EFFECT_UNKNOWN, not permission to send the same Attempt to another host/provider. Reconcile the same host/worker operation first."
  - "A provider 429/auth/transport failure after an Attempt begins does not authorize blind retry or cross-provider failover; reconcile the Executive Attempt/effect state first."
  - "Phase 1F-C owns schema v4. Capacity Fabric must not introduce another v4 migration or temporary v3 placement schema."
  - "Phase 1F-C freezes placement_snapshot_json to exactly worker_id/quota_class/provider/account_label/snapshot time. Capacity Fabric must not add quota, host, policy or reason fields to that object or change its digest definition."
  - "Capacity decision evidence belongs in the existing atomic claim receipt only after CF2-F source-law acceptance; if that seam proves insufficient, return to Sol rather than inventing a second event/ledger or schema v5."
  - "Whole-repository Macro commit identity is audit provenance only. High-churn unrelated repo commits must not change provider-capacity semantic snapshot_hash; material provider-source bytes must."
  - "snapshot_hash and generated_at are distinct: Executive claim evidence must bind both, because identical semantic contents can have different freshness."
  - "CF1 stdout proves the contract, not the future Executive acquisition transport. CF2-F froze one secret-free bounded acquisition seam; Executive may not import floating Macro provider internals or read raw provider ledgers/secrets."
  - "The provider-capacity normalizer receives only secret-free typed observations. Existing Provider Control helpers may continue their already-reviewed credential-presence mechanics internally; that authority is not transferred to the normalizer or Executive OS."
  - "Subscription headroom should reduce marginal API spend for routine eligible work, but policy may reserve scarce frontier capacity for critical/interactive work."
  - "Never expose auth tokens, cookies, API keys, raw auth files, provider-home contents, email/account PII, remote endpoint credentials or private host addresses in the capacity projection."
  - "Merged is not proven. The three ACP/HF1-B merges (#575 91dbdf87, #579 3a8cc8b0, #576 cb95ae8b) the three HF1-C/HF1-D merges (#578 d6beb70f, #581 27a5d893, #583 7868e2c2) and the provider-fabric merge (#577 ef4682c8) — all seven Wave 1 carriers — establish provider-free ACP SDK / native-process boundaries, the provider-neutral broker seam and the subscription realms on the Codex worker. None proves a live provider route or a production heterogeneous workflow; native Anthropic Claude capacity still belongs to the PF1 / native-Claude path and the Family-B Provider Control / realm work."
  - "The intake pin 0fe8074ff953b2ced9025ed40f0f66019c759967 is an ANCESTOR of bf843961c0e1b5bd45fa481f0138c71f2a87d4e2 — older, not newer. SCOPE: bf843961 was the protected master when this was measured at 2026-09-16T19:5xZ; it has since been SUPERSEDED three times over — by e8803ba3d3ee928d150d7dcac1a1e2bad2dc0d48 at 20:4xZ, then 5ee11ab1e993616f3568cfca4069cb21fa61fd8f, then 4537f066775c73d305f82acf0643701f01f5e53c, which is the CURRENT protected master as read 2026-09-16T22:55:39Z. The verified order is 0fe8074f -> 8ba7deed -> bf843961 -> e8803ba3 -> 5ee11ab1 -> 4537f066 (current). Every 'ancestor of bf843961' measurement in this record remains true as measured and holds against 4537f066 by transitivity. The intake pin does not advance the record and must not be written as the protected-master pin."
do_not_redo:
  - "Do not create a provider/account/quota database in Mastermind Executive OS."
  - "Do not duplicate Macro key_pool, budget_gate, llm_auth, provider_health or Codex account-home identity logic."
  - "Do not change existing provider dispatcher selection/fail-open behavior merely to make Capacity Fabric easier; observation APIs remain read-only and independently tested."
  - "Do not import floating Macro provider internals directly into Mastermind as the cross-repo contract; consume the accepted versioned projection."
  - "Do not put live quota/cooling state into Model Router policy files."
  - "Do not create a second router for provider capacity; evolve the existing stateless Model Router through RF1."
  - "Do not create one Executive Runtime/database/queue per Mac or use GitHub Actions/tmux/SSH as Executive lifecycle authority."
  - "Do not create a long-lived capacity daemon/service merely to bridge Macro to Executive without a separate architecture ruling."
  - "Do not use LLM judgment to select a worker, waive an independence requirement, or interpret unknown quota as capacity."
  - "Do not widen Phase 1F-C placement_snapshot_json for Capacity Fabric."
  - "Do not disguise Alibaba/Z.AI/Grok/Cursor behind a `codex_home` field or copy Codex-only secret-canary semantics into the common harness contract."
  - "Do not reopen CF1 implementation absent a concrete defect or material-source change."
  - "Do not reopen CF2-F; Mastermind #150 is the accepted source law."
  - "Do not patch `mastermind.provider_capacity.v1` in place to add native Claude realm semantics. OCR-2C Family B, if approved, is a new versioned Provider Control evolution."
  - "HOST SATURATION CONSTRAINT, binding on every actor in this fabric until the incident owner lifts it (Chairman incident, root ts 1789596435.196469, delta 1789597170.411539): no new whole-root, home, volume or temp diagnostic sweeps and no generic heavy work on M2 (24 CPUs, load ~127, ~0% idle), and do not spill that work blindly to M1 (load 37.8, ~3% idle, ~13 GiB free, connector since OFFLINE). Three >30-minute read-only `rg` diagnostics were TERM'd and M2 remained saturated — that is explicitly not a fleet-fixed claim. The gateway's local backend/RPC slots do NOT reserve CPU or I/O for children that outlive the start call. Use exact tracked paths and GitHub reads instead."
  - "Do not widen Capacity Fabric into Wake, Slack dispatch, Control Room, browser/devserver resources, host arming, merge/deploy authority or capital/trading authority."
  - "Do not treat the merged Mastermind #581 (27a5d893ca28f7006c1007dffa51e677c9c7a4ab) as native Anthropic capacity or as PF1 progress, and never treat a #581 merge as native readiness (Sol R21)."
  - "Do not build a native Claude worker, adapter or carrier outside PF1. Native ownership is PF1 `claude-code` / `ClaudeCodeWorkerAdapter`; PF1-F0 custody is PR #455 and it stays held. A second native writer for one operation is the error, not a shortcut around a slow one."
  - "macro #7181 is MERGED at d7d8bdc6fb9f3548b90487cf51c274693f4e105a and TERMINAL (release child verdict exactly `PASS / MERGE_RECEIPT_VERIFIED / TERMINAL_RELEASE_ACT`). Never re-merge, re-verify or reopen the release child."
  - "Do NOT replay or reroute the platform-blocked MacBook RWE native `run` launch (Environment R7, root ts 1789595728.262069). Readback proved it created no log, receipt, result, cache or temp environment. It is an OPTIONAL attended-host probe and is NOT a release prerequisite on #625, which is merged as 4dc8b9c2 and whose `rwe_env.py run` is to be REUSED, never rebuilt."
  - "Do NOT rebuild `Mastermind_Connected_Reader_Integration_2026-09-16.zip` or retry its blocked native action (root ts 1789596917.528609). Targeted Library/Project lookup and two exact native artifact locations failed to recover it; ask its incumbent to return the existing artifact's accessible reference and hash. Source inspection is not replacement publication."
  - "Do NOT rerun, cancel or replace Mastermind #707's hosted `test` run 35155252029 (root ts 1789597361.588869). It was still in its repository-test step; CodeQL/security were green. #707 stays DRAFT / BUILT_NOT_PROVEN until both gates close."
  - "Do NOT re-verify packet05 #699 with the unprotected candidate verifier, and do not treat REMOTE_PROOF_CHANGED as source divergence or as permission to rerun (Sol ruling, root ts 1789597068.473939). The single authorized invocation is SPENT. A fresh evidence-only remote-complete grant becomes possible only AFTER #707 is independently accepted and protected."
  - "Never re-run the packet05 verifier without a NEW material source-continuity edge. The packet05 grant (Sol edge 1789565866, Mastermind #699) is SPENT and its ONE granted run returned `VERDICT: REFUSAL REMOTE_PROOF_CHANGED`, a repo-wide quiescence guard over every open PR and NOT a verdict on packet05's source; the seat-owned p05-verify-… worktree stays INERT/UNCHANGED — do not remove it without Sol. CORRECTED 2026-09-16: `OUT_OF_SCOPE_DIRT` and grant edge 1789588151 belong to the separate Mastermind #677 one-shot, not to packet05."
next_action: >
  VPS economical-provider track (seat Claude6 5fae71cf, Fable; Sol root
  C0BSBM78V1N/1789324397.992989, ruled at edges 1789694411.329219 + 1789694989.668909): TWO verticals
  sit DRAFT and HELD and may not be readied, merged or auto-merged without an explicit Sol acceptance
  ruling on that root. (1) Macro PR #7280, branch claude/provider-production-modes-20260918, head
  284bd893f5fb2085d597611d065017494f3275db — production API usage modes. (2) Mastermind PR #804, branch
  claude/executive-service-principal-20260918, head 3b5182e2545cab671f2da2db6735b51c926baf18 — tier A1
  executive service principal, which reports NOT_YET_ADMITTED by design because the intent sink refuses a
  typed schema, a provenance key and constraints.task_kind. A2 (actor-aware CEO gate in
  executive_runtime.py) and B (OpenCode native Worker) are NOT started: they collide with open PR #699
  and PR #762/#590 respectively. Read DSC:EXECUTIVE-PROVENANCE-GATE-IS-SCHEMA-ONLY — the CEO provenance
  gate is schema-only, so an actor-aware CEO branch is a security prerequisite before any non-CEO
  principal is armed beyond READ/RESEARCH — and agentos/handoffs/EXECUTIVE-CAPACITY-FABRIC-2026-09-18.md
  before touching either vertical. Protected Mastermind master is now
  320f586126b7c82c843ef17612f12d40d20a42e0; executive generation 8b231e82 is installed but
  UNARMED/STOPPED and the next gate is HUMAN_AUTH/CREDENTIAL_READINESS.

  CEO REGIME 2026-09-17 (DEC:FABLE-SEAT-IS-CEO-COEQUAL-WITH-SOL, amended ~08:50Z): the Chairman delegated
  ownership and decision authority over the ENTIRE Agent Fabric program to the Fable seat (aa22a3d2,
  Claude8) - no separate Sol authorization inside the program; bounded by unrelated programs, shared
  infrastructure outside Agent Fabric, and active worker custody (Claude6 seat 5fae71cf holds the STARTed
  Executive-closure milestone and its manifest/symlink worktree; Claude5 keeps #710). Mastermind #716
  MERGED 2026-09-17T09:32:10Z as 7e4d18c1283c95d1b5b840acb51a2d0bf3a34e67 and #665 MERGED 10:11:33Z as
  e878878c9a4ae2dd50a48d825e031e07e8211708 (both protected master, BUILT_NOT_PROVEN, activation
  Chairman-gated per the kit packet MINIMAX_CODEX_ACTIVATION_BOUNDARY_2026-09-17.md). Next act = integrate
  macro #7114's published first-use patch once the org-level `ci-linux` pool drains (hold retained;
  starvation escalated to the Chairman with exact evidence, no duplicate control plane); the #7114 and
  #7257 watchers are the only CI observers (no polling). Everything below is the state this record
  inherited on 2026-09-16 and is historical where it conflicts. Current carrier state: §10 of
  agentos/handoffs/EXECUTIVE-CAPACITY-FABRIC-2026-09-16-POST-7181-FOLD.md.

  Fable principal integration, operation agent-fabric-end-to-end-fable-integration-20260913-sol-001.
  Protected Mastermind master is 4537f066775c73d305f82acf0643701f01f5e53c, read 2026-09-16T22:55:39Z
  (`gh api repos/mastermindx-market-intelligence/Mastermind/branches/master --jq .commit.sha`),
  replacing the 7642aea155d2817219135b24246b55c1d7611c66 pin this record inherited. It moved twice more
  during this session: the verified order is 0fe8074f -> 8ba7deed -> bf843961 -> e8803ba3 -> 5ee11ab1 ->
  4537f066, each step measured by compare (see §8 of the handoff). Earlier pins in this record are
  timestamped where they were read and every "ancestor of <older pin>" measurement still holds against
  4537f066 by transitivity. Current carrier state is in
  agentos/handoffs/EXECUTIVE-CAPACITY-FABRIC-2026-09-16-POST-7181-FOLD.md. Principal critical path is
  W1-H3 (Mastermind #677, OPEN/DRAFT on the SAME child/worktree/writer; head is now
  6dc2ea83bc738c2532745ef71dcde6c170c58d91 after the R80 four-path repair — SUPERSEDING the
  09e53b30092400c501a508992bf942474d70d830 head and its 20:4xZ CHANGES_REQUESTED reading, both of which
  are historical. Seat REPAIR_RETURN at root ts 1789598965.415869: R14 APPROVE / BLOCKING 0, hosted
  `test` success (run 35156879220), canonical remote-complete receipt_digest
  45525cd549f57646e679a04c7fbb69fb79b5955444df92db850a8cec63200530 on the third invocation, HOLD-FOR-SOL
  and awaiting Sol's ruling. Sol accepted the
  R48/R50/R68/R76 semantic closure at this head (root ts 1789588151), but **R80 (ts 1789590510.060009,
  durable contract comment 5704046553) is a REQUEST_REPAIR, not an acceptance** — disposition verbatim
  `REQUEST_REPAIR / SAME CHILD+BRANCH+WRITER / EXACT FOUR-PATH CEILING / H4 NOT_STARTED` over
  ops/executive_os/autonomy_control.py, tests/test_executive_autonomy_control.py,
  scripts/executive_os_phase1c_control_wrapper.py and tests/test_executive_launchd_config.py. The
  old-head `remote-complete` grant was WITHDRAWN BEFORE ACCEPTANCE; both typed results produced against
  09e53b30 — the `OUT_OF_SCOPE_DIRT` refusal and the later `REMOTE_COMPLETE_VERIFIED`
  (receipt_digest 3edb2976…, root ts 1789591021.847339) — are HISTORICAL EVIDENCE ONLY per Sol R81 and
  release nothing. The no-retry rule is scoped to the OLD head 09e53b30 ONLY; R80 requires the canonical
  remote-complete verifier on the NEW head once one exists) and H0 prestage attempt 2 on the existing runner. Before
  sizing, routing, promising or reporting native Anthropic Fable/Opus capacity anywhere in this fabric,
  read DSC:CLAUDE-SUBSCRIPTION-HARNESS-IS-NOT-NATIVE-ANTHROPIC and re-run its four falsifier commands
  at the then-current protected master: the merged Claude subscription worker is a compatible-provider
  harness, the native path is PF1's and is NOT BUILT. Wave 1 ACP/HF1-B carriers #575/#579/#576 and
  HF1-C/HF1-D carriers #578/#581/#583 and the provider-fabric carrier #577 have merged on the protected
  master as it stood at bf843961 (and therefore on its descendants e8803ba3 / 5ee11ab1 / 4537f066)
  — ALL SEVEN Wave 1 carriers, see the corrected "Wave 1 open carriers" table below (all seven
  merge commits are
  ancestors of it) — see the HF1 umbrella wave `next_action` for the per-PR sentences; merged is not
  proven for any of them. Re-read every head before acting on it. Accepted Macro CF1 remains
  dcdd939c45b23abce5ba04f95e330ac914a3904b. Any native H0 build or root action still belongs to the
  CF2-H0 wave: re-pin CURRENT protected Mastermind, keep the immutable repair release
  229aebce5e8d0c1c7372f5fead9c24516b027cc1, and require repair ancestry plus exact mode/blob equality
  for all five authenticated H0 paths before treating a pin as CARRIER_COMMIT_SHA. OCR-1 Task 4 and
  OCR-3 Task 1 may proceed separately on their own lawful carriers; OCR-2C Family B remains a separate
  architecture gate.
---

## Capability state

CF1 is accepted and merged in Macro as `dcdd939c45b23abce5ba04f95e330ac914a3904b`.
CF2-F is accepted and merged in Mastermind as `e9cb5cbd745b36dc51f54bd83238ec38ef0c80c7`.
OCR-1 Tasks 1–2 provider-work-free Claude preflight is accepted and merged in Mastermind #184 as
`1d5ad1249172e8b93882f0dff157fc13636dd62d`; it remains `BUILT_NOT_PROVEN` / production-inert and
proves no live realm, capacity identity or routing. OCR-1 Task 4 is separately commissioned RED-first.

The first independent P0 census correctly refused with `NO_SAFE_CF1_ACQUISITION_PATH`; H0 code then
merged in Mastermind #157 and source-closure repair #200 merged as `e53f524230ffc4e8730c844f6fc319d50a2050f3`.
Subsequent protected-master movement exposed a runbook provenance collision between exact current carrier
and immutable repair identity. Mastermind #213 repaired that split on the single canonical H0 carrier and
released the bounded v3 source transport as protected `229aebce5e8d0c1c7372f5fead9c24516b027cc1`
after full required repository test, CodeQL/static and exact-head Sol review. Protected master later advanced
to `dfd69451dce5e186ce05f65446023fbe21f07a58` through records-only watcher-resource design #205, and at the
2026-09-13 record repair it stands at `89d890f0ae526205e762ad2924b6590f35847e8f` — 152 commits past
`dfd69451...`, which is an ancestor of it. The immutable repair remains `229aebce...` and is also an ancestor
of `89d890f0...`, so repair ANCESTRY holds at the new pin; the runbook's exact five-path mode/blob EQUALITY
reproof was not re-run by this records-only repair, so the carrier axis is reported, not proven. Source law
is no longer the H0 blocker, but the implementation remains `BUILT_NOT_PROVEN` / production-inert until the
final native v3 build and administrator ceremony produce the required installed-host receipts.

RF1 is accepted and merged in Mastermind #449 as `cc03ea329148a44b048b65a4649481d637980dd3` (2026-09-04) and
HF1-A is accepted and merged in Mastermind #471 as `66a1125c4e0f02351f33dbf8c8583eb19ea1d2e4` (2026-09-07);
both merge commits are ancestors of protected master `89d890f0...`. Both are SOURCE CAPABILITY ONLY: RF1's
ordered suitability tiers prove no capacity-ranked claim, and HF1-A's provider-neutral execution contract
proves no live worker realm, Ready receipt or Executive Job launch. Capacity-aware placement, real
multi-account routing/fan-out, automatic heterogeneous placement, the HF1-B/HF1-C/HF1-D harness slices, PF1
first real non-Codex worker and MH1 multi-host transport are not production-proven.

OCR-2C Family A has returned `FAMILY_A_NO_SAFE_EQUALITY_WITNESS` and
`FAMILY_A_NO_ROTATION_INVALIDATION`: current native Claude evidence plus existing Provider Control slot
identity cannot safely prove that a native realm and `claude_code_oauth_N` are the same paid subscription
across rotation without forbidden account/secret coupling. This refusal is a successful falsifier result,
not permission to weaken identity. Family B architecture is the next design gate and must preserve the
real underlying native Claude realm capacity identity rather than collapsing it into a synthetic ordinal.

The program remains `PARTIAL`.

## Wave 1 open carriers (Mastermind, pinned 2026-09-13)

Fable principal integration, operation `agent-fabric-end-to-end-fable-integration-20260913-sol-001`, Wave 1,
under ruling `orch/fabric/INTEGRATION_RULING_W1.md` (Fable, 2026-09-13). Heads and titles were read with
`gh pr list -R mastermindx-market-intelligence/Mastermind --state open --limit 100 --json number,title,headRefName,headRefOid,isDraft`;
all seven were DRAFT and none was merged AT THAT READING. **That is no longer true: as re-read on
2026-09-16, ALL SEVEN have MERGED**, and every merge commit below is an ancestor of protected master
`bf843961c0e1b5bd45fa481f0138c71f2a87d4e2` (`gh pr view <n> -R mastermindx-market-intelligence/Mastermind
--json state,headRefOid,mergeCommit` and `gh api repos/.../compare/<merge>...bf843961...`). A head recorded
here is a pin, not a promise — re-read it before acting on it, and never merge, rebase, label or ready one of
these carriers from a records-only session.

| PR | Released head | Merge commit | Role (one line) |
|---|---|---|---|
| #575 | `6035d6b5` | `91dbdf876f1f1ea10d24342b9d4ea49ba081bfcc` | ACP probe: qualify the provider-free SDK boundary and conformance with no real provider work. |
| #579 | `6f9f420e` | `3a8cc8b007c4573bd01efd909bf6d0e786c71663` | ACP turn driver: bind the guarded native ACP worker to the common worker receipts. |
| #576 | `d3587a15` | `cb95ae8bf76382df14d1017691e4ccc0b6356f7c` | HF1-B: configure the existing worker broker by provider-neutral adapter identity. |
| #578 | `092c2bf2` | `d6beb70f1b6278a5d656a8b88384c9e2936332ef` | HF1-C: reviewed GLM, Alibaba and MiniMax subscription profiles; the repaired contract REJECTS `adapter_id`/`harness_id` on a provider profile — a plan identity does not globally select a harness. |
| #581 | `17623544` | `27a5d893ca28f7006c1007dffa51e677c9c7a4ab` | HF1-D: the fixed-profile Claude subscription worker. The bounded `claude-compatible-subscription` harness for the purchased GLM/Alibaba/MiniMax plan stack, production disarmed absent exact admission/realm/capacity. COMPATIBLE-PROVIDER, NOT native — see `DSC:CLAUDE-SUBSCRIPTION-HARNESS-IS-NOT-NATIVE-ANTHROPIC`. |
| #583 | `11f7abf8` | `7868e2c2727a8871f64f387de9ce00dc6a67cff9` | HF1-D: `control_plane/subscription_harness_bindings.py` is the single plan-to-harness binding authority. |
| #577 | `d862ff93` | `ef4682c8b998a9ca522b4690fadf938aa57029ad` | Provider fabric v2: MiniMax and Alibaba subscription realms on the Codex worker. |

These are protected SOURCE. None of the seven proves a live provider route, a real provider turn, a Ready
receipt, an Executive Job or a production heterogeneous workflow, and PF1's first real non-Codex vertical
remains `todo`. Current carrier state and the full receipts are in
`agentos/handoffs/EXECUTIVE-CAPACITY-FABRIC-2026-09-16-POST-7181-FOLD.md`.

Before the merge, #578 moved after the Wave 1 packet was cut: the packet pinned `5d786da2`, the live head is
`ed3ed5e06c0a45c06a2709b3ac77acdda05fd229`, and
`gh api repos/mastermindx-market-intelligence/Mastermind/compare/5d786da2...ed3ed5e0` returns
`status: ahead, ahead_by: 1, behind_by: 0`. The one added commit is the ruling-R1 amendment
"fix(exec): decouple provider profiles from harness selection" — purchased-plan profiles no longer pin a
global adapter — so R1 is already on the branch as a fast-forward descendant, not a divergent rewrite.

## Native versus compatible Claude capacity (Sol R21/R22, pinned 2026-09-16)

Verified at protected Mastermind master `7642aea155d2817219135b24246b55c1d7611c66`. Full receipts,
falsifier and consequence: `DSC:CLAUDE-SUBSCRIPTION-HARNESS-IS-NOT-NATIVE-ANTHROPIC` and
`agentos/handoffs/EXECUTIVE-CAPACITY-FABRIC-2026-09-16.md`.

The merged "Claude subscription worker" (#581, merge `27a5d893ca28f7006c1007dffa51e677c9c7a4ab`) is the
**Claude Code harness** used to reach third-party subscription providers. It is not native Anthropic
Fable/Opus capacity, and its merge is not PF1 progress.

| Question | Answer at `7642aea1` | Command |
|---|---|---|
| Which providers does the catalog carry? | Exactly three: `glm-coding-plan` (glm), `alibaba-token-plan-personal` (alibaba), `minimax-token-plan` (minimax). No Anthropic profile. | `git show origin/master:config/subscription_provider_profiles.v1.json` |
| Is there a `claude-code` adapter descriptor? | No. The only `claude` hits are one entry, `claude-compatible-subscription` → `control_plane.claude_subscription_worker.ClaudeSubscriptionWorkerAdapter`. | `git show origin/master:control_plane/worker_adapter.py \| grep -n claude` |
| Does a native Claude worker module exist? | No. Both paths return empty. | `git ls-tree origin/master control_plane/claude_worker.py tests/test_executive_claude_worker.py` |
| Does the PF1 plan exist? | Yes, blob `5ec3b062264c4146a7c92e1576f1753f788bd440`. | `git ls-tree origin/master docs/superpowers/plans/2026-08-27-hybrid-workforce-pf1-claude-worker.md` |

The grep in row 2 fires on that file, so the absence of `claude-code` is an instrument-verified null
rather than an empty pattern. Native capacity remains the PF1 wave's, whose exact next dependency is
recorded in that wave's `next_action`: PF1-F0 custody and its current protocol gate (PR #455,
OPEN/DRAFT/HOLD at `0a368935ece318c1b7f3301337f75d3a58d61006` — a provider-free falsifier, not a
worker), then the missing native `ClaudeCodeWorkerAdapter` with a dedicated native-auth worker principal
and no token-in-environment shortcut, through the existing common broker.

## 10/10 end-state

A real Sol mission is decomposed through accepted Executive/COO law; child Jobs can land on
heterogeneous subscription/API/local workers according to suitability, independence and fresh
capacity; one provider can become cooling/exhausted without duplicate execution; a different
eligible provider can take later safe work; independent review/repair still follows Executive
lineage; claim receipts explain why each worker was selected while the closed placement identity
remains stable; the existing Model Router defines provider-neutral suitability tiers while capacity
selects only within the first lawful tier; one provider-neutral harness/broker lifecycle executes
approved Codex/supported-tool/ACP adapters without vendor-specific queues or brokers; one canonical
Executive Runtime can later drive bounded worker brokers on multiple authenticated physical hosts
without copying provider credentials or creating per-host lifecycle state; the Control Room can
later project workforce/capacity truth without owning it; and the Chairman does not manually choose
providers, watch quotas, assign Macs or carry messages between sessions.

## Learning boundary

Later descriptive metrics may include provider reliability, capacity evidence age, quota
utilisation, marginal API spend avoided, host availability, remote transport reliability, repair
rate and independent-review catches. They are operational learning signals only. Provider
sentiment/summary/model output never gains market, portfolio, authority or capital control from
this workstream.
