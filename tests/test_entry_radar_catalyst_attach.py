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


# --- wave 2b-1: decision-time owner read (catalyst_edgar_live) ---

from engine.entry_radar.catalyst_edgar_live import read_edgar_item_202_live

NOW_W2B1 = datetime(2026, 10, 5, 13, 4, tzinfo=timezone.utc)
OBSERVED = NOW_W2B1 + timedelta(seconds=3)


def _submissions(rows: list[dict]) -> dict:
    keys = (
        "form",
        "filingDate",
        "acceptanceDateTime",
        "accessionNumber",
        "reportDate",
        "items",
    )
    out: dict[str, list] = {k: [] for k in keys}
    for row in rows:
        for k in keys:
            out[k].append(row.get(k, ""))
    return {"filings": {"recent": out}}


def _fetch_stub(mapping: dict):
    calls: list[int] = []

    def fetch(cik: int):
        calls.append(cik)
        val = mapping[cik]
        if isinstance(val, Exception):
            raise val
        return val

    return fetch, calls


def test_W2B1_blocking_filing_usable_at_decision():
    acc = (NOW_W2B1 - timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    subs = _submissions(
        [
            {
                "form": "8-K",
                "filingDate": "2026-10-05",
                "acceptanceDateTime": acc,
                "accessionNumber": "0000000001-26-000001",
                "reportDate": "2026-09-30",
                "items": "2.02,9.01",
            },
        ]
    )
    fetch, calls = _fetch_stub({1: subs})
    got = read_edgar_item_202_live(
        tickers=["ABC"],
        now=NOW_W2B1,
        cik_by_ticker={"ABC": 1},
        fetch=fetch,
        clock=lambda: OBSERVED,
        pace_seconds=0,
    )
    read = got.reads_by_ticker["ABC"]
    assert read.status == "ok"
    assert read.source_asof == OBSERVED
    assert read.observed_at == OBSERVED
    assert read.fresh_until == OBSERVED + timedelta(seconds=DEFAULT_MAX_SOURCE_STALENESS_SECONDS)
    assert read.usable_at(OBSERVED) is True
    assert read.usable_at(OBSERVED + timedelta(seconds=899)) is True
    assert read.usable_at(OBSERVED + timedelta(seconds=901)) is False
    assert read.usable_at(NOW_W2B1) is False
    assert len(got.evidence_by_ticker["ABC"]) == 1
    ev = got.evidence_by_ticker["ABC"][0]
    assert ev.owner == EDGAR_EARNINGS_OWNER
    assert ev.known_at == OBSERVED
    assert got.attempted == got.fetched_ok == 1
    assert got.budget_exhausted == 0
    assert got.rows_scanned == 1
    assert got.last_observed_at == OBSERVED
    assert got.error is None
    assert calls == [1]


def test_W2B1_lookback_excludes_stale_acceptance():
    acc = (NOW_W2B1 - timedelta(days=11)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    subs = _submissions(
        [
            {
                "form": "8-K",
                "filingDate": "2026-09-24",
                "acceptanceDateTime": acc,
                "accessionNumber": "0000000001-26-000001",
                "reportDate": "2026-09-30",
                "items": "2.02,9.01",
            },
        ]
    )
    fetch, _calls = _fetch_stub({1: subs})
    got = read_edgar_item_202_live(
        tickers=["ABC"],
        now=NOW_W2B1,
        cik_by_ticker={"ABC": 1},
        fetch=fetch,
        clock=lambda: OBSERVED,
        pace_seconds=0,
    )
    assert got.reads_by_ticker["ABC"].status == "ok"
    assert "ABC" not in got.evidence_by_ticker
    assert got.rows_scanned == 1
    assert got.refusals == {}


def test_W2B1_cap_and_budget():
    subs = _submissions(
        [
            {
                "form": "8-K",
                "filingDate": "2026-10-05",
                "acceptanceDateTime": "2026-10-05T11:04:00.000Z",
                "accessionNumber": "0000000001-26-000001",
                "reportDate": "2026-09-30",
                "items": "2.02",
            },
        ]
    )
    mapping = {i: subs for i in range(1, 6)}
    fetch, calls = _fetch_stub(mapping)
    got = read_edgar_item_202_live(
        tickers=list("ABCDE"),
        now=NOW_W2B1,
        cik_by_ticker={t: i + 1 for i, t in enumerate("ABCDE")},
        fetch=fetch,
        clock=lambda: OBSERVED,
        pace_seconds=0,
        max_tickers=2,
    )
    assert got.attempted == 2
    assert got.budget_exhausted == 3
    assert calls == [1, 2]
    for t in "CDE":
        r = got.reads_by_ticker[t]
        assert r.status == "unavailable"
        assert r.detail == "live budget exhausted"
        assert r.source_asof == NOW_W2B1

    fetch2, calls2 = _fetch_stub(mapping)
    got2 = read_edgar_item_202_live(
        tickers=list("ABCDE"),
        now=NOW_W2B1,
        cik_by_ticker={t: i + 1 for i, t in enumerate("ABCDE")},
        fetch=fetch2,
        clock=lambda: OBSERVED,
        pace_seconds=0,
        time_budget_seconds=0.0,
    )
    assert got2.attempted == 0
    assert got2.budget_exhausted == 5
    assert calls2 == []


def test_W2B1_fetch_failure_and_404():
    subs = _submissions([])
    fetch, _calls = _fetch_stub({1: RuntimeError("boom"), 2: None})
    got = read_edgar_item_202_live(
        tickers=["A", "B"],
        now=NOW_W2B1,
        cik_by_ticker={"A": 1, "B": 2},
        fetch=fetch,
        clock=lambda: OBSERVED,
        pace_seconds=0,
    )
    ra = got.reads_by_ticker["A"]
    rb = got.reads_by_ticker["B"]
    assert ra.detail.startswith("live fetch failed: RuntimeError")
    assert rb.detail == "submissions 404"
    assert ra.status == rb.status == "unavailable"
    assert got.error is None
    assert got.attempted == 2
    assert got.fetched_ok == 0
    assert got.last_observed_at is None


def test_W2B1_cik_resolution(tmp_path):
    subs = _submissions(
        [
            {
                "form": "8-K",
                "filingDate": "2026-10-05",
                "acceptanceDateTime": "2026-10-05T11:04:00.000Z",
                "accessionNumber": "0000000001-26-000001",
                "reportDate": "2026-09-30",
                "items": "2.02",
            },
        ]
    )
    fetch, calls = _fetch_stub({1: subs})
    got = read_edgar_item_202_live(
        tickers=["A", "B"],
        now=NOW_W2B1,
        cik_by_ticker={"A": 1},
        fetch=fetch,
        clock=lambda: OBSERVED,
        pace_seconds=0,
    )
    assert got.reads_by_ticker["B"].detail == "cik unknown in store"
    assert calls == [1]

    fetch2, calls2 = _fetch_stub({})
    got2 = read_edgar_item_202_live(
        tickers=["A"],
        now=NOW_W2B1,
        cik_by_ticker=None,
        store_path=tmp_path / "missing.parquet",
        fetch=fetch2,
        clock=lambda: OBSERVED,
        pace_seconds=0,
    )
    assert got2.reads_by_ticker["A"].detail.startswith("cik lookup unavailable")
    assert got2.error.startswith("cik lookup unavailable")
    assert calls2 == []

    store = tmp_path / "store.parquet"
    _write_store(store, [_item202_row(ticker="A", cik=7)])
    fetch3, calls3 = _fetch_stub({7: subs})
    got3 = read_edgar_item_202_live(
        tickers=["A"],
        now=NOW_W2B1,
        cik_by_ticker=None,
        store_path=store,
        fetch=fetch3,
        clock=lambda: OBSERVED,
        pace_seconds=0,
    )
    assert calls3 == [7]
    assert got3.reads_by_ticker["A"].status == "ok"


def test_W2B1_refusals_dedup_clock_no_network(tmp_path, monkeypatch):
    acc_ok = (NOW_W2B1 - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    subs = _submissions(
        [
            {
                "form": "8-K",
                "filingDate": "2026-10-05",
                "acceptanceDateTime": "",
                "accessionNumber": "0000000001-26-000002",
                "reportDate": "2026-09-30",
                "items": "2.02",
            },
            {
                "form": "8-K",
                "filingDate": "2026-10-05",
                "acceptanceDateTime": acc_ok,
                "accessionNumber": "0000000001-26-000001",
                "reportDate": "2026-09-30",
                "items": "2.02",
            },
            {
                "form": "8-K",
                "filingDate": "2026-10-05",
                "acceptanceDateTime": acc_ok,
                "accessionNumber": "0000000001-26-000001",
                "reportDate": "2026-09-30",
                "items": "2.02",
            },
            {
                "form": "10-Q",
                "filingDate": "2026-10-05",
                "acceptanceDateTime": acc_ok,
                "accessionNumber": "0000000001-26-000099",
                "reportDate": "2026-09-30",
                "items": "2.02",
            },
        ]
    )
    fetch, _calls = _fetch_stub({1: subs})
    got = read_edgar_item_202_live(
        tickers=["X"],
        now=NOW_W2B1,
        cik_by_ticker={"X": 1},
        fetch=fetch,
        clock=lambda: OBSERVED,
        pace_seconds=0,
    )
    assert sum(got.refusals.values()) == 1
    assert len(got.evidence_by_ticker["X"]) == 1
    assert got.rows_scanned == 3

    with pytest.raises(CatalystContextError):
        read_edgar_item_202_live(
            tickers=["X"],
            now=datetime(2026, 10, 5, 13, 4),
            cik_by_ticker={"X": 1},
            fetch=fetch,
            pace_seconds=0,
        )

    got_clock = read_edgar_item_202_live(
        tickers=["X"],
        now=NOW_W2B1,
        cik_by_ticker={"X": 1},
        fetch=fetch,
        clock=lambda: NOW_W2B1 - timedelta(seconds=1),
        pace_seconds=0,
    )
    assert got_clock.reads_by_ticker["X"].detail == "clock before pass now"

    monkeypatch.setattr(
        "collectors.edgar_earnings_8k._sec_get_json",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("network")),
    )
    acc = (NOW_W2B1 - timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    subs_t14 = _submissions(
        [
            {
                "form": "8-K",
                "filingDate": "2026-10-05",
                "acceptanceDateTime": acc,
                "accessionNumber": "0000000001-26-000001",
                "reportDate": "2026-09-30",
                "items": "2.02,9.01",
            },
        ]
    )
    fetch_t14, calls_t14 = _fetch_stub({1: subs_t14})
    got_t14 = read_edgar_item_202_live(
        tickers=["ABC"],
        now=NOW_W2B1,
        cik_by_ticker={"ABC": 1},
        fetch=fetch_t14,
        clock=lambda: OBSERVED,
        pace_seconds=0,
    )
    assert got_t14.reads_by_ticker["ABC"].status == "ok"
    assert calls_t14 == [1]
