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
    with pytest.raises(sqlite3.DatabaseError):
        owner.prepare()
    assert owner._selected is None
    bounded = QualifiedReadProvider(store, expected_producer_commit=fixture.COMMIT,
        clock=lambda: now[0], writer_policy=lambda: True, corpus_byte_budget=4)
    with pytest.raises(SelectedReadUnavailable):
        bounded.prepare()


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
