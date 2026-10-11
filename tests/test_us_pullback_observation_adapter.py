"""US price-basis adapter contracts. Synthetic inputs, no network or source writes."""
from __future__ import annotations

from datetime import date, datetime, timezone

import pandas as pd
import pytest

from engine.close_pass.massive_close import CorpActions, SessionCloses
from lib import nyse_calendar
from lib import us_pullback_observation as pb
from lib.us_pullback_observation import (
    LicensedCloses, SourceRefused, licensed_spy_closes, snapshot,
)


FIXED_NOW = datetime(2026, 10, 9, 22, 0, tzinfo=timezone.utc)
EXPECTED = date(2026, 10, 9)


def store(stamps=("2026-10-06", "2026-10-07", "2026-10-08"), closes=(90.0, 88.5, 88.0),
          column="close"):
    """The licensed daily store's shape: naive UTC-midnight date index, raw close."""
    return pd.DataFrame({column: list(closes)}, index=pd.to_datetime(list(stamps)))


def quiet(session):
    return CorpActions(session=session, complete=True)


def final_close(price=89.0):
    def fetch(session, wanted):
        assert wanted == {"SPY"}
        return SessionCloses(session=session, closes={"SPY": price},
                             source="grouped", finalized=True)
    return fetch


def reader(**over):
    kwargs = {"load": lambda ticker: store(), "session_closes": final_close(),
              "corp_actions": quiet}
    kwargs.update(over)
    return lambda expected: licensed_spy_closes(expected, **kwargs)


def observer_receipt(rows, *, expected_session, is_session):
    return {
        "schema": "pullback_observation.v1",
        "available": True,
        "quality": "current",
        "phase": "underway",
        "active": True,
        "asof": expected_session.isoformat(),
        "expected_session": expected_session.isoformat(),
        "close": rows[-1][1],
        "peak_close": 100.0,
        "low_close": 87.0,
        "peak_session": "2026-09-18",
        "source_digest": "a" * 64,
        "price_path": {"dates": ["2026-10-08", "2026-10-09"], "vals": [-12.0, -11.0]},
    }


def currency_observer(rows, *, expected_session, is_session):
    """Mirrors the owner's currency rule: a series short of the session is delayed."""
    if rows[-1][0] != expected_session.isoformat():
        return {"schema": "pullback_observation.v1", "available": False,
                "quality": "delayed", "phase": "unavailable", "active": None,
                "asof": rows[-1][0], "drawdown_pct": None}
    return observer_receipt(rows, expected_session=expected_session, is_session=is_session)


def test_licensed_store_and_same_session_close_feed_the_owner_observer():
    seen = []
    def load(ticker):
        seen.append(("load", ticker))
        return store()

    def observe(rows, *, expected_session, is_session):
        seen.append(("observe", tuple(rows), expected_session))
        assert is_session is nyse_calendar.is_session
        return observer_receipt(rows, expected_session=expected_session, is_session=is_session)

    out = snapshot(now=FIXED_NOW, read=reader(load=load), observer=observe)
    assert seen == [
        ("load", "SPY"),
        ("observe", (("2026-10-06", 90.0), ("2026-10-07", 88.5), ("2026-10-08", 88.0),
                     ("2026-10-09", 89.0)), EXPECTED),
    ]
    assert out["market"] == "us" and out["benchmark"] == "SPY"
    assert out["benchmark_en"].startswith("S&P 500") and "标普" in out["benchmark_zh"]
    assert out["price_basis"] == "split_adjusted_dividend_unadjusted_close"
    assert out["close"] == 89.0 and out["available"] is True
    assert out["session_tip"] == {"appended": [{"session": "2026-10-09", "settlement": "final"}],
                                  "hold": None}
    assert out["source_digest"] == "a" * 64
    assert out["clock"] == "settled_close"
    assert out["valid_until"] == "2026-10-12T21:00:00+00:00"
    assert out["produced_at"] == FIXED_NOW.isoformat()


def test_provenance_label_never_names_a_vendor():
    assert not any(v in pb.SOURCE.lower() for v in ("yahoo", "massive", "polygon"))
    out = snapshot(now=FIXED_NOW, read=reader(), observer=observer_receipt)
    assert out["source"] == pb.SOURCE


def test_reader_never_touches_the_internal_only_yahoo_store(monkeypatch):
    from lib import store as yahoo_store
    def forbidden(*args, **kwargs):
        raise AssertionError("Yahoo prices are internal-only; never a popup source")
    monkeypatch.setattr(yahoo_store, "read", forbidden)
    out = snapshot(now=FIXED_NOW, read=reader(), observer=observer_receipt)
    assert out["available"] is True


def test_current_store_needs_no_session_fetch():
    def no_network(*args, **kwargs):
        raise AssertionError("a store that already holds the session needs no fetch")
    got = licensed_spy_closes(
        EXPECTED, load=lambda t: store(stamps=("2026-10-07", "2026-10-08", "2026-10-09")),
        session_closes=no_network, corp_actions=no_network)
    assert got.rows[-1] == ("2026-10-09", 88.0)
    assert got.appended == () and got.hold is None


def test_multi_session_tip_appends_in_order_and_never_skips_a_failed_session():
    asked = []
    def closes(session, wanted):
        asked.append(session)
        if session == "2026-10-08":
            return SessionCloses(session=session, reason="grouped and snapshot both returned no rows")
        return SessionCloses(session=session, closes={"SPY": 88.0}, finalized=True)
    got = licensed_spy_closes(
        EXPECTED, load=lambda t: store(stamps=("2026-10-05", "2026-10-06"), closes=(90.0, 89.0)),
        session_closes=closes, corp_actions=quiet)
    assert asked == ["2026-10-07", "2026-10-08"]
    assert [r[0] for r in got.rows] == ["2026-10-05", "2026-10-06", "2026-10-07"]
    assert got.hold == "session_close_unavailable"


def test_provisional_snapshot_close_is_labelled_provisional():
    def snap(session, wanted):
        return SessionCloses(session=session, closes={"SPY": 89.0}, finalized=False)
    got = licensed_spy_closes(EXPECTED, load=lambda t: store(), session_closes=snap,
                              corp_actions=quiet)
    assert got.appended == ({"session": "2026-10-09", "settlement": "provisional"},)


@pytest.mark.parametrize("actions, hold", [
    (lambda s: CorpActions(session=s, complete=False, reason="page cap"), "corporate_action_guard_down"),
    (lambda s: CorpActions(session=s, tickers=frozenset({"SPY"}), complete=True), "corporate_action_on_session"),
])
def test_corporate_action_guard_holds_the_tip_and_the_owner_reports_delay(actions, hold):
    def no_close(*args, **kwargs):
        raise AssertionError("no close may be spliced past a down or tripped guard")
    out = snapshot(now=FIXED_NOW, read=reader(session_closes=no_close, corp_actions=actions),
                   observer=currency_observer)
    assert out["available"] is False and out["quality"] == "delayed"
    assert out["drawdown_pct"] is None
    assert out["session_tip"] == {"appended": [], "hold": hold}


@pytest.mark.parametrize("result", [
    SessionCloses(session="2026-10-09", reason="no API key (MASSIVE_API_KEY/POLYGON_API_KEY unset)"),
    SessionCloses(session="2026-10-08", closes={"SPY": 89.0}, finalized=True),
    SessionCloses(session="2026-10-09", closes={"QQQ": 500.0}, finalized=True),
    SessionCloses(session="2026-10-09", closes={"SPY": float("nan")}, finalized=True),
])
def test_unusable_session_close_is_held_not_spliced(result):
    out = snapshot(now=FIXED_NOW, read=reader(session_closes=lambda s, w: result),
                   observer=currency_observer)
    assert out["quality"] == "delayed" and out["available"] is False
    assert out["session_tip"]["hold"] == "session_close_unavailable"


def test_stalled_store_is_not_patched_from_session_closes():
    def no_network(*args, **kwargs):
        raise AssertionError("a stalled store must not be rebuilt from session closes")
    out = snapshot(
        now=FIXED_NOW,
        read=reader(load=lambda t: store(stamps=("2026-10-01", "2026-10-02"), closes=(90.0, 89.0)),
                    session_closes=no_network, corp_actions=no_network),
        observer=currency_observer)
    assert out["quality"] == "delayed"
    assert out["session_tip"] == {"appended": [], "hold": "store_behind"}


@pytest.mark.parametrize("closes, tip", [
    ((90.0, 45.0, 44.0), 44.5),     # 2:1 split inside the stored history
    ((90.0, 89.0, 88.0), 44.0),     # 2:1 split on the appended session
    ((90.0, 180.0, 181.0), 182.0),  # 1:2 reverse split
])
def test_split_like_discontinuity_refuses_the_basis(closes, tip):
    def observe(*args, **kwargs):
        raise AssertionError("no observation on an unverified price basis")
    out = snapshot(now=FIXED_NOW,
                   read=reader(load=lambda t: store(closes=closes),
                               session_closes=final_close(tip)),
                   observer=observe)
    assert out["available"] is False and out["quality"] == "price_basis_discontinuity"
    assert out["drawdown_pct"] is None


def test_crash_sized_move_is_not_mistaken_for_a_split():
    got = licensed_spy_closes(EXPECTED, load=lambda t: store(closes=(90.0, 79.0, 70.0)),
                              session_closes=final_close(62.0), corp_actions=quiet)
    assert got.rows[-1] == ("2026-10-09", 62.0)


@pytest.mark.parametrize("frame", [None, pd.DataFrame(), store(column="close_price"),
                                   store(stamps=("2026-10-12",), closes=(90.0,))])
def test_missing_store_or_close_column_fails_closed(frame):
    with pytest.raises(SourceRefused) as refused:
        licensed_spy_closes(EXPECTED, load=lambda t: frame,
                            session_closes=final_close(), corp_actions=quiet)
    assert refused.value.quality == "source_unavailable"
    out = snapshot(now=FIXED_NOW, read=reader(load=lambda t: frame), observer=observer_receipt)
    assert out["quality"] == "source_unavailable" and out["available"] is False
    assert out["active"] is None and out["drawdown_pct"] is None


@pytest.mark.parametrize("failure", [None, LicensedCloses(rows=[]), [("2026-10-09", 1.0)],
                                     ValueError("corrupt"), OSError("read failed")])
def test_missing_or_unreadable_source_fails_closed(failure):
    def read(expected):
        if isinstance(failure, Exception):
            raise failure
        return failure
    out = snapshot(now=FIXED_NOW, read=read, observer=observer_receipt)
    assert out["quality"] == "source_unavailable"
    assert out["available"] is False
    assert out["active"] is None
    assert out["drawdown_pct"] is None


def test_intraday_label_is_forwarded_intact_for_canonical_rejection():
    def observer(rows, *, expected_session, is_session):
        assert any(label.startswith("2026-10-08T14:15:00") for label, _ in rows)
        return {"schema": "pullback_observation.v1", "available": False,
                "quality": "invalid_session_label", "phase": "unavailable",
                "active": None, "drawdown_pct": None, "asof": None}
    mixed = pd.DataFrame({"close": [88.0, 88.2]},
                         index=[pd.Timestamp("2026-10-07"), pd.Timestamp("2026-10-08T14:15:00")])
    out = snapshot(now=FIXED_NOW, read=reader(load=lambda t: mixed), observer=observer)
    assert not out["available"] and out["quality"] == "invalid_session_label"


@pytest.mark.parametrize("now", [datetime(2026, 10, 9, 22, 0), "2026-10-09"])
def test_explicit_clock_must_be_aware_datetime(now):
    with pytest.raises(ValueError):
        snapshot(now=now, read=reader(), observer=observer_receipt)


def test_caller_cannot_promote_inconsistent_observer_as_current():
    def inconsistent(rows, *, expected_session, is_session):
        result = observer_receipt(rows, expected_session=expected_session, is_session=is_session)
        result["asof"] = "2026-10-08"
        return result
    out = snapshot(now=FIXED_NOW, read=reader(), observer=inconsistent)
    assert out["available"] is False and out["quality"] == "observation_inconsistent"
    assert out["drawdown_pct"] is None
    assert out["source_digest"] is None


def test_default_missing_observer_dependency_yields_unavailable_not_fabricated_price():
    out = snapshot(now=FIXED_NOW, read=reader())
    # This repository branch has not taken custody of held PR #8188's observer.
    # Once that source is merged, it may produce an observation; never infer one from a score.
    assert out["schema"] == "pullback_observation.v1"
    assert out["market"] == "us"
    assert out["price_basis"] == "split_adjusted_dividend_unadjusted_close"
    assert out["quality"] == "observer_unavailable"


def test_us_view_has_country_correct_accessible_chart_without_reusing_china_labels():
    from lib.us_pullback_observation import present
    obs = observer_receipt([("2026-10-08", 88.0), ("2026-10-09", 89.0)],
                           expected_session=FIXED_NOW.date(), is_session=nyse_calendar.is_session)
    obs.update(market="us", benchmark="SPY", benchmark_en="S&P 500 ETF (SPY)",
               benchmark_zh="标普500 ETF (SPY)", quality="current",
               clock="settled_close", valid_until="2026-10-12T21:00:00+00:00")
    view = present(obs, radar={"top_score": 99, "dd21": 0.98})
    assert view["phase"] == "underway"
    assert view["observation"] is obs
    assert 'aria-label="Observed SPY' in view["detail_chart_html"]
    assert "Shanghai" not in view["detail_chart_html"]
    assert "probability" not in view and "score" not in view and "forecast" not in view


def test_no_usable_price_cannot_generate_a_spurious_drawdown_chart():
    from lib.us_pullback_observation import present
    obs = snapshot(now=FIXED_NOW, read=lambda expected: None, observer=observer_receipt)
    view = present(obs)
    assert view["phase"] == "unavailable"
    assert view["detail_chart_html"] == ""
    assert view["observation"]["drawdown_pct"] is None


def test_unmerged_observer_must_be_explicitly_injected_not_auto_imported(monkeypatch):
    """A similarly named module is not a release/ownership or license receipt."""
    import sys
    from types import ModuleType
    candidate = ModuleType("lib.pullback_observation")
    invoked = []
    def unauthorized_observe(*args, **kwargs):
        invoked.append(True)
        raise AssertionError("unmerged observer must not run")
    candidate.observe = unauthorized_observe
    monkeypatch.setitem(sys.modules, "lib.pullback_observation", candidate)

    def unauthorized_read(*args):
        raise AssertionError("source must not be read before observer admitted")
    out = snapshot(now=FIXED_NOW, read=unauthorized_read)
    assert out["available"] is False
    assert out["quality"] == "observer_unavailable"
    assert out["drawdown_pct"] is None
    assert invoked == []


def test_absent_source_reader_never_autoselects_a_store(monkeypatch):
    """Model/display rights are not established by whichever local SPY parquet exists."""
    from collectors import massive_stock_day
    from lib import store
    def forbidden(*args, **kwargs):
        raise AssertionError("an unbound reader must not select a store implicitly")
    monkeypatch.setattr(store, "read", forbidden)
    monkeypatch.setattr(massive_stock_day, "load_ticker", forbidden)
    out = snapshot(now=FIXED_NOW, observer=observer_receipt)
    assert not out["available"]
    assert out["quality"] == "source_unavailable"
    assert out["drawdown_pct"] is None
