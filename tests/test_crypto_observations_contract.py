"""T22 contract for collectors/_crypto_observations.py.

Fake payloads and a temp store only. Live HTTP is patched to fail the test.
"""
from __future__ import annotations

import requests
import pytest


@pytest.fixture(autouse=True)
def _forbid_live_network(monkeypatch):
    def _boom(*_args, **_kwargs):
        raise AssertionError("live network is forbidden in the observation contract test")

    monkeypatch.setattr(requests, "get", _boom)
    monkeypatch.setattr(requests, "post", _boom)
    monkeypatch.setattr(requests.sessions.Session, "request", _boom)


def _payload(rows):
    return {"code": "0", "data": [
        {"instId": "BTC-USDT-SWAP", "instType": "SWAP", "fundingTime": ts,
         "fundingRate": rate, "realizedRate": realized, "formulaType": "withRate",
         "method": "current_period"}
        for ts, rate, realized in rows
    ]}


def _capture(at, rows):
    from collectors import _crypto_observations as obs
    return obs.build_capture(
        "okx_funding", {"instId": "BTC-USDT-SWAP", "limit": "100"}, _payload(rows), at,
    )


def test_correction_preserves_first_available(tmp_path):
    from collectors import _crypto_observations as obs
    original = _capture("2026-01-01T01:00:00Z", [("1767225600000", "0.0002", "0.00021")])
    correction = _capture("2026-01-01T02:00:00Z", [("1767225600000", "0.0002", "0.00030")])
    assert original["capture_id"] != correction["capture_id"]
    assert original["payload_sha256"] != correction["payload_sha256"]
    assert obs.persist_capture(original, root=tmp_path)["status"] == "stored"
    assert obs.persist_capture(correction, root=tmp_path)["status"] == "stored"
    assert obs.persist_capture(original, root=tmp_path)["status"] == "already_present"

    stored = obs.load_asof("okx_funding", "2026-01-01T04:00:00Z", root=tmp_path)
    assert list(stored["capture_id"]) == [original["capture_id"], correction["capture_id"]]
    first = obs.checked(stored.loc[stored.capture_id == original["capture_id"]].iloc[0].to_dict())
    assert first == obs.checked(original)
    assert first["first_seen"] == first["received_at"] == first["fetched_at"]
    assert first["payload_json"] == original["payload_json"]
    assert first["payload_sha256"] == original["payload_sha256"]

    early = obs.funding_asof(stored, "2026-01-01T01:30:00Z")[0]
    late = obs.funding_asof(stored, "2026-01-01T02:30:00Z")[0]
    assert early["settled_rate"] == 0.00021 and early["capture_id"] == original["capture_id"]
    assert late["settled_rate"] == 0.00030 and late["capture_id"] == correction["capture_id"]
    # The later view does not delete the first receipt.
    assert obs.checked(
        obs.load_asof("okx_funding", "2026-01-01T04:00:00Z", root=tmp_path)
        .loc[lambda f: f.capture_id == original["capture_id"]].iloc[0].to_dict()
    ) == first


def test_missing_interval_is_visible(tmp_path):
    """A hole between two captured settlements stays a hole.

    Field names on the derived event: settlement_at, interval_hours (null),
    status. The raw fundingTime values live in payload_json. The missing
    08:00 slot is not synthesized and interval_hours is not filled in.
    """
    from collectors import _crypto_observations as obs
    missing_ms = "1767254400000"  # 2026-01-01T08:00:00Z, between 00:00 and 16:00
    capture = _capture("2026-01-02T00:00:00Z", [
        ("1767225600000", "0.0001", "0.00011"),
        ("1767283200000", "0.0002", "0.00022"),
    ])
    assert missing_ms not in capture["payload_json"]
    assert "1767225600000" in capture["payload_json"]
    assert "1767283200000" in capture["payload_json"]
    assert obs.persist_capture(capture, root=tmp_path)["status"] == "stored"
    stored = obs.load_asof("okx_funding", "2026-01-02T03:00:00Z", root=tmp_path)
    assert missing_ms not in stored.iloc[0]["payload_json"]
    events = obs.funding_asof(stored, "2026-01-02T03:00:00Z")
    settlements = [event["settlement_at"] for event in events]
    assert settlements == ["2026-01-01T00:00:00+00:00", "2026-01-01T16:00:00+00:00"]
    assert "2026-01-01T08:00:00+00:00" not in settlements
    assert [event["interval_hours"] for event in events] == [None, None]
    assert [event["status"] for event in events] == ["observed", "observed"]
    assert all(event["provider_first_published_at"] is None for event in events)


def test_capture_failure_is_recorded_not_hidden(tmp_path, monkeypatch):
    from types import SimpleNamespace
    from collectors import _crypto_observations as obs

    monkeypatch.setattr(obs.config, "data_dir", lambda: tmp_path)
    adapter = SimpleNamespace(_crypto_capture_active=True, source_capture_status=[])
    response = SimpleNamespace(content=b"{}", url=obs.SOURCES["okx_funding"][1])
    result = obs.record_response(
        adapter, "okx_funding", {"instId": "BTC-USDT-SWAP"}, response,
        _payload([("1767225600000", "0.0002", "0.00021")]),
        "2026-01-01T01:00:00Z", endpoint=obs.SOURCES["okx_funding"][1],
    )
    assert result == {"status": "unavailable", "error_type": "ValueError"}
    assert adapter.source_capture_status == [{
        "status": "unavailable", "error_type": "ValueError", "source_id": "okx_funding",
    }]
    assert obs.fetch_result_status(adapter, {}) == "stale"
    assert not obs.capture_path("okx_funding", root=tmp_path).exists()

    original = _capture("2026-01-01T01:00:00Z", [("1767225600000", "0.0002", "0.00021")])
    assert obs.persist_capture(original, root=tmp_path)["status"] == "stored"

    def _fail(*_args, **_kwargs):
        raise OSError("synthetic atomic failure")

    monkeypatch.setattr(obs.fss, "atomic_write", _fail)
    correction = _capture("2026-01-01T02:00:00Z", [("1767225600000", "0.0002", "0.00030")])
    failed = obs.persist_capture(correction, root=tmp_path)
    # accrue_keep_first swallows the OSError and returns 0. persist_capture
    # then fails its readback proof and records ValueError, not a success.
    assert failed == {"status": "unavailable", "error_type": "ValueError"}
    kept = obs.load_asof("okx_funding", "2026-01-01T04:00:00Z", root=tmp_path)
    assert len(kept) == 1
    assert obs.checked(kept.iloc[0].to_dict()) == obs.checked(original)
    assert obs.fetch_result_status(SimpleNamespace(source_capture_status=[]), {}) is None


def test_unknown_future_outcome_is_not_mature():
    from collectors import _crypto_observations as obs
    import pandas as pd
    early = _capture("2025-12-31T23:00:00Z", [("1767225600000", "0.0002", "0.00021")])
    event = obs.funding_asof(pd.DataFrame([early]), "2026-01-01T03:00:00Z")[0]
    assert event["status"] == "receipt_before_settlement"
    assert event["settled_rate"] is None
    assert event["predicted_rate"] == 0.0002
    assert event["status"] != "observed"

    blank = _capture("2026-01-01T02:00:00Z", [("1767225600000", "0.0002", "")])
    unsettled = obs.funding_asof(pd.DataFrame([blank]), "2026-01-01T03:00:00Z")[0]
    assert unsettled["status"] == "observed"
    assert unsettled["settled_rate"] is None
    assert unsettled["settled_rate"] != unsettled["predicted_rate"]
