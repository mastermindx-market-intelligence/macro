---
key: PF1-CLAUDE-WORK-LEG-BOUNDARY
claim: >
  PF1's `claude-code` worker can be driven through the canonical Executive supervisor only via a
  profile-less Job, and even on that path it can never reach a COMPLETED Job, because the fake-only
  PF1-F0 falsifier emits a fixed two-key sealed-evidence result that the supervisor's twelve-key
  closed per-Job schema must reject.
falsifier: >
  In Mastermind at 0df5e985 (branch claude/ssd-pf1-native-claude-worker-adapter), any of these reads
  disproves it: `sed -n '70p' control_plane/executive_agent_capabilities.py` no longer showing
  `_EXECUTION_SURFACES = frozenset({"codex-exec", "codex-app-server"})`;
  `sed -n '980,982p' control_plane/executive_supervisor.py` no longer returning early when
  `execution_profile_id` is absent; `sed -n '557,558p' control_plane/claude_cli_protocol.py` no longer
  fixing `_derived_result` to `{"decision": "HOLD", "evidence_sha256": ...}`;
  `sed -n '763p' control_plane/claude_worker.py` no longer assigning that derived value
  unconditionally as `structured_output`; or `sed -n '373,390p' control_plane/executive_supervisor.py`
  no longer declaring `additionalProperties: False` with the twelve required keys.
so_what: >
  Two consequences a future PF1 session would otherwise pay for twice. First, the remaining native gap
  is ONE blocker, not two: a Job-conformant result can only come from a real model turn, so the
  result-content leg and the adjudicated dedicated-principal decision are the same wall, and no amount
  of adapter or test work moves it. Second, a commission to "write the claude-code round trip" is
  unbuildable as a success path and must instead assert the refusal as the designed outcome. Also
  closes the wrong template: tests/test_w6b_native_round_trip.py proves the PLAN leg through the
  operator/app-server path and its own embedded FINDING records that the WORK leg cannot complete
  hermetically for any provider, so the live-supervisor template is
  tests/test_executive_supervisor.py::test_run_once_persists_process_checkpoint_result_receipt_and_reopens.
  Third, the seam is narrower than profile-less alone: the supervisor's complete-launch-attestation
  gate is Codex-bound and fires on `effective_grant is not None` independently of its flag, so a
  Claude worker is refused for any Job carrying an effective grant. The seam is profile-less AND
  grant-less. Closing that from the PF1 side would mean claiming the Codex contract's schema
  version, which is a provider-boundary violation; promoting `LaunchAttestation` to an HF1 common
  type is HF1's decision, not PF1's.
kind: architecture
verified_at: 2026-09-17
verified_by: >
  control_plane/executive_agent_capabilities.py:70 and :288; control_plane/executive_supervisor.py:373-390,
  :980-982, :1016 and :570-571; control_plane/executive_service.py:1998; control_plane/model_router.py:703;
  control_plane/claude_cli_protocol.py:557-558 and :742; control_plane/claude_worker.py:169-172 and :763;
  tests/test_executive_supervisor.py:354, :398, :430 and :627;
  tests/test_w6b_native_round_trip.py embedded FINDING at lines 845-853;
  control_plane/executive_supervisor.py:85-92, :1051, :1061 and :1072-1075;
  control_plane/codex_worker.py:255 and :2966; `grep -c "def launch_attestation"` returning 1 for
  control_plane/codex_worker.py and 0 for control_plane/claude_worker.py;
  tests/test_worker_execution_contract.py:702-712.
scope:
  - mastermindx-market-intelligence/Mastermind
  - control_plane/**
  - WS:EXECUTIVE-CAPACITY-FABRIC
confidence: verified
---

# The PF1 Claude work-leg boundary

The Executive **work** leg — the only leg a `WorkerExecutionAdapter` serves — is bound to Codex at four
independent sites, and the surface list is a closed enumeration rather than a config value:

- `executive_agent_capabilities.py:70` declares `_EXECUTION_SURFACES = frozenset({"codex-exec", "codex-app-server"})`,
  consumed by `_closed_choice` (line 288), which raises `CapabilityPolicyError` at config-load time for
  any other value. A Claude capability profile cannot be declared in
  `config/executive_agent_capabilities.json` at all.
- `executive_supervisor.py:1016` refuses unless `profile.execution_surface == "codex-exec"`, together
  with `auth_realm == "dedicated-worker-account"` — itself a one-element closed set, and the adjudicated
  principal blocker.
- `executive_service.py:1998` and `model_router.py:703` enforce the same constraint independently; the
  router's error text reads "requires an implemented Codex execution surface".

One lawful seam exists. `executive_supervisor.py:980-982` returns early when the Job carries no
`execution_profile_id`, documented in the method's own docstring as "Legacy Jobs without a profile keep
their historical path". A profile-less Job therefore reaches `_run_claimed` → `_launch_spec` →
`adapter.start()` with no surface check, which is how a non-Codex adapter can be integration-tested
against the real supervisor today. `tests/test_executive_supervisor.py::_runtime_and_job` builds exactly
such a Job.

The seam does not reach a COMPLETED Job. `claude_worker.py:763` assigns
`structured_output = json.loads(_protocol._derived_result(state.evidence_sha256))` unconditionally — the
adapter never parses the model's own output as the result — and `claude_cli_protocol.py:557-558` fixes
that value at `{"decision": "HOLD", "evidence_sha256": "<64 hex>"}`. That shape is load-bearing to
PF1-F0's own proof: line 742 raises `RESULT_BINDING_INVALID` when the expected result is not canonically
derived from the sealed evidence file. The supervisor's per-Job schema requires twelve keys under
`additionalProperties: False`, with `job_id`/`run_id`/`worker_id` const-bound to live identities, so
`_validate_structured_output` (`claude_worker.py:169-172`, which checks `required` before
`additionalProperties`) raises a missing-required-keys `ResultValidationError`, which
`_build_success_receipt` converts to `WorkerRunStatus.INVALID_RESULT`.

This is not a defect in either component. It is the fake-only effect ceiling doing its job: a
Job-conformant result would have to come from a real model turn, and the real turn is what the
dedicated-principal decision blocks.

## Third constraint: the complete-launch-attestation gate is Codex-bound

Measured after the integration proof landed, and it narrows the seam above.

`executive_supervisor.py:1051` duck-types `getattr(self.adapter, "launch_attestation", None)`. When the
adapter has no such method the supervisor substitutes a `legacy-partial` attestation (line 1061). Lines
1072-1075 then refuse the launch unless the attestation's `schema_version` equals
`_codex_worker_contract()[1]` — and `_codex_worker_contract` (lines 85-92) is a lazy import of
`LAUNCH_ATTESTATION_SCHEMA_VERSION` from `control_plane.codex_worker`. So "a complete launch attestation"
is *defined as* the Codex contract's schema version.

`LaunchAttestation` is declared at `codex_worker.py:255` and does not appear in
`control_plane/worker_execution_contract.py`: HF1 never promoted it to a common type.
`ClaudeCodeWorkerAdapter` has no `launch_attestation` method, where `CodexWorkerAdapter` has one
(`codex_worker.py:2966`, a one-line read of its own `_RunState`).

Two consequences. The gate's condition is
`self.require_complete_launch_attestation or effective_grant is not None`, so it fires for **any Job
carrying an effective grant** whether or not the flag is set — which means the lawful seam is
profile-less *and* grant-less, not profile-less alone. And the gap cannot be closed from the PF1 side:
supplying a "complete" attestation would require the Claude adapter to claim the Codex contract's schema
version, which is exactly the provider-boundary crossing HF1 exists to prevent. HF1's own law at
`tests/test_worker_execution_contract.py:702-712` only guards names it has already promoted
(`_MOVED_NAMES`), so the lazy import at lines 85-92 evades that law rather than satisfying it.

The remedy is HF1's: promote `LaunchAttestation` and a provider-neutral attestation schema version into
`worker_execution_contract.py`, then have each adapter attest under it. PF1 must not manufacture a pass
here.
