"""Real deep-stock fetch must not accept historical prices as tonight's data."""
from datetime import date
import numpy as np
import pandas as pd
import pytest
import yfinance as yf
from collectors import sector_holdings as sh
from lib import config, store

SESSION=date(2026,9,15)
DATES=pd.to_datetime(["2026-09-11","2026-09-14","2026-09-15"])
NAMES=["AAA","BBB","CCC","DDD","EEE","FFF","GGG","HHH","III","JJJ"]


def response(names, current=103.0, volume=700.0):
    return pd.concat({name:pd.DataFrame({"Close":[100.,101.,current],
        "High":[101.,102.,current+1],"Low":[99.,100.,current-1],"Volume":volume},index=DATES)
        for name in names},axis=1)


def adapter(tmp_path,monkeypatch,*,batch_size=10,retries=2):
    monkeypatch.setattr(config,"data_dir",lambda:tmp_path)
    monkeypatch.setattr(sh,"top10_union",lambda:list(NAMES))
    monkeypatch.setattr(sh,"_dead_tickers",lambda:frozenset())
    monkeypatch.setattr(sh.delisted_symbols,"tickers",lambda:frozenset())
    monkeypatch.setattr(sh.nyse_calendar,"expected_last_session",lambda now=None:SESSION)
    monkeypatch.setattr(sh.time,"sleep",lambda _:None)
    a=sh.StockPriceAdapter()
    a.ycfg={"batch_size":batch_size,"retries":retries,"backoff_base_s":0,"upsert_basis_tol":0.001}
    monkeypatch.setattr(a,"_needs_full",lambda ticker:False)
    return a


def test_volume_only_completed_row_is_retried_within_existing_budget(tmp_path,monkeypatch):
    a=adapter(tmp_path,monkeypatch);calls=[]
    def download(names,**kw):
        calls.append(kw)
        return response(names,current=np.nan if len(calls)==1 else 103.,volume=99999 if len(calls)==1 else 700.)
    monkeypatch.setattr(yf,"download",download)
    frames=a.fetch()
    assert len(calls)==2
    assert all(c["auto_adjust"] is True for c in calls)
    assert len(frames)==10
    assert frames["AAA"].loc[str(SESSION),"close"]==103.
    assert frames["AAA"].loc[str(SESSION),"volume"]==700.


@pytest.mark.parametrize("bad",[np.nan,0.,-1.,np.inf,-np.inf])
def test_historical_or_invalid_prices_fail_current_session(tmp_path,monkeypatch,bad):
    a=adapter(tmp_path,monkeypatch);calls=[]
    monkeypatch.setattr(yf,"download",lambda names,**kw:calls.append(names) or response(names,current=bad))
    with pytest.raises(RuntimeError,match="completed session"):
        a.fetch()
    assert len(calls)==2


@pytest.mark.parametrize("dtype", [bool, object, "boolean"])
def test_boolean_completed_close_is_never_a_price(tmp_path, monkeypatch, dtype):
    """A bool scalar is numerically coercible to 1 but is not a market price."""
    a=adapter(tmp_path,monkeypatch);calls=[]
    def download(names,**kw):
        calls.append(names)
        frame=response(names)
        for name in names:
            frame[(name,"Close")]=pd.Series([True,True,True],index=DATES,dtype=dtype)
        return frame
    monkeypatch.setattr(yf,"download",download)
    with pytest.raises(RuntimeError,match="completed session"):
        a.fetch()
    assert len(calls)==a.ycfg["retries"]


@pytest.mark.parametrize("value,expected",[(True,False),(np.bool_(True),False),(False,False),(1,True),(1.0,True),(101.25,True)])
def test_completed_close_scalar_type_distinguishes_boolean_from_numeric_one(value, expected):
    series=pd.Series([value],index=[pd.Timestamp(SESSION)],dtype=object)
    assert sh._has_completed_stock_close(series,SESSION) is expected


def test_seventy_percent_current_coverage_preserves_partial_universe(tmp_path,monkeypatch):
    a=adapter(tmp_path,monkeypatch,batch_size=1);calls=[]
    def download(names,**kw):
        calls.append(names[0])
        return response(names,current=np.nan if names[0] in NAMES[7:] else 103.)
    monkeypatch.setattr(yf,"download",download)
    frames=a.fetch()
    assert set(frames)==set(NAMES[:7]),"stale response frames must not be republished as current"
    assert all(calls.count(t)==2 for t in NAMES[7:])


def test_below_existing_seventy_percent_floor_fails(tmp_path,monkeypatch):
    a=adapter(tmp_path,monkeypatch,batch_size=1)
    monkeypatch.setattr(yf,"download",lambda names,**kw:response(names,current=np.nan if names[0] in NAMES[6:] else 103.))
    with pytest.raises(RuntimeError,match="6/10"):
        a.fetch()


def test_one_calendar_observation_accepts_yesterday_before_close(tmp_path,monkeypatch):
    a=adapter(tmp_path,monkeypatch);observations=[];calls=[]
    monkeypatch.setattr(sh.nyse_calendar,"expected_last_session",lambda now=None:observations.append(now) or date(2026,9,14))
    monkeypatch.setattr(yf,"download",lambda names,**kw:calls.append(names) or response(names,current=np.nan))
    frames=a.fetch()
    assert len(observations)==1 and len(calls)==1
    assert len(frames)==10


def test_future_date_does_not_cover_missing_completed_close(tmp_path,monkeypatch):
    a=adapter(tmp_path,monkeypatch)
    def download(names,**kw):
        d=response(names);d.index=pd.to_datetime(["2026-09-11","2026-09-14","2026-09-16"]);return d
    monkeypatch.setattr(yf,"download",download)
    with pytest.raises(RuntimeError,match="completed session"):
        a.fetch()


def test_duplicate_session_rows_are_not_current_evidence(tmp_path,monkeypatch):
    a=adapter(tmp_path,monkeypatch)
    def download(names,**kw):
        d=response(names);d.index=pd.to_datetime(["2026-09-14","2026-09-15","2026-09-15"]);return d
    monkeypatch.setattr(yf,"download",download)
    with pytest.raises(RuntimeError,match="completed session"):
        a.fetch()


def test_existing_run_adapter_preserves_store_on_exhaustion(tmp_path,monkeypatch):
    from collectors import base
    a=adapter(tmp_path,monkeypatch)
    p=store._path("stocks","AAA")
    pd.DataFrame({"close":[100.,101.],"volume":[1000.,1000.]},index=DATES[:2]).to_parquet(p)
    before=p.read_bytes()
    monkeypatch.setattr(base,"_breaker_state",lambda:{})
    monkeypatch.setattr(yf,"download",lambda names,**kw:response(names,current=np.nan))
    monkeypatch.setattr(store,"upsert",lambda *a,**kw:pytest.fail("failed current response cannot publish"))
    r=base.run_adapter(a)
    assert r.status=="failed" and "completed session" in r.error
    assert p.read_bytes()==before


def test_full_history_repull_still_requires_completed_prices(tmp_path,monkeypatch):
    a=adapter(tmp_path,monkeypatch);calls=[]
    def download(names,**kw):
        calls.append(kw["period"]);return response(names,current=np.nan if len(calls)==1 else 103.)
    monkeypatch.setattr(yf,"download",download)
    assert len(a.fetch(full_history=True))==10
    assert calls==["max","max"]


def test_post_rebase_completed_row_refused_without_changing_rebase_rules(tmp_path,monkeypatch):
    a=adapter(tmp_path,monkeypatch);calls=[]
    monkeypatch.setattr(store,"basis_shifted",lambda *a,**kw:True)
    def download(names,**kw):
        calls.append(kw["period"]);return response(names,current=103. if kw["period"]=="1mo" else np.nan)
    monkeypatch.setattr(yf,"download",download)
    with pytest.raises(RuntimeError,match="completed session"):
        a.fetch()
    assert calls==["1mo","max","max"]


def test_healthy_download_is_not_repeated(tmp_path,monkeypatch):
    a=adapter(tmp_path,monkeypatch);calls=[]
    monkeypatch.setattr(yf,"download",lambda names,**kw:calls.append(kw) or response(names))
    assert len(a.fetch())==10 and len(calls)==1


def test_transport_and_semantic_failure_share_one_budget(tmp_path,monkeypatch):
    a=adapter(tmp_path,monkeypatch,retries=3);calls=[]
    def download(names,**kw):
        calls.append(kw)
        if len(calls)==1:raise ConnectionError("temporary source failure")
        return response(names,current=np.nan if len(calls)==2 else 103.)
    monkeypatch.setattr(yf,"download",download)
    assert len(a.fetch())==10 and len(calls)==3


def test_missing_close_does_not_promote_volume(tmp_path,monkeypatch):
    a=adapter(tmp_path,monkeypatch,batch_size=1)
    def download(names,**kw):
        frame=response(names)
        if names[0] in NAMES[7:]:frame=frame.loc[:,frame.columns.get_level_values(1)=="Volume"]
        return frame
    monkeypatch.setattr(yf,"download",download)
    frames=a.fetch()
    assert set(frames)==set(NAMES[:7])
    assert all("close" in f for f in frames.values())


def test_legacy_direct_download_does_not_create_a_new_calendar_owner(tmp_path,monkeypatch):
    a=adapter(tmp_path,monkeypatch)
    monkeypatch.setattr(sh.nyse_calendar,"expected_last_session",lambda *a:pytest.fail("direct historical helper must not pick a new clock"))
    monkeypatch.setattr(yf,"download",lambda names,**kw:response(names,current=np.nan))
    assert len(a._download(NAMES,"max"))==3


def test_final_boundary_rejects_stale_post_pull_frames(tmp_path,monkeypatch):
    a=adapter(tmp_path,monkeypatch)
    def corrupt_pull(period,tlist,frames,rebase,tol,**kw):
        for ticker in tlist:frames[ticker]=pd.DataFrame({"close":[100.]},index=[pd.Timestamp("2026-09-14")])
    monkeypatch.setattr(a,"_pull",corrupt_pull)
    with pytest.raises(RuntimeError,match="completed session"):
        a.fetch()


# Current-main compatibility: reuse the existing per-market clock owner.
def _mixed_market_case(tmp_path, monkeypatch, market="cn", retries=2):
    from datetime import datetime, timezone
    from lib import market_session
    instant = datetime(2026, 10, 7, 12, tzinfo=timezone.utc)
    real_us = sh.nyse_calendar.expected_last_session
    real_market = market_session.expected_session
    us_session = real_us(instant)
    foreign_session = real_market(market, instant) if market else date(2026, 9, 30)
    foreign = {
        "cn": ["600519.SS", "600000.SS", "601398.SS", "601318.SS", "600036.SS"],
        "hk": ["0700.HK", "9988.HK", "0005.HK", "1299.HK", "3690.HK"],
        "ca": ["RY.TO", "TD.TO", "BMO.TO", "BNS.TO", "CNR.TO"],
        None: ["VOD.L", "SHEL.L", "BP.L", "RIO.L", "HSBA.L"],
    }[market]
    names = ["AAPL", "MSFT", "NVDA", "AMD", "GOOG"] + foreign
    dates = {name: foreign_session if name in foreign else us_session for name in names}
    a = adapter(tmp_path, monkeypatch, batch_size=20, retries=retries)
    monkeypatch.setattr(sh, "top10_union", lambda: list(names))
    observations = {"us": [], "foreign": []}
    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return instant if tz else instant.replace(tzinfo=None)
    monkeypatch.setattr(sh, "datetime", Clock)
    def observe_us(now=None):
        observations["us"].append(now)
        return real_us(instant if now is None else now)
    def observe_foreign(which, now=None):
        observations["foreign"].append((which, now))
        return real_market(which, instant if now is None else now)
    monkeypatch.setattr(sh.nyse_calendar, "expected_last_session", observe_us)
    monkeypatch.setattr(market_session, "expected_session", observe_foreign)
    calls, faults = [], {}
    def download(batch, **kwargs):
        calls.append((list(batch), kwargs["period"]))
        pieces = {}
        for symbol in batch:
            fault = faults.get(symbol, {})
            day = fault.get("day", dates[symbol])
            value = fault.get("value", 103.0)
            frame = pd.DataFrame({"High": [104.0], "Low": [102.0], "Volume": [700.0]},
                                 index=pd.to_datetime([day]))
            frame["Close"] = pd.Series([value], index=frame.index, dtype=object)
            pieces[symbol] = frame
        return pd.concat(pieces, axis=1)
    monkeypatch.setattr(yf, "download", download)
    return a, names, foreign, dates, instant, observations, calls, faults


@pytest.mark.parametrize("market", ["cn", "hk", "ca", None])
def test_mixed_market_completed_closes_use_existing_clocks(tmp_path, monkeypatch, market):
    a, names, foreign, dates, instant, observed, calls, _ = _mixed_market_case(
        tmp_path, monkeypatch, market)
    frames = a.fetch()
    assert set(frames) == set(names)
    assert len(calls) == 1
    assert observed["us"] == [instant]
    assert observed["foreign"] == ([(market, instant)] if market else [])
    for symbol in names:
        assert frames[symbol]["close"].dropna().index.max().date() == dates[symbol]
    if market == "cn":
        assert dates[foreign[0]] == date(2026, 9, 30)
        assert dates["AAPL"] == date(2026, 10, 6)


@pytest.mark.parametrize("fault", ["us_session", "stale", "zero", "boolean", "missing"])
def test_foreign_completed_close_contract_is_not_the_us_date(tmp_path, monkeypatch, fault):
    a, _, foreign, dates, _, _, calls, faults = _mixed_market_case(tmp_path, monkeypatch)
    defect = {
        "us_session": {"day": dates["AAPL"]},
        "stale": {"day": date(2026, 9, 29)},
        "zero": {"value": 0.0},
        "boolean": {"value": True},
        "missing": {"value": np.nan},
    }[fault]
    faults.update({symbol: defect for symbol in foreign})
    with pytest.raises(RuntimeError, match="completed session"):
        a.fetch()
    assert len(calls) == a.ycfg["retries"]


@pytest.mark.parametrize("missing_count", [3, 4])
def test_mixed_retained_markets_keep_whole_universe_coverage_floor(
        tmp_path, monkeypatch, missing_count):
    a, names, foreign, _, _, _, calls, faults = _mixed_market_case(tmp_path, monkeypatch)
    missing = set(foreign[:missing_count])
    faults.update({symbol: {"value": np.nan} for symbol in missing})
    if missing_count == 3:
        assert set(a.fetch()) == set(names) - missing
        assert len(calls) == 1
    else:
        with pytest.raises(RuntimeError, match="6/10"):
            a.fetch()
        assert len(calls) == a.ycfg["retries"]


def test_mixed_market_rebase_keeps_the_same_market_sessions(tmp_path, monkeypatch):
    a, names, _, _, instant, observed, calls, _ = _mixed_market_case(tmp_path, monkeypatch)
    monkeypatch.setattr(store, "basis_shifted", lambda *args, **kwargs: True)
    assert set(a.fetch()) == set(names)
    assert [period for _, period in calls] == ["1mo", "max"]
    assert observed["us"] == [instant]
    assert observed["foreign"] == [("cn", instant)]
