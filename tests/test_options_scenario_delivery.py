"""Actual local endpoints, no SSH/provider/storage/runtime effect."""
from dataclasses import asdict
import io
import json
import os
from pathlib import Path
import sys

import pytest

from scripts import deliver_options_scenario_source as delivery
from tests.test_options_scenario_capture import world


def setup(tmp_path):
    h = world(with_moves=False)
    request = {"operation_id": "10000000-0000-4000-8000-000000000001", "descriptor": asdict(h.descriptor_owner)}
    origin = tmp_path / "native"; origin.mkdir(mode=0o700)
    (origin / "gex").mkdir(mode=0o700)
    (origin / "gex/SPY.json").write_bytes(h.gex_bytes)
    target = tmp_path / "private"; target.mkdir(mode=0o700)
    (target / "gex").mkdir(mode=0o700)
    def call(path, uid):
        return lambda action, request, raw=b"": delivery.endpoint(
            {"action": action, "request": request, "directory": str(path), "expected_uid": uid}, io.BytesIO(raw))
    return h, request, origin, target, call(origin, None), call(target, os.geteuid())


def test_actual_source_endpoint_to_private_arrival_exact_bytes_and_no_save(tmp_path):
    h, request, origin, target, src, dst = setup(tmp_path)
    records = []
    result = delivery.deliver(request, src, dst, record=records.append)
    assert result == delivery.receipt(request, "arrived", save_performed=False)
    assert records == [delivery.receipt(request, "effect_unknown"), result]
    assert (target / "gex/SPY.json").read_bytes() == h.gex_bytes
    assert dst("inspect", request) == delivery.receipt(request, "present_exact", save_performed=False)
    assert not h.s3.log and not h.saves
    assert delivery.deliver(request, src, dst, record=records.append)["status"] == "not_delivered"


@pytest.mark.parametrize("kind", ["uid", "root_public", "leaf_public", "symlink", "existing", "missing"])
def test_destination_refuses_before_native_export(tmp_path, kind):
    h, request, origin, target, src, dst = setup(tmp_path)
    if kind == "uid":
        dst = lambda action, req: delivery.endpoint({"action": action, "request": req, "directory": str(target), "expected_uid": os.geteuid() + 1}, io.BytesIO())
    elif kind == "root_public": target.chmod(0o755)
    elif kind == "leaf_public": (target / "gex").chmod(0o750)
    elif kind == "symlink":
        (target / "gex").rmdir(); (target / "gex").symlink_to(origin / "gex")
    elif kind == "existing": (target / "gex/SPY.json").write_bytes(h.gex_bytes)
    else: (target / "gex").rmdir()
    result = delivery.deliver(request, lambda *args: pytest.fail("no source IO"), dst, record=lambda x: None)
    assert result["status"] == "not_delivered"
    assert (origin / "gex/SPY.json").read_bytes() == h.gex_bytes


def test_changed_source_refuses_without_arrival(tmp_path):
    h, request, origin, target, src, dst = setup(tmp_path)
    (origin / "gex/SPY.json").write_bytes(h.gex_bytes + b" ")
    assert delivery.deliver(request, src, dst, record=lambda x: None)["status"] == "not_delivered"
    assert not list((target / "gex").iterdir())


def test_write_response_lost_is_unknown_then_read_only_exact_inspection(tmp_path):
    h, request, origin, target, src, dst = setup(tmp_path)
    calls = []; records = []
    def lost(action, req, raw=b""):
        calls.append(action)
        result = dst(action, req, raw)
        if action == "arrive": raise TimeoutError("lost after actual commit")
        return result
    assert delivery.deliver(request, src, lost, record=records.append)["status"] == "effect_unknown"
    assert calls == ["preflight", "arrive"]
    assert dst("inspect", request)["status"] == "present_exact"
    assert records == [delivery.receipt(request, "effect_unknown")] * 2


def test_journal_failure_prevents_write_dispatch(tmp_path):
    h, request, origin, target, src, dst = setup(tmp_path)
    def broken(value): raise OSError("disk full")
    with pytest.raises(OSError): delivery.deliver(request, src, dst, record=broken)
    assert not list((target / "gex").iterdir())


def test_prequalified_directory_inode_survives_path_swap(tmp_path, monkeypatch):
    h, request, origin, target, src, dst = setup(tmp_path)
    original = delivery.arrival.arrive_gex_source
    held = tmp_path / "held"
    def swap(*args, **kwargs):
        target.rename(held)
        target.mkdir(mode=0o755); (target / "gex").mkdir(mode=0o755)
        return original(*args, **kwargs)
    monkeypatch.setattr(delivery.arrival, "arrive_gex_source", swap)
    result = delivery.deliver(request, src, dst, record=lambda x: None)
    assert result["status"] == "effect_unknown"
    assert not list((target / "gex").iterdir())
    assert (held / "gex/SPY.json").read_bytes() == h.gex_bytes


def intent_for(request, origin, target):
    def binding(path, uid):
        return {"host": "existing-host", "cwd": "/existing/repo", "python": "/usr/bin/python3", "directory": str(path), "identity": None, "expected_uid": uid}
    return {"request": request, "source": binding(origin, None), "target": binding(target, os.geteuid())}


def test_cli_default_no_remote_call_execute_once_and_original_inspect(tmp_path, monkeypatch, capsys):
    h, request, origin, target, src, dst = setup(tmp_path)
    intent = intent_for(request, origin, target)
    packet = tmp_path / "intent.json"; packet.write_text(json.dumps(intent))
    journal = tmp_path / "operation.jsonl"
    count = []
    def transport(binding):
        real = src if binding["expected_uid"] is None else dst
        def counted(*args): count.append(args[0]); return real(*args)
        return counted
    monkeypatch.setattr(delivery, "ssh_transport", transport)
    def run(mode, execute=False):
        monkeypatch.setattr(sys, "argv", ["delivery", mode, "--intent", str(packet), "--receipt", str(journal)] + (["--execute"] if execute else []))
        return delivery.main()
    assert run("deliver") == 0 and not count and not journal.exists()
    assert run("deliver", True) == 0
    assert count == ["preflight", "export", "arrive"]
    assert journal.stat().st_mode & 0o777 == 0o600
    with pytest.raises(FileExistsError): run("deliver", True)
    assert count == ["preflight", "export", "arrive"]
    assert run("inspect") == 0 and count[-1] == "inspect"
    output = capsys.readouterr().out
    assert h.gex_bytes.decode() not in output
    assert "600.25" not in journal.read_text()
    journal.chmod(0o644)
    with pytest.raises(delivery.DeliveryRefused, match="original_receipt_not_private"): run("inspect")


def test_ssh_command_preserves_known_host_and_never_echoes_remote_stderr(tmp_path, monkeypatch):
    h, request, origin, target, src, dst = setup(tmp_path)
    binding = intent_for(request, origin, target)["target"]
    binding["cwd"] = "/existing/repo with spaces"
    def run(args, packet, limit):
        assert args[0] == "ssh"
        for option in ["BatchMode=yes", "StrictHostKeyChecking=yes", "IdentitiesOnly=yes"]: assert option in args
        assert "cd '/existing/repo with spaces'" in args[-1]
        assert limit == delivery.MAX_HEADER
        header = json.loads(packet.splitlines()[0])
        assert header["action"] == "preflight"
        raise delivery.DeliveryRefused("remote_result_unconfirmed")
    monkeypatch.setattr(delivery, "_exchange", run)
    with pytest.raises(delivery.DeliveryRefused, match="^remote_result_unconfirmed$"):
        delivery.ssh_transport(binding)("preflight", request)
    binding["host"] = "-oProxyCommand=unsafe"
    with pytest.raises(delivery.DeliveryRefused, match="host_invalid"): delivery.ssh_transport(binding)


@pytest.mark.parametrize("kind", ["moves", "grant", "extra", "bad_operation"])
def test_bad_intent_refuses_without_transport(tmp_path, kind):
    h, request, origin, target, src, dst = setup(tmp_path)
    if kind == "moves": request["descriptor"]["moves"] = {}
    elif kind == "grant": request["descriptor"]["grant_id"] = request["operation_id"]
    elif kind == "extra": request["authority"] = "invented"
    else: request["operation_id"] = "not-a-uuid"
    with pytest.raises(Exception): delivery.deliver(request, lambda *a: pytest.fail("IO"), lambda *a: pytest.fail("IO"), record=lambda x: None)


def test_real_transport_pipe_bounds_and_private_stderr():
    assert delivery._exchange([sys.executable, "-c", "import sys;sys.stdout.buffer.write(sys.stdin.buffer.read())"], b"exact", 5) == b"exact"
    with pytest.raises(delivery.DeliveryRefused, match="^remote_result_unconfirmed$"):
        delivery._exchange([sys.executable, "-c", "import sys;sys.stderr.write('secret');sys.stdout.write('x'*100000)"], b"", 64)
    with pytest.raises(delivery.DeliveryRefused):
        delivery._exchange([sys.executable, "-c", "import time;time.sleep(10)"], b"", 64, timeout=0.05)


def test_receipt_directory_durability_failure_prevents_remote_dispatch(tmp_path, monkeypatch):
    _, request, origin, target, _, _ = setup(tmp_path)
    packet = tmp_path / "intent.json"; packet.write_text(json.dumps(intent_for(request, origin, target)))
    journal = tmp_path / "operation.jsonl"
    monkeypatch.setattr(sys, "argv", ["delivery", "deliver", "--intent", str(packet), "--receipt", str(journal), "--execute"])
    monkeypatch.setattr(delivery, "ssh_transport", lambda b: lambda *a: pytest.fail("no remote dispatch"))
    actual = os.fsync
    def fail_parent(fd):
        import stat
        if stat.S_ISDIR(os.fstat(fd).st_mode): raise OSError("directory durability unavailable")
        actual(fd)
    monkeypatch.setattr(delivery.os, "fsync", fail_parent)
    with pytest.raises(OSError): delivery.main()
    assert journal.exists() and json.loads(journal.read_text())["intent"]["request"] == request
    with pytest.raises(FileExistsError): delivery.main()
