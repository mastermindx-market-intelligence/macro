"""One fixed trusted workload through the existing transport lifecycle.

No CLI, subprocess launcher or admission issuer lives here. An absent executor
is dormant. The commissioning caller still owes the installed-runtime check,
trusted host/resource mapping, helper census, outer supervision and an actual
grant before injecting an executor. Guest reports and successful cleanup do not
establish containment. This successor is excluded from the frozen v4 capsule.
"""
import hashlib
import json
import os
import time
from types import MappingProxyType

import fixed_workload_plans as plans
import qualification_smoke as smoke
import qualification_runsc_smoke as runsc

WHOLE_SECONDS = 120.0
WORK_SECONDS = 90.0
TOTAL_BYTES = 65536
CLEANUP_BYTES = 4096
MAX_RECEIPT_BYTES = 131072
# Four commands in the longest cleanup path fit inside the 30-second reserve,
# leaving two seconds for ordinary bookkeeping. The caller still owes outer
# supervision: these ceilings cannot interrupt blocked I/O or a bad executor.
CLEANUP_COMMAND_SECONDS = MappingProxyType({
    "stop": 7.0, "kill": 7.0, "rm": 7.0, "absence": 7.0,
})


def _checked_binding(binding):
    """Validate and freeze caller data; this does not authenticate a host."""
    if type(binding) is not dict or set(binding) != smoke._BINDING_KEYS:
        raise smoke.BindingMismatch("fixed workload binding schema mismatch")
    fixed = {"binding_schema": smoke.BINDING_SCHEMA, "expected_uid": smoke.UID,
             "expected_gid": smoke.GID, "docker_endpoint": smoke.DOCKER_ENDPOINT,
             "docker_server_version": smoke.EXPECTED_SERVER_VERSION,
             "daemon_arch": smoke.DAEMON_ARCH, "ostype": smoke.DAEMON_OSTYPE}
    for key, expected in fixed.items():
        if type(binding[key]) is not type(expected) or binding[key] != expected:
            raise smoke.BindingMismatch("fixed workload binding constant mismatch")
    for key in ("expected_hostname", "expected_kernel", "expected_host_os"):
        value = binding[key]
        if (type(value) is not str or not 0 < len(value) <= 128
                or any(not 0x20 <= ord(char) <= 0x7e for char in value)):
            raise smoke.BindingMismatch("fixed workload binding host fact mismatch")
    directory = binding["client_config_dir"]
    if (type(directory) is not str or not os.path.isabs(directory)
            or len(directory) > 1024 or "\x00" in directory
            or type(binding["client_config_sha256"]) is not str
            or binding["client_config_sha256"] != smoke.ANONYMOUS_CLIENT_CONFIG_SHA256):
        raise smoke.BindingMismatch("fixed workload anonymous config mismatch")
    for key in ("image_receipt_sha256", "image_adjudication_sha256"):
        if type(binding[key]) is not str or smoke._HEX64_RE.fullmatch(binding[key]) is None:
            raise smoke.BindingMismatch("fixed workload image binding digest mismatch")
    return dict(binding)


class FixedWorkloadEngine(smoke.FixedQualificationEngine):
    """Closed seven-source frontend; reuse exact-CID policy and settlement."""

    policy_format = runsc._RUNSC_POLICY_FORMAT
    runtime_requirement = runsc.RUNTIME_NAME

    def __init__(self, case_id, source_bytes, *, transport_path,
                 executor=None, binding=None):
        # Use the incumbent loader: hash the bytes, then compile those same
        # bytes. An importable lookalike or a later file edit cannot select the
        # executed lifecycle. No second transport implementation is introduced.
        if plans.REQUIRED_TRANSPORT_SHA256 != smoke.TRANSPORT_SHA256:
            raise smoke.SourceContractError("fixed workload transport pin mismatch")
        t = smoke.load_transport_module(transport_path)
        plan = t.TransportPlan(**plans._fixed_fields(case_id, source_bytes))
        self._description = plans._describe_plan(case_id, plan, t)
        self._description["transport_sha256"] = smoke.TRANSPORT_SHA256
        if binding is not None:
            binding = _checked_binding(binding)
        elif executor is not None:
            raise smoke.BindingMismatch("fixed workload requires a host binding")
        super().__init__(t, plan, executor=executor, binding=binding)
        self._attempt_claimed = False
        self._receipt_ready = False

    @property
    def operation_id(self):
        return self._plan.operation_id

    @property
    def _binding(self):
        # The incumbent preflight requires an exact dict. Supply a snapshot,
        # preserving that contract without exposing mutable stored host facts.
        return None if self._binding_data is None else dict(self._binding_data)

    @_binding.setter
    def _binding(self, value):
        if hasattr(self, "_binding_data"):
            raise AttributeError("fixed workload binding is immutable")
        self._binding_data = None if value is None else MappingProxyType(dict(value))

    @property
    def container_name(self):
        return self._plan.operation_id

    @property
    def run_label(self):
        return smoke.RUN_LABEL_KEY + "=" + self._plan.operation_id

    def run(self, argv, *, deadline_seconds, output_cap_bytes):
        kind, _ = self._classify(argv)
        if kind == "create" and not (self._attempt_claimed and self._receipt_ready
                                     and self._cid_sink is not None):
            raise self._t.TransportStateError("fixed workload receipt required before create")
        return super().run(argv, deadline_seconds=deadline_seconds,
                           output_cap_bytes=output_cap_bytes)

    def effective_create_argv(self):
        base = self._t.build_create_argv(self._plan)
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
                    cleanup_command_max_seconds=dict(CLEANUP_COMMAND_SECONDS),
                    workload_capture_is_remaining_aggregate=True,
                    physical_executor_injected=self._executor is not None)

    def _budget(self, kind, phase, requested):
        now = time.monotonic()
        if self._t0 is None:
            self._t0 = now
        remaining = WHOLE_SECONDS - (now - self._t0)
        if phase != "cleanup":
            remaining = min(remaining, WORK_SECONDS - (now - self._t0))
        ceiling = (CLEANUP_COMMAND_SECONDS[kind] if phase == "cleanup"
                   else 5.0 if kind == "start" else smoke._CMD_MAX[kind])
        effective = min(ceiling, remaining, requested)
        if effective <= 0:
            raise self._t.TransportStateError("fixed workload budget exhausted")
        return effective

    def _cap(self, kind, phase, requested):
        ceiling = TOTAL_BYTES if phase == "cleanup" else TOTAL_BYTES - CLEANUP_BYTES
        available = ceiling - self._bytes_used
        per_command = smoke._CLEANUP_CMD_CAP_BYTES if phase == "cleanup" else ceiling
        effective = min(available, per_command, requested)
        if effective <= 0:
            raise self._t.TransportStateError("fixed workload output exhausted")
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
    transport = engine._t
    if engine._executor is None:
        raise transport.TransportDormantError("no physical executor injected")
    if engine.frozen:
        raise transport.TransportPermissionRefusal("fixed workload effect frozen")
    if engine._attempt_claimed or engine._create_issued or engine.settled_cid is not None:
        raise transport.TransportStateError("fixed workload already attempted")
    if engine._binding is None:
        raise smoke.BindingMismatch("fixed workload requires a host binding")
    engine._attempt_claimed = True
    engine._t0 = time.monotonic()
    plan = engine._plan

    def document(phase, **fields):
        return dict(schema="rf.fixed_workload.receipt.v1", phase=phase,
                    operation=plan.operation_id, root=smoke.ROOT_ID,
                    transport_sha256=smoke.TRANSPORT_SHA256,
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
                              cleanup_reserved_bytes=CLEANUP_BYTES,
                              cleanup_command_max_seconds=dict(CLEANUP_COMMAND_SECONDS)),
                     excl=True)

    def sink(cid):
        write(document("container_id_settled", container_id=cid),
              expected_identity=identity)

    engine.set_cid_sink(sink)
    engine._receipt_ready = True
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
