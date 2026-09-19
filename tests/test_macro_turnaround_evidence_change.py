from __future__ import annotations

from datetime import date, timedelta
import math

import pandas as pd
import pytest

from engine import macro_turnaround_replay as replay_api


def _row(period: date, start: date, end: date, value: float) -> replay_api.VintageRow:
    return replay_api.VintageRow("PPIFIS", period, start, end, value)


def _binding() -> replay_api.SeriesBinding:
    return replay_api.SeriesBinding(
        "ppi_final_demand",
        "PPIFIS",
        "inflation",
        transform="pct_change",
    )


def _frame(*, flat: bool = False) -> pd.DataFrame:
    rows = []
    year, month = 2018, 1
    for index in range(48):
        period = date(year, month, 1)
        value = 100.0 if flat else 100.0 + 0.15 * index + math.sin(index * 0.37)
        rows.append(
            {
                "series": "PPIFIS",
                "period": pd.Timestamp(period),
                "realtime_start": pd.Timestamp(period + timedelta(days=35)),
                "realtime_end": date(2022, 3, 14),
                "value": value,
                "source_output_type": 2,
            }
        )
        month += 1
        if month == 13:
            year += 1
            month = 1
    return pd.DataFrame(rows)


def _with_second_snapshot(frame: pd.DataFrame, *, revise: bool, flat: bool = False) -> pd.DataFrame:
    second = frame.copy()
    second["realtime_start"] = pd.Timestamp("2022-03-15")
    second["realtime_end"] = date.max
    if revise:
        second.loc[10, "value"] = float(second.loc[10, "value"]) + 0.5
    new = {
        "series": "PPIFIS",
        "period": pd.Timestamp("2022-01-01"),
        "realtime_start": pd.Timestamp("2022-03-15"),
        "realtime_end": date.max,
        "value": 100.0 if flat else 108.0,
        "source_output_type": 2,
    }
    return pd.concat([frame, second, pd.DataFrame([new])], ignore_index=True)


def test_same_value_vintage_refresh_separates_numeric_values_from_source_identity() -> None:
    frame = _frame()
    second = frame.copy()
    second["realtime_start"] = pd.Timestamp("2022-03-15")
    second["realtime_end"] = date.max
    report = replay_api.replay(
        replay_api.prepare_panel({"PPIFIS": pd.concat([frame, second], ignore_index=True)}),
        [_binding()],
        ["2022-02-10", "2022-03-15"],
        domain="inflation",
    )
    change = report["rows"][1]["evidence_change"]
    series = change["series"]["ppi_final_demand"]

    assert series["counts"]["vintage_refreshed"] == 48
    assert series["counts"]["revised_value"] == 0
    assert series["events"] == []
    assert series["active_values_unchanged"] is True
    assert series["source_identity_unchanged"] is False
    assert change["active_values_unchanged"] is True
    assert change["source_identity_unchanged"] is False
    assert change["causal_score_attribution_established"] is False
    assert change["is_forecast"] is False


def test_revision_new_period_and_refresh_have_disjoint_counts() -> None:
    report = replay_api.replay(
        replay_api.prepare_panel({"PPIFIS": _with_second_snapshot(_frame(), revise=True)}),
        [_binding()],
        ["2022-02-10", "2022-03-15"],
        domain="inflation",
    )
    change = report["rows"][1]["evidence_change"]
    series = change["series"]["ppi_final_demand"]

    assert series["counts"] == {
        "new_period": 1,
        "historical_period_added": 0,
        "restored_period": 0,
        "initial_availability": 0,
        "revised_value": 1,
        "withdrawn_period": 0,
        "vintage_refreshed": 47,
        "unchanged_period": 0,
    }
    assert [event["kind"] for event in series["events"]] == ["revised_value", "new_period"]
    assert series["active_values_unchanged"] is False
    assert change["active_values_unchanged"] is False
    assert change["count_unit"] == "source_periods_not_independent_economic_confirmations"


def test_all_change_kinds_are_classified_without_calling_them_causal() -> None:
    jan, feb, mar, apr = (date(2020, month, 1) for month in range(1, 5))
    before = replay_api._ActiveSelection(
        "PPIFIS",
        (
            _row(jan, date(2020, 2, 1), date.max, 1.0),
            _row(mar, date(2020, 4, 1), date.max, 3.0),
        ),
        frozenset({jan, feb, mar}),
        "incomplete_active_monthly_history",
    )
    after = replay_api._ActiveSelection(
        "PPIFIS",
        (
            _row(date(2019, 12, 1), date(2020, 5, 1), date.max, 0.0),
            _row(feb, date(2020, 5, 1), date.max, 2.0),
            _row(mar, date(2020, 5, 1), date.max, 3.0),
            _row(apr, date(2020, 5, 1), date.max, 4.0),
        ),
        frozenset({date(2019, 12, 1), jan, feb, mar, apr}),
        None,
    )
    change = replay_api._series_change(before, after)

    assert change["counts"]["withdrawn_period"] == 1
    assert change["counts"]["restored_period"] == 1
    assert change["counts"]["historical_period_added"] == 1
    assert change["counts"]["new_period"] == 1
    assert change["counts"]["vintage_refreshed"] == 1
    assert {event["kind"] for event in change["events"]} == {
        "withdrawn_period",
        "restored_period",
        "historical_period_added",
        "new_period",
    }
    assert change["input_status_semantics"] == "active_vintage_selection_not_model_usability"


def test_unavailable_scores_are_not_reemitted_as_numeric_deltas() -> None:
    report = replay_api.replay(
        replay_api.prepare_panel(
            {"PPIFIS": _with_second_snapshot(_frame(flat=True), revise=False, flat=True)}
        ),
        [_binding()],
        ["2022-02-10", "2022-03-15"],
        domain="inflation",
    )
    assessment = report["rows"][1]["evidence_change"]["assessment_change"]

    assert assessment["previous_score_status"] == "unavailable"
    assert assessment["score_status"] == "unavailable"
    for direction in ("upturn", "downturn"):
        assert assessment["raw_scores"][direction] == {
            "before": None,
            "after": None,
            "delta": None,
            "status": "not_comparable_unavailable_score",
        }


def test_evidence_change_and_replay_hash_are_order_deterministic() -> None:
    frame = _with_second_snapshot(_frame(), revise=True)
    left = replay_api.replay(
        replay_api.prepare_panel({"PPIFIS": frame}),
        [_binding()],
        ["2022-02-10", "2022-03-15"],
        domain="inflation",
    )
    right = replay_api.replay(
        replay_api.prepare_panel({"PPIFIS": frame.sample(frac=1, random_state=17)}),
        [_binding()],
        ["2022-03-15", "2022-02-10"],
        domain="inflation",
    )

    assert right == left
    assert right["replay_hash"] == left["replay_hash"]
    assert all(row["evidence_change"]["causal_score_attribution_established"] is False for row in left["rows"])
    assert all(row["evidence_change"]["is_forecast"] is False for row in left["rows"])
