"""Build the Theme Map page -> site/theme_tree.html.

Reads the live theme graph via
``engine.theme_graph.hierarchy_breadth_display.hierarchy_breadth_table`` and
the curated node name table via ``engine.theme_graph.store.read_nodes``.
The page is display_only / context-only — no authority signals, no sized
inputs. The reader is the only source for counts and child relationships;
the page emits whatever the reader emits and never invents any signal.

Usage::

    python -m scripts.build_theme_tree_page                # auto-detect root
    python -m scripts.build_theme_tree_page --root /repo
    python -m scripts.build_theme_tree_page --root . --out /tmp/theme_tree.html
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
from jinja2 import Environment, FileSystemLoader, Undefined

log = logging.getLogger("build_theme_tree_page")

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))


# ---------------------------------------------------------------------------
# SPEC_U3 — "Why is this company here?" ticker lookup
# ---------------------------------------------------------------------------
# Public house basket families (the producer's EXPRESSES key surface). The five
# prefixes are the only places a company can find a public theme path; the two
# internal-only families (``basket:baskets_china_ths:`` and ``ltheme:``) are
# never named, counted or hinted at in any U3 output.
_PUBLIC_BASKET_FAMILIES: tuple[str, ...] = (
    "basket:baskets:",
    "basket:baskets_china:",
    "basket:baskets_hk:",
    "basket:baskets_intl:",
    "basket:baskets_canada:",
)
_PUBLIC_BASKET_FAMILY_SET: frozenset[str] = frozenset(_PUBLIC_BASKET_FAMILIES)
_INTERNAL_BASKET_PREFIXES: tuple[str, ...] = (
    "basket:baskets_china_ths:",
    "ltheme:",
)
# Families the producer has no EXPRESSES key for. A basket in one of these
# families always abstains as ``market_not_wired`` until a producer key lands
# (separate lane, out of U3 scope).
_MARKET_NOT_WIRED_FAMILIES: frozenset[str] = frozenset({
    "basket:baskets_hk:",
    "basket:baskets_intl:",
    "basket:baskets_canada:",
})
# Raw blob size cap. Real-data sizing (worktree C, 2,809 companies + every
# path) runs larger than this; when the budget trips, only companies with at
# least one path ship, plus an abstention summary block (logged, not silent).
_TICKER_BLOB_BUDGET_BYTES = 400 * 1024


def _unmapped_basket_slugs(root: Path) -> frozenset[str]:
    """Slugs listed under ``config/theme_crosswalk.yml::unmapped_baskets``.

    A public house basket whose slug is in this set abstains as
    ``basket_not_a_theme`` rather than ``basket_unmapped``. The YAML is read
    at build time; an unreadable document yields an empty set (degrades
    safely: every no-path basket falls into ``basket_unmapped``).
    """
    path = root / "config" / "theme_crosswalk.yml"
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return frozenset()
    try:
        import yaml  # noqa: PLC0415
        document = yaml.safe_load(text)
    except Exception:  # noqa: BLE001
        return frozenset()
    if not isinstance(document, dict):
        return frozenset()
    rows = document.get("unmapped_baskets")
    if not isinstance(rows, list):
        return frozenset()
    out: set[str] = set()
    for row in rows:
        if isinstance(row, dict):
            slug = row.get("id")
            if isinstance(slug, str) and slug.strip():
                out.add(slug.strip())
    return frozenset(out)


def _family_market(prefix: str) -> str | None:
    """Two-letter market code for a basket id prefix, or None for internal-only."""
    if prefix == "basket:baskets:":
        return "us"
    if prefix == "basket:baskets_china:":
        return "cn"
    if prefix == "basket:baskets_hk:":
        return "hk"
    if prefix == "basket:baskets_intl:":
        return "intl"
    if prefix == "basket:baskets_canada:":
        return "ca"
    return None


def _public_basket_id(basket_id: str) -> bool:
    """True iff the basket id is a public house basket (one of the five
    families); internal-only families return False."""
    return any(basket_id.startswith(p) for p in _PUBLIC_BASKET_FAMILIES)


def _internal_basket_id(basket_id: str) -> bool:
    return any(basket_id.startswith(p) for p in _INTERNAL_BASKET_PREFIXES)


def _symbol_for_node(row: dict) -> str:
    """Uppercased ticker from ``external_ids.symbol`` on a company-kind row.

    Empty when the row carries no symbol — the caller then drops the node
    from the ticker lookup (a mint without a round-trippable ticker cannot
    be addressed by users).
    """
    raw = row.get("external_ids")
    if isinstance(raw, str) and raw.strip():
        try:
            parsed = json.loads(raw)
        except ValueError:
            return ""
        if isinstance(parsed, dict):
            sym = parsed.get("symbol")
            if isinstance(sym, str):
                return sym.strip().upper()
    return ""


class _FrameStore:
    """Read-only store adapter for ``structural_navigation.hierarchy_paths``.

    The reader takes a store view that exposes ``read_nodes``,
    ``read_node_lifecycle`` and ``read_edges``. Tests inject small in-memory
    DataFrames; the live path uses the canonical ``RepositoryStore``. Both
    shapes implement the same triple, so the same builder code runs.
    """

    def __init__(
        self,
        nodes: pd.DataFrame,
        edges: pd.DataFrame,
        lifecycle: pd.DataFrame | None = None,
    ) -> None:
        self._nodes = nodes
        self._edges = edges
        self._lifecycle = lifecycle if lifecycle is not None else pd.DataFrame()

    def read_nodes(self) -> pd.DataFrame:
        return self._nodes

    def read_edges(self) -> pd.DataFrame:
        return self._edges

    def read_node_lifecycle(self) -> pd.DataFrame:
        return self._lifecycle


# ---------------------------------------------------------------------------
# Frame loading
# ---------------------------------------------------------------------------


def _as_of_date(meta_path: Path) -> str:
    """SPEC §2 — the store's ``belief_time`` (YYYY-MM-DD), else "" so the page
    renders "Date unavailable". File mtimes are not used: in a CI checkout they
    are the checkout time, not the data date."""
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return ""
    value = str(meta.get("belief_time") or "")[:10] if isinstance(meta, dict) else ""
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        return ""
    return value


def _load_frames(root: Path) -> tuple[pd.DataFrame | None, pd.DataFrame | None]:
    """Read nodes (current=True) and edges from the store, no caching.

    Returns ``(None, None)`` on any failure — the page builder renders an
    honest ".mx-empty" page rather than crash.
    """
    try:
        sys.path.insert(0, str(root))
        from engine.theme_graph import store  # noqa: PLC0415
        nodes = store.read_nodes(current=True)
        edges = store.read_edges()
        return nodes, edges
    except Exception as exc:  # noqa: BLE001
        log.warning("theme_graph store unreadable: %s; page renders empty state", exc)
        return None, None


def _node_name_index(nodes: pd.DataFrame) -> dict[str, dict]:
    """node_id -> ``{name_en, name_zh, tier}`` for theme-kind rows.

    The page reads names only — no other column. The map is local to one
    call; the reader underneath already keeps its own lookup.
    """
    index: dict[str, dict] = {}
    for row in nodes.to_dict("records"):
        if row.get("kind") != "theme":
            continue
        node_id = row.get("node_id")
        if not isinstance(node_id, str) or not node_id:
            continue
        if node_id in index:
            continue
        index[node_id] = {
            "node_id": node_id,
            "name_en": (row.get("name_en") or node_id) if isinstance(row.get("name_en"), str) else node_id,
            "name_zh": row.get("name_zh") if isinstance(row.get("name_zh"), str) else "",
            "tier": row.get("tier") or "",
        }
    return index


# ---------------------------------------------------------------------------
# Pure compose
# ---------------------------------------------------------------------------


def _sort_macros(
    macros: list[dict], name_index: dict[str, dict]
) -> list[dict]:
    """Alphabetical by name_en (EN page); empty categories sort last — SPEC §3."""

    def key(macro: dict) -> tuple[int, str]:
        nm = (name_index.get(macro["subject_id"], {}).get("name_en") or "").lower()
        # empty marker (child_counts.theme == 0 AND descendant_micro_theme_count == 0
        # AND no themes carry child sub_themes or micro_themes → 0)
        is_empty = macro["empty"]
        return (1 if is_empty else 0, nm)

    return sorted(macros, key=key)


def _build_tree(
    envelopes: list[dict], name_index: dict[str, dict]
) -> dict:
    """Group reader envelopes by tier; build the macro → theme → sub_theme →
    micro-theme rows and the breadth strip data.

    Multi-parent micro-themes appear under EVERY parent macro/theme; the
    caller surfaces the 'Also under' line. Spec §3 explicitly forbids
    de-duplication so the breadth numbers stay honest about how many
    parents a micro-theme serves.
    """
    by_id = {env["subject_id"]: env for env in envelopes}

    macros = [
        env for env in envelopes
        if env.get("status") == "available" and env["value"]["tier"] == "macro_category"
    ]
    themes = [
        env for env in envelopes
        if env.get("status") == "available" and env["value"]["tier"] == "theme"
    ]
    sub_themes = [
        env for env in envelopes
        if env.get("status") == "available" and env["value"]["tier"] == "sub_theme"
    ]
    micros = [
        env for env in envelopes
        if env.get("status") == "available" and env["value"]["tier"] == "micro_theme"
    ]

    # Multi-parent index: micro_id -> sorted list of distinct active parents (any tier)
    micro_parents: dict[str, list[str]] = {}
    for micro in micros:
        parents = micro["value"]["parents"]
        micro_parents[micro["subject_id"]] = [
            p for p in parents
            if by_id.get(p, {}).get("status") == "available"
        ]

    def _name(node_id: str) -> str:
        return name_index.get(node_id, {}).get("name_en") or node_id

    # For each micro-theme under a parent: the OTHER active parents' names.
    def _other_parents_line(micro_id: str, current_parent_id: str, *, lang: str) -> str:
        others = [
            pid for pid in micro_parents.get(micro_id, []) if pid != current_parent_id
        ]
        if not others:
            return ""
        names = [_name(pid) for pid in others]
        if lang == "zh":
            # Concatenation kept minimal — name_zh is not on the envelope.
            return "同时属于：" + "、".join(names)
        return "Also under: " + ", ".join(names)

    # Per-theme: organize sub_theme + micro_theme children.
    themes_out: list[dict] = []
    for theme in themes:
        subject_id = theme["subject_id"]
        name_en = name_index.get(subject_id, {}).get("name_en") or subject_id
        name_zh = name_index.get(subject_id, {}).get("name_zh") or name_en
        sub_ids = list(theme["value"]["children"].get("sub_theme", []))
        direct_micros = list(theme["value"]["children"].get("micro_theme", []))

        # Pick the SAME micro-themes under any sub-theme out of the direct list.
        # The reader enforces disjoint adjacency, so this set is the union.
        sub_micros: dict[str, list[str]] = {}
        for sid in sub_ids:
            sub_env = by_id.get(sid)
            if sub_env and sub_env.get("status") == "available":
                sub_micros[sid] = list(sub_env["value"]["children"].get("micro_theme", []))

        # Build sub_theme rows (sorted by name_en).
        sub_rows: list[dict] = []
        for sid in sorted(sub_ids, key=_name):
            sub_env = by_id.get(sid)
            if not sub_env or sub_env.get("status") != "available":
                continue
            sub_name_en = name_index.get(sid, {}).get("name_en") or sid
            sub_name_zh = name_index.get(sid, {}).get("name_zh") or sub_name_en
            micro_chips: list[dict] = []
            for mid in sub_micros.get(sid, []):
                micro_env = by_id.get(mid)
                if not micro_env or micro_env.get("status") != "available":
                    continue
                micro_name_en = name_index.get(mid, {}).get("name_en") or mid
                micro_name_zh = name_index.get(mid, {}).get("name_zh") or micro_name_en
                tip_en = _other_parents_line(mid, sid, lang="en")
                tip_zh = _other_parents_line(mid, sid, lang="zh")
                micro_chips.append({
                    "node_id": mid,
                    "name_en": micro_name_en,
                    "name_zh": micro_name_zh,
                    "tip_en": tip_en,
                    "tip_zh": tip_zh,
                })
            sub_rows.append({
                "subject_id": sid,
                "name_en": sub_name_en,
                "name_zh": sub_name_zh,
                "micro_count": len(micro_chips),
                "micros": micro_chips,
            })

        # Direct micro chips (theme has no sub_theme layer).
        direct_chips: list[dict] = []
        for mid in direct_micros:
            micro_env = by_id.get(mid)
            if not micro_env or micro_env.get("status") != "available":
                continue
            micro_name_en = name_index.get(mid, {}).get("name_en") or mid
            micro_name_zh = name_index.get(mid, {}).get("name_zh") or micro_name_en
            tip_en = _other_parents_line(mid, subject_id, lang="en")
            tip_zh = _other_parents_line(mid, subject_id, lang="zh")
            direct_chips.append({
                "node_id": mid,
                "name_en": micro_name_en,
                "name_zh": micro_name_zh,
                "tip_en": tip_en,
                "tip_zh": tip_zh,
            })

        themes_out.append({
            "subject_id": subject_id,
            "name_en": name_en,
            "name_zh": name_zh,
            "has_sub_theme_layer": bool(sub_rows),
            "sub_themes": sub_rows,
            "direct_micros": direct_chips,
        })

    # Per-macro distinct micro-theme descendants — the breadth strip (§4).
    def _descendant_micros(node_id: str) -> set[str]:
        seen = {node_id}
        stack = [node_id]
        out: set[str] = set()
        while stack:
            cur = stack.pop()
            env = by_id.get(cur)
            if not env or env.get("status") != "available":
                continue
            children = env["value"]["children"]
            for child_tier, child_ids in children.items():
                for cid in child_ids:
                    if cid in seen:
                        continue
                    seen.add(cid)
                    child_env = by_id.get(cid)
                    if child_env and child_env.get("status") == "available" \
                            and child_env["value"]["tier"] == "micro_theme":
                        out.add(cid)
                    stack.append(cid)
        return out

    macros_out: list[dict] = []
    empty_macros_count = 0
    for macro in macros:
        subject_id = macro["subject_id"]
        theme_ids = list(macro["value"]["children"].get("theme", []))
        child_themes = [
            t for t in themes_out
            if t["subject_id"] in theme_ids
        ]
        # Sort by name_en to keep macro inner ordering deterministic.
        child_themes.sort(key=lambda t: t["name_en"].lower())
        descendants = _descendant_micros(subject_id)
        is_empty = (
            not child_themes and not descendants
        )
        if is_empty:
            empty_macros_count += 1
        macros_out.append({
            "subject_id": subject_id,
            "name_en": name_index.get(subject_id, {}).get("name_en") or subject_id,
            "name_zh": name_index.get(subject_id, {}).get("name_zh") or subject_id,
            "themes": child_themes,
            "dist_micros_count": len(descendants),
            "empty": is_empty,
        })

    macros_out = _sort_macros(macros_out, name_index)

    # Summary tier counts come from the reader envelope, not the DOM.
    summary = {
        "macro_count": len(macros),
        "theme_count": len(themes),
        "sub_theme_count": len(sub_themes),
        "micro_count": len(micros),
        "missing_count": sum(
            1 for env in envelopes
            if env.get("status") != "available"
        ),
    }

    return {
        "macros": macros_out,
        "summary": summary,
        "empty_macros_count": empty_macros_count,
        "available": True,
    }


# Basket node prefix -> published page directory under site/. Only house-owned
# basket families are listed; anything else renders as plain text (no link).
_BASKET_FAMILIES = {
    "basket:baskets:": ("basket", "US", "美股"),
    "basket:baskets_china:": ("basket_china", "China A-shares", "A股"),
    "basket:baskets_hk:": ("basket_hk", "Hong Kong", "港股"),
    "basket:baskets_intl:": ("basket_intl", "International", "国际"),
    "basket:baskets_canada:": ("basket_canada", "Canada", "加拿大"),
}
_MAX_CHAINS = 4


def _basket_family(src_id: str) -> tuple[str, str, str, str] | None:
    """``(page_dir, slug, market_en, market_zh)`` for a house basket id."""
    for prefix, (page_dir, market_en, market_zh) in _BASKET_FAMILIES.items():
        if src_id.startswith(prefix):
            return page_dir, src_id[len(prefix):], market_en, market_zh
    return None


def _basket_href(src_id: str, site_dir: Path) -> str | None:
    family = _basket_family(src_id)
    if family is None:
        return None
    page_dir, slug = family[0], family[1]
    if slug and "/" not in slug and (site_dir / page_dir / f"{slug}.html").is_file():
        return f"{page_dir}/{slug}.html"
    return None


def _build_details(
    envelopes: list[dict],
    name_index: dict[str, dict],
    nodes: pd.DataFrame,
    edges: pd.DataFrame,
    site_dir: Path,
) -> dict[str, dict]:
    """Per micro-theme detail for the click card (U2).

    Parent chains and branch breadth come from the hierarchy-breadth
    envelopes; watch-instead instruments come from the rights-gated proxy
    reader. Display-only: names, ids, links and counts of themes — never a
    weight, share, score or rank. A missing value stays a typed state
    (``proxy_state``), never a zero.
    """
    from engine.theme_graph import micro_rs_proxy_display as mrp  # noqa: PLC0415

    by_id = {env["subject_id"]: env for env in envelopes}
    proxies = {
        env["subject_id"]: env
        for env in mrp.micro_rs_proxy_table(nodes=nodes, edges=edges)
    }
    basket_names: dict[str, tuple[str, str]] = {}
    if "kind" in nodes.columns:
        for row in nodes[nodes["kind"] == "basket"].to_dict("records"):
            nid = row.get("node_id")
            if isinstance(nid, str):
                en = row.get("name_en") if isinstance(row.get("name_en"), str) else None
                zh = row.get("name_zh") if isinstance(row.get("name_zh"), str) else None
                basket_names[nid] = (en or nid, zh or en or nid)

    def _ref(node_id: str) -> dict:
        info = name_index.get(node_id, {})
        en = info.get("name_en") or node_id
        return {
            "node_id": node_id,
            "name_en": en,
            "name_zh": info.get("name_zh") or en,
            "tier": info.get("tier") or by_id.get(node_id, {}).get("value", {}).get("tier"),
        }

    def _chains(micro_id: str) -> list[list[dict]]:
        out: list[list[dict]] = []

        def walk(cur: str, path: list[str]) -> None:
            if len(out) >= _MAX_CHAINS:
                return
            env = by_id.get(cur)
            parents = []
            if env and env.get("status") == "available":
                parents = [
                    p for p in env["value"]["parents"]
                    if by_id.get(p, {}).get("status") == "available" and p not in path
                ]
            if not parents:
                if len(path) > 1:
                    out.append([_ref(n) for n in reversed(path[1:])])
                return
            for parent in parents:
                walk(parent, path + [parent])

        walk(micro_id, [micro_id])
        return out

    details: dict[str, dict] = {}
    for env in envelopes:
        if env.get("status") != "available" or env["value"]["tier"] != "micro_theme":
            continue
        micro_id = env["subject_id"]
        chains = _chains(micro_id)
        breadth = []
        seen_themes: set[str] = set()
        for chain in chains:
            for ref in chain:
                if ref["tier"] == "theme" and ref["node_id"] not in seen_themes:
                    seen_themes.add(ref["node_id"])
                    theme_env = by_id.get(ref["node_id"], {})
                    breadth.append({
                        "theme": ref,
                        "micro_count": theme_env.get("value", {}).get(
                            "descendant_micro_theme_count"),
                    })
        proxy_env = proxies.get(micro_id)
        instruments: list[dict] = []
        if proxy_env is None or proxy_env.get("status") != "available":
            proxy_state = "unknown"
        else:
            seen_src: set[str] = set()
            for inst in proxy_env["value"]["proxy_instruments"]:
                src = inst["src_id"]
                if src in seen_src:
                    continue
                seen_src.add(src)
                en, zh = basket_names.get(src, (src, src))
                family = _basket_family(src)
                instruments.append({
                    "name_en": en,
                    "name_zh": zh,
                    "market_en": family[2] if family else "",
                    "market_zh": family[3] if family else "",
                    "href": _basket_href(src, site_dir),
                })
            instruments.sort(key=lambda i: (i["market_en"], i["name_en"].lower()))
            proxy_state = "available" if instruments else "none"
        details[micro_id] = {
            **_ref(micro_id),
            "chains": chains,
            "breadth": breadth,
            "proxy_state": proxy_state,
            "instruments": instruments,
        }
    return details


def _details_json(envelopes, name_index, nodes, edges, site_dir: Path) -> str:
    """Serialize the U2 card data, or ``""`` when it cannot be shown safely.

    The forbidden-key walk runs over the whole payload; any hit (or any
    reader failure) drops the card data and the page falls back to the U1
    hover tip instead of shipping a value-shaped field.
    """
    from engine.theme_graph import hierarchy_breadth_display as hb  # noqa: PLC0415

    try:
        details = _build_details(envelopes, name_index, nodes, edges, site_dir)
    except Exception as exc:  # noqa: BLE001
        log.warning("theme_tree: detail card data unavailable: %s", exc)
        return ""
    if hb.validate_no_forbidden_keys(details):
        log.warning("theme_tree: detail card data refused by forbidden-key walk")
        return ""
    # ``</`` cannot appear inside the inline JSON script element.
    return json.dumps(details, ensure_ascii=False, sort_keys=True).replace("</", "<\\/")


# ---------------------------------------------------------------------------
# SPEC_U3 — ticker lookup batch composition
# ---------------------------------------------------------------------------


def _basket_record_to_chain(
    record: dict, basket_meta: dict, site_dir: Path,
    member_edge_id: str = "",
) -> dict:
    """Flatten a ``hierarchy_paths(basket)`` record into the U3 path shape.

    The chain runs root → ... → theme anchor, matching the U2 walk order
    (the chain's last element is the anchor that ``EXPRESSES`` lands on).
    ``member_edge_id`` is the live MEMBER_OF edge id joining the company to
    the basket — not emitted in the public blob (the spec only requires
    ``basket`` and ``chain``), but tracked on the in-memory record so the
    parity walk can match ``hierarchy_paths(company)`` exactly.
    """
    basket_id = basket_meta.get("node_id", "")
    chain = [
        {
            "node_id": el["node_id"],
            "name_en": el.get("name_en") or el["node_id"],
            "name_zh": el.get("name_zh") or el.get("name_en") or el["node_id"],
            "tier": el.get("tier") or "",
        }
        for el in record.get("path", [])
    ]
    out = {
        "basket": {
            "name_en": basket_meta.get("name_en", basket_id),
            "name_zh": basket_meta.get("name_zh", basket_id),
            "href": _basket_href(basket_id, site_dir),
        },
        "chain": chain,
    }
    if member_edge_id:
        out["_member_edge_id"] = member_edge_id
    return out


def _classify_abstention(
    basket_id: str, unmapped_slugs: frozenset[str]
) -> str:
    """One of ``market_not_wired`` / ``basket_not_a_theme`` / ``basket_unmapped``.

    ``basket_id`` is assumed to be a public house basket (the only baskets
    that reach this code path). Internal-only families never surface, so
    they're not classified here.
    """
    for prefix in _MARKET_NOT_WIRED_FAMILIES:
        if basket_id.startswith(prefix):
            return "market_not_wired"
    slug = ""
    for prefix in _PUBLIC_BASKET_FAMILIES:
        if basket_id.startswith(prefix):
            slug = basket_id[len(prefix):]
            break
    if slug and slug in unmapped_slugs:
        return "basket_not_a_theme"
    return "basket_unmapped"


def _abstention_entry(code: str, meta: dict) -> dict:
    """One typed abstention line: the reason code plus the PUBLIC basket name.

    Only public house baskets reach this helper, so the name shown is always
    one the site already publishes; internal-only families never get here.
    """
    nid = str(meta.get("node_id") or "")
    en = meta.get("name_en") if isinstance(meta.get("name_en"), str) else ""
    zh = meta.get("name_zh") if isinstance(meta.get("name_zh"), str) else ""
    return {
        "code": code,
        "basket": {"name_en": en or nid, "name_zh": zh or en or nid},
    }


def _empty_company_record(
    *,
    no_public_basket: bool = False,
    not_in_graph: bool = False,
    abstentions: list[str] | None = None,
) -> dict:
    """The U3 record shape for a company with no live path.

    The keys are stable so the JS can branch on them without surprises:
    ``paths`` is always a list, ``micro`` is always the typed abstention,
    and the state flags are mutually exclusive.
    """
    return {
        "paths": [],
        "micro": "micro_not_wired",
        "abstentions": list(abstentions) if abstentions else [],
        "no_public_basket": bool(no_public_basket),
        "not_in_graph": bool(not_in_graph),
    }


def _build_ticker_lookup(
    root: Path,
    nodes: pd.DataFrame,
    edges: pd.DataFrame,
    *,
    as_of: str,
    knowledge_cutoff: str | None = None,
) -> dict[str, dict]:
    """Batch composition of company → basket → theme paths (SPEC_U3).

    One ``hierarchy_paths(store, basket_id, asof)`` call per public house
    basket (≤121) resolves every anchor up to root once. Then for each
    company we look up its live MEMBER_OF rows via the incumbent
    ``_collapse_relevant_edges`` and concatenate MEMBER_OF → EXPRESSES hop
    to the pre-resolved basket paths. No per-company call to
    ``hierarchy_paths`` — that would cost ~19 minutes for the real graph
    (SPEC §"Measured state").

    Returns a dict keyed by ``"<market>:<TICKER>"`` (e.g. ``"us:AAPL"``).
    """
    from engine.theme_graph import structural_navigation as sn  # noqa: PLC0415

    site_dir = Path(root) / "site"
    unmapped = _unmapped_basket_slugs(Path(root))
    # Convert each frame to records ONCE. ``hierarchy_paths`` runs
    # ``_records`` (a DataFrame ``to_dict``) on every call; handing it lists
    # makes that a cheap row copy. Measured: ~50 s of the first cut's ~43 s
    # overrun was repeated ``to_dict`` across ~121 basket calls.
    node_rows = nodes.to_dict("records") if hasattr(nodes, "to_dict") else list(nodes)
    edges_records = edges.to_dict("records") if hasattr(edges, "to_dict") else list(edges)
    store_view = _FrameStore(node_rows, edges_records)  # type: ignore[arg-type]

    # 1. Public house basket ids present in the graph (kind == "basket" and
    #    starts with one of the five families). Sorted for deterministic build
    #    order. The cap of 121 comes from the SPEC ("≤121"); we never exceed
    #    that in practice — the largest family, baskets (US), tops out around
    #    49 today and the rest are smaller.
    public_baskets: list[str] = []
    if "node_id" in nodes.columns and "kind" in nodes.columns:
        for row in node_rows:
            nid = row.get("node_id")
            if not isinstance(nid, str) or not nid:
                continue
            if row.get("kind") != "basket":
                continue
            if not _public_basket_id(nid):
                continue
            public_baskets.append(nid)
    public_baskets = sorted(set(public_baskets))

    # 2. basket_id → list of (anchor, chain, via) records (the same shape
    #    hierarchy_paths returns; ``via`` here is just the EXPRESSES hop).
    #    A basket reaches a theme only through an EXPRESSES row whose src is
    #    the basket (structural_navigation.hierarchy_paths), so a basket with
    #    no such row at any time returns [] — skip the call, same result.
    expresses_src = {
        str(r.get("src") or "") for r in edges_records
        if str(r.get("type") or "") == "EXPRESSES"
    }
    basket_records: dict[str, list[dict]] = {}
    for basket_id in public_baskets:
        if basket_id not in expresses_src:
            basket_records[basket_id] = []
            continue
        try:
            basket_records[basket_id] = sn.hierarchy_paths(
                store_view, basket_id, as_of,
                knowledge_cutoff=knowledge_cutoff,
            )
        except Exception as exc:  # noqa: BLE001
            log.warning("theme_tree: hierarchy_paths(%s) failed: %s", basket_id, exc)
            basket_records[basket_id] = []

    # 3. Cache basket node metadata (name_en/name_zh). One pass over nodes.
    basket_meta: dict[str, dict] = {}
    for row in node_rows:
        nid = row.get("node_id")
        if (
            isinstance(nid, str) and nid in basket_records
            and nid not in basket_meta and row.get("kind") == "basket"
        ):
            en = row.get("name_en") if isinstance(row.get("name_en"), str) else ""
            zh = row.get("name_zh") if isinstance(row.get("name_zh"), str) else ""
            basket_meta[nid] = {
                "node_id": nid,
                "name_en": en or nid,
                "name_zh": zh or en or nid,
            }

    # 4. Live MEMBER_OF edges per company, liveness via _collapse_relevant_edges.
    from engine.theme_graph.ontology import (  # noqa: PLC0415
        _collapse_relevant_edges,
        _parse_date,
    )

    asof_date = _parse_date(as_of, "as_of")
    cutoff_date = (
        _parse_date(knowledge_cutoff, "knowledge_cutoff")
        if knowledge_cutoff
        else asof_date
    )

    company_live_baskets: dict[str, set[str]] = {}
    # ``member_edge_index[company_id][edge_id] = {basket_id, ...}`` — tracks
    # which MEMBER_OF edge ids live for each (company → basket) pair so the
    # parity walk can match ``hierarchy_paths(company)``'s via tuple exactly.
    member_edge_index: dict[str, dict[str, set[str]]] = {}
    company_ids = set()
    if "node_id" in nodes.columns and "kind" in nodes.columns:
        for row in node_rows:
            if row.get("kind") == "company" and isinstance(row.get("node_id"), str):
                company_ids.add(row["node_id"])
    # Group edge rows by endpoint in ONE pass, preserving original order
    # (``_collapse_relevant_edges`` uses the row index as a tie-break, and it
    # already skips rows not touching ``node_id`` — so a per-company slice in
    # original order yields the identical live set).
    rows_by_company: dict[str, list[dict]] = {}
    for r in edges_records:
        for end in {str(r.get("src") or ""), str(r.get("dst") or "")}:
            if end in company_ids:
                rows_by_company.setdefault(end, []).append(r)
    for company_id in sorted(company_ids):
        try:
            live, _future = _collapse_relevant_edges(
                rows_by_company.get(company_id, []), node_id=company_id, asof=asof_date,
                knowledge_cutoff=cutoff_date,
            )
        except Exception as exc:  # noqa: BLE001
            log.warning("theme_tree: liveness for %s failed: %s", company_id, exc)
            continue
        member_baskets: set[str] = set()
        for row in live:
            if str(row.get("type") or "") != "MEMBER_OF":
                continue
            if str(row.get("src") or "") != company_id:
                continue
            dst = str(row.get("dst") or "")
            if not dst:
                continue
            member_baskets.add(dst)
            eid = str(row.get("edge_id") or "")
            if eid:
                member_edge_index.setdefault(company_id, {})\
                    .setdefault(eid, set()).add(dst)
        if member_baskets:
            company_live_baskets[company_id] = member_baskets

    # 5. Compose per-company records.
    lookup: dict[str, dict] = {}
    if "node_id" not in nodes.columns:
        return lookup

    for row in node_rows:
        if row.get("kind") != "company":
            continue
        company_id = row.get("node_id")
        if not isinstance(company_id, str) or not company_id:
            continue
        symbol = _symbol_for_node(row)
        if not symbol:
            continue
        market = row.get("market_scope")
        if not isinstance(market, str) or not market:
            # A company without market_scope cannot be addressed by users;
            # drop it from the lookup.
            continue
        key = f"{market}:{symbol}"
        member_baskets = company_live_baskets.get(company_id, set())

        if not member_baskets:
            lookup[key] = _empty_company_record(not_in_graph=True)
            continue

        # Partition: public vs internal-only. Internal-only memberships are
        # silently dropped (never named, counted, or hinted at).
        public_memberships = sorted(
            b for b in member_baskets if _public_basket_id(b)
        )
        internal_only = any(_internal_basket_id(b) for b in member_baskets)

        if not public_memberships:
            # Every membership is internal-only — show the typed state.
            lookup[key] = _empty_company_record(no_public_basket=True)
            continue

        # Public baskets that produced no path → typed abstention per basket.
        paths: list[dict] = []
        abstentions: list[str] = []
        for basket_id in public_memberships:
            records = basket_records.get(basket_id) or []
            if records:
                meta = basket_meta.get(basket_id, {"node_id": basket_id})
                # Find the live MEMBER_OF edge_id for this (company, basket)
                # pair so the parity walk can confirm the batch composition
                # matches ``hierarchy_paths(company)`` exactly.
                member_edge_id = ""
                for eid, baskets in member_edge_index.get(company_id, {}).items():
                    if basket_id in baskets:
                        member_edge_id = eid
                        break
                for rec in records:
                    paths.append(_basket_record_to_chain(
                        rec, meta, site_dir, member_edge_id,
                    ))
            else:
                abstentions.append(_abstention_entry(
                    _classify_abstention(basket_id, unmapped),
                    basket_meta.get(basket_id, {"node_id": basket_id}),
                ))

        record: dict = {
            "paths": paths,
            "micro": "micro_not_wired",
            "abstentions": abstentions,
            "no_public_basket": False,
            "not_in_graph": False,
        }
        # ``internal_only`` is read for symmetry — a company with BOTH
        # internal-only and public memberships is still "has_public_basket".
        # The flag is intentionally NOT emitted; internal-only memberships
        # never surface, so we never claim the inverse either.
        _ = internal_only
        lookup[key] = record

    return lookup


# --- U4: six-axis company profile (display-only AxisCell labels) -----------

# Added build time on real data is measured in the PR; the size share is
# asserted in tests. Axes ride inside the U3 blob and its 400 KB budget.
_AXES_BLOB_BUDGET_BYTES = 120 * 1024

_COUNTRY_NAMES = {
    "US": ("United States", "美国"),
    "CN": ("China", "中国"),
    "HK": ("Hong Kong, China", "中国香港"),
    "CA": ("Canada", "加拿大"),
}
_MIC_NAMES = {
    "XNAS": ("Nasdaq", "纳斯达克"),
    "XNYS": ("NYSE", "纽交所"),
    "ARCX": ("NYSE Arca", "NYSE Arca"),
    "XASE": ("NYSE American", "NYSE American"),
    "XSHG": ("Shanghai SE", "上交所"),
    "XSHE": ("Shenzhen SE", "深交所"),
    "XHKG": ("HKEX", "港交所"),
    "XTSE": ("TSX", "多伦多交易所"),
}
_VALUE_CHAIN_NAMES = {
    "upstream": ("Upstream", "上游"),
    "midstream": ("Midstream", "中游"),
    "downstream": ("Downstream", "下游"),
    "enabler": ("Enabler", "支撑环节"),
}


def _country_label(code: object) -> tuple[str, str] | None:
    text = str(code or "").strip().upper()
    if not text:
        return None
    return _COUNTRY_NAMES.get(text, (text, text))


def _axis_label(axis: str, value: object) -> tuple[str, str] | None:
    """A plain display string for one AVAILABLE cell, or None.

    Only named text fields are read; the raw value, its numbers, source and
    provenance never reach the blob.
    """
    if not isinstance(value, dict):
        return None
    if axis == "sic_industry":
        text = str(value.get("sic_description") or "").strip()
        # SIC descriptions exist in English only; ZH shows the same text.
        return (text, text) if text else None
    if axis == "geography":
        country = _country_label(value.get("listing_country"))
        if country is None:
            return None
        en, zh = country
        mic = _MIC_NAMES.get(str(value.get("listing_mic") or "").strip().upper())
        if mic is not None:
            en, zh = f"{mic[0]}, {en}", f"{zh}·{mic[1]}"
        domicile = _country_label(value.get("domicile"))
        if domicile is not None and domicile != country:
            en, zh = f"{en} (domiciled in {domicile[0]})", f"{zh}（注册地：{domicile[1]}）"
        return en, zh
    if axis == "business_model":
        groups = [g for g in value.get("groups") or [] if isinstance(g, dict)]
        en = [str(g.get("label_en") or "").strip() for g in groups]
        zh = [str(g.get("label_zh") or g.get("label_en") or "").strip() for g in groups]
        en, zh = [t for t in en if t], [t for t in zh if t]
        return ("; ".join(en), "；".join(zh)) if en else None
    if axis == "lifecycle":
        status = str(value.get("node_status") or "").strip()
        if not status:
            return None
        return ("Active", "存续") if status == "canonical" else ("Tracked", "跟踪中")
    if axis == "value_chain":
        return _VALUE_CHAIN_NAMES.get(str(value.get("value_chain_position") or ""))
    if axis == "macro_sensitivity":
        # The measured betas live on the stock page; the profile only says
        # that a measurement exists (no numbers on this page).
        return ("Measured — see the stock page", "已测算——见个股页")
    return None


def _batched_identity_resolver(as_of: str):
    """``resolve_graph_node_identity`` with its per-call loads hoisted.

    The public function re-reads the node table and the Data OS master
    inputs on every call (~0.15 s each). This loads both once and calls the
    same incumbent ``_resolve_node_row`` in HISTORICAL mode, raising
    ``UnknownGraphNodeError`` for the same cases. Parity is pinned by
    tests/test_theme_tree_axes.py.
    """
    from engine.theme_graph import identity_resolution as ir  # noqa: PLC0415
    from engine.theme_graph import store  # noqa: PLC0415

    nodes_df = store.read_nodes()
    kinds = (
        dict(zip(nodes_df["node_id"].astype(str), nodes_df["kind"].astype(str)))
        if not nodes_df.empty else {}
    )
    etf_syms = ir._etf_symbols(nodes_df.to_dict("records"))
    inputs = ir.load_master_inputs()
    cache: dict[tuple[str, str], dict] = {}

    def resolve(node_id: str, asof: str | None = None) -> dict:
        nid = str(node_id)
        kind = kinds.get(nid)
        if kind is None:
            raise ir.UnknownGraphNodeError(f"{nid!r} is not a node in the theme graph")
        if kind != "company":
            raise ir.UnknownGraphNodeError(f"{nid!r} is kind={kind!r}")
        asof_str = str(asof if asof is not None else as_of)
        key = (nid, asof_str)
        if key not in cache:
            cache[key] = ir._resolve_node_row(
                node_id=nid, resolution_asof=asof_str, inputs=inputs,
                etf_symbols=etf_syms, computed_at=ir._utc_now_stamp(),
                engine_version=store.ENGINE_VERSION, historical=True,
            )
        return cache[key]

    return resolve


def _axis_readers(root: Path, as_of: str) -> tuple[dict, object]:
    """Per-build injected readers: every artifact is opened once.

    Returns ``(static_readers, geography_factory)``; the geography reader is
    built per subject so it sees only that company's security-master slice
    (the reader filters by ``security_id`` itself, so the slice changes cost,
    never the answer).
    """
    from functools import partial  # noqa: PLC0415

    from engine.classification_axes import (  # noqa: PLC0415
        business_model, geography, lifecycle, sic_industry, value_chain,
    )
    from engine.theme_graph import store  # noqa: PLC0415

    readers: dict = {}
    profiles_path = root / sic_industry.SOURCE_ARTIFACT
    if profiles_path.exists():
        readers["sic_industry"] = partial(
            sic_industry.read_sic_industry, profiles=pd.read_parquet(profiles_path)
        )
    membership_path = root / business_model.SOURCE_ARTIFACT
    if membership_path.exists():
        readers["business_model"] = partial(
            business_model.read_business_model,
            membership=json.loads(membership_path.read_text(encoding="utf-8")),
        )
    graph_nodes = store.read_nodes(current=False, strict=True)
    try:
        node_lifecycle = store.read_node_lifecycle(latest=False, strict=True)
    except FileNotFoundError:
        node_lifecycle = None
    if node_lifecycle is not None:
        readers["lifecycle"] = partial(
            lifecycle.read_lifecycle, nodes=graph_nodes, lifecycle=node_lifecycle
        )
        readers["value_chain"] = partial(
            value_chain.read_value_chain, nodes=graph_nodes, lifecycle=node_lifecycle
        )
    else:
        readers["lifecycle"] = partial(lifecycle.read_lifecycle, nodes=graph_nodes)
        readers["value_chain"] = partial(value_chain.read_value_chain, nodes=graph_nodes)

    master_path = geography._master_path(root)
    if not master_path.exists():
        return readers, None
    master = pd.read_parquet(master_path)
    empty = master.iloc[0:0]
    slices = {str(k): g for k, g in master.groupby(master["security_id"].astype(str))}
    resolve = _batched_identity_resolver(as_of)

    def geography_for(subject_id: str):
        def _slice() -> pd.DataFrame:
            try:
                row = resolve(subject_id, asof=as_of)
            except Exception:  # noqa: BLE001 — the reader types the failure itself
                return empty
            sid = row.get("security_id") if hasattr(row, "get") else None
            return slices.get(str(sid), empty) if sid is not None else empty
        return partial(geography.read_geography, resolve=resolve, master=_slice())

    return readers, geography_for


def _company_axes(root: Path, keys: list[str], as_of: str) -> dict[str, list[dict]]:
    """``{lookup key: [axis entries]}`` for the given U3 record keys.

    Each entry is ``{axis, status, reason_code, label_en, label_zh}`` in
    ``cell.AXES`` order. A row failing ``validate_row`` is dropped and
    counted in the log. Raises nothing: any setup fault returns ``{}``.
    """
    from engine.classification_axes import cell, registry  # noqa: PLC0415

    try:
        static, geography_for = _axis_readers(root, as_of)
    except Exception as exc:  # noqa: BLE001
        log.warning("theme_tree: company profile readers unavailable: %s", exc)
        return {}

    out: dict[str, list[dict]] = {}
    dropped = 0
    for key in keys:
        market, _, symbol = key.partition(":")
        subject_id = f"co:{market}:{symbol}"
        readers = dict(static)
        if geography_for is not None:
            readers["geography"] = geography_for(subject_id)
        try:
            row = registry.read_axes(subject_id, as_of=as_of, root=root, readers=readers)
        except Exception:  # noqa: BLE001 — a malformed subject id is a dropped row
            dropped += 1
            continue
        if registry.validate_row(row):
            dropped += 1
            continue
        entries = []
        for axis in cell.AXES:
            c = row["cells"].get(axis) or {}
            status = str(c.get("status") or "unknown")
            label = _axis_label(axis, c.get("value")) if status == "available" else None
            if status == "available" and label is None:
                status, reason = "unknown", "value_missing"
            else:
                reason = str(c.get("reason_code") or "") or None
            entries.append({
                "axis": axis,
                "status": status,
                "reason_code": reason,
                "label_en": label[0] if label else None,
                "label_zh": label[1] if label else None,
            })
        out[key] = entries
    if dropped:
        log.warning("theme_tree: company profile dropped %d invalid row(s)", dropped)
    return out


def _axes_key_findings(payload: object) -> list[str]:
    """Keys in ``payload`` that carry a ``cell.FORBIDDEN_VALUE_KEY_WORDS`` word."""
    from engine.classification_axes import cell  # noqa: PLC0415

    found: list[str] = []

    def walk(node: object) -> None:
        if isinstance(node, dict):
            for k, v in node.items():
                low = str(k).lower()
                if any(w in low for w in cell.FORBIDDEN_VALUE_KEY_WORDS):
                    found.append(str(k))
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(payload)
    return found


def _attach_axes(root: Path, records: dict[str, dict], as_of: str) -> list[dict] | None:
    """Add U4 ``axes`` to path-bearing records; return the shared cell table.

    Most cells repeat across companies (every company's value chain is the
    same ``not_applicable`` cell), so each distinct entry is stored once in
    the returned table and a record's ``axes`` lists six indices into it, in
    ``cell.AXES`` order. Returns ``None`` and leaves records untouched (the
    U3 panel still works) on any forbidden key or when the table plus the
    indices exceed their 120 KB share; both are logged.
    """
    from engine.theme_graph import hierarchy_breadth_display as hb  # noqa: PLC0415

    axes = _company_axes(root, sorted(records), as_of)
    if not axes:
        return None
    if hb.validate_no_forbidden_keys(axes) or _axes_key_findings(axes):
        log.warning("theme_tree: company profile refused by forbidden-key walk")
        return None
    table: list[dict] = []
    index: dict[str, int] = {}
    refs: dict[str, list[int]] = {}
    for key, entries in axes.items():
        row = []
        for entry in entries:
            ident = json.dumps(entry, ensure_ascii=False, sort_keys=True)
            if ident not in index:
                index[ident] = len(table)
                table.append(entry)
            row.append(index[ident])
        refs[key] = row
    size = len(json.dumps([table, refs], ensure_ascii=False, sort_keys=True).encode("utf-8"))
    if size > _AXES_BLOB_BUDGET_BYTES:
        log.warning(
            "theme_tree: company profile %d KB > %d KB share; shipping without it",
            size // 1024, _AXES_BLOB_BUDGET_BYTES // 1024,
        )
        return None
    for key, row in refs.items():
        records[key]["axes"] = row
    return table


def _ticker_lookup_json(
    root: Path,
    nodes: pd.DataFrame,
    edges: pd.DataFrame,
    *,
    as_of: str,
    knowledge_cutoff: str | None = None,
) -> str:
    """Serialize the U3 lookup blob, or ``""`` when it cannot be shown safely.

    The forbidden-key walk runs over the whole payload; any hit (or any
    builder failure) drops the blob and the page hides the lookup. When the
    raw blob would exceed the 400 KB budget, only companies with at least
    one path ship plus an abstention summary block; the drop is logged.
    """
    from engine.theme_graph import hierarchy_breadth_display as hb  # noqa: PLC0415

    if not as_of:
        return ""
    try:
        full = _build_ticker_lookup(
            root, nodes, edges,
            as_of=as_of, knowledge_cutoff=knowledge_cutoff,
        )
    except Exception as exc:  # noqa: BLE001
        log.warning("theme_tree: ticker lookup unavailable: %s", exc)
        return ""

    # Path-bearing companies ship whole. Every other company ships in a
    # compact ``abstainers`` index (key → state string, or a list of
    # ``[code, basket_index]`` pairs into ``basket_names``) so an abstaining
    # ticker still renders its typed reason instead of "not found".
    records: dict[str, dict] = {}
    abstainers: dict[str, object] = {}
    basket_names: list[dict] = []
    name_index: dict[tuple[str, str], int] = {}
    for key, rec in full.items():
        if rec.get("paths"):
            # Ship only what the page reads; the join key stays builder-side.
            records[key] = {
                "paths": [
                    {k: v for k, v in path.items() if not k.startswith("_")}
                    for path in rec["paths"]
                ],
                "micro": rec.get("micro"),
                "abstentions": rec.get("abstentions") or [],
            }
            continue
        if rec.get("no_public_basket"):
            abstainers[key] = "no_public_basket"
            continue
        if rec.get("not_in_graph") or not rec.get("abstentions"):
            abstainers[key] = "not_in_graph"
            continue
        pairs: list[list] = []
        for a in rec["abstentions"]:
            b = a.get("basket") or {}
            nk = (str(b.get("name_en") or ""), str(b.get("name_zh") or ""))
            if nk not in name_index:
                name_index[nk] = len(basket_names)
                basket_names.append({"name_en": nk[0], "name_zh": nk[1]})
            pairs.append([a.get("code"), name_index[nk]])
        abstainers[key] = pairs

    axis_cells = _attach_axes(root, records, as_of)

    payload = {
        "version": 2,
        "as_of": as_of,
        "records": records,
        "abstainers": abstainers,
        "basket_names": basket_names,
    }
    if axis_cells is not None:
        payload["axis_cells"] = axis_cells
    if hb.validate_no_forbidden_keys(payload):
        log.warning("theme_tree: ticker lookup refused by forbidden-key walk")
        return ""

    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    if len(raw.encode("utf-8")) <= _TICKER_BLOB_BUDGET_BYTES:
        return raw.replace("</", "<\\/")

    # Budget exceeded → drop the abstainer index, keep path-bearing companies
    # plus a typed summary count. The drop is logged (no silent cap).
    summary = {"with_paths": len(records), "no_paths": len(abstainers)}
    log.warning(
        "theme_tree: ticker lookup %d KB > %d KB budget; "
        "dropping the abstainer index (%d companies; %d path-bearing kept)",
        len(raw.encode("utf-8")) // 1024,
        _TICKER_BLOB_BUDGET_BYTES // 1024,
        summary["no_paths"], summary["with_paths"],
    )
    payload = {
        "version": 2,
        "as_of": as_of,
        "records": records,
        "_summary": summary,
    }
    if hb.validate_no_forbidden_keys(payload):
        log.warning("theme_tree: pruned ticker lookup refused by forbidden-key walk")
        return ""
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return raw.replace("</", "<\\/")


def compose(
    root: Path,
    *,
    nodes: pd.DataFrame | None = None,
    edges: pd.DataFrame | None = None,
) -> dict:
    """Build template context from live artifacts. Never raises.

    ``nodes``/``edges`` are caller-injectable for tests. When ``None`` we
    read the store at call time — nothing cached across calls.
    """
    injected = nodes is not None and edges is not None
    if not injected:
        loaded_nodes, loaded_edges = _load_frames(root)
        if loaded_nodes is None or loaded_edges is None:
            return {
                "available": False,
                "as_of": "",
                "macros": [],
                "summary": {"macro_count": 0, "theme_count": 0,
                            "sub_theme_count": 0, "micro_count": 0,
                            "missing_count": 0},
                "empty_macros_count": 0,
                "empty_reason_en": "The theme map could not be loaded. Other pages still work.",
                "empty_reason_zh": "主题地图无法加载。其他页面仍可使用。",
            }
        nodes = loaded_nodes
        edges = loaded_edges

    from engine.theme_graph import hierarchy_breadth_display as hb  # noqa: PLC0415

    envelopes = hb.hierarchy_breadth_table(nodes=nodes, edges=edges)
    name_index = _node_name_index(nodes)
    tree = _build_tree(envelopes, name_index)
    tree["details_json"] = _details_json(
        envelopes, name_index, nodes, edges, Path(root) / "site"
    )

    meta_path = Path(root) / "data" / "theme_graph" / "_meta.json"
    as_of = "" if injected else _as_of_date(meta_path)
    # When the date is unknown (injected frames, missing artifact) leave it
    # empty: the template renders "Date unavailable" rather than a guessed
    # present-day stamp (SPEC §2).
    tree["as_of"] = as_of
    # SPEC_U3 — ticker lookup. The blob is built from live frames when
    # ``as_of`` is known; an empty ``as_of`` (injected frames, missing meta)
    # skips the lookup entirely, same degrade as U2's detail card.
    tree["ticker_lookup_json"] = (
        _ticker_lookup_json(
            Path(root), nodes, edges,
            as_of=as_of, knowledge_cutoff=as_of or None,
        )
        if as_of
        else ""
    )
    return tree


# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------


def render(root: Path, ctx: dict | None = None) -> str:
    """Render ``templates/theme_tree.html.j2`` and return the HTML string."""
    if ctx is None:
        ctx = compose(root)

    templates_dir = root / "templates"
    env = Environment(
        loader=FileSystemLoader(str(templates_dir)),
        autoescape=True,
        undefined=Undefined,
    )

    tpl = env.get_template("theme_tree.html.j2")
    return tpl.render(tree=ctx, root=str(root))


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    parser = argparse.ArgumentParser(description="Render theme_tree.html")
    parser.add_argument("--root", default=None, help="Repo root (default: auto-detect)")
    parser.add_argument("--out", default=None,
                        help="Output path (default: site/theme_tree.html under --root)")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve() if args.root else _REPO_ROOT
    out_path = (
        Path(args.out).resolve() if args.out
        else (root / "site" / "theme_tree.html")
    )

    try:
        ctx = compose(root)
        html = render(root, ctx=ctx)
    except Exception as exc:  # noqa: BLE001
        log.error("render failed: %s", exc, exc_info=True)
        return 1

    from lib.pages import write_page  # noqa: PLC0415
    write_page(out_path, html)
    kb = len(html) // 1024
    log.info("wrote %s (%d KB)", out_path, kb)
    return 0


if __name__ == "__main__":
    sys.exit(main())
