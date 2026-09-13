---
workstream: WS:EXECUTIVE-CAPACITY-FABRIC
session: claude/fable-native-harness-20260913-sol
model: sol
ended_because: blocked
mission: >
  Give Fable a native-feeling orchestrator environment without uncontrolled premium
  fan-out, using existing routing, capability, workspace and Executive lifecycle owners.
state_before: >
  PR 7114 head 0c95fa51c4bd0b79be28e30bf7a8fa263b2ae622 had strict opt-in
  router-only/native-leaf profiles and 110 passing source checks, but no installed-CLI
  proof. The compiler validated source hooks without carrying them in emitted settings.
changed:
  - path: scripts/fable_harness_profile.py
    what: Carry existing routing/context hooks in emitted settings and declare exact workspace sources; map guard command failures to blocking exit 2.
  - path: tests/test_fable_harness_profile.py
    what: Assert self-contained compiler-to-hook wiring, required source hashes and missing-command refusal.
  - path: tests/fable_native_cli_conformance.py
    what: Add explicit opt-in installed-CLI qualification with a fixed loopback oracle, isolated homes, bounded processes and exact tool-result bindings; no real inference.
  - path: tests/test_fable_native_cli_conformance.py
    what: Verify the protocol oracle, exact result bindings, finite request budget and native tool-free prefetch distinction without launching Claude.
  - path: research/evidence/fable_native_cli_qualification_2026-09-13.json
    what: Preserve exact binary/compiler/driver hashes and six actual native outcomes plus a paired old-compiler failure.
  - path: research/FABLE_NATIVE_HARNESS_ARCHITECTURE_2026-09-13.md
    what: Update proven configuration behavior, source-owner integration gaps and the sealed-leaf versus rich-principal boundary.
prs: [7114]
verified:
  - claim: Current focused source tests pass in the partial candidate snapshot.
    command: python -m pytest -q tests/test_fable_harness_profile.py tests/test_fable_native_cli_conformance.py --junitxml=continuation-tests.xml
    result: 123 passed in 2.45s; 113 profile checks and 10 oracle checks; not full repository CI.
  - claim: Installed native Claude exposes the intended scout tools and returns the actual fixture value to the exact parent.
    command: python3 tests/fable_native_cli_conformance.py --run --binary /absolute/installed/claude --source-root /exact/candidate --evidence /new/receipt.json
    result: Final six-case native matrix passed on Claude Code 2.1.239; valid scout made two local protocol requests, invoked Read, and returned its value. No real model inference.
  - claim: The native CLI rejects ten Fable requests, premium overrides and incomplete missions under the emitted profile.
    command: The same native six-case command; native-exact-after-06.json and the published compact receipt retain exact refusal codes and native statistics.
    result: Ten NATIVE_LEAF_ONLY errors, one NATIVE_MODEL_PIN_REQUIRED error and one missing-commission error; zero helper starts for each refused case. Router-only omits Agent.
  - claim: The leaf context stops at its fourteen-turn ceiling.
    command: The same native command with case leaf_turn_limit; parent maximum set to twenty turns.
    result: Exactly fourteen leaf requests, one parent tool return and no descendant; native completed is termination, not research acceptance.
  - claim: Missing hook delivery is causally demonstrated against the original compiler.
    command: Final native driver v6 with case premium_override against original source 0c95fa51c4bd0b79be28e30bf7a8fa263b2ae622, then the fixed compiler.
    result: Old emitted settings started one Sonnet helper instead of refusing the Opus-shaped request; fixed settings refuse before any helper. This is not evidence of Opus billing.
unverified:
  - claim: A real Fable principal can use an admitted rich Claude execution surface and receive a routed economical worker result.
    what_would_verify: Existing rich adapter/capability/workspace owners must integrate the profile; healthy Executive admission and exact RuntimeBinding/Capacity must then carry one real input and exact-parent result.
  - claim: The policy is installed across active or production sessions.
    what_would_verify: Reviewed source release plus intended-realm effective configuration, binary, source and served-model attestation; no active session was changed here.
  - claim: Full native skills, native resume and root-shared nested-leader budgets work.
    what_would_verify: Qualify actual resolved skills and resume behavior, then extend existing atomic root admission and prove a bounded leader-worker tree; these remain later architecture waves.
  - claim: Full repository CI, full-store Agent OS validation and independent review are complete.
    what_would_verify: Consume the same PR's exact-head normal validation, complete writer reconciliation and attributable non-author review; partial local checks do not replace them.
unresolved:
  - Executive state connector still returns invalid_mcp_response with gateway 404; no runtime admission attempted.
  - Mac Studio has no live command connection; Mini relay reports ENOSPC. MacBook command access and native qualification succeeded without migrating a Job or modifying another worktree.
  - Rich Claude capability/adapter integration is not supplied by this Macro compiler or by the separately owned sealed subscription leaf in Mastermind PR 581.
  - Native Skill and SendMessage remain disabled in strict profiles pending qualified restoration.
next_actions:
  - Keep PR 7114 on its existing branch and carrier; obtain source review, exact-head normal CI and full writer reconciliation without auto-merge.
  - Reconcile the existing rich OperatorHarnessAdapter/capability/workspace source owner and integrate the profile's CLI arguments plus required_workspace_sources there; do not weaken PR 581's sealed leaf.
  - When current Executive admission, binding and capacity are readable and healthy, prove one real principal request through the existing router to one qualified economical worker and an exact-parent useful result.
  - Then complete native skill qualification and shared-root nested-leader admission; do not raise the depth constant or spend Fable to repeat deterministic checks.
do_not_redo:
  - The six native fixture cases and paired compiler defect are proven on the cited exact bytes; rerun only for relevant source or binary movement.
  - The original 110-check receipt and original repeated-Fable hook reproduction remain historical evidence, not new-head proof.
  - No new router, queue, quota ledger, session registry, watcher or provider launcher is needed.
  - Mastermind PR 581 is a sealed leaf adapter with disableAllHooks and native-agent denial; it is not a rich principal harness.
danger_areas:
  - The final native driver uses a scripted loopback provider. CLI model names, token counts and dollar estimates do not attest a served model or billing.
  - Two preliminary exact-argv runs misclassified native tool-free prefetches; they are excluded. Final v6 distinguishes them and binds returns to tool-use IDs.
  - Source files declared by required_workspace_sources still need exact staging and attestation by the existing workspace owner before a real launch.
  - Four concurrent agents is only a vendor hint; the fourteen-turn per-helper limit is not a root, account, lifetime or ultracode budget.
  - Hook commands are not an OS sandbox. Managed settings, shell access, credentials and other execution tools need the existing host/grant boundary.
  - Unprofiled active sessions retain their previous behavior; merging this PR is not installed protection.
---

## 0. State - what is true now

The compiler/guard is **BUILT_NOT_PROVEN for production, with native fixture
qualification**. This continuation fixed a real integration defect: the emitted
profile now carries the existing routing hooks instead of depending on ambient
project settings. The current focused suite passes 123 checks and six cases passed
on the actual installed Claude Code 2.1.239 binary. The native parent and helper
were driven by a fixed local oracle, not by paid Fable or any remote model.

Source carrier remains Macro PR #7114, branch
`claude/fable-native-harness-20260913-sol`, operation
`fable-native-harness-20260913-sol-001`. Original source head is
`0c95fa51c4bd0b79be28e30bf7a8fa263b2ae622`; protected Mastermind procedure was
`9ed16bf0fcc5b47e870350ff2413ff5c8c73b447`, Skillpack 1.0.1/bootstrap 1.
Re-pin current procedure at continuation. No reciprocal worker watcher exists.

The machine receipt is
`research/evidence/fable_native_cli_qualification_2026-09-13.json`, SHA-256
`412b77a7f52c5b0f9ff26e828081cad4c56aa9624e9ac97b51c9e6be0689df32`.
Qualified compiler SHA-256 is
`13db4fedf9bb37848f752c8539b1d268d0c71d540190a41d411139f91d33c359`;
driver SHA-256 is
`99eb93036779022c9d709b63373461edb686b04580b370f2645a884dea8533bf`.
Raw immutable receipts `native-exact-before-06.json` and
`native-exact-after-06.json` are on the authorized MacBook under
`~/.local/share/mastermind-evidence/fable-native-7114-20260913-sol/`.
Their hashes, binary identity and observed outcomes are in the public receipt.
All test runs returned a terminal process result; none is an in-flight provider Job.

## 1. What is left - in order

The highest-leverage product step is architecture wave N1: integrate this profile
through the existing rich capability/workspace/adapter boundary, then prove real
admission, routing and useful exact-parent consumption. Source review and current
writer reconciliation are required before release. Runtime state is not available
through the Executive connector, so a real launch is not authorized by these tests.
The broader architecture remains in
`research/FABLE_NATIVE_HARNESS_ARCHITECTURE_2026-09-13.md`.

Do not treat restoring the 404 as the only missing step. Mastermind PR #581 at
`e6aca940eaa2ee5e9971b4526d700dec62351e4a` is a separately owned sealed leaf.
Its safe-mode invocation and `_closed_settings` disable hooks, Agent and Skill.
Do not strip those safeguards to host a principal. The protected capability
registry still names Codex execution surfaces; this compiler does not add a
registered rich Claude capability. The existing rich-harness owner must qualify
that consumer rather than create another launcher or claim it already exists.

After the real N1 result, N2 qualifies actual resolved skills/resume, and N3 extends
the existing atomic admission for a shared root budget. The closed depth-one
policy stays unchanged until that joint contract is implemented and proven.

## 2. What will bite the next session

The native fixture used the compiler's actual arguments with ambient settings
sources disabled and no test-injected hooks. This matters: manually adding hooks
in a test made the earlier profile look integrated when its output was not.
The repaired output also declares which exact sources must be staged. It does not
stage them, sign a grant, reserve capacity or prove managed-policy compatibility.

The baseline Opus-shaped request resolved to Sonnet on the local wire. Report the
actual defect as a missed refusal, not invented premium billing. A native turn-limit
return is termination, not accepted completion. A fake provider's usage values
must not feed Provider Control or any real quota ledger.

## 3. What was decided and found

Keep intelligent decomposition with the principal and deterministic placement,
spend reservation and lifecycle in the existing owners. Extra Fable defaults to
zero. Preserve native leaf versus independent leader boundaries. No new DEC/DSC
key was needed; detailed findings and falsifiers live in this same research/evidence
carrier. Existing sibling adapter and capacity work remains independently owned.

## 4. Not in scope - do not adopt

No real provider call, account enrollment, credential read/copy, purchase, global
configuration change, production service, current-session mutation or Executive Job
was performed. Do not use a blocked connector as permission to call a provider
CLI directly. Do not alter another worker's branch or clean the full Mini.
Hold on source collision, missing admission, stale binding/capacity, unknown effect,
unqualified tools or served-model substitution; preserve the same operation until
its effect is reconciled. Source tests, native fixture proof, merge and production
acceptance remain separate facts.
