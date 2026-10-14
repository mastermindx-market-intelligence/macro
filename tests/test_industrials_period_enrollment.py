"""Enroll the stated fiscal label onto the native edition record (W8-A).

The synthetic cell already carries ``FY2026 Q2`` and period end 3 July.
Enrollment copies that label onto ``presented_fiscal_label`` and must not
let a three-day tolerance rewrite the cell end to 30 June.
"""
from __future__ import annotations

import re
from collections.abc import Callable
from copy import deepcopy
from datetime import date

import pytest

from engine.company_intelligence.industrials_period_enrollment import (
    enroll_stated_period,
)
from engine.company_intelligence.industrials_source_facts import edition_documents
from tests.industrials_result_cash_helpers import case


def test_stated_end_not_snapped_on_enrolled_cell() -> None:
    result = enroll_stated_period(case("same_number_two_headers"), tolerance_days=3)
    assert result.stated_ends
    assert set(result.stated_ends) == {date(2026, 7, 3)}
    assert all(end != date(2026, 6, 30) for end in result.stated_ends)
    assert len(result.cells) == 2
    assert [cell["period"]["end"] for cell in result.cells] == [
        "2026-07-03",
        "2026-07-03",
    ]


def test_presented_fiscal_label_reaches_payload() -> None:
    loaded = case("same_number_two_headers")
    cell = deepcopy(loaded["cells"][0])
    enrolled = enroll_stated_period(
        _one_release(cells=[cell]),
        tolerance_days=3,
    )
    assert len(enrolled.documents) == 1
    document = enrolled.documents[0]
    assert document.to_payload()["presented_fiscal_label"] == "FY2026 Q2"
    assert document.rights_profile == "rp_unknown_v1"
    assert cell["quality"]["rights_profile"] == "rp_public_primary_v1"
    assert enrolled.label == "FY2026 Q2"
    assert enrolled.hold is None


def test_disagreed_labels_leave_payload_null() -> None:
    loaded = case("same_number_two_headers")
    first = deepcopy(loaded["cells"][0])
    second = deepcopy(loaded["cells"][1])
    second["period"] = dict(second["period"])
    second["period"]["fiscal_label"] = "FY2026 Q3"
    enrolled = enroll_stated_period(
        _one_release(cells=[first, second]),
        tolerance_days=3,
    )
    assert enrolled.label is None
    assert enrolled.hold == "fiscal_label_disagreement"
    assert enrolled.documents
    assert all(
        document.presented_fiscal_label is None for document in enrolled.documents
    )
    assert all(
        document.to_payload()["presented_fiscal_label"] is None
        for document in enrolled.documents
    )


def test_preliminary_final_has_no_cell_label() -> None:
    loaded = case("preliminary_final")
    enrolled = enroll_stated_period(loaded, tolerance_days=3)
    assert enrolled.label is None
    assert enrolled.hold == "no_cell_fiscal_label"
    assert enrolled.cells == ()
    assert enrolled.stated_ends == ()
    assert enrolled.documents == edition_documents(loaded)
    assert len(enrolled.documents) == 2


def _one_release(*, cells: list[dict]) -> dict:
    """One synthetic example.invalid release plus the cells under test."""
    return {
        "synthetic": True,
        "issuer": {"company_id": "synthetic:northgate"},
        "sources": [
            {
                "source_id": "northgate-stated",
                "url": "https://example.invalid/stated-period.json",
                "mode": "release",
                "rights_state": "public_primary",
                "recorded_at": "2026-07-10T12:00:00Z",
            }
        ],
        "documents": [
            {
                "document_ref": "synthetic:document:stated-period",
                "source_id": "northgate-stated",
                "source_at": "2026-07-10T12:00:00Z",
                "recorded_at": "2026-07-10T12:01:00Z",
            }
        ],
        "cells": cells,
    }


# Tolerance is validated once, up front, on every path.
_BAD_TOLERANCES = [
    pytest.param(-1, ValueError, "tolerance_days must be >= 0", id="negative"),
    pytest.param(True, TypeError, "tolerance_days must be an int, not bool", id="bool"),
]


@pytest.mark.parametrize("tolerance_days,expected,message", _BAD_TOLERANCES)
def test_bad_tolerance_rejected_on_zero_cell_path(
    tolerance_days: object, expected: type[Exception], message: str
) -> None:
    """A bad ``tolerance_days`` is refused even when the case has no cells.

    The check is ``check_tolerance_days``, called once at the top of
    ``enroll_stated_period``, not a dummy-date call buried in the empty branch.
    """
    loaded = case("preliminary_final")
    assert loaded["cells"] == []
    with pytest.raises(expected, match=re.escape(message)):
        enroll_stated_period(loaded, tolerance_days=tolerance_days)


@pytest.mark.parametrize("tolerance_days,expected,message", _BAD_TOLERANCES)
def test_bad_tolerance_rejected_on_cell_path(
    tolerance_days: object, expected: type[Exception], message: str
) -> None:
    """The same refusal happens when the case carries one valid cell."""
    cell = deepcopy(case("same_number_two_headers")["cells"][0])
    with pytest.raises(expected, match=re.escape(message)):
        enroll_stated_period(
            _one_release(cells=[cell]), tolerance_days=tolerance_days
        )


def _cell_without_period() -> dict:
    cell = deepcopy(case("same_number_two_headers")["cells"][0])
    cell.pop("period")
    return _one_release(cells=[cell])


# A shape error elsewhere in the input would raise its own refusal; the
# tolerance check runs first, so the tolerance refusal is the one raised.
_SHAPE_ERRORS = [
    pytest.param(_cell_without_period, id="cell-without-period"),
    pytest.param(lambda: _one_release(cells="nope"), id="cells-not-a-list"),
    pytest.param(lambda: "not-a-case", id="case-not-a-mapping"),
]


@pytest.mark.parametrize("build", _SHAPE_ERRORS)
def test_bad_tolerance_preempts_shape_errors(build: Callable[[], dict]) -> None:
    """A bad ``tolerance_days`` is refused before a case- or cell-shape error."""
    with pytest.raises(
        TypeError, match=re.escape("tolerance_days must be an int, not bool")
    ):
        enroll_stated_period(build(), tolerance_days=True)


# Pins for the branches of ``_shared_label`` and ``_with_stated_end`` that had
# no test. These pin current behaviour only.


def test_string_and_none_labels_are_a_disagreement() -> None:
    """One stated label and one absent label is a disagreement, not a shared label.

    ``_shared_label`` only returns a label when EVERY cell carries the same
    non-empty string; a ``None`` alongside it falls to
    ``fiscal_label_disagreement``.
    """
    loaded = case("same_number_two_headers")
    first = deepcopy(loaded["cells"][0])
    second = deepcopy(loaded["cells"][1])
    second["period"] = dict(second["period"])
    second["period"]["fiscal_label"] = None
    enrolled = enroll_stated_period(
        _one_release(cells=[first, second]), tolerance_days=3
    )
    assert enrolled.label is None
    assert enrolled.hold == "fiscal_label_disagreement"
    assert len(enrolled.cells) == 2
    assert [cell["period"]["fiscal_label"] for cell in enrolled.cells] == [
        "FY2026 Q2",
        None,
    ]


def test_cell_without_period_is_refused() -> None:
    """A cell carrying no ``period`` raises with the field named in the message."""
    cell = deepcopy(case("same_number_two_headers")["cells"][0])
    cell.pop("period")
    with pytest.raises(ValueError, match=re.escape("cell period is required")):
        enroll_stated_period(_one_release(cells=[cell]), tolerance_days=3)


def test_non_iso_period_end_is_refused() -> None:
    """A non-string ``period.end`` raises with the field named in the message."""
    cell = deepcopy(case("same_number_two_headers")["cells"][0])
    cell["period"] = dict(cell["period"])
    cell["period"]["end"] = 20260703
    with pytest.raises(
        ValueError, match=re.escape("cell period.end must be a YYYY-MM-DD string")
    ):
        enroll_stated_period(_one_release(cells=[cell]), tolerance_days=3)


# Refusal shape is documented on ``_with_stated_end``.
_MALFORMED_ENDS = [
    pytest.param("2026-13-45", id="impossible-month-day"),
    pytest.param("not-a-date", id="not-a-date"),
    pytest.param("20260703", id="basic-format"),
    pytest.param("２０２６-０７-０３", id="fullwidth-digits"),
]


@pytest.mark.parametrize("raw_end", _MALFORMED_ENDS)
def test_malformed_period_end_names_the_field(raw_end: str) -> None:
    """A malformed ``period.end`` string chains the parse error under a named one."""
    cell = deepcopy(case("same_number_two_headers")["cells"][0])
    cell["period"] = dict(cell["period"])
    cell["period"]["end"] = raw_end
    with pytest.raises(
        ValueError, match=re.escape("cell period.end must be a YYYY-MM-DD string")
    ) as caught:
        enroll_stated_period(_one_release(cells=[cell]), tolerance_days=3)
    assert isinstance(caught.value.__cause__, ValueError)
