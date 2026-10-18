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
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from jinja2 import Environment, FileSystemLoader, Undefined

log = logging.getLogger("build_theme_tree_page")

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))


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
