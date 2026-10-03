from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from engine.entry_radar.catalyst_context import (
    CatalystContextError,
    CatalystEvidence,
    CatalystSourceRead,
    assess_catalyst_context,
)

T0 = datetime(2026, 10, 2, 14, 30, tzinfo=timezone.utc)


def _read(source_id="issuer_events", status="ok", observed_at=T0, source_asof=None):
    return CatalystSourceRead(
        source_id=source_id,
        status=status,
        source_asof=source_asof or observed_at,
        observed_at=observed_at,
    )


def _event(
    *,
    native_id="evt-1",
    disposition="blocking",
    known_at=T0,
    source_available_at=None,
    ticker="NVDA",
    ref="event:evt-1",
):
    return CatalystEvidence(
        owner="issuer_event_owner",
        native_id=native_id,
        ticker=ticker,
        event_kind="issuer_event",
        source_available_at=source_available_at or known_at,
        known_at=known_at,
        owner_disposition=disposition,
        evidence_ref=ref,
    )


def _assess(**overrides):
    kwargs = dict(
        ticker="NVDA",
        tactical_episode_ref="radar:episode:abc123",
        decision_at=T0,
        required_sources=["issuer_events"],
        source_reads=[_read()],
        evidence=[],
    )
    kwargs.update(overrides)
    return assess_catalyst_context(**kwargs)


def test_healthy_empty_coverage_says_only_no_blocking_event_observed():
    got = _assess()
    assert got.context_state == "no_blocking_event_observed"
    assert got.coverage_complete is True
    assert got.blocking_evidence_refs == ()


@pytest.mark.parametrize("status", ["stale", "unavailable"])
def test_non_ok_required_source_fails_closed(status):
    got = _assess(source_reads=[_read(status=status)])
    assert got.context_state == "coverage_unknown"
    assert got.coverage_complete is False


def test_missing_required_source_fails_closed():
    got = _assess(required_sources=["issuer_events", "halt_feed"])
    assert got.context_state == "coverage_unknown"
    assert got.coverage_complete is False


def test_source_observed_after_decision_does_not_backfill_coverage():
    got = _assess(source_reads=[_read(observed_at=T0 + timedelta(minutes=1))])
    assert got.context_state == "coverage_unknown"
    assert got.coverage_complete is False


def test_source_asof_after_observed_at_is_contract_error():
    with pytest.raises(CatalystContextError):
        _read(source_asof=T0 + timedelta(seconds=1))


def test_known_blocking_event_has_precedence():
    got = _assess(evidence=[_event()])
    assert got.context_state == "blocking_event_observed"
    assert got.blocking_evidence_refs == ("event:evt-1",)


def test_unknown_owner_disposition_fails_closed():
    got = _assess(evidence=[_event(disposition="unknown")])
    assert got.context_state == "event_classification_unknown"
    assert got.unknown_evidence_refs == ("event:evt-1",)


def test_soft_event_is_context_not_blocking_authority():
    got = _assess(evidence=[_event(disposition="soft")])
    assert got.context_state == "soft_event_observed"
    payload = got.to_dict()
    assert all(value is False for value in payload["authority"].values())
    assert payload["research_only"] is True


def test_late_blocking_event_does_not_rewrite_past_decision():
    late = _event(known_at=T0 + timedelta(minutes=5), ref="event:late")
    got = _assess(evidence=[late])
    assert got.context_state == "no_blocking_event_observed"
    assert got.blocking_evidence_refs == ()
    assert got.late_evidence_refs == ("event:late",)


def test_evidence_available_after_known_at_is_contract_error():
    with pytest.raises(CatalystContextError):
        _event(source_available_at=T0 + timedelta(seconds=1))


def test_wrong_ticker_is_refused():
    with pytest.raises(CatalystContextError):
        _assess(evidence=[_event(ticker="AMD")])


def test_exact_duplicate_evidence_is_idempotent():
    row = _event()
    got = _assess(evidence=[row, row])
    assert got.blocking_evidence_refs == ("event:evt-1",)


def test_conflicting_duplicate_evidence_fails_closed_at_contract_boundary():
    a = _event()
    b = _event(disposition="soft")
    with pytest.raises(CatalystContextError):
        _assess(evidence=[a, b])


def test_episode_reference_is_passed_through_not_reminted():
    got = _assess(tactical_episode_ref="mastermind.live_entry_episode.v1:deadbeef")
    assert got.tactical_episode_ref == "mastermind.live_entry_episode.v1:deadbeef"


def test_output_is_deterministic_and_contains_no_strength_fields():
    got = _assess(
        required_sources=["halt_feed", "issuer_events"],
        source_reads=[_read("issuer_events"), _read("halt_feed")],
        evidence=[
            _event(native_id="2", disposition="nonblocking", ref="event:z"),
            _event(native_id="1", disposition="soft", ref="event:a"),
        ],
    )
    payload = got.to_dict()
    assert payload == got.to_dict()
    assert payload["required_sources"] == ["halt_feed", "issuer_events"]
    assert [r["source_id"] for r in payload["source_reads"]] == [
        "halt_feed", "issuer_events"
    ]
    own_keys = set(payload) - {"authority"}
    banned = ("score", "rank", "points", "weight", "conviction", "buy", "sell", "trade")
    assert not any(token in key.lower() for key in own_keys for token in banned)


def test_required_sources_cannot_be_empty():
    with pytest.raises(CatalystContextError):
        _assess(required_sources=[])


def test_duplicate_source_read_is_refused():
    with pytest.raises(CatalystContextError):
        _assess(source_reads=[_read(), _read()])
