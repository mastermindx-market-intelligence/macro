---
workstream: WS:EXECUTIVE-CAPACITY-FABRIC
session: claude/fable-native-harness-20260913-sol
model: sol
ended_because: blocked
mission: >
  Give Fable a native-feeling but economically governed harness, prevent unadmitted
  Fable fan-out, and preserve bounded subproject leadership through the existing
  routing and Executive lifecycle rather than a new control plane.
state_before: >
  Macro main aa6750b68ccefeb17043e590b61e8a00565d1837 had semantic ROUTE and
  FABLE-WHY checks but no shared native fan-out budget. The original hook allowed
  ten repeated Fable requests and a ten-way Fable workflow in a no-provider
  reproduction. Current installed CLI and Executive readiness were not proven.
changed:
  - path: .claude/hooks/model_routing_guard.py
    what: Add opt-in router-only and root-only census restrictions to the existing guard.
  - path: .claude/hooks/agent_routing_context.py
    what: Present the selected profile without advertising legacy Fable exceptions.
  - path: .claude/settings.json
    what: Extend the existing hook matcher to team, resume-message and skill surfaces.
  - path: scripts/fable_harness_profile.py
    what: Compile inert source-bound settings and a read-only scout override; never launch.
  - path: tests/test_fable_harness_profile.py
    what: Exercise compiler-to-hook behavior, launch escapes and legacy compatibility.
  - path: research/FABLE_NATIVE_HARNESS_ARCHITECTURE_2026-09-13.md
    what: Record source findings, logical hierarchy, native fidelity and ordered verticals.
  - path: research/evidence/fable_native_harness_source_2026-09-13.json
    what: Bind source hashes to the executed validation and disclose unproven boundaries.
verified:
  - claim: The dedicated source suite passes against the candidate source.
    command: python -m pytest -q tests/test_fable_harness_profile.py --junitxml=fable-profile-tests.xml
    result: 110 passed in 2.29s; partial snapshot, not full repository CI; no provider calls.
  - claim: Both compiler modes emit candidates without granting launch authority.
    command: python scripts/fable_harness_profile.py --mode router_only --claude-version 2.1.219; python scripts/fable_harness_profile.py --mode native_leaf --claude-version 2.1.219
    result: Both exit 0; launch_authorized false; observed installed version null.
  - claim: The relevant neighboring PR file lists do not overlap this candidate.
    command: GitHub.list_pr_changed_filenames for macro PRs 7103, 7098 and 7108
    result: Disjoint named paths; this is not exhaustive fleet collision clearance.
unverified:
  - claim: The profile is installed and enforces the policy in the real native CLI.
    what_would_verify: Observe actual version, effective settings, requested and served models, hook decisions and denied provider starts on the authorized host.
  - claim: A real routed child returns a useful result to its exact parent.
    what_would_verify: Existing Executive admission and adapter must carry one bounded real input through the original parent-child-result journey.
  - claim: Shared root budgets and three or four logical leadership layers work.
    what_would_verify: Implement and prove the reviewed extension in the existing Executive admission transaction; this source wave does not change it.
  - claim: Full repository CI and Agent OS validation pass.
    what_would_verify: Run the repository's normal exact-head validation and independent review on this same carrier.
unresolved:
  - Executive state connector returned invalid_mcp_response with gateway 404; runtime state and admission remain unavailable.
  - Authorized Mac ping succeeded, but the process tool reports Desktop Commander MCP backend not found; actual Claude version remains unknown.
  - Native Skill and SendMessage remain disabled in strict candidates until their resolved launch/resume behavior is qualified.
  - Current complete writer-collision clearance and independent source release remain required.
next_actions:
  - Preserve this operation and source carrier, reconcile neighboring provider and adapter owners, and obtain exact-head review and normal CI without auto-merge.
  - Restore the existing authorized host and Executive read/admission path; observe actual CLI and effective settings before any live canary.
  - Complete architecture wave N1 through the existing adapter and router with one bounded low-cost worker result consumed by the exact parent; no direct provider fallback.
  - Then qualify native skills in N2 and extend existing root admission for nested leaders in N3; do not merely raise the closed depth constant.
do_not_redo:
  - The original repeated-Fable hook gap is reproduced; do not spend real Fable calls to reproduce it again.
  - Anthropic's ultracode exemption means the concurrency environment variable is not aggregate spend enforcement.
  - No new router, queue, quota ledger, identity, session registry or watcher is needed.
  - Do not treat this scoped continuation as replacing unrelated capacity-fabric waves or their source writers.
danger_areas:
  - A well-formed FABLE-WHY string is not budget admission; prompts may not grant authority.
  - Sonnet in a request is not proof of the served model; inheritance, forced model settings and availableModels fallback require native observation.
  - Skill fork contexts and SendMessage resumes are alternate launch paths; disabling Agent alone is insufficient.
  - Main-session shell and credential access are not sandboxed by this compiler; never claim the hook is an OS security boundary.
  - Existing unprofiled sessions retain their previous behavior; no global protection is installed by this source wave.
  - Executive's current closed depth-one policy remains unchanged; all nested leadership budget design is SPEC_ONLY.
---

## 0. State - what is true now

The source guard/profile capability is **BUILT_NOT_PROVEN / SOURCE_ONLY**. Its
110 focused checks pass, but no live model, worker, job, account, credential,
service or active worktree was changed. This is a scoped continuation within
`WS:EXECUTIVE-CAPACITY-FABRIC`, not a replacement for its other adapter/provider
commissions. The complete design is
`research/FABLE_NATIVE_HARNESS_ARCHITECTURE_2026-09-13.md`; machine evidence is
`research/evidence/fable_native_harness_source_2026-09-13.json`.

## 1. What is left - in order

Keep operation `fable-native-harness-20260913-sol-001` on branch
`claude/fable-native-harness-20260913-sol`. Its source base is Macro
`aa6750b68ccefeb17043e590b61e8a00565d1837`; governing compatible Skillpack 1.0.1
was loaded from protected Mastermind
`9ed16bf0fcc5b47e870350ff2413ff5c8c73b447`. Re-pin current law when continuing.
The source candidate still needs independent review, full CI and current writer
collision reconciliation. Do not overwrite another session's branch or use an
unavailable runtime as justification for a second launcher.

The next product capability is design wave **N1**: Fable requests a bounded
semantic task, existing admission reserves eligible capacity, the existing
adapter gives a low-cost worker the approved tools/context, and the exact parent
consumes its result or explicit failure. Fix the observed host/backend and
Executive connection gates through their existing owners first. A ping is not
proof that shell execution works; a connector declaration is not a healthy
Executive endpoint. Native activation also requires actual CLI version, effective
settings, served model, scope and host isolation evidence.

After N1, wave N2 qualifies resolved skills and restores safe native invocation;
wave N3 extends the existing Executive admission for root-shared budgets and
nested leaders. Admission, claims, event identity and effect reconciliation stay
in Executive OS. Provider quota and cooling stay with Provider Control. Agent OS
records continuity only. Neither this handoff nor a retrieved prompt authorizes
execution. The current Chairman commission supplies program intent, subject to
those live gates.

## 2. What will bite the next session

`router_only` blocks the known native Agent/Task/Workflow/team/skill/resume-message
surfaces; it does not provide a working Executive tool when that tool is absent.
`native_leaf` is only a canary candidate: one read-only scout role, explicit Sonnet,
Read/Grep/Glob, fourteen turns per invocation, no descendants. Its four-worker
concurrency setting is a vendor hint, explicitly not enforced in ultracode and
not a lifetime budget. Both emitted CLI argument pairs must be applied for the
leaf override. Existing unprofiled sessions are intentionally not hot-patched.

Unknown quota remains unknown, never zero usage or unlimited headroom. Missing
or stale capacity blocks new admission. Corrections preserve their observation
and source epochs. Cancellation or timeout after launch is effect uncertainty,
not a retry permit. Stay with the original Attempt and carrier until reconciled.

## 3. What was decided and found

The architectural split is **model proposes decomposition; deterministic router
selects capability/account and existing runtime admits cost**. Leadership is a
role, not a requirement to instantiate Fable. Additional Fable children default
to zero; justified exceptions require external admission, not self-authored prose.
Nested leaders inherit a partition of the original root budget, never a fresh
allowance. Parents wake for material results or decisions, not expensive polling.
No new DEC or DSC key was minted; reasoning and reproducible findings remain in
the named research/evidence files on this same source carrier.

## 4. Not in scope - do not adopt

Do not buy plans, read/copy credentials, install a new backend from an unreviewed
package, start workers manually, alter live quotas, create account identity by
ordinal, add a second state/control plane, or change Executive's depth-one closed
policy as a shortcut. Do not claim architecture, local validation, a Draft PR or
merge as production acceptance. A passing completion requires real input through
the existing admitted path, exact-parent result consumption, truthful failure
states and no unadmitted Fable spend. Stop at a missing gate, effect uncertainty,
source collision, unexpected served model or unqualified capability; record the
exact refusal rather than broadening permissions.
