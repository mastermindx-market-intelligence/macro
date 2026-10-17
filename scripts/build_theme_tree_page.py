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


def _as_of_date(nodes_path: Path) -> str:
    """Honor SPEC §2 — the nodes artifact mtime, else "Date unavailable"."""
    if not nodes_path.exists():
        return ""
    try:
        mtime = nodes_path.stat().st_mtime
        return datetime.fromtimestamp(mtime, tz=timezone.utc).strftime("%Y-%m-%d")
    except OSError:
        return ""


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
    if nodes is None or edges is None:
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

    nodes_path = Path(root) / "data" / "theme_graph" / "nodes.parquet"
    as_of = _as_of_date(nodes_path) if not isinstance(nodes, pd.DataFrame) else ""
    # When the caller injected frames we cannot read the artifact mtime —
    # fall back to a present-day stamp so the hero never lies about as-of.
    if not as_of:
        as_of = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
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
