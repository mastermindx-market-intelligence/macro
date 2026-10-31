"""Production composition root for the Research Read service.

One process-cached service, shared later by the F12 MCP runtime. Importing this
module builds nothing and opens no socket.
"""
from __future__ import annotations

import functools
from typing import Any

from engine.research_vault.read_adapters import BrainResearchAdapter
from engine.research_vault.read_service import ResearchReadService

_service: ResearchReadService | None = None
_adapter: BrainResearchAdapter | None = None

# engine.research_intelligence.store exposes load_latest_research_intelligence
# and load_research_intelligence_version. Neither is an inventory, so
# rio_inventory stays None until an incumbent reader exists.


def _source_classifier():
    """Bind the freshness evaluator at build time, not on the request path."""
    from scripts.check_research_vault_source_freshness import evaluate

    def _evaluate(payload, *, now, source="catalog", **kwargs):
        return evaluate(payload, now=now, source=source, **kwargs)

    return _evaluate


def build_read_service(**overrides: Any) -> ResearchReadService:
    """Build a service with zero required arguments.

    Collaborators come from their incumbent factories. Keyword arguments exist
    only for tests; a required parameter would be a defect.
    """
    from engine.research_intelligence.store import load_latest_research_intelligence
    from engine.research_vault import fulltext_store
    from engine.research_vault.catalog import preview_ids
    from engine.research_vault.corpus import corpus_connection
    from engine.research_vault.r2_store import build_store

    store = overrides["catalog_store"] if "catalog_store" in overrides else build_store()
    built: dict[str, Any] = {
        "catalog_store": store,
        "corpus_connection": corpus_connection,
        "preview_selector": preview_ids,
        "extracted_text_loader": functools.partial(
            fulltext_store.load_extracted_text, store
        ),
        # Filename inventory includes stale, corrupt and no-text derivatives.
        # Until E04 supplies a current qualified generation reader, use the
        # frozen unavailable-inventory basis: 0.0 with FULL_TEXT_PARTIAL. That
        # zero is degraded/unknown measurement, not an observed zero census.
        "full_text_inventory": None,
        "source_digest_reader": functools.partial(
            fulltext_store.source_digest, store
        ),
        "rio_reader": functools.partial(load_latest_research_intelligence, store),
        "rio_inventory": None,
        "source_classifier": _source_classifier(),
    }
    built.update(overrides)
    clock = {}
    if "clock" in built:
        clock["clock"] = built["clock"]
    return ResearchReadService(
        catalog_store=built["catalog_store"],
        corpus_connection=built["corpus_connection"],
        preview_selector=built["preview_selector"],
        extracted_text_loader=built["extracted_text_loader"],
        full_text_inventory=built["full_text_inventory"],
        source_digest_reader=built["source_digest_reader"],
        rio_reader=built["rio_reader"],
        rio_inventory=built["rio_inventory"],
        source_classifier=built["source_classifier"],
        comparison_owners=built.get("comparison_owners"),
        **clock,
    )


def get_read_service() -> ResearchReadService:
    """Return the process-cached service, building it on first use."""
    global _service
    if _service is None:
        _service = build_read_service()
    return _service


def brain_adapter() -> BrainResearchAdapter:
    """Return the process-cached Brain adapter over :func:`get_read_service`."""
    global _adapter
    if _adapter is None:
        _adapter = BrainResearchAdapter(get_read_service())
    return _adapter


def build_qualified_read_service(provider, **overrides: Any) -> ResearchReadService:
    """Explicit dedicated-runtime composition; callers must use provider.run.

    Preparation, current writer policy and final HTTP delivery guards remain
    the runtime owner's obligations. The ordinary shared factory is unchanged.
    """
    reserved = {"catalog_store", "corpus_connection", "full_text_inventory"}
    if reserved.intersection(overrides):
        raise ValueError("qualified reader owns catalog, corpus and inventory")
    return build_read_service(catalog_store=provider.catalog_store,
                              corpus_connection=provider.connection,
                              full_text_inventory=provider.full_text_inventory,
                              **overrides)
