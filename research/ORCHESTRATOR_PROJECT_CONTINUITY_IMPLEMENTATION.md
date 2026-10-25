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

Those availability observations are historical. The read-only Executive state
route returned successfully at 2026-10-21T10:46:34Z from installed Mastermind
80f384b8f58b7ca46422d9783aa5c0613c7bf4b2 and Macro
88804ed7079700c598bb8e04aa64307d1335402d. Its active-builds view was reported as
583 hours old and truncated. The exact Fabric roots route recovered at 10:47:31Z
and retained ceo_submit_armed: false. Neither read creates admission, removes the
arm restriction, qualifies Session Bridge, or proves the candidates installed.

The screenshot attachment could not be opened at its supplied local path.
This implementation is grounded in the user's stated outcome and the inspected
estate; it makes no claim to have observed the screenshot or Claude's private internals.

## Source slices implemented

### W0: return-binding preflight

Mastermind PR 1664 adds a read-only diagnostic for the actual configured Fabric
Stop definitions. It checks adapter-source pins, hash-named helpers, supported
command syntax, fixed identities and state-directory metadata. It reports native
loading and delivery as UNOBSERVED.

The local acceptance command is:

```sh
python3 -B -m pytest -q tests/test_fabric_stop_preflight.py tests/test_fabric_stop_return.py tests/test_fabric_stop_subscriptions.py tests/test_fabric_stop_retirement.py tests/test_ceo_submit_armed_composition.py::test_d8_template_topology_and_protected_defaults
git diff --check
```

The original source candidate b740b9afce945d15884076a14bbc6f9471716a46 passed 121
focused tests. Broader hosted CI then found a D8 source-guard interaction: a mode
literal shared a physical line with a UID check. Commit
7e68f7d3bc5aa90c553c6fe6aaaa3259fe7ae1c3 separates those checks without changing
their behavior or the guard. All 122 cases, including the exact D8 test against
committed HEAD, passed locally after the correction and independent review.
Installed drift was reproduced by read-only inspection. The checker never
repairs pins or trust and is not a runtime rollout.

### W1: startup and compaction orientation

Mastermind PR 1666, initially f48ed994cb1a1800ecfbf3d343fd4c98f27c17f5, adds
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
python3 -B -m pytest -q tests/test_agentos_session_start.py tests/test_fabric_launch_agentos.py tests/test_fabric_launch_agentos_process.py tests/test_ceo_submit_armed_composition.py::test_d8_template_topology_and_protected_defaults
git diff --check
```

Sixty-two tests passed at 6b160c6c17e9ffaa64446b75100628f15c1c40e8, including the
exact D8 guard after an AST-identical formatting repair. Published
76bee5a7276a51cb0777e5f26c6cea5a0036e299 adds only an owner-resolution guide note.
Tested adapter SHA256 is f59adf3597a4b384b21ef686ddb4634b2439402b73acf5bdb2fe9f337857d85b.
The tests cover source events,
workspace exclusion, current decision rereads, exact target/hash checks, full
accounting, size limits, uncertain-read handling and bounded malformed CLI input.

The official Codex hooks contract, checked 2026-10-21, supports SessionStart
additionalContext before the immediate post-compaction model request.
Codex's default large-output preview would weaken complete-delivery claims;
the guide therefore uses additionalContextLimit: 0 only for the strictly bounded
handler. Actual installed-version loading, trust and model behavior remain
separate evidence.

### W1 dependency: compiler latency

The first focused reads timed out at the incumbent 25-second limit, both before
and after committing the records. A 55-second diagnostic completed store loading
in 1.835 seconds, then spent the remainder in repeated Git history walks. The
compiler requested both creation and update dates for every candidate while
discarding every creation date. A membership-only diagnostic counted 48 distinct
date paths; that diagnostic substituted no-date results and is not an owner-read
or delivery proof.

Removing unused creation-history queries alone still timed out at 25.025 seconds.
The reviewed fix therefore queries exact per-path update dates with at most four
concurrent reads. It deduplicates original Path objects within one invocation and
fills every eligible item before budget costing, including workstream constraint
copies. It retains no cache and changes no selection, source-digest, omission or
mandatory-content rule. The old date readers remain unchanged.

Reusing the older combined-path batch reader was rejected after a real Git
merge-resolution fixture returned August 3 where the per-path oracle correctly
returned August 4. That pre-existing batch-helper defect is not silently propagated
or repaired in unrelated consumers by this change.

The compiler source SHA256
21b1857ab7c30b9b41cf37903ceb74fd369d9ed5cf2450e870e92c92024a32a0
passed independent review and all 104 tests in tests/test_agentos_compile.py.
The tests cover real merge-resolution, rename/re-add and fresh-commit dates;
bounded concurrency; and complete bundle parity under two budgets.
Its actual M2 composition through Mastermind PR 1666
completed in 17.105 seconds, supplying 32,236 bytes of additional context from a
31,031-byte owner bundle. Goal, phase plan, next action, do-not-redo facts and the
handoff were present. The owner reported three degraded inputs and 44 omissions;
its 6,309-token estimate exceeded the requested 4,000 without hiding that fact.
This proves complete delivery by the source adapter to its JSON output, not
native hook firing or model consumption. Subsequent record wording is shortened
to leave more capacity under the unchanged 32-KiB bound.

The next complete read supplied 32,424 bytes in 22.346 seconds. Its three degraded
inputs are explicit: the sparse worktree lacks active_builds.json for PR joins;
the configured Mastermind P0 source is unavailable; and mandatory material plus
accounting tails exceed the requested token budget. The latter two are not
silently turned into current strategic or runtime facts. The small remaining byte
margin requires an explicitly smaller packing budget for the native canary, with
another complete-owner-read check; the adapter's hard limit stays unchanged.

The P0 gap was traced to existing sibling autodiscovery selecting the non-Git
/Volumes/Mastermind mount. The existing process-local MACRO_MASTERMIND_REPO
override selects the intended reviewed Git checkout. Its source file/HEAD must
be recorded separately: the Macro record digest does not bind that live join.
This changes no API or persistent setting.

With that explicit binding, the actual budget-3200 adapter read timed out at
25.023 seconds. A later stage diagnostic completed in 16.719 seconds, returning
28,192 bytes; 15.204 seconds were the 48 exact date reads. Its 5,596-token estimate
still reports full accounting above the request. P0 was present; remaining
degradation was the sparse active-builds artifact and reported budget overrun.
The diagnostic used a 55-second bound and is not a replacement acceptance for
the failed 25-second adapter invocation.

A single temporary eight-reader comparison did not justify a change: the
incumbent runner raised `owned process group did not settle` after 27.22 seconds,
before returning captured streams. The original child PID/PGID was unavailable.
A subsequent read-only check found no matching diagnostic Python process, but
does not prove the former group empty. No process was killed or extra compiler
call made. Keep the reviewed four-reader implementation and preserve this
specific lifecycle uncertainty for the process owner. Do not increase limits,
hide accounting, introduce a cache, or repeat a read to label the failure green.

### W2: durable planning and checkpoint

The workstream carries the project objective, phase dependencies and next action.
A cumulative handoff carries verified source heads, tests, current gaps,
outstanding effects and do-not-redo facts. This plan carries the architecture
and acceptance sequence. These are existing Agent OS record types.
Macro PR 9967 publishes these records and the compiler improvement. The numeric
handoff PR field contains that Macro identity; cross-repository source carriers
remain explicit Mastermind links instead of incorrect numeric joins.

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

### W3: reconcile existing continuation source carriers

The protected pin lacks the production draft builder, but existing open source
carriers were subsequently located: Mastermind PR 656 at
9a461ee416437f5b8591154f00b608e9b0ce0a32 contains the builder and tests;
PR 1289 at 9b7318baeb63399bd264bfb4fad2bd1617fff61c contains fenced PREPARE/ACK
integration. PR 656 has requested changes for accepting empty or malformed Git
head identity. PR 1289 is draft and explicitly held from production. Its source
test result is not permission to activate it. Reconcile these carriers and their
ownership before repairing or integrating; do not create another implementation.
Native SessionStart qualification is not a prerequisite for this source review
and repair. End-to-end continuation acceptance still needs authentic current
owner records, model delivery, original-parent custody and effect reconciliation.

The reviewed Git identity repair is published as PR 1673 at
c23cfddd18e67e1769e386e32746b1f47603815a, targeting PR 656's existing branch.
It retains contract normalization and provider/credential refusals before
checking repository shape and the existing full Git object-ID grammar. All 239
source/contract cases passed after eight new invalid cases first reproduced the
defect. Publication alone does not resolve PR 656's formal review or release
PR 1289. A separately acquired integration workspace composes its exact head
with both scoped builder commits using author-preserving cherry-picks. No
incumbent branch or workspace was changed.

The composed verification passes 385 cases with zero failures, errors or skips:
219 capsule cases, 20 repaired source-builder cases, three source integration
contracts, 37 PREPARE/Event owner cases, 104 RuntimeBinding projections and two
new public lifecycle cases. The three previously skipped source-contract cases
now execute. No further production Runtime or port change was needed.

The new positive case uses actual public Runtime APIs in a private test Runtime
to admit an Attempt, write a generation-bound checkpoint, record a synthetic
predecessor stop/release observation, restore and invalidate the old binding,
derive retry safety, commit the atomic COO retry decision, admit a successor,
build a draft without Event writes, and PREPARE one capsule with exact replay.
The negative case refuses preparation without positive predecessor release.
There is no SQL insertion of predecessor history or authority; SQL only reads
Events. The test explicitly verifies no continuation ACK Event.

This qualifies the specifically exercised read-only LOST/TX9_DETACHED source
journey. Principal, session, process and release observations remain synthetic.
It does not establish rate-limit rollover, native cross-provider continuation,
delivery, model consumption, successor action or parent acceptance. The isolated
composition remains reviewable source work, not release of PR 1289's HOLD.

The reviewed integration is published as Mastermind PR 1676 at
012449874afbd2a6dc92563f6b7f0f03a8d7cfc4, targeting PR 1289's existing branch.
That commit records the tested lifecycle file unchanged. Its cherry-picks are
dependency snapshots for review: before merging the contribution, reconcile
them with accepted PR 656/1673 source heads. Keep further builder corrections
on that original carrier.

The successor is already synthetically RUNNING before PREPARE in both cases;
this proves the release gate on preparation, not on launch. The fixed GitHub,
Agent OS, authority and RUNTIME_SOURCE_PIN references are supplied fixtures,
not fresh external acquisition or an attestation to the composed checkout.

### Reviewable attended installation candidate

The proposed canary uses the existing context-review workspace and focused
Macro owner below. These exact paths exist in the acquired source estate; this
is a definition for review, not an installed setting. Reconcile their source
heads through the existing installation owner after source acceptance, and
resolve the read-latency/process-settlement gap before executing the canary.

```json
{
  "matcher": "^(startup|resume|clear|compact|fork)$",
  "hooks": [{
    "type": "command",
    "command": "env MACRO_MASTERMIND_REPO='/Volumes/Mastermind 2/agent-workspaces/web/astra-project-context-20261021-001' python3 -B '/Volumes/Mastermind 2/agent-workspaces/web/astra-project-context-20261021-001/integrations/session_bridge/agentos_session_start.py' --workspace-root '/Volumes/Mastermind 2/agent-workspaces/web/astra-project-context-20261021-001' --workstream WS:ORCHESTRATOR-PROJECT-CONTINUITY --macro-root '/Volumes/Mastermind 2/agent-workspaces/macro/web/astra-long-horizon-agentos-20261021-001' --budget 3200",
    "timeout": 35,
    "async": false,
    "additionalContextLimit": 0
  }]
}
```

The native installation owner must merge this reviewed SessionStart entry with
existing definitions and pin the reviewed source/dependency closure. Actual
native Codex review/trust is still required; no trusted_hash is supplied or
written. Budget 3,200 is an explicit candidate, not a claim that the failed
configured-owner read passed. The return-hook definition remains held pending
review of the exact seven private source lines denied by automatic review.

## Remaining implementation and acceptance order

1. Qualify the published source candidates through required hosted checks and review.
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
- [Attended project-context source PR](https://github.com/mastermindx-market-intelligence/Mastermind/pull/1666)
- [Macro compiler and durable project records](https://github.com/mastermindx-market-intelligence/macro/pull/9967)
- [Existing continuation-builder repair](https://github.com/mastermindx-market-intelligence/Mastermind/pull/1673)
- [Public Runtime integration proof](https://github.com/mastermindx-market-intelligence/Mastermind/pull/1676)
