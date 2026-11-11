"""Packet 4 negative contracts for the existing D5 consumer.

These are deterministic FIXTURES, not real issuer evidence or a live journey.
No provider, production store, paid data, ledger, or real user is accessed.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from urllib.parse import quote

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.prophet_lab as api
from engine.prophet_lab.intelligence_vector import (
    IntelligenceVectorContractError,
    build_earnings_intelligence_vector,
    validate_intelligence_vector,
)
from engine.us_candidate_episode import (
    CandidateEpisodeStoreSnapshot, ValidatedCandidateEpisodeGeneration, episode_id,
)
from lib.dataos.identity import IssuerMaster

CUT = "2026-07-30T20:05:00Z"
GENERATION = "peg:" + "a" * 64
ANCHOR = {
    "kind": "turn_watch_reset_low", "time": "2026-07-30T20:00:00Z",
    "price": "100.0000", "basis": "turn_watch.reset_low",
    "source_receipt": "sha256:" + "b" * 64,
}
BAD_BINDINGS = [
    ("SEC:US-XNAS-MSFT", "AMBIGUOUS", "CONFLICTED"),
    ("SEC:US-XNAS-NOTLISTED", "UNRESOLVED", "IDENTITY_UNRESOLVED"),
    ("SEC:CA-XTSE-AAPL", "UNRESOLVED", "IDENTITY_UNRESOLVED"),
]


def master(*, second_security=False):
    rows = [
        {"security_id": "SEC:US-XNAS-AAPL", "issuer_id": "ISS:US:320193",
         "issuer_state": "active", "listing_key": "US:XNAS:AAPL",
         "issuer_cik": "0000320193"},
        {"security_id": "SEC:US-XNAS-MSFT", "issuer_id": "ISS:US:789019",
         "issuer_state": "active", "listing_key": "US:XNAS:MSFT",
         "issuer_cik": "0000789019"},
    ]
    if second_security:
        # Synthetic second security: no ticker-equality shortcut is permissible.
        rows.append({"security_id": "SEC:US-XNAS-TESTA", "issuer_id": "ISS:US:320193",
                     "issuer_state": "active", "listing_key": "US:XNAS:TESTA",
                     "issuer_cik": "0000320193"})
    return IssuerMaster.from_records(rows)


def episode(security="SEC:US-XNAS-AAPL", company="ISS:US:320193"):
    return {
        "schema": "prophet.candidate_episode/v1",
        "episode_id": episode_id(security, "epoch_0", ANCHOR, 1),
        "company_id": company, "security_id": security,
        "identity_epoch": "epoch_0", "state": "CANDIDATE",
        "opened_at": CUT, "opened_session": "2026-07-30",
        "structural_anchor": deepcopy(ANCHOR), "expert_events": [],
    }


def consume(row, *, identity=None):
    owner_reads = []
    def discover(company_id):
        owner_reads.append(company_id)
        return None
    result = build_earnings_intelligence_vector(
        episode=row, episode_generation_id=GENERATION, episode_known_at=CUT,
        issuer_master=identity if identity is not None else master(),
        find_event_id=discover,
        read_revisions=lambda _: pytest.fail("No event means no revision read"),
    )
    validate_intelligence_vector(result)
    return result, owner_reads


def assert_withheld(result, state, reason):
    family = result["evidence_families"][0]
    assert family["subject_binding"]["state"] == state
    assert family["subject_binding"]["earnings_company_id"] is None
    assert family["coverage"]["state"] == "UNKNOWN"
    assert family["observations"][0]["value_state"] == "ABSENT"
    assert family["observations"][0]["absence_reasons"] == [reason]
    assert family["source_refs"] == []
    assert not any(result["authority"].values())


def test_control_matching_native_security_and_issuer():
    result, reads = consume(episode())
    assert reads == ["cik:0000320193"]
    assert result["evidence_families"][0]["subject_binding"]["state"] == "RESOLVED"
    assert not any(result["authority"].values())


@pytest.mark.parametrize("security,state,reason", BAD_BINDINGS)
def test_foreign_or_unresolved_listing_never_reads_issuer_evidence(security, state, reason):
    row = episode(security=security)
    before = deepcopy(row)
    result, reads = consume(row)
    assert reads == []
    assert_withheld(result, state, reason)
    assert row == before  # Never silently repair the episode or change entry state.
    assert result["episode_ref"]["episode_id"] == row["episode_id"]


def test_second_security_of_same_canonical_issuer_is_not_a_false_mismatch():
    result, reads = consume(episode("SEC:US-XNAS-TESTA"), identity=master(second_security=True))
    assert reads == ["cik:0000320193"]
    assert result["evidence_families"][0]["subject_binding"]["state"] == "RESOLVED"


def test_changed_epoch_without_matching_episode_identity_is_rejected_before_owner_reads():
    row = episode()
    row["identity_epoch"] = "epoch_1"
    with pytest.raises(IntelligenceVectorContractError, match="episode identity"):
        consume(row)


@pytest.mark.parametrize("security,state,reason", BAD_BINDINGS)
def test_paid_route_keeps_native_roster_and_returns_private_typed_absence(
    monkeypatch, security, state, reason,
):
    row = episode(security)
    rows = (row, episode())
    before = deepcopy(rows)
    snapshot = CandidateEpisodeStoreSnapshot(
        generation_id=GENERATION,
        generation=ValidatedCandidateEpisodeGeneration(
            path=Path("/fixture/not-a-production-generation"),
            episodes=rows, suppressions=(), receipt={},
            events=tuple({"event_type": "OPENED", "episode_id": r["episode_id"],
                          "known_at": CUT} for r in rows),
        ),
    )
    owner_reads = []
    def native_builder(**kwargs):
        return build_earnings_intelligence_vector(
            **kwargs, find_event_id=lambda cid: owner_reads.append(cid),
            read_revisions=lambda _: pytest.fail("Unbound evidence must not be read"),
        )
    monkeypatch.setenv("PROPHET_LAB_DISABLED", "0")
    monkeypatch.setattr(api, "load_candidate_episode_store_snapshot", lambda _: snapshot)
    monkeypatch.setattr(api, "_load_issuer_master", lambda _: master())
    monkeypatch.setattr(api, "build_earnings_intelligence_vector", native_builder)
    app = FastAPI()
    app.include_router(api.router)
    app.dependency_overrides[api.require_site_full_user] = lambda: {"id": "fixture-paid"}
    with TestClient(app) as client:
        response = client.get("/api/prophet/lab/v1/episodes/" + quote(row["episode_id"], safe="") + "/intelligence")
    assert response.status_code == 200
    assert response.headers["cache-control"] == "private, no-store"
    assert response.headers["vary"] == "Authorization"
    assert owner_reads == []
    payload = response.json()
    validate_intelligence_vector(payload)
    assert_withheld(payload, state, reason)
    assert payload["episode_ref"]["episode_id"] == row["episode_id"]
    assert snapshot.generation.episodes == before
    assert len(snapshot.generation.episodes) == 2
