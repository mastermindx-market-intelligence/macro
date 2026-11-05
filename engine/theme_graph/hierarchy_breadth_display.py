"""Hierarchy breadth display reader — how wide is one theme node, per Taxonomy V2.

Answers, for a single ``kind="theme"`` node, the DISPLAY-tier breadth questions of
the GMI taxonomy (WS:GMI-THEME-GRAPH, DEC:GMI-TAXONOMY-UPGRADE-V2): its tier, its
active ``PARENT_OF`` parents, its direct active children grouped by child tier
(only the child tiers that are legal for the subject's tier under SPEC §1
adjacency), the count of DISTINCT active ``micro_theme`` descendants, and whether
a ``sub_theme`` layer exists under a theme. Counts and id lists only — no
weights, shares, scores, ranks or exposure percentages anywhere in the value,
and no ordering by any magnitude.

Gate #2: vendor local themes (``ltheme:*``) and the ``finviz_themes`` /
``ths_concepts`` suites are INTERNAL-ONLY. Such ids are never an input subject
and never an output value: they are pruned from the edge set before any walk and
from every emitted parent/child/descendant list, and a subject that names one
gets a typed ``not_applicable`` envelope. Gate #8: a pure reader over
``engine/theme_graph/store.py`` (or the caller-injected equivalent). No writes,
no cache across calls, no network, no LLM, no wall clock, no second store. The
store is touched only when an injected input is ``None``, and
:func:`hierarchy_breadth_table` loads the store at most once per call.

Failure semantics — every return is a uniform envelope; a missing answer is a
typed null, never a zero and never a guess:

- subject absent from the node frame      -> ``unknown`` / ``value_missing``
- subject is not a ``kind="theme"`` node  -> ``not_applicable`` / ``not_applicable``
- subject retired / merged                -> ``not_applicable`` / ``retired_entity``
                                            | ``superseded_entity``
- subject carries a tier outside the four
  §1 tiers (out-of-contract data)         -> ``not_applicable`` / ``not_applicable``
- otherwise                               -> ``available`` / null reason + value

Retired/merged nodes (``store.RETIRED_LIKE_STATUSES``) are excluded from every
emitted parent/child list and never counted as micro descendants. Reachability
for the descendant count is a property of the OPEN ``PARENT_OF`` edge set — an
active micro hanging under a retired intermediate is still reachable and still
counted, while the retired intermediate itself is neither listed nor counted.
"""
from __future__ import annotations

import pandas as pd

from engine.classification_axes.cell import FORBIDDEN_VALUE_KEY_WORDS
from engine.theme_graph import store

#: Bumped only when the envelope contract changes.
SCHEMA_VERSION = "gmi.hierarchy_breadth_display.v1"

#: Every envelope carries the house-curated label: the hierarchy is curated
#: vocabulary, never a vendor-derived reading.
LABELS = ["house_curated"]

QUALITY = "display_only"

#: The one producer of the data this reader reads. Field is ``PARENT_OF``: every
#: emitted fact derives from ``PARENT_OF`` edges plus the node rows at their ends.
SOURCE = {
    "owner": "engine/theme_graph/store.py",
    "artifact": "data/theme_graph/nodes.parquet+edges.parquet",
    "field": "PARENT_OF",
}

#: The four §1 tiers of a ``kind="theme"`` node, in taxonomy order.
TIERS = ("macro_category", "theme", "sub_theme", "micro_theme")

#: SPEC §1 ``PARENT_OF`` adjacency: subject tier -> its legal child tiers.
#: (macro_category,theme), (theme,sub_theme), (theme,micro_theme),
#: (sub_theme,micro_theme); a micro_theme is a leaf. Every other pair is refused
#: by the writers; this reader simply never groups under a non-legal tier key.
LEGAL_CHILD_TIERS = {
    "macro_category": ("theme",),
    "theme": ("sub_theme", "micro_theme"),
    "sub_theme": ("micro_theme",),
    "micro_theme": (),
}


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------

def _is_internal_only_id(node_id: object) -> bool:
    """Gate #2: vendor local themes and the two vendor suites are never in play."""
    if not isinstance(node_id, str):
        return False
    return (node_id.startswith("ltheme:")
            or "finviz_themes" in node_id
            or "ths_concepts" in node_id)


def _edge_open(valid_to: object) -> bool:
    """True when the edge interval is open: ``valid_to`` null/NaN/empty."""
    if valid_to is None:
        return True
    if isinstance(valid_to, str):
        return not valid_to.strip()
    try:
        return bool(pd.isna(valid_to))
    except (TypeError, ValueError):
        return False


def _is_active(row: dict | None) -> bool:
    return row is not None and row.get("status") not in store.RETIRED_LIKE_STATUSES


def _node_index(nodes: pd.DataFrame) -> dict[str, dict]:
    """node_id -> row (keep-first; the store itself is keep-first on node_id)."""
    index: dict[str, dict] = {}
    for row in nodes.to_dict("records"):
        node_id = row.get("node_id")
        if isinstance(node_id, str) and node_id and node_id not in index:
            index[node_id] = row
    return index


def _parent_child_maps(edges: pd.DataFrame) -> tuple[dict[str, list[str]],
                                                    dict[str, list[str]]]:
    """Open ``PARENT_OF`` edges as parent->children / child->parents id maps.

    ``PARENT_OF`` is parent(src) -> child(dst). Gate #2 ids are pruned here, at
    the edge set, so no walk downstream can ever reach one. Exposure columns on
    the edge frame are never read.
    """
    parents: dict[str, set[str]] = {}
    children: dict[str, set[str]] = {}
    if len(edges):
        for row in edges.to_dict("records"):
            if row.get("type") != "PARENT_OF" or not _edge_open(row.get("valid_to")):
                continue
            src, dst = row.get("src"), row.get("dst")
            if not isinstance(src, str) or not isinstance(dst, str):
                continue
            if _is_internal_only_id(src) or _is_internal_only_id(dst):
                continue
            children.setdefault(src, set()).add(dst)
            parents.setdefault(dst, set()).add(src)
    return ({key: sorted(values) for key, values in parents.items()},
            {key: sorted(values) for key, values in children.items()})


def _descendant_micro_theme_count(subject_id: str, index: dict[str, dict],
                                  children_map: dict[str, list[str]]) -> int:
    """Distinct ACTIVE micro_theme ids reachable via open ``PARENT_OF`` edges.

    Cycle-safe visited set seeded with the subject. Only active micro_theme
    endpoints are counted; the walk itself follows open edges wherever they lead.
    """
    seen = {subject_id}
    stack = [subject_id]
    micros: set[str] = set()
    while stack:
        for child_id in children_map.get(stack.pop(), ()):
            if child_id in seen:
                continue
            seen.add(child_id)
            child = index.get(child_id)
            if child is None:
                continue
            if (child.get("kind") == "theme"
                    and child.get("tier") == "micro_theme"
                    and _is_active(child)):
                micros.add(child_id)
            stack.append(child_id)
    return len(micros)


def _envelope(subject_id: str, status: str, reason_code: str | None,
              value: dict | None = None) -> dict:
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


def _breadth(subject_id: str, index: dict[str, dict],
             parents_map: dict[str, list[str]],
             children_map: dict[str, list[str]]) -> dict:
    """One breadth envelope for ``subject_id`` over pre-built lookup maps."""
    row = index.get(subject_id)
    if row is None:
        return _envelope(subject_id, "unknown", "value_missing")
    if row.get("kind") != "theme":
        return _envelope(subject_id, "not_applicable", "not_applicable")
    status = row.get("status")
    if status in store.RETIRED_LIKE_STATUSES:
        reason = "superseded_entity" if status == "merged" else "retired_entity"
        return _envelope(subject_id, "not_applicable", reason)
    tier = row.get("tier")
    if tier not in TIERS:
        # Out-of-contract data: the four §1 tiers are the whole vocabulary.
        return _envelope(subject_id, "not_applicable", "not_applicable")

    legal = LEGAL_CHILD_TIERS[tier]
    children: dict[str, list[str]] = {
        child_tier: [] for child_tier in TIERS if child_tier in legal
    }
    for child_id in children_map.get(subject_id, ()):
        child = index.get(child_id)
        if not _is_active(child) or child.get("kind") != "theme":
            continue
        child_tier = child.get("tier")
        if child_tier in children:
            children[child_tier].append(child_id)
    children = {child_tier: sorted(ids) for child_tier, ids in children.items()}

    parent_ids = sorted(
        parent_id for parent_id in parents_map.get(subject_id, ())
        if _is_active(index.get(parent_id))
    )

    value = {
        "tier": tier,
        "parents": parent_ids,
        "children": children,
        "child_counts": {child_tier: len(ids) for child_tier, ids in children.items()},
        "descendant_micro_theme_count": _descendant_micro_theme_count(
            subject_id, index, children_map),
        "has_sub_theme_layer": bool(tier == "theme" and children.get("sub_theme")),
    }
    return _envelope(subject_id, "available", None, value)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def read_hierarchy_breadth(node_id: str, *, nodes: pd.DataFrame | None = None,
                           edges: pd.DataFrame | None = None) -> dict:
    """Read the hierarchy breadth of one theme node as a uniform envelope.

    ``nodes``/``edges`` default to ``store.read_nodes(current=True)`` /
    ``store.read_edges()`` and are read at call time only — nothing is cached
    across calls. Tests inject small in-memory frames and never read ``data/**``.
    """
    if _is_internal_only_id(node_id):
        # Gate #2: never an input subject; refuse before any store read.
        return _envelope(node_id, "not_applicable", "not_applicable")
    if nodes is None:
        nodes = store.read_nodes(current=True)
    if edges is None:
        edges = store.read_edges()
    index = _node_index(nodes)
    parents_map, children_map = _parent_child_maps(edges)
    return _breadth(node_id, index, parents_map, children_map)


def hierarchy_breadth_table(*, nodes: pd.DataFrame | None = None,
                            edges: pd.DataFrame | None = None) -> list[dict]:
    """One :func:`read_hierarchy_breadth` envelope per ACTIVE theme-kind node.

    Sorted by ``subject_id``. The store (when not injected) is loaded at most
    once per call; the per-subject envelopes reuse the same lookup maps.
    Gate #2 ids and retired/merged nodes are never subjects here.
    """
    if nodes is None:
        nodes = store.read_nodes(current=True)
    if edges is None:
        edges = store.read_edges()
    index = _node_index(nodes)
    parents_map, children_map = _parent_child_maps(edges)
    subjects = sorted(
        node_id for node_id, row in index.items()
        if row.get("kind") == "theme"
        and _is_active(row)
        and not _is_internal_only_id(node_id)
    )
    return [_breadth(node_id, index, parents_map, children_map)
            for node_id in subjects]


def validate_no_forbidden_keys(obj: object, _path: str = "") -> list[str]:
    """Recursively report every dict key whose lower-cased name contains a
    DISPLAY-forbidden word (``cell.FORBIDDEN_VALUE_KEY_WORDS``). Returns one
    human-readable path per violation and never raises; ``[]`` means clean.
    """
    problems: list[str] = []
    if isinstance(obj, dict):
        for key, item in obj.items():
            here = f"{_path}.{key}" if _path else str(key)
            name = str(key).lower()
            if any(word in name for word in FORBIDDEN_VALUE_KEY_WORDS):
                problems.append(f"forbidden value key: {here}")
            problems.extend(validate_no_forbidden_keys(item, here))
    elif isinstance(obj, (list, tuple, set)):
        for position, item in enumerate(obj):
            problems.extend(validate_no_forbidden_keys(item, f"{_path}[{position}]"))
    return problems
