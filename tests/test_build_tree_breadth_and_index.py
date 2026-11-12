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
    res = bt.build(cp, dm, dis, "1999-06-01", out, root=root, daily=True, families=tree_fams)
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


# --- Vendor rights (COO ruling 32 s1, 2026-11-12) ---
# Vendor-tree breadth series stay internal (COO ruling 32 s1, 2026-11-12).
# 
# The subsector and theme families come from the finviz_themes tree, recorded at
# config/theme_sources.yml:33 as internal-only with no public or customer display
# rights. Their files live under data/breadth/history/internal_only/. These tests
# fail if a site builder, template, rendered page or publish script names those
# files, or if the vendor sidecar loses its rights fields.

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
