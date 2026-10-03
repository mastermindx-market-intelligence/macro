---
workstream: WS:EXECUTIVE-CAPACITY-FABRIC
session: claude/agentos-pf1-native-claude-worker-boundary-20260917
model: opus
ended_because: blocked
mission: >
  Carry the PF1 native Anthropic Claude worker vertical through the smallest remaining critical path
  toward one real native Claude Code worker executing one bounded Executive child Job through the
  canonical Job / Attempt / Worker / broker-supervisor / foreground process / structured result /
  validation / canonical consumer path, without building a substitute for any owning system and without
  relabelling the merged Claude-compatible subscription harness as native Anthropic. Chairman
  instruction of record for this stretch: release the ratified hold on PR #455 and act on that carrier
  only; then continue the vertical from the highest-leverage remaining unblocked step, treating the
  dedicated native-Claude-principal issue as BLOCKED and adjudicated, until the next genuine
  authority/architecture blocker, a coherent phase boundary, or proven acceptance.
state_before: >
  The workstream's newest handoff was EXECUTIVE-CAPACITY-FABRIC-2026-09-16, which preserved Sol rulings
  R21/R22 (the merged #581 compatible-provider harness is not native Anthropic) and named the exact next
  native dependency as PF1-F0 custody plus the missing native ClaudeCodeWorkerAdapter. At protected
  Mastermind master the native adapter was absent. Mastermind PR #455
  "[PF1-F0][HOLD] Provider-free Claude CLI protocol falsifier" was OPEN, DRAFT and unmerged at head
  0a368935ece318c1b7f3301337f75d3a58d61006 under a ratified Sol hold whose Slack carrier
  C0BSBM78V1N/1788496784.623109 recorded KEEP 455 DRAFT and RELEASE_BLOCKED. The vertical's plan of
  record for the next slice was to mirror tests/test_w6b_native_round_trip.py as a claude-code round
  trip. That premise was wrong, and correcting it is the substance of this record.
changed:
  - path: agentos/discoveries/DSC-PF1-CLAUDE-WORK-LEG-BOUNDARY.md
    what: >
      New discovery record. Establishes that the Executive work leg is bound to Codex at four
      independent sites with a closed surface enumeration, that a profile-less Job is the one lawful
      seam for a non-Codex WorkerExecutionAdapter, and that even on that seam the claude-code adapter
      can never reach a COMPLETED Job because the PF1-F0 fake-only falsifier's fixed two-key
      sealed-evidence result cannot satisfy the supervisor's twelve-key closed per-Job schema. Records
      that the remaining native gap is therefore ONE blocker rather than two, and that
      tests/test_w6b_native_round_trip.py is the wrong template for the work leg.
  - path: agentos/workstreams/WS-EXECUTIVE-CAPACITY-FABRIC.md
    what: >
      Durable-state edit to the PF1 wave next_action only; no completed wave rewritten and no status
      changed. Records that the native adapter now exists as unmerged branch work with its descriptor
      deliberately unarmed, and appends the two newly measured architecture constraints plus the
      citation to DSC:PF1-CLAUDE-WORK-LEG-BOUNDARY. Adds that discovery to the wave's discoveries and
      artifacts lists.
verified:
  - claim: >
      Mastermind PR #455 is OPEN, DRAFT and was never merged; its head is unchanged at
      0a368935ece318c1b7f3301337f75d3a58d61006, it carries no labels and no native auto-merge request.
    command: >
      gh pr view 455 --repo mastermindx-market-intelligence/Mastermind --json
      number,state,isDraft,mergedAt,mergeCommit,headRefOid,mergeStateStatus,labels,autoMergeRequest
    result: >
      state OPEN, draft true, mergedAt null, mergeCommit null, head
      0a368935ece318c1b7f3301337f75d3a58d61006, mergeStateStatus CLEAN, labels [], autoMergeRequest null.
  - claim: >
      The native Claude worker adapter exists as unmerged branch work with no pull request, and its
      registry descriptor is deliberately NOT armed.
    command: >
      git ls-remote origin refs/heads/claude/ssd-pf1-native-claude-worker-adapter; gh pr list --repo
      mastermindx-market-intelligence/Mastermind --state all --head
      claude/ssd-pf1-native-claude-worker-adapter --json number,state,title
    result: >
      Remote branch present at 0df5e985c85ca4d3e16dcee075086d101ed0e722; the pull-request query returns
      an empty list. The claude-code descriptor in control_plane/worker_adapter.py carries
      implementation="control_plane.claude_worker.ClaudeCodeWorkerAdapter" with implemented=False, which
      keeps it constructible and testable while leaving broker execution disarmed.
  - claim: >
      The Executive work leg refuses every non-Codex execution surface, and the surface list is a closed
      enumeration that rejects an unknown value at config-load time rather than at dispatch.
    command: >
      sed -n '70p;288,294p' control_plane/executive_agent_capabilities.py; sed -n '1016p'
      control_plane/executive_supervisor.py; sed -n '1998p' control_plane/executive_service.py; sed -n
      '703,709p' control_plane/model_router.py
    result: >
      _EXECUTION_SURFACES = frozenset({"codex-exec", "codex-app-server"}) consumed by _closed_choice,
      which raises CapabilityPolicyError for any other value; the supervisor refuses unless
      execution_surface == "codex-exec"; the service route applies the same check; the router rejects a
      worker-eligible alias whose surface is not one of the two Codex values.
  - claim: >
      A Job carrying no execution_profile_id skips that gate entirely, which is the one lawful seam by
      which a non-Codex adapter can be driven through the real supervisor.
    command: >
      sed -n '964,982p' control_plane/executive_supervisor.py; sed -n '354,398p'
      tests/test_executive_supervisor.py
    result: >
      _validate_execution_profile returns immediately when the profile id is absent, documented in its
      own docstring as the historical path for legacy Jobs; the incumbent test helper _runtime_and_job
      builds exactly such a Job and binds the adapter directly into ExecutiveSupervisor.
  - claim: >
      The claude-code adapter cannot produce a COMPLETED canonical Job today, because its structured
      output is a fixed two-key derived value that the supervisor's closed twelve-key per-Job schema
      must reject as missing required keys.
    command: >
      sed -n '763p' control_plane/claude_worker.py; sed -n '557,558p;742,746p'
      control_plane/claude_cli_protocol.py; sed -n '373,390p' control_plane/executive_supervisor.py;
      sed -n '169,176p' control_plane/claude_worker.py
    result: >
      _build_success_receipt assigns json.loads(_protocol._derived_result(state.evidence_sha256))
      unconditionally; _derived_result is fixed at {"decision": "HOLD", "evidence_sha256": ...} and is
      enforced by a RESULT_BINDING_INVALID check; the generated schema is additionalProperties False
      with twelve required keys; _validate_structured_output tests required before additionalProperties,
      so the refusal is a missing-required-keys ResultValidationError converted to INVALID_RESULT.
  - claim: >
      tests/test_w6b_native_round_trip.py cannot serve as the work-leg template, by its own recorded
      finding rather than by inference.
    command: sed -n '845,853p' tests/test_w6b_native_round_trip.py
    result: >
      The module's embedded FINDING states that work launch cannot complete hermetically, that the
      sealed supervisor refuses the operator/MCP profile and the operator supervisor refuses non-plan
      work, and that review, aggregation and next-child therefore do not run.
  - claim: >
      An independent adversarial review of PR #455's ordered repair refused every previously reported
      acceptance while proving the harness still reaches terminal acceptance, so no release-blocking
      defect survives on that carrier.
    command: >
      Independent reviewer commission against a pre-staged read-only copy of the #455 source; verdict
      posted to Slack C0BSBM78V1N/1789630204.800479 and to the pull request as comment 5710693561.
    result: >
      Versions 2.1.248 and 2.1.259 accepted with TERMINAL_RESULT_OBSERVED as controls; 2.1.260, 2.1.261,
      3.0.0, 2.2.0 and 999999.999999.999999 refused VERSION_UNSUPPORTED; three field/latency mixtures
      refused VERSION_PROFILE_FIELD_DRIFT; an echoed-version attack refused FAKE_CONTROL_INVALID; init
      version drift refused VERSION_DRIFT. Deadline handling CLOSED, model provenance CLOSED, failure
      provenance PARTIAL and left open to the carrier owner.
  - claim: >
      A profile-less, grant-less Job does drive the real ClaudeCodeWorkerAdapter through the live
      ExecutiveSupervisor: real launched subprocess, real pid and process_start_identity recorded,
      correct event ordering, 0600 evidence files, and the measured result-content refusal as the
      terminal outcome.
    command: >
      python3 -m pytest tests/test_executive_claude_lifecycle_integration.py -v (with ANTHROPIC_* and
      CLAUDE_* scrubbed), on branch claude/ssd-pf1-native-claude-worker-adapter at commit 5b461fb2
    result: >
      3 passed. Measured terminal states JobStatus.FAILED and AttemptStatus.FAILED; measured refusal
      reason "structured output missing required keys: ['schema_version', 'job_id', 'run_id',
      'worker_id', 'status', 'summary', 'completed_steps', 'current_state', 'artifacts',
      'next_actions', 'errors', 'validations']". Regression set green in the same scrubbed environment:
      test_executive_claude_worker 26 passed 1 skipped, test_executive_supervisor 19 passed,
      test_worker_adapter 1 passed, test_worker_execution_contract 13 passed. The claude-code
      descriptor remained implemented=False.
  - claim: >
      The supervisor's complete-launch-attestation gate is Codex-bound and fires on any Job carrying an
      effective grant independently of its flag, so the lawful seam is profile-less AND grant-less and
      cannot be widened from the PF1 side.
    command: >
      sed -n '85,92p;1051,1075p' control_plane/executive_supervisor.py; grep -c "def
      launch_attestation" control_plane/codex_worker.py control_plane/claude_worker.py; grep -n
      "LaunchAttestation" control_plane/worker_execution_contract.py; sed -n '702,712p'
      tests/test_worker_execution_contract.py
    result: >
      The gate requires the attestation schema_version to equal _codex_worker_contract()[1], which is
      LAUNCH_ATTESTATION_SCHEMA_VERSION lazily imported from control_plane.codex_worker; the condition
      is "require_complete_launch_attestation or effective_grant is not None". codex_worker.py has one
      launch_attestation method and claude_worker.py has zero; LaunchAttestation is absent from
      worker_execution_contract.py, so HF1 never promoted it; and HF1's no-codex-import law guards only
      already-promoted _MOVED_NAMES, so the lazy import evades that law rather than satisfying it.
unverified:
  - claim: >
      That the ClaudeCodeWorkerAdapter can satisfy a supervisor configured with
      require_complete_launch_attestation=True, or serve any Job carrying an effective grant.
    what_would_verify: >
      It cannot today, and the fix is not PF1's to make. HF1 promoting LaunchAttestation and a
      provider-neutral attestation schema version into control_plane/worker_execution_contract.py would
      verify it; the integration test therefore leaves the flag at its default False and documents why
      in its own supervisor-construction docstring.
  - claim: >
      That the failure-provenance PARTIAL finding on PR #455 is correct design rather than an omission.
    what_would_verify: >
      A ruling by the carrier's holding authority. The orchestrator's reading is that an
      OUTCOME_UNRECONCILED terminal has no validated terminal frame to bind, so evidence=None is
      correct, but that reasoning disposes another party's finding and was deliberately left open.
unresolved:
  - >
    PR #455 remains under its ratified Sol hold. The release decision belongs to the holding authority;
    the evidence package is complete and posted on both the Slack carrier and the pull request.
  - >
    The dedicated native-Claude worker principal remains BLOCKED and adjudicated. No _mastermind_claude_*
    principal exists, ops/executive_os/provider_worker_slots.py restricts slot ids by the regex
    ^codex(?:-pro)?-[0-9]{2}$ which structurally excludes a Claude slot, and wave OCR-2C records
    FAMILY_A_NO_SAFE_EQUALITY_WITNESS and FAMILY_A_NO_ROTATION_INVALIDATION.
  - >
    Because a Job-conformant result can only come from a real model turn, the result-content leg and the
    dedicated-principal decision are the same wall. No adapter or test work moves it.
  - >
    The lawful seam is narrower than profile-less alone. The supervisor's complete-launch-attestation
    gate is keyed to the Codex contract's schema version and fires whenever a Job carries an effective
    grant, so the seam is profile-less AND grant-less. Widening it requires HF1 to promote
    LaunchAttestation to a provider-neutral common type; PF1 must not close it by claiming the Codex
    schema version.
next_actions:
  - >
    Await the holding authority's release decision on Mastermind PR #455. Do not arm it, mark it ready,
    merge it, rebase it, or open a replacement carrier.
  - >
    Land tests/test_executive_claude_lifecycle_integration.py on
    claude/ssd-pf1-native-claude-worker-adapter once its commissioned build returns, keeping the
    claude-code descriptor at implemented=False. That branch cannot open a pull request ahead of #455.
  - >
    Put one bounded question to the principal/auth authority: whether PF1 may declare a Claude execution
    surface, which requires widening _EXECUTION_SURFACES in
    control_plane/executive_agent_capabilities.py and the matching checks in executive_supervisor.py,
    executive_service.py and model_router.py. That is an architecture decision across four owners and is
    not a configuration edit.
  - >
    Put one bounded question to HF1's owner: whether LaunchAttestation and its schema version should be
    promoted from control_plane/codex_worker.py into control_plane/worker_execution_contract.py with a
    provider-neutral version, so a non-Codex adapter can attest completely and serve Jobs carrying an
    effective grant. Until then no non-Codex worker can serve such a Job.
  - >
    Only after a dedicated native principal exists and a real turn is authorized, add the real-output
    path to the adapter's collect step so a Job-conformant result can be produced, then arm the
    descriptor against a documented real-turn receipt path as tests/test_worker_adapter.py requires.
do_not_redo:
  - >
    Do not mirror tests/test_w6b_native_round_trip.py for a claude-code round trip. Its own embedded
    FINDING records that the work leg cannot complete hermetically for any provider; it proves the plan
    leg through the operator/app-server path. The live-supervisor template is
    tests/test_executive_supervisor.py::test_run_once_persists_process_checkpoint_result_receipt_and_reopens.
  - >
    Do not commission a claude-code round trip whose acceptance is a COMPLETED Job. It is unbuildable
    today for the reason recorded in DSC:PF1-CLAUDE-WORK-LEG-BOUNDARY.
  - >
    Do not set implemented=True on the claude-code descriptor. It arms broker execution, and
    tests/test_worker_adapter.py pins the implemented set to names whose authorizing receipt path is
    documented in that test's own docstring. The proof available today is fake-only, so the pin is
    correct to refuse.
  - >
    Do not widen _EXECUTION_SURFACES, relax the supervisor's execution-surface check, or add a Claude
    capability profile to config/executive_agent_capabilities.json in order to make a test pass.
  - >
    Do not add a launch_attestation method to control_plane/claude_worker.py that claims the Codex
    contract's LAUNCH_ATTESTATION_SCHEMA_VERSION, and do not import LaunchAttestation from
    control_plane.codex_worker. That manufactures a pass at a real provider boundary. The remedy is an
    HF1 promotion of the type and a provider-neutral schema version.
  - >
    Do not re-run or repair the PR #455 protocol repair. It was already implemented at head
    0a368935ece318c1b7f3301337f75d3a58d61006, which post-dates both the disposition and all three
    advisory comments, and an independent adversarial review confirmed it.
  - >
    Do not treat the merged #581 Claude-compatible subscription harness as native Anthropic proof, and
    do not route native Claude subscription login through its ANTHROPIC_AUTH_TOKEN and external
    base-URL credential model.
  - >
    Do not open a second PF1 carrier. One duplicate carrier was opened in error during this lineage and
    closed unmerged; the authoritative query for an existing carrier is
    `gh pr list --state all --head <branch>`, never a truncated `gh pr list --limit N`.
danger_areas:
  - >
    The Claude worker suites fail closed on ambient provider environment variables, so they false-red
    from inside a Claude Code session, where roughly 29 ANTHROPIC_* and CLAUDE_* variables are present.
    A contaminated preflight measured 11 failures; the same preflight with those variables scrubbed
    measured 80 passed at exit 0. Scrub before every run and verify the scrub rather than trusting the
    incantation.
  - >
    scripts/ohf/fake_claude_cli.py requires the isolated HOME, the isolated TMPDIR and the fake state
    file to be siblings under one state parent and otherwise rejects with a bare
    "fake claude: environment rejected" on stderr, which surfaces only as STDERR_NOT_EMPTY. Do not
    restructure the adapter's per-run isolation root.
  - >
    The D8 identity ratchet fails any pull request that adds an integer literal in 400..999 on a changed
    line, including token counts and loop bounds. The scanner is owned by Mastermind PR #721; never
    patch it from another carrier.
  - >
    The Slack carrier, not the pull-request body, is authoritative for hold state on this lineage.
    Reconciling GitHub state alone once put #455 into the merge queue against an intact RELEASE_BLOCKED
    instruction; `gh pr merge --disable-auto` did not dequeue it and `gh pr ready 455 --undo` was what
    ejected it and restored DRAFT. Re-read the carrier from the last counterpart edge before any push,
    label, ready or merge act.
prs: [455]
discoveries:
  - DSC:PF1-CLAUDE-WORK-LEG-BOUNDARY
  - DSC:CLAUDE-SUBSCRIPTION-HARNESS-IS-NOT-NATIVE-ANTHROPIC
---

# Where the vertical actually stands

Nothing merged and nothing armed. The native Claude worker adapter is built, independently reviewed and
green in isolation, sitting on an unmerged branch whose registry descriptor is deliberately unarmed so
the broker cannot execute it. The carrier it depends on, PR #455, is DRAFT and unmerged under a ratified
hold, with its ordered repair already implemented and independently confirmed; the release decision is
its holding authority's, not this session's.

The substantive result of this stretch is a correction, not a build. The plan of record was to mirror the
W6-B native round trip for a claude-code Job. Reading the code rather than the plan showed that W6-B
proves the plan leg and records in its own source that the work leg cannot complete hermetically for any
provider, and that the work leg is bound to Codex by a closed surface enumeration with exactly one lawful
seam — a profile-less Job. Following that seam to its end showed the decisive fact: the fake-only PF1-F0
falsifier emits a two-key sealed-evidence result by design, and the supervisor's per-Job schema is closed
with twelve required keys, so the adapter can never reach a COMPLETED Job while the effect ceiling holds.

That collapses the remaining gap. What looked like two independent blockers — the missing dedicated
principal, and an unwritten round-trip proof — is one wall: a Job-conformant result requires a real model
turn, and the real turn is exactly what the adjudicated principal decision withholds. A future session
should therefore spend its effort on the authority question, not on adapter or test work, and should read
DSC:PF1-CLAUDE-WORK-LEG-BOUNDARY before proposing either.
