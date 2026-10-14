"""China price-basis adapter contracts. Synthetic inputs, no network or source writes."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pandas as pd
import pytest

from lib import cn_calendar
from lib import cn_pullback_observation as pb
from lib.cn_pullback_observation import LicensedCloses, SourceRefused, licensed_index_closes, snapshot
from lib.pullback_observation import observe

# 2026-10-09 17:30 CST: Friday's close has settled.
FIXED_NOW = datetime(2026, 10, 9, 9, 30, tzinfo=timezone.utc)
EXPECTED = date(2026, 10, 9)


def sessions_through(last: date, n: int) -> list[date]:
    days, day = [], last
    while len(days) < n:
        if cn_calendar.is_session(day):
            days.append(day)
        day -= timedelta(days=1)
    return days[::-1]


def store(last=EXPECTED, closes=None, ticker="000001.SS"):
    """The collector's store shape: ISO trade_date, index close, one ticker."""
    if closes is None:
        # 70 flat-to-rising sessions to a 3400 high, then a settled 5% decline.
        closes = [3200.0 + 3 * i for i in range(67)] + [3400.0, 3300.0, 3260.0, 3230.0]
    days = sessions_through(last, len(closes))
    return pd.DataFrame({"ticker": ticker, "trade_date": [d.isoformat() for d in days],
                         "close": closes, "first_seen": "2026-10-09T09:00:00+00:00"})


def reader(frame):
    return lambda expected: licensed_index_closes(expected, load=lambda: frame)


def test_licensed_store_feeds_the_one_owner_on_the_sse_calendar():
    seen = []

    def owner(rows, *, expected_session, is_session):
        seen.append((rows[-1], expected_session, is_session))
        return observe(rows, expected_session=expected_session, is_session=is_session)

    out = snapshot(now=FIXED_NOW, read=reader(store()), observer=owner)
    assert seen == [(("2026-10-09", 3230.0), EXPECTED, cn_calendar.is_session)]
    assert out["available"] is True and out["quality"] == "current"
    assert out["market"] == "cn" and out["clock"] == "settled_close"
    assert out["asof"] == out["expected_session"] == "2026-10-09"
    assert out["peak_close"] == 3400.0 and out["close"] == 3230.0
    assert out["phase"] in {"underway", "stabilizing"} and out["active"] is True
    assert out["benchmark_en"] == "Shanghai Composite" and out["benchmark_zh"] == "上证综指"


def test_view_expires_at_the_next_sessions_settle_across_golden_week():
    # 2026-09-30 settled; the next session is 10-08 after the 10-01..10-07 closure.
    now = datetime(2026, 10, 3, 4, tzinfo=timezone.utc)
    out = snapshot(now=now, read=reader(store(last=date(2026, 9, 30))), observer=observe)
    assert out["expected_session"] == "2026-09-30"
    assert out["valid_until"] == "2026-10-08T09:00:00+00:00"
    assert out["quality"] == "current"


def test_before_the_settle_buffer_the_prior_session_is_expected():
    # 16:30 CST: today's close is in the store but not yet the owning session.
    now = datetime(2026, 10, 9, 8, 30, tzinfo=timezone.utc)
    out = snapshot(now=now, read=reader(store()), observer=observe)
    assert out["expected_session"] == "2026-10-08" and out["asof"] == "2026-10-08"
    assert out["valid_until"] == "2026-10-09T09:00:00+00:00"


def test_a_store_behind_the_session_is_delayed_not_patched():
    out = snapshot(now=FIXED_NOW, read=reader(store(last=date(2026, 10, 8))), observer=observe)
    assert out["available"] is False and out["quality"] == "delayed"
    assert pb.present(out)["phase"] == "unavailable"


def test_short_history_is_insufficient_not_a_calm_reading():
    out = snapshot(now=FIXED_NOW, read=reader(store(closes=[3300.0] * 40)), observer=observe)
    assert out["available"] is False and out["quality"] == "insufficient_history"


@pytest.mark.parametrize("frame", [
    None,
    pd.DataFrame(),
    store().drop(columns=["close"]),
    store(ticker="399001.SZ"),
])
def test_missing_or_foreign_store_fails_closed(frame):
    with pytest.raises(SourceRefused) as exc:
        licensed_index_closes(EXPECTED, load=lambda: frame)
    assert exc.value.quality == "source_unavailable"
    out = snapshot(now=FIXED_NOW, read=reader(frame), observer=observe)
    assert out["available"] is False and out["quality"] == "source_unavailable"


def test_a_rebased_series_refuses_the_basis():
    closes = [3200.0] * 69 + [320.0, 321.0]
    out = snapshot(now=FIXED_NOW, read=reader(store(closes=closes)), observer=observe)
    assert out["available"] is False and out["quality"] == "price_basis_discontinuity"


def test_a_limit_sized_index_move_is_not_mistaken_for_a_rebase():
    closes = [3200.0 + i for i in range(69)] + [2600.0, 2620.0]
    out = snapshot(now=FIXED_NOW, read=reader(store(closes=closes)), observer=observe)
    assert out["quality"] == "current"


def test_reader_never_touches_the_internal_only_yahoo_store(monkeypatch):
    from lib import store as macro_store

    def forbidden(*args, **kwargs):
        raise AssertionError("the internal-only store must never be read")

    monkeypatch.setattr(macro_store, "read", forbidden)
    assert isinstance(licensed_index_closes(EXPECTED, load=lambda: store()), LicensedCloses)


def test_default_reader_reads_only_the_licensed_collector_store(tmp_path, monkeypatch):
    from collectors import tushare_index_daily as tid
    out = tmp_path / "index_daily.parquet"
    monkeypatch.setattr(tid, "OUT", out)
    with pytest.raises(SourceRefused):
        licensed_index_closes(EXPECTED)
    store().to_parquet(out, index=False)
    got = licensed_index_closes(EXPECTED)
    assert got.rows[-1] == ("2026-10-09", 3230.0) and got.hold is None


def test_provenance_label_never_names_a_vendor():
    out = snapshot(now=FIXED_NOW, read=reader(store()), observer=observe)
    text = " ".join(str(out[k]) for k in ("source", "price_basis", "benchmark")).lower()
    assert "tushare" not in text and "yahoo" not in text


@pytest.mark.parametrize("now", [None, datetime(2026, 10, 9, 9, 30)])
def test_explicit_clock_must_be_aware_datetime(now):
    if now is None:
        assert snapshot(read=reader(store()), observer=None)["market"] == "cn"
        return
    with pytest.raises(ValueError):
        snapshot(now=now, read=reader(store()), observer=observe)


def test_missing_observer_yields_unavailable_and_reads_nothing():
    def never(expected):
        raise AssertionError("no source is read before an observer is admitted")

    out = snapshot(now=FIXED_NOW, read=never, observer=None)
    assert out["available"] is False and out["quality"] == "observer_unavailable"


def test_cn_view_draws_a_country_correct_accessible_chart():
    view = pb.present(snapshot(now=FIXED_NOW, read=reader(store()), observer=observe))
    assert view["phase"] in {"underway", "stabilizing"}
    assert view["detail_path"]["dates"][-1] == "2026-10-09"
    html = view["detail_chart_html"]
    assert 'aria-label="Observed Shanghai Composite' in html
    assert "SPY" not in html
    assert "probability" not in view and "score" not in view and "forecast" not in view


def test_us_observation_is_never_presented_as_china():
    out = snapshot(now=FIXED_NOW, read=reader(store()), observer=observe)
    assert pb.present({**out, "market": "us"})["phase"] == "unavailable"
