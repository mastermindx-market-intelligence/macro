from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from engine.entry_radar.catalyst_context import (
    CatalystContextError,
    CatalystEvidence,
    CatalystSourceRead,
    assess_catalyst_context,
)

from engine.entry_radar.catalyst_adapters import (\n    adapt_company_intelligence_earnings_workspace,\n    adapt_edgar_earnings_item_202,\n)

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
\n\ndef _company_workspace(\n    *,\n    state="complete",\n    event_id="evt_cik0001045810_2026q3_results",\n    listing_ticker="NVDA",\n    source_available_at="2026-10-02T14:00:00Z",\n    observed_at="2026-10-02T14:05:00Z",\n    generated_at="2026-10-02T14:10:00Z",\n    generation_id="aaaaaaaaaaaaaaaaaaaaaaaa",\n):\n    return {\n        "schema": "event_workspace.v1",\n        "event_id": event_id,\n        "aliases": [],\n        "issuer": {\n            "company_id": "cik:0001045810",\n            "display_name": "NVIDIA Corporation",\n            "listings": [{"ticker": listing_ticker}],\n        },\n        "fiscal_period": {"year": 2026, "quarter": 3, "calendar_end": "2026-09-30"},\n        "lifecycle": {\n            "state": state,\n            "source_available_at": source_available_at,\n            "observed_at": observed_at,\n        },\n        "completeness": {},\n        "facts": [],\n        "deltas": [],\n        "guidance": [],\n        "claims": [],\n        "sources": [],\n        "warnings": [],\n        "generation_id": generation_id,\n        "generated_at": generated_at,\n        "authority": "context_only",\n        "prophet_flags": {\n            "may_rank": False,\n            "may_size": False,\n            "may_gate": False,\n            "prophet_authority": False,\n        },\n        "claim_citations_pending": False,\n        "qa_exchanges": [],\n    }\n\n\ndef test_company_workspace_adapter_preserves_exact_owner_version_and_consumer_clock():\n    got = adapt_company_intelligence_earnings_workspace(\n        _company_workspace(), ticker="NVDA", owner_observed_at=T0,\n    )\n    version = "evt_cik0001045810_2026q3_results@aaaaaaaaaaaaaaaaaaaaaaaa"\n    assert got.native_id == version\n    assert got.evidence_ref == f"company-intelligence-workspace:{version}"\n    assert got.event_kind == "earnings_results_company_event"\n    assert got.owner_disposition == "blocking"\n    assert got.known_at == T0\n    assert got.source_available_at == datetime(2026, 10, 2, 14, 0, tzinfo=timezone.utc)\n\n\n@pytest.mark.parametrize(\n    "state",\n    ["started", "completed_partial", "complete", "corrected", "derived_ready", "distributed"],\n)\ndef test_company_workspace_adapter_accepts_only_frozen_post_release_states(state):\n    got = adapt_company_intelligence_earnings_workspace(\n        _company_workspace(state=state), ticker="NVDA", owner_observed_at=T0,\n    )\n    assert got.owner_disposition == "blocking"\n\n\n@pytest.mark.parametrize(\n    "state",\n    ["discovered", "scheduled", "rescheduled", "cancelled", "superseded"],\n)\ndef test_company_workspace_adapter_refuses_pre_release_or_terminal_noncurrent_states(state):\n    with pytest.raises(CatalystContextError):\n        adapt_company_intelligence_earnings_workspace(\n            _company_workspace(state=state), ticker="NVDA", owner_observed_at=T0,\n        )\n\n\ndef test_company_workspace_adapter_refuses_wrong_listing_ticker():\n    with pytest.raises(CatalystContextError):\n        adapt_company_intelligence_earnings_workspace(\n            _company_workspace(listing_ticker="AMD"), ticker="NVDA", owner_observed_at=T0,\n        )\n\n\ndef test_company_workspace_adapter_refuses_non_results_event_identity():\n    with pytest.raises(CatalystContextError):\n        adapt_company_intelligence_earnings_workspace(\n            _company_workspace(event_id="evt_cik0001045810_2026q3_call"),\n            ticker="NVDA",\n            owner_observed_at=T0,\n        )\n\n\ndef test_company_workspace_adapter_refuses_lifecycle_clock_inversion():\n    with pytest.raises(CatalystContextError):\n        adapt_company_intelligence_earnings_workspace(\n            _company_workspace(\n                source_available_at="2026-10-02T14:06:00Z",\n                observed_at="2026-10-02T14:05:00Z",\n            ),\n            ticker="NVDA",\n            owner_observed_at=T0,\n        )\n\n\ndef test_company_workspace_adapter_refuses_generation_before_owner_event_observation():\n    with pytest.raises(CatalystContextError):\n        adapt_company_intelligence_earnings_workspace(\n            _company_workspace(generated_at="2026-10-02T14:04:00Z"),\n            ticker="NVDA",\n            owner_observed_at=T0,\n        )\n\n\ndef test_company_workspace_adapter_refuses_consumer_clock_before_generation():\n    with pytest.raises(CatalystContextError):\n        adapt_company_intelligence_earnings_workspace(\n            _company_workspace(generated_at="2026-10-02T14:31:00Z"),\n            ticker="NVDA",\n            owner_observed_at=T0,\n        )\n\n\ndef test_known_company_blocking_event_remains_visible_when_coverage_is_incomplete():\n    evidence = adapt_company_intelligence_earnings_workspace(\n        _company_workspace(), ticker="NVDA", owner_observed_at=T0,\n    )\n    got = assess_catalyst_context(\n        ticker="NVDA",\n        tactical_episode_ref="radar:episode:abc123",\n        decision_at=T0,\n        required_sources=["company_intelligence"],\n        source_reads=[],\n        evidence=[evidence],\n    )\n    assert got.coverage_complete is False\n    assert got.context_state == "blocking_event_observed"\n    assert got.blocking_evidence_refs == (evidence.evidence_ref,)\n