"""Wave 2a attach tests for EDGAR store reader (W2A1+)."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import pytest

from collectors.edgar_earnings_8k import STORE_COLUMNS
from engine.entry_radar.catalyst_adapters import EDGAR_EARNINGS_OWNER
from engine.entry_radar.catalyst_context import (
    CatalystContextError,
    DEFAULT_MAX_SOURCE_STALENESS_SECONDS,
)
from engine.entry_radar.catalyst_edgar_store import (
    DEFAULT_LOOKBACK_DAYS,
    read_edgar_item_202_for_tickers,
)

DECISION = datetime(2026, 10, 2, 13, 4, tzinfo=timezone.utc)
GENERATED = DECISION


def _item202_row(**overrides):
    row = {
        "ticker": "ABC",
        "cik": 1234567,
        "accession": "0001234567-26-000001",
        "form": "8-K",
        "filing_date": "2026-10-02",
        "acceptance_datetime": (DECISION - timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "report_date": "2026-09-30",
        "items": "2.02,9.01",
    }
    row.update(overrides)
    return row


def _write_store(path: Path, rows: list[dict]) -> None:
    pd.DataFrame(rows, columns=STORE_COLUMNS).to_parquet(path, index=False)


def _write_manifest(path: Path, manifest: dict) -> None:
    path.write_text(json.dumps(manifest))


def _paths(tmp_path: Path):
    store = tmp_path / "earnings_8k_dates.parquet"
    manifest = tmp_path / "earnings_8k_dates_manifest.json"
    return store, manifest


def test_W2A1_one_ticker_ok_manifest_and_evidence(tmp_path):
    store, manifest = _paths(tmp_path)
    ts = DECISION - timedelta(minutes=10)
    _write_store(store, [_item202_row()])
    _write_manifest(
        manifest,
        {
            "1234567": {
                "ticker": "ABC",
                "status": "ok",
                "n_filings": 1,
                "n_shards_missing": 0,
                "ts": ts.isoformat().replace("+00:00", "Z"),
            },
        },
    )
    got = read_edgar_item_202_for_tickers(
        tickers=["ABC"],
        decision_at=DECISION,
        generated_at=GENERATED,
        store_path=store,
        manifest_path=manifest,
    )
    read = got.reads_by_ticker["ABC"]
    assert read.status == "ok"
    assert read.usable_at(DECISION) is True
    assert read.source_asof == ts
    assert read.fresh_until == ts + timedelta(seconds=DEFAULT_MAX_SOURCE_STALENESS_SECONDS)
    assert len(got.evidence_by_ticker["ABC"]) == 1
    ev = got.evidence_by_ticker["ABC"][0]
    assert ev.owner == EDGAR_EARNINGS_OWNER
    assert ev.known_at == ts
    assert got.refusals == {}
    assert got.error is None
    assert got.rows_scanned == 1
    assert got.source_asof == ts


def test_W2A1_stale_manifest_ts_still_emits_evidence(tmp_path):
    store, manifest = _paths(tmp_path)
    ts = DECISION - timedelta(hours=12)
    _write_store(
        store,
        [_item202_row(acceptance_datetime=(DECISION - timedelta(hours=14)).strftime("%Y-%m-%dT%H:%M:%SZ"))],
    )
    _write_manifest(
        manifest,
        {
            "1234567": {
                "ticker": "ABC",
                "status": "ok",
                "n_filings": 1,
                "n_shards_missing": 0,
                "ts": ts.isoformat().replace("+00:00", "Z"),
            },
        },
    )
    got = read_edgar_item_202_for_tickers(
        tickers=["ABC"],
        decision_at=DECISION,
        generated_at=GENERATED,
        store_path=store,
        manifest_path=manifest,
    )
    read = got.reads_by_ticker["ABC"]
    assert read.status == "ok"
    assert read.usable_at(DECISION) is False
    assert len(got.evidence_by_ticker["ABC"]) == 1
    assert got.evidence_by_ticker["ABC"][0].known_at == ts


def test_W2A1_refusals_and_manifest_gaps(tmp_path):
    store, manifest = _paths(tmp_path)
    ts = DECISION - timedelta(minutes=10)
    old_accept = (DECISION - timedelta(days=DEFAULT_LOOKBACK_DAYS + 1)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    rows = [
        _item202_row(items="9.01"),
        _item202_row(form="10-Q"),
        _item202_row(acceptance_datetime=""),
        _item202_row(acceptance_datetime=old_accept),
    ]
    _write_store(store, rows)
    _write_manifest(
        manifest,
        {
            "1234567": {
                "ticker": "ABC",
                "status": "ok",
                "n_filings": 4,
                "n_shards_missing": 0,
                "ts": ts.isoformat().replace("+00:00", "Z"),
            },
            "ticker:QQQ": {
                "ticker": "QQQ",
                "status": "skipped_no_cik",
                "ts": ts.isoformat().replace("+00:00", "Z"),
            },
        },
    )
    got = read_edgar_item_202_for_tickers(
        tickers=["ABC", "ZZZ", "QQQ"],
        decision_at=DECISION,
        generated_at=GENERATED,
        store_path=store,
        manifest_path=manifest,
    )
    assert sum(got.refusals.values()) == 3
    assert "ABC" not in got.evidence_by_ticker
    assert got.reads_by_ticker["ZZZ"].status == "unavailable"
    assert got.reads_by_ticker["ZZZ"].detail == "manifest entry missing"
    assert got.reads_by_ticker["QQQ"].status == "unavailable"
    assert got.rows_scanned == 4


def test_W2A1_manifest_clock_and_shard_refusals(tmp_path):
    store, manifest = _paths(tmp_path)
    future_ts = (GENERATED + timedelta(minutes=5)).isoformat().replace("+00:00", "Z")
    _write_store(store, [_item202_row()])
    _write_manifest(
        manifest,
        {
            "1234567": {
                "ticker": "ABC",
                "status": "ok",
                "n_filings": 1,
                "n_shards_missing": 0,
                "ts": future_ts,
            },
        },
    )
    got = read_edgar_item_202_for_tickers(
        tickers=["ABC"],
        decision_at=DECISION,
        generated_at=GENERATED,
        store_path=store,
        manifest_path=manifest,
    )
    assert got.reads_by_ticker["ABC"].status == "unavailable"
    assert got.reads_by_ticker["ABC"].detail == "manifest ts after generated_at"

    ts = DECISION - timedelta(minutes=10)
    _write_manifest(
        manifest,
        {
            "1234567": {
                "ticker": "ABC",
                "status": "ok",
                "n_filings": 1,
                "n_shards_missing": 2,
                "ts": ts.isoformat().replace("+00:00", "Z"),
            },
        },
    )
    got2 = read_edgar_item_202_for_tickers(
        tickers=["ABC"],
        decision_at=DECISION,
        generated_at=GENERATED,
        store_path=store,
        manifest_path=manifest,
    )
    assert got2.reads_by_ticker["ABC"].status == "unavailable"
    assert "n_shards_missing=2" in got2.reads_by_ticker["ABC"].detail


def test_W2A1_missing_files_and_bad_clocks(tmp_path):
    store, manifest = _paths(tmp_path)
    got_store = read_edgar_item_202_for_tickers(
        tickers=["ABC"],
        decision_at=DECISION,
        generated_at=GENERATED,
        store_path=store,
        manifest_path=manifest,
    )
    assert got_store.error.startswith("store missing")
    assert got_store.reads_by_ticker["ABC"].status == "unavailable"

    _write_store(store, [_item202_row()])
    got_manifest = read_edgar_item_202_for_tickers(
        tickers=["ABC"],
        decision_at=DECISION,
        generated_at=GENERATED,
        store_path=store,
        manifest_path=manifest,
    )
    assert got_manifest.error.startswith("manifest missing")
    assert got_manifest.reads_by_ticker["ABC"].status == "unavailable"

    with pytest.raises(CatalystContextError):
        read_edgar_item_202_for_tickers(
            tickers=["ABC"],
            decision_at=datetime(2026, 10, 2, 13, 4),
            generated_at=GENERATED,
            store_path=store,
            manifest_path=manifest,
        )
    with pytest.raises(CatalystContextError):
        read_edgar_item_202_for_tickers(
            tickers=["ABC"],
            decision_at=DECISION,
            generated_at=DECISION - timedelta(seconds=1),
            store_path=store,
            manifest_path=manifest,
        )


def test_W2A1_no_network_with_fetch_monkeypatch(tmp_path, monkeypatch):
    import requests

    def _boom(*_a, **_k):
        raise AssertionError("network")

    monkeypatch.setattr(requests, "get", _boom)
    store, manifest = _paths(tmp_path)
    ts = DECISION - timedelta(minutes=10)
    _write_store(store, [_item202_row()])
    _write_manifest(
        manifest,
        {
            "1234567": {
                "ticker": "ABC",
                "status": "ok",
                "n_filings": 1,
                "n_shards_missing": 0,
                "ts": ts.isoformat().replace("+00:00", "Z"),
            },
        },
    )
    got = read_edgar_item_202_for_tickers(
        tickers=["ABC"],
        decision_at=DECISION,
        generated_at=GENERATED,
        store_path=store,
        manifest_path=manifest,
    )
    assert got.reads_by_ticker["ABC"].status == "ok"
    assert len(got.evidence_by_ticker["ABC"]) == 1


# --- W2A2: live_eval catalyst attach (engine/entry_radar/live_eval.py) ---

import copy

from engine.entry_radar import live_ledger as ll
from engine.entry_radar.catalyst_adapters import adapt_edgar_earnings_item_202
from engine.entry_radar.catalyst_context import (
    CatalystContextError,
    CatalystSourceRead,
    assess_catalyst_context_for_live_episode,
)
from engine.entry_radar.catalyst_edgar_store import (
    EDGAR_STORE_SOURCE_ID,
    EdgarStoreRead,
)
from engine.entry_radar.live_eval import (
    _CATALYST_COVERAGE_PHRASES,
    _attach_catalyst,
    _episode_catalyst_payload,
    _iso,
)
from engine.entry_radar.live_ledger import LiveEpisode, compute_episode_id

NOW = datetime(2026, 10, 2, 14, 35, tzinfo=timezone.utc)

_F2_KEYS = frozenset({
    "radar_episode_schema",
    "radar_episode_id",
    "fresh_until",
    "relevant_until",
    "coverage",
    "context_state",
    "catalyst_schema",
})


# Copied from tests/test_entry_radar_catalyst_context.py::_live_episode
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


def _item202_row_nvda(**overrides):
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


def _edgar_source_read(
    *,
    usable: bool,
    observed_at: datetime = NOW,
) -> CatalystSourceRead:
    if usable:
        source_asof = observed_at - timedelta(minutes=10)
    else:
        source_asof = observed_at - timedelta(hours=12)
    fresh_until = source_asof + timedelta(seconds=DEFAULT_MAX_SOURCE_STALENESS_SECONDS)
    return CatalystSourceRead(
        source_id=EDGAR_STORE_SOURCE_ID,
        status="ok",
        source_asof=source_asof,
        observed_at=observed_at,
        fresh_until=fresh_until,
    )


def _blocking_edgar_evidence(ticker: str = "NVDA"):
    observed = NOW - timedelta(minutes=5)
    return adapt_edgar_earnings_item_202(
        _item202_row_nvda(ticker=ticker),
        owner_observed_at=observed,
    )


def _fake_edgar_read(
    *,
    reads_by_ticker: dict[str, CatalystSourceRead],
    evidence_by_ticker: dict[str, tuple] | None = None,
    error: str | None = None,
) -> EdgarStoreRead:
    return EdgarStoreRead(
        reads_by_ticker=reads_by_ticker,
        evidence_by_ticker=evidence_by_ticker or {},
        refusals={},
        rows_scanned=0,
        error=error,
        source_asof=NOW - timedelta(minutes=10),
    )


def test_W2A2_episode_catalyst_payload_blocking_active():
    episode = _live_episode().to_dict()
    read = _edgar_source_read(usable=True)
    evidence = _blocking_edgar_evidence()
    ctx = assess_catalyst_context_for_live_episode(
        episode=episode,
        decision_at=NOW,
        generated_at=NOW,
        required_sources=(EDGAR_STORE_SOURCE_ID,),
        source_reads=(read,),
        evidence=(evidence,),
    )
    payload = _episode_catalyst_payload(ctx)
    assert set(payload.keys()) == _F2_KEYS
    assert payload["coverage"] == "earnings filing in window"
    assert payload["context_state"] == "blocking_event_observed"
    assert payload["relevant_until"] == _iso(evidence.relevant_until)
    assert payload["fresh_until"] == _iso(read.fresh_until)
    assert payload["radar_episode_id"] == episode["episode_id"]
    assert payload["radar_episode_schema"] == ll.SCHEMA_LIVE_EPISODE


def test_W2A2_attach_catalyst_mixed_usable_and_unusable(monkeypatch):
    import engine.entry_radar.catalyst_edgar_store as ces

    ev_a = _blocking_edgar_evidence(ticker="A")
    read_a = _edgar_source_read(usable=True)
    read_b = _edgar_source_read(usable=False)
    fake = _fake_edgar_read(
        reads_by_ticker={"A": read_a, "B": read_b},
        evidence_by_ticker={"A": (ev_a,)},
    )
    monkeypatch.setattr(ces, "read_edgar_item_202_for_tickers", lambda **_k: fake)

    rows = [
        _live_episode(ticker="A").to_dict(),
        _live_episode(ticker="B").to_dict(),
    ]
    before = copy.deepcopy(rows)
    health: dict = {}
    _attach_catalyst(rows, now=NOW, health=health)
    assert "catalyst" in rows[0]
    assert "catalyst" not in rows[1]
    assert health["catalyst"]["attached_count"] == 1
    assert health["catalyst"]["rows_considered"] == 2
    assert health["catalyst"]["states"] == {
        "blocking_event_observed": 1,
        "coverage_unknown": 1,
    }
    assert health["catalyst"]["source_status"] == "ok"
    assert health["catalyst"]["source_usable"] is True
    after = copy.deepcopy(rows)
    after[0].pop("catalyst", None)
    assert before == after
    assert rows[0]["evidence_refs"] == before[0]["evidence_refs"]


def test_W2A2_attach_catalyst_all_unusable_no_attach(monkeypatch):
    import engine.entry_radar.catalyst_edgar_store as ces

    fake = _fake_edgar_read(
        reads_by_ticker={
            "A": _edgar_source_read(usable=False),
            "B": _edgar_source_read(usable=False),
        },
    )
    monkeypatch.setattr(ces, "read_edgar_item_202_for_tickers", lambda **_k: fake)
    rows = [
        _live_episode(ticker="A").to_dict(),
        _live_episode(ticker="B").to_dict(),
    ]
    health: dict = {}
    _attach_catalyst(rows, now=NOW, health=health)
    assert "catalyst" not in rows[0]
    assert "catalyst" not in rows[1]
    assert health["catalyst"]["attached_count"] == 0
    assert health["catalyst"]["source_usable"] is False
    assert health["catalyst"]["states"] == {"coverage_unknown": 2}


def test_W2A2_attach_catalyst_fail_open_reader_and_store(monkeypatch):
    import engine.entry_radar.catalyst_edgar_store as ces

    def _boom(**_k):
        raise RuntimeError("boom")

    monkeypatch.setattr(ces, "read_edgar_item_202_for_tickers", _boom)
    rows = [_live_episode().to_dict()]
    health: dict = {}
    _attach_catalyst(rows, now=NOW, health=health)
    assert "catalyst" not in rows[0]
    assert health["catalyst"]["error"].startswith("RuntimeError")

    fake = _fake_edgar_read(
        reads_by_ticker={"NVDA": _edgar_source_read(usable=False)},
        error="store missing: /x",
    )
    monkeypatch.setattr(ces, "read_edgar_item_202_for_tickers", lambda **_k: fake)
    health2: dict = {}
    _attach_catalyst(rows, now=NOW, health=health2)
    assert health2["catalyst"]["reader_error"].startswith("store missing")
    assert health2["catalyst"]["attached_count"] == 0


def test_W2A2_attach_catalyst_episode_id_refusal(monkeypatch):
    import engine.entry_radar.catalyst_edgar_store as ces

    ev_a = _blocking_edgar_evidence(ticker="A")
    fake = _fake_edgar_read(
        reads_by_ticker={
            "A": _edgar_source_read(usable=True),
            "B": _edgar_source_read(usable=True),
        },
        evidence_by_ticker={"A": (ev_a,)},
    )
    monkeypatch.setattr(ces, "read_edgar_item_202_for_tickers", lambda **_k: fake)
    good = _live_episode(ticker="B").to_dict()
    bad = _live_episode(ticker="A").to_dict()
    bad["episode_id"] = bad["episode_id"] + "x"
    rows = [bad, good]
    health: dict = {}
    _attach_catalyst(rows, now=NOW, health=health)
    assert "catalyst" not in rows[0]
    assert "catalyst" in rows[1]
    assert health["catalyst"]["episode_errors"] == 1
    assert health["catalyst"]["attached_count"] == 1


def test_W2A2_attach_catalyst_empty_rows_and_none_health(monkeypatch):
    import engine.entry_radar.catalyst_edgar_store as ces

    def _never(**_k):
        raise AssertionError("reader must not run")

    monkeypatch.setattr(ces, "read_edgar_item_202_for_tickers", _never)
    health: dict = {}
    _attach_catalyst(None, now=NOW, health=health)
    assert health["catalyst"]["attached_count"] == 0
    assert health["catalyst"]["rows_considered"] == 0
    _attach_catalyst([], now=NOW, health=health)
    assert health["catalyst"]["rows_considered"] == 0
    _attach_catalyst([], now=NOW, health=None)
