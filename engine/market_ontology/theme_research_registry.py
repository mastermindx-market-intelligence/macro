"""Closed vertical registration for the theme-research shell (shared hook 1).

Sol ruling on carrier PR #7780 (issuecomment-5813801605, Option A, items 1
and 4), verbatim: "NO wildcard/regex schema acceptance. Use a trusted closed
registration binding anchor, slice set, exact schema/version, composer and
evidence selector; preserve auth-first handling and current private errors.
Unknown/mismatched schema/anchor/slice fails. Config-driven and multi-anchor
mounts reuse the existing shell; each domain supplies its accepted contract."

How a vertical registers
------------------------
A vertical (Semiconductor today; Robotics, Technology ex-Semis, Mining on
their own carriers or via a later additive commit here) adds ONE
:class:`VerticalRegistration` entry to :data:`REGISTRY` carrying its own
accepted composer, evidence selector, owner-bundle loader and definition
version, and adds its mount's anchor, slice set, schema ids and bilingual
copy to the leaf :mod:`engine.market_ontology.theme_research_mounts` module
that this one reads. Nothing else changes: ``app/theme_research.py`` resolves
the registration by exact anchor after auth and body parsing and dispatches
to it, and the mount partial and the page builders render that same leaf
module's strings (shared hook 2), so the served route and the rendered
section cannot drift apart.

Closure laws
------------
* Exact-string keys only: no wildcard, no regex, no prefix match, no case or
  whitespace normalisation, no default vertical, no environment variable, no
  config file read. An unknown anchor resolves to ``None`` and the caller
  fails closed with its existing private refusal.
* A slice is accepted only when it is a member of the registration's closed
  ``slice_keys`` tuple, and a view only when it is a member of the closed
  ``view_keys`` tuple. Unknown or foreign slices and views fail closed. The
  shell holds NO literal from either vocabulary: membership is decided here
  (Sol #7870 issuecomment-5923155205, "the finished closed registration must
  own and validate the admitted view set as well as the admitted slice set").
* The schema ids and definition version are the exact strings the vertical's
  composer emits; the shell compares the composed payload's ``schema`` (and,
  for the query envelope, ``definition_version``) against the registration
  and refuses a mismatch (a composer and its registration can never drift
  apart silently).
* This module imports no web framework and no template engine so
  ``scripts/`` and ``templates/`` producers can import it without pulling
  FastAPI into a build, and it binds every vertical callable LAZILY so
  importing it loads no vertical composer at all. Before this, importing the
  registry — or the shell, which imports the registry — eagerly executed the
  semiconductor composer's whole closure, so the SHARED shell could not load
  without this ONE vertical. ``test_registry_import_closure_stays_light``
  names the forbidden modules; the wrappers expose ``lazy_target()`` so a test
  can still assert by identity WHICH function a registration dispatches to.
* No authority: a registration carries no ranking, gating, sizing, entry or
  origination flag, and this module performs no arithmetic.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

from engine.market_ontology.theme_research_mounts import MOUNTS as _MOUNTS

__all__ = [
    "REGISTRY",
    "VerticalRegistration",
    "allowed_slices",
    "allowed_views",
    "registration_for",
]

# The canonical theme-id grammar (``^[a-z0-9_]+$``) expressed as a closed
# character set so this module needs no regular-expression machinery.
_ID_CHARS = frozenset("abcdefghijklmnopqrstuvwxyz0123456789_")
_ID_MAX_LENGTH = 64


def _is_canonical_id(value: object) -> bool:
    return (
        isinstance(value, str)
        and 0 < len(value) <= _ID_MAX_LENGTH
        and all(char in _ID_CHARS for char in value)
    )


def _require_nonempty_text(field: str, value: object) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"VerticalRegistration.{field} must be non-empty text")


@dataclass(frozen=True)
class VerticalRegistration:
    """One vertical's accepted contract, bound to exactly one anchor theme.

    ``compose(query, bundle) -> Mapping``,
    ``select_evidence(query, bundle, assertion_ref) -> Mapping`` and
    ``load_bundle(query, *, rights_snapshot) -> OwnerBundle`` are the
    vertical's own callables; the shell never inspects their internals. The
    loader serves the vertical's accepted owner surfaces for a request the
    shell has already authenticated, parsed and resolved; it raises
    :class:`~engine.market_ontology.theme_research_binding.BundleUnavailable`
    when it cannot serve (the shell's private 503) and the composer's
    ``ResearchRefusal`` for a research mode it does not support.

    ``build_query(**fields) -> <the vertical's query type>`` is how the shell
    turns a parsed request body into the object the vertical's own callables
    accept. The shell cannot construct that type itself without naming a
    vertical module, which is the coupling this registration exists to
    remove; the vertical supplies the constructor and keeps ownership of its
    own query literals. A field the vertical does not accept raises from the
    vertical, not from the shell.

    ``view_keys`` is the admitted view vocabulary, closed exactly like
    ``slice_keys``. The shell validates membership against it instead of
    pinning the five semiconductor views in a transport-layer ``Literal``.

    The title/note strings are the bilingual copy the mount renders verbatim.
    """

    anchor_theme_id: str
    slice_keys: tuple[str, ...]
    view_keys: tuple[str, ...]
    schema_id: str
    evidence_schema_id: str
    definition_version: str
    compose: Callable[..., Mapping[str, Any]]
    select_evidence: Callable[..., Mapping[str, Any]]
    load_bundle: Callable[..., Any]
    build_query: Callable[..., Any]
    title_en: str
    title_zh: str
    note_en: str
    note_zh: str

    def __post_init__(self) -> None:
        if not _is_canonical_id(self.anchor_theme_id):
            raise ValueError(
                "VerticalRegistration.anchor_theme_id must match the canonical "
                "theme-id grammar (lowercase a-z, 0-9, underscore; 1-64 chars)"
            )
        if not isinstance(self.slice_keys, tuple) or not self.slice_keys:
            raise ValueError("VerticalRegistration.slice_keys must be a non-empty tuple")
        for slice_key in self.slice_keys:
            if not _is_canonical_id(slice_key):
                raise ValueError(
                    "VerticalRegistration.slice_keys entries must match the "
                    "canonical id grammar"
                )
        if len(set(self.slice_keys)) != len(self.slice_keys):
            raise ValueError("VerticalRegistration.slice_keys must not repeat a slice")
        if not isinstance(self.view_keys, tuple) or not self.view_keys:
            raise ValueError("VerticalRegistration.view_keys must be a non-empty tuple")
        for view_key in self.view_keys:
            if not _is_canonical_id(view_key):
                raise ValueError(
                    "VerticalRegistration.view_keys entries must match the "
                    "canonical id grammar"
                )
        if len(set(self.view_keys)) != len(self.view_keys):
            raise ValueError("VerticalRegistration.view_keys must not repeat a view")
        for field in ("schema_id", "evidence_schema_id", "definition_version",
                      "title_en", "title_zh", "note_en", "note_zh"):
            _require_nonempty_text(field, getattr(self, field))
        if self.schema_id == self.evidence_schema_id:
            raise ValueError(
                "VerticalRegistration.schema_id and evidence_schema_id must differ"
            )
        if not callable(self.compose) or not callable(self.select_evidence) \
                or not callable(self.load_bundle) or not callable(self.build_query):
            raise TypeError(
                "VerticalRegistration.compose, select_evidence, load_bundle and "
                "build_query must be callable"
            )


# ---------------------------------------------------------------------------
# The closed registry — one entry today
# ---------------------------------------------------------------------------

def _semiconductor_composer() -> Any:
    """The semiconductor composer module, imported on FIRST USE only.

    This one-line indirection is the whole fix for the defect Sol named on
    this carrier: the registry used to import the composer at module level,
    so every importer of the SHARED shell executed one vertical's entire
    closure — the shared foundation could not load without Semiconductor.
    ``sys.modules`` caches the module, so the cost is paid once per process
    and only by a request that actually resolved this registration.
    """
    from engine.market_ontology import (  # noqa: PLC0415 — lazy by design
        semiconductor_theme_research,
    )
    return semiconductor_theme_research


def _compose_semiconductor(*args: Any, **kwargs: Any) -> Mapping[str, Any]:
    """Forward to this vertical's composer, resolved lazily."""
    return _semiconductor_composer().compose_semiconductor_research(*args, **kwargs)


def _select_semiconductor_evidence(*args: Any, **kwargs: Any) -> Mapping[str, Any]:
    """Forward to this vertical's evidence selector, resolved lazily."""
    return _semiconductor_composer().select_authorized_evidence(*args, **kwargs)


def _build_semiconductor_query(**fields: Any) -> Any:
    """Construct this vertical's own query type from the shell's parsed body.

    The vertical owns its query literals, so an unaccepted ``slice_key`` or
    ``view`` fails inside this dataclass rather than in the transport.
    """
    return _semiconductor_composer().ResearchQuery(**fields)


# Each wrapper carries the resolver for the function it forwards to, so a test
# can assert WHICH vertical function a registration dispatches to by identity
# — the guarantee the eager import used to provide — without the registry
# importing it to answer the question.
_compose_semiconductor.lazy_target = (
    lambda: _semiconductor_composer().compose_semiconductor_research
)
_select_semiconductor_evidence.lazy_target = (
    lambda: _semiconductor_composer().select_authorized_evidence
)
_build_semiconductor_query.lazy_target = (
    lambda: _semiconductor_composer().ResearchQuery
)


def _load_semiconductor_owner_bundle(query: Any, *, rights_snapshot: Any = None) -> Any:
    """The semiconductor entry's loader, bound LAZILY: the loader module pulls
    the Company Intelligence reader (requests, pandas, pyarrow) which this
    registry must not drag into ``scripts/`` / ``templates/`` producers that
    import it for the mount (module law: no web framework, no template engine,
    and no data/network stack). ``test_registry_import_closure_stays_light``
    is what enforces that — it names the forbidden modules rather than a
    count, which is interpreter-dependent. Resolved on the first served
    request, never at import."""
    from engine.market_ontology.semiconductor_owner_bundle import (  # noqa: PLC0415 — lazy by design
        load_semiconductor_owner_bundle,
    )
    return load_semiconductor_owner_bundle(query, rights_snapshot=rights_snapshot)


# Shared hook 2: every DECLARATIVE fact — the anchor, the slice set, the view
# set, the schema ids, the definition version and the bilingual copy — is the
# mount's own definition, read from the leaf ``theme_research_mounts`` module
# the page builders also read. The route and the rendered section can no
# longer disagree, and neither can be changed without the other. The
# definition version and the view set joined the mount on this carrier: the
# registry cannot read them off the composer without importing it eagerly,
# which is precisely the edge removed here, and a literal typed a second time
# three lines below would be a copy with nothing covering its agreement. The
# registration owns what a mount never sees — the composer, the evidence
# selector, the owner-bundle loader and the query constructor — and it owns
# them as LAZY bindings.
_SEMICONDUCTOR_MOUNT = _MOUNTS["ai_semiconductors"]

_SEMICONDUCTOR = VerticalRegistration(
    anchor_theme_id=_SEMICONDUCTOR_MOUNT.anchor_theme_id,
    slice_keys=_SEMICONDUCTOR_MOUNT.slice_keys,
    view_keys=_SEMICONDUCTOR_MOUNT.view_keys,
    schema_id=_SEMICONDUCTOR_MOUNT.schema_id,
    evidence_schema_id=_SEMICONDUCTOR_MOUNT.evidence_schema_id,
    definition_version=_SEMICONDUCTOR_MOUNT.definition_version,
    compose=_compose_semiconductor,
    select_evidence=_select_semiconductor_evidence,
    # T08c-2: public half through the Company Intelligence reader, private
    # half declared absent (R4 pending).
    load_bundle=_load_semiconductor_owner_bundle,
    build_query=_build_semiconductor_query,
    title_en=_SEMICONDUCTOR_MOUNT.title_en,
    title_zh=_SEMICONDUCTOR_MOUNT.title_zh,
    note_en=_SEMICONDUCTOR_MOUNT.note_en,
    note_zh=_SEMICONDUCTOR_MOUNT.note_zh,
)

_ENTRIES: tuple[VerticalRegistration, ...] = (_SEMICONDUCTOR,)


def _assert_unique_anchors(entries: tuple[VerticalRegistration, ...]) -> None:
    """Load-time closure: a registration is keyed by its own anchor, once."""
    anchors = [entry.anchor_theme_id for entry in entries]
    for anchor in anchors:
        if anchors.count(anchor) != 1:
            raise RuntimeError(f"theme_research_registry: anchor registered twice: {anchor!r}")


_assert_unique_anchors(_ENTRIES)

#: Closed, read-only mapping ``anchor_theme_id -> VerticalRegistration``.
REGISTRY: Mapping[str, VerticalRegistration] = MappingProxyType(
    {entry.anchor_theme_id: entry for entry in _ENTRIES}
)


def registration_for(anchor_theme_id: object) -> VerticalRegistration | None:
    """Exact-key lookup. No normalisation, no pattern, no default.

    Returns ``None`` for anything that is not a registered anchor string; the
    caller applies its own fail-closed refusal.
    """
    if not isinstance(anchor_theme_id, str):
        return None
    return REGISTRY.get(anchor_theme_id)


def allowed_slices(anchor_theme_id: object) -> frozenset[str]:
    """The closed slice set for ``anchor_theme_id``; empty when unregistered."""
    registration = registration_for(anchor_theme_id)
    if registration is None:
        return frozenset()
    return frozenset(registration.slice_keys)


def allowed_views(anchor_theme_id: object) -> frozenset[str]:
    """The closed view set for ``anchor_theme_id``; empty when unregistered.

    An empty set is the fail-closed answer, exactly as for slices: an
    unregistered anchor admits no view, so the caller refuses rather than
    falling back to some default vocabulary.
    """
    registration = registration_for(anchor_theme_id)
    if registration is None:
        return frozenset()
    return frozenset(registration.view_keys)
