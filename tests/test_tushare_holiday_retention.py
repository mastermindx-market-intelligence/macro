"""Daily Tushare snapshots retain true trade_date and last-good latest tables."""
from datetime import date

import pandas as pd
import pytest

from collectors import tushare_chips, tushare_margin, tushare_moneyflow, tushare_valuation
from lib import market_session

MODULES = [tushare_valuation, tushare_moneyflow, tushare_margin, tushare_chips]


def payload():
    return pd.DataFrame([{
        "ts_code": "600000.SH", "close": 10.0, "total_mv": 10000.0, "circ_mv": 8000.0,
        "pe": 10.0, "pe_ttm": 10.0, "pb": 1.0, "net_amount": 20.0, "net_amount_rate": 1.0,
        "buy_elg_amount": 10.0, "buy_lg_amount": 10.0,
        "rzye": 100.0, "rqye": 50.0, "rzmre": 20.0, "rzrqye": 150.0,
        "winner_rate": 0.5, "weight_avg": 10.0, "cost_50pct": 10.0,
    }])


@pytest.fixture(params=MODULES, ids=lambda module: module.__name__.split(".")[-1])
def module(request, tmp_path, monkeypatch):
    mod = request.param
    for name in ("OUT", "OUT_HIST", "OUT_SECTOR", "OUT_SECTOR_HIST"):
        if hasattr(mod, name):
            monkeypatch.setattr(mod, name, tmp_path / f"{name}.parquet")
    monkeypatch.setattr(mod.tc, "enabled", lambda: True)
    monkeypatch.setattr(market_session, "market_local_date", lambda *args: date(2026, 10, 7))
    old = payload().rename(columns={"ts_code": "ticker"})
    old["trade_date"] = "20260930"
    old["asof"] = "2000-01-01"
    old.to_parquet(mod.OUT, index=False)
    return mod


@pytest.mark.parametrize("kind", ["older", "holiday", "future", "empty-identities", "invalid-values", "provider-date-mismatch"])
def test_unusable_daily_snapshot_does_not_replace_last_good_or_accrue_history(
    module, monkeypatch, kind,
):
    before = module.OUT.read_bytes()
    incoming = payload()
    day = {"older": "20260929", "holiday": "20261007", "future": "20261009"}.get(kind, "20260930")
    if kind == "empty-identities":
        incoming["ts_code"] = None
    elif kind == "invalid-values":
        for col in incoming.columns.difference(["ts_code"]):
            incoming[col] = float("nan")
    elif kind == "provider-date-mismatch":
        incoming["trade_date"] = "20261007"
    monkeypatch.setattr(module.tc, "snapshot_by_date", lambda *args, **kwargs: (incoming.copy(), day))
    assert module.refresh() == 0
    assert module.OUT.read_bytes() == before
    for name in ("OUT_HIST", "OUT_SECTOR_HIST"):
        if hasattr(module, name):
            assert not getattr(module, name).exists()


def test_valid_provider_correction_on_holiday_keeps_real_trade_date(module, monkeypatch):
    incoming = payload()
    incoming["close"] = 11.0
    def response(api, **kwargs):
        return (None, None) if api == "moneyflow_ind_dc" else (incoming.copy(), "20260930")
    monkeypatch.setattr(module.tc, "snapshot_by_date", response)
    assert module.refresh() == 1
    saved = pd.read_parquet(module.OUT)
    assert saved["trade_date"].tolist() == ["20260930"]
    assert saved["ticker"].tolist() == ["600000.SH"]


def test_moneyflow_sector_holiday_rows_cannot_overwrite_last_good(tmp_path, monkeypatch):
    module = tushare_moneyflow
    for name in ("OUT", "OUT_HIST", "OUT_SECTOR", "OUT_SECTOR_HIST"):
        monkeypatch.setattr(module, name, tmp_path / f"{name}.parquet")
    monkeypatch.setattr(module.tc, "enabled", lambda: True)
    monkeypatch.setattr(market_session, "market_local_date", lambda *args: date(2026, 10, 7))
    old = pd.DataFrame({"sector_code": ["BKTEST"], "net_amount": [10.0],
                        "trade_date": ["20260930"], "asof": ["2000-01-01"]})
    old.to_parquet(module.OUT_SECTOR, index=False)
    before = module.OUT_SECTOR.read_bytes()
    def response(api, **kwargs):
        if api == "moneyflow_ind_dc":
            return pd.DataFrame({"ts_code": ["BKTEST"], "net_amount": [999.0]}), "20261007"
        return payload(), "20260930"
    monkeypatch.setattr(module.tc, "snapshot_by_date", response)
    assert module.refresh() == 1
    assert module.OUT_SECTOR.read_bytes() == before
    assert not module.OUT_SECTOR_HIST.exists()



@pytest.mark.parametrize("requested,returned", [
    ("20261007", "20261007"), ("20261009", "20261009"), ("20260929", "20260928"),
])
def test_history_grid_cannot_relabel_provider_dates(tmp_path, monkeypatch, requested, returned):
    from collectors import tushare_history as history

    path = tmp_path / "history.parquet"
    pd.DataFrame({"ticker": ["600000.SH"], "date": ["20260930"], "flow": [10.0]}).to_parquet(path, index=False)
    before = path.read_bytes()
    monkeypatch.setattr(market_session, "market_local_date", lambda *args: date(2026, 10, 7))
    raw = pd.DataFrame({"ts_code": ["600000.SH"], "trade_date": [returned], "net_amount_rate": [99.0]})
    monkeypatch.setattr(history.tc, "query", lambda *args, **kwargs: raw)
    assert history._accrue(path, "moneyflow_dc", "ts_code,trade_date,net_amount_rate",
                           lambda row: row.net_amount_rate, "flow", set(), [requested]) == 0
    assert path.read_bytes() == before


def test_history_valid_older_correction_can_accrue_without_erasing_latest(tmp_path, monkeypatch):
    from collectors import tushare_history as history

    path = tmp_path / "history.parquet"
    pd.DataFrame({"ticker": ["600000.SH"], "date": ["20260930"], "flow": [10.0]}).to_parquet(path, index=False)
    monkeypatch.setattr(market_session, "market_local_date", lambda *args: date(2026, 10, 7))
    raw = pd.DataFrame({"ts_code": ["600000.SH"], "trade_date": ["20260929"], "net_amount_rate": [9.0]})
    monkeypatch.setattr(history.tc, "query", lambda *args, **kwargs: raw)
    assert history._accrue(path, "moneyflow_dc", "ts_code,trade_date,net_amount_rate",
                           lambda row: row.net_amount_rate, "flow", set(), ["20260929"]) == 1
    saved = pd.read_parquet(path).set_index("date")
    assert saved.loc["20260930", "flow"] == 10.0
    assert saved.loc["20260929", "flow"] == 9.0



def test_chips_distribution_cannot_accrue_a_holiday_date(tmp_path, monkeypatch):
    from collectors import tushare_history as history

    path = tmp_path / "chips_distribution.parquet"
    monkeypatch.setattr(market_session, "market_local_date", lambda *args: date(2026, 10, 7))
    monkeypatch.setattr(history, "_close_panel", lambda: None)
    raw = pd.DataFrame({"trade_date": ["20261007", "20261007"],
                        "price": [10.0, 11.0], "percent": [50.0, 50.0]})
    monkeypatch.setattr(history.tc, "query", lambda *args, **kwargs: raw)
    assert history._accrue_chips_distribution(path, {"600000.SS"}, ["20261007"]) == 0
    assert not path.exists()
