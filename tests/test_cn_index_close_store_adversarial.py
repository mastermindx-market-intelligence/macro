"""Adversarial cases for the settled index-close store and its reader.

Synthetic frames only. No network and no token. Closes are made-up levels.
"""
from __future__ import annotations

import logging
from datetime import date

import pandas as pd
import pytest

from collectors import tushare_index_daily as tid
from lib import cn_calendar
from lib import cn_pullback_observation as pb
from lib.cn_pullback_observation import licensed_index_closes, snapshot
from lib.pullback_observation import observe
from tests.test_cn_pullback_observation_adapter import (
    EXPECTED, FIXED_NOW, reader, store as close_store,
)


def _vendor(rows):
    return pd.DataFrame(
        [{"ts_code": "000001.SS", "trade_date": d, "close": c} for d, c in rows])


@pytest.fixture
def store(tmp_path, monkeypatch):
    out = tmp_path / "index_daily.parquet"
    monkeypatch.setattr(tid, "OUT", out)
    monkeypatch.setattr(tid.tc, "enabled", lambda: True)
    return out


def _serve(monkeypatch, frame):
    calls = []

    def query(api_name, fields="", **params):
        calls.append((api_name, fields, params))
        return frame

    monkeypatch.setattr(tid.tc, "query", query)
    return calls


def _warning_lines(capsys):
    captured = capsys.readouterr()
    return [ln for ln in captured.out.splitlines() if ln.startswith("::warning")], captured


def test_idempotent_rerun_keeps_identical_bytes_and_emits_no_warning(
        store, monkeypatch, capsys, caplog):
    frame = _vendor([("20261008", 3290.5), ("20261009", 3300.0)])
    _serve(monkeypatch, frame)
    assert tid.refresh(today=date(2026, 10, 11)) == 2
    before = store.read_bytes()
    capsys.readouterr()
    caplog.clear()
    with caplog.at_level(logging.WARNING):
        assert tid.refresh(today=date(2026, 10, 11)) == 0
    assert store.read_bytes() == before
    lines, captured = _warning_lines(capsys)
    assert lines == []
    assert "::warning" not in captured.err
    assert not [r for r in caplog.records if r.levelno >= logging.WARNING]


def test_disagreement_on_one_held_session_rejects_the_whole_fetch(
        store, monkeypatch, capsys):
    _serve(monkeypatch, _vendor([("20261008", 3290.0), ("20261009", 3300.0)]))
    assert tid.refresh(today=date(2026, 10, 9)) == 2
    before = store.read_bytes()
    capsys.readouterr()
    # One held session disagrees; the new session in the same fetch must not land.
    _serve(monkeypatch, _vendor([
        ("20261008", 3290.0),
        ("20261009", 3333.0),
        ("20261012", 3310.0),
    ]))
    assert tid.refresh(today=date(2026, 10, 12)) == 0
    assert store.read_bytes() == before
    lines, _captured = _warning_lines(capsys)
    assert len(lines) == 1
    assert "session 2026-10-09" in lines[0]
    assert "holds 3300.0" in lines[0] and "prints 3333.0" in lines[0]


def test_a_close_inside_four_dp_rounding_is_accepted(store, monkeypatch, capsys):
    # Tolerance is round-to-_CLOSE_DP. Both prints round to 3300.1234.
    assert tid._CLOSE_DP == 4
    assert round(3300.12341, tid._CLOSE_DP) == round(3300.12344, tid._CLOSE_DP) == 3300.1234
    _serve(monkeypatch, _vendor([("20261009", 3300.12341)]))
    assert tid.refresh(today=date(2026, 10, 9)) == 1
    capsys.readouterr()
    _serve(monkeypatch, _vendor([("20261009", 3300.12344), ("20261012", 3310.0)]))
    assert tid.refresh(today=date(2026, 10, 12)) == 1
    lines, _captured = _warning_lines(capsys)
    assert lines == []
    held = pd.read_parquet(store)
    assert held["trade_date"].tolist() == ["2026-10-09", "2026-10-12"]
    assert held["close"].tolist() == [3300.1234, 3310.0]


def test_a_close_one_rounding_unit_past_tolerance_rejects_the_fetch(
        store, monkeypatch, capsys):
    assert round(3300.12346, tid._CLOSE_DP) == 3300.1235
    assert round(3300.12341, tid._CLOSE_DP) == 3300.1234
    _serve(monkeypatch, _vendor([("20261009", 3300.12341)]))
    assert tid.refresh(today=date(2026, 10, 9)) == 1
    before = store.read_bytes()
    capsys.readouterr()
    _serve(monkeypatch, _vendor([("20261009", 3300.12346), ("20261012", 3310.0)]))
    assert tid.refresh(today=date(2026, 10, 12)) == 0
    assert store.read_bytes() == before
    lines, _captured = _warning_lines(capsys)
    assert len(lines) == 1
    assert "holds 3300.1234" in lines[0] and "prints 3300.1235" in lines[0]


def test_new_sessions_are_appended_in_session_order(store, monkeypatch):
    _serve(monkeypatch, _vendor([("20261008", 3290.0), ("20261009", 3300.0)]))
    assert tid.refresh(today=date(2026, 10, 9)) == 2
    # Arrival order is not session order. The held overlap agrees.
    _serve(monkeypatch, _vendor([
        ("20261013", 3320.0),
        ("20261009", 3300.0),
        ("20261012", 3310.0),
    ]))
    assert tid.refresh(today=date(2026, 10, 13)) == 2
    held = pd.read_parquet(store)
    assert held["trade_date"].tolist() == [
        "2026-10-08", "2026-10-09", "2026-10-12", "2026-10-13",
    ]
    assert held["close"].tolist() == [3290.0, 3300.0, 3310.0, 3320.0]


def test_out_of_order_and_duplicate_sessions_in_one_fetch_collapse_sorted(
        store, monkeypatch):
    _serve(monkeypatch, _vendor([
        ("20261013", 3320.0),
        ("20261009", 3300.0),
        ("20261012", 3310.0),
        ("20261009", 3300.0),
        ("20261013", 3320.0),
    ]))
    assert tid.refresh(today=date(2026, 10, 13)) == 3
    held = pd.read_parquet(store)
    assert held["trade_date"].tolist() == ["2026-10-09", "2026-10-12", "2026-10-13"]
    assert held["close"].tolist() == [3300.0, 3310.0, 3320.0]
    assert held["trade_date"].is_unique


def test_a_row_before_the_anchor_is_ignored(store, monkeypatch):
    assert tid.ANCHOR == date(2023, 1, 1)
    _serve(monkeypatch, _vendor([("20221230", 3000.0), ("20230103", 3100.0)]))
    added = tid.refresh(today=date(2023, 1, 4))
    held = pd.read_parquet(store)
    assert added == 1
    assert set(held["trade_date"]) == {"2023-01-03"}


@pytest.mark.parametrize("bad", [float("nan"), 0.0, -1.0])
def test_nan_zero_or_negative_close_rejects_the_fetch(store, monkeypatch, bad):
    _serve(monkeypatch, _vendor([("20261009", 3300.0)]))
    assert tid.refresh(today=date(2026, 10, 9)) == 1
    before = store.read_bytes()
    # A bad close anywhere in the frame drops the whole fetch, including a new session.
    _serve(monkeypatch, _vendor([("20261009", 3300.0), ("20261012", bad)]))
    assert tid.refresh(today=date(2026, 10, 12)) == 0
    assert store.read_bytes() == before


def test_empty_fetch_leaves_the_store_unchanged(store, monkeypatch):
    _serve(monkeypatch, pd.DataFrame(columns=["ts_code", "trade_date", "close"]))
    assert tid.refresh(today=date(2026, 10, 11)) == 0
    assert not store.exists()
    _serve(monkeypatch, None)
    assert tid.refresh(today=date(2026, 10, 11)) == 0
    assert not store.exists()

    _serve(monkeypatch, _vendor([("20261009", 3300.0)]))
    assert tid.refresh(today=date(2026, 10, 11)) == 1
    before = store.read_bytes()
    for frame in (None, pd.DataFrame(columns=["ts_code", "trade_date", "close"])):
        _serve(monkeypatch, frame)
        assert tid.refresh(today=date(2026, 10, 12)) == 0
        assert store.read_bytes() == before


def test_ss_rows_returned_for_an_sh_query_are_stored(store, monkeypatch):
    # The query code is .SH. The client answers with .SS, and that ticker is what is held.
    assert tid.TS_CODE == "000001.SH"
    assert tid.TICKER == "000001.SS"
    frame = pd.DataFrame(
        [{"ts_code": "000001.SS", "trade_date": "20261009", "close": 3300.0}])
    calls = _serve(monkeypatch, frame)
    assert tid.refresh(today=date(2026, 10, 11)) == 1
    assert calls[0][2]["ts_code"] == "000001.SH"
    held = pd.read_parquet(store)
    assert set(held["ticker"]) == {"000001.SS"}
    assert held["trade_date"].tolist() == ["2026-10-09"]


def test_a_missing_middle_session_is_a_gap_and_does_not_crash():
    frame = close_store()
    mid = len(frame) // 2
    missing = date.fromisoformat(frame.iloc[mid]["trade_date"])
    assert cn_calendar.is_session(missing)
    gapped = frame.drop(frame.index[mid]).reset_index(drop=True)
    earlier = date.fromisoformat(gapped.iloc[mid - 1]["trade_date"])
    later = date.fromisoformat(gapped.iloc[mid]["trade_date"])
    assert cn_calendar.sessions_between(earlier, later) > 1
    assert gapped.iloc[-1]["trade_date"] == EXPECTED.isoformat()
    got = licensed_index_closes(EXPECTED, load=lambda: gapped)
    assert got.rows[-1][0] == EXPECTED.isoformat()
    out = snapshot(now=FIXED_NOW, read=reader(gapped), observer=observe)
    assert out["history_gap_count"] == 1
    assert out["available"] is True and out["quality"] == "current"
    assert isinstance(pb.present(out), dict)


def test_reader_refuses_a_store_older_than_its_session_tolerance():
    # Tolerance is 0 sessions: observe() keeps a series current only when the
    # last stored session is the expected session. Anything older is delayed.
    # This fixture is also past the longest legitimate closure.
    last = cn_calendar.session_n_back(EXPECTED, cn_calendar.MAX_LEGIT_CLOSURE_DAYS + 1)
    assert last is not None and last < EXPECTED
    assert cn_calendar.sessions_behind(last, FIXED_NOW) > cn_calendar.MAX_LEGIT_CLOSURE_DAYS
    out = snapshot(now=FIXED_NOW, read=reader(close_store(last=last)), observer=observe)
    assert out["available"] is False
    assert out["quality"] == "delayed"
    assert out["drawdown_pct"] is None
    assert pb.present(out)["phase"] == "unavailable"


def test_a_bar_fetched_before_the_settle_buffer_is_left_for_a_later_run(
        store, monkeypatch, capsys):
    from datetime import datetime, timezone

    # 2026-10-09 is a session; 07:20 UTC is 15:20 CST, before the 17:00 settle.
    early = datetime(2026, 10, 9, 7, 20, tzinfo=timezone.utc)
    _serve(monkeypatch, _vendor([("20261008", 3290.5), ("20261009", 3300.0)]))
    assert tid.refresh(now=early) == 1
    assert list(pd.read_parquet(store)["trade_date"]) == ["2026-10-08"]
    # The settled print differs from the early one; nothing early was kept, so
    # this is a first sighting, not a revision to refuse.
    _serve(monkeypatch, _vendor([("20261008", 3290.5), ("20261009", 3301.25)]))
    capsys.readouterr()
    assert tid.refresh(now=datetime(2026, 10, 9, 9, 5, tzinfo=timezone.utc)) == 1
    assert not _warning_lines(capsys)[0]
    held = pd.read_parquet(store)
    assert list(held["trade_date"]) == ["2026-10-08", "2026-10-09"]
    assert held["close"].iloc[-1] == 3301.25


def test_a_run_with_only_unsettled_bars_keeps_the_store(store, monkeypatch):
    from datetime import datetime, timezone

    _serve(monkeypatch, _vendor([("20261009", 3300.0)]))
    assert tid.refresh(now=datetime(2026, 10, 9, 6, 0, tzinfo=timezone.utc)) == 0
    assert not store.exists()
