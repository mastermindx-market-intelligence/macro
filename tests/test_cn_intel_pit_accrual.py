"""Mutation tests for China Intelligence prospective PIT accrual (WS:CN-LIMIT-ALPHA).

Display snapshots stay latest-window overwrites. Evidence lives in separate
keep-first first_seen stores. This file proves the contract; it does not score
anything or read outcomes.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json

import pandas as pd
import pytest

from collectors import _first_seen_store as fss
from engine import china_extras as ce


# --------------------------------------------------------------------------- #
# shared helper
# --------------------------------------------------------------------------- #

_HELPER_COLS = ("k", "payload", "first_seen", "fetched_at")


def _helper_row(k, payload, ts):
    return {"k": k, "payload": payload, "first_seen": ts, "fetched_at": ts}


def test_helper_second_write_preserves_day1_and_is_idempotent(tmp_path):
    path = tmp_path / "ev.parquet"
    day1 = "2026-08-14T00:00:00+00:00"
    day2 = "2026-08-15T00:00:00+00:00"
    assert fss.accrue_keep_first(
        path, [_helper_row("A", 1, day1)], columns=_HELPER_COLS, key=["k"]) == 1
    assert fss.accrue_keep_first(
        path, [_helper_row("A", 1, day1)], columns=_HELPER_COLS, key=["k"]) == 0
    assert fss.accrue_keep_first(
        path, [_helper_row("A", 99, day2), _helper_row("B", 2, day2)],
        columns=_HELPER_COLS, key=["k"]) == 1
    got = pd.read_parquet(path)
    assert len(got) == 2
    a = got.loc[got["k"] == "A"].iloc[0]
    assert a["payload"] == 1
    assert a["first_seen"] == day1


def test_helper_unreadable_store_aborts_untouched(tmp_path):
    path = tmp_path / "ev.parquet"
    fss.accrue_keep_first(
        path, [_helper_row("A", 1, "t0")], columns=_HELPER_COLS, key=["k"])
    corrupt = b"PAR1 not a parquet"
    path.write_bytes(corrupt)
    assert fss.accrue_keep_first(
        path, [_helper_row("B", 2, "t1")], columns=_HELPER_COLS, key=["k"]) == 0
    assert path.read_bytes() == corrupt


# --------------------------------------------------------------------------- #
# broker 金股
# --------------------------------------------------------------------------- #

def test_broker_old_month_is_not_month_start_pit(monkeypatch, tmp_path):
    from collectors import tushare_broker as tb
    monkeypatch.setattr(tb, "OUT_HIST", tmp_path / "broker_hist.parquet")
    fetched = "2026-08-15T04:00:00+00:00"  # Asia/Shanghai still 2026-08-15
    pit_ok, known_at = tb.broker_pit_flags("202607", fetched)
    assert pit_ok is False
    assert known_at == ""
    # the forbidden backstamp
    assert known_at != "2026-07-01"
    assert not known_at.startswith("2026-07-01")

    raw = pd.DataFrame([
        {"ticker": "600519.SS", "broker": "中信证券", "name": "贵州茅台"},
        {"ticker": "600519.SS", "broker": "中金公司", "name": "贵州茅台"},
    ])
    rows = tb.hist_rows_from_raw(raw, month="202607", fetched_at=fetched, asof="2026-08-15")
    assert all(r["pit_eligible"] is False and r["known_at"] == "" for r in rows)
    assert tb.accrue_broker_hist(rows) == 2
    # current-month rows collected the same day ARE PIT-eligible
    cur = tb.hist_rows_from_raw(raw, month="202608", fetched_at=fetched, asof="2026-08-15")
    assert all(r["pit_eligible"] is True and r["known_at"] == fetched for r in cur)
    assert tb.accrue_broker_hist(cur) == 2
    got = pd.read_parquet(tb.OUT_HIST)
    july = got[got["month"] == "202607"]
    assert (july["known_at"] == "").all()
    assert not july["known_at"].astype(str).str.startswith("2026-07-01").any()


def test_broker_hist_keep_first_and_snapshot_rolls(monkeypatch, tmp_path):
    from collectors import tushare_broker as tb
    monkeypatch.setattr(tb, "OUT", tmp_path / "broker.parquet")
    monkeypatch.setattr(tb, "OUT_HIST", tmp_path / "broker_hist.parquet")
    monkeypatch.setattr(tb.tc, "enabled", lambda: True)

    day1_raw = pd.DataFrame([
        {"month": "202608", "broker": "中信证券", "ts_code": "600519.SS", "name": "贵州茅台"},
        {"month": "202608", "broker": "中金公司", "ts_code": "600519.SS", "name": "贵州茅台"},
    ])
    day2_raw = pd.DataFrame([
        {"month": "202609", "broker": "中信证券", "ts_code": "600519.SS", "name": "贵州茅台"},
        {"month": "202609", "broker": "中信证券", "ts_code": "000001.SZ", "name": "平安银行"},
    ])
    windows = iter([day1_raw, day2_raw])
    monkeypatch.setattr(tb.tc, "query", lambda *a, **kw: next(windows))

    clock = {"asof": "2026-08-15", "fetched": "2026-08-15T01:00:00+00:00"}
    monkeypatch.setattr(pd.Timestamp, "utcnow", staticmethod(
        lambda: pd.Timestamp(clock["asof"])))
    monkeypatch.setattr(tb, "datetime", type("D", (), {
        "now": staticmethod(lambda tz=None: datetime.fromisoformat(clock["fetched"])),
        "timedelta": __import__("datetime").timedelta,
        "timezone": timezone,
    }))

    assert tb.refresh() == 1
    hist1 = pd.read_parquet(tb.OUT_HIST)
    assert len(hist1) == 2
    assert set(hist1["month"]) == {"202608"}
    snap1 = pd.read_parquet(tb.OUT)
    assert snap1.iloc[0]["month"] == "202608"
    assert snap1.iloc[0]["n_brokers"] == 2
    first_seen_aug = hist1["first_seen"].iloc[0]

    # revised vendor payload for the same August keys + a new September month
    clock["asof"] = "2026-09-02"
    clock["fetched"] = "2026-09-02T01:00:00+00:00"
    # second refresh sees September (latest month with rows)
    assert tb.refresh() == 2
    snap2 = pd.read_parquet(tb.OUT)
    assert set(snap2["month"]) == {"202609"}
    assert len(snap2) == 2
    hist2 = pd.read_parquet(tb.OUT_HIST)
    # August rows survived; September appended; no duplicates
    assert len(hist2) == 4
    aug = hist2[hist2["month"] == "202608"]
    assert len(aug) == 2
    assert (aug["first_seen"] == first_seen_aug).all()
    assert (aug["broker"].isin(["中信证券", "中金公司"])).all()
    # September collected in September is PIT; August collected in August stays PIT
    assert bool(aug["pit_eligible"].all())
    sep = hist2[hist2["month"] == "202609"]
    assert bool(sep["pit_eligible"].all())


def test_broker_refetch_cannot_rewrite_payload_or_first_seen(monkeypatch, tmp_path):
    from collectors import tushare_broker as tb
    monkeypatch.setattr(tb, "OUT_HIST", tmp_path / "broker_hist.parquet")
    t0 = "2026-08-15T01:00:00+00:00"
    t1 = "2026-08-16T01:00:00+00:00"
    raw = pd.DataFrame([{"ticker": "600519.SS", "broker": "中信证券", "name": "贵州茅台"}])
    r0 = tb.hist_rows_from_raw(raw, month="202608", fetched_at=t0, asof="2026-08-15")
    assert tb.accrue_broker_hist(r0) == 1
    raw2 = pd.DataFrame([{"ticker": "600519.SS", "broker": "中信证券", "name": "REVISED"}])
    r1 = tb.hist_rows_from_raw(raw2, month="202608", fetched_at=t1, asof="2026-08-16")
    assert tb.accrue_broker_hist(r1) == 0
    got = pd.read_parquet(tb.OUT_HIST)
    assert len(got) == 1
    assert got.iloc[0]["first_seen"] == t0
    assert got.iloc[0]["name"] == "贵州茅台"


# --------------------------------------------------------------------------- #
# per-name margin
# --------------------------------------------------------------------------- #

def test_margin_hist_preserves_trade_date_and_rolls_snapshot(monkeypatch, tmp_path):
    from collectors import tushare_margin as tm
    monkeypatch.setattr(tm, "OUT", tmp_path / "margin.parquet")
    monkeypatch.setattr(tm, "OUT_HIST", tmp_path / "margin_hist.parquet")
    monkeypatch.setattr(tm.tc, "enabled", lambda: True)

    def _snap(trade_date, bal):
        return pd.DataFrame([
            {"ts_code": "600519.SS", "rzye": bal, "rqye": 1.0, "rzmre": 2.0, "rzrqye": bal + 1,
             "trade_date": trade_date},
        ]), trade_date

    snaps = iter([_snap("20260814", 100.0), _snap("20260817", 999.0)])
    monkeypatch.setattr(tm.tc, "snapshot_by_date", lambda *a, **kw: next(snaps))
    clock = {"asof": "2026-08-14", "fetched": "2026-08-14T08:00:00+00:00"}
    monkeypatch.setattr(pd.Timestamp, "utcnow", staticmethod(
        lambda: pd.Timestamp(clock["asof"])))
    monkeypatch.setattr(tm, "datetime", type("D", (), {
        "now": staticmethod(lambda tz=None: datetime.fromisoformat(clock["fetched"])),
        "timezone": timezone,
    }))

    assert tm.refresh() == 1
    hist1 = pd.read_parquet(tm.OUT_HIST)
    assert hist1.iloc[0]["trade_date"] == "20260814"
    assert hist1.iloc[0]["fin_balance"] == 100.0
    first_seen = hist1.iloc[0]["first_seen"]
    snap1 = pd.read_parquet(tm.OUT)
    assert snap1.iloc[0]["trade_date"] == "20260814"
    assert "fin_pctile" in snap1.columns
    assert "fin_pctile" not in hist1.columns

    clock["asof"] = "2026-08-17"
    clock["fetched"] = "2026-08-17T08:00:00+00:00"
    assert tm.refresh() == 1
    snap2 = pd.read_parquet(tm.OUT)
    assert snap2.iloc[0]["trade_date"] == "20260817"
    assert snap2.iloc[0]["fin_balance"] == 999.0
    hist2 = pd.read_parquet(tm.OUT_HIST)
    assert len(hist2) == 2
    old = hist2[hist2["trade_date"] == "20260814"].iloc[0]
    assert old["fin_balance"] == 100.0
    assert old["first_seen"] == first_seen


def test_margin_refetch_cannot_move_first_seen_or_rewrite(monkeypatch, tmp_path):
    from collectors import tushare_margin as tm
    monkeypatch.setattr(tm, "OUT_HIST", tmp_path / "margin_hist.parquet")
    t0 = "2026-08-14T08:00:00+00:00"
    frame = pd.DataFrame([{"ticker": "600519.SS", "fin_balance": 10.0,
                           "short_balance": 1.0, "fin_buy": 2.0, "total_balance": 11.0}])
    r0 = tm.hist_rows_from_snapshot(frame, trade_date="20260814",
                                    fetched_at=t0, asof="2026-08-14")
    assert tm.accrue_margin_hist(r0) == 1
    frame2 = frame.copy()
    frame2["fin_balance"] = 99.0
    r1 = tm.hist_rows_from_snapshot(frame2, trade_date="20260814",
                                    fetched_at="2026-08-15T08:00:00+00:00",
                                    asof="2026-08-15")
    assert tm.accrue_margin_hist(r1) == 0
    got = pd.read_parquet(tm.OUT_HIST)
    assert len(got) == 1
    assert got.iloc[0]["fin_balance"] == 10.0
    assert got.iloc[0]["first_seen"] == t0


# --------------------------------------------------------------------------- #
# block trades
# --------------------------------------------------------------------------- #

def _block_raw(rows):
    return pd.DataFrame(rows)


def test_block_events_keep_first_and_snapshot_rolls(monkeypatch, tmp_path):
    from collectors import china_block_trades as cbt
    monkeypatch.setattr(cbt, "OUT", tmp_path / "detail.parquet")
    monkeypatch.setattr(cbt, "OUT_HIST", tmp_path / "events.parquet")
    monkeypatch.setattr(cbt, "_trading_dates", lambda n=14: ["20260801", "20260814"])
    monkeypatch.setattr(cbt.time, "sleep", lambda *_: None)

    day1 = _block_raw([{
        "证券代码": "600519", "证券简称": "贵州茅台", "折溢率": -0.05,
        "成交总额": 20000.0, "成交笔数": 2, "交易日期": "2026-08-13",
    }])
    day2 = _block_raw([{
        "证券代码": "600519", "证券简称": "贵州茅台", "折溢率": 0.10,
        "成交总额": 80000.0, "成交笔数": 1, "交易日期": "2026-08-15",
    }])
    windows = iter([day1, day2])
    monkeypatch.setattr(cbt, "_fetch_window", lambda *a, **kw: next(windows))
    clock = {"asof": "2026-08-14"}
    monkeypatch.setattr(pd.Timestamp, "utcnow", staticmethod(
        lambda: pd.Timestamp(clock["asof"])))

    assert cbt.refresh() == 1
    snap1 = pd.read_parquet(cbt.OUT)
    assert snap1.iloc[0]["last_date"] == "2026-08-13"
    hist1 = pd.read_parquet(cbt.OUT_HIST)
    assert hist1.iloc[0]["event_date"] == "2026-08-13"
    assert hist1.iloc[0]["event_date"] != hist1.iloc[0]["first_seen"]
    first_seen = hist1.iloc[0]["first_seen"]
    prem1 = hist1.iloc[0]["premium_pct"]

    clock["asof"] = "2026-08-15"
    assert cbt.refresh() == 1
    snap2 = pd.read_parquet(cbt.OUT)
    assert snap2.iloc[0]["last_date"] == "2026-08-15"
    assert snap2.iloc[0]["avg_premium_pct"] == pytest.approx(10.0)
    hist2 = pd.read_parquet(cbt.OUT_HIST)
    assert len(hist2) == 2
    old = hist2[hist2["event_date"] == "2026-08-13"].iloc[0]
    assert old["first_seen"] == first_seen
    assert old["premium_pct"] == prem1


def test_block_refetch_cannot_rewrite_or_multiply(monkeypatch, tmp_path):
    from collectors import china_block_trades as cbt
    monkeypatch.setattr(cbt, "OUT_HIST", tmp_path / "events.parquet")
    raw = _block_raw([{
        "证券代码": "000001", "证券简称": "平安银行", "折溢率": 0.02,
        "成交总额": 10000.0, "成交笔数": 1, "交易日期": "20260810",
    }])
    t0 = "2026-08-14T00:00:00+00:00"
    r0 = cbt.event_rows_from_raw(raw, fetched_at=t0, asof="2026-08-14")
    assert r0[0]["event_date"] == "2026-08-10"
    assert cbt.accrue_block_events(r0) == 1
    raw2 = raw.copy()
    raw2["折溢率"] = 0.99
    r1 = cbt.event_rows_from_raw(raw2, fetched_at="2026-08-15T00:00:00+00:00",
                                 asof="2026-08-15")
    assert cbt.accrue_block_events(r1) == 0
    assert cbt.accrue_block_events(r0) == 0
    got = pd.read_parquet(cbt.OUT_HIST)
    assert len(got) == 1
    assert got.iloc[0]["first_seen"] == t0
    assert got.iloc[0]["premium_pct"] == pytest.approx(2.0)


def test_block_missing_event_date_is_not_fabricated():
    from collectors import china_block_trades as cbt
    raw = _block_raw([{
        "证券代码": "000001", "证券简称": "平安银行", "折溢率": 0.02,
        "成交总额": 10000.0, "成交笔数": 1,
    }])
    rows = cbt.event_rows_from_raw(raw, fetched_at="t0", asof="2026-08-15")
    assert rows == []


# --------------------------------------------------------------------------- #
# buybacks
# --------------------------------------------------------------------------- #

def test_buyback_publication_date_is_not_known_at(monkeypatch, tmp_path):
    from collectors import china_buyback as cb
    monkeypatch.setattr(cb, "OUT_HIST", tmp_path / "buyback_hist.parquet")
    fetched = "2026-08-15T03:00:00+00:00"
    raw = pd.DataFrame([{
        "股票代码": "600519", "股票简称": "贵州茅台",
        "最新公告日期": "2024-03-01", "起始日期": "2024-01-15",
        "计划回购金额上限": 2.0e9, "已回购金额": 1.0e8,
        "占总股本比例上限": 1.2, "进度": "实施中",
    }])
    rows = cb.hist_rows_from_table(raw, fetched_at=fetched, asof="2026-08-15")
    assert len(rows) == 1
    r = rows[0]
    assert r["event_date"] == "2024-03-01"
    assert r["event_date_kind"] == "vendor_publication"
    assert r["plan_start"] == "2024-01-15"
    assert r["known_at"] == fetched
    assert r["first_seen"] == fetched
    assert r["known_at"] != r["event_date"]
    assert r["known_at"] != r["plan_start"]
    assert cb.accrue_buyback_hist(rows) == 1


def test_buyback_missing_publication_uses_first_seen_clock(monkeypatch, tmp_path):
    from collectors import china_buyback as cb
    monkeypatch.setattr(cb, "OUT_HIST", tmp_path / "buyback_hist.parquet")
    fetched = "2026-08-15T03:00:00+00:00"
    raw = pd.DataFrame([{
        "股票代码": "000001", "股票简称": "平安银行",
        "起始日期": "2023-06-01",
        "计划回购金额": 5.0e8, "已回购金额": 0.0,
        "占总股本比例": 0.4, "进度": "实施中",
    }])
    event_date, kind = cb.vendor_publication_date(list(raw.columns), raw.iloc[0])
    assert event_date == "" and kind == "absent"
    rows = cb.hist_rows_from_table(raw, fetched_at=fetched, asof="2026-08-15")
    r = rows[0]
    assert r["event_date"] == ""
    assert r["event_date_kind"] == "absent"
    assert r["plan_start"] == "2023-06-01"
    assert r["known_at"] == fetched
    assert r["first_seen"] == fetched
    # plan start must not be laundered into the evidence clock
    assert r["known_at"] != r["plan_start"]
    assert cb.accrue_buyback_hist(rows) == 1


def test_buyback_refetch_cannot_rewrite_and_snapshot_rolls(monkeypatch, tmp_path):
    from collectors import china_buyback as cb
    monkeypatch.setattr(cb, "OUT", tmp_path / "buyback.parquet")
    monkeypatch.setattr(cb, "OUT_HIST", tmp_path / "buyback_hist.parquet")

    day1 = pd.DataFrame([{
        "股票代码": "600519", "股票简称": "贵州茅台",
        "最新公告日期": "2026-08-01",
        "计划回购金额上限": 1.0e9, "已回购金额": 1.0e8,
        "占总股本比例上限": 0.5, "进度": "实施中",
    }])
    day2 = pd.DataFrame([{
        "股票代码": "600519", "股票简称": "贵州茅台",
        "最新公告日期": "2026-08-01",
        "计划回购金额上限": 1.0e9, "已回购金额": 9.0e8,
        "占总股本比例上限": 0.5, "进度": "已完成",
    }, {
        "股票代码": "000001", "股票简称": "平安银行",
        "最新公告日期": "2026-08-15",
        "计划回购金额上限": 2.0e8, "已回购金额": 0.0,
        "占总股本比例上限": 0.1, "进度": "实施中",
    }])
    tables = iter([day1, day2])
    monkeypatch.setattr(cb, "fetch_table", lambda: next(tables))
    clock = {"asof": "2026-08-14"}
    monkeypatch.setattr(pd.Timestamp, "utcnow", staticmethod(
        lambda: pd.Timestamp(clock["asof"])))

    assert cb.refresh() == 1
    snap1 = pd.read_parquet(cb.OUT)
    assert list(snap1["ticker"]) == ["600519.SS"]
    assert snap1.iloc[0]["progress"] == "实施中"
    hist1 = pd.read_parquet(cb.OUT_HIST)
    first_seen = hist1.iloc[0]["first_seen"]
    done1 = hist1.iloc[0]["done_amt_yi"]

    clock["asof"] = "2026-08-15"
    assert cb.refresh() == 2
    snap2 = pd.read_parquet(cb.OUT)
    assert set(snap2["ticker"]) == {"600519.SS", "000001.SZ"}
    assert snap2.loc[snap2["ticker"] == "600519.SS", "progress"].item() == "已完成"
    hist2 = pd.read_parquet(cb.OUT_HIST)
    # same (ticker, event_date, plan_key) kept first vintage; new name appended
    assert len(hist2) == 2
    old = hist2[hist2["ticker"] == "600519.SS"].iloc[0]
    assert old["first_seen"] == first_seen
    assert old["done_amt_yi"] == done1
    assert old["progress"] == "实施中"


# --------------------------------------------------------------------------- #
# snapshot consumers stay on the display files
# --------------------------------------------------------------------------- #

def test_display_consumers_still_read_snapshots_not_hist(monkeypatch, tmp_path):
    from engine import china_extras as ce
    monkeypatch.setattr(ce.config, "data_dir", lambda: tmp_path)
    (tmp_path / "china_block_trades").mkdir()
    (tmp_path / "china_buyback").mkdir()
    pd.DataFrame([{
        "ticker": "600519.SS", "name": "贵州茅台", "avg_premium_pct": 3.0,
        "block_amt_yi": 5.0, "n_blocks": 1, "last_date": "2026-08-14",
        "asof": "2026-08-15",
    }]).to_parquet(tmp_path / "china_block_trades" / "detail.parquet", index=False)
    pd.DataFrame([{
        "ticker": "600519.SS", "name": "贵州茅台", "plan_amt_yi": 10.0,
        "done_amt_yi": 2.0, "pct_shares": 0.4, "progress": "实施中",
        "asof": "2026-08-15",
    }]).to_parquet(tmp_path / "china_buyback" / "buyback.parquet", index=False)
    blocks = ce.block_trades()
    buys = ce.buyback()
    assert "600519.SS" in blocks
    assert "600519.SS" in buys
    assert blocks["600519.SS"]["avg_premium_pct"] == 3.0
    assert buys["600519.SS"]["in_progress"] is True


# Stopped-buyback snapshot/consumer qualification belongs with the existing
# collector first-seen/history tests below the retained native contract.
def _buyback_point(monkeypatch, tmp_path):
    monkeypatch.setattr(ce.config, "data_dir", lambda: tmp_path)


def _buyback_write(tmp_path, group, name, df):
    d = tmp_path / group
    d.mkdir(parents=True, exist_ok=True)
    df.to_parquet(d / name, index=False)


# Canonical stopped-program status is not an active confirmer. Keep the raw
# plan, execution amounts and immutable first-seen history available as context.
@pytest.mark.parametrize("progress", ["停止实施", " 停止实施 ", "\t停止实施\n", "\u3000停止实施\u3000"])
@pytest.mark.parametrize("pct,done", [(0.0, 0.0), (1.5, 1.0), (3.0, 10.0)])
def test_stopped_buyback_is_not_active_in_snapshot_readers(monkeypatch, tmp_path, progress, pct, done):
    from engine import china_discovery as cd

    _buyback_point(monkeypatch, tmp_path)
    _buyback_write(tmp_path, "china_buyback", "buyback.parquet", pd.DataFrame([{
        "ticker": "600001.SS", "progress": progress, "pct_shares": pct,
        "done_amt_yi": done, "buyback_score": 0.4,
    }]))
    assert cd.buyback() == {}  # Even a precomputed score cannot override status.
    assert ce.buyback()["600001.SS"] == {
        "progress": progress, "pct_shares": pct, "done_amt_yi": done,
        "in_progress": False, "buyback_score": 0.0,
    }


@pytest.mark.parametrize("progress,active", [
    ("实施中", True), ("完成实施", True), ("已完成", True),
    (" 完成实施 ", True), ("董事会预案", False), ("股东大会通过", False),
    ("股东大会否决", False), ("", False),
])
def test_nonstopped_buyback_reader_contract_is_preserved(monkeypatch, tmp_path, progress, active):
    from engine import china_discovery as cd

    _buyback_point(monkeypatch, tmp_path)
    _buyback_write(tmp_path, "china_buyback", "buyback.parquet", pd.DataFrame([{
        "ticker": "600001.SS", "progress": progress,
        "pct_shares": 3.0, "done_amt_yi": 10.0,
    }]))
    block = ce.buyback()["600001.SS"]
    assert block["progress"] == progress
    assert block["in_progress"] is active
    assert block["buyback_score"] == (0.4 if active else 0.0)
    discovery = cd.buyback()
    assert ("600001.SS" in discovery) is active
    if active:
        assert discovery["600001.SS"]["buyback_score"] == 0.4


def _buyback_discovery_context(monkeypatch, cd):
    # Isolate unrelated membership, ETF-price and display-name dependencies.
    # The collector, Parquet readers, positive legs, cap and composite stay native.
    monkeypatch.setattr(cd, "_bundle_universe", lambda: frozenset())
    monkeypatch.setattr(cd, "_runup_haircut", lambda ticker: 1.0)
    monkeypatch.setattr(cd, "_name_for", lambda ticker: None)


@pytest.mark.parametrize("progress", ["停止实施", " 停止实施 "])
@pytest.mark.parametrize("pct,done", [(0.0, 0.0), (1.5, 1.0), (3.0, 10.0)])
def test_collector_active_to_stopped_removes_only_buyback_evidence(
    monkeypatch, tmp_path, progress, pct, done,
):
    from datetime import date
    from collectors import china_buyback as cb
    from engine import china_discovery as cd

    _buyback_point(monkeypatch, tmp_path)
    _buyback_discovery_context(monkeypatch, cd)
    snapshot = tmp_path / "china_buyback" / "buyback.parquet"
    history = tmp_path / "china_buyback" / "buyback_hist.parquet"
    monkeypatch.setattr(cb, "OUT", snapshot)
    monkeypatch.setattr(cb, "OUT_HIST", history)
    raw = pd.DataFrame([{
        "股票代码": "600001", "股票简称": "Synthetic issuer",
        "进度": "实施中", "计划回购金额上限": 1e9,
        "已回购金额": done * 1e8, "占总股本比例上限": pct,
        "最新公告日期": "2026-11-10",
    }])
    monkeypatch.setattr(cb, "fetch_table", lambda: raw)
    _buyback_write(tmp_path, "china_comment", "detail.parquet", pd.DataFrame([
        {"ticker": "600001.SS", "rank_delta": 10.0},
    ]))
    assert cb.refresh() == 1
    before = cd.build(date(2026, 11, 12))
    assert before["by_ticker"]["600001.SS"]["legs"] == ["attention_rising", "buyback"]
    original_history = pd.read_parquet(history)

    # Make only the collection stamp stale so the real refresh path executes.
    old = pd.read_parquet(snapshot)
    old["asof"] = "2000-01-01"
    old.to_parquet(snapshot, index=False)
    raw.loc[0, "进度"] = progress
    assert cb.refresh() == 1
    assert pd.read_parquet(snapshot).iloc[0]["progress"] == progress
    pd.testing.assert_frame_equal(pd.read_parquet(history), original_history)
    block = ce.buyback()["600001.SS"]
    assert block == {"progress": progress, "pct_shares": pct,
                     "done_amt_yi": done, "in_progress": False, "buyback_score": 0.0}
    after = cd.build(date(2026, 11, 12))
    assert after["n"] == 0 and after["by_ticker"] == {}
    assert after["sources"]["buyback"] == 0
    assert after["sources"]["attention"] == 1
    assert after["is_context_only"] is True
    json.dumps(after, allow_nan=False)

    # Two independent real leading legs still qualify; no buyback reason/score.
    _buyback_write(tmp_path, "china_lhb", "detail.parquet", pd.DataFrame([
        {"ticker": "600001.SS", "inst_net_buy_yi": 1.0, "n_inst_buy": 2,
         "inst_accum_score": 0.5, "asof": "2026-11-12"},
    ]))
    independent = cd.build(date(2026, 11, 12))["by_ticker"]["600001.SS"]
    assert independent["legs"] == ["attention_rising", "inst_accum"]
    assert independent["buyback_score"] is None
    assert "buyback in progress" not in independent["reason"]
    assert independent["disc_score"] == 0.643


def test_stopped_buyback_does_not_remove_other_ticker_context(monkeypatch, tmp_path):
    from engine import china_discovery as cd

    _buyback_point(monkeypatch, tmp_path)
    _buyback_write(tmp_path, "china_buyback", "buyback.parquet", pd.DataFrame([
        {"ticker": "600001.SS", "progress": "停止实施", "pct_shares": 3.0, "done_amt_yi": 10.0},
        {"ticker": "600002.SS", "progress": "实施中", "pct_shares": 3.0, "done_amt_yi": 10.0},
    ]))
    assert list(cd.buyback()) == ["600002.SS"]
    extra = ce.buyback()
    assert extra["600001.SS"]["in_progress"] is False
    assert extra["600002.SS"]["in_progress"] is True
    assert extra["600002.SS"]["buyback_score"] == 0.4

