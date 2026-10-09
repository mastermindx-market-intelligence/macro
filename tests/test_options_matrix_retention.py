"""Immutable EOD matrix identity and failure-atomic publisher regressions."""
from __future__ import annotations

import hashlib
import io
import json

import pytest

from engine import options_matrix_retention as retention


def payload(root="SPY", session="2026-10-02", strike=500.0):
    return {"schema": "options_structure.matrix/v1", "root": root,
            "session": session, "_build_meta": {"asof_date": session},
            "asof": "2026-10-03T10:00:00Z", "spot": 500.0,
            "cells": [{"strike": strike, "expiry": "2026-10-16", "gex": 1}]}


def encoded(**kwargs):
    return json.dumps(payload(**kwargs), allow_nan=False).encode()


class S3Error(Exception):
    def __init__(self, code):
        self.response = {"Error": {"Code": code}}


class ShortBody(io.BytesIO):
    def read(self, size=-1):
        assert size > 0, "unbounded reads forbidden"
        return super().read(min(size, 7))


class Store:
    def __init__(self):
        self.objects = {}
        self.calls = []
        self.streams = []
        self.put_fault = None
        self.get_fault = None
        self.body_factory = ShortBody
        self.length_override = None

    def get_object(self, *, Bucket, Key):
        self.calls.append(("get", Key))
        if self.get_fault:
            raise S3Error(self.get_fault)
        if Key not in self.objects:
            raise S3Error("NoSuchKey")
        body = self.body_factory(self.objects[Key])
        self.streams.append(body)
        length = len(self.objects[Key]) if self.length_override is None else self.length_override
        return {"ContentLength": length, "Body": body}

    def put_object(self, *, Bucket, Key, Body, ContentType, **kwargs):
        self.calls.append(("put", Key))
        if self.put_fault == "before":
            raise TimeoutError("before write")
        if kwargs.get("IfNoneMatch") == "*" and Key in self.objects:
            raise S3Error("PreconditionFailed")
        if "/history/" in Key:
            assert kwargs.get("IfNoneMatch") == "*"
        assert ContentType == "application/json"
        self.objects[Key] = Body
        if self.put_fault == "after":
            raise TimeoutError("response lost after write")


def test_retained_a_survives_current_b_and_repeat_is_idempotent():
    store = Store()
    a, b = encoded(), encoded(session="2026-10-05")
    a_ref = retention.reference_for_bytes("SPY", a)
    b_ref = retention.reference_for_bytes("SPY", b)
    retention.retain_snapshot(store, "bucket", a_ref, a)
    store.put_object(Bucket="bucket", Key="options_structure/matrix/SPY.json",
                     Body=b, ContentType="application/json")
    retention.retain_snapshot(store, "bucket", a_ref, a)
    assert retention.load_snapshot(store, "bucket", a_ref) == a
    assert store.objects["options_structure/matrix/SPY.json"] == b
    assert a_ref != b_ref
    assert store.calls.count(("put", a_ref.key)) == 1
    assert all(s.closed for s in store.streams)
    assert retention.parse_reference("SPY", a_ref.version_ref, a_ref.sha256) == a_ref


@pytest.mark.parametrize("root", ["spy", " SPY", "SPY\n", "../SPY", "A..B", "", "A/1", "A" * 16, "-SPY"])
def test_bad_roots_refused(root):
    with pytest.raises(retention.HistoricalUnavailable):
        retention.reference_for_bytes(root, encoded())


@pytest.mark.parametrize("version", [
    "sha256:{sha}:bytes:0:session:2026-10-02",
    "sha256:{sha}:bytes:01:session:2026-10-02",
    "sha256:{sha}:bytes:+1:session:2026-10-02",
    "sha256:{sha}:bytes:1.0:session:2026-10-02",
    "sha256:{sha}:bytes:1e2:session:2026-10-02",
    "sha256:{sha}:bytes:9007199254740992:session:2026-10-02",
    "sha256:{sha}:bytes:16777217:session:2026-10-02",
    "sha256:{sha}:bytes:1:session:2026-02-30",
    "sha256:{sha}:bytes:1:session:20261002",
    "sha256:{sha}:bytes:1:session:2026-W40-5",
    "sha256:{sha}:bytes:1:session:2026-10-02\n",
])
def test_strict_ref_decoding(version):
    sha = "a" * 64
    with pytest.raises(retention.HistoricalUnavailable):
        retention.parse_reference("SPY", version.format(sha=sha), sha)


@pytest.mark.parametrize("fingerprint", ["A" * 64, "b" * 64, "a" * 64 + "\n", None, True])
def test_fingerprint_must_match(fingerprint):
    with pytest.raises(retention.HistoricalUnavailable):
        retention.parse_reference("SPY", "sha256:" + "a" * 64 + ":bytes:1:session:unknown", fingerprint)


@pytest.mark.parametrize("change", [
    {"session": "2026-10-03"}, {"session": True}, {"session": "20261002"},
    {"session": "2026-10-02\n"}, {"session": "2026-02-30"},
    {"_build_meta": []}, {"_build_meta": "bad"},
    {"_build_meta": {"asof_date": False}},
])
def test_malformed_or_contradictory_session_is_not_unknown(change):
    doc = payload()
    doc.update(change)
    with pytest.raises(retention.HistoricalUnavailable):
        retention.reference_for_bytes("SPY", json.dumps(doc).encode())


def test_session_fallback_and_unknown_do_not_use_build_clock():
    for doc, expected in [
        ({"session": None, "_build_meta": {"asof_date": "2026-10-02"}}, "2026-10-02"),
        ({"session": "2026-10-02", "_build_meta": None}, "2026-10-02"),
        ({"session": None, "_build_meta": None, "asof": "2026-10-08"}, None),
    ]:
        assert retention.source_session(doc) == expected
    doc = payload()
    doc.update(session=None, _build_meta=None, spot=None, cells=[])
    ref = retention.reference_for_bytes("SPY", json.dumps(doc).encode())
    assert ref.version_ref.endswith(":session:unknown")


@pytest.mark.parametrize("raw", [
    b"[]", b"null", b"\xff", b'{"schema":"bad","root":"SPY"}',
    b'{"schema":"options_structure.matrix/v1","root":"QQQ"}',
    b'{"schema":"options_structure.matrix/v1","root":"SPY","root":"SPY"}',
    b'{"schema":"options_structure.matrix/v1","root":"SPY","spot":NaN}',
    b'{"schema":"options_structure.matrix/v1","root":"SPY","spot":1e9999}',
])
def test_invalid_payload_refused(raw):
    with pytest.raises(retention.HistoricalUnavailable):
        retention.reference_for_bytes("SPY", raw)


@pytest.mark.parametrize("fault", ["missing", "truncated", "extra", "corrupt", "length", "bool_length", "oversize"])
def test_retained_read_refuses_corruption_and_closes_stream(fault):
    store = Store()
    raw = encoded()
    ref = retention.reference_for_bytes("SPY", raw)
    store.objects[ref.key] = raw
    if fault == "missing":
        del store.objects[ref.key]
    elif fault == "truncated":
        store.objects[ref.key] = raw[:-1]
        store.length_override = len(raw)
    elif fault == "extra":
        store.objects[ref.key] = raw + b" "
        store.length_override = len(raw)
    elif fault == "corrupt":
        store.objects[ref.key] = raw.replace(b"SPY", b"QQQ")
    elif fault == "length":
        store.length_override = "123"
    elif fault == "bool_length":
        store.length_override = True
    elif fault == "oversize":
        store.length_override = retention.MAX_MATRIX_BYTES + 1
    with pytest.raises(retention.HistoricalUnavailable):
        retention.load_snapshot(store, "bucket", ref)
    assert all(s.closed for s in store.streams)
    assert not any(c[0] == "put" for c in store.calls)


def test_access_denied_is_not_missing_and_never_attempts_write():
    store = Store()
    store.get_fault = "AccessDenied"
    raw = encoded()
    with pytest.raises(retention.HistoricalUnavailable):
        retention.retain_snapshot(store, "bucket", retention.reference_for_bytes("SPY", raw), raw)
    assert not any(c[0] == "put" for c in store.calls)


@pytest.mark.parametrize("fault,ok", [("before", False), ("after", True)])
def test_uncertain_put_reconciles_same_key(fault, ok):
    store = Store()
    store.put_fault = fault
    raw = encoded()
    ref = retention.reference_for_bytes("SPY", raw)
    if ok:
        retention.retain_snapshot(store, "bucket", ref, raw)
    else:
        with pytest.raises(retention.HistoricalUnavailable):
            retention.retain_snapshot(store, "bucket", ref, raw)
    assert store.calls == [("get", ref.key), ("put", ref.key), ("get", ref.key)]


def test_existing_wrong_bytes_refuse_without_overwrite():
    store = Store()
    raw = encoded()
    ref = retention.reference_for_bytes("SPY", raw)
    store.objects[ref.key] = b"wrong"
    with pytest.raises(retention.HistoricalUnavailable):
        retention.retain_snapshot(store, "bucket", ref, raw)
    assert store.objects[ref.key] == b"wrong"
    assert not any(c[0] == "put" for c in store.calls)


@pytest.mark.parametrize("same", [True, False])
def test_conditional_race_requires_exact_readback(same):
    store = Store()
    raw = encoded()
    ref = retention.reference_for_bytes("SPY", raw)
    def race(**kwargs):
        assert kwargs["IfNoneMatch"] == "*"
        store.objects[ref.key] = raw if same else b"other bytes"
        raise S3Error("PreconditionFailed")
    store.put_object = race
    if same:
        retention.retain_snapshot(store, "bucket", ref, raw)
    else:
        with pytest.raises(retention.HistoricalUnavailable):
            retention.retain_snapshot(store, "bucket", ref, raw)


def test_size_limit_is_checked_before_network(monkeypatch):
    raw = encoded()
    ref = retention.reference_for_bytes("SPY", raw)
    store = Store()
    monkeypatch.setattr(retention, "MAX_MATRIX_BYTES", len(raw) - 1)
    with pytest.raises(retention.HistoricalUnavailable):
        retention.retain_snapshot(store, "bucket", ref, raw)
    assert store.calls == []


def test_reference_digest_and_session_bind_exact_payload():
    raw = encoded()
    ref = retention.reference_for_bytes("SPY", raw)
    assert ref.sha256 == hashlib.sha256(raw).hexdigest()
    wrong = retention.parse_reference("SPY", ref.version_ref.replace("2026-10-02", "2026-10-03"), ref.sha256)
    with pytest.raises(retention.HistoricalUnavailable):
        retention.verify_snapshot(wrong, raw)


def _run_builder(monkeypatch, tmp_path, store, doc):
    import sys
    import scripts.build_options_matrix as builder
    import engine.thetadata_store as td
    monkeypatch.setattr(td, "resolve_thetadata_store", lambda **kwargs: tmp_path)
    monkeypatch.setattr(builder, "build_matrix", lambda *args, **kwargs: doc)
    monkeypatch.setattr(builder, "_r2_client", lambda: store)
    monkeypatch.setenv("R2_BUCKET", "fixture-bucket")
    monkeypatch.setattr(sys, "argv", ["builder", "--publish", "--roots", "SPY", "--out", str(tmp_path)])
    builder.main()


def test_real_publisher_retains_a_before_b_current(monkeypatch, tmp_path):
    store = Store()
    _run_builder(monkeypatch, tmp_path, store, payload())
    a = (tmp_path / "SPY.json").read_bytes()
    a_ref = retention.reference_for_bytes("SPY", a)
    _run_builder(monkeypatch, tmp_path, store, payload(session="2026-10-05"))
    b = (tmp_path / "SPY.json").read_bytes()
    b_ref = retention.reference_for_bytes("SPY", b)
    assert b != a
    assert retention.load_snapshot(store, "fixture-bucket", a_ref) == a
    assert retention.load_snapshot(store, "fixture-bucket", b_ref) == b
    assert store.objects["options_structure/matrix/SPY.json"] == b
    assert (tmp_path / "history" / "SPY" / (a_ref.sha256 + ".json")).read_bytes() == a
    calls = store.calls
    first_head = calls.index(("put", "options_structure/matrix/SPY.json"))
    assert calls.index(("put", a_ref.key)) < first_head
    assert ("get", a_ref.key) in calls[calls.index(("put", a_ref.key))+1:first_head]


@pytest.mark.parametrize("fault", ["before", "get", "local_collision", "metadata", "oversize"])
def test_publisher_retention_failure_preserves_current(monkeypatch, tmp_path, fault):
    import scripts.build_options_matrix as builder
    store = Store()
    _run_builder(monkeypatch, tmp_path, store, payload())
    a = (tmp_path / "SPY.json").read_bytes()
    doc = payload(session="2026-10-05")
    if fault == "before":
        store.put_fault = "before"
    elif fault == "get":
        store.get_fault = "AccessDenied"
    elif fault == "metadata":
        doc["_build_meta"]["asof_date"] = "2026-10-04"
    elif fault == "oversize":
        monkeypatch.setattr(retention, "MAX_MATRIX_BYTES", len(a)-1)
    elif fault == "local_collision":
        raw = builder._serialize(doc)
        ref = retention.reference_for_bytes("SPY", raw)
        path = tmp_path / "history" / "SPY" / (ref.sha256 + ".json")
        path.write_bytes(b"bad")
    with pytest.raises(SystemExit) as error:
        _run_builder(monkeypatch, tmp_path, store, doc)
    assert error.value.code == 1
    assert (tmp_path / "SPY.json").read_bytes() == a
    assert store.objects["options_structure/matrix/SPY.json"] == a


def test_local_retention_repeat_and_collision(monkeypatch, tmp_path):
    import scripts.build_options_matrix as builder
    raw = encoded()
    ref = retention.reference_for_bytes("SPY", raw)
    builder._retain_local(tmp_path, ref, raw)
    builder._retain_local(tmp_path, ref, raw)
    path = tmp_path / "history" / "SPY" / (ref.sha256 + ".json")
    path.write_bytes(b"wrong")
    with pytest.raises(retention.HistoricalUnavailable):
        builder._retain_local(tmp_path, ref, raw)
    assert path.read_bytes() == b"wrong"


def test_lossless_source_coordinate_preserves_number_counterexample():
    raw = encoded().replace(b'500.0, "expiry"', b'999999999999.12345678, "expiry"')
    ref = retention.reference_for_bytes("SPY", raw)
    keys = retention.matrix_coordinate_tokens(ref, raw)
    assert keys == (("2026-10-16", "999999999999.12345678"),)
    rounded = str(json.loads(raw)["cells"][0]["strike"])
    assert rounded == "999999999999.1234"
    assert ("2026-10-16", rounded) not in keys


def test_source_coordinate_rejects_duplicates_and_empty_has_no_membership():
    doc = payload()
    doc["cells"] *= 2
    raw = json.dumps(doc).encode()
    with pytest.raises(retention.HistoricalUnavailable):
        retention.matrix_coordinate_tokens(retention.reference_for_bytes("SPY", raw), raw)
    doc["cells"] = []
    raw = json.dumps(doc).encode()
    assert retention.matrix_coordinate_tokens(retention.reference_for_bytes("SPY", raw), raw) == ()


@pytest.mark.parametrize("strike", [True, "500", 0, -1, 1000000000000, 0.000000001])
def test_source_coordinate_refuses_invalid_domain(strike):
    raw = encoded(strike=strike)
    ref = retention.reference_for_bytes("SPY", raw)
    with pytest.raises(retention.HistoricalUnavailable):
        retention.matrix_coordinate_tokens(ref, raw)


def test_atomic_local_head_keeps_shared_read_permissions(monkeypatch, tmp_path):
    import stat
    import scripts.build_options_matrix as builder
    path = tmp_path / "SPY.json"
    builder._write_bytes(path, b"a")
    assert stat.S_IMODE(path.stat().st_mode) == 0o644
    path.chmod(0o640)
    builder._write_bytes(path, b"b")
    assert path.read_bytes() == b"b"
    assert stat.S_IMODE(path.stat().st_mode) == 0o640


@pytest.mark.parametrize("precision,emin", [(28,-999999), (6,-99), (50,-999999)])
@pytest.mark.parametrize("token,expected", [
    ("1e-999999999", None), ("1e-1000027", None), ("1e-9", None),
    ("1e-8", "0.00000001"), ("123456789.123456780000", "123456789.12345678"),
    ("100.0000000000000000000000000000000000000000000000000000", "100"),
])
def test_coordinate_scale_is_context_independent_and_bounded(monkeypatch, precision, emin, token, expected):
    import builtins
    from decimal import localcontext
    raw = encoded().replace(b'500.0, "expiry"', (token + ', "expiry"').encode())
    ref = retention.reference_for_bytes("SPY", raw)
    formats = []
    def safe_format(value, spec):
        digits = value.as_tuple()
        assert digits.exponent >= -8, "tiny exponent reached formatting"
        assert len(digits.digits) <= 20, "unbounded coefficient reached formatting"
        formats.append(True)
        return builtins.format(value, spec)
    monkeypatch.setattr(retention, "format", safe_format, raising=False)
    with localcontext() as context:
        context.prec, context.Emin = precision, emin
        if expected is None:
            with pytest.raises(retention.HistoricalUnavailable):
                retention.matrix_coordinate_tokens(ref, raw)
            assert not formats
        else:
            assert retention.matrix_coordinate_tokens(ref, raw) == (("2026-10-16", expected),)
            assert formats


def test_committed_engine_fixtures_round_trip_through_real_publisher(monkeypatch, tmp_path):
    from pathlib import Path
    fixtures = Path(__file__).parent / "fixtures" / "options_matrix_retention"
    expected = [
        ("a", "cb50c35a3250b48d70169af2a3aa1450f5c4478bc1dc5fe01b191307fcd2cfb2", 2950, "2026-09-22"),
        ("b", "e8537aedb1005b01db8725983d1c255051562b10054d6cad86ada2bb3e7f6de7", 2971, "2026-09-23"),
    ]
    store = Store()
    refs = []
    for name, sha, count, session in expected:
        raw = (fixtures / (name + ".json")).read_bytes()
        ref = retention.parse_reference("SPY", f"sha256:{sha}:bytes:{count}:session:{session}", sha)
        doc = retention.verify_snapshot(ref, raw)
        _run_builder(monkeypatch, tmp_path, store, doc)
        assert (tmp_path / "SPY.json").read_bytes() == raw
        assert retention.load_snapshot(store, "fixture-bucket", ref) == raw
        assert retention.matrix_coordinate_tokens(ref, raw) == (
            ("2026-10-16", "95"), ("2026-10-16", "100"), ("2026-10-16", "105"))
        refs.append(ref)
    assert retention.load_snapshot(store, "fixture-bucket", refs[0]) == (fixtures / "a.json").read_bytes()
    assert store.objects["options_structure/matrix/SPY.json"] == (fixtures / "b.json").read_bytes()


# Local publication must preserve identity under allocation and filesystem faults.
def test_existing_head_oversize_is_rejected_before_open():
    import scripts.build_options_matrix as builder
    class OversizedHead:
        def exists(self): return True
        def stat(self):
            return type("Info", (), {"st_size": retention.MAX_MATRIX_BYTES + 1})()
        def open(self, *args, **kwargs):
            pytest.fail("oversized head reached allocation")
        def read_text(self, *args, **kwargs):
            pytest.fail("oversized head reached unbounded read_text")
    session, error = builder._existing_usable_session(OversizedHead())
    assert session is None and error is not None


def test_existing_head_growth_is_bounded(monkeypatch, tmp_path):
    from pathlib import Path
    import scripts.build_options_matrix as builder
    path = tmp_path / "SPY.json"
    path.write_bytes(encoded() + b" " * 1000)
    cap = 512
    monkeypatch.setattr(retention, "MAX_MATRIX_BYTES", cap)
    original_stat, original_open = Path.stat, Path.open
    reads = []
    def short_stat(self, *args, **kwargs):
        if self == path:
            return type("Info", (), {"st_size": 1})()
        return original_stat(self, *args, **kwargs)
    class ReadGuard:
        def __init__(self, handle): self.handle = handle
        def __enter__(self): return self
        def __exit__(self, *args): self.handle.close()
        def __getattr__(self, name): return getattr(self.handle, name)
        def read(self, size=-1):
            assert 0 < size <= cap + 1, "unbounded current-head read"
            reads.append(size)
            return self.handle.read(size)
    def guard_open(self, mode="r", *args, **kwargs):
        handle = original_open(self, mode, *args, **kwargs)
        return ReadGuard(handle) if self == path else handle
    monkeypatch.setattr(Path, "stat", short_stat)
    monkeypatch.setattr(Path, "open", guard_open)
    session, error = builder._existing_usable_session(path)
    assert session is None and error is not None
    assert reads and sum(reads) <= cap + 1


@pytest.mark.parametrize("raw", [
    b'{"spot":100,"cells":[{}],"session":"2026-10-02","session":"2026-10-05"}',
    b'{"spot":100,"cells":[{}],"_build_meta":{"asof_date":"2026-10-02","asof_date":"2026-10-05"}}',
    b'{"spot":100,"cells":[{}],"root":"SPY","root":"QQQ","session":"2026-10-02"}',
    b'{"spot":null,"cells":[],"session":true}',
    b'{"spot":null,"cells":[],"_build_meta":[]}',
    b'{"spot":100,"cells":[{}],"session":"2026-10-02","_build_meta":{"asof_date":"2026-10-05"}}',
    b'{"spot":NaN,"cells":[{}],"session":"2026-10-02"}',
    b'{"spot":1e9999,"cells":[{}],"session":"2026-10-02"}',
    b'[]', b'null', b'\xff',
])
def test_existing_head_refuses_ambiguous_or_malformed_metadata(tmp_path, raw):
    import scripts.build_options_matrix as builder
    path = tmp_path / "SPY.json"
    path.write_bytes(raw)
    session, error = builder._existing_usable_session(path)
    assert session is None and error is not None
    assert path.read_bytes() == raw


@pytest.mark.parametrize("doc,session", [
    ({"spot":None,"cells":[]}, None),
    ({"spot":100,"cells":[],"session":None}, None),
    ({"spot":100,"cells":[{}],"_build_meta":{"asof_date":"2026-10-02"}}, "2026-10-02"),
    ({"spot":100,"cells":[{}],"session":"2026-10-02"}, "2026-10-02"),
])
def test_existing_head_preserves_legacy_and_empty_compatibility(tmp_path, doc, session):
    import scripts.build_options_matrix as builder
    path = tmp_path / "SPY.json"
    path.write_text(json.dumps(doc))
    assert builder._existing_usable_session(path) == (session, None)


def test_local_retention_fsync_failure_has_no_final_key_and_can_retry(monkeypatch, tmp_path):
    import scripts.build_options_matrix as builder
    raw = encoded()
    ref = retention.reference_for_bytes("SPY", raw)
    final = tmp_path / "history" / "SPY" / (ref.sha256 + ".json")
    def fail_sync(fd): raise OSError("injected pre-publication fsync failure")
    with monkeypatch.context() as fault:
        fault.setattr(builder.os, "fsync", fail_sync)
        with pytest.raises(OSError, match="injected"):
            builder._retain_local(tmp_path, ref, raw)
    assert not final.exists(), "failed preparation exposed an immutable final key"
    assert list(final.parent.iterdir()) == [], "failed preparation leaked a temporary"
    builder._retain_local(tmp_path, ref, raw)
    assert final.read_bytes() == raw


@pytest.mark.parametrize("same", [True, False])
def test_local_retention_racing_key_is_verified_never_replaced(monkeypatch, tmp_path, same):
    import scripts.build_options_matrix as builder
    raw = encoded()
    ref = retention.reference_for_bytes("SPY", raw)
    final = tmp_path / "history" / "SPY" / (ref.sha256 + ".json")
    linked = []
    real_link = builder.os.link
    def racing_link(src, dst, *args, **kwargs):
        # A concurrently published immutable file is already complete.
        assert not final.exists()
        final.write_bytes(raw if same else b"other bytes")
        linked.append(True)
        return real_link(src, dst, *args, **kwargs)
    monkeypatch.setattr(builder.os, "link", racing_link)
    if same:
        builder._retain_local(tmp_path, ref, raw)
    else:
        with pytest.raises(retention.HistoricalUnavailable):
            builder._retain_local(tmp_path, ref, raw)
    assert linked
    assert final.read_bytes() == (raw if same else b"other bytes")
    assert list(final.parent.iterdir()) == [final]


@pytest.mark.parametrize("failure", ["interrupted", "short"])
def test_interrupted_staged_history_preserves_heads_and_exact_retry(monkeypatch, tmp_path, failure):
    import scripts.build_options_matrix as builder
    store = Store()
    _run_builder(monkeypatch, tmp_path, store, payload())
    previous = (tmp_path / "SPY.json").read_bytes()
    candidate = payload(session="2026-10-05")
    raw = builder._serialize(candidate)
    ref = retention.reference_for_bytes("SPY", raw)
    final = tmp_path / "history" / "SPY" / (ref.sha256 + ".json")
    original_temporary = builder.tempfile.NamedTemporaryFile
    class InterruptedWriter:
        def __init__(self, handle): self.handle = handle
        def __enter__(self): self.handle.__enter__(); return self
        def __exit__(self, *args): return self.handle.__exit__(*args)
        def __getattr__(self, name): return getattr(self.handle, name)
        def write(self, data):
            self.handle.write(data[:8])
            self.handle.flush()
            if failure == "interrupted":
                raise OSError("injected interrupted write after eight bytes")
            return 8
    with monkeypatch.context() as fault:
        fault.setattr(builder.tempfile, "NamedTemporaryFile",
                      lambda *args, **kwargs: InterruptedWriter(original_temporary(*args, **kwargs)))
        with pytest.raises(SystemExit) as exc:
            _run_builder(monkeypatch, tmp_path, store, candidate)
        assert exc.value.code == 1
    assert not final.exists()
    assert not list(final.parent.glob(".matrix-history-*"))
    assert (tmp_path / "SPY.json").read_bytes() == previous
    assert store.objects["options_structure/matrix/SPY.json"] == previous
    assert ref.key not in store.objects
    _run_builder(monkeypatch, tmp_path, store, candidate)
    assert final.read_bytes() == raw
    assert (tmp_path / "SPY.json").read_bytes() == raw
    assert store.objects[ref.key] == raw
    assert store.objects["options_structure/matrix/SPY.json"] == raw


@pytest.mark.parametrize("change", [
    {"root":"QQQ"}, {"root":None}, {"root":"SPY\n"},
    {"schema":"wrong"}, {"session":"2026-02-30", "cells":[], "spot":None},
])
def test_existing_head_supplied_identity_is_strict(tmp_path, change):
    import scripts.build_options_matrix as builder
    path = tmp_path / "SPY.json"
    doc = payload(); doc.update(change)
    raw = json.dumps(doc).encode(); path.write_bytes(raw)
    session, error = builder._existing_usable_session(path)
    assert session is None and error is not None
    assert path.read_bytes() == raw
