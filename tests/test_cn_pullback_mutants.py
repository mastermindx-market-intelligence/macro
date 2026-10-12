"""Kills one-edit mutants the China index store and reader suites left alive.

Synthetic frames only. The vendor client is stubbed; nothing is fetched.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone, tzinfo

import pandas as pd
import pytest

from collectors import tushare_index_daily as tid
from lib import cn_calendar
from lib import cn_pullback_observation as pb
from lib.cn_pullback_observation import SourceRefused, licensed_index_closes, snapshot
from lib.pullback_observation import observe
from tests.test_cn_pullback_observation_adapter import (
    EXPECTED, FIXED_NOW, reader, store as close_store,
)


AFTER_SETTLE = datetime(2026, 10, 14, 12, tzinfo=timezone.utc)


def _vendor(rows, ts_code="000001.SS"):
    return pd.DataFrame(
        [{"ts_code": ts_code, "trade_date": d, "close": c} for d, c in rows])


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


def _warnings(capsys):
    out = capsys.readouterr().out
    return [ln for ln in out.splitlines() if ln.startswith("::warning")]


def _held_row(day, close, first_seen="kept", **extra):
    row = {"ticker": "000001.SS", "trade_date": day, "close": close,
           "first_seen": first_seen}
    row.update(extra)
    return row


class _NoFloat:
    """float() raises TypeError, which normalize's narrow handler must catch."""


class _Boom:
    def __float__(self):
        raise RuntimeError("price-decode")


class _NoOffset(tzinfo):
    def utcoffset(self, dt):
        return None

    def dst(self, dt):
        return None

    def tzname(self, dt):
        return "NONE"


def test_positive_close_below_one_point_is_stored(store, monkeypatch):
    _serve(monkeypatch, _vendor([("20261009", 0.5)]))
    assert tid.refresh(today=date(2026, 10, 11)) == 1
    assert pd.read_parquet(store)["close"].tolist() == [0.5]


def test_mixed_vendor_codes_reject_the_fetch(store, monkeypatch):
    # Distinct sessions, so a conflicting duplicate close cannot be what refuses them.
    frame = pd.DataFrame([
        {"ts_code": "000001.SS", "trade_date": "20261009", "close": 3300.0},
        {"ts_code": "399001.SZ", "trade_date": "20261012", "close": 3310.0},
    ])
    _serve(monkeypatch, frame)
    assert tid.refresh(today=date(2026, 10, 12)) == 0
    assert not store.exists()


def test_non_numeric_close_rejects_the_fetch(store, monkeypatch):
    frame = pd.DataFrame({
        "ts_code": pd.Series(["000001.SS"], dtype=object),
        "trade_date": pd.Series(["20261009"], dtype=object),
        "close": pd.Series([_NoFloat()], dtype=object),
    })
    _serve(monkeypatch, frame)
    assert tid.refresh(today=date(2026, 10, 11)) == 0
    assert not store.exists()


def test_unexpected_close_failure_propagates(store, monkeypatch):
    frame = pd.DataFrame({
        "ts_code": pd.Series(["000001.SS"], dtype=object),
        "trade_date": pd.Series(["20261009"], dtype=object),
        "close": pd.Series([_Boom()], dtype=object),
    })
    _serve(monkeypatch, frame)
    with pytest.raises(RuntimeError, match="price-decode"):
        tid.refresh(today=date(2026, 10, 11))


def test_refusal_names_the_first_printed_disagreement(store, monkeypatch, capsys):
    _serve(monkeypatch, _vendor([("20261008", 3290.0), ("20261009", 3300.0)]))
    assert tid.refresh(today=date(2026, 10, 9)) == 2
    capsys.readouterr()
    # Printed order, not session order: 10-09 is the first row that disagrees.
    _serve(monkeypatch, _vendor([
        ("20261009", 3333.0),
        ("20261008", 1111.0),
        ("20261012", 3310.0),
    ]))
    assert tid.refresh(today=date(2026, 10, 12)) == 0
    lines = _warnings(capsys)
    assert len(lines) == 1
    assert "session 2026-10-09" in lines[0]
    assert "holds 3300.0" in lines[0] and "prints 3333.0" in lines[0]
    assert "2026-10-08" not in lines[0]


def test_duplicate_held_sessions_compare_the_last_close(store, monkeypatch, capsys):
    pd.DataFrame([
        _held_row("2026-10-09", 3300.0, "first"),
        _held_row("2026-10-09", 3310.0, "last"),
    ]).to_parquet(store, index=False)
    _serve(monkeypatch, _vendor([("20261009", 3310.0), ("20261012", 3320.0)]))
    assert tid.refresh(today=date(2026, 10, 12)) == 1
    assert _warnings(capsys) == []
    assert "2026-10-12" in set(pd.read_parquet(store)["trade_date"])


def test_disagreement_rounds_the_held_close_to_four_dp(store, monkeypatch, capsys):
    pd.DataFrame([_held_row("2026-10-09", 3300.12341)]).to_parquet(store, index=False)
    _serve(monkeypatch, _vendor([("20261009", 3300.12344), ("20261012", 3310.0)]))
    assert tid.refresh(today=date(2026, 10, 12)) == 1
    assert _warnings(capsys) == []
    held = pd.read_parquet(store).set_index("trade_date")["close"]
    assert held.loc["2026-10-09"] == 3300.12341
    assert held.loc["2026-10-12"] == 3310.0


def test_session_dated_on_the_anchor_is_stored(store, monkeypatch):
    assert tid.ANCHOR == date(2023, 1, 1)
    _serve(monkeypatch, _vendor([("20230101", 3000.0), ("20230103", 3100.0)]))
    assert tid.refresh(now=AFTER_SETTLE) == 2
    assert set(pd.read_parquet(store)["trade_date"]) == {"2023-01-01", "2023-01-03"}


def test_overlap_start_is_clamped_to_the_anchor(store, monkeypatch):
    pd.DataFrame([_held_row("2023-01-05", 3100.0)]).to_parquet(store, index=False)
    calls = _serve(monkeypatch, _vendor([("20230105", 3100.0), ("20230106", 3110.0)]))
    assert tid.refresh(now=AFTER_SETTLE) == 1
    # 2023-01-05 minus the 30-day overlap is 2022-12-06, before the anchor.
    assert calls[0][2]["start_date"] == "20230101"


def test_unsettled_only_fetch_warns_no_admissible_closes(store, monkeypatch, caplog):
    # 06:00 UTC is 14:00 Asia/Shanghai, before the 17:00 settle.
    early = datetime(2026, 10, 9, 6, 0, tzinfo=timezone.utc)
    _serve(monkeypatch, _vendor([("20261009", 3300.0)]))
    with caplog.at_level(logging.WARNING):
        assert tid.refresh(now=early) == 0
    assert not store.exists()
    assert "no admissible" in caplog.text
    assert "nothing admissible to merge" not in caplog.text


def test_a_missing_store_is_not_an_unreadable_store(store, monkeypatch, caplog):
    _serve(monkeypatch, _vendor([("20261009", 3300.0)]))
    with caplog.at_level(logging.WARNING):
        assert tid.refresh(today=date(2026, 10, 11)) == 1
    assert "unreadable" not in caplog.text
    assert pd.read_parquet(store)["trade_date"].tolist() == ["2026-10-09"]


def test_corrupt_store_is_refetched_from_the_anchor(store, monkeypatch):
    store.write_bytes(b"not a parquet file")
    calls = _serve(monkeypatch, _vendor([("20261009", 3300.0)]))
    assert tid.refresh(today=date(2026, 10, 11)) == 1
    assert calls[0][2]["start_date"] == "20230101"
    assert pd.read_parquet(store)["close"].tolist() == [3300.0]


def test_an_extra_held_column_keeps_the_store_and_its_first_seen(store, monkeypatch):
    pd.DataFrame([_held_row("2026-10-09", 3300.0, note="keep")]).to_parquet(store, index=False)
    calls = _serve(monkeypatch, _vendor([("20261009", 3300.0), ("20261012", 3310.0)]))
    assert tid.refresh(today=date(2026, 10, 12)) == 1
    assert calls[0][2]["start_date"] == "20260909"
    held = pd.read_parquet(store).set_index("trade_date")
    assert held.loc["2026-10-09", "first_seen"] == "kept"


def test_an_extra_vendor_column_is_admissible(store, monkeypatch):
    frame = _vendor([("20261009", 3300.0)]).assign(volume=[1])
    _serve(monkeypatch, frame)
    assert tid.refresh(today=date(2026, 10, 11)) == 1
    assert pd.read_parquet(store)["close"].tolist() == [3300.0]


def test_a_disagreement_stops_before_the_empty_merge_warning(
        store, monkeypatch, capsys, caplog):
    _serve(monkeypatch, _vendor([("20261009", 3300.0)]))
    assert tid.refresh(today=date(2026, 10, 9)) == 1
    before = store.read_bytes()
    capsys.readouterr()
    caplog.clear()
    _serve(monkeypatch, _vendor([("20261009", 3333.0), ("20261012", 3310.0)]))
    with caplog.at_level(logging.WARNING):
        assert tid.refresh(today=date(2026, 10, 12)) == 0
    assert store.read_bytes() == before
    assert len(_warnings(capsys)) == 1
    assert "nothing admissible to merge" not in caplog.text


def test_first_seen_is_an_aware_utc_timestamp(store, monkeypatch):
    _serve(monkeypatch, _vendor([("20261009", 3300.0)]))
    assert tid.refresh(today=date(2026, 10, 11)) == 1
    seen = pd.read_parquet(store)["first_seen"].iloc[0]
    parsed = datetime.fromisoformat(seen)
    assert parsed.utcoffset() == timedelta(0)


def test_queried_sh_code_in_the_response_is_not_admitted(store, monkeypatch):
    calls = _serve(monkeypatch, _vendor([("20261009", 3300.0)], ts_code="000001.SH"))
    assert tid.refresh(today=date(2026, 10, 11)) == 0
    assert calls[0][2]["ts_code"] == "000001.SH"
    assert not store.exists()


def test_held_columns_outside_the_store_schema_are_not_written(store, monkeypatch):
    pd.DataFrame([_held_row("2026-10-09", 3300.0, note="drop-me")]).to_parquet(
        store, index=False)
    _serve(monkeypatch, _vendor([("20261009", 3300.0), ("20261012", 3310.0)]))
    assert tid.refresh(today=date(2026, 10, 12)) == 1
    assert list(pd.read_parquet(store).columns) == list(tid.COLUMNS)


def test_merge_refuses_the_whole_frame_when_one_session_disagrees():
    held = pd.DataFrame([_held_row("2026-10-09", 3300.0)])
    fetched = tid.normalize(_vendor([("20261009", 3333.0), ("20261012", 3310.0)]))
    assert fetched is not None
    assert tid.merge(held, fetched, first_seen="2026-10-12T00:00:00+00:00") is None


def test_overlap_follows_the_max_session_not_file_order(store, monkeypatch):
    pd.DataFrame([
        _held_row("2026-10-12", 3320.0),
        _held_row("2026-10-08", 3290.0),
    ]).to_parquet(store, index=False)
    calls = _serve(monkeypatch, _vendor([
        ("20261012", 3320.0),
        ("20261008", 3290.0),
        ("20261013", 3330.0),
    ]))
    assert tid.refresh(today=date(2026, 10, 13)) == 1
    # max session is 2026-10-12; the last file row is 2026-10-08 (minus 30 days = 09-08).
    assert calls[0][2]["start_date"] == "20260912"


def test_reader_refuses_mixed_tickers():
    frame = close_store()
    foreign = frame.iloc[[0]].copy()
    foreign["ticker"] = "399001.SZ"
    mixed = pd.concat([frame, foreign], ignore_index=True)
    with pytest.raises(SourceRefused) as exc:
        licensed_index_closes(EXPECTED, load=lambda: mixed)
    assert exc.value.quality == "source_unavailable"


def test_reader_accepts_required_columns_without_first_seen():
    frame = close_store().drop(columns=["first_seen"])
    got = licensed_index_closes(EXPECTED, load=lambda: frame)
    assert got.rows[-1] == ("2026-10-09", 3230.0)


def test_snapshot_rejects_a_zone_with_no_offset():
    now = datetime(2026, 10, 9, 17, 30, tzinfo=_NoOffset())
    with pytest.raises(ValueError, match="aware datetime"):
        snapshot(now=now, read=reader(close_store()), observer=observe)


def test_snapshot_rejects_a_non_datetime_clock():
    with pytest.raises(ValueError, match="aware datetime"):
        snapshot(now=date(2026, 10, 9), read=reader(close_store()), observer=observe)


def test_produced_at_is_normalized_to_utc():
    now = datetime(2026, 10, 9, 17, 30, tzinfo=cn_calendar.CST)
    out = snapshot(now=now, read=reader(close_store()), observer=observe)
    assert out["produced_at"] == "2026-10-09T09:30:00+00:00"


def test_missing_successor_session_raises(monkeypatch):
    monkeypatch.setattr(pb, "_next_session", lambda day: None)
    with pytest.raises(ValueError, match="successor settlement session"):
        snapshot(now=FIXED_NOW, read=reader(close_store()), observer=observe)


def test_successor_window_includes_its_last_day(monkeypatch):
    anchor = date(2026, 1, 5)
    target = anchor + timedelta(days=pb._MAX_SUCCESSOR_DAYS)
    monkeypatch.setattr(cn_calendar, "is_session", lambda day: day == target)
    assert pb._next_session(anchor) == target


def test_successor_window_stops_at_its_last_day(monkeypatch):
    anchor = date(2026, 1, 5)
    beyond = anchor + timedelta(days=pb._MAX_SUCCESSOR_DAYS + 1)
    monkeypatch.setattr(cn_calendar, "is_session", lambda day: day == beyond)
    assert pb._next_session(anchor) is None


def test_expected_session_includes_the_close_at_exactly_17_00():
    now = datetime(2026, 10, 9, 17, 0, tzinfo=cn_calendar.CST)
    out = snapshot(now=now, read=reader(close_store()), observer=observe)
    assert out["expected_session"] == "2026-10-09"
    assert out["valid_until"] == "2026-10-12T09:00:00+00:00"


def test_price_basis_names_the_index_level():
    out = snapshot(now=FIXED_NOW, read=reader(close_store()), observer=observe)
    assert out["price_basis"] == "index_level_close"


def test_snapshot_reports_the_session_tip():
    out = snapshot(now=FIXED_NOW, read=reader(close_store()), observer=observe)
    assert out["session_tip"] == {"appended": [], "hold": None}


def test_benchmark_is_the_admitted_ss_series():
    out = snapshot(now=FIXED_NOW, read=reader(close_store()), observer=observe)
    assert out["benchmark"] == "000001.SS"


def test_reader_keeps_rows_after_the_expected_session():
    frame = close_store()
    later = pd.DataFrame([_held_row("2026-10-12", 3231.0)])
    frame = pd.concat([frame, later], ignore_index=True)
    got = licensed_index_closes(EXPECTED, load=lambda: frame)
    assert got.rows[-1] == ("2026-10-12", 3231.0)


def test_present_does_not_ingest_a_radar_payload():
    obs = snapshot(now=FIXED_NOW, read=reader(close_store()), observer=observe)
    plain = pb.present(obs)
    fed = pb.present(obs, radar={"odds": 0.9, "probability": 0.1})
    assert fed["phase"] == plain["phase"]
    assert fed["detail_chart_html"] == plain["detail_chart_html"]
    assert "probability" not in fed and "odds" not in fed


def test_source_label_is_the_licensed_close_field():
    out = snapshot(now=FIXED_NOW, read=reader(close_store()), observer=observe)
    assert out["source"] == "licensed_cn_index_daily/000001.SS.close"


def test_reader_returns_rows_in_store_order():
    frame = close_store().iloc[::-1].reset_index(drop=True)
    got = licensed_index_closes(EXPECTED, load=lambda: frame)
    assert [row[0] for row in got.rows] == frame["trade_date"].tolist()
