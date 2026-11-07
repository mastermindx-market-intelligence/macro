"""Flag-gated production wiring of the Catalyst SEC source reader (A3-R).

``configure_from_environment`` is the only production path that may call
``catalyst_admission.configure`` with a real store-backed source.  It is inert
unless ``CATALYST_PUBLIC_ENABLED == "1"``, refuses a local research store, and
only configures over a real, available namespaced R2 store.  It never raises
and never logs anything beyond bare reason codes and exception type names —
no environment values, keys, URLs or user agents.
"""
from __future__ import annotations

import logging
import os

logger = logging.getLogger("macro.api")


def _is_production_store(store: object) -> bool:
    """A NamespacedSourceStore over a real, available R2Store — nothing else."""
    from engine.marketing.catalyst_source_store import NamespacedSourceStore
    from engine.research_vault.r2_store import R2Store
    return (isinstance(store, NamespacedSourceStore)
            and type(store.inner) is R2Store
            and store.inner.available is True)


def configure_from_environment() -> bool:
    """Configure the admitted source when, and only when, production admits it.

    Returns True only when a source was actually configured; every refusal is
    a logged reason code and leaves admission unconfigured (fail closed).
    """
    if os.environ.get("CATALYST_PUBLIC_ENABLED") != "1":
        return False
    if os.environ.get("RESEARCH_LOCAL_STORE"):
        logger.warning("catalyst source wiring refused: reason=local_store_refused")
        return False
    try:
        from engine.marketing.catalyst_source_store import open_production_store
        store = open_production_store()
        if not _is_production_store(store):
            logger.warning("catalyst source wiring refused: reason=not_production_store")
            return False
        from engine.marketing import catalyst_admission
        from engine.marketing.catalyst_source_adapter import build_admitted_source
        catalyst_admission.configure(build_admitted_source(store))
    except Exception as exc:  # noqa: BLE001 - type name only, never detail.
        logger.warning("catalyst source wiring failed: reason=%s",
                       type(exc).__name__)
        return False
    return True
