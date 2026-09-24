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
accepted composer, evidence selector, exact schema ids and definition
version, and the bilingual title/note the mount renders. Nothing else changes:
``app/theme_research.py`` resolves the registration by exact anchor after auth
and body parsing and dispatches to it. The mount partial and build scripts
are bound to the same registration by shared hook 2 (a separate additive
commit); until it lands they carry their own copy of the bilingual title/note
and slice list, and this module pins those strings so the two cannot drift
unnoticed once wired.

Closure laws
------------
* Exact-string keys only: no wildcard, no regex, no prefix match, no case or
  whitespace normalisation, no default vertical, no environment variable, no
  config file read. An unknown anchor resolves to ``None`` and the caller
  fails closed with its existing private refusal.
* A slice is accepted only when it is a member of the registration's closed
  ``slice_keys`` tuple. Unknown or foreign slices fail closed.
* The schema ids and definition version are the exact strings the vertical's
  composer emits; the shell compares the composed payload's ``schema`` (and,
  for the query envelope, ``definition_version``) against the registration
  and refuses a mismatch (a composer and its registration can never drift
  apart silently).
* This module imports no web framework and no template engine so
  ``scripts/`` and ``templates/`` producers can import it without pulling
  FastAPI into a build.
* No authority: a registration carries no ranking, gating, sizing, entry or
  origination flag, and this module performs no arithmetic.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

from engine.market_ontology.semiconductor_theme_research import (
    DEFINITION_VERSION as _SEMICONDUCTOR_DEFINITION_VERSION,
    compose_semiconductor_research,
    select_authorized_evidence,
)

__all__ = [
    "REGISTRY",
    "VerticalRegistration",
    "allowed_slices",
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

    ``compose(query, bundle) -> Mapping`` and
    ``select_evidence(query, bundle, assertion_ref) -> Mapping`` are the
    vertical's own callables; the shell never inspects their internals. The
    title/note strings are the bilingual copy the mount renders verbatim.
    """

    anchor_theme_id: str
    slice_keys: tuple[str, ...]
    schema_id: str
    evidence_schema_id: str
    definition_version: str
    compose: Callable[..., Mapping[str, Any]]
    select_evidence: Callable[..., Mapping[str, Any]]
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
        for field in ("schema_id", "evidence_schema_id", "definition_version",
                      "title_en", "title_zh", "note_en", "note_zh"):
            _require_nonempty_text(field, getattr(self, field))
        if self.schema_id == self.evidence_schema_id:
            raise ValueError(
                "VerticalRegistration.schema_id and evidence_schema_id must differ"
            )
        if not callable(self.compose) or not callable(self.select_evidence):
            raise TypeError(
                "VerticalRegistration.compose and select_evidence must be callable"
            )


# ---------------------------------------------------------------------------
# The closed registry — one entry today
# ---------------------------------------------------------------------------

_SEMICONDUCTOR = VerticalRegistration(
    anchor_theme_id="ai_semiconductors",
    slice_keys=("hbm_packaging", "sic_gan_specialty"),
    schema_id="semiconductor_theme_research.v1",
    evidence_schema_id="semiconductor_theme_research.evidence.v1",
    definition_version=_SEMICONDUCTOR_DEFINITION_VERSION,
    compose=compose_semiconductor_research,
    select_evidence=select_authorized_evidence,
    # Bilingual copy pinned verbatim from the reviewed T10b mount
    # (templates/_theme_research_mount.html.j2, law L5).
    title_en="Semiconductor industry research",
    title_zh="半导体产业研究",
    note_en=(
        "Paid research context for members. Nothing here ranks, gates, sizes "
        "or times anything."
    ),
    note_zh="会员研究内容。此处内容不构成排序、准入、仓位或时机判断。",
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
