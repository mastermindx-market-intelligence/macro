"""The one exception a vertical's owner-bundle loader raises when it cannot
serve (shared hook 1, Sol #7780 issuecomment-5813801605).

A :class:`~engine.market_ontology.theme_research_registry.VerticalRegistration`
carries a ``load_bundle(query, *, rights_snapshot)`` callable. When the
loader's owner surface is unbound, unreachable, or hands back something it
cannot vouch for, it raises :class:`BundleUnavailable`; the theme-research
shell maps it to its fixed private 503 envelope and never lets the message
cross the wire. The class lives in this leaf module so the registry, every
vertical's loader and the shell can share it without an import cycle.

A loader refuses a *research mode* it cannot serve with the composer's own
``ResearchRefusal`` (the shell maps refusal codes to the existing private
error family); it never invents a status code or an error string family.
"""
from __future__ import annotations

__all__ = ["BundleUnavailable"]


class BundleUnavailable(Exception):
    """The registered loader cannot serve a bundle for this request.

    Raised for: unbound private store, unreachable or refusing owner reader,
    a reader envelope that breaks its own contract, a rights snapshot that
    carries no revision. Never raised for coverage absence — that is a typed
    omission on the bundle, so the response says what is missing.
    """
