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
    engine = work.FixedWorkloadEngine("w01", raw, binding=dict(BINDING_OK))
    comp = SimpleNamespace(t=work.transport, plan=engine._plan)
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
    assert description["candidate_admission"] is False
    assert description["containment_qualified"] is False
    assert description["execute_authorized"] is False
    assert engine._plan.argv[-1] not in json.dumps(description)


def test_dormant_without_executor_does_not_write(prepared, tmp_path):
    engine, collector = prepared
    engine._executor = None
    path = tmp_path / "receipt.jsonl"
    with pytest.raises(work.transport.TransportDormantError):
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
            work.transport, 0, b"partial", deadline=deadline, cap=cap,
            timed_out=failure == "timeout", output_truncated=failure == "overflow")
    path = tmp_path / "receipt.jsonl"
    result = work.execute_prepared_workload(engine, path)
    assert result.cleanup_confirmed and not result.workload_confirmed
    assert result.state is work.transport.AttemptState.CLEANED_FAILURE
    assert documents(path)[-1]["workload_problem"]


def test_unknown_create_never_starts_or_cleans_a_guessed_id(prepared, tmp_path):
    engine, collector = prepared
    collector.script["create"] = lambda deadline, cap: res(
        work.transport, None, b"", deadline=deadline, cap=cap, timed_out=True)
    path = tmp_path / "receipt.jsonl"
    result = work.execute_prepared_workload(engine, path)
    assert result.container_id is None and result.execution_uncertain
    assert not any(c["kind"] in {"start", "stop", "kill", "rm"} for c in collector.calls)
    before = len(collector.calls)
    with pytest.raises(work.transport.TransportStateError):
        work.execute_prepared_workload(engine, tmp_path / "replacement.jsonl")
    assert len(collector.calls) == before


def test_prior_receipt_refuses_before_docker(prepared, tmp_path):
    engine, collector = prepared
    path = tmp_path / "receipt.jsonl"
    path.write_bytes(b"old unresolved receipt\n")
    with pytest.raises(FileExistsError):
        work.execute_prepared_workload(engine, path)
    assert not collector.calls and path.read_bytes() == b"old unresolved receipt\n"
    with pytest.raises(work.transport.TransportStateError):
        work.execute_prepared_workload(engine, tmp_path / "replacement.jsonl")


def test_permission_refusal_freezes_commands_and_receipt_publication(prepared, tmp_path):
    engine, collector = prepared
    collector.script["create"] = PermissionError("fixture refusal")
    path = tmp_path / "receipt.jsonl"
    with pytest.raises(work.transport.TransportPermissionRefusal):
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
    with pytest.raises(work.transport.TransportStateError):
        engine._budget("start", "workload", 5.0)
    assert engine._budget("rm", "cleanup", 60.0) == 10.0
    engine._bytes_used = 61440
    with pytest.raises(work.transport.TransportStateError):
        engine._cap("start", "workload", 65536)
    assert engine._cap("rm", "cleanup", 65536) == 1024


def test_completed_engine_cannot_run_again(prepared, tmp_path):
    engine, collector = prepared
    work.execute_prepared_workload(engine, tmp_path / "first.jsonl")
    before = len(collector.calls)
    with pytest.raises(work.transport.TransportStateError):
        work.execute_prepared_workload(engine, tmp_path / "second.jsonl")
    assert len(collector.calls) == before
