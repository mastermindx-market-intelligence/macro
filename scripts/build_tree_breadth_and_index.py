"""Reconstructed breadth for the theme tree, plus equal-weight total-return indexes.

Off the render path; never run nightly. Inputs are one single-vintage, full-history
download held off git (scratch), the registries on main, and the yearly
second-source disagreement table measured against the Tiingo archive.

Writes to ``--out`` (default data/breadth/history):

  tree_breadth_weekly_current.parquet  (date, family, group) weekly fixed-set
      breadth for family ``subsector`` (268 groups in data/themes_heatmap/themes_tree.json)
      and family ``theme`` (its 40 parent themes); same engine functions as the
      sector history (``engine.group_breadth_history.weekly_fixed_set``).
  group_ew_index_weekly_current.parquet  (date, family, group) equal-weight
      total-return index level for families subsector, theme, basket
      (data/baskets/membership.json, active members) and sector (S&P 500 GICS sectors).
  group_ew_index_daily_current.parquet   the same index daily (only with --daily).
  tree_breadth_and_index_current.meta.json  sidecar.

Basis: ``reconstructed_current_membership``. Today's members applied to the past;
not point-in-time; survivors only. A name in several groups counts in each.

Start date: ``--start`` (the second-source rule date). Before it every value is
missing with reason ``second_source_disagreement``; no row is emitted before it.
Floors: share, change, rank and state at 10 counted members (engine MIN_MEMBERS);
index at 5 priced members (``INDEX_FLOOR``); counts at any size. Ranks are among
valid groups of the same family only.

No forward returns, no outcome relation, no threshold, no signal.

Usage:
  python scripts/build_tree_breadth_and_index.py --closes <scratch closes.parquet> \
      --download-meta <scratch download_meta.json> --disagreement <yearly csv> \
      --start 2000-01-01 [--daily] [--out data/breadth/history]
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
INDEX_FLOOR = 5
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
GROUP_SIZE_SENTENCE = ("In a 10-name group one name moves the share by 10 points, and a 13-week "
                       "change differences two such shares; a large group-level gap between "
                       "vendors can come from one name.")
SURVIVOR_INDEX_SENTENCE = ("The index holds only names alive today, so its past returns are "
                           "overstated, more so the further back and in themes with high failure "
                           "rates; relative turns between groups are less affected than levels, "
                           "and that is not tested here.")
INDEX_SENTENCE = ("A difference in dividend method shifts the long-run level of a total-return "
                  "index, not the timing of its turns.")
SOURCE_SENTENCE = ("These series sit on a different price source from the sector breadth "
                   "history (group_breadth_*_current.parquet, Tiingo archive); the two are "
                   "never joined or mixed.")
FLOOR_GAP_NOTE = ("On a session with fewer than 5 priced members the level is missing "
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
FAMILIES = [
    {"family": "subsector", "registry": "data/themes_heatmap/themes_tree.json", "loader": "tree_subsector",
     "outputs": ["breadth", "index"], "label": "themes_tree.json subsectors (group = subsector key)"},
    {"family": "theme", "registry": "data/themes_heatmap/themes_tree.json", "loader": "tree_theme",
     "outputs": ["breadth", "index"], "label": "themes_tree.json parent themes (group = theme key)"},
    {"family": "basket", "registry": "data/baskets/membership.json", "loader": "baskets",
     "outputs": ["index"], "label": "baskets, active members (basket breadth stays in "
                                    "basket_breadth_*_current.parquet on archive prices)"},
    {"family": "sector", "registry": "data/breadth/constituents.parquet", "loader": "constituents_sector",
     "outputs": ["index"], "label": "S&P 500 GICS sectors (sector breadth stays in "
                                    "group_breadth_*_current.parquet on archive prices)"},
]


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
        w = gbh.weekly_fixed_set(wide, emem, groups=groups, include_last_partial_week=False)
        w = w[w["date"] >= start]
        w.insert(1, "family", fam)
        out.append(w)
    return pd.concat(out, ignore_index=True)


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
            parts.append(pd.DataFrame({"date": closes.index[keep], "family": fam, "group": g,
                                       "level": lvl[keep].round(6).values,
                                       "n_priced": n[keep].values, "reason": reason[keep].values}))
    return pd.concat(parts, ignore_index=True)


def to_weekly(daily: pd.DataFrame, index: pd.DatetimeIndex) -> pd.DataFrame:
    rows = gbh.week_end_rows(index)
    if len(rows) and index[rows[-1]].dayofweek < 3:
        rows = rows[:-1]                       # same partial-week rule as weekly_fixed_set
    return daily[daily["date"].isin(index[rows])].reset_index(drop=True)


# ---------------------------------------------------------------- build
def _sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def first_valid(df: pd.DataFrame, col: str) -> dict:
    v = df.dropna(subset=[col]).groupby(["family", "group"])["date"].min()
    return {f"{f}/{g}": str(pd.Timestamp(d).date()) for (f, g), d in v.items()}


def build(closes_path: Path, download_meta: Path, disagreement: Path, start: str,
          out: Path, root: Path = _ROOT, daily: bool = False,
          families: list[dict] = FAMILIES) -> dict:
    start_ts = pd.Timestamp(start)
    closes = pd.read_parquet(closes_path).sort_index()
    closes = gbh.through_last_complete_row(closes)
    fams = load_families(root, families)
    mems = {f: m for f, (_, m) in fams.items()}
    b_fams = {f: m for f, (s, m) in fams.items() if "breadth" in s["outputs"]}
    i_fams = {f: m for f, (s, m) in fams.items() if "index" in s["outputs"]}

    breadth = tree_breadth_weekly(closes, b_fams, start_ts)
    idx_daily = ew_index_daily(closes, i_fams, start_ts)
    idx_weekly = to_weekly(idx_daily, closes.index)

    out.mkdir(parents=True, exist_ok=True)
    files = {"tree_breadth_weekly_current.parquet": breadth,
             "group_ew_index_weekly_current.parquet": idx_weekly}
    if daily:
        files["group_ew_index_daily_current.parquet"] = idx_daily
    for name, df in files.items():
        df.to_parquet(out / name, index=False, compression="zstd")

    dm = json.loads(Path(download_meta).read_text())
    tab = pd.read_csv(disagreement, index_col=0)
    priced = set(closes.columns[closes.notna().any()])
    members = {}
    for fam, mem in mems.items():
        members[fam] = {"groups": int(mem["group"].nunique()), "tickers": int(mem["ticker"].nunique()),
                        "slots": int(len(mem)),
                        "tickers_priced": len(set(mem["ticker"]) & priced),
                        "unpriced": sorted(set(mem["ticker"]) - priced)}
    last_week = breadth["date"].max()
    lw = breadth[breadth["date"] == last_week]
    meta = {
        "basis": BASIS, "basis_note": BASIS_NOTE,
        "families": {f: {"registry": s["registry"], "registry_sha256": _sha(root / s["registry"]),
                         "outputs": s["outputs"], "label": s["label"]} for f, (s, _) in fams.items()},
        "multi_group": "a name in several groups counts in each",
        "price_source": "yfinance yf.download(auto_adjust=True, period='max'), one single-vintage "
                        "download, held off git; never the collector cache or data/yahoo",
        "price_vintage": dm.get("vintage"), "price_retry": dm.get("retry"),
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
        "floors": {"share_change_rank_state": gbh.MIN_MEMBERS, "index": INDEX_FLOOR,
                   "counts": "any size", "rank": "among valid groups of the same family"},
        "index": {"rebalance_rule": REBALANCE_RULE, "return": "total return (auto_adjust closes)",
                  "floor_gap": FLOOR_GAP_NOTE, "dividend_effect": INDEX_SENTENCE,
                  "survivors_only_effect": SURVIVOR_INDEX_SENTENCE,
                  "daily_committed": bool(daily)},
        "members": members,
        "valid_last_week": {f: int(lw[(lw.family == f)][gbh.HEADLINE].notna().sum())
                            for f in b_fams},
        "first_valid_breadth": first_valid(breadth, gbh.HEADLINE),
        "first_valid_index": first_valid(idx_weekly, "level"),
        "rows": {k: int(len(v)) for k, v in files.items()},
        "engine": "engine.group_breadth_history.weekly_fixed_set; engine.baskets._ew_level",
        "no_outcomes": "no forward returns, no outcome relation, no threshold, no signal",
    }
    (out / "tree_breadth_and_index_current.meta.json").write_text(json.dumps(meta, indent=1) + "\n")
    return meta


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--closes", type=Path, required=True)
    ap.add_argument("--download-meta", type=Path, required=True)
    ap.add_argument("--disagreement", type=Path, required=True)
    ap.add_argument("--start", required=True)
    ap.add_argument("--out", type=Path, default=_ROOT / "data/breadth/history")
    ap.add_argument("--daily", action="store_true")
    a = ap.parse_args()
    m = build(a.closes, a.download_meta, a.disagreement, a.start, a.out, daily=a.daily)
    print(json.dumps({"rows": m["rows"], "valid_last_week": m["valid_last_week"],
                      "last_week": m["last_week"]}))


if __name__ == "__main__":
    main()
