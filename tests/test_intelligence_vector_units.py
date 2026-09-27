from __future__ import annotations

import json
from hashlib import sha256

import pytest

from engine.prophet_lab.intelligence_vector import (
    _MAX_REVENUE,
    _REVENUE_UNIT_SCALE,
    _REVENUE_UNITS,
    build_earnings_intelligence_vector,
    validate_intelligence_vector,
)
from engine.us_candidate_episode import episode_id as b1_episode_id
from lib.dataos.identity import IssuerMaster


_ANCHOR = {
    "kind": "turn_watch_reset_low",
    "time": "2026-07-30T20:00:00Z",
    "price": "100.0000",
    "basis": "turn_watch.reset_low",
    "source_receipt": "sha256:" + "b" * 64,
}
_EVENT_ID = "evt_cik0000320193_2026q3_results"
_GENERATION_ID = "peg:" + "a" * 64


def _unit_workspace(*, value: int, unit: str) -> dict:
    return {
        "schema": "event_workspace.v1",
        "event_id": _EVENT_ID,
        "generation_id": "1" * 24,
        "issuer": {
            "company_id": "cik:0000320193",
            "display_name": "Apple Inc.",
        },
        "fiscal_period": {
            "year": 2026,
            "quarter": 3,
            "calendar_end": "2026-06-27",
        },
        "lifecycle": {
            "state": "complete",
            "source_available_at": "2026-07-30T20:00:00Z",
            "observed_at": "2026-07-30T20:03:00Z",
        },
        "generated_at": "2026-07-30T20:04:00Z",
        "facts": [{
            "schema": "event_fact.v1",
            "metric": "revenue",
            "value": value,
            "unit": unit,
            "period": "2026Q3",
            "basis": "reported",
            "source_span": {"document_id": "doc:issuer-release:1"},
        }],
        "deltas": [{
            "schema": "metric_delta.v1",
            "metric": "revenue",
            "current": {
                "value": value,
                "unit": unit,
                "basis": "reported",
            },
            "prior": {"state": "absent", "reason": "not_available"},
            "consensus": {"state": "absent", "reason": "consensus_unlicensed"},
            "basis_match": False,
        }],
        "guidance": [],
        "claims": [],
        "sources": [{
            "kind": "issuer_release",
            "document_id": "doc:issuer-release:1",
            "source_sha256": "c" * 64,
            "receipt_state": "byte_replayed",
        }],
        "warnings": [],
    }


def _revisions(*, value: int, unit: str) -> list[dict]:
    workspace = _unit_workspace(value=value, unit=unit)
    canonical_workspace = json.dumps(
        workspace, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode()
    return [{
        "generation_id": workspace["generation_id"],
        "source_sha256": workspace["sources"][0]["source_sha256"],
        "source_available_at": workspace["lifecycle"]["source_available_at"],
        "observed_at": workspace["lifecycle"]["observed_at"],
        "lifecycle_state": "complete",
        "form": "8-K",
        "workspace_receipt": {
            "sha256": sha256(canonical_workspace).hexdigest(),
            "bytes": len(canonical_workspace),
        },
        "workspace": workspace,
    }]


def _build_unit_projection(*, value: int, unit: str) -> dict:
    episode = {
        "schema": "prophet.candidate_episode/v1",
        "episode_id": b1_episode_id(
            "SEC:US-XNAS-AAPL", "epoch_0", _ANCHOR, 1,
        ),
        "company_id": "ISS:US:320193",
        "security_id": "SEC:US-XNAS-AAPL",
        "identity_epoch": "epoch_0",
        "state": "CANDIDATE",
        "opened_at": "2026-07-30T20:05:00Z",
        "opened_session": "2026-07-30",
        "structural_anchor": _ANCHOR,
        "expert_events": ["radar:event:content-addressed-1"],
    }
    issuer_master = IssuerMaster.from_records([{
        "security_id": "SEC:US-XNAS-AAPL",
        "issuer_id": "ISS:US:320193",
        "issuer_state": "active",
        "listing_key": "US:XNAS:AAPL",
        "issuer_cik": "0000320193",
    }])
    return build_earnings_intelligence_vector(
        episode=episode,
        episode_generation_id=_GENERATION_ID,
        episode_known_at="2026-07-30T20:05:00Z",
        issuer_master=issuer_master,
        find_event_id=lambda company_id: _EVENT_ID,
        read_revisions=lambda event_id: _revisions(value=value, unit=unit),
    )


def _revenue_observation(payload: dict) -> dict | None:
    return next((
        observation for observation
        in payload["evidence_families"][0]["observations"]
        if observation["native_metric_id"] == "fact:revenue"
    ), None)


def test_revenue_units_normalize_to_identical_usd_values() -> None:
    raw_usd = _build_unit_projection(
        value=109_417_000_000, unit="USD",
    )
    usd_millions = _build_unit_projection(
        value=109_417, unit="usd_millions",
    )
    raw_observation = _revenue_observation(raw_usd)
    producer_observation = _revenue_observation(usd_millions)

    assert raw_observation is not None
    assert producer_observation is not None
    assert raw_observation["value_usd"] == 109_417_000_000
    assert producer_observation["value_usd"] == raw_observation["value_usd"]
    validate_intelligence_vector(raw_usd)
    validate_intelligence_vector(usd_millions)


def test_revenue_observation_preserves_native_value_and_unit() -> None:
    observation = _revenue_observation(_build_unit_projection(
        value=109_417_000_000, unit="USD",
    ))

    assert observation is not None
    assert observation["value"] == 109_417_000_000
    assert observation["units"] == "USD"
    assert set(observation) == {
        "observation_id", "native_metric_id", "value_state", "value", "units",
        "value_usd", "method_class", "method_version", "source_ref_ids",
        "evidence_root_ids", "economic_dependence_group_ids", "quality_flags",
        "absence_reasons", "neutral_definition_ref", "correction_lineage_state",
    }


@pytest.mark.parametrize(
    ("value", "unit"),
    [
        (_MAX_REVENUE + 1, "USD"),
        (_MAX_REVENUE // _REVENUE_UNIT_SCALE["usd_millions"] + 1, "usd_millions"),
    ],
)
def test_revenue_bound_is_applied_to_usd_equivalent(
    value: int, unit: str,
) -> None:
    payload = _build_unit_projection(value=value, unit=unit)

    assert _revenue_observation(payload) is None
    assert payload["evidence_families"][0]["coverage"]["state"] in {
        "COVERED", "PARTIAL", "UNKNOWN", "NOT_COVERED",
    }
    validate_intelligence_vector(payload)


def test_revenue_unit_table_and_admission_set_match() -> None:
    assert set(_REVENUE_UNIT_SCALE) == set(_REVENUE_UNITS)
    assert set(_REVENUE_UNIT_SCALE) == {"USD", "usd_millions"}


@pytest.mark.parametrize("unit", ["eur", "unknown", None])
def test_unknown_revenue_unit_remains_typed_absence(unit: str | None) -> None:
    payload = _build_unit_projection(value=109_417, unit=unit)

    assert _revenue_observation(payload) is None
    assert payload["evidence_families"][0]["coverage"]["state"] == "UNKNOWN"
    validate_intelligence_vector(payload)


def test_current_fact_consistency_still_requires_value_and_unit_match() -> None:
    payload = _build_unit_projection(
        value=109_417_000_000, unit="USD",
    )
    delta = payload["evidence_families"][0]["trajectory"]["dimensions"][0]["value"]

    assert delta["current"] == {
        "value": 109_417_000_000,
        "unit": "USD",
        "basis": "reported",
    }
