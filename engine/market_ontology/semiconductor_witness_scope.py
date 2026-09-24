"""Declared witness roster + identity join through the existing owners (T08c-1).

Operation gmi-semiconductors-fable-ceo-e2e-20260923-chairman-001 (carrier
PR #7870). The composer never filters by ``slice_key`` and ``_build_economics``
picks ONE best triple across every company in the bundle, so the binder must
scope event workspaces to the slice BEFORE composing or the same economics
panel is served for ``hbm_packaging`` and ``sic_gan_specialty``.

WITNESS ROSTER, NOT AN AUTHORITY
--------------------------------
:data:`WITNESS_ROSTER` is the declared two-witness proof cohort for the
Semiconductor B acceptance (W-A HBM/advanced packaging with TSMC, W-B non-AI
SiC/GaN with onsemi). It is NOT a membership, ranking, entry, sizing, index or
breadth authority and cannot satisfy a general coverage proof. No estate owner
binds TSMC or onsemi to ``ai_semiconductors`` or to a slice today
(``data/theme_graph/edges.parquet`` has no 1- or 2-hop path from ``co:us:TSM``
/ ``co:us:ON`` to ``theme:ai_semiconductors``; ``data/baskets/membership.json``
``ai_semiconductors`` has neither; ``config/theme_crosswalk.yml`` names baskets
only). Durable slice ownership is escalated to Sol (PR #7780
issuecomment-5813739560, item 2); until ruled, EVERY result this module
returns carries :data:`SLICE_SCOPE_UNOWNED` in ``omissions`` so the response
says so (Sol ruling issuecomment-5813801605: "declared limited cohort
``slice_scope_unowned``, consistently filtering data AND evidence").

IDENTITY JOIN — OWNER APIS ONLY, IN THIS ORDER
----------------------------------------------
For each roster ticker:

1. ``engine.theme_graph.identity.company_node_id("baskets", ticker)`` mints the
   canonical graph node id (``co:us:TSM``);
2. ``engine.theme_graph.identity_resolution.resolve_graph_node_identity(node_id)``
   returns the node's typed resolution row from the persisted sidecar; the row
   must carry ``resolution_state == "RESOLVED"`` and a non-empty ``issuer_id``;
3. ``lib.dataos.identity.IssuerMaster.cik_of_issuer(issuer_id)`` — the ONE
   canonical Data OS issuer reader — yields the evidenced CURRENT ten-digit
   CIK. The reader is constructed from the committed
   ``data/reference/security_master.parquet`` rows by ONE immutable byte read
   per call through :func:`_load_issuer_master` (the reader's own contract:
   "reading the parquet is the caller's job", exactly as
   ``app/prophet_lab._load_issuer_master`` and
   ``engine/intelligence_workspace/entity._security_sources`` do). No other
   Data OS artifact is read here; nothing is written.

On ANY refusal, exception or missing value along that chain the ticker yields
NO identity and ``"identity_unverified:<ticker>"`` is recorded; when the Data
OS master itself cannot be located or read, ``"identity_source_unavailable"``
is recorded once in addition, so the two failure classes stay
distinguishable without disclosing paths or exception text. There is no
guess, no ticker-equality fallback and no invented ``co:*`` node. The two
identity clocks (the sidecar's ``master_generated_at`` / ``resolution_asof``
and the live master read) are NOT compared here — a build id is not a
learning date; a stale sidecar fails closed only when its ``issuer_id`` no
longer exists in the master (recorded as a known limitation, review nit 4).

NO ``mapping_learned_at``. The identity sidecar is re-derived nightly
(``resolution_asof`` / ``computed_at`` are rebuild stamps), so no honest
learning date exists for a ticker→CIK mapping; ``system_replay`` over an
as-known identity is therefore unsupported on this surface (escalated as
item 3 of #7780 issuecomment-5813739560) and no field of that name appears
in any result.

Pure and closed: no network, no store write, no config file, no new parquet,
no FastAPI or ``app/**`` import, no fuzzy matching, no name search, no
ranking, no authority flag, no arithmetic. :func:`resolve_witness_scope`
never raises for a string ``slice_key``.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from types import MappingProxyType

from lib import config
from lib.dataos.identity import IssuerMaster
from engine.theme_graph import identity as graph_identity
from engine.theme_graph import identity_resolution

__all__ = [
    "IDENTITY_SOURCE_UNAVAILABLE",
    "SLICE_SCOPE_UNOWNED",
    "WITNESS_ROSTER",
    "WitnessIdentity",
    "WitnessScope",
    "resolve_witness_scope",
    "verify_workspace_cik",
]

#: Every result carries this token: durable slice ownership is escalated, not
#: owned (see the module docstring).
SLICE_SCOPE_UNOWNED = "slice_scope_unowned"

#: Recorded (once) when the Data OS issuer master could not be loaded at all —
#: a distinct diagnostic from a graph-side refusal, so an operator chases the
#: master, not the graph. Every roster ticker is then ``identity_unverified``.
IDENTITY_SOURCE_UNAVAILABLE = "identity_source_unavailable"

#: The graph suite the witnesses' company nodes are minted in.
GRAPH_SUITE = "baskets"

#: Closed, read-only witness roster ``slice_key -> tickers`` for the B proof.
#: Adding a witness is an additive edit here AND a new declared limitation; it
#: is never membership.
WITNESS_ROSTER: Mapping[str, tuple[str, ...]] = MappingProxyType({
    "hbm_packaging": ("TSM",),
    "sic_gan_specialty": ("ON",),
})

_CIK_DIGITS = frozenset("0123456789")
_CIK_LENGTH = 10


@dataclass(frozen=True)
class WitnessIdentity:
    """One witness, joined through the three owners. Every field is the exact
    string the owner returned (the CIK is the Data OS reader's ten-digit form).
    Deliberately NO ``mapping_learned_at`` (module docstring)."""

    ticker: str
    company_node_id: str
    issuer_id: str
    cik: str


@dataclass(frozen=True)
class WitnessScope:
    """The scoped cohort for one slice plus the typed omissions the response
    must carry. ``identities`` is in roster order; ``omissions`` always
    contains :data:`SLICE_SCOPE_UNOWNED`."""

    slice_key: str
    identities: tuple[WitnessIdentity, ...]
    omissions: tuple[str, ...]


def _is_ten_digit_cik(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == _CIK_LENGTH
        and all(char in _CIK_DIGITS for char in value)
    )


def _load_issuer_master(root: Path | None = None) -> IssuerMaster | None:
    """Build the canonical Data OS issuer reader from ONE immutable byte read
    of the committed security master (the Theme Graph's own locator constants
    name the artifact). ``None`` when the artifact is absent or unreadable —
    every witness then resolves as ``identity_unverified``. Nothing here can
    raise: locating the artifact (``config.data_dir()`` reads the repo's
    ``config.yml``) is inside the same fail-closed guard as reading it. The
    accepted cost: a programming error in the locate step is indistinguishable
    from an absent artifact — both surface to the operator only as
    :data:`IDENTITY_SOURCE_UNAVAILABLE` on the caller's omissions."""
    try:
        base = Path(root) if root is not None else config.data_dir()
        path = base / identity_resolution.REFERENCE_SUBDIR / identity_resolution.MASTER_FILE
        if not path.is_file():
            return None
        import pandas as pd  # noqa: PLC0415 — the reader's caller reads the parquet

        raw = path.read_bytes()
        records = pd.read_parquet(BytesIO(raw)).to_dict("records")
        return IssuerMaster.from_records(records)
    except Exception:  # noqa: BLE001 — an unlocatable/unreadable master is a refusal, never a raise
        return None


def _resolve_one(ticker: str, issuer_master: IssuerMaster | None) -> WitnessIdentity | None:
    """The owner chain for one ticker; ``None`` on any refusal (the caller
    records ``identity_unverified:<ticker>``)."""
    if issuer_master is None:
        return None
    try:
        node_id = graph_identity.company_node_id(GRAPH_SUITE, ticker)
        row = identity_resolution.resolve_graph_node_identity(node_id)
        if not isinstance(row, Mapping):
            return None
        if row.get("resolution_state") != "RESOLVED":
            return None
        issuer_id = row.get("issuer_id")
        if not isinstance(issuer_id, str) or not issuer_id:
            return None
        cik = issuer_master.cik_of_issuer(issuer_id)
    except Exception:  # noqa: BLE001 — unknown node, ambiguous CIK, unreadable owner: refuse
        return None
    if not _is_ten_digit_cik(cik):
        return None
    return WitnessIdentity(ticker=ticker, company_node_id=node_id, issuer_id=issuer_id, cik=cik)


def resolve_witness_scope(slice_key: str) -> WitnessScope:
    """Resolve the declared witness cohort for ``slice_key`` through the owner
    APIs. Unknown slice → no identities and ``slice_unknown:<slice_key>``;
    every result carries :data:`SLICE_SCOPE_UNOWNED`. Never raises for a
    string input."""
    omissions: list[str] = []
    if not isinstance(slice_key, str):
        return WitnessScope(slice_key="", identities=(),
                            omissions=("slice_unknown:<non_string>", SLICE_SCOPE_UNOWNED))
    # Exact-``str`` copy: a hostile ``str`` subclass (raising ``__hash__`` /
    # ``__str__`` / ``__format__``) runs no code in the lookup or the token.
    slice_key = str.__str__(slice_key)
    tickers = WITNESS_ROSTER.get(slice_key)
    if tickers is None:
        omissions.append(f"slice_unknown:{slice_key}")
        omissions.append(SLICE_SCOPE_UNOWNED)
        return WitnessScope(slice_key=slice_key, identities=(), omissions=tuple(omissions))

    issuer_master = _load_issuer_master()
    if issuer_master is None:
        omissions.append(IDENTITY_SOURCE_UNAVAILABLE)
    identities: list[WitnessIdentity] = []
    for ticker in tickers:
        identity = _resolve_one(ticker, issuer_master)
        if identity is None:
            omissions.append(f"identity_unverified:{ticker}")
            continue
        identities.append(identity)
    omissions.append(SLICE_SCOPE_UNOWNED)
    return WitnessScope(slice_key=slice_key, identities=tuple(identities), omissions=tuple(omissions))


def verify_workspace_cik(identity: WitnessIdentity, workspace_cik: object) -> bool:
    """Exact string equality on the ten-digit form — the binder refuses a
    workspace whose CIK disagrees with the identity plane. No padding, no
    stripping, no int coercion; always a real ``bool``. The comparison is
    ``str.__eq__`` bound on the identity's exact ``str`` (never the operand's
    reflected ``__eq__``), so a ``str`` subclass with a truthy non-bool
    ``__eq__`` cannot pass as a match and one with a falsy ``__eq__`` cannot
    hide a real match."""
    return isinstance(workspace_cik, str) and str.__eq__(identity.cik, workspace_cik) is True
