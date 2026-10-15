"""Place one certified Industrials comparison on a caller page dict (W10-B).

The first consumer-visible Industrials signal: admit a synthetic case, build the
certified record through W10-A's ``enroll_certified_comparison`` — which quotes
``derive_result_cash`` and enrolls the stated period — and write exactly one key
onto the caller's page mapping, ``page["industrials_certified_comparison"]``.
A reader of that key sees either a quoted ready value with the shared fiscal
label and the cell's stated end, or a refusal whose ``value`` is ``None``. A
refusal is still a published signal: the key is present either way, so a
mislabeled share can never arrive on that key as segment mix.

Placement is all-or-nothing. Every admission check, every lookup on the caller
page, and the whole payload build happen before the first write, so a raising
lookup leaves the page exactly as it was. A ``__setitem__`` that raises on a
caller-supplied mapping is outside the guarantee: undoing such a write would
itself call ``__setitem__``.

This module owns no derivation and no period logic. It copies the derivation's
``status`` / ``value`` / ``formula`` / ``formula_version`` / ``limitations`` and
the enrollment's label, stated end and ``hold``; it never recomputes a number,
never refuses placement because a chronology is held (R-IND-07: the certified
number and the chronology are different sections), never copies a
``rights_profile``, and imports nothing from ``sector_intelligence``,
``market_ontology`` or ``theme_graph``. Synthetic cases only; no network, no
issuer lookup.
"""
from __future__ import annotations

from collections.abc import Mapping, MutableMapping, Sequence
from datetime import date
from typing import Any

from engine.company_intelligence.industrials_certified_enrollment import (
    enroll_certified_comparison,
)
from engine.fundamental_forensics.industrials_result_cash import ALLOWED_FORMULAS

#: The one page key a later renderer reads. Placed whole, replaced whole.
PAGE_KEY = "industrials_certified_comparison"

#: The closed payload shape: ready and refused payloads carry exactly these.
PAYLOAD_KEYS: tuple[str, ...] = (
    "status",
    "value",
    "formula",
    "formula_version",
    "presented_fiscal_label",
    "stated_period_end",
    "limitations",
    "hold",
)


class IndustrialsCertifiedSignalRefusal(ValueError):
    """The page refuses the case, or refuses the page. ``str(exc)`` is the code."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code

    def __str__(self) -> str:
        return self.code


def apply_industrials_certified_signal(
    case: Mapping[str, Any],
    page: MutableMapping[str, Any],
    *,
    formula: str,
    comparison_receipt: Mapping[str, Any],
    tolerance_days: int,
) -> None:
    """Enroll one synthetic case and place its certified payload on ``page``.

    The three refusals below are caller errors, raised before anything is
    written: ``case_not_synthetic`` when ``case["synthetic"] is not True`` (or
    ``case`` is no mapping at all), ``page_not_mapping`` when the caller hands
    something that cannot receive the key, and ``formula_unknown`` when
    ``formula`` is outside ``derive_result_cash``'s own closed
    ``ALLOWED_FORMULAS`` — the owner's vocabulary is read by reference, never
    copied here.

    A data-level refusal is NOT an error: ``derive_result_cash`` answers with
    ``status == "refused"`` and ``value is None``, and that refusal is published
    on the same key, with the enrollment's label, stated end and ``hold`` beside
    it. An enrollment or derivation error raised after these checks also leaves
    the page as it was, because the payload is built before the single write.
    """
    if not isinstance(case, Mapping) or case.get("synthetic") is not True:
        raise IndustrialsCertifiedSignalRefusal("case_not_synthetic")
    if not isinstance(page, MutableMapping):
        raise IndustrialsCertifiedSignalRefusal("page_not_mapping")
    if formula not in ALLOWED_FORMULAS:
        raise IndustrialsCertifiedSignalRefusal("formula_unknown")

    # The only read of the caller page is this lookup, and it happens before the
    # first write, so a page whose ``get`` raises is left exactly as it was.
    page.get(PAGE_KEY)

    record = enroll_certified_comparison(
        case,
        formula=formula,
        comparison_receipt=comparison_receipt,
        tolerance_days=tolerance_days,
    )
    page[PAGE_KEY] = _certified_payload(record)


def _certified_payload(record: Mapping[str, Any]) -> dict[str, Any]:
    """Build the closed payload from one ``enroll_certified_comparison`` record.

    Every field is a copy of what the owners already returned — the derivation
    dict quoted verbatim and the enrollment's label, stated ends and hold. The
    derivation's ``status`` is carried as it arrives, so ``ready``, ``limited``
    and ``refused`` all reach the reader without this module deciding anything.
    ``rights_profile`` is never read, so it can never be copied.
    """
    derivation = record["derivation"]
    fields = {
        "status": derivation["status"],
        "value": derivation["value"],
        "formula": derivation["formula"],
        "formula_version": derivation["formula_version"],
        "presented_fiscal_label": record["presented_fiscal_label"],
        "stated_period_end": _shared_stated_period_end(record["stated_ends"]),
        "limitations": list(derivation["limitations"]),
        "hold": record["hold"],
    }
    # Projecting through ``PAYLOAD_KEYS`` is what makes the shape closed: a
    # field a later edit adds here without adding to the declared tuple cannot
    # reach the page, and a declared key nothing supplies fails loudly instead
    # of placing a half-shaped signal.
    return {key: fields[key] for key in PAYLOAD_KEYS}


def _shared_stated_period_end(stated_ends: Sequence[date]) -> str | None:
    """One ISO stated end for the page, or ``None``.

    The enrollment owner returns one stated end per cell, un-snapped by
    ``tolerance_days`` (a 3 July cell stays 3 July). The closed payload names a
    single period, so the end is placed only when the cells agree on one: no
    cells and a disagreeing pair both place ``None`` rather than silently
    promoting one cell's date into the other's period. The label next to it
    follows the owner's same rule (``enroll_stated_period`` nulls a label no
    cell shares and names the hold).
    """
    if not stated_ends:
        return None
    first = stated_ends[0]
    if all(end == first for end in stated_ends):
        return first.isoformat()
    return None


__all__ = [
    "PAGE_KEY",
    "PAYLOAD_KEYS",
    "IndustrialsCertifiedSignalRefusal",
    "apply_industrials_certified_signal",
]
