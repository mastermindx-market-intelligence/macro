"""US price-basis adapter contracts. Synthetic inputs, no network or source writes."""
from __future__ import annotations

from datetime import datetime, timezone
from math import nan
from types import SimpleNamespace

import pandas as pd
import pytest

from lib import nyse_calendar
from lib.us_pullback_observation import snapshot


FIXED_NOW = datetime(2026, 10, 9, 22, 0, tzinfo=timezone.utc)


def frame(*, with_price=True, stamps=("2026-10-08", "2026-10-09")):
    dates = pd.to_datetime(list(stamps))
    values = {"close": [91.0, 92.0][:len(dates)]}
    if with_price:
        values["close_price"] = [88.0, 89.0][:len(dates)]
    return pd.DataFrame(values, index=dates)


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


def test_uses_spy_split_adjusted_price_and_owner_calendar_not_total_return():
    seen = []
    def read(group, name):
        seen.append(("read", group, name))
        return frame()

    def observe(rows, *, expected_session, is_session):
        seen.append(("observe", tuple(rows), expected_session))
        assert is_session is nyse_calendar.is_session
        return observer_receipt(rows, expected_session=expected_session, is_session=is_session)

    out = snapshot(now=FIXED_NOW, read=read, observer=observe)
    assert seen == [
        ("read", "yahoo", "SPY"),
        ("observe", (("2026-10-08", 88.0), ("2026-10-09", 89.0)), FIXED_NOW.date()),
    ]
    assert out["market"] == "us" and out["benchmark"] == "SPY"
    assert out["benchmark_en"].startswith("S&P 500") and "标普" in out["benchmark_zh"]
    assert out["price_basis"] == "split_adjusted_dividend_unadjusted_close"
    assert out["source"] == "yahoo/SPY.close_price"
    assert out["close"] == 89.0
    assert out["source_digest"] == "a" * 64
    assert out["clock"] == "settled_close"
    assert out["valid_until"] == "2026-10-12T21:00:00+00:00"
    assert out["produced_at"] == FIXED_NOW.isoformat()


def test_missing_price_basis_abstains_and_never_uses_total_return():
    called = []
    def observer(*args, **kwargs):
        called.append(True)
        raise AssertionError("No observer call allowed when close_price is absent")
    result = snapshot(now=FIXED_NOW, read=lambda *args: frame(with_price=False),
                      observer=observer)
    assert called == []
    assert result["available"] is False
    assert result["quality"] == "source_unavailable"
    assert result["phase"] == "unavailable"
    assert result["drawdown_pct"] is None and result["close"] is None
    assert result["price_basis"] == "split_adjusted_dividend_unadjusted_close"


@pytest.mark.parametrize("failure", [None, pd.DataFrame(), ValueError("corrupt"), OSError("read failed")])
def test_missing_or_unreadable_source_fails_closed(failure):
    def read(*args):
        if isinstance(failure, Exception):
            raise failure
        return failure
    out = snapshot(now=FIXED_NOW, read=read, observer=observer_receipt)
    assert out["quality"] == "source_unavailable"
    assert out["available"] is False
    assert out["active"] is None
    assert out["drawdown_pct"] is None


def test_outdated_source_cannot_be_misrepresented_as_current():
    def delayed(rows, *, expected_session, is_session):
        assert rows[-1][0] == "2026-10-08"
        return {
            "schema": "pullback_observation.v1",
            "available": False,
            "quality": "delayed",
            "phase": "unavailable",
            "active": None,
            "asof": "2026-10-08",
            "last_observation": {"drawdown_pct": -6.8, "phase": "underway"},
            "drawdown_pct": None,
        }
    out = snapshot(now=FIXED_NOW, read=lambda *args: frame(stamps=("2026-10-07", "2026-10-08")),
                   observer=delayed)
    assert not out["available"] and out["quality"] == "delayed"
    assert out["drawdown_pct"] is None and out["phase"] == "unavailable"
    assert out["expected_session"] == "2026-10-09"


def test_intraday_timestamp_is_forwarded_intact_for_canonical_rejection():
    def observer(rows, *, expected_session, is_session):
        assert rows[0][0].startswith("2026-10-09T14:15:00")
        return {"schema": "pullback_observation.v1", "available": False,
                "quality": "invalid_session_label", "phase": "unavailable",
                "active": None, "drawdown_pct": None, "asof": None}
    out = snapshot(now=FIXED_NOW,
                   read=lambda *args: pd.DataFrame(
                       {"close_price": [89.0]},
                       index=pd.to_datetime(["2026-10-09T14:15:00"])),
                   observer=observer)
    assert not out["available"] and out["quality"] == "invalid_session_label"


@pytest.mark.parametrize("now", [datetime(2026, 10, 9, 22, 0), "2026-10-09", None])
def test_explicit_clock_must_be_aware_datetime(now):
    if now is None:
        return
    with pytest.raises(ValueError):
        snapshot(now=now, read=lambda *args: frame(), observer=observer_receipt)


def test_caller_cannot_promote_inconsistent_observer_as_current():
    def inconsistent(rows, *, expected_session, is_session):
        result = observer_receipt(rows, expected_session=expected_session, is_session=is_session)
        result["asof"] = "2026-10-08"
        return result
    out = snapshot(now=FIXED_NOW, read=lambda *args: frame(), observer=inconsistent)
    assert out["available"] is False and out["quality"] == "observation_inconsistent"
    assert out["drawdown_pct"] is None
    assert out["source_digest"] is None


def test_default_missing_observer_dependency_yields_unavailable_not_fabricated_price():
    out = snapshot(now=FIXED_NOW, read=lambda *args: frame())
    # This repository branch has not taken custody of held PR #8188's observer.
    # Once that source is merged, it may produce an observation; never infer one from a score.
    assert out["schema"] == "pullback_observation.v1"
    assert out["market"] == "us"
    assert out["price_basis"] == "split_adjusted_dividend_unadjusted_close"
    assert out["quality"] in {"observer_unavailable", "insufficient_history", "current"}

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
    obs = snapshot(now=FIXED_NOW, read=lambda *args: None, observer=observer_receipt)
    view = present(obs)
    assert view["phase"] == "unavailable"
    assert view["detail_chart_html"] == ""
    assert view["observation"]["drawdown_pct"] is None
