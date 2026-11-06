"""Enroll a synthetic cell's stated fiscal label onto its native document.

``stated_period_end`` and ``edition_documents`` stay in the modules that
already own them. This function copies ``period.fiscal_label`` onto
``presented_fiscal_label`` when every cell shares one non-empty label, and
it writes each cell's stated end back without applying ``tolerance_days``.
"""
from __future__ import annotations

import re
from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass, replace
from datetime import date
from typing import Any

from engine.company_intelligence.documents import SourceDocument
from engine.company_intelligence.industrials_fiscal import (
    check_tolerance_days,
    stated_period_end,
)
from engine.company_intelligence.industrials_source_facts import (
    edition_documents,
    extract_case_cells,
)


@dataclass(frozen=True, slots=True)
class StatedPeriodEnrollment:
    """Cell copies, stated ends, documents, the shared label, and any hold."""

    cells: tuple[dict[str, Any], ...]
    stated_ends: tuple[date, ...]
    documents: tuple[SourceDocument, ...]
    label: str | None
    hold: str | None


def enroll_stated_period(
    case: Mapping[str, Any],
    *,
    tolerance_days: int,
) -> StatedPeriodEnrollment:
    """Return the case's cells and documents with the stated period enrolled.

    A shared non-empty ``period.fiscal_label`` is copied onto each document
    with ``dataclasses.replace``. Zero cells leave the label null and name
    ``no_cell_fiscal_label``. Distinct labels leave it null and name
    ``fiscal_label_disagreement``. The cell's ``quality.rights_profile`` is
    not copied; ``rights_profile`` stays the class default.

    ``tolerance_days`` is checked first, so a bad tolerance is refused before
    any case-shape or cell-shape error the same call would otherwise raise.
    """
    check_tolerance_days(tolerance_days)
    cells = extract_case_cells(case)
    if not cells:
        # No stated end to return; the tolerance was already checked above.
        return StatedPeriodEnrollment(
            cells=(),
            stated_ends=(),
            documents=edition_documents(case),
            label=None,
            hold="no_cell_fiscal_label",
        )

    copied: list[dict[str, Any]] = []
    stated_ends: list[date] = []
    for cell in cells:
        enrolled_cell, stated_end = _with_stated_end(
            cell, tolerance_days=tolerance_days
        )
        copied.append(enrolled_cell)
        stated_ends.append(stated_end)
    label, hold = _shared_label(copied)
    documents = edition_documents(case)
    if label is not None:
        documents = tuple(
            replace(document, presented_fiscal_label=label) for document in documents
        )
    return StatedPeriodEnrollment(
        cells=tuple(copied),
        stated_ends=tuple(stated_ends),
        documents=documents,
        label=label,
        hold=hold,
    )


def _with_stated_end(
    cell: Mapping[str, Any],
    *,
    tolerance_days: int,
) -> tuple[dict[str, Any], date]:
    """Return ``(cell copy, stated end)``. A non-mapping ``period`` is refused
    as ``cell period is required``; a non-``str`` or malformed ``period.end``
    is refused as ``cell period.end must be a YYYY-MM-DD string``, naming the
    field instead of leaking ``date.fromisoformat``'s bare message. Chaining
    differs per branch: a non-mapping ``period`` and a non-``str`` end are
    each a bare ``raise`` and chain nothing (``__cause__`` and
    ``__context__`` are both ``None``);
    the shape gate below chains a SYNTHETIC shape error whose text begins
    ``expected exactly YYYY-MM-DD``, not a parse error; only the parser
    branch chains ``date.fromisoformat``'s own
    ``ValueError``. The gate runs before the parser and admits exactly the
    ASCII ``YYYY-MM-DD`` shape, so it also refuses forms that the 3.12 parser
    itself accepts — ``20260703``, week-without-day ``2026-W27`` and
    trailing-garbage ``02071203:6``. ``flags=re.ASCII`` is load-bearing for
    fullwidth digits: an unflagged ``\\d`` matches them, the gate admits the
    string, and the parser's message lands in ``__cause__`` instead.
    """
    period = cell.get("period")
    if not isinstance(period, Mapping):
        raise ValueError("cell period is required")
    raw_end = period.get("end")
    if not isinstance(raw_end, str):
        raise ValueError("cell period.end must be a YYYY-MM-DD string")
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw_end, flags=re.ASCII) is None:
        raise ValueError("cell period.end must be a YYYY-MM-DD string") from ValueError(
            f"expected exactly YYYY-MM-DD, got {raw_end!r}"
        )
    try:
        parsed_end = date.fromisoformat(raw_end)
    except ValueError as exc:
        raise ValueError("cell period.end must be a YYYY-MM-DD string") from exc
    stated_end = stated_period_end(parsed_end, tolerance_days=tolerance_days)
    copied = deepcopy(dict(cell))
    copied_period = dict(copied["period"])
    copied_period["end"] = stated_end.isoformat()
    copied["period"] = copied_period
    return copied, stated_end


def _shared_label(
    cells: tuple[dict[str, Any], ...] | list[dict[str, Any]],
) -> tuple[str | None, str | None]:
    """``(label, hold)``. The label is copied only when every cell agrees."""
    seen: list[str | None] = []
    for cell in cells:
        period = cell.get("period")
        raw = period.get("fiscal_label") if isinstance(period, Mapping) else None
        if isinstance(raw, str) and raw.strip():
            seen.append(raw)
        else:
            seen.append(None)
    present = {label for label in seen if label is not None}
    if len(present) == 1 and all(label == next(iter(present)) for label in seen):
        return next(iter(present)), None
    if not present:
        return None, "no_cell_fiscal_label"
    return None, "fiscal_label_disagreement"
