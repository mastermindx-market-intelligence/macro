"""Export GMI graph registries and the group links table (COO ruling 31 s2a, s2b).

Reads a theme-graph snapshot (``data/theme_graph/`` at one pinned commit), the
vendor theme tree, the basket roster and ``config/theme_pathways.yml``. Writes:

  data/breadth/history/registry/gmi_theme.csv           (ticker, group)  18 themes, 15 with US-listed members
  data/breadth/history/registry/gmi_macro_category.csv  (ticker, group)  10 macro categories, 7 with US-listed members
  data/breadth/history/registry/rel_customers_of.csv    (ticker, group)  customers of 4 supplier hubs
  data/breadth/history/registry/rel_suppliers_of.csv    (ticker, group)  suppliers of 3 customer hubs
  data/breadth/history/group_links_current.parquet      house links (one row per link)
  <--vendor-out>/vendor_internal_only_group_links_current.parquet
                                                        links touching a vendor family
  and a sidecar beside each links file (pinned commit, counts). The vendor links file is
  kept off git, in scratch (``--vendor-out``, default /tmp/si_plan/quant/vendor_out),
  because the repository is public (COO ruling 38 §2b); it is never committed or pushed.

Link types: EXPRESSES / PARENT_OF / PATHWAY_* from the graph and the pathways file;
``overlap`` (COO ruling 34 s3) for every pair of groups in the history build that
share at least one member, with the shared count and each side's member count. A
group of one member is marked ``single_name`` (it has no series; the stock is the
series). Rows touching the vendor families (subsector, theme) carry
``rights_class: internal_only`` and live only in the vendor file.

Relationship hubs (COO ruling 32 s2): proposed edges of
``data/company_intelligence/relationships/relationship_edges.json`` of species
supplier_customer, contract_manufacturing and component_dependency, roles normalised
to (supplier, customer); a hub is a company with 5 or more counterparties.

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
      [--vendor-out /tmp/si_plan/quant/vendor_out]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import yaml  # noqa: E402

TG = "data/theme_graph"
TREE = "data/themes_heatmap/themes_tree.json"
BASKETS = "data/baskets/membership.json"
PATHWAYS = "config/theme_pathways.yml"
RELS = "data/company_intelligence/relationships/relationship_edges.json"
REL_SPECIES = ("supplier_customer", "contract_manufacturing", "component_dependency")
HUB_MIN = 5
VENDOR_FAMILIES = ("subsector", "theme")
# COO ruling on #11146 (2026-11-12): the 0-of-268 subsector -> house theme match needs a stated cause.
SUBSECTOR_THEME_CAUSE = (
    "Each vendor subsector key equals its graph node id exactly (ltheme:finviz:<key>, 268 of 268), "
    "but the graph by design mints no EXPRESSES edge from a finviz local theme to a house theme "
    "(engine/theme_graph/materialize.py:1385-1390: no concept-grain curation exists for its "
    "subthemes, and a mechanical mapping would smear application-tier subthemes onto "
    "infrastructure-tier themes), and config/theme_crosswalk.yml keys only the 40 vendor theme "
    "names, so no exact documented subsector-to-theme key exists and no such rows are written.")
LINK_COLUMNS = ["child_family", "child_id", "parent_family", "parent_id", "link_type",
                "pathway_node", "node_type", "source_file", "source_commit",
                "child_has_series", "parent_has_series", "n_shared", "child_n", "parent_n",
                "child_single_name", "parent_single_name", "rights_class"]
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


def relationship_registries(root: Path) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """(customers_of, suppliers_of) registries of the hubs, plus counts."""
    doc = json.loads((root / RELS).read_text())
    t = lambda i: i.split("-", 2)[2].replace(".", "-")  # noqa: E731
    pairs = sorted({(t(e["direction"]["from_issuer_id"]), t(e["direction"]["to_issuer_id"]))
                    for e in doc["edges"] if e["species"] in REL_SPECIES})
    p = pd.DataFrame(pairs, columns=["supplier", "customer"])
    out, hubs = [], {}
    for fam, grp, mem in (("rel_customers_of", "supplier", "customer"),
                          ("rel_suppliers_of", "customer", "supplier")):
        n = p.groupby(grp)[mem].nunique()
        h = sorted(n[n >= HUB_MIN].index)
        hubs[fam] = {g: int(n[g]) for g in h}
        r = p[p[grp].isin(h)].rename(columns={mem: "ticker", grp: "group"})[["ticker", "group"]]
        out.append(r.drop_duplicates().sort_values(["group", "ticker"]).reset_index(drop=True))
    meta = {"edges_in_scope": sum(e["species"] in REL_SPECIES for e in doc["edges"]),
            "pairs": len(pairs), "hubs": hubs, "species": list(REL_SPECIES),
            "package_admission": doc.get("adoption_state")}
    return out[0], out[1], meta


def overlap_links(mems: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """One row per unordered pair of groups sharing at least one member."""
    slot = pd.concat([m.assign(family=f)[["family", "group", "ticker"]] for f, m in mems.items()],
                     ignore_index=True).drop_duplicates()
    size = slot.groupby(["family", "group"])["ticker"].nunique()
    j = slot.merge(slot, on="ticker", suffixes=("_a", "_b"))
    j = j[(j["family_a"] + "\0" + j["group_a"]) < (j["family_b"] + "\0" + j["group_b"])]
    c = j.groupby(["family_a", "group_a", "family_b", "group_b"]).size().rename("n_shared").reset_index()
    c["child_n"] = [int(size[(f, g)]) for f, g in zip(c.family_a, c.group_a)]
    c["parent_n"] = [int(size[(f, g)]) for f, g in zip(c.family_b, c.group_b)]
    return c.rename(columns={"family_a": "child_family", "group_a": "child_id",
                             "family_b": "parent_family", "group_b": "parent_id"})


def _basket_id(node_id: str) -> str:
    return node_id.split(":", 2)[2]


def unresolved_ids(df: pd.DataFrame, g: dict, baskets: set[str], subs: set[str], pw: dict,
                   groups: dict[str, set[str]] | None = None) -> list:
    """Every (family, id) in the table must name a graph node, a basket, a subsector
    key, a pathway node of the config, or a group of a history-build family."""
    graph = set(g["nodes"]["node_id"])
    pnodes = {nd["id"] for th in pw["themes"] for nd in th["nodes"]}
    known = {f: set(v) for f, v in (groups or {}).items() if not f.startswith("gmi_")}
    known.update({"basket": baskets | known.get("basket", set()),
                  "subsector": subs | known.get("subsector", set()), "pathway_node": pnodes})
    bad = []
    for fam_col, id_col in (("child_family", "child_id"), ("parent_family", "parent_id")):
        for f, i in zip(df[fam_col], df[id_col]):
            ok = i in known[f] if f in known else i in graph
            if not ok:
                bad.append((f, i))
    return bad


def links(root: Path, g: dict, commit: str, series: dict[str, set[str]],
          mems: dict[str, pd.DataFrame] | None = None) -> tuple[pd.DataFrame, dict]:
    """``series``: family -> set of group ids that have a series (index file).
    ``mems``: family -> (ticker, group) registry of every history-build family, for
    the overlap rows and member counts."""
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
    df = pd.DataFrame(rows, columns=LINK_COLUMNS)
    mems = mems or {}
    size = {(f, gid): int(n) for f, m in mems.items()
            for gid, n in m.groupby("group")["ticker"].nunique().items()}
    if mems:
        ov = overlap_links(mems)
        ov["link_type"] = "overlap"
        ov["source_file"] = "registries of the history build (sidecar families.registry)"
        ov["source_commit"] = commit
        ov["child_has_series"] = [has(f, i) for f, i in zip(ov.child_family, ov.child_id)]
        ov["parent_has_series"] = [has(f, i) for f, i in zip(ov.parent_family, ov.parent_id)]
        df = pd.concat([df, ov.reindex(columns=LINK_COLUMNS)], ignore_index=True)
    df["child_n"] = [size.get((f, i)) for f, i in zip(df.child_family, df.child_id)]
    df["parent_n"] = [size.get((f, i)) for f, i in zip(df.parent_family, df.parent_id)]
    df["n_shared"] = df["n_shared"].astype("Int64")
    for side in ("child", "parent"):
        df[f"{side}_n"] = df[f"{side}_n"].astype("Int64")
        df[f"{side}_single_name"] = df[f"{side}_n"].eq(1).fillna(False).astype(bool)
    vend = df["child_family"].isin(VENDOR_FAMILIES) | df["parent_family"].isin(VENDOR_FAMILIES)
    df["rights_class"] = np.where(vend, "internal_only", "house")
    df = df.drop_duplicates().reset_index(drop=True)
    unresolved = unresolved_ids(df, g, us_baskets, subs, pw,
                                {f: set(m["group"]) for f, m in mems.items()})
    if unresolved:
        raise ValueError(f"link ids that resolve to no node or config entry: {unresolved[:10]}")
    single = {f: sorted(k for (ff, k), n in size.items() if ff == f and n == 1) for f in mems}
    return df, {"subsectors_total": len(subs), "subsectors_matched_to_local_theme": len(matched),
                "subsectors_unmatched": sorted(subs - matched),
                "single_name_groups": {f: v for f, v in single.items() if v}}


def main() -> None:
    from scripts import build_tree_breadth_and_index as bt
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--root", type=Path, required=True, help="tree with the pinned graph inputs")
    ap.add_argument("--commit", required=True)
    ap.add_argument("--out", type=Path, default=_ROOT / "data/breadth/history")
    ap.add_argument("--vendor-out", type=Path, default=bt.VENDOR_OUT_DEFAULT,
                    help="scratch directory for the internal_only links (off git; public repository)")
    ap.add_argument("--build-root", type=Path, default=_ROOT,
                    help="tree with the registries the history build reads (overlap rows)")
    ap.add_argument("--index", type=Path, nargs="*", default=[],
                    help="weekly index files (house and vendor), for has_series")
    ap.add_argument("--registries-only", action="store_true")
    a = ap.parse_args()
    g = graph_frames(a.root)
    th, mc = registries(a.root, g)
    cu, su, rmeta = relationship_registries(a.root)
    reg = a.out / "registry"
    reg.mkdir(parents=True, exist_ok=True)
    th.to_csv(reg / "gmi_theme.csv", index=False)
    mc.to_csv(reg / "gmi_macro_category.csv", index=False)
    cu.to_csv(reg / "rel_customers_of.csv", index=False)
    su.to_csv(reg / "rel_suppliers_of.csv", index=False)
    if a.registries_only:
        print(json.dumps({"gmi_theme": len(th), "gmi_macro_category": len(mc),
                          "rel_customers_of": len(cu), "rel_suppliers_of": len(su), **rmeta}))
        return
    mems = {f: m for f, (_, m) in bt.load_families(a.build_root).items()}
    series: dict[str, set[str]] = {}
    for p in a.index:
        ix = pd.read_parquet(p, columns=["family", "group", "level"]).dropna(subset=["level"])
        for f, s_ in ix.groupby("family")["group"]:
            series.setdefault(f, set()).update(s_)
    lk, m = links(a.root, g, a.commit, series, mems)
    sets = {"house": (a.out, "group_links_current"),
            "internal_only": (a.vendor_out, "vendor_internal_only_group_links_current")}
    summary = {}
    for rc, (d, stem) in sets.items():
        part = lk[lk["rights_class"] == rc].reset_index(drop=True)
        d.mkdir(parents=True, exist_ok=True)
        part.to_parquet(d / f"{stem}.parquet", index=False, compression="zstd")
        # COO ruling 21:07Z: the house sidecar carries counts only. The vendor-family
        # name list (subsectors_unmatched) stays in the off-tree vendor sidecar; the
        # house sidecar records its length as an integer beside the other counts.
        side = m if rc == "internal_only" else {
            **m, "subsectors_unmatched": len(m["subsectors_unmatched"])}
        meta = {"rights_class": rc, "source_commit": a.commit,
                "edges_open_latest_belief": g["n_edges"],
                "dropped_lifecycle_nodes": g["dead"], "dated_membership_note": DATED_SENTENCE,
                "registry_rows": {"gmi_theme": int(len(th)), "gmi_macro_category": int(len(mc)),
                                  "rel_customers_of": int(len(cu)), "rel_suppliers_of": int(len(su))},
                "relationships": rmeta,
                "links_by_type": part.groupby(["child_family", "parent_family", "link_type"]).size()
                                     .rename("n").reset_index().to_dict("records"),
                "rows": int(len(part)),
                "has_series_source": [str(p.name) for p in a.index],
                "member_counts": "child_n / parent_n count registry members (any price state)",
                "overlap": "one row per unordered pair of groups sharing at least one member; "
                           "n_shared is the shared member count; no tickers",
                "no_tickers_no_prices": True, **side}
        if rc == "internal_only":
            from scripts.build_tree_breadth_and_index import VENDOR_RIGHTS
            meta.update(VENDOR_RIGHTS)
            meta["subsector_to_theme_cause"] = SUBSECTOR_THEME_CAUSE
        (d / f"{stem}.meta.json").write_text(json.dumps(meta, indent=1, default=str) + "\n")
        summary[rc] = int(len(part))
    print(json.dumps({"rows": summary, "subsectors_matched": m["subsectors_matched_to_local_theme"],
                      "by_type": {f"{r}/{t}": int(n) for (r, t), n in
                                  lk.groupby(["rights_class", "link_type"]).size().items()}},
                     default=str))


if __name__ == "__main__":
    main()
