"""Enroll the stated fiscal label onto the native edition record (W8-A).

The synthetic cell already carries ``FY2026 Q2`` and period end 3 July.
Enrollment copies that label onto ``presented_fiscal_label`` and must not
let a three-day tolerance rewrite the cell end to 30 June.
"""
from __future__ import annotations

import builtins
import re
import sys
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
# Two-sided: each param also names the refusal the SAME input raises once the
# tolerance is valid. Without that half, the preemption assertion would pass
# on an input that raises nothing at all.
_SHAPE_ERRORS = [
    pytest.param(
        _cell_without_period,
        ValueError,
        "cell period is required",
        id="cell-without-period",
    ),
    pytest.param(
        lambda: _one_release(cells="nope"),
        TypeError,
        "cells must be a list",
        id="cells-not-a-list",
    ),
    pytest.param(
        lambda: "not-a-case",
        ValueError,
        "edition input must be a synthetic case",
        id="case-not-a-mapping",
    ),
]


@pytest.mark.parametrize("build,expected,message", _SHAPE_ERRORS)
def test_bad_tolerance_preempts_shape_errors(
    build: Callable[[], object], expected: type[Exception], message: str
) -> None:
    """A bad ``tolerance_days`` preempts a shape error the same input does raise."""
    with pytest.raises(
        TypeError, match=re.escape("tolerance_days must be an int, not bool")
    ):
        enroll_stated_period(build(), tolerance_days=True)
    with pytest.raises(expected, match=re.escape(message)):
        enroll_stated_period(build(), tolerance_days=3)


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
    """A cell carrying no ``period`` raises with the field named in the message.

    The non-mapping-``period`` branch is a bare ``raise``, so it chains nothing:
    ``__cause__`` is ``None``, and ``__context__`` is ``None`` as well (measured
    ``True`` on 3.12.3, where no other exception is in flight when it raises).
    This is the other half of the split documented on ``_with_stated_end``: only
    the shape gate and the parser chain. A regression that routes this refusal
    through either of them chains something and fails here.
    """
    cell = deepcopy(case("same_number_two_headers")["cells"][0])
    cell.pop("period")
    with pytest.raises(
        ValueError, match=re.escape("cell period is required")
    ) as caught:
        enroll_stated_period(_one_release(cells=[cell]), tolerance_days=3)
    assert caught.value.__cause__ is None
    assert caught.value.__context__ is None


def test_non_iso_period_end_is_refused() -> None:
    """A non-string ``period.end`` raises with the field named in the message.

    The non-``str``-``end`` branch is a bare ``raise``, so it chains nothing:
    ``__cause__`` is ``None``, and ``__context__`` is ``None`` as well (measured
    ``True`` on 3.12.3). An ``int`` end such as this one must be refused for its
    TYPE here, before the shape gate ever sees it -- if the type check were
    dropped, the same value would fall to the shape gate, which chains its
    synthetic shape error, and the assertion below would fail.
    """
    cell = deepcopy(case("same_number_two_headers")["cells"][0])
    cell["period"] = dict(cell["period"])
    cell["period"]["end"] = 20260703
    with pytest.raises(
        ValueError, match=re.escape("cell period.end must be a YYYY-MM-DD string")
    ) as caught:
        enroll_stated_period(_one_release(cells=[cell]), tolerance_days=3)
    assert caught.value.__cause__ is None
    assert caught.value.__context__ is None


# Refusal shape is documented on ``_with_stated_end``. The two lists below
# split the malformed strings by WHICH branch refuses them, and the chained
# ``__cause__`` proves which branch ran: the ASCII-only shape gate chains its
# own synthetic "expected exactly YYYY-MM-DD" error, the parser chains
# ``date.fromisoformat``'s message. Measured on this 3.12: the parser ADMITS
# "2026-W27" (date(2026, 6, 29)) and "02071203:6" (date(207, 12, 3)), so only
# the gate can refuse those, and it also refuses "20260703". The fullwidth
# form is refused by both branches, so it is the flag discriminator: without
# ``flags=re.ASCII`` the gate's digit class matches fullwidth digits, the gate
# admits the string, and the parser's different message is what gets chained.
_SHAPE_REFUSED_ENDS = [
    pytest.param("20260703", id="basic-format"),
    pytest.param("２０２６-０７-０３", id="fullwidth-digits"),
    pytest.param("not-a-date", id="not-a-date"),
    pytest.param("2026-W27", id="week-without-day"),
    pytest.param("02071203:6", id="trailing-garbage"),
]

# Exact ASCII ``YYYY-MM-DD`` shape, so the gate admits them and the parser
# refuses them on value range alone.
_PARSE_REFUSED_ENDS = [
    pytest.param("2026-13-45", id="impossible-month-day"),
    pytest.param("2026-02-30", id="impossible-day"),
    pytest.param("0000-01-01", id="year-zero"),
]


# Two read-only probes of THIS interpreter, used below to derive the
# parser-admitted subset of ``_SHAPE_REFUSED_ENDS`` instead of restating it.
def _raw_end_of(param: object) -> str:
    """The end string carried by a ``_SHAPE_REFUSED_ENDS`` entry.

    Entries are ``pytest.param`` objects today (``object.values`` is a tuple);
    bare strings are read too, so an append of either shape joins the derived
    guard instead of dropping out when the attribute probe misses. An entry
    exposing a non-sequence ``.values`` (e.g. a dict) is read as a bare entry;
    the guard below keeps it from being subscripted. Without that guard the two
    crash sites differ -- IN ``_SHAPE_REFUSED_ENDS`` the entry crashes module
    collection at the ``_SHAPE_REFUSED_ENDS_PARSER_ADMITTED`` derivation, while
    the direct call in the non-str test fails only that test.
    """
    values = getattr(param, "values", None)
    if not isinstance(values, (tuple, list)):
        return param
    return values[0]


def _parser_admits(raw_end: str) -> bool:
    """True when THIS interpreter's ``date.fromisoformat`` accepts ``raw_end``.

    A non-str entry is treated as not parser-admitted: ``_raw_end_of`` reads
    bare entries too, and the ``TypeError`` ``date.fromisoformat`` raises on a
    non-str must not crash import/collection of this module.
    """
    try:
        date.fromisoformat(raw_end)
    except (TypeError, ValueError):
        return False
    return True


# DERIVED, not restated: every entry of ``_SHAPE_REFUSED_ENDS`` this running
# interpreter's ``date.fromisoformat`` accepts. A new parser-admitted shape
# appended to that list joins the guard below on its own; only entries this
# parser refuses drop out, and those are exactly the entries whose
# gate-vs-parser attribution this interpreter cannot prove.
_SHAPE_REFUSED_ENDS_PARSER_ADMITTED = [
    param for param in _SHAPE_REFUSED_ENDS if _parser_admits(_raw_end_of(param))
]


def _case_with_end(raw_end: object) -> dict:
    """The synthetic release with one cell whose ``period.end`` is ``raw_end``."""
    cell = deepcopy(case("same_number_two_headers")["cells"][0])
    cell["period"] = dict(cell["period"])
    cell["period"]["end"] = raw_end
    return _one_release(cells=[cell])


@pytest.mark.parametrize("raw_end", _SHAPE_REFUSED_ENDS)
def test_shape_refused_period_end_names_the_field(raw_end: str) -> None:
    """The shape gate refuses before parsing and chains ITS OWN shape error."""
    with pytest.raises(
        ValueError, match=re.escape("cell period.end must be a YYYY-MM-DD string")
    ) as caught:
        enroll_stated_period(_case_with_end(raw_end), tolerance_days=3)
    assert isinstance(caught.value.__cause__, ValueError)
    assert "expected exactly YYYY-MM-DD" in str(caught.value.__cause__)


@pytest.mark.parametrize("raw_end", _PARSE_REFUSED_ENDS)
def test_parse_refused_period_end_chains_the_parser_error(raw_end: str) -> None:
    """The gate admits these, so the parser's own error is what gets chained."""
    with pytest.raises(
        ValueError, match=re.escape("cell period.end must be a YYYY-MM-DD string")
    ) as caught:
        enroll_stated_period(_case_with_end(raw_end), tolerance_days=3)
    assert isinstance(caught.value.__cause__, ValueError)
    assert "expected exactly" not in str(caught.value.__cause__)


_SKIP_PRE_311_PARSER_ADMITTED = pytest.mark.skipif(
    sys.version_info < (3, 11),
    reason="all three parser-admitted forms these guards derive only parse "
    "on 3.11+ -- the basic form without hyphens (20260703), the ISO week "
    "without a weekday (2026-W27) and the trailing-colon form (02071203:6); "
    "under 3.11 the version premise these tests guard does not exist",
)


@_SKIP_PRE_311_PARSER_ADMITTED
@pytest.mark.parametrize("raw_end", _SHAPE_REFUSED_ENDS_PARSER_ADMITTED)
def test_parser_admitted_subset_of_shape_refused_forms_is_gate_refused(
    raw_end: str,
) -> None:
    """Pin the parser-ADMITTED subset of ``_SHAPE_REFUSED_ENDS``, per shape.

    The shape list and the parse list say different things only because the
    3.11+ ``date.fromisoformat`` ADMITS the parser-admitted forms -- the basic
    form without hyphens, the ISO week without a weekday, and the trailing-colon
    form -- while the ASCII-only shape gate refuses them. If a future Python
    tightened the parser so that it refused them too, both parametrized tests
    would keep passing while the shape list silently lost its point: every
    "shape-refused" form could then be refused by the parser branch alone, and
    ``test_shape_refused_period_end_names_the_field`` would no longer prove that
    the gate, rather than the parser, did the refusing.

    The parameters are DERIVED from ``_SHAPE_REFUSED_ENDS``, so a parser-admitted
    shape added there joins this guard automatically instead of silently not
    joining it, and this guard asserts BOTH halves of the attribution for each
    of them: the interpreter admits the form, yet the engine still refuses it
    with the gate's own chained shape error. Measured on this 3.12.3 the parser
    admits ``20260703`` as ``date(2026, 7, 3)``, ``2026-W27`` as
    ``date(2026, 6, 29)`` and ``02071203:6`` as ``date(207, 12, 3)``.
    """
    assert isinstance(date.fromisoformat(raw_end), date)
    with pytest.raises(
        ValueError, match=re.escape("cell period.end must be a YYYY-MM-DD string")
    ) as caught:
        enroll_stated_period(_case_with_end(raw_end), tolerance_days=3)
    assert isinstance(caught.value.__cause__, ValueError)
    assert "expected exactly YYYY-MM-DD" in str(caught.value.__cause__)


@_SKIP_PRE_311_PARSER_ADMITTED
def test_parser_admitted_subset_of_shape_refused_forms_meets_the_floor() -> None:
    """Floor the derived guard so it can never pass by collecting nothing.

    ``_SHAPE_REFUSED_ENDS_PARSER_ADMITTED`` is filtered on the running
    interpreter, so a Python that refused every shape-listed form would empty
    it -- and a parametrized test over an empty set asserts nothing (measured on
    this pytest 9.1.1: one SKIPPED item, "got empty parameter set", suite still
    green). The floor below is load-bearing: the three forms #9338 measured must
    still be IN the derived set, so the premise failing is a failure, not a
    silent skip.
    """
    derived = {_raw_end_of(param) for param in _SHAPE_REFUSED_ENDS_PARSER_ADMITTED}
    floor = {"20260703", "2026-W27", "02071203:6"}
    assert floor <= derived, (
        f"date.fromisoformat no longer admits {sorted(floor - derived)} on "
        f"Python {sys.version_info[:2]}; the "
        "shape list has lost its discriminating power and the parametrized "
        f"guard collected {len(derived)} of {len(_SHAPE_REFUSED_ENDS)} shapes"
    )


def test_parser_admits_treats_non_str_entries_as_not_admitted() -> None:
    """Pin exactly the four forms asserted below.

    ``None`` and the int ``20260703`` reach ``date.fromisoformat`` as non-str
    and raise ``TypeError`` (measured on this 3.12.3: "fromisoformat: argument
    must be str"). The dict-shaped entry ``{"a": 1}`` is read by ``_raw_end_of``
    as a bare entry -- its ``.values`` is the bound method ``dict.values``, not
    a sequence, so the guard in ``_raw_end_of`` returns the dict unchanged and
    it reaches ``date.fromisoformat`` as a non-str. The compact form ``"20260703"``
    as a STR is version-bound: 3.11+ admits it, earlier interpreters refuse it
    with ``ValueError``. Each non-str form is asserted ``False`` here; the
    version-bound str form surfaces whatever this interpreter's parser decides.
    """
    assert _parser_admits(None) is False
    assert _parser_admits(20260703) is False
    assert _parser_admits(_raw_end_of({"a": 1})) is False
    assert _parser_admits("20260703") == (sys.version_info >= (3, 11))


def _matches_probe(obj: object) -> bool:
    """``obj`` is an ``Exception`` subclass outside ``(TypeError, ValueError)`` whose
    ``obj("probe")`` constructs and renders ``"probe"`` in its ``str``."""
    if not isinstance(obj, type):
        return False
    if not issubclass(obj, Exception):
        return False
    if issubclass(obj, (TypeError, ValueError)):
        return False
    try:
        instance = obj("probe")
    except Exception:
        return False
    return "probe" in str(instance)


# Derived from ``builtins``: every public class X with
# ``issubclass(X, Exception) and not issubclass(X, (TypeError, ValueError))``
# such that ``X("probe")`` constructs and ``"probe" in str(X("probe"))``.
# Sorted by ``X.__name__``; the id set follows the running interpreter's
# builtins (CI pins 3.12.13 in ``.github/workflows/ci.yml``). Duplicates by
# class object are coalesced (multiple builtin names alias to one class).
_PROBE_EXCEPTIONS = tuple(
    sorted(
        {
            obj
            for name, obj in vars(builtins).items()
            if not name.startswith("_") and _matches_probe(obj)
        },
        key=lambda cls: cls.__name__,
    )
)


@pytest.mark.parametrize(
    "probe_exc",
    _PROBE_EXCEPTIONS,
    ids=[cls.__name__ for cls in _PROBE_EXCEPTIONS],
)
def test_parser_admits_does_not_swallow_exceptions_outside_type_or_value_errors(
    monkeypatch: pytest.MonkeyPatch, probe_exc: type[Exception]
) -> None:
    """Every exception outside ``(TypeError, ValueError)`` escapes ``_parser_admits``.

    The stub replaces the local ``date`` binding in THIS module and raises the
    parameter's type from ``fromisoformat``. The probe is parametrized over
    ``_PROBE_EXCEPTIONS`` -- every public builtin ``Exception`` subclass outside
    ``(TypeError, ValueError)`` that this interpreter constructs with ``"probe"``.
    Widening the handler to a type turns the ids of that type and of its probed
    subclasses red, and ``except Exception:`` turns every id red. ``match="probe"``
    binds the message: a handler that catches the probe and raises the same type
    with a different message fails to match.
    """
    class _ProbeDate:
        @staticmethod
        def fromisoformat(value: object) -> object:
            raise probe_exc("probe")

    monkeypatch.setattr(sys.modules[__name__], "date", _ProbeDate)
    with pytest.raises(probe_exc, match="probe") as excinfo:
        _parser_admits("2026-07-03")
    assert type(excinfo.value) is probe_exc
