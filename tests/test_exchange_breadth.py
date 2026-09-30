"""Pure XNYS breadth core contracts.

These tests pin the semantics before any collector or dashboard wiring exists:
point-in-time XNYS cohorts, incumbent identity precedence, gap-honest membership
intervals, point-in-time split normalization, ticker-rename/reuse safety, and
prior-252 (current-session excluded) new-high/new-low breadth.
"""
from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd
import pytest

from engine import exchange_breadth as eb


class _AliasTable:
    def __init__(self, mapping: dict[tuple[str, str], str]):
        self.mapping = mapping
        self.calls: list[tuple[str, str, date]] = []

    def resolve(self, vendor: str, vendor_symbol: str, on: date) -> str | None:
        self.calls.append((vendor, vendor_symbol, on))
        return self.mapping.get((vendor, vendor_symbol))


def _row(
    ticker: str,
    ticker_type: str = "CS",
    *,
    exchange: str = "XNYS",
    market: str = "stocks",
    active: bool = True,
    share_figi: str | None = None,
    composite_figi: str | None = None,
) -> dict:
    return {
        "ticker": ticker,
        "name": f"{ticker} Incorporated",
        "market": market,
        "primary_exchange": exchange,
        "active": active,
        "type": ticker_type,
        "currency_name": "usd",
        "share_class_figi": share_figi,
        "composite_figi": composite_figi,
    }


def _observed(
    session: str,
    rows: list[tuple[str, str, str, str]],
) -> pd.DataFrame:
    """(universe, entity, ticker, type) -> normalized resolved observations."""
    return pd.DataFrame(
        [
            {
                "session": pd.Timestamp(session),
                "universe_key": universe,
                "entity_key": entity,
                "security_id": entity if entity.startswith("SEC:") else None,
                "share_class_figi": entity.removeprefix("FIGI:") if entity.startswith("FIGI:") else None,
                "composite_figi": None,
                "ticker": ticker,
                "name": ticker,
                "ticker_type": ticker_type,
                "primary_exchange": "XNYS",
                "currency": "usd",
                "identity_source": "fixture",
                "identity_resolved": True,
            }
            for universe, entity, ticker, ticker_type in rows
        ]
    )


def test_normalize_roster_splits_operating_and_all_issues_and_filters_non_xnys():
    aliases = _AliasTable({("massive", "IBM"): "SEC:IBM"})
    rows = [
        _row("IBM", "CS", share_figi="BBG000BLNNH6", composite_figi="BBG000BLNNH6"),
        _row("BABA", "ADRC", share_figi="BBG006G2JVL2", composite_figi="BBG006G2JVL2"),
        _row("SPY", "ETF", composite_figi="BBG000BDTBL9"),
        _row("AMEX", "CS", exchange="XASE", share_figi="BBG000AMEX00"),
        _row("DEAD", "CS", active=False, share_figi="BBG000DEAD00"),
        _row("BTCUSD", "CS", market="crypto", share_figi="BBG000BTC000"),
    ]

    out = eb.normalize_roster(rows, "2026-09-28", alias_table=aliases)

    operating = out[out["universe_key"] == eb.UNIVERSE_OPERATING]
    all_issues = out[out["universe_key"] == eb.UNIVERSE_ALL_ISSUES]
    assert operating["ticker"].tolist() == ["BABA", "IBM"]
    assert all_issues["ticker"].tolist() == ["BABA", "IBM", "SPY"]
    assert set(out["primary_exchange"]) == {"XNYS"}
    assert set(out["session"]) == {pd.Timestamp("2026-09-28")}

    by_ticker = all_issues.set_index("ticker")
    assert by_ticker.loc["IBM", "entity_key"] == "SEC:IBM"
    assert by_ticker.loc["IBM", "identity_source"] == "security_id"
    assert by_ticker.loc["BABA", "entity_key"] == "FIGI:BBG006G2JVL2"
    assert by_ticker.loc["BABA", "identity_source"] == "share_class_figi"
    assert by_ticker.loc["SPY", "entity_key"] == "CFIGI:BBG000BDTBL9"
    assert aliases.calls[0] == ("massive", "IBM", date(2026, 9, 28))


def test_identity_precedence_and_unresolved_rows_are_explicit():
    aliases = _AliasTable({("membership", "CANON"): "SEC:CANON"})
    rows = [
        _row("CANON", share_figi="SHARE1", composite_figi="COMP1"),
        _row("SHARE", share_figi="SHARE2", composite_figi="COMP2"),
        _row("COMP", composite_figi="COMP3"),
        _row("NONE"),
    ]

    out = eb.normalize_roster(rows, pd.Timestamp("2026-09-28"), alias_table=aliases)
    all_issues = out[out["universe_key"] == eb.UNIVERSE_ALL_ISSUES].set_index("ticker")

    assert all_issues.loc["CANON", "entity_key"] == "SEC:CANON"
    assert all_issues.loc["SHARE", "entity_key"] == "FIGI:SHARE2"
    assert all_issues.loc["COMP", "entity_key"] == "CFIGI:COMP3"
    assert pd.isna(all_issues.loc["NONE", "entity_key"])
    assert all_issues.loc["NONE", "identity_source"] == "unresolved"
    assert bool(all_issues.loc["NONE", "identity_resolved"]) is False


def test_membership_intervals_extend_only_across_confirmed_consecutive_sessions():
    day1 = _observed(
        "2026-09-25",
        [
            (eb.UNIVERSE_OPERATING, "SEC:AAA", "AAA", "CS"),
            (eb.UNIVERSE_OPERATING, "SEC:BBB", "BBB", "CS"),
        ],
    )
    first = eb.update_membership_intervals(
        pd.DataFrame(columns=eb.INTERVAL_COLUMNS),
        day1,
        "2026-09-25",
        previous_session=None,
        last_observed_session=None,
    )

    day2 = _observed(
        "2026-09-28",
        [
            (eb.UNIVERSE_OPERATING, "SEC:AAA", "AAA", "CS"),
            (eb.UNIVERSE_OPERATING, "SEC:CCC", "CCC", "CS"),
        ],
    )
    second = eb.update_membership_intervals(
        first,
        day2,
        "2026-09-28",
        previous_session="2026-09-25",
        last_observed_session="2026-09-25",
    )

    aaa = second[second["entity_key"] == "SEC:AAA"]
    bbb = second[second["entity_key"] == "SEC:BBB"]
    ccc = second[second["entity_key"] == "SEC:CCC"]
    assert len(aaa) == 1
    assert aaa.iloc[0]["valid_from_session"] == pd.Timestamp("2026-09-25")
    assert aaa.iloc[0]["valid_to_session"] == pd.Timestamp("2026-09-28")
    assert bbb.iloc[0]["valid_to_session"] == pd.Timestamp("2026-09-25")
    assert ccc.iloc[0]["valid_from_session"] == pd.Timestamp("2026-09-28")

    # Missing the canonical prior session makes continuity unprovable: reopen,
    # never bridge the gap even when the same entity/ticker appears again.
    day3 = _observed(
        "2026-09-30",
        [(eb.UNIVERSE_OPERATING, "SEC:AAA", "AAA", "CS")],
    )
    third = eb.update_membership_intervals(
        second,
        day3,
        "2026-09-30",
        previous_session="2026-09-29",
        last_observed_session="2026-09-28",
    )
    aaa = third[third["entity_key"] == "SEC:AAA"].sort_values("valid_from_session")
    assert len(aaa) == 2
    assert aaa.iloc[0]["valid_to_session"] == pd.Timestamp("2026-09-28")
    assert aaa.iloc[1]["valid_from_session"] == pd.Timestamp("2026-09-30")


def test_ticker_rename_opens_a_new_interval_without_changing_entity_identity():
    first = eb.update_membership_intervals(
        pd.DataFrame(columns=eb.INTERVAL_COLUMNS),
        _observed("2026-09-25", [(eb.UNIVERSE_OPERATING, "SEC:SAME", "OLD", "CS")]),
        "2026-09-25",
        previous_session=None,
        last_observed_session=None,
    )
    second = eb.update_membership_intervals(
        first,
        _observed("2026-09-28", [(eb.UNIVERSE_OPERATING, "SEC:SAME", "NEW", "CS")]),
        "2026-09-28",
        previous_session="2026-09-25",
        last_observed_session="2026-09-25",
    )

    rows = second.sort_values("valid_from_session")
    assert rows["entity_key"].tolist() == ["SEC:SAME", "SEC:SAME"]
    assert rows["ticker"].tolist() == ["OLD", "NEW"]
    assert rows.iloc[0]["valid_to_session"] == pd.Timestamp("2026-09-25")
    assert rows.iloc[1]["valid_from_session"] == pd.Timestamp("2026-09-28")


@pytest.mark.parametrize(
    ("split_from", "split_to", "raw_pre", "raw_execution", "expected_pre", "adjustment_type"),
    [
        (1.0, 4.0, 100.0, 26.0, 25.0, "forward_split"),
        (10.0, 1.0, 10.0, 102.0, 100.0, "reverse_split"),
        (4.0, 5.0, 100.0, 81.0, 80.0, "stock_dividend"),
    ],
)
def test_split_adjustment_restates_only_pre_event_bars(
    split_from, split_to, raw_pre, raw_execution, expected_pre, adjustment_type
):
    idx = pd.to_datetime(["2026-01-02", "2026-01-05", "2026-01-06"])
    raw = pd.Series([raw_pre, raw_execution, raw_execution + 1], index=idx, name="E1")
    events = pd.DataFrame(
        [
            {
                "entity_key": "E1",
                "execution_date": pd.Timestamp("2026-01-05"),
                "split_from": split_from,
                "split_to": split_to,
                "adjustment_type": adjustment_type,
            }
        ]
    )

    adjusted = eb.adjust_raw_close_series(raw, events, "2026-01-06")

    assert adjusted.loc["2026-01-02"] == pytest.approx(expected_pre)
    assert adjusted.loc["2026-01-05"] == pytest.approx(raw_execution)
    assert adjusted.loc["2026-01-06"] == pytest.approx(raw_execution + 1)


def test_future_split_never_enters_a_historical_observation():
    idx = pd.to_datetime(["2026-01-02", "2026-01-05", "2026-01-06"])
    raw = pd.Series([100.0, 102.0, 104.0], index=idx)
    events = pd.DataFrame(
        [{"execution_date": "2026-02-02", "split_from": 1, "split_to": 4}]
    )

    adjusted = eb.adjust_raw_close_series(raw, events, "2026-01-06")
    pd.testing.assert_series_equal(adjusted, raw, check_freq=False)


def test_unmatched_split_like_seam_is_disclosed_but_adjusted_series_is_clean():
    idx = pd.to_datetime(["2026-01-02", "2026-01-05", "2026-01-06"])
    raw = pd.Series([100.0, 102.0, 25.5], index=idx)
    assert eb.find_split_like_seams(raw) == [pd.Timestamp("2026-01-06")]

    events = pd.DataFrame(
        [{"execution_date": "2026-01-06", "split_from": 1, "split_to": 4}]
    )
    adjusted = eb.adjust_raw_close_series(raw, events, "2026-01-06")
    assert eb.find_split_like_seams(adjusted) == []


def test_entity_panel_preserves_rename_and_separates_ticker_reuse():
    idx = pd.bdate_range("2026-01-05", periods=6)
    prices = {
        "OLD": pd.Series([10, 11, 12, 50, 51, 52], index=idx, dtype=float),
        "NEW": pd.Series([np.nan, np.nan, np.nan, 13, 14, 15], index=idx, dtype=float),
    }
    intervals = pd.DataFrame(
        [
            {
                "universe_key": eb.UNIVERSE_OPERATING,
                "entity_key": "E1",
                "ticker": "OLD",
                "valid_from_session": idx[0],
                "valid_to_session": idx[2],
            },
            {
                "universe_key": eb.UNIVERSE_OPERATING,
                "entity_key": "E1",
                "ticker": "NEW",
                "valid_from_session": idx[3],
                "valid_to_session": idx[5],
            },
            {
                "universe_key": eb.UNIVERSE_OPERATING,
                "entity_key": "E2",
                "ticker": "OLD",
                "valid_from_session": idx[3],
                "valid_to_session": idx[5],
            },
        ]
    )

    result = eb.assemble_entity_close_panel(
        prices,
        intervals,
        split_events=pd.DataFrame(),
        observation_session=idx[-1],
        universe_key=eb.UNIVERSE_OPERATING,
    )

    assert result.excluded_entities == {}
    assert result.closes["E1"].tolist() == [10, 11, 12, 13, 14, 15]
    assert result.closes["E2"].iloc[:3].isna().all()
    assert result.closes["E2"].iloc[3:].tolist() == [50, 51, 52]


def test_entity_panel_excludes_an_unmatched_split_like_seam():
    idx = pd.bdate_range("2026-01-05", periods=4)
    prices = {"AAA": pd.Series([100, 102, 103, 25], index=idx, dtype=float)}
    intervals = pd.DataFrame(
        [
            {
                "universe_key": eb.UNIVERSE_OPERATING,
                "entity_key": "E1",
                "ticker": "AAA",
                "valid_from_session": idx[0],
                "valid_to_session": idx[-1],
            }
        ]
    )

    result = eb.assemble_entity_close_panel(
        prices,
        intervals,
        split_events=pd.DataFrame(),
        observation_session=idx[-1],
        universe_key=eb.UNIVERSE_OPERATING,
    )

    assert "E1" not in result.closes.columns
    assert result.excluded_entities["E1"]["reason"] == "unmatched_split_like_seam"
    assert result.excluded_entities["E1"]["dates"] == ["2026-01-08"]


def test_new_high_low_requires_252_prior_closes_and_excludes_young_issues():
    idx = pd.bdate_range("2025-01-02", periods=253)
    closes = pd.DataFrame(
        {
            "seasoned": np.arange(1.0, 254.0),
            "young": [np.nan] * 153 + list(np.arange(1.0, 101.0)),
        },
        index=idx,
    )
    membership = closes.notna()

    out = eb.compute_breadth_history(
        closes,
        membership=membership,
        listed_counts=pd.Series(2, index=idx),
        nhnl_window=252,
    )

    assert out.iloc[-2]["seasoned_n"] == 0
    assert out.iloc[-2]["nh"] == 0
    assert out.iloc[-1]["seasoned_n"] == 1
    assert out.iloc[-1]["nh"] == 1
    assert out.iloc[-1]["nl"] == 0
    assert out.iloc[-1]["nh_pct"] == pytest.approx(100.0)
    assert out.iloc[-1]["seasoned_pct"] == pytest.approx(50.0)


def test_flat_series_can_be_both_a_new_high_and_new_low():
    idx = pd.bdate_range("2026-01-05", periods=4)
    closes = pd.DataFrame({"flat": [10.0, 10.0, 10.0, 10.0]}, index=idx)

    out = eb.compute_breadth_history(closes, nhnl_window=3, ma_windows=(2, 3))
    last = out.iloc[-1]

    assert last["seasoned_n"] == 1
    assert last["nh"] == 1
    assert last["nl"] == 1
    assert last["both_extremes"] == 1
    assert last["net_nh"] == 0
    assert last["high_low_index"] == pytest.approx(50.0)


def test_missing_prior_price_is_not_silently_counted_as_unchanged():
    idx = pd.bdate_range("2026-01-05", periods=3)
    closes = pd.DataFrame(
        {
            "advancer": [10.0, 10.0, 11.0],
            "missing_prior": [20.0, np.nan, 20.0],
            "unchanged": [30.0, 30.0, 30.0],
        },
        index=idx,
    )
    listed = pd.Series([5, 5, 5], index=idx)

    out = eb.compute_breadth_history(
        closes,
        membership=closes.notna(),
        listed_counts=listed,
        nhnl_window=2,
        ma_windows=(2,),
    )
    last = out.iloc[-1]

    assert last["listed_n"] == 5
    assert last["priced_n"] == 3
    assert last["coverage_pct"] == pytest.approx(60.0)
    assert last["adv"] == 1
    assert last["dec"] == 0
    assert last["unch"] == 1
    assert last["adv_pct"] == pytest.approx(100.0)
    assert last["pct_above_2"] == pytest.approx(50.0)


def test_state_classification_is_causal_at_requested_asof():
    idx = pd.bdate_range("2026-01-05", periods=30)
    frame = pd.DataFrame(
        {
            "adv_pct": [58.0] * 25 + [20.0] * 5,
            "pct_above_50": list(np.linspace(50, 70, 25)) + [20.0] * 5,
            "net_nh_pct": [2.5] * 25 + [-12.0] * 5,
            "nh_pct": [3.0] * 25 + [0.2] * 5,
            "nl_pct": [0.5] * 25 + [12.0] * 5,
        },
        index=idx,
    )
    price = pd.Series(list(np.linspace(100, 120, 25)) + [110, 100, 95, 90, 85], index=idx)

    at_day_25 = eb.classify_breadth_state(frame, price=price, asof=idx[24], lookback=5)
    truncated = eb.classify_breadth_state(frame.iloc[:25], price=price.iloc[:25], lookback=5)

    assert at_day_25 == truncated
    assert at_day_25["state"] == "broad_confirmation"
    assert at_day_25["authority"] == "display_research_context_only"
    assert at_day_25["reasons"]


def test_normalize_roster_keeps_massive_case_as_security_identity() -> None:
    aliases = _AliasTable(
        {
            ("massive", "TPC"): "SEC:TUTOR-PERINI",
            ("massive", "TpC"): "SEC:ATT-PREFERRED-C",
        }
    )
    rows = [
        _row("TPC", "CS"),
        _row("TpC", "PFD"),
    ]

    out = eb.normalize_roster(rows, "2026-09-29", alias_table=aliases)
    operating = out[out["universe_key"] == eb.UNIVERSE_OPERATING]
    all_issues = out[out["universe_key"] == eb.UNIVERSE_ALL_ISSUES]

    assert operating["ticker"].tolist() == ["TPC"]
    assert all_issues["ticker"].tolist() == ["TPC", "TpC"]
    assert all_issues.set_index("ticker").loc["TPC", "entity_key"] == "SEC:TUTOR-PERINI"
    assert all_issues.set_index("ticker").loc["TpC", "entity_key"] == "SEC:ATT-PREFERRED-C"
    assert ("massive", "TPC", date(2026, 9, 29)) in aliases.calls
    assert ("massive", "TpC", date(2026, 9, 29)) in aliases.calls
