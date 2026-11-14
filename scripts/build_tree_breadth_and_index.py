"""Reconstructed breadth for the theme tree, plus equal-weight total-return indexes.

Off the render path; never run nightly. Inputs are one single-vintage, full-history
download held off git (scratch), the registries on main, and the yearly
second-source disagreement table measured against the Tiingo archive.

Writes one file set per rights class (``RIGHTS_SETS``):

  house (plain path under ``--out``, default data/breadth/history):
      house_breadth_weekly_current.parquet (breadth families, when
      any), house_ew_index_{weekly,daily}_current.parquet, house_breadth_and_index_current.meta.json
      — families basket (data/baskets/membership.json, active members) and sector
      (S&P 500 GICS sectors), and later house families such as the GMI graph's.
  internal_only (``--vendor-out``, default /tmp/si_plan/quant/vendor_out, outside the
      repository tree): vendor_internal_only_breadth_weekly_current.parquet,
      vendor_internal_only_ew_index_{weekly,daily}_current.parquet and its sidecar —
      the vendor tree's 268 subsectors and 40 parent themes
      (data/themes_heatmap/themes_tree.json, source family finviz_themes). Internal
      research data under the Chairman's gate 2 ruling (config/theme_sources.yml:33):
      never displayed or published. The repository is public, so these files are kept
      off git, in scratch (COO ruling 38 §2b); they are never committed or pushed.

Breadth is the weekly fixed-set change (``engine.group_breadth_history.weekly_fixed_set``);
the index is a (date, family, group) equal-weight total-return level.

Basis: ``reconstructed_current_membership``. Today's members applied to the past;
not point-in-time; survivors only. A name in several groups counts in each.

Start date: ``--start`` (the second-source rule date). Before it every value is
missing with reason ``second_source_disagreement``; no row is emitted before it.
Floors (COO ruling 34 s2, replacing the floors of rulings 27, 31 and 32 for these
files): share, change, rank and state from 2 counted members (``BREADTH_FLOOR``),
each share committed with ``n_above_200`` and ``n_counted_200`` beside it; index
from 2 priced members (``INDEX_FLOOR``). A one-member group has no series.
``size_class`` per group per date: ``small`` under 10 counted members, else
``standard``. Ranks are within the same family AND size class on each date only.
The live engine's own floor (engine MIN_MEMBERS) is unchanged.

No forward returns, no outcome relation, no threshold, no signal.

Usage:
  python scripts/build_tree_breadth_and_index.py --closes <scratch closes.parquet> \
      --download-meta <scratch download_meta.json> --disagreement <yearly csv> \
      --start 2000-01-01 [--daily [house internal_only]] [--out data/breadth/history]
      [--vendor-out /tmp/si_plan/quant/vendor_out]

``--daily`` alone writes the daily index for every rights class; with class names it
writes it for those only (house only: the committed set keeps the total under 25 MB, a working size figure, not a repository rule).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

import hashlib  # noqa: E402

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from engine import group_breadth_history as gbh  # noqa: E402
from engine.baskets import _ew_level  # noqa: E402

BASIS = "reconstructed_current_membership"
BASIS_NOTE = "today's members applied to the past; not point-in-time; survivors only"
INDEX_FLOOR = 2
BREADTH_FLOOR = 2
SIZE_STANDARD = 10
REASON_START = "second_source_disagreement"
REASON_FLOOR = "below_index_member_floor"
_SEP = "@"

REBALANCE_RULE = ("engine.baskets._ew_level: each session the index return is the plain mean "
                  "of the daily total returns of the members priced that session (daily "
                  "rebalance to equal weight), chained from 1.0 on the group's first valid session")
DIVIDEND_SENTENCE = ("Before about 2000 the two price vendors (this download and the Tiingo "
                     "archive behind the sector history) apply dividend adjustment differently "
                     "in old history; neither is shown to be right. The yearly name-week "
                     "disagreement table below states the rate.")
GROUP_SIZE_SENTENCE = ("In a group of n members the share moves in steps of 100/n; read a small "
                       "group's share as a count (n_above_200 of n_counted_200). A 13-week change "
                       "differences two such shares, so in a small group one name moves it a lot.")
SURVIVOR_INDEX_SENTENCE = ("The index holds only names alive today, so its past returns are "
                           "overstated, more so the further back and in themes with high failure "
                           "rates; relative turns between groups are less affected than levels, "
                           "and that is not tested here.")
INDEX_SENTENCE = ("A difference in dividend method shifts the long-run level of a total-return "
                  "index, not the timing of its turns.")
SOURCE_SENTENCE = ("These series sit on a different price source from the sector breadth "
                   "history (group_breadth_*_current.parquet, Tiingo archive); the two are "
                   "never joined or mixed.")
FLOOR_GAP_NOTE = ("On a session with fewer than 2 priced members the level is missing "
                  "(reason below_index_member_floor) and that session carries no return; the "
                  "chain resumes from the last valid level.")


# ---------------------------------------------------------------- registries
def tree_membership(path: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(ticker, group) for subsectors (group = subsector key) and themes (group = theme key)."""
    tree = json.loads(Path(path).read_text())
    sub = [{"ticker": m, "group": s["key"]} for th in tree for s in th["subsectors"] for m in s["members"]]
    thm = [{"ticker": m, "group": th["key"]} for th in tree for s in th["subsectors"] for m in s["members"]]
    f = lambda r: pd.DataFrame(r, columns=["ticker", "group"]).drop_duplicates()  # noqa: E731
    return f(sub), f(thm)


def basket_membership(path: Path) -> pd.DataFrame:
    doc = json.loads(Path(path).read_text())
    rows = [{"ticker": m["ticker"], "group": bid}
            for bid, b in doc["baskets"].items() for m in b["members"] if not m.get("removed")]
    return pd.DataFrame(rows, columns=["ticker", "group"]).drop_duplicates()


def sector_membership(path: Path) -> pd.DataFrame:
    c = pd.read_parquet(path)
    return pd.DataFrame({"ticker": c.index.astype(str), "group": c["sector"].astype(str).values})


def pairs_membership(path: Path) -> pd.DataFrame:
    """Generic registry: a file of (ticker, group) rows — .parquet/.csv with those two
    columns, or .json as a list of {"ticker", "group"} objects. A new family needs only
    such a file and an entry in ``FAMILIES``; no new code."""
    p = Path(path)
    if p.suffix == ".parquet":
        df = pd.read_parquet(p)
    elif p.suffix == ".csv":
        df = pd.read_csv(p)
    else:
        df = pd.DataFrame(json.loads(p.read_text()))
    return df[["ticker", "group"]].astype(str).drop_duplicates().reset_index(drop=True)


LOADERS = {
    "tree_subsector": lambda p: tree_membership(p)[0],
    "tree_theme": lambda p: tree_membership(p)[1],
    "baskets": basket_membership,
    "constituents_sector": sector_membership,
    "pairs": pairs_membership,
}

# One entry per family: label, registry path (repo-relative), loader, and outputs.
# ``breadth`` -> weekly fixed-set breadth file; ``index`` -> equal-weight index files.
GROUP_ID_NOTE = ("gmi_theme and gmi_macro_category group ids are the theme graph's own node ids, unchanged; macro categories are graph nodes of kind theme at tier macro_category, so they carry the theme: prefix too")

FAMILIES = [
    {"family": "subsector", "registry": "data/themes_heatmap/themes_tree.json", "loader": "tree_subsector",
     "rights_class": "internal_only", "outputs": ["breadth", "index"], "label": "themes_tree.json subsectors (group = subsector key)"},
    {"family": "theme", "registry": "data/themes_heatmap/themes_tree.json", "loader": "tree_theme",
     "rights_class": "internal_only", "outputs": ["breadth", "index"], "label": "themes_tree.json parent themes (group = theme key)"},
    {"family": "basket", "registry": "data/baskets/membership.json", "loader": "baskets",
     "rights_class": "house", "outputs": ["index"], "label": "baskets, active members (basket breadth stays in "
                                    "basket_breadth_*_current.parquet on archive prices)"},
    {"family": "sector", "registry": "data/breadth/constituents.parquet", "loader": "constituents_sector",
     "rights_class": "house", "outputs": ["index"], "label": "S&P 500 GICS sectors (sector breadth stays in "
                                    "group_breadth_*_current.parquet on archive prices)"},
    {"family": "gmi_theme", "registry": "data/breadth/history/registry/gmi_theme.csv", "loader": "pairs",
     "rights_class": "house", "outputs": ["breadth", "index"],
     "label": "GMI house themes (18 themes, 15 with US-listed members): open latest-belief company->basket->theme edges of "
              "data/theme_graph, US-listed resolved identities; exported by "
              "scripts/export_gmi_history_registry.py at the commit in group_links_current.meta.json"},
    {"family": "gmi_macro_category", "registry": "data/breadth/history/registry/gmi_macro_category.csv",
     "loader": "pairs", "rights_class": "house", "outputs": ["breadth", "index"],
     "label": "GMI macro categories (10 macro categories, 7 with US-listed members): gmi_theme members rolled up through open PARENT_OF edges"},
    {"family": "rel_customers_of", "registry": "data/breadth/history/registry/rel_customers_of.csv",
     "loader": "pairs", "rights_class": "house", "outputs": ["breadth", "index"],
     "basis": "proposed_relationships_unadmitted",
     "label": "customers of a supplier hub (group = the supplier: TSM, UMC, AMKR, GFS), from the "
              "proposed edges of relationship_edges.json, roles normalised"},
    {"family": "rel_suppliers_of", "registry": "data/breadth/history/registry/rel_suppliers_of.csv",
     "loader": "pairs", "rights_class": "house", "outputs": ["breadth", "index"],
     "basis": "proposed_relationships_unadmitted",
     "label": "suppliers of a customer hub (group = the customer: AAPL, FTNT, INTC), from the "
              "proposed edges of relationship_edges.json, roles normalised"},
]

# Relationship families (COO ruling 32 s2): proposed, unadmitted edges.
REL_NOTE = {
    "basis": "proposed_relationships_unadmitted",
    "precision": {"value": 0.6621, "basis": "stratum-weighted, 100-item owner sample, Wilson 95% "
                                             "[0.5596, 0.7646]",
                  "source": "research/theme_graph/GMI_O5_VERIFICATION_VERDICTS_2026-11-02.md:210"},
    "recall": {"value": 0.3487, "basis": "83/238, 31 issuers, Wilson 95% [0.291, 0.4113]",
               "source": "research/theme_graph/GMI_O5_VERIFICATION_VERDICTS_2026-11-02.md:201"},
    "sentence": ("About one member in three may be wrong, and about two in three true members are "
                 "missing. Today's proposed edges are applied to the past."),
    "hubs_note": "All seven hubs are chips and hardware companies.",
    "hub_rule": "hubs are the companies with 5 or more counterparties (ruling 32); no further "
                "relationship series until the edge set grows",
}


def load_families(root: Path, specs: list[dict] = FAMILIES) -> dict[str, tuple[dict, pd.DataFrame]]:
    fams = {}
    for s in specs:
        if s["family"] in fams:
            raise ValueError(f"duplicate family {s['family']}")
        fams[s["family"]] = (s, LOADERS[s["loader"]](root / s["registry"]))
    return fams


def expand_multi(closes: pd.DataFrame, mem: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """One column per (ticker, group) so a name counts in every group it belongs to."""
    m = mem[mem["ticker"].isin(closes.columns)]
    keys = (m["ticker"] + _SEP + m["group"]).tolist()
    wide = (pd.concat({k: closes[t] for k, t in zip(keys, m["ticker"])}, axis=1)
            if keys else pd.DataFrame(index=closes.index))
    return wide, pd.DataFrame({"ticker": keys, "group": m["group"].tolist()})


# ---------------------------------------------------------------- breadth
def tree_breadth_weekly(closes: pd.DataFrame, families: dict[str, pd.DataFrame],
                        start: pd.Timestamp) -> pd.DataFrame:
    """Weekly fixed-set breadth per family; flags use full history, rows from ``start``."""
    out = []
    for fam, mem in families.items():
        wide, emem = expand_multi(closes, mem)
        groups = sorted(mem["group"].unique())
        w = gbh.weekly_fixed_set(wide, emem, groups=groups, include_last_partial_week=False,
                                 min_members=BREADTH_FLOOR)
        w = w[w["date"] >= start].copy()
        w.insert(1, "family", fam)
        out.append(w)
    return with_size_class(pd.concat(out, ignore_index=True))


def with_size_class(b: pd.DataFrame) -> pd.DataFrame:
    """Counts beside every share, ``size_class`` per group per date, and every rank
    recomputed within (date, family, size_class): no rank across classes."""
    b = b.rename(columns={"n_has_200": "n_counted_200"})
    n = b["n_counted_200"]
    b.insert(b.columns.get_loc("pct_above_200"), "n_above_200",
             (b["pct_above_200"] * n / 100).round().astype("Int64"))
    b.insert(3, "size_class", np.where(n < SIZE_STANDARD, "small", "standard"))
    keys = [b["date"], b["family"], b["size_class"]]
    for c in [c for c in b.columns if c.startswith("fix_chg_")]:
        g = b[c].groupby(keys)
        b[f"rank_{c}"] = g.rank(method="min", ascending=False)
        b[f"n_ranked_{c}"] = g.transform("count").astype("int32")
    return b


# ---------------------------------------------------------------- index
def group_index(rets: pd.DataFrame, members: list[str], start: pd.Timestamp,
                floor: int = INDEX_FLOOR,
                priced: pd.DataFrame | None = None) -> tuple[pd.Series, pd.Series, pd.Series]:
    """(level, n_priced, reason) daily for one group, via the existing _ew_level convention.

    ``n_priced`` counts members with a close that session (``priced``; defaults to
    members with a return). The floor applies to that count."""
    idx = rets.index
    present = [t for t in members if t in rets.columns]
    sub = rets[present] if present else pd.DataFrame(index=idx)
    has = (priced[present] if priced is not None else sub.notna()) if present else sub
    n = has.sum(axis=1).astype("int64")
    ok = (n >= floor) & (idx >= start)
    gated = sub.where(ok, axis=0)
    roster = [{"ticker": t, "added": str(start.date()), "removed": None} for t in present]
    lvl = _ew_level(gated, roster, idx) if present else pd.Series(np.nan, index=idx)
    lvl = lvl.where(ok)
    reason = pd.Series(None, index=idx, dtype=object)
    reason[idx < start] = REASON_START
    reason[(idx >= start) & ~ok] = REASON_FLOOR
    return lvl, n, reason


def ew_index_daily(closes: pd.DataFrame, families: dict[str, pd.DataFrame],
                   start: pd.Timestamp) -> pd.DataFrame:
    rets = closes.pct_change(fill_method=None)
    rets = rets.where(closes.notna() & closes.shift(1).notna())
    priced = closes.notna()
    parts = []
    for fam, mem in families.items():
        for g, sub in mem.groupby("group", sort=True):
            lvl, n, reason = group_index(rets, sub["ticker"].tolist(), start, priced=priced)
            keep = closes.index >= start
            nk = n[keep].values
            parts.append(pd.DataFrame({"date": closes.index[keep], "family": fam, "group": g,
                                       "size_class": np.where(nk < SIZE_STANDARD, "small", "standard"),
                                       "level": lvl[keep].round(6).values,
                                       "n_priced": nk, "reason": reason[keep].values}))
    return pd.concat(parts, ignore_index=True)


def to_weekly(daily: pd.DataFrame, index: pd.DatetimeIndex) -> pd.DataFrame:
    rows = gbh.week_end_rows(index)
    if len(rows) and index[rows[-1]].dayofweek < 3:
        rows = rows[:-1]                       # same partial-week rule as weekly_fixed_set
    return daily[daily["date"].isin(index[rows])].reset_index(drop=True)


# ---------------------------------------------------------------- build
def _sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def single_name_groups(mem: pd.DataFrame) -> list[str]:
    n = mem.groupby("group")["ticker"].nunique()
    return sorted(n[n < 2].index)


def _by_class_last(b: pd.DataFrame) -> dict:
    lw = b[(b["date"] == b["date"].max()) & b[gbh.HEADLINE].notna()]
    return {f: {k: int(v) for k, v in g["size_class"].value_counts().items()}
            for f, g in lw.groupby("family")}


def _index_last(w: pd.DataFrame) -> dict:
    lw = w[(w["date"] == w["date"].max()) & w["level"].notna()]
    return {f: int(n) for f, n in lw.groupby("family").size().items()}


def first_valid(df: pd.DataFrame, col: str) -> dict:
    v = df.dropna(subset=[col]).groupby(["family", "group"])["date"].min()
    return {f"{f}/{g}": str(pd.Timestamp(d).date()) for (f, g), d in v.items()}


# Output sets by rights class (COO ruling 32 s1). Vendor-tree families are internal
# research data: their files carry the class in the name. The repository is public,
# so the vendor set is written to scratch outside the tree (VENDOR_OUT_DEFAULT) and
# never committed or pushed (COO ruling 38 §2b); house families keep the plain names
# under --out.
VENDOR_OUT_DEFAULT = Path("/tmp/si_plan/quant/vendor_out")
RIGHTS_SETS = {
    "house": {"dir": "", "prefix": "house",
              "breadth": "house_breadth_weekly_current.parquet",
              "index_weekly": "house_ew_index_weekly_current.parquet",
              "index_daily": "house_ew_index_daily_current.parquet",
              "meta": "house_breadth_and_index_current.meta.json"},
    "internal_only": {"dir": "internal_only", "prefix": "vendor_internal_only",
                      "breadth": "vendor_internal_only_breadth_weekly_current.parquet",
                      "index_weekly": "vendor_internal_only_ew_index_weekly_current.parquet",
                      "index_daily": "vendor_internal_only_ew_index_daily_current.parquet",
                      "meta": "vendor_internal_only_breadth_and_index_current.meta.json"},
}
VENDOR_RIGHTS = {
    "source_family": "finviz_themes",
    "rights_class": "internal_only",
    "rights_source": "config/theme_sources.yml:33",
    "rights_sentence": ("retained internal-only. NO public/customer display or redistribution "
                        "rights granted"),
    "use": ("internal research data: no name or number from these families goes to any site "
            "page, site data file, Terminal surface, member page or public bucket (COO ruling 32)"),
}


def _write_set(rights: str, fams: dict, closes: pd.DataFrame, start_ts: pd.Timestamp, out: Path,
               root: Path, daily: bool, dm: dict, tab: pd.DataFrame, vendor_out: Path) -> dict:
    spec = RIGHTS_SETS[rights]
    mems = {f: m for f, (_, m) in fams.items()}
    single = {f: single_name_groups(m) for f, m in mems.items()}
    series = {f: m[~m["group"].isin(single[f])] for f, m in mems.items()}
    b_fams = {f: series[f] for f, (s, _) in fams.items() if "breadth" in s["outputs"]}
    i_fams = {f: series[f] for f, (s, _) in fams.items() if "index" in s["outputs"]}
    d = vendor_out if rights == "internal_only" else (out / spec["dir"] if spec["dir"] else out)
    d.mkdir(parents=True, exist_ok=True)
    files = {}
    breadth = tree_breadth_weekly(closes, b_fams, start_ts) if b_fams else None
    if breadth is not None:
        files[spec["breadth"]] = breadth
    idx_daily = ew_index_daily(closes, i_fams, start_ts) if i_fams else None
    idx_weekly = to_weekly(idx_daily, closes.index) if idx_daily is not None else None
    if idx_weekly is not None:
        files[spec["index_weekly"]] = idx_weekly
        if daily:
            files[spec["index_daily"]] = idx_daily
        elif (d / spec["index_daily"]).exists():
            (d / spec["index_daily"]).unlink()      # never leave a stale daily file
    for name, df in files.items():
        df.to_parquet(d / name, index=False, compression="zstd")
    priced = set(closes.columns[closes.notna().any()])
    members = {f: {"groups": int(m["group"].nunique()), "tickers": int(m["ticker"].nunique()),
                   "slots": int(len(m)), "tickers_priced": len(set(m["ticker"]) & priced),
                   "unpriced": sorted(set(m["ticker"]) - priced)} for f, m in mems.items()}
    last_dates = [x["date"].max() for x in (breadth, idx_weekly) if x is not None]
    last_week = max(last_dates)
    meta = {"rights_class": rights}
    if rights == "internal_only":
        meta.update(VENDOR_RIGHTS)
    rel = sorted(f for f, (s, _) in fams.items() if s.get("basis") == REL_NOTE["basis"])
    if rel:
        meta["relationship_families"] = {"families": rel, **REL_NOTE}
    meta.update({
        "basis": BASIS, "basis_note": BASIS_NOTE,
        "families": {f: {"registry": s["registry"], "registry_sha256": _sha(root / s["registry"]),
                         "rights_class": s["rights_class"], "outputs": s["outputs"], "label": s["label"],
                         "basis": s.get("basis", BASIS)}
                     for f, (s, _) in fams.items()},
        "multi_group": "a name in several groups counts in each",
        "group_ids": GROUP_ID_NOTE,
        "price_source": "yfinance yf.download(auto_adjust=True, period='max'), one single-vintage "
                        "download, held off git; never the collector cache or data/yahoo",
        "price_vintage": dm.get("vintage"), "price_retry": dm.get("retry"),
        "price_topup": dm.get("topup"),
        "aliases": {"MMC": "MRSH", "FI": "FISV"},
        "data_end": str(closes.index.max().date()), "last_week": str(pd.Timestamp(last_week).date()),
        "source_sentence": SOURCE_SENTENCE,
        "start": {"date": str(start_ts.date()), "reason_before": REASON_START,
                  "rule": "first January 1 from which every later calendar year has name-week "
                          "above-200 flag disagreement against the Tiingo archive of 0.5% or less "
                          "(S&P 500 members priced in both, weeks where both hold 200 sessions)",
                  "note": "200-session averages use the full download, so the first weeks after "
                          "the start read flags from late in the prior year"},
        "second_source_disagreement_by_year": {
            str(y): {"name_weeks": int(r["both"]), "disagree": int(r["flag_dis"]),
                     "rate": round(float(r["rate"]), 5)} for y, r in tab.iterrows()},
        "dividend_sentence": DIVIDEND_SENTENCE, "group_size_sentence": GROUP_SIZE_SENTENCE,
        "floors": {"share_change_rank_state": BREADTH_FLOOR, "index": INDEX_FLOOR,
                   "counts": "any size", "single_name": "a one-member group has no series; the "
                   "links table marks it single_name (the stock is the series)",
                   "size_class": f"small under {SIZE_STANDARD} counted members on that date, "
                                 "else standard",
                   "rank": "within the same family and size class on each date; no rank across "
                           "classes",
                   "source": "COO ruling 34 s2 (replaces the floors of rulings 27, 31 and 32 for "
                             "these files); the live engine's floor is unchanged"},
        "single_name_groups": {f: g for f, g in single.items() if g},
        "index": {"rebalance_rule": REBALANCE_RULE, "return": "total return (auto_adjust closes)",
                  "floor_gap": FLOOR_GAP_NOTE, "dividend_effect": INDEX_SENTENCE,
                  "survivors_only_effect": SURVIVOR_INDEX_SENTENCE,
                  "daily_committed": bool(daily),
                  "daily_note": (None if daily else
                                 "the daily index of this class is not committed (it would take the "
                                 "committed files over 25 MB, a working size figure, not a repository rule); weekly is "
                                 "committed and the daily "
                                 "rebuilds from the scratch download with --daily")},
        "members": members,
        "valid_last_week": ({f: int(breadth[(breadth["date"] == breadth["date"].max())
                                             & (breadth.family == f)][gbh.HEADLINE].notna().sum())
                             for f in b_fams} if breadth is not None else {}),
        "valid_last_week_by_size_class": (_by_class_last(breadth) if breadth is not None else {}),
        "index_valid_last_week": (_index_last(idx_weekly) if idx_weekly is not None else {}),
        "first_valid_breadth": first_valid(breadth, gbh.HEADLINE) if breadth is not None else {},
        "first_valid_index": first_valid(idx_weekly, "level") if idx_weekly is not None else {},
        "files": sorted(str((d / n).relative_to(out if d.is_relative_to(out) else d)) for n in files),
        "rows": {k: int(len(v)) for k, v in files.items()},
        "engine": "engine.group_breadth_history.weekly_fixed_set; engine.baskets._ew_level",
        "no_outcomes": "no forward returns, no outcome relation, no threshold, no signal",
    })
    (d / spec["meta"]).write_text(json.dumps(meta, indent=1) + "\n")
    return meta


def build(closes_path: Path, download_meta: Path, disagreement: Path, start: str,
          out: Path, root: Path = _ROOT, daily: bool | set[str] = False,
          families: list[dict] = FAMILIES, vendor_out: Path | None = None) -> dict:
    """Build every family; write one file set per rights class. Returns {rights_class: meta}.

    The internal_only set goes to ``vendor_out`` (default VENDOR_OUT_DEFAULT, outside
    the repository tree, off git); the house set goes under ``out``."""
    start_ts = pd.Timestamp(start)
    closes = gbh.through_last_complete_row(pd.read_parquet(closes_path).sort_index())
    fams = load_families(root, families)
    dm = json.loads(Path(download_meta).read_text())
    tab = pd.read_csv(disagreement, index_col=0)
    by_class: dict[str, dict] = {}
    for f, (s, m) in fams.items():
        if s.get("rights_class") not in RIGHTS_SETS:
            raise ValueError(f"family {f}: rights_class must be one of {sorted(RIGHTS_SETS)}")
        by_class.setdefault(s["rights_class"], {})[f] = (s, m)
    want = (lambda rc: rc in daily) if isinstance(daily, (set, frozenset, list, tuple)) \
        else (lambda rc: bool(daily))
    vout = Path(vendor_out) if vendor_out is not None else VENDOR_OUT_DEFAULT
    return {rc: _write_set(rc, fs, closes, start_ts, out, root, want(rc), dm, tab, vout)
            for rc, fs in sorted(by_class.items())}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--closes", type=Path, required=True)
    ap.add_argument("--download-meta", type=Path, required=True)
    ap.add_argument("--disagreement", type=Path, required=True)
    ap.add_argument("--start", required=True)
    ap.add_argument("--out", type=Path, default=_ROOT / "data/breadth/history")
    ap.add_argument("--vendor-out", type=Path, default=VENDOR_OUT_DEFAULT,
                    help="scratch directory for the internal_only set (off git; public repository)")
    ap.add_argument("--daily", nargs="*", default=None, choices=sorted(RIGHTS_SETS))
    a = ap.parse_args()
    daily = False if a.daily is None else (set(a.daily) if a.daily else True)
    res = build(a.closes, a.download_meta, a.disagreement, a.start, a.out, daily=daily,
                vendor_out=a.vendor_out)
    print(json.dumps({rc: {"files": m["files"], "valid_last_week": m["valid_last_week"],
                           "last_week": m["last_week"]} for rc, m in res.items()}))


if __name__ == "__main__":
    main()
