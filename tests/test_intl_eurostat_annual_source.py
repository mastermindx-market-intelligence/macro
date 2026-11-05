"""Focused tests for the admitted annual EA21 current-account series.

These tests exercise the annual ``TIPSBP20`` admission of
``lib/intl_eurostat_source.py`` only.  Every fixture is built in this file.
The facts quoted from the commission are the retained response's axis order,
sizes, cell layout, category indexes, dataset update clock and its three
``EXT_EA21`` values; the distractor cells are placeholders that preserve the
real payload's shape so a collapsing or partner-blind decoder cannot pass by
accident.
"""

from __future__ import annotations

import copy
import itertools
from typing import Any

import pytest

from lib.intl_eurostat_source import (
    EurostatPayloadError,
    SUPPORTED_SERIES,
    parse_eurostat_series,
)

CA = "TIPSBP20"

CA_SELECTORS = {
    "freq": "A",
    "unit": "PC_GDP",
    "bop_item": "CA",
    "sector10": "S1",
    "sectpart": "S1",
    "stk_flow": "BAL",
    "partner": "EXT_EA21",
    "s_adj": "NSA",
    "geo": "EA21",
}

CA_UPDATED = "2026-10-28T23:00:00+0100"

CA_AXES = [
    "freq",
    "unit",
    "bop_item",
    "sector10",
    "sectpart",
    "stk_flow",
    "partner",
    "s_adj",
    "geo",
    "time",
]

CA_TIME_LABELS = ["2023", "2024", "2025"]

CA_LABELS = {
    "freq": ["A"],
    "unit": ["PC_GDP"],
    "bop_item": ["CA"],
    "sector10": ["S1"],
    "sectpart": ["S1"],
    "stk_flow": ["BAL"],
    "partner": ["WRL_REST", "EXT_EU27_2020", "EXT_EA21", "EXT_EA20"],
    "s_adj": ["NSA"],
    "geo": ["EA21"],
    "time": CA_TIME_LABELS,
}

#: The retained response, verbatim, except for the prose-only ``extension``
#: description and annotation blocks.  Everything the decoder reads -- the
#: axis order, the sizes, the flat cell layout, the category indexes, the
#: source, the dataset update clock and the ``positions-with-no-data`` note
#: -- is the retained text.
RETAINED_RESPONSE: dict[str, Any] = {
    "version": "2.0",
    "class": "dataset",
    "label": "Current account balance - annual data",
    "source": "ESTAT",
    "updated": "2026-10-28T23:00:00+0100",
    "value": {"6": 1.8, "7": 2.5, "8": 1.7},
    "id": [
        "freq",
        "unit",
        "bop_item",
        "sector10",
        "sectpart",
        "stk_flow",
        "partner",
        "s_adj",
        "geo",
        "time",
    ],
    "size": [1, 1, 1, 1, 1, 1, 4, 1, 1, 3],
    "dimension": {
        "freq": {
            "label": "Time frequency",
            "category": {"index": {"A": 0}, "label": {"A": "Annual"}},
        },
        "unit": {
            "label": "Unit of measure",
            "category": {
                "index": {"PC_GDP": 0},
                "label": {
                    "PC_GDP": "Percentage of gross domestic product (GDP)"
                },
            },
        },
        "bop_item": {
            "label": "Balance of payments item",
            "category": {"index": {"CA": 0}, "label": {"CA": "Current account"}},
        },
        "sector10": {
            "label": "Sector (ESA 2010)",
            "category": {"index": {"S1": 0}, "label": {"S1": "Total economy"}},
        },
        "sectpart": {
            "label": "Counterpart sector (ESA 2010)",
            "category": {"index": {"S1": 0}, "label": {"S1": "Total economy"}},
        },
        "stk_flow": {
            "label": "Stock or flow",
            "category": {"index": {"BAL": 0}, "label": {"BAL": "Balance"}},
        },
        "partner": {
            "label": "Geopolitical entity (partner)",
            "category": {
                "index": {
                    "WRL_REST": 0,
                    "EXT_EU27_2020": 1,
                    "EXT_EA21": 2,
                    "EXT_EA20": 3,
                },
                "label": {
                    "WRL_REST": "Rest of the world",
                    "EXT_EU27_2020": "Extra-EU27 (from 2020)",
                    "EXT_EA21": "Extra-euro area - 21 countries (from 2026)",
                    "EXT_EA20": "Extra-euro area - 20 countries (2023-2025)",
                },
            },
        },
        "s_adj": {
            "label": "Seasonal adjustment",
            "category": {
                "index": {"NSA": 0},
                "label": {
                    "NSA": (
                        "Unadjusted data (i.e. neither seasonally adjusted nor "
                        "calendar adjusted data)"
                    )
                },
            },
        },
        "geo": {
            "label": "Geopolitical entity (reporting)",
            "category": {
                "index": {"EA21": 0},
                "label": {"EA21": "Euro area - 21 countries (from 2026)"},
            },
        },
        "time": {
            "label": "Time",
            "category": {
                "index": {"2023": 0, "2024": 1, "2025": 2},
                "label": {"2023": "2023", "2024": "2024", "2025": "2025"},
            },
        },
    },
    "extension": {"lang": "EN", "id": "TIPSBP20", "agencyId": "ESTAT", "version": "1.0"},
    "positions-with-no-data": {
        "freq": [],
        "unit": [],
        "bop_item": [],
        "sector10": [],
        "sectpart": [],
        "stk_flow": [],
        "partner": [0, 1, 3],
        "s_adj": [],
        "geo": [],
        "time": [],
    },
}

#: ``(axis overrides, time label, value, status)``
Cell = tuple[dict[str, str], str, Any, str | None]

RETAINED_CELLS: list[Cell] = [
    ({}, "2023", 1.8, None),
    ({}, "2024", 2.5, None),
    ({}, "2025", 1.7, None),
]


def _payload(
    *,
    axes: list[str] | None = None,
    labels: dict[str, list[str]] | None = None,
    cells: list[Cell] | None = None,
    updated: str | None = CA_UPDATED,
    index_form: str = "object",
    value_form: str = "object",
    status_form: str | None = None,
    source: str = "ESTAT",
    extension_id: str | None = None,
    sizes: dict[str, int] | None = None,
) -> dict[str, Any]:
    """Build a JSON-stat 2.0 payload in the shape Eurostat returns.

    ``cells`` holds the SELECTED slice (one value/flag per time label); an
    entry may override an axis to place a distractor cell in another
    category, so a partner-blind decoder cannot pass by accident.  The flat
    index of every cell is computed with row-major strides over the axis
    order the payload declares, so the fixture stays well formed whatever
    order the axes are listed in.
    """
    axes = list(axes) if axes is not None else list(CA_AXES)
    labels = labels or {axis: list(CA_LABELS[axis]) for axis in axes}
    cells = RETAINED_CELLS if cells is None else cells
    sizes = sizes or {axis: len(labels[axis]) for axis in axes}

    strides: dict[str, int] = {}
    stride = 1
    for axis in reversed(axes):
        strides[axis] = stride
        stride *= sizes[axis]
    total_cells = stride

    value_cells: dict[int, Any] = {}
    status_cells: dict[int, str] = {}
    for overrides, time_label, value, status in cells:
        positions = {
            axis: labels[axis].index(CA_SELECTORS[axis])
            for axis in axes
            if axis != "time"
        }
        positions.update(
            {axis: labels[axis].index(code) for axis, code in overrides.items()}
        )
        positions["time"] = labels["time"].index(time_label)
        flat = sum(positions[axis] * strides[axis] for axis in axes)
        value_cells[flat] = value
        if status is not None:
            status_cells[flat] = status

    if value_form == "object":
        value_payload: Any = {
            str(flat): value for flat, value in sorted(value_cells.items())
        }
    else:
        dense: list[Any] = [None] * total_cells
        for flat, value in value_cells.items():
            dense[flat] = value
        value_payload = dense

    status_form = status_form or value_form
    status_payload: Any = None
    if status_cells:
        if status_form == "object":
            status_payload = {
                str(flat): status for flat, status in sorted(status_cells.items())
            }
        else:
            dense_status: list[Any] = [None] * total_cells
            for flat, status in status_cells.items():
                dense_status[flat] = status
            status_payload = dense_status

    if index_form == "object":
        dimension = {
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
        dimension = {
            axis: {"label": axis, "category": {"index": list(labels[axis])}}
            for axis in axes
        }

    payload: dict[str, Any] = {
        "version": "2.0",
        "class": "dataset",
        "label": "Current account balance - annual data",
        "source": source,
        "updated": updated,
        "extension": {
            "id": extension_id if extension_id is not None else CA,
            "agencyId": "ESTAT",
            "version": "1.0",
        },
        "id": list(axes),
        "size": [sizes[axis] for axis in axes],
        "dimension": dimension,
        "value": value_payload,
    }
    if status_payload is not None:
        payload["status"] = status_payload
    return payload


def _parse(
    payload: Any,
    dataset: str = CA,
    selectors: dict[str, str] | None = None,
) -> dict[str, Any]:
    return parse_eurostat_series(
        payload,
        dataset=dataset,
        selectors=dict(CA_SELECTORS) if selectors is None else selectors,
    )


def _values(payload: Any, dataset: str = CA) -> list[Any]:
    return [item["value"] for item in _parse(payload, dataset)["observations"]]


def _reference_flat(
    axes: list[str],
    sizes: dict[str, int],
    positions: dict[str, int],
) -> int:
    """Brute-force row-major flat index: walk every cell in order."""
    index = 0
    for combination in itertools.product(*(range(sizes[axis]) for axis in axes)):
        if all(combination[axes.index(axis)] == positions[axis] for axis in positions):
            return index
        index += 1
    raise AssertionError("cell not found")


# --- the admitted contract ----------------------------------------------------


def test_the_annual_series_is_admitted_with_its_exact_contract():
    assert CA in SUPPORTED_SERIES
    spec = SUPPORTED_SERIES[CA]
    assert set(spec["axes"]) == set(CA_AXES)
    assert len(spec["axes"]) == len(CA_AXES)
    assert spec["selectors"] == CA_SELECTORS
    assert spec["frequency"] == "A"


# --- the retained response ----------------------------------------------------


def test_the_retained_response_decodes_to_the_three_native_annual_observations():
    result = _parse(copy.deepcopy(RETAINED_RESPONSE))

    assert result["dataset"] == CA
    assert result["source"] == "ESTAT"
    assert result["updated"] == CA_UPDATED
    assert result["dimensions"] == CA_SELECTORS

    observations = result["observations"]
    assert [item["period"] for item in observations] == ["2023", "2024", "2025"]
    assert [item["value"] for item in observations] == [1.8, 2.5, 1.7]
    assert [item["status"] for item in observations] == [None, None, None]


def test_the_retained_response_keeps_the_native_annual_calendar():
    observations = _parse(copy.deepcopy(RETAINED_RESPONSE))["observations"]

    assert [item["period_start"] for item in observations] == [
        "2023-01-01",
        "2024-01-01",
        "2025-01-01",
    ]
    assert [item["period_end_exclusive"] for item in observations] == [
        "2024-01-01",
        "2025-01-01",
        "2026-01-01",
    ]
    assert [item["observation_at"] for item in observations] == [
        "2023-12-31",
        "2024-12-31",
        "2025-12-31",
    ]


# --- the selected partner against a foreign-partner sentinel ------------------


def test_the_foreign_partner_cells_are_not_read():
    """EXT_EA20 and the other partners carry other values; they are not ours."""
    cells: list[Cell] = list(RETAINED_CELLS) + [
        ({"partner": "EXT_EA20"}, "2023", 9.9, None),
        ({"partner": "EXT_EA20"}, "2024", 8.8, None),
        ({"partner": "EXT_EA20"}, "2025", 7.7, None),
        ({"partner": "WRL_REST"}, "2023", -1.1, None),
        ({"partner": "WRL_REST"}, "2025", -2.2, None),
        ({"partner": "EXT_EU27_2020"}, "2024", -3.3, None),
    ]

    assert _values(_payload(cells=cells)) == [1.8, 2.5, 1.7]


def test_a_payload_without_the_selected_partner_cells_decodes_to_missing():
    cells: list[Cell] = [
        ({"partner": "EXT_EA20"}, "2023", 9.9, None),
        ({"partner": "EXT_EA20"}, "2024", 8.8, None),
        ({"partner": "EXT_EA20"}, "2025", 7.7, None),
    ]

    assert _values(_payload(cells=cells)) == [None, None, None]


@pytest.mark.parametrize(
    "partner",
    ["EXT_EA20", "WRL_REST", "EXT_EU27_2020", "ext_ea21", "EA21", "EXT_EA22"],
)
def test_a_foreign_partner_cannot_be_selected(partner):
    with pytest.raises(EurostatPayloadError):
        _parse(_payload(), selectors=dict(CA_SELECTORS, partner=partner))


# --- the annual period grammar ------------------------------------------------


@pytest.mark.parametrize(
    "label",
    [
        "2023-01",
        "2023-Q1",
        "2023M01",
        "23",
        "20230",
        "2023 ",
        " 2023",
        "2023.0",
        "20-23",
        "0000",
        "99999",
    ],
)
def test_a_malformed_annual_period_label_is_refused(label):
    labels = dict(CA_LABELS, time=[label])
    payload = _payload(labels=labels, cells=[({}, label, 1.0, None)])

    with pytest.raises(EurostatPayloadError):
        _parse(payload)


# --- cells, zeros and source flags -------------------------------------------


def test_a_zero_observation_is_a_value_and_not_a_missing_cell():
    cells: list[Cell] = [
        ({}, "2023", 0.0, None),
        ({}, "2024", 2.5, None),
        ({}, "2025", 1.7, None),
    ]

    observations = _parse(_payload(cells=cells))["observations"]
    assert observations[0]["value"] == 0.0
    assert observations[0]["value"] is not None
    assert observations[1]["value"] == 2.5


def test_the_source_observation_flags_are_preserved():
    cells: list[Cell] = [
        ({}, "2023", 1.8, "p"),
        ({}, "2024", 2.5, "e"),
        ({}, "2025", 1.7, None),
    ]

    observations = _parse(_payload(cells=cells))["observations"]
    assert [item["status"] for item in observations] == ["p", "e", None]


# --- the payload's own geometry ----------------------------------------------


@pytest.mark.parametrize(
    "axes",
    [
        CA_AXES,
        ["time", "partner", "freq", "unit", "bop_item", "sector10", "sectpart", "stk_flow", "s_adj", "geo"],
        ["partner", "time", "geo", "s_adj", "stk_flow", "sectpart", "sector10", "bop_item", "unit", "freq"],
        ["geo", "s_adj", "partner", "stk_flow", "sectpart", "sector10", "bop_item", "unit", "freq", "time"],
    ],
)
def test_reordered_axes_decode_identically(axes):
    """The axis order the payload declares is the axis order used to address."""
    payload = _payload(axes=axes, cells=RETAINED_CELLS)

    assert _values(payload) == [1.8, 2.5, 1.7]


@pytest.mark.parametrize(
    "axes",
    [
        CA_AXES,
        ["time", "partner", "freq", "unit", "bop_item", "sector10", "sectpart", "stk_flow", "s_adj", "geo"],
        ["partner", "time", "geo", "s_adj", "stk_flow", "sectpart", "sector10", "bop_item", "unit", "freq"],
    ],
)
def test_the_positional_category_index_form_decodes_identically(axes):
    payload = _payload(axes=axes, index_form="list")

    assert _values(payload) == [1.8, 2.5, 1.7]


# --- the strict payload fields ------------------------------------------------


def test_the_dataset_update_clock_is_carried_through_verbatim():
    result = _parse(_payload(updated="2026-10-28T23:00:00+0530"))

    assert result["updated"] == "2026-10-28T23:00:00+0530"


def test_the_payload_is_not_mutated():
    payload = copy.deepcopy(RETAINED_RESPONSE)
    before = copy.deepcopy(payload)

    _parse(payload)

    assert payload == before
