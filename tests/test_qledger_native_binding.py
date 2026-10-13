"""Synthetic integration of the inactive claims binding and incumbent owners."""

import asyncio
from contextlib import contextmanager
from dataclasses import replace
from hashlib import sha256
import json
from pathlib import Path

import pytest

from engine import qledger as q
from engine import qledger_store as s
from engine import qledger_store_native as n
from engine import qledger_store_protocol as p


@pytest.fixture
def limits():
    return p.ProtocolLimits(
        base_bytes=262144, part_bytes=4096, page_bytes=8192, root_bytes=4096,
        descriptor_bytes=2048, leaf_entries=4, fanout=4, index_levels=3,
        history_operations=32, reference_visits=4096, snapshot_members=2048,
        snapshot_bytes=1048576, logical_bytes=262144, input_rows=1024,
        publication_objects=2048, git_blob_bytes=262144,
    )


def digest(data):
    return sha256(data).hexdigest()


def serialized(rows):
    return b"".join((json.dumps(row, ensure_ascii=False) + "\n").encode() for row in rows)


def verified(raw, limits):
    ref = p.MemberRef(p.BASE_PATH, digest(raw), len(raw))
    record = p.RootRecord(ref, None, 0, len(raw), digest(raw), limits.fingerprint)
    source = p.InMemorySource({p.BASE_PATH: raw}, snapshot_id="fixture:" + digest(raw))
    return p.verify_snapshot(source, record, limits=limits)


def logical(snapshot):
    with p.open_logical_bytes(snapshot) as handle:
        return handle.read()


class RetainedBinding:
    def __init__(self, path, *snapshots):
        self.claims_path = path
        self.snapshots = snapshots
        self.reads = 0

    def read_snapshot(self):
        index = min(self.reads, len(self.snapshots) - 1)
        self.reads += 1
        value = self.snapshots[index]
        if isinstance(value, Exception):
            raise value
        return value


@pytest.fixture
def registrar(monkeypatch):
    hooks = []

    def prepare(claim):
        if claim.get("prepare_error"):
            raise ValueError("synthetic preparation failure")
        return dict(claim)

    monkeypatch.setattr(q, "_prepare_claim", prepare)
    monkeypatch.setattr(q, "_start_control_clocks_for", lambda rows, root, today=None: hooks.append(list(rows)))
    return hooks


@contextmanager
def owner(tmp_path, limits, raw=b"", *, native, transaction_id="fixture-tx", session_factory=None):
    root = tmp_path / "repo"
    path = root / p.BASE_PATH
    path.parent.mkdir(parents=True)
    path.write_bytes(raw)
    if not native:
        yield root, None
        return
    snapshot = verified(raw, limits)
    (root / p.ROOT_PATH).write_bytes(snapshot.root_bytes)
    intent = n.NativeClaimsIntent("fixture-operation", "fixture-lane", transaction_id)
    binding = s._NativeClaimsBinding(path, intent=intent, limits=limits, session_factory=session_factory)
    with s._synthetic_claims_binding(path, binding):
        yield root, binding


def test_production_selection_is_unconditionally_legacy_and_no_io(tmp_path, monkeypatch):
    path = tmp_path / p.BASE_PATH
    marker = object()
    selected = s._production_claims_binding(marker)
    assert isinstance(selected, s.LegacyClaimsBinding) and selected.claims_path is marker
    for method in ("exists", "is_file", "open", "read_text", "read_bytes", "resolve"):
        monkeypatch.setattr(Path, method, lambda *a, **k: pytest.fail("selector performed I/O"))
    assert not s.uses_native_claims(path)
    assert isinstance(s._production_claims_binding(path), s.LegacyClaimsBinding)


def test_private_selection_is_context_local_without_reading_its_source(tmp_path, limits):
    path = tmp_path / p.BASE_PATH
    binding = RetainedBinding(path, verified(b"", limits))
    with s._synthetic_claims_binding(path, binding):
        assert s.uses_native_claims(path)
        assert binding.reads == 0
        assert isinstance(s._production_claims_binding(path), s.LegacyClaimsBinding)
    assert not s.uses_native_claims(path)


@pytest.mark.parametrize("raw", [
    b"", b"one\n\nmalformed\nnull\nfalse\n1\n[]\n", b'{"id":1}\n{"id":1}\n',
    b"one\rtwo\r\nthree\n", "one\u2028two\u0085three\n".encode(),
])
def test_native_eager_and_json_policies_match_legacy_exactly(raw, tmp_path, limits):
    path = tmp_path / p.BASE_PATH
    path.parent.mkdir(parents=True)
    path.write_bytes(raw)
    expected_lines, expected_rows = s.read_raw_lines(path), s.read_legacy_rows(path)
    binding = RetainedBinding(path, verified(raw, limits))
    with s._synthetic_claims_binding(path, binding):
        assert s.read_raw_lines(path) == expected_lines
        assert s.read_legacy_rows(path) == expected_rows
        assert s.read_raw_lines(path, encoding=None) == path.read_text(encoding=None).splitlines()


def test_legacy_missing_errors_encoding_and_callback_identity_stay_exact(tmp_path):
    path = tmp_path / "missing"
    assert s.read_raw_lines(path) == []
    with pytest.raises(FileNotFoundError):
        s.read_raw_lines(path, missing_ok=False)
    with pytest.raises(FileNotFoundError):
        with s.open_raw_lines(path):
            pass
    path.write_bytes(b"\xff")
    with pytest.raises(UnicodeDecodeError):
        s.read_raw_lines(path)
    result = (None, "legacy exact source")
    calls = []
    root, relative = object(), object()

    def callback(a, b):
        calls.append((a, b))
        return result

    assert s.read_tracked_claims_text(root, relative, legacy_reader=callback) is result
    assert calls == [(root, relative)]


@pytest.mark.parametrize("native", [False, True])
def test_physical_stream_line_decoding_and_exception_closure(native, tmp_path, limits):
    raw = "one\u2028inside\r\ntwo\rthree\n".encode()
    with owner(tmp_path, limits, raw, native=native) as (root, _):
        path = root / p.BASE_PATH
        with pytest.raises(RuntimeError):
            with s.open_raw_lines(path) as handle:
                assert next(handle) == "one\u2028inside\n"
                assert next(handle) == "two\n"
                raise RuntimeError("synthetic consumer failure")
        assert handle.closed


def test_native_source_failure_precedes_parser_and_never_uses_registry_fallback(tmp_path, limits, monkeypatch):
    path = tmp_path / p.BASE_PATH
    failure = p.SnapshotIntegrityError("HASH_MISMATCH", "synthetic incomplete source")
    binding = RetainedBinding(path, failure)
    monkeypatch.setattr(s, "_legacy_rows_from_lines", lambda *a, **k: pytest.fail("parser ran on a failed source"))
    with s._synthetic_claims_binding(path, binding):
        with pytest.raises(p.SnapshotIntegrityError) as caught:
            s.read_legacy_rows(path)
        assert caught.value is failure
        with pytest.raises(p.SnapshotIntegrityError) as caught:
            s.read_tracked_claims_text(tmp_path, Path(p.BASE_PATH), legacy_reader=lambda *a: pytest.fail("native fallback"))
        assert caught.value is failure
        with pytest.raises(p.SnapshotIntegrityError):
            with s.ClaimsReadScope(tmp_path):
                pytest.fail("failed source entered scope")


def test_native_empty_and_unverified_results_are_not_physical_missing_or_unknown(tmp_path, limits):
    path = tmp_path / p.BASE_PATH
    good = RetainedBinding(path, verified(b"", limits))
    with s._synthetic_claims_binding(path, good):
        assert s.read_raw_lines(path, missing_ok=False) == []
        text, label = s.read_tracked_claims_text(tmp_path, Path(p.BASE_PATH), legacy_reader=lambda *a: pytest.fail("native fallback"))
        assert text == "" and label.startswith("qledger-native:fixture:")
    bad = RetainedBinding(path, {"complete": True})
    with s._synthetic_claims_binding(path, bad):
        with pytest.raises(p.SnapshotIntegrityError):
            with s.ClaimsReadScope(tmp_path):
                pass
    assert not s.uses_native_claims(path)


def test_nested_scopes_reuse_root_snapshot_and_binding_and_restore_after_errors(tmp_path, limits):
    root_a, root_b = tmp_path / "a", tmp_path / "b"
    a = RetainedBinding(root_a / p.BASE_PATH, verified(b"a\n", limits), verified(b"later\n", limits))
    b = RetainedBinding(root_b / p.BASE_PATH, verified(b"b\n", limits))
    different_a = RetainedBinding(root_a / p.BASE_PATH, verified(b"different\n", limits))
    with s._synthetic_claims_binding(a.claims_path, a), s._synthetic_claims_binding(b.claims_path, b):
        with s.ClaimsReadScope(root_a):
            assert s.read_raw_lines(a.claims_path) == ["a"]
            with s._synthetic_claims_binding(a.claims_path, different_a):
                with s.ClaimsReadScope(root_a):
                    assert s.read_raw_lines(a.claims_path) == ["a"]
            with pytest.raises(RuntimeError):
                with s.ClaimsReadScope(root_b):
                    assert s.read_raw_lines(b.claims_path) == ["b"]
                    assert s.read_raw_lines(a.claims_path) == ["a"]
                    raise RuntimeError("synthetic scope exit")
            assert s.read_raw_lines(a.claims_path) == ["a"]
        assert s.read_raw_lines(a.claims_path) == ["later"]
    assert a.reads == 2 and b.reads == 1 and different_a.reads == 0


def test_concurrent_same_root_scopes_have_task_local_retained_snapshots(tmp_path, limits):
    path = tmp_path / p.BASE_PATH
    binding = RetainedBinding(path, verified(b"first\n", limits), verified(b"second\n", limits))

    async def task():
        with s.ClaimsReadScope(tmp_path):
            before = s.read_raw_lines(path)
            await asyncio.sleep(0)
            assert s.read_raw_lines(path) == before
            return before

    async def run():
        return await asyncio.gather(task(), task())

    with s._synthetic_claims_binding(path, binding):
        assert asyncio.run(run()) == [["first"], ["second"]]
        assert binding.reads == 2
        with s.ClaimsReadScope(tmp_path):
            assert binding.reads == 3


@pytest.mark.parametrize("native", [False, True])
def test_registrar_keeps_first_existing_and_batch_result_slots(native, tmp_path, limits, registrar):
    rows = [{"claim_id": "existing", "value": "first"}, {"claim_id": "existing", "value": "later"}]
    with owner(tmp_path, limits, serialized(rows), native=native) as (root, binding):
        result = q.register_batch([
            {"claim_id": "existing", "value": "incoming"},
            {"claim_id": "new", "value": "first-new"},
            {"claim_id": "new", "value": "later-new"},
            {"prepare_error": True},
            {"claim_id": "last"},
        ], root)
        assert len(result) == 5 and result[0] == rows[0]
        assert result[1] is result[2] and result[1]["value"] == "first-new"
        assert result[3] == {"status": "error", "error": "synthetic preparation failure"}
        assert [row["claim_id"] for row in q.load_claims(root)] == ["existing", "existing", "new", "last"]
        assert len(registrar) == 1 and [row["claim_id"] for row in registrar[0]] == ["new", "last"]
        if native:
            assert binding.last_outcome.status == "materialized"
            assert binding.last_outcome.clock_status == "uncertain"


@pytest.mark.parametrize("native", [False, True])
def test_single_existing_return_and_intentional_duplicate_batch(native, tmp_path, limits, registrar):
    old = {"claim_id": "same", "value": "first"}
    with owner(tmp_path, limits, serialized([old]), native=native) as (root, binding):
        assert q.register({"claim_id": "same", "value": "new"}, root) == old
        assert registrar == []
        result = q.register_batch([old, old], root, dedupe=False)
        assert result == [old, old]
        assert q.load_claims(root) == [old, old, old]
        assert registrar == [[old, old]]


@pytest.mark.parametrize("native", [False, True])
def test_scalar_loader_values_are_not_normalized_for_registrar_dedupe(native, tmp_path, limits, registrar):
    with owner(tmp_path, limits, b"null\n[]\nfalse\n1\n", native=native) as (root, _):
        assert q.load_claims(root) == [None, [], False, 1]
        with pytest.raises(AttributeError):
            q.register({"claim_id": "new"}, root)
        assert not registrar


def test_legacy_preparation_mkdir_and_partial_write_timing(tmp_path, registrar):
    single = tmp_path / "single"
    with pytest.raises(ValueError):
        q.register({"prepare_error": True}, single)
    assert not (single / p.BASE_PATH).parent.exists()
    batch = tmp_path / "batch"
    assert q.register_batch([{"prepare_error": True}], batch)[0]["status"] == "error"
    assert (batch / p.BASE_PATH).parent.is_dir() and not (batch / p.BASE_PATH).exists()
    cycle = {}; cycle["cycle"] = cycle
    with pytest.raises(ValueError, match="Circular"):
        q.register_batch([{"claim_id": "first"}, {"claim_id": "broken", "cycle": cycle}], batch, dedupe=False)
    assert (batch / p.BASE_PATH).read_bytes() == serialized([{"claim_id": "first"}])
    assert registrar == []


@pytest.mark.parametrize("batch", [False, True])
def test_native_serialization_failure_is_structured_before_root_and_clock(batch, tmp_path, limits, registrar):
    with owner(tmp_path, limits, native=True) as (root, binding):
        original = (root / p.ROOT_PATH).read_bytes()
        cycle = {}; cycle["cycle"] = cycle
        bad = {"claim_id": "broken", "cycle": cycle}
        with pytest.raises(n.ClaimsStorageError) as caught:
            if batch:
                q.register_batch([{"claim_id": "first"}, bad], root, dedupe=False)
            else:
                q.register(bad, root, dedupe=False)
        assert caught.value.outcome.status == "failed_before_root"
        assert binding.last_outcome == caught.value.outcome
        assert (root / p.ROOT_PATH).read_bytes() == original
        assert q.load_claims(root) == [] and not registrar


def test_native_retry_keeps_stable_intent_and_never_restarts_clock(tmp_path, limits, registrar):
    row = {"claim_id": "same", "timestamp": "2026-10-09T00:00:00Z"}
    with owner(tmp_path, limits, native=True) as (root, binding):
        intent = binding.intent
        assert q.register(row, root, dedupe=False) == row
        assert binding.last_outcome.intent is intent
        assert binding.last_outcome.status == "materialized" and binding.last_outcome.clock_status == "uncertain"
        assert q.register(row, root, dedupe=False) == row
        assert binding.last_outcome.intent is intent
        assert binding.last_outcome.status == "already_applied"
        assert q.load_claims(root) == [row] and registrar == [[row]]


def test_writer_ignores_read_scope_for_fresh_dedupe_and_scope_stays_coherent(tmp_path, limits, registrar):
    with owner(tmp_path, limits, native=True) as (root, binding):
        with s.ClaimsReadScope(root):
            assert q.load_claims(root) == []
            first = q.register({"claim_id": "new", "value": "stored"}, root)
            assert q.load_claims(root) == []
            assert q.register({"claim_id": "new", "value": "different"}, root) == first
            with s.ClaimsReadScope(root):
                assert q.load_claims(root) == []
        assert q.load_claims(root) == [first]
        assert registrar == [[first]]


@pytest.mark.parametrize("native", [False, True])
def test_backfill_rewrites_all_parsed_rows_only_on_real_modification(native, tmp_path, limits, registrar, monkeypatch):
    rows = [
        {"claim_id": "fill", "asof": "covered", "vector_asof": None, "regime_stamp_basis": "pit_live"},
        {"claim_id": "keep", "asof": "covered", "vector_asof": "old", "regime_stamp_basis": "pit_live"},
        {"claim_id": "hk", "asof": "covered", "scope": {"key": "0005.HK"}, "vector_asof": None},
        {"claim_id": "pre", "asof": "before", "vector_asof": None},
    ]
    original = b"malformed\n" + serialized(rows)
    monkeypatch.setattr(q, "_regime_stamp_for_asof", lambda asof: {"vector_asof": "covered", "risk_mode": "mixed"} if asof == "covered" else {"vector_asof": None})
    with owner(tmp_path, limits, original, native=native) as (root, binding):
        result = q.backfill_regime_stamps(root)
        assert result == {"n_claims": 4, "n_backfilled": 1, "n_unstamped": 2, "n_precoverage": 1}
        expected = [dict(row) for row in rows]
        expected[0].update(vector_asof="covered", risk_mode="mixed", regime_stamp_basis="recomputed_history")
        assert q.load_claims(root) == expected and not registrar
        if native:
            assert (root / p.BASE_PATH).read_bytes() == original
            assert logical(binding.read_snapshot()) == serialized(expected)
            assert binding.last_outcome.status == "materialized"
            assert binding.last_outcome.clock_status == "not_attempted"
        else:
            assert (root / p.BASE_PATH).read_bytes() == serialized(expected)


@pytest.mark.parametrize("native", [False, True])
def test_backfill_noop_preserves_unparsed_raw_bytes(native, tmp_path, limits, registrar, monkeypatch):
    original = b"\nmalformed\n" + serialized([{"claim_id": "keep", "vector_asof": "old"}])
    monkeypatch.setattr(q, "_regime_stamp_for_asof", lambda *a: pytest.fail("stamped row recomputed"))
    with owner(tmp_path, limits, original, native=native) as (root, binding):
        before_root = (root / p.ROOT_PATH).read_bytes() if native else None
        assert q.backfill_regime_stamps(root)["n_backfilled"] == 0
        assert (root / p.BASE_PATH).read_bytes() == original and not registrar
        if native:
            assert (root / p.ROOT_PATH).read_bytes() == before_root
            assert logical(binding.read_snapshot()) == original and binding.last_outcome is None


def test_clock_attempt_survives_stronger_session_release_error(tmp_path, limits, registrar):
    class ReleaseFailure:
        def __init__(self, *args, **kwargs):
            self.session = n.NativeClaimsSession(*args, **kwargs)

        def __enter__(self):
            self.session.__enter__()
            return self.session

        def __exit__(self, *args):
            result = self.session.__exit__(*args)
            if self.session.last_outcome is not None:
                raise n.ClaimsStorageError(replace(
                    self.session.last_outcome, failure_code="SYNTHETIC_RELEASE",
                    failure_message="synthetic release receipt", reason="synthetic_release_failure",
                ))
            return result

    with owner(tmp_path, limits, native=True, session_factory=ReleaseFailure) as (root, binding):
        with pytest.raises(n.ClaimsStorageError) as caught:
            q.register({"claim_id": "new"}, root)
        outcome = caught.value.outcome
        assert outcome.status == "materialized" and outcome.root_visibility == "visible"
        assert outcome.failure_code == "SYNTHETIC_RELEASE" and outcome.clock_status == "uncertain"
        assert binding.last_outcome == outcome and registrar == [[{"claim_id": "new"}]]
        assert q.load_claims(root) == [{"claim_id": "new"}]


def test_native_backfill_rejects_changed_root_before_replacement(tmp_path, limits, registrar, monkeypatch):
    class ChangedRoot:
        def __init__(self, location, **kwargs):
            self.location = location
            self.session = n.NativeClaimsSession(location, **kwargs)

        def __enter__(self):
            self.session.__enter__()
            return self

        def __exit__(self, *args):
            return self.session.__exit__(*args)

        def read_snapshot(self):
            return self.session.read_snapshot()

        def replace_serialized_rows(self, rows, *, expected_view_digest):
            # Synthetic non-cooperating owner changes only this fixture's root.
            other = p.plan_append(self.read_snapshot(), transaction_id="external", serialized_rows=[b'{"claim_id":"external"}\n'], limits=limits)
            for path, value in other.members.items():
                target = self.location / path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(value)
            (self.location / p.ROOT_PATH).write_bytes(other.root_bytes)
            return self.session.replace_serialized_rows(rows, expected_view_digest=expected_view_digest)

    monkeypatch.setattr(q, "_regime_stamp_for_asof", lambda *a: {"vector_asof": "covered"})
    old = {"claim_id": "old", "asof": "covered", "vector_asof": None}
    with owner(tmp_path, limits, serialized([old]), native=True, session_factory=ChangedRoot) as (root, binding):
        with pytest.raises(n.ClaimsStorageError) as caught:
            q.backfill_regime_stamps(root)
        assert caught.value.outcome.status == "failed_before_root"
        assert binding.last_outcome == caught.value.outcome and not registrar
        assert q.load_claims(root) == [old, {"claim_id": "external"}]
