"""Same-read join (prophet.b4.same_read/v1): one B3 read + one B4 owner read.

These tests pin the FROZEN SPEC of ``engine/prophet_b4_same_read.py`` against
the REAL owner chain — the real episode store, the real native reader, the
real composer and the real B4 evaluator.  Fixtures are imported from the
existing suites (``tests/test_prophet_strategy_definition.py`` reader world,
``tests/test_prophet_candidate_state.py`` store builders) rather than copied.

BASE interposition note: the native entry-geometry and metric owners do not
exist yet, and the join lawfully passes the composer the empty "no owner fact"
mappings — so an EVALUATED envelope can only be exercised by standing in for
those two future owners at the composer boundary (a wrapper on this module's
``evaluate_runtime_entry_availability`` reference that injects exactly the
incumbent entry/metric fixtures the existing adapter tests use).  The composer
and B4 still run for real and still decide; nothing is injected into them.
At BASE, without that interposition, the join is always UNAVAILABLE_DATA.
"""
import json

import pytest

import engine.prophet_b4_same_read as same_read
import engine.prophet_candidate_state as candidate_state
import engine.prophet_entry_availability_sources as sources_module
from engine.prophet_b4_same_read import (
    RESULT_KEYS,
    SAME_READ_SCHEMA,
    classify_nbbo,
    evaluate_same_read_entry_availability,
)
from engine.prophet_entry_availability_sources import evaluate_runtime_entry_availability
from engine.prophet_strategy_definition import (
    build_early_leadership_sector_rotation_definition,
)
from lib.nyse_calendar import is_session, session_n_forward
from tests.test_prophet_strategy_definition import (
    _B4Aliases,
    _QUALIFIED_RECORDED_AT,
    _QUALIFIED_SOURCE_KNOWN_AT,
    _READER_READ_AT,
    _b4_reader_observation,
    _b4_reader_world,
    _b4_runtime_sources,
)

from datetime import date

#: The same-read world's own clock spine, all BEFORE the 19:30:08Z live pass
#: that owns the B4 decision clock: the B3 builder requires the assembly clock
#: at/after the store recording, and B4 requires the projection generated
#: at/before decision_at — so the store must be recorded before the pass.
_SR_STORE_RECORDED_AT = "2026-09-17T19:10:00Z"
#: Anchored at 19:05Z (the anchor time becomes the episode ``opened_at``; the
#: shared fixture's default 19:55Z anchor postdates the pass).
_SR_ANCHOR_AT = "2026-09-17T19:05:00Z"
#: Where the verified B3 pair is assembled: inside the lawful window between
#: the store recording (19:10Z) and the live pass (19:30:08Z).
_ASSEMBLY_AT = _READER_READ_AT.replace(hour=19, minute=20, second=0)

#: The incumbent entry-geometry/metric fixtures reused as the stand-in for the
#: two future native owners (exactly what tests/test_prophet_strategy_definition
#: feeds the same composer for the same symbol and prices).
_FUTURE_GEOMETRY, _FUTURE_METRICS = _b4_runtime_sources("UNIT")[2:]


def _qualified_world(tmp_path, **overrides):
    kwargs = {
        "source_known_at": _QUALIFIED_SOURCE_KNOWN_AT,
        "store_recorded_at": _SR_STORE_RECORDED_AT,
        "observations": [
            _b4_reader_observation(
                day="2026-09-17",
                known_at=_QUALIFIED_SOURCE_KNOWN_AT,
                anchor_time=_SR_ANCHOR_AT,
            )
        ],
    }
    kwargs.update(overrides)
    return _b4_reader_world(tmp_path, **kwargs)


def _pin_clocks(monkeypatch, *, read_at=_READER_READ_AT, assembly_at=_ASSEMBLY_AT):
    monkeypatch.setattr(sources_module, "_now_utc", lambda: read_at, raising=False)
    monkeypatch.setattr(
        candidate_state, "_assembly_now", lambda: assembly_at, raising=False
    )


def _same_read_call(world, **overrides):
    call = {
        "repo_root": world["tmp_path"],
        "snapshot": world["snapshot"],
        "candidate_source_event_id": world["source_event_id"],
        "candidate_source_receipt": world["source_receipt"],
        "native_live_root": world["live_root"],
        "alias_table": _B4Aliases("UNIT"),
        "strategy_definition": build_early_leadership_sector_rotation_definition(),
    }
    call.update(overrides)
    return evaluate_same_read_entry_availability(**call)


def _inject_future_geometry_metric_owners(monkeypatch):
    """Stand in for the two owners that do not exist at BASE (see header)."""
    captured = {}
    real = same_read.evaluate_runtime_entry_availability

    def wrapper(candidate_projection, *, episode_id, strategy_definition, **source_kwargs):
        captured["projection"] = candidate_projection
        captured["episode_id"] = episode_id
        captured["strategy_definition"] = strategy_definition
        captured["source_kwargs"] = dict(source_kwargs)
        assert source_kwargs["entry_rows_by_symbol"] == {}
        assert source_kwargs["metric_inputs"] == {}
        source_kwargs["entry_rows_by_symbol"] = _FUTURE_GEOMETRY
        source_kwargs["metric_inputs"] = _FUTURE_METRICS
        return real(
            candidate_projection,
            episode_id=episode_id,
            strategy_definition=strategy_definition,
            **source_kwargs,
        )

    monkeypatch.setattr(same_read, "evaluate_runtime_entry_availability", wrapper)
    return captured


def _d01_artifact(*, at_utc="2026-09-16T22:35:00Z", validity_overrides=None):
    """A D01 signal-gate artifact for the fixture's 2026-09-17 session.

    Mirrors ``_b4_signal_gate`` with the source session that is genuinely
    prior-and-settled for a 2026-09-17 19:30:08Z decision clock: emitted
    2026-09-16T22:35:00Z (after the 17:00 ET settle of the 09-16 session) and
    valid for exactly the next session.
    """
    from tests.test_prophet_strategy_definition import _b4_signal_gate

    artifact = _b4_signal_gate(
        at_utc=at_utc,
        as_of="2026-09-16",
        decision_at="2026-09-17T19:30:08Z",
        market_session="2026-09-17",
    )
    artifact.pop("_decision_at")
    artifact.pop("_market_session")
    artifact["validity"].update(
        {"valid_for_decision_sessions": ["2026-09-17"], "expiry_session": "2026-09-17"}
    )
    artifact["validity"].update(validity_overrides or {})
    return artifact


# ── Spec 1/2/6: the closed envelope, the one-read law, BASE fail-closed ─────


def test_result_key_set_is_closed_and_deterministic(tmp_path, monkeypatch):
    world = _qualified_world(tmp_path)
    _pin_clocks(monkeypatch)
    first = _same_read_call(world)
    second = _same_read_call(world)

    assert set(RESULT_KEYS) == {
        "schema", "state", "availability", "b3_projection_id", "episode_id",
        "binding", "owner_read_schema", "nbbo_quality", "unavailable_reasons",
        "receipts",
    }
    assert set(first) == set(RESULT_KEYS)
    assert first["schema"] == SAME_READ_SCHEMA == "prophet.b4.same_read/v1"
    assert isinstance(first["unavailable_reasons"], list)
    assert isinstance(first["receipts"], list)
    assert first["unavailable_reasons"] == sorted(first["unavailable_reasons"])
    assert first["receipts"] == sorted(first["receipts"])
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)


def test_base_has_no_geometry_or_metric_owner_so_the_join_fails_closed(
        tmp_path, monkeypatch):
    world = _qualified_world(tmp_path)
    _pin_clocks(monkeypatch)
    result = _same_read_call(world)

    assert result["state"] == "UNAVAILABLE_DATA"
    assert result["availability"] is None
    assert result["unavailable_reasons"] == [
        "RuntimeOwnerFactError: entry geometry owner has no row for canonical "
        "store symbol"
    ]
    # The two reads that DID happen are still receipted evidence.
    assert result["b3_projection_id"].startswith("pcs:")
    assert result["owner_read_schema"] == "prophet.b4.native_owner_read/v1"
    assert result["nbbo_quality"] == "MISSING"
    assert result["b3_projection_id"] in result["receipts"]


def test_one_native_read_one_owner_read_and_no_direct_projection(
        tmp_path, monkeypatch):
    world = _qualified_world(tmp_path)
    _pin_clocks(monkeypatch)

    builder_calls = []
    real_builder = same_read.build_native_factual_assessment_result

    def builder_spy(snapshot, **kwargs):
        builder_calls.append((snapshot, kwargs))
        return real_builder(snapshot, **kwargs)

    reader_calls = []
    real_reader = same_read.read_native_b4_owner_inputs

    def reader_spy(*args, **kwargs):
        reader_calls.append((args, kwargs))
        return real_reader(*args, **kwargs)

    projector_calls = []
    real_projector = candidate_state.project_candidate_states

    def projector_spy(*args, **kwargs):
        projector_calls.append((args, kwargs))
        return real_projector(*args, **kwargs)

    monkeypatch.setattr(same_read, "build_native_factual_assessment_result", builder_spy)
    monkeypatch.setattr(same_read, "read_native_b4_owner_inputs", reader_spy)
    monkeypatch.setattr(candidate_state, "project_candidate_states", projector_spy)

    result = _same_read_call(world)

    assert len(builder_calls) == 1
    assert builder_calls[0][0] is world["snapshot"]
    assert builder_calls[0][1] == {
        "candidate_source_event_id": world["source_event_id"],
        "candidate_source_receipt": world["source_receipt"],
    }
    assert len(reader_calls) == 1
    assert reader_calls[0][0][1] is world["snapshot"], "the SAME snapshot object"
    assert reader_calls[0][1]["candidate_source_event_id"] == world["source_event_id"]
    assert reader_calls[0][1]["candidate_source_receipt"] == world["source_receipt"]
    # The projector ran exactly once — inside the single builder call.  A
    # second call would mean this module projected directly.
    assert len(projector_calls) == 1
    assert not hasattr(same_read, "project_candidate_states")
    assert result["state"] == "UNAVAILABLE_DATA"


# ── Spec 6 + happy path: EVALUATED equals the direct evaluator call ─────────


def test_happy_owner_read_is_evaluated_and_equals_the_direct_evaluator_call(
        tmp_path, monkeypatch):
    world = _qualified_world(tmp_path)
    _pin_clocks(monkeypatch)
    captured = _inject_future_geometry_metric_owners(monkeypatch)

    result = _same_read_call(world)

    assert result["schema"] == SAME_READ_SCHEMA
    assert result["state"] == "EVALUATED"
    assert result["availability"] is not None
    assert result["availability"]["state"] != "ENTRY_OPEN"
    assert result["availability"]["state"] == "UNAVAILABLE_DATA"
    assert result["episode_id"] == result["binding"]["episode_id"]
    assert result["nbbo_quality"] == "MISSING"

    # The module passed the composer exactly the attested owner bytes and the
    # owner read's own clocks — and the empty no-owner mappings for geometry
    # and metrics.
    served_live = json.loads(world["live_bytes"])
    served_quotes = json.loads(world["quotes_bytes"])
    assert captured["episode_id"] == result["episode_id"]
    assert captured["source_kwargs"]["decision_at"] == served_live["meta"]["pass_ts"]
    assert captured["source_kwargs"]["market_session"] == "2026-09-17"
    assert captured["source_kwargs"]["quotes_by_symbol"] == served_quotes["quotes"]
    assert captured["source_kwargs"]["live_state_artifact"] == served_live
    assert captured["source_kwargs"]["signal_gate_artifact"] is None

    # A DIRECT evaluator call on the same verified pair with the same owner
    # inputs reproduces the row byte for byte: the join adds, removes and
    # re-labels nothing.
    direct = evaluate_runtime_entry_availability(
        captured["projection"],
        episode_id=captured["episode_id"],
        strategy_definition=captured["strategy_definition"],
        decision_at=captured["source_kwargs"]["decision_at"],
        market_session=captured["source_kwargs"]["market_session"],
        alias_table=captured["source_kwargs"]["alias_table"],
        quotes_by_symbol=captured["source_kwargs"]["quotes_by_symbol"],
        live_state_artifact=captured["source_kwargs"]["live_state_artifact"],
        entry_rows_by_symbol=_FUTURE_GEOMETRY,
        metric_inputs=_FUTURE_METRICS,
    )
    assert result["availability"] == direct
    assert result["receipts"] == sorted(set(result["receipts"]) | {
        *direct["source_receipts"],
    })


# ── Spec 3/4/5: typed refusals, verbatim passthrough, byte attestation ──────


def test_binding_mismatch_against_a_foreign_owner_read_is_typed(
        tmp_path, monkeypatch):
    world = _qualified_world(tmp_path)
    # A second, genuinely different store (different observation receipt ->
    # different content -> different generation id and episode digest): its
    # qualified owner read is a REAL read of a DIFFERENT snapshot, the
    # packet's mismatch case.  The receipt the reader must present is the one
    # the observation actually carries, not the world dict's shared default.
    foreign_receipt = "sha256:" + "d" * 64
    other_world = _b4_reader_world(
        tmp_path / "other",
        source_known_at=_QUALIFIED_SOURCE_KNOWN_AT,
        store_recorded_at=_QUALIFIED_RECORDED_AT,
        observations=[
            _b4_reader_observation(
                day="2026-09-17",
                known_at=_QUALIFIED_SOURCE_KNOWN_AT,
                source_receipt=foreign_receipt,
            )
        ],
    )
    assert other_world["generation_id"] != world["generation_id"]
    _pin_clocks(monkeypatch)
    real_reader = same_read.read_native_b4_owner_inputs

    def foreign_reader(*args, **kwargs):
        return real_reader(
            other_world["tmp_path"],
            other_world["snapshot"],
            candidate_source_event_id=other_world["source_event_id"],
            candidate_source_receipt=foreign_receipt,
            native_live_root=other_world["live_root"],
            alias_table=_B4Aliases("UNIT"),
        )

    monkeypatch.setattr(same_read, "read_native_b4_owner_inputs", foreign_reader)
    result = _same_read_call(world)

    assert result["state"] == "UNAVAILABLE_DATA"
    assert result["availability"] is None
    assert result["unavailable_reasons"], "a foreign read must be typed"
    assert all(
        reason.startswith("SAME_READ_BINDING_MISMATCH:")
        for reason in result["unavailable_reasons"]
    )
    assert (
        "SAME_READ_BINDING_MISMATCH:candidate_generation_id"
        in result["unavailable_reasons"]
    )


def test_owner_refusal_reasons_pass_through_verbatim(tmp_path, monkeypatch):
    from datetime import datetime, timezone

    world = _qualified_world(tmp_path)

    # A read that completes in a LATER ET session, weeks later.
    _pin_clocks(
        monkeypatch,
        read_at=datetime(2026, 10, 13, 0, 10, 30, tzinfo=timezone.utc),
        assembly_at=datetime(2026, 10, 13, 0, 10, 29, tzinfo=timezone.utc),
    )
    later = _same_read_call(world)
    assert later["state"] == "UNAVAILABLE_DATA"
    assert later["availability"] is None
    # The reader's reason STRINGS verbatim, in the envelope's sorted order.
    assert later["unavailable_reasons"] == [
        "QUOTE_STALE_AT_OWN_READ",
        "READ_SESSION_CROSS_SESSION",
    ]
    assert later["b3_projection_id"] in later["receipts"]

    # A same-session read half a minute past the disclosed 25-minute ceiling.
    _pin_clocks(
        monkeypatch,
        read_at=datetime(2026, 9, 17, 19, 55, 30, tzinfo=timezone.utc),
    )
    stale = _same_read_call(world)
    assert stale["state"] == "UNAVAILABLE_DATA"
    assert stale["unavailable_reasons"] == ["QUOTE_STALE_AT_OWN_READ"]
    assert stale["nbbo_quality"] == "MISSING"


def test_owner_bytes_changed_between_read_and_compose_is_typed(
        tmp_path, monkeypatch):
    real_reader = same_read.read_native_b4_owner_inputs

    for name in ("quotes_full", "prophet_live"):
        world = _qualified_world(tmp_path / name)
        _pin_clocks(monkeypatch)

        def mutating_reader(*args, **kwargs):
            read = real_reader(*args, **kwargs)
            path = world["quotes_path"] if name == "quotes_full" else world["live_path"]
            path.write_bytes(path.read_bytes() + b" ")
            return read

        monkeypatch.setattr(same_read, "read_native_b4_owner_inputs", mutating_reader)
        result = _same_read_call(world)
        monkeypatch.setattr(same_read, "read_native_b4_owner_inputs", real_reader)

        assert result["state"] == "UNAVAILABLE_DATA"
        assert result["availability"] is None
        assert result["unavailable_reasons"] == [f"SAME_READ_OWNER_BYTES_CHANGED:{name}"]


def test_retracted_candidate_relation_is_unavailable_as_owners_decide(
        tmp_path, monkeypatch):
    from engine.us_candidate_episode import (
        DEFAULT_DEFINITION_ERA,
        apply_commands,
        reconcile_observations,
    )

    opened = reconcile_observations(
        [], [_b4_reader_observation(known_at=_QUALIFIED_SOURCE_KNOWN_AT)],
        recorded_at=_QUALIFIED_RECORDED_AT, definition_era=DEFAULT_DEFINITION_ERA,
    )
    episode_id_text = opened.episodes[0]["episode_id"]
    retraction = {
        "event_type": "RETRACTED", "episode_id": episode_id_text,
        "source_system": "operator", "source_schema": "candidate-command/v1",
        "source_event_id": "retract:1", "source_receipt": "sha256:" + "b" * 64,
        "occurred_at": "2026-09-17T19:10:00Z", "known_at": "2026-09-17T19:10:00Z",
        "correction_of": opened.events[0]["event_id"],
        "payload": {"reason": "source withdrew the observation"},
    }
    result_events = apply_commands(
        opened.events, [retraction], recorded_at=_QUALIFIED_RECORDED_AT,
        definition_era=DEFAULT_DEFINITION_ERA,
    )
    world = _b4_reader_world(
        tmp_path, events=result_events.events, candidate_inputs=1,
        source_known_at=_QUALIFIED_SOURCE_KNOWN_AT,
        store_recorded_at=_QUALIFIED_RECORDED_AT,
    )
    _pin_clocks(monkeypatch)

    result = _same_read_call(world)

    assert result["state"] == "UNAVAILABLE_DATA"
    assert result["availability"] is None
    assert len(result["unavailable_reasons"]) == 1
    reason = result["unavailable_reasons"][0]
    assert reason.startswith("CandidateStateContractError:")
    assert "retracted" in reason
    # Nothing was minted beside the typed refusal.
    assert result["b3_projection_id"] is None
    assert result["binding"] is None


# ── D01: the real composer binds prior-session confluence for the next one ──


def _d01_row(tmp_path, monkeypatch, artifact):
    world = _qualified_world(tmp_path)
    _pin_clocks(monkeypatch)
    _inject_future_geometry_metric_owners(monkeypatch)
    result = _same_read_call(world, signal_gate_artifact=artifact)
    assert result["state"] == "EVALUATED"
    return result["availability"]


def test_d01_prior_completed_session_confluence_is_valid_next_session(
        tmp_path, monkeypatch):
    row = _d01_row(tmp_path, monkeypatch, _d01_artifact())
    assert "OWNER_CONFLUENCE_UNKNOWN" not in row["blockers"]
    assert any(
        receipt.startswith("signal-gate-pair:unit-pair-001@2026-09-16")
        for receipt in row["source_receipts"]
    )


def test_d01_late_emission_is_unknown_not_fail(tmp_path, monkeypatch):
    # Emitted 2026-09-17T20:00:00Z — after the 19:30:08Z decision clock.
    artifact = _d01_artifact(at_utc="2026-09-17T20:00:00Z")
    row = _d01_row(tmp_path, monkeypatch, artifact)
    assert "OWNER_CONFLUENCE_UNKNOWN" in row["blockers"]
    assert "OWNER_CONFLUENCE_NOT_PASSED" not in row["blockers"]
    assert row["state"] == "UNAVAILABLE_DATA"
    assert any(
        receipt.endswith("reason:confluence_late_emission")
        for receipt in row["source_receipts"]
    )


def test_d01_expired_window_is_unknown(tmp_path, monkeypatch):
    artifact = _d01_artifact(
        validity_overrides={"valid_for_decision_sessions": ["2026-09-18"]}
    )
    row = _d01_row(tmp_path, monkeypatch, artifact)
    assert "OWNER_CONFLUENCE_UNKNOWN" in row["blockers"]
    assert row["state"] == "UNAVAILABLE_DATA"
    assert any(
        receipt.endswith("reason:confluence_expired")
        for receipt in row["source_receipts"]
    )


def test_d01_lineage_mismatch_is_unknown(tmp_path, monkeypatch):
    artifact = _d01_artifact(validity_overrides={"lineage_token": "other-pair"})
    row = _d01_row(tmp_path, monkeypatch, artifact)
    assert "OWNER_CONFLUENCE_UNKNOWN" in row["blockers"]
    assert row["state"] == "UNAVAILABLE_DATA"
    assert any(
        receipt.endswith("reason:confluence_lineage_mismatch")
        for receipt in row["source_receipts"]
    )


# ── Spec 7: classify_nbbo — the rejection rule a future NBBO owner faces ────


@pytest.mark.parametrize(
    ("bid", "ask", "nbbo_ts", "expected"),
    (
        (None, 10.5, "2026-09-17T19:30:00Z", "MISSING"),
        (10.0, None, "2026-09-17T19:30:00Z", "MISSING"),
        ("10", 10.5, "2026-09-17T19:30:00Z", "INVALID"),
        (0, 10.5, "2026-09-17T19:30:00Z", "INVALID"),
        (-1.0, 10.5, "2026-09-17T19:30:00Z", "INVALID"),
        (float("nan"), 10.5, "2026-09-17T19:30:00Z", "INVALID"),
        (float("inf"), 10.5, "2026-09-17T19:30:00Z", "INVALID"),
        (True, 10.5, "2026-09-17T19:30:00Z", "INVALID"),
        (10.0, 10.5, None, "UNCLOCKED"),
        (10.0, 10.5, "not-a-timestamp", "UNCLOCKED"),
        (10.0, 10.5, "2026-09-17T19:30:00", "UNCLOCKED"),
        (10.0, 10.5, "2026-09-17T19:31:00Z", "STALE"),
        (10.0, 10.5, "2026-09-17T19:27:00Z", "STALE"),
        (10.5, 10.5, "2026-09-17T19:30:00Z", "LOCKED"),
        (10.6, 10.5, "2026-09-17T19:30:00Z", "CROSSED"),
    ),
)
def test_classify_nbbo_outcomes(bid, ask, nbbo_ts, expected):
    assert (
        classify_nbbo(
            bid, ask, nbbo_ts,
            decision_at="2026-09-17T19:30:08Z", max_age_seconds=120,
        )
        == expected
    )


def test_classify_nbbo_boundary_age_exactly_at_the_ceiling_is_qualified():
    kwargs = {"decision_at": "2026-09-17T19:30:08Z", "max_age_seconds": 120}
    assert classify_nbbo(10.0, 10.5, "2026-09-17T19:28:08Z", **kwargs) == "QUALIFIED"
    assert classify_nbbo(10.0, 10.5, "2026-09-17T19:28:07Z", **kwargs) == "STALE"


def test_classify_nbbo_reference_contract_is_not_evidence():
    good = {"bid": 10.0, "ask": 10.5, "nbbo_ts": "2026-09-17T19:30:00Z"}
    with pytest.raises(ValueError):
        classify_nbbo(good["bid"], good["ask"], good["nbbo_ts"],
                      decision_at="not-a-clock", max_age_seconds=60)
    with pytest.raises(ValueError):
        classify_nbbo(good["bid"], good["ask"], good["nbbo_ts"],
                      decision_at="2026-09-17T19:30:08Z", max_age_seconds=-1)
    with pytest.raises(ValueError):
        classify_nbbo(good["bid"], good["ask"], good["nbbo_ts"],
                      decision_at="2026-09-17T19:30:08Z", max_age_seconds=True)


# ── Documented gap: the calendar models no early closes ──────────────


def test_half_day_after_thanksgiving_documents_the_calendar_gap():
    """2026-11-27 is a 13:00 ET early close; ``lib.nyse_calendar`` models none.

    Current behaviour, documented without asserting it is correct: the half
    day is an ordinary session for every calendar helper this chain rides —
    the D01 next-session window steps onto it, and a 19:30Z (14:30 ET) pass
    still session-maps to it even though the real market closed 90 minutes
    earlier; ``expected_last_session`` at that instant still says the PRIOR
    session because its settle buffer assumes a 16:00 close.  The only owner
    that knows about the early close is the B4 session policy's own local
    date set (``engine/prophet_entry_policy.py``), which the gate consults
    separately from this calendar.  See GAPS in the lane return.
    """
    from engine.prophet_live.live_states import session_et

    half_day = date(2026, 11, 27)
    assert is_session(half_day)
    assert session_n_forward(date(2026, 11, 25), 1) == half_day
    assert session_et(_READER_READ_AT.replace(year=2026, month=11, day=27)) == "2026-11-27"
