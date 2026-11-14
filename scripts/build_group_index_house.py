"""House group price indexes (COO ruling 38 Part B + continuation) — in-repo producer.

Builds the eight committed house files (default --out data/breadth/history/):
  group_index_daily_dated.parquet               sectors, sp500 dated membership
  group_index_daily_current_sensitivity.parquet sectors + baskets, today's members
  group_index.meta.json                         counts-only sidecar
  group_index_key_map.csv                       group_key, level, engine_key, spdr_parent
  group_index_basket_daily_dated.parquet        baskets, recorded [added, removed) windows
  group_index_basket_daily_dated.meta.json      counts-only sidecar
  group_index_daily_dated_sp400_sp600.parquet   sectors per universe, never pooled
  group_index_daily_dated_sp400_sp600.meta.json counts-only sidecar

The method is the ruling-38 builders' method verbatim: engine.baskets._ew_level
(called, not copied), the dated loaders in scripts/build_group_breadth_history.py
(membership_dated, drop_partial_rows, duplicate_series_pairs, count_duplicates_once,
unpriced_in_window) and the pinned floor-gating convention in
scripts/build_tree_breadth_and_index.py (group_index). Floor of 5 priced members.
Group-level numbers and counts only: no member ticker, price or per-security date
is written. Nothing is fetched; every input is a required command-line argument:

  python3 scripts/build_group_index_house.py \
      --closes <sector-universe daily adjusted closes parquet> \
      --basket-closes <basket-member daily adjusted closes parquet> \
      --membership-dir <dir with sp1500_pit_membership.parquet, \
          sp1500_pit_sectors.parquet, constituents.parquet> \
      --basket-membership <basket membership JSON (seed_date + added/removed)> \
      --out <output directory>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))

from engine.baskets import _ew_level                       # noqa: E402
from engine.neuralweb.sector_map import GICS_TO_ETF        # noqa: E402
from scripts import build_group_breadth_history as gbh_b   # noqa: E402
from scripts import build_tree_breadth_and_index as bt     # noqa: E402

FLOOR = 5
DATED_BASIS = "reconstructed_dated_membership"
CURRENT_BASIS = "reconstructed_current_membership"
SEED = "2023-05-09"

PRICE_NOTE = ("Total return = the dividend-adjusted close already used in the breadth history. "
              "Adjusted closes are today's restated values (split and dividend adjustment as of "
              "the Tiingo archive capture 2026-10-11..16), not the prices printed at the time. "
              "Data end 2026-10-09.")
REDIST_NOTE = ("Group-level index levels and counts only; no member prices, tickers or "
               "per-security dates. Member-level history stays off git.")
INDEX_RULES = {
    "rebalance_rule": ("engine.baskets._ew_level: equal-weight daily total-return level, cumprod "
                       "of (1 + EW daily return) from 1.0 at the first active session; a member "
                       "counts only inside its membership window"),
    "return": "total return (dividend-adjusted close)",
    "floor": FLOOR,
    "floor_rule": ("first date per key = earliest session with at least 5 priced members; rows "
                   "below 5 keep n_priced_members with a blank index"),
    "floor_gap": ("below-floor sessions are blank; the chain stays flat across the gap and "
                  "resumes from the last valid level"),
}
NO_OUTCOMES = ("Data only. Descriptive group levels and counts. No outcome relation, no backtest, "
               "no hit rate, no signal, ranking or score column.")
DROPPED_RULE = ("centred 21-row median of priced names; a row under half is dropped "
                "(data cleaning, not a signal rule)")
DUP_RULE = ("month-by-month hash of daily returns, then pairwise check: >=60 identical returns "
            "and >=95% identical between first and last identical session; the second ticker is "
            "counted once over the span. Detection and labelling only; no store repaired. Pair "
            "tickers are not committed (group-level counts only).")


def sha16(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()[:16]


def sha256(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def rets_priced(closes: pd.DataFrame):
    rets = closes.pct_change(fill_method=None)
    rets = rets.where(closes.notna() & closes.shift(1).notna())
    return rets, closes.notna()


def dated_index(rets, mem, priced, floor):
    """One sector, dated [start,end) windows, via _ew_level. Returns (level, n_priced)."""
    idx = rets.index
    present = sorted({t for t in mem["ticker"] if t in rets.columns})
    if not present:
        return pd.Series(np.nan, index=idx), pd.Series(0, index=idx, dtype="int64")
    win = pd.DataFrame(False, index=idx, columns=present)
    for r in mem.itertuples(index=False):
        t = r.ticker
        if t not in win.columns:
            continue
        a = pd.Timestamp(r.start_date) if pd.notna(r.start_date) else idx.min()
        e = pd.Timestamp(r.end_date) if pd.notna(r.end_date) else None
        m = idx >= a
        if e is not None:
            m = m & (idx < e)
        win[t] = win[t] | m
    has = priced[present] & win
    n = has.sum(axis=1).astype("int64")
    ok = n >= floor
    gated = rets[present].where(win).where(ok, axis=0)
    roster = [{"ticker": t, "added": str(idx.min().date()), "removed": None} for t in present]
    lvl = _ew_level(gated, roster, idx).where(ok)
    return lvl, n


def current_index(rets, members, priced, floor):
    idx = rets.index
    lvl, n, _reason = bt.group_index(rets, list(members), idx.min(), floor=floor, priced=priced)
    return lvl, n


def frame(idx, level, group, lvl, n, basis):
    return pd.DataFrame({"date": idx, "level": level, "group": group,
                         "index": np.round(lvl.values, 6), "n_priced_members": n.values,
                         "membership_basis": basis})


def firsts_n(df):
    first, nlast = {}, {}
    for g, sub in df.groupby("group"):
        v = sub.dropna(subset=["index"])
        first[g] = str(v["date"].min().date()) if len(v) else None
        nlast[g] = int(sub.loc[sub["date"].idxmax(), "n_priced_members"])
    return first, nlast


def dated_basket_membership(doc: dict) -> pd.DataFrame:
    """All member rows (including removed) as dated [added, removed) windows —
    the same inclusion mask engine/baskets.py reads."""
    rows = []
    for bid, b in doc["baskets"].items():
        for m in b["members"]:
            rows.append({"ticker": m["ticker"], "group": bid,
                         "start_date": pd.Timestamp(m["added"]),
                         "end_date": pd.Timestamp(m["removed"]) if m.get("removed") else pd.NaT})
    return pd.DataFrame(rows, columns=["ticker", "group", "start_date", "end_date"])


def below_floor_counts(df: pd.DataFrame) -> dict:
    """Per group: sessions inside the file span with n < floor (blank index)."""
    out = {}
    for g, sub in df.groupby("group"):
        out[g] = int((sub["n_priced_members"] < FLOOR).sum())
    return out


def _parse_args(argv=None):
    p = argparse.ArgumentParser(
        description="House group price indexes (ruling 38 Part B + continuation). "
                    "Group-level numbers and counts only; nothing is fetched.")
    p.add_argument("--closes", required=True,
                   help="daily dividend-adjusted closes parquet for the sector universes "
                        "(date index, one column per member)")
    p.add_argument("--basket-closes", required=True,
                   help="daily dividend-adjusted closes parquet for the basket members")
    p.add_argument("--membership-dir", required=True,
                   help="directory holding sp1500_pit_membership.parquet, "
                        "sp1500_pit_sectors.parquet and constituents.parquet")
    p.add_argument("--basket-membership", required=True,
                   help="basket membership JSON with seed_date and per-member added/removed")
    p.add_argument("--out", default=str(_ROOT / "data/breadth/history"),
                   help="output directory (default: data/breadth/history at the repo root)")
    return p.parse_args(argv)


def main(argv=None):
    args = _parse_args(argv)
    closes_path = Path(args.closes)
    basket_closes_path = Path(args.basket_closes)
    bd = Path(args.membership_dir)
    basket_mem_path = Path(args.basket_membership)
    hist = Path(args.out)

    # ---- price stores -------------------------------------------------------
    repo_raw = pd.read_parquet(closes_path).sort_index()
    basket_raw = pd.read_parquet(basket_closes_path).sort_index()
    repo, dropped_repo = gbh_b.drop_partial_rows(repo_raw)
    basket, dropped_basket = gbh_b.drop_partial_rows(basket_raw)
    print("repo_closes after drop_partial:", repo.shape, repo.index.min().date(), repo.index.max().date(),
          "| dropped:", dropped_repo)
    print("basket_closes after drop_partial:", basket.shape, basket.index.min().date(), basket.index.max().date(),
          "| dropped:", dropped_basket)

    # ---- membership ---------------------------------------------------------
    mem_dated = gbh_b.membership_dated(bd, "sp500")          # ticker, group, start_date, end_date
    mem_cur_sec = bt.sector_membership(bd / "constituents.parquet")
    mem_bk = bt.basket_membership(basket_mem_path)
    sec_labels_dated = sorted(mem_dated["group"].dropna().unique())
    sec_labels_cur = sorted(mem_cur_sec["group"].dropna().unique())
    print("dated sector groups:", len(sec_labels_dated), sec_labels_dated)
    print("current sector groups:", len(sec_labels_cur), sec_labels_cur)
    assert set(sec_labels_dated) <= set(GICS_TO_ETF), "dated sector label not in GICS_TO_ETF"
    assert set(sec_labels_cur) <= set(GICS_TO_ETF), "current sector label not in GICS_TO_ETF"
    basket_ids = sorted(mem_bk["group"].unique())
    print("basket groups:", len(basket_ids))

    # ---- duplicate-series labelling (counts only in sidecar) ----------------
    dup_dated = gbh_b.duplicate_series_pairs(repo, mem_dated)
    repo_d = gbh_b.count_duplicates_once(repo, dup_dated)
    dup_cur_sec = gbh_b.duplicate_series_pairs(repo, mem_cur_sec)
    repo_c = gbh_b.count_duplicates_once(repo, dup_cur_sec)
    dup_bk = gbh_b.duplicate_series_pairs(basket, mem_bk)
    basket_c = gbh_b.count_duplicates_once(basket, dup_bk)
    print("dup pairs: dated", len(dup_dated), "| cur_sector", len(dup_cur_sec), "| basket", len(dup_bk))

    # ---- dated sectors (sp500 dated membership x as-of-now GICS) ------------
    rd, pd_ = rets_priced(repo_d)
    dstart = pd.Timestamp(mem_dated["start_date"].min())
    didx = rd.index[rd.index >= dstart]
    dparts = []
    for g in sec_labels_dated:
        lvl, n = dated_index(rd, mem_dated[mem_dated["group"] == g], pd_, FLOOR)
        dparts.append(frame(didx, "sector", g, lvl.reindex(didx), n.reindex(didx), DATED_BASIS))
    dated = pd.concat(dparts, ignore_index=True)

    # ---- sensitivity: current sectors + current baskets ---------------------
    rc, pc = rets_priced(repo_c)
    cparts = []
    for g in sec_labels_cur:
        members = mem_cur_sec.loc[mem_cur_sec["group"] == g, "ticker"].tolist()
        lvl, n = current_index(rc, members, pc, FLOOR)
        cparts.append(frame(rc.index, "sector", g, lvl, n, CURRENT_BASIS))
    rb, pb = rets_priced(basket_c)
    for g in basket_ids:
        members = mem_bk.loc[mem_bk["group"] == g, "ticker"].tolist()
        lvl, n = current_index(rb, members, pb, FLOOR)
        cparts.append(frame(rb.index, "basket", g, lvl, n, CURRENT_BASIS))
    sens = pd.concat(cparts, ignore_index=True)

    # ---- write the two parquet files ----------------------------------------
    hist.mkdir(parents=True, exist_ok=True)
    dated.to_parquet(hist / "group_index_daily_dated.parquet", index=False, compression="zstd")
    sens.to_parquet(hist / "group_index_daily_current_sensitivity.parquet", index=False, compression="zstd")

    # ---- key map (engine_key from engine code, never name similarity) -------
    km = []
    for g in sorted(set(sec_labels_dated) | set(sec_labels_cur)):
        km.append({"group_key": g, "level": "sector", "engine_key": GICS_TO_ETF[g], "spdr_parent": ""})
    for g in basket_ids:
        km.append({"group_key": g, "level": "basket", "engine_key": g, "spdr_parent": ""})
    km = pd.DataFrame(km, columns=["group_key", "level", "engine_key", "spdr_parent"])
    km.to_csv(hist / "group_index_key_map.csv", index=False)

    # ---- counts-only sidecar ------------------------------------------------
    d_first, d_nlast = firsts_n(dated)
    cs = sens[sens["level"] == "sector"]
    cb = sens[sens["level"] == "basket"]
    cs_first, cs_nlast = firsts_n(cs)
    cb_first, cb_nlast = firsts_n(cb)
    cov_d = {"members_in_map": int(mem_dated["ticker"].nunique()),
             "members_priced": int(len(set(mem_dated["ticker"]) & set(repo.columns))),
             "membership_rows": int(len(mem_dated)),
             "membership_rows_unlabeled": int(mem_dated["group"].isna().sum())}
    cov_b = {"members_in_map": int(mem_bk["ticker"].nunique()),
             "members_priced": int(len(set(mem_bk["ticker"]) & set(basket.columns))),
             "membership_rows": int(len(mem_bk))}
    meta = {
        "rights_class": "house",
        "title": "Group price indexes for baskets and sectors (COO ruling 38 Part B)",
        "price_note": PRICE_NOTE,
        "redistribution_note": REDIST_NOTE,
        "index": INDEX_RULES,
        "files": {
            "group_index_daily_dated.parquet": {
                "basis": DATED_BASIS, "levels": ["sector"], "rows": int(len(dated)),
                "span": {"start": str(dated["date"].min().date()), "end": str(dated["date"].max().date())},
                "membership": "S&P 500 dated membership (sp1500_pit_membership src=sp500) x as-of-now GICS "
                              "sector classification (sp1500_pit_sectors); classification is as of now, NOT "
                              "era-correct; same basis as #11094 group_breadth_daily_dated_sp500.parquet",
            },
            "group_index_daily_current_sensitivity.parquet": {
                "basis": CURRENT_BASIS, "sensitivity": True, "levels": ["sector", "basket"],
                "rows": int(len(sens)),
                "span": {"start": str(sens["date"].min().date()), "end": str(sens["date"].max().date())},
                "membership": "today's members applied to every past session; survivors only; not "
                              "point-in-time",
            },
        },
        "levels": {
            "sector": {
                "engine_key_source": ("engine/neuralweb/sector_map.py GICS_TO_ETF (explicit code map) and "
                                      "engine/sector_cycles.py SECTORS / engine/subsector_rotation.py "
                                      "SECTOR_ETFS, keyed by the 11 SPDR sector ETF tickers"),
                "engine_key": "SPDR sector ETF ticker via GICS_TO_ETF",
                "dated": {"first_valid_index": d_first, "n_priced_at_last_date": d_nlast,
                          "price_input": {"path": str(closes_path),
                                          "sha256_16": sha16(closes_path)}},
                "current_sensitivity": {"first_valid_index": cs_first, "n_priced_at_last_date": cs_nlast},
            },
            "basket": {
                "engine_key_source": ("engine/us_basket_turn.py and engine/baskets.py read "
                                      "data/baskets/membership.json keyed by basket id; engine_key = basket id"),
                "engine_key": "basket id",
                "dated": False,
                "no_dated_file_reason": ("The basket membership on main carries added/removed fields, but "
                                         "added_semantics states `added` is an index-inclusion mask "
                                         "back-projected to seed_date (2023-05-09) for any roster curated "
                                         "later (35 of 49 baskets are back-projected), and `curated_added` "
                                         "is a recent curation stamp, not an era-correct entry date. "
                                         "membership_history.parquet holds only 4 snapshots "
                                         "(2026-08-13..2026-10-14). There is no historical point-in-time "
                                         "basket entry/exit record covering the price span, so a dated "
                                         "basket index would misrepresent hindsight-curated, back-projected "
                                         "rosters as genuine dated history. Baskets are therefore current "
                                         "members only, in the sensitivity file."),
                "current_sensitivity": {"first_valid_index": cb_first, "n_priced_at_last_date": cb_nlast,
                                        "price_input": {"path": str(basket_closes_path),
                                                        "sha256_16": sha16(basket_closes_path),
                                                        "note": "the same closes #11107 used"}},
            },
        },
        "membership_census": {
            "sp500": {"rows": 1255, "tickers": 1202, "first_start": "1996-01-02", "open_rows": 503},
            "sp400": {"rows": 969, "tickers": 930, "first_start": "2012-01-13", "open_rows": 400},
            "sp600": {"rows": 1062, "tickers": 1048, "first_start": "2019-12-17", "open_rows": 603},
            "note": ("All three dated S&P sources exist in sp1500_pit_membership.parquet with the desk's "
                     "expected first dates. The committed dated sector index uses sp500 (the same basis as "
                     "#11094 group_breadth_daily_dated_sp500.parquet). sp400/sp600 membership is available "
                     "for a future extension; nothing was purchased or downloaded."),
        },
        "inputs": [
            {"path": str(closes_path), "sha256_16": sha16(closes_path)},
            {"path": str(basket_closes_path), "sha256_16": sha16(basket_closes_path)},
            {"path": str(bd / "sp1500_pit_membership.parquet"), "sha256_16": sha16(bd / "sp1500_pit_membership.parquet")},
            {"path": str(bd / "sp1500_pit_sectors.parquet"), "sha256_16": sha16(bd / "sp1500_pit_sectors.parquet")},
            {"path": str(bd / "constituents.parquet"), "sha256_16": sha16(bd / "constituents.parquet")},
            {"path": str(basket_mem_path), "sha256_16": sha16(basket_mem_path)},
        ],
        "coverage": {"dated_sector": cov_d, "basket": cov_b},
        "dropped_partial_rows": {"repo_closes": dropped_repo, "basket_closes_tradj": dropped_basket},
        "dropped_partial_rows_rule": DROPPED_RULE,
        "duplicate_series_pairs_count": {"dated_sector": int(len(dup_dated)),
                                         "current_sector": int(len(dup_cur_sec)), "basket": int(len(dup_bk))},
        "duplicate_series_rule": DUP_RULE,
        "no_outcomes": NO_OUTCOMES,
        "build_time_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "engine": ("engine.baskets._ew_level; scripts/build_group_breadth_history.py dated loaders; "
                   "scripts/build_tree_breadth_and_index.py group_index"),
    }
    (hist / "group_index.meta.json").write_text(json.dumps(meta, indent=1, default=str) + "\n")

    # ---- console summary (counts only) --------------------------------------
    print("\n=== dated sectors ===")
    print("rows:", len(dated), "| groups:", dated['group'].nunique(),
          "| valid groups at last date:", int(dated[dated['date'] == dated['date'].max()]['index'].notna().sum()))
    print("first dates:", json.dumps(d_first))
    print("\n=== sensitivity sectors ===")
    print("first dates:", json.dumps(cs_first))
    print("\n=== sensitivity baskets ===")
    print("rows:", len(cb), "| groups:", cb['group'].nunique(),
          "| valid at last date:", int(cb[cb['date'] == cb['date'].max()]['index'].notna().sum()),
          "| never valid:", sum(1 for v in cb_first.values() if v is None))
    print("\n=== files ===")
    for n in ["group_index_daily_dated.parquet", "group_index_daily_current_sensitivity.parquet",
              "group_index.meta.json", "group_index_key_map.csv"]:
        p = hist / n
        print(f"{n}: bytes={p.stat().st_size} sha256={sha256(p)}")
    print("key map rows:", len(km), "| unique keys:", km['group_key'].nunique())

    # ---- Fix 2: dated basket index -------------------------------------------
    doc = json.loads(basket_mem_path.read_text())
    assert doc["seed_date"] == SEED
    mem_bk = dated_basket_membership(doc)
    basket_ids = sorted(mem_bk["group"].unique())
    assert len(basket_ids) == 49
    dup_bk = gbh_b.duplicate_series_pairs(basket, mem_bk)
    basket_d = gbh_b.count_duplicates_once(basket, dup_bk)
    rb, pb = rets_priced(basket_d)
    seed_ts = pd.Timestamp(SEED)
    bidx = rb.index[rb.index >= seed_ts]
    bparts = []
    for g in basket_ids:
        lvl, n = dated_index(rb, mem_bk[mem_bk["group"] == g], pb, FLOOR)
        bparts.append(frame(bidx, "basket", g, lvl.reindex(bidx), n.reindex(bidx), DATED_BASIS))
    bk_dated = pd.concat(bparts, ignore_index=True)
    bk_dated.to_parquet(hist / "group_index_basket_daily_dated.parquet", index=False,
                        compression="zstd")
    b_first, b_nlast = firsts_n(bk_dated)
    b_below = below_floor_counts(bk_dated)
    early = mem_bk[mem_bk["start_date"] < seed_ts]
    created_after = sum(1 for b in doc["baskets"].values() if b.get("created", "") > SEED)
    bk_meta = {
        "rights_class": "house",
        "title": "Dated basket price index (COO ruling 38 Part B, continuation Fix 2)",
        "price_note": PRICE_NOTE,
        "redistribution_note": REDIST_NOTE,
        "index": INDEX_RULES,
        "file": {
            "name": "group_index_basket_daily_dated.parquet",
            "basis": DATED_BASIS, "levels": ["basket"], "rows": int(len(bk_dated)),
            "span": {"start": str(bk_dated["date"].min().date()),
                     "end": str(bk_dated["date"].max().date())},
            "membership": ("data/baskets/membership.json on main: every member row (including "
                           "removed members) as its recorded [added, removed) inclusion window, "
                           "the same mask engine/baskets.py and engine/us_basket_turn.py read; "
                           "a member counts only on sessions inside its own window"),
        },
        "dated_membership_start": SEED,
        "dated_membership_start_note": (
            "Dated basket membership starts 2023-05-09 (the membership file's seed_date); before "
            "that date the basket has only the current-members sensitivity series "
            "(group_index_daily_current_sensitivity.parquet). The file span begins at the first "
            "session on/after the seed."),
        "provenance_caveat": (
            "Reconstruction, not a point-in-time record. `added` is the index-inclusion mask; for "
            "the 35 baskets curated after the seed it is back-projected, so pre-curation history "
            "shows what today's recorded windows did, not what anyone held at the time. "
            "`curated_added` is the provenance stamp and is never earlier than the basket's "
            "created date; treat history before a member's curated_added as context, never as a "
            "track record. 34 member rows in 3 baskets carry a recorded added date (2023-01-03) "
            "earlier than the seed; they are effective from the first session on/after the seed "
            "in this file. This file supersedes the earlier no-dated-basket disposition recorded "
            "in group_index.meta.json, per the continuation brief: the dated windows are built "
            "as recorded, labelled reconstructed_dated_membership, with this caveat."),
        "first_valid_index": b_first,
        "n_priced_at_last_date": b_nlast,
        "below_floor_sessions_per_basket": b_below,
        "baskets_never_reaching_floor": sorted(g for g, v in b_first.items() if v is None),
        "coverage": {
            "baskets": len(basket_ids),
            "membership_rows": int(len(mem_bk)),
            "membership_rows_active": int(mem_bk["end_date"].isna().sum()),
            "membership_rows_removed": int(mem_bk["end_date"].notna().sum()),
            "members_in_map": int(mem_bk["ticker"].nunique()),
            "members_priced": int(len(set(mem_bk["ticker"]) & set(basket.columns))),
            "rows_added_before_seed": int(len(early)),
            "baskets_created_after_seed": created_after,
        },
        "price_input": {"path": str(basket_closes_path),
                        "sha256_16": sha16(basket_closes_path),
                        "note": "the same closes #11107 used and the sensitivity file uses"},
        "inputs": [
            {"path": str(basket_closes_path),
             "sha256_16": sha16(basket_closes_path)},
            {"path": "data/baskets/membership.json (origin/main)",
             "sha256_16": sha16(basket_mem_path)},
        ],
        "dropped_partial_rows": {"basket_closes_tradj": dropped_basket},
        "dropped_partial_rows_rule": DROPPED_RULE,
        "duplicate_series_pairs_count": int(len(dup_bk)),
        "duplicate_series_rule": DUP_RULE,
        "no_outcomes": NO_OUTCOMES,
        "build_time_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "engine": ("engine.baskets._ew_level; scripts/build_group_breadth_history.py dated "
                   "loaders; prior-round method /tmp/r38b/build_house.py dated_index"),
    }
    (hist / "group_index_basket_daily_dated.meta.json").write_text(
        json.dumps(bk_meta, indent=1, default=str) + "\n")

    # ---- Fix 3: dated sp400 / sp600 sector indexes ----------------------------
    uni_parts, uni_meta = [], {}
    for src in ("sp400", "sp600"):
        mem = gbh_b.membership_dated(bd, src)
        labels = sorted(mem["group"].dropna().unique())
        assert set(labels) <= set(GICS_TO_ETF), f"{src} label not in GICS_TO_ETF"
        dup = gbh_b.duplicate_series_pairs(repo, mem)
        repo_d = gbh_b.count_duplicates_once(repo, dup)
        rd, pd_ = rets_priced(repo_d)
        ustart = pd.Timestamp(mem["start_date"].min())
        uidx = rd.index[rd.index >= ustart]
        parts = []
        for g in labels:
            lvl, n = dated_index(rd, mem[mem["group"] == g], pd_, FLOOR)
            parts.append(frame(uidx, "sector", g, lvl.reindex(uidx), n.reindex(uidx), DATED_BASIS))
        u = pd.concat(parts, ignore_index=True)
        u["index_universe"] = src
        uni_parts.append(u)
        first, nlast = firsts_n(u)
        gone = gbh_b.unpriced_in_window(repo_d, mem)
        uni_meta[src] = {
            "basis": DATED_BASIS, "levels": ["sector"], "rows": int(len(u)),
            "span": {"start": str(u["date"].min().date()), "end": str(u["date"].max().date())},
            "first_start": str(ustart.date()),
            "labels": "as-of-now GICS sector classification (sp1500_pit_sectors); NOT era-correct",
            "first_valid_index": first,
            "n_priced_at_last_date": nlast,
            "below_floor_sessions_per_sector": below_floor_counts(u),
            "sectors_never_reaching_floor": sorted(g for g, v in first.items() if v is None),
            "coverage": {
                "members_in_map": int(mem["ticker"].nunique()),
                "members_priced": int(len(set(mem["ticker"]) & set(repo.columns))),
                "membership_rows": int(len(mem)),
                "membership_rows_open": int(mem["end_date"].isna().sum()),
                "membership_rows_unlabeled": int(mem["group"].isna().sum()),
                "rows_unpriced_in_own_window": int(len(gone)),
                "rows_unpriced_in_own_window_ticker_present": int(gone["ticker_in_store"].sum()),
                "unpriced_in_window_by_start_year": {
                    str(k): int(v) for k, v in
                    gone["start_date"].dt.year.value_counts().sort_index().items()},
            },
            "duplicate_series_pairs_count": int(len(dup)),
        }
        print(f"{src}: rows={len(u)} labels={len(labels)} unlabeled={int(mem['group'].isna().sum())} "
              f"unpriced_in_window={len(gone)} dup_pairs={len(dup)}")
    sp = pd.concat(uni_parts, ignore_index=True)
    sp = sp[["date", "level", "group", "index", "n_priced_members", "membership_basis",
             "index_universe"]]
    sp.to_parquet(hist / "group_index_daily_dated_sp400_sp600.parquet", index=False,
                  compression="zstd")
    sp_meta = {
        "rights_class": "house",
        "title": "Dated S&P 400 and S&P 600 sector price indexes (COO ruling 38 Part B, continuation Fix 3)",
        "price_note": PRICE_NOTE,
        "redistribution_note": REDIST_NOTE,
        "index": INDEX_RULES,
        "never_pooled": "The S&P 500, 400 and 600 indexes are never pooled.",
        "file": {
            "name": "group_index_daily_dated_sp400_sp600.parquet",
            "basis": DATED_BASIS, "levels": ["sector"], "rows": int(len(sp)),
            "index_universe_values": ["sp400", "sp600"],
            "membership": ("dated S&P 400 / S&P 600 membership (sp1500_pit_membership src=sp400 / "
                           "src=sp600) x as-of-now GICS sector classification (sp1500_pit_sectors); "
                           "each universe is indexed separately and never combined with sp500 or "
                           "with each other"),
        },
        "universes": uni_meta,
        "known_gaps": {
            "dropped_partial_rows": {"repo_closes": dropped_repo},
            "dropped_partial_rows_rule": DROPPED_RULE,
            "below_floor_rule": ("sessions with fewer than 5 priced in-window members keep "
                                 "n_priced_members with a blank index; per-universe per-sector "
                                 "counts are in universes.<src>.below_floor_sessions_per_sector"),
            "unlabeled_rows_rule": ("membership rows with no sector classification are absent from "
                                    "every sector index (counts in universes.<src>.coverage)"),
            "unpriced_in_window_rule": ("membership rows with no stored close inside their own "
                                        "[start_date, end_date) window contribute nothing (counts "
                                        "in universes.<src>.coverage); a ticker present in the "
                                        "store only outside its window is a likely ticker reuse"),
        },
        "price_input": {"path": str(closes_path),
                        "sha256_16": sha16(closes_path),
                        "note": "the same closes the dated sp500 sector index uses"},
        "inputs": [
            {"path": str(closes_path),
             "sha256_16": sha16(closes_path)},
            {"path": str(bd / "sp1500_pit_membership.parquet"),
             "sha256_16": sha16(bd / "sp1500_pit_membership.parquet")},
            {"path": str(bd / "sp1500_pit_sectors.parquet"),
             "sha256_16": sha16(bd / "sp1500_pit_sectors.parquet")},
        ],
        "duplicate_series_rule": DUP_RULE,
        "no_outcomes": NO_OUTCOMES,
        "build_time_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "engine": ("engine.baskets._ew_level; scripts/build_group_breadth_history.py "
                   "membership_dated / drop_partial_rows / duplicate_series_pairs / "
                   "unpriced_in_window; prior-round method /tmp/r38b/build_house.py dated_index"),
    }
    (hist / "group_index_daily_dated_sp400_sp600.meta.json").write_text(
        json.dumps(sp_meta, indent=1, default=str) + "\n")

    # ---- summary (counts only) ------------------------------------------------
    print("\n=== dated baskets ===")
    print("rows:", len(bk_dated), "| span:", bk_dated["date"].min().date(), "..",
          bk_dated["date"].max().date(), "| never valid:",
          len(bk_meta["baskets_never_reaching_floor"]))
    print("first dates:", json.dumps(b_first))
    print("\n=== sp400/sp600 ===")
    for src in ("sp400", "sp600"):
        print(src, "first dates:", json.dumps(uni_meta[src]["first_valid_index"]))
    print("\n=== new files ===")
    for n in ("group_index_basket_daily_dated.parquet", "group_index_basket_daily_dated.meta.json",
              "group_index_daily_dated_sp400_sp600.parquet",
              "group_index_daily_dated_sp400_sp600.meta.json"):
        p = hist / n
        print(f"{n}: bytes={p.stat().st_size} sha256={sha256(p)}")


if __name__ == "__main__":
    main()