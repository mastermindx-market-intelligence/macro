"""One fixed trusted workload through the existing transport lifecycle.

No CLI, subprocess launcher or admission issuer lives here. An absent executor
is dormant. The commissioning caller still owes the installed-runtime check,
trusted host/resource mapping, helper census, outer supervision and an actual
grant before injecting an executor. Guest reports and successful cleanup do not
establish containment. This successor is excluded from the frozen v4 capsule.
"""
import hashlib
import json
import time

from engine.research_codegen import transport
import fixed_workload_plans as plans
import qualification_smoke as smoke
import qualification_runsc_smoke as runsc

WHOLE_SECONDS = 120.0
WORK_SECONDS = 90.0
TOTAL_BYTES = 65536
CLEANUP_BYTES = 4096
MAX_RECEIPT_BYTES = 131072


class FixedWorkloadEngine(smoke.FixedQualificationEngine):
    """Closed seven-source frontend; reuse exact-CID policy and settlement."""

    policy_format = runsc._RUNSC_POLICY_FORMAT
    runtime_requirement = runsc.RUNTIME_NAME

    def __init__(self, case_id, source_bytes, *, executor=None, binding=None):
        plan = plans.build_workload_plan(case_id, source_bytes)
        self._description = plans.describe_workload(case_id, source_bytes)
        self.operation_id = self.container_name = plan.operation_id
        self.run_label = smoke.RUN_LABEL_KEY + "=" + plan.operation_id
        super().__init__(transport, plan, executor=executor, binding=binding)
        self._attempt_claimed = False

    def effective_create_argv(self):
        base = transport.build_create_argv(self._plan)
        sep = base.index("--")
        head = list(base[1:sep])
        tmpfs = head.index("--tmpfs") + 1
        expected = "/tmp:rw,noexec,nosuid,size=%d" % self._plan.tmpfs_bytes
        if head[tmpfs] != expected:
            raise smoke.SourceContractError("fixed workload tmpfs contract changed")
        head[tmpfs] += ",mode=1777"
        head.insert(1, runsc.RUNTIME_FLAG)
        return (self._prefix() + tuple(head)
                + ("--name", self.container_name, "--label", smoke.ROOT_LABEL,
                   "--label", self.run_label) + base[sep:])

    def _policy_expectations(self):
        return {"require_runtime": runsc.RUNTIME_NAME,
                "expect_name": "/" + self.container_name,
                "expect_run_label": self.operation_id}

    def describe(self):
        # No source text, arbitrary paths or credentials are projected here.
        return dict(self._description,
                    effective_create_argv_sha256=smoke.argv_sha256(
                        self.effective_create_argv()),
                    aggregate_capture_bytes=TOTAL_BYTES,
                    cleanup_reserved_bytes=CLEANUP_BYTES,
                    workload_capture_is_remaining_aggregate=True,
                    physical_executor_injected=self._executor is not None)

    def _budget(self, kind, phase, requested):
        now = time.monotonic()
        if self._t0 is None:
            self._t0 = now
        remaining = WHOLE_SECONDS - (now - self._t0)
        if phase != "cleanup":
            remaining = min(remaining, WORK_SECONDS - (now - self._t0))
        ceiling = 5.0 if kind == "start" else smoke._CMD_MAX[kind]
        effective = min(ceiling, remaining, requested)
        if effective <= 0:
            raise transport.TransportStateError("fixed workload budget exhausted")
        return effective

    def _cap(self, kind, phase, requested):
        ceiling = TOTAL_BYTES if phase == "cleanup" else TOTAL_BYTES - CLEANUP_BYTES
        available = ceiling - self._bytes_used
        per_command = smoke._CLEANUP_CMD_CAP_BYTES if phase == "cleanup" else ceiling
        effective = min(available, per_command, requested)
        if effective <= 0:
            raise transport.TransportStateError("fixed workload output exhausted")
        return effective


def execute_prepared_workload(engine, receipt_path):
    """Run one caller-commissioned attempt, preserving every failed outcome.

    No retry/resume/campaign loop is supplied. A caller may advance to another
    precommitted case only after adjudicating this attempt and its host cleanup.
    The receipt uses the incumbent exclusive-create / identity-bound append
    writer. An interrupted or refused effect stays with its original identity.
    """
    if type(engine) is not FixedWorkloadEngine:
        raise smoke.SourceContractError("exact fixed workload engine required")
    if engine._executor is None:
        raise transport.TransportDormantError("no physical executor injected")
    if engine.frozen:
        raise transport.TransportPermissionRefusal("fixed workload effect frozen")
    if engine._attempt_claimed or engine._create_issued or engine.settled_cid is not None:
        raise transport.TransportStateError("fixed workload already attempted")
    engine._attempt_claimed = True
    engine._t0 = time.monotonic()
    plan = engine._plan

    def document(phase, **fields):
        return dict(schema="rf.fixed_workload.receipt.v1", phase=phase,
                    operation=engine.operation_id, root=smoke.ROOT_ID,
                    source_sha256=hashlib.sha256(plan.argv[-1].encode("ascii")).hexdigest(),
                    plan_sha256=transport.plan_identity(plan),
                    candidate_admission=False, containment_qualified=False,
                    **fields)

    def write(doc, *, excl=False, expected_identity=None):
        body = json.dumps(doc, sort_keys=True, separators=(",", ":")).encode("ascii")
        if len(body) + 1 > MAX_RECEIPT_BYTES:
            raise smoke.SourceContractError("fixed workload receipt bound")
        return smoke._write_receipt(receipt_path, doc, excl,
                                    expected_identity=expected_identity)

    identity = write(document("pre_create", whole_attempt_seconds=WHOLE_SECONDS,
                              aggregate_capture_bytes=TOTAL_BYTES,
                              cleanup_reserved_bytes=CLEANUP_BYTES), excl=True)

    def sink(cid):
        write(document("container_id_settled", container_id=cid),
              expected_identity=identity)

    engine.set_cid_sink(sink)
    try:
        attempt = transport.TransportOrchestrator(engine).execute(
            transport.TransportSession(plan))
    except BaseException as exc:
        if not engine.frozen:
            try:
                write(document("attempt_interrupted", exception_type=type(exc).__name__,
                               container_id=engine.settled_cid,
                               cid_persist_problem=engine.cid_persist_problem,
                               self_cleanup_confirmed=engine.self_cleanup_confirmed,
                               engine_ledger=engine.evidence_ledger()),
                      expected_identity=identity)
            except Exception:
                pass  # Preserve original interruption and durable partial receipt.
        raise
    if engine.frozen:
        raise transport.TransportPermissionRefusal("settlement publication frozen")
    write(document("attempt_settled", container_id=attempt.container_id,
                   state=attempt.state.value, workload_confirmed=attempt.workload_confirmed,
                   workload_returncode=attempt.workload_returncode,
                   workload_output_sha256=hashlib.sha256(attempt.workload_output).hexdigest(),
                   workload_output_bytes=len(attempt.workload_output),
                   workload_problem=attempt.workload_problem,
                   execution_uncertain=attempt.execution_uncertain,
                   cleanup_confirmed=attempt.cleanup_confirmed,
                   reconciliation_required=attempt.reconciliation_required,
                   cid_persist_problem=engine.cid_persist_problem,
                   engine_ledger=engine.evidence_ledger()), expected_identity=identity)
    return attempt
