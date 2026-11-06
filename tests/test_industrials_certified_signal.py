"""Place one certified Industrials comparison on a caller page dict (W10-B).

:func:`apply_industrials_certified_signal` is the first consumer-visible
Industrials signal. It admits a synthetic case, builds the certified record
through W10-A's ``enroll_certified_comparison``, and writes exactly one key,
``page["industrials_certified_comparison"]``, all-or-nothing. A reader of that
key sees either a quoted ready value carrying ``FY2026 Q2`` / ``2026-07-03`` or
a refusal whose ``value`` is ``None`` — a refusal is still a published signal,
so the key is present in both cases. Nothing here recomputes a number: the
placed ``value``, ``formula``, ``formula_version`` and ``limitations`` arrive
verbatim from ``derive_result_cash`` through the enrollment join, and a held
chronology never suppresses them (the enrollment ``hold`` is copied, not used as
a placement gate).

Synthetic fixtures only. No network, no issuer lookup, no ``rights_profile`` on
the placed payload.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

import pytest

from engine.company_intelligence.industrials_certified_signal import (
    IndustrialsCertifiedSignalRefusal,
    apply_industrials_certified_signal,
)
from engine.company_intelligence.industrials_source_facts import extract_case_cells
from engine.fundamental_forensics.industrials_result_cash import derive_result_cash
from tests.industrials_result_cash_helpers import case, comparison

PAGE_KEY = "industrials_certified_comparison"

#: The closed payload shape (spec constraint 4) — declared here, in the test, so
#: a production-side key rename cannot move the goalposts with it.
PAYLOAD_KEYS = frozenset(
    {
        "status",
        "value",
        "formula",
        "formula_version",
        "presented_fiscal_label",
        "stated_period_end",
        "limitations",
        "hold",
    }
)


def _receipt(loaded: dict[str, Any]) -> dict[str, Any]:
    return comparison("same_period", extract_case_cells(loaded))


def test_ready_share_places_label_and_july_3() -> None:
    """A ready share pair places the label, the 3 July end and the quote."""
    loaded = case("same_number_two_headers")
    cells = extract_case_cells(loaded)
    quoted = derive_result_cash(
        "margin_pct",
        deepcopy(cells),
        comparison_receipt=comparison("same_period", cells),
    )
    # Pinned by measurement at this ref, not by assumption: these two
    # ``revenue_share_pct`` cells are one same-period pair the qualifier
    # accepts, so ``margin_pct`` is the ready formula on this fixture.
    assert quoted["status"] == "ready"

    page: dict[str, Any] = {}
    apply_industrials_certified_signal(
        loaded,
        page,
        formula="margin_pct",
        comparison_receipt=_receipt(loaded),
        tolerance_days=3,
    )

    placed = page[PAGE_KEY]
    assert frozenset(placed) == PAYLOAD_KEYS
    assert placed["status"] == "ready"
    assert placed["presented_fiscal_label"] == "FY2026 Q2"
    assert placed["stated_period_end"] == "2026-07-03"
    assert placed["value"] == quoted["value"]
    assert placed["formula"] == quoted["formula"]
    assert placed["formula_version"] == quoted["formula_version"]
    assert placed["limitations"] == quoted["limitations"]
    assert placed["hold"] is None


def test_mislabeled_denominator_places_refusal_with_no_value() -> None:
    """A swapped engineering denominator publishes a refusal, not a number.

    The refusal lands on the same key a later renderer reads, so a mislabeled
    share can never appear there as segment mix (IND-R206 conjunct 2, placed,
    not re-derived).
    """
    loaded = case("same_number_two_headers")
    swapped = False
    for candidate in loaded["cells"]:
        dimensions = candidate.get("business_dimensions") or {}
        if dimensions.get("segment") == "engineering":
            dimensions["denominator"] = "group_revenue"
            swapped = True
    assert swapped, "fixture no longer carries an engineering segment to swap"

    page: dict[str, Any] = {}
    apply_industrials_certified_signal(
        loaded,
        page,
        formula="margin_pct",
        comparison_receipt=_receipt(loaded),
        tolerance_days=3,
    )

    placed = page[PAGE_KEY]
    assert PAGE_KEY in page
    assert placed["status"] == "refused"
    assert "mislabeled_denominator" in placed["limitations"]
    assert placed["value"] is None
    assert placed["formula"] == "margin_pct"
    assert placed["presented_fiscal_label"] == "FY2026 Q2"
    assert placed["stated_period_end"] == "2026-07-03"


def test_unknown_accounting_places_refusal_with_no_value() -> None:
    """An unknown basis publishes the owner's existing refusal, value None.

    The limitation is ``derive_result_cash``'s own ``required_basis_unknown``;
    this module names no refusal code of its own for it.
    """
    loaded = case("same_number_two_headers")
    copy_cell = deepcopy(loaded["cells"][0])
    copy_cell["basis"] = {**copy_cell["basis"], "accounting": "Unknown "}
    loaded["cells"][0] = copy_cell

    page: dict[str, Any] = {}
    apply_industrials_certified_signal(
        loaded,
        page,
        formula="margin_pct",
        comparison_receipt=_receipt(loaded),
        tolerance_days=3,
    )

    placed = page[PAGE_KEY]
    assert PAGE_KEY in page
    assert placed["value"] is None
    assert placed["status"] == "refused"
    assert "required_basis_unknown" in placed["limitations"]


def test_non_synthetic_writes_nothing() -> None:
    """A case that is not explicitly synthetic is refused before any write."""
    receipt_holder = case("same_number_two_headers")
    loaded = case("same_number_two_headers")
    loaded["synthetic"] = False
    page: dict[str, Any] = {}

    with pytest.raises(IndustrialsCertifiedSignalRefusal) as caught:
        apply_industrials_certified_signal(
            loaded,
            page,
            formula="margin_pct",
            comparison_receipt=_receipt(receipt_holder),
            tolerance_days=3,
        )

    assert str(caught.value) == "case_not_synthetic"
    assert page == {}


def test_raising_setitem_is_outside_the_pre_write_guarantee() -> None:
    """The guarantee covers lookups, not a caller ``__setitem__`` that raises.

    Undoing such a write would itself call ``__setitem__``, so the exception
    propagates and the key stays absent: the guarantee this module makes is
    about lookups before the first write, and a write a caller refuses is not
    undone by the signal's owner.
    """

    class _WriteRefuses(dict):
        def __setitem__(self, key: Any, value: Any) -> None:
            raise RuntimeError("caller page refuses every write")

    loaded = case("same_number_two_headers")
    page = _WriteRefuses()

    with pytest.raises(RuntimeError):
        apply_industrials_certified_signal(
            loaded,
            page,
            formula="margin_pct",
            comparison_receipt=_receipt(loaded),
            tolerance_days=3,
        )

    assert PAGE_KEY not in page
