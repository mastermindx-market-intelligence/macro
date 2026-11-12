"""Tests for scripts/export_gmi_history_registry.py (synthetic graph, network-free),
plus consistency of the committed links table with the committed index file."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest
import yaml

from scripts import export_gmi_history_registry as ex

ROOT = Path(__file__).resolve().parent.parent
HIST = ROOT / "data/breadth/history"


def _edge(t, s, d, belief="2026-11-01", valid_to=None, comp="c1"):
    return {"edge_id": f"{t}:{s}->{d}", "type": t, "src": s, "dst": d, "valid_to": valid_to,
            "belief_time": belief, "computed_at": comp}


@pytest.fixture
def graph(tmp_path):
    tg = tmp_path / "data/theme_graph"; tg.mkdir(parents=True)
    nodes = pd.DataFrame([
        {"node_id": "co:us:AAA", "kind": "company", "tier": None},
        {"node_id": "co:us:BBB", "kind": "company", "tier": None},
        {"node_id": "co:us:DEAD", "kind": "company", "tier": None},
        {"node_id": "co:cn:CCC", "kind": "company", "tier": None},
        {"node_id": "basket:baskets:b1", "kind": "basket", "tier": None},
        {"node_id": "theme:t1", "kind": "theme", "tier": "theme"},
        {"node_id": "theme:m1", "kind": "theme", "tier": "macro_category"},
        {"node_id": "theme:s1", "kind": "theme", "tier": "sub_theme"},
        {"node_id": "theme:u1", "kind": "theme", "tier": "micro_theme"},
        {"node_id": "ltheme:finviz:sub1", "kind": "local_theme", "tier": None},
    ])
    nodes.to_parquet(tg / "nodes.parquet")
    edges = pd.DataFrame([
        _edge("MEMBER_OF", "co:us:AAA", "basket:baskets:b1"),
        _edge("MEMBER_OF", "co:us:BBB", "basket:baskets:b1", valid_to="2026-10-01"),      # closed
        _edge("MEMBER_OF", "co:us:DEAD", "basket:baskets:b1"),                             # retired
        _edge("MEMBER_OF", "co:cn:CCC", "basket:baskets:b1"),                              # not US
        _edge("MEMBER_OF", "co:us:AAA", "ltheme:finviz:sub1"),                             # vendor plane
        _edge("EXPRESSES", "basket:baskets:b1", "theme:t1"),
        _edge("EXPRESSES", "ltheme:finviz:sub1", "theme:t1"),
        _edge("PARENT_OF", "theme:m1", "theme:t1"),
        _edge("PARENT_OF", "theme:t1", "theme:s1"),
        _edge("PARENT_OF", "theme:s1", "theme:u1"),
        # older belief that was closed later: latest belief wins
        _edge("MEMBER_OF", "co:us:BBB", "basket:baskets:b1", belief="2026-09-01", valid_to=None),
    ])
    edges.to_parquet(tg / "edges.parquet")
    pd.DataFrame([{"node_id": "co:us:DEAD", "status": "retired"}]).to_parquet(tg / "node_lifecycle.parquet")
    pd.DataFrame([
        {"node_id": "co:us:AAA", "computed_at": "1", "resolution_state": "RESOLVED", "listing_key": "US-XNYS-AAA"},
        {"node_id": "co:us:BBB", "computed_at": "1", "resolution_state": "RESOLVED", "listing_key": "US-XNAS-BBB"},
        {"node_id": "co:us:DEAD", "computed_at": "1", "resolution_state": "RESOLVED", "listing_key": "US-XNAS-DEAD"},
        {"node_id": "co:cn:CCC", "computed_at": "1", "resolution_state": "RESOLVED", "listing_key": "CN-XSHG-CCC"},
    ]).to_parquet(tg / "identity_resolution.parquet")
    (tmp_path / "data/themes_heatmap").mkdir(parents=True)
    (tmp_path / "data/themes_heatmap/themes_tree.json").write_text(json.dumps(
        [{"key": "T", "subsectors": [{"key": "sub1", "members": ["AAA"]}, {"key": "sub2", "members": ["BBB"]}]}]))
    (tmp_path / "data/baskets").mkdir(parents=True)
    (tmp_path / "data/baskets/membership.json").write_text(json.dumps({"baskets": {"b1": {"members": []}}}))
    (tmp_path / "config").mkdir()
    (tmp_path / "config/theme_pathways.yml").write_text(yaml.safe_dump({"themes": [{
        "theme_id": "t1",
        "nodes": [{"id": "t1__driver", "node_type": "enabling_infrastructure", "basket_refs": []},
                  {"id": "t1__ben", "node_type": "direct_beneficiary", "basket_refs": ["b1"]}],
        "edges": [{"src": "t1__driver", "dst": "t1__ben", "order": 1, "side": "winner"}]}]}))
    return tmp_path


def test_registry_rules(graph):
    g = ex.graph_frames(graph)
    th, mc = ex.registries(graph, g)
    assert th.to_dict("records") == [{"ticker": "AAA", "group": "theme:t1"}]   # closed, retired, non-US, vendor dropped
    assert mc.to_dict("records") == [{"ticker": "AAA", "group": "theme:m1"}]


def test_links_shape_and_series_flags(graph):
    g = ex.graph_frames(graph)
    lk, m = ex.links(graph, g, "abc", {"gmi_theme": {"theme:t1"}, "basket": {"b1"}})
    assert "ticker" not in lk.columns and not any("price" in c for c in lk.columns)
    assert m["subsectors_matched_to_local_theme"] == 1 and m["subsectors_unmatched"] == ["sub2"]
    got = set(zip(lk.child_family, lk.child_id, lk.parent_family, lk.parent_id, lk.link_type))
    assert ("basket", "b1", "gmi_theme", "theme:t1", "EXPRESSES") in got
    assert ("subsector", "sub1", "gmi_theme", "theme:t1", "EXPRESSES") in got
    assert ("gmi_theme", "theme:t1", "gmi_macro_category", "theme:m1", "PARENT_OF") in got
    assert ("gmi_micro_theme", "theme:u1", "gmi_sub_theme", "theme:s1", "PARENT_OF") in got
    assert ("basket", "b1", "gmi_theme", "theme:t1", "PATHWAY_ROLE") in got
    assert ("pathway_node", "t1__ben", "pathway_node", "t1__driver", "PATHWAY_WINNER") in got
    sub = lk[lk.child_family.isin(["gmi_sub_theme", "gmi_micro_theme"])]
    assert not sub.child_has_series.any()
    assert (lk.source_commit == "abc").all()


def test_overlap_single_name_and_rights_rows(graph):
    g = ex.graph_frames(graph)
    mems = {"basket": pd.DataFrame({"ticker": ["A", "B", "C"], "group": ["b1", "b1", "b1"]}),
            "subsector": pd.DataFrame({"ticker": ["A", "B", "Z"], "group": ["sub1", "sub1", "sub2"]}),
            "sector": pd.DataFrame({"ticker": ["C", "D"], "group": ["S", "S"]})}
    lk, m = ex.links(graph, g, "abc", {"basket": {"b1"}}, mems)
    ov = lk[lk.link_type == "overlap"].set_index(["child_family", "child_id", "parent_family", "parent_id"])
    assert ov.loc[("basket", "b1", "subsector", "sub1"), "n_shared"] == 2
    assert ov.loc[("basket", "b1", "sector", "S"), "n_shared"] == 1
    assert ov.loc[("basket", "b1", "sector", "S"), ["child_n", "parent_n"]].tolist() == [3, 2]
    assert ov.loc[("basket", "b1", "subsector", "sub1"), "rights_class"] == "internal_only"
    assert ov.loc[("basket", "b1", "sector", "S"), "rights_class"] == "house"
    assert ("subsector", "sub2") not in {(a, b) for a, b, _, _ in ov.index}   # shares nothing
    assert m["single_name_groups"] == {"subsector": ["sub2"]}
    one = lk[(lk.child_family == "subsector") & (lk.child_id == "sub2")]
    assert one.child_single_name.all()


def test_unresolved_id_refused(graph):
    g = ex.graph_frames(graph)
    pw = yaml.safe_load((graph / "config/theme_pathways.yml").read_text())
    df = pd.DataFrame([{"child_family": "basket", "child_id": "nope", "parent_family": "gmi_theme",
                        "parent_id": "theme:t1"}])
    assert ex.unresolved_ids(df, g, {"b1"}, {"sub1"}, pw) == [("basket", "nope")]


# ---- committed artifacts (skipped on a sparse tree without data/)
_needs = pytest.mark.skipif(not (HIST / "group_links_current.parquet").exists(),
                            reason="data/ not checked out (sparse tree)")


VEND = HIST / "internal_only"
LINK_FILES = {"house": (HIST / "group_links_current.parquet", HIST / "house_ew_index_weekly_current.parquet"),
              "internal_only": (VEND / "vendor_internal_only_group_links_current.parquet",
                                VEND / "vendor_internal_only_ew_index_weekly_current.parquet")}


def _series():
    out = set()
    for _, ix_path in LINK_FILES.values():
        ix = pd.read_parquet(ix_path, columns=["family", "group", "level"]).dropna(subset=["level"])
        out |= set(zip(ix.family, ix.group))
    return out


@_needs
def test_committed_links_have_no_tickers_and_match_index():
    series = _series()
    for rc, (path, _) in LINK_FILES.items():
        lk = pd.read_parquet(path)
        assert list(lk.columns) == ex.LINK_COLUMNS
        assert not any("ticker" in c or "price" in c for c in lk.columns)
        assert (lk["rights_class"] == rc).all()
        for fc, ic, hc in (("child_family", "child_id", "child_has_series"),
                           ("parent_family", "parent_id", "parent_has_series")):
            exp = [(f, i) in series for f, i in zip(lk[fc], lk[ic])]
            assert lk[hc].tolist() == exp
        meta = json.loads(path.with_suffix(".meta.json").read_text())
        assert len(meta["source_commit"]) == 40 and meta["no_tickers_no_prices"] is True
        assert meta["rights_class"] == rc


@_needs
def test_vendor_links_stay_with_vendor_files():
    house = pd.read_parquet(LINK_FILES["house"][0])
    vend = pd.read_parquet(LINK_FILES["internal_only"][0])
    fam = lambda d: set(d.child_family) | set(d.parent_family)  # noqa: E731
    assert not fam(house) & set(ex.VENDOR_FAMILIES)
    assert ((vend.child_family.isin(ex.VENDOR_FAMILIES)) | (vend.parent_family.isin(ex.VENDOR_FAMILIES))).all()
    meta = json.loads(LINK_FILES["internal_only"][0].with_suffix(".meta.json").read_text())
    assert meta["source_family"] == "finviz_themes"


@_needs
def test_overlap_rows_are_consistent():
    for path, _ in LINK_FILES.values():
        ov = pd.read_parquet(path)
        ov = ov[ov.link_type == "overlap"]
        assert len(ov) and (ov.n_shared >= 1).all()
        assert (ov.n_shared <= ov[["child_n", "parent_n"]].min(axis=1)).all()
        key = list(zip(ov.child_family, ov.child_id, ov.parent_family, ov.parent_id))
        assert len(key) == len(set(key))
        assert not set(key) & {(c, d, a, b) for a, b, c, d in key}     # unordered: one row per pair


@_needs
def test_committed_gmi_and_relationship_families_built():
    meta = json.loads((HIST / "house_breadth_and_index_current.meta.json").read_text())
    assert meta["members"]["gmi_theme"]["groups"] == 15        # 18 house themes, 3 member-empty
    assert meta["members"]["gmi_macro_category"]["groups"] == 7
    for f in ("gmi_theme", "gmi_macro_category", "rel_customers_of", "rel_suppliers_of"):
        assert meta["members"][f]["unpriced"] == []
    assert meta["members"]["rel_customers_of"]["groups"] == 4
    assert meta["members"]["rel_suppliers_of"]["groups"] == 3
    rel = meta["relationship_families"]
    assert rel["basis"] == "proposed_relationships_unadmitted"
    assert rel["precision"]["value"] == 0.6621 and rel["recall"]["value"] == 0.3487
    assert "one member in three" in rel["sentence"] and "chips and hardware" in rel["hubs_note"]
    assert meta["families"]["rel_customers_of"]["basis"] == "proposed_relationships_unadmitted"
    assert meta["price_topup"]["names"] == 4 and "single download" in meta["price_topup"]["rule"]
