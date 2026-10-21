"""Actual inert storage and injected trusted-owner boundaries, no study access."""
import pytest

from engine.research_factory.market_memory_e0_reservations import ReservationError, ReservationStore
from engine.research_factory.market_memory_e0_reserved_read import E0ReservedReadError, _run_reserved_read


INTENT = {"task_id": "fixture-task", "condition": "fixed_l1", "scope": {"source": "fixture"}}
BODY = b'{"source":"inert-original-result"}'


@pytest.fixture
def owner(tmp_path):
    directory = tmp_path / "study"
    directory.mkdir(mode=0o700)
    store = ReservationStore(directory, {"study_id": "inert-study", "installation_id": "inert-install",
        "installation_epoch": "epoch-1", "registration_sha256": "a" * 64,
        "publication_sha256": "b" * 64})
    store.initialize(2)
    events = []

    def authorize(phase, operation_id, intent):
        assert operation_id == "op-1" and intent == INTENT
        events.append(phase)

    def load():
        assert store.snapshot()["reserved_looks"] == 1
        events.append("load")
        return BODY

    def qualify(body, operation_id, intent):
        assert body == BODY and operation_id == "op-1" and intent == INTENT
        events.append("qualify")

    return store, events, {"authorize": authorize, "load": load, "qualify": qualify}


def run(owner, **overrides):
    store, _, callbacks = owner
    return _run_reserved_read(store, "op-1", INTENT, **(callbacks | overrides))


def test_new_reads_only_after_durability_and_repeated_completion_never_replays(owner):
    store, events, _ = owner
    assert run(owner) == BODY
    assert events == ["reserve", "read", "load", "persist", "qualify", "persist",
                      "read_completed", "qualify", "disclose"]
    events.clear()
    assert run(owner) == BODY
    assert events == ["reserve", "read_completed", "qualify", "disclose"]
    assert store.snapshot()["consumed_looks"] == 1


def test_original_pending_does_not_read_or_refund(owner):
    store, events, _ = owner
    store.reserve("op-1", INTENT)
    with pytest.raises(E0ReservedReadError, match="pending_no_replay"):
        run(owner)
    assert events == ["reserve"]
    assert store.snapshot()["reserved_looks"] == 1


@pytest.mark.parametrize("phase,loaded,completed", [
    ("reserve", False, False), ("read", False, False),
    ("persist", True, False), ("read_completed", True, True), ("disclose", True, True),
])
def test_denial_at_each_current_policy_boundary_never_discloses(owner, phase, loaded, completed):
    store, events, callbacks = owner
    def authorize(current, operation_id, intent):
        callbacks["authorize"](current, operation_id, intent)
        if current == phase:
            raise PermissionError("fixture policy denied")
    with pytest.raises(PermissionError):
        run(owner, authorize=authorize)
    assert ("load" in events) is loaded
    state = store.snapshot()
    assert state["consumed_looks"] == int(completed)
    assert state["reserved_looks"] == int(not completed and phase != "reserve")


def test_revoke_during_qualification_prevents_persistence(owner):
    store, events, callbacks = owner
    revoked = False
    def qualify(*args):
        nonlocal revoked
        callbacks["qualify"](*args)
        revoked = True
    def authorize(*args):
        if revoked:
            raise PermissionError("revoked during qualification")
        callbacks["authorize"](*args)
    with pytest.raises(PermissionError):
        run(owner, authorize=authorize, qualify=qualify)
    assert store.snapshot()["reserved_looks"] == 1
    assert store.snapshot()["consumed_looks"] == 0


def test_revoked_cached_completion_is_not_read(owner):
    store, events, _ = owner
    assert run(owner) == BODY
    events.clear()
    def denied(*args):
        raise PermissionError("revoked")
    with pytest.raises(PermissionError):
        run(owner, authorize=denied)
    assert events == []
    assert store.snapshot()["consumed_looks"] == 1


@pytest.mark.parametrize("failure", ["load", "qualify"])
def test_original_reader_or_qualifier_failure_retains_pending(owner, failure):
    store, events, _ = owner
    def fail(*args):
        raise RuntimeError("inert source failure")
    with pytest.raises(RuntimeError):
        run(owner, **{failure: fail})
    events.clear()
    with pytest.raises(E0ReservedReadError, match="pending_no_replay"):
        run(owner)
    assert events == ["reserve"]
    assert store.snapshot()["reserved_looks"] == 1


@pytest.mark.parametrize("body", [b"", "not bytes", b"x" * (1024 * 1024 + 1)])
def test_unqualified_result_does_not_reach_storage_or_disclosure(owner, body):
    store, events, _ = owner
    with pytest.raises(E0ReservedReadError, match="bounded_result"):
        run(owner, load=lambda: body)
    assert "qualify" not in events
    assert store.snapshot()["reserved_looks"] == 1


def test_callbacks_cannot_mutate_the_intent_used_by_later_boundaries(owner):
    _, _, callbacks = owner
    def authorize(phase, operation_id, intent):
        callbacks["authorize"](phase, operation_id, intent)
        intent["scope"]["source"] = "mutated callback copy"
    def qualify(body, operation_id, intent):
        callbacks["qualify"](body, operation_id, intent)
        intent.clear()
    assert run(owner, authorize=authorize, qualify=qualify) == BODY
    assert INTENT["scope"]["source"] == "fixture"


def test_changed_intent_conflict_precedes_reader(owner):
    store, events, callbacks = owner
    store.reserve("op-1", INTENT | {"condition": "recency"})
    with pytest.raises(ReservationError, match="intent_conflict"):
        run(owner)
    assert events == ["reserve"]


def test_boolean_callback_is_not_an_authorization_grant(owner):
    store, events, _ = owner
    with pytest.raises(E0ReservedReadError, match="authorization_callback_contract"):
        run(owner, authorize=lambda *args: True)
    assert events == []
    assert store.snapshot()["reserved_looks"] == 0
