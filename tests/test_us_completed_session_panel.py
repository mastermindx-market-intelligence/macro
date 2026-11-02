"""US Prophet producer clock: score one completed-session cross-section."""
from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd

import scripts.build_site as build_site
import scripts.build_stock_library as stocklib
from engine.prophet_bridge import _resolve_origination_clocks


def _series(values: list[float], dates: list[str]) -> pd.Series:
    return pd.Series(values, index=pd.to_datetime(dates), dtype="float64")


def test_preclose_panel_excludes_provisional_equity_bars_but_keeps_raw_reach(monkeypatch):
    normalise = getattr(stocklib, "_normalise_us_equity_universe", None)
    assert callable(normalise), "completed-session universe normalizer is missing"
    monkeypatch.setattr(stocklib, "_crypto_tickers", lambda: frozenset({"BTC-USD"}))
    equity_close = _series([100, 101, 111], ["2026-09-11", "2026-09-14", "2026-09-15"])
    equity_high = _series([101, 102, 112], ["2026-09-11", "2026-09-14", "2026-09-15"])
    crypto_close = _series([50, 52], ["2026-09-14", "2026-09-15"])
    universe = [
        ("AAPL", equity_close, equity_high, "Apple", "Technology"),
        ("BTC-USD", crypto_close, None, "Bitcoin", "ETF / macro"),
    ]
    observed = datetime(2026, 9, 15, 15, 9, tzinfo=timezone.utc)

    clipped, reach, clock = normalise(universe, now=observed)

    by_ticker = {row[0]: row for row in clipped}
    assert by_ticker["AAPL"][1].index.max() == pd.Timestamp("2026-09-14")
    assert by_ticker["AAPL"][2].index.max() == pd.Timestamp("2026-09-14")
    assert by_ticker["BTC-USD"][1].index.max() == pd.Timestamp("2026-09-15")
    assert reach["through"] == "2026-09-14"
    assert reach["majority_through"] == "2026-09-14"
    assert reach["mixed_vintage"] is False
    assert reach["through_raw"] == "2026-09-15"
    assert clock == {
        "observed_at_utc": "2026-09-15T15:09:00+00:00",
        "completed_session": "2026-09-14",
        "raw_through": "2026-09-15",
        "provisional_member_count": 1,
        "provisional_tickers": ["AAPL"],
    }


def test_normalizer_preserves_a_genuine_completed_session_tear(monkeypatch):
    normalise = getattr(stocklib, "_normalise_us_equity_universe", None)
    assert callable(normalise), "completed-session universe normalizer is missing"
    monkeypatch.setattr(stocklib, "_crypto_tickers", lambda: frozenset())
    friday = _series([10], ["2026-09-11"])
    monday = _series([10, 11], ["2026-09-11", "2026-09-14"])
    universe = [
        (ticker, friday, None, ticker, "Industrials")
        for ticker in ("OLD1", "OLD2", "OLD3")
    ] + [
        (ticker, monday, None, ticker, "Industrials")
        for ticker in ("NEW1", "NEW2")
    ]

    _, reach, _ = normalise(
        universe,
        now=datetime(2026, 9, 15, 15, 9, tzinfo=timezone.utc),
    )

    assert reach["through"] == "2026-09-14"
    assert reach["majority_through"] == "2026-09-11"
    assert reach["mixed_vintage"] is True
    assert reach["off_majority_tickers"] == ["NEW1", "NEW2"]


def test_preclose_observation_clock_accepts_the_prior_completed_session():
    recorded_at, price_basis_date, errors = _resolve_origination_clocks(
        price_through="2026-09-14",
        recorded_asof="2026-09-15T15:09:00+00:00",
        panel_mixed_vintage=False,
        source_delayed=False,
        source_unknown=False,
        source_basis="panel_majority",
    )

    assert errors == []
    assert recorded_at == "2026-09-15"
    assert price_basis_date == "2026-09-14"


def test_after_close_observation_clock_rejects_a_prior_session_board():
    _, _, errors = _resolve_origination_clocks(
        price_through="2026-09-14",
        recorded_asof="2026-09-15T22:00:00+00:00",
        panel_mixed_vintage=False,
        source_delayed=False,
        source_unknown=False,
        source_basis="panel_majority",
    )

    assert any("stale boards cannot originate plans" in error for error in errors)


def test_staleness_receipt_binds_the_observation_clock(tmp_path):
    observed = datetime(2026, 9, 15, 15, 9, tzinfo=timezone.utc)
    result = stocklib._compute_board_staleness(
        ohlcv_dir=tmp_path / "absent",
        now=observed,
        panel_reach={
            "through": "2026-09-14",
            "through_raw": "2026-09-15",
            "majority_through": "2026-09-14",
            "members_at_through": 2,
            "members_total": 2,
            "mixed_vintage": False,
            "off_majority_tickers": [],
        },
        board_asof="2026-09-14",
    )
    assert result.get("observed_at_utc") == "2026-09-15T15:09:00+00:00"
    assert result.get("expected_session") == "2026-09-14"
    assert result["max_through"] == "2026-09-15"


def test_main_applies_one_clock_before_us_scoring_and_staleness():
    import inspect

    source = inspect.getsource(stocklib.main)
    observed = source.index("_board_observed_at = now or datetime.now(timezone.utc)")
    benchmark = source.index("_clip_daily_to_completed_session(spy[\"close\"]")
    normalise = source.index("_normalise_us_equity_universe")
    extension = source.index("_ext_closes =")
    worker = source.index("_winit(")
    staleness = source.index("panel_reach=_panel_reach")

    assert observed < benchmark < normalise < extension < worker < staleness
    assert "now=_board_observed_at" in source
    assert "_raw_ohlcv = store.read(\"stocks\", ticker)" in source
    assert "_clip_daily_to_completed_session(_raw_ohlcv, _completed_session)" in source


def test_alpha_builder_uses_the_shared_completed_session(monkeypatch, tmp_path):
    seen: dict[str, object] = {}

    def fake_compute_residual_alpha(*, asof=None):
        seen["asof"] = asof
        return {
            "as_of": str(asof),
            "n": 1,
            "by_sector": {},
            "top": [],
            "per_ticker": {},
        }

    monkeypatch.setattr(
        "engine.residual_alpha.compute_residual_alpha",
        fake_compute_residual_alpha,
    )

    result = build_site.build_alpha_data(tmp_path, asof="2026-09-14")

    assert seen == {"asof": "2026-09-14"}
    assert result is not None
    assert result["as_of"] == "2026-09-14"


def test_build_site_shares_one_clock_with_alpha_and_stock_library():
    import inspect

    source = inspect.getsource(build_site.main)
    observed = source.index("_us_board_observed_at = datetime.now(timezone.utc)")
    completed = source.index("_us_completed_session =")
    alpha = source.index("build_alpha_data(site, asof=_us_completed_session)")
    library = source.index("build_library(now=_us_board_observed_at)")

    assert observed < completed < alpha < library


def test_staleness_calendar_failure_fails_closed(monkeypatch, tmp_path):
    from lib import nyse_calendar

    def broken_calendar(_now):
        raise RuntimeError("calendar unavailable")

    monkeypatch.setattr(nyse_calendar, "expected_last_session", broken_calendar)

    result = stocklib._compute_board_staleness(
        ohlcv_dir=tmp_path / "absent",
        now=datetime(2026, 9, 15, 15, 9, tzinfo=timezone.utc),
        panel_reach=None,
        board_asof="2026-09-14",
    )

    assert result["delayed"] is True
    assert result["unknown"] is True
    assert result["expected_session"] is None
    assert result["unknown_reason"] == "error:RuntimeError"
