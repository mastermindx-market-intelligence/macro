"""Actual file/Parquet -> existing identity owner. All fixtures are synthetic."""
from __future__ import annotations

import hashlib
import inspect
import json
import os
from datetime import date, datetime
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from engine.entry_radar.replay import identity_observation_snapshot as adapter
from lib.dataos.identity import IdentityError, ReferenceReadReceipt, ReferenceSnapshot, VendorAliasTable
from tests import test_dataos_identity as f

NAMES = ("security_master.parquet", "vendor_aliases.parquet", "issuer_master.parquet",
         "issuer_migrations.parquet", "security_migrations.parquet")
START = f._OBS_T0 + 9_000_000_000
END = START + 1_000_000_000


def rectangular(rows):
    keys = list(dict.fromkeys(key for row in rows for key in row))
    return [{key: row.get(key) for key in keys} for row in rows]


def parquet_bytes(rows):
    table = pa.Table.from_pylist(rows) if rows else pa.table({"empty": pa.array([], type=pa.string())})
    sink = pa.BufferOutputStream()
    pq.write_table(table, sink)
    return sink.getvalue().to_pybytes()


def generation(root, *, state=None, original=None, history=None, rows=None, master=None):
    if original is None:
        original, history, rows, master = f._obs_base()
    if state is not None:
        history, rows = f._obs_append(original, history, rows, status=state)
    rows, master = rectangular(rows), rectangular(master)
    payloads = {name: parquet_bytes([]) for name in NAMES}
    payloads["vendor_aliases.parquet"] = parquet_bytes(rows)
    payloads["security_master.parquet"] = parquet_bytes(master)
    semantics = {"vendor_aliases.parquet": f._obs_rows_hash(rows),
                 "security_master.parquet": f._obs_rows_hash(master)}
    manifest = {name: {"sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw),
                       "semantic_sha256": semantics.get(name)} for name, raw in payloads.items()}
    pub = f._obs_seal({"schema": "mastermind.identity_publication.v1",
        "predecessor_receipt_sha256": None, "code_version": "3" * 40,
        "artifacts": manifest, "history_sha256": f._obs_hash(history)}, "generation_id")
    receipt = {"publication": pub, "identity_observations": history, "prospective_reference": original}
    root.mkdir(parents=True, exist_ok=True)
    for name, raw in payloads.items():
        (root / name).write_bytes(raw)
    (root / "_receipt.json").write_bytes(f._obs_json(receipt))
    return original, history, rows, master


def reseal(root, name, data, *, semantic=None):
    p = root / "_receipt.json"
    receipt = json.loads(p.read_bytes())
    (root / name).write_bytes(data)
    entry = receipt["publication"]["artifacts"][name]
    entry.update(sha256=hashlib.sha256(data).hexdigest(), bytes=len(data))
    if semantic is not None:
        entry["semantic_sha256"] = semantic
    receipt["publication"] = f._obs_seal(receipt["publication"], "generation_id")
    p.write_bytes(f._obs_json(receipt))


@pytest.fixture
def prepared(tmp_path, monkeypatch):
    root = tmp_path / "reference"
    generation(root)
    times = iter((START, END))
    monkeypatch.setattr(adapter.time, "time_ns", lambda: next(times))
    return root


def lookup(read, ns=END, symbol="MU"):
    return read.alias_table().resolve_binding("polygon", symbol, date(2026, 10, 7),
        decision_at=f._obs_iso(ns), snapshot_receipts=(read.receipt,))


def test_real_parquet_read_returns_existing_types_and_actual_clock(prepared):
    observed = adapter.read_identity_snapshot(prepared)
    assert type(observed.snapshot) is ReferenceSnapshot
    assert type(observed.receipt) is ReferenceReadReceipt
    assert observed.receipt.read_started_at_utc_ns == str(START)
    assert observed.receipt.read_completed_at_utc_ns == str(END)
    assert lookup(observed).security_id == "SEC:US-XNAS-MU"
    assert lookup(observed, END - 1).reason == "NO_ENROLLED_SNAPSHOT_BY_CUTOFF"
    assert lookup(observed, symbol="SPY").status == "REFUSED"


def test_hashes_are_exact_actual_bytes_not_display_or_mtime(prepared):
    before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in prepared.iterdir()}
    os.utime(prepared / "_receipt.json", (1, 1))
    observed = adapter.read_identity_snapshot(prepared)
    assert observed.receipt.receipt_sha256 == before["_receipt.json"]
    assert dict(observed.receipt.artifact_sha256) == {n: before[n] for n in NAMES}
    assert {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in prepared.iterdir()} == before
    assert observed.receipt.read_completed_at_utc_ns == str(END)


def test_no_public_clock_override_or_fallback(prepared):
    assert list(inspect.signature(adapter.read_identity_snapshot).parameters) == ["directory"]
    with pytest.raises(TypeError):
        adapter.read_identity_snapshot(prepared, known_at="2000-01-01T00:00:00Z")
    old = json.loads((prepared / "_receipt.json").read_bytes())
    del old["identity_observations"]
    del old["publication"]
    (prepared / "_receipt.json").write_bytes(f._obs_json(old))
    with pytest.raises(IdentityError, match="snapshot owner context missing"):
        adapter.read_identity_snapshot(prepared)


@pytest.mark.parametrize("missing", ["_receipt.json", *NAMES])
def test_missing_member_refuses_whole_snapshot(prepared, missing):
    (prepared / missing).unlink()
    with pytest.raises(IdentityError, match="unavailable"):
        adapter.read_identity_snapshot(prepared)


def test_torn_before_after_receipt_is_refused(prepared, monkeypatch):
    original = adapter._read_file
    calls = []
    def changing(fd, name, limit):
        value = original(fd, name, limit)
        calls.append(name)
        if name == "_receipt.json" and calls.count(name) == 2:
            return value + b" "
        return value
    monkeypatch.setattr(adapter, "_read_file", changing)
    with pytest.raises(IdentityError, match="receipt changed during read"):
        adapter.read_identity_snapshot(prepared)
    assert calls == ["_receipt.json", *NAMES, "_receipt.json"]


def test_parquet_is_decoded_from_read_bytes_without_second_file_open(prepared, monkeypatch):
    original = adapter._read_file
    calls = []
    def recording(fd, name, limit):
        calls.append(name)
        return original(fd, name, limit)
    monkeypatch.setattr(adapter, "_read_file", recording)
    adapter.read_identity_snapshot(prepared)
    assert calls == ["_receipt.json", *NAMES, "_receipt.json"]


def test_valid_parquet_byte_tamper_and_semantic_mismatch_refuse(prepared):
    changed = parquet_bytes([{"vendor": "store", "vendor_symbol": "BAD"}])
    (prepared / "vendor_aliases.parquet").write_bytes(changed)
    with pytest.raises(IdentityError, match="artifact byte"):
        adapter.read_identity_snapshot(prepared)


def test_resealed_but_wrong_semantic_records_refuse(prepared):
    raw = (prepared / "vendor_aliases.parquet").read_bytes()
    reseal(prepared, "vendor_aliases.parquet", raw, semantic="f" * 64)
    with pytest.raises(IdentityError, match="semantic record seal"):
        adapter.read_identity_snapshot(prepared)


def test_invalid_parquet_does_not_fall_back_to_a_legacy_lookup(prepared):
    reseal(prepared, "vendor_aliases.parquet", b"not parquet")
    with pytest.raises(IdentityError, match="Parquet"):
        adapter.read_identity_snapshot(prepared)


def test_sparse_oversize_file_is_refused_before_reading(prepared):
    with (prepared / "vendor_aliases.parquet").open("wb") as stream:
        stream.truncate(64 * 1024 * 1024 + 1)
    with pytest.raises(IdentityError, match="byte bound"):
        adapter.read_identity_snapshot(prepared)


@pytest.mark.parametrize("target", ["root", "vendor_aliases.parquet"])
def test_symlink_boundary_refuses(prepared, target):
    if target == "root":
        alias = prepared.parent / "alias"
        alias.symlink_to(prepared, target_is_directory=True)
        root = alias
    else:
        source = prepared / target
        backup = prepared.parent / "elsewhere.parquet"
        source.rename(backup)
        source.symlink_to(backup)
        root = prepared
    with pytest.raises(IdentityError, match="unavailable"):
        adapter.read_identity_snapshot(root)


def test_nonregular_input_refuses_without_waiting_for_writer(prepared):
    file = prepared / "issuer_master.parquet"
    file.unlink()
    os.mkfifo(file)
    with pytest.raises(IdentityError, match="regular file"):
        adapter.read_identity_snapshot(prepared)


@pytest.mark.parametrize("ticks", [(END, START), (True, END), (START, 2**63)])
def test_bad_actual_clock_fails_closed(prepared, monkeypatch, ticks):
    times = iter(ticks)
    monkeypatch.setattr(adapter.time, "time_ns", lambda: next(times))
    with pytest.raises(IdentityError, match="clock"):
        adapter.read_identity_snapshot(prepared)


def test_read_preceding_owner_clock_cannot_create_usable_receipt(prepared, monkeypatch):
    times = iter((f._OBS_T0 - 2, f._OBS_T0 - 1))
    monkeypatch.setattr(adapter.time, "time_ns", lambda: next(times))
    with pytest.raises(IdentityError, match="owner observation"):
        adapter.read_identity_snapshot(prepared)


def test_old_read_receipt_cannot_authorize_new_snapshot(prepared, monkeypatch):
    old = adapter.read_identity_snapshot(prepared)
    generation(prepared, state="BOUND")
    times = iter((END + 10, END + 20))
    monkeypatch.setattr(adapter.time, "time_ns", lambda: next(times))
    new = adapter.read_identity_snapshot(prepared)
    with pytest.raises(IdentityError, match="no exact snapshot"):
        new.alias_table().resolve_binding("polygon", "MU", date(2026, 10, 7),
            decision_at=f._obs_iso(END + 20), snapshot_receipts=(old.receipt,))


def test_later_refusal_and_older_view_use_native_selector(tmp_path, monkeypatch):
    root = tmp_path / "reference"
    original, history, rows, master = generation(root, state="BOUND")
    times = iter((START, END, END + 10, END + 20))
    monkeypatch.setattr(adapter.time, "time_ns", lambda: next(times))
    old = adapter.read_identity_snapshot(root)
    history, rows = f._obs_append(original, history, rows, status="REFUSED")
    generation(root, original=original, history=history, rows=rows, master=master)
    new = adapter.read_identity_snapshot(root)
    table = VendorAliasTable.from_records(json.loads(new.snapshot.alias_json),
        observation_history=history, original_reference=original,
        snapshot_contexts=(old.snapshot, new.snapshot))
    def query(cutoff):
        return table.resolve_binding("polygon", "MU", date(2026, 10, 7),
            decision_at=f._obs_iso(cutoff), snapshot_receipts=(old.receipt, new.receipt))
    assert query(END).status == "BOUND"
    assert query(END + 19).status == "BOUND"
    assert query(END + 20).status == "REFUSED"


def test_nanosecond_timestamp_and_nullable_fields_preserve_meaning(prepared):
    raw = (prepared / "security_master.parquet").read_bytes()
    table = pq.read_table(pa.BufferReader(raw))
    values = [f._OBS_T0 + 123] + [None] * (table.num_rows - 1)
    table = table.append_column("observed_clock", pa.array(values, type=pa.timestamp("ns", tz="UTC")))
    semantic = table.drop(["observed_clock"]).to_pylist()
    for row, value in zip(semantic, values):
        row["observed_clock"] = f._obs_iso(value) if value is not None else None
    sink = pa.BufferOutputStream(); pq.write_table(table, sink)
    reseal(prepared, "security_master.parquet", sink.getvalue().to_pybytes(),
        semantic=f._obs_rows_hash(semantic))
    observed = adapter.read_identity_snapshot(prepared)
    assert json.loads(observed.snapshot.master_json)[0:]
    found = [r["observed_clock"] for r in json.loads(observed.snapshot.master_json) if r["observed_clock"]]
    assert found == [f._obs_iso(f._OBS_T0 + 123)]


def test_nonmidnight_validity_timestamp_refuses_instead_of_truncating(prepared):
    table = pq.read_table(pa.BufferReader((prepared / "vendor_aliases.parquet").read_bytes()))
    values = pa.array([f._OBS_T0 + 123] * table.num_rows, type=pa.timestamp("ns"))
    table = table.set_column(table.column_names.index("valid_from"), "valid_from", values)
    sink = pa.BufferOutputStream(); pq.write_table(table, sink)
    reseal(prepared, "vendor_aliases.parquet", sink.getvalue().to_pybytes())
    with pytest.raises(IdentityError, match="date-only"):
        adapter.read_identity_snapshot(prepared)


def test_naive_known_time_is_not_assumed_utc(prepared):
    table = pq.read_table(pa.BufferReader((prepared / "vendor_aliases.parquet").read_bytes()))
    values = pa.array([f._OBS_T0] * table.num_rows, type=pa.timestamp("ns"))
    table = table.set_column(table.column_names.index("known_at"), "known_at", values)
    sink = pa.BufferOutputStream(); pq.write_table(table, sink)
    reseal(prepared, "vendor_aliases.parquet", sink.getvalue().to_pybytes())
    with pytest.raises(IdentityError, match="timezone"):
        adapter.read_identity_snapshot(prepared)


def test_duplicate_columns_and_nested_values_are_not_silently_projected(prepared):
    table = pa.Table.from_arrays([pa.array([1]), pa.array([2])], names=["same", "same"])
    sink = pa.BufferOutputStream(); pq.write_table(table, sink)
    reseal(prepared, "vendor_aliases.parquet", sink.getvalue().to_pybytes())
    with pytest.raises(IdentityError, match="column"):
        adapter.read_identity_snapshot(prepared)


def test_successful_read_has_no_implicit_binding_without_receipt(prepared):
    read = adapter.read_identity_snapshot(prepared)
    result = read.alias_table().resolve_binding("polygon", "MU", date(2026, 10, 7),
        decision_at=f._obs_iso(END))
    assert result.status == "UNAVAILABLE"
    assert result.reason == "NO_ENROLLED_SNAPSHOT_BY_CUTOFF"


@pytest.mark.parametrize("rows", [[{"nested": [1]}], [{"value": float("nan")}], [{"payload": b"raw"}]])
def test_unsupported_or_nonfinite_parquet_values_refuse(prepared, rows):
    reseal(prepared, "vendor_aliases.parquet", parquet_bytes(rows))
    with pytest.raises(IdentityError, match="unsupported|nonfinite"):
        adapter.read_identity_snapshot(prepared)


def test_row_bound_is_checked_before_decoding_batches(prepared, monkeypatch):
    sink = pa.BufferOutputStream()
    pq.write_table(pa.table({"value": pa.array([0] * 100_001)}), sink)
    reseal(prepared, "vendor_aliases.parquet", sink.getvalue().to_pybytes())
    def forbidden(*args, **kwargs):
        raise AssertionError("oversize input must not begin batch decoding")
    monkeypatch.setattr(pq.ParquetFile, "iter_batches", forbidden)
    with pytest.raises(IdentityError, match="row bound"):
        adapter.read_identity_snapshot(prepared)


def test_duplicate_receipt_keys_refuse(prepared):
    p = prepared / "_receipt.json"
    raw = p.read_bytes()
    p.write_bytes(b'{"publication":null,' + raw[1:])
    with pytest.raises(IdentityError, match="unreadable JSON") as failure:
        adapter.read_identity_snapshot(prepared)
    assert isinstance(failure.value.__cause__, IdentityError)
    assert str(failure.value.__cause__).endswith("duplicate JSON key")


def test_file_growth_during_read_is_not_accepted(prepared, monkeypatch):
    original = adapter.os.read
    changed = False
    def grows(fd, length):
        nonlocal changed
        data = original(fd, length)
        if not changed:
            changed = True
            with (prepared / "_receipt.json").open("ab") as handle:
                handle.write(b" ")
        return data
    monkeypatch.setattr(adapter.os, "read", grows)
    with pytest.raises(IdentityError, match="changed during read"):
        adapter.read_identity_snapshot(prepared)


def test_midnight_timestamp_validity_matches_native_date_contract(prepared):
    raw = (prepared / "vendor_aliases.parquet").read_bytes()
    table = pq.read_table(pa.BufferReader(raw))
    rows = table.to_pylist()
    values = [None if row["valid_from"] is None else
              datetime.fromisoformat(row["valid_from"]) for row in rows]
    table = table.set_column(table.column_names.index("valid_from"), "valid_from",
        pa.array(values, type=pa.timestamp("ns")))
    sink = pa.BufferOutputStream(); pq.write_table(table, sink)
    reseal(prepared, "vendor_aliases.parquet", sink.getvalue().to_pybytes())
    read = adapter.read_identity_snapshot(prepared)
    assert lookup(read).status == "BOUND"


def test_real_clock_not_patched_produces_no_historical_availability(tmp_path):
    root = tmp_path / "reference"
    generation(root)
    begin = adapter.time.time_ns()
    read = adapter.read_identity_snapshot(root)
    finished = adapter.time.time_ns()
    assert begin <= int(read.receipt.read_started_at_utc_ns)
    assert int(read.receipt.read_started_at_utc_ns) <= int(read.receipt.read_completed_at_utc_ns) <= finished
    assert lookup(read, f._OBS_T0 + 100_000).reason == "NO_ENROLLED_SNAPSHOT_BY_CUTOFF"


@pytest.mark.parametrize("directory", ["https://example.invalid/reference", "relative/reference", 2, b"/tmp", Path("/tmp/../root")])
def test_no_remote_relative_or_coerced_root(directory):
    with pytest.raises(IdentityError, match="absolute local"):
        adapter.read_identity_snapshot(directory)


@pytest.fixture
def legacy(tmp_path):
    root = tmp_path / "legacy"
    generation(root)
    (root / "_receipt.json").write_bytes(b'{"generated_at":"synthetic legacy fixture"}')
    return root


def test_legacy_complete_bytes_are_immutable_and_have_no_clock(legacy, monkeypatch):
    from dataclasses import FrozenInstanceError
    def forbidden():
        raise AssertionError("LEGACY acquisition must not sample a clock")
    monkeypatch.setattr(adapter.time, "time_ns", forbidden)
    read = adapter.read_reference_generation(legacy)
    assert read.mode == "LEGACY"
    assert read.receipt_bytes == (legacy / "_receipt.json").read_bytes()
    assert dict(read.artifact_bytes) == {n: (legacy / n).read_bytes() for n in NAMES}
    with pytest.raises(FrozenInstanceError):
        read.mode = "NATIVE"
    old = dict(read.artifact_bytes)[NAMES[0]]
    (legacy / NAMES[0]).write_bytes(b"later synthetic bytes")
    assert dict(read.artifact_bytes)[NAMES[0]] == old


def test_legacy_root_shared_lock_excludes_incumbent_writer_and_covers_every_read(legacy, monkeypatch):
    import fcntl
    fd = os.open(legacy, os.O_RDONLY | os.O_DIRECTORY)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with pytest.raises(IdentityError, match="busy"):
            adapter.read_reference_generation(legacy)
        fcntl.flock(fd, fcntl.LOCK_UN)
        original = adapter._read_file
        calls = []
        def under_lock(directory_fd, name, limit):
            with pytest.raises(BlockingIOError):
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            calls.append(name)
            return original(directory_fd, name, limit)
        monkeypatch.setattr(adapter, "_read_file", under_lock)
        adapter.read_reference_generation(legacy)
        assert calls == ["_receipt.json", *NAMES, "_receipt.json"]
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    finally:
        os.close(fd)


def test_native_readback_preserves_incumbent_writer_owned_lock_behavior(prepared):
    import fcntl
    # The actual writer performs native readback while holding EX on a separate
    # descriptor. Native acquisition must not introduce a competing SH lock.
    fd = os.open(prepared, os.O_RDONLY | os.O_DIRECTORY)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        observed = adapter.read_identity_snapshot(prepared)
        assert lookup(observed).security_id == "SEC:US-XNAS-MU"
        with pytest.raises(IdentityError, match="busy"):
            adapter.read_reference_generation(prepared)
    finally:
        os.close(fd)


@pytest.mark.parametrize("defect", ["missing", "symlink", "oversize", "fifo", "torn", "root_replaced"])
def test_legacy_acquisition_refuses_incomplete_or_unstable_input(legacy, monkeypatch, defect):
    member = legacy / NAMES[0]
    if defect == "missing":
        member.unlink()
    elif defect == "symlink":
        other = legacy.parent / "other"
        member.rename(other)
        member.symlink_to(other)
    elif defect == "oversize":
        with member.open("wb") as stream:
            stream.truncate(64 * 1024 * 1024 + 1)
    elif defect == "fifo":
        member.unlink()
        os.mkfifo(member)
    else:
        original = adapter._read_file
        count = 0
        def unstable(fd, name, limit):
            nonlocal count
            raw = original(fd, name, limit)
            if name == "_receipt.json":
                count += 1
                if count == 2:
                    if defect == "torn":
                        return raw + b" "
                    legacy.rename(legacy.parent / "moved")
                    legacy.mkdir()
            return raw
        monkeypatch.setattr(adapter, "_read_file", unstable)
    with pytest.raises(IdentityError):
        adapter.read_reference_generation(legacy)


@pytest.mark.parametrize("raw", [b"[]", b'{"x":1,"x":2}', b'{"x":NaN}', b"not JSON",
                                  b'{"publication":null}', b'{"identity_observations":null}'])
def test_legacy_receipt_never_falls_back_from_native_or_invalid_context(legacy, raw):
    (legacy / "_receipt.json").write_bytes(raw)
    with pytest.raises(IdentityError):
        adapter.read_reference_generation(legacy)


def test_legacy_refuses_native_layout_without_reading_pointer_or_control(legacy, monkeypatch):
    (legacy / ".identity").mkdir()
    def forbidden(*args):
        raise AssertionError("native layout must refuse before reading artifacts")
    monkeypatch.setattr(adapter, "_read_file", forbidden)
    with pytest.raises(IdentityError, match="native"):
        adapter.read_reference_generation(legacy)
