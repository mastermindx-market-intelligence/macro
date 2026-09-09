"""GMI exposure composer: pure shock -> theme -> company projection (A-F04-W2-1).

Authority ceiling: ``research_display_only``. This module originates no score, rank,
confidence, weight, ordering-by-magnitude, gate, size or trade semantic. It is a
read-only projection of edges the theme graph already holds, at a caller-supplied
as-of date, rights-filtered through the owner's own gate
(``engine.theme_graph.rights``). Nothing in the scoring path imports it, and it
imports nothing from the scoring core (test 13 enforces both directions).

Three laws, restated from the frozen spec:

* L1 — owner-side reads only: GMI is reached ONLY through
  ``engine.theme_graph.store.read_edges`` / ``read_identity_resolution``.
* L2 — nothing new in the graph: no new node kind, no new edge type, no new store,
  no generic ``RELATED`` traversal, no causal DAG, no opportunity scalar.
* L3 — no value may order anything (G0.11): every list here is ordered by node id
  (or ``(code, subject_id)`` for typed-null lists), never by a magnitude.

The shock -> theme link is CALLER-SUPPLIED (``ShockSpec``), never derived: this module
does not and may never infer which themes a macro shock hits — that is a causal claim.

No clock, no network, no LLM, no ``data/`` write. A loader exception, an unknown shock,
a rights refusal and an unresolved identifier are all TYPED NULLS in the return value —
this module never raises for a data-availability reason.
"""
from __future__ import annotations

import dataclasses
import datetime
import re
import typing
from collections.abc import Callable, Mapping, Sequence
from typing import Any

SCHEMA_ID = "market_ontology.exposure_map/v1"
ENGINE_VERSION = "market_ontology.exposure_map.v1"
AUTHORITY_CEILING = "research_display_only"

# Production reads the append-only history. The owner's latest_belief=True view is
# as-of-independent (one row per edge_id at max belief_time overall) and cannot
# supply an earlier belief for a historical as-of; this module collapses itself.
_EDGE_READER = "engine.theme_graph.store.read_edges(latest_belief=False)"
_IDENTITY_READER = "engine.theme_graph.store.read_identity_resolution(latest=True)"
_CHAIN_READER = "engine.transmission_chains.load_chains()"
_BELIEF_COLLAPSE = (
    "max belief_time <= asof per edge_id (null belief_time never eligible); "
    "ties on computed_at then src then dst"
)

# --- §3.1 id grammars (closed allowlist) -----------------------------------------

_COMPANY_ID_RE = re.compile(r"^co:(us|cn|hk|ca|intl):[A-Za-z0-9.\-]+(#[0-9]+)?$")
_LOCAL_THEME_ID_RE = re.compile(r"^ltheme:(finviz|ths):[A-Za-z0-9_.\-]+$")


def _is_company_id(node_id: object) -> bool:
    return isinstance(node_id, str) and bool(_COMPANY_ID_RE.match(node_id))


def _is_local_theme_id(node_id: object) -> bool:
    return isinstance(node_id, str) and bool(_LOCAL_THEME_ID_RE.match(node_id))


def _is_canonical_theme_id(node_id: object) -> bool:
    return isinstance(node_id, str) and node_id.startswith("theme:")


def _is_known_theme_grammar(node_id: str) -> bool:
    return _is_local_theme_id(node_id) or _is_canonical_theme_id(node_id)


def _market_scope_of_company(node_id: str) -> str | None:
    m = _COMPANY_ID_RE.match(node_id)
    return m.group(1) if m else None


# --- copied verbatim from engine/intelligence_workspace/adapters/theme.py --------
# (this packet must not create a dependency between two consumer planes; the source
# module is a different consumer with its own contract, so these three tiny helpers
# are duplicated rather than imported.)

def _records(value: Any) -> list[Mapping[str, Any]]:
    if value is None:
        raise TypeError("owner view is absent")
    if hasattr(value, "to_dict"):
        rows = value.to_dict("records")
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        rows = list(value)
    else:
        raise TypeError("owner view is not tabular")
    if any(not isinstance(row, Mapping) for row in rows):
        raise TypeError("owner view contains a non-record row")
    return rows


def _is_null(value: Any) -> bool:
    if value is None:
        return True
    try:
        import pandas as pd

        return bool(pd.isna(value))
    except (ImportError, TypeError, ValueError):
        return False


def _date(value: Any) -> datetime.date | None:
    if _is_null(value):
        return None
    if isinstance(value, datetime.datetime):
        return value.date()
    if isinstance(value, datetime.date):
        return value
    try:
        return datetime.date.fromisoformat(str(value).strip())
    except (ValueError, TypeError):
        # A malformed date is a data-availability problem, never a reason to raise
        # (module docstring: "never raises for a data-availability reason"). Treated
        # as absent, same as a genuinely null value.
        return None


def _date_str(value: Any) -> str | None:
    d = _date(value)
    return d.isoformat() if d is not None else None


def _str_or_none(value: Any) -> str | None:
    return None if _is_null(value) else str(value)


# --- typed nulls (§4.5 / §4.6) ---------------------------------------------------

_REASONS: dict[str, tuple[str, str]] = {
    "SHOCK_UNKNOWN": (
        "This shock is not in the transmission library yet, so we cannot map it.",
        "该冲击尚未收录在传导链知识库中，暂时无法绘制其影响路径。",
    ),
    "NO_THEMES_DECLARED": (
        "No themes have been linked to this shock yet.",
        "尚未为该冲击关联任何主题。",
    ),
    "NO_THEME_EDGES": (
        "We have no links recorded for this theme as of this date.",
        "截至该日期，我们尚未记录该主题的任何关联。",
    ),
    "NO_MEMBERSHIP_YET": (
        "We know this theme, but its company list has not been recorded yet.",
        "我们已知晓该主题，但其公司名单尚未被记录。",
    ),
    "RIGHTS_SUPPRESSED": (
        "The source of this theme's company list cannot be shown here.",
        "该主题公司名单的来源在此处不可展示。",
    ),
    "IDENTITY_UNRESOLVED": (
        "We could not recognise this identifier.",
        "我们无法识别该标识符。",
    ),
    "STORE_UNAVAILABLE": (
        "The theme graph is not available right now.",
        "主题图谱目前不可用。",
    ),
    "NO_ETF_EDGES": (
        "No fund is recorded as tracking this group yet.",
        "尚无基金被记录为跟踪该组别。",
    ),
    "BELIEF_AFTER_ASOF": (
        "A later update to this link exists but is not used for this date.",
        "该关联存在更晚的更新，但未用于此日期。",
    ),
    "IDENTITY_COLLISION": (
        "Two different identifiers resolved to the same security here.",
        "此处两个不同的标识符指向了同一证券。",
    ),
    "UNKNOWN_RIGHTS_FAMILY": (
        "This source is not a reviewed family, so its company list cannot be shown here.",
        "该来源不属于已审核的数据族，其公司名单在此处不可展示。",
    ),
    "BELIEF_TIME_UNKNOWN": (
        "We do not know when this link became known, so it cannot be used for this date.",
        "我们不知道该关联是何时被确认的，因此无法用于此日期。",
    ),
    "EDGE_ID_MISSING": (
        "This link has no identifier, so it cannot be used.",
        "该关联没有标识符，因此无法使用。",
    ),
}


def _unavailable(code: str, *, subject_id: str | None = None,
                  detail: str | None = None) -> dict[str, Any]:
    en, zh = _REASONS[code]
    return {
        "code": code,
        "reason": {"en": en, "zh": zh},
        "subject_id": subject_id,
        "detail": detail,
    }


# --- public dataclasses -----------------------------------------------------------

@dataclasses.dataclass(frozen=True, slots=True)
class ShockSpec:
    """A named TXI chain plus the theme node ids a CALLER declares it touches.

    The shock->theme link is an INPUT, never a derivation: this module does not and
    may never infer which themes a macro shock hits (that is a causal claim; DNR
    no-causal-DAG). ``shock_id`` must be a chain id present in
    knowledge/transmission/*.yaml. ``theme_node_ids`` must satisfy the GMI id
    grammar (engine/theme_graph/identity.py).
    """

    shock_id: str
    theme_node_ids: tuple[str, ...]
    declared_by: str
    note: str | None = None


@dataclasses.dataclass(frozen=True, slots=True)
class Shock:
    shock_id: str
    vocabulary: str
    title: Mapping[str, str | None]
    tier: str | None
    declared_by: str
    note: str | None


@dataclasses.dataclass(frozen=True, slots=True)
class ThemeExposure:
    theme_node_id: str
    theme_plane: str | None
    rights_family: str | None
    name: Mapping[str, str | None]
    state: str
    unavailable: Mapping[str, Any] | None
    companies: tuple[Mapping[str, Any], ...] | None
    company_count: int | None
    distinct_security_count: int | None
    etf_proxies: tuple[Mapping[str, Any], ...] | None
    abstentions: tuple[Mapping[str, Any], ...]


@dataclasses.dataclass(frozen=True, slots=True)
class ExposureMap:
    schema: str
    asof: datetime.date
    shock: Shock
    themes: tuple[ThemeExposure, ...]
    unavailable: Mapping[str, Any] | None
    provenance: Mapping[str, Any]


class StoreView(typing.Protocol):
    """The read-only slice of engine.theme_graph.store this module is allowed to see."""

    def read_edges(self) -> Any: ...

    def read_identity_resolution(self) -> Any: ...

    def read_meta(self) -> Mapping[str, Any]: ...

    def read_nodes(self) -> Any: ...  # theme name_en/name_zh (M3)


class _DefaultStoreView:
    """Production view. Imports engine.theme_graph.store lazily, inside each call."""

    def read_edges(self) -> Any:
        from engine.theme_graph.store import read_edges

        return read_edges(latest_belief=False)

    def read_identity_resolution(self) -> Any:
        from engine.theme_graph.store import read_identity_resolution

        return read_identity_resolution(latest=True)

    def read_meta(self) -> Mapping[str, Any]:
        from engine.theme_graph.store import read_meta

        return read_meta()

    def read_nodes(self) -> Any:
        from engine.theme_graph.store import read_nodes

        return read_nodes(current=True)


def default_store_view() -> StoreView:
    """The production ``StoreView``. See ``_DefaultStoreView`` for the exact bindings."""
    return _DefaultStoreView()


def _default_chain_loader() -> Mapping[str, Mapping[str, Any]]:
    from engine.transmission_chains import load_chains

    out: dict[str, Mapping[str, Any]] = {}
    for chain in load_chains():
        cid = chain.get("chain")
        if isinstance(cid, str):
            out[cid] = chain
    return out


def _default_family_resolver(node_id: object) -> str | None:
    from engine.theme_graph import rights

    return rights.family_for_node_id(node_id)


def _default_assert_allowed(family: str) -> None:
    from engine.theme_graph import rights

    rights.assert_public_emission_allowed(family)


def _is_rights_bearing_plane(node_id: object) -> bool:
    """Vendor planes whose prefix must resolve to a reviewed family, or refuse."""
    return isinstance(node_id, str) and (
        node_id.startswith("basket:") or node_id.startswith("ltheme:")
    )


def _emission_refused(
    node_id: object,
    family: str | None,
    assert_allowed: Callable[[str], None],
) -> dict[str, Any] | None:
    """Typed rights abstention, or None if this node may be emitted.

    A ``basket:`` / ``ltheme:`` id whose prefix is not in the owner's
    ``NODE_PREFIX_FAMILY`` table has no family — that is
    ``UNKNOWN_RIGHTS_FAMILY``, fail closed, never assumed safe. A registered
    family is checked through ``assert_allowed``. Company, canonical-theme and
    ETF ids carry no family by construction and stay ungated unless a resolver
    assigns one.
    """
    if family is None:
        if _is_rights_bearing_plane(node_id):
            return _unavailable("UNKNOWN_RIGHTS_FAMILY", subject_id=str(node_id))
        return None
    try:
        assert_allowed(family)
    except Exception:
        return _unavailable(
            "RIGHTS_SUPPRESSED", subject_id=str(node_id), detail=family,
        )
    return None


# --- as-of parsing -----------------------------------------------------------------

def _parse_asof(asof: datetime.date | str) -> datetime.date:
    if isinstance(asof, datetime.datetime):
        return asof.date()
    if isinstance(asof, datetime.date):
        return asof
    return datetime.date.fromisoformat(str(asof).strip())


# --- edge normalisation + belief collapse (§3.4) -----------------------------------

_EDGE_FIELDS = (
    "edge_id", "type", "src", "dst", "valid_from", "valid_to", "evidence_time",
    "belief_time", "era", "source_class", "date_provenance", "evidence_refs",
    "confidence_basis", "computed_at", "engine_version",
)


def _normalise_edge(row: Mapping[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for field in _EDGE_FIELDS:
        value = row.get(field)
        if field in ("valid_from", "valid_to", "evidence_time", "belief_time"):
            out[field] = _date_str(value)
        elif field == "evidence_refs":
            if _is_null(value):
                out[field] = []
            elif isinstance(value, (list, tuple)):
                out[field] = list(value)
            else:
                out[field] = [value]
        else:
            out[field] = _str_or_none(value)
    return out


def _edge_row_order_key(row: Mapping[str, Any]) -> tuple[str, str, str, str]:
    """Total order for raw edge rows: (edge_id, computed_at, src, dst)."""
    eid = "" if _is_null(row.get("edge_id")) else str(row.get("edge_id"))
    computed = "" if _is_null(row.get("computed_at")) else str(row.get("computed_at"))
    src = "" if _is_null(row.get("src")) else str(row.get("src"))
    dst = "" if _is_null(row.get("dst")) else str(row.get("dst"))
    return (eid, computed, src, dst)


def _collapse_and_filter_edges(
    raw_rows: list[Mapping[str, Any]], asof: datetime.date,
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    """Group raw edge rows by edge_id, collapse to the belief in view at ``asof``,
    then apply the point-in-time filter (§3.4). Returns (in_view_by_edge_id,
    clock_mismatch_abstentions).

    Candidate rows are sorted by ``(edge_id, computed_at, src, dst)`` before any
    grouping or first-wins logic so the BELIEF_AFTER_ASOF attribution set cannot
    depend on input order. Every distinct future ``dst`` for an edge receives
    the abstention — not whichever row happened to arrive first.
    """
    by_id: dict[str, list[Mapping[str, Any]]] = {}
    abstentions: list[dict[str, Any]] = []
    for row in sorted(raw_rows, key=_edge_row_order_key):
        eid = row.get("edge_id")
        if _is_null(eid):
            dst = "" if _is_null(row.get("dst")) else str(row.get("dst"))
            entry = _unavailable("EDGE_ID_MISSING", subject_id=None)
            entry["_dst"] = dst
            abstentions.append(entry)
            continue
        by_id.setdefault(str(eid), []).append(row)

    in_view: dict[str, dict[str, Any]] = {}

    for eid, rows in by_id.items():
        eligible: list[Mapping[str, Any]] = []
        future: list[Mapping[str, Any]] = []
        unknown: list[Mapping[str, Any]] = []
        for row in rows:
            belief = _date(row.get("belief_time"))
            if belief is None:
                # Knowability is untyped: a null belief_time is never eligible
                # at any as-of (fail closed). This is what makes
                # "max belief_time <= asof per edge_id" true by construction.
                unknown.append(row)
            elif belief > asof:
                future.append(row)
            else:
                eligible.append(row)
        if unknown:
            dsts = sorted({
                ("" if _is_null(row.get("dst")) else str(row.get("dst")))
                for row in unknown
            })
            for dst in dsts:
                entry = _unavailable("BELIEF_TIME_UNKNOWN", subject_id=eid)
                entry["_dst"] = dst
                abstentions.append(entry)
        if future:
            dsts = sorted({
                ("" if _is_null(row.get("dst")) else str(row.get("dst")))
                for row in future
            })
            for dst in dsts:
                entry = _unavailable("BELIEF_AFTER_ASOF", subject_id=eid)
                entry["_dst"] = dst
                abstentions.append(entry)
        if not eligible:
            continue

        def _sort_key(row: Mapping[str, Any]) -> tuple[Any, ...]:
            # Total order: same-edge_id rows can share belief_time and computed_at
            # while differing on src/dst; edge_id is the group key so it cannot
            # break that tie. Node ids are identifiers, never a magnitude (G0.11).
            belief = _date(row.get("belief_time")) or datetime.date.min
            computed = "" if _is_null(row.get("computed_at")) else str(row.get("computed_at"))
            src = "" if _is_null(row.get("src")) else str(row.get("src"))
            dst = "" if _is_null(row.get("dst")) else str(row.get("dst"))
            return (belief, computed, src, dst)

        selected = sorted(eligible, key=_sort_key)[-1]

        valid_from = _date(selected.get("valid_from"))
        valid_to = _date(selected.get("valid_to"))
        if valid_from is not None and valid_from > asof:
            continue
        if valid_to is not None and valid_to <= asof:
            continue

        in_view[eid] = _normalise_edge(selected)

    return in_view, sorted(abstentions, key=lambda a: (a["code"], a["subject_id"] or ""))


# --- the walk (§3.3) ----------------------------------------------------------------

@dataclasses.dataclass
class _PathHit:
    company_node_id: str
    path_kind: str
    hops: int
    via_node_id: str | None
    edge_ids: tuple[str, ...]


def _index_by_dst(edges: dict[str, dict[str, Any]], edge_type: str) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {}
    for edge in edges.values():
        if edge["type"] == edge_type:
            out.setdefault(edge["dst"], []).append(edge)
    return out


def _walk_theme(
    theme_id: str,
    *,
    member_of_by_dst: dict[str, list[dict[str, Any]]],
    expresses_by_dst: dict[str, list[dict[str, Any]]],
    family_resolver: Callable[[object], str | None],
    assert_allowed: Callable[[str], None],
) -> tuple[list[_PathHit], list[dict[str, Any]], set[str], set[str]]:
    """Returns (hits, abstentions, baskets_used_on_allowed_bridges, lthemes_used)."""
    hits: list[_PathHit] = []
    abstentions: list[dict[str, Any]] = []
    baskets_used: set[str] = set()
    lthemes_used: set[str] = set()

    # Path A — direct_membership (1 hop).
    for edge in member_of_by_dst.get(theme_id, []):
        src = edge.get("src")
        if _is_company_id(src):
            hits.append(_PathHit(src, "direct_membership", 1, None, (edge["edge_id"],)))

    # Path B — basket_bridge (2 hops).
    for edge in expresses_by_dst.get(theme_id, []):
        basket = edge.get("src")
        if not isinstance(basket, str) or not basket.startswith("basket:"):
            continue
        family = family_resolver(basket)
        refused = _emission_refused(basket, family, assert_allowed)
        if refused is not None:
            abstentions.append(refused)
            continue
        baskets_used.add(basket)
        for member_edge in member_of_by_dst.get(basket, []):
            if _is_company_id(member_edge["src"]):
                hits.append(_PathHit(
                    member_edge["src"], "basket_bridge", 2, basket,
                    (edge["edge_id"], member_edge["edge_id"]),
                ))

    # Path C — local_theme_bridge (2 hops), only for canonical theme:* ids.
    # Rights before grammar: an ltheme: id whose vendor is not a registered
    # rights family is UNKNOWN_RIGHTS_FAMILY, same as the basket plane. The
    # §3.1 grammar skip must not fire first and rewrite that as
    # NO_MEMBERSHIP_YET (a false data fact). A registered vendor whose
    # membership is genuinely unrecorded is the only path that sentence is true.
    if _is_canonical_theme_id(theme_id):
        for edge in expresses_by_dst.get(theme_id, []):
            ltheme = edge.get("src")
            if not isinstance(ltheme, str) or not ltheme.startswith("ltheme:"):
                continue
            family = family_resolver(ltheme)
            refused = _emission_refused(ltheme, family, assert_allowed)
            if refused is not None:
                abstentions.append(refused)
                continue
            if not _is_local_theme_id(ltheme):
                continue
            lthemes_used.add(ltheme)
            for member_edge in member_of_by_dst.get(ltheme, []):
                if _is_company_id(member_edge["src"]):
                    hits.append(_PathHit(
                        member_edge["src"], "local_theme_bridge", 2, ltheme,
                        (edge["edge_id"], member_edge["edge_id"]),
                    ))

    return hits, abstentions, baskets_used, lthemes_used


# --- identity (§3.6) -----------------------------------------------------------------

def _identity_for(node_id: str, identity_rows: dict[str, Mapping[str, Any]]) -> dict[str, Any]:
    row = identity_rows.get(node_id)
    if row is None:
        return {
            "state": "NO_RESOLUTION_ROW", "security_id": None, "listing_key": None,
            "issuer_id": None, "resolution_asof": None, "refusal_reason": None,
            "collision_group": None,
        }
    state = _str_or_none(row.get("resolution_state")) or "NO_RESOLUTION_ROW"
    if state != "RESOLVED":
        return {
            "state": state, "security_id": None, "listing_key": None, "issuer_id": None,
            "resolution_asof": _date_str(row.get("resolution_asof")),
            "refusal_reason": _str_or_none(row.get("refusal_reason")),
            "collision_group": None,
        }
    return {
        "state": state,
        "security_id": _str_or_none(row.get("security_id")),
        "listing_key": _str_or_none(row.get("listing_key")),
        "issuer_id": _str_or_none(row.get("issuer_id")),
        "resolution_asof": _date_str(row.get("resolution_asof")),
        "refusal_reason": _str_or_none(row.get("refusal_reason")),
        "collision_group": None,
    }


# --- one theme's full row -------------------------------------------------------------

def _compose_theme(
    theme_id: str,
    *,
    edges_by_id: dict[str, dict[str, Any]],
    member_of_by_dst: dict[str, list[dict[str, Any]]],
    expresses_by_dst: dict[str, list[dict[str, Any]]],
    tracks_by_dst: dict[str, list[dict[str, Any]]],
    identity_rows: dict[str, Mapping[str, Any]],
    family_resolver: Callable[[object], str | None],
    assert_allowed: Callable[[str], None],
    clock_abstentions: list[dict[str, Any]],
    node_names: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:

    def _with_clock(entry: dict[str, Any], relevant: set[str]) -> dict[str, Any]:
        # Attach BELIEF_AFTER_ASOF (and any other clock) abstentions whose excluded
        # edge terminated at this theme OR at a bridge node (basket / local theme)
        # this theme actually walked through — so a dropped bridge edge is never a
        # silent discard (B2): the surface can always say why a path is missing.
        own = [
            {k: v for k, v in a.items() if k != "_dst"}
            for a in clock_abstentions if a.get("_dst") in relevant
        ]
        if own:
            entry["abstentions"] = sorted(
                list(entry["abstentions"]) + own,
                key=lambda a: (a["code"], a["subject_id"] or ""),
            )
        return entry
    if not _is_known_theme_grammar(theme_id):
        return {
            "theme_node_id": theme_id, "theme_plane": None, "rights_family": None,
            "name": {"en": None, "zh": None}, "state": "IDENTITY_UNRESOLVED",
            "unavailable": _unavailable("IDENTITY_UNRESOLVED", subject_id=theme_id),
            "companies": None, "company_count": None, "distinct_security_count": None,
            "etf_proxies": None, "abstentions": [],
        }

    theme_plane = "local_theme" if _is_local_theme_id(theme_id) else "canonical_theme"
    theme_family = family_resolver(theme_id)

    theme_node_row = node_names.get(theme_id)
    theme_name = {
        "en": _str_or_none(theme_node_row.get("name_en")) if theme_node_row else None,
        "zh": _str_or_none(theme_node_row.get("name_zh")) if theme_node_row else None,
    }
    base = {
        "theme_node_id": theme_id, "theme_plane": theme_plane,
        "rights_family": theme_family, "name": theme_name,
    }

    # Clock abstentions are omitted on a rights-refused theme so a later-belief
    # edge cannot leak through the unavailable/abstention lists of a family we
    # may not show. Sibling OK / NO_* returns call _with_clock; this one does not.
    theme_refused = _emission_refused(theme_id, theme_family, assert_allowed)
    if theme_refused is not None:
        return {
            **base, "state": "RIGHTS_SUPPRESSED",
            "unavailable": theme_refused,
            "companies": None, "company_count": None, "distinct_security_count": None,
            "etf_proxies": None, "abstentions": [],
        }

    has_any_edge = bool(member_of_by_dst.get(theme_id)) or bool(expresses_by_dst.get(theme_id)) or any(
        e["src"] == theme_id or e["dst"] == theme_id for e in edges_by_id.values()
    )
    if not has_any_edge:
        return _with_clock({
            **base, "state": "NO_THEME_EDGES",
            "unavailable": _unavailable("NO_THEME_EDGES", subject_id=theme_id),
            "companies": None, "company_count": None, "distinct_security_count": None,
            "etf_proxies": None, "abstentions": [],
        }, {theme_id})

    hits, path_abstentions, baskets_used, lthemes_used = _walk_theme(
        theme_id, member_of_by_dst=member_of_by_dst, expresses_by_dst=expresses_by_dst,
        family_resolver=family_resolver, assert_allowed=assert_allowed,
    )
    bridge_dsts = {theme_id} | baskets_used | lthemes_used

    if not hits:
        abstentions = sorted(path_abstentions, key=lambda a: (a["code"], a["subject_id"] or ""))
        # A rights-refused bridge is not "membership not recorded yet": that sentence
        # asserts a false data fact. When every walkable bridge was refused and no
        # allowed path produced a company, the theme is rights-suppressed.
        rights_blocked_every_bridge = (
            any(a["code"] in ("RIGHTS_SUPPRESSED", "UNKNOWN_RIGHTS_FAMILY")
                for a in path_abstentions)
            and not baskets_used
            and not lthemes_used
        )
        if rights_blocked_every_bridge:
            unknown = any(a["code"] == "UNKNOWN_RIGHTS_FAMILY" for a in path_abstentions)
            unavail_code = "UNKNOWN_RIGHTS_FAMILY" if unknown else "RIGHTS_SUPPRESSED"
            return _with_clock({
                **base, "state": "RIGHTS_SUPPRESSED",
                "unavailable": _unavailable(unavail_code, subject_id=theme_id),
                "companies": None, "company_count": None, "distinct_security_count": None,
                "etf_proxies": None, "abstentions": abstentions,
            }, {theme_id})
        return _with_clock({
            **base, "state": "NO_MEMBERSHIP_YET",
            "unavailable": _unavailable("NO_MEMBERSHIP_YET", subject_id=theme_id),
            "companies": None, "company_count": None, "distinct_security_count": None,
            "etf_proxies": None, "abstentions": abstentions,
        }, bridge_dsts)

    # Group hits by company -> paths (double-count law: one row per company, N paths).
    by_company: dict[str, list[_PathHit]] = {}
    for hit in hits:
        by_company.setdefault(hit.company_node_id, []).append(hit)

    company_rows: list[dict[str, Any]] = []
    company_rights_abstentions: list[dict[str, Any]] = []
    for company_id in sorted(by_company):
        # M2: the rights gate is node-id-based (owner-side, engine.theme_graph.rights)
        # and applies to every emitted node id. A basket:/ltheme: prefix that
        # family_for_node_id does not resolve is UNKNOWN_RIGHTS_FAMILY — fail
        # closed, never assumed safe because today's table maps no such prefix.
        # Company ids carry no family by construction and stay ungated unless a
        # resolver assigns one; an assigned family is then checked like any other.
        company_family = family_resolver(company_id)
        company_refused = _emission_refused(company_id, company_family, assert_allowed)
        if company_refused is not None:
            company_rights_abstentions.append(company_refused)
            continue
        company_hits = by_company[company_id]
        paths: list[dict[str, Any]] = []
        for hit in company_hits:
            edge_objs = sorted(
                (edges_by_id[eid] for eid in hit.edge_ids if eid in edges_by_id),
                key=lambda e: e["edge_id"],
            )
            paths.append({
                "path_kind": hit.path_kind, "hops": hit.hops,
                "via_node_id": hit.via_node_id, "edges": edge_objs,
            })
        paths.sort(key=lambda p: (p["edges"][0]["edge_id"] if p["edges"] else ""))
        identity = _identity_for(company_id, identity_rows)
        company_rows.append({
            "company_node_id": company_id,
            "market_scope": _market_scope_of_company(company_id),
            "rights_family": company_family,
            "identity": identity,
            "paths": paths,
        })

    if not company_rows and company_rights_abstentions:
        # Hits existed but every company was rights-blocked. An empty companies
        # list under state OK reads as "no exposure" — acceptance 7 forbids that.
        all_abstentions = sorted(
            path_abstentions + company_rights_abstentions,
            key=lambda a: (a["code"], a["subject_id"] or ""),
        )
        return _with_clock({
            **base, "state": "RIGHTS_SUPPRESSED",
            "unavailable": _unavailable("RIGHTS_SUPPRESSED", subject_id=theme_id),
            "companies": None, "company_count": None, "distinct_security_count": None,
            "etf_proxies": None, "abstentions": all_abstentions,
        }, bridge_dsts)

    # Identity collision (§3.6).
    by_security: dict[str, list[str]] = {}
    for row in company_rows:
        sec = row["identity"]["security_id"]
        if sec is not None:
            by_security.setdefault(sec, []).append(row["company_node_id"])
    collision_abstentions: list[dict[str, Any]] = []
    for sec, members in by_security.items():
        if len(members) > 1:
            for row in company_rows:
                if row["identity"]["security_id"] == sec:
                    row["identity"]["collision_group"] = sec
            collision_abstentions.append(
                _unavailable("IDENTITY_COLLISION", subject_id=sec, detail=",".join(sorted(members)))
            )

    company_count = len(company_rows)
    distinct_security_count = len({r["identity"]["security_id"] for r in company_rows
                                    if r["identity"]["security_id"] is not None})

    # etf_proxies (§4.4b).
    etf_proxies: list[dict[str, Any]] | None = None
    etf_abstentions: list[dict[str, Any]] = []
    if baskets_used:
        found: list[dict[str, Any]] = []
        any_tracks = False
        for basket in sorted(baskets_used):
            for tedge in tracks_by_dst.get(basket, []):
                etf_id = tedge.get("src")
                if not isinstance(etf_id, str):
                    continue
                any_tracks = True
                etf_family = family_resolver(etf_id)
                etf_refused = _emission_refused(etf_id, etf_family, assert_allowed)
                if etf_refused is not None:
                    etf_abstentions.append(etf_refused)
                    continue
                found.append({
                    "etf_node_id": etf_id, "via_basket_node_id": basket,
                    "rights_family": etf_family, "edges": [tedge],
                })
        if not any_tracks:
            etf_abstentions.append(_unavailable("NO_ETF_EDGES", subject_id=theme_id))
        else:
            found.sort(key=lambda p: p["etf_node_id"])
            etf_proxies = found if found else None
    else:
        # M5: a theme reached only via direct_membership / local_theme_bridge never
        # walks a basket, so etf_proxies would otherwise be a silent, unexplained
        # None here — indistinguishable from "we checked, there are none". Print the
        # typed reason instead.
        etf_abstentions.append(
            _unavailable("NO_ETF_EDGES", subject_id=theme_id, detail="no_basket_path")
        )

    all_abstentions = sorted(
        path_abstentions + collision_abstentions + etf_abstentions + company_rights_abstentions,
        key=lambda a: (a["code"], a["subject_id"] or ""),
    )

    return _with_clock({
        **base, "state": "OK", "unavailable": None,
        "companies": company_rows, "company_count": company_count,
        "distinct_security_count": distinct_security_count,
        "etf_proxies": etf_proxies, "abstentions": all_abstentions,
    }, bridge_dsts)


# --- top-level composition -------------------------------------------------------------

def compose_exposure_map(
    store: StoreView,
    shock_spec: ShockSpec,
    *,
    asof: datetime.date | str,
    chain_loader: Callable[[], Mapping[str, Mapping[str, Any]]] | None = None,
    family_resolver: Callable[[object], str | None] | None = None,
    assert_allowed: Callable[[str], None] | None = None,
) -> ExposureMap:
    """Pure projection. No clock, no network, no LLM, no write. Never raises for a
    data reason — an absent store, an unknown shock, a rights refusal and an
    unresolved id are all TYPED NULLS in the returned value."""
    asof_date = _parse_asof(asof)
    chain_loader = chain_loader or _default_chain_loader
    family_resolver = family_resolver or _default_family_resolver
    assert_allowed = assert_allowed or _default_assert_allowed

    try:
        chains = chain_loader()
    except Exception:
        chains = {}

    chain = chains.get(shock_spec.shock_id)
    provenance = {
        "edge_reader": _EDGE_READER,
        "identity_reader": _IDENTITY_READER,
        "chain_reader": _CHAIN_READER,
        "store_meta": None,
        "engine_version": ENGINE_VERSION,
        "belief_collapse": _BELIEF_COLLAPSE,
    }

    if chain is None:
        shock = Shock(
            shock_id=shock_spec.shock_id,
            vocabulary="knowledge/transmission/*.yaml (TXI chain library)",
            title={"en": None, "zh": None}, tier=None,
            declared_by=shock_spec.declared_by, note=shock_spec.note,
        )
        return ExposureMap(
            schema=SCHEMA_ID, asof=asof_date, shock=shock, themes=(),
            unavailable=_unavailable("SHOCK_UNKNOWN", subject_id=shock_spec.shock_id),
            provenance=provenance,
        )

    title = chain.get("title") if isinstance(chain.get("title"), Mapping) else {}
    shock = Shock(
        shock_id=shock_spec.shock_id,
        vocabulary="knowledge/transmission/*.yaml (TXI chain library)",
        title={"en": title.get("en"), "zh": title.get("zh")},
        tier=chain.get("tier"),
        declared_by=shock_spec.declared_by, note=shock_spec.note,
    )

    if not shock_spec.theme_node_ids:
        return ExposureMap(
            schema=SCHEMA_ID, asof=asof_date, shock=shock, themes=(),
            unavailable=_unavailable("NO_THEMES_DECLARED"),
            provenance=provenance,
        )

    try:
        raw_edges = _records(store.read_edges())
        raw_identity = _records(store.read_identity_resolution())
        try:
            meta = store.read_meta()
        except Exception:
            meta = None
        provenance = {**provenance, "store_meta": meta}
    except Exception:
        return ExposureMap(
            schema=SCHEMA_ID, asof=asof_date, shock=shock, themes=(),
            unavailable=_unavailable("STORE_UNAVAILABLE"),
            provenance=provenance,
        )

    edges_by_id, clock_abstentions = _collapse_and_filter_edges(raw_edges, asof_date)
    member_of_by_dst = _index_by_dst(edges_by_id, "MEMBER_OF")
    expresses_by_dst = _index_by_dst(edges_by_id, "EXPRESSES")
    tracks_by_dst = _index_by_dst(edges_by_id, "TRACKS")

    try:
        raw_nodes = _records(store.read_nodes())
    except Exception:
        raw_nodes = []
    node_names: dict[str, Mapping[str, Any]] = {}
    for row in raw_nodes:
        node_id = row.get("node_id")
        if node_id is not None:
            node_names[str(node_id)] = row

    identity_rows: dict[str, Mapping[str, Any]] = {}
    for row in raw_identity:
        node_id = row.get("node_id")
        if node_id is not None:
            identity_rows[str(node_id)] = row

    theme_rows: list[dict[str, Any]] = []
    for theme_id in sorted(set(shock_spec.theme_node_ids)):
        row = _compose_theme(
            theme_id, edges_by_id=edges_by_id, member_of_by_dst=member_of_by_dst,
            expresses_by_dst=expresses_by_dst, tracks_by_dst=tracks_by_dst,
            identity_rows=identity_rows, family_resolver=family_resolver,
            assert_allowed=assert_allowed, clock_abstentions=clock_abstentions,
            node_names=node_names,
        )
        theme_rows.append(row)

    themes = tuple(
        ThemeExposure(
            theme_node_id=r["theme_node_id"], theme_plane=r["theme_plane"],
            rights_family=r["rights_family"], name=r["name"], state=r["state"],
            unavailable=r["unavailable"], companies=r["companies"],
            company_count=r["company_count"],
            distinct_security_count=r["distinct_security_count"],
            etf_proxies=r["etf_proxies"], abstentions=tuple(r["abstentions"]),
        )
        for r in theme_rows
    )

    return ExposureMap(
        schema=SCHEMA_ID, asof=asof_date, shock=shock, themes=themes,
        unavailable=None, provenance=provenance,
    )


def _shock_json(shock: Shock) -> dict[str, Any]:
    return {
        "shock_id": shock.shock_id, "vocabulary": shock.vocabulary,
        "title": dict(shock.title), "tier": shock.tier,
        "declared_by": shock.declared_by, "note": shock.note,
    }


def _theme_json(theme: ThemeExposure) -> dict[str, Any]:
    return {
        "theme_node_id": theme.theme_node_id, "theme_plane": theme.theme_plane,
        "rights_family": theme.rights_family, "name": dict(theme.name),
        "state": theme.state, "unavailable": theme.unavailable,
        "companies": list(theme.companies) if theme.companies is not None else None,
        "company_count": theme.company_count,
        "distinct_security_count": theme.distinct_security_count,
        "etf_proxies": list(theme.etf_proxies) if theme.etf_proxies is not None else None,
        "abstentions": list(theme.abstentions),
    }


def to_json(exposure_map: ExposureMap) -> dict[str, Any]:
    """The exposure_map.v1 payload as plain JSON-serializable types. Pure and total."""
    return {
        "schema": exposure_map.schema,
        "asof": exposure_map.asof.isoformat(),
        "authority_ceiling": AUTHORITY_CEILING,
        "display_only": True,
        "shock": _shock_json(exposure_map.shock),
        "themes": [_theme_json(t) for t in exposure_map.themes],
        "unavailable": exposure_map.unavailable,
        "provenance": dict(exposure_map.provenance),
    }
