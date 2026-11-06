"""Hold payload for the dossier's source-edition section.

The block set is exactly the holes that keep the T05 strict xfails in place.
``select_editions`` and ``assess_dossier_comparison`` are not defined here,
and this module does not emit a same-day refusal.
"""
from __future__ import annotations

from collections.abc import Mapping
import inspect
from typing import Any

from engine.company_intelligence import financial_dossier
from engine.company_intelligence import industrials_source_facts as source_facts
from engine.company_intelligence.documents import SourceDocument


# Names the producer would have to define before the same-day block can clear.
# Checked for absence only. This module does not import theme state and does
# not return either refusal.
_SAME_DAY_REFUSALS = ("KNOWLEDGE_TIME_UNPROVEN", "same_day_boundary_unresolved")


def edition_hold(case: Mapping[str, Any]) -> dict[str, Any]:
    """Return ``status`` ``held``, the current blocks, and the producer's documents.

    The blocks are structural facts about this tree. They are the same for
    every case ``edition_documents`` accepts. A later ``select_editions``
    drops ``selector_signature_unruled`` and the pinned frozenset goes red.
    """
    return {
        "status": "held",
        "blocks": _blocks(),
        "documents": source_facts.edition_documents(case),
    }


def _blocks() -> frozenset[str]:
    blocks: set[str] = set()
    fields = SourceDocument.__dataclass_fields__
    if "statement_mode" not in fields:
        blocks.add("statement_mode_unstored")
    selector = getattr(financial_dossier, "select_editions", None)
    if not callable(selector):
        blocks.add("selector_signature_unruled")
    parameters = inspect.signature(source_facts.edition_documents).parameters
    if "source_cutoff" not in parameters:
        blocks.add("cutoff_exclusion_unselected")
    producer_names = set(vars(source_facts))
    if not any(name in producer_names for name in _SAME_DAY_REFUSALS):
        blocks.add("same_day_grain_unstored")
    if "completed" not in fields and "potential_confound" not in fields:
        blocks.add("acquisition_outside_document")
    comparison = getattr(financial_dossier, "assess_dossier_comparison", None)
    if not callable(comparison):
        blocks.add("comparison_unbound")
    return frozenset(blocks)
