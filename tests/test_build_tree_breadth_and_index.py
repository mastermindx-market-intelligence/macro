"""Network-free tests for scripts/build_tree_breadth_and_index.py (synthetic registries)."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from scripts import build_tree_breadth_and_index as bt
from scripts import build_vendor_subsector_index as bv


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


# ===========================================================================
# Group price indexes (COO ruling 38 Part B) — house sectors + baskets.
# Reuses engine.baskets._ew_level and build_tree_breadth_and_index.group_index
# with a floor of 5 priced members. Group-level numbers and counts only: no
# member ticker, price or per-security date in the committed files.
# ===========================================================================
import hashlib  # noqa: E402

from engine.baskets import _ew_level  # noqa: E402
from engine.neuralweb.sector_map import GICS_TO_ETF  # noqa: E402

GI_DATED = HIST / "group_index_daily_dated.parquet"
GI_SENS = HIST / "group_index_daily_current_sensitivity.parquet"
GI_META = HIST / "group_index.meta.json"
GI_KEYMAP = HIST / "group_index_key_map.csv"
GI_REPORT = ROOT / "research/breadth_history/GROUP_INDEX_REPORT.md"
GI_FLOOR = 5
_GI_COLS = ["date", "level", "group", "index", "n_priced_members", "membership_basis"]
_GI_ABBREV = {"EW", "COO"}   # equal-weight / ruling authority, not member references
_gi_needs = pytest.mark.skipif(not GI_DATED.exists(),
                               reason="data/ not checked out (sparse tree)")


def _gi_member_tickers() -> set:
    cons = pd.read_parquet(ROOT / "data/breadth/constituents.parquet")
    bmem = json.loads((ROOT / "data/baskets/membership.json").read_text())
    return (set(cons.index.astype(str))
            | {m["ticker"] for b in bmem["baskets"].values() for m in b["members"]})


# ---- synthetic: EW convention, floor of 5, dated window --------------------
def test_group_index_ew_matches_manual_cumprod():
    closes = _closes(6, start="1999-01-01", periods=400)
    start = pd.Timestamp("2000-01-03")
    rets = closes.pct_change(fill_method=None).where(closes.notna() & closes.shift(1).notna())
    members = list(closes.columns)
    lvl, n, reason = bt.group_index(rets, members, start, floor=GI_FLOOR, priced=closes.notna())
    r = closes[members].pct_change().loc[start:].mean(axis=1)
    exp = (1 + r.fillna(0)).cumprod()
    assert np.allclose(lvl.loc[start:].values, exp.round(6).values, atol=2e-6)
    assert (n.loc[start:] == 6).all()
    assert reason.loc[start:].isna().all()
    assert lvl.loc[:start].iloc[:-1].isna().all()        # blank before the start gate


def test_group_index_floor_of_5_blanks_below_floor():
    closes = _closes(6, start="2000-01-03", periods=300)
    closes.iloc[100:110, :2] = np.nan                    # 4 priced -> below floor of 5
    rets = closes.pct_change(fill_method=None).where(closes.notna() & closes.shift(1).notna())
    lvl, n, reason = bt.group_index(rets, list(closes.columns), pd.Timestamp("2000-01-03"),
                                    floor=GI_FLOOR, priced=closes.notna())
    assert (n.iloc[100:110] == 4).all() and n.iloc[110] == 6   # floor counts closes, not returns
    assert lvl.iloc[100:110].isna().all()
    assert (reason.iloc[100:110] == bt.REASON_FLOOR).all()
    assert lvl.iloc[110:].notna().all() and lvl.iloc[99] > 0
    closes.iloc[120:130, :1] = np.nan                    # exactly 5 priced -> at the floor
    rets2 = closes.pct_change(fill_method=None).where(closes.notna() & closes.shift(1).notna())
    lvl2, n2, _ = bt.group_index(rets2, list(closes.columns), pd.Timestamp("2000-01-03"),
                                 floor=GI_FLOOR, priced=closes.notna())
    assert (n2.iloc[120:130] == 5).all() and lvl2.iloc[120:130].notna().all()


def test_group_index_dated_window_added_member_not_counted_early():
    idx = pd.bdate_range("2000-01-03", periods=12)
    closes = pd.DataFrame({f"T{i}": 100 * np.cumprod(1 + np.random.default_rng(i).normal(0.0003, 0.01, 12))
                           for i in range(4)}, index=idx)
    rets = closes.pct_change(fill_method=None).where(closes.notna() & closes.shift(1).notna())
    base = [{"ticker": f"T{i}", "added": "2000-01-03", "removed": None} for i in range(3)]
    late = base + [{"ticker": "T3", "added": str(idx[6].date()), "removed": None}]
    lvl_base = _ew_level(rets, base, idx)
    lvl_late = _ew_level(rets, late, idx)
    # before T3's added date both rosters have the same active members -> identical level
    assert np.allclose(lvl_base.loc[idx[1]:idx[5]].values, lvl_late.loc[idx[1]:idx[5]].values, atol=1e-9)
    # once added, the fourth member changes the equal-weight return -> levels diverge
    assert not np.allclose(lvl_base.loc[idx[8]:].values, lvl_late.loc[idx[8]:].values)


# ---- committed artifacts (skipped on a sparse tree without data/) ----------
@_gi_needs
def test_group_index_committed_columns_and_no_ticker_column():
    tickers = _gi_member_tickers() - _GI_ABBREV
    for p in (GI_DATED, GI_SENS):
        df = pd.read_parquet(p)
        assert list(df.columns) == _GI_COLS
        assert not any("ticker" in c for c in df.columns)   # n_priced_members is a count, not a price
        assert pd.api.types.is_integer_dtype(df["n_priced_members"])
        assert not df.duplicated(["level", "group", "date"]).any()
        assert not (set(df.group) & tickers)


@_gi_needs
def test_group_index_committed_floor_and_basis():
    dated = pd.read_parquet(GI_DATED)
    sens = pd.read_parquet(GI_SENS)
    assert set(dated.level) == {"sector"}
    assert dated.membership_basis.unique().tolist() == ["reconstructed_dated_membership"]
    assert set(sens.level) == {"sector", "basket"}
    assert sens.membership_basis.unique().tolist() == ["reconstructed_current_membership"]
    for df in (dated, sens):
        assert (df["index"].notna() == (df["n_priced_members"] >= GI_FLOOR)).all()
    meta = json.loads(GI_META.read_text())
    assert meta["files"]["group_index_daily_current_sensitivity.parquet"]["sensitivity"] is True
    assert meta["levels"]["basket"]["dated"] is False
    assert meta["index"]["floor"] == GI_FLOOR


@_gi_needs
def test_group_index_key_map_one_row_per_key():
    km = pd.read_csv(GI_KEYMAP, keep_default_na=False)
    assert list(km.columns) == ["group_key", "level", "engine_key", "spdr_parent"]
    assert len(km) == km.group_key.nunique()
    assert (km.spdr_parent == "").all()
    dated = pd.read_parquet(GI_DATED, columns=["level", "group"])
    sens = pd.read_parquet(GI_SENS, columns=["level", "group"])
    keys = set(zip(dated.level, dated.group)) | set(zip(sens.level, sens.group))
    assert set(zip(km.level, km.group_key)) == keys
    sec = km[km.level == "sector"]
    assert set(sec.engine_key) == set(GICS_TO_ETF.values())      # SPDR tickers, from the code map
    for r in sec.itertuples(index=False):
        assert GICS_TO_ETF[r.group_key] == r.engine_key
    bk = km[km.level == "basket"]
    assert (bk.engine_key == bk.group_key).all()                 # basket id is the organ key


@_regime_needs
def test_group_index_regime_files_frozen():
    assert hashlib.sha256((HIST / "regime_inputs_daily_current.parquet").read_bytes()).hexdigest() == \
        "c15d5c2d533ae7d66dd84a67c8c1abfa19457aa44fcd1e8504d00bc0c9348177"
    assert hashlib.sha256((HIST / "regime_inputs_current.meta.json").read_bytes()).hexdigest() == \
        "552260044b01a67b6a5aed0a30dee52db634c77dd100fb7726d5f282cf0f634d"


@_gi_needs
def test_group_index_committed_sidecar_and_report_clean():
    meta_text = GI_META.read_text()
    report = GI_REPORT.read_text()
    assert not _FORBIDDEN.search(meta_text)
    assert not _FORBIDDEN.search(report)
    tickers = _gi_member_tickers() - _GI_ABBREV
    for text in (meta_text, report):
        hits = {t for t in tickers if len(t) >= 2 and re.search(r"\b" + re.escape(t) + r"\b", text)}
        assert not hits, sorted(hits)
    meta = json.loads(meta_text)
    dated = pd.read_parquet(GI_DATED)
    fv = meta["levels"]["sector"]["dated"]["first_valid_index"]
    for g, sub in dated.groupby("group"):
        v = sub.dropna(subset=["index"])
        assert fv[g] == (str(v["date"].min().date()) if len(v) else None)


# ---- vendor subsector index (COO ruling 38 s2b) -------------------------------
# The repository is public: the vendor builder writes only outside the tree and its
# tests use a made-up fixture group, never a vendor name. No vendor data is committed.
def _vendor_fixture_mem() -> pd.DataFrame:
    rows = [{"ticker": f"T{i:02d}", "group": "fixture_group_a"} for i in range(6)]   # 6 -> reaches floor
    rows += [{"ticker": f"T{i:02d}", "group": "fixture_group_b"} for i in range(6, 9)]  # 3 -> below floor
    return pd.DataFrame(rows, columns=["ticker", "group"])


def test_vendor_index_fixture_floor_and_rights():
    closes = _closes(12, start="1999-01-01", periods=400)
    mem = _vendor_fixture_mem()
    engine_keys = {"fixture_group_a", "fixture_group_b", "fixture_store_only"}
    start = pd.Timestamp("2000-01-01")
    df, km, counts = bv.build_index(closes, mem, engine_keys, start)
    assert list(df.columns) == bv.COLS
    assert (df["level"] == "subsector").all()
    assert (df["rights_class"] == "internal_only").all()           # rights on every row
    assert (df["membership_basis"] == "reconstructed_current_membership").all()
    assert pd.api.types.is_integer_dtype(df["n_priced_members"])
    assert (df["index"].notna() == (df["n_priced_members"] >= 5)).all()
    assert df["date"].min() >= start
    assert set(df.group) == {"fixture_group_a", "fixture_group_b"}  # store-only key not built
    a = df[df.group == "fixture_group_a"]
    b = df[df.group == "fixture_group_b"]
    assert a["index"].notna().any() and not b["index"].notna().any()
    assert counts["built_keys"] == 2
    assert counts["store_only_keys"] == 1 and counts["family_only_keys"] == 0
    assert counts["groups_reaching_floor"] == 1
    assert counts["groups_below_floor_throughout"] == 1
    assert list(km.columns) == ["group_key", "level", "engine_key", "spdr_parent"]
    assert (km.engine_key == km.group_key).all() and (km.spdr_parent == "").all()
    assert set(km.group_key) == {"fixture_group_a", "fixture_group_b"}


def test_vendor_index_family_only_key_not_built():
    closes = _closes(12, start="1999-01-01", periods=400)
    mem = _vendor_fixture_mem()
    df, km, counts = bv.build_index(closes, mem, {"fixture_group_a"}, pd.Timestamp("2000-01-01"))
    assert set(df.group) == {"fixture_group_a"}
    assert counts["built_keys"] == 1
    assert counts["family_only_keys"] == 1 and counts["store_only_keys"] == 0


def test_vendor_guard_refuses_in_tree(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    with pytest.raises(ValueError):
        bv.guard_out(root / "data/breadth/history", root)
    with pytest.raises(ValueError):
        bv.guard_out(root, root)
    out = tmp_path / "outside"                       # sibling of the repo, not under it
    assert bv.guard_out(out, root) == out.resolve()


def test_vendor_default_out_is_out_of_tree():
    assert bv.DEFAULT_OUT == Path("/tmp/r38b/vendor_out")
    assert ROOT not in bv.DEFAULT_OUT.resolve().parents


def test_vendor_write_outputs_out_of_tree(tmp_path):
    closes = _closes(12, start="1999-01-01", periods=400)
    mem = _vendor_fixture_mem()
    start = pd.Timestamp("2000-01-01")
    df, km, counts = bv.build_index(closes, mem, {"fixture_group_a", "fixture_group_b"}, start)
    root = tmp_path / "repo"
    root.mkdir()
    out = tmp_path / "vendor_out"
    meta = bv.write_outputs(df, km, counts, out, root, {"vintage": "fixture", "topup": None}, start)
    for name in (bv.OUT_INDEX, bv.OUT_META, bv.OUT_KEYMAP):
        assert (out / name).exists()
    assert meta["rights_class"] == "internal_only"
    assert meta["rights_sentence"] == bt.VENDOR_RIGHTS["rights_sentence"]
    assert meta["use"] == bt.VENDOR_RIGHTS["use"]
    assert meta["rights_source"] == "config/theme_sources.yml:33"
    assert meta["sensitivity"] is True and meta["floor"] == 5
    assert not list(root.rglob("*"))                 # nothing written under the repo root
    back = pd.read_parquet(out / bv.OUT_INDEX)
    assert (back["rights_class"] == "internal_only").all()


def test_vendor_builder_source_names_no_vendor_file():
    src = (ROOT / "scripts/build_vendor_subsector_index.py").read_text()
    for m in MARKERS:                                # derives names from the rights prefix
        assert m not in src


def test_vendor_cli_refuses_in_tree_out(tmp_path, monkeypatch):
    """COO ruling 38 continuation A: the builder CLI exits non-zero with a clear message
    when --out is inside the repository tree, using a made-up fixture group."""
    import sys  # noqa: E402
    root = tmp_path / "repo"
    root.mkdir()
    closes = _closes(12, start="1999-01-01", periods=400)
    cp = tmp_path / "closes.parquet"; closes.to_parquet(cp)
    dm = tmp_path / "dm.json"; dm.write_text(json.dumps({"vintage": "fixture"}))
    tree = tmp_path / "tree.json"
    tree.write_text(json.dumps([{"theme": "Fixture", "key": "fixture_theme", "subsectors": [
        {"key": "fixture_group_a", "members": list(closes.columns[:6])}]}]))
    state = tmp_path / "state.json"; state.write_text(json.dumps({"fixture_group_a": {}}))
    monkeypatch.setattr(sys, "argv", ["build_vendor_subsector_index.py",
                                      "--closes", str(cp), "--download-meta", str(dm),
                                      "--tree", str(tree), "--state", str(state),
                                      "--root", str(root),
                                      "--out", str(root / "data/breadth/history")])
    with pytest.raises(SystemExit) as ei:
        bv.main()
    assert ei.value.code not in (0, None)
    assert not list(root.rglob("*"))                 # refused before writing anything


# ---- continuation fixes (ruling 38 Part B): dated baskets, dated sp400/sp600 ----
# New files only; the four existing group_index files stay byte-frozen. The dated
# basket index uses the engine's [added, removed) inclusion windows from
# data/baskets/membership.json (seed 2023-05-09); the sp400/sp600 sector indexes are
# built per universe and never pooled with sp500.
GI_BK_DATED = HIST / "group_index_basket_daily_dated.parquet"
GI_BK_META = HIST / "group_index_basket_daily_dated.meta.json"
GI_SP_EXT = HIST / "group_index_daily_dated_sp400_sp600.parquet"
GI_SP_META = HIST / "group_index_daily_dated_sp400_sp600.meta.json"
_gi_ext_needs = pytest.mark.skipif(not GI_BK_DATED.exists(),
                                   reason="data/ not checked out (sparse tree)")


def test_basket_dated_window_counts_only_inside_window():
    """Synthetic: the dated basket method (engine.baskets._ew_level) counts a member only
    on sessions inside [added, removed): a late entrant joins at added, and a removed
    member stops counting ON the removed date."""
    idx = pd.bdate_range("2024-01-01", periods=30)
    closes = pd.DataFrame({f"T{i}": 100 * np.cumprod(
        1 + np.random.default_rng(i).normal(0.0003, 0.01, 30)) for i in range(6)}, index=idx)
    rets = closes.pct_change(fill_method=None).where(closes.notna() & closes.shift(1).notna())
    base = [f"T{i}" for i in range(4)]
    roster = [{"ticker": t, "added": str(idx[0].date()), "removed": None} for t in base]
    roster.append({"ticker": "T4", "added": str(idx[10].date()), "removed": None})
    roster.append({"ticker": "T5", "added": str(idx[0].date()), "removed": str(idx[15].date())})
    lvl = _ew_level(rets, roster, idx)
    assert np.isnan(lvl.iloc[0])                       # no return on the first session
    r = lvl.pct_change()
    # T5 is active from idx[0] until removed (exclusive) at idx[15]; T4 joins at idx[10].
    assert np.allclose(r.iloc[2:10].values,
                       rets[base + ["T5"]].iloc[2:10].mean(axis=1).values, atol=1e-12)
    assert np.allclose(r.iloc[10:15].values,
                       rets[base + ["T4", "T5"]].iloc[10:15].mean(axis=1).values, atol=1e-12)
    assert np.allclose(r.iloc[15:].values,
                       rets[base + ["T4"]].iloc[15:].mean(axis=1).values, atol=1e-12)
    # a late entrant never changes history before its added date
    no_late = _ew_level(rets, [m for m in roster if m["ticker"] != "T4"], idx)
    assert np.allclose(lvl.iloc[:10].values, no_late.iloc[:10].values,
                       atol=1e-12, equal_nan=True)


@_gi_ext_needs
def test_basket_dated_committed_window_bound_and_floor():
    df = pd.read_parquet(GI_BK_DATED)
    assert list(df.columns) == _GI_COLS
    assert set(df.level) == {"basket"}
    assert df.membership_basis.unique().tolist() == ["reconstructed_dated_membership"]
    assert (df["index"].notna() == (df.n_priced_members >= GI_FLOOR)).all()
    assert str(df.date.min().date()) == "2023-05-09"   # dated basket membership starts at the seed
    assert df.group.nunique() == 49
    assert pd.api.types.is_integer_dtype(df.n_priced_members)
    assert not df.duplicated(["level", "group", "date"]).any()
    # Repo-only window bound: the priced count can never exceed the number of members
    # whose recorded [added, removed) window covers the session (prices only lower it).
    doc = json.loads((ROOT / "data/baskets/membership.json").read_text())
    dates = pd.DatetimeIndex(df.date.drop_duplicates().sort_values())
    for bid, b in doc["baskets"].items():
        cap = pd.Series(0, index=dates)
        for m in b["members"]:
            w = dates >= pd.Timestamp(m["added"])
            if m.get("removed"):
                w = w & (dates < pd.Timestamp(m["removed"]))
            cap = cap + w.astype(int)
        n = df[df.group == bid].set_index("date").n_priced_members.reindex(dates)
        assert (n <= cap).all(), bid


@_gi_ext_needs
def test_group_index_extension_no_ticker():
    tickers = _gi_member_tickers() - _GI_ABBREV
    bk = pd.read_parquet(GI_BK_DATED)
    sp = pd.read_parquet(GI_SP_EXT)
    assert list(sp.columns) == _GI_COLS + ["index_universe"]
    for df in (bk, sp):
        assert not any("ticker" in c for c in df.columns)
        assert not (set(df.group) & tickers)
    assert set(sp[sp.index_universe == "sp400"].group) == set(GICS_TO_ETF)
    assert set(sp[sp.index_universe == "sp600"].group) == set(GICS_TO_ETF)
    for p in (GI_BK_META, GI_SP_META):
        text = p.read_text()
        assert not _FORBIDDEN.search(text)
        hits = {t for t in tickers if len(t) >= 2 and re.search(r"\b" + re.escape(t) + r"\b", text)}
        assert not hits, sorted(hits)


@_gi_ext_needs
def test_group_index_extension_floor_basis_and_separation():
    sp = pd.read_parquet(GI_SP_EXT)
    assert set(sp.level) == {"sector"}
    assert sp.membership_basis.unique().tolist() == ["reconstructed_dated_membership"]
    assert set(sp.index_universe) == {"sp400", "sp600"}
    assert (sp["index"].notna() == (sp.n_priced_members >= GI_FLOOR)).all()
    assert not sp.duplicated(["level", "group", "date", "index_universe"]).any()
    assert str(sp[sp.index_universe == "sp400"].date.min().date()) == "2012-01-13"
    assert str(sp[sp.index_universe == "sp600"].date.min().date()) == "2019-12-17"
    sm = json.loads(GI_SP_META.read_text())
    assert sm["never_pooled"] == "The S&P 500, 400 and 600 indexes are never pooled."
    bm = json.loads(GI_BK_META.read_text())
    assert bm["dated_membership_start"] == "2023-05-09"
    assert bm["index"]["floor"] == GI_FLOOR and sm["index"]["floor"] == GI_FLOOR


@_gi_ext_needs
def test_group_index_extension_sidecars_consistent():
    bk = pd.read_parquet(GI_BK_DATED)
    bm = json.loads(GI_BK_META.read_text())
    for g, sub in bk.groupby("group"):
        v = sub.dropna(subset=["index"])
        assert bm["first_valid_index"][g] == (str(v.date.min().date()) if len(v) else None)
        assert bm["n_priced_at_last_date"][g] == int(sub.loc[sub.date.idxmax(), "n_priced_members"])
        assert bm["below_floor_sessions_per_basket"][g] == int((sub.n_priced_members < GI_FLOOR).sum())
    sp = pd.read_parquet(GI_SP_EXT)
    sm = json.loads(GI_SP_META.read_text())
    for src in ("sp400", "sp600"):
        u = sp[sp.index_universe == src]
        um = sm["universes"][src]
        assert um["rows"] == len(u)
        for g, sub in u.groupby("group"):
            v = sub.dropna(subset=["index"])
            assert um["first_valid_index"][g] == (str(v.date.min().date()) if len(v) else None)
            assert um["n_priced_at_last_date"][g] == int(sub.loc[sub.date.idxmax(), "n_priced_members"])


@_gi_needs
def test_group_index_key_map_house_only():
    """COO continuation B: the committed key map stays HOUSE ONLY — exactly 11 sector and
    49 basket rows; the extension files add no new key (levels stay sector and basket)."""
    km = pd.read_csv(GI_KEYMAP, keep_default_na=False)
    assert len(km) == 60
    assert km.level.value_counts().to_dict() == {"basket": 49, "sector": 11}
    if GI_BK_DATED.exists():
        bk = pd.read_parquet(GI_BK_DATED, columns=["level", "group"])
        sp = pd.read_parquet(GI_SP_EXT, columns=["level", "group"])
        keys = set(zip(km.level, km.group_key))
        assert set(zip(bk.level, bk.group)) <= keys
        assert set(zip(sp.level, sp.group)) <= keys


@_gi_needs
def test_group_index_existing_files_frozen():
    """COO continuation D: the four existing group_index files keep their exact bytes from
    ac0da85fadab861477c23d107eaa62033fcc06a0; the extension adds new files only."""
    frozen = {
        "group_index.meta.json":
            "5a22beeb1e09b0bb618913de1cafc8043a21ff5f9a9e59815733b3bd535e02da",
        "group_index_daily_current_sensitivity.parquet":
            "1116577f3fb10a7fe9f9da534c9726fa63009ccd3c6496c30229a87be0514fba",
        "group_index_daily_dated.parquet":
            "27a4420e0c990fb97486a3e2829e6e3580f5f199a3267ba2d09731f68ebea6e3",
        "group_index_key_map.csv":
            "b34de4871aac30c0e26c1735092163f88d77867bfe0944e7700866d85f1b7de2",
    }
    for name, h in frozen.items():
        assert hashlib.sha256((HIST / name).read_bytes()).hexdigest() == h, name


# ---- in-repo house builder (#11171 reproducibility) ---------------------------
# scripts/build_group_index_house.py is the committed producer of the eight house
# group-index files. The fixture tests run its core functions on made-up tickers
# and prices only (no real ticker, no archive data). The value-equality test
# rebuilds every committed file from the real price inputs named by the
# GROUP_INDEX_* environment variables and skips cleanly when those inputs (or
# the committed data/ files) are absent, e.g. in CI or on a sparse tree.
import os  # noqa: E402

from scripts import build_group_index_house as bh  # noqa: E402


def test_house_builder_three_group_fixture():
    """Core functions on a 3-group made-up fixture: dated [start, end) windows,
    the floor of 5, the EW level convention, frame columns and the first-date
    census. Every ticker and price here is synthetic."""
    idx = pd.bdate_range("2001-01-01", periods=120)
    rng = np.random.default_rng(11)
    tickers = [f"FAKE{i:02d}" for i in range(1, 19)]
    closes = pd.DataFrame(
        100 * np.exp(np.cumsum(rng.normal(0.0003, 0.01, size=(120, 18)), axis=0)),
        index=idx, columns=tickers)
    # fixture_grp_a: six members over the whole span.
    # fixture_grp_b: FAKE12 joins at session 30; FAKE11 is removed AT session 60.
    # fixture_grp_c: only four in-window members until session 40 (below floor).
    rows = [{"ticker": t, "group": "fixture_grp_a", "start_date": idx[0], "end_date": pd.NaT}
            for t in tickers[0:6]]
    rows += [{"ticker": t, "group": "fixture_grp_b", "start_date": idx[0], "end_date": pd.NaT}
             for t in tickers[6:10]]
    rows.append({"ticker": tickers[10], "group": "fixture_grp_b",
                 "start_date": idx[0], "end_date": idx[60]})
    rows.append({"ticker": tickers[11], "group": "fixture_grp_b",
                 "start_date": idx[30], "end_date": pd.NaT})
    rows += [{"ticker": t, "group": "fixture_grp_c", "start_date": idx[0], "end_date": pd.NaT}
             for t in tickers[12:16]]
    rows += [{"ticker": t, "group": "fixture_grp_c", "start_date": idx[40], "end_date": pd.NaT}
             for t in tickers[16:18]]
    mem = pd.DataFrame(rows, columns=["ticker", "group", "start_date", "end_date"])

    rets, priced = bh.rets_priced(closes)
    out = {}
    for g, sub in mem.groupby("group"):
        out[g] = bh.dated_index(rets, sub, priced, bh.FLOOR)

    lvl_a, n_a = out["fixture_grp_a"]
    assert (n_a == 6).all()
    assert np.isnan(lvl_a.iloc[0])                    # no return on the first session
    exp = (1 + rets[tickers[0:6]].mean(axis=1).fillna(0)).cumprod()
    assert np.allclose(lvl_a.iloc[1:].values, exp.iloc[1:].values, atol=1e-12)

    lvl_b, n_b = out["fixture_grp_b"]
    assert (n_b.iloc[:30] == 5).all()                 # FAKE12 not yet in its window
    assert (n_b.iloc[30:60] == 6).all()
    assert (n_b.iloc[60:] == 5).all()                 # FAKE11 removed ON its end date
    assert lvl_b.iloc[1:].notna().all()               # never below the floor of 5
    r_b = lvl_b.pct_change()
    assert np.allclose(r_b.iloc[2:30].values,
                       rets[tickers[6:11]].iloc[2:30].mean(axis=1).values, atol=1e-12)
    assert np.allclose(r_b.iloc[30:60].values,
                       rets[tickers[6:12]].iloc[30:60].mean(axis=1).values, atol=1e-12)
    assert np.allclose(r_b.iloc[60:].values,
                       rets[tickers[6:10] + [tickers[11]]].iloc[60:].mean(axis=1).values,
                       atol=1e-12)

    lvl_c, n_c = out["fixture_grp_c"]
    assert (n_c.iloc[:40] == 4).all() and (n_c.iloc[40:] == 6).all()
    assert lvl_c.iloc[:40].isna().all()               # below floor: blank index
    assert lvl_c.iloc[40:].notna().all()

    # current-members convention on the same fixture matches the dated one when
    # every member is in-window for the whole span
    lvl_cur, n_cur = bh.current_index(rets, tickers[0:6], priced, bh.FLOOR)
    assert (n_cur == 6).all()
    assert np.allclose(lvl_cur.iloc[1:].values, exp.iloc[1:].values, atol=1e-12)

    df = pd.concat([bh.frame(idx, "sector", g, lvl, n, bh.DATED_BASIS)
                    for g, (lvl, n) in out.items()], ignore_index=True)
    assert list(df.columns) == ["date", "level", "group", "index",
                                "n_priced_members", "membership_basis"]
    assert (df["index"].dropna() == df["index"].dropna().round(6)).all()
    first, nlast = bh.firsts_n(df)
    assert first == {"fixture_grp_a": str(idx[1].date()),
                     "fixture_grp_b": str(idx[1].date()),
                     "fixture_grp_c": str(idx[40].date())}
    assert nlast == {"fixture_grp_a": 6, "fixture_grp_b": 5, "fixture_grp_c": 6}

    # a group with no priced member yields a blank level and zero counts
    lvl_none, n_none = bh.dated_index(rets, mem.iloc[0:0], priced, bh.FLOOR)
    assert lvl_none.isna().all() and (n_none == 0).all()


def test_house_builder_basket_windows_and_below_floor_counts():
    """dated_basket_membership keeps removed members as [added, removed) windows;
    below_floor_counts counts blank-index sessions per group. Made-up doc only."""
    doc = {"seed_date": "2023-05-09", "baskets": {
        "fixture_bk_a": {"members": [
            {"ticker": "FAKE01", "added": "2023-05-09", "removed": None},
            {"ticker": "FAKE02", "added": "2023-05-09", "removed": "2024-01-02"}]},
        "fixture_bk_b": {"members": [
            {"ticker": "FAKE03", "added": "2023-01-03", "removed": None}]}}}
    mem = bh.dated_basket_membership(doc)
    assert list(mem.columns) == ["ticker", "group", "start_date", "end_date"]
    assert len(mem) == 3                              # removed members are kept
    assert mem.loc[mem.ticker == "FAKE02", "end_date"].iloc[0] == pd.Timestamp("2024-01-02")
    assert mem.loc[mem.ticker == "FAKE01", "end_date"].iloc[0] is pd.NaT
    assert mem.loc[mem.ticker == "FAKE03", "start_date"].iloc[0] == pd.Timestamp("2023-01-03")
    df = pd.DataFrame({"group": ["fixture_bk_a"] * 4 + ["fixture_bk_b"] * 2,
                       "n_priced_members": [5, 4, 6, 3, 2, 5]})
    assert bh.below_floor_counts(df) == {"fixture_bk_a": 2, "fixture_bk_b": 1}


_HB_INPUT_ENV = ("GROUP_INDEX_CLOSES", "GROUP_INDEX_BASKET_CLOSES",
                 "GROUP_INDEX_MEMBERSHIP_DIR", "GROUP_INDEX_BASKET_MEMBERSHIP")


def _hb_inputs():
    vals = [os.environ.get(k) for k in _HB_INPUT_ENV]
    if not all(vals):
        return None
    paths = [Path(v) for v in vals]
    return paths if all(p.exists() for p in paths) else None


_HB_INPUTS = _hb_inputs()
_hb_needs = pytest.mark.skipif(
    _HB_INPUTS is None or not GI_DATED.exists() or not GI_BK_DATED.exists(),
    reason="house-builder price inputs (GROUP_INDEX_* env) or committed data/ absent")


def _hb_strip_volatile(obj):
    """Sidecar comparison modulo the build timestamp and input-path fields — the
    only keys the reproducibility contract allows to differ."""
    if isinstance(obj, dict):
        return {k: _hb_strip_volatile(v) for k, v in obj.items()
                if k not in ("build_time_utc", "path")}
    if isinstance(obj, list):
        return [_hb_strip_volatile(v) for v in obj]
    return obj


@_hb_needs
def test_house_builder_reproduces_committed_values(tmp_path):
    """Rebuild all eight house files from the real inputs and assert VALUE
    equality with the committed files (parquets exact; sidecars modulo the build
    timestamp and input paths). Skips when the inputs or data/ are absent."""
    closes, basket_closes, mem_dir, basket_mem = _HB_INPUTS
    out = tmp_path / "house_out"
    bh.main(["--closes", str(closes), "--basket-closes", str(basket_closes),
             "--membership-dir", str(mem_dir), "--basket-membership", str(basket_mem),
             "--out", str(out)])
    for name in ("group_index_daily_dated.parquet",
                 "group_index_daily_current_sensitivity.parquet",
                 "group_index_basket_daily_dated.parquet",
                 "group_index_daily_dated_sp400_sp600.parquet"):
        pd.testing.assert_frame_equal(pd.read_parquet(out / name),
                                      pd.read_parquet(HIST / name), check_exact=True)
    pd.testing.assert_frame_equal(
        pd.read_csv(out / "group_index_key_map.csv", keep_default_na=False),
        pd.read_csv(GI_KEYMAP, keep_default_na=False), check_exact=True)
    for name in ("group_index.meta.json", "group_index_basket_daily_dated.meta.json",
                 "group_index_daily_dated_sp400_sp600.meta.json"):
        got = json.loads((out / name).read_text())
        want = json.loads((HIST / name).read_text())
        assert _hb_strip_volatile(got) == _hb_strip_volatile(want), name

# ===========================================================================
# Organ alert histories (COO ruling 38 Part A) — scripts/build_organ_histories.py
# Three HOUSE organs only: us_basket washout (dated + current membership),
# rolling-over override and phase_v2 (11 SPDR sectors). Group-level rows only:
# no member ticker, price or per-security date; nothing related to outcomes.
# The `state` column holds the engine's OWN output, so the regime _FORBIDDEN
# regex (which bans the word "state") does NOT apply to these files.
# Fidelity tests recompute via the build script's own comparison functions on
# the committed parquet and assert the observed counts + "no new mismatch".
# ===========================================================================
from scripts import build_organ_histories as oh  # noqa: E402

_ORGAN_PQ = HIST / "organ_histories_house.parquet"
_ORGAN_META = HIST / "organ_histories_house.meta.json"
_ORGAN_REPORT = ROOT / "research/breadth_history/ORGAN_HISTORIES_REPORT.md"
_LEDGER = ROOT / "data/us_basket_turn/ledger.jsonl"
_BACKFILL = ROOT / "data/sector_cycles/backfill.parquet"
_FORWARD = ROOT / "data/sector_cycles/forward_log.parquet"
_YAHOO = ROOT / "data/yahoo"

_organ_needs = pytest.mark.skipif(not _ORGAN_PQ.exists(),
                                  reason="data/ not checked out (sparse tree)")
_organ_ledger_needs = pytest.mark.skipif(
    not (_ORGAN_PQ.exists() and _LEDGER.exists()),
    reason="organ parquet or us_basket ledger not checked out (sparse tree)")
_organ_sector_store_needs = pytest.mark.skipif(
    not (_ORGAN_PQ.exists() and _BACKFILL.exists() and _FORWARD.exists()),
    reason="organ parquet or sector cycle stores not checked out (sparse tree)")
# rolling-over has no persisted store: fidelity recomputes the live engine path
# on the latest sessions, so it needs the price panel at the PIN basis (the
# committed parquet was built on pin prices). The sentinel skips when the panel
# is absent (sparse CI) or restored to HEAD bytes (post-build cleanup).
_PIN_SPY_SHA256 = "37bad67655facda3cb3b171f34dde36471b975bcfdf16f438f33a66bf5368eb5"


def _pin_price_panel() -> bool:
    import hashlib
    spy = _YAHOO / "SPY.parquet"
    if not spy.exists():
        return False
    try:
        return hashlib.sha256(spy.read_bytes()).hexdigest() == _PIN_SPY_SHA256
    except OSError:
        return False


_organ_yahoo_needs = pytest.mark.skipif(
    not (_ORGAN_PQ.exists() and _pin_price_panel()),
    reason="organ parquet or pin-basis yahoo panel not present (sparse tree / restored inputs)")

# --- Observed fidelity (full build @ engine pin 72082493, restated prices).
# --- These literals are the regression baseline: the test asserts the counts
# --- AND the sha256 of the full sorted mismatch detail ("no new mismatch" — any
# --- added/removed/changed mismatch flips the hash). Every mismatch is enumerated
# --- by (group_key, session_date) in ORGAN_HISTORIES_REPORT.md and the sidecar.
# --- The replay is faithful to the LIVE engine (phase_v2 and rolling_over both
# --- 110/110 vs sector_cycles.compute on the latest sessions); the store
# --- mismatches are restated-price vintage effects plus a calendar-vs-trading
# --- date convention (stores stamp month-end/run dates incl. weekends). They are
# --- reported, never tuned (brief; ruling 38 s2d).
_OB_US = {"total": 1911, "match": 1803, "mismatch": 108}         # us_basket dated vs ledger
_OB_US_MM_SHA = "f294e536e376992592d40e26853b94b473897d6ffecf6dfcfe192c584d485507"
_OB_PH_BF = {"total": 1881, "match": 652, "mismatch": 1229}      # phase_v2 current vs backfill (month_end)
_OB_PH_BF_MM_SHA = "12600d05fa845783836f1275971b38a84b421989d22aa956bcd56147bfb594c5"
_OB_PH_FL = {"total": 858, "match": 601, "mismatch": 257}        # phase_v2 current vs forward_log (daily)
_OB_PH_FL_MM_SHA = "962fb38d6032a89f23536e33c124df88b77656bf1c6a7ef60ed8ad2f9228402a"
_OB_PH_BF_LEG = {"total": 1881, "match": 1881, "mismatch": 0}    # phase_v2 legacy vs backfill (exact: legacy wrote it)
_OB_PH_BF_LEG_MM_SHA = "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945"
_OB_PH_FL_LEG = {"total": 858, "match": 0, "mismatch": 858}      # phase_v2 legacy vs forward_log (current wrote it)
_OB_PH_FL_LEG_MM_SHA = "dcb64e5d6c1e3420e4fe2f14fa7963dc070c51d555156a1f2845257906dd14c0"
_OB_RO = {"total": 110, "match": 110, "mismatch": 0}             # rolling_over vs live engine (branch + main tape)
_OB_RO_MM_SHA = "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945"
_OB_RO_N = 10                                                    # --rolling-fidelity-sessions

_ORGAN_COLS = [
    "organ", "level", "group_key", "session_date", "state", "first_knowable_date",
    "membership_basis", "n_members", "engine_code_sha", "after_2023_12_29",
    "days_in_state", "confirmed_transition", "phase", "pos_v2", "osc_slope",
    "basis", "phase_v2_source", "rolling", "pos", "engine_timing_state", "engine_signal",
    "divergence",
]


def _mm_sha(res: dict) -> str:
    import hashlib
    mm = sorted(res.get("mismatches", []),
                key=lambda x: (x.get("group_key", ""), x.get("session_date", ""), x.get("kind", "")))
    return hashlib.sha256(json.dumps(mm, sort_keys=True, default=str).encode()).hexdigest()


def _assert_fidelity(res: dict, observed: dict, observed_sha: str):
    assert (res["total"], res["match"], res["mismatch"]) == (
        observed["total"], observed["match"], observed["mismatch"]), res
    assert _mm_sha(res) == observed_sha, "fidelity mismatch detail changed (new/removed/changed mismatch)"


@_organ_needs
def test_organ_histories_schema_and_provenance():
    df = pd.read_parquet(_ORGAN_PQ)
    assert list(df.columns) == _ORGAN_COLS
    assert set(df["organ"].unique()) == {"us_basket", "rolling_over", "phase_v2"}
    # two pinned engine commits: the current engine (primary series) and the legacy
    # engine that wrote backfill.parquet; no hand-copied threshold/rule
    assert set(df["engine_code_sha"].unique()) == {oh.ENGINE_CODE_SHA, oh.LEGACY_ENGINE_CODE_SHA}
    assert oh.ENGINE_CODE_SHA == "72082493cb5e29cf5fe4a093fadf6f435b6fe2c3"
    assert oh.LEGACY_ENGINE_CODE_SHA == "896471652cea87edc77a651d5c7e8d9d790119f8"
    # legacy rows are phase_v2 only (the backfill writer's organ)
    assert set(df.loc[df.engine_code_sha == oh.LEGACY_ENGINE_CODE_SHA, "organ"]) == {"phase_v2"}
    # levels + membership bases
    assert set(df.loc[df.organ == "us_basket", "level"]) == {"basket"}
    assert set(df.loc[df.organ != "us_basket", "level"]) == {"sector"}
    assert set(df.loc[df.organ == "us_basket", "membership_basis"]) == {"dated", "current"}
    assert set(df.loc[df.organ != "us_basket", "membership_basis"]) == {"etf_price"}
    # two labelled membership versions of the basket washout, both present
    ub = df[df.organ == "us_basket"]
    assert set(ub["membership_basis"]) == {"dated", "current"}
    assert set(ub.loc[ub.membership_basis == "dated", "group_key"]) == \
        set(ub.loc[ub.membership_basis == "current", "group_key"])
    # group keys are organ ids, never member tickers
    spdr_ids = {t.lower() for t in oh.SPDRS}
    sec = df[df.organ != "us_basket"]
    assert set(sec["group_key"]) == spdr_ids
    assert set(sec["n_members"].dropna().astype(int)) == {1}
    bmem = json.loads((ROOT / "data/baskets/membership.json").read_text())
    assert set(ub["group_key"]) <= set(bmem["baskets"])
    # first knowable never after the session; desk-block flag consistent
    assert (df["first_knowable_date"] <= df["session_date"]).all()
    expect_after = df["session_date"] > oh.DESK_BLOCK.strftime("%Y-%m-%d")
    assert (df["after_2023_12_29"].astype(bool) == expect_after).all()
    # state is the engine's own output. us_basket and phase_v2 always carry a
    # state string; rolling_over carries the engine's phaseLabel, which may be
    # null during warm-up (the rolling boolean is the organ's primary output).
    assert df.loc[df.organ != "rolling_over", "state"].notna().all()
    assert df.loc[df.organ == "rolling_over", "rolling"].notna().all()
    # nothing related to outcomes / prices: the exact column set above is the guard
    assert not (set(df.columns) & {"forward", "outcome", "return", "price", "close",
                                   " fwd_ret", "forward_return"})


@_organ_ledger_needs
def test_organ_us_basket_fidelity_vs_ledger():
    df = pd.read_parquet(_ORGAN_PQ)
    res = oh.fidelity_us_basket(df)
    _assert_fidelity(res, _OB_US, _OB_US_MM_SHA)


def _organ_forward_log_through() -> str:
    """The organ build's own last phase_v2 session, read from its sidecar (never typed here)."""
    import datetime as _dt
    assert _ORGAN_META.exists(), (
        "organ_histories_house.meta.json is absent; the forward_log comparison has no as_of")
    meta = json.loads(_ORGAN_META.read_text())
    through = ((meta.get("organs") or {}).get("phase_v2") or {}).get("last_session")
    try:
        ok = isinstance(through, str) and _dt.date.fromisoformat(through).isoformat() == through
    except ValueError:
        ok = False
    assert ok, (
        "organ_histories_house.meta.json carries no YYYY-MM-DD organs.phase_v2.last_session; "
        "the forward_log comparison has no as_of to scope to")
    fl = pd.read_parquet(_FORWARD)
    fl = fl[fl["id"].isin([t.lower() for t in oh.SPDRS])]
    dates = fl["date"].astype(str).str[:10]
    assert (dates <= through).any(), (
        f"forward_log holds no sector row at or before the organ as_of {through}; "
        "refusing an empty comparison")
    print(f"forward_log rows after the organ as_of {through}: {int((dates > through).sum())} "
          "(counted, not compared)")
    return through


@_organ_sector_store_needs
def test_organ_phase_v2_fidelity_vs_stores():
    """phase_v2 replay vs backfill and forward_log, at pinned counts and mismatch hashes.

    The forward_log comparison is scoped to sessions up to the organ build's own as_of
    (organs.phase_v2.last_session in its meta.json). The store is appended every night,
    so unscoped, each new night's rows fall outside the replay and break the pin daily.
    Rows after the as_of are counted and printed, not compared; a change to any row at or
    before it still flips the counts or the hash (ruling 104).
    """
    df = pd.read_parquet(_ORGAN_PQ)
    res = oh.fidelity_phase_v2(df, forward_log_through=_organ_forward_log_through())
    # current engine (primary series) vs both stores
    _assert_fidelity(res["current"]["backfill"], _OB_PH_BF, _OB_PH_BF_MM_SHA)
    _assert_fidelity(res["current"]["forward_log"], _OB_PH_FL, _OB_PH_FL_MM_SHA)
    # legacy engine (the backfill writer's version) vs both stores
    _assert_fidelity(res["legacy"]["backfill"], _OB_PH_BF_LEG, _OB_PH_BF_LEG_MM_SHA)
    _assert_fidelity(res["legacy"]["forward_log"], _OB_PH_FL_LEG, _OB_PH_FL_LEG_MM_SHA)
    # forward_log writer is not recorded -> labelled unproven against the store
    assert res["current"]["forward_log"]["fidelity"] == "unproven_against_store"
    assert res["legacy"]["forward_log"]["fidelity"] == "unproven_against_store"
    # both engine versions overlap on the store grid; the version difference is counted
    assert res["version_overlap"]["overlap_pairs"] > 0
    assert res["version_overlap"]["different_phase"] >= 0
    # D-1 table cells sum to the population (no row added/re-keyed)
    d1 = res["current"]["forward_log"]["d1_table"]
    assert d1["sum_check"] is True


@_organ_yahoo_needs
def test_organ_rolling_over_fidelity_vs_live_engine():
    df = pd.read_parquet(_ORGAN_PQ)
    res = oh.fidelity_rolling_over(df, _OB_RO_N)
    _assert_fidelity(res, _OB_RO, _OB_RO_MM_SHA)


@_organ_needs
def test_organ_sidecar_consistency():
    import hashlib
    df = pd.read_parquet(_ORGAN_PQ)
    meta = json.loads(_ORGAN_META.read_text())
    raw = _ORGAN_PQ.read_bytes()
    assert meta["parquet"]["bytes"] == len(raw)
    assert meta["parquet"]["sha256"] == hashlib.sha256(raw).hexdigest()
    assert meta["engine_code_sha"] == oh.ENGINE_CODE_SHA
    assert meta["price_basis"] == "restated"
    assert meta["no_outcome"]
    # sidecar fidelity counts agree with the regression baseline
    fid = meta["fidelity"]
    us = fid["us_basket"]
    assert (us["total"], us["match"], us["mismatch"]) == (
        _OB_US["total"], _OB_US["match"], _OB_US["mismatch"])
    bf = fid["phase_v2"]["current"]["backfill"]
    fl = fid["phase_v2"]["current"]["forward_log"]
    assert (bf["total"], bf["match"], bf["mismatch"]) == (
        _OB_PH_BF["total"], _OB_PH_BF["match"], _OB_PH_BF["mismatch"])
    assert (fl["total"], fl["match"], fl["mismatch"]) == (
        _OB_PH_FL["total"], _OB_PH_FL["match"], _OB_PH_FL["mismatch"])
    bfl = fid["phase_v2"]["legacy"]["backfill"]
    fll = fid["phase_v2"]["legacy"]["forward_log"]
    assert (bfl["total"], bfl["match"], bfl["mismatch"]) == (
        _OB_PH_BF_LEG["total"], _OB_PH_BF_LEG["match"], _OB_PH_BF_LEG["mismatch"])
    assert (fll["total"], fll["match"], fll["mismatch"]) == (
        _OB_PH_FL_LEG["total"], _OB_PH_FL_LEG["match"], _OB_PH_FL_LEG["mismatch"])
    # no-fallback proof: both regime calibrations opened at inputs_commit bytes, caches non-empty
    rcp = meta["regime_calibration_proof"]
    assert rcp["fitted_bands_nonempty"] is True
    assert rcp["risk_calib_nonempty"] is True
    for rec in rcp["files"].values():
        assert rec["opened"] is True
        assert rec["matches_inputs_commit"] is True
    assert meta["hazard_cannot_load_count"] == 0
    ro = fid["rolling_over"]
    assert (ro["total"], ro["match"], ro["mismatch"]) == (
        _OB_RO["total"], _OB_RO["match"], _OB_RO["mismatch"])
    # first-knowable in the sidecar matches the parquet group minima
    fk = meta["first_knowable"]["by_organ_key"]
    for organ in ("phase_v2", "rolling_over"):
        g = df[df.organ == organ].groupby("group_key")["first_knowable_date"].min()
        for key, val in g.items():
            assert fk[organ][key] == val
    assert _ORGAN_REPORT.exists()


# --- Builder refusal guards (brief item 6; COO steers 2d / 3d / 22:48).
# --- Fixture git repos in tmp_path with MADE-UP files only; no real engine input is
# --- touched. These assert the builder REFUSES (SystemExit), never that it proceeds.
def _fixture_git_env():
    import os
    return {**os.environ, "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_SYSTEM": "/dev/null"}


def _init_fixture_repo(tmp_path):
    import subprocess
    repo = tmp_path / "fixture_repo"
    repo.mkdir()
    env = _fixture_git_env()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True, env=env)
    subprocess.run(["git", "config", "user.email", "fixture@example.com"], cwd=repo, check=True, env=env)
    subprocess.run(["git", "config", "user.name", "fixture"], cwd=repo, check=True, env=env)
    subprocess.run(["git", "config", "commit.gpgsign", "false"], cwd=repo, check=True, env=env)
    (repo / "seed.txt").write_text("seed")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, env=env)
    subprocess.run(["git", "commit", "-qm", "seed", "--no-verify"], cwd=repo, check=True, env=env)
    return repo


def _fixture_commit_all(repo):
    import subprocess
    env = _fixture_git_env()
    subprocess.run(["git", "add", "."], cwd=repo, check=True, env=env)
    subprocess.run(["git", "commit", "-qm", "update", "--no-verify"], cwd=repo, check=True, env=env)


def test_organ_requires_staging_dir():
    # --staging-dir is REQUIRED; invoking without it must refuse (argparse SystemExit)
    with pytest.raises(SystemExit):
        oh.main([])


def test_organ_staging_refusal_nonempty(tmp_path):
    st = tmp_path / "staging"
    st.mkdir()
    (st / "preexisting.txt").write_text("x")
    with pytest.raises(SystemExit):
        oh.check_staging(st)


def test_organ_staging_refusal_prelinked(tmp_path):
    st = tmp_path / "staging"
    st.mkdir()
    target = tmp_path / "target"
    target.mkdir()
    (st / "link").symlink_to(target, target_is_directory=True)
    with pytest.raises(SystemExit):
        oh.check_staging(st)


def test_organ_input_gate_refusal_differs_from_head(tmp_path, monkeypatch):
    # a made-up in-repo input whose working bytes differ from its blob at HEAD -> refuse
    repo = _init_fixture_repo(tmp_path)
    f = repo / "data" / "made_up_input.json"
    f.parent.mkdir(parents=True)
    f.write_text('{"v": 1}')
    _fixture_commit_all(repo)
    monkeypatch.setattr(oh, "ROOT", repo)
    monkeypatch.setattr(oh, "enumerate_inputs", lambda: (["data/made_up_input.json"], []))
    f.write_text('{"v": 2}')  # working bytes now differ from the HEAD blob
    with pytest.raises(SystemExit):
        oh.input_gate(oh.git_head(), oh.head_blobs())


def test_organ_input_gate_refusal_absent_calibration(tmp_path, monkeypatch):
    # a made-up calibration file absent from the fixture tree -> refuse (missing required)
    repo = _init_fixture_repo(tmp_path)
    monkeypatch.setattr(oh, "ROOT", repo)
    monkeypatch.setattr(oh, "enumerate_inputs",
                    lambda: (["data/regime/made_up_calibration.json"], []))
    with pytest.raises(SystemExit):
        oh.input_gate(oh.git_head(), oh.head_blobs())


def test_organ_input_gate_refusal_empty_calibration(tmp_path, monkeypatch):
    # a made-up calibration file present but EMPTY (made-up bytes) -> refuse
    repo = _init_fixture_repo(tmp_path)
    f = repo / "data" / "regime" / "made_up_calibration.json"
    f.parent.mkdir(parents=True)
    f.write_text('{"bands": [1, 2]}')
    _fixture_commit_all(repo)
    monkeypatch.setattr(oh, "ROOT", repo)
    monkeypatch.setattr(oh, "enumerate_inputs",
                    lambda: (["data/regime/made_up_calibration.json"], []))
    f.write_text("")  # present but empty -> working bytes differ from the HEAD blob
    with pytest.raises(SystemExit):
        oh.input_gate(oh.git_head(), oh.head_blobs())


# ── overlay-gate refusals (COO 23:32Z): data/vol_regime/basket_overlay_gate.json ──────
# Loader engine/vol_regime.py load_overlay_gate (:291-308, path constant :87). When the
# file is absent, `if p.exists()` falls through and returns a CLOSED gate with NO log,
# reached unconditionally from cycles.ladder_state via regime_caution_scored
# (cycles.py:1458-1462, vol_regime.py:311-315). An open audit hook does NOT see the
# p.exists() stat, so absence leaves no trace in the opened-file record — only this
# required-present gate (pinned by sha256 at inputs_commit) catches it.
def test_organ_input_gate_refusal_absent_overlay_gate(tmp_path, monkeypatch):
    repo = _init_fixture_repo(tmp_path)
    monkeypatch.setattr(oh, "ROOT", repo)
    monkeypatch.setattr(oh, "enumerate_inputs",
                    lambda: (["data/vol_regime/basket_overlay_gate.json"], []))
    with pytest.raises(SystemExit):
        oh.input_gate(oh.git_head(), oh.head_blobs())


def test_organ_input_gate_refusal_empty_overlay_gate(tmp_path, monkeypatch):
    # present but EMPTY (made-up bytes) -> working bytes differ from the HEAD blob
    repo = _init_fixture_repo(tmp_path)
    f = repo / "data" / "vol_regime" / "basket_overlay_gate.json"
    f.parent.mkdir(parents=True)
    f.write_text('{"gate": "open"}')
    _fixture_commit_all(repo)
    monkeypatch.setattr(oh, "ROOT", repo)
    monkeypatch.setattr(oh, "enumerate_inputs",
                    lambda: (["data/vol_regime/basket_overlay_gate.json"], []))
    f.write_text("")
    with pytest.raises(SystemExit):
        oh.input_gate(oh.git_head(), oh.head_blobs())


def test_organ_input_gate_refusal_unreadable_overlay_gate(tmp_path, monkeypatch):
    # present but UNREADABLE (mode 000) -> working_blob_id catches OSError -> refuse
    repo = _init_fixture_repo(tmp_path)
    f = repo / "data" / "vol_regime" / "basket_overlay_gate.json"
    f.parent.mkdir(parents=True)
    f.write_text('{"gate": "open"}')
    _fixture_commit_all(repo)
    monkeypatch.setattr(oh, "ROOT", repo)
    monkeypatch.setattr(oh, "enumerate_inputs",
                    lambda: (["data/vol_regime/basket_overlay_gate.json"], []))
    f.chmod(0o000)
    try:
        with pytest.raises(SystemExit):
            oh.input_gate(oh.git_head(), oh.head_blobs())
    finally:
        f.chmod(0o644)


# ===========================================================================
# Dated S&P 500 membership basis (COO ruling 36 s2 addition) + like-for-like
# fixed-set change on both bases. Same engine functions; aggregates/counts only.
# ===========================================================================
import hashlib  # noqa: E402

from engine import group_breadth_history as gbh  # noqa: E402
from scripts import build_group_breadth_history as gb  # noqa: E402

_REGIME_DATED_PQ = HIST / "regime_inputs_dated_sp500_daily.parquet"
_REGIME_DATED_META = HIST / "regime_inputs_dated_sp500.meta.json"
_REGIME_FIXCHG_PQ = HIST / "regime_inputs_fixchg_current.parquet"
_REGIME_FIXCHG_META = HIST / "regime_inputs_fixchg_current.meta.json"
_dated_needs = pytest.mark.skipif(not _REGIME_DATED_PQ.exists(),
                                  reason="data/ not checked out (sparse tree)")
_fixchg_needs = pytest.mark.skipif(not _REGIME_FIXCHG_PQ.exists(),
                                   reason="data/ not checked out (sparse tree)")
# The two current-basis outputs are FROZEN: a dated/fixchg addition must never
# rewrite them. This guard pins their exact bytes for the life of the repo.
_FROZEN_CURRENT = {
    "regime_inputs_daily_current.parquet":
        "c15d5c2d533ae7d66dd84a67c8c1abfa19457aa44fcd1e8504d00bc0c9348177",
    "regime_inputs_current.meta.json":
        "552260044b01a67b6a5aed0a30dee52db634c77dd100fb7726d5f282cf0f634d",
}
_FIXCHG_SERIES = ({f"fix_chg_pct_above_{w}_{k}" for w in rg.WINDOWS for k in rg.CHANGE_HORIZONS}
                  | {f"n_fixed_{w}_{k}" for w in rg.WINDOWS for k in rg.CHANGE_HORIZONS})
# The 11 GICS sector names (as-of-now labels) plus the two computed aggregates are
# the only legal groups on the dated basis; a member ticker can never be a group.
_GICS = {"Communication Services", "Consumer Discretionary", "Consumer Staples", "Energy",
         "Financials", "Health Care", "Industrials", "Information Technology", "Materials",
         "Real Estate", "Utilities"}
_DATED_GROUPS = _GICS | {"universe", "high_beta_computed"}


def _regime_dated_synth(tmp: Path, n=12, periods=700, start="2020-01-01"):
    """Synthetic dated membership windows over the regime synth universe.

    The last member exits at 60% of the span and the second-to-last enters at
    20%, so the in-window count varies by date; sector labels S1/S2 as of now."""
    closes, root, etf_dir, cp, dm = _regime_synth_root(tmp, n=n, periods=periods, start=start)
    idx = closes.index
    t = list(closes.columns)
    pit = tmp / "pit"; pit.mkdir()
    rows = []
    for i, tk in enumerate(t):
        s, e = idx[0], pd.NaT
        if i == n - 1:
            e = idx[int(periods * 0.6)]
        if i == n - 2:
            s = idx[int(periods * 0.2)]
        rows.append({"ticker": tk, "start_date": s, "end_date": e, "src": "sp500"})
    # A dated member with no stored close (ticker reuse): exercises the same
    # missing-rows path as the real archive, where some windows are unpriced.
    rows.append({"ticker": "T99", "start_date": idx[0], "end_date": idx[100], "src": "sp500"})
    pd.DataFrame(rows).to_parquet(pit / "sp1500_pit_membership.parquet")
    sec = ["S1"] * (n // 2) + ["S2"] * (n - n // 2)
    pd.DataFrame({"ticker": t + ["T99"], "sector": sec + ["S2"]}).to_parquet(
        pit / "sp1500_pit_sectors.parquet")
    return closes, root, etf_dir, cp, pit


# ---- synthetic: dated window semantics -------------------------------------
def test_regime_dated_window_not_counted_outside():
    idx = pd.bdate_range("2020-01-01", periods=300)
    up = np.linspace(100, 200, 300)
    closes = pd.DataFrame({"A": up, "B": up, "C": up, "D": up}, index=idx)
    mem = pd.DataFrame({"ticker": ["A", "B", "C", "D"], "group": ["universe"] * 4,
                        "start_date": [idx[0]] * 4,
                        "end_date": [pd.NaT, pd.NaT, pd.NaT, idx[250]]})
    out, ns = rg.universe_breadth(closes, pd.Timestamp("2020-01-01"), membership=mem)
    assert ns["pct_above_50"].loc[idx[240]] == 4.0     # D still in-window
    assert ns["pct_above_50"].loc[idx[260]] == 3.0     # D left at idx[250]
    assert out["pct_above_50"].loc[idx[260]] == 100.0  # 3 of 3 above
    assert ns["pct_above_50"].loc[idx[-1]] == 3.0
    assert out["n_counted_nh"].loc[idx[-1]] == 3.0     # NH/NL excludes D too


def test_regime_dated_fixed_change_matches_engine():
    rng = np.random.default_rng(7)
    idx = pd.bdate_range("2020-01-01", periods=500)
    r = rng.normal(0.0003, 0.01, size=(500, 8))
    closes = pd.DataFrame(100 * np.exp(np.cumsum(r, axis=0)), index=idx,
                          columns=[f"T{i:02d}" for i in range(8)])
    closes.iloc[100:140, 3] = np.nan                   # a price gap
    mem = pd.DataFrame({"ticker": list(closes.columns), "group": ["universe"] * 8,
                        "start_date": [idx[0]] * 6 + [idx[120], idx[0]],
                        "end_date": [pd.NaT] * 7 + [idx[420]]})
    out, ns = rg.universe_fixed_change(closes, pd.Timestamp("2020-01-01"), membership=mem)
    ref = gbh.daily_group_breadth(closes, mem, groups=["universe"], windows=rg.WINDOWS,
                                  horizons=rg.CHANGE_HORIZONS,
                                  min_members=bt.BREADTH_FLOOR).set_index("date")
    for w in rg.WINDOWS:
        for k in rg.CHANGE_HORIZONS:
            s = f"fix_chg_pct_above_{w}_{k}"
            pd.testing.assert_series_equal(out[s], ref[s].reindex(out[s].index), check_names=False)
            nf = f"n_fixed_{w}_{k}"
            assert (ns[s].to_numpy() == ref[nf].reindex(ns[s].index).to_numpy()).all()


def test_regime_dated_fixchg_start_window_blanked(tmp_path):
    """The dated build produces no fix_chg / n_fixed row before k sessions of
    dated membership lie before the end date: the start session t-k must not
    read closes from before the first dated-membership session. The removal
    lives in build_dated; universe_fixed_change itself is unchanged."""
    closes, root, etf_dir, cp, dm = _regime_synth_root(tmp_path, n=8, periods=400)
    idx = closes.index
    t = list(closes.columns)
    pit = tmp_path / "pit"; pit.mkdir()
    mem_start = idx[100]                     # archive closes predate membership
    rows = [{"ticker": tk, "start_date": mem_start,
             "end_date": idx[350] if i == 7 else pd.NaT, "src": "sp500"}
            for i, tk in enumerate(t)]
    # A dated member with no stored close: exercises the unpriced-in-window
    # path of the dated build (same as _regime_dated_synth's T99).
    rows.append({"ticker": "T99", "start_date": mem_start,
                 "end_date": idx[350], "src": "sp500"})
    pd.DataFrame(rows).to_parquet(pit / "sp1500_pit_membership.parquet")
    pd.DataFrame({"ticker": t + ["T99"], "sector": ["S1"] * 4 + ["S2"] * 5}).to_parquet(
        pit / "sp1500_pit_sectors.parquet")
    out = tmp_path / "out"
    rg.build_dated(cp, pit, out, root=root, etf_dir=etf_dir, start=str(mem_start.date()))
    df = pd.read_parquet(out / "regime_inputs_dated_sp500_daily.parquet")
    for w in rg.WINDOWS:
        for k in rg.CHANGE_HORIZONS:
            cut = idx[100 + k]               # k membership sessions must lie before t
            fc = df[df.series == f"fix_chg_pct_above_{w}_{k}"]
            nf = df[df.series == f"n_fixed_{w}_{k}"]
            diff = df[df.series == f"diff_pct_above_{w}_{k}d"]
            assert not fc.empty and not nf.empty and not diff.empty
            assert (fc.date >= cut).all() and (nf.date >= cut).all()
            assert fc.date.min() == diff.date.min()      # aligned with the diff series
            assert list(nf.date) == list(fc.date)
    # the 50-day lines are the ones the blanking actually cuts: without it they
    # would start at the first membership session (the archive has closes there)
    assert df[df.series == "fix_chg_pct_above_50_21"].date.min() == idx[121]
    assert df[df.series == "fix_chg_pct_above_50_63"].date.min() == idx[163]
    # universe_fixed_change itself still produces the start-window rows
    mem = gb.membership_dated(pit, "sp500")
    mem["group"] = "universe"
    raw, _ = rg.universe_fixed_change(closes, pd.Timestamp(mem_start), membership=mem)
    assert raw["fix_chg_pct_above_50_21"].index.min() == idx[100]


def test_regime_dated_dispersion_both_ends():
    rng = np.random.default_rng(5)
    idx = pd.bdate_range("2020-01-01", periods=120)
    r = rng.normal(0.0003, 0.01, size=(120, 4))
    closes = pd.DataFrame(100 * np.exp(np.cumsum(r, axis=0)), index=idx, columns=list("ABCD"))
    mask = pd.DataFrame(True, index=idx, columns=list("ABCD"))
    mask.loc[idx[:80], "D"] = False                    # D enters at idx[80]
    got = rg.dispersion(closes, {}, pd.Timestamp("2020-01-01"), masks={"universe": mask})
    v, n = got["dispersion_21d"]["universe"]
    assert n.loc[idx[95]] == 3                         # t-21=idx[74]: D not yet in-window
    assert n.loc[idx[101]] == 4                        # t-21=idx[80]: D in-window at both ends
    r21 = rg.window_return(closes, 21)
    exp = r21.loc[idx[95], ["A", "B", "C"]].std(ddof=1) * 100.0
    assert abs(v.loc[idx[95]] - exp) < 1e-9


def test_regime_dated_high_beta_selection_mask():
    idx = pd.bdate_range("2020-01-01", periods=700)
    rng = np.random.default_rng(3)
    s = rng.normal(0.0003, 0.01, 700)
    spy = pd.Series(100 * np.cumprod(1 + s), index=idx)
    betas = np.linspace(0.5, 1.5, 10)
    closes = pd.DataFrame({f"T{i:02d}": 100 * np.cumprod(1 + b * s)
                           for i, b in enumerate(betas)}, index=idx)
    start = pd.Timestamp("2021-06-01")
    keep = list(closes.columns[:8])
    mask = pd.DataFrame(False, index=idx, columns=closes.columns)
    mask[keep] = True
    # A constant in-window mask over a subset == passing only that subset's columns.
    lvl_m, n_m, facts_m = rg.high_beta_cohorts(closes, spy, start, member_mask=mask)
    lvl_s, n_s, facts_s = rg.high_beta_cohorts(closes[keep], spy, start)
    pd.testing.assert_series_equal(lvl_m, lvl_s, check_names=False)
    pd.testing.assert_series_equal(n_m, n_s, check_names=False)
    assert facts_m["cohort_size_max"] == facts_s["cohort_size_max"] == 2   # ceil(8/5)
    assert facts_m["selection_set"] == "dated members at the selection session"
    none = pd.DataFrame(False, index=idx, columns=closes.columns)
    lvl0, _, facts0 = rg.high_beta_cohorts(closes, spy, start, member_mask=none)
    assert lvl0.dropna().empty and facts0["months_selected"] == 0


def test_regime_fixchg_static_equals_plain_diff_without_gaps():
    rng = np.random.default_rng(9)
    idx = pd.bdate_range("2020-01-01", periods=400)
    r = rng.normal(0.0003, 0.01, size=(400, 6))
    closes = pd.DataFrame(100 * np.exp(np.cumsum(r, axis=0)), index=idx,
                          columns=[f"T{i:02d}" for i in range(6)])
    start = pd.Timestamp("2020-01-01")
    fc, _ = rg.universe_fixed_change(closes, start)            # static, no gaps
    ub, _ = rg.universe_breadth(closes, start)
    for w in rg.WINDOWS:
        for k in rg.CHANGE_HORIZONS:
            # no gaps + static membership => fixed-set == plain difference
            pd.testing.assert_series_equal(fc[f"fix_chg_pct_above_{w}_{k}"],
                                           ub[f"diff_pct_above_{w}_{k}d"], check_names=False)
    mem = pd.DataFrame({"ticker": list(closes.columns), "group": ["universe"] * 6})
    ref = gbh.daily_group_breadth(closes, mem, groups=["universe"], windows=rg.WINDOWS,
                                  horizons=rg.CHANGE_HORIZONS,
                                  min_members=bt.BREADTH_FLOOR).set_index("date")
    for w in rg.WINDOWS:
        for k in rg.CHANGE_HORIZONS:
            s = f"fix_chg_pct_above_{w}_{k}"
            pd.testing.assert_series_equal(fc[s], ref[s].reindex(fc[s].index), check_names=False)


def test_regime_dated_full_synthetic_build(tmp_path):
    closes, root, etf_dir, cp, pit = _regime_dated_synth(tmp_path)
    out = tmp_path / "out"
    meta = rg.build_dated(cp, pit, out, root=root, etf_dir=etf_dir, start="2021-06-01")
    df = pd.read_parquet(out / "regime_inputs_dated_sp500_daily.parquet")
    assert list(df.columns) == ["date", "series", "group", "value", "n", "kind"]
    assert set(df.kind) <= set(rg.KINDS)
    assert (df.n >= 2).all() and not df.isna().any().any()
    assert df.date.min() >= pd.Timestamp("2021-06-01")
    assert not df.duplicated(["series", "group", "date"]).any()
    assert set(df.group) <= {"universe", "high_beta_computed", "S1", "S2"}
    assert meta["basis"] == rg.BASIS_DATED == "reconstructed_dated_membership"
    assert meta["set"] == "full"
    assert set(meta["series"]) == set(df.series.unique())
    # no curated-basket relative indices on the dated basis; computed high-beta is kept
    assert not any(s.startswith("rel_") and s != "rel_high_beta_computed_vs_ew_universe"
                   for s in df.series)
    assert "rel_high_beta_computed_vs_ew_universe" in set(df.series)
    last = df[(df.series == "pct_above_200") & (df.group == "universe")].sort_values("date").iloc[-1]
    assert last.n == 11                                # T11 left, T10 present at the end
    for entry in meta["series"].values():
        assert {"definition", "first_date", "source", "basis", "kind", "gaps"} <= set(entry)
    # minimum mode: the COO minimum set, universe + computed high-beta groups only
    meta_m = rg.build_dated(cp, pit, tmp_path / "out_min", root=root, etf_dir=etf_dir,
                            start="2021-06-01", minimum=True)
    dfm = pd.read_parquet(tmp_path / "out_min/regime_inputs_dated_sp500_daily.parquet")
    assert meta_m["set"] == "minimum"
    assert rg.MINIMUM_SERIES <= set(dfm.series.unique())
    assert set(dfm.group) <= {"universe", "high_beta_computed"}
    assert (tmp_path / "out_min/regime_inputs_dated_sp500.meta.json").stat().st_size < 30_000
    assert not any(k.endswith("_sample") for k in meta_m["coverage"])


def test_regime_fixchg_current_synthetic_build(tmp_path):
    closes, root, etf_dir, cp, dm = _regime_synth_root(tmp_path)
    out = tmp_path / "out"
    meta = rg.build_fixchg_current(cp, dm, out, root=root, start="2021-06-01")
    df = pd.read_parquet(out / "regime_inputs_fixchg_current.parquet")
    assert list(df.columns) == ["date", "series", "group", "value", "n", "kind"]
    assert set(df.series.unique()) == _FIXCHG_SERIES
    assert set(df.group) == {"universe"} and set(df.kind) == {"house"}
    assert (df.n >= 2).all() and not df.isna().any().any()
    assert meta["basis"] == bt.BASIS == "reconstructed_current_membership"
    assert set(meta["series"]) == _FIXCHG_SERIES


# ---- committed dated / fixchg artifacts (skipped on a sparse tree) ---------
@_dated_needs
def test_regime_dated_committed_columns_kinds_floors():
    df = pd.read_parquet(_REGIME_DATED_PQ)
    assert list(df.columns) == ["date", "series", "group", "value", "n", "kind"]
    assert not any("ticker" in c or "price" in c for c in df.columns)
    assert set(df.kind) <= set(rg.KINDS)
    assert (df.n >= 2).all() and not df.isna().any().any()
    assert df.date.min() >= pd.Timestamp(rg.START_DATED)
    assert not df.duplicated(["series", "group", "date"]).any()
    # No member ticker leaks: a group is one of the 11 GICS sectors or the two
    # computed aggregates; a series is a lower-case snake_case name.
    assert set(df.group.unique()) <= _DATED_GROUPS
    assert all(s == s.lower() for s in df.series.unique())
    assert rg.MINIMUM_SERIES <= set(df.series.unique())
    assert not _FORBIDDEN.search(" ".join(df.series.unique()) + " " + " ".join(df.group.unique()))


@_dated_needs
def test_regime_dated_committed_sidecar():
    df = pd.read_parquet(_REGIME_DATED_PQ)
    meta = json.loads(_REGIME_DATED_META.read_text())
    assert _REGIME_DATED_META.stat().st_size < 30_000
    assert meta["basis"] == "reconstructed_dated_membership"
    assert meta["no_outcomes"] and not _FORBIDDEN.search(meta["no_outcomes"])
    assert meta["not_included"]
    firsts = df.groupby("series").date.min()
    kinds = df.groupby("series").kind.agg(lambda s: sorted(set(s)))
    assert set(meta["series"]) == set(df.series.unique())
    for s, entry in meta["series"].items():
        assert {"definition", "first_date", "source", "basis", "kind", "gaps"} <= set(entry)
        assert entry["first_date"] == str(firsts[s].date())
        ek = entry["kind"] if isinstance(entry["kind"], list) else [entry["kind"]]
        assert sorted(ek) == kinds[s]
    # counts only, no per-ticker sample lists in the committed sidecar
    assert not any(k.endswith("_sample") for k in meta["coverage"])
    assert isinstance(meta["dropped_partial_rows_count"], int)
    assert isinstance(meta["duplicate_series_pairs_count"], int)


@_fixchg_needs
def test_regime_fixchg_committed():
    df = pd.read_parquet(_REGIME_FIXCHG_PQ)
    assert list(df.columns) == ["date", "series", "group", "value", "n", "kind"]
    assert set(df.series.unique()) == _FIXCHG_SERIES
    assert set(df.group) == {"universe"} and set(df.kind) == {"house"}
    assert (df.n >= 2).all() and not df.isna().any().any()
    assert df.date.min() >= pd.Timestamp(rg.START)
    assert not df.duplicated(["series", "group", "date"]).any()
    meta = json.loads(_REGIME_FIXCHG_META.read_text())
    assert meta["basis"] == bt.BASIS
    assert set(meta["series"]) == _FIXCHG_SERIES
    assert not _FORBIDDEN.search(_REGIME_FIXCHG_META.read_text())


@_regime_needs
def test_regime_current_outputs_frozen():
    for name, want in _FROZEN_CURRENT.items():
        got = hashlib.sha256((HIST / name).read_bytes()).hexdigest()
        assert got == want, f"{name} was rewritten (frozen output)"
