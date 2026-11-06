"""Nightly runner for the Grey Deer pullback prospective lane.

Synthetic closes only. The store loader, both clocks and both HEAD reads are
monkeypatched, and every log goes to ``tmp_path``. No price store, no
network, no repo ``data/`` write.

Run from the repo root:
    python3 -m pytest tests/test_grey_deer_pullback_nightly.py -rA -q
"""
from __future__ import annotations

import json
import math
from datetime import date, datetime, timedelta, timezone

import numpy as np
import pandas as pd
import pytest

import engine.grey_deer_pullback_forward as fwd
import engine.grey_deer_pullback_forward_grade as grader
from lib.nyse_calendar import ET, is_session
from scripts import grey_deer_pullback_nightly as nightly

HEAD = "b" * 40
LAST = date(2024, 7, 15)  # a Monday session
GAP = 40  # sessions between the two nights; every horizon (max 21) matures


def _at(day: date, hour: int, minute: int = 0) -> datetime:
    """ET civil time as an aware UTC instant (the writer's clock contract)."""
    return datetime(day.year, day.month, day.day, hour, minute, tzinfo=ET).astimezone(timezone.utc)


def _sessions_ending(end: date, n: int) -> list[date]:
    out: list[date] = []
    day = end
    while len(out) < n:
        if is_session(day):
            out.append(day)
        day -= timedelta(days=1)
    out.reverse()
    return out


def _gbm_prices(n: int, seed: int) -> np.ndarray:
    """Seeded GBM with clustered volatility and occasional gaps down."""
    rng = np.random.default_rng(seed)
    log_sig = np.empty(n)
    log_sig[0] = math.log(0.01)
    for i in range(1, n):
        log_sig[i] = 0.92 * log_sig[i - 1] + 0.08 * math.log(0.01) + float(rng.normal(0.0, 0.25))
    sigma = np.exp(np.clip(log_sig, math.log(0.004), math.log(0.08)))
    rets = rng.normal(0.0, 1.0, n) * sigma
    crash = rng.random(n) < 0.03
    rets = rets - crash * rng.uniform(0.06, 0.14, n)
    rets[0] = 0.0
    return 400.0 * np.exp(np.cumsum(rets))


def _series(dates: list[date], prices: np.ndarray) -> pd.Series:
    index = pd.DatetimeIndex(pd.to_datetime([day.isoformat() for day in dates]))
    return pd.Series(np.asarray(prices, dtype=float), index=index)


def _two_nights(n: int = 470, seed: int = 31):
    dates = _sessions_ending(LAST, n)
    prices = _gbm_prices(n, seed)
    first = _series(dates[: n - GAP], prices[: n - GAP])
    full = _series(dates, prices)
    return first, full, dates[n - GAP - 1], dates[-1]


def _arm(monkeypatch, when: datetime) -> None:
    monkeypatch.setenv("COLLECT_LANE", "nightly")
    monkeypatch.setenv("GREY_DEER_PULLBACK_WRITER_IDENTITY", "daily.yml:engine")
    monkeypatch.setenv("GREY_DEER_PULLBACK_GRADER_IDENTITY", "daily.yml:engine")
    monkeypatch.delenv("US_LANE", raising=False)
    monkeypatch.setattr(fwd, "_utc_now", lambda: when)
    monkeypatch.setattr(fwd, "_git_head", lambda: HEAD)
    monkeypatch.setattr(grader, "_utc_now", lambda: when.isoformat(timespec="seconds"))
    monkeypatch.setattr(grader, "_git_head", lambda: HEAD)


def _night(monkeypatch, capsys, close: pd.Series, when: datetime, out_dir) -> tuple[dict, list[str]]:
    _arm(monkeypatch, when)
    monkeypatch.setattr(nightly, "load_close", lambda ticker=nightly.TICKER: close)
    assert nightly.main(["--out-dir", str(out_dir)]) == 0
    lines = capsys.readouterr().out.splitlines()
    return json.loads(lines[-1]), [line for line in lines if "::warning" in line]


def _grades(out_dir) -> list[dict]:
    path = out_dir / grader.GRADE_LOG_NAME
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def test_issue_then_grade_round_trip_is_unrevised(tmp_path, monkeypatch, capsys):
    first, full, d1, d2 = _two_nights()
    assert first.index[-1] == pd.Timestamp(d1)

    report, warnings = _night(monkeypatch, capsys, first, _at(d1, 20), tmp_path)
    assert warnings == []
    assert report["store_identity"] == nightly.STORE_IDENTITY
    assert report["issue"]["issued"] == 30
    assert report["issue"]["refusals"] == ["OBSERVER_NOT_ON_MAIN"]
    assert report["grade"]["graded"] == 0
    assert report["grade"]["immature"] == 30

    report, warnings = _night(monkeypatch, capsys, full, _at(d2, 20), tmp_path)
    assert warnings == []
    assert report["issue"]["issued"] == 30
    assert report["grade"]["graded"] == 30
    rows = _grades(tmp_path)
    assert {row["asof"] for row in rows} == {d1.isoformat()}
    assert [row["revision_flag"] for row in rows] == [False] * 30

    # A same-night rerun is quiet: duplicates on issue, already_graded on grade.
    report, warnings = _night(monkeypatch, capsys, full, _at(d2, 20, 30), tmp_path)
    assert warnings == []
    assert report["issue"]["issued"] == 0
    assert report["issue"]["duplicates"] == 30
    assert report["grade"]["graded"] == 0
    assert report["grade"]["already_graded"] == 30
    assert len(_grades(tmp_path)) == 30


def test_a_revised_issue_close_flags_every_grade(tmp_path, monkeypatch, capsys):
    first, full, d1, d2 = _two_nights()
    _night(monkeypatch, capsys, first, _at(d1, 20), tmp_path)

    revised = full.copy()
    revised.loc[pd.Timestamp(d1)] *= 1.01
    report, _ = _night(monkeypatch, capsys, revised, _at(d2, 20), tmp_path)
    assert report["grade"]["graded"] == 30
    assert [row["revision_flag"] for row in _grades(tmp_path)] == [True] * 30


def test_store_unreadable_warns_and_exits_zero(tmp_path, monkeypatch, capsys):
    import collectors.massive_stock_day as massive_stock_day

    monkeypatch.setattr(massive_stock_day, "load_ticker", lambda ticker: pd.DataFrame())
    out_dir = tmp_path / "lane"
    assert nightly.main(["--out-dir", str(out_dir)]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert lines[0].startswith("::warning title=grey-deer-pullback-store-unreadable::")
    assert json.loads(lines[-1])["error"] == "store_unreadable"
    assert not out_dir.exists()


@pytest.mark.parametrize("lane", [None, "render"])
def test_off_lane_warns_and_writes_nothing(tmp_path, monkeypatch, capsys, lane):
    first, _, d1, _ = _two_nights()
    _arm(monkeypatch, _at(d1, 20))
    monkeypatch.delenv("US_LANE", raising=False)
    if lane is None:
        monkeypatch.delenv("COLLECT_LANE", raising=False)
    else:
        monkeypatch.setenv("COLLECT_LANE", lane)
    monkeypatch.setattr(nightly, "load_close", lambda ticker=nightly.TICKER: first)
    out_dir = tmp_path / "lane"
    assert nightly.main(["--out-dir", str(out_dir)]) == 0
    lines = capsys.readouterr().out.splitlines()
    warnings = [line for line in lines if "::warning" in line]
    assert len(warnings) == 2
    assert all(line.startswith("::warning title=") for line in warnings)
    assert "LANE" in warnings[0] and "LANE" in warnings[1]
    report = json.loads(lines[-1])
    assert report["issue"] == {"refused": "LANE"}
    assert report["grade"]["refusals"] == ["LANE"]
    assert not out_dir.exists()


def test_an_issue_exception_still_grades(tmp_path, monkeypatch, capsys):
    first, full, d1, d2 = _two_nights()
    _night(monkeypatch, capsys, first, _at(d1, 20), tmp_path)

    def _boom(*_args, **_kwargs):
        raise RuntimeError("writer exploded")

    monkeypatch.setattr(fwd, "issue", _boom)
    report, warnings = _night(monkeypatch, capsys, full, _at(d2, 20), tmp_path)
    assert warnings == ["::warning title=grey-deer-pullback-issue-error::RuntimeError: writer exploded"]
    assert report["issue"] == {"error": "RuntimeError"}
    assert report["grade"]["graded"] == 30


def test_load_close_normalises_both_store_shapes(monkeypatch):
    import collectors.massive_stock_day as massive_stock_day

    columns = pd.DataFrame(
        {
            "date": ["2024-07-12", "2024-07-10", "2024-07-11"],
            "open": [1.0, 1.0, 1.0],
            "close": [3.0, 1.0, 2.0],
        }
    )
    indexed = columns.assign(date=pd.to_datetime(columns["date"])).set_index("date")
    utc_midnight = indexed.tz_localize("UTC")
    utc_21 = indexed.copy()
    utc_21.index = pd.DatetimeIndex(
        [pd.Timestamp(f"{stamp.strftime('%Y-%m-%d')}T21:00:00Z") for stamp in indexed.index]
    )
    expected = pd.Series(
        [1.0, 2.0, 3.0],
        index=pd.DatetimeIndex(pd.to_datetime(["2024-07-10", "2024-07-11", "2024-07-12"])),
    )
    for frame in (columns, indexed, utc_midnight, utc_21):
        monkeypatch.setattr(massive_stock_day, "load_ticker", lambda ticker, frame=frame: frame)
        pd.testing.assert_series_equal(nightly.load_close("SPY"), expected, check_freq=False)
