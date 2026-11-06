"""Drive the real fixed frontend/transport with bounded fake Docker responses."""
import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

import fixed_workload_engine as work
from test_qualification_smoke import (
    BINDING_OK, CID, FakeCollector, policy_doc_ok, res, sources, state_doc_ok,
)


@pytest.fixture(autouse=True)
def no_process(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("physical process forbidden in source test")
    monkeypatch.setattr(subprocess, "Popen", forbidden)


@pytest.fixture
def prepared(sources):
    # Read as bytes only; never import or execute the workload.
    raw = (Path(__file__).parents[2] / "w01_boundary.py").read_bytes()
    engine = work.FixedWorkloadEngine("w01", raw, transport_path=sources[0], binding=dict(BINDING_OK))
    comp = SimpleNamespace(t=engine._t, plan=engine._plan)
    policy = policy_doc_ok(comp)
    policy["Name"] = "/" + engine.operation_id
    policy["Cfg"]["Labels"][work.smoke.RUN_LABEL_KEY] = engine.operation_id
    policy["HC"].update(Runtime="rf-runsc", PidsLimit=128,
                         Memory=268435456, MemorySwap=268435456,
                         Tmpfs={"/tmp": "rw,noexec,nosuid,size=8388608,mode=1777"})
    collector = FakeCollector(comp, policy, state_doc=state_doc_ok(CID),
                              verdict_out=b'{"guest_report":"untrusted"}\n',
                              policy_format=work.runsc._RUNSC_POLICY_FORMAT)
    engine._executor = collector  # Test-only explicit injected fake, no launcher.
    return engine, collector


def documents(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def test_exact_fixed_create_and_redacted_description(prepared):
    engine, _ = prepared
    args = engine.effective_create_argv()
    assert args[5:7] == ("create", "--runtime=rf-runsc")
    assert args.count("--runtime=rf-runsc") == 1
    assert args[args.index("--tmpfs") + 1] == "/tmp:rw,noexec,nosuid,size=8388608,mode=1777"
    assert args[args.index("--name") + 1] == "rf-containment-w01-01a1333c-v1"
    description = engine.describe()
    assert description["aggregate_capture_bytes"] == 65536
    assert description["cleanup_reserved_bytes"] == 4096
    assert description["transport_sha256"] == work.smoke.TRANSPORT_SHA256
    assert sum(description["cleanup_command_max_seconds"].values()) < 30
    assert description["candidate_admission"] is False
    assert description["containment_qualified"] is False
    assert description["execute_authorized"] is False
    assert engine._plan.argv[-1] not in json.dumps(description)


def test_dormant_without_executor_does_not_write(prepared, tmp_path):
    engine, collector = prepared
    engine._executor = None
    path = tmp_path / "receipt.jsonl"
    with pytest.raises(engine._t.TransportDormantError):
        work.execute_prepared_workload(engine, path)
    assert not path.exists() and not collector.calls


def test_success_has_same_cid_cleanup_and_false_qualification(prepared, tmp_path):
    engine, collector = prepared
    path = tmp_path / "receipt.jsonl"
    result = work.execute_prepared_workload(engine, path)
    assert result.cleanup_confirmed and result.workload_confirmed
    assert result.container_id == CID
    rows = documents(path)
    assert [row["phase"] for row in rows] == [
        "pre_create", "container_id_settled", "attempt_settled"]
    assert all(row["candidate_admission"] is False and row["containment_qualified"] is False
               for row in rows)
    assert all(row["transport_sha256"] == work.smoke.TRANSPORT_SHA256 for row in rows)
    assert rows[-1]["workload_output_bytes"] == len(result.workload_output)
    starts = [c for c in collector.calls if c["kind"] == "start"]
    assert len(starts) == 1 and starts[0]["deadline"] <= 5
    assert collector.calls[-1]["kind"] == "inspect"
    assert len(path.read_bytes()) <= work.MAX_RECEIPT_BYTES


@pytest.mark.parametrize("failure", ["timeout", "overflow", "nonzero"])
def test_failed_workload_is_not_erased_by_successful_cleanup(prepared, tmp_path, failure):
    engine, collector = prepared
    if failure == "nonzero":
        collector.state_doc = state_doc_ok(CID, ExitCode=4)
    else:
        collector.script["start"] = lambda deadline, cap: res(
            engine._t, 0, b"partial", deadline=deadline, cap=cap,
            timed_out=failure == "timeout", output_truncated=failure == "overflow")
    path = tmp_path / "receipt.jsonl"
    result = work.execute_prepared_workload(engine, path)
    assert result.cleanup_confirmed and not result.workload_confirmed
    assert result.state is engine._t.AttemptState.CLEANED_FAILURE
    assert documents(path)[-1]["workload_problem"]


def test_unknown_create_never_starts_or_cleans_a_guessed_id(prepared, tmp_path):
    engine, collector = prepared
    collector.script["create"] = lambda deadline, cap: res(
        engine._t, None, b"", deadline=deadline, cap=cap, timed_out=True)
    path = tmp_path / "receipt.jsonl"
    result = work.execute_prepared_workload(engine, path)
    assert result.container_id is None and result.execution_uncertain
    assert not any(c["kind"] in {"start", "stop", "kill", "rm"} for c in collector.calls)
    before = len(collector.calls)
    with pytest.raises(engine._t.TransportStateError):
        work.execute_prepared_workload(engine, tmp_path / "replacement.jsonl")
    assert len(collector.calls) == before


def test_prior_receipt_refuses_before_docker(prepared, tmp_path):
    engine, collector = prepared
    path = tmp_path / "receipt.jsonl"
    path.write_bytes(b"old unresolved receipt\n")
    with pytest.raises(FileExistsError):
        work.execute_prepared_workload(engine, path)
    assert not collector.calls and path.read_bytes() == b"old unresolved receipt\n"
    with pytest.raises(engine._t.TransportStateError):
        work.execute_prepared_workload(engine, tmp_path / "replacement.jsonl")


def test_permission_refusal_freezes_commands_and_receipt_publication(prepared, tmp_path):
    engine, collector = prepared
    collector.script["create"] = PermissionError("fixture refusal")
    path = tmp_path / "receipt.jsonl"
    with pytest.raises(engine._t.TransportPermissionRefusal):
        work.execute_prepared_workload(engine, path)
    assert [x["phase"] for x in documents(path)] == ["pre_create"]
    assert collector.calls[-1]["kind"] == "create" and engine.frozen


def test_wrong_created_policy_cleans_same_cid_without_start(prepared, tmp_path):
    engine, collector = prepared
    collector.policy_doc["HC"]["PidsLimit"] = 0
    result = work.execute_prepared_workload(engine, tmp_path / "receipt.jsonl")
    assert not result.workload_confirmed and result.cleanup_confirmed
    assert not any(c["kind"] == "start" for c in collector.calls)


def test_cid_persistence_failure_cleans_before_start(prepared, tmp_path, monkeypatch):
    engine, collector = prepared
    original = work.smoke._write_receipt
    def fail_cid(path, doc, *args, **kwargs):
        if doc["phase"] == "container_id_settled":
            raise OSError("fixture full disk")
        return original(path, doc, *args, **kwargs)
    monkeypatch.setattr(work.smoke, "_write_receipt", fail_cid)
    result = work.execute_prepared_workload(engine, tmp_path / "receipt.jsonl")
    assert not result.workload_confirmed and result.cleanup_confirmed
    assert not any(c["kind"] == "start" for c in collector.calls)


def test_interruption_preserves_original_and_known_cid_cleanup(prepared, tmp_path):
    engine, collector = prepared
    collector.script["start"] = KeyboardInterrupt()
    path = tmp_path / "receipt.jsonl"
    with pytest.raises(KeyboardInterrupt):
        work.execute_prepared_workload(engine, path)
    assert collector.calls[-1]["kind"] == "inspect"
    assert documents(path)[-1]["phase"] == "attempt_interrupted"


def test_work_budget_preserves_cleanup_reserve(prepared, monkeypatch):
    engine, _ = prepared
    engine._t0 = 100.0
    monkeypatch.setattr(work.time, "monotonic", lambda: 190.0)
    with pytest.raises(engine._t.TransportStateError):
        engine._budget("start", "workload", 5.0)
    assert engine._budget("rm", "cleanup", 60.0) == 7.0
    engine._bytes_used = 61440
    with pytest.raises(engine._t.TransportStateError):
        engine._cap("start", "workload", 65536)
    assert engine._cap("rm", "cleanup", 65536) == 1024


def test_completed_engine_cannot_run_again(prepared, tmp_path):
    engine, collector = prepared
    work.execute_prepared_workload(engine, tmp_path / "first.jsonl")
    before = len(collector.calls)
    with pytest.raises(engine._t.TransportStateError):
        work.execute_prepared_workload(engine, tmp_path / "second.jsonl")
    assert len(collector.calls) == before


def test_cleanup_four_command_path_fits_reserved_clock(prepared, tmp_path, monkeypatch):
    engine, collector = prepared
    clock = [100.0]
    monkeypatch.setattr(work.time, "monotonic", lambda: clock[0])
    original = collector._default
    write = work.smoke._write_receipt

    def reserve_clock(path, doc, *args, **kwargs):
        result = write(path, doc, *args, **kwargs)
        if doc["phase"] == "pre_create":
            clock[0] += 50.0  # Real receipt work belongs to the whole budget.
        return result

    monkeypatch.setattr(work.smoke, "_write_receipt", reserve_clock)

    def bounded(argv, kind, deadline, cap):
        # Exhaust work time, then exercise the longest cleanup path, including
        # stop failure followed by kill. Every collector obeys its ceiling.
        clock[0] += deadline
        if kind == "stop":
            return res(engine._t, 1, deadline=deadline, cap=cap)
        return original(argv, kind, deadline, cap)

    collector._default = bounded
    result = work.execute_prepared_workload(engine, tmp_path / "receipt.jsonl")
    assert result.cleanup_confirmed
    assert not result.workload_confirmed
    assert [c["kind"] for c in collector.calls[-4:]] == ["stop", "kill", "rm", "inspect"]
    assert clock[0] <= 220.0


def test_operation_identity_cannot_change_after_description(prepared):
    engine, _ = prepared
    before = engine.describe()
    for attr in ("operation_id", "container_name", "run_label"):
        with pytest.raises(AttributeError):
            setattr(engine, attr, "different-operation")
    assert engine.describe() == before


def test_incomplete_binding_refused_before_any_executor_call(sources):
    raw = (Path(__file__).parents[2] / "w01_boundary.py").read_bytes()
    binding = dict(BINDING_OK)
    del binding["expected_hostname"]
    with pytest.raises(work.smoke.BindingMismatch):
        work.FixedWorkloadEngine("w01", raw, transport_path=sources[0], binding=binding)


def test_unreceipted_direct_create_refuses_before_preflight(prepared):
    engine, collector = prepared
    with pytest.raises(engine._t.TransportStateError):
        engine.run(engine._t.build_create_argv(engine._plan),
                   deadline_seconds=10, output_cap_bytes=65536)
    assert not collector.calls


def test_changed_transport_bytes_refuse_before_import(sources):
    path = Path(sources[0])
    path.write_bytes(path.read_bytes() + b'\nraise AssertionError("must not import")\n')
    raw = (Path(__file__).parents[2] / "w01_boundary.py").read_bytes()
    with pytest.raises(work.smoke.SourceContractError, match="expected pinned"):
        work.FixedWorkloadEngine("w01", raw, transport_path=str(path), binding=dict(BINDING_OK))


def test_pinned_lifecycle_ignores_importable_lookalike(prepared, tmp_path, monkeypatch):
    engine, _ = prepared
    assert engine._t is not work.plans.transport
    def forbidden(*args, **kwargs):
        raise AssertionError("unverified lifecycle was used")
    monkeypatch.setattr(work.plans.transport, "TransportOrchestrator", forbidden)
    monkeypatch.delattr(work.plans.transport, "parse_container_absence")
    # The module was compiled from verified bytes, so changing its former
    # source file also cannot silently change the lifecycle during execution.
    Path(engine._t.__file__).write_bytes(b'raise AssertionError("not pinned")\n')
    result = work.execute_prepared_workload(engine, tmp_path / "receipt.jsonl")
    assert result.cleanup_confirmed


def test_execution_plan_and_identity_also_use_verified_lifecycle(sources, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("unverified plan or identity implementation was used")
    monkeypatch.setattr(work.plans.transport, "TransportPlan", forbidden)
    monkeypatch.setattr(work.plans.transport, "plan_identity", forbidden)
    raw = (Path(__file__).parents[2] / "w01_boundary.py").read_bytes()
    engine = work.FixedWorkloadEngine("w01", raw, transport_path=sources[0], binding=dict(BINDING_OK))
    assert engine._plan.pids_limit == 128
    assert engine.describe()["plan_sha256"] == engine._t.plan_identity(engine._plan)


@pytest.mark.parametrize("key,value", [
    ("expected_uid", True), ("expected_gid", 0), ("expected_hostname", ""),
    ("client_config_dir", "/private\x00bad"), ("client_config_dir", "relative"),
    ("client_config_sha256", "0" * 64), ("image_receipt_sha256", "invalid"),
    ("docker_endpoint", "tcp://unapproved:2375"),
])
def test_invalid_binding_refuses_early(sources, key, value):
    raw = (Path(__file__).parents[2] / "w01_boundary.py").read_bytes()
    binding = dict(BINDING_OK, **{key: value})
    with pytest.raises(work.smoke.BindingMismatch):
        work.FixedWorkloadEngine("w01", raw, transport_path=sources[0], binding=binding)


def test_binding_copy_cannot_be_changed_through_caller(sources):
    raw = (Path(__file__).parents[2] / "w01_boundary.py").read_bytes()
    binding = dict(BINDING_OK)
    engine = work.FixedWorkloadEngine("w01", raw, transport_path=sources[0], binding=binding)
    binding["expected_hostname"] = "different-host"
    assert engine._binding["expected_hostname"] == BINDING_OK["expected_hostname"]
    engine._binding["expected_hostname"] = "different-host"
    assert engine._binding["expected_hostname"] == BINDING_OK["expected_hostname"]
    with pytest.raises(AttributeError):
        engine._binding = binding


def test_cid_sink_alone_cannot_bypass_exclusive_receipt(prepared):
    engine, collector = prepared
    engine.set_cid_sink(lambda cid: None)
    with pytest.raises(engine._t.TransportStateError, match="receipt required"):
        engine.run(engine._t.build_create_argv(engine._plan),
                   deadline_seconds=10, output_cap_bytes=65536)
    assert not collector.calls
