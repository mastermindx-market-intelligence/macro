"""Source-store, publication and prospective-evidence boundaries, without network."""
from datetime import datetime, timezone
import copy
import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest

from engine.darkflow_index import Policy
from engine.darkflow_observations import record_observation
from engine.darkflow_publish import SourceUnavailable, build_from_store, load_membership, load_panel, publish
from scripts.build_darkflow_index import main

NOW = datetime(2026, 1, 15, 0, 0, tzinfo=timezone.utc)
SMALL = Policy(min_market_names=1, min_sector_names=1, percentile_min=3, history_sessions=8)


def store(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    value.to_parquet(path, index=True)


@pytest.fixture
def data(tmp_path):
    root = tmp_path / "data"
    dates = pd.bdate_range("2026-01-05", periods=8)
    rows = [dict(date=d, ticker=t, short_vol=30+i, short_exempt=.25, total_vol=100.5)
            for i, d in enumerate(dates) for t in ["A", "B"]]
    store(root / "finra_short_volume/panel.parquet", pd.DataFrame(rows))
    membership = pd.DataFrame([dict(ticker=t, src="sp500", start_date=pd.Timestamp("2020-01-01"), end_date=pd.NaT)
                               for t in ["A", "B"]])
    store(root / "breadth/sp1500_pit_membership.parquet", membership)
    ledger = pd.DataFrame([dict(ticker=t, group="sp500", first_seen=dates[0], last_seen=dates[-1], active=True, sector="Tech")
                          for t in ["A", "B"]])
    store(root / "universe/membership.parquet", ledger)
    for ticker, base in [("A", 10), ("B", 100), ("SPY", 500)]:
        store(root / f"massive_stock_day/{ticker}.parquet", pd.DataFrame({"close": [base+i for i in range(8)]}, index=dates))
    return root


def test_real_store_contract_and_matching_generation(data, tmp_path):
    r = build_from_store(data, now=NOW, policy=SMALL)
    assert r["display"]["mode"] == "current"
    assert r["display"]["asof"] == r["asof"] == "2026-01-14"
    assert r["display"]["reading"]["value"] is not None
    assert r["context"]["spy_change_5d_pct"] is not None
    site = tmp_path / "site"
    summary = publish(r, site)
    history = json.loads((site / "darkflow_history.json").read_text())
    assert summary["generation"] == history["generation"] == r["generation"]
    assert "names" not in summary and "history" not in summary
    assert history["names_asof"] == "2026-01-14"
    assert r["history_basis"] == "reconstructed_source_vintage"
    assert r["next_due_at"] == "2026-01-15T23:30:00+00:00"


def test_partial_latest_displays_one_consistent_previous_session(data):
    for ticker in ["A", "B", "SPY"]:
        p = data / f"massive_stock_day/{ticker}.parquet"
        store(p, pd.read_parquet(p).iloc[:-1])
    r = build_from_store(data, now=NOW, policy=SMALL)
    assert r["current"]["value"] is None
    assert r["current"]["date"] == "2026-01-14"
    assert r["display"]["mode"] == "last_complete"
    d = r["display"]
    assert d["asof"] == d["reading"]["date"] == d["context"]["asof"] == r["names_asof"] == "2026-01-13"
    assert d["sectors"][0]["value"] == d["reading"]["value"]
    assert d["reading"]["change_1d_pp"] is not None
    assert r["sources"]["prices"]["latest_available"] == "2026-01-13"


def test_unavailable_raw_price_does_not_use_adjusted_fallback(data):
    for path in (data / "massive_stock_day").glob("*.parquet"):
        store(data / "yahoo" / path.name, pd.read_parquet(path))
        path.unlink()
    with pytest.raises(SourceUnavailable, match="adjusted-price fallback prohibited"):
        build_from_store(data, now=NOW, policy=SMALL)


def test_stale_membership_refuses_publication(data):
    p = data / "universe/membership.parquet"
    ledger = pd.read_parquet(p)
    ledger["last_seen"] = pd.Timestamp("2025-12-01")
    ledger["first_seen"] = pd.Timestamp("2025-11-01")
    store(p, ledger)
    with pytest.raises(SourceUnavailable, match="more than five"):
        build_from_store(data, now=NOW, policy=SMALL)


def test_source_failure_retains_previous_publication(data, tmp_path):
    site = tmp_path / "site"
    publish(build_from_store(data, now=NOW, policy=SMALL), site)
    old = {p.name: p.read_bytes() for p in site.iterdir()}
    (data / "universe/membership.parquet").unlink()
    assert main(["--data-dir", str(data), "--site-dir", str(site), "--now", NOW.isoformat()]) == 2
    assert old == {p.name: p.read_bytes() for p in site.iterdir()}


def test_deep_source_merge_never_mutates_sealed_panel(data):
    p = data / "finra_short_volume/panel.parquet"
    original = p.read_bytes()
    extra = pd.read_parquet(p).copy()
    extra["short_vol"] = 1
    store(data / "finra_short_volume/panel_deep.parquet", extra)
    merged, receipts = load_panel(data)
    assert merged.short_vol.min() >= 30
    assert p.read_bytes() == original
    assert len(receipts) == 2


def test_membership_history_yields_to_observed_ledger(data):
    p = data / "universe/membership.parquet"
    ledger = pd.read_parquet(p)
    ledger.loc[ledger.ticker == "B", "active"] = False
    ledger.loc[ledger.ticker == "B", "last_seen"] = pd.Timestamp("2026-01-06")
    store(p, ledger)
    m, receipt, sectors = load_membership(data)
    from engine.darkflow_index import members_on
    assert members_on(m, pd.Timestamp("2026-01-04")) == {"A", "B"}
    assert members_on(m, pd.Timestamp("2026-01-08")) == {"A"}
    assert receipt["observed_through"] == "2026-01-14"
    assert sectors["B"] == "Tech"


def live_result(data):
    r = build_from_store(data, now=NOW, policy=SMALL)
    r["known_at"] = datetime.now(timezone.utc).isoformat()
    from collectors.finra_short_volume import expected_available_session
    r["asof"] = str(expected_available_session())
    r["current"]["date"] = r["asof"]
    return r


def test_nightly_gate_refuses_before_any_ledger_write(data, monkeypatch):
    monkeypatch.delenv("COLLECT_LANE", raising=False)
    monkeypatch.delenv("US_LANE", raising=False)
    with pytest.raises(PermissionError):
        record_observation(live_result(data), data)
    assert not (data / "darkpool").exists()


def test_first_observation_retained_after_correction(data, monkeypatch):
    monkeypatch.setenv("COLLECT_LANE", "nightly")
    r = live_result(data)
    assert record_observation(r, data)["rows_added"] == 1
    p = data / "darkpool/ledger/index_observations.jsonl"
    before = p.read_bytes()
    correction = copy.deepcopy(r)
    correction["generation"] = "a" * 64
    correction["current"]["value"] += .5
    assert record_observation(correction, data)["state"] == "FIRST_OBSERVATION_RETAINED"
    assert p.read_bytes() == before
    assert len(p.read_text().splitlines()) == 1


def test_replay_cannot_become_live_observation(data, monkeypatch):
    monkeypatch.setenv("COLLECT_LANE", "nightly")
    r = build_from_store(data, now=NOW, policy=SMALL)
    with pytest.raises(ValueError, match="replay clock"):
        record_observation(r, data)
    with pytest.raises(SystemExit):
        main(["--data-dir", str(data), "--now", NOW.isoformat(), "--record-observation"])
    assert not (data / "darkpool").exists()


def test_incomplete_latest_does_not_originate_observation(data, monkeypatch):
    monkeypatch.setenv("COLLECT_LANE", "nightly")
    r = live_result(data)
    r["current"]["value"] = None
    assert record_observation(r, data)["state"] == "NO_COMPLETE_OBSERVATION"
    assert not (data / "darkpool").exists()


def test_corrupt_existing_ledger_is_not_rewritten(data, monkeypatch):
    monkeypatch.setenv("COLLECT_LANE", "nightly")
    path = data / "darkpool/ledger/index_observations.jsonl"
    path.parent.mkdir(parents=True)
    path.write_text("{bad\n")
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    with pytest.raises(json.JSONDecodeError):
        record_observation(live_result(data), data)
    assert hashlib.sha256(path.read_bytes()).hexdigest() == before


def test_failure_between_payload_files_is_detectable_by_generation(data, tmp_path, monkeypatch):
    import engine.darkflow_publish as module
    site = tmp_path / "site"
    r = build_from_store(data, now=NOW, policy=SMALL)
    publish(r, site)
    old = (site / "darkflow_latest.json").read_bytes()
    newer = copy.deepcopy(r)
    newer["generation"] = "b" * 64
    atomic = module._atomic_json
    def fail_summary(path, value):
        if path.name == "darkflow_latest.json":
            raise OSError("simulated interruption")
        atomic(path, value)
    monkeypatch.setattr(module, "_atomic_json", fail_summary)
    with pytest.raises(OSError):
        publish(newer, site)
    assert (site / "darkflow_latest.json").read_bytes() == old
    assert json.loads((site / "darkflow_history.json").read_text())["generation"] != json.loads(old)["generation"]


def test_source_hash_attests_parsed_bytes_during_replacement(data, monkeypatch):
    from io import BytesIO
    from engine.darkflow_publish import _read_snapshot
    path = data / 'massive_stock_day/A.parquet'
    original = path.read_bytes()
    changed = pd.read_parquet(path).copy()
    changed['close'] += 1000
    buffer = BytesIO()
    changed.to_parquet(buffer)
    replacement = buffer.getvalue()
    read = Path.read_bytes
    def race_read(p):
        raw = read(p)
        if p == path:
            p.write_bytes(replacement)
        return raw
    monkeypatch.setattr(Path, 'read_bytes', race_read)
    frame, digest = _read_snapshot(path)
    assert digest == hashlib.sha256(original).hexdigest()
    assert frame.close.max() < 1000
    assert read(path) == replacement


def test_all_missing_current_retains_structured_unavailable_display(data):
    path = data / 'finra_short_volume/panel.parquet'
    empty = pd.read_parquet(path).iloc[:0]
    store(path, empty)
    result = build_from_store(data, now=NOW, policy=SMALL)
    assert result['display']['mode'] == 'unavailable'
    assert result['display']['reading']['value'] is None
    assert result['display']['reading']['date'] == result['asof']


def test_freshness_clock_uses_covered_session_not_build_expectation(data):
    for ticker in ['A', 'B', 'SPY']:
        path = data / f'massive_stock_day/{ticker}.parquet'
        store(path, pd.read_parquet(path).iloc[:-1])
    result = build_from_store(data, now=NOW, policy=SMALL)
    assert result['asof'] == '2026-01-14'
    assert result['observed_asof'] == '2026-01-13'
    from scripts.check_surface_freshness import _ARTIFACTS
    spec = next(item for item in _ARTIFACTS if item.path == 'site/darkflow_latest.json')
    assert spec.as_of_key == 'observed_asof'
    assert spec.clock == 'finra'


def test_existing_desk_render_only_does_not_advance_context_or_ledger(data, tmp_path, monkeypatch):
    import scripts.build_darkpool_desk as desk
    from engine import options_universe
    from lib import config
    root = Path(__file__).resolve().parents[1]
    (tmp_path / 'templates').symlink_to(root / 'templates', target_is_directory=True)
    monkeypatch.setattr(config, 'ROOT', tmp_path)
    monkeypatch.setattr(config, 'load', lambda: {'darkpool': {'enabled': True}, 'storage': {'data_dir': 'data', 'site_dir': 'site'}})
    monkeypatch.setattr(desk, '_load_panel', lambda: pd.read_parquet(data / 'finra_short_volume/panel.parquet'))
    monkeypatch.setattr(desk, 'ATS_DIR', tmp_path / 'missing_ats')
    monkeypatch.setattr(desk, 'NONATS_DIR', tmp_path / 'missing_nonats')
    monkeypatch.setattr(desk, 'YAHOO_DIR', tmp_path / 'missing_prices')
    monkeypatch.setattr(options_universe, 'gex_symbols', lambda: {'A', 'B'})
    assert desk.main(render_only=True) == 0
    html = (tmp_path / 'site/darkpool.html').read_text()
    assert 'id="dark-flow"' in html and 'darkflow.js' in html
    assert not (data / 'darkpool/ledger').exists()
    assert not (data / 'darkpool/context/latest.json').exists()
