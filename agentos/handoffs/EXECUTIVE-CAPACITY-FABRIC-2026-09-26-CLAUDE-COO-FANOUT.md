---
workstream: WS:EXECUTIVE-CAPACITY-FABRIC
session: sol/claude-coo-environment-fanout-20260926
model: sol
ended_because: ci_handoff
mission: >
  Continue native Claude fabric integration while decomposing the Chairman's rich COO
  environment, three-repo access, portable Executive/Agent OS plugin and communications
  requirements into four non-overlapping end-to-end Web CEO briefs, without account login.
state_before: >
  Mastermind #999 published the endpoint/facade slice at 517a4b8e6c68d4c60163989a06fabb47dc24ee95.
  Its 359-test local suite did not establish full integration. Existing #676 and #962/#955
  already owned parity and plugin/client proposals; no new sibling was delivered or started.
changed:
  - path: Mastermind/control_plane/executive_worker_broker.py
    what: Require the broker's exact adapter identity during remote status and restart recovery.
  - path: Mastermind/tests/test_native_claude_remote_fleet.py
    what: Add discriminating native identity/recovery tests and preserve same-run no-restart behavior.
  - path: Mastermind/tests/test_executive_worker_broker.py
    what: Make the Codex positive fixture include the real broker's existing adapter identity.
  - path: agentos/handoffs/EXECUTIVE-CAPACITY-FABRIC-2026-09-26-CLAUDE-COO-FANOUT.md
    what: Persist the expanded mission, current source/evidence and four prepared lane briefs.
verified:
  - claim: The parent source successor is published and local/remote heads match.
    command: Studio_Direct.studio_git_commit_current_changes and studio_git_push_current_branch for the existing parent operation.
    result: APPLIED, clean, exact head 4d50af8f90a1a1a41fbbf1b38580b972e3af5843 on Mastermind PR 999.
  - claim: Native broker-identity defects are discriminated and the adjacent suite passes.
    command: PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -p anyio.pytest_plugin tests/test_native_claude_remote_fleet.py tests/test_remote_worker_broker_fleet.py tests/test_executive_worker_broker.py tests/test_remote_worker_broker_client.py tests/test_executive_claude_worker.py tests/test_claude_worker_preflight.py tests/test_worker_adapter.py tests/test_executive_worker_broker_turnkey_binding.py -q --tb=short -o addopts=''
    result: Before repair 14 failing identity subcases; after repair 364 passed and 25 subtests passed, exit 0, 65.39 seconds.
  - claim: Original hosted failure has an existing repair owner rather than requiring another fix.
    command: GitHub workflow run 36234343299 job 108383295498 logs and exact-test issue search.
    result: One ordered-prefix observer timing failure in the 754-module gate; existing Mastermind PR 984 owns it; evidence comment 5845514532.
  - claim: The Claude Executive plugin and parity proposals already exist but are not live acceptance.
    command: GitHub.get_pr_info for Mastermind PRs 962 and 676.
    result: Both open Draft/Hold; exact observed heads 201d8787f825fabbd7562e666ae5fbfc6c32eb8f and 7e6a35b66e8ec42a3263fcb7c06379d68bbc474c.
unverified:
  - claim: The complete native pre-onboarding vertical is source-accepted and live.
    what_would_verify: Complete the existing 992/919 transport-admission and worker-local construction dependencies, exact-head review/CI, then separately authorized native canaries.
  - claim: Four sibling Web CEO sessions have consumed the briefs and started work.
    what_would_verify: Deliberate exact-session delivery plus required pickup and canonical START evidence; these packets alone prove none of those.
  - claim: Rich environment behavioral quality matches or exceeds the native baseline.
    what_would_verify: Lane 1's preregistered native baseline comparison and actual task/consumer proof after source qualification; no model run was performed here.
unresolved:
  - Native worker-local trusted policy/validation construction and post-claim provider/adapter binding remain unfinished.
  - Current source release requires fresh exact-head CI/review; the earlier full-suite pass is not claimed.
  - Existing plugin/client role-correct admission and account enrollment remain distinct gates; no login now.
  - Rich COO environment and communication consumers still require implementation by their prepared lanes.
next_actions:
  - Parent Sol reconciles current 992/919 source custody and wires the native provider/adapter pair through the existing post-claim transport; preserve 999 recovery checks.
  - Deliver each annex into one eligible fresh Web CEO session; consume exact pickup and return evidence rather than infer activity.
  - Lane 3 composes accepted Lane 1, 2 and 4 outputs through existing 962/955 owners and publishes an offline integration proof.
  - Complete later account onboarding only after source and role gates are satisfied and current authorization covers that ceremony.
do_not_redo:
  - Do not rebuild 999 endpoint/facade or its status/recovery identity repair absent a material invalidator.
  - Do not duplicate the exact CI timing repair already carried by 984.
  - Do not recreate the existing 962 plugin, 955 authentication edge, Agent OS store or canonical communication/lifecycle planes.
  - Do not infer native Anthropic readiness from a Claude-compatible third-party subscription harness.
  - Do not weaken sealed worker fences to enable a rich COO principal.
  - Do not revive superseded 589 or reinterpret 633's unresolved DCR effect as permission to retry.
danger_areas:
  - Prepared or delivered packets are not worker START, runtime admission, parent consumption or acceptance.
  - Historical 7882 login-first/CEO-submit wording is not current COO authority; 955's role correction and current source law govern.
  - Latest provider documentation may exceed the actual installed native version; test the exact configuration consumer.
  - Multiple writers to global MCP/plugin/workspace configuration would recreate the fragmentation this fanout is meant to avoid.
---

# Claude fabric and COO environment — cumulative fanout handoff

## §0 State — what is true now

`CHECKPOINTED_CONTINUATION`; `MISSION_COMPLETE: false`. The native endpoint/facade and recovery-identity source is published in Mastermind #999 at `4d50af8f90a1a1a41fbbf1b38580b972e3af5843`. Local regression is 364 tests plus 25 subtests green; full hosted acceptance and the wider native/COO integration remain unfinished. Four briefs below are prepared, not delivered or started. This record carries no runtime gate or dispatch authority.

The procedure pin is protected Mastermind `763ec8f920177fdf48b18df1b8e37b61ab482ef0`, Skillpack 1.0.1. The organizational source base read for this record is macro `0d4b8457ba21734627e5ff100156f04c98676a69`. The existing workstream is verified at `agentos/workstreams/WS-EXECUTIVE-CAPACITY-FABRIC.md`; it is not recreated or marked complete.

## §1 What is left — in order

The parent retains the native adapter lane and source/release acceptance. Next implementation is the existing #992 host-binding/provider-to-adapter composition and #919 admission/worker-local dependencies, with current source-custody reconciliation. The four annexes may be deliberately delivered to eligible Web CEO sessions; Lane 3 owns final plugin/configuration composition and consumes the other lanes' exact artifacts.

No account login or production arming belongs to the current source phase. The target is an installable, offline-qualified complete environment, followed by explicitly separate native enrollment and real-path proof. This does not let any lane stop at a plan when source and test work remain safely executable.

## §2 What will bite the successor

The prior hosted CI failed on a known observer timing issue, not the local missing-jwt environment problem. #984 already owns the exact repair. Source checks, package manifests, tool discovery, authentication, admission, Worker START, result consumption and acceptance are different facts. The existing skills-only package verifier is not authority to install arbitrary executable plugins. A nominal three-repo folder mount is not source custody or proof the native process can access it.

No worker/watcher was dispatched, no live session was rebound, and no provider/credential/installation/runtime action was performed. One compound discovery read was refused before dispatch and not repeated; separate permitted source and tests succeeded. No modifying effect is unresolved in this record. Other carriers' uncertainty, particularly #633, remains untouched.

## §3 What was decided and found

The Chairman's expanded scope is decomposed into four implementation lanes, not four new company programs. Rich COO principal capability is separate from the sealed worker. Existing #676 and #962/#955 are reused. Official MCPs are the initial preference where they meet the exact action contract; company-specific adapters require a demonstrated gap and reuse existing authority/effect owners. No DEC/DSC key or new runtime schema is minted here.

The model labels below are the Chairman-requested initial substantive work profiles, not automatic selection, current served-model telemetry, or a fabricated Pro exception receipt. Current protected cognition/routing admission still applies when a receiver picks up a packet. Fable is not routine labor merely because an older host configuration selected it globally.

## §4 Not in scope — do not adopt

No new orchestration queue, memory database, token store, inbox registry, browser/session selector, retry engine, message journal, placement scheduler or heartbeat plane. No blanket permissions bypass, simultaneous conflicting configuration writers, provider-account login, live trade authority, release bypass or duplicated source repair. This record does not amend runtime state or the workstream's wave status.

## Prepared delivery and integration contract

## Chairman assignment and pickup

The Chairman commissioned a production-quality Claude/local-session COO environment: the complete relevant skills and plugin capability set, direct development access to Mastermind, macro and mastermind-terminal, and effective Executive OS, Agent OS, Mastermind OS, GitHub and Slack integration. Build and qualify the source and offline paths now. **Do not log into a Claude account, enroll new credentials, or activate production routing in this phase.** The parent Sol session retains the native adapter/transport lane.

This is an end-to-end lane commission, not a request for another audit alone. Its authority comes from the Chairman's deliberate current delivery into your session, not from finding this file in search. Before that delivery, it is a prepared packet, not a started worker.

- Parent: `WS:EXECUTIVE-CAPACITY-FABRIC`; organizational continuity is `mastermindx-market-intelligence/macro/agentos`.
- Parent adapter operation: `claude-fabric-preonboarding-integration-20260926-sol-001`, Mastermind PR #999.
- Latest parent source: `4d50af8f90a1a1a41fbbf1b38580b972e3af5843`; checkpoint `docs/CLAUDE_FABRIC_PREONBOARDING_CHECKPOINT_2026-09-26.md`.
- This packet's procedure reference: protected Mastermind `763ec8f920177fdf48b18df1b8e37b61ab482ef0`, Skillpack 1.0.1, bootstrap major 1. **Fresh-pin protected master and load INDEX plus required companions at that same fresh SHA before modification.** This reference is evidence, not a forever-current pin.
- Reconcile the existing source owner, live writer/custody and unresolved effects before touching its branch. An old author name is not a live lease; an observation failure is not expiry. Use the canonical workspace owner. No duplicate source writer, dispatcher, queue, registry, retry engine, token store or watcher.
- `RECEIVER_BINDING_MODE: CAPACITY_SELECTABLE`; `PLACEMENT_STATE: WAITING_CAPACITY / needs_placement` until exact live delivery. `PREFERRED_AVENUE: CTO Sol`. Do not ask the Chairman to allocate routine accounts or quotas.
- Requested initial model/mode below is a substantive work-profile recommendation, not an admission receipt, served-model assertion, numeric budget, or automatic switch. Resolve current cognition admission at pickup. Do not promote standalone polling, handoff or mechanical edits into Pro work. Use Extra High for iterative tool work when it materially improves execution.
- `WHY NOT FABLE`: these are bounded Web-CEO-owned capabilities with existing contracts; use economical admitted workers for routine implementation. Reserve scarce Fable principal capacity for an evidenced exceptional need.

Executive OS owns admission/lifecycle/effects; Agent OS owns continuity; GitHub owns code/PR/CI/evidence; Slack is transport; Mastermind OS is their coherent user interface. A rich COO principal is **not** the sealed child-worker adapter. Keep the sealed profile's restrictions intact. Live authentication, provider calls and release remain separate gates. Do not stop at a plan while safe source/testing work remains.


## Annex 1: COO skills and native-environment parity

**Requested initial profile:** Astra Pro — concentrated cross-system architecture and adversarial environment qualification.

**Proposed lane operation:** `claude-coo-skills-environment-20260926-sol-001`.

### Outcome

A native local COO can discover and use the complete relevant, approved skill/plugin capability set for real engineering and orchestration without losing native Claude Code functionality or silently inheriting uncontrolled account configuration. Surpass the baseline through cross-repo grounding, organizational continuity, reliable verification and visible communication—not by counting installed plugins or making unsupported quality claims.

### Existing owners and scope

Start with Mastermind #676, branch `sol/claude-fabric-parity-and-portable-orchestration-20260915`, observed head `7e6a35b66e8ec42a3263fcb7c06379d68bbc474c`. Its plan is `docs/superpowers/plans/2026-09-15-claude-fabric-parity-and-portable-orchestration.md`. It is a held parity proposal, not live proof; statements that native Claude code is absent are stale against current `control_plane/claude_worker.py`.

Reuse `control_plane/executive_agent_capabilities.py`, `control_plane/executive_capability_packages.py`, and their existing tests/accepted materializers. The package module explicitly owns **skills-only source verification** and is not a plugin installer. Do not silently add executable plugins to that contract. Recover the current Craft/role-kit and fable-mode owners before modifying either; do not deploy an older remembered revision or make Fable a mandatory model for every principal.

Own the rich-environment contract, capability inventory, approved skill closure, native configuration qualification, and parity evaluation. Lane 3 owns the distributable Executive plugin and its final connection composition. Lane 2 owns repo/dev-tool preparation. Lane 4 owns communication action bindings. Parent owns #999/#992/#919 native adapter/admission integration. Shared policy files require current owner reconciliation; start with path-disjoint tests/specification when occupied.

### Implementation sequence

1. Build a bounded baseline from the exact installed native CLI/SDK version, project/user/managed configuration precedence and available tools. Record only non-secret facts. Compare interactive native Claude with the intended local COO harness on the same capability requirements; do not infer parity from a CLI label or a plugin manifest.
2. Define two explicit environments: sealed bounded worker and rich COO principal. Specify which skills, native tools, approved hooks, LSP/developer tools, browser/artifact tools and MCP actions each can consume. Preserve the existing delegated authority and native-helper budget/child policy, including #980's acceptance status. No permission-bypass flag, hidden native fanout, or routing reset.
3. Reuse the current capability package/materialization owner for a discoverable catalog with bounded, on-demand loading. Cover orchestration, repository reasoning, planning, debugging, TDD, review, research, browser verification and document/data workflows where the actual tasks require them. Produce immutable source/version/digest references, dependency closure, declared side effects and revocation behavior. Do not fill every prompt with the entire catalog.
4. Connect native plugin installation/update/rollback through the existing native package and host-release owners. Scope it to the intended runtime profile, not a blanket edit of all users' global settings. Detect unreviewed marketplaces, missing executables, conflicting hooks, ambient/cloud plugin drift and stale versions. If an executable-package policy is genuinely absent, freeze the smallest extension with its current policy owner rather than treating skills-only proof as authorization.
5. Prove an offline installation/materialization and discovery vertical using disposable fixtures. Then deliver the installable, source-qualified configuration to Lane 3. Leave only genuine later enrollment/native-model proof at the no-login boundary.

### Acceptance and adversarial tests

Proposed dedicated test owner: `tests/test_coo_environment_parity.py` after collision check; reuse current capability-package tests rather than duplicating their validator. Include `test_rich_profile_does_not_widen_sealed_worker`, `test_revoked_skill_is_not_loaded`, `test_plugin_version_drift_is_visible`, `test_missing_required_tool_is_not_ready`, and a proof that the materialized profile is consumed by the actual native launch composition in an offline harness.

Define a scored task benchmark before running it: cross-repo diagnosis, bounded delegation, failing-test repair, review response, durable handoff, documentation/artifact work, and receipt-backed communications. Evaluate task correctness, reproducibility, refusal quality, completion and total effort; same-model/same-task comparison where feasible. Offline fixtures establish wiring, not behavioral superiority. Native before/after runs await the approved no-login boundary being lifted or a separately authorized already-enrolled test surface; do not infer their results.

### Return and continuation

Return the exact environment/package revision, approved skill/tool matrix, observed native versions, verification commands/results, consumer proof, denied/missing features and rollback/revocation path. Lane 3 consumes these references, not copied ambient home directories. Report source-qualified versus native-proven separately, and persist the result in the existing #676/Agent OS parent. No independent environment registry.

### Primary documentation to verify at pickup

Anthropic's plugin manifest and CLI references describe the native packaging/launch surface; the settings documentation describes scope, precedence and trust-dependent loading. Validate every chosen setting against the actual installed version, not only the latest website.

- https://code.claude.com/docs/en/plugins-reference
- https://code.claude.com/docs/en/cli-reference
- https://code.claude.com/docs/en/settings
- https://code.claude.com/docs/en/agent-sdk/overview

## Annex 2: Three-repository COO workspace and developer-tool parity

**Requested initial profile:** Sol Pro — sustained workspace/toolchain integration; Extra High for iterative edits and tests.

**Proposed lane operation:** `coo-three-repo-workspace-20260926-sol-001`.

### Outcome

A COO session can directly inspect and perform authorized development across all three real repositories, run their relevant tests and browser checks, and return exact cross-repo evidence without operating in somebody else's dirty checkout. Repository access must be usable in the native session, not just described in a README.

### Exact identities and existing owners

The verified repositories are:

| Repository | GitHub repository ID | Default branch |
|---|---:|---|
| mastermindx-market-intelligence/Mastermind | 1317762013 | master |
| mastermindx-market-intelligence/macro | 1266869026 | main |
| mastermindx-market-intelligence/mastermind-terminal | 1290596392 | master |

Refresh head SHAs on pickup. Resolve host paths from existing workspace/host configuration and prove each path's remote/repository identity. Do not equate a folder label such as “Macro Main” or a copied directory with the canonical repository.

Reuse `control_plane/executive_workspace.py`, `common/executive_workspace_contract.py`, the installed `mmx-workspace` source-custody launcher, existing multi-host placement and the three repositories' delivery/test workflows. Existing workspace tests include `tests/test_executive_workspace.py` and `tests/test_executive_workspace_mount.py`. A launcher for one repo does not prove it supports the other two: inspect its contract and extend the existing owner rather than inventing a parallel worktree allocator.

Own repo binding, development dependencies, toolchain/preflight and native process visibility. Do not edit native provider authentication, #999/#992 transport, #919 admission, #962 plugin packaging, or Lane 4 communication identities. Supply verified workspace/tool references to Lanes 1 and 3. No hardcoded provider account or host selection in a user task payload.

### Implementation sequence

1. Recover the current host/workspace owner and inspect exact permitted roots, remotes, branches, mounts and current source leases without reading credentials. Preserve dirty/shared checkouts and all unresolved operations. Keep workspace allocation on the current owner and eligible host placement on Capacity; do not default every test to the busiest Studio.
2. Make all three repos directly available to the rich COO profile. Read access can span the approved repo set; any source modification must use the appropriate current-authorized worktree(s) with per-repo base/branch/custody. A cross-repo mission may need three granted worktrees, not an artificial single-repo limitation. Never give a sealed child every repo merely because its parent can see them.
3. Prepare the exact required language/runtime/package-manager/test dependencies in the established environment owner. Discover actual commands from each repo. Include browser/dev-server resources, ports and build outputs only through their existing resource/lease owners. No unrelated global package upgrades, duplicate runners or new scheduler.
4. Wire the native rich-session directory/configuration inputs to those verified bindings. Validate path resolution, symlink/mount behavior, spaces in paths, inherited CLAUDE.md/AGENTS.md semantics and directory-trust requirements. Prove the native process can open the intended repo files; a host-side ls is not enough.
5. Provide one read-only cross-repo dependency task and one reversible cross-repo source/test fixture, with exact repo/diff/result references. Exercise cleanup without deleting active work. Implement a useful doctor/preflight through the existing environment owner, not a second readiness database.

### Acceptance and negative cases

Proposed dedicated test owner: `tests/test_coo_multi_repo_environment.py` after collision check. Pin at least `test_three_repo_bindings_preserve_remote_identity`, `test_cross_repo_write_requires_each_worktree_grant`, `test_mount_loss_is_not_empty_repository`, `test_symlink_escape_refused`, `test_dirty_shared_checkout_preserved`, `test_active_workspace_not_cleaned`, and `test_child_does_not_inherit_parent_repo_set`.

An empty/missing mount, wrong remote, missing binary, stale base, occupied port, offline host or unavailable dependency must produce an explicit bounded result, not silently select another repo/host. Source-ready proof requires the actual native-launch configuration consumer plus deterministic file/tool fixtures. Provider inference, account login and production install remain outside this phase.

### Return and continuation

Return exact repo IDs/remotes/base SHAs, approved workspace receipts, native environment version/configuration evidence, commands that passed/failed, read/write distinctions, cleanup proof and the exact remaining onboarding prerequisites. Paths are trusted local configuration, not credentials and not a new cross-host registry. Lane 1 consumes tool availability; Lane 3 consumes workspace references. Update the existing Agent OS parent and cross-link the actual workspace implementation carrier.

### Primary documentation to verify at pickup

Claude's additional-directory configuration is subject to native permissions and trust. Codex and other consumers need their own documented equivalent; do not assume one provider's directory flag configures another provider.

- https://code.claude.com/docs/en/cli-reference
- https://code.claude.com/docs/en/settings
- https://developers.openai.com/codex/config-reference

## Annex 3: Portable local-principal Executive OS and Agent OS plugin

**Requested initial profile:** Astra Pro — cross-provider architecture, authority boundaries and end-to-end plugin convergence.

**Proposed lane operation:** `local-principal-executive-plugin-convergence-20260926-sol-001`.

### Outcome

Claude Code, Codex and other supported local orchestrator sessions use one coherent Executive/Agent OS workflow: load current context, act within their actual role, delegate through the canonical fabric, inspect returns, record decisions/handoffs, and recover the same operation. The packages may differ by provider; lifecycle, authority, identity, continuity and authentication owners must not multiply.

### Existing source to continue

Mastermind **#962** is the existing Claude Executive plugin, not a missing new project:
- observed head `201d8787f825fabbd7562e666ae5fbfc6c32eb8f`;
- `integrations/claude_executive_plugin/.claude-plugin/plugin.json`;
- `integrations/claude_executive_plugin/skills/executive-orchestration/SKILL.md`;
- `integrations/claude_executive_plugin/commands/executive-context.md`;
- package README and `tests/test_claude_executive_plugin_source.py`.

It is Draft/Hold, source-only, with read-only executable instructions. It intentionally has no .mcp.json or hooks and reuses existing #955 registration `mastermind-executive`. Do not interpret the package as installed, authenticated or allowed to commission work.

**#955**, observed head `25a3d7bf9c3e36715789253e1dac24541aa15d00`, owns the incumbent Claude authenticated client edge. Preserve its identity and PKCE/public-client findings; do not create a second OAuth registration. Current COO-role source dependencies include #957/#960/#961 and the existing non-CEO sink #804; reconcile their latest accepted successors before changing scopes. **COO is not CEO**: do not grant `mastermind.executive.intent.submit` to Fable/Claude simply because a CEO app already exposes it. #633's unrelated DCR effect uncertainty remains frozen.

Existing Agent OS continuity carrier: macro #7882, head `c64a5cde875352a7765b23b8dce66bdaf1e94866`. Its older login-first/CEO-submit suggestions are superseded for this commission by role-correct source integration and the no-login phase; preserve useful transport evidence, not obsolete authority suggestions.

Own provider packaging, shared workflow contract, install/doctor/recovery documentation and integration of the three sibling outputs. Do not take their implementation paths. Reuse the canonical runtime/client/Agent OS tools; do not build an MCP server merely to rebrand an already adequate endpoint.

### Implementation sequence

1. Reconcile #962/#955 and discover the actual Codex/local-session equivalent already in the repo. Produce a small provider support matrix: package layout, skills, hooks, MCP transport, native trust and available tool schemas. Unknown is not unsupported. Verify capabilities on the installed version and current official documentation.
2. Freeze one shared role/workflow contract with provider-specific thin packaging. Inputs are accepted role/grant, exact RuntimeBinding/operation, Lane 1 skill/environment references, Lane 2 workspace references and Lane 4 connection/action bindings. Never accept model/account/home/credential selection in ordinary task prose.
3. Implement context reads, bounded role-correct delegation/status/return/reconciliation, and canonical Agent OS read/write workflows through their existing owners. A local token cache is not organizational memory. Durable record updates must target macro/agentos through normal source custody and validation, not a mirrored memory service.
4. Connect accepted components through the existing plugin/client installation owner. Prefer native portable packaging where qualified, but keep compatibility shims for exact supported surfaces. Current OpenAI docs describe a portable root manifest plus supported legacy layouts; that is not proof the installed Claude/Codex versions accept every component. Do not churn #962's manifest without a consumer test.
5. Build an offline local-client -> authenticated-test-endpoint -> role-policy -> fixture Executive operation -> return -> plugin-consumption vertical. Test actual tool discovery and schemas, not just SKILL.md substrings. Source docs and fixtures can be completed without account login. Prepare a precise later enrollment/canary sequence without executing it now.

### Acceptance and failures

Extend `tests/test_claude_executive_plugin_source.py` on its reconciled carrier and add provider-neutral integration tests in an agreed disjoint path. Require `test_coo_profile_exposes_no_ceo_submit_tool`, `test_skill_tool_dependency_is_resolved`, `test_missing_auth_is_not_connected`, `test_stale_runtime_binding_refused`, `test_result_is_consumed_by_exact_parent`, `test_agentos_write_uses_canonical_repo`, and `test_lost_submit_response_reconciles_same_operation`.

Prove child delivery, ACK, admission, START, result, parent consumption and acceptance separately. Test unavailable sibling MCP, revoked permission, partial install, stale package and service restart. Never repair these by copying tokens, falling back to the raw control socket, or changing accounts.

### Return and continuation

Return installable package revisions for each supported surface, exact component/support matrix, offline integration evidence, current role/tool permissions and a minimal per-account onboarding checklist. Mark unsupported/unproven surfaces honestly. Coordinate one final config writer, not four sessions racing to edit .mcp.json. Persist in #962/its lawful successor and the existing Agent OS parent; parent Sol retains overall acceptance and the native worker lane.

### Primary documentation to verify at pickup

Skills encode workflow; MCP servers provide controlled actions and authorization. Packaging does not transfer marketplace approval, native hook trust, account authentication or permission.

- https://code.claude.com/docs/en/plugins-reference
- https://developers.openai.com/plugins/build/plugins
- https://developers.openai.com/plugins/build/skills
- https://developers.openai.com/plugins/guides/submit-claude-plugin

## Annex 4: COO GitHub, Slack and Mastermind OS communications

**Requested initial profile:** Sol Pro — sustained multi-system integration; Astra consultation only for a material authority exception.

**Proposed lane operation:** `coo-communications-mcp-integration-20260926-sol-001`.

### Outcome

A local COO can read the relevant GitHub/Slack context, leave a useful PR comment or review reply, continue the exact Slack thread, inspect responses, and expose those actions and receipts in Mastermind OS. Communication must work through actual supported tools—not depend on a human copying text, a global transcript dump or a second agent inbox/control plane.

### Owners and scope

GitHub owns implementation/PR/CI evidence; Slack owns transport; Executive/Agent Relay/Dialogue and RuntimeBinding own canonical operation and conversation identity; Agent OS owns durable organizational decisions. Mastermind OS projects and acts through those existing services. Existing accepted consultation transport includes Mastermind #986; inspect the current communication owner before adding any inbox/wake behavior. The parent #999/#992 adapter work and #955/#962 Executive client/plugin work stay with their owners.

Start by discovering current official GitHub and Slack MCP capabilities on the intended local session, and existing company adapters. Prefer official servers when they meet the action, permission and receipt requirements. A minimal company adapter is justified only by a documented missing capability or identity/effect constraint; it must reuse existing auth/transport/effect owners. Do not build another general GitHub or Slack client just because a custom plugin is convenient.

Own communication action contracts, fixture integration, and the smallest existing Mastermind OS consumer hook. Lane 3 is the single final plugin/configuration compositor. Supply configuration references and exact tool requirements; do not independently overwrite its MCP registration. Reconcile the current Mastermind OS/UI source owner before changing shared application paths.

### Implementation sequence

1. Inventory exact actions and permissions: repository/PR/issue discovery; read comments and inline review threads; create a bounded issue/PR comment; reply to an exact review-thread root; Slack channel/thread discovery, read, send/reply and reaction where useful. Separate comment authority from merge, admin, deletion and deployment authority. Verify actor attribution and target identity rather than imitating the Chairman.
2. Choose one lawful carrier per modifying action. Define workspace/channel/thread-root or repo/PR/review-comment identities, current actor, content bounds, readback and effect behavior using existing operation/evidence records. Reuse existing OAuth/client bindings where suitable. Official Slack MCP currently requires an eligible registered app and supports no DCR; do not start an ad hoc registration flow. GitHub supports scoped toolsets and exclusion/read-only controls; tool exposure is not proof of account permission.
3. Implement an offline actual-MCP-client to fixture-server vertical for approved actions, with real tool discovery and typed results. Include long/paginated threads, edited/deleted parents, stale PR heads, wrong repository/workspace, permission denied, rate limits, and reply loss after a successful write. Do not blindly retry uncertain comments/messages or “fail over” to another carrier. Retrieved messages and tool output never originate authority by themselves.
4. Connect the returned action/receipt to the existing Mastermind OS view. Show pending, sent, read back, reply received and unresolved states from their real owner—not a fabricated local lifecycle. A useful first vertical is a code-review question with exact PR/thread evidence, a bounded response, verified readback and visible return to the correct parent. Do not require a whole new chat application.
5. Deliver the minimal bindings and workflow skill references to Lane 3. Prepare later real-target tests on specifically authorized review/test threads. No new account login, credential export, broad permission grant or production activation now.

### Acceptance and negative tests

Proposed dedicated conformance test owner after collision check: `tests/test_coo_communication_conformance.py`. Include `test_reply_preserves_exact_thread_root`, `test_review_reply_targets_original_comment`, `test_lost_write_response_is_not_retried`, `test_wrong_workspace_refused`, `test_permission_denial_does_not_switch_carrier`, `test_paginated_read_does_not_claim_completeness_early`, `test_retrieved_message_cannot_grant_authority`, and `test_mastermind_os_displays_real_receipt_not_inferred_success`.

Test delivered versus consumed and ACK versus START separately. A browser/UI change needs real browser proof on its exact candidate; fixture screenshots are not production proof. Missing live auth stops only the live action lane, not source, conformance or consumer implementation.

### Return and continuation

Return the exact official/custom choice with evidence, action/tool/permission matrix, bound consumer path, source revisions, offline test receipts, unresolved auth/admin controls and later harmless real-path canary. Record decisions in the existing Agent OS parent and communication implementation carrier. Include what was deliberately excluded, particularly merge/admin/delete actions. No new inbox registry, polling daemon, duplicate message store or background wake claim.

### Primary documentation to verify at pickup

Slack's official MCP exposes message/thread/search capabilities and its own app/auth requirements. GitHub's official MCP can restrict tool exposure. Confirm the intended provider surface can actually use the selected configuration; a ChatGPT connector being installed does not enroll Claude or Codex.

- https://docs.slack.dev/ai/slack-mcp-server/
- https://github.com/github/github-mcp-server/blob/main/docs/server-configuration.md
- https://docs.github.com/en/copilot/how-tos/provide-context/use-mcp-in-your-ide/configure-toolsets
