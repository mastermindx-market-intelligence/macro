"""Semiconductor Theme Intelligence B — the owner-bundle loader the closed
registration hands to the theme-research shell (T08c-2).

What it serves
--------------
The PUBLIC half only. For the request's slice it resolves the declared
witness cohort through :mod:`engine.market_ontology.semiconductor_witness_scope`
(Theme Graph + Data OS owners; Sol #7780 issuecomment-5813801605: a declared
limited proof cohort carrying ``slice_scope_unowned``), reads each witness's
CURRENT event workspace and the IMMEDIATELY PRECEDING fiscal period through
the Company Intelligence reader's model-facing surfaces
(:func:`~engine.neuralweb.company_intelligence_reader.read_current_event_workspace`,
:func:`~engine.neuralweb.company_intelligence_reader.read_event_workspace` —
marker → immutable generation → sha256 receipt → contract validation; never a
base-URL override, never a producer or raw surface, never the predecessor
chain walk), refuses a workspace whose issuer CIK disagrees with the identity
plane, and projects the survivors with
:func:`~engine.market_ontology.workspace_projection.project_event_workspace`
into the composer's ``event_workspaces`` row shape. Two consecutive periods
are what the composer's economics pane needs (the earlier release's guidance
is ``prior``; the later release's reported figure is ``actual`` and its
guidance the ``new_outlook``).

What it declares absent
-----------------------
The PRIVATE half. ``assertions``, ``identity_results``, ``financial_packets``,
``interpretation_blocks`` and ``native_refs`` are empty and the bundle ALWAYS
carries the omission ``private_assertions_unbound`` (private binding R4 is an
open Sol ruling). The composer turns every omission into ``omitted:<name>``,
so the served response SAYS the industrial half is missing; nothing here
synthesises an assertion, an identity label or a financial packet.
``financial_packets=()`` is the designed steady state (derivation is
unowned).

Wire grammar of omissions
-------------------------
The owners' tokens carry a colon (``identity_unverified:TSM``,
``reported_malformed:<metric>``); the composer prefixes ``omitted:`` and the
frozen ``semiconductor_theme_research.v1`` limitation grammar allows exactly
ONE colon (``^[a-z0-9_]+(?::[A-Za-z0-9_.-]+)?$``). :func:`wire_omission`
therefore joins name and detail with ``.``, maps every foreign character to
``-``, and bounds the token; the tokens are data (an owner echo can carry a
raw request value), never trusted text.

Refusals
--------
* ``time_mode == "system_replay"``: refused with the composer's
  ``ResearchRefusal("identity_vintage_unsupported")`` before any reader call
  (Sol 5813801605: "refuse affected system_replay without supported as-known
  identity; a nightly rebuild time is not mapping_learned_at; latest can
  proceed within its own qualified scope; source_history is not system
  belief"). ``latest`` and ``source_history`` proceed — the composer applies
  no identity vintage to public workspaces in either.
* A reader that raises past its own envelope, an envelope that breaks the
  reader's contract, or a rights snapshot without a revision:
  :class:`~engine.market_ontology.theme_research_binding.BundleUnavailable`
  → the shell's private 503. Coverage absence is never a failure: it is a
  typed omission (``workspace_unavailable.<TICKER>`` when the reader's
  documented coverage-absence note is returned for the current period;
  ``workspace_unavailable.<TICKER>-<YYYYQn>`` when the preceding alias is not
  published). The preceding read is a single-alias read whose envelope
  reports every refusal as ``available: False`` + note; when that note is
  NOT one of the reader's two coverage-absence literals (alias unresolved /
  event not covered) the period is recorded as ``workspace_unverified.<alias>``
  instead — a receipt, validation or transport failure on an object the
  manifest advertises — and the economics pane still degrades to
  ``witness_economics_missing`` rather than failing a request that a
  single-period issuer would legitimately produce. The current read fails the
  request on the same failures because the reader itself documents them as a
  503 class.

Authority
---------
None. The cohort grants no membership, breadth or rank authority and cannot
satisfy a general coverage proof; public workspaces alone are not research
acceptance. No ranking, gating, sizing, entry or origination flag is read or
written; the only arithmetic is stepping a validated fiscal label back one
quarter.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
from typing import Any

from engine.market_ontology.semiconductor_theme_research import (
    OwnerBundle,
    ResearchQuery,
    ResearchRefusal,
)
from engine.market_ontology.semiconductor_witness_scope import (
    WitnessIdentity,
    WitnessScope,
    resolve_witness_scope,
    verify_workspace_cik,
)
from engine.market_ontology.theme_research_binding import BundleUnavailable
from engine.market_ontology.workspace_projection import project_event_workspace
from engine.neuralweb import company_intelligence_reader as reader
from engine.theme_graph.rights import load_registry_snapshot

__all__ = [
    "IDENTITY_MISMATCH",
    "IDENTITY_VINTAGE_UNSUPPORTED",
    "PERIOD_UNSTEPPABLE",
    "PRIVATE_ASSERTIONS_UNBOUND",
    "WORKSPACE_UNAVAILABLE",
    "WORKSPACE_UNPROJECTABLE",
    "WORKSPACE_UNVERIFIED",
    "load_semiconductor_owner_bundle",
    "scope_filter",
    "wire_omission",
    "WORKSPACE_GENERATION_SPLIT",
    "WORKSPACE_GENERATION_UNQUALIFIED",
]

# Omission names this loader emits (the owners' own tokens are lifted verbatim
# and then wire-normalised alongside these).
PRIVATE_ASSERTIONS_UNBOUND = "private_assertions_unbound"
WORKSPACE_UNAVAILABLE = "workspace_unavailable"
WORKSPACE_UNVERIFIED = "workspace_unverified"
WORKSPACE_UNPROJECTABLE = "workspace_unprojectable"
IDENTITY_MISMATCH = "identity_mismatch"
PERIOD_UNSTEPPABLE = "period_unsteppable"
WORKSPACE_GENERATION_SPLIT = "workspace_generation_split"
WORKSPACE_GENERATION_UNQUALIFIED = "workspace_generation_unqualified"
OMISSIONS_TRUNCATED = "omissions_truncated"
# Refusal code for a research mode this surface cannot serve (see module doc).
IDENTITY_VINTAGE_UNSUPPORTED = "identity_vintage_unsupported"

# The reader's two coverage-absence notes for a single-alias read
# (engine/neuralweb/company_intelligence_reader.py::_load_event_workspace:
# "event workspace alias could not be resolved" when the alias is not in the
# manifest, "event workspace does not cover this event" when the manifest has
# no receipt for it). Every other note on a preceding read is a failure on an
# advertised object and is recorded as ``workspace_unverified``.
_PRECEDING_ABSENT_NOTES = frozenset({
    "event workspace alias could not be resolved",
    "event workspace does not cover this event",
})

_NAME_CHARS = frozenset("abcdefghijklmnopqrstuvwxyz0123456789_")
_DETAIL_CHARS = frozenset(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_.-"
)
_MAX_TOKEN_LENGTH = 64
_MAX_TOKENS = 64
_MALFORMED_NAME = "omission_malformed"


# ---------------------------------------------------------------------------
# Wire grammar
# ---------------------------------------------------------------------------

def wire_omission(token: object) -> str:
    """Normalise one owner omission token to the frozen limitation grammar.

    ``name:detail`` → ``name.detail`` (the composer adds the one permitted
    colon as ``omitted:``); a non-string or a name outside ``[a-z0-9_]``
    becomes ``omission_malformed``; every detail character outside
    ``[A-Za-z0-9_.-]`` becomes ``-``; the result is bounded to 64 characters.
    Pure; never raises.
    """
    if not isinstance(token, str):
        return _MALFORMED_NAME
    text = str.__str__(token)  # exact-str copy: a hostile subclass runs no code below
    name, _, detail = text.partition(":")
    if not name or any(char not in _NAME_CHARS for char in name):
        name = _MALFORMED_NAME
    detail = "".join(char if char in _DETAIL_CHARS else "-" for char in detail)
    wire = f"{name}.{detail}" if detail else name
    return wire[:_MAX_TOKEN_LENGTH]


def _wire_omissions(tokens: list[object]) -> tuple[str, ...]:
    """Dedupe (first occurrence wins), normalise, bound the count."""
    seen: list[str] = []
    for token in tokens:
        wire = wire_omission(token)
        if wire not in seen:
            seen.append(wire)
    if len(seen) > _MAX_TOKENS:
        seen = seen[: _MAX_TOKENS - 1] + [OMISSIONS_TRUNCATED]
    return tuple(seen)


# ---------------------------------------------------------------------------
# Period stepping — the one piece of arithmetic (a fiscal label, not a figure)
# ---------------------------------------------------------------------------

def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _preceding_alias(ticker: str, fiscal_period: Mapping[str, Any]) -> str | None:
    """``TICKER/YYYYQn`` for the fiscal period immediately before the row's.

    Fiscal labels step uniformly: Qn → Q(n-1) in the same labelled year, Q1 →
    Q4 of the previous labelled year, whatever the issuer's calendar mapping.
    ``None`` when the row's period is not a validated ``(year, quarter)``.
    """
    year = fiscal_period.get("year")
    quarter = fiscal_period.get("quarter")
    if not (_is_int(year) and _is_int(quarter)):
        return None
    if not (1 <= quarter <= 4 and 1000 <= year <= 9999):
        return None
    if quarter == 1:
        year, quarter = year - 1, 4
    else:
        quarter = quarter - 1
    return f"{ticker}/{year}Q{quarter}"


# ---------------------------------------------------------------------------
# Reader admission — one workspace envelope → one composer row, or a token
# ---------------------------------------------------------------------------

def _admit(
    identity: WitnessIdentity,
    envelope: Mapping[str, Any],
    tokens: list[object],
    revisions: list[tuple[str, str]],
) -> dict[str, Any] | None:
    """Project one ``available: True`` reader envelope for ``identity``.

    Refuses (typed omission, ``None``) a workspace the projector cannot shape
    or whose CIK disagrees with the identity plane; lifts every row-level
    projector omission into ``tokens``; records ``("event", event_id)`` and
    ``("generation", generation_id)`` for the generation fingerprint.
    """
    workspace = envelope.get("workspace")
    if not isinstance(workspace, Mapping):
        raise BundleUnavailable("reader envelope carries no workspace")
    receipt = envelope.get("receipt")
    receipt = receipt if isinstance(receipt, Mapping) else {}
    raw_event_id = workspace.get("event_id")
    label = raw_event_id if isinstance(raw_event_id, str) and raw_event_id else "unknown"
    row = project_event_workspace(workspace)
    if row is None:
        tokens.append(f"{WORKSPACE_UNPROJECTABLE}:{label}")
        return None
    if not verify_workspace_cik(identity, row.get("cik")):
        tokens.append(f"{IDENTITY_MISMATCH}:{identity.ticker}")
        return None
    for omission in row.get("omissions") or ():
        tokens.append(omission)
    served = {key: value for key, value in row.items() if key != "omissions"}
    # The identity plane's answer, not a label learned from the workspace.
    served["company_node_id"] = identity.company_node_id
    revisions.append(("event", served["event_id"]))
    generation = receipt.get("generation_id")
    if isinstance(generation, str) and generation:
        revisions.append(("generation", generation))
    return served


def _generation_of(envelope: Mapping[str, Any]) -> str | None:
    """The publication generation a reader envelope's receipt was qualified in,
    or None when the receipt carries none.

    None is not a detail to tolerate: a workspace with no generation is a
    workspace no owner snapshot vouches for, and it may not anchor or join a
    comparison (Sol #7780 issuecomment-5825621672 item 3).
    """
    receipt = envelope.get("receipt")
    if not isinstance(receipt, Mapping):
        return None
    generation = receipt.get("generation_id")
    return generation if isinstance(generation, str) and generation else None


def _read(surface: Any, params: Mapping[str, Any]) -> Mapping[str, Any]:
    """Call one model-facing reader surface; a raise past the reader's own
    envelope, or a non-mapping envelope, is a transport failure."""
    try:
        envelope = surface(params)
    except Exception as exc:  # noqa: BLE001 — the reader's message must never cross the wire
        raise BundleUnavailable("company-intelligence reader raised") from exc
    if not isinstance(envelope, Mapping):
        raise BundleUnavailable("company-intelligence reader returned no envelope")
    return envelope


def _serve_witness(
    identity: WitnessIdentity,
) -> tuple[list[dict[str, Any]], list[tuple[str, str]], list[object]]:
    """The current and the preceding fiscal period for one verified witness.

    The current read distinguishes coverage absence (the reader's documented
    note, ``read_current_event_workspace`` docstring: "note exactly ...") from
    every other refusal, which the reader itself documents as a 503 class —
    so it fails this request rather than serving a silent gap. The nest is
    then proven reachable; the preceding alias is a single-alias read whose
    envelope does not separate "not published" from a transport fault, so an
    unavailable preceding period is a typed omission and the economics pane
    degrades to ``witness_economics_missing`` instead of the request failing.
    """
    rows: list[dict[str, Any]] = []
    revisions: list[tuple[str, str]] = []
    tokens: list[object] = []

    current = _read(reader.read_current_event_workspace, {"ticker": identity.ticker})
    if current.get("available") is not True:
        if current.get("note") == reader._NOT_COVERED_NOTE:  # noqa: SLF001 — the reader's documented contract string
            tokens.append(f"{WORKSPACE_UNAVAILABLE}:{identity.ticker}")
            return rows, revisions, tokens
        raise BundleUnavailable("company-intelligence reader refused the current workspace")
    current_row = _admit(identity, current, tokens, revisions)
    if current_row is None:
        return rows, revisions, tokens
    rows.append(current_row)

    alias = _preceding_alias(identity.ticker, current_row.get("fiscal_period") or {})
    if alias is None:
        tokens.append(f"{PERIOD_UNSTEPPABLE}:{identity.ticker}")
        return rows, revisions, tokens
    prior = _read(reader.read_event_workspace, {"event_id": alias})
    if prior.get("available") is not True:
        absent = prior.get("note") in _PRECEDING_ABSENT_NOTES
        tokens.append(f"{WORKSPACE_UNAVAILABLE if absent else WORKSPACE_UNVERIFIED}:{alias}")
        return rows, revisions, tokens
    # ONE OWNER-QUALIFIED SNAPSHOT PER COMPARISON (Sol #7780
    # issuecomment-5825621672 item 3, grain fixed by 5825811888 item 4). Both
    # halves of this economics comparison come from ONE publication domain —
    # Company Intelligence event workspaces — so they must come from one
    # generation of it. If publication advances A->B between the current read
    # and the preceding read, the pair describes two different worlds, and the
    # panel would present them as one. The comparison is withheld instead.
    #
    # This is checked BEFORE ``_admit`` deliberately: admitting the row first
    # would record its ("event", ...) and ("generation", ...) in the revision
    # fingerprint, so the served bundle would name a period it does not serve.
    #
    # The native reader's 300-second manifest cache usually makes the two reads
    # reuse one manifest. That is helpful behaviour, not proof, and this guard
    # does not rely on it.
    #
    # The rule is scoped to THIS publication domain and is not a general
    # equality rule over unrelated generation strings: 5825811888 item 4
    # forbids comparing generations across independent domains, which have no
    # common clock to be equal in.
    current_generation = _generation_of(current)
    prior_generation = _generation_of(prior)
    if current_generation is None or prior_generation is None:
        tokens.append(f"{WORKSPACE_GENERATION_UNQUALIFIED}:{alias}")
        return rows, revisions, tokens
    if current_generation != prior_generation:
        tokens.append(f"{WORKSPACE_GENERATION_SPLIT}:{alias}")
        return rows, revisions, tokens

    prior_row = _admit(identity, prior, tokens, revisions)
    if prior_row is not None:
        rows.append(prior_row)
    return rows, revisions, tokens


# ---------------------------------------------------------------------------
# Scope — data AND evidence filtered by the same declared cohort
# ---------------------------------------------------------------------------

def scope_filter(bundle: OwnerBundle, scope: WitnessScope) -> OwnerBundle:
    """Apply the declared cohort to every input tuple (Sol 5813801605:
    "consistently filtering data AND evidence").

    An empty cohort empties every input — never a fall-through to an unscoped
    bundle. A non-empty cohort keeps only event workspaces whose CIK the
    hardened comparator :func:`verify_workspace_cik` accepts for a witness.
    The private half is unbound today (R4 open), so the five private tuples
    reaching this seam are always empty — and this seam FAILS CLOSED
    (:class:`BundleUnavailable`) the moment any of them is non-empty, because
    no cohort rule for assertions, identity results, financial packets,
    interpretation blocks or native references has been accepted yet. The R4
    commit that binds them must extend this function with the native-subject
    CIK rule before anything passes; it cannot slip through unscoped. The
    seam grants no membership, breadth or rank authority.
    """
    if not scope.identities:
        return replace(
            bundle,
            assertions=(),
            identity_results=(),
            event_workspaces=(),
            financial_packets=(),
            interpretation_blocks=(),
            native_refs=(),
        )
    if (bundle.assertions or bundle.identity_results or bundle.financial_packets
            or bundle.interpretation_blocks or bundle.native_refs):
        raise BundleUnavailable("private inputs reached the scope seam before R4 keyed them")
    workspaces = tuple(
        workspace for workspace in bundle.event_workspaces
        if isinstance(workspace, Mapping)
        and any(verify_workspace_cik(identity, workspace.get("cik")) for identity in scope.identities)
    )
    return replace(bundle, event_workspaces=workspaces)


# ---------------------------------------------------------------------------
# The registered loader
# ---------------------------------------------------------------------------

def load_semiconductor_owner_bundle(
    query: ResearchQuery,
    *,
    rights_snapshot: tuple[str, Mapping[str, Any]] | None = None,
) -> OwnerBundle:
    """Serve the public half for ``query``; declare the private half absent.

    Reads from the request ONLY ``query.slice_key`` and ``query.time_mode``
    (the anchor was already resolved by the closed registration); never a
    path, URL, locator, event id, ticker or CIK. ``rights_snapshot`` is the
    ONE rights registry read the shell performs per request and also enforces
    with, so the fingerprinted ``rights_revision`` equals the enforced one;
    when absent (direct callers) the loader reads the snapshot itself.
    """
    if query.time_mode == "system_replay":
        raise ResearchRefusal(IDENTITY_VINTAGE_UNSUPPORTED)
    snapshot = rights_snapshot if rights_snapshot is not None else load_registry_snapshot()
    if not (isinstance(snapshot, tuple) and len(snapshot) == 2
            and isinstance(snapshot[0], str) and snapshot[0]):
        raise BundleUnavailable("rights snapshot carries no revision")
    rights_revision = snapshot[0]

    scope = resolve_witness_scope(query.slice_key)
    tokens: list[object] = [PRIVATE_ASSERTIONS_UNBOUND, *scope.omissions]
    rows: list[dict[str, Any]] = []
    revisions: list[tuple[str, str]] = []
    for identity in scope.identities:
        served_rows, served_revisions, served_tokens = _serve_witness(identity)
        rows.extend(served_rows)
        revisions.extend(served_revisions)
        tokens.extend(served_tokens)
        revisions.append(("identity", f"{identity.issuer_id}={identity.cik}"))

    bundle = OwnerBundle(
        revision_tuple=tuple(sorted(set(revisions))),
        rights_revision=rights_revision,
        assertions=(),
        identity_results=(),
        event_workspaces=tuple(rows),
        financial_packets=(),
        interpretation_blocks=(),
        native_refs=(),
        omissions=_wire_omissions(tokens),
    )
    return scope_filter(bundle, scope)
