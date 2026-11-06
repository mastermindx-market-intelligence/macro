"""Ownership transfer must refuse old providers before attempts or writes."""
from __future__ import annotations

import asyncio
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from lib.yahoo_runtime_profile import (
    COHORT, PROFILE_SCHEMA, SNAPSHOT_SCHEMA, SECTOR_CLOSE_TICKERS,
    VerifiedYahooCohort, YahooRuntimeBindingError, YahooRuntimeOwnershipError,
    YahooRuntimeProfile, YahooRuntimeProfileError, assert_legacy_write_allowed,
    bind_snapshot, parse_profile, partition_legacy_symbols, require_snapshot, runtime_owns,
)


def profile_config(mode="runtime"):
    return {"schema": PROFILE_SCHEMA, "mode": mode, "cohort": COHORT,
            "snapshot_schema": SNAPSHOT_SCHEMA}


def frame(value=100.0):
    return pd.DataFrame(
        {"close": [value, value + 1, value + 2],
         "close_price": [value + 10, value + 11, value + 12],
         "volume": [1000, 1100, 1200]},
        index=pd.date_range("2026-11-02", periods=3),
    )


def cohort(generation="generation-a", value=100.0):
    return VerifiedYahooCohort(
        generation, "2026-11-04",
        {symbol: frame(value) for symbol in SECTOR_CLOSE_TICKERS},
    )


@pytest.fixture
def runtime_config(monkeypatch, tmp_path):
    from lib import config
    cfg = {"yahoo": {"sector_runtime": profile_config()},
           "stock_search": {"extra_tickers": ["SPY", "IWM"]}}
    monkeypatch.setattr(config, "load", lambda: cfg)
    monkeypatch.setattr(config, "data_dir", lambda: tmp_path)
    return cfg


def fail(*args, **kwargs):
    raise AssertionError("A legacy read, provider, retry or write was reached")


def test_committed_profile_is_inactive():
    import yaml
    cfg = yaml.safe_load((Path(__file__).resolve().parents[1] / "config.yml").read_text())
    profile = parse_profile(cfg["yahoo"])
    assert profile.declared and profile.mode == "legacy"


def test_exact_group_and_symbol_scope():
    expected = {
        "XLB", "XLC", "XLE", "XLF", "XLI", "XLK", "XLP", "XLRE",
        "XLU", "XLV", "XLY", "SPY", "QQQ", "IWM",
    }
    assert set(SECTOR_CLOSE_TICKERS) == expected and len(SECTOR_CLOSE_TICKERS) == 14
    for mode in ("legacy", "shadow", "runtime"):
        profile = parse_profile({"sector_runtime": profile_config(mode)})
        assert all(runtime_owns(profile, group="yahoo", symbol=s) == (mode == "runtime")
                   for s in expected)
        assert not runtime_owns(profile, group="stocks", symbol="SPY")
        assert not runtime_owns(profile, group="yahoo", symbol="AAPL")
    assert parse_profile({}) == YahooRuntimeProfile()


@pytest.mark.parametrize("field,value", [
    ("mode", "auto"), ("schema", "v2"), ("cohort", "all"),
    ("snapshot_schema", "latest"), ("mode", None),
])
def test_unknown_profile_cannot_fall_back_to_legacy(field, value):
    raw = profile_config()
    raw[field] = value
    with pytest.raises(YahooRuntimeProfileError):
        parse_profile({"sector_runtime": raw})


@pytest.mark.parametrize("raw", [None, {}, [], {"mode": "runtime"}])
def test_malformed_declared_profile_is_not_absence(raw):
    with pytest.raises(YahooRuntimeProfileError):
        parse_profile({"sector_runtime": raw})


def test_partition_preserves_order_without_making_exclusion_a_failure():
    profile = YahooRuntimeProfile(mode="runtime")
    result = partition_legacy_symbols(profile, ["AAPL", "SPY", "TSLA", "IWM", "AAPL"])
    assert result.allowed == ("AAPL", "TSLA", "AAPL")
    assert result.excluded == ("SPY", "IWM")
    with pytest.raises(YahooRuntimeOwnershipError):
        assert_legacy_write_allowed(profile, group="yahoo", symbol="spy")
    assert_legacy_write_allowed(profile, group="stocks", symbol="SPY")


def test_binding_pins_selection_and_detaches_both_price_bases(monkeypatch):
    from lib import config
    monkeypatch.setattr(config, "load", fail)
    profile = YahooRuntimeProfile(mode="runtime")
    selected = cohort()
    with bind_snapshot(profile, selected):
        selected.frames["SPY"].iloc[0, 0] = 999
        returned = require_snapshot(profile).frame("SPY")
        assert returned.iloc[0]["close"] == 100
        assert returned.iloc[0]["close_price"] == 110
        returned.iloc[0, 0] = 888
        # A new external selection cannot change this calculation's binding.
        selected = cohort("generation-b", 200)
        assert require_snapshot(profile).generation_id == "generation-a"
        assert require_snapshot(profile).frame("SPY").iloc[0, 0] == 100
    with pytest.raises(YahooRuntimeBindingError):
        require_snapshot(profile)


def test_nested_binding_reuses_only_identical_generation_and_always_resets():
    profile = YahooRuntimeProfile(mode="runtime")
    selected = cohort()
    with bind_snapshot(profile, selected):
        with bind_snapshot(profile, cohort()):
            assert require_snapshot(profile).source_session == "2026-11-04"
        for other in (cohort("generation-b"), cohort(value=200)):
            with pytest.raises(YahooRuntimeBindingError, match="CONFLICT"):
                with bind_snapshot(profile, other):
                    pass
        assert require_snapshot(profile).generation_id == "generation-a"
    with pytest.raises(RuntimeError, match="consumer failed"):
        with bind_snapshot(profile, selected):
            raise RuntimeError("consumer failed")
    with pytest.raises(YahooRuntimeBindingError):
        require_snapshot(profile)


def test_async_computations_do_not_share_selection():
    profile = YahooRuntimeProfile(mode="runtime")
    async def run_one(identity, value):
        with bind_snapshot(profile, cohort(identity, value)):
            await asyncio.sleep(0)
            return (require_snapshot(profile).generation_id,
                    require_snapshot(profile).frame("SPY").iloc[0, 0])
    async def run_both():
        return await asyncio.gather(run_one("a", 100), run_one("b", 200))
    assert asyncio.run(run_both()) == [("a", 100), ("b", 200)]


@pytest.mark.parametrize("defect", [
    "missing_member", "missing_basis", "nan_basis", "infinite_basis", "zero_basis",
    "boolean_basis", "string_basis", "wrong_session", "duplicate_date",
    "unsorted", "intraday", "timezone",
])
def test_invalid_snapshot_never_establishes_binding(defect):
    profile = YahooRuntimeProfile(mode="runtime")
    selected = cohort()
    frames = dict(selected.frames)
    if defect == "missing_member":
        del frames["IWM"]
    elif defect == "missing_basis":
        frames["SPY"] = frames["SPY"].drop(columns="close_price")
    elif defect in ("nan_basis", "infinite_basis", "zero_basis"):
        frames["SPY"].loc[frames["SPY"].index[-1], "close_price"] = {
            "nan_basis": np.nan, "infinite_basis": np.inf, "zero_basis": 0,
        }[defect]
    elif defect == "boolean_basis":
        frames["SPY"]["close_price"] = True
    elif defect == "string_basis":
        frames["SPY"]["close_price"] = "100"
    elif defect == "wrong_session":
        frames["SPY"] = frames["SPY"].iloc[:-1]
    elif defect == "duplicate_date":
        frames["SPY"] = pd.concat([frames["SPY"], frames["SPY"].iloc[-1:]])
    elif defect == "unsorted":
        frames["SPY"] = frames["SPY"].iloc[::-1]
    elif defect == "intraday":
        frames["SPY"].index = frames["SPY"].index + pd.Timedelta(hours=10)
    elif defect == "timezone":
        frames["SPY"].index = frames["SPY"].index.tz_localize("UTC")
    candidate = VerifiedYahooCohort("a", "2026-11-04", frames)
    with pytest.raises(YahooRuntimeBindingError):
        with bind_snapshot(profile, candidate):
            pass
    with pytest.raises(YahooRuntimeBindingError):
        require_snapshot(profile)


def test_repull_refuses_before_adapter_construction(runtime_config, monkeypatch):
    from scripts import refresh_regime_if_stale as refresh
    from collectors import base, yahoo
    monkeypatch.setattr(base, "run_adapter", fail)
    monkeypatch.setattr(yahoo, "YahooAdapter", fail)
    with pytest.raises(YahooRuntimeOwnershipError):
        refresh._repull_yahoo()


def test_forced_regime_refresh_cannot_reopen_provider(runtime_config, monkeypatch):
    import sys
    import types
    import engine
    from scripts import refresh_regime_if_stale as refresh
    from collectors import base

    class CanonicalEngineReached(RuntimeError):
        pass

    def stop_before_engine_effects():
        raise CanonicalEngineReached()

    module = types.ModuleType("engine.run")
    module.run = stop_before_engine_effects
    monkeypatch.setitem(sys.modules, "engine.run", module)
    monkeypatch.setattr(engine, "run", module, raising=False)
    monkeypatch.setattr(refresh, "_store_close_date", lambda: "2026-11-03")
    monkeypatch.setattr(refresh, "_market_reference_date", lambda: "2026-11-04")
    monkeypatch.setattr(refresh, "_regime_asof", lambda: "2026-11-04")
    monkeypatch.setattr(base, "run_adapter", fail)
    with pytest.raises(CanonicalEngineReached):
        refresh.refresh(force=True)


@pytest.mark.parametrize("unbound", [False, True])
def test_freshness_heal_stays_stale_and_does_not_claim_attempt(
    runtime_config, monkeypatch, unbound,
):
    from scripts import check_price_store_freshness as gate
    from scripts import refresh_regime_if_stale as refresh
    def source():
        if unbound:
            raise YahooRuntimeBindingError()
        return "2026-11-03"
    monkeypatch.setattr(refresh, "_store_close_date", source)
    monkeypatch.setattr(refresh, "_repull_yahoo", fail)
    monkeypatch.setattr(gate.nyse_calendar, "expected_last_session", lambda now: date(2026, 11, 4))
    markers = []
    monkeypatch.setattr(gate, "_write_marker", markers.append)
    assert gate.run(heal=True) == 3
    assert markers[0]["heal_attempted"] is False
    assert markers[0]["healed"] is False
    assert markers[0]["heal_refused"] == "runtime_owner"
    assert markers[0]["status"] == ("no_store" if unbound else "stale")


def test_force_seed_cannot_reopen_provider_or_stooq(runtime_config, monkeypatch):
    from scripts import seed_extra_tickers as seed
    from lib import stooq
    monkeypatch.setattr(seed.store, "read", fail)
    monkeypatch.setattr(seed.store, "upsert", fail)
    monkeypatch.setattr(seed.yf, "Ticker", fail)
    monkeypatch.setattr(stooq, "stooq_daily", fail)
    monkeypatch.setattr(seed.time, "sleep", fail)
    monkeypatch.setattr(seed.sys, "argv", ["seed", "--force"])
    assert seed.main() == 0


def test_backfill_queue_excludes_before_caps(runtime_config, monkeypatch):
    from scripts import backfill_yahoo_universe as backfill
    monkeypatch.setattr(backfill, "ledger_last_seen", lambda *a: {"SPY": "2026-11-04", "AAPL": "2026-11-04"})
    monkeypatch.setattr(backfill, "hub_universe", lambda *a: ({"SPY", "AAPL"}, {"SPY", "AAPL"}))
    monkeypatch.setattr(backfill, "stored_tickers", lambda *a: set())
    queue, _ = backfill.needed_queue({}, today=date(2026, 11, 4))
    assert queue == [("AAPL", 1)]


def test_refresh_candidates_exclude_before_parquet_read(runtime_config, monkeypatch, tmp_path):
    from scripts import backfill_yahoo_universe as backfill
    folder = tmp_path / "yahoo"
    folder.mkdir()
    for symbol in ("SPY", "IWM", "AAPL"):
        (folder / (symbol + ".parquet")).touch()
    monkeypatch.setattr(backfill, "maintained_stems", lambda: set())
    reads = []
    def read(path):
        reads.append(Path(path).stem)
        assert Path(path).stem == "AAPL"
        return frame()
    monkeypatch.setattr(backfill.pd, "read_parquet", read)
    assert backfill.refresh_candidates({}, data_dir=tmp_path) == (["AAPL"], 1)
    assert reads == ["AAPL"]


def test_both_backfill_phases_filter_before_requests_and_attempts(runtime_config, monkeypatch):
    from scripts import backfill_yahoo_universe as backfill
    from lib import nyse_calendar
    state = {"done": {}, "pending": {"SPY": {"attempts": 2}}, "parked": {}}
    monkeypatch.setattr(backfill, "load_state", lambda: state)
    monkeypatch.setattr(backfill, "needed_queue", lambda *a, **k: ([("SPY", 1), ("AAPL", 1)], {"queue": 2}))
    monkeypatch.setattr(backfill, "refresh_candidates", lambda *a: (["IWM", "TSLA"], 2))
    monkeypatch.setattr(backfill, "save_state", lambda *a, **k: None)
    monkeypatch.setattr(backfill, "_emit", lambda *a: None)
    monkeypatch.setattr(backfill.time, "sleep", lambda *a: None)
    monkeypatch.setattr(nyse_calendar, "expected_last_session", lambda: date(2026, 11, 4))
    calls, writes = [], []
    monkeypatch.setattr(backfill, "download_batch", lambda names, period: calls.append(names) or object())
    monkeypatch.setattr(backfill, "slice_symbol", lambda *a: object())
    monkeypatch.setattr(backfill, "extract_store_frame", lambda *a, **k: frame())
    class Adapter:
        def validate(self, ticker, value):
            return value
    monkeypatch.setattr(backfill, "YahooAdapter", Adapter)
    monkeypatch.setattr(backfill, "schema_violation", lambda value: None)
    monkeypatch.setattr(backfill, "ratio_report", lambda value: {"anomalies": []})
    monkeypatch.setattr(backfill.store, "upsert", lambda group, ticker, value: writes.append(ticker))
    result = backfill.run(cap=1, refresh_all=True, sleep_s=0)
    assert calls == [["AAPL"], ["TSLA"]]
    assert writes == ["AAPL", "TSLA"]
    assert result["attempted"] == 2 and result["refreshable"] == 1
    assert state["pending"]["SPY"] == {"attempts": 2}
    assert "SPY" not in state["done"] and "IWM" not in state["done"]
    assert not state["parked"]


@pytest.mark.parametrize("ticker,safe_name", [("SPY", "SPY"), ("OTHER", "SPY"), ("SPY", "OTHER")])
def test_direct_price_basis_writer_refuses_before_read(runtime_config, monkeypatch, ticker, safe_name):
    from scripts import backfill_price_basis as basis
    monkeypatch.setattr(basis.store, "read", fail)
    monkeypatch.setattr(basis, "_download_max", fail)
    assert basis.backfill_ticker(ticker, safe_name) == {"status": "skipped", "reason": "runtime_owner"}


def test_shallow_scan_and_plan_do_not_read_transferred_histories(runtime_config, monkeypatch, tmp_path):
    from scripts import heal_shallow_caches as heal
    folder = tmp_path / "data" / "yahoo"
    folder.mkdir(parents=True)
    (folder / "SPY.parquet").touch()
    monkeypatch.setattr(heal.pd, "read_parquet", fail)
    assert heal.shallow_targets(tmp_path) == []
    assert heal.plan_heal(tmp_path, "SPY", "data/yahoo") is None


@pytest.mark.parametrize("declared_dir", ["data/yahoo", "data/stocks"])
def test_heal_apply_checks_actual_path_before_temp_write(runtime_config, monkeypatch, tmp_path, declared_dir):
    from scripts import heal_shallow_caches as heal
    monkeypatch.setattr(heal.pd, "concat", fail)
    plan = {"ticker": "SPY", "target_dir": declared_dir,
            "_path": tmp_path / "data" / "yahoo" / "SPY.parquet", "_head": None, "_target": None}
    with pytest.raises(YahooRuntimeOwnershipError):
        heal.apply_heal(plan)


def test_yahoo_donor_requires_binding_and_returns_bound_copy(runtime_config, monkeypatch, tmp_path):
    from scripts import heal_shallow_caches as heal
    monkeypatch.setattr(heal.pd, "read_parquet", fail)
    with pytest.raises(YahooRuntimeBindingError):
        heal._read_donor(tmp_path, "data/yahoo", "SPY")
    profile = YahooRuntimeProfile(mode="runtime")
    with bind_snapshot(profile, cohort()):
        result = heal._read_donor(tmp_path, "data/yahoo", "SPY")
        assert result.iloc[0]["close_price"] == 110
