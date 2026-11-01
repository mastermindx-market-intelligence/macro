import hashlib
import io
import json
import os
from pathlib import Path
import shlex
import sys
import tarfile
from types import SimpleNamespace

import pytest

from scripts.publish_boats_history import encode, publish_bundle, receiver_code, verify_archive, transfer_timeout, validate_manifest


def bundle(tmp_path, body=b'{"bars":[]}\n', bad_hash=False):
    manifest = {"schema":"terminal.private_boats_delivery.v1", "complete_history":False,
        "directory":"/mnt/terminal_storage/boats-history/day2", "bytes":len(body), "bars":0,
        "files":[{"name":"AAPL.json", "bytes":len(body), "bars":0,
                  "sha256":hashlib.sha256(body if not bad_hash else b"wrong").hexdigest()}]}
    raw = encode(manifest)
    mp, ap, key = (tmp_path/name for name in ("manifest.json", "bundle.tar", "ssh-key"))
    mp.write_bytes(raw)
    key.write_bytes(b"inert test key; never used by SSH")
    with tarfile.open(ap, "w") as archive:
        for name, data in [(".delivery-manifest.json", raw), ("AAPL.json", body)]:
            item = tarfile.TarInfo(name)
            item.size = len(data)
            archive.addfile(item, io.BytesIO(data))
    for path in (mp, ap, key): path.chmod(0o600)
    evidence = tmp_path/"evidence"
    evidence.mkdir(mode=0o700)
    return manifest, mp, ap, key, evidence


def publish(args, run):
    manifest, mp, ap, key, evidence = args
    return publish_bundle(mp, ap, evidence, "day2", "day1", "root@example.test", key, run=run)


def test_verified_bundle_uses_one_transport_and_refuses_replay(tmp_path):
    args = bundle(tmp_path)
    manifest, mp, _, _, evidence = args
    calls = []
    def transport(argv, **kwargs):
        assert (evidence/"publish-start.json").exists()
        assert kwargs["stdin"].tell() == 0
        assert argv[:2] == ["ssh", "-i"] and argv[-2] == "root@example.test"
        assert "ServerAliveInterval=30" in argv and "ServerAliveCountMax=3" in argv
        assert kwargs["timeout"] == transfer_timeout(args[2].stat().st_size, 1)
        compile(shlex.split(argv[-1])[-1], "receiver", "exec")
        calls.append(argv)
        return SimpleNamespace(returncode=0, stdout=encode({
            "schema":"terminal.private_boats_selection.v1", "selected_version":"day2",
            "previous_version":"day1", "files":1, "manifest_sha256":hashlib.sha256(mp.read_bytes()).hexdigest(),
            "service_restarted":False}))
    assert publish(args, transport)["selected_version"] == "day2"
    assert len(calls) == 1
    with pytest.raises(ValueError, match="reconciliation"): publish(args, transport)
    assert len(calls) == 1


def test_corrupt_bundle_is_rejected_before_start_or_transport(tmp_path):
    args = bundle(tmp_path, bad_hash=True)
    with pytest.raises(ValueError, match="digest"):
        publish(args, lambda *a, **k: pytest.fail("transport started"))
    assert not (args[-1]/"publish-start.json").exists()


def test_real_cohort_transfer_gets_bounded_size_and_fsync_allowance():
    seconds = transfer_timeout(1_118_747_051, 8343)
    assert 2500 < seconds < 3600
    assert transfer_timeout(8 * 1024**3 + 32 * 1024**2, 20000) <= 14400


@pytest.mark.parametrize("symbols", [["../bad"], ["AAPL"], ["EMPTY", "EMPTY"], [1]])
def test_invalid_empty_symbol_partition_refuses(tmp_path, symbols):
    manifest = bundle(tmp_path)[0]
    manifest["vendor_empty_symbols"] = symbols
    with pytest.raises(ValueError, match="empty-symbol"):
        validate_manifest(manifest, "day2")


@pytest.mark.parametrize("result", ["nonzero", "wrong-receipt", "timeout"])
def test_unknown_transport_result_preserves_permanent_start(tmp_path, result):
    args = bundle(tmp_path)
    calls = []
    def transport(*a, **k):
        calls.append(1)
        if result == "timeout": raise TimeoutError("inert timeout")
        return SimpleNamespace(returncode=1 if result == "nonzero" else 0, stdout=b"{}")
    with pytest.raises((RuntimeError, TimeoutError)): publish(args, transport)
    assert (args[-1]/"publish-start.json").is_file()
    assert not (args[-1]/"publish-result.json").exists()
    with pytest.raises(ValueError, match="reconciliation"): publish(args, transport)
    assert len(calls) == 1


def test_symlink_input_does_not_read_or_publish(tmp_path):
    args = list(bundle(tmp_path))
    alias = tmp_path/"alias.tar"
    alias.symlink_to(args[2])
    args[2] = alias
    with pytest.raises(ValueError, match="regular inputs"):
        publish(args, lambda *a, **k: pytest.fail("transport started"))


def test_tar_link_member_cannot_escape_destination(tmp_path):
    manifest, mp, ap, _, _ = bundle(tmp_path)
    with tarfile.open(ap, "w") as archive:
        first = tarfile.TarInfo(".delivery-manifest.json")
        first.size = mp.stat().st_size
        archive.addfile(first, io.BytesIO(mp.read_bytes()))
        link = tarfile.TarInfo("AAPL.json")
        link.type, link.linkname = tarfile.SYMTYPE, "/outside"
        archive.addfile(link)
    with ap.open("rb") as stream, pytest.raises(ValueError, match="unexpected"):
        verify_archive(stream, mp.read_bytes(), manifest)


@pytest.mark.parametrize("predecessor", ["day1", "foreign-writer"])
def test_actual_receiver_selects_only_expected_predecessor(tmp_path, monkeypatch, capsys, predecessor):
    manifest, mp, ap, _, _ = bundle(tmp_path)
    root = tmp_path/"private-history"
    root.mkdir(mode=0o700)
    (root/"day1").mkdir(mode=0o700)
    (root/"current").symlink_to(predecessor)
    manifest["directory"] = str(root/"day2")
    raw = encode(manifest)
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w") as archive:
        for name, data in [(".delivery-manifest.json", raw), ("AAPL.json", b'{"bars":[]}\n')]:
            item = tarfile.TarInfo(name)
            item.size = len(data)
            archive.addfile(item, io.BytesIO(data))
    stream.seek(0)
    monkeypatch.setattr(sys, "stdin", SimpleNamespace(buffer=stream))
    monkeypatch.setattr(os.path, "ismount", lambda path: str(path) == "/mnt/terminal_storage")
    code = receiver_code("day2", "day1", hashlib.sha256(raw).hexdigest())
    code = code.replace("/mnt/terminal_storage/boats-history", str(root))
    if predecessor != "day1":
        with pytest.raises(AssertionError): exec(compile(code, "receiver", "exec"), {})
        assert os.readlink(root/"current") == predecessor
        assert not (root/"day2").exists()
    else:
        exec(compile(code, "receiver", "exec"), {})
        assert os.readlink(root/"current") == "day2"
        assert (root/"day1").is_dir()
        assert (root/"day2"/"AAPL.json").stat().st_mode & 0o777 == 0o600
        assert json.loads(capsys.readouterr().out)["service_restarted"] is False
