from __future__ import annotations

import copy
import json
from datetime import datetime, timedelta, timezone
from dataclasses import replace
from hashlib import sha256
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from engine.entry_radar.catalyst_context import (
    CatalystContext,
    CatalystContextError,
    CatalystEvidence,
    CatalystEvidenceClock,
    CatalystSourceRead,
    RADAR_EPISODE_SCHEMA,
    assess_catalyst_context,
    assess_catalyst_context_for_live_episode,
)

from engine.entry_radar.catalyst_adapters import (
    adapt_company_intelligence_earnings_workspace,
    adapt_edgar_earnings_item_202,
    assess_company_intelligence_current_read_for_live_episode,
    first_full_session_close_after,
)
from engine.entry_radar.live_ledger import LiveEpisode, compute_episode_id
from engine.company_intelligence.contracts import canonical_json_bytes

ROOT = Path(__file__).resolve().parent.parent
CATALYST_CONTEXT_SCHEMA = json.loads(
    (ROOT / "research" / "live_entry_radar" / "contracts" / "catalyst_context.schema.json").read_text()
)
CATALYST_CONTEXT_VALIDATOR = Draft202012Validator(CATALYST_CONTEXT_SCHEMA)

T0 = datetime(2026, 10, 2, 14, 30, tzinfo=timezone.utc)


def _read(
    source_id="issuer_events",
    status="ok",
    observed_at=T0,
    source_asof=None,
    *,
    fresh_until,
):
    return CatalystSourceRead(
        source_id=source_id,
        status=status,
        source_asof=source_asof or observed_at,
        observed_at=observed_at,
        fresh_until=fresh_until,
    )


def _event(
    *,
    native_id="evt-1",
    disposition="blocking",
    known_at=T0,
    source_available_at=None,
    relevant_until,
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
        relevant_until=relevant_until,
        owner_disposition=disposition,
        evidence_ref=ref,
    )


def _assess(**overrides):
    kwargs = dict(
        ticker="NVDA",
        radar_episode_id="0123456789abcdef",
        decision_at=T0,
        generated_at=T0,
        required_sources=["issuer_events"],
        source_reads=[_read(fresh_until=T0)],
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
    got = _assess(source_reads=[_read(status=status, fresh_until=T0)])
    assert got.context_state == "coverage_unknown"
    assert got.coverage_complete is False


def test_missing_required_source_fails_closed():
    got = _assess(required_sources=["issuer_events", "halt_feed"])
    assert got.context_state == "coverage_unknown"
    assert got.coverage_complete is False


def test_source_observed_after_decision_does_not_backfill_coverage():
    late_observed = T0 + timedelta(minutes=1)
    got = _assess(
        decision_at=T0,
        generated_at=late_observed,
        source_reads=[
            _read(observed_at=late_observed, fresh_until=late_observed),
        ],
    )
    assert got.context_state == "coverage_unknown"
    assert got.coverage_complete is False


def test_source_asof_after_observed_at_is_contract_error():
    with pytest.raises(CatalystContextError):
        _read(source_asof=T0 + timedelta(seconds=1), fresh_until=T0)


def test_known_blocking_event_has_precedence():
    got = _assess(evidence=[_event(relevant_until=T0)])
    assert got.context_state == "blocking_event_observed"
    assert got.blocking_evidence_refs == ("event:evt-1",)


def test_unknown_owner_disposition_fails_closed():
    got = _assess(evidence=[_event(disposition="unknown", relevant_until=T0)])
    assert got.context_state == "event_classification_unknown"
    assert got.unknown_evidence_refs == ("event:evt-1",)


def test_soft_event_is_context_not_blocking_authority():
    got = _assess(evidence=[_event(disposition="soft", relevant_until=T0)])
    assert got.context_state == "soft_event_observed"
    payload = got.to_dict()
    assert all(value is False for value in payload["authority"].values())
    assert payload["research_only"] is True


def test_late_blocking_event_does_not_rewrite_past_decision():
    late_known = T0 + timedelta(minutes=5)
    late = _event(
        known_at=late_known, ref="event:late", relevant_until=late_known,
    )
    got = _assess(evidence=[late], generated_at=late_known)
    assert got.context_state == "no_blocking_event_observed"
    assert got.blocking_evidence_refs == ()
    assert got.late_evidence_refs == ("event:late",)


def test_evidence_available_after_known_at_is_contract_error():
    with pytest.raises(CatalystContextError):
        _event(source_available_at=T0 + timedelta(seconds=1), relevant_until=T0)


def test_wrong_ticker_is_refused():
    with pytest.raises(CatalystContextError):
        _assess(evidence=[_event(ticker="AMD", relevant_until=T0)])


def test_exact_duplicate_evidence_is_idempotent():
    row = _event(relevant_until=T0)
    got = _assess(evidence=[row, row])
    assert got.blocking_evidence_refs == ("event:evt-1",)


def test_conflicting_duplicate_evidence_fails_closed_at_contract_boundary():
    a = _event(relevant_until=T0)
    b = _event(disposition="soft", relevant_until=T0)
    with pytest.raises(CatalystContextError):
        _assess(evidence=[a, b])


def test_owner_radar_episode_id_is_passed_through_without_wrapper_identity():
    got = _assess(radar_episode_id="deadbeefdeadbeef")
    payload = got.to_dict()
    assert got.radar_episode_id == "deadbeefdeadbeef"
    assert payload["radar_episode_schema"] == RADAR_EPISODE_SCHEMA
    assert payload["radar_episode_id"] == "deadbeefdeadbeef"
    assert "tactical_episode_ref" not in payload

@pytest.mark.parametrize(
    "bad_id",
    [
        "radar:episode:deadbeef",
        "mastermind.live_entry_episode.v1:deadbeef",
        "DEADBEEFDEADBEEF",
        "deadbeef",
        "g" * 16,
    ],
)
def test_surrogate_or_malformed_radar_episode_identity_is_refused(bad_id):
    with pytest.raises(CatalystContextError):
        _assess(radar_episode_id=bad_id)


def test_output_is_deterministic_and_contains_no_strength_fields():
    got = _assess(
        required_sources=["halt_feed", "issuer_events"],
        source_reads=[
            _read("issuer_events", fresh_until=T0),
            _read("halt_feed", fresh_until=T0),
        ],
        evidence=[
            _event(
                native_id="2", disposition="nonblocking", ref="event:z", relevant_until=T0,
            ),
            _event(
                native_id="1", disposition="soft", ref="event:a", relevant_until=T0,
            ),
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
        _assess(source_reads=[_read(fresh_until=T0), _read(fresh_until=T0)])




def _item202_row(**overrides):
    row = {
        "ticker": "NVDA",
        "cik": 1045810,
        "accession": "0001045810-26-000123",
        "form": "8-K",
        "filing_date": "2026-10-02",
        "acceptance_datetime": "2026-10-02T14:00:00Z",
        "report_date": "2026-09-30",
        "items": "2.02,9.01",
    }
    row.update(overrides)
    return row


def test_edgar_item202_adapter_uses_canonical_filing_identity_and_observed_clock():
    got = adapt_edgar_earnings_item_202(
        _item202_row(accession="000104581026000123"),
        owner_observed_at=T0,
    )
    assert got.native_id == "0001045810:0001045810-26-000123"
    assert got.evidence_ref == "sec-edgar-item202:0001045810:0001045810-26-000123"
    assert got.event_kind == "earnings_results_item_2_02"
    assert got.owner_disposition == "blocking"
    assert got.source_available_at < got.known_at


def test_edgar_item202_amendment_is_distinct_blocking_presence_evidence():
    got = adapt_edgar_earnings_item_202(
        _item202_row(form="8-K/A"), owner_observed_at=T0,
    )
    assert got.event_kind == "earnings_results_item_2_02_amendment"
    assert got.owner_disposition == "blocking"


@pytest.mark.parametrize("items", ["12.02,9.01", "2.020", "9.01", ""])
def test_edgar_item202_adapter_requires_exact_item_token(items):
    with pytest.raises(CatalystContextError):
        adapt_edgar_earnings_item_202(_item202_row(items=items), owner_observed_at=T0)


def test_edgar_item202_adapter_refuses_non_8k_forms():
    with pytest.raises(CatalystContextError):
        adapt_edgar_earnings_item_202(_item202_row(form="10-Q"), owner_observed_at=T0)


def test_edgar_item202_adapter_refuses_missing_canonical_identity():
    with pytest.raises(CatalystContextError):
        adapt_edgar_earnings_item_202(_item202_row(accession=""), owner_observed_at=T0)


def test_edgar_item202_adapter_refuses_missing_acceptance_clock():
    with pytest.raises(CatalystContextError):
        adapt_edgar_earnings_item_202(
            _item202_row(acceptance_datetime=""), owner_observed_at=T0,
        )


def test_edgar_item202_adapter_refuses_observation_before_source_availability():
    with pytest.raises(CatalystContextError):
        adapt_edgar_earnings_item_202(
            _item202_row(acceptance_datetime="2026-10-02T14:31:00Z"),
            owner_observed_at=T0,
        )


def _company_workspace(
    *,
    state="complete",
    event_id="evt_cik0001045810_2026q3_results",
    listing_ticker="NVDA",
    source_available_at="2026-10-02T14:00:00Z",
    observed_at="2026-10-02T14:05:00Z",
    generated_at="2026-10-02T14:10:00Z",
    generation_id="aaaaaaaaaaaaaaaaaaaaaaaa",
):
    return {
        "schema": "event_workspace.v1",
        "event_id": event_id,
        "aliases": [],
        "issuer": {
            "company_id": "cik:0001045810",
            "display_name": "NVIDIA Corporation",
            "listings": [{"ticker": listing_ticker}],
        },
        "fiscal_period": {"year": 2026, "quarter": 3, "calendar_end": "2026-09-30"},
        "lifecycle": {
            "state": state,
            "source_available_at": source_available_at,
            "observed_at": observed_at,
        },
        "completeness": {},
        "facts": [],
        "deltas": [],
        "guidance": [],
        "claims": [],
        "sources": [],
        "warnings": [],
        "generation_id": generation_id,
        "generated_at": generated_at,
        "authority": "context_only",
        "prophet_flags": {
            "may_rank": False,
            "may_size": False,
            "may_gate": False,
            "prophet_authority": False,
        },
        "claim_citations_pending": False,
        "qa_exchanges": [],
    }


def test_company_workspace_adapter_preserves_exact_owner_version_and_consumer_clock():
    got = adapt_company_intelligence_earnings_workspace(
        _company_workspace(), ticker="NVDA", owner_observed_at=T0,
    )
    version = "evt_cik0001045810_2026q3_results@aaaaaaaaaaaaaaaaaaaaaaaa"
    assert got.native_id == version
    assert got.evidence_ref == f"company-intelligence-workspace:{version}"
    assert got.event_kind == "earnings_results_company_event"
    assert got.owner_disposition == "blocking"
    assert got.known_at == T0
    assert got.source_available_at == datetime(2026, 10, 2, 14, 0, tzinfo=timezone.utc)


@pytest.mark.parametrize("state", ["complete", "corrected"])
def test_company_workspace_adapter_accepts_only_current_published_results_states(state):
    got = adapt_company_intelligence_earnings_workspace(
        _company_workspace(state=state), ticker="NVDA", owner_observed_at=T0,
    )
    assert got.owner_disposition == "blocking"


@pytest.mark.parametrize(
    "state",
    [
        "discovered",
        "scheduled",
        "rescheduled",
        "started",
        "completed_partial",
        "derived_ready",
        "distributed",
        "cancelled",
        "superseded",
    ],
)
def test_company_workspace_adapter_refuses_states_not_minted_by_current_workspace_publisher(state):
    with pytest.raises(CatalystContextError):
        adapt_company_intelligence_earnings_workspace(
            _company_workspace(state=state), ticker="NVDA", owner_observed_at=T0,
        )


def test_company_workspace_adapter_refuses_wrong_listing_ticker():
    with pytest.raises(CatalystContextError):
        adapt_company_intelligence_earnings_workspace(
            _company_workspace(listing_ticker="AMD"), ticker="NVDA", owner_observed_at=T0,
        )


def test_company_workspace_adapter_refuses_non_results_event_identity():
    with pytest.raises(CatalystContextError):
        adapt_company_intelligence_earnings_workspace(
            _company_workspace(event_id="evt_cik0001045810_2026q3_call"),
            ticker="NVDA",
            owner_observed_at=T0,
        )


def test_company_workspace_adapter_refuses_lifecycle_clock_inversion():
    with pytest.raises(CatalystContextError):
        adapt_company_intelligence_earnings_workspace(
            _company_workspace(
                source_available_at="2026-10-02T14:06:00Z",
                observed_at="2026-10-02T14:05:00Z",
            ),
            ticker="NVDA",
            owner_observed_at=T0,
        )


def test_company_workspace_adapter_refuses_generation_before_owner_event_observation():
    with pytest.raises(CatalystContextError):
        adapt_company_intelligence_earnings_workspace(
            _company_workspace(generated_at="2026-10-02T14:04:00Z"),
            ticker="NVDA",
            owner_observed_at=T0,
        )


def test_company_workspace_adapter_refuses_consumer_clock_before_generation():
    with pytest.raises(CatalystContextError):
        adapt_company_intelligence_earnings_workspace(
            _company_workspace(generated_at="2026-10-02T14:31:00Z"),
            ticker="NVDA",
            owner_observed_at=T0,
        )


def test_known_company_blocking_event_remains_visible_when_coverage_is_incomplete():
    evidence = adapt_company_intelligence_earnings_workspace(
        _company_workspace(), ticker="NVDA", owner_observed_at=T0,
    )
    got = assess_catalyst_context(
        ticker="NVDA",
        radar_episode_id="0123456789abcdef",
        decision_at=T0,
        generated_at=T0,
        required_sources=["company_intelligence"],
        source_reads=[],
        evidence=[evidence],
    )
    assert got.coverage_complete is False
    assert got.context_state == "blocking_event_observed"
    assert got.blocking_evidence_refs == (evidence.evidence_ref,)


def _live_episode(**overrides):
    identity = {
        "ticker": "NVDA",
        "detector_id": "C1_1D_LIVE_WASHOUT@1",
        "variant": None,
        "first_armed_at": "2026-10-02T14:10:00Z",
    }
    for key in ("ticker", "detector_id", "variant", "first_armed_at"):
        if key in overrides:
            identity[key] = overrides[key]
    episode_id = overrides.get("episode_id") or compute_episode_id(**identity)
    return LiveEpisode(
        episode_id=episode_id,
        ticker=identity["ticker"],
        detector_id=identity["detector_id"],
        detector_version=1,
        detector_spec_hash="spec-test",
        state="CANDIDATE",
        market_session="2026-10-02",
        variant=identity["variant"],
        first_armed_at=identity["first_armed_at"],
        candidate_at="2026-10-02T14:20:00Z",
        last_observed_at="2026-10-02T14:30:00Z",
        bar_availability={},
        feature_snapshot={},
        universe_admission={},
        lobe_nominations=(),
        price_at_signal=100.0,
        risk_geometry={},
        data_quality="ok",
        freshness={},
        evidence_refs=("entry-event-owner-id",),
    )


def test_live_episode_binding_uses_owner_id_and_ticker_without_mutation():
    episode = _live_episode()
    before = episode.to_dict()
    got = assess_catalyst_context_for_live_episode(
        episode=episode,
        decision_at=T0,
        generated_at=T0,
        required_sources=["issuer_events"],
        source_reads=[_read(fresh_until=T0)],
        evidence=[],
    )
    assert got.radar_episode_id == episode.episode_id
    assert got.ticker == "NVDA"
    assert episode.to_dict() == before
    assert episode.evidence_refs == ("entry-event-owner-id",)
    assert "entry-event-owner-id" not in got.to_dict()["blocking_evidence_refs"]


def test_live_episode_mapping_roundtrip_binds_same_owner_identity():
    episode = _live_episode()
    got = assess_catalyst_context_for_live_episode(
        episode=episode.to_dict(),
        decision_at=T0,
        generated_at=T0,
        required_sources=["issuer_events"],
        source_reads=[_read(fresh_until=T0)],
        evidence=[],
    )
    assert got.radar_episode_id == episode.episode_id


def test_tampered_live_episode_id_is_refused_before_context_build():
    episode = _live_episode().to_dict()
    episode["episode_id"] = "deadbeefdeadbeef"
    with pytest.raises(CatalystContextError, match="does not match owner identity tuple"):
        assess_catalyst_context_for_live_episode(
            episode=episode,
            decision_at=T0,
            generated_at=T0,
            required_sources=["issuer_events"],
            source_reads=[_read(fresh_until=T0)],
            evidence=[],
        )


def test_live_episode_binding_preserves_evidence_ticker_check():
    episode = _live_episode()
    with pytest.raises(CatalystContextError, match="does not match"):
        assess_catalyst_context_for_live_episode(
            episode=episode,
            decision_at=T0,
            generated_at=T0,
            required_sources=["issuer_events"],
            source_reads=[_read(fresh_until=T0)],
            evidence=[_event(ticker="AMD", relevant_until=T0)],
        )


def _current_company_read(
    *,
    available=True,
    ticker="NVDA",
    workspace=None,
    note="Verified event workspace context only.",
    receipt=None,
):
    out = {
        "available": available,
        "ticker": ticker,
        "is_context_only": True,
        "display_only": True,
        "authority": "context_only",
        "note": note,
    }
    if available:
        out["workspace"] = workspace or _company_workspace()
        out["event_id"] = out["workspace"]["event_id"]
        out["receipt"] = receipt or {
            "workspace_sha256": sha256(canonical_json_bytes(out["workspace"])).hexdigest()
        }
    return out


def test_current_company_read_found_is_blocking_presence_but_not_coverage_clearance():
    episode = _live_episode()
    got = assess_company_intelligence_current_read_for_live_episode(
        episode=episode,
        read_result=_current_company_read(),
        read_observed_at=T0,
        decision_at=T0,
        generated_at=T0,
    )
    assert got.context_state == "blocking_event_observed"
    assert got.coverage_complete is False
    assert len(got.blocking_evidence_refs) == 1


@pytest.mark.parametrize(
    "note",
    [
        "Event workspace does not cover this ticker",
        "temporary CDN fetch failure",
    ],
)
def test_current_company_read_unavailable_never_becomes_no_event(note):
    got = assess_company_intelligence_current_read_for_live_episode(
        episode=_live_episode(),
        read_result=_current_company_read(available=False, note=note),
        read_observed_at=T0,
        decision_at=T0,
        generated_at=T0,
    )
    assert got.context_state == "coverage_unknown"
    assert got.coverage_complete is False
    assert got.blocking_evidence_refs == ()
    assert got.late_evidence_refs == ()


def test_current_company_read_found_after_decision_is_late_not_backfilled():
    late_observed = T0 + timedelta(minutes=2)
    got = assess_company_intelligence_current_read_for_live_episode(
        episode=_live_episode(),
        read_result=_current_company_read(),
        read_observed_at=late_observed,
        decision_at=T0,
        generated_at=late_observed,
    )
    assert got.context_state == "coverage_unknown"
    assert got.blocking_evidence_refs == ()
    assert len(got.late_evidence_refs) == 1


def test_current_company_read_ticker_mismatch_is_refused():
    with pytest.raises(CatalystContextError, match="does not match Radar episode"):
        assess_company_intelligence_current_read_for_live_episode(
            episode=_live_episode(),
            read_result=_current_company_read(ticker="AMD"),
            read_observed_at=T0,
            decision_at=T0,
            generated_at=T0,
        )


@pytest.mark.parametrize(
    "read_result",
    [
        {"available": True, "is_context_only": True, "authority": "context_only", "ticker": "NVDA"},
        {"available": "yes", "is_context_only": True, "authority": "context_only"},
        {"available": False, "is_context_only": True, "authority": "trade"},
    ],
)
def test_current_company_read_malformed_envelope_fails_closed(read_result):
    with pytest.raises(CatalystContextError):
        assess_company_intelligence_current_read_for_live_episode(
            episode=_live_episode(),
            read_result=read_result,
            read_observed_at=T0,
            decision_at=T0,
            generated_at=T0,
        )


def test_current_company_read_requires_verified_workspace_receipt():
    bad = _current_company_read(receipt={"workspace_sha256": "bad"})
    with pytest.raises(CatalystContextError, match="SHA-256 receipt"):
        assess_company_intelligence_current_read_for_live_episode(
            episode=_live_episode(),
            read_result=bad,
            read_observed_at=T0,
            decision_at=T0,
            generated_at=T0,
        )


def test_current_company_read_cannot_backdate_before_workspace_generation():
    too_early = datetime(2026, 10, 2, 14, 9, tzinfo=timezone.utc)
    with pytest.raises(CatalystContextError, match="workspace generation"):
        assess_company_intelligence_current_read_for_live_episode(
            episode=_live_episode(),
            read_result=_current_company_read(),
            read_observed_at=too_early,
            decision_at=T0,
            generated_at=T0,
        )



def _schema_messages(payload):
    return [
        error.message
        for error in sorted(
            CATALYST_CONTEXT_VALIDATOR.iter_errors(payload),
            key=lambda error: tuple(str(part) for part in error.absolute_path),
        )
    ]


def test_catalyst_context_wire_schema_accepts_runtime_serialization():
    payload = _assess().to_dict()
    assert _schema_messages(payload) == []


def test_catalyst_context_wire_schema_is_closed_to_unknown_root_fields():
    payload = _assess().to_dict()
    payload["surprise_score"] = 99
    errors = _schema_messages(payload)
    assert any("Additional properties are not allowed" in message for message in errors)


def test_catalyst_context_wire_schema_hard_false_authority_cannot_be_escalated():
    payload = copy.deepcopy(_assess().to_dict())
    payload["authority"]["can_gate"] = True
    errors = _schema_messages(payload)
    assert any("False was expected" in message for message in errors)


def test_catalyst_context_wire_schema_refuses_surrogate_episode_identity():
    payload = _assess().to_dict()
    payload["radar_episode_id"] = "radar:episode:abc123"
    errors = _schema_messages(payload)
    assert any("does not match" in message for message in errors)


def test_catalyst_context_wire_schema_requires_nonempty_declared_source_set():
    payload = _assess().to_dict()
    payload["required_sources"] = []
    errors = _schema_messages(payload)
    assert any("should be non-empty" in message or "is too short" in message for message in errors)


@pytest.mark.parametrize(
    ("mutator", "needle"),
    [
        (
            lambda payload: payload.update(
                {
                    "context_state": "coverage_unknown",
                    "coverage_complete": True,
                }
            ),
            "False was expected",
        ),
        (
            lambda payload: payload.update(
                {
                    "context_state": "blocking_event_observed",
                    "blocking_evidence_refs": [],
                }
            ),
            "should be non-empty",
        ),
        (
            lambda payload: payload.update(
                {
                    "context_state": "no_blocking_event_observed",
                    "blocking_evidence_refs": ["event:should-not-exist"],
                }
            ),
            "is expected to be empty",
        ),
    ],
)
def test_catalyst_context_wire_schema_pins_state_semantics(mutator, needle):
    payload = _assess().to_dict()
    mutator(payload)
    errors = _schema_messages(payload)
    assert any(
        needle in message
        or ("is too short" in message and needle == "should be non-empty")
        or ("is too long" in message and needle == "is expected to be empty")
        for message in errors
    )


def test_catalyst_context_wire_schema_pins_house_utc_second_timestamp():
    payload = _assess().to_dict()
    payload["decision_at"] = "2026-10-02T14:30:00+00:00"
    errors = _schema_messages(payload)
    assert any("does not match" in message for message in errors)


def test_catalyst_context_wire_schema_closes_source_read_shape_and_status():
    payload = _assess().to_dict()
    payload["source_reads"][0]["extra"] = "not-owned"
    payload["source_reads"][0]["status"] = "fresh"
    errors = _schema_messages(payload)
    assert any("Additional properties are not allowed" in message for message in errors)
    assert any("is not one of" in message for message in errors)


# Pre-outcome hardening: decision clocks, immutable bindings and collection.
@pytest.mark.parametrize("value", [
    "2026-10-02", "2026-10-02T14:30:00", datetime(2026, 10, 2, 14, 30),
])
@pytest.mark.parametrize("boundary", ["decision", "read", "evidence", "edgar"])
def test_hardening_rejects_ambiguous_clocks(value, boundary):
    with pytest.raises(CatalystContextError):
        if boundary == "decision":
            _assess(decision_at=value)
        elif boundary == "read":
            _read(observed_at=value, fresh_until=T0)
        elif boundary == "evidence":
            _event(known_at=value, relevant_until=T0)
        else:
            adapt_edgar_earnings_item_202(
                _item202_row(acceptance_datetime=value), owner_observed_at=T0,
            )


def test_hardening_preserves_subsecond_decision_and_source_wire_clocks():
    instant = T0 + timedelta(microseconds=150001)
    payload = _assess(
        decision_at=instant,
        generated_at=instant,
        source_reads=[_read(observed_at=instant, fresh_until=instant)],
    ).to_dict()
    assert payload["decision_at"] == "2026-10-02T14:30:00.150001Z"
    assert payload["source_reads"][0]["observed_at"] == payload["decision_at"]
    assert _schema_messages(payload) == []


def test_hardening_subsecond_conflicting_evidence_is_not_deduplicated():
    a = _event(
        known_at=T0 + timedelta(microseconds=100),
        source_available_at=T0,
        relevant_until=T0,
    )
    b = _event(
        known_at=T0 + timedelta(microseconds=200),
        source_available_at=T0,
        relevant_until=T0,
    )
    with pytest.raises(CatalystContextError, match="conflicting"):
        _assess(
            evidence=[a, b],
            generated_at=T0 + timedelta(microseconds=200),
        )


def test_hardening_equivalent_offset_clocks_remain_identical():
    a = _event(relevant_until=T0)
    b = _event(
        known_at=T0.astimezone(timezone(timedelta(hours=-4))),
        relevant_until=T0,
    )
    assert _assess(evidence=[a, b]).blocking_evidence_refs == ("event:evt-1",)


@pytest.mark.parametrize("field", ["first_armed_at", "candidate_at", "last_observed_at"])
def test_hardening_rejects_episode_snapshot_after_decision(field):
    episode = _live_episode().to_dict()
    episode[field] = "2026-10-02T14:30:01Z"
    episode["episode_id"] = compute_episode_id(**{
        k: episode[k] for k in ("ticker", "detector_id", "variant", "first_armed_at")
    })
    with pytest.raises(CatalystContextError, match="after decision"):
        assess_catalyst_context_for_live_episode(
            episode=episode,
            decision_at=T0,
            generated_at=T0,
            required_sources=["issuer_events"],
            source_reads=[],
            evidence=[],
        )


@pytest.mark.parametrize("field", ["first_armed_at", "last_observed_at"])
def test_hardening_requires_episode_snapshot_clocks(field):
    episode = _live_episode().to_dict()
    episode[field] = None
    episode["episode_id"] = compute_episode_id(**{
        k: episode[k] for k in ("ticker", "detector_id", "variant", "first_armed_at")
    })
    with pytest.raises(CatalystContextError):
        assess_catalyst_context_for_live_episode(
            episode=episode,
            decision_at=T0,
            generated_at=T0,
            required_sources=["issuer_events"],
            source_reads=[],
            evidence=[],
        )


@pytest.mark.parametrize("mutation", ["hash", "body", "envelope_event"])
def test_hardening_binds_company_receipt_to_exact_workspace(mutation):
    read = _current_company_read()
    if mutation == "hash":
        read["receipt"]["workspace_sha256"] = "0" * 64
    elif mutation == "body":
        read["workspace"]["issuer"]["display_name"] = "Changed after owner verification"
    else:
        read["event_id"] = "evt_cik0001045810_2026q2_results"
    with pytest.raises(CatalystContextError):
        assess_company_intelligence_current_read_for_live_episode(
            episode=_live_episode(),
            read_result=read,
            read_observed_at=T0,
            decision_at=T0,
            generated_at=T0,
        )


def test_hardening_binds_company_event_to_native_issuer():
    workspace = _company_workspace(event_id="evt_cik0000320193_2026q3_results")
    with pytest.raises(CatalystContextError):
        adapt_company_intelligence_earnings_workspace(
            workspace, ticker="NVDA", owner_observed_at=T0,
        )


@pytest.mark.parametrize("changes", [
    {"coverage_complete": False}, {"context_state": "blocking_event_observed"},
    {"required_sources": ()}, {"schema": "other"},
])
def test_hardening_direct_context_cannot_forge_inconsistent_wire(changes):
    with pytest.raises(CatalystContextError):
        replace(_assess(), **changes)


def test_hardening_required_sources_is_not_a_bare_string():
    with pytest.raises(CatalystContextError):
        _assess(required_sources="issuer_events")


@pytest.mark.parametrize("case", ["found", "uncovered", "corrupt_body"])
def test_owner_publisher_reader_to_catalyst(tmp_path, monkeypatch, case):
    """Exercise real owner publication and receipt validation, not a forged envelope.

    Only the HTTP byte transport is substituted. No provider, outcome or live
    ledger is read or written; all owner records here are fabricated fixtures.
    """
    from engine.company_intelligence.event_workspace import write_workspace_generation
    from engine.neuralweb import company_intelligence_reader as reader

    workspace = _company_workspace()
    workspace["aliases"] = [] if case == "uncovered" else ["NVDA/2026Q3"]
    product = tmp_path / "company_intelligence"
    generation = write_workspace_generation(
        product, {workspace["event_id"]: workspace},
        generated_at=workspace["generated_at"],
    )
    # A distinct origin per fixture also prevents a cached previous case masking corruption.
    base = "https://catalyst-owner-" + tmp_path.name.lower().replace("_", "-") + ".example"
    paths = {base + "/" + p.relative_to(product).as_posix(): p.read_bytes()
             for p in product.rglob("*.json")}
    body_url = base + "/event_workspaces/generations/" + generation.name + "/workspaces/" + workspace["event_id"] + ".json"
    if case == "corrupt_body":
        body = json.loads(paths[body_url])
        body["issuer"]["display_name"] = "Corrupted body after manifest publication"
        paths[body_url] = canonical_json_bytes(body)
    calls = []

    def fetch_bytes(url, *, limit, allow_404=False):
        calls.append(url)
        assert url in paths, "Unexpected source: " + url
        assert len(paths[url]) <= limit
        return paths[url]

    monkeypatch.setattr(reader, "_public_base_url", lambda: base)
    monkeypatch.setattr(reader, "_fetch_bytes", fetch_bytes)
    read = reader.read_current_event_workspace({"ticker": "NVDA"})
    context = assess_company_intelligence_current_read_for_live_episode(
        episode=_live_episode(),
        read_result=read,
        read_observed_at=T0,
        decision_at=T0,
        generated_at=T0,
    )
    assert calls
    assert context.coverage_complete is False
    assert all(v is False for v in context.to_dict()["authority"].values())
    if case == "found":
        assert read["available"] is True, read.get("note")
        assert body_url in calls
        assert context.context_state == "blocking_event_observed"
        assert generation.name in context.blocking_evidence_refs[0]
        before_calls = list(calls)
        warm_read = reader.read_current_event_workspace({"ticker": "NVDA"})
        warm_context = assess_company_intelligence_current_read_for_live_episode(
            episode=_live_episode(),
            read_result=warm_read,
            read_observed_at=T0,
            decision_at=T0,
            generated_at=T0,
        )
        assert calls == before_calls, "Warm validation must not add a network fetch"
        assert warm_read["receipt"]["workspace_sha256"] == read["receipt"]["workspace_sha256"]
        assert warm_context.to_dict() == context.to_dict()
    else:
        assert read["available"] is False
        assert context.context_state == "coverage_unknown"
        assert context.blocking_evidence_refs == ()


DECISION_LATE = datetime(2026, 10, 3, 15, 0, tzinfo=timezone.utc)
STALE_ASOF = datetime(2026, 1, 2, tzinfo=timezone.utc)
STALE_FRESH = datetime(2026, 1, 3, tzinfo=timezone.utc)


def test_stale_ok_read_cannot_clear_coverage():
    got = assess_catalyst_context(
        ticker="NVDA",
        radar_episode_id="0123456789abcdef",
        decision_at=DECISION_LATE,
        generated_at=DECISION_LATE,
        required_sources=["issuer_events"],
        source_reads=[
            _read(
                observed_at=STALE_ASOF,
                source_asof=STALE_ASOF,
                fresh_until=STALE_FRESH,
                status="ok",
            )
        ],
        evidence=[],
    )
    assert got.context_state == "coverage_unknown"
    assert got.coverage_complete is False


def test_read_fresh_through_decision_clears_coverage():
    got = assess_catalyst_context(
        ticker="NVDA",
        radar_episode_id="0123456789abcdef",
        decision_at=DECISION_LATE,
        generated_at=DECISION_LATE,
        required_sources=["issuer_events"],
        source_reads=[
            _read(
                observed_at=STALE_ASOF,
                source_asof=STALE_ASOF,
                fresh_until=DECISION_LATE,
                status="ok",
            )
        ],
        evidence=[],
    )
    assert got.context_state == "no_blocking_event_observed"
    assert got.coverage_complete is True


def test_fresh_until_before_source_asof_is_refused():
    with pytest.raises(CatalystContextError):
        _read(
            source_asof=STALE_ASOF,
            observed_at=STALE_ASOF,
            fresh_until=STALE_ASOF - timedelta(seconds=1),
        )


def test_expired_blocking_event_does_not_drive_state():
    expired = _event(
        disposition="blocking",
        known_at=STALE_ASOF,
        source_available_at=STALE_ASOF,
        relevant_until=STALE_FRESH,
        ref="event:expired-block",
    )
    got = assess_catalyst_context(
        ticker="NVDA",
        radar_episode_id="0123456789abcdef",
        decision_at=DECISION_LATE,
        generated_at=DECISION_LATE,
        required_sources=["issuer_events"],
        source_reads=[_read(observed_at=DECISION_LATE, fresh_until=DECISION_LATE)],
        evidence=[expired],
    )
    assert got.context_state == "no_blocking_event_observed"
    assert got.blocking_evidence_refs == ()
    assert got.expired_evidence_refs == ("event:expired-block",)


def test_active_blocking_event_still_blocks():
    active = _event(
        disposition="blocking",
        known_at=STALE_ASOF,
        source_available_at=STALE_ASOF,
        relevant_until=DECISION_LATE,
        ref="event:active-block",
    )
    got = assess_catalyst_context(
        ticker="NVDA",
        radar_episode_id="0123456789abcdef",
        decision_at=DECISION_LATE,
        generated_at=DECISION_LATE,
        required_sources=["issuer_events"],
        source_reads=[_read(observed_at=DECISION_LATE, fresh_until=DECISION_LATE)],
        evidence=[active],
    )
    assert got.context_state == "blocking_event_observed"
    assert got.blocking_evidence_refs == ("event:active-block",)


def test_late_event_is_late_not_expired():
    late = _event(
        known_at=DECISION_LATE + timedelta(minutes=1),
        relevant_until=DECISION_LATE + timedelta(days=1),
        ref="event:late-only",
    )
    got = assess_catalyst_context(
        ticker="NVDA",
        radar_episode_id="0123456789abcdef",
        decision_at=DECISION_LATE,
        generated_at=DECISION_LATE + timedelta(minutes=1),
        required_sources=["issuer_events"],
        source_reads=[_read(observed_at=DECISION_LATE, fresh_until=DECISION_LATE)],
        evidence=[late],
    )
    assert got.late_evidence_refs == ("event:late-only",)
    assert got.expired_evidence_refs == ()


def test_relevant_until_before_source_available_is_refused():
    with pytest.raises(CatalystContextError):
        _event(
            source_available_at=T0,
            known_at=T0,
            relevant_until=T0 - timedelta(seconds=1),
        )


def test_decision_after_generated_at_is_refused():
    with pytest.raises(CatalystContextError):
        _assess(
            decision_at=datetime(2099, 1, 1, tzinfo=timezone.utc),
            generated_at=datetime(2026, 10, 3, tzinfo=timezone.utc),
        )


def test_evidence_known_after_generated_at_is_refused():
    with pytest.raises(CatalystContextError):
        _assess(
            generated_at=T0,
            evidence=[
                _event(
                    known_at=T0 + timedelta(seconds=1),
                    relevant_until=T0 + timedelta(days=1),
                )
            ],
        )


def test_source_read_observed_after_generated_at_is_refused():
    with pytest.raises(CatalystContextError):
        _assess(
            generated_at=T0,
            source_reads=[_read(observed_at=T0 + timedelta(seconds=1), fresh_until=T0)],
        )


def test_wire_carries_generated_at_and_evidence_clocks():
    got = _assess(
        evidence=[
            _event(relevant_until=T0, ref="event:a"),
            _event(native_id="2", disposition="soft", ref="event:b", relevant_until=T0),
        ],
    )
    payload = got.to_dict()
    assert payload["generated_at"] == "2026-10-02T14:30:00Z"
    assert "expired_evidence_refs" in payload
    clocks = {row["evidence_ref"]: row for row in payload["evidence_clocks"]}
    for ref in (
        "event:a",
        "event:b",
    ):
        assert ref in clocks
        assert clocks[ref]["timing"] == "active"
        assert clocks[ref]["known_at"]
        assert clocks[ref]["relevant_until"]
        assert clocks[ref]["source_available_at"]


def test_shared_evidence_ref_across_identities_is_refused():
    a = _event(native_id="a", ref="event:shared", relevant_until=T0)
    b = _event(native_id="b", ref="event:shared", relevant_until=T0)
    with pytest.raises(CatalystContextError, match="evidence_ref maps"):
        _assess(evidence=[a, b])


def test_forged_context_with_overlapping_ref_groups_is_refused():
    base = _assess(evidence=[_event(relevant_until=T0)])
    with pytest.raises(CatalystContextError):
        CatalystContext(
            ticker=base.ticker,
            radar_episode_id=base.radar_episode_id,
            decision_at=base.decision_at,
            generated_at=base.generated_at,
            context_state=base.context_state,
            coverage_complete=base.coverage_complete,
            required_sources=base.required_sources,
            source_reads=base.source_reads,
            blocking_evidence_refs=base.blocking_evidence_refs,
            soft_evidence_refs=base.blocking_evidence_refs,
            unknown_evidence_refs=(),
            nonblocking_evidence_refs=(),
            late_evidence_refs=(),
            expired_evidence_refs=(),
            evidence_clocks=base.evidence_clocks,
        )


def test_forged_context_with_wrong_clock_timing_is_refused():
    base = _assess(evidence=[_event(relevant_until=T0, ref="event:forge")])
    bad_clock = CatalystEvidenceClock(
        evidence_ref="event:forge",
        source_available_at=T0,
        known_at=T0 + timedelta(hours=1),
        relevant_until=T0 + timedelta(days=1),
        timing="active",
    )
    with pytest.raises(CatalystContextError):
        CatalystContext(
            ticker=base.ticker,
            radar_episode_id=base.radar_episode_id,
            decision_at=base.decision_at,
            generated_at=base.generated_at,
            context_state="no_blocking_event_observed",
            coverage_complete=base.coverage_complete,
            required_sources=base.required_sources,
            source_reads=base.source_reads,
            blocking_evidence_refs=(),
            soft_evidence_refs=(),
            unknown_evidence_refs=(),
            nonblocking_evidence_refs=(),
            late_evidence_refs=(),
            expired_evidence_refs=(),
            evidence_clocks=(bad_clock,),
        )


def test_non_string_detail_is_refused():
    with pytest.raises(CatalystContextError):
        CatalystSourceRead(
            source_id="issuer_events",
            status="ok",
            source_asof=T0,
            observed_at=T0,
            fresh_until=T0,
            detail=123,
        )


def test_oversized_strings_and_arrays_are_refused():
    big_ref = "x" * 257
    with pytest.raises(CatalystContextError):
        _event(ref=big_ref, relevant_until=T0)
    with pytest.raises(CatalystContextError):
        CatalystSourceRead(
            source_id="issuer_events",
            status="ok",
            source_asof=T0,
            observed_at=T0,
            fresh_until=T0,
            detail="d" * 513,
        )
    with pytest.raises(CatalystContextError):
        _assess(required_sources=[f"src-{i}" for i in range(33)])
    with pytest.raises(CatalystContextError):
        _assess(
            evidence=[
                _event(
                    native_id=f"evt-{i}",
                    ref=f"event:{i}",
                    relevant_until=T0,
                )
                for i in range(257)
            ],
        )


@pytest.mark.parametrize(
    "builder",
    [
        lambda: _assess(),
        lambda: _assess(evidence=[_event(disposition="soft", relevant_until=T0)]),
        lambda: _assess(evidence=[_event(disposition="unknown", relevant_until=T0)]),
        lambda: _assess(source_reads=[_read(status="stale", fresh_until=T0)]),
        lambda: _assess(
            evidence=[
                _event(
                    known_at=T0 + timedelta(minutes=1),
                    relevant_until=T0 + timedelta(days=1),
                    ref="event:late-probe",
                )
            ],
            generated_at=T0 + timedelta(minutes=1),
        ),
    ],
)
def test_every_probe_output_validates_against_schema(builder):
    assert _schema_messages(builder().to_dict()) == []


@pytest.mark.parametrize(
    ("instant", "expected_close"),
    [
        (
            datetime(2026, 7, 30, 20, 30, 28, tzinfo=timezone.utc),
            datetime(2026, 7, 31, 20, 0, tzinfo=timezone.utc),
        ),
        (
            datetime(2026, 7, 31, 11, 0, 0, tzinfo=timezone.utc),
            datetime(2026, 7, 31, 20, 0, tzinfo=timezone.utc),
        ),
        (
            datetime(2026, 7, 31, 15, 0, 0, tzinfo=timezone.utc),
            datetime(2026, 8, 3, 20, 0, tzinfo=timezone.utc),
        ),
        (
            datetime(2026, 7, 31, 13, 30, 0, tzinfo=timezone.utc),
            datetime(2026, 7, 31, 20, 0, tzinfo=timezone.utc),
        ),
    ],
)
def test_first_full_session_close_after_examples(instant, expected_close):
    got = first_full_session_close_after(instant)
    assert got == expected_close


def test_first_full_session_close_after_fails_closed_past_calendar_edge():
    with pytest.raises(CatalystContextError):
        first_full_session_close_after(datetime(2999, 1, 1, tzinfo=timezone.utc))


def test_edgar_adapter_sets_relevance_through_next_full_session():
    acceptance = datetime(2026, 7, 31, 15, 0, tzinfo=timezone.utc)
    got = adapt_edgar_earnings_item_202(
        _item202_row(acceptance_datetime=acceptance.isoformat().replace("+00:00", "Z")),
        owner_observed_at=acceptance + timedelta(minutes=5),
    )
    assert got.relevant_until == datetime(2026, 8, 3, 20, 0, tzinfo=timezone.utc)


def test_amendment_stays_a_separate_reference():
    original = adapt_edgar_earnings_item_202(
        _item202_row(form="8-K", accession="0001045810-26-000100"),
        owner_observed_at=T0,
    )
    amended = adapt_edgar_earnings_item_202(
        _item202_row(form="8-K/A", accession="0001045810-26-000101"),
        owner_observed_at=T0,
    )
    assert original.evidence_ref != amended.evidence_ref
    assert original.native_id != amended.native_id
    ctx = _assess(evidence=[original, amended])
    assert len(ctx.evidence_clocks) == 2
    refs = {clock.evidence_ref for clock in ctx.evidence_clocks}
    assert refs == {original.evidence_ref, amended.evidence_ref}
