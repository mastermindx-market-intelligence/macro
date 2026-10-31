"""Micro-theme relative-strength PROXY display reader (display tier only).

``sub_theme`` and ``micro_theme`` nodes carry no EXPRESSES/MEMBER_OF edges by law
(SPEC §1 ``NEW_TIER_IN_EXPRESSES_MAP``), so any relative-strength VIEW of a
micro theme can only be a PROXY read through its ancestor theme's expressing
baskets/ETFs. This module names that proxy path — the nearest active
``theme``-tier ancestors and the open EXPRESSES instruments that point at them.
It computes NO strength number of its own: no weights, shares, scores, ranks or
exposure percentages exist here, and the relative-strength owners stay the
owners of strength itself (Gate #8). Counts are the only numbers emitted.

Gate #2: any id starting ``ltheme:`` or containing ``finviz_themes`` /
``ths_concepts`` is vendor-internal. It is never a graph subject here and is
filtered out of every emitted list.

Gate #8: a pure reader — no file writes, no caching across calls, no network,
no LLM, no wall clock. Inputs are keyword-injected frames; when omitted, the
incumbent ``engine/theme_graph/store.py`` readers are called at most once each.

Failure semantics: every refusal is a typed null on the envelope, never a zero
and never a guess. ``not_applicable`` covers a subject this reader does not
cover (absent tier, wrong kind, retired/merged, vendor-internal);
``unknown``/``value_missing`` covers a subject absent from the node frame and
an orphan with no active ``theme``-tier ancestor. ``reason_code`` is null
exactly when status is ``available``; ``value`` is null exactly when it is not.

No emitted dict key at any depth may contain ``weight``, ``share``, ``score``,
``rank`` or ``exposure_pct`` (``cell.FORBIDDEN_VALUE_KEY_WORDS``); the test
suite enforces that walk over every output.
"""
from __future__ import annotations

import pandas as pd

from engine.theme_graph import rights, store

SCHEMA_VERSION = "gmi.micro_rs_proxy_display.v1"

#: Every envelope carries the proxy label — an available reading is a proxy
#: through ancestor membership, never a micro-level membership fact.
LABELS: tuple[str, ...] = ("proxy_not_micro_membership",)

QUALITY = "display_only"

SOURCE = {
    "owner": "engine/theme_graph/store.py",
    "artifact": "data/theme_graph/nodes.parquet+edges.parquet",
    "field": "PARENT_OF+EXPRESSES",
}

#: The only subject tiers this reader covers (SPEC §1 tier ladder).
SUBJECT_TIERS = ("sub_theme", "micro_theme")

#: Gate #2 tokens beyond the ``ltheme:`` prefix.
_INTERNAL_ONLY_TOKENS = ("finviz_themes", "ths_concepts")


def _is_internal_only(node_id: str) -> bool:
    """True for a Gate #2 vendor-internal id (never a subject or an output)."""
    return node_id.startswith("ltheme:") or any(
        token in node_id for token in _INTERNAL_ONLY_TOKENS
    )


def _text(value: object) -> str | None:
    """A scalar as text, with pandas nulls (NaN/NaT/NA) read as absent."""
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        return None
    return str(value)


def _is_open(valid_to: object) -> bool:
    """True when an edge interval is still open (``valid_to`` null/blank)."""
    if valid_to is None:
        return True
    try:
        if pd.isna(valid_to):
            return True
    except (TypeError, ValueError):
        return False
    return isinstance(valid_to, str) and valid_to.strip() == ""


def _is_retired(status: str | None) -> bool:
    return (status or "") in store.RETIRED_LIKE_STATUSES


def _load(nodes: object, edges: object) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Resolve injected frames, calling each incumbent store reader at most once."""
    if nodes is None:
        nodes = store.read_nodes(current=True)
    if edges is None:
        edges = store.read_edges()
    return nodes, edges


def _node_index(nodes: pd.DataFrame) -> dict[str, dict[str, str | None]]:
    """``node_id → {kind, tier, status}`` for the current view."""
    index: dict[str, dict[str, str | None]] = {}
    if nodes is None or len(nodes) == 0:
        return index
    for row in nodes.to_dict("records"):
        node_id = _text(row.get("node_id"))
        if not node_id:
            continue
        index[node_id] = {
            "kind": _text(row.get("kind")),
            "tier": _text(row.get("tier")),
            "status": _text(row.get("status")),
        }
    return index


def _parent_map(edges: pd.DataFrame) -> dict[str, set[str]]:
    """``child → {parents}`` over open PARENT_OF rows (parent=src, child=dst)."""
    mapping: dict[str, set[str]] = {}
    if edges is None or len(edges) == 0:
        return mapping
    for row in edges.to_dict("records"):
        if _text(row.get("type")) != "PARENT_OF" or not _is_open(row.get("valid_to")):
            continue
        parent = _text(row.get("src"))
        child = _text(row.get("dst"))
        if parent and child:
            mapping.setdefault(child, set()).add(parent)
    return mapping


def _instrument_emission_ok(src_id: str) -> bool:
    """Gate #2 for proxy instruments, decided by the rights registry.

    The id-token check above misses vendor-derived instruments whose id does
    not spell the vendor (``basket:baskets_china_ths:*`` is ``ths_concepts``).
    The source family comes from ``rights.family_for_node_id`` and must permit
    a public emission; an unmapped family, or a registry that cannot answer,
    refuses rather than defaulting open.
    """
    family = rights.family_for_node_id(src_id)
    if family is None:
        return False
    try:
        return rights.emission_allowed(family)
    except Exception:  # unknown family / unreadable registry: fail closed
        return False


def _expresses_pairs(edges: pd.DataFrame, index: dict) -> list[tuple[str, str]]:
    """Sorted ``(theme_id, src_id)`` for every open EXPRESSES edge whose source
    is an active node. Gate #2 sources are dropped here and never re-enter."""
    pairs: set[tuple[str, str]] = set()
    if edges is None or len(edges) == 0:
        return []
    for row in edges.to_dict("records"):
        if _text(row.get("type")) != "EXPRESSES" or not _is_open(row.get("valid_to")):
            continue
        src_id = _text(row.get("src"))
        theme_id = _text(row.get("dst"))
        if not src_id or not theme_id or _is_internal_only(src_id):
            continue
        if not _instrument_emission_ok(src_id):
            continue
        node = index.get(src_id)
        if node is None or _is_retired(node["status"]):
            continue
        pairs.add((theme_id, src_id))
    return sorted(pairs)


def _nearest_theme_ancestors(
    subject_id: str, tier: str | None, parent_map: dict[str, set[str]],
    index: dict[str, dict],
) -> tuple[set[str], set[str]]:
    """``(direct, via_sub)`` — the nearest active ``theme``-tier ancestors.

    ``direct`` are active theme-tier parents of the subject itself; ``via_sub``
    (micro_theme subjects only) are theme-tier ancestors first reached through
    an active ``sub_theme`` parent. A retired/merged or vendor-internal
    ancestor is neither emitted nor traversed; the walk terminates at every
    ``theme``-tier node (nearest only — a theme's own macro_category parents
    are never proxies) and is cycle-safe.
    """
    direct: set[str] = set()
    via_sub: set[str] = set()

    def _eligible(node_id: str) -> dict | None:
        node = index.get(node_id)
        if node is None or node["kind"] != "theme" or _is_internal_only(node_id):
            return None
        if _is_retired(node["status"]):
            return None
        return node

    sub_parents: list[str] = []
    for parent in parent_map.get(subject_id, ()):
        node = _eligible(parent)
        if node is None:
            continue
        if node["tier"] == "theme":
            direct.add(parent)
        elif tier == "micro_theme" and node["tier"] == "sub_theme":
            sub_parents.append(parent)

    seen: set[str] = set(sub_parents)
    frontier = list(sub_parents)
    while frontier:
        child = frontier.pop(0)
        for parent in parent_map.get(child, ()):
            node = _eligible(parent)
            if node is None:
                continue
            if node["tier"] == "theme":
                via_sub.add(parent)
            elif node["tier"] == "sub_theme" and parent not in seen:
                seen.add(parent)
                frontier.append(parent)
    return direct, via_sub


def _path_kind(tier: str | None, direct: set[str], via_sub: set[str]) -> str:
    """How the proxy themes were reached. ``none`` is part of the declared
    vocabulary but is unreachable on an ``available`` envelope: a subject with
    no active theme-tier ancestor is ``unknown``/``value_missing`` instead."""
    if tier == "sub_theme":
        return "direct_theme" if direct else "none"
    if direct and via_sub:
        return "both"
    if direct:
        return "direct_theme"
    if via_sub:
        return "via_sub_theme"
    return "none"


def _envelope(
    subject_id: object, status: str, reason_code: str | None = None, value: object = None
) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "subject_id": subject_id,
        "status": status,
        "reason_code": reason_code,
        "value": value,
        "labels": list(LABELS),
        "quality": QUALITY,
        "source": dict(SOURCE),
    }


def _read(subject_id: object, index: dict, parent_map: dict, pairs: list) -> dict:
    if not isinstance(subject_id, str) or not subject_id.strip():
        return _envelope(subject_id, "not_applicable", "not_applicable")
    if _is_internal_only(subject_id):
        # Gate #2: named only as the requested id, never read as a graph subject.
        return _envelope(subject_id, "not_applicable", "not_applicable")
    node = index.get(subject_id)
    if node is None:
        return _envelope(subject_id, "unknown", "value_missing")
    if node["kind"] != "theme" or node["tier"] not in SUBJECT_TIERS:
        return _envelope(subject_id, "not_applicable", "not_applicable")
    if _is_retired(node["status"]):
        reason = "superseded_entity" if node["status"] == "merged" else "retired_entity"
        return _envelope(subject_id, "not_applicable", reason)

    direct, via_sub = _nearest_theme_ancestors(
        subject_id, node["tier"], parent_map, index
    )
    proxy_themes = sorted(direct | via_sub)
    if not proxy_themes:
        # An orphan has no proxy; never guess one.
        return _envelope(subject_id, "unknown", "value_missing")

    wanted = set(proxy_themes)
    instruments = [
        {"theme_id": theme_id, "src_id": src_id}
        for theme_id, src_id in pairs
        if theme_id in wanted
    ]
    return _envelope(
        subject_id,
        "available",
        None,
        {
            "tier": node["tier"],
            "proxy_themes": proxy_themes,
            "proxy_instruments": instruments,
            "proxy_instrument_count": len(instruments),
            "path_kind": _path_kind(node["tier"], direct, via_sub),
        },
    )


def read_micro_rs_proxy(node_id: str, *, nodes=None, edges=None) -> dict:
    """The relative-strength PROXY path for one ``sub_theme``/``micro_theme``.

    A display-tier read only: the nearest active ``theme``-tier ancestors and
    the open EXPRESSES instruments pointing at them. No strength number is
    computed and no edge economics column is read. See the module docstring
    for the Gate #2/#8 statements and the failure semantics.
    """
    nodes, edges = _load(nodes, edges)
    index = _node_index(nodes)
    return _read(
        node_id, index, _parent_map(edges), _expresses_pairs(edges, index)
    )


def micro_rs_proxy_table(*, nodes=None, edges=None) -> list[dict]:
    """One envelope per active ``sub_theme``/``micro_theme`` node, by subject id.

    Store inputs, when not injected, are loaded at most once for the whole
    table. Retired/merged subjects are excluded — their lifecycle is a typed
    per-subject refusal through :func:`read_micro_rs_proxy`, never a silent
    table row.
    """
    nodes, edges = _load(nodes, edges)
    index = _node_index(nodes)
    parent_map = _parent_map(edges)
    pairs = _expresses_pairs(edges, index)
    subjects = sorted(
        node_id
        for node_id, node in index.items()
        if node["kind"] == "theme"
        and node["tier"] in SUBJECT_TIERS
        and not _is_retired(node["status"])
        and not _is_internal_only(node_id)
    )
    return [_read(subject_id, index, parent_map, pairs) for subject_id in subjects]
