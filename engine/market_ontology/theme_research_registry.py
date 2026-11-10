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

from engine.market_ontology.theme_research_binding import ENTRY_KINDS as _ENTRY_KINDS
from engine.market_ontology.theme_research_mounts import MOUNTS as _MOUNTS

__all__ = [
    "REGISTRY",
    "PROFILE_REGISTRY",
    "VerticalRegistration",
    "allowed_slices",
    "allowed_views",
    "profile_registration_for",
    "registration_for",
]

# The canonical theme-id grammar (``^[a-z0-9_]+$``) expressed as a closed
# character set so this module needs no regular-expression machinery.
_ID_CHARS = frozenset("abcdefghijklmnopqrstuvwxyz0123456789_")
_ID_MAX_LENGTH = 64

# The profile-id grammar (``^[a-z0-9_.]+$``): a canonical id plus the dot the
# versioned profile ids carry (``technology_economic_change.v1``). Still a
# closed character set — no regex machinery in this module.
_PROFILE_ID_CHARS = _ID_CHARS | frozenset(".")

# The subject-value grammar for closed subject vocabularies: a canonical id
# plus the separators the typed subject refs legally carry — ``co:us:...``,
# ``cik:...``, ``sector:financials``, revision pins (``#3``) and hyphens.
# MEMBERSHIP stays the vertical's: a registration with an empty
# ``subject_values`` tuple defers to the vertical's own grammar/resolution.
_SUBJECT_VALUE_CHARS = _ID_CHARS | frozenset(":.#-")


def _is_canonical_id(value: object) -> bool:
    return (
        isinstance(value, str)
        and 0 < len(value) <= _ID_MAX_LENGTH
        and all(char in _ID_CHARS for char in value)
    )


def _is_profile_id(value: object) -> bool:
    return (
        isinstance(value, str)
        and 0 < len(value) <= _ID_MAX_LENGTH
        and all(char in _PROFILE_ID_CHARS for char in value)
    )


def _is_subject_value(value: object) -> bool:
    return (
        isinstance(value, str)
        and 0 < len(value) <= 128
        and all(char in _SUBJECT_VALUE_CHARS for char in value)
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
    # --- v2 profile columns (packet §3.4, lane 5) -----------------------------
    # Every field below is DEFAULTED so the fourteen v1 fields keep their
    # order and positional construction: a theme entry built exactly as
    # before is a ``theme`` entry in the v2 union without touching its
    # constructor call. The defaults are the theme-entry semantics; a
    # profile entry overrides them.
    #: Which v2 entry kind this registration serves. A registration serves
    #: exactly ONE kind: the profile registry keys the entry by this token
    #: and the closed union refuses everything else.
    entry_kind: str = "theme"
    #: The profile id a ``company_profile``/``sector_profile`` request must
    #: carry exactly (``technology_economic_change.v1``); ``None`` on a
    #: theme entry, whose identity IS the anchor.
    profile_id: str | None = None
    #: Which of the shared request fields names this entry's SUBJECT. A
    #: theme entry's subject is its slice; a profile entry names its typed
    #: subject (``company_ref`` / ``sector_ref``). The shell uses the name
    #: only to read the subject off its own parsed body — never to accept a
    #: foreign field the vertical did not name.
    subject_field: str = "slice_key"
    #: Closed subject vocabulary. EMPTY means the vertical owns the
    #: grammar/resolution itself (Technology resolves ``co:``/``cik:``
    #: refs through its bundle's identity results); non-empty means the
    #: registration admits exactly these values (Finance's
    #: ``sector:financials``).
    subject_values: tuple[str, ...] = ()
    #: Closed time-mode tokens this entry serves. The shell refuses a
    #: request whose ``time_mode`` is outside it with the entry's own
    #: refusal, mirroring the existing loader-refusal precedence (404
    #: before a cutoff 400).
    time_modes: tuple[str, ...] = ("latest", "source_history", "system_replay")
    #: Single-document entries (the two profile kinds initially) reject
    #: ``cursor``, nonzero ``offset`` and supplied ``limit`` rather than
    #: silently ignoring them.
    single_document: bool = False
    #: The prefix of the NATIVE generation this entry's composer emits
    #: (``gen_`` for semiconductor, ``tecd_`` for Technology's dossier id).
    #: The native generation is NEVER renamed; this is validation grammar
    #: only, kept as prefix+width so the module needs no regex.
    native_generation_prefix: str = "gen_"
    #: The hex width of the native generation after its prefix.
    native_generation_width: int = 32
    #: The native payload field carrying this entry's native generation
    #: (``generation`` for the theme and Finance composers; ``dossier_id`` for
    #: Technology — the sealed dossier's own name). The shell reads the
    #: NATIVE generation from this field to re-check the expected native
    #: generation and to bind the context generation; the native value is
    #: never renamed or re-prefixed.
    native_generation_field: str = "generation"
    #: The native payload field carrying the owner-issued assertion
    #: references bound to rendered evidence (``evidence_refs`` for the
    #: theme composer, ``assertion_refs`` for Finance's dossier envelope).
    #: ``None`` — the payload publishes no such list and the v2 envelope
    #: reports an EMPTY one — is the honest state for a vertical whose
    #: native payload does not yet carry one.
    evidence_refs_field: str | None = "evidence_refs"
    #: Optional issuer-economics builder (lane 5 v1.1 amendment,
    #: ``sector_intelligence.issuer_economics.v1``): when callable, the v2
    #: QUERY envelope carries its block as a SIBLING of ``data`` under
    #: ``issuer_economics``. The v1 response and the v2 evidence path never
    #: call it (byte-identity pinned by test). The callable owns its own
    #: owner reads — declared cohort, witness scope, Data OS alias
    #: enumeration — and must never raise. ``None`` (the default) means the
    #: entry serves no such block and its envelopes are unchanged.
    issuer_economics: Callable[..., Mapping[str, Any]] | None = None

    def __post_init__(self) -> None:
        # --- entry-kind branch: the two kinds carry different identity laws ---
        if self.entry_kind not in _ENTRY_KINDS:
            raise ValueError(
                "VerticalRegistration.entry_kind must be one of the closed v2 "
                "entry kinds: " + ", ".join(_ENTRY_KINDS)
            )
        if self.entry_kind == "theme":
            if self.profile_id is not None:
                raise ValueError(
                    "VerticalRegistration.profile_id must be None on a theme "
                    "entry: a theme entry is keyed by its anchor, not a profile"
                )
            if not _is_canonical_id(self.anchor_theme_id):
                raise ValueError(
                    "VerticalRegistration.anchor_theme_id must match the canonical "
                    "theme-id grammar (lowercase a-z, 0-9, underscore; 1-64 chars)"
                )
            if not isinstance(self.slice_keys, tuple) or not self.slice_keys:
                raise ValueError(
                    "VerticalRegistration.slice_keys must be a non-empty tuple"
                )
            for slice_key in self.slice_keys:
                if not _is_canonical_id(slice_key):
                    raise ValueError(
                        "VerticalRegistration.slice_keys entries must match the "
                        "canonical id grammar"
                    )
            if len(set(self.slice_keys)) != len(self.slice_keys):
                raise ValueError(
                    "VerticalRegistration.slice_keys must not repeat a slice"
                )
        else:
            # A profile entry carries NO theme anchor of its own; the anchor
            # column holds the profile id so the entry keeps exactly one
            # identity across both registries. Slices are theme vocabulary
            # and stay empty.
            if not _is_profile_id(self.profile_id):
                raise ValueError(
                    "VerticalRegistration.profile_id must be a non-empty "
                    "profile id (lowercase a-z, 0-9, underscore, dot) on a "
                    f"{self.entry_kind} entry"
                )
            if self.anchor_theme_id != self.profile_id:
                raise ValueError(
                    "VerticalRegistration.anchor_theme_id must equal profile_id "
                    f"on a {self.entry_kind} entry (the one key both registries "
                    "share); got a different string"
                )
            if self.slice_keys:
                raise ValueError(
                    f"VerticalRegistration.slice_keys must be empty on a "
                    f"{self.entry_kind} entry"
                )
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
        # --- v2 profile columns ---------------------------------------------------
        if not _is_canonical_id(self.subject_field):
            raise ValueError(
                "VerticalRegistration.subject_field must match the canonical "
                "id grammar (it names a shared request field)"
            )
        if not isinstance(self.subject_values, tuple):
            raise ValueError("VerticalRegistration.subject_values must be a tuple")
        for value in self.subject_values:
            if not _is_subject_value(value):
                raise ValueError(
                    "VerticalRegistration.subject_values entries must match the "
                    "closed subject-value grammar"
                )
        if len(set(self.subject_values)) != len(self.subject_values):
            raise ValueError("VerticalRegistration.subject_values must not repeat")
        if not isinstance(self.time_modes, tuple) or not self.time_modes:
            raise ValueError(
                "VerticalRegistration.time_modes must be a non-empty tuple"
            )
        for mode in self.time_modes:
            if not _is_canonical_id(mode):
                raise ValueError(
                    "VerticalRegistration.time_modes entries must match the "
                    "canonical id grammar"
                )
        if len(set(self.time_modes)) != len(self.time_modes):
            raise ValueError("VerticalRegistration.time_modes must not repeat")
        if not isinstance(self.single_document, bool):
            raise ValueError("VerticalRegistration.single_document must be a bool")
        if not isinstance(self.native_generation_prefix, str) \
                or not self.native_generation_prefix:
            raise ValueError(
                "VerticalRegistration.native_generation_prefix must be "
                "non-empty text"
            )
        if not isinstance(self.native_generation_width, int) \
                or isinstance(self.native_generation_width, bool) \
                or self.native_generation_width < 8 \
                or self.native_generation_width > 64:
            raise ValueError(
                "VerticalRegistration.native_generation_width must be an int "
                "in [8, 64]"
            )
        if any(char not in _ID_CHARS for char in self.native_generation_prefix):
            raise ValueError(
                "VerticalRegistration.native_generation_prefix must match the "
                "canonical id grammar so prefix+width composes into a closed "
                "generation grammar without regex machinery"
            )
        if not _is_canonical_id(self.native_generation_field):
            raise ValueError(
                "VerticalRegistration.native_generation_field must match the "
                "canonical id grammar (it names a native payload field)"
            )
        if self.evidence_refs_field is not None:
            _require_nonempty_text("evidence_refs_field", self.evidence_refs_field)
        if self.issuer_economics is not None and not callable(self.issuer_economics):
            raise TypeError(
                "VerticalRegistration.issuer_economics must be callable or None"
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


def _issuer_economics_module() -> Any:
    """The lane-5 v1.1 issuer-economics module, imported on FIRST USE only —
    stdlib-only at import, but the registry's import-closure laws are asserted
    by naming verticals, and a new eager edge is exactly what those tests
    exist to prevent."""
    from engine.market_ontology import (  # noqa: PLC0415 — lazy by design
        issuer_economics,
    )
    return issuer_economics


def _build_semiconductor_issuer_economics(
    query: Any, bundle: Any, *, dropped: bool = False,
) -> Mapping[str, Any]:
    """The semiconductor theme entry's issuer-economics builder (lane 5 v1.1).

    The REGISTRATION SEAM performs the owner reads the block itself never
    does: the declared witness scope
    (:func:`semiconductor_witness_scope.resolve_witness_scope`), the DECLARED
    cohort size (the roster, independent of identity resolution), and the
    Data OS alias enumeration (``IssuerMaster.securities_of_issuer`` via the
    scope module's own canonical master loader — the one immutable-byte-read
    reader contract; ``None`` when the master is unreadable, which the block
    carries as the typed alias unknown). Every import is lazy: importing the
    registry loads no vertical and no data stack. The builder is pure over
    mapping-shaped inputs and never raises, so a builder fault cannot take
    the query route down."""
    from engine.market_ontology.semiconductor_witness_scope import (  # noqa: PLC0415 — lazy by design
        WITNESS_ROSTER,
        _load_issuer_master,
        resolve_witness_scope,
    )

    slice_key = getattr(query, "slice_key", "")
    scope = resolve_witness_scope(slice_key if isinstance(slice_key, str) else "")
    master = _load_issuer_master()
    return _issuer_economics_module().build_issuer_economics(
        query, bundle,
        scope=scope,
        eligible_count=len(WITNESS_ROSTER.get(scope.slice_key, ())),
        alias_resolver=(master.securities_of_issuer if master is not None else None),
        dropped=dropped,
    )


_build_semiconductor_issuer_economics.lazy_target = (
    lambda: _issuer_economics_module().build_issuer_economics
)


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
    # Lane 5 v1.1 (amendment §6.2/§6.3): the issuer-economics block rides the
    # v2 QUERY envelope only, as a sibling of ``data``.
    issuer_economics=_build_semiconductor_issuer_economics,
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


# ---------------------------------------------------------------------------
# The closed PROFILE registry — the v2 company/sector profile kinds
# (packet §3.4, lane 5). Keyed by exact profile id, never by anchor: a
# profile entry carries NO theme anchor of its own (its ``anchor_theme_id``
# column holds the profile id so the entry has exactly one identity). The
# declarative columns below are literals pinned against each adapter's own
# constants by the registry suite — the mounts leaf carries no profile
# facts, so the reconciliation test is the drift guard instead of the mount.
# ---------------------------------------------------------------------------

def _technology_adapter() -> Any:
    """The Technology §8 registration adapter, imported on FIRST USE only.

    The adapter imports the sealed Technology composer eagerly on its own
    import; binding it lazily here keeps the registry's import closure free
    of every vertical, exactly as for the semiconductor composer."""
    from engine.market_ontology import (  # noqa: PLC0415 — lazy by design
        technology_research_registration,
    )
    return technology_research_registration


def _compose_technology(*args: Any, **kwargs: Any) -> Mapping[str, Any]:
    return _technology_adapter().compose(*args, **kwargs)


def _select_technology_evidence(*args: Any, **kwargs: Any) -> Mapping[str, Any]:
    return _technology_adapter().select_evidence(*args, **kwargs)


def _build_technology_query(**fields: Any) -> Any:
    return _technology_adapter().build_query(**fields)


def _load_technology_owner_bundle(query: Any, *, rights_snapshot: Any = None) -> Any:
    return _technology_adapter().load_bundle(query, rights_snapshot=rights_snapshot)


_compose_technology.lazy_target = lambda: _technology_adapter().compose
_select_technology_evidence.lazy_target = (
    lambda: _technology_adapter().select_evidence
)
_build_technology_query.lazy_target = lambda: _technology_adapter().build_query
_load_technology_owner_bundle.lazy_target = (
    lambda: _technology_adapter().load_bundle
)

#: Declarative Technology columns — literals reconciled against
#: ``technology_research_registration.TECHNOLOGY_REGISTRATION_FACTS`` and
#: the module's own constants by the registry suite.
_TECHNOLOGY = VerticalRegistration(
    anchor_theme_id="technology_economic_change.v1",
    slice_keys=(),
    view_keys=(
        "business", "comparison", "counter_observations", "identity", "coverage",
    ),
    schema_id="technology_economic_change.v1",
    evidence_schema_id="technology_economic_change.evidence.v2",
    definition_version="2026-09-24.1",
    compose=_compose_technology,
    select_evidence=_select_technology_evidence,
    load_bundle=_load_technology_owner_bundle,
    build_query=_build_technology_query,
    title_en="Technology economic-change research",
    title_zh="科技产业经济变化研究",
    note_en=(
        "Paid research context for members. Nothing here ranks, gates, sizes "
        "or times anything."
    ),
    note_zh="会员研究内容。此处内容不构成排序、准入、仓位或时机判断。",
    entry_kind="company_profile",
    profile_id="technology_economic_change.v1",
    subject_field="company_ref",
    subject_values=(),
    time_modes=("latest",),
    single_document=True,
    native_generation_prefix="tecd_",
    native_generation_width=32,
    native_generation_field="dossier_id",
    evidence_refs_field=None,
)


def _finance_adapter() -> Any:
    """The Finance §8 registration adapter, imported on FIRST USE only.

    The adapter imports the finance projection at its own import time;
    binding it lazily here keeps the registry importable by producers
    without the projection's closure."""
    from engine.sector_intelligence import (  # noqa: PLC0415 — lazy by design
        finance_research_registration,
    )
    return finance_research_registration


def _compose_finance(*args: Any, **kwargs: Any) -> Mapping[str, Any]:
    return _finance_adapter().compose(*args, **kwargs)


def _select_finance_evidence(*args: Any, **kwargs: Any) -> Mapping[str, Any]:
    return _finance_adapter().select_evidence(*args, **kwargs)


def _build_finance_query(**fields: Any) -> Any:
    return _finance_adapter().build_query(**fields)


def _load_finance_owner_bundle(query: Any, *, rights_snapshot: Any = None) -> Any:
    return _finance_adapter().load_bundle(query, rights_snapshot=rights_snapshot)


_compose_finance.lazy_target = lambda: _finance_adapter().compose
_select_finance_evidence.lazy_target = lambda: _finance_adapter().select_evidence
_build_finance_query.lazy_target = lambda: _finance_adapter().build_query
_load_finance_owner_bundle.lazy_target = lambda: _finance_adapter().load_bundle

#: Declarative Finance columns — literals reconciled against
#: ``finance_research_registration.FINANCE_REGISTRATION_FACTS`` and the
#: module's own constants by the registry suite.
_FINANCE = VerticalRegistration(
    anchor_theme_id="finance_intelligence_research.v1",
    slice_keys=(),
    view_keys=("dossier",),
    schema_id="finance_intelligence_research.v1",
    evidence_schema_id="finance_intelligence_research.evidence.v1",
    definition_version="2026-09-25.1",
    compose=_compose_finance,
    select_evidence=_select_finance_evidence,
    load_bundle=_load_finance_owner_bundle,
    build_query=_build_finance_query,
    title_en="Finance Intelligence",
    title_zh="金融情报",
    note_en=(
        "A rerating-first read of the financial system for members. "
        "Nothing here ranks, gates, sizes or times anything."
    ),
    note_zh=(
        "面向会员的金融体系重估研究。此处内容不构成排序、准入、仓位或时机判断。"
    ),
    entry_kind="sector_profile",
    profile_id="finance_intelligence_research.v1",
    subject_field="sector_ref",
    subject_values=("sector:financials",),
    time_modes=("latest",),
    single_document=True,
    native_generation_prefix="gen_",
    native_generation_width=32,
    evidence_refs_field="assertion_refs",
)

_PROFILE_ENTRIES: tuple[VerticalRegistration, ...] = (_TECHNOLOGY, _FINANCE)


def _assert_unique_profiles(entries: tuple[VerticalRegistration, ...]) -> None:
    """Load-time closure: a profile id is registered once, and no profile id
    collides with a theme anchor (the two registries name disjoint key
    spaces; a collision would make one registration unreachable)."""
    ids = [entry.profile_id for entry in entries]
    for profile_id in ids:
        if ids.count(profile_id) != 1:
            raise RuntimeError(
                f"theme_research_registry: profile registered twice: {profile_id!r}"
            )
        if profile_id in REGISTRY:
            raise RuntimeError(
                f"theme_research_registry: profile id collides with a theme "
                f"anchor: {profile_id!r}"
            )


_assert_unique_profiles(_PROFILE_ENTRIES)

#: Closed, read-only mapping ``profile_id -> VerticalRegistration`` for the
#: v2 profile entry kinds. Lookup is exact-string, no normalisation, no
#: default — ``profile_registration_for`` mirrors :func:`registration_for`.
PROFILE_REGISTRY: Mapping[str, VerticalRegistration] = MappingProxyType(
    {entry.profile_id: entry for entry in _PROFILE_ENTRIES}
)


def profile_registration_for(profile_id: object) -> VerticalRegistration | None:
    """Exact-key lookup for a ``company_profile``/``sector_profile`` request's
    ``profile_id``. No normalisation, no pattern, no default.

    Returns ``None`` for anything that is not a registered profile id; the
    caller applies its own fail-closed private 404.
    """
    if not isinstance(profile_id, str):
        return None
    return PROFILE_REGISTRY.get(profile_id)
