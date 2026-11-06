"""Genuine temporary reservation files; authorization is an explicit fixture.

No native service, selected installation, source grant, or study is admitted.
"""
import pytest

from engine.research_factory.market_memory_e0_original_case import (
    E0OriginalCaseError, _read_original_case,
)
from engine.research_factory.market_memory_e0_reservations import ReservationError, ReservationStore


INTENT = {"study_id": "fixture-study", "scope": {"recipient": "fixture-original"}}
BODY = b'{"source":"fixture-original-input"}'


@pytest.fixture
def owner(tmp_path):
    directory = tmp_path / "original"
    directory.mkdir(mode=0o700)
    store = ReservationStore(directory, {"study_id": "fixture-study",
        "installation_id": "fixture-installation", "installation_epoch": "epoch-1",
        "registration_sha256": "a" * 64, "publication_sha256": "b" * 64})
    store.initialize(2)
    events = []
    def authorize(phase, operation, intent):
        assert operation == "original-1" and intent == INTENT
        events.append(phase)
    def qualify(body, operation, intent):
        assert body == BODY and operation == "original-1" and intent == INTENT
        events.append("qualify")
    return store, events, {"authorize": authorize, "qualify": qualify}


def frozen(store):
    return {p.name: p.read_bytes() for p in store.directory.iterdir()}


def invoke(owner, **changes):
    store, _, callbacks = owner
    return _read_original_case(store, "original-1", INTENT, **(callbacks | changes))


def no_mutations(store, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("original read must not initialize, reserve, finish or publish")
    for name in ("initialize", "reserve", "finish", "_publish", "_write_new"):
        monkeypatch.setattr(ReservationStore, name, forbidden)


@pytest.mark.parametrize("status", ["ABSENT", "PENDING", "COMPLETE"])
def test_actual_original_status_never_reissues_or_changes_any_file(owner, monkeypatch, status):
    store, events, _ = owner
    if status != "ABSENT": store.reserve("original-1", INTENT)
    if status == "COMPLETE": store.finish("original-1", INTENT, BODY)
    before = frozen(store)
    no_mutations(store, monkeypatch)
    assert invoke(owner) == (status, BODY if status == "COMPLETE" else None)
    assert frozen(store) == before
    expected = ["inspect_original", "disclose_original_state"] if status != "COMPLETE" else [
        "inspect_original", "read_original_completed", "qualify",
        "recheck_original_completed", "disclose_original_completed"]
    assert events == expected
    assert invoke(owner) == (status, BODY if status == "COMPLETE" else None)
    assert frozen(store) == before


@pytest.mark.parametrize("status", ["PENDING", "COMPLETE"])
def test_original_intent_is_exact_before_status_disclosure(owner, status):
    store, events, _ = owner
    other = {**INTENT, "scope": {"recipient": "different-original"}}
    store.reserve("original-1", other)
    if status == "COMPLETE": store.finish("original-1", other, BODY)
    before = frozen(store)
    with pytest.raises(ReservationError, match="operation_intent_conflict"):
        invoke(owner)
    assert events == ["inspect_original"] and frozen(store) == before


@pytest.mark.parametrize("phase", ["inspect_original", "read_original_completed",
    "recheck_original_completed", "disclose_original_completed"])
def test_current_permission_checked_at_every_original_boundary(owner, monkeypatch, phase):
    store, events, callbacks = owner
    store.reserve("original-1", INTENT); store.finish("original-1", INTENT, BODY)
    before = frozen(store)
    def authorize(current, *args):
        callbacks["authorize"](current, *args)
        if current == phase: raise PermissionError("fixture-current-permission-revoked")
    if phase == "inspect_original":
        def forbidden(*args): raise AssertionError("denial precedes store inspection")
        monkeypatch.setattr(ReservationStore, "_locked", forbidden)
    with pytest.raises(PermissionError): invoke(owner, authorize=authorize)
    assert frozen(store) == before
    assert events[-1] == phase


def test_absent_and_pending_status_still_require_final_permission(owner):
    store, events, callbacks = owner
    def authorize(phase, *args):
        callbacks["authorize"](phase, *args)
        if phase == "disclose_original_state": raise PermissionError("revoked")
    for pending in (False, True):
        if pending: store.reserve("original-1", INTENT)
        before = frozen(store)
        with pytest.raises(PermissionError): invoke(owner, authorize=authorize)
        assert frozen(store) == before


@pytest.mark.parametrize("when", ["before", "during_qualification"])
def test_actual_same_size_body_corruption_is_never_metadata_only_success(owner, when):
    store, events, callbacks = owner
    store.reserve("original-1", INTENT); store.finish("original-1", INTENT, BODY)
    journal = store.snapshot()
    path = store.directory / store._result_name("original-1")
    def corrupt():
        path.write_bytes(b"x" + BODY[1:])
        assert path.stat().st_size == len(BODY)
        assert store.snapshot() == journal
    def qualify(*args):
        callbacks["qualify"](*args)
        if when == "during_qualification": corrupt()
    if when == "before": corrupt()
    with pytest.raises(ReservationError, match="result_digest_mismatch"):
        invoke(owner, qualify=qualify)
    assert store.snapshot() == journal


def test_revocation_during_qualification_withholds_original(owner):
    store, _, callbacks = owner
    store.reserve("original-1", INTENT); store.finish("original-1", INTENT, BODY)
    before = frozen(store)
    revoked = [False]
    def qualify(*args):
        callbacks["qualify"](*args); revoked[0] = True
    def authorize(*args):
        if revoked[0]: raise PermissionError("revoked-during-qualification")
        callbacks["authorize"](*args)
    with pytest.raises(PermissionError): invoke(owner, authorize=authorize, qualify=qualify)
    assert frozen(store) == before


@pytest.mark.parametrize("callback", ["authorize", "qualify"])
def test_truthy_callback_does_not_become_authority(owner, callback):
    store, _, _ = owner
    store.reserve("original-1", INTENT); store.finish("original-1", INTENT, BODY)
    before = frozen(store)
    with pytest.raises(E0OriginalCaseError, match="callback_contract"):
        invoke(owner, **{callback: lambda *args: True})
    assert frozen(store) == before


def test_owner_mutation_during_policy_is_refused_before_touching_replacement(owner, tmp_path):
    store, _, callbacks = owner
    original = store.directory
    def authorize(*args):
        callbacks["authorize"](*args)
        store.directory = tmp_path / "never-created"
    try:
        with pytest.raises(E0OriginalCaseError, match="original_reservation_owner_changed"):
            invoke(owner, authorize=authorize)
        assert not store.directory.exists()
    finally:
        store.directory = original


def test_policy_and_qualifier_cannot_rewrite_original_intent(owner):
    store, _, callbacks = owner
    store.reserve("original-1", INTENT); store.finish("original-1", INTENT, BODY)
    def authorize(*args):
        callbacks["authorize"](*args); args[-1].clear()
    def qualify(*args):
        callbacks["qualify"](*args); args[-1]["scope"].clear()
    assert invoke(owner, authorize=authorize, qualify=qualify) == ("COMPLETE", BODY)
    assert INTENT["scope"] == {"recipient": "fixture-original"}


def test_orphan_publication_does_not_become_absent(owner):
    store, events, _ = owner
    (store.directory / "orphan.bin").write_bytes(b"orphan")
    with pytest.raises(ReservationError): invoke(owner)
    assert events == ["inspect_original"]


def test_uninitialized_store_is_not_absent_or_implicitly_initialized(owner, tmp_path, monkeypatch):
    store, events, _ = owner
    empty = tmp_path / "empty-original"
    empty.mkdir(mode=0o700)
    store.directory = empty
    no_mutations(store, monkeypatch)
    with pytest.raises(ReservationError, match="uninitialized_store"):
        invoke(owner)
    assert events == ["inspect_original"]
    assert list(empty.iterdir()) == []


def test_foreign_store_type_refuses_before_callbacks(owner):
    _, events, callbacks = owner
    class Foreign(ReservationStore): pass
    with pytest.raises(E0OriginalCaseError, match="original_reservation_owner_required"):
        _read_original_case(object.__new__(Foreign), "original-1", INTENT, **callbacks)
    assert not events
