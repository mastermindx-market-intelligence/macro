"""Network-free tests for scripts/build_tree_breadth_and_index.py (synthetic registries)."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from scripts import build_tree_breadth_and_index as bt


def _closes(n_tickers: int, start="1998-01-01", periods=1500, seed=0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range(start, periods=periods)
    r = rng.normal(0.0003, 0.01, size=(periods, n_tickers))
    return pd.DataFrame(100 * np.exp(np.cumsum(r, axis=0)), index=idx,
                        columns=[f"T{i:02d}" for i in range(n_tickers)])


def _root(tmp: Path, tree, baskets, sectors: dict[str, str]) -> Path:
    (tmp / "data/themes_heatmap").mkdir(parents=True)
    (tmp / "data/baskets").mkdir(parents=True)
    (tmp / "data/breadth").mkdir(parents=True)
    (tmp / "data/themes_heatmap/themes_tree.json").write_text(json.dumps(tree))
    (tmp / "data/baskets/membership.json").write_text(json.dumps({"baskets": baskets}))
    pd.DataFrame({"sector": list(sectors.values())}, index=list(sectors.keys())).to_parquet(
        tmp / "data/breadth/constituents.parquet")
    return tmp


@pytest.fixture
def world(tmp_path):
    closes = _closes(30)
    t = list(closes.columns)
    tree = [{"theme": "Alpha", "key": "alpha", "subsectors": [
                {"key": "a_big", "members": t[:12]},          # >= 10: standard
                {"key": "a_mid", "members": t[10:16]},        # 6: small, full series
                {"key": "a_small", "members": t[16:19]},     # 3: small, full series
                {"key": "a_one", "members": t[18:19]}]},     # 1: single_name, no series
            {"theme": "Beta", "key": "beta", "subsectors": [
                {"key": "b_one", "members": t[19:30]}]}]
    baskets = {"bk": {"members": [{"ticker": x, "removed": None} for x in t[:6]]
                      + [{"ticker": t[6], "removed": "2026-01-01"}]}}
    sectors = {x: ("S1" if i < 15 else "S2") for i, x in enumerate(t)}
    root = _root(tmp_path / "root", tree, baskets, sectors)
    cp = tmp_path / "closes.parquet"; closes.to_parquet(cp)
    dm = tmp_path / "dm.json"; dm.write_text(json.dumps({"vintage": "v1"}))
    dis = tmp_path / "dis.csv"
    pd.DataFrame({"both": [100, 100], "flag_dis": [9, 0], "has_only_one": [0, 0], "rate": [0.09, 0.0]},
                 index=pd.Index([1999, 2000], name="era")).to_csv(dis)
    out = tmp_path / "out"
    tree_fams = [f for f in bt.FAMILIES if not f["family"].startswith(("gmi_", "rel_"))]
    res = bt.build(cp, dm, dis, "1999-06-01", out, root=root, daily=True, families=tree_fams,
                   vendor_out=out / "internal_only")
    return closes, out, res


def test_no_row_before_start_and_floors(world):
    closes, out, res = world
    meta = res["internal_only"]
    b = pd.read_parquet(out / "internal_only/vendor_internal_only_breadth_weekly_current.parquet")
    assert b["date"].min() >= pd.Timestamp("1999-06-01")
    lw = b[b["date"] == b["date"].max()].set_index(["family", "group"])
    H = "fix_chg_pct_above_200_13w"
    assert pd.notna(lw.loc[("subsector", "a_big"), H])
    assert pd.notna(lw.loc[("subsector", "a_mid"), H])          # ruling 34: from 2 members
    assert pd.notna(lw.loc[("subsector", "a_small"), H])
    assert lw.loc[("subsector", "a_mid"), "n_members"] == 6
    assert lw.loc[("subsector", "a_small"), "n_members"] == 3
    assert ("subsector", "a_one") not in lw.index                # one member: no series
    assert meta["single_name_groups"] == {"subsector": ["a_one"]}
    assert meta["valid_last_week"] == {"subsector": 4, "theme": 2}
    assert meta["valid_last_week_by_size_class"]["subsector"] == {"small": 2, "standard": 2}


def test_size_class_counts_and_rank_within_class(world):
    _, out, _ = world
    b = pd.read_parquet(out / "internal_only/vendor_internal_only_breadth_weekly_current.parquet")
    H = "fix_chg_pct_above_200_13w"
    assert ((b["n_counted_200"] < 10) == (b["size_class"] == "small")).all()
    ok = b["pct_above_200"].notna()
    assert np.allclose(b.loc[ok, "pct_above_200"],
                       100 * b.loc[ok, "n_above_200"].astype(float) / b.loc[ok, "n_counted_200"])
    lw = b[(b["date"] == b["date"].max()) & (b.family == "subsector")].set_index("group")
    # two small and two standard groups: ranks run 1..2 inside each class, never 1..4
    for cls in ("small", "standard"):
        r = lw[lw.size_class == cls]["rank_" + H]
        assert sorted(r.tolist()) in ([1.0, 2.0], [1.0, 1.0])
        assert (lw[lw.size_class == cls]["n_ranked_" + H] == 2).all()
    assert (b["n_fixed_200_13w"][b[H].notna()] >= 2).all()


def test_multi_group_name_counts_in_each(world):
    _, out, _ = world
    b = pd.read_parquet(out / "internal_only/vendor_internal_only_breadth_weekly_current.parquet")
    lw = b[b["date"] == b["date"].max()].set_index(["family", "group"])
    # T10, T11 sit in a_big and a_mid; theme alpha counts each ticker once (19 distinct)
    assert lw.loc[("subsector", "a_big"), "n_members"] == 12
    assert lw.loc[("theme", "alpha"), "n_members"] == 19


def test_index_floor_and_reasons(world):
    closes, out, _ = world
    d = pd.read_parquet(out / "internal_only/vendor_internal_only_ew_index_daily_current.parquet")
    small = d[(d.family == "subsector") & (d.group == "a_small")]
    assert small["level"].notna().all() and (small["size_class"] == "small").all()
    assert d[(d.family == "subsector") & (d.group == "a_one")].empty
    mid = d[(d.family == "subsector") & (d.group == "a_mid")]
    assert mid["level"].notna().all() and mid["reason"].isna().all()
    assert d["date"].min() >= pd.Timestamp("1999-06-01")


def test_index_matches_ew_level_convention(world):
    closes, out, _ = world
    d = pd.read_parquet(out / "internal_only/vendor_internal_only_ew_index_daily_current.parquet")
    g = d[(d.family == "subsector") & (d.group == "a_mid")].set_index("date")["level"]
    m = closes.columns[10:16]
    r = closes[m].pct_change().loc["1999-06-01":].mean(axis=1)
    exp = (1 + r.fillna(0)).cumprod()
    assert np.allclose(g.values, exp.round(6).values, atol=2e-6)


def test_removed_basket_member_excluded(world):
    _, out, res = world
    assert res["house"]["members"]["basket"]["tickers"] == 6


def test_floor_gap_carries_no_return(tmp_path):
    closes = _closes(6, start="2000-01-03", periods=300)
    closes.iloc[100:110, :5] = np.nan                       # 1 priced -> below floor of 2
    rets = closes.pct_change(fill_method=None).where(closes.notna() & closes.shift(1).notna())
    lvl, n, reason = bt.group_index(rets, list(closes.columns), pd.Timestamp("2000-01-03"),
                                    priced=closes.notna())
    assert (n.iloc[100:110] == 1).all() and n.iloc[110] == 6   # floor counts closes, not returns
    assert lvl.iloc[100:110].isna().all()
    assert (reason.iloc[100:110] == bt.REASON_FLOOR).all()
    assert lvl.iloc[110:].notna().all()
    assert lvl.iloc[99] > 0


def test_weekly_drops_in_progress_week(tmp_path):
    idx = pd.bdate_range("2026-01-05", "2026-01-14")          # ends Wednesday
    daily = pd.DataFrame({"date": idx, "family": "x", "group": "g", "level": 1.0})
    w = bt.to_weekly(daily, idx)
    assert w["date"].max() == pd.Timestamp("2026-01-09")


def test_meta_labels(world):
    _, _, res = world
    meta = res["internal_only"]
    assert meta["basis"] == "reconstructed_current_membership"
    assert meta["basis_note"] == "today's members applied to the past; not point-in-time; survivors only"
    assert meta["start"]["reason_before"] == "second_source_disagreement"
    assert meta["second_source_disagreement_by_year"]["1999"]["rate"] == 0.09
    for k in ("dividend_sentence", "group_size_sentence", "source_sentence"):
        assert meta[k]
    assert "turns" in meta["index"]["dividend_effect"]
    assert "overstated" in meta["index"]["survivors_only_effect"]
    assert "rebalance" in meta["index"]["rebalance_rule"]
    assert meta["first_valid_breadth"] and meta["first_valid_index"]
    assert meta["floors"]["index"] == 2 and meta["floors"]["share_change_rank_state"] == 2
    assert "100/n" in meta["group_size_sentence"]


def test_new_family_is_registry_file_plus_entry(tmp_path, world):
    closes, _, _ = world
    root = tmp_path / "root2"
    (root / "data/x").mkdir(parents=True)
    pd.DataFrame({"ticker": list(closes.columns[:11]), "group": "g1"}).to_csv(root / "data/x/reg.csv", index=False)
    cp = tmp_path / "c.parquet"; closes.to_parquet(cp)
    dm = tmp_path / "dm.json"; dm.write_text("{}")
    dis = tmp_path / "dis.csv"
    pd.DataFrame({"both": [1], "flag_dis": [0], "has_only_one": [0], "rate": [0.0]},
                 index=pd.Index([2000], name="era")).to_csv(dis)
    spec = [{"family": "newfam", "registry": "data/x/reg.csv", "loader": "pairs",
             "outputs": ["breadth", "index"], "label": "test family", "rights_class": "house"}]
    meta = bt.build(cp, dm, dis, "1999-06-01", tmp_path / "o", root=root, families=spec)["house"]
    assert meta["valid_last_week"] == {"newfam": 1}
    assert meta["families"]["newfam"]["label"] == "test family"
    w = pd.read_parquet(tmp_path / "o/house_ew_index_weekly_current.parquet")
    assert set(w.family) == {"newfam"} and w.level.notna().any()


def test_files_split_by_rights_class(world):
    _, out, res = world
    vend = pd.read_parquet(out / "internal_only/vendor_internal_only_ew_index_weekly_current.parquet")
    house = pd.read_parquet(out / "house_ew_index_weekly_current.parquet")
    assert set(vend.family) == {"subsector", "theme"}
    assert set(house.family) == {"basket", "sector"}
    assert not (out / "house_breadth_weekly_current.parquet").exists()   # no house breadth family yet
    v = res["internal_only"]
    assert v["source_family"] == "finviz_themes" and v["rights_class"] == "internal_only"
    assert v["rights_source"] == "config/theme_sources.yml:33"
    assert "NO public/customer display or redistribution" in v["rights_sentence"]
    assert res["house"]["rights_class"] == "house" and "source_family" not in res["house"]


def test_family_without_rights_class_refused(world, tmp_path):
    closes, _, _ = world
    root = tmp_path / "r"; (root / "x").mkdir(parents=True)
    pd.DataFrame({"ticker": list(closes.columns[:6]), "group": "g"}).to_csv(root / "x/r.csv", index=False)
    cp = tmp_path / "c.parquet"; closes.to_parquet(cp)
    dm = tmp_path / "dm.json"; dm.write_text("{}")
    dis = tmp_path / "dis.csv"
    pd.DataFrame({"both": [1], "flag_dis": [0], "has_only_one": [0], "rate": [0.0]},
                 index=pd.Index([2000], name="era")).to_csv(dis)
    spec = [{"family": "f", "registry": "x/r.csv", "loader": "pairs", "outputs": ["index"], "label": "l"}]
    with pytest.raises(ValueError, match="rights_class"):
        bt.build(cp, dm, dis, "1999-06-01", tmp_path / "o", root=root, families=spec)


# --- Vendor rights (COO ruling 32 s1, 2026-11-12; COO ruling 38 §2b) ---
# Vendor-tree breadth series stay internal (COO ruling 32 s1, 2026-11-12).
#
# The subsector and theme families come from the finviz_themes tree, recorded at
# config/theme_sources.yml:33 as internal-only with no public or customer display
# rights. The repository is public, so their files are kept off git, in scratch
# (builder default /tmp/si_plan/quant/vendor_out), never committed or pushed
# (COO ruling 38 §2b). These tests fail if a site builder, template, rendered page
# or publish script names those files, or if the vendor sidecar loses its rights
# fields. The committed-sidecar test below skips while the file is absent.

ROOT = Path(__file__).resolve().parents[1]
MARKERS = ("vendor_internal_only", "breadth/history/internal_only")
SIDECAR = ROOT / "data/breadth/history/internal_only/vendor_internal_only_breadth_and_index_current.meta.json"


def _surface_files():
    out = list((ROOT / "scripts").glob("build_*.py"))
    out += [p for p in (ROOT / "scripts").glob("*.py") if "publish" in p.name or "sync" in p.name]
    for d in ("templates", "site"):
        base = ROOT / d
        if base.is_dir():
            out += [p for p in base.rglob("*") if p.is_file() and p.suffix in
                    {".py", ".j2", ".html", ".js", ".json", ".css", ".md", ".txt"}]
    return out


def test_no_display_surface_names_vendor_files():
    own = ROOT / "scripts/build_tree_breadth_and_index.py"   # the writer itself
    hits = []
    for p in _surface_files():
        if p == own:
            continue
        try:
            text = p.read_text(errors="ignore")
        except OSError:
            continue
        hits += [f"{p.relative_to(ROOT)}: {m}" for m in MARKERS if m in text]
    assert not hits, hits


def test_vendor_families_route_to_internal_set():
    rc = {f["family"]: f["rights_class"] for f in bt.FAMILIES}
    assert rc["subsector"] == rc["theme"] == "internal_only"
    assert rc["basket"] == rc["sector"] == "house"
    assert bt.RIGHTS_SETS["internal_only"]["dir"] == "internal_only"
    assert all(n.startswith("vendor_internal_only_")
               for k, n in bt.RIGHTS_SETS["internal_only"].items() if k not in ("dir", "prefix"))


def test_default_vendor_out_is_off_tree():
    # COO ruling 38 §2b: the repository is public; the vendor set is built to
    # scratch outside the repository tree and never committed.
    assert bt.VENDOR_OUT_DEFAULT.is_absolute()
    assert not bt.VENDOR_OUT_DEFAULT.is_relative_to(ROOT)


def test_rights_sentence_quotes_the_config_line():
    line = (ROOT / "config/theme_sources.yml").read_text().splitlines()[32]
    assert bt.VENDOR_RIGHTS["rights_source"] == "config/theme_sources.yml:33"
    assert bt.VENDOR_RIGHTS["rights_sentence"] in line


@pytest.mark.skipif(not SIDECAR.exists(), reason="data/ not materialised (sparse tree)")
def test_committed_vendor_sidecar_has_rights_fields():
    m = json.loads(SIDECAR.read_text())
    assert m["source_family"] == "finviz_themes"
    assert m["rights_class"] == "internal_only"
    assert m["rights_source"] == "config/theme_sources.yml:33"
    assert m["rights_sentence"] == bt.VENDOR_RIGHTS["rights_sentence"]
    assert set(m["families"]) == {"subsector", "theme"}


# --- GMI and relationship-hub registry export and the links tables (scripts/export_gmi_history_registry.py; COO rulings 31 s2, 32 s2, 34 s3) ---
# Kept in this registered file: a separate test file in the breadth step takes the
# build_free_content packing probe to 11 packs (measured 2026-11-12).
import yaml  # noqa: E402

from scripts import export_gmi_history_registry as ex  # noqa: E402

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
# The vendor files are kept off git, in scratch (public repository; COO ruling 38 §2b),
# so the internal_only entries are absent from the tree. Tests that read them skip;
# the house assertions still run wherever the house files are present.
_needs_vendor = pytest.mark.skipif(not LINK_FILES["internal_only"][0].exists(),
                                   reason="vendor files kept off git (public repo; COO ruling 38 §2b)")


def _link_files_present():
    return {rc: paths for rc, paths in LINK_FILES.items() if paths[0].exists()}


def _series():
    out = set()
    for _, ix_path in _link_files_present().values():
        ix = pd.read_parquet(ix_path, columns=["family", "group", "level"]).dropna(subset=["level"])
        out |= set(zip(ix.family, ix.group))
    return out


@_needs
def test_committed_links_have_no_tickers_and_match_index():
    series = _series()
    for rc, (path, _) in _link_files_present().items():
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
@_needs_vendor
def test_vendor_links_stay_with_vendor_files():
    vend = pd.read_parquet(LINK_FILES["internal_only"][0])
    assert ((vend.child_family.isin(ex.VENDOR_FAMILIES)) | (vend.parent_family.isin(ex.VENDOR_FAMILIES))).all()
    meta = json.loads(LINK_FILES["internal_only"][0].with_suffix(".meta.json").read_text())
    assert meta["source_family"] == "finviz_themes"
    # no subsector -> house theme rows without an exact key; the cause is stated in one sentence
    if meta["subsectors_matched_to_local_theme"] == 0:
        assert meta["subsector_to_theme_cause"] == ex.SUBSECTOR_THEME_CAUSE
        assert not ((vend.child_family == "subsector") & (vend.parent_family == "gmi_theme")).any()


@_needs
def test_house_links_contain_no_vendor_families():
    # House-side containment half of test_vendor_links_stay_with_vendor_files, moved out so it
    # runs without the off-tree vendor files (COO ruling 21:07Z). No new skip; nothing loosened.
    house = pd.read_parquet(LINK_FILES["house"][0])
    fam = set(house.child_family) | set(house.parent_family)
    assert not fam & set(ex.VENDOR_FAMILIES)


# A house sidecar carries vendor-fed fields as counts (integers), never as name lists: the
# vendor-family name list stays in the off-tree vendor sidecar (COO ruling 21:07Z).
VENDOR_COUNT_FIELDS = ("subsectors_total", "subsectors_matched_to_local_theme", "subsectors_unmatched")


@_needs
def test_house_sidecars_carry_vendor_counts_not_names():
    sidecars = [p for p in sorted(HIST.rglob("*.meta.json"))
                if "internal_only" not in p.parts and "vendor" not in p.name]
    assert sidecars
    checked = 0
    for p in sidecars:
        meta = json.loads(p.read_text())
        if meta.get("rights_class") == "internal_only":
            continue
        for k in VENDOR_COUNT_FIELDS:
            if k in meta:
                assert isinstance(meta[k], int) and not isinstance(meta[k], bool), (p.name, k)
                checked += 1
        for k, v in meta.items():
            if k.startswith("subsectors_"):
                assert not isinstance(v, list), (p.name, k)
    assert checked


@_needs
def test_overlap_rows_are_consistent():
    for path, _ in _link_files_present().values():
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
    assert meta["families"]["gmi_theme"]["label"].startswith("GMI house themes (18 themes, 15 with US-listed")
    assert meta["families"]["gmi_macro_category"]["label"].startswith(
        "GMI macro categories (10 macro categories, 7 with US-listed")
    assert meta["group_ids"] == bt.GROUP_ID_NOTE


@_needs
def test_topup_and_first_download_share_no_ticker():
    """COO 2026-11-12 09:39Z: no ticker has history from two downloads. The first download
    priced the registries of the families built before the top-up (subsector, theme, basket,
    sector); every top-up name must lie outside all of them and inside a family that needed it."""
    meta = json.loads((HIST / "house_breadth_and_index_current.meta.json").read_text())
    top = set(meta["price_topup"]["tickers"])
    assert len(top) == meta["price_topup"]["names"] == 4
    fams = bt.load_families(ROOT)
    first = set().union(*(set(m["ticker"]) for f, (_, m) in fams.items()
                          if not f.startswith(("gmi_", "rel_"))))
    assert not top & first, sorted(top & first)
    later = set().union(*(set(m["ticker"]) for f, (_, m) in fams.items()
                          if f.startswith(("gmi_", "rel_"))))
    assert top <= later


@_needs
def test_gmi_group_ids_are_graph_node_ids():
    reg = HIST / "registry"
    for f in ("gmi_theme", "gmi_macro_category"):
        ids = set(pd.read_csv(reg / f"{f}.csv")["group"])
        assert ids and all(i.startswith("theme:") for i in ids)
    assert "node ids, unchanged" in bt.GROUP_ID_NOTE


# ===========================================================================
# Regime inputs (COO ruling 36 s2) — scripts/build_regime_inputs.py
# Series only: group/universe numbers, no member ticker/row/price, no regime
# category / cutoff / score / signal, nothing related to outcomes.
# ===========================================================================
import re  # noqa: E402

from scripts import build_regime_inputs as rg  # noqa: E402

_REGIME_PQ = HIST / "regime_inputs_daily_current.parquet"
_REGIME_META = HIST / "regime_inputs_current.meta.json"
_REGIME_REPORT = ROOT / "research/breadth_history/REGIME_INPUTS_REPORT.md"
_regime_needs = pytest.mark.skipif(not _REGIME_PQ.exists(),
                                   reason="data/ not checked out (sparse tree)")
_FORBIDDEN = re.compile(r"\b(state|label|threshold|forward)\b", re.I)
# Domain abbreviations that collide with S&P member tickers but are not member
# references: EW = equal-weight, COO = the ruling authority. The real member-leak
# surface (parquet group/series columns and raw ticker lists) is checked exactly.
_TICKER_ABBREV = {"EW", "COO"}


def _regime_member_tickers() -> set:
    cons = pd.read_parquet(ROOT / "data/breadth/constituents.parquet")
    bmem = json.loads((ROOT / "data/baskets/membership.json").read_text())
    return (set(cons.index.astype(str))
            | {m["ticker"] for b in bmem["baskets"].values() for m in b["members"]})


def _regime_synth_root(tmp: Path, n=12, periods=700, start="2020-01-01"):
    """Small synthetic universe + baskets + ETFs for a network-free regime build."""
    rng = np.random.default_rng(11)
    idx = pd.bdate_range(start, periods=periods)
    r = rng.normal(0.0003, 0.01, size=(periods, n))
    closes = pd.DataFrame(100 * np.exp(np.cumsum(r, axis=0)), index=idx,
                          columns=[f"T{i:02d}" for i in range(n)])
    t = list(closes.columns)
    root = tmp / "root"
    (root / "data/breadth").mkdir(parents=True)
    (root / "data/baskets").mkdir(parents=True)
    pd.DataFrame({"sector": ["S1"] * (n // 2) + ["S2"] * (n - n // 2)}, index=t).to_parquet(
        root / "data/breadth/constituents.parquet")
    baskets = {b: {"members": [{"ticker": x, "removed": None} for x in ms]}
               for b, ms in (("ai_software", t[0:4]), ("non_ai_software", t[4:8]),
                             ("ai_semiconductors", t[8:12]))}
    (root / "data/baskets/membership.json").write_text(json.dumps({"baskets": baskets}))
    etf_dir = tmp / "etfs"; etf_dir.mkdir()
    rng2 = np.random.default_rng(12)
    for e in rg.ETFS:
        px = 100 * np.cumprod(1 + rng2.normal(0.0003, 0.01, size=len(closes)))
        pd.DataFrame({"close": px}, index=closes.index).to_parquet(etf_dir / f"{e}.parquet")
    cp = tmp / "closes.parquet"; closes.to_parquet(cp)
    dm = tmp / "dm.json"; dm.write_text(json.dumps({"vintage": "synthetic-v1"}))
    return closes, root, etf_dir, cp, dm


# ---- synthetic: one test per statistic -------------------------------------
def test_regime_return_conventions():
    idx = pd.bdate_range("2020-01-01", periods=6)
    closes = pd.DataFrame({"A": [100, 101, np.nan, 103, 104, 105],
                           "B": [100, 100, 100, 100, 100, 100]}, index=idx)
    dr = rg.daily_returns(closes)
    assert np.isnan(dr["A"].iloc[2]) and np.isnan(dr["A"].iloc[3])  # both endpoints needed
    assert dr["B"].iloc[1] == 0.0
    wr = rg.window_return(closes, 2)
    assert abs(wr["A"].iloc[3] - (103 / 101 - 1)) < 1e-12  # t-2 = idx 1 is valid
    assert np.isnan(wr["A"].iloc[4])            # t-2 = idx 2 is NaN
    assert abs(wr["A"].iloc[5] - (105 / 103 - 1)) < 1e-12


def test_regime_ew_level_held_matches_house_convention(tmp_path):
    closes, *_ = _regime_synth_root(tmp_path, n=8, periods=400)
    rets = rg.daily_returns(closes)
    priced = closes.notna()
    members = list(closes.columns[:5])
    held = pd.DataFrame(False, index=closes.index, columns=closes.columns)
    held[members] = True
    start = pd.Timestamp("2020-06-01")
    lvl, n = rg.ew_level_held(rets, priced, held, start)
    ref_lvl, ref_n, _ = bt.group_index(rets, members, start, priced=priced)
    pd.testing.assert_series_equal(lvl, ref_lvl, check_names=False)
    pd.testing.assert_series_equal(n, ref_n, check_names=False)


def test_regime_rebased_ratio():
    idx = pd.bdate_range("2020-01-01", periods=5)
    num = pd.Series([np.nan, 2.0, 4.0, 6.0, 8.0], index=idx)
    den = pd.Series([1.0, 1.0, 2.0, 3.0, 4.0], index=idx)
    r = rg.rebased_ratio(num, den)
    assert r.index[0] == idx[1]                 # first session both valid
    assert r.iloc[0] == 100.0
    assert abs(r.iloc[-1] - 100.0 * (8.0 / 4.0) / (2.0 / 1.0)) < 1e-12


def test_regime_universe_breadth():
    idx = pd.bdate_range("2020-01-01", periods=300)
    up = np.linspace(100, 200, 300)
    dn = np.linspace(200, 100, 300)
    closes = pd.DataFrame({"A": up, "B": up, "C": dn, "D": dn}, index=idx)
    out, ns = rg.universe_breadth(closes, pd.Timestamp("2020-01-01"))
    last = idx[-1]
    assert out["pct_above_50"].loc[last] == 50.0      # 2 of 4 above
    assert out["n_above_50"].loc[last] == 2.0
    assert ns["pct_above_50"].loc[last] == 4.0
    assert out["diff_pct_above_50_21d"].loc[last] == 0.0
    assert out["new_highs_252"].loc[last] == 2.0
    assert out["new_lows_252"].loc[last] == 2.0
    assert out["nh_nl_252"].loc[last] == 0.0
    assert out["n_counted_nh"].loc[last] == 4.0


def test_regime_dispersion(tmp_path):
    closes, root, *_ = _regime_synth_root(tmp_path, n=12, periods=400)
    sectors = {g: sorted(m["ticker"].tolist()) for g, m in
               bt.sector_membership(root / "data/breadth/constituents.parquet").groupby("group")}
    start = pd.Timestamp("2020-01-01")
    got = rg.dispersion(closes, sectors, start)
    r21 = rg.window_return(closes, 21)
    exp = r21.std(axis=1, ddof=1) * 100.0
    v, n = got["dispersion_21d"]["universe"]
    pd.testing.assert_series_equal(v, exp.where(n >= bt.BREADTH_FLOOR), check_names=False)
    assert (n == r21.notna().sum(axis=1)).all()
    for g, members in sectors.items():
        vg, ng = got["dispersion_21d"][g]
        expg = r21[members].std(axis=1, ddof=1) * 100.0
        pd.testing.assert_series_equal(vg, expg.where(ng >= bt.BREADTH_FLOOR), check_names=False)


def test_regime_sector_dispersion(tmp_path):
    closes, root, *_ = _regime_synth_root(tmp_path, n=12, periods=400)
    sectors = {g: sorted(m["ticker"].tolist()) for g, m in
               bt.sector_membership(root / "data/breadth/constituents.parquet").groupby("group")}
    start = pd.Timestamp("2020-01-01")
    levels = rg.ew_levels(closes, sectors, start)
    got = rg.sector_dispersion(levels, sorted(sectors), start)
    names = sorted(sectors)
    rk = pd.DataFrame({g: rg.window_return(levels[g][0].to_frame("l"), 21)["l"] for g in names})
    exp = rk.std(axis=1, ddof=1) * 100.0
    v, n = got["sector_dispersion_21d"]
    pd.testing.assert_series_equal(v, exp.where(n >= bt.BREADTH_FLOOR), check_names=False)
    assert (n == rk.notna().sum(axis=1)).all()


def test_regime_leadership():
    idx = pd.bdate_range("2020-01-01", periods=200)
    up = np.linspace(100, 200, 200)
    dn = np.linspace(200, 100, 200)
    closes = pd.DataFrame({"A": up, "B": up, "C": dn, "D": dn}, index=idx)
    ew = pd.Series(100.0, index=idx)                 # flat index: 0 window return
    out, ns = rg.leadership(closes, ew, pd.Timestamp("2020-01-01"))
    last = idx[-1]
    assert out["pct_beat_ew_63d"].loc[last] == 50.0   # the 2 rising members beat 0
    assert out["n_beat_ew_63d"].loc[last] == 2.0
    assert ns["pct_beat_ew_63d"].loc[last] == 4.0


def test_regime_month_end_betas():
    idx = pd.bdate_range("2020-01-01", periods=300)
    rng = np.random.default_rng(0)
    s = rng.normal(0, 0.01, 300)
    mrets = pd.DataFrame({"A": 2.0 * s, "B": 0.5 * s}, index=idx)
    sret = pd.Series(s, index=idx)
    month_ends = pd.Series(idx, index=idx.to_period("M")).groupby(level=0).max()
    betas = rg.month_end_betas(mrets, sret, month_ends)
    last = betas[max(betas)]
    assert abs(last["A"] - 2.0) < 1e-9 and abs(last["B"] - 0.5) < 1e-9
    # month ends without a full trailing window are skipped, not estimated
    assert all(list(idx).index(t) + 1 >= rg.BETA_WINDOW for t in
               [month_ends[p] for p in betas])


def test_regime_high_beta_cohorts():
    idx = pd.bdate_range("2020-01-01", periods=700)
    rng = np.random.default_rng(3)
    s = rng.normal(0.0003, 0.01, 700)
    spy = pd.Series(100 * np.cumprod(1 + s), index=idx)
    betas = np.linspace(0.5, 1.5, 10)
    closes = pd.DataFrame({f"T{i:02d}": 100 * np.cumprod(1 + b * s)
                           for i, b in enumerate(betas)}, index=idx)
    lvl, n, facts = rg.high_beta_cohorts(closes, spy, pd.Timestamp("2021-06-01"))
    assert facts["cohort_size_max"] == 2            # ceil(10 / 5)
    assert facts["months_selected"] > 0
    valid = lvl.dropna()
    assert len(valid) and (n.loc[valid.index] >= bt.INDEX_FLOOR).all()


def test_regime_full_synthetic_build(tmp_path):
    closes, root, etf_dir, cp, dm = _regime_synth_root(tmp_path)
    meta = rg.build(cp, dm, tmp_path / "out", root=root, etf_dir=etf_dir, start="2021-06-01")
    df = pd.read_parquet(tmp_path / "out/regime_inputs_daily_current.parquet")
    assert list(df.columns) == ["date", "series", "group", "value", "n", "kind"]
    assert set(df.kind) <= set(rg.KINDS)
    assert (df.n >= 2).all() and not df.isna().any().any()
    assert df.date.min() >= pd.Timestamp("2021-06-01")
    assert not df.duplicated(["series", "group", "date"]).any()
    rel = [s for s in df.series.unique() if s.startswith("rel_")]
    assert len(rel) == 15                            # 5 numerators x 3 denominators
    for s in ("ew_vs_spy", "rsp_vs_spy", "rel_igv_vs_ew_universe"):
        v = df[df.series == s].sort_values("date").value
        assert abs(v.iloc[0] - 100.0) < 1e-9          # rebased to 100
    assert "computed" in set(df[df.series == "ew_index"].kind)
    assert not _FORBIDDEN.search(json.dumps(meta))
    for s, entry in meta["series"].items():
        assert {"definition", "first_date", "source", "basis", "kind", "gaps"} <= set(entry)


# ---- committed artifacts (skipped on a sparse tree without data/) ----------
@_regime_needs
def test_regime_committed_columns_kinds_floors():
    df = pd.read_parquet(_REGIME_PQ)
    assert list(df.columns) == ["date", "series", "group", "value", "n", "kind"]
    assert not any("ticker" in c or "price" in c for c in df.columns)
    assert set(df.kind) <= set(rg.KINDS)
    assert (df.n >= 2).all() and not df.isna().any().any()
    assert df.date.min() >= pd.Timestamp(rg.START)
    assert not df.duplicated(["series", "group", "date"]).any()
    tickers = _regime_member_tickers()
    assert not (set(df.group) & tickers) and not (set(df.series) & tickers)


@_regime_needs
def test_regime_committed_no_forbidden_words():
    df = pd.read_parquet(_REGIME_PQ, columns=["series", "group"])
    assert not _FORBIDDEN.search(" ".join(df.series.unique()) + " " + " ".join(df.group.unique()))
    assert not _FORBIDDEN.search(_REGIME_META.read_text())
    assert not _FORBIDDEN.search(_REGIME_REPORT.read_text())


@_regime_needs
def test_regime_committed_sidecar_consistency():
    df = pd.read_parquet(_REGIME_PQ)
    meta = json.loads(_REGIME_META.read_text())
    assert _REGIME_META.stat().st_size < 40_000
    firsts = df.groupby("series").date.min()
    kinds = df.groupby("series").kind.agg(lambda s: sorted(set(s)))
    assert set(meta["series"]) == set(df.series.unique())
    for s, entry in meta["series"].items():
        assert {"definition", "first_date", "source", "basis", "kind", "gaps"} <= set(entry)
        assert entry["first_date"] == str(firsts[s].date())
        ek = entry["kind"] if isinstance(entry["kind"], list) else [entry["kind"]]
        assert sorted(ek) == kinds[s]
        assert len(entry["gaps"].split("; ")) <= 3
        assert "groups" not in entry and "rows" not in entry   # no per-date/per-ticker lists
    assert meta["no_outcomes"] and not _FORBIDDEN.search(meta["no_outcomes"])
    assert "series" not in meta["rates_credit_dollar_on_main"]  # census list lives in the report
    tickers = _regime_member_tickers() - _TICKER_ABBREV
    report = _REGIME_REPORT.read_text()
    table_part = report.split("## Rates, credit and dollar on main")[0]
    # The census section is a read-only inventory of macro series already on main;
    # its FRED ids (e.g. IR, CI) legitimately collide with member tickers and are
    # not member references. The regime-series surfaces are checked exactly.
    prose = _REGIME_META.read_text() + table_part
    hits = {t for t in tickers if len(t) >= 2 and re.search(r"\b" + re.escape(t) + r"\b", prose)}
    assert not hits, sorted(hits)
    assert len(table_part.encode()) < 15_000
