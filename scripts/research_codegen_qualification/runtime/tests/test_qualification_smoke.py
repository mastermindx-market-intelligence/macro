from pathlib import Path
"""Hermetic tests for the corrected qualification-only fixed Docker smoke.

Stages the exact root-provided transport/probe source bytes, verifies their
pinned SHA-256, and drives the real callable control flow through fake bounded
collectors modeling correct Docker field semantics.  subprocess.Popen is
patched to fail for every test: no Docker, no subprocess, no host effect.
The physical --execute path is never run here.  Host binding facts are
fictional approvedhost fixtures; nothing examines private host config.
"""
import hashlib
import json
import os
import stat
import base64
from dataclasses import replace

import pytest

import qualification_smoke as qsm
import qualification_runsc_smoke as qrs
from qualification_smoke import (
    ACTIVE_CHECKS, CLEANUP_RESERVE_BYTES, CONTAINER_NAME, DAEMON_IMAGE_ID,
    DOCKER_BINARY, DOCKER_ENDPOINT, EXPECTED_IMAGE_ENV, IMAGE_REF,
    OPERATION_ID, ROOT_ID, ROOT_LABEL_KEY, RUN_LABEL_KEY, SKIP_CHECKS,
    SKIP_REASON, TOTAL_OUTPUT_CAP_BYTES, BindingMismatch, SourceContractError,
)

TRANSPORT_SHA256 = "b6d36717ad3630d127b16fe9e117d9401bea1136880e28d19f0d18061933c633"
PROBE_SHA256 = "92fad6f371419f4cbb4bafba83257846429eae2df77feead83678905a9988cf7"

_TRANSPORT_SOURCE = Path(os.environ.get("RF_QUALIFICATION_TRANSPORT_SOURCE", str(Path(__file__).resolve().parents[4] / "engine/research_codegen/transport.py"))).read_bytes()

_PROBE_SOURCE = (Path(__file__).resolve().parents[1] / "fixed_smoke_probe.py").read_bytes()

CID = "a" * 64
OTHER_CID = "b" * 64
STATE_FORMAT = "[{{json .Id}},{{json .State}}]"

BINDING_OK = {
    "binding_schema": "rf.qualification_smoke.binding.v3",
    "expected_hostname": "rf-approved-host",
    "expected_uid": 65534, "expected_gid": 65534,
    "expected_kernel": "7.0.0-31-generic",
    "expected_host_os": "Approved Host OS 24.04",
    "daemon_arch": "x86_64", "ostype": "linux",
    "docker_endpoint": DOCKER_ENDPOINT, "docker_server_version": "29.1.3",
    "image_receipt_sha256": "e" * 64, "image_adjudication_sha256": "f" * 64,
    "client_config_dir": "/var/tmp/rf-test-client",
    "client_config_sha256": qsm.ANONYMOUS_CLIENT_CONFIG_SHA256
}


@pytest.fixture(autouse=True)
def no_subprocess(monkeypatch):
    import subprocess

    def _boom(*args, **kwargs):
        raise AssertionError("subprocess.Popen called inside hermetic test")

    monkeypatch.setattr(subprocess, "Popen", _boom)


@pytest.fixture()
def sources(tmp_path):
    tpath = tmp_path / "transport.py"
    ppath = tmp_path / "fixed_smoke_probe.py"
    tpath.write_bytes(_TRANSPORT_SOURCE)
    ppath.write_bytes(_PROBE_SOURCE)
    config = tmp_path / "docker-client"
    config.mkdir(mode=0o700)
    (config / "config.json").write_bytes(qsm.ANONYMOUS_CLIENT_CONFIG)
    (config / "config.json").chmod(0o600)
    BINDING_OK["client_config_dir"] = str(config)
    return str(tpath), str(ppath)


@pytest.fixture()
def comp(sources):
    tpath, ppath = sources
    return qsm.build_composition(tpath, ppath)


@pytest.fixture()
def runsc_comp(sources):
    tpath, ppath = sources
    return qrs.build_runsc_composition(tpath, ppath)


def res(t, rc, out=b"", err=b"", deadline=1.0, cap=1024, **kw):
    return t.EngineCommandResult(
        rc, out, err, deadline, cap, kw.pop("timed_out", False),
        kw.pop("output_truncated", False), kw.pop("observed_container_id", None),
        kw.pop("permission_refused", False), kw.pop("error_type", None))


def image_doc_ok(**over):
    doc = {"Id": DAEMON_IMAGE_ID, "RepoDigests": [IMAGE_REF],
           "Os": "linux", "Architecture": "amd64",
           "Cfg": {"Entrypoint": None, "Cmd": ["python3"], "User": "",
                   "WorkingDir": "/", "Volumes": None,
                   "Env": list(EXPECTED_IMAGE_ENV)}}
    doc.update(over)
    return doc


def version_doc_ok(**over):
    doc = {"Client": "29.1.3", "Server": "29.1.3"}
    doc.update(over)
    return doc


def info_doc_ok(**over):
    doc = {"Name": BINDING_OK["expected_hostname"],
           "KernelVersion": BINDING_OK["expected_kernel"],
           "ServerVersion": "29.1.3",
           "OperatingSystem": BINDING_OK["expected_host_os"],
           "OSType": "linux", "Architecture": "x86_64"}
    doc.update(over)
    return doc


def policy_doc_ok(comp, **over):
    base = {
        "Id": CID, "Name": "/" + CONTAINER_NAME,
        "Image": DAEMON_IMAGE_ID, "StateRunning": False,
        "Cfg": {"Image": IMAGE_REF, "Entrypoint": ["/usr/bin/env"],
                "Cmd": list(comp.plan.argv), "User": "65534:65534",
                "WorkingDir": "/", "Env": list(EXPECTED_IMAGE_ENV),
                "Labels": {ROOT_LABEL_KEY: ROOT_ID, RUN_LABEL_KEY: OPERATION_ID},
                "Healthcheck": {"Test": ["NONE"]}},
        "HC": {"ReadonlyRootfs": True, "CapDrop": ["ALL"], "CapAdd": None,
               "SecurityOpt": ["no-new-privileges"], "IpcMode": "private",
               "PidMode": "", "UTSMode": "", "CgroupnsMode": "private",
               "Privileged": False, "PidsLimit": 16,
               "Memory": 64 * 1024 * 1024, "MemorySwap": 64 * 1024 * 1024,
               "NanoCpus": 500000000,
               "Tmpfs": {"/tmp": "rw,noexec,nosuid,size=1048576,mode=1777"},
               "NetworkMode": "none", "PortBindings": None, "Links": None,
               "VolumesFrom": None, "Devices": None, "Binds": None,
               "GroupAdd": None, "ExtraHosts": None, "AutoRemove": False,
               "RestartPolicy": {"Name": "no", "MaximumRetryCount": 0},
               "LogConfig": {"Type": "none", "Config": {}}},
    }
    for path, value in over.items():
        node = base
        parts = path.split(".")
        for part in parts[:-1]:
            node = node[part]
        node[parts[-1]] = value
    return base


def runsc_policy_doc_ok(comp, **over):
    doc = policy_doc_ok(comp)
    doc["Name"] = "/" + qrs.CONTAINER_NAME
    doc["Cfg"]["Labels"] = {ROOT_LABEL_KEY: ROOT_ID, RUN_LABEL_KEY: qrs.OPERATION_ID}
    doc["HC"]["PidsLimit"] = 64
    doc["HC"]["Memory"] = 256 * 1024 * 1024
    doc["HC"]["MemorySwap"] = 256 * 1024 * 1024
    doc["HC"]["Runtime"] = "rf-runsc"
    return doc


def state_doc_ok(cid, **over):
    state = {"Status": "exited", "Running": False, "Paused": False,
             "Restarting": False, "OOMKilled": False, "Dead": False,
             "Pid": 0, "ExitCode": 0, "Error": "",
             "StartedAt": "2026-10-13T18:00:00Z",
             "FinishedAt": "2026-10-13T18:00:01Z"}
    state.update(over)
    return {"Id": cid, "State": state}


def verdict_dict():
    observed = {"allowed_computation": 42, "uid_gid": [65534, 65534],
                "minimal_environment": ["LANG", "PATH"], "readonly_root": True,
                "allowed_small_scratch": 16, "no_new_privileges": "1",
                "capabilities_dropped": "0000000000000000",
                "seccomp_present": "2", "api_socket_absent": False}
    records = [{"check": name, "status": "PASS", "observed": observed[name]}
               for name in ACTIVE_CHECKS if name != "public_egress"]
    records.append({"check": "public_egress", "status": "PASS", "errno": 101})
    records.extend({"check": name, "status": "SKIP", "reason": SKIP_REASON}
                   for name in SKIP_CHECKS)
    return {"schema": "rf.fixed_docker_smoke.v1",
            "mechanical_checks_passed": True, "candidate_admission": False,
            "containment_qualified": False, "records": records}


def verdict_bytes(**over):
    doc = verdict_dict()
    doc.update(over)
    return (json.dumps(doc, sort_keys=True, separators=(",", ":")) + "\n").encode()


def absence_bytes(cid):
    err = ("Error response from daemon: No such container: " + cid + "\n").encode()
    return b"[]\n", err


def canonical(doc):
    return json.dumps(doc, sort_keys=True, separators=(",", ":")).encode()


class FakeCollector:
    """Bounded fake engine executor dispatching on the exact effective argv."""

    def __init__(self, comp, policy_doc, state_doc=None, image_doc=None,
                 info_doc=None, version_doc=None, verdict_out=b"",
                 script=None, policy_format=None):
        self.t = comp.t
        self.policy_doc = policy_doc
        self.state_doc = state_doc
        self.image_doc = image_doc if image_doc is not None else image_doc_ok()
        self.info_doc = info_doc if info_doc is not None else info_doc_ok()
        self.version_doc = version_doc if version_doc is not None else version_doc_ok()
        self.verdict_out = verdict_out
        self.script = script or {}
        self.policy_format = policy_format or qsm._POLICY_FORMAT
        self.calls = []

    def __call__(self, argv, *, deadline_seconds, output_cap_bytes):
        assert argv[0] == DOCKER_BINARY, argv
        assert list(argv[1:3]) == ["--host", DOCKER_ENDPOINT], argv
        effective_argv = argv
        assert argv[3:5] == ("--config", BINDING_OK["client_config_dir"])
        argv = argv[:3] + argv[5:]  # explicit logical view for legacy shape assertions
        kind = argv[3]
        self.calls.append({"kind": kind, "argv": list(effective_argv), "logical_argv": list(argv),
                           "deadline": deadline_seconds, "cap": output_cap_bytes})
        if kind in self.script:
            action = self.script.pop(kind)
            if isinstance(action, BaseException):
                raise action
            if callable(action):
                outcome = action(deadline_seconds, output_cap_bytes)
            else:
                outcome = action
        else:
            outcome = self._default(argv, kind, deadline_seconds, output_cap_bytes)
        return self._classify_refusal(kind, outcome)

    def _classify_refusal(self, kind, outcome):
        # Mirror the real executor: only failed control commands classify.
        verb = {"image": "inspect", "info": "inspect", "version": "inspect",
                "inspect": "inspect"}.get(kind, kind)
        if (verb in ("create", "stop", "kill", "rm", "inspect")
                and outcome.returncode not in (0, None)):
            refused = self.t.control_permission_refusal(
                verb, outcome.returncode, outcome.stdout + outcome.stderr)
            if refused:
                return replace(outcome, permission_refused=True)
        return outcome

    def _default(self, argv, kind, deadline, cap):
        t = self.t
        if kind == "image":
            return res(t, 0, canonical(self.image_doc), deadline=deadline, cap=cap)
        if kind == "info":
            return res(t, 0, canonical(self.info_doc), deadline=deadline, cap=cap)
        if kind == "version":
            return res(t, 0, canonical(self.version_doc), deadline=deadline, cap=cap)
        if kind == "create":
            return res(t, 0, (CID + "\n").encode(), deadline=deadline, cap=cap,
                       observed_container_id=CID)
        if kind == "start":
            assert CID in argv
            return res(t, 0, self.verdict_out, deadline=deadline, cap=cap)
        if kind == "inspect":
            if len(argv) == 9 and argv[7] == self.policy_format:
                assert argv[8] == CID
                return res(t, 0, canonical(self.policy_doc), deadline=deadline, cap=cap)
            if len(argv) == 9 and argv[7] == STATE_FORMAT:
                assert argv[8] == CID
                # Go template [{{json .Id}},{{json .State}}] -> 2-element array.
                out = json.dumps([self.state_doc["Id"], self.state_doc["State"]],
                                 sort_keys=True, separators=(",", ":")).encode()
                return res(t, 0, out, deadline=deadline, cap=cap)
            assert len(argv) == 7 and argv[5] == "container" and argv[6] == CID, argv
            out, err = absence_bytes(CID)
            return res(t, 1, out, err, deadline=deadline, cap=cap)
        if kind in ("stop", "kill", "rm"):
            assert CID in argv
            return res(t, 0, b"", deadline=deadline, cap=cap)
        raise AssertionError("unexpected engine command: " + kind)


def make_engine(comp, collector, binding=None):
    return qsm.FixedQualificationEngine(comp.t, comp.plan, executor=collector,
                                        binding=BINDING_OK if binding is None
                                        else binding)


def make_runsc_engine(comp, collector, binding=None):
    return qrs.RunscQualificationEngine(comp.t, comp.plan, executor=collector,
                                        binding=BINDING_OK if binding is None
                                        else binding)


def run_attempt(comp, engine):
    t = comp.t
    return t.TransportOrchestrator(engine).execute(t.TransportSession(comp.plan))

# ---------------------------------------------------------------------------
# Source contract and dry-run plan
# ---------------------------------------------------------------------------

def test_sources_stage_and_verify_exact_bytes(comp):
    assert hashlib.sha256(_TRANSPORT_SOURCE).hexdigest() == TRANSPORT_SHA256
    assert hashlib.sha256(_PROBE_SOURCE).hexdigest() == PROBE_SHA256
    assert len(_PROBE_SOURCE) == 2997
    assert comp.transport_sha256 == TRANSPORT_SHA256
    assert comp.probe_sha256 == PROBE_SHA256


def test_wrong_source_or_probe_bytes_refused(sources, tmp_path):
    tpath, ppath = sources
    bad_t = tmp_path / "t2.py"
    bad_t.write_bytes(_TRANSPORT_SOURCE.replace(b"Dormant", b"dormant", 1))
    with pytest.raises(SourceContractError, match="transport source"):
        qsm.build_composition(str(bad_t), ppath)
    bad_p = tmp_path / "p2.py"
    bad_p.write_bytes(_PROBE_SOURCE.replace(b"smoke", b"Smoke", 1))
    with pytest.raises(SourceContractError, match="probe"):
        qsm.build_composition(tpath, str(bad_p))


def test_no_physical_host_hardcoded(sources):
    # Root-approved actual-host binding: no forced Ubuntu0 hostname/kernel or
    # stale acquisition receipt is baked into the executable source.
    for module in (qsm, qrs):
        text = open(module.__file__).read()
        assert "ubuntu0" not in text.lower()
        assert "222f5b68a6c6c7dbbcf17113e079a5fad48b84e710f9a52dacc5fe27ac3f780f" not in text
        assert "d389d5054a5b3d549a0e4a4bc1f20889008486cc20ac18ba35a7822d61b528cf" not in text
    assert "expected_hostname" in qsm._BINDING_KEYS


def test_dry_run_plan_matches_fixed_design(comp):
    t = comp.t
    engine = qsm.FixedQualificationEngine(t, comp.plan, executor=None)
    d = engine.describe()
    assert d["plan_sha256"] == t.plan_identity(comp.plan)
    assert d["effective_create_argv_sha256"] == qsm.argv_sha256(
        engine.effective_create_argv())
    assert d["plan_sha256"] != d["effective_create_argv_sha256"]
    argv = d["effective_create_argv"]
    assert argv[0:3] == [DOCKER_BINARY, "--host", DOCKER_ENDPOINT]
    for flag in ("--pull=never", "--network=none", "--read-only",
                 "--cap-drop=ALL", "--security-opt=no-new-privileges",
                 "--no-healthcheck", "--log-driver=none", "--restart=no",
                 "--cgroupns=private", "--ipc=private"):
        assert flag in argv
    i = argv.index("--tmpfs")
    assert argv[i + 1] == "/tmp:rw,noexec,nosuid,size=1048576,mode=1777"
    assert argv[argv.index("--name") + 1] == CONTAINER_NAME
    assert argv[argv.index("--label") + 1] == "org.mastermind.root=" + ROOT_ID
    j = argv.index("--")
    assert argv[j + 1] == IMAGE_REF
    assert argv[-1] == _PROBE_SOURCE.decode("ascii")
    assert argv[argv.index("--entrypoint") + 1] == "/usr/bin/env"
    assert not any(item.startswith("--runtime") for item in argv)
    assert d["selected_runtime"] is None
    assert d["execute_authorized"] is False
    assert d["candidate_admission"] is False
    assert d["containment_qualified"] is False
    assert d["budgets"]["whole_attempt_seconds"] == 130.0
    assert d["budgets"]["workload_phase_seconds"] == 90.0
    assert d["budgets"]["aggregate_output_bytes"] == 16384
    assert d["budgets"]["cleanup_reserved_bytes"] == 4096
    limits = d["limits"]
    assert (limits["uid"], limits["gid"], limits["pids_limit"]) == (65534, 65534, 16)
    assert limits["memory_bytes"] == 67108864 and limits["cpus"] == 0.5
    assert limits["wall_clock_seconds"] == 20.0 and limits["tmpfs_bytes"] == 1048576
    assert limits["stop_timeout_seconds"] == 2.0
    assert d["binding"]["binding_schema"] == "rf.qualification_smoke.binding.v3"
    assert set(d["binding"]["fixed_values"]) == {
        "docker_endpoint", "expected_uid", "expected_gid",
        "docker_server_version", "daemon_arch", "ostype"}
    assert "rf-approved-host" not in json.dumps(d)


def test_dry_run_info_and_version_templates_match_primary_source():
    # docker CLI 29.1.3 info.go: dockerInfo embeds *system.Info; top-level
    # .ServerVersion/.OSType/.Architecture, and no .Server object.
    fmt = qsm._INFO_FORMAT
    assert "{{json .ServerVersion}}" in fmt and "{{json .OSType}}" in fmt \
            and "{{json .Architecture}}" in fmt
    assert ".Server." not in fmt
    # Only `docker version` carries .Client/.Server.
    vfmt = qsm._VERSION_FORMAT
    assert vfmt == '{"Client":{{json .Client.Version}},"Server":{{json .Server.Version}}}'
    assert "{{json .Client.Version}}" in vfmt and "{{json .Server.Version}}" in vfmt


def test_dry_run_engine_never_executes(comp):
    engine = qsm.FixedQualificationEngine(comp.t, comp.plan, executor=None)
    with pytest.raises(comp.t.TransportDormantError):
        engine.run(comp.t.build_create_argv(comp.plan),
                   deadline_seconds=20.0, output_cap_bytes=16384)


def test_dry_run_cli_emits_plan_without_subprocess(sources, capsys):
    tpath, ppath = sources
    assert qsm.main(["--transport", tpath, "--probe", ppath]) == 0
    doc = json.loads(capsys.readouterr().out)
    assert doc["schema"] == "rf.qualification_smoke.dryrun.v1"
    assert doc["execute_authorized"] is False
    assert doc["candidate_admission"] is False


def test_execute_gate_requires_binding_and_receipt(sources, capsys):
    tpath, ppath = sources
    assert qsm.main(["--transport", tpath, "--probe", ppath, "--execute"]) == 2
    refusal = json.loads(capsys.readouterr().err)
    assert refusal["candidate_admission"] is False
    assert refusal["containment_qualified"] is False


def binding_file(tmp_path, doc=None):
    body = json.dumps(doc or BINDING_OK, sort_keys=True,
                      separators=(",", ":")).encode()
    path = tmp_path / "binding.json"
    path.write_bytes(body)
    return str(path), hashlib.sha256(body).hexdigest()


def test_binding_file_contract(tmp_path):
    path, sha = binding_file(tmp_path)
    assert qsm.load_binding_file(path, sha) == BINDING_OK
    with pytest.raises(SourceContractError):
        qsm.load_binding_file(path, "0" * 64)
    for bad in (dict(BINDING_OK, docker_endpoint="unix:///var/run/other.sock"),
                dict(BINDING_OK, docker_server_version="28.0.0"),
                dict(BINDING_OK, daemon_arch="amd64"),
                dict(BINDING_OK, expected_uid=0),
                dict(BINDING_OK, image_receipt_sha256="nothex"),
                {k: v for k, v in BINDING_OK.items() if k != "expected_kernel"},
                dict(BINDING_OK, expected_hostname="bad host\n")):
        bad_path, bad_sha = binding_file(tmp_path, bad)
        with pytest.raises(BindingMismatch):
            qsm.load_binding_file(bad_path, bad_sha)


def test_host_binding_mismatch_refuses_create(comp):
    # The daemon must match the root-approved binding's selected host exactly.
    collector = FakeCollector(comp, policy_doc_ok(comp),
                              info_doc=info_doc_ok(Name="somewhere-else"))
    engine = make_engine(comp, collector)
    with pytest.raises(BindingMismatch, match="daemon identity"):
        engine.run(comp.t.build_create_argv(comp.plan), deadline_seconds=20.0,
                   output_cap_bytes=16384)
    assert not any(c["kind"] == "create" for c in collector.calls)


def test_fsync_failure_after_cid_still_cleans_truthfully(comp, tmp_path,
                                                         monkeypatch):
    # Repaired semantics: a failed durable CID receipt blocks start but the
    # exact same known CID still reaches ordinary cleanup, and the settled
    # outcome stays truthful (never CLEANED_SUCCESS for skipped work).
    t = comp.t
    collector = FakeCollector(comp, policy_doc_ok(comp),
                              state_doc=state_doc_ok(CID),
                              verdict_out=verdict_bytes())
    engine = make_engine(comp, collector)
    receipt = str(tmp_path / "receipt.jsonl")
    original = qsm._write_receipt
    def flaky(path, doc, excl, **kwargs):
        if excl is False and doc.get("phase") == "container_id_settled":
            raise OSError("disk on fire")
        return original(path, doc, excl, **kwargs)
    monkeypatch.setattr(qsm, "_write_receipt", flaky)
    attempt = qsm.execute_attempt(comp, engine, receipt)
    assert attempt.container_id == CID
    assert attempt.cleanup_confirmed
    assert attempt.state is t.AttemptState.CLEANED_FAILURE
    assert not attempt.workload_confirmed
    assert engine.cid_persist_problem and "OSError" in engine.cid_persist_problem
    final = json.loads(open(receipt).readlines()[-1])
    assert "OSError" in final["cid_persist_problem"]
    assert "start" not in [c["kind"] for c in collector.calls]


def test_fixed_actualhost_binding_positive_mismatch_and_dryrun(
        comp, sources, tmp_path, capsys):
    tpath, ppath = sources
    # Positive: the fictional approvedhost binding drives the daemon gate and
    # the full known-CID path proceeds.
    collector = FakeCollector(comp, policy_doc_ok(comp),
                              state_doc=state_doc_ok(CID),
                              verdict_out=verdict_bytes())
    engine = make_engine(comp, collector)
    attempt = qsm.execute_attempt(comp, engine, str(tmp_path / "r"))
    assert attempt.state is comp.t.AttemptState.CLEANED_SUCCESS
    # Mismatch: daemon reports a different selected host than the binding.
    collector2 = FakeCollector(comp, policy_doc_ok(comp),
                               info_doc=info_doc_ok(Name="unbound-host-elsewhere"))
    engine2 = make_engine(comp, collector2)
    with pytest.raises(BindingMismatch, match="daemon identity"):
        engine2.run(comp.t.build_create_argv(comp.plan), deadline_seconds=20.0,
                    output_cap_bytes=16384)
    assert not any(c["kind"] == "create" for c in collector2.calls)
    # Dryrun needs no binding at all and never bakes host facts in.
    assert qsm.main(["--transport", tpath, "--probe", ppath]) == 0
    doc = json.loads(capsys.readouterr().out)
    assert doc["binding"]["host_facts_from_root_approved_file"] is True
    assert "expected_hostname" not in doc["binding"]["fixed_values"]

# ---------------------------------------------------------------------------
# Positive known-CID path through the real callable control flow
# ---------------------------------------------------------------------------

def test_positive_known_cid_full_path(comp, tmp_path):
    t = comp.t
    collector = FakeCollector(comp, policy_doc_ok(comp),
                              state_doc=state_doc_ok(CID),
                              verdict_out=verdict_bytes())
    engine = make_engine(comp, collector)
    receipt = str(tmp_path / "receipt.jsonl")
    attempt = qsm.execute_attempt(comp, engine, receipt)
    assert attempt.state is t.AttemptState.CLEANED_SUCCESS
    assert attempt.container_id == CID
    assert attempt.workload_confirmed and attempt.cleanup_confirmed
    assert not attempt.execution_uncertain and not attempt.reconciliation_required
    assert engine.settled_cid == CID and engine.cid_persist_problem is None
    verdict = qsm.validate_verdict(t, attempt)
    assert verdict["mechanical_checks_passed"] is True
    assert verdict["candidate_admission"] is False
    kinds = [c["kind"] for c in collector.calls]
    assert kinds == ["image", "info", "version", "create", "inspect", "start",
                     "inspect", "stop", "rm", "inspect"]
    policy_call, state_call, absence_call = (collector.calls[4],
                                             collector.calls[6],
                                             collector.calls[9])
    assert policy_call["logical_argv"][7] == qsm._POLICY_FORMAT
    assert policy_call["logical_argv"][8] == CID
    assert policy_call["logical_argv"][3:7] == ["inspect", "--type", "container", "--format"]
    assert state_call["logical_argv"][7] == STATE_FORMAT
    assert state_call["logical_argv"][8] == CID
    assert state_call["logical_argv"][5] == "container"
    assert len(absence_call["logical_argv"]) == 7 and absence_call["logical_argv"][6] == CID
    assert absence_call["logical_argv"][4:6] == ["--type", "container"]
    out, err = absence_bytes(CID)
    assert len(out + err) == 115
    for record in collector.calls[7:]:
        assert CID in record["logical_argv"]
    assert stat.S_IMODE(os.stat(receipt).st_mode) == 0o600
    lines = open(receipt).readlines()
    assert [json.loads(line)["phase"] for line in lines] == [
        "pre_create", "container_id_settled", "attempt_settled"]
    assert json.loads(lines[1])["container_id"] == CID
    final = json.loads(lines[2])
    assert final["container_id"] == CID
    assert len(final["engine_ledger"]) == len(collector.calls)


def test_every_real_command_carries_exact_host_prefix(comp):
    collector = FakeCollector(comp, policy_doc_ok(comp),
                              state_doc=state_doc_ok(CID),
                              verdict_out=verdict_bytes())
    engine = make_engine(comp, collector)
    run_attempt(comp, engine)
    for record in collector.calls:
        assert record["argv"][:5] == [DOCKER_BINARY, "--host", DOCKER_ENDPOINT,
                                      "--config", BINDING_OK["client_config_dir"]]


def test_strict_absence_grammar_only_exact_form(comp):
    t = comp.t
    out, err = absence_bytes(CID)
    assert len(out + err) == 115
    assert t.parse_container_absence(out, err, CID) is True
    assert t.parse_container_absence(b"", err, CID) is True
    generic = ("Error response from daemon: No such object: " + CID + "\n").encode()
    assert t.parse_container_absence(out, generic, CID) is False
    assert t.parse_container_absence(out, err.replace(b"a" * 8, b"b" * 8, 1), CID) is False
    assert t.parse_container_absence(out, err + err, CID) is False
    assert t.parse_container_absence(b"[] extra\n", err, CID) is False
    assert t.parse_container_absence(out, absence_bytes(OTHER_CID)[1], CID) is False
    assert t.parse_container_absence("[]", err, CID) is False


def test_create_unknown_no_start_and_no_recreate(comp):
    t = comp.t
    collector = FakeCollector(comp, policy_doc_ok(comp))
    collector.script["create"] = res(t, 0, b"not-a-container-id\n")
    engine = make_engine(comp, collector)
    attempt = run_attempt(comp, engine)
    assert attempt.state is t.AttemptState.CREATE_UNCERTAIN
    assert attempt.container_id is None and attempt.execution_uncertain
    assert engine.settled_cid is None
    assert not any(c["kind"] in ("start", "inspect", "stop", "rm")
                   for c in collector.calls)
    # A fresh session must never mint a replacement create for an unknown effect.
    second = run_attempt(comp, engine)
    assert second.state is t.AttemptState.CREATE_UNCERTAIN
    assert second.container_id is None
    assert [c["kind"] for c in collector.calls].count("create") == 1


def test_second_create_on_settled_engine_refused(comp):
    t = comp.t
    collector = FakeCollector(comp, policy_doc_ok(comp))
    engine = make_engine(comp, collector)
    argv = t.build_create_argv(comp.plan)
    engine.run(argv, deadline_seconds=20.0, output_cap_bytes=16384)
    assert engine.settled_cid == CID
    with pytest.raises(t.TransportStateError):
        engine.run(argv, deadline_seconds=20.0, output_cap_bytes=16384)


def test_strict_argv_tuple_required(comp):
    t = comp.t

    def boom(argv, *, deadline_seconds, output_cap_bytes):
        raise AssertionError("executor must never be called")

    engine = qsm.FixedQualificationEngine(comp.t, comp.plan, executor=boom)
    with pytest.raises(t.TransportPlanError):
        engine.run(list(t.build_create_argv(comp.plan)), deadline_seconds=20.0,
                   output_cap_bytes=16384)
    with pytest.raises(t.TransportPlanError):
        engine.run(("/bin/docker", "create"), deadline_seconds=10.0,
                   output_cap_bytes=1024)


def test_tampered_or_generic_argv_refused_before_any_effect(comp):
    t = comp.t

    def boom(argv, *, deadline_seconds, output_cap_bytes):
        raise AssertionError("executor must never be called")

    engine = qsm.FixedQualificationEngine(t, comp.plan, executor=boom)
    argv = list(t.build_create_argv(comp.plan))
    argv[argv.index("--pids-limit") + 1] = "4096"
    with pytest.raises(t.TransportPlanError):
        engine.run(tuple(argv), deadline_seconds=20.0, output_cap_bytes=16384)
    with pytest.raises(t.TransportPlanError):
        engine.run((DOCKER_BINARY, "run", "--rm", IMAGE_REF),
                   deadline_seconds=10.0, output_cap_bytes=1024)
    with pytest.raises(t.TransportPlanError):
        engine.run((DOCKER_BINARY, "inspect", "--type", "container",
                    "--format", "{{json .State}}", CID),
                   deadline_seconds=10.0, output_cap_bytes=1024)
    with pytest.raises(t.TransportPlanError):
        engine.run((DOCKER_BINARY, "inspect", "--format", STATE_FORMAT,
                    "--type", "container", CID),
                   deadline_seconds=10.0, output_cap_bytes=1024)


def test_wrong_cid_lifecycle_refused(comp):
    t = comp.t
    collector = FakeCollector(comp, policy_doc_ok(comp))
    engine = make_engine(comp, collector)
    engine.run(t.build_create_argv(comp.plan), deadline_seconds=20.0,
               output_cap_bytes=16384)
    assert engine.settled_cid == CID
    with pytest.raises(t.TransportPlanError):
        engine.run(t.build_stop_argv(comp.plan, OTHER_CID),
                   deadline_seconds=10.0, output_cap_bytes=1024)
    assert all(OTHER_CID not in c["logical_argv"] for c in collector.calls)

# ---------------------------------------------------------------------------
# Preflight field semantics (image manifest vs OCI config vs daemon facts)
# ---------------------------------------------------------------------------

def test_image_preflight_mismatch_refuses_create(comp):
    t = comp.t
    bad_image = image_doc_ok()
    bad_image["Id"] = "sha256:" + "c" * 64
    collector = FakeCollector(comp, policy_doc_ok(comp), image_doc=bad_image)
    engine = make_engine(comp, collector)
    with pytest.raises(BindingMismatch, match="image preflight"):
        engine.run(t.build_create_argv(comp.plan), deadline_seconds=20.0,
                   output_cap_bytes=16384)
    assert not any(c["kind"] == "create" for c in collector.calls)


def test_typed_user_empty_string_never_null(comp):
    t = comp.t
    # OCIv1 ImageConfig User is a Go string with omitempty: an absent JSON
    # User decodes to the typed empty string; null is a wrong shape.
    good = FakeCollector(comp, policy_doc_ok(comp), image_doc=image_doc_ok())
    make_engine(comp, good).run(t.build_create_argv(comp.plan),
                                deadline_seconds=20.0, output_cap_bytes=16384)
    assert good.calls[0]["kind"] == "image"
    with pytest.raises(BindingMismatch, match="Cfg.User"):
        make_engine(comp, FakeCollector(comp, policy_doc_ok(comp),
                                        image_doc=image_doc_ok(
                                            Cfg={"Entrypoint": None,
                                                 "Cmd": ["python3"], "User": None,
                                                 "WorkingDir": "/", "Volumes": None,
                                                 "Env": list(EXPECTED_IMAGE_ENV)})
                                        )).run(
            t.build_create_argv(comp.plan), deadline_seconds=20.0,
            output_cap_bytes=16384)


def test_exact_image_ref_spelling_required_no_suffix_normalization(comp):
    t = comp.t
    # Same digest under a different repo spelling stays refused: one actual
    # approved fixed ref spelling per root binding, no permissive suffix rule.
    other_spelling = image_doc_ok(
        RepoDigests=["python@" + DAEMON_IMAGE_ID])
    collector = FakeCollector(comp, policy_doc_ok(comp), image_doc=other_spelling)
    engine = make_engine(comp, collector)
    with pytest.raises(BindingMismatch, match="RepoDigests"):
        engine.run(t.build_create_argv(comp.plan), deadline_seconds=20.0,
                   output_cap_bytes=16384)
    assert not any(c["kind"] == "create" for c in collector.calls)


def test_image_manifest_id_separate_from_oci_config_digest(comp):
    # The manifest Id (bfebb...) and the OCI config digest (607dc...) are
    # distinct bindings; neither may stand in for the other.
    assert qsm.DAEMON_IMAGE_ID == "sha256:bfebb8e11b53c46715fe3634e3b7bc5afb33b21ec82521539af1467c81ad3aed"
    assert qsm.OCI_CONFIG_DIGEST == "sha256:607dc744833974b365cc338d565e01bb76eaebe25993fe328ce185170bcd8f05"
    assert qsm.DAEMON_IMAGE_ID != qsm.OCI_CONFIG_DIGEST
    collector = FakeCollector(comp, policy_doc_ok(comp),
                              image_doc=image_doc_ok(Id=qsm.OCI_CONFIG_DIGEST))
    with pytest.raises(BindingMismatch, match="Id"):
        make_engine(comp, collector).run(comp.t.build_create_argv(comp.plan),
                                         deadline_seconds=20.0,
                                         output_cap_bytes=16384)


def test_daemon_arch_x86_64_image_amd64_explicit_binding(comp):
    t = comp.t
    # docker info reports the uname-style daemon arch x86_64 while the image
    # manifest is amd64; neither is normalized into the other.
    assert qsm.DAEMON_ARCH == "x86_64"
    collector = FakeCollector(comp, policy_doc_ok(comp),
                              info_doc=info_doc_ok(Architecture="amd64"))
    with pytest.raises(BindingMismatch, match="daemon identity"):
        make_engine(comp, collector).run(t.build_create_argv(comp.plan),
                                         deadline_seconds=20.0,
                                         output_cap_bytes=16384)
    bad_image_arch = image_doc_ok(Architecture="x86_64")
    collector2 = FakeCollector(comp, policy_doc_ok(comp), image_doc=bad_image_arch)
    with pytest.raises(BindingMismatch, match="platform"):
        make_engine(comp, collector2).run(t.build_create_argv(comp.plan),
                                          deadline_seconds=20.0,
                                          output_cap_bytes=16384)


def test_version_check_finite_client_and_server(comp):
    t = comp.t
    for bad in (version_doc_ok(Server="28.3.0"), version_doc_ok(Client="28.3.0")):
        collector = FakeCollector(comp, policy_doc_ok(comp), version_doc=bad)
        engine = make_engine(comp, collector)
        with pytest.raises(BindingMismatch, match="version mismatch"):
            engine.run(t.build_create_argv(comp.plan), deadline_seconds=20.0,
                       output_cap_bytes=16384)
        assert not any(c["kind"] == "create" for c in collector.calls)
        kinds = [c["kind"] for c in collector.calls]
        assert kinds == ["image", "info", "version"]


# ---------------------------------------------------------------------------
# Policy gate, permission refusals and freezing
# ---------------------------------------------------------------------------

def test_policy_violation_blocks_start_and_cleans(comp):
    t = comp.t
    bad = policy_doc_ok(comp, **{"HC.Privileged": True})
    collector = FakeCollector(comp, bad, state_doc=state_doc_ok(CID),
                              verdict_out=verdict_bytes())
    engine = make_engine(comp, collector)
    attempt = run_attempt(comp, engine)
    assert not attempt.workload_confirmed and attempt.execution_uncertain
    assert attempt.state is t.AttemptState.CLEANED_FAILURE
    kinds = [c["kind"] for c in collector.calls]
    assert "start" not in kinds
    assert kinds.count("rm") == 1 and kinds[-1] == "inspect"
    with pytest.raises(SourceContractError):
        qsm.validate_verdict(t, attempt)


def test_policy_document_is_the_container_not_the_image(comp):
    # .Id must be the engine's known 64-hex container id; the image manifest
    # id in that slot is a wrong document shape.
    assert qsm._policy_mismatch(comp.plan, policy_doc_ok(comp)) is None
    doc = policy_doc_ok(comp, **{"Id": qsm.DAEMON_IMAGE_ID})
    assert qsm._policy_mismatch(comp.plan, doc) == "Id"
    doc = policy_doc_ok(comp, **{"Id": "short"})
    assert qsm._policy_mismatch(comp.plan, doc) == "Id"


def test_policy_permission_refusal_freezes_all_mutation(comp):
    t = comp.t
    collector = FakeCollector(comp, policy_doc_ok(comp))
    collector.script["inspect"] = res(t, 126, b"docker: permission denied\n")
    engine = make_engine(comp, collector)
    attempt = run_attempt(comp, engine)
    assert engine.frozen is True
    assert "permission refusal" in attempt.detail
    assert attempt.state is t.AttemptState.CLEANUP_UNCERTAIN
    kinds = [c["kind"] for c in collector.calls]
    assert kinds.count("inspect") == 1
    assert "start" not in kinds and "rm" not in kinds and "stop" not in kinds
    with pytest.raises(t.TransportPermissionRefusal):
        engine.run(t.build_inspect_argv(comp.plan, CID),
                   deadline_seconds=10.0, output_cap_bytes=1024)


def test_cleanup_permission_refusal_freezes_no_retry(comp):
    t = comp.t
    collector = FakeCollector(comp, policy_doc_ok(comp),
                              state_doc=state_doc_ok(CID),
                              verdict_out=verdict_bytes())
    collector.script["stop"] = res(comp.t, 126, b"permission denied\n")
    engine = make_engine(comp, collector)
    attempt = run_attempt(comp, engine)
    assert engine.frozen is True
    assert "cleanup mutation frozen" in attempt.detail
    kinds = [c["kind"] for c in collector.calls]
    assert kinds.count("stop") == 1
    assert "kill" not in kinds and "rm" not in kinds
    assert attempt.state is t.AttemptState.CLEANUP_UNCERTAIN


def test_control_refusal_on_each_phase_freezes(comp):
    t = comp.t
    refused = res(t, 126, b"Error response from daemon: authorization denied\n")
    cases = {
        "image": ["image"],
        "info": ["image", "info"],
        "version": ["image", "info", "version"],
        "create": ["image", "info", "version", "create"],
        "inspect": ["image", "info", "version", "create", "inspect"],
        "stop": ["image", "info", "version", "create", "inspect", "start",
                 "inspect", "stop"],
    }
    for script_kind, before in cases.items():
        collector = FakeCollector(comp, policy_doc_ok(comp),
                                  state_doc=state_doc_ok(CID),
                                  verdict_out=verdict_bytes())
        collector.script[script_kind] = refused
        engine = make_engine(comp, collector)
        run_attempt(comp, engine)
        assert engine.frozen is True, script_kind
        kinds = [c["kind"] for c in collector.calls]
        assert kinds == before, (kind, kinds)
        with pytest.raises(t.TransportPermissionRefusal):
            engine.run(t.build_inspect_argv(comp.plan, CID),
                       deadline_seconds=10.0, output_cap_bytes=1024)


def test_local_permissionerror_freezes_but_workload_text_never_classifies(comp):
    t = comp.t
    collector = FakeCollector(comp, policy_doc_ok(comp),
                              state_doc=state_doc_ok(CID),
                              verdict_out=verdict_bytes())
    collector.script["start"] = PermissionError("collector exec refused")
    engine = make_engine(comp, collector)
    attempt = run_attempt(comp, engine)
    assert engine.frozen is True
    kinds = [c["kind"] for c in collector.calls]
    assert kinds == ["image", "info", "version", "create", "inspect", "start"]
    assert attempt.state is t.AttemptState.CLEANUP_UNCERTAIN
    # Attached workload text containing permission-looking words never
    # classifies a denial: the start gate stays purely local.
    collector2 = FakeCollector(comp, policy_doc_ok(comp),
                               state_doc=state_doc_ok(CID),
                               verdict_out=b'{"note": "permission denied"}\n')
    engine2 = make_engine(comp, collector2)
    attempt2 = run_attempt(comp, engine2)
    assert engine2.frozen is False
    # The odd workload text caused no freeze and no denial classification;
    # the state inspect still decides the outcome independently.
    assert attempt2.state is t.AttemptState.CLEANED_SUCCESS

# ---------------------------------------------------------------------------
# Durable caller receipt: start gating, interruption, truthful settlement
# ---------------------------------------------------------------------------

def test_cid_sink_oserror_blocks_start_and_cleans(comp, tmp_path, monkeypatch):
    t = comp.t
    collector = FakeCollector(comp, policy_doc_ok(comp),
                              state_doc=state_doc_ok(CID),
                              verdict_out=verdict_bytes())
    engine = make_engine(comp, collector)
    receipt = str(tmp_path / "receipt")
    original = qsm._write_receipt
    def fail(path, doc, excl, **kwargs):
        if doc.get("phase") == "container_id_settled":
            raise OSError("simulated fsync failure")
        return original(path, doc, excl, **kwargs)
    monkeypatch.setattr(qsm, "_write_receipt", fail)
    attempt = qsm.execute_attempt(comp, engine, receipt)
    assert "start" not in [c["kind"] for c in collector.calls]
    assert attempt.cleanup_confirmed and not attempt.workload_confirmed
    assert attempt.state is t.AttemptState.CLEANED_FAILURE
    assert engine.settled_cid == CID
    assert engine.cid_persist_problem == "OSError"
    phases = [json.loads(line)["phase"] for line in open(receipt).readlines()]
    assert phases == ["pre_create", "attempt_settled"]
    final = json.loads(open(receipt).readlines()[-1])
    assert final["cid_persist_problem"] == "OSError"
    assert final["container_id"] == CID


def test_cid_sink_keyboardinterrupt_cleans_same_id(comp, tmp_path, monkeypatch):
    t = comp.t
    collector = FakeCollector(comp, policy_doc_ok(comp),
                              state_doc=state_doc_ok(CID))
    engine = make_engine(comp, collector)
    receipt = str(tmp_path / "receipt")
    original = qsm._write_receipt
    def interrupt(path, doc, excl, **kwargs):
        if doc.get("phase") == "container_id_settled":
            raise KeyboardInterrupt("interrupted immediately after known CID")
        return original(path, doc, excl, **kwargs)
    monkeypatch.setattr(qsm, "_write_receipt", interrupt)
    with pytest.raises(KeyboardInterrupt):
        qsm.execute_attempt(comp, engine, receipt)
    assert engine.settled_cid == CID
    kinds = [c["kind"] for c in collector.calls]
    assert "start" not in kinds
    assert "stop" in kinds and "rm" in kinds and "inspect" in kinds
    for record in collector.calls:
        if record["kind"] in ("stop", "rm", "inspect"):
            assert CID in record["logical_argv"]
    assert engine.self_cleanup_confirmed is True
    final = json.loads(open(receipt).readlines()[-1])
    assert final["phase"] == "attempt_interrupted"
    assert final["exception_type"] == "KeyboardInterrupt"
    assert final["engine_settled_container_id"] == CID
    assert final["self_cleanup_confirmed"] is True


def test_interruption_after_create_cleans_same_id(comp, tmp_path):
    t = comp.t
    collector = FakeCollector(comp, policy_doc_ok(comp),
                              state_doc=state_doc_ok(CID))
    collector.script["start"] = KeyboardInterrupt("simulated interruption")
    engine = make_engine(comp, collector)
    receipt = str(tmp_path / "receipt.jsonl")
    with pytest.raises(KeyboardInterrupt):
        qsm.execute_attempt(comp, engine, receipt)
    kinds = [c["kind"] for c in collector.calls]
    assert kinds.count("start") == 1  # attempted once, interrupted, never retried
    assert kinds.count("create") == 1
    assert "stop" in kinds and "rm" in kinds
    for record in collector.calls:
        if record["kind"] in ("stop", "rm"):
            assert CID in record["logical_argv"]
    lines = open(receipt).readlines()
    assert json.loads(lines[0])["phase"] == "pre_create"
    assert json.loads(lines[1])["container_id"] == CID
    final = json.loads(lines[-1])
    assert final["phase"] == "attempt_interrupted"
    assert final["engine_settled_container_id"] == CID
    assert final["exception_type"] == "KeyboardInterrupt"


def test_final_receipt_failure_remains_truthful(comp, tmp_path, monkeypatch):
    t = comp.t
    collector = FakeCollector(comp, policy_doc_ok(comp),
                              state_doc=state_doc_ok(CID),
                              verdict_out=verdict_bytes())
    engine = make_engine(comp, collector)
    receipt = str(tmp_path / "receipt")
    original = qsm._write_receipt
    def fail_final(path, doc, excl, **kwargs):
        if doc.get("phase") == "attempt_settled":
            raise OSError("final receipt write refused")
        return original(path, doc, excl, **kwargs)
    monkeypatch.setattr(qsm, "_write_receipt", fail_final)
    with pytest.raises(OSError):
        qsm.execute_attempt(comp, engine, receipt)
    # Cleanup fully settled before the failed write; no false PASS anywhere.
    kinds = [c["kind"] for c in collector.calls]
    assert kinds[-1] == "inspect" and kinds.count("rm") == 1
    assert engine.settled_cid == CID
    phases = [json.loads(line)["phase"] for line in open(receipt).readlines()]
    assert "attempt_settled" not in phases


def test_interrupted_receipt_failure_keeps_original_exception(
        comp, tmp_path, monkeypatch):
    collector = FakeCollector(comp, policy_doc_ok(comp),
                              state_doc=state_doc_ok(CID))
    collector.script["start"] = KeyboardInterrupt("original interruption")
    engine = make_engine(comp, collector)
    receipt = str(tmp_path / "receipt")
    original = qsm._write_receipt
    def fail_interrupted(path, doc, excl, **kwargs):
        if doc.get("phase") == "attempt_interrupted":
            raise OSError("interrupted receipt write also failed")
        return original(path, doc, excl, **kwargs)
    monkeypatch.setattr(qsm, "_write_receipt", fail_interrupted)
    with pytest.raises(KeyboardInterrupt):  # never the OSError
        qsm.execute_attempt(comp, engine, receipt)
    assert "stop" in [c["kind"] for c in collector.calls]


def test_full_raw_proof_recovery(comp, tmp_path):
    collector = FakeCollector(comp, policy_doc_ok(comp),
                              state_doc=state_doc_ok(CID),
                              verdict_out=verdict_bytes())
    engine = make_engine(comp, collector)
    receipt = str(tmp_path / "receipt")
    attempt = qsm.execute_attempt(comp, engine, receipt)
    doc = json.loads(open(receipt).readlines()[-1])
    probe = verdict_bytes()
    assert base64.b64encode(probe).decode() == doc["workload_output_b64"]
    assert doc["workload_output_sha256"] == hashlib.sha256(probe).hexdigest()
    by_kind = {}
    for entry in doc["engine_ledger"]:
        by_kind.setdefault(entry["kind"], []).append(entry)
    # Preflight, policy and state control outputs are retained raw and bounded.
    assert set(by_kind) == {"preflight_image", "preflight_info",
                            "preflight_version", "create", "policy", "start",
                            "state", "stop", "rm", "absence"}
    image_doc = json.loads(base64.b64decode(
        by_kind["preflight_image"][0]["stdout_b64"]).decode())
    assert image_doc == image_doc_ok()
    policy_doc = json.loads(base64.b64decode(
        by_kind["policy"][0]["stdout_b64"]).decode())
    assert policy_doc == policy_doc_ok(comp)
    state_entry = by_kind["state"][0]
    state_id, state = json.loads(base64.b64decode(state_entry["stdout_b64"]))
    assert state_id == CID and state["ExitCode"] == 0 and state["Running"] is False
    absence_entry = by_kind["absence"][0]
    out, err = absence_bytes(CID)
    assert base64.b64decode(absence_entry["stdout_b64"]) == out
    assert base64.b64decode(absence_entry["stderr_b64"]) == err
    assert absence_entry["returncode"] == 1
    for entry in doc["engine_ledger"]:
        raw = (base64.b64decode(entry["stdout_b64"])
               + base64.b64decode(entry["stderr_b64"]))
        assert entry["output_sha256"] == hashlib.sha256(raw).hexdigest()
        assert entry["bytes"] == len(raw) <= entry["cap_bytes"]
        assert 0 <= entry["started_offset_seconds"] <= 130.0
        assert entry["duration_seconds"] >= 0.0
        assert entry["deadline_seconds"] > 0.0
    assert attempt.cleanup_confirmed is True

# ---------------------------------------------------------------------------
# Workload outcomes, aggregate output cap, budgets and cleanup finiteness
# ---------------------------------------------------------------------------

def test_workload_timeout_cleans_and_is_not_confirmed(comp):
    t = comp.t
    collector = FakeCollector(comp, policy_doc_ok(comp),
                              state_doc=state_doc_ok(CID),
                              verdict_out=verdict_bytes())
    collector.script["start"] = res(t, None, verdict_bytes(), timed_out=True)
    engine = make_engine(comp, collector)
    attempt = run_attempt(comp, engine)
    assert attempt.execution_uncertain and not attempt.workload_confirmed
    assert attempt.state is t.AttemptState.CLEANED_FAILURE
    assert [c["kind"] for c in collector.calls].count("rm") == 1
    with pytest.raises(SourceContractError):
        qsm.validate_verdict(t, attempt)


def test_collector_error_cleans_known_id(comp):
    t = comp.t
    collector = FakeCollector(comp, policy_doc_ok(comp),
                              state_doc=state_doc_ok(CID))
    collector.script["start"] = OSError("collector crashed")
    engine = make_engine(comp, collector)
    attempt = run_attempt(comp, engine)
    assert "collector error" in attempt.workload_problem
    assert not attempt.workload_confirmed
    assert attempt.state is t.AttemptState.CLEANED_FAILURE
    assert [c["kind"] for c in collector.calls].count("rm") == 1


def test_nonzero_exit_not_confirmed(comp):
    t = comp.t
    collector = FakeCollector(comp, policy_doc_ok(comp),
                              state_doc=state_doc_ok(CID, ExitCode=3),
                              verdict_out=verdict_bytes())
    engine = make_engine(comp, collector)
    attempt = run_attempt(comp, engine)
    assert attempt.workload_returncode == 3
    assert attempt.state is t.AttemptState.CLEANED_FAILURE
    with pytest.raises(SourceContractError):
        qsm.validate_verdict(t, attempt)


def test_oomkilled_and_running_state_not_confirmed(comp):
    t = comp.t
    for over in ({"OOMKilled": True}, {"Running": True}):
        collector = FakeCollector(comp, policy_doc_ok(comp),
                                  state_doc=state_doc_ok(CID, **over))
        engine = make_engine(comp, collector)
        attempt = run_attempt(comp, engine)
        assert not attempt.workload_confirmed
        assert attempt.state in (t.AttemptState.CLEANED_FAILURE,
                                 t.AttemptState.CLEANUP_UNCERTAIN)
        with pytest.raises(SourceContractError):
            qsm.validate_verdict(t, attempt)


def test_cleanup_absence_not_proven_no_pass(comp):
    t = comp.t
    collector = FakeCollector(comp, policy_doc_ok(comp),
                              state_doc=state_doc_ok(CID),
                              verdict_out=verdict_bytes())
    generic = ("Error response from daemon: No such object: " + CID + "\n").encode()

    def executor(argv, *, deadline_seconds, output_cap_bytes):
        if argv[5] == "inspect" and len(argv) == 9:
            return res(t, 1, b"[]\n", generic, deadline=deadline_seconds,
                       cap=output_cap_bytes)
        return collector(argv, deadline_seconds=deadline_seconds,
                         output_cap_bytes=output_cap_bytes)

    engine = qsm.FixedQualificationEngine(comp.t, comp.plan, executor=executor,
                                          binding=BINDING_OK)
    attempt = run_attempt(comp, engine)
    assert attempt.cleanup_confirmed is False
    assert attempt.state is t.AttemptState.CLEANUP_UNCERTAIN
    assert "absence check failed" in attempt.detail
    with pytest.raises(SourceContractError):
        qsm.validate_verdict(t, attempt)


def test_aggregate_cap_includes_controls_and_reserves_cleanup(comp):
    t = comp.t
    collector = FakeCollector(comp, policy_doc_ok(comp),
                              state_doc=state_doc_ok(CID),
                              verdict_out=verdict_bytes())

    def executor(argv, *, deadline_seconds, output_cap_bytes):
        outcome = collector(argv, deadline_seconds=deadline_seconds,
                            output_cap_bytes=output_cap_bytes)
        if argv[5] != "start":
            return outcome
        inflated = b"x" * min(output_cap_bytes, 8192)
        return res(t, outcome.returncode, inflated, deadline=deadline_seconds,
                   cap=output_cap_bytes)

    engine = qsm.FixedQualificationEngine(comp.t, comp.plan, executor=executor,
                                          binding=BINDING_OK)
    attempt = run_attempt(comp, engine)
    # Cleanup phase = stop, rm and the final absence inspect only; the
    # preflight/policy/state controls run inside the workload-phase pool.
    workload = [c for c in collector.calls
                if c["kind"] in ("image", "info", "version", "create", "start")]
    workload += [c for c in collector.calls[:8] if c["kind"] == "inspect"]
    cleanup = [c for c in collector.calls if c["kind"] in ("stop", "rm")]
    cleanup.append(collector.calls[-1])
    assert collector.calls[-1]["kind"] == "inspect"
    assert max(c["cap"] for c in workload) <= TOTAL_OUTPUT_CAP_BYTES - CLEANUP_RESERVE_BYTES
    assert max(c["cap"] for c in cleanup) <= 1024
    assert sum(e.get("bytes", 0) for e in engine.ledger) <= TOTAL_OUTPUT_CAP_BYTES
    assert engine.ledger[-1]["bytes"] >= 1  # absence inspect retained raw bytes
    kinds = [c["kind"] for c in collector.calls]
    assert kinds.count("rm") == 1 and kinds[-1] == "inspect"
    assert attempt.cleanup_confirmed is True
    assert not any(e.get("error_type") == "malformed_engine_result"
                   for e in engine.ledger)


def test_workload_budget_exhaustion_still_cleans(comp, monkeypatch):
    t = comp.t
    times = {"now": 1000.0}
    monkeypatch.setattr(qsm.time, "monotonic", lambda: times["now"])
    collector = FakeCollector(comp, policy_doc_ok(comp),
                              state_doc=state_doc_ok(CID))

    def executor(argv, *, deadline_seconds, output_cap_bytes):
        outcome = collector(argv, deadline_seconds=deadline_seconds,
                            output_cap_bytes=output_cap_bytes)
        overrun = 45.0 if argv[5] == "create" else 0.0
        # The create client hangs far past its bounded deadline; the workload
        # phase budget is what must stop the start gate afterwards.
        times["now"] += deadline_seconds + overrun
        return outcome

    engine = qsm.FixedQualificationEngine(comp.t, comp.plan, executor=executor,
                                          binding=BINDING_OK)
    attempt = run_attempt(comp, engine)
    kinds = [c["kind"] for c in collector.calls]
    # image 10 + info 10 + version 10 + create 20 (+45 overrun) burns the 90s
    # workload phase; cleanup still gets its own <=10s slices and 1024B caps
    # inside the whole 130s envelope.
    assert kinds == ["image", "info", "version", "create", "stop", "rm", "inspect"]
    assert "start" not in kinds and "kill" not in kinds
    assert not attempt.workload_confirmed
    assert attempt.state is t.AttemptState.CLEANED_FAILURE
    assert attempt.cleanup_confirmed is True
    deadlines = {e["kind"]: e["deadline_seconds"] for e in engine.ledger}
    assert deadlines["create"] <= 20.0
    assert deadlines["stop"] <= 10.0 and deadlines["rm"] <= 10.0
    assert deadlines["absence"] <= 10.0
    for e in engine.ledger:
        if e["kind"] in ("stop", "rm", "absence"):
            assert e["cap_bytes"] <= 1024

# ---------------------------------------------------------------------------
# Verdict gate: strict one-document probe, failed required check never passes
# ---------------------------------------------------------------------------

def verdict_attempt(t, output, **over):
    fields = {"state": t.AttemptState.CLEANED_SUCCESS, "confirmed": True,
              "cleanup": True, "uncertain": False, "rc": 0, "problem": None,
              "recon": False}
    fields.update(over)
    return t.TransportAttempt(
        OPERATION_ID, CID, fields["state"], fields["recon"], "d", (),
        fields["confirmed"], fields["rc"], output, fields["problem"],
        fields["uncertain"], fields["cleanup"], "p" * 64)


def test_verdict_positive_exact(comp):
    t = comp.t
    qsm.validate_verdict(t, verdict_attempt(t, verdict_bytes()))
    qsm.validate_verdict(t, verdict_attempt(t, canonical(verdict_dict())))
    verdict = qsm.validate_verdict(t, verdict_attempt(t, verdict_bytes()))
    assert verdict == verdict_dict()


def test_failed_required_probe_never_passes(comp):
    t = comp.t
    failing = verdict_dict()
    failing["records"][0]["status"] = "FAIL"  # allowed_computation failed
    with pytest.raises(SourceContractError):
        qsm.validate_verdict(t, verdict_attempt(t, canonical(failing) + b"\n"))
    false_flag = verdict_dict()
    false_flag["mechanical_checks_passed"] = False
    with pytest.raises(SourceContractError):
        qsm.validate_verdict(t, verdict_attempt(t, canonical(false_flag) + b"\n"))
    inconclusive = verdict_dict()
    for record in inconclusive["records"]:
        if record["check"] == "public_egress":
            record["status"] = "INCONCLUSIVE"
    with pytest.raises(SourceContractError):
        qsm.validate_verdict(t, verdict_attempt(t, canonical(inconclusive) + b"\n"))
    exception = verdict_dict()
    exception["records"].append({"check": "probe_exception", "status": "FAIL",
                                 "exception_type": "ValueError"})
    with pytest.raises(SourceContractError):
        qsm.validate_verdict(t, verdict_attempt(t, canonical(exception) + b"\n"))


def test_verdict_negative_variants(comp):
    t = comp.t
    good = verdict_bytes()
    doc = verdict_dict()
    cases = [
        canonical(dict(doc, extra_key=1)),
        canonical({k: v for k, v in doc.items() if k != "records"}),
        canonical(dict(doc, schema="other.v1")),
        canonical(dict(doc, mechanical_checks_passed=False)),
        canonical(dict(doc, candidate_admission=True)),
        canonical(dict(doc, containment_qualified=True)),
        good,
        good,
        good,
        good,
        good,
        b"",
        good + b"trailing text",
        canonical(doc) + canonical(doc),
    ]
    overlays = [{}, {}, {}, {}, {}, {},
                {"confirmed": False}, {"cleanup": False}, {"rc": 1},
                {"uncertain": True}, {"state": t.AttemptState.CLEANUP_UNCERTAIN},
                {}, {}, {}]
    for output, over in zip(cases, overlays):
        with pytest.raises(SourceContractError):
            qsm.validate_verdict(t, verdict_attempt(t, output, **over))

    duplicate = verdict_dict()
    duplicate["records"][1] = dict(duplicate["records"][0])
    with pytest.raises(SourceContractError):
        qsm.validate_verdict(t, verdict_attempt(t, canonical(duplicate) + b"\n"))

    bad_skip = verdict_dict()
    bad_skip["records"][-1]["reason"] = "changed_reason"
    with pytest.raises(SourceContractError):
        qsm.validate_verdict(t, verdict_attempt(t, canonical(bad_skip) + b"\n"))

    extra_skip = verdict_dict()
    extra_skip["records"].append({"check": "extra_probe", "status": "SKIP",
                                  "reason": SKIP_REASON})
    with pytest.raises(SourceContractError):
        qsm.validate_verdict(t, verdict_attempt(t, canonical(extra_skip) + b"\n"))

    swapped = verdict_dict()
    swapped["records"][0], swapped["records"][1] = (swapped["records"][1],
                                                    swapped["records"][0])
    with pytest.raises(SourceContractError):
        qsm.validate_verdict(t, verdict_attempt(t, canonical(swapped) + b"\n"))


# ---------------------------------------------------------------------------
# Six reviewer red discriminators against the actual production functions
# ---------------------------------------------------------------------------

def test_reviewer_actual_container_id_not_image_digest(comp):
    doc = policy_doc_ok(comp)
    doc["Id"] = CID
    assert qsm._policy_mismatch(comp.plan, doc) is None


def test_reviewer_policy_image_and_name_are_bound(comp):
    doc = policy_doc_ok(comp)
    doc["Image"] = "sha256:" + "a" * 64
    doc["Name"] = "/unrelated"
    assert qsm._policy_mismatch(comp.plan, doc) is not None


def test_reviewer_cid_receipt_failure_blocks_start(comp, tmp_path, monkeypatch):
    collector = FakeCollector(comp, policy_doc_ok(comp),
                              state_doc=state_doc_ok(CID),
                              verdict_out=verdict_bytes())
    engine = make_engine(comp, collector)
    original = qsm._write_receipt
    def fail(path, doc, excl, **kwargs):
        if doc.get("phase") == "container_id_settled":
            raise OSError("reviewer simulated fsync failure")
        return original(path, doc, excl, **kwargs)
    monkeypatch.setattr(qsm, "_write_receipt", fail)
    attempt = qsm.execute_attempt(comp, engine, str(tmp_path / "receipt"))
    assert "start" not in [c["kind"] for c in collector.calls]
    assert attempt.cleanup_confirmed
    assert not attempt.workload_confirmed


def test_reviewer_known_cid_sink_interruption_cleans(comp, tmp_path, monkeypatch):
    collector = FakeCollector(comp, policy_doc_ok(comp),
                              state_doc=state_doc_ok(CID))
    engine = make_engine(comp, collector)
    original = qsm._write_receipt
    def interrupt(path, doc, excl, **kwargs):
        if doc.get("phase") == "container_id_settled":
            raise KeyboardInterrupt(
                "reviewer interrupted immediately after known CID")
        return original(path, doc, excl, **kwargs)
    monkeypatch.setattr(qsm, "_write_receipt", interrupt)
    with pytest.raises(KeyboardInterrupt):
        qsm.execute_attempt(comp, engine, str(tmp_path / "receipt"))
    assert engine.settled_cid == CID
    kinds = [c["kind"] for c in collector.calls]
    assert "start" not in kinds
    assert "stop" in kinds and "rm" in kinds


def test_reviewer_image_type_state_argv_not_whitelisted(comp):
    collector = FakeCollector(comp, policy_doc_ok(comp),
                              state_doc=state_doc_ok(CID))
    engine = make_engine(comp, collector)
    engine.run(comp.t.build_create_argv(comp.plan), deadline_seconds=20,
               output_cap_bytes=16384)
    altered = (qsm.DOCKER_BINARY, "inspect", "--type", "image", "--format",
               qsm._STATE_INSPECT_FORMAT, CID)
    with pytest.raises(comp.t.TransportPlanError):
        engine.run(altered, deadline_seconds=10, output_cap_bytes=16384)
    assert all("image" != c["kind"] or len(c["logical_argv"]) != 7
               for c in collector.calls)


def test_reviewer_receipt_retains_probe_and_absence_raw_evidence(
        comp, tmp_path):
    collector = FakeCollector(comp, policy_doc_ok(comp),
                              state_doc=state_doc_ok(CID),
                              verdict_out=verdict_bytes())
    engine = make_engine(comp, collector)
    path = tmp_path / "receipt"
    attempt = qsm.execute_attempt(comp, engine, str(path))
    assert attempt.cleanup_confirmed
    doc = json.loads(path.read_text().splitlines()[-1])
    def leaf_strings(node):
        if isinstance(node, str):
            yield node
        elif isinstance(node, dict):
            for value in node.values():
                yield from leaf_strings(value)
        elif isinstance(node, list):
            for value in node:
                yield from leaf_strings(value)
    retained = list(leaf_strings(doc))
    actual_probe = verdict_bytes()
    assert (actual_probe.decode() in retained
            or base64.b64encode(actual_probe).decode() in retained)
    expected_out, expected_err = absence_bytes(CID)
    assert (expected_err.decode() in retained
            or base64.b64encode(expected_err).decode() in retained
            or base64.b64encode(expected_out + expected_err).decode() in retained)

# ---------------------------------------------------------------------------
# Selected-runtime derivative: rf-runsc fixed frontend
# ---------------------------------------------------------------------------

def manifest_ok():
    members = {}
    for name, size in qrs.MEMBER_SPECS.items():
        digest = (qrs.RUNSC_BINARY_SHA256 if name == "runsc"
                  else hashlib.sha256(name.encode()).hexdigest())
        members[name] = {"size": size, "sha256": digest}
    return {"manifest_schema": "rf.qualification_runsc.installer_receipt.v1",
            "root": ROOT_ID, "installer_operation": "rf-runsc-installer-01a137ac-v1",
            "archive_sha256": qrs.ARCHIVE_SHA256,
            "consumer_path": qrs.CONSUMER_PATH, "runtime_name": "rf-runsc",
            "runtime_args": ["--platform=systrap", "--network=none",
                             "--oci-seccomp"],
            "config_path": "/etc/docker/daemon.json",
            "config_sha256": hashlib.sha256(b"config").hexdigest(),
            "actual_hostname": BINDING_OK["expected_hostname"],
            "status": "installed", "members": members,
            "pin_adjudication_sha256": qrs.PIN_ADJUDICATION_SHA256}


def manifest_file(tmp_path, doc):
    body = json.dumps(doc, sort_keys=True, separators=(",", ":")).encode()
    path = tmp_path / "installer.json"
    path.write_bytes(body)
    return str(path), hashlib.sha256(body).hexdigest()


def test_runsc_dryrun_plan_and_budget(sources):
    tpath, ppath = sources
    comp = qrs.build_runsc_composition(tpath, ppath)
    engine = qrs.RunscQualificationEngine(comp.t, comp.plan, executor=None)
    d = engine.describe()
    assert d["operation"] == qrs.OPERATION_ID
    assert d["selected_runtime"] == "rf-runsc"
    assert d["runtime_flag"] == "--runtime=rf-runsc"
    assert d["runtime_args"] == ["--platform=systrap", "--network=none",
                                 "--oci-seccomp"]
    assert d["create_addendum"]["name"] == qrs.CONTAINER_NAME
    limits = d["limits"]
    assert (limits["uid"], limits["gid"]) == (65534, 65534)
    assert limits["pids_limit"] == 64 and limits["memory_bytes"] == 256 * 1024 * 1024
    assert limits["cpus"] == 0.5 and limits["wall_clock_seconds"] == 30.0
    assert limits["output_cap_bytes"] == 16384 and limits["tmpfs_bytes"] == 1048576
    assert limits["stop_timeout_seconds"] == 2.0
    assert "candidate-capacity claim" in d["accounting_limitation"]
    assert d["s02_note"] == qrs.S02_NOTE
    assert d["member_specs_bytes"] == qrs.MEMBER_SPECS
    assert d["archive_sha256"] == qrs.ARCHIVE_SHA256
    assert d["execute_authorized"] is False
    assert d["candidate_admission"] is False and d["containment_qualified"] is False
    # The base engine stays untouched by the derivative preset.
    base = qsm.FixedQualificationEngine(comp.t, comp.plan, executor=None)
    assert base.describe()["selected_runtime"] is None
    assert not any(item.startswith("--runtime")
                   for item in base.effective_create_argv())


def test_runsc_runtime_policy_format_requests_hostconfig_runtime():
    assert '"Runtime":{{json .HostConfig.Runtime}}' in qrs._RUNSC_POLICY_FORMAT
    assert '"HC":{"Runtime":' in qrs._RUNSC_POLICY_FORMAT
    assert '"Runtime"' not in qsm._POLICY_FORMAT


def test_runsc_create_labels_preserve_root_and_match_inspected_policy(runsc_comp):
    engine = qrs.RunscQualificationEngine(runsc_comp.t, runsc_comp.plan,
                                         executor=None)
    argv = engine.effective_create_argv()
    pairs = [argv[i + 1].split("=", 1) for i, value in enumerate(argv)
             if value == "--label"]
    # Model Docker's final key/value map from the actual create arguments,
    # rather than supplying an independent idealized inspect fixture.
    actual_labels = dict(pairs)
    assert len(actual_labels) == len(pairs) == 2
    assert actual_labels == {
        ROOT_LABEL_KEY: ROOT_ID,
        RUN_LABEL_KEY: engine.operation_id,
    }
    policy = runsc_policy_doc_ok(runsc_comp)
    policy["Cfg"]["Labels"] = actual_labels
    assert qsm._policy_mismatch(runsc_comp.plan, policy,
                                **engine._policy_expectations()) is None


def test_runsc_exact_create_and_inspected_runtime(runsc_comp):
    collector = FakeCollector(runsc_comp, runsc_policy_doc_ok(runsc_comp),
                              state_doc=state_doc_ok(CID),
                              verdict_out=verdict_bytes(),
                              policy_format=qrs._RUNSC_POLICY_FORMAT)
    engine = make_runsc_engine(runsc_comp, collector)
    attempt = run_attempt(runsc_comp, engine)
    assert attempt.state is runsc_comp.t.AttemptState.CLEANED_SUCCESS
    create = collector.calls[3]
    assert create["kind"] == "create"
    assert create["logical_argv"].count("--runtime=rf-runsc") == 1
    assert create["logical_argv"][4] == "--runtime=rf-runsc"
    assert create["logical_argv"][3] == "create"
    policy = collector.calls[4]
    assert policy["logical_argv"][7] == qrs._RUNSC_POLICY_FORMAT
    assert policy["logical_argv"][3:7] == ["inspect", "--type", "container", "--format"]
    assert engine.settled_cid == CID
    qsm.validate_verdict(runsc_comp.t, attempt)


def test_runsc_runtime_gate_blocks_start_on_wrong_hostconfig(runsc_comp):
    t = runsc_comp.t
    for wrong in ("runc", "", None):
        doc = runsc_policy_doc_ok(runsc_comp)
        if wrong is None:
            del doc["HC"]["Runtime"]
        else:
            doc["HC"]["Runtime"] = wrong
        collector = FakeCollector(runsc_comp, doc,
                                  state_doc=state_doc_ok(CID),
                                  verdict_out=verdict_bytes(),
                                  policy_format=qrs._RUNSC_POLICY_FORMAT)
        engine = make_runsc_engine(runsc_comp, collector)
        attempt = run_attempt(runsc_comp, engine)
        assert "start" not in [c["kind"] for c in collector.calls]
        assert not attempt.workload_confirmed
        assert attempt.cleanup_confirmed is True
        with pytest.raises(SourceContractError):
            qsm.validate_verdict(t, attempt)


def test_runsc_manifest_positive_and_zero_docker_calls(runsc_comp, tmp_path):
    path, sha = manifest_file(tmp_path, manifest_ok())
    manifest = qrs.load_installer_manifest(path, sha, BINDING_OK)
    assert manifest["runtime_name"] == "rf-runsc"
    assert set(manifest["members"]) == set(qrs.MEMBER_SPECS)


def test_runsc_manifest_mismatch_stops_before_any_mutation(runsc_comp, tmp_path):
    good = manifest_ok()
    bad_cases = [
        {},
        dict(good, manifest_schema="rf.other.v1"),
        dict(good, status="draft"),
        dict(good, archive_sha256="0" * 64),
        dict(good, consumer_path="/usr/local/bin/runsc"),
        dict(good, runtime_args=["--platform=systrap", "--network=none"]),
        dict(good, runtime_name="runc"),
        dict(good, config_sha256="0" * 64),
        dict(good, actual_hostname="somewhere-else"),
        dict(good, pin_adjudication_sha256="1" * 64),
        dict(good, root="01a00000-0000-0000-0000-000000000000"),
    ]
    missing = dict(good)
    missing["members"] = {k: v for k, v in good["members"].items()
                          if k != "gvisor-bin/runsc-metric-server"}
    bad_cases.append(missing)
    wrong_size = dict(good)
    wrong_size["members"] = dict(good["members"])
    wrong_size["members"]["runsc"] = {"size": 1, "sha256": qrs.RUNSC_BINARY_SHA256}
    bad_cases.append(wrong_size)
    placeholder = dict(good)
    placeholder["members"] = dict(good["members"])
    placeholder["members"]["gvisor-bin/gvisor_sentry"] = {
        "size": 52149808, "sha256": "0" * 64}
    bad_cases.append(placeholder)
    wrong_binary = dict(good)
    wrong_binary["members"] = dict(good["members"])
    wrong_binary["members"]["runsc"] = {"size": 109966750, "sha256": "2" * 64}
    bad_cases.append(wrong_binary)
    for doc in bad_cases:
        path, sha = manifest_file(tmp_path, doc)
        with pytest.raises(SourceContractError):
            qrs.load_installer_manifest(path, sha, BINDING_OK)
    collector = FakeCollector(runsc_comp, runsc_policy_doc_ok(runsc_comp),
                              policy_format=qrs._RUNSC_POLICY_FORMAT)
    make_runsc_engine(runsc_comp, collector)  # engine may exist but is never run
    assert collector.calls == []


def test_runsc_installed_bundle_bytes_verified_privately(runsc_comp, monkeypatch):
    manifest = manifest_ok()
    calls = []
    from types import SimpleNamespace
    monkeypatch.setattr(qrs.os, "lstat", lambda p: SimpleNamespace(
        st_mode=0o40755, st_uid=0, st_gid=0))
    root = os.path.dirname(qrs.CONSUMER_PATH)
    monkeypatch.setattr(qrs.os, "listdir", lambda p: ["runsc", "gvisor-bin"] if p == root
        else [n.split("/", 1)[1] for n in qrs.MEMBER_SPECS if n != "runsc"])
    def fake_hash(path, size, deadline, *, config=False):
        calls.append((path, size, config))
        return manifest["config_sha256"] if config else manifest["members"][os.path.relpath(path, root)]["sha256"]
    monkeypatch.setattr(qrs, "_sha256_file", fake_hash)
    qrs.verify_installed_bundle(manifest)
    assert len(calls) == 7
    assert calls[:-1] == [(os.path.join(root, n), size, False) for n, size in qrs.MEMBER_SPECS.items()]
    assert calls[-1] == ("/etc/docker/daemon.json", 262144, True)
    monkeypatch.setattr(qrs, "_sha256_file", lambda *a, **kw: "3" * 64)
    with pytest.raises(SourceContractError):
        qrs.verify_installed_bundle(manifest)


def test_runsc_cli_dryrun_and_gate(sources, capsys):
    tpath, ppath = sources
    assert qrs.main(["--transport", tpath, "--probe", ppath]) == 0
    doc = json.loads(capsys.readouterr().out)
    assert doc["selected_runtime"] == "rf-runsc"
    assert doc["candidate_admission"] is False
    assert qrs.main(["--transport", tpath, "--probe", ppath, "--execute"]) == 2
    refusal = json.loads(capsys.readouterr().err)
    assert refusal["refusal"] == "RunscGateIncomplete"
    assert refusal["candidate_admission"] is False
