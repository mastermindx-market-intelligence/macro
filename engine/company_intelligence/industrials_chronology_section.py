"""Chronology-section dict the dossier renders until a selector ruling (W10-C).

Publishes one dict the source-edition section of the dossier can render while
``financial_dossier.select_editions`` and ``assess_dossier_comparison`` stay
unbound: ``status`` is ``"held"`` and ``blocks`` is the same frozenset W8-B
pins. The dict carries the enrolled ``presented_fiscal_label`` and stated
ends, and ``SourceDocument.to_payload()`` for each document. Documents come
from ``enroll_stated_period(...).documents`` so the label is on the payload;
blocks come from ``edition_hold(case)["blocks"]``. When a later ruling makes
``financial_dossier.select_editions`` callable, the W8-B frozenset pin turns
red and this section's ``blocks`` pin turns red in the same change.

This module does not define ``select_editions`` or ``assess_dossier_comparison``.
It does not add a field to ``SourceDocument`` and does not add a
``document_kind``. It does not import ``engine.theme_graph.theme_state`` to
manufacture ``KNOWLEDGE_TIME_UNPROVEN``. It does not implement cutoff
exclusion under another function name. It does not import
``guidance_history``. The hold is not a substitute selector.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from engine.company_intelligence.industrials_edition_record import edition_hold
from engine.company_intelligence.industrials_period_enrollment import (
    enroll_stated_period,
)


def chronology_section(
    case: Mapping[str, Any],
    *,
    tolerance_days: int,
) -> dict[str, Any]:
    """Return the held chronology-section dict for the dossier source-edition slot.

    Closed keys: ``status``, ``blocks``, ``presented_fiscal_label``,
    ``stated_ends``, ``hold``, ``documents`` (tuple of ``to_payload()`` dicts).
    """
    enrollment = enroll_stated_period(case, tolerance_days=tolerance_days)
    documents = tuple(document.to_payload() for document in enrollment.documents)
    return {
        "status": "held",
        "blocks": edition_hold(case)["blocks"],
        "presented_fiscal_label": enrollment.label,
        "stated_ends": enrollment.stated_ends,
        "hold": enrollment.hold,
        "documents": documents,
    }
