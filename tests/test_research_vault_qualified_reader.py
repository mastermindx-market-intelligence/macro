"""Actual canonical SQLite/read-service binding; no remote or readiness proof."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
import sqlite3
import threading

import pytest
from tests import test_research_vault_producer_generation as fixture
from engine.research_vault import catalog, corpus, producer_generation as generation
from engine.research_vault.qualified_reader import QualifiedReadProvider, SelectedReadUnavailable
from engine.research_vault.read_runtime import build_qualified_read_service
from engine.research_vault.read_service import ServerReadContext


def test_refresh_keeps_valid_reads_available_during_full_census(prepared, monkeypatch):
    owner, store, now, policy = prepared
    original = generation.explained_selection
    entered, release = threading.Event(), threading.Event()
    def delayed(*args, **kwargs):
        entered.set()
        assert release.wait(3)
        return original(*args, **kwargs)
    monkeypatch.setattr(generation, "explained_selection", delayed)
    old = owner.run(lambda: "old")
    store.reads.clear()
    now[0] += 1
    with ThreadPoolExecutor(max_workers=1) as pool:
        pending = pool.submit(owner.refresh)
        try:
            assert entered.wait(1)
            assert owner.run(lambda: "still available").value == "still available"
            old.delivery_guard()
            assert all(kind == "versioned" for kind, _ in store.reads)
        finally:
            release.set()
        pending.result(timeout=3)
    assert owner.run(lambda: "new").value == "new"
    with pytest.raises(SelectedReadUnavailable, match="replaced"):
        old.delivery_guard()
    assert store.reads.count(("corpus", "*")) == 1


def test_refresh_waits_for_active_operation_before_corpus_allocation(prepared, monkeypatch):
    owner, store, now, policy = prepared
    active, release = threading.Event(), threading.Event()
    corpus_read = threading.Event()
    original = store.get_bytes_strict_bounded
    def read(key, bound):
        if key == generation.CORPUS_KEY:
            corpus_read.set()
        return original(key, bound)
    monkeypatch.setattr(store, "get_bytes_strict_bounded", read)
    def operation():
        active.set()
        assert release.wait(3)
        return "settled"
    with ThreadPoolExecutor(max_workers=2) as pool:
        running = pool.submit(owner.run, operation)
        assert active.wait(1)
        refreshing = pool.submit(owner.refresh)
        try:
            with owner._drained:
                assert owner._drained.wait_for(lambda: owner._refresh_exclusive, timeout=1)
            assert not corpus_read.is_set()
            with pytest.raises(SelectedReadUnavailable, match="refresh_image_transition"):
                owner.run(lambda: pytest.fail("new operation started during transition"))
        finally:
            release.set()
        assert running.result(timeout=3).value == "settled"
        refreshing.result(timeout=3)
    assert corpus_read.is_set()
    assert owner._active == owner._guard_active == owner._refresh_reserved == 0
    assert not owner._refresh_exclusive


def test_failed_refresh_keeps_an_independently_valid_selection(prepared, monkeypatch):
    owner, store, now, policy = prepared
    previous, stamp = owner._selected, owner._prepared_at
    monkeypatch.setattr(generation, "explained_selection", lambda *a, **k: (None, {"code": "fixture_refusal"}))
    with pytest.raises(SelectedReadUnavailable, match="fixture_refusal"):
        owner.refresh()
    assert owner._selected is previous and owner._prepared_at == stamp
    assert owner._refresh_reserved == 0 and not owner._refresh_exclusive
    assert owner.run(lambda: "valid").value == "valid"


def test_refresh_reserves_raw_capacity_before_corpus_read(prepared):
    owner, store, now, policy = prepared
    prior = owner._selected
    retained = len(prior.catalog_bytes) + len(prior.corpus_bytes)
    owner.corpus_byte_budget = len(prior.corpus_bytes)
    owner.image_admission_bytes = retained + 2 * generation.CATALOG_MAX_BYTES + owner.corpus_byte_budget - 1
    store.reads.clear()
    with pytest.raises(SelectedReadUnavailable, match="image_admission_exceeded"):
        owner.refresh()
    assert ("corpus", "*") not in store.reads
    assert owner._selected is prior
    assert owner._refresh_reserved == 0 and not owner._refresh_exclusive


def test_refresh_cannot_self_extend_or_resurrect_expired_cache(prepared):
    owner, store, now, policy = prepared
    with pytest.raises(SelectedReadUnavailable, match="nested"):
        owner.run(owner.refresh)
    now[0] += 301
    with pytest.raises(SelectedReadUnavailable):
        owner.run(lambda: None)
    assert owner._selected is None
    store.reads.clear()
    owner.refresh()
    assert store.reads.count(("corpus", "*")) == 1
    assert owner.run(lambda: "fully qualified").value == "fully qualified"


def test_refresh_drains_final_delivery_guard_before_corpus_read(prepared, monkeypatch):
    owner, store, now, policy = prepared
    result = owner.run(lambda: "body")
    entered, release, corpus_read = threading.Event(), threading.Event(), threading.Event()
    read_catalog = store.get_bytes_strict_bounded_versioned
    read_object = store.get_bytes_strict_bounded
    def catalog_read(*args):
        if threading.current_thread().name.startswith("held-guard"):
            entered.set()
            assert release.wait(3)
        return read_catalog(*args)
    def object_read(key, bound):
        if key == generation.CORPUS_KEY:
            corpus_read.set()
        return read_object(key, bound)
    monkeypatch.setattr(store, "get_bytes_strict_bounded_versioned", catalog_read)
    monkeypatch.setattr(store, "get_bytes_strict_bounded", object_read)
    with ThreadPoolExecutor(1, thread_name_prefix="held-guard") as guards, ThreadPoolExecutor(1) as refreshes:
        guard = guards.submit(result.delivery_guard)
        assert entered.wait(1)
        pending = refreshes.submit(owner.refresh)
        try:
            with owner._drained:
                assert owner._drained.wait_for(lambda: owner._refresh_exclusive, timeout=1)
            assert owner._guard_active == 1
            assert not corpus_read.is_set()
        finally:
            release.set()
        guard.result(timeout=3)
        pending.result(timeout=3)
    assert corpus_read.is_set()
    assert owner._guard_active == owner._refresh_reserved == 0


def test_refresh_drain_timeout_preserves_old_cut_and_releases_admission(prepared):
    owner, store, now, policy = prepared
    old, stamp = owner._selected, owner._prepared_at
    entered, release = threading.Event(), threading.Event()
    def hold():
        entered.set()
        assert release.wait(3)
    with ThreadPoolExecutor(1) as pool:
        operation = pool.submit(owner.run, hold)
        assert entered.wait(1)
        store.reads.clear()
        try:
            with pytest.raises(SelectedReadUnavailable, match="refresh_drain_timeout"):
                owner.refresh(drain_timeout_seconds=0.02)
            assert ("corpus", "*") not in store.reads
            assert owner._selected is old and owner._prepared_at == stamp
            assert owner._refresh_reserved == 0 and not owner._refresh_exclusive
            assert owner.run(lambda: "still valid").value == "still valid"
        finally:
            release.set()
        operation.result(timeout=3)
    owner.refresh()  # timed-out refresh released the preparation lock


def test_refresh_sqlite_capacity_refuses_before_opening_candidate(prepared, monkeypatch):
    from engine.research_vault import qualified_reader as reader
    owner, store, now, policy = prepared
    old = owner._selected
    raw = len(old.corpus_bytes)
    owner.corpus_byte_budget = raw
    owner.image_admission_bytes = len(old.catalog_bytes) + raw + 2 * generation.CATALOG_MAX_BYTES + 4 * raw - 1
    monkeypatch.setattr(reader, "_open_image", lambda _: pytest.fail("unadmitted SQLite image"))
    store.reads.clear()
    with pytest.raises(SelectedReadUnavailable, match="image_admission_exceeded"):
        owner.refresh()
    assert store.reads.count(("corpus", "*")) == 1
    assert owner._selected is old
    assert owner._refresh_reserved == 0 and not owner._refresh_exclusive


@pytest.mark.parametrize("change", ["source", "policy"])
def test_refresh_final_fence_and_policy_withhold_candidate(prepared, monkeypatch, change):
    from engine.research_vault import qualified_reader as reader
    owner, store, now, policy = prepared
    old, stamp = owner._selected, owner._prepared_at
    original = reader._open_image
    def changed(selected):
        conn = original(selected)
        if change == "source":
            store.set_object(catalog.CATALOG_KEY, store.objects[catalog.CATALOG_KEY])
        else:
            policy[0] = False
        return conn
    monkeypatch.setattr(reader, "_open_image", changed)
    with pytest.raises(SelectedReadUnavailable):
        owner.refresh()
    assert owner._selected is old and owner._prepared_at == stamp
    assert owner._refresh_reserved == 0 and not owner._refresh_exclusive
    with pytest.raises(SelectedReadUnavailable):
        owner.run(lambda: pytest.fail("invalid old selection served"))
    assert owner._selected is None


def test_refresh_reuse_clock_starts_after_full_sweep_sqlite_and_fence(prepared, monkeypatch):
    from engine.research_vault import qualified_reader as reader
    owner, store, now, policy = prepared
    full_sweep, image, fence = generation.explained_selection, reader._open_image, store.get_bytes_strict_bounded_versioned
    final_read = [False]
    def slow_sweep(*args, **kwargs):
        selected = full_sweep(*args, **kwargs)
        now[0] += 400
        return selected
    def slow_image(selected):
        conn = image(selected)
        now[0] += 10
        final_read[0] = True
        return conn
    def slow_fence(*args):
        value = fence(*args)
        if final_read[0]:
            now[0] += 5
            final_read[0] = False
        return value
    monkeypatch.setattr(generation, "explained_selection", slow_sweep)
    monkeypatch.setattr(reader, "_open_image", slow_image)
    monkeypatch.setattr(store, "get_bytes_strict_bounded_versioned", slow_fence)
    owner.refresh()
    assert owner._prepared_at == fixture.NOW + 415
    now[0] += 300
    assert owner.run(lambda: "full reuse window").value == "full reuse window"
    now[0] += 1
    with pytest.raises(SelectedReadUnavailable):
        owner.run(lambda: None)


def test_refresh_wrapper_preserves_qualified_r2_four_member_window(monkeypatch):
    from engine.research_vault.qualified_reader import _LimitedStore
    from engine.research_vault.r2_store import R2Store
    store = object.__new__(R2Store)
    store._receipt_reads_thread_safe = True
    wrapped = _LimitedStore(store, 1024, before_corpus_read=lambda: None)
    barrier = threading.Barrier(4)
    entered = []
    def member(*args):
        entered.append(threading.get_ident())
        barrier.wait(timeout=2)
    monkeypatch.setattr(generation, "_verify_member", member)
    generation._verify_members(wrapped, None, None, None, range(4))
    assert len(set(entered)) == 4


def test_policy_withdrawal_during_census_requires_a_later_full_refresh(prepared, monkeypatch):
    owner, store, now, policy = prepared
    entered, release = threading.Event(), threading.Event()
    verify = generation._verify_members
    def held_members(*args, **kwargs):
        verify(*args, **kwargs)
        entered.set()
        assert release.wait(3)
    monkeypatch.setattr(generation, "_verify_members", held_members)
    with ThreadPoolExecutor(1) as pool:
        pending = pool.submit(owner.refresh)
        try:
            assert entered.wait(1)
            policy[0] = False
            with pytest.raises(SelectedReadUnavailable):
                owner.run(lambda: pytest.fail("withdrawn policy served"))
            assert owner._selected is None
            policy[0] = True
        finally:
            release.set()
        with pytest.raises(SelectedReadUnavailable, match="refresh_policy_changed"):
            pending.result(timeout=3)
    assert owner._selected is None
    owner.refresh()  # a new full sweep after policy restoration is eligible
    assert owner.run(lambda: "fresh qualification").value == "fresh qualification"


@pytest.fixture
def prepared(tmp_path):
    path = tmp_path / "producer.sqlite"
    conn = corpus.open_db(path)
    item = dict(id="fixture-a", title="Alpha report", institution="Synthetic", side="sell",
                published_at=datetime.fromtimestamp(fixture.NOW - 50, timezone.utc).isoformat())
    corpus.upsert(conn, item, "alpha source text", facts={"content_sha256": "a" * 64,
                                                        "text_layer": "full"})
    conn.close()
    store = fixture.MemoryStore()
    record = fixture.build_generation(store, {"fixture-a": "full"})
    store.corpus = path.read_bytes()
    record["corpus_sha256"] = hashlib.sha256(store.corpus).hexdigest()
    document = json.loads(store.objects[catalog.CATALOG_KEY])
    document["items"] = [item]
    record["catalog_payload_sha256"] = generation.compute_catalog_payload_digest(document)
    document[generation.GENERATION_FIELD] = record
    store.set_object(catalog.CATALOG_KEY, json.dumps(document).encode())
    now, policy = [fixture.NOW], [True]
    owner = QualifiedReadProvider(store, expected_producer_commit=fixture.COMMIT,
                                  clock=lambda: now[0], writer_policy=lambda: policy[0])
    owner.prepare()
    return owner, store, now, policy


def test_actual_service_reads_selected_sqlite_and_catalog_not_old_cache(prepared, monkeypatch):
    owner, store, now, policy = prepared
    def forbidden(*a, **k):
        pytest.fail("incumbent mutable cache/open_db must not be used")
    monkeypatch.setattr(corpus, "corpus_connection", forbidden)
    monkeypatch.setattr(corpus, "open_db", forbidden)
    service = build_qualified_read_service(owner, clock=lambda: datetime.fromtimestamp(now[0], timezone.utc))
    context = ServerReadContext(principal_id="a" * 64, entitlement="pro",
                                scopes=frozenset({"status", "search"}), surface="mcp")
    result = owner.run(lambda: service.status(caller_context=context))
    assert result.value["ok"] is True
    assert result.value["full_text_coverage"] == 1.0
    result.delivery_guard()
    result = owner.run(lambda: service.search(caller_context=context, query="alpha", filters={}, limit=5, cursor=None))
    assert result.value["available"] is True
    assert [r["report_id"] for r in result.value["candidates"]] == ["fixture-a"]
    result.delivery_guard()
    assert owner._current.get() is None and owner._active == 0


def test_reuse_does_not_repeat_receipt_derivative_or_corpus_sweep(prepared):
    owner, store, now, policy = prepared
    store.reads.clear()
    for _ in range(3):
        result = owner.run(lambda: corpus.search(owner.connection(), "alpha"))
        assert result.value[0]["id"] == "fixture-a"
        result.delivery_guard()
    assert store.reads == [("versioned", catalog.CATALOG_KEY)] * 9


def test_default_policy_refuses_before_io(prepared):
    owner, store, now, policy = prepared
    store.reads.clear()
    closed = QualifiedReadProvider(store, expected_producer_commit=fixture.COMMIT, clock=lambda: now[0])
    with pytest.raises(SelectedReadUnavailable, match="writer_protocol_qualified_required"):
        closed.prepare()
    assert not store.reads


@pytest.mark.parametrize("boundary", ["before", "during", "after"])
def test_catalog_move_at_each_delivery_boundary_withholds_body(prepared, boundary):
    owner, store, now, policy = prepared
    def move():
        store.set_object(catalog.CATALOG_KEY, store.objects[catalog.CATALOG_KEY])
    if boundary == "before":
        move()
    def operation():
        result = corpus.search(owner.connection(), "alpha")
        if boundary == "during":
            move()
        return result
    if boundary == "after":
        result = owner.run(operation)
        move()  # e.g. the final awaited JWT check let the producer advance.
        with pytest.raises(SelectedReadUnavailable):
            result.delivery_guard()
    else:
        with pytest.raises(SelectedReadUnavailable):
            owner.run(operation)
    assert owner._selected is None
    assert owner._active == 0 and owner._current.get() is None


def test_observed_withdrawal_cannot_be_restored_into_cached_success(prepared):
    owner, store, now, policy = prepared
    policy[0] = False
    with pytest.raises(SelectedReadUnavailable):
        owner.run(lambda: "body")
    policy[0] = True
    with pytest.raises(SelectedReadUnavailable, match="not_prepared"):
        owner.run(lambda: "body")


@pytest.mark.parametrize("delta", [-1, 301, 4000])
def test_clock_and_reuse_expiration(prepared, delta):
    owner, store, now, policy = prepared
    now[0] += delta
    with pytest.raises(SelectedReadUnavailable):
        owner.run(lambda: "body")


def test_sql_writes_denied_and_original_image_preserved(prepared):
    owner, store, now, policy = prepared
    def operation():
        conn = owner.connection()
        for sql in ["DELETE FROM documents", "CREATE TABLE forged(x)",
                    "PRAGMA query_only=OFF", "ATTACH DATABASE ':memory:' AS extra"]:
            with pytest.raises(sqlite3.DatabaseError):
                conn.execute(sql)
        conn.close()  # borrow close preserves final image verification
        return corpus.search(owner.connection(), "alpha")
    assert owner.run(operation).value[0]["id"] == "fixture-a"


def test_exception_releases_connection_context_and_admission(prepared):
    owner, store, now, policy = prepared
    def broken():
        owner.connection()
        raise ValueError("controlled failure")
    with pytest.raises(ValueError, match="controlled"):
        owner.run(broken)
    assert owner._active == 0 and owner._inflight_bytes == 0
    assert owner._current.get() is None
    assert owner.run(lambda: corpus.search(owner.connection(), "alpha")).value


def test_concurrent_operations_have_distinct_connections_and_no_context_leak(prepared):
    owner, store, now, policy = prepared
    barrier = threading.Barrier(2)
    def query():
        conn = owner.connection()
        ident = id(conn._conn)
        barrier.wait(timeout=5)
        return ident, corpus.search(conn, "alpha")
    with ThreadPoolExecutor(2) as pool:
        jobs = [pool.submit(owner.run, query) for _ in range(2)]
        rows = [job.result(timeout=10) for job in jobs]
    assert rows[0].value[0] != rows[1].value[0]
    assert all(row.value[1][0]["id"] == "fixture-a" for row in rows)
    assert owner._active == 0 and owner._current.get() is None
    with pytest.raises(SelectedReadUnavailable):
        owner.connection()
    with pytest.raises(SelectedReadUnavailable):
        owner.catalog_store.get_bytes_strict(catalog.CATALOG_KEY)


def test_wrong_or_oversized_sqlite_is_unavailable_without_rebuilding(prepared):
    owner, store, now, policy = prepared
    store.corpus = b"not SQLite"
    record = json.loads(store.objects[catalog.CATALOG_KEY])
    record[generation.GENERATION_FIELD]["corpus_sha256"] = hashlib.sha256(store.corpus).hexdigest()
    store.set_object(catalog.CATALOG_KEY, json.dumps(record).encode())
    with pytest.raises(sqlite3.DatabaseError) as caught:
        owner.prepare()
    frames = []
    tb = caught.value.__traceback__
    while tb is not None:
        if tb.tb_frame.f_code.co_name == "prepare":
            frames.append(tb.tb_frame)
        tb = tb.tb_next
    assert len(frames) == 1 and frames[0].f_locals["selected"] is None
    assert owner._selected is None
    bounded = QualifiedReadProvider(store, expected_producer_commit=fixture.COMMIT,
        clock=lambda: now[0], writer_policy=lambda: True, corpus_byte_budget=4)
    with pytest.raises(SelectedReadUnavailable):
        bounded.prepare()


def test_refresh_uses_one_corpus_budget_for_reservation_and_read(prepared, monkeypatch):
    owner, store, now, policy = prepared
    old = owner._selected
    raw = len(old.corpus_bytes)
    owner.corpus_byte_budget = raw
    owner.image_admission_bytes = len(old.catalog_bytes) + raw + 2 * generation.CATALOG_MAX_BYTES + raw - 1
    original = generation.explained_selection
    def changed(*args, **kwargs):
        # The bounded store already captured its read ceiling. A later owner
        # setting cannot lower only its corresponding memory reservation.
        owner.corpus_byte_budget = 1
        return original(*args, **kwargs)
    monkeypatch.setattr(generation, "explained_selection", changed)
    store.reads.clear()
    with pytest.raises(SelectedReadUnavailable):
        owner.refresh()
    assert ("corpus", "*") not in store.reads
    assert owner._selected is old
    assert owner._refresh_reserved == 0 and not owner._refresh_exclusive


def test_image_admission_is_nonwaiting_and_does_not_change_existing_owner(prepared):
    owner, store, now, policy = prepared
    owner.image_admission_bytes = 1
    with pytest.raises(SelectedReadUnavailable, match="admission"):
        owner.run(lambda: "body")
    assert owner._active == 0 and owner._selected is not None


def test_store_ignoring_stricter_image_bound_cannot_admit_oversized_image(prepared):
    owner, store, now, policy = prepared
    original = store.get_bytes_strict_bounded
    store.get_bytes_strict_bounded = lambda key, bound: original(key, generation.CORPUS_MAX_BYTES)
    bounded = QualifiedReadProvider(store, expected_producer_commit=fixture.COMMIT,
        clock=lambda: now[0], writer_policy=lambda: True, corpus_byte_budget=1024)
    with pytest.raises(SelectedReadUnavailable):
        bounded.prepare()


def test_policy_withdrawn_during_final_fence_read_refuses_delivery(prepared):
    owner, store, now, policy = prepared
    result = owner.run(lambda: "sensitive result")
    original = store.get_bytes_strict_bounded_versioned
    def withdraw(key, bound):
        observed = original(key, bound)
        policy[0] = False
        return observed
    store.get_bytes_strict_bounded_versioned = withdraw
    with pytest.raises(SelectedReadUnavailable):
        result.delivery_guard()
    assert owner._selected is None


def test_reuse_window_begins_after_real_preparation_but_source_age_never_resets(prepared):
    owner, store, now, policy = prepared
    # A full bounded qualification sweep may take longer than the reuse window.
    # This is a fresh sweep, not renewal of a cached success timestamp.
    store.midflight = lambda _store: now.__setitem__(0, now[0] + 400)
    owner.prepare()
    assert owner.run(lambda: corpus.search(owner.connection(), 'alpha')).value
    now[0] += 301
    with pytest.raises(SelectedReadUnavailable):
        owner.run(lambda: 'body')
    # Repreparation cannot make a stale producer generation fresh.
    now[0] = fixture.COMPLETED_AT + owner.max_age_seconds + 1
    with pytest.raises(SelectedReadUnavailable):
        owner.prepare()
