"""Enroll the stated period and fiscal label beside a quoted derivation (W10-A).

One join, two owners, no rewrite.  ``enroll_stated_period`` already copies a
shared non-empty ``period.fiscal_label`` onto each edition document and returns
each cell's stated end WITHOUT applying ``tolerance_days`` (a 3 July cell stays
3 July).  ``derive_result_cash`` already returns the closed derivation dict,
including ``status == "refused"`` with ``value is None``.  Neither today
carries the label or the stated end onto the certified number: the dossier
quotes ``value`` and copies only ``_DERIVATION_REF_FIELDS``.

This module is the missing join.  It imports both owners — it does not copy
``stated_period_end``, ``enroll_stated_period`` or ``derive_result_cash``, it
does not add ``period`` to ``_ready_result``, and it never recomputes a refused
derivation.  The returned record is a plain dict with keys ``derivation``,
``stated_ends``, ``presented_fiscal_label``, ``hold`` and ``documents``.

Synthetic cases only: a non-synthetic case is refused by ``extract_case_cells``
through the same ``_require_synthetic`` gate ``enroll_stated_period`` runs.
``quality.rights_profile`` is never copied onto a document's
``rights_profile`` — that stays the class default, exactly as
``enroll_stated_period`` leaves it.  ``documents`` is a tuple of
``engine.company_intelligence.documents.SourceDocument``.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from engine.company_intelligence.industrials_period_enrollment import (
    enroll_stated_period,
)
from engine.company_intelligence.industrials_source_facts import extract_case_cells
from engine.fundamental_forensics.industrials_result_cash import derive_result_cash


def enroll_certified_comparison(
    case: Mapping[str, Any],
    *,
    formula: str,
    comparison_receipt: Mapping[str, Any],
    tolerance_days: int,
) -> dict[str, Any]:
    """Return the certified-comparison record for one synthetic case.

    ``derivation`` is the ``derive_result_cash`` dict quoted verbatim over the
    case's own cells (``extract_case_cells(case)``) — a refusal arrives with
    ``status == "refused"`` and ``value is None`` and is never recomputed here.
    ``stated_ends`` and ``presented_fiscal_label`` / ``hold`` come from one
    ``enroll_stated_period`` call with the given ``tolerance_days``: a shared
    non-empty label is copied onto every returned document; otherwise the
    label is ``None`` and ``hold`` names ``no_cell_fiscal_label`` or
    ``fiscal_label_disagreement``.
    """
    enrolled = enroll_stated_period(case, tolerance_days=tolerance_days)
    derivation = derive_result_cash(
        formula,
        extract_case_cells(case),
        comparison_receipt=comparison_receipt,
    )
    return {
        "derivation": derivation,
        "stated_ends": enrolled.stated_ends,
        "presented_fiscal_label": enrolled.label,
        "hold": enrolled.hold,
        "documents": enrolled.documents,
    }


__all__ = ["enroll_certified_comparison"]
