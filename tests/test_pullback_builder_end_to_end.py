"""Builder hooks over synthetic stores, below the snapshot seam.

The page builders call the real snapshot, the shared episode owner, and
present. These tests replace only the store loader and, for the US reader,
the session-close and corporate-action seams. No source file is read and
nothing is fetched.
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone

import pandas as pd
import pytest

from collectors import massive_stock_day
from engine.close_pass import massive_close
from engine.close_pass.massive_close import CorpActions, SessionCloses
from lib import cn_calendar, cn_pullback_observation, nyse_calendar, us_pullback_observation
from scripts import build_china, build_site


# Friday 2026-10-09 is a regular session on both calendars. The instants below
# are after that session's 17:00 settle, so the store tip is the expected day.
SESSION = date(2026, 10, 9)
PRIOR = date(2026, 10, 8)
CN_NOW = datetime(2026, 10, 9, 9, 30, tzinfo=timezone.utc)
US_NOW = datetime(2026, 10, 9, 22, 0, tzinfo=timezone.utc)
# SourceRefused carries this text. The builder must not log it.
REFUSAL_TEXT = "source_unavailable"
MEASURED = ("close", "peak_close", "low_close", "drawdown_pct", "loss_recovered_pct")


def call_hook(hook, now):
    """E8: every builder call is wrapped so a raised error fails the test."""
    try:
        return hook(now=now)
    except Exception as exc:  # noqa: BLE001 — the hook's contract is not to raise
        pytest.fail(f"{hook.__name__} raised {type(exc).__name__}")


def session_days(is_session, last, n):
    found = []
    day = last
    while len(found) < n:
        if is_session(day):
            found.append(day)
        day -= timedelta(days=1)
    return found[::-1]


def active_closes():
    """Seventy-one synthetic closes: a rise, one high, then a new low.

    The last close is the episode low, so stabilization cannot start and the
    owner keeps the episode active.
    """
    return [3200.0 + 3 * i for i in range(67)] + [3400.0, 3300.0, 3260.0, 3230.0]


def cn_frame(days, closes, ticker=None):
    ticker = cn_pullback_observation.BENCHMARK if ticker is None else ticker
    tickers = ticker if isinstance(ticker, list) else [ticker] * len(days)
    return pd.DataFrame({
        "ticker": tickers,
        "trade_date": [d.isoformat() for d in days],
        "close": list(closes),
        "first_seen": "2026-10-09T09:00:00+00:00",
    })


def us_frame(days, closes):
    return pd.DataFrame(
        {"close": list(closes)},
        index=pd.to_datetime([d.isoformat() for d in days]),
    )


def patch_cn(monkeypatch, frame):
    calls = []

    def load():
        calls.append("load")
        return frame

    monkeypatch.setattr(cn_pullback_observation, "_load_store", load)
    return calls


def patch_us(monkeypatch, frame, *, actions=None):
    calls = []

    def load(ticker):
        calls.append(("load", ticker))
        return frame

    def fetch(session, wanted):
        calls.append(("closes", session))
        return SessionCloses(session=session, closes={}, finalized=True)

    def guard(session):
        calls.append(("actions", session))
        if actions is not None:
            return actions(session)
        return CorpActions(session=session, complete=True)

    monkeypatch.setattr(massive_stock_day, "load_ticker", load)
    monkeypatch.setattr(massive_close, "fetch_session_closes", fetch)
    monkeypatch.setattr(massive_close, "corp_action_tickers", guard)
    return calls


def assert_log_omits(caplog, secret):
    """A builder log line may name an exception type and nothing from its message."""
    assert secret not in caplog.text
    for rec in caplog.records:
        if rec.name not in {"build_china", "build_site"}:
            continue
        text = rec.getMessage()
        assert secret not in text
        assert text.rsplit(": ", 1)[-1].isidentifier()


def assert_unavailable(view, quality):
    assert view is not None
    assert view["phase"] == "unavailable"
    assert view["detail_chart_html"] == ""
    assert view["detail_path"] is None
    obs = view["observation"]
    assert obs["available"] is False
    assert obs["quality"] == quality
    assert obs["active"] is None
    for key in MEASURED:
        assert obs.get(key) is None
    return obs


def assert_active(view, market):
    assert view is not None
    obs = view["observation"]
    assert view["phase"] == "underway"
    assert obs["phase"] == "underway"
    assert obs["active"] is True
    assert obs["available"] is True
    assert obs["quality"] == "current"
    assert obs["market"] == market
    assert obs["asof"] == obs["expected_session"] == SESSION.isoformat()
    assert datetime.fromisoformat(obs["valid_until"]) > datetime.fromisoformat(obs["produced_at"])
    assert view["detail_chart_html"]
    assert view["detail_path"]["dates"][-1] == SESSION.isoformat()
    assert "forecast" not in view and "probability" not in view
    return obs


def _cn_days(n):
    return session_days(cn_calendar.is_session, SESSION, n)


def _us_days(n):
    return session_days(nyse_calendar.is_session, SESSION, n)


def test_e1_cn_healthy_store_is_an_active_episode(monkeypatch):
    closes = active_closes()
    calls = patch_cn(monkeypatch, cn_frame(_cn_days(len(closes)), closes))
    view = call_hook(build_china._cn_pullback_risk_popup, CN_NOW)
    assert calls == ["load"]
    assert_active(view, "cn")
    assert "Shanghai Composite" in view["detail_chart_html"]


def test_e1_us_healthy_store_is_an_active_episode(monkeypatch):
    closes = active_closes()
    calls = patch_us(monkeypatch, us_frame(_us_days(len(closes)), closes))
    view = call_hook(build_site._us_pullback_risk_popup, US_NOW)
    assert calls == [("load", us_pullback_observation.BENCHMARK)]
    obs = assert_active(view, "us")
    assert obs["benchmark"] == "SPY"
    assert "SPY" in view["detail_chart_html"]


@pytest.mark.parametrize("kind", ["missing", "empty", "columns"])
def test_e2_cn_bad_store_is_unavailable_and_its_message_is_not_logged(monkeypatch, caplog, kind):
    frame = {
        "missing": None,
        "empty": pd.DataFrame(),
        "columns": pd.DataFrame({
            "ticker": [cn_pullback_observation.BENCHMARK],
            "trade_date": [SESSION.isoformat()],
        }),
    }[kind]
    calls = patch_cn(monkeypatch, frame)
    with caplog.at_level("WARNING"):
        view = call_hook(build_china._cn_pullback_risk_popup, CN_NOW)
    assert calls == ["load"]
    assert_unavailable(view, "source_unavailable")
    assert_log_omits(caplog, REFUSAL_TEXT)


@pytest.mark.parametrize("kind", ["missing", "empty", "columns"])
def test_e2_us_bad_store_is_unavailable_and_its_message_is_not_logged(monkeypatch, caplog, kind):
    frame = {
        "missing": None,
        "empty": pd.DataFrame(),
        "columns": pd.DataFrame({"open": [1.0]}, index=pd.to_datetime([SESSION.isoformat()])),
    }[kind]
    calls = patch_us(monkeypatch, frame)
    with caplog.at_level("WARNING"):
        view = call_hook(build_site._us_pullback_risk_popup, US_NOW)
    assert calls == [("load", us_pullback_observation.BENCHMARK)]
    assert_unavailable(view, "source_unavailable")
    assert_log_omits(caplog, REFUSAL_TEXT)


def test_e3_cn_fewer_than_63_closes_is_not_active_and_has_no_chart(monkeypatch):
    closes = [3300.0] * 40
    calls = patch_cn(monkeypatch, cn_frame(_cn_days(len(closes)), closes))
    view = call_hook(build_china._cn_pullback_risk_popup, CN_NOW)
    assert calls == ["load"]
    obs = assert_unavailable(view, "insufficient_history")
    assert obs["active"] is not True
    assert len(closes) < 63


def test_e3_us_fewer_than_63_closes_is_not_active_and_has_no_chart(monkeypatch):
    closes = [3300.0] * 40
    calls = patch_us(monkeypatch, us_frame(_us_days(len(closes)), closes))
    view = call_hook(build_site._us_pullback_risk_popup, US_NOW)
    assert calls == [("load", us_pullback_observation.BENCHMARK)]
    assert_unavailable(view, "insufficient_history")


def test_e4_cn_second_ticker_mixed_in_is_source_unavailable(monkeypatch):
    closes = active_closes()
    days = _cn_days(len(closes))
    mixed = pd.concat([
        cn_frame(days, closes),
        cn_frame(days, closes, ticker="399001.SZ"),
    ], ignore_index=True)
    calls = patch_cn(monkeypatch, mixed)
    view = call_hook(build_china._cn_pullback_risk_popup, CN_NOW)
    assert calls == ["load"]
    assert set(mixed["ticker"]) == {cn_pullback_observation.BENCHMARK, "399001.SZ"}
    assert_unavailable(view, "source_unavailable")


def test_e5_cn_two_for_one_level_break_has_no_chart_or_numbers(monkeypatch):
    days = _cn_days(2)
    calls = patch_cn(monkeypatch, cn_frame(days, [3200.0, 1600.0]))
    view = call_hook(build_china._cn_pullback_risk_popup, CN_NOW)
    assert calls == ["load"]
    assert_unavailable(view, "price_basis_discontinuity")


def test_e5_us_two_for_one_level_break_has_no_chart_or_numbers(monkeypatch):
    days = _us_days(2)
    calls = patch_us(monkeypatch, us_frame(days, [3200.0, 1600.0]))
    view = call_hook(build_site._us_pullback_risk_popup, US_NOW)
    assert calls == [("load", us_pullback_observation.BENCHMARK)]
    assert_unavailable(view, "price_basis_discontinuity")


def test_e6_us_split_like_tip_with_incomplete_guard_is_refused(monkeypatch):
    """0.80 sits inside the hard band and outside the suspect band.

    The landed tip is the later session of that pair. An incomplete guard
    refuses with the adapter's stored-suspect reason, rather than appending.
    """
    days = _us_days(3)
    frame = us_frame(days, [100.0, 100.0, 80.0])

    def actions(session):
        return CorpActions(session=session, complete=False)

    calls = patch_us(monkeypatch, frame, actions=actions)
    view = call_hook(build_site._us_pullback_risk_popup, US_NOW)
    assert ("closes", SESSION.isoformat()) not in calls
    assert ("actions", SESSION.isoformat()) in calls
    assert_unavailable(view, "corporate_action_guard_down")


def test_e6_us_split_like_tip_listing_the_benchmark_is_a_discontinuity(monkeypatch):
    days = _us_days(3)
    frame = us_frame(days, [100.0, 100.0, 80.0])

    def actions(session):
        return CorpActions(session=session, complete=True,
                           tickers=frozenset({us_pullback_observation.BENCHMARK}))

    calls = patch_us(monkeypatch, frame, actions=actions)
    view = call_hook(build_site._us_pullback_risk_popup, US_NOW)
    assert ("actions", SESSION.isoformat()) in calls
    assert ("closes", SESSION.isoformat()) not in calls
    assert_unavailable(view, "price_basis_discontinuity")


def _settle_instant(day, zone, settle):
    return datetime.combine(day, settle, tzinfo=zone)


def _expected(view):
    return view["observation"]["expected_session"]


def test_e7_cn_expected_session_advances_at_the_settle_instant(monkeypatch):
    # The clock treats 17:00 Asia/Shanghai as already settled (`>=`), so the
    # session advances at that instant and not one second earlier.
    assert cn_calendar.is_session(PRIOR) and cn_calendar.is_session(SESSION)
    assert cn_calendar._CLOSE_PLUS_SETTLE == time(17, 0)
    closes = active_closes()
    calls = patch_cn(monkeypatch, cn_frame(_cn_days(len(closes)), closes))
    at = _settle_instant(SESSION, cn_calendar.CST, time(17, 0))
    probes = {"before": at - timedelta(seconds=1), "at": at, "after": at + timedelta(seconds=1)}
    got = {name: _expected(call_hook(build_china._cn_pullback_risk_popup, now))
           for name, now in probes.items()}
    assert calls == ["load", "load", "load"]
    assert got["before"] == PRIOR.isoformat()
    assert got["at"] == SESSION.isoformat()
    assert got["after"] == SESSION.isoformat()


def test_e7_us_expected_session_advances_at_the_settle_instant(monkeypatch):
    assert nyse_calendar.is_session(PRIOR) and nyse_calendar.is_session(SESSION)
    settle = nyse_calendar._CLOSE_PLUS_SETTLE
    closes = active_closes()
    calls = patch_us(monkeypatch, us_frame(_us_days(len(closes)), closes))
    at = _settle_instant(SESSION, nyse_calendar.ET, settle)
    probes = {"before": at - timedelta(seconds=1), "at": at, "after": at + timedelta(seconds=1)}
    got = {name: _expected(call_hook(build_site._us_pullback_risk_popup, now))
           for name, now in probes.items()}
    assert [name for name, _ticker in calls] == ["load", "load", "load"]
    assert got["before"] == PRIOR.isoformat()
    assert got["at"] == SESSION.isoformat()
    assert got["after"] == SESSION.isoformat()
