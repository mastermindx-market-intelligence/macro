"""Export GMI graph registries and the group links table (COO ruling 31 s2a, s2b).

Reads a theme-graph snapshot (``data/theme_graph/`` at one pinned commit), the
vendor theme tree, the basket roster and ``config/theme_pathways.yml``. Writes:

  data/breadth/history/registry/gmi_theme.csv           (ticker, group)  18 house themes
  data/breadth/history/registry/gmi_macro_category.csv  (ticker, group)  10 macro categories
  data/breadth/history/group_links_current.parquet      one row per link between two groups
  data/breadth/history/group_links_current.meta.json    sidecar (pinned commit, counts)

The registries are membership only (ticker -> group), the same class as
``data/baskets/membership.json``; no prices. The links table has no ticker column
and no prices.

Membership rule (ruling 31 2a), using the store's own read views
(``engine/theme_graph/store.py``):
- edges: latest belief per edge_id (max belief_time, ties on computed_at), then open
  (valid_to null);
- company -MEMBER_OF-> basket -EXPRESSES-> theme (tier theme);
  macro_category -PARENT_OF-> theme;
- US-listed resolved identities only: latest identity row per node, RESOLVED, listing
  key starting ``US-``; ticker = the listing key's symbol, '.' spelled '-';
- nodes that ``node_lifecycle.parquet`` marks retired or merged are dropped;
- no vendor local-theme rows.

Usage:
  python scripts/export_gmi_history_registry.py --root <tree with the pinned inputs> \
      --commit <pinned sha> [--out data/breadth/history]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

import pandas as pd  # noqa: E402
import yaml  # noqa: E402

TG = "data/theme_graph"
TREE = "data/themes_heatmap/themes_tree.json"
BASKETS = "data/baskets/membership.json"
PATHWAYS = "config/theme_pathways.yml"
LINK_COLUMNS = ["child_family", "child_id", "parent_family", "parent_id", "link_type",
                "pathway_node", "node_type", "source_file", "source_commit",
                "child_has_series", "parent_has_series"]
DATED_SENTENCE = ("The graph's dated membership is not used: most of its dates are a seed "
                  "constant or a reconstruction, not observed change, so today's members "
                  "are applied to the past (reconstructed_current_membership).")


def _latest_open_edges(root: Path) -> pd.DataFrame:
    e = pd.read_parquet(root / TG / "edges.parquet")
    e = (e.sort_values(["edge_id", "belief_time", "computed_at"], kind="stable")
           .drop_duplicates("edge_id", keep="last"))
    return e[e["valid_to"].isna()]


def _dead(root: Path) -> set[str]:
    life = pd.read_parquet(root / TG / "node_lifecycle.parquet")
    return set(life.loc[life["status"].isin(["retired", "merged"]), "node_id"])


def _us_tickers(root: Path) -> pd.Series:
    idr = pd.read_parquet(root / TG / "identity_resolution.parquet")
    idr = idr.sort_values(["node_id", "computed_at"], kind="stable").drop_duplicates("node_id", keep="last")
    us = idr[(idr["resolution_state"] == "RESOLVED") & idr["listing_key"].fillna("").str.startswith("US-")]
    return us.set_index("node_id")["listing_key"].str.split("-", n=2).str[2].str.replace(".", "-", regex=False)


def graph_frames(root: Path) -> dict:
    nodes = pd.read_parquet(root / TG / "nodes.parquet")
    dead = _dead(root)
    nodes = nodes[~nodes["node_id"].isin(dead)]
    e = _latest_open_edges(root)
    e = e[~e["src"].isin(dead) & ~e["dst"].isin(dead)]
    kind = nodes.set_index("node_id")["kind"]
    tier = nodes.set_index("node_id")["tier"]
    pick = lambda t, s, d: e[(e["type"] == t) & s(e["src"]) & d(e["dst"])][["src", "dst"]]  # noqa: E731
    return {
        "nodes": nodes, "dead": sorted(dead), "n_edges": int(len(e)),
        "company_basket": pick("MEMBER_OF", lambda s: s.map(kind).eq("company"), lambda d: d.map(kind).eq("basket")),
        "basket_theme": pick("EXPRESSES", lambda s: s.map(kind).eq("basket"), lambda d: d.map(tier).eq("theme")),
        "ltheme_theme": pick("EXPRESSES", lambda s: s.map(kind).eq("local_theme"), lambda d: d.map(tier).eq("theme")),
        "parent_of": pick("PARENT_OF", lambda s: s.map(kind).eq("theme"), lambda d: d.map(kind).eq("theme")),
        "tier": tier,
    }


def registries(root: Path, g: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    tick = _us_tickers(root)
    cb = g["company_basket"].rename(columns={"src": "company", "dst": "basket"})
    cb = cb[cb["company"].isin(tick.index)]
    bt = g["basket_theme"].rename(columns={"src": "basket", "dst": "theme"})
    ct = cb.merge(bt, on="basket")[["company", "theme"]].drop_duplicates()
    po = g["parent_of"]
    mt = po[po["src"].map(g["tier"]).eq("macro_category") & po["dst"].map(g["tier"]).eq("theme")]
    mt = mt.rename(columns={"src": "macro", "dst": "theme"})
    cm = ct.merge(mt, on="theme")[["company", "macro"]].drop_duplicates()
    th = pd.DataFrame({"ticker": ct["company"].map(tick).values, "group": ct["theme"].values})
    mc = pd.DataFrame({"ticker": cm["company"].map(tick).values, "group": cm["macro"].values})
    tidy = lambda d: d.drop_duplicates().sort_values(["group", "ticker"]).reset_index(drop=True)  # noqa: E731
    return tidy(th), tidy(mc)


def _basket_id(node_id: str) -> str:
    return node_id.split(":", 2)[2]


def unresolved_ids(df: pd.DataFrame, g: dict, baskets: set[str], subs: set[str], pw: dict) -> list:
    """Every (family, id) in the table must name a graph node, a basket, a subsector
    key or a pathway node of the config."""
    graph = set(g["nodes"]["node_id"])
    pnodes = {nd["id"] for th in pw["themes"] for nd in th["nodes"]}
    known = {"basket": baskets, "subsector": subs, "pathway_node": pnodes}
    bad = []
    for fam_col, id_col in (("child_family", "child_id"), ("parent_family", "parent_id")):
        for f, i in zip(df[fam_col], df[id_col]):
            ok = i in known[f] if f in known else i in graph
            if not ok:
                bad.append((f, i))
    return bad


def links(root: Path, g: dict, commit: str, series: dict[str, set[str]]) -> tuple[pd.DataFrame, dict]:
    """``series``: family -> set of group ids that have a series (index file)."""
    rows = []
    tier = g["tier"]
    fam_of_tier = {"theme": "gmi_theme", "macro_category": "gmi_macro_category",
                   "sub_theme": "gmi_sub_theme", "micro_theme": "gmi_micro_theme"}
    has = lambda f, i: i in series.get(f, set())  # noqa: E731

    def add(cf, ci, pf, pi, lt, src, pn=None, nt=None):
        rows.append({"child_family": cf, "child_id": ci, "parent_family": pf, "parent_id": pi,
                     "link_type": lt, "pathway_node": pn, "node_type": nt, "source_file": src,
                     "source_commit": commit, "child_has_series": has(cf, ci),
                     "parent_has_series": has(pf, pi)})

    us_baskets = set(json.loads((root / BASKETS).read_text())["baskets"])
    for _, r in g["basket_theme"].iterrows():
        b = _basket_id(r["src"])
        if r["src"].startswith("basket:baskets:") and b in us_baskets:
            add("basket", b, "gmi_theme", r["dst"], "EXPRESSES", f"{TG}/edges.parquet")
    tree = json.loads((root / TREE).read_text())
    subs = {s["key"] for t in tree for s in t["subsectors"]}
    matched = set()
    for _, r in g["ltheme_theme"].iterrows():
        if r["src"].startswith("ltheme:finviz:"):
            k = r["src"].split(":", 2)[2]
            if k in subs:
                matched.add(k)
                add("subsector", k, "gmi_theme", r["dst"], "EXPRESSES", f"{TG}/edges.parquet")
    for _, r in g["parent_of"].iterrows():
        cf, pf = fam_of_tier.get(tier.get(r["dst"])), fam_of_tier.get(tier.get(r["src"]))
        if cf and pf:
            add(cf, r["dst"], pf, r["src"], "PARENT_OF", f"{TG}/edges.parquet")
    pw = yaml.safe_load((root / PATHWAYS).read_text())
    for th in pw["themes"]:
        for nd in th["nodes"]:
            for b in nd.get("basket_refs") or []:
                add("basket", b, "gmi_theme", f"theme:{th['theme_id']}", "PATHWAY_ROLE", PATHWAYS,
                    pn=nd["id"], nt=nd["node_type"])
            if not nd.get("basket_refs"):
                add("pathway_node", nd["id"], "gmi_theme", f"theme:{th['theme_id']}", "PATHWAY_ROLE",
                    PATHWAYS, pn=nd["id"], nt=nd["node_type"])
        for ed in th.get("edges") or []:
            add("pathway_node", ed["dst"], "pathway_node", ed["src"], f"PATHWAY_{ed['side'].upper()}",
                PATHWAYS, pn=ed["dst"], nt=f"order_{ed['order']}")
    df = pd.DataFrame(rows, columns=LINK_COLUMNS).drop_duplicates().reset_index(drop=True)
    unresolved = unresolved_ids(df, g, us_baskets, subs, pw)
    if unresolved:
        raise ValueError(f"link ids that resolve to no node or config entry: {unresolved[:10]}")
    return df, {"subsectors_total": len(subs), "subsectors_matched_to_local_theme": len(matched),
                "subsectors_unmatched": sorted(subs - matched)}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--commit", required=True)
    ap.add_argument("--out", type=Path, default=_ROOT / "data/breadth/history")
    ap.add_argument("--index", type=Path, default=None,
                    help="group_ew_index_weekly_current.parquet, for has_series")
    a = ap.parse_args()
    g = graph_frames(a.root)
    th, mc = registries(a.root, g)
    reg = a.out / "registry"
    reg.mkdir(parents=True, exist_ok=True)
    th.to_csv(reg / "gmi_theme.csv", index=False)
    mc.to_csv(reg / "gmi_macro_category.csv", index=False)
    series: dict[str, set[str]] = {}
    if a.index is not None and a.index.exists():
        ix = pd.read_parquet(a.index, columns=["family", "group", "level"])
        ok = ix.dropna(subset=["level"])
        series = {f: set(s) for f, s in ok.groupby("family")["group"]}
    lk, m = links(a.root, g, a.commit, series)
    lk.to_parquet(a.out / "group_links_current.parquet", index=False, compression="zstd")
    meta = {"source_commit": a.commit, "edges_open_latest_belief": g["n_edges"],
            "dropped_lifecycle_nodes": g["dead"], "dated_membership_note": DATED_SENTENCE,
            "registry_rows": {"gmi_theme": int(len(th)), "gmi_macro_category": int(len(mc))},
            "links_by_type": lk.groupby(["child_family", "parent_family", "link_type"]).size()
                              .rename("n").reset_index().to_dict("records"),
            "has_series_source": "group_ew_index_weekly_current.parquet (any valid level)",
            "no_tickers_no_prices": True, **m}
    (a.out / "group_links_current.meta.json").write_text(json.dumps(meta, indent=1) + "\n")
    print(json.dumps({"registry_rows": meta["registry_rows"], "links": int(len(lk)),
                      "subsectors_matched": m["subsectors_matched_to_local_theme"]}))


if __name__ == "__main__":
    main()
