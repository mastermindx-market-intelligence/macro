"""Synthetic tests for completed OHLC generation delivery; no provider access."""
from __future__ import annotations

import copy
import fcntl
import hashlib
import io
import json
import os
from pathlib import Path
import socket
import tarfile

import pytest

from scripts import build_chart_data as producer
from scripts import publish_ohlc as delivery


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def refused(*args, **kwargs):
        raise AssertionError("synthetic OHLC tests cannot access the network")
    monkeypatch.setattr(socket.socket, "connect", refused)
    monkeypatch.setattr(socket, "create_connection", refused)


@pytest.fixture
def receiver(tmp_path):
    app = tmp_path / "app"
    app.mkdir()
    lock = tmp_path / "macro-update.lock"
    lock.touch()
    return app, lock


def build(base, *, number=1, attempt=1, run_id=None, symbols=("AAPL",),
          unavailable=None, variant=0):
    payload = base / "payload"
    payload.mkdir(parents=True)
    for symbol in symbols:
        (payload / delivery._filename(symbol)).write_text(
            json.dumps({"t": symbol, "o": 0, "src": "synthetic",
                        "bars": [["2026-01-02", 1.0, variant]]}))
    manifest = base / "manifest.json"
    unavailable = {} if unavailable is None else unavailable
    doc = delivery.seal_generation(
        payload, manifest, source_sha="a" * 40, run_id=str(run_id or 1000 + number),
        run_number=number, run_attempt=attempt, index_sha256="b" * 64,
        expected_symbols=[*symbols, *unavailable], unavailable_symbols=unavailable)
    bundle = base / "bundle.tar"
    receipt = delivery.build_bundle(payload, manifest, bundle)
    return {"payload": payload, "manifest": manifest, "doc": doc,
            "bundle": bundle, "digest": receipt["manifest_sha256"],
            "id": doc["generation"]}


def receive(item, receiver, predecessor=None, *, stream=None):
    app, lock = receiver
    return delivery.receive_bundle(
        io.BytesIO(item["bundle"].read_bytes()) if stream is None else stream,
        app, operation_id=item["id"], manifest_sha256=item["digest"],
        expected_predecessor=predecessor, lock_path=lock, lock_timeout=0)


def status(receiver, operation=None):
    app, lock = receiver
    return delivery.receiver_status(app, operation_id=operation, lock_path=lock)


def archive_members(item):
    with tarfile.open(item["bundle"]) as archive:
        return [(copy.copy(member), archive.extractfile(member).read())
                for member in archive.getmembers()]


def archive_bytes(entries):
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w", format=tarfile.USTAR_FORMAT) as archive:
        for member, body in entries:
            archive.addfile(member, io.BytesIO(body) if member.isfile() else None)
    return output.getvalue()


def environment(item):
    doc = item["doc"]
    return {"GITHUB_REPOSITORY": delivery.REPOSITORY, "GITHUB_REF": "refs/heads/main",
            "GITHUB_WORKFLOW_REF": delivery.WORKFLOW, "GITHUB_RUN_ID": doc["run_id"],
            "GITHUB_RUN_NUMBER": str(doc["run_number"]),
            "GITHUB_RUN_ATTEMPT": str(doc["run_attempt"]),
            # The output-commit tail may have rebased since production.
            "GITHUB_SHA": "f" * 40}


def test_completion_exact_partition_and_original_bytes(tmp_path):
    item = build(tmp_path / "build", symbols=("AAPL", "^GSPC", "BRK=F"),
                 unavailable={"SPY": "no_retained_price"})
    doc = json.loads(item["manifest"].read_bytes())
    assert doc == item["doc"]
    assert doc["unavailable_symbols"] == {"SPY": "no_retained_price"}
    assert {x["name"] for x in doc["files"]} == {"AAPL.json", "_GSPC.json", "BRK_F.json"}
    assert doc["total_bytes"] == sum(x["size"] for x in doc["files"])
    for entry in doc["files"]:
        raw = (item["payload"] / entry["name"]).read_bytes()
        assert (len(raw), hashlib.sha256(raw).hexdigest()) == (entry["size"], entry["sha256"])


@pytest.mark.parametrize("defect", [
    "partition", "overlap", "reason", "duplicate", "collision", "unsafe",
    "total", "workflow", "boolean_run", "missing_source",
])
def test_manifest_refuses_invalid_identity_or_census(tmp_path, defect):
    doc = build(tmp_path / "build", unavailable={"SPY": "no_retained_price"})["doc"]
    if defect == "partition":
        doc["unavailable_symbols"] = {}
    elif defect == "overlap":
        doc["unavailable_symbols"]["AAPL"] = "no_retained_price"
    elif defect == "reason":
        doc["unavailable_symbols"]["SPY"] = "invented_fallback"
    elif defect == "duplicate":
        doc["files"].append(dict(doc["files"][0]))
    elif defect == "collision":
        doc["expected_symbols"].append("aapl")
        doc["unavailable_symbols"]["aapl"] = "no_retained_price"
    elif defect == "unsafe":
        doc["files"][0]["name"] = "../AAPL.json"
    elif defect == "total":
        doc["total_bytes"] += 1
    elif defect == "workflow":
        doc["workflow"] = "untrusted"
    elif defect == "boolean_run":
        doc["run_number"] = True
    else:
        del doc["source_sha"]
    with pytest.raises(delivery.DeliveryError):
        delivery.validate_manifest(doc)


@pytest.mark.parametrize("defect", ["missing", "extra", "hash", "size", "symlink", "hardlink"])
def test_payload_refuses_changed_census_and_link_aliases(tmp_path, defect):
    item = build(tmp_path / "build")
    file = item["payload"] / "AAPL.json"
    if defect == "missing":
        file.unlink()
    elif defect == "extra":
        (item["payload"] / "SPY.json").write_text("{}")
    elif defect == "hash":
        file.write_bytes(file.read_bytes().replace(b"1.0", b"2.0"))
    elif defect == "size":
        file.write_bytes(file.read_bytes() + b" ")
    else:
        outside = tmp_path / "outside"
        outside.write_bytes(file.read_bytes())
        file.unlink()
        file.symlink_to(outside) if defect == "symlink" else os.link(outside, file)
    with pytest.raises(delivery.DeliveryError):
        delivery.validate_payload(item["payload"], item["doc"])


@pytest.mark.parametrize("length", [1, 95])
def test_ustar_prefix_roundtrip_and_idempotent_selection(tmp_path, receiver, length):
    symbol = "A" * length
    item = build(tmp_path / "build", symbols=(symbol,))
    result = receive(item, receiver)
    assert result["state"] == "published"
    assert receive(item, receiver)["state"] == "published"
    app, _lock = receiver
    for tree in ("site", "site.served"):
        link = app / tree / "ohlc"
        assert os.readlink(link) == "../ohlc.served/current"
        assert (link / (symbol + ".json")).read_bytes() == (
            item["payload"] / (symbol + ".json")).read_bytes()
    assert status(receiver, item["id"])["manifest_sha256"] == item["digest"]


def test_ustar_malicious_prefix_is_checked_as_part_of_full_path(tmp_path, receiver):
    item = build(tmp_path / "build")
    raw = bytearray(item["bundle"].read_bytes())
    manifest_size = len(item["manifest"].read_bytes())
    offset = 512 + ((manifest_size + 511) // 512) * 512
    header = bytearray(raw[offset:offset + 512])
    # Keep an innocuous basename and forge only the USTAR prefix field.
    header[:100] = b"AAPL.json".ljust(100, b"\0")
    header[345:500] = b"../payload".ljust(155, b"\0")
    header[148:156] = b" " * 8
    header[148:156] = ("%06o\0 " % sum(header)).encode("ascii")
    raw[offset:offset + 512] = header
    with pytest.raises(delivery.DeliveryError, match="unexpected_archive_member"):
        receive(item, receiver, stream=io.BytesIO(raw))
    assert status(receiver)["current"] is None


@pytest.mark.parametrize("kind", [
    tarfile.GNUTYPE_LONGNAME, tarfile.GNUTYPE_LONGLINK,
    tarfile.XHDTYPE, tarfile.XGLTYPE, tarfile.SYMTYPE, tarfile.LNKTYPE,
])
def test_extension_or_link_header_is_rejected_before_body_read(tmp_path, receiver, kind):
    item = build(tmp_path / "build")
    member = tarfile.TarInfo("manifest.json")
    member.type = kind
    member.size = 1024 * 1024 * 1024
    header = member.tobuf(format=tarfile.USTAR_FORMAT)

    class HeaderOnly:
        reads = []
        def read(self, size):
            self.reads.append(size)
            assert len(self.reads) == 1, "must reject header before reading its body"
            assert size == 512
            return header

    stream = HeaderOnly()
    with pytest.raises(delivery.DeliveryError, match="archive_member_type"):
        receive(item, receiver, stream=stream)
    assert stream.reads == [512]


@pytest.mark.parametrize("defect", [
    "duplicate", "unexpected", "missing", "traversal", "symlink",
    "hash", "size", "truncated", "trailing",
])
def test_bad_archive_preserves_selected_generation(tmp_path, receiver, defect):
    first = build(tmp_path / "first")
    receive(first, receiver)
    second = build(tmp_path / "second", number=2, variant=1)
    entries = archive_members(second)
    member, body = entries[1]
    if defect == "duplicate":
        entries.append((copy.copy(member), body))
    elif defect == "unexpected":
        member.name = "payload/UNDECLARED.json"
    elif defect == "missing":
        entries.pop()
    elif defect == "traversal":
        member.name = "../AAPL.json"
    elif defect == "symlink":
        member.type, member.linkname, member.size = tarfile.SYMTYPE, "../../outside", 0
        entries[1] = (member, b"")
    elif defect == "hash":
        entries[1] = (member, body.replace(b"1.0", b"2.0"))
    elif defect == "size":
        member.size += 1
        entries[1] = (member, body + b" ")
    raw = archive_bytes(entries)
    if defect == "truncated":
        raw = raw[:512 + len(second["manifest"].read_bytes()) + 4]
    elif defect == "trailing":
        raw += b"not another archive"
    with pytest.raises(delivery.DeliveryError):
        receive(second, receiver, first["id"], stream=io.BytesIO(raw))
    assert status(receiver)["current"] == first["id"]
    assert (receiver[0] / "site.served/ohlc/AAPL.json").read_bytes() == (
        first["payload"] / "AAPL.json").read_bytes()


def test_failed_upload_does_not_hold_updater_lock(tmp_path, receiver):
    item = build(tmp_path / "build")
    _app, lock = receiver

    class BrokenUpload:
        probed = False
        def read(self, size):
            with lock.open("r+") as probe:
                fcntl.flock(probe, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.probed = True
            raise OSError("synthetic connection failure")

    stream = BrokenUpload()
    with pytest.raises(OSError, match="synthetic"):
        receive(item, receiver, stream=stream)
    assert stream.probed
    assert status(receiver)["current"] is None
    assert not list((receiver[0] / "ohlc.served").glob(".incoming-*"))


def test_selection_rechecks_predecessor_after_staging(tmp_path, receiver, monkeypatch):
    first = build(tmp_path / "first")
    second = build(tmp_path / "second", number=2)
    winner = build(tmp_path / "winner", number=3)
    receive(first, receiver)
    extract = delivery._extract

    def competing_selection(stream, stage, operation, digest):
        doc = extract(stream, stage, operation, digest)
        if operation == second["id"]:
            receive(winner, receiver, first["id"])
        return doc

    monkeypatch.setattr(delivery, "_extract", competing_selection)
    with pytest.raises(delivery.DeliveryError, match="predecessor_changed"):
        receive(second, receiver, first["id"])
    assert status(receiver)["current"] == winner["id"]


def test_lock_contention_and_borrowed_descriptor_custody(tmp_path, receiver):
    item = build(tmp_path / "build")
    receive(item, receiver)
    app, lock = receiver
    with lock.open("r+") as owner, lock.open("r+") as probe:
        fcntl.flock(owner, fcntl.LOCK_EX | fcntl.LOCK_NB)
        delivery.reconcile(app, lock_fd=owner.fileno(), lock_path=lock)
        with pytest.raises(BlockingIOError):
            fcntl.flock(probe, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with pytest.raises(delivery.DeliveryError, match="lock_busy"):
            receive(item, receiver)
    other = tmp_path / "other.lock"
    other.touch()
    with other.open("r+") as foreign:
        with pytest.raises(delivery.DeliveryError, match="invalid_lock_fd"):
            delivery.reconcile(app, lock_fd=foreign.fileno(), lock_path=lock)


def test_current_manifest_mutation_cannot_receive_original_digest_ack(tmp_path, receiver):
    item = build(tmp_path / "build")
    receive(item, receiver)
    path = receiver[0] / "ohlc.served/generations" / item["id"] / "manifest.json"
    altered = json.loads(path.read_bytes())
    altered["created_at_utc"] = "2026-01-01T00:00:00Z"
    path.write_bytes(delivery._json_bytes(altered))
    # This remains a valid manifest and exact payload, but no longer matches its receipt.
    delivery.validate_payload(path.parent / "payload", altered)
    with pytest.raises(delivery.DeliveryError, match="current_receipt_conflict"):
        receive(item, receiver)


def test_missing_watermark_refuses_regression_in_used_store(tmp_path, receiver):
    newer = build(tmp_path / "newer", number=20)
    older = build(tmp_path / "older", number=19)
    receive(newer, receiver)
    (receiver[0] / "ohlc.served/watermark.json").unlink()
    with pytest.raises(delivery.DeliveryError, match="missing_watermark"):
        receive(older, receiver, newer["id"])
    assert status(receiver)["current"] == newer["id"]


def test_rollback_preserves_high_water_and_fences_superseded_writer(tmp_path, receiver):
    one = build(tmp_path / "one")
    three = build(tmp_path / "three", number=3)
    two = build(tmp_path / "two", number=2)
    receive(one, receiver)
    receive(three, receiver, one["id"])
    app, lock = receiver
    delivery.rollback_generation(app, expected_current=three["id"], predecessor=one["id"],
                                 lock_path=lock)
    with pytest.raises(delivery.DeliveryError, match="older_generation"):
        receive(two, receiver, one["id"])
    four = build(tmp_path / "four", number=4)
    receive(four, receiver, one["id"])
    with pytest.raises(delivery.DeliveryError, match="rollback_current_changed"):
        delivery.rollback_generation(app, expected_current=three["id"],
                                     predecessor=one["id"], lock_path=lock)
    assert status(receiver)["current"] == four["id"]
    assert {p.name for p in (app / "ohlc.served/generations").iterdir()} == {one["id"], four["id"]}


def test_rollback_refuses_changed_predecessor_manifest(tmp_path, receiver):
    one = build(tmp_path / "one")
    two = build(tmp_path / "two", number=2)
    receive(one, receiver)
    receive(two, receiver, one["id"])
    app, lock = receiver
    path = app / "ohlc.served/generations" / one["id"] / "manifest.json"
    doc = json.loads(path.read_bytes())
    doc["created_at_utc"] = "2026-01-01T00:00:00Z"
    path.write_bytes(delivery._json_bytes(doc))
    with pytest.raises(delivery.DeliveryError, match="rollback_receipt_conflict"):
        delivery.rollback_generation(app, expected_current=two["id"],
                                     predecessor=one["id"], lock_path=lock)
    assert status(receiver)["current"] == two["id"]


@pytest.mark.parametrize("kind", ["directory", "foreign_link"])
def test_foreign_serving_path_is_preserved(tmp_path, receiver, kind):
    item = build(tmp_path / "build")
    path = receiver[0] / "site.served/ohlc"
    path.parent.mkdir()
    if kind == "directory":
        path.mkdir()
        (path / "owned-by-someone-else").write_text("preserve")
    else:
        path.symlink_to("../../outside")
    with pytest.raises(delivery.DeliveryError, match="foreign_ohlc_path"):
        receive(item, receiver)
    assert path.is_symlink() if kind == "foreign_link" else path.is_dir()


def test_sender_lost_ack_reconciles_without_second_receive(tmp_path, receiver, monkeypatch):
    item = build(tmp_path / "build")
    calls = []
    unavailable = True

    def ssh(arguments, *, ssh_key, stdin_path=None):
        calls.append(arguments[0])
        if arguments[0] == "receive":
            receive(item, receiver)
            raise OSError("synthetic loss after remote selection")
        if len(arguments) > 1 and unavailable:
            raise OSError("synthetic status outage")
        return status(receiver, item["id"] if len(arguments) > 1 else None)

    monkeypatch.setattr(delivery, "_ssh", ssh)
    evidence = tmp_path / "evidence"
    first = delivery.publish(item["manifest"], item["payload"], evidence, tmp_path / "key",
                             environment=environment(item))
    assert first["state"] == "unknown"
    assert calls == ["status", "receive", "status"]
    unavailable = False
    second = delivery.publish(item["manifest"], item["payload"], evidence, tmp_path / "key",
                              environment=environment(item))
    assert second["state"] == "published_reconciled"
    assert calls == ["status", "receive", "status", "status"]
    assert json.loads((evidence / "operation.json").read_bytes())["source_sha"] == "a" * 40


def test_post_ack_receipt_write_error_is_unknown_and_never_resends(tmp_path, receiver, monkeypatch):
    item = build(tmp_path / "build")
    calls = []

    def ssh(arguments, *, ssh_key, stdin_path=None):
        calls.append(arguments[0])
        return receive(item, receiver) if arguments[0] == "receive" else status(
            receiver, item["id"] if len(arguments) > 1 else None)

    original = delivery._write_json
    def broken_result(path, value, **kwargs):
        if path.name == "result.json":
            raise OSError("synthetic full filesystem")
        return original(path, value, **kwargs)

    monkeypatch.setattr(delivery, "_ssh", ssh)
    monkeypatch.setattr(delivery, "_write_json", broken_result)
    evidence = tmp_path / "evidence"
    for _ in range(2):
        result = delivery.publish(item["manifest"], item["payload"], evidence, tmp_path / "key",
                                  environment=environment(item))
        assert result["state"] == "unknown"
        assert result["code"] == "result_receipt_unwritten"
    assert calls.count("receive") == 1
    assert status(receiver)["current"] == item["id"]


def test_sender_rejects_other_workflow_attempt_before_transport(tmp_path, monkeypatch):
    item = build(tmp_path / "build")
    monkeypatch.setattr(delivery, "_ssh", lambda *a, **kw: pytest.fail("must not transport"))
    env = environment(item)
    env["GITHUB_RUN_ATTEMPT"] = "2"
    with pytest.raises(delivery.DeliveryError, match="receipt_from_another_run"):
        delivery.publish(item["manifest"], item["payload"], tmp_path / "evidence",
                         tmp_path / "key", environment=env)


def producer_site(tmp_path, monkeypatch, symbols=("AAPL", "SPY")):
    site = tmp_path / "site"
    (site / "stockdata").mkdir(parents=True)
    (site / "stockdata/index.json").write_text(json.dumps([{"t": x} for x in symbols]))
    (site / "ohlc").mkdir()
    (site / "ohlc/OLD.json").write_text('{"old":true}')
    (site / "_tmp").mkdir()
    (site / "_tmp/ohlc-complete.json").write_text('{"stale":true}')
    monkeypatch.setattr(producer, "_daily_ohlc_identity", lambda: {
        "source_sha": "a" * 40, "run_id": "1001", "run_number": 1, "run_attempt": 1})
    monkeypatch.setattr(producer.config, "data_dir", lambda: tmp_path / "data")
    monkeypatch.setattr(producer, "_load_caches", lambda: {})
    return site


@pytest.mark.parametrize("failure", ["exception", "empty", "bad_index"])
def test_producer_failed_build_preserves_payload_and_invalidates_receipt(
        tmp_path, monkeypatch, failure):
    site = producer_site(tmp_path, monkeypatch)
    def ticker(*args, **kwargs):
        if failure == "exception":
            raise RuntimeError("synthetic producer failure")
        return None
    monkeypatch.setattr(producer, "_build_ticker", ticker)
    if failure == "bad_index":
        (site / "stockdata/index.json").write_text("{")
    if failure == "empty":
        assert producer.build_us(site) == (0, 0)
    else:
        with pytest.raises((RuntimeError, ValueError)):
            producer.build_us(site)
    assert (site / "ohlc/OLD.json").read_text() == '{"old":true}'
    assert not (site / "_tmp/ohlc-complete.json").exists()


@pytest.mark.parametrize("symbols", [("AAPL", "aapl"), ("^GSPC", "_GSPC"), ("A/B",)])
def test_producer_rejects_filename_census_before_loading_prices(tmp_path, monkeypatch, symbols):
    site = producer_site(tmp_path, monkeypatch, symbols)
    monkeypatch.setattr(producer, "_load_caches", lambda: pytest.fail("must reject first"))
    with pytest.raises(ValueError):
        producer.build_us(site)
    assert (site / "ohlc/OLD.json").exists()
    assert not (site / "_tmp/ohlc-complete.json").exists()


def test_producer_completion_records_unavailable_and_replaces_whole_payload(tmp_path, monkeypatch):
    site = producer_site(tmp_path, monkeypatch)
    monkeypatch.setattr(producer, "_build_ticker", lambda ticker, *a, **kw: (
        {"t": ticker, "o": 0, "bars": [["2026-01-02", 1.0, None]]}
        if ticker == "AAPL" else None))
    assert producer.build_us(site) == (1, 0)
    doc = json.loads((site / "_tmp/ohlc-complete.json").read_bytes())
    assert doc["expected_symbols"] == ["AAPL", "SPY"]
    assert doc["unavailable_symbols"] == {"SPY": "no_retained_price"}
    assert doc["index_sha256"] == hashlib.sha256(
        (site / "stockdata/index.json").read_bytes()).hexdigest()
    assert {x.name for x in (site / "ohlc").iterdir()} == {"AAPL.json"}
    delivery.validate_payload(site / "ohlc", doc)


def test_producer_captures_git_identity_before_loading_prices(tmp_path, monkeypatch):
    # Use the real identity routine, with only git and retained-price inputs synthetic.
    identity = producer._daily_ohlc_identity
    site = producer_site(tmp_path, monkeypatch, ("AAPL",))
    monkeypatch.setattr(producer, "_daily_ohlc_identity", identity)
    env = environment({"doc": {"run_id": "1001", "run_number": 1, "run_attempt": 1}})
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    events = []
    def head(*args, **kwargs):
        events.append("git")
        return "a" * 40 + "\n"
    def caches():
        events.append("prices")
        return {}
    monkeypatch.setattr(producer.subprocess, "check_output", head)
    monkeypatch.setattr(producer, "_load_caches", caches)
    monkeypatch.setattr(producer, "_build_ticker", lambda *a, **kw: {
        "t": "AAPL", "o": 0, "bars": [["2026-01-02", 1.0, None]]})
    producer.build_us(site)
    assert events == ["git", "prices"]
    assert json.loads((site / "_tmp/ohlc-complete.json").read_bytes())["source_sha"] == "a" * 40


def test_inherited_lock_body_error_keeps_lock_and_original_error(receiver):
    _app, lock = receiver
    with lock.open("r+") as owner, lock.open("r+") as probe:
        fcntl.flock(owner, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with pytest.raises(OSError, match="synthetic protected-body failure"):
            with delivery._locked(lock, inherited_fd=owner.fileno()):
                raise OSError("synthetic protected-body failure")
        with pytest.raises(BlockingIOError):
            fcntl.flock(probe, fcntl.LOCK_EX | fcntl.LOCK_NB)


def test_missing_watermark_after_rollback_cannot_forget_higher_order(tmp_path, receiver):
    one = build(tmp_path / "one")
    three = build(tmp_path / "three", number=3)
    two = build(tmp_path / "two", number=2)
    receive(one, receiver)
    receive(three, receiver, one["id"])
    app, lock = receiver
    delivery.rollback_generation(app, expected_current=three["id"],
                                 predecessor=one["id"], lock_path=lock)
    (app / "ohlc.served/watermark.json").unlink()
    with pytest.raises(delivery.DeliveryError, match="missing_watermark"):
        receive(two, receiver, one["id"])
    assert status(receiver)["current"] == one["id"]


@pytest.mark.parametrize("number,attempt,run_id,code", [
    (19, 9, "1999", "older_generation"),
    (20, 1, "2000", "older_generation"),
    (20, 3, "2001", "run_identity_conflict"),
])
def test_order_fences_stale_attempts_and_reused_run_numbers(
        tmp_path, receiver, number, attempt, run_id, code):
    first = build(tmp_path / "first", number=20, attempt=2, run_id="2000")
    receive(first, receiver)
    stale = build(tmp_path / "stale", number=number, attempt=attempt, run_id=run_id)
    with pytest.raises(delivery.DeliveryError, match=code):
        receive(stale, receiver, first["id"])
    assert status(receiver)["current"] == first["id"]


def test_changed_generation_with_same_git_sha_advances(tmp_path, receiver):
    first = build(tmp_path / "first")
    second = build(tmp_path / "second", number=2, variant=1)
    assert first["doc"]["source_sha"] == second["doc"]["source_sha"]
    receive(first, receiver)
    receive(second, receiver, first["id"])
    assert status(receiver)["current"] == second["id"]
    assert (receiver[0] / "site.served/ohlc/AAPL.json").read_bytes() == (
        second["payload"] / "AAPL.json").read_bytes()


def test_producer_receipt_install_failure_rolls_back_directory(tmp_path, monkeypatch):
    site = producer_site(tmp_path, monkeypatch, ("AAPL",))
    monkeypatch.setattr(producer, "_build_ticker", lambda *a, **kw: {
        "t": "AAPL", "o": 0, "bars": [["2026-01-02", 1.0, None]]})
    replace = os.replace
    def fail_receipt(source, destination, *args, **kwargs):
        if Path(destination) == site / "_tmp/ohlc-complete.json":
            raise OSError("synthetic completion-rename failure")
        return replace(source, destination, *args, **kwargs)
    monkeypatch.setattr(os, "replace", fail_receipt)
    with pytest.raises(OSError, match="synthetic completion-rename failure"):
        producer.build_us(site)
    assert {p.name for p in (site / "ohlc").iterdir()} == {"OLD.json"}
    assert not (site / "_tmp/ohlc-complete.json").exists()


def test_non_daily_producer_cannot_seal_completion_receipt(tmp_path, monkeypatch):
    identity = producer._daily_ohlc_identity
    site = producer_site(tmp_path, monkeypatch, ("AAPL",))
    monkeypatch.setattr(producer, "_daily_ohlc_identity", identity)
    monkeypatch.delenv("GITHUB_WORKFLOW_REF", raising=False)
    monkeypatch.setattr(producer.subprocess, "check_output",
                        lambda *a, **kw: pytest.fail("untrusted producer requested Git identity"))
    monkeypatch.setattr(producer, "_build_ticker", lambda *a, **kw: {
        "t": "AAPL", "o": 0, "bars": [["2026-01-02", 1.0, None]]})
    assert producer.build_us(site) == (1, 0)
    assert (site / "ohlc/AAPL.json").is_file()
    assert not (site / "_tmp/ohlc-complete.json").exists()
