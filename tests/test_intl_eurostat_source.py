"""Focused tests for the strict Eurostat JSON-stat parser.

These tests exercise ``lib/intl_eurostat_source.py`` only.  They make no
claim about the repository suite, protected CI or publication: every fixture
below is built in this file, and the only facts quoted from the commission are
the two dataset update stamps and the two latest observation values (the rest
of the series are placeholders that preserve the real payload's shape).
"""

from __future__ import annotations

import copy
import itertools
import math
from typing import Any

import pytest

from lib.intl_eurostat_source import (
    EurostatPayloadError,
    SUPPORTED_SERIES,
    parse_eurostat_series,
)

GDP = "NAMQ_10_GDP"
HICP = "PRC_HICP_MINR"

GDP_SELECTORS = {
    "freq": "Q",
    "unit": "CLV_PCH_SM",
    "s_adj": "SCA",
    "na_item": "B1GQ",
    "geo": "EA21",
}
HICP_SELECTORS = {
    "freq": "M",
    "unit": "RCH_A",
    "coicop18": "TOTAL",
    "geo": "EA21",
}

GDP_UPDATED = "2026-10-30T23:00:00+0100"
HICP_UPDATED = "2026-10-16T23:00:00+0200"

GDP_AXES = ["freq", "unit", "s_adj", "na_item", "geo", "time"]
HICP_AXES = ["freq", "unit", "coicop18", "geo", "time"]

GDP_TIME_LABELS = [
    "2024-Q1",
    "2024-Q2",
    "2024-Q3",
    "2024-Q4",
    "2025-Q1",
    "2025-Q2",
    "2025-Q3",
    "2025-Q4",
    "2026-Q1",
    "2026-Q2",
    "2026-Q3",
]
# Only the final point (1.3) is quoted from the commission; the earlier
# points are placeholders that keep the eleven-row 2024-Q1 -> 2026-Q3 shape.
GDP_VALUES = [0.4, 0.6, 0.9, 1.1, 0.8, 1.0, 1.2, 1.1, 0.9, 1.2, 1.3]


def _month_labels(start_year: int, start_month: int, count: int) -> list[str]:
    labels: list[str] = []
    year, month = start_year, start_month
    for _ in range(count):
        labels.append(f"{year}-{month:02d}")
        month += 1
        if month == 13:
            year, month = year + 1, 1
    return labels


HICP_TIME_LABELS = _month_labels(2024, 1, 33)  # 2024-01 .. 2026-09
HICP_VALUES = [round(2.0 + 0.05 * index, 2) for index in range(len(HICP_TIME_LABELS))]
HICP_VALUES[-1] = 3.8

# 555 categories, TOTAL deliberately NOT at position 0.
COICOP18_LABELS = [f"CP{index:03d}" for index in range(552)] + [
    "TOTAL",
    "CP552",
    "CP553",
]
TOTAL_POSITION = COICOP18_LABELS.index("TOTAL")
assert TOTAL_POSITION == 552 and len(COICOP18_LABELS) == 555


def _payload(
    *,
    dataset: str,
    axes: list[str],
    labels: dict[str, list[str]],
    selected: dict[str, str],
    cells: dict[str, tuple[Any, str | None]],
    extra_cells: tuple[tuple[dict[str, str], str, Any], ...] = (),
    value_form: str = "object",
    status_form: str = "object",
    index_form: str = "object",
    updated: str | None = None,
    top_level_updated: str | None = None,
    source: str = "ESTAT",
    extension_id: str | None = None,
    sizes: dict[str, int] | None = None,
) -> dict[str, Any]:
    """Build a JSON-stat 2.0 payload in the shape Eurostat returns.

    ``cells`` holds the SELECTED slice (one value/flag per time label);
    ``extra_cells`` places distractor cells in other categories so a
    collapsing decoder cannot pass by accident.
    """
    sizes = sizes or {axis: len(labels[axis]) for axis in axes}
    strides: dict[str, int] = {}
    stride = 1
    for axis in reversed(axes):
        strides[axis] = stride
        stride *= sizes[axis]
    total_cells = stride

    def flat_of(axis_positions: dict[str, int]) -> int:
        return sum(axis_positions[axis] * strides[axis] for axis in axes)

    value_cells: dict[int, Any] = {}
    status_cells: dict[int, str] = {}
    for time_label, (value, flag) in cells.items():
        axis_positions = {
            axis: labels[axis].index(selected[axis]) for axis in axes if axis != "time"
        }
        axis_positions["time"] = labels["time"].index(time_label)
        flat = flat_of(axis_positions)
        value_cells[flat] = value
        if flag is not None:
            status_cells[flat] = flag
    for positions_by_code, time_label, value in extra_cells:
        axis_positions = {
            axis: labels[axis].index(code) for axis, code in positions_by_code.items()
        }
        axis_positions["time"] = labels["time"].index(time_label)
        value_cells[flat_of(axis_positions)] = value

    if value_form == "object":
        value_payload: Any = {
            str(flat): value for flat, value in sorted(value_cells.items())
        }
    else:
        dense: list[Any] = [None] * total_cells
        for flat, value in value_cells.items():
            dense[flat] = value
        value_payload = dense

    if status_cells:
        if status_form == "object":
            status_payload: Any = {
                str(flat): flag for flat, flag in sorted(status_cells.items())
            }
        else:
            dense_status: list[Any] = [None] * total_cells
            for flat, flag in status_cells.items():
                dense_status[flat] = flag
            status_payload = dense_status
    else:
        status_payload = None

    if index_form == "object":
        index_body: Any = {
            axis: {
                "label": axis,
                "category": {
                    "index": {
                        label: position
                        for position, label in enumerate(labels[axis])
                    }
                },
            }
            for axis in axes
        }
    else:
        index_body = {
            axis: {
                "label": axis,
                "category": {"index": list(labels[axis])},
            }
            for axis in axes
        }

    stamp = updated if updated is not None else "2026-01-01T00:00:00+0000"
    payload: dict[str, Any] = {
        "version": "2.0",
        "class": "dataset",
        "label": dataset,
        "source": source,
        "updated": top_level_updated if top_level_updated is not None else stamp,
        "extension": {
            "id": extension_id if extension_id is not None else dataset,
            "label": dataset,
            "updated": stamp,
        },
        "id": list(axes),
        "size": [sizes[axis] for axis in axes],
        "dimension": index_body,
        "value": value_payload,
    }
    if status_payload is not None:
        payload["status"] = status_payload
    return payload


def _gdp_labels() -> dict[str, list[str]]:
    return {
        "freq": ["Q"],
        "unit": ["CLV_PCH_SM"],
        "s_adj": ["SCA"],
        "na_item": ["B1GQ"],
        "geo": ["EA21"],
        "time": list(GDP_TIME_LABELS),
    }


def _gdp_cells() -> dict[str, tuple[Any, str | None]]:
    cells: dict[str, tuple[Any, str | None]] = {}
    for label, value in zip(GDP_TIME_LABELS, GDP_VALUES):
        cells[label] = (value, None)
    return cells


def _gdp_payload(**overrides: Any) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "dataset": GDP,
        "axes": list(GDP_AXES),
        "labels": _gdp_labels(),
        "selected": dict(GDP_SELECTORS),
        "cells": _gdp_cells(),
        "updated": GDP_UPDATED,
    }
    kwargs.update(overrides)
    return _payload(**kwargs)


def _hicp_labels() -> dict[str, list[str]]:
    return {
        "freq": ["M"],
        "unit": ["RCH_A"],
        "coicop18": list(COICOP18_LABELS),
        "geo": ["EA21"],
        "time": list(HICP_TIME_LABELS),
    }


def _hicp_cells() -> dict[str, tuple[Any, str | None]]:
    cells: dict[str, tuple[Any, str | None]] = {}
    for index, (label, value) in enumerate(zip(HICP_TIME_LABELS, HICP_VALUES)):
        cells[label] = (value, "p" if index == len(HICP_TIME_LABELS) - 2 else None)
    return cells


def _hicp_payload(**overrides: Any) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "dataset": HICP,
        "axes": list(HICP_AXES),
        "labels": _hicp_labels(),
        "selected": dict(HICP_SELECTORS),
        "cells": _hicp_cells(),
        "updated": HICP_UPDATED,
        "extra_cells": tuple(
            (
                {"coicop18": code, "freq": "M", "unit": "RCH_A", "geo": "EA21"},
                time_label,
                value,
            )
            for code, value in (("CP000", 88.8), ("CP003", 99.9), ("CP553", 77.7))
            for time_label in HICP_TIME_LABELS
        ),
    }
    kwargs.update(overrides)
    return _payload(**kwargs)


def _parse(payload: dict[str, Any], dataset: str, selectors: dict[str, str]):
    return parse_eurostat_series(payload, dataset=dataset, selectors=selectors)


def _incumbent_style_decode(payload: dict[str, Any]) -> dict[str, Any]:
    """Replica of the incumbent collector's collapsing decode, for contrast.

    It keeps the *time* coordinate of each flat cell and throws the other
    coordinates away, so every non-time category is written onto the same
    time label.  The two tests below use it to show that the fixtures really
    do discriminate: the incumbent-style decode must come back with a wrong
    value on exactly the payloads this parser is meant to repair.
    """
    dims = list(payload["id"])
    sizes = [int(value) for value in payload["size"]]
    time_axis = dims.index("time")
    index = payload["dimension"]["time"]["category"]["index"]
    label_by_pos = {position: label for label, position in index.items()}
    stride = 1
    for size in sizes[time_axis + 1 :]:
        stride *= size
    values: dict[str, Any] = {}
    for raw_flat, raw_value in payload["value"].items():
        flat = int(raw_flat)
        time_pos = (flat // stride) % sizes[time_axis]
        label = label_by_pos.get(time_pos)
        if label is None:
            continue
        values[label] = raw_value
    return values


# --- the admitted series ------------------------------------------------------


def test_supported_series_are_exactly_the_two_admitted_ones():
    assert set(SUPPORTED_SERIES) == {GDP, HICP}
    assert SUPPORTED_SERIES[GDP]["axes"] == tuple(GDP_AXES)
    assert SUPPORTED_SERIES[HICP]["axes"] == tuple(HICP_AXES)


def test_gdp_real_shape_eleven_quarterly_rows():
    result = _parse(_gdp_payload(), GDP, GDP_SELECTORS)

    assert result["dataset"] == GDP
    assert result["source"] == "ESTAT"
    assert result["updated"] == GDP_UPDATED
    assert result["dimensions"] == GDP_SELECTORS
    assert len(result["observations"]) == 11

    periods = [observation["period"] for observation in result["observations"]]
    assert periods == GDP_TIME_LABELS
    assert periods[0] == "2024-Q1"
    assert periods[-1] == "2026-Q3"

    latest = result["observations"][-1]
    assert latest["value"] == 1.3
    assert latest["status"] is None
    assert latest["period_start"] == "2026-07-01"
    assert latest["period_end_exclusive"] == "2026-10-01"
    assert latest["observation_at"] == "2026-09-30"


def test_hicp_real_shape_latest_month_and_update_stamp():
    result = _parse(_hicp_payload(), HICP, HICP_SELECTORS)

    assert result["dataset"] == HICP
    assert result["source"] == "ESTAT"
    assert result["updated"] == HICP_UPDATED
    assert result["dimensions"] == HICP_SELECTORS
    assert len(result["observations"]) == len(HICP_TIME_LABELS)

    latest = result["observations"][-1]
    assert latest["period"] == "2026-09"
    assert latest["value"] == 3.8
    assert latest["status"] is None
    assert latest["period_start"] == "2026-09-01"
    assert latest["period_end_exclusive"] == "2026-10-01"
    assert latest["observation_at"] == "2026-09-30"


def test_observation_keys_are_exactly_the_contracted_ones():
    observation = _parse(_gdp_payload(), GDP, GDP_SELECTORS)["observations"][0]
    assert set(observation) == {
        "period",
        "value",
        "status",
        "period_start",
        "period_end_exclusive",
        "observation_at",
    }
    assert set(_parse(_gdp_payload(), GDP, GDP_SELECTORS)) == {
        "dataset",
        "source",
        "updated",
        "dimensions",
        "observations",
    }


# --- the collapsing defect ----------------------------------------------------


def test_multi_category_axis_is_not_collapsed_onto_the_time_label():
    """The 555-category coicop18 axis must not overwrite the TOTAL slice."""
    result = _parse(_hicp_payload(), HICP, HICP_SELECTORS)

    values = [observation["value"] for observation in result["observations"]]
    assert values == HICP_VALUES
    # The distractors sit at other category positions with far higher values.
    assert 88.8 not in values
    assert 99.9 not in values
    assert 77.7 not in values


def test_distractor_written_after_the_selected_slice_does_not_win():
    """A later-written category must not overwrite the selected period."""
    payload = _hicp_payload(
        extra_cells=(
            (
                {
                    "coicop18": "CP553",
                    "freq": "M",
                    "unit": "RCH_A",
                    "geo": "EA21",
                },
                "2026-09",
                42.42,
            ),
        )
    )
    result = _parse(payload, HICP, HICP_SELECTORS)
    assert result["observations"][-1]["value"] == 3.8


@pytest.mark.parametrize(
    "axes",
    [
        ["time", "freq", "unit", "s_adj", "na_item", "geo"],
        ["freq", "time", "unit", "s_adj", "na_item", "geo"],
        ["unit", "s_adj", "na_item", "geo", "time", "freq"],
        ["geo", "na_item", "s_adj", "unit", "freq", "time"],
    ],
)
def test_reordered_axes_decode_identically(axes):
    """The flat cell is decoded with strides for the axis order returned."""
    labels = _gdp_labels()
    reference = _parse(_gdp_payload(), GDP, GDP_SELECTORS)

    payload = _payload(
        dataset=GDP,
        axes=axes,
        labels=labels,
        selected=dict(GDP_SELECTORS),
        cells=_gdp_cells(),
        updated=GDP_UPDATED,
    )
    result = _parse(payload, GDP, GDP_SELECTORS)
    assert result["observations"] == reference["observations"]


def test_reordered_axes_with_multi_category_axis_decode_identically():
    reference = _parse(_hicp_payload(), HICP, HICP_SELECTORS)
    axes = ["time", "coicop18", "geo", "unit", "freq"]
    payload = _payload(
        dataset=HICP,
        axes=axes,
        labels=_hicp_labels(),
        selected=dict(HICP_SELECTORS),
        cells=_hicp_cells(),
        extra_cells=(
            (
                {"coicop18": "CP000", "freq": "M", "unit": "RCH_A", "geo": "EA21"},
                "2026-09",
                88.8,
            ),
        ),
        updated=HICP_UPDATED,
    )
    result = _parse(payload, HICP, HICP_SELECTORS)
    assert result["observations"] == reference["observations"]


def test_two_multi_category_axes_are_crossed_correctly():
    """coicop18 x geo: the exact cross-cell is read, not the first of each."""
    labels = _hicp_labels()
    labels["geo"] = ["EA20", "EA21"]
    cells = {label: (value, None) for label, value in zip(HICP_TIME_LABELS, HICP_VALUES)}
    payload = _payload(
        dataset=HICP,
        axes=list(HICP_AXES),
        labels=labels,
        selected=dict(HICP_SELECTORS),
        cells=cells,
        extra_cells=(
            (
                {"coicop18": "TOTAL", "freq": "M", "unit": "RCH_A", "geo": "EA20"},
                "2026-09",
                55.5,
            ),
            (
                {"coicop18": "CP000", "freq": "M", "unit": "RCH_A", "geo": "EA21"},
                "2026-09",
                88.8,
            ),
        ),
        updated=HICP_UPDATED,
    )
    result = _parse(payload, HICP, HICP_SELECTORS)
    assert result["observations"][-1]["value"] == 3.8


# --- missing points and flags -------------------------------------------------


def test_missing_point_stays_missing_and_is_not_back_filled():
    labels = _gdp_labels()
    cells = _gdp_cells()
    dropped = cells.pop("2025-Q2")
    payload = _gdp_payload(cells=cells)

    result = _parse(payload, GDP, GDP_SELECTORS)
    observations = {item["period"]: item for item in result["observations"]}
    assert len(observations) == 11
    assert observations["2025-Q2"]["value"] is None
    assert observations["2025-Q2"]["status"] is None
    assert observations["2025-Q2"]["period_start"] == "2025-04-01"
    assert observations["2025-Q2"]["observation_at"] == "2025-06-30"
    assert dropped == (GDP_VALUES[GDP_TIME_LABELS.index("2025-Q2")], None)


def test_explicit_null_cell_stays_missing():
    cells = _gdp_cells()
    cells["2025-Q2"] = (None, None)
    result = _parse(_gdp_payload(cells=cells), GDP, GDP_SELECTORS)
    observations = {item["period"]: item for item in result["observations"]}
    assert observations["2025-Q2"]["value"] is None


def test_observation_flags_are_preserved():
    cells = _gdp_cells()
    cells["2026-Q2"] = (GDP_VALUES[-2], "p")
    cells["2026-Q1"] = (GDP_VALUES[-3], "e")
    cells["2024-Q1"] = (GDP_VALUES[0], ":")
    result = _parse(_gdp_payload(cells=cells), GDP, GDP_SELECTORS)

    observations = {item["period"]: item for item in result["observations"]}
    assert observations["2026-Q2"]["status"] == "p"
    assert observations["2026-Q1"]["status"] == "e"
    assert observations["2024-Q1"]["status"] == ":"
    assert observations["2026-Q3"]["status"] is None


def test_flag_without_a_value_is_kept():
    cells = _gdp_cells()
    cells["2025-Q2"] = (None, ":")
    result = _parse(_gdp_payload(cells=cells), GDP, GDP_SELECTORS)
    observations = {item["period"]: item for item in result["observations"]}
    assert observations["2025-Q2"]["value"] is None
    assert observations["2025-Q2"]["status"] == ":"


def test_dense_list_forms_are_supported():
    reference = _parse(_gdp_payload(), GDP, GDP_SELECTORS)
    dense = _gdp_payload(value_form="list", status_form="list")
    result = _parse(dense, GDP, GDP_SELECTORS)
    assert result["observations"] == reference["observations"]


def test_dense_list_form_for_the_multi_category_axis():
    reference = _parse(_hicp_payload(), HICP, HICP_SELECTORS)
    dense = _hicp_payload(value_form="list", status_form="list")
    result = _parse(dense, HICP, HICP_SELECTORS)
    assert result["observations"] == reference["observations"]


# --- economic period normalization --------------------------------------------


@pytest.mark.parametrize(
    ("period", "start", "end", "observation"),
    [
        ("2026-Q1", "2026-01-01", "2026-04-01", "2026-03-31"),
        ("2026-Q2", "2026-04-01", "2026-07-01", "2026-06-30"),
        ("2026-Q3", "2026-07-01", "2026-10-01", "2026-09-30"),
        ("2026-Q4", "2026-10-01", "2027-01-01", "2026-12-31"),
        ("2024-Q2", "2024-04-01", "2024-07-01", "2024-06-30"),
    ],
)
def test_quarter_normalization(period, start, end, observation):
    labels = _gdp_labels()
    labels["time"] = [period]
    payload = _gdp_payload(labels=labels, cells={period: (1.5, None)})
    result = _parse(payload, GDP, GDP_SELECTORS)
    item = result["observations"][0]
    assert item["period_start"] == start
    assert item["period_end_exclusive"] == end
    assert item["observation_at"] == observation


@pytest.mark.parametrize(
    ("period", "start", "end", "observation"),
    [
        ("2026-01", "2026-01-01", "2026-02-01", "2026-01-31"),
        ("2026-09", "2026-09-01", "2026-10-01", "2026-09-30"),
        ("2026-12", "2026-12-01", "2027-01-01", "2026-12-31"),
        ("2024-02", "2024-02-01", "2024-03-01", "2024-02-29"),
    ],
)
def test_month_normalization(period, start, end, observation):
    labels = _hicp_labels()
    labels["time"] = [period]
    payload = _hicp_payload(labels=labels, cells={period: (2.4, None)}, extra_cells=())
    result = _parse(payload, HICP, HICP_SELECTORS)
    item = result["observations"][0]
    assert item["period_start"] == start
    assert item["period_end_exclusive"] == end
    assert item["observation_at"] == observation


def test_observations_are_sorted_by_economic_period():
    labels = _gdp_labels()
    labels["time"] = list(reversed(GDP_TIME_LABELS))
    payload = _gdp_payload(labels=labels)
    result = _parse(payload, GDP, GDP_SELECTORS)
    periods = [item["period"] for item in result["observations"]]
    assert periods == GDP_TIME_LABELS


def test_monthly_observations_are_sorted_by_economic_period():
    labels = _hicp_labels()
    labels["time"] = list(reversed(HICP_TIME_LABELS))
    payload = _hicp_payload(labels=labels)
    result = _parse(payload, HICP, HICP_SELECTORS)
    periods = [item["period"] for item in result["observations"]]
    assert periods == HICP_TIME_LABELS


@pytest.mark.parametrize("label", ["2026-Q5", "2026-Q0", "2026-3", "26-Q3", "2026"])
def test_invalid_quarterly_period_is_refused(label):
    labels = _gdp_labels()
    labels["time"] = [label]
    payload = _gdp_payload(labels=labels, cells={label: (1.0, None)})
    with pytest.raises(EurostatPayloadError):
        _parse(payload, GDP, GDP_SELECTORS)


@pytest.mark.parametrize("label", ["2026-13", "2026-00", "2026-1", "2026-09-Q"])
def test_invalid_monthly_period_is_refused(label):
    labels = _hicp_labels()
    labels["time"] = [label]
    payload = _hicp_payload(labels=labels, cells={label: (1.0, None)}, extra_cells=())
    with pytest.raises(EurostatPayloadError):
        _parse(payload, HICP, HICP_SELECTORS)


# --- category index geometry --------------------------------------------------


def test_missing_category_index_is_refused():
    payload = _gdp_payload()
    del payload["dimension"]["geo"]["category"]["index"]
    with pytest.raises(EurostatPayloadError):
        _parse(payload, GDP, GDP_SELECTORS)


def test_duplicate_category_position_is_refused():
    payload = _gdp_payload()
    payload["dimension"]["na_item"]["category"]["index"] = {"B1GQ": 0, "B1GF": 0}
    with pytest.raises(EurostatPayloadError):
        _parse(payload, GDP, GDP_SELECTORS)


def test_non_contiguous_category_positions_are_refused():
    payload = _gdp_payload()
    payload["dimension"]["na_item"]["category"]["index"] = {"B1GQ": 0, "B1GF": 2}
    with pytest.raises(EurostatPayloadError):
        _parse(payload, GDP, GDP_SELECTORS)


def test_short_category_index_is_refused():
    payload = _gdp_payload()
    payload["dimension"]["time"]["category"]["index"] = {"2026-Q3": 0}
    with pytest.raises(EurostatPayloadError):
        _parse(payload, GDP, GDP_SELECTORS)


def test_out_of_range_category_position_is_refused():
    payload = _gdp_payload()
    payload["dimension"]["na_item"]["category"]["index"] = {"B1GQ": 3}
    with pytest.raises(EurostatPayloadError):
        _parse(payload, GDP, GDP_SELECTORS)


def test_duplicate_label_in_the_positional_index_form_is_refused():
    payload = _gdp_payload(index_form="list")
    payload["dimension"]["na_item"]["category"]["index"] = ["B1GQ", "B1GQ"]
    with pytest.raises(EurostatPayloadError):
        _parse(payload, GDP, GDP_SELECTORS)


def test_positional_index_form_is_accepted():
    reference = _parse(_gdp_payload(), GDP, GDP_SELECTORS)
    result = _parse(_gdp_payload(index_form="list"), GDP, GDP_SELECTORS)
    assert result["observations"] == reference["observations"]


def test_selected_code_missing_from_the_returned_categories_is_refused():
    payload = _gdp_payload()
    payload["dimension"]["geo"]["category"]["index"] = {"EA20": 0}
    with pytest.raises(EurostatPayloadError):
        _parse(payload, GDP, GDP_SELECTORS)


def test_non_numeric_category_position_is_refused():
    payload = _gdp_payload()
    payload["dimension"]["na_item"]["category"]["index"] = {"B1GQ": "0"}
    with pytest.raises(EurostatPayloadError):
        _parse(payload, GDP, GDP_SELECTORS)


# --- identity and contract ----------------------------------------------------


def test_non_estat_source_is_refused():
    payload = _gdp_payload(source="EUROSTAT")
    with pytest.raises(EurostatPayloadError):
        _parse(payload, GDP, GDP_SELECTORS)


def test_dataset_mismatch_in_the_extension_is_refused():
    payload = _gdp_payload(extension_id=HICP)
    with pytest.raises(EurostatPayloadError):
        _parse(payload, GDP, GDP_SELECTORS)


def test_missing_extension_is_refused():
    payload = _gdp_payload()
    del payload["extension"]
    with pytest.raises(EurostatPayloadError):
        _parse(payload, GDP, GDP_SELECTORS)


def test_unsupported_dataset_is_refused():
    payload = _gdp_payload()
    with pytest.raises(EurostatPayloadError):
        _parse(payload, "PRC_HICP_MANR", HICP_SELECTORS)


def test_unit_mismatch_is_refused():
    payload = _gdp_payload()
    selectors = dict(GDP_SELECTORS)
    selectors["unit"] = "PC_200"
    with pytest.raises(EurostatPayloadError):
        _parse(payload, GDP, selectors)


def test_missing_selector_is_refused():
    selectors = dict(GDP_SELECTORS)
    del selectors["geo"]
    with pytest.raises(EurostatPayloadError):
        _parse(_gdp_payload(), GDP, selectors)


def test_extra_selector_is_refused():
    selectors = dict(GDP_SELECTORS)
    selectors["extra"] = "X"
    with pytest.raises(EurostatPayloadError):
        _parse(_gdp_payload(), GDP, selectors)


def test_hicp_selectors_are_not_accepted_for_the_gdp_dataset():
    with pytest.raises(EurostatPayloadError):
        _parse(_gdp_payload(), GDP, HICP_SELECTORS)


def test_selectors_must_be_a_mapping():
    with pytest.raises(EurostatPayloadError):
        parse_eurostat_series(_gdp_payload(), dataset=GDP, selectors=["freq", "Q"])


def test_selected_code_missing_from_the_frequency_axis_is_refused():
    payload = _gdp_payload()
    payload["dimension"]["freq"]["category"]["index"] = {"M": 0}
    with pytest.raises(EurostatPayloadError):
        _parse(payload, GDP, GDP_SELECTORS)


def test_wrong_axis_set_is_refused():
    payload = _gdp_payload()
    payload["id"] = ["freq", "unit", "s_adj", "geo", "time"]
    with pytest.raises(EurostatPayloadError):
        _parse(payload, GDP, GDP_SELECTORS)


def test_repeated_axis_is_refused():
    payload = _gdp_payload()
    payload["id"] = ["freq", "freq", "s_adj", "na_item", "geo", "time"]
    with pytest.raises(EurostatPayloadError):
        _parse(payload, GDP, GDP_SELECTORS)


def test_non_positive_size_is_refused():
    payload = _gdp_payload()
    payload["size"] = [1, 1, 1, 1, 0, 11]
    with pytest.raises(EurostatPayloadError):
        _parse(payload, GDP, GDP_SELECTORS)


def test_size_count_mismatch_is_refused():
    payload = _gdp_payload()
    payload["size"] = [1, 1, 1, 1, 1]
    with pytest.raises(EurostatPayloadError):
        _parse(payload, GDP, GDP_SELECTORS)


def test_non_integer_size_is_refused():
    payload = _gdp_payload()
    payload["size"] = [1, 1, 1, 1, 1, "11"]
    with pytest.raises(EurostatPayloadError):
        _parse(payload, GDP, GDP_SELECTORS)


def test_unbounded_cell_product_is_refused():
    payload = _gdp_payload()
    payload["size"] = [100_000, 100_000, 1, 1, 1, 11]
    with pytest.raises(EurostatPayloadError):
        _parse(payload, GDP, GDP_SELECTORS)


# --- values and flags ---------------------------------------------------------


@pytest.mark.parametrize(
    "bad_value",
    [True, False, math.nan, math.inf, -math.inf, "1.3", "n/a", [1.3], {"v": 1.3}],
)
def test_invalid_observation_values_are_refused(bad_value):
    cells = _gdp_cells()
    cells["2026-Q3"] = (bad_value, None)
    payload = _gdp_payload(cells=cells)
    with pytest.raises(EurostatPayloadError):
        _parse(payload, GDP, GDP_SELECTORS)


def test_non_text_observation_flag_is_refused():
    cells = _gdp_cells()
    cells["2026-Q3"] = (GDP_VALUES[-1], 7)
    payload = _gdp_payload(cells=cells)
    with pytest.raises(EurostatPayloadError):
        _parse(payload, GDP, GDP_SELECTORS)


def test_out_of_range_flat_index_is_refused():
    payload = _gdp_payload()
    payload["value"]["999999"] = 1.0
    with pytest.raises(EurostatPayloadError):
        _parse(payload, GDP, GDP_SELECTORS)


def test_malformed_flat_index_is_refused():
    payload = _gdp_payload()
    payload["value"]["not-an-index"] = 1.0
    with pytest.raises(EurostatPayloadError):
        _parse(payload, GDP, GDP_SELECTORS)


def test_dense_array_longer_than_the_geometry_is_refused():
    payload = _gdp_payload(value_form="list")
    payload["value"].append(1.0)
    with pytest.raises(EurostatPayloadError):
        _parse(payload, GDP, GDP_SELECTORS)


def test_missing_value_array_is_refused():
    payload = _gdp_payload()
    del payload["value"]
    with pytest.raises(EurostatPayloadError):
        _parse(payload, GDP, GDP_SELECTORS)


# --- update stamp -------------------------------------------------------------


def test_update_stamp_is_returned_verbatim():
    result = _parse(_gdp_payload(updated=GDP_UPDATED), GDP, GDP_SELECTORS)
    assert result["updated"] == "2026-10-30T23:00:00+0100"


def test_actual_top_level_update_stamp_is_not_replaced_by_extension():
    payload = _gdp_payload(
        updated=GDP_UPDATED,
        top_level_updated="2026-11-01T08:30:00+0100",
    )
    result = _parse(payload, GDP, GDP_SELECTORS)
    assert result["updated"] == "2026-11-01T08:30:00+0100"


def test_missing_update_stamp_is_refused():
    payload = _gdp_payload()
    del payload["extension"]["updated"]
    del payload["updated"]
    with pytest.raises(EurostatPayloadError):
        _parse(payload, GDP, GDP_SELECTORS)


def test_naive_update_stamp_is_refused():
    payload = _gdp_payload(updated="2026-10-30T23:00:00")
    with pytest.raises(EurostatPayloadError):
        _parse(payload, GDP, GDP_SELECTORS)


def test_unparsable_update_stamp_is_refused():
    payload = _gdp_payload(updated="yesterday")
    with pytest.raises(EurostatPayloadError):
        _parse(payload, GDP, GDP_SELECTORS)


# --- shape of the payload itself ----------------------------------------------


def test_non_object_payload_is_refused():
    with pytest.raises(EurostatPayloadError):
        _parse([], GDP, GDP_SELECTORS)
    with pytest.raises(EurostatPayloadError):
        _parse(None, GDP, GDP_SELECTORS)


def test_missing_id_is_refused():
    payload = _gdp_payload()
    del payload["id"]
    with pytest.raises(EurostatPayloadError):
        _parse(payload, GDP, GDP_SELECTORS)


def test_missing_dimension_is_refused():
    payload = _gdp_payload()
    del payload["dimension"]["geo"]
    with pytest.raises(EurostatPayloadError):
        _parse(payload, GDP, GDP_SELECTORS)


def test_the_payload_is_not_mutated():
    payload = _gdp_payload()
    before = copy.deepcopy(payload)
    _parse(payload, GDP, GDP_SELECTORS)
    assert payload == before


def _reference_flat(axes: list[str], sizes: dict[str, int], positions: dict[str, int]) -> int:
    """Brute-force row-major flat index: walk every cell in order.

    ``positions`` pins only the axes the caller cares about; the walk returns
    the flat index of the first cell that matches them.
    """
    index = 0
    for combination in itertools.product(*(range(sizes[axis]) for axis in axes)):
        if all(combination[axes.index(axis)] == positions[axis] for axis in positions):
            return index
        index += 1
    raise AssertionError("cell not found")


@pytest.mark.parametrize(
    "axes",
    [
        ["coicop18", "geo", "time", "unit", "freq"],
        ["time", "geo", "coicop18", "unit", "freq"],
        ["geo", "coicop18", "time", "unit", "freq"],
        ["freq", "unit", "coicop18", "geo", "time"],
    ],
)
def test_selected_cell_matches_a_brute_force_row_major_walk(axes):
    """The decoded cell is the one a full row-major walk would land on."""
    labels = {
        "freq": ["M"],
        "unit": ["RCH_A"],
        "coicop18": ["C0", "C1", "C2", "TOTAL"],
        "geo": ["EA20", "EA21"],
        "time": ["2026-07", "2026-08", "2026-09"],
    }
    sizes = {axis: len(labels[axis]) for axis in axes}
    payload = _payload(
        dataset=HICP,
        axes=axes,
        labels=labels,
        selected=dict(HICP_SELECTORS),
        cells={},
        sizes=sizes,
        updated=HICP_UPDATED,
    )
    # Fill every cell with a marker; only the selected cross-cell differs.
    filled: dict[int, Any] = {}
    for combination in itertools.product(*(range(sizes[axis]) for axis in axes)):
        positions = {axis: combination[index] for index, axis in enumerate(axes)}
        flat = _reference_flat(axes, sizes, positions)
        filled[flat] = -1.0
    for index, time_label in enumerate(labels["time"]):
        positions = {
            "coicop18": labels["coicop18"].index("TOTAL"),
            "geo": labels["geo"].index("EA21"),
            "time": labels["time"].index(time_label),
        }
        filled[_reference_flat(axes, sizes, positions)] = 100.0 + index
    payload["value"] = {str(flat): value for flat, value in sorted(filled.items())}

    result = _parse(payload, HICP, HICP_SELECTORS)
    assert [item["value"] for item in result["observations"]] == [100.0, 101.0, 102.0]
    assert [item["period"] for item in result["observations"]] == labels["time"]


# --- the fixture must actually discriminate -----------------------------------


def test_the_multi_category_fixture_defeats_the_incumbent_collapse():
    """The incumbent-style decode lands on a distractor, the parser does not."""
    payload = _hicp_payload()
    collapsed = _incumbent_style_decode(payload)
    parsed = _parse(payload, HICP, HICP_SELECTORS)

    latest = parsed["observations"][-1]
    assert latest["value"] == 3.8
    assert collapsed["2026-09"] != latest["value"]
    assert collapsed["2026-09"] in (88.8, 99.9, 77.7)


def test_the_reordered_fixture_defeats_the_incumbent_time_axis_assumption():
    """Reordering the axes does not save the incumbent-style decode."""
    axes = ["time", "coicop18", "geo", "unit", "freq"]
    payload = _payload(
        dataset=HICP,
        axes=axes,
        labels=_hicp_labels(),
        selected=dict(HICP_SELECTORS),
        cells=_hicp_cells(),
        extra_cells=tuple(
            (
                {"coicop18": code, "freq": "M", "unit": "RCH_A", "geo": "EA21"},
                time_label,
                value,
            )
            for code, value in (("CP000", 88.8), ("CP003", 99.9), ("CP553", 77.7))
            for time_label in HICP_TIME_LABELS
        ),
        updated=HICP_UPDATED,
    )
    collapsed = _incumbent_style_decode(payload)
    parsed = _parse(payload, HICP, HICP_SELECTORS)

    assert parsed["observations"][-1]["period"] == "2026-09"
    assert parsed["observations"][-1]["value"] == 3.8
    assert collapsed["2026-09"] != 3.8
    assert collapsed["2026-09"] in (88.8, 99.9, 77.7)


def test_extension_clock_cannot_fill_a_missing_native_top_level_clock():
    payload = _gdp_payload()
    del payload["updated"]
    with pytest.raises(EurostatPayloadError):
        _parse(payload, GDP, GDP_SELECTORS)


@pytest.mark.parametrize("alias", ["00", " 0", "٠"])
def test_noncanonical_flat_index_alias_is_refused(alias):
    payload = _gdp_payload()
    payload["value"][alias] = 999
    with pytest.raises(EurostatPayloadError):
        _parse(payload, GDP, GDP_SELECTORS)


def test_dense_truncation_is_not_a_missing_native_observation():
    payload = _gdp_payload(value_form="list")
    payload["value"].pop()
    with pytest.raises(EurostatPayloadError):
        _parse(payload, GDP, GDP_SELECTORS)
