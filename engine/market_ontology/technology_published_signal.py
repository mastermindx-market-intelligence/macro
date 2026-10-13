"""Publish one technology economic-change dossier onto the company-first fragment.

The caller supplies the dossier. This module calls the fragment renderer. It
does not import the composer or the curation contract, and it does not fetch,
write, or read a clock.
"""
from __future__ import annotations

import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from engine.market_ontology.technology_dossier_page import (
    render_technology_dossier_page,
)

__all__ = ["TechnologyPublishedSignalRefusal", "publish_technology_dossier"]

_TEMPLATE = (
    Path(__file__).resolve().parents[2]
    / "templates"
    / "_technology_economic_change_page.html.j2"
)
_CURATION_REVISION_RE = re.compile(r"gmirca_[0-9a-f]{32}")


class TechnologyPublishedSignalRefusal(ValueError):
    """Typed refusal. ``str(exc)`` is the snake_case code."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def publish_technology_dossier(dossier: Mapping[str, Any]) -> str:
    """Return the company-first fragment, or refuse with ``no_published_row``.

    A refused business section still renders (the sealed
    ``shared_contract_unavailable`` page). Otherwise the dossier must carry
    exactly one ``product_workload_role`` / ``attributed`` row whose
    ``curation_revision`` matches ``gmirca_`` plus 32 hex digits.
    """
    if not isinstance(dossier, Mapping):
        raise TechnologyPublishedSignalRefusal("no_published_row")
    business = dossier.get("business")
    if isinstance(business, Mapping) and business.get("refused") is True:
        return render_technology_dossier_page(dossier, _TEMPLATE)
    if _one_conformant_row(business):
        return render_technology_dossier_page(dossier, _TEMPLATE)
    raise TechnologyPublishedSignalRefusal("no_published_row")


def _one_conformant_row(business: Any) -> bool:
    if not isinstance(business, Mapping):
        return False
    rows = business.get("rows")
    if not isinstance(rows, list) or len(rows) != 1 or not isinstance(rows[0], Mapping):
        return False
    row = rows[0]
    revision = row.get("curation_revision")
    return (
        row.get("predicate") == "product_workload_role"
        and row.get("statement_mode") == "attributed"
        and isinstance(revision, str)
        and _CURATION_REVISION_RE.fullmatch(revision) is not None
    )
