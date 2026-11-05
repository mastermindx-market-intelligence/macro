"""Bounded scheduling proof; synthetic transports do not qualify production R2."""
from concurrent.futures import ThreadPoolExecutor
import threading

import pytest

from engine.research_vault import catalog, producer_generation as generation, r2_store
from engine.research_vault.qualified_reader import _LimitedStore
from engine.research_vault.r2_store import R2Store
from tests import test_research_vault_producer_generation as fixture


def exact_transport(memory=None, *, admitted=True):
    # Only scheduler tests use this unconstructed transport. No SDK/network call.
    store = object.__new__(R2Store)
    store._receipt_reads_thread_safe = admitted
    if memory is not None:
        store.get_bytes_strict_bounded = memory.get_bytes_strict_bounded
        store.get_bytes_strict_bounded_versioned = memory.get_bytes_strict_bounded_versioned
    return store


@pytest.mark.parametrize("wrapped", [False, True])
def test_four_member_overlap_has_bounded_admission(monkeypatch, wrapped):
    memory = fixture.MemoryStore()
    spec = fixture.spec_with(12, {"full": 12})
    fixture.build_generation(memory, spec)
    # Exercise the merged ordinary-client constructor admission, not a manually
    # asserted safety flag. Only the SDK transport and bytes are synthetic.
    monkeypatch.setattr(r2_store, "_r2_client", lambda: object())
    store = R2Store("synthetic-bucket")
    store.get_bytes_strict_bounded = memory.get_bytes_strict_bounded
    store.get_bytes_strict_bounded_versioned = memory.get_bytes_strict_bounded_versioned
    if wrapped:
        store = _LimitedStore(store, 1024)
    barrier, lock = threading.Barrier(4), threading.Lock()
    active, peak, observed = 0, 0, []

    def verify(_store, _fulltext, _records, _generation, member):
        nonlocal active, peak
        with lock:
            active += 1
            peak = max(peak, active)
            observed.append(member["report_id"])
        try:
            barrier.wait(timeout=3)
        finally:
            with lock:
                active -= 1

    monkeypatch.setattr(generation, "_verify_member", verify)
    selected, reason = generation.explained_selection(
        store, expected_producer_commit=fixture.COMMIT, now=fixture.NOW,
        max_age_seconds=fixture.MAX_AGE_SECONDS, writer_protocol_qualified=True)
    assert selected is not None and reason is None
    assert sorted(observed) == sorted(spec)
    assert peak == 4 and active == 0


def test_unknown_subclass_and_unadmitted_transports_stay_serial(monkeypatch):
    class Unknown:
        _receipt_reads_thread_safe = True

    class R2Subclass(R2Store):
        pass

    class WrapperSubclass(_LimitedStore):
        pass

    subclass = object.__new__(R2Subclass)
    subclass._receipt_reads_thread_safe = True
    stores = [Unknown(), subclass, exact_transport(admitted=False),
              _LimitedStore(Unknown(), 1024),
              _LimitedStore(subclass, 1024),
              _LimitedStore(exact_transport(admitted=False), 1024),
              WrapperSubclass(exact_transport(), 1024)]
    expected_thread = threading.get_ident()
    observed = []

    def verify(_store, _fulltext, _records, _generation, member):
        observed.append((threading.get_ident(), member))

    monkeypatch.setattr(generation, "_verify_member", verify)
    for store in stores:
        observed.clear()
        generation._verify_members(store, None, None, {}, list(range(8)))
        assert observed == [(expected_thread, member) for member in range(8)]


def test_failure_drains_started_reads_before_return_and_admits_no_next_batch(monkeypatch):
    barrier = threading.Barrier(4)
    failed, release = threading.Event(), threading.Event()
    started, settled = set(), set()
    lock = threading.Lock()

    def verify(_store, _fulltext, _records, _generation, member):
        with lock:
            started.add(member)
        try:
            barrier.wait(timeout=3)
            if member == 0:
                failed.set()
                raise generation._Fail("member_receipt_changed")
            assert release.wait(timeout=3)
        finally:
            with lock:
                settled.add(member)

    monkeypatch.setattr(generation, "_verify_member", verify)
    with ThreadPoolExecutor(max_workers=1) as caller:
        operation = caller.submit(generation._verify_members, exact_transport(),
                                  None, None, {}, list(range(12)))
        try:
            assert failed.wait(timeout=3)
            assert not operation.done()
            assert started == {0, 1, 2, 3}
        finally:
            release.set()
        with pytest.raises(generation._Fail):
            operation.result(timeout=3)
    assert started == settled == {0, 1, 2, 3}


@pytest.mark.parametrize("wrapped", [False, True])
def test_complete_real_verification_keeps_the_final_catalog_fence(wrapped):
    memory = fixture.MemoryStore()
    fixture.build_generation(memory, fixture.spec_with(8, {"full": 8}))
    memory.midflight = lambda value: value.set_object(
        catalog.CATALOG_KEY, value.objects[catalog.CATALOG_KEY])
    store = exact_transport(memory)
    if wrapped:
        store = _LimitedStore(store, generation.CORPUS_MAX_BYTES)
    selected, reason = generation.explained_selection(
        store, expected_producer_commit=fixture.COMMIT, now=fixture.NOW,
        max_age_seconds=fixture.MAX_AGE_SECONDS, writer_protocol_qualified=True)
    assert selected is None and reason["code"] == "catalog_moved"


def test_member_failure_never_advances_to_corpus_read(monkeypatch):
    memory = fixture.MemoryStore()
    fixture.build_generation(memory, fixture.spec_with(8, {"full": 8}))
    store = exact_transport(memory)

    def refuse(*args):
        raise generation._Fail("member_receipt_changed")

    monkeypatch.setattr(generation, "_verify_member", refuse)
    memory.reads.clear()
    selected, reason = generation.explained_selection(
        store, expected_producer_commit=fixture.COMMIT, now=fixture.NOW,
        max_age_seconds=fixture.MAX_AGE_SECONDS, writer_protocol_qualified=True)
    assert selected is None and reason["code"] == "member_receipt_changed"
    assert memory.reads == [("versioned", catalog.CATALOG_KEY)]
