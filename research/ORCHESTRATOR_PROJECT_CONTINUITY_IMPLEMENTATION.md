# Orchestrator project continuity implementation

## Intended outcome

The 2026-10-21 assignment is to give Astra and the other currently assigned
orchestrators the planning and recovery support needed to complete long projects.
The harness should preserve the goal, constraints, phase plan, accepted work,
pending reviews, effects and next action across compaction and interruption.
It should continue authorized ready work without making the user repeatedly say
“continue.” Model choice should not determine whether those facilities exist.

The canonical project identity is
[WS:ORCHESTRATOR-PROJECT-CONTINUITY](../agentos/workstreams/WS-ORCHESTRATOR-PROJECT-CONTINUITY.md).
This is an engineering assignment within the existing executive-os program.
The record is organizational knowledge; actual execution grants, liveness and
custody remain with their existing owners.

## Architecture and ownership

| Concern | Existing owner | Required integration |
|---|---|---|
| Goal, phases, accepted outcomes, decisions, handoff and next action | Macro Agent OS workstream/decision/discovery/handoff records | Maintain concise current records at material boundaries; use deep research documents for history |
| Exact recorded project context | Macro compile-context; Mastermind ops.fabric_launch.agentos.read_context | Supply the actual owner-produced bundle to the intended session |
| Cross-owner current facts and scope | Mastermind SessionTruth acquisition and ContextResolver | Acquire authentic observations; select decisive exact references; preserve unavailable sources |
| Worker dispatch, leases, roots, effects and result custody | Existing Executive and paid Subagent Fabric owners | Preserve original carriers, identity and unresolved effects |
| Attended Codex context ingress | New thin SessionStart adapter using existing owner reads | Qualify startup/resume/compact delivery in the installed Codex entrypoint |
| Active-boundary return attention | Existing Codex Fabric Stop helper/subscriptions | Diagnose source drift, qualify reviewed bindings and prove original-parent consumption |
| Full semantic continuation and model input delivery | Existing continuation contracts, operator/runtime owners and Codex turn-input loader | Complete missing production composition without inventing runtime receipts |
| Evaluation | Existing project acceptance and review owners | Prove behavior in normal and interrupted journeys; keep source, installation, delivery and acceptance distinct |

Agent OS does not dispatch or decide whether work may run. The Improvement Agenda
remains the company priority owner. A task list in a transcript is only a session
view of recorded project direction. No additional global task database, scheduler,
lease registry, history mirror or provider-specific source of truth is introduced.

## Verified starting point

The source review was pinned to Mastermind d010b161386853586198a43f9ea9f535bbebb377,
then the context implementation acquired
1b240d2fcbd576a31cca080950cac4fb3b0af044. The intervening applicable change clarified
refusal provenance; the context dependencies were unchanged. The Agent OS source
workspace began at Macro 96649436590c5d25f503eac90a74c2379e4f8a8e.

Several useful contracts already exist, but their existence does not prove a
working long-project principal loop:

- ContextResolver selects references from a SessionTruth receipt. Its renderer
  does not materialize the project mission.
- ops.fabric_launch.agentos.read_context already expands an exact workstream by
  calling the incumbent compiler once with bounded output and process settlement.
- operator_continuation.py supplies a production-inert contract. The referenced
  operator_continuation_sources.py production builder was not present at the
  inspected pin; PREPARE composition must not be claimed from pure validation.
- The inspected managed Executive operator path was a bounded planning turn and
  the supervisor worker path was one-shot. Neither is evidence that an attended
  Astra principal can advance a project indefinitely.
- The installed Codex SessionStart definitions provided sparse-workspace/storage
  support, not demonstrated project-state recovery. The inspected Claude context
  hook supplied static routing guidance; it was not a mission-state loader.
- Both inspected M2 Codex Stop definitions had stale adapter-source pins. The
  reviewed preflight returned exit 78 for both without reading results or
  subscriptions. This is a configured failure mechanism, not a native-run trace.
- The exposed Executive read and Session Bridge research submission returned
  backend_unavailable. No worker START receipt was observed. The bounded source
  work therefore continued directly under the assigned principal's source custody,
  with independent review.

The screenshot that motivated the assignment shows visible task planning and
continued work around compaction. It is not evidence of Claude's private internals
or of automatic recovery from a crashed or idle process.

## Source slices implemented

### W0: return-binding preflight

Mastermind PR 1664 adds a read-only diagnostic for the actual configured Fabric
Stop definitions. It checks adapter-source pins, hash-named helpers, supported
command syntax, fixed identities and state-directory metadata. It reports native
loading and delivery as UNOBSERVED.

The local acceptance command is:

```sh
python3 -B -m pytest -q tests/test_fabric_stop_preflight.py tests/test_fabric_stop_return.py tests/test_fabric_stop_subscriptions.py tests/test_fabric_stop_retirement.py
git diff --check
```

The exact source candidate b740b9afce945d15884076a14bbc6f9471716a46 passed 121
tests and independent review. Installed drift was reproduced by read-only
inspection. The checker never repairs pins or trust and is not a runtime rollout.

### W1: startup and compaction orientation

Mastermind PR 1666 at f48ed994cb1a1800ecfbf3d343fd4c98f27c17f5 adds
integrations/session_bridge/agentos_session_start.py and its operation guide.
The reviewed invocation selects one existing WS key and one exact intended
workspace. Matching SessionStart events reread the incumbent Agent OS owner.
Sibling workspaces receive no injection. An observed session ID is reported,
not promoted into an assignment or parent binding.

The adapter supplies the owner bundle intact, with a 32-KiB limit on the entire
additional-context string. An oversized mandatory bundle is explicitly unavailable;
no constraints or omission accounting are silently clipped. The normal compiler
budget is 4,000 estimated tokens, but the compiler may preserve mandatory material
above that request.

A real composition read of WS:EXECUTIVE-ECOSYSTEM-COMPLETION produced 50,869 bytes,
including 40,792 bytes in the workstream section, with a 10,895-token estimate
against the requested 4,000. The adapter correctly refused complete delivery.
That measured result motivates this focused project record; the unrelated
ecosystem workstream and its history were preserved.

The exact source suites are:

```sh
python3 -B -m pytest -q tests/test_agentos_session_start.py tests/test_fabric_launch_agentos.py tests/test_fabric_launch_agentos_process.py
git diff --check
```

Sixty-one tests passed after independent review. They cover source events,
workspace exclusion, current decision rereads, exact target/hash checks, full
accounting, size limits, uncertain-read handling and bounded malformed CLI input.

The official Codex hooks contract, checked 2026-10-21, supports SessionStart
additionalContext before the immediate post-compaction model request.
Codex's default large-output preview would weaken complete-delivery claims;
the guide therefore uses additionalContextLimit: 0 only for the strictly bounded
handler. Actual installed-version loading, trust and model behavior remain
separate evidence.

### W2: durable planning and checkpoint

The workstream carries the project objective, phase dependencies and next action.
A cumulative handoff carries verified source heads, tests, current gaps,
outstanding effects and do-not-redo facts. This plan carries the architecture
and acceptance sequence. These are existing Agent OS record types.

At a material phase boundary, the orchestrator should update the current phase
and next action, record new decisions or discoveries only when warranted, and
save a recoverable handoff before a risky interruption or actual transfer.
Accepted outcomes stay closed unless current evidence invalidates them.
A checkpoint preserves the mission; it does not end an otherwise useful session.

A fresh adapter read means a new read of the explicitly configured Macro owner
checkout. The hook neither fetches Git nor advances that checkout. The existing
source-acquisition/installation owner must keep it current; source revisions and
publication state must be reconciled before its records are treated as current
shared knowledge. Native acceptance must include a real recorded decision change
reaching that intended owner root, not only a changed fixture in a unit test.

## Remaining implementation and acceptance order

1. Qualify both source candidates through required hosted checks and review.
   Reuse exact unchanged local evidence; investigate genuine candidate failures.
   Do not rerun suites or start duplicate CI just because the session resumes.
2. Complete the held installed-adapter provenance review before repinning a return
   definition. The automatic refusal covered disclosure of the private installed
   source diff. A later human instruction must explicitly address that action;
   source metadata or an old trust record is not substitute approval.
3. Prepare the exact source-qualified context and return definitions through the
   current installation owner, preserving other hooks, immutable trusted helpers,
   active subscriptions and security settings. Obtain actual native Codex review
   and trust. Do not write trusted_hash or mutate a helper to avoid review.
4. Prove complete project context at startup and compaction in an intended attended
   Astra session. The model must recover the current objective and changed decision,
   preserve constraints and accepted work, ignore sibling-project changes, and
   continue the next justified substantive action without another “continue.”
5. Resolve the intended Executive/Session Bridge runtime path through its existing
   owner. Preserve the separate ecosystem readiness and acceptance holds. Do not
   use Studio Direct commands as a worker-handoff carrier or replace an unavailable
   route with an unadmitted provider.
6. Compose full semantic continuation at the existing source/turn-input seams
   using current owner observations. This needs the actual mission assignment,
   source revisions, current authorizations, original root, child/result custody
   and effect state. A model-generated summary or fresh conversation is not
   authority to recreate these facts.
7. Run a multi-phase canary with real delegated work, retained return, independent
   review, acceptance, compaction and continued phase execution. Then repeat with
   an interruption and an unresolved effect; reconcile on the original carrier
   and demonstrate no duplicate effects or claims of transferred custody.
8. Qualify each additional provider adapter against the same recorded project and
   acceptance contract. A Codex success does not automatically certify Claude,
   ChatGPT Web or a managed one-shot worker entrypoint. Idle wake and automatic
   crash restart require an existing admitted runtime owner and distinct proof.

## Completion criteria

Completion requires all of the following observed outcomes, not a favorable
architecture review alone:

- The assigned goal and constraints survive compaction and resume.
- The next action reflects a changed current decision and excludes unrelated work.
- Accepted work is not redone without a material invalidator.
- Real worker START, retained result, review and acceptance belong to the correct
  original parent, with no duplicate writers or repeated uncertain effects.
- The principal advances at least two substantive project phases without repeated
  user continuation prompts.
- A controlled interruption recovers the mission and reconciles outstanding effects.
- Source, installed binding, native loading, model-visible delivery and behavioral
  acceptance are separately evidenced for every claimed entrypoint.

No native canary has been spent by this project. No runtime arm, provider setting,
trust field or live return pin has been changed. The cumulative handoff records
the exact current publication and held-action state.

## Sources

- [Mastermind context reader](https://github.com/mastermindx-market-intelligence/Mastermind/blob/d010b161386853586198a43f9ea9f535bbebb377/ops/fabric_launch/agentos.py)
- [ContextResolver](https://github.com/mastermindx-market-intelligence/Mastermind/blob/d010b161386853586198a43f9ea9f535bbebb377/control_plane/context_resolver.py)
- [Continuation contract](https://github.com/mastermindx-market-intelligence/Mastermind/blob/d010b161386853586198a43f9ea9f535bbebb377/control_plane/operator_continuation.py)
- [Agent OS owner contract](../agentos/README.md)
- [Official Codex hooks contract](https://learn.chatgpt.com/docs/hooks)
- [Return diagnostic source PR](https://github.com/mastermindx-market-intelligence/Mastermind/pull/1664)
