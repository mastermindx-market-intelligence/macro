"""Regime inputs: equity-internal group and universe series (COO ruling 36 s2).

Series only. No regime category, no cutoff, no score, no signal, no rank-based
call; nothing related to outcomes, hit rates or backtests, on any period.
Group-level and universe-level numbers only: no member ticker, member row or
member price is written. Off the render path; never run nightly.

Inputs (read-only):
  * one single-vintage full-history member-close download held off git (scratch),
    the same file the house tree breadth/index build reads;
  * data/breadth/constituents.parquet (today's S&P 500, GICS sector labels) and
    data/baskets/membership.json (active members), both on this branch;
  * the ETF closes on main at data/yahoo/{SPY,RSP,SPHB,IGV,SOXX}.parquet, column
    ``close``, read with ``git show origin/main:...`` unless --etf-dir is given.

Basis is the house tree build's basis (``reconstructed_current_membership``):
today's members applied to the past, today's labels, survivors only. Equal-weight
levels reuse ``engine.baskets._ew_level`` through
``scripts.build_tree_breadth_and_index.group_index`` (daily rebalance, chained
from 1.0, INDEX_FLOOR priced members). Breadth flags reuse
``engine.group_breadth_history.member_flags`` / ``group_levels`` / ``level_change``;
new 252-session highs/lows reuse the house ``high52w_new`` convention
(engine.momentum_context_signals): close strictly beyond the prior 252-session
extreme, full window required. The high-beta group is computed, not curated:
the top fifth of universe members by trailing 252-session beta to SPY daily
returns, set at each month's last session and held the next month.

Outputs under --out (default data/breadth/history):
  regime_inputs_daily_current.parquet  (date, series, group, value, n, kind)
  regime_inputs_current.meta.json      (per-series definition, first date,
                                        source, basis, gaps; no-outcome sentence)

Basis ``dated`` (COO ruling 36 s2 addition) reconstructs the same statistics on
the dated S&P 500 membership windows from 1996 (``sp1500_pit_membership`` rows
with src == sp500, as-of-now sector labels), priced from the licensed Tiingo
archive closes held off git. A member counts only on sessions inside its own
membership window, exactly as engine.group_breadth_history.assign_groups does
for the house dated sector history. Cleaning reuses
scripts.build_group_breadth_history (drop_partial_rows, duplicate_series_pairs,
count_duplicates_once, missing_sentence). Archive rule: only group/universe
aggregates and counts are written — no archive row, price, ticker name or
per-security date enters git, the PR body or a comment. Outputs:
  regime_inputs_dated_sp500_daily.parquet  (same columns as the current file)
  regime_inputs_dated_sp500.meta.json      (basis reconstructed_dated_membership)
``--minimum`` writes the COO 13:58Z minimum set only (200-day breadth and its
changes, NH-NL, universe dispersion_21d, pct_beat_ew_63d, the dated computed
high-beta relative index, and the like-for-like fixed-set changes).

Basis ``fixchg-current`` writes ONLY the like-for-like (fixed-set) universe
change on the current basis — same members and prices as the frozen current
file — into a separate small file, so the frozen outputs stay byte-identical:
  regime_inputs_fixchg_current.parquet / regime_inputs_fixchg_current.meta.json

Usage:
  python scripts/build_regime_inputs.py --closes <scratch closes.parquet> \
      --download-meta <scratch download_meta.json> [--out data/breadth/history] \
      [--start 2000-01-01] [--etf-dir <dir>] [--house-index <house daily parquet>] \
      [--census-json <rates/credit/dollar census>]
  python scripts/build_regime_inputs.py --basis dated --closes <tiingo archive.parquet> \
      --pit-dir <scratch breadth dir with the two sp1500 parquets> [--minimum] \
      [--etf-dir <dir with SPY.parquet>] [--out data/breadth/history]
  python scripts/build_regime_inputs.py --basis fixchg-current --closes <closes.parquet> \
      --download-meta <download_meta.json> [--out data/breadth/history]
"""
from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
import tempfile
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

import hashlib  # noqa: E402

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from engine import group_breadth_history as gbh  # noqa: E402
from scripts import build_group_breadth_history as gb  # noqa: E402
from scripts import build_tree_breadth_and_index as bt  # noqa: E402

START = "2000-01-01"
START_DATED = "1996-01-02"      # first dated S&P 500 membership start
# Same rule and sentence as the tree build's start block (its meta "start").
START_RULE = ("first January 1 from which every later calendar year has name-week "
              "above-200 flag disagreement against the Tiingo archive of 0.5% or less "
              "(S&P 500 members priced in both, weeks where both hold 200 sessions)")
START_NOTE = ("200-session averages use the full download, so the first weeks after "
              "the start read flags from late in the prior year")
NO_OUTCOMES = ("series only: no outcome relation, no regime assignment, no trading call "
               "of any kind, on any period")
KINDS = ("house", "etf", "computed")

ETFS = ("SPY", "RSP", "SPHB", "IGV", "SOXX")
ETF_FIRST = {"SPY": "1993-01-29", "RSP": "2003-05-01", "SPHB": "2011-05-05",
             "IGV": "2001-07-17", "SOXX": "2001-07-13"}
BASKETS = ("ai_software", "non_ai_software", "ai_semiconductors")
UNIVERSE = "universe"
HIGH_BETA = "high_beta_computed"
WINDOWS = (50, 200)
CHANGE_HORIZONS = (21, 63)
DISPERSION_HORIZONS = (21, 63)
LEADERSHIP_HORIZONS = (63, 126)
NH_WINDOW = 252
BETA_WINDOW = 252
HIGH_BETA_FRACTION = 5          # top fifth
ETF_COLUMN = "close"

PRICE_SOURCE = ("yfinance yf.download(auto_adjust=True, period='max'), one single-vintage "
                "download, held off git; never the collector cache or data/yahoo")
ETF_SOURCE = ("data/yahoo/<T>.parquet on origin/main, column close (vendor price series, "
              "not the house auto_adjust download); read with git show, never edited")
HIGH_BETA_RULE = ("top fifth of universe members by trailing 252-session beta to SPY daily "
                  "returns (cov/var on 252 paired daily returns, full window required), "
                  "ranked at each month's last session, held the next month; ties broken "
                  "by ticker; equal-weight daily rebalance within the held month, same "
                  "_ew_level chaining from 1.0")
# Short per-series gap sentences (at most 3 per series in the sidecar); the full
# house sentences live in the top-level meta blocks.
DIVIDEND_GAP = ("different dividend methods between legs shift the long-run ratio level, "
                "not the timing of its turns")
SURVIVOR_GAP = "survivors only: past levels are overstated, more so further back"
COUNTED_GAP = "the counted set can differ between the two endpoints of a change"
WINDOW_GAP = "a close and a full prior 252-session window are both required"
SURVIVOR_LONG = bt.SURVIVOR_INDEX_SENTENCE
BASIS_HOUSE = bt.BASIS_NOTE
BASIS_ETF = "vendor close on origin/main; not the house download"
BASIS_MIXED = ("house EW level (today's members, survivors only) and vendor close "
               "on origin/main")
BASIS_COMPUTED = BASIS_HOUSE + "; cohort computed monthly, not curated"

# ---- dated basis (COO ruling 36 s2 addition, 13:54Z / 13:58Z) --------------
BASIS_DATED = gb.BASIS["dated"]                       # reconstructed_dated_membership
BASIS_DATED_NOTE = ("S&P 500 dated membership windows (sp1500_pit_membership, src=sp500); "
                    "a member counts only on sessions inside its own window; sector labels "
                    "are as of now, not era-correct")
BASIS_DATED_ETF = ("dated EW level (Tiingo archive closes) and SPY vendor close on origin/main")
BASIS_DATED_COMPUTED = BASIS_DATED_NOTE + "; cohort computed monthly from dated members, not curated"
TIINGO_SOURCE = ("Tiingo EOD archive /Volumes/Mastermind/market-data/tiingo (normalized eod-bars, "
                 "captures 2026-10-11..16) via scripts/build_tiingo_member_closes.py; "
                 "member-level, off git")
TIINGO_PRICE_NOTE = ("Adjusted closes are the archive's restated values (split and dividend "
                     "adjustment as of the 2026-10-11..16 capture), not the prices printed at "
                     "the time. Group-level shares and counts only; no member prices. The "
                     "Tiingo research reader marks raw views redistribution_admitted=false; "
                     "member-level history stays off git.")
ARCHIVE_GAP = ("members without a stored close inside their own window are absent; "
               "early-year coverage is lean")
DATED_DISPERSION_GAP = ("members without both endpoint closes, or outside their membership "
                        "window at either end, are not counted")
DATED_LEADERSHIP_GAP = ("membership is required on the session; the return window may span "
                        "a member's entry date")
DATED_HIGH_BETA_GAP = ("computed, not curated; selection restricted to dated members with a "
                       "full 252-session window at the selection session; the cohort is held "
                       "fixed within the month")
SECTOR_EW_GAP = ("a sector with fewer than 2 priced members in-window has no EW level that "
                 "session; n = sectors with a valid return")
NOT_INCLUDED = ("curated basket relative indices (ai_software, non_ai_software, IGV, SOXX and "
                "SPHB legs) are not included: no dated membership exists for curated baskets. "
                "The computed high-beta group IS included; it is derived from the dated universe.")
FIXCHG_GAP = ("the fixed set is the members at t with a defined average at both ends; a name "
              "leaving the universe before t drops out")
# COO 13:58Z minimum set: 200-day breadth + changes, NH-NL, universe dispersion_21d,
# pct_beat_ew_63d, the dated computed high-beta relative index, the fixed-set changes
# (200- and 50-day lines), plus the universe EW level the last two are measured against.
MINIMUM_SERIES = {
    "pct_above_200", "n_above_200", "diff_pct_above_200_21d", "diff_pct_above_200_63d",
    "nh_nl_252", "n_counted_nh", "dispersion_21d", "pct_beat_ew_63d", "n_beat_ew_63d",
    "ew_index", "rel_high_beta_computed_vs_ew_universe",
    "fix_chg_pct_above_200_21", "fix_chg_pct_above_200_63", "n_fixed_200_21", "n_fixed_200_63",
    "fix_chg_pct_above_50_21", "fix_chg_pct_above_50_63", "n_fixed_50_21", "n_fixed_50_63",
}
MINIMUM_UNIVERSE_ONLY = {"dispersion_21d", "ew_index"}


def _sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _retry_note(retry: dict | None) -> dict | None:
    """Retry provenance without member tickers (group/universe-only rule)."""
    if not retry:
        return None
    return {"vintage": retry.get("vintage"),
            "requested": len(retry.get("requested", [])),
            "served": len(retry.get("served", []))}


def _topup_note(topup: dict | None) -> dict | None:
    """Top-up provenance without member tickers (group/universe-only rule)."""
    if not topup:
        return None
    return {"vintage": topup.get("vintage"), "names": topup.get("names"),
            "call": topup.get("call"), "library": topup.get("library"),
            "rule": topup.get("rule"), "reason": topup.get("reason")}


# ---------------------------------------------------------------- inputs
def load_closes(path: Path) -> pd.DataFrame:
    return gbh.through_last_complete_row(pd.read_parquet(path).sort_index())


def load_etfs(root: Path, etf_dir: Path | None = None) -> dict[str, pd.Series]:
    """ETF close series, read-only. Default: git show origin/main:data/yahoo/<T>.parquet."""
    out: dict[str, pd.Series] = {}
    tmp = Path(tempfile.mkdtemp(prefix="regime_etf_")) if etf_dir is None else None
    for t in ETFS:
        if etf_dir is not None:
            p = Path(etf_dir) / f"{t}.parquet"
        else:
            raw = subprocess.run(["git", "-C", str(root), "show",
                                  f"origin/main:data/yahoo/{t}.parquet"],
                                 capture_output=True, check=True).stdout
            p = tmp / f"{t}.parquet"
            p.write_bytes(raw)
        df = pd.read_parquet(p)
        out[t] = df[ETF_COLUMN].astype(float).sort_index()
    return out


def daily_returns(closes: pd.DataFrame) -> pd.DataFrame:
    """The tree build's return convention: valid only where both closes exist."""
    rets = closes.pct_change(fill_method=None)
    return rets.where(closes.notna() & closes.shift(1).notna())


def window_return(closes: pd.DataFrame, k: int) -> pd.DataFrame:
    """Simple k-session return, valid only where both endpoint closes exist."""
    r = closes / closes.shift(k) - 1.0
    return r.where(closes.notna() & closes.shift(k).notna())


# ---------------------------------------------------------------- levels
def ew_levels(closes: pd.DataFrame, groups: dict[str, list[str]],
              start: pd.Timestamp) -> dict[str, tuple[pd.Series, pd.Series]]:
    """group -> (level, n_priced) via the tree build's group_index (_ew_level)."""
    rets = daily_returns(closes)
    priced = closes.notna()
    out = {}
    for g, members in groups.items():
        lvl, n, _ = bt.group_index(rets, members, start, priced=priced)
        out[g] = (lvl, n)
    return out


def ew_level_held(rets: pd.DataFrame, priced: pd.DataFrame, held: pd.DataFrame,
                  start: pd.Timestamp) -> tuple[pd.Series, pd.Series]:
    """_ew_level convention for a roster that changes by date (monthly cohorts).

    ``held`` is a boolean sessions-x-members mask of the cohort in force each
    session. Same arithmetic as engine.baskets._ew_level: plain mean of the held
    members' daily returns, chained from 1.0 on the first valid session; sessions
    under INDEX_FLOOR priced members carry no level and no return.
    """
    sub = rets.where(held)
    n = (priced & held).sum(axis=1).astype("int64")
    ok = (n >= bt.INDEX_FLOOR) & (rets.index >= start)
    ew = sub.mean(axis=1).where(ok)
    lvl = pd.Series(np.nan, index=rets.index)
    first = ew.first_valid_index()
    if first is not None:
        lvl.loc[first:] = (1.0 + ew.loc[first:].fillna(0.0)).cumprod()
    return lvl.where(ok), n


def month_end_betas(mrets: pd.DataFrame, sret: pd.Series,
                    month_ends: pd.Series) -> dict[pd.Period, pd.Series]:
    """Beta to SPY at each month's last session only: sample cov/var on the
    trailing BETA_WINDOW paired daily returns, full window required (the same
    estimator as rolling(BETA_WINDOW, min_periods=BETA_WINDOW).cov/.var)."""
    pos = {t: i for i, t in enumerate(mrets.index)}
    mr = mrets.to_numpy()
    sr = sret.to_numpy()
    out: dict[pd.Period, pd.Series] = {}
    for per, t in month_ends.items():
        p = pos[t]
        if p + 1 < BETA_WINDOW:
            continue
        w = mr[p - BETA_WINDOW + 1: p + 1]
        s = sr[p - BETA_WINDOW + 1: p + 1]
        if not np.isfinite(s).all():
            continue
        ok = np.isfinite(w).all(axis=0)
        if not ok.any():
            continue
        wc = w[:, ok]
        sc = s - s.mean()
        denom = float(sc @ sc)
        if denom <= 0:
            continue
        cov = (wc - wc.mean(axis=0)).T @ sc / (BETA_WINDOW - 1)
        out[per] = pd.Series(cov / (denom / (BETA_WINDOW - 1)), index=mrets.columns[ok])
    return out


def high_beta_cohorts(closes_u: pd.DataFrame, spy: pd.Series,
                      start: pd.Timestamp, member_mask: pd.DataFrame | None = None
                      ) -> tuple[pd.Series, pd.Series, dict]:
    """(level, n_priced, facts) for the computed high-beta group on the closes index.

    ``member_mask`` (dated basis) is the boolean sessions-x-members in-window
    mask: at each month-end only dated members of that session with a full
    252-session beta window are ranked. The selected cohort is held fixed the
    next month, exactly as on the current basis."""
    common = closes_u.index.intersection(spy.index)
    mrets = daily_returns(closes_u.reindex(common))
    sret = daily_returns(spy.reindex(common).to_frame("SPY"))["SPY"]
    month_ends = pd.Series(common, index=common.to_period("M")).groupby(level=0).max()
    betas = month_end_betas(mrets, sret, month_ends)
    cohorts: dict[pd.Period, list[str]] = {}
    sizes: dict[str, int] = {}
    for per, b in betas.items():
        if member_mask is not None:
            held_now = member_mask.loc[month_ends[per]]
            b = b[held_now.reindex(b.index).fillna(False).to_numpy()]
            if b.empty:
                continue
        k = max(1, math.ceil(len(b) / HIGH_BETA_FRACTION))
        top = sorted(b.index, key=lambda x: (-float(b[x]), x))[:k]
        cohorts[per] = top
        sizes[str(per)] = len(top)
    held = pd.DataFrame(False, index=closes_u.index, columns=closes_u.columns)
    sess_per = closes_u.index.to_period("M")
    for per, cohort in cohorts.items():
        rows = sess_per == (per + 1)           # set at prior month's last session
        if rows.any():
            held.loc[rows, cohort] = True
    lvl, n = ew_level_held(daily_returns(closes_u), closes_u.notna(), held, start)
    first_per = min(cohorts) if cohorts else None
    facts = {"rule": HIGH_BETA_RULE, "beta_window": BETA_WINDOW,
             "fraction": f"top 1/{HIGH_BETA_FRACTION} (ceil)",
             "first_selection": str(month_ends[first_per].date()) if first_per else None,
             "cohort_size_min": min(sizes.values()) if sizes else None,
             "cohort_size_max": max(sizes.values()) if sizes else None,
             "cohort_size_last": sizes.get(str(sess_per[-1] - 1)),
             "months_selected": len(sizes)}
    if member_mask is not None:
        # Dated-only note; kept out of the current-basis facts so the frozen
        # current meta stays byte-reproducible.
        facts["selection_set"] = "dated members at the selection session"
    return lvl, n, facts


# ---------------------------------------------------------------- breadth
def universe_breadth(closes_u: pd.DataFrame, start: pd.Timestamp,
                     membership: pd.DataFrame | None = None
                     ) -> tuple[dict[str, pd.Series], dict[str, pd.Series]]:
    """House-convention universe breadth: shares, counts, plain changes, NH-NL.

    Returns (series, n_by_series): the counted members beside every value.
    ``membership`` None = the current basis (every column a member on every
    session); a dated membership map (ticker/group/start_date/end_date, group
    already set to UNIVERSE) counts a member only inside its own window, via
    the engine's assign_groups — the same rule as the house dated history."""
    if membership is None:
        mem = pd.DataFrame({"ticker": list(closes_u.columns), "group": UNIVERSE})
    else:
        mem = membership
    codes, groups = gbh.assign_groups(closes_u.index, list(closes_u.columns), mem, [UNIVERSE])
    flags = {w: gbh.member_flags(closes_u, w) for w in WINDOWS}
    lv = gbh.group_levels(codes, closes_u.notna().to_numpy(), flags, len(groups),
                          bt.BREADTH_FLOOR)
    out: dict[str, pd.Series] = {}
    ns: dict[str, pd.Series] = {}
    idx = closes_u.index
    for w in WINDOWS:
        counted_w = pd.Series(lv[f"n_has_{w}"][:, 0], index=idx)
        out[f"pct_above_{w}"] = pd.Series(lv[f"pct_above_{w}"][:, 0], index=idx)
        # group_levels gates the share but not the raw count: apply the same floor
        out[f"n_above_{w}"] = pd.Series(lv[f"n_above_{w}"][:, 0], index=idx).where(
            counted_w >= bt.BREADTH_FLOOR).astype(float)
        ns[f"pct_above_{w}"] = ns[f"n_above_{w}"] = counted_w
        for k in CHANGE_HORIZONS:
            s = f"diff_pct_above_{w}_{k}d"
            out[s] = pd.Series(gbh.level_change(lv[f"pct_above_{w}"], k)[:, 0], index=idx)
            ns[s] = counted_w
    prior_max = closes_u.shift(1).rolling(NH_WINDOW, min_periods=NH_WINDOW).max()
    prior_min = closes_u.shift(1).rolling(NH_WINDOW, min_periods=NH_WINDOW).min()
    in_window = pd.DataFrame(codes == 0, index=idx, columns=closes_u.columns) \
        if membership is not None else True
    counted = (prior_max.notna() & closes_u.notna() & in_window).sum(axis=1)
    n_high = ((closes_u > prior_max) & prior_max.notna() & in_window).sum(axis=1)
    n_low = ((closes_u < prior_min) & prior_min.notna() & in_window).sum(axis=1)
    ok = counted >= bt.BREADTH_FLOOR
    out["new_highs_252"] = n_high.where(ok).astype(float)
    out["new_lows_252"] = n_low.where(ok).astype(float)
    out["nh_nl_252"] = (n_high - n_low).where(ok).astype(float)
    out["n_counted_nh"] = counted.where(ok).astype(float)
    for s in ("new_highs_252", "new_lows_252", "nh_nl_252", "n_counted_nh"):
        ns[s] = counted.astype(float)
    keep = lambda d: {s: v[v.index >= start] for s, v in d.items()}  # noqa: E731
    return keep(out), keep(ns)


def universe_fixed_change(closes_u: pd.DataFrame, start: pd.Timestamp,
                          membership: pd.DataFrame | None = None
                          ) -> tuple[dict[str, pd.Series], dict[str, pd.Series]]:
    """Like-for-like (fixed-set) universe change, the engine's fix_chg method.

    Reuses engine.group_breadth_history.fixed_set_change: the members of the
    universe at t with a defined w-session average at BOTH t and t-k; their
    share above at t minus the share of the SAME names at t-k (points). The
    counted-beside-value n is the eligible count, also emitted as n_fixed_w_k.
    ``membership`` None = current basis (static); a dated map counts a member
    only inside its own window at t (the engine's assign_groups rule)."""
    if membership is None:
        mem = pd.DataFrame({"ticker": list(closes_u.columns), "group": UNIVERSE})
    else:
        mem = membership
    codes, groups = gbh.assign_groups(closes_u.index, list(closes_u.columns), mem, [UNIVERSE])
    out: dict[str, pd.Series] = {}
    ns: dict[str, pd.Series] = {}
    idx = closes_u.index
    for w in WINDOWS:
        has, above = gbh.member_flags(closes_u, w)
        for k in CHANGE_HORIZONS:
            chg, nfix = gbh.fixed_set_change(codes, has, above, k, len(groups),
                                             bt.BREADTH_FLOOR)
            s = f"fix_chg_pct_above_{w}_{k}"
            out[s] = pd.Series(chg[:, 0], index=idx)
            nf = pd.Series(nfix[:, 0], index=idx)
            ns[s] = nf.astype(float)
            out[f"n_fixed_{w}_{k}"] = nf.where(nf >= bt.BREADTH_FLOOR).astype(float)
            ns[f"n_fixed_{w}_{k}"] = nf.astype(float)
    keep = lambda d: {s: v[v.index >= start] for s, v in d.items()}  # noqa: E731
    return keep(out), keep(ns)


# ---------------------------------------------------------------- dispersion / leadership
def dispersion(closes_u: pd.DataFrame, sectors: dict[str, list[str]],
               start: pd.Timestamp, masks: dict[str, pd.DataFrame] | None = None
               ) -> dict[str, dict[str, tuple[pd.Series, pd.Series]]]:
    """series -> group -> (value in percent, n). Cross-sectional std, ddof=1.

    ``masks`` (dated basis) maps group -> boolean sessions-x-members in-window
    mask; a member then counts only when in-window at BOTH ends of the return
    window. None = current basis, unchanged."""
    out: dict[str, dict[str, tuple[pd.Series, pd.Series]]] = {}
    for k in DISPERSION_HORIZONS:
        r = window_return(closes_u, k)
        name = f"dispersion_{k}d"
        out[name] = {}
        ru = r
        if masks is not None:
            mu = masks[UNIVERSE]
            ru = r.where(mu & mu.shift(k, fill_value=False))
        n = ru.notna().sum(axis=1)
        sd = ru.std(axis=1, ddof=1) * 100.0
        out[name][UNIVERSE] = (sd.where(n >= bt.BREADTH_FLOOR), n)
        for g, members in sectors.items():
            sub = r[members]
            if masks is not None:
                mg = masks[g][members]
                sub = sub.where(mg & mg.shift(k, fill_value=False))
            ng = sub.notna().sum(axis=1)
            out[name][g] = (sub.std(axis=1, ddof=1) * 100.0, ng)
            out[name][g] = (out[name][g][0].where(ng >= bt.BREADTH_FLOOR), ng)
    return {s: {g: (v[v.index >= start], n[v.index >= start]) for g, (v, n) in gd.items()}
            for s, gd in out.items()}


def sector_dispersion(levels: dict[str, tuple[pd.Series, pd.Series]],
                      sector_names: list[str], start: pd.Timestamp
                      ) -> dict[str, tuple[pd.Series, pd.Series]]:
    """Std across the sector EW index k-session returns (ddof=1, percent)."""
    out = {}
    for k in DISPERSION_HORIZONS:
        rk = pd.DataFrame({g: window_return(levels[g][0].to_frame("l"), k)["l"]
                           for g in sector_names})
        n = rk.notna().sum(axis=1)
        sd = rk.std(axis=1, ddof=1) * 100.0
        out[f"sector_dispersion_{k}d"] = (sd.where(n >= bt.BREADTH_FLOOR)[lambda s: s.index >= start],
                                          n[n.index >= start])
    return out


def leadership(closes_u: pd.DataFrame, ew_lvl: pd.Series, start: pd.Timestamp,
               in_window: pd.DataFrame | None = None
               ) -> tuple[dict[str, pd.Series], dict[str, pd.Series]]:
    """``in_window`` (dated basis) counts a member only on sessions inside its
    own membership window; the return itself still needs both endpoint closes."""
    out: dict[str, pd.Series] = {}
    ns: dict[str, pd.Series] = {}
    for k in LEADERSHIP_HORIZONS:
        r = window_return(closes_u, k)
        if in_window is not None:
            r = r.where(in_window)
        ir = window_return(ew_lvl.to_frame("l"), k)["l"]
        counted = r.notna().mul(ir.notna(), axis=0).sum(axis=1)
        # gt with NaN on either side is already False; no extra mask needed
        # (a date-indexed Series ANDed onto the frame would align on columns).
        beat = r.gt(ir, axis=0)
        n_beat = beat.sum(axis=1)
        ok = counted >= bt.BREADTH_FLOOR
        out[f"pct_beat_ew_{k}d"] = (100.0 * n_beat / counted).where(ok)
        out[f"n_beat_ew_{k}d"] = n_beat.where(ok).astype(float)
        ns[f"pct_beat_ew_{k}d"] = ns[f"n_beat_ew_{k}d"] = counted.astype(float)
    keep = lambda d: {s: v[v.index >= start] for s, v in d.items()}  # noqa: E731
    return keep(out), keep(ns)


# ---------------------------------------------------------------- ratios
def rebased_ratio(num: pd.Series, den: pd.Series,
                  start: pd.Timestamp | None = None) -> pd.Series:
    """num/den rebased to 100 at the first session both are valid (and >= start).

    The start floor makes the panel-wide start hold by construction for the
    pure-vendor ratios too; their natural first dates already sit after it, so
    this trims nothing on the real download.
    """
    both = pd.concat([num.rename("n"), den.rename("d")], axis=1, sort=True).dropna()
    if start is not None:
        both = both[both.index >= start]
    if both.empty:
        return pd.Series(dtype=float)
    r = both["n"] / both["d"]
    return 100.0 * r / r.iloc[0]


# ---------------------------------------------------------------- assembly
class Long:
    def __init__(self) -> None:
        self.parts: list[pd.DataFrame] = []

    def add(self, series: str, group: str, values: pd.Series, n: pd.Series | int,
              kind: str) -> None:
        v = values.dropna()
        if v.empty:
            return
        nn = n.reindex(v.index) if isinstance(n, pd.Series) else pd.Series(n, index=v.index)
        self.parts.append(pd.DataFrame({"date": v.index, "series": series, "group": group,
                                        "value": v.to_numpy(dtype=float),
                                        "n": nn.to_numpy(dtype="int64"), "kind": kind}))

    def frame(self) -> pd.DataFrame:
        df = pd.concat(self.parts, ignore_index=True)
        return df.sort_values(["series", "group", "date"]).reset_index(drop=True)


def build(closes_path: Path, download_meta: Path, out: Path, root: Path = _ROOT,
          start: str = START, etf_dir: Path | None = None,
          house_index: Path | None = None, census_json: Path | None = None) -> dict:
    start_ts = pd.Timestamp(start)
    closes = load_closes(closes_path)
    dm = json.loads(Path(download_meta).read_text())
    cons = pd.read_parquet(root / "data/breadth/constituents.parquet")
    universe = [str(t) for t in cons.index]
    sectors: dict[str, list[str]] = {g: sorted(m["ticker"].tolist()) for g, m in
                                     bt.sector_membership(root / "data/breadth/constituents.parquet")
                                     .groupby("group", sort=True)}
    bmem = bt.basket_membership(root / "data/baskets/membership.json")
    baskets = {b: sorted(bmem[bmem["group"] == b]["ticker"].tolist()) for b in BASKETS}
    etfs = load_etfs(root, etf_dir)
    closes_u = closes[universe]

    groups = {UNIVERSE: universe, **sectors, **baskets}
    # Full closes, not closes_u: basket rosters hold members outside the S&P
    # universe; the house build prices them from the same download, so
    # restricting to universe columns would silently drop them.
    levels = ew_levels(closes, groups, start_ts)
    hb_lvl, hb_n, hb_facts = high_beta_cohorts(closes_u, etfs["SPY"], start_ts)
    levels[HIGH_BETA] = (hb_lvl, hb_n)

    L = Long()
    for g, (lvl, n) in levels.items():
        kind = "computed" if g == HIGH_BETA else "house"
        L.add("ew_index", g, lvl, n, kind)

    # 1. equal weight against cap weight
    ew_u, ew_u_n = levels[UNIVERSE]
    L.add("ew_vs_spy", UNIVERSE, rebased_ratio(ew_u, etfs["SPY"], start_ts), ew_u_n, "etf")
    L.add("rsp_vs_spy", "rsp", rebased_ratio(etfs["RSP"], etfs["SPY"], start_ts), 2, "etf")

    # 2. universe breadth (house history holds no universe rows; all new)
    ub, ub_n = universe_breadth(closes_u, start_ts)
    for s, v in ub.items():
        L.add(s, UNIVERSE, v, ub_n[s], "house")

    # 3. dispersion
    for s, gd in dispersion(closes_u, sectors, start_ts).items():
        for g, (v, n) in gd.items():
            L.add(s, g, v, n, "house")
    for s, (v, n) in sector_dispersion(levels, sorted(sectors), start_ts).items():
        L.add(s, UNIVERSE, v, n, "house")

    # 4. leadership concentration (count-based; no historical S&P weights on main)
    ld, ld_n = leadership(closes_u, ew_u, start_ts)
    for s, v in ld.items():
        L.add(s, UNIVERSE, v, ld_n[s], "house")

    # 5. relative indices
    num_levels = {"ai_software": (levels["ai_software"][0], levels["ai_software"][1], "house"),
                  "non_ai_software": (levels["non_ai_software"][0], levels["non_ai_software"][1], "house"),
                  "igv": (etfs["IGV"], None, "etf"),
                  HIGH_BETA: (hb_lvl, hb_n, "computed"),
                  "sphb": (etfs["SPHB"], None, "etf")}
    den_levels = {"ew_universe": (ew_u, ew_u_n, "house"),
                  "ai_semiconductors": (levels["ai_semiconductors"][0], levels["ai_semiconductors"][1], "house"),
                  "soxx": (etfs["SOXX"], None, "etf")}
    for ns, (nl, nn, nk) in num_levels.items():
        for ds, (dl, dn, dk) in den_levels.items():
            kind = "etf" if "etf" in (nk, dk) else ("computed" if "computed" in (nk, dk) else "house")
            n = nn if nn is not None else (dn if dn is not None else 2)
            L.add(f"rel_{ns}_vs_{ds}", ns, rebased_ratio(nl, dl, start_ts), n, kind)

    df = L.frame()
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    pq = out / "regime_inputs_daily_current.parquet"
    df.to_parquet(pq, index=False, compression="zstd")

    meta = _meta(df, pq, root, closes, dm, cons, bmem, etf_dir, hb_facts,
                 house_index, levels, census_json, start_ts)
    (out / "regime_inputs_current.meta.json").write_text(json.dumps(meta, indent=1) + "\n")
    return meta


# ---------------------------------------------------------------- dated basis
def load_spy(root: Path, etf_dir: Path | None = None) -> pd.Series:
    """SPY close only (the dated build's single ETF leg), read-only."""
    if etf_dir is not None:
        p = Path(etf_dir) / "SPY.parquet"
    else:
        raw = subprocess.run(["git", "-C", str(root), "show",
                              "origin/main:data/yahoo/SPY.parquet"],
                             capture_output=True, check=True).stdout
        p = Path(tempfile.mkdtemp(prefix="regime_spy_")) / "SPY.parquet"
        p.write_bytes(raw)
    return pd.read_parquet(p)[ETF_COLUMN].astype(float).sort_index()


def _fixchg_defs() -> dict[str, dict]:
    d: dict[str, dict] = {}
    for w in WINDOWS:
        for k in CHANGE_HORIZONS:
            d[f"fix_chg_pct_above_{w}_{k}"] = {
                "definition": (f"like-for-like change (points) of the percent-above-{w} share "
                               f"over {k} sessions: universe members at t with a defined "
                               f"{w}-session average at BOTH t and t-k; their share above at t "
                               f"minus the share of the same names at t-k"),
                "source": "engine.group_breadth_history.fixed_set_change",
                "gaps": FIXCHG_GAP}
            d[f"n_fixed_{w}_{k}"] = {
                "definition": (f"members counted at both ends of the {k}-session fixed-set "
                               f"change of the percent-above-{w} share (defined {w}-session "
                               f"average at t and t-k)"),
                "source": "engine.group_breadth_history.fixed_set_change",
                "gaps": FIXCHG_GAP}
    return d


def build_dated(closes_path: Path, pit_dir: Path, out: Path, root: Path = _ROOT,
                start: str = START_DATED, etf_dir: Path | None = None,
                minimum: bool = False) -> dict:
    """Regime inputs on the dated S&P 500 membership windows (Tiingo archive).

    Same statistics as the current basis, same engine functions; the universe
    is the dated members on each date. Cleaning and the missing-rows sentence
    reuse scripts.build_group_breadth_history, so this file and the house dated
    sector history read the archive identically. Aggregates and counts only."""
    start_ts = pd.Timestamp(start)
    closes, dropped = gb.drop_partial_rows(pd.read_parquet(closes_path).sort_index())
    mem = gb.membership_dated(pit_dir, "sp500")
    pairs = gb.duplicate_series_pairs(closes, mem)
    closes = gb.count_duplicates_once(closes, pairs)
    used = sorted(set(mem["ticker"]) & set(closes.columns))
    closes_u = closes[used]
    mem_u = mem.copy()
    mem_u["group"] = UNIVERSE
    sector_names = sorted(mem["group"].dropna().unique().tolist())
    sectors: dict[str, list[str]] = {
        g: sorted(set(mem.loc[mem["group"] == g, "ticker"]) & set(used))
        for g in sector_names}

    idx = closes_u.index
    codes_u, _ = gbh.assign_groups(idx, used, mem_u, [UNIVERSE])
    mask_u = pd.DataFrame(codes_u == 0, index=idx, columns=used)
    codes_s, _ = gbh.assign_groups(idx, used, mem, sector_names)
    masks = {UNIVERSE: mask_u,
             **{g: pd.DataFrame(codes_s == j, index=idx, columns=used)
                for j, g in enumerate(sector_names)}}

    spy = load_spy(root, etf_dir)
    rets = daily_returns(closes_u)
    priced = closes_u.notna()
    ew_u, ew_u_n = ew_level_held(rets, priced, mask_u, start_ts)
    levels: dict[str, tuple[pd.Series, pd.Series]] = {UNIVERSE: (ew_u, ew_u_n)}
    for g in sector_names:
        levels[g] = ew_level_held(rets, priced, masks[g], start_ts)
    hb_lvl, hb_n, hb_facts = high_beta_cohorts(closes_u, spy, start_ts, member_mask=mask_u)
    levels[HIGH_BETA] = (hb_lvl, hb_n)

    L = Long()
    for g, (lvl, n) in levels.items():
        L.add("ew_index", g, lvl, n, "computed" if g == HIGH_BETA else "house")
    L.add("ew_vs_spy", UNIVERSE, rebased_ratio(ew_u, spy, start_ts), ew_u_n, "etf")

    ub, ub_n = universe_breadth(closes_u, start_ts, membership=mem_u)
    for s, v in ub.items():
        L.add(s, UNIVERSE, v, ub_n[s], "house")
    fc, fc_n = universe_fixed_change(closes_u, start_ts, membership=mem_u)
    # Blank the fixed-set start window (dated basis only): an end date t keeps
    # its fix_chg / n_fixed row for horizon k only when at least k sessions of
    # dated membership lie before it, so the start session t-k never reads
    # closes from before the first dated-membership session. The diff series
    # already start there; this aligns the fixed-set lines with them. Rows are
    # removed, not set null; universe_fixed_change itself is unchanged.
    first_mem = pd.Timestamp(mem["start_date"].min())
    mem_pos = int(idx.searchsorted(first_mem))
    for s in fc:
        k = int(s.rsplit("_", 1)[-1])
        if mem_pos + k >= len(idx):
            fc[s] = fc[s].iloc[:0]
            fc_n[s] = fc_n[s].iloc[:0]
        else:
            cut = idx[mem_pos + k]
            fc[s] = fc[s][fc[s].index >= cut]
            fc_n[s] = fc_n[s][fc_n[s].index >= cut]
    for s, v in fc.items():
        L.add(s, UNIVERSE, v, fc_n[s], "house")

    for s, gd in dispersion(closes_u, sectors, start_ts, masks=masks).items():
        for g, (v, n) in gd.items():
            L.add(s, g, v, n, "house")
    for s, (v, n) in sector_dispersion(levels, sector_names, start_ts).items():
        L.add(s, UNIVERSE, v, n, "house")

    ld, ld_n = leadership(closes_u, ew_u, start_ts, in_window=mask_u)
    for s, v in ld.items():
        L.add(s, UNIVERSE, v, ld_n[s], "house")
    L.add("rel_high_beta_computed_vs_ew_universe", HIGH_BETA,
          rebased_ratio(hb_lvl, ew_u, start_ts), hb_n, "computed")

    df = L.frame()
    if minimum:
        df = df[df["series"].isin(MINIMUM_SERIES)
                & ~(df["series"].isin(MINIMUM_UNIVERSE_ONLY) & (df["group"] != UNIVERSE))]
        df = df.reset_index(drop=True)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    pq = out / "regime_inputs_dated_sp500_daily.parquet"
    df.to_parquet(pq, index=False, compression="zstd")

    sentence, stats = gb.missing_sentence(closes, mem, "dated")
    stats = {k: v for k, v in stats.items() if not k.endswith("_sample")}
    if len(pairs):
        sentence += (f" {len(pairs)} ticker pair(s) carry the same price series and are "
                     f"counted once (the second ticker is not counted over the span); "
                     f"names withheld under the archive rule.")
    else:
        sentence += (" Duplicate-series scan: no two member tickers carry the same price "
                     "series (identical daily returns or a constant price ratio).")
    meta = _dated_meta(df, pq, closes_path, pit_dir, closes, mem, dropped, pairs,
                       sentence, stats, hb_facts, start_ts, minimum)
    (out / "regime_inputs_dated_sp500.meta.json").write_text(json.dumps(meta, indent=1) + "\n")
    return meta


def _dated_meta(df: pd.DataFrame, pq: Path, closes_path: Path, pit_dir: Path,
                closes: pd.DataFrame, mem: pd.DataFrame, dropped: list, pairs: pd.DataFrame,
                sentence: str, stats: dict, hb_facts: dict, start_ts: pd.Timestamp,
                minimum: bool) -> dict:
    base = _series_defs(hb_facts)
    fix = _fixchg_defs()
    src_flags = "Tiingo archive member closes via engine.group_breadth_history.member_flags"
    d: dict[str, dict] = {}

    def take(s: str, source: str, basis: str = BASIS_DATED_NOTE, gaps: str = ARCHIVE_GAP,
             definition: str | None = None) -> None:
        e = dict(base[s] if s in base else fix[s])
        e["definition"] = definition if definition is not None else e["definition"]
        e["source"], e["basis"], e["gaps"] = source, basis, gaps
        d[s] = e

    take("ew_index", "Tiingo archive member closes via engine.baskets._ew_level "
                     "(dated in-window members)")
    take("ew_vs_spy", "dated EW index; SPY close on main", BASIS_DATED_ETF, DIVIDEND_GAP)
    for w in WINDOWS:
        take(f"pct_above_{w}", src_flags, gaps=COUNTED_GAP + "; " + ARCHIVE_GAP)
        take(f"n_above_{w}", src_flags, gaps=COUNTED_GAP + "; " + ARCHIVE_GAP)
        for k in CHANGE_HORIZONS:
            take(f"diff_pct_above_{w}_{k}d",
                 "Tiingo archive member closes via engine.group_breadth_history.level_change",
                 gaps=COUNTED_GAP + "; " + ARCHIVE_GAP)
    first_mem = pd.Timestamp(mem["start_date"].min())
    fixchg_clause = (
        "the fixed set is the dated members at t with a defined average at both t and t-k; "
        "it is not membership at both ends. Rows whose start session precedes the first "
        f"dated-membership session ({first_mem.date()}) are not produced.")
    for s, entry in fix.items():
        take(s, entry["source"] + " on Tiingo archive closes",
             gaps=entry["gaps"] + "; " + ARCHIVE_GAP,
             definition=entry["definition"] + "; " + fixchg_clause)
    for s in ("new_highs_252", "new_lows_252", "nh_nl_252", "n_counted_nh"):
        take(s, "Tiingo archive member closes; house high52w_new/low52w_new convention",
             gaps=WINDOW_GAP + "; " + ARCHIVE_GAP,
             definition=base[s]["definition"] + "; the member must be in-window on the session")
    for k in DISPERSION_HORIZONS:
        take(f"dispersion_{k}d", "Tiingo archive member closes",
             gaps=DATED_DISPERSION_GAP + "; " + ARCHIVE_GAP,
             definition=base[f"dispersion_{k}d"]["definition"]
             + "; dated members must be in-window at both ends")
        take(f"sector_dispersion_{k}d", "dated sector EW levels (Tiingo archive closes)",
             gaps=SECTOR_EW_GAP + "; " + ARCHIVE_GAP)
    for k in LEADERSHIP_HORIZONS:
        take(f"pct_beat_ew_{k}d", "Tiingo archive member closes and dated EW universe index",
             gaps=DATED_LEADERSHIP_GAP + "; " + ARCHIVE_GAP)
        take(f"n_beat_ew_{k}d", "Tiingo archive member closes and dated EW universe index",
             gaps=DATED_LEADERSHIP_GAP + "; " + ARCHIVE_GAP)
    take("rel_high_beta_computed_vs_ew_universe", "dated EW levels (Tiingo archive closes)",
         BASIS_DATED_COMPUTED, DATED_HIGH_BETA_GAP)

    firsts = df.groupby("series")["date"].min()
    kinds = df.groupby("series")["kind"].agg(lambda s: sorted(set(s)))
    series = {}
    for s in sorted(d):
        if s not in firsts.index:
            continue
        series[s] = {**d[s], "first_date": str(firsts[s].date()),
                     "kind": kinds[s][0] if len(kinds[s]) == 1 else kinds[s]}
    return {
        "basis": BASIS_DATED, "basis_note": BASIS_DATED_NOTE,
        "no_outcomes": NO_OUTCOMES,
        "scope": "series only: group and universe numbers; no member ticker, row or price; "
                 "no regime assignment of any kind; archive aggregates and counts only",
        "set": "minimum" if minimum else "full",
        "start": {"date": str(start_ts.date()),
                  "note": "first dated membership start; averages and 252-session windows "
                          "read the member's own earlier archive closes, which may predate "
                          "its entry"},
        "floors": {"index": bt.INDEX_FLOOR, "share_and_statistic": bt.BREADTH_FLOOR,
                   "source": "scripts/build_tree_breadth_and_index.py (COO ruling 34 s2)"},
        "index": {"rebalance_rule": bt.REBALANCE_RULE,
                  "return": "total return (archive adjusted closes)",
                  "floor_gap": bt.FLOOR_GAP_NOTE},
        "high_beta_computed": hb_facts,
        "price_source": TIINGO_SOURCE, "price_note": TIINGO_PRICE_NOTE,
        "data_end": str(closes.index.max().date()),
        "inputs": [{"path": str(p), "sha256_16": _sha(p)[:16]} for p in
                   (closes_path, pit_dir / "sp1500_pit_membership.parquet",
                    pit_dir / "sp1500_pit_sectors.parquet")],
        "missing": sentence,
        "coverage": stats,
        "dropped_partial_rows_count": len(dropped),
        "dropped_partial_rows_rule": ("centred 21-row median of priced names; a row under "
                                      "half is dropped. Looks ahead up to 10 rows to decide "
                                      "which rows are sessions; values themselves use only "
                                      "data on or before their date."),
        "dropped_partial_rows_note": ("same archive and rule as the house dated sector "
                                      "history; the session list lives in "
                                      "group_breadth_dated_sp500.meta.json"),
        "duplicate_series_pairs_count": int(len(pairs)),
        "duplicate_series_rule": ("month-by-month hash of daily returns, then pairwise "
                                  "check: >=60 identical returns and >=95% identical "
                                  "between the first and last identical session. Detection "
                                  "and labelling only; no store repaired. Names withheld "
                                  "under the archive rule."),
        "not_included": NOT_INCLUDED,
        "universe": {"registry": "sp1500_pit_membership.parquet (src=sp500)",
                     "rows": int(len(mem)), "members": int(mem["ticker"].nunique()),
                     "sectors": int(mem["group"].nunique()),
                     "labels": "sp1500_pit_sectors.parquet, as of now, not era-correct"},
        "etfs": {"SPY": {"path": "data/yahoo/SPY.parquet", "ref": "origin/main",
                         "column": ETF_COLUMN, "first_date": ETF_FIRST["SPY"]}},
        "series": series,
        "files": [pq.name], "rows": {pq.name: int(len(df))},
        "bytes": {pq.name: int(pq.stat().st_size)},
        "columns": list(df.columns),
        "missing_rule": "a session with no valid value carries no row; n is the counted "
                        "members (or priced members for a level) beside every value",
        "dispersion_units": "percent (a 0.01 return reads 1.0); ddof=1",
        "ratio_rule": "every ratio is rebased to 100 at the first session both legs are valid",
        "engine": "engine.baskets._ew_level; engine.group_breadth_history.member_flags/"
                  "group_levels/level_change/fixed_set_change/assign_groups; "
                  "scripts.build_group_breadth_history cleaning and membership",
    }


def build_fixchg_current(closes_path: Path, download_meta: Path, out: Path,
                         root: Path = _ROOT, start: str = START) -> dict:
    """Like-for-like universe change on the CURRENT basis, in a separate small
    file: same members and prices as the frozen regime_inputs_daily_current,
    which stays byte-identical."""
    start_ts = pd.Timestamp(start)
    closes = load_closes(closes_path)
    dm = json.loads(Path(download_meta).read_text())
    cons = pd.read_parquet(root / "data/breadth/constituents.parquet")
    universe = [str(t) for t in cons.index]
    fc, fc_n = universe_fixed_change(closes[universe], start_ts)
    L = Long()
    for s, v in fc.items():
        L.add(s, UNIVERSE, v, fc_n[s], "house")
    df = L.frame()
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    pq = out / "regime_inputs_fixchg_current.parquet"
    df.to_parquet(pq, index=False, compression="zstd")

    defs = _fixchg_defs()
    firsts = df.groupby("series")["date"].min()
    series = {s: {**defs[s], "basis": BASIS_HOUSE, "first_date": str(firsts[s].date()),
                  "kind": "house"} for s in sorted(defs) if s in firsts.index}
    meta = {
        "basis": bt.BASIS, "basis_note": bt.BASIS_NOTE,
        "no_outcomes": NO_OUTCOMES,
        "purpose": "like-for-like universe change on the same members and prices as "
                   "regime_inputs_daily_current.parquet; a separate file so the frozen "
                   "current outputs stay byte-identical",
        "scope": "series only: universe numbers; no member ticker, row or price; "
                 "no regime assignment of any kind",
        "start": {"date": str(start_ts.date()), "rule": START_RULE, "note": START_NOTE},
        "floors": {"share_and_statistic": bt.BREADTH_FLOOR,
                   "source": "scripts/build_tree_breadth_and_index.py (COO ruling 34 s2)"},
        "price_source": PRICE_SOURCE, "price_vintage": dm.get("vintage"),
        "price_retry": _retry_note(dm.get("retry")),
        "price_topup": _topup_note(dm.get("topup")),
        "inputs": [{"path": str(closes_path), "sha256": _sha(closes_path)},
                   {"path": "data/breadth/constituents.parquet",
                    "sha256": _sha(root / "data/breadth/constituents.parquet")}],
        "universe": {"registry": "data/breadth/constituents.parquet",
                     "registry_sha256": _sha(root / "data/breadth/constituents.parquet"),
                     "members": int(len(cons)),
                     "basis": "today's S&P 500 members, same as regime_inputs_daily_current.parquet"},
        "data_end": str(closes.index.max().date()),
        "series": series,
        "files": [pq.name], "rows": {pq.name: int(len(df))},
        "bytes": {pq.name: int(pq.stat().st_size)},
        "columns": list(df.columns),
        "missing_rule": "a session with no valid value carries no row; n is the members "
                        "counted at both ends beside every value",
        "engine": "engine.group_breadth_history.fixed_set_change/member_flags/assign_groups",
    }
    (out / "regime_inputs_fixchg_current.meta.json").write_text(json.dumps(meta, indent=1) + "\n")
    return meta


# ---------------------------------------------------------------- meta
def _series_defs(hb_facts: dict) -> dict[str, dict]:
    d: dict[str, dict] = {}
    d["ew_index"] = {"definition": "equal-weight total-return index level of the group, chained from 1.0 (daily rebalance)",
                     "source": "house member closes via engine.baskets._ew_level",
                     "basis": BASIS_HOUSE, "gaps": SURVIVOR_GAP}
    d["ew_vs_spy"] = {"definition": "EW universe index divided by SPY close, rebased to 100 at the first common session",
                      "source": "house EW index; SPY close on main",
                      "basis": BASIS_MIXED, "gaps": DIVIDEND_GAP}
    d["rsp_vs_spy"] = {"definition": "RSP close divided by SPY close, rebased to 100 at the first common session",
                      "source": "RSP and SPY close on main",
                      "basis": BASIS_ETF, "gaps": "RSP starts 2003-05-01; " + DIVIDEND_GAP}
    for w in WINDOWS:
        d[f"pct_above_{w}"] = {"definition": f"percent of counted universe members strictly above their own {w}-session simple moving average",
                               "source": "house member closes via engine.group_breadth_history.member_flags",
                               "basis": BASIS_HOUSE, "gaps": COUNTED_GAP}
        d[f"n_above_{w}"] = {"definition": f"count of universe members strictly above their own {w}-session SMA (n = counted members)",
                             "source": "house member closes via engine.group_breadth_history.member_flags",
                             "basis": BASIS_HOUSE, "gaps": COUNTED_GAP}
        for k in CHANGE_HORIZONS:
            d[f"diff_pct_above_{w}_{k}d"] = {"definition": f"plain difference (points) of the percent-above-{w} share, session t minus t-{k}",
                                             "source": "house member closes via engine.group_breadth_history.level_change",
                                             "basis": BASIS_HOUSE, "gaps": COUNTED_GAP}
    d["new_highs_252"] = {"definition": "count of universe members whose close strictly exceeds the prior 252-session maximum (full window)",
                          "source": "house member closes; house high52w_new convention",
                          "basis": BASIS_HOUSE, "gaps": WINDOW_GAP}
    d["new_lows_252"] = {"definition": "count of universe members whose close is strictly below the prior 252-session minimum (full window)",
                         "source": "house member closes; house low52w_new convention",
                         "basis": BASIS_HOUSE, "gaps": WINDOW_GAP}
    d["nh_nl_252"] = {"definition": "new 252-session highs minus new lows (counts)",
                      "source": "house member closes; house high52w_new/low52w_new convention",
                      "basis": BASIS_HOUSE, "gaps": WINDOW_GAP}
    d["n_counted_nh"] = {"definition": "universe members with a close and a full prior 252-session window on the session",
                         "source": "house member closes", "basis": BASIS_HOUSE, "gaps": WINDOW_GAP}
    for k in DISPERSION_HORIZONS:
        d[f"dispersion_{k}d"] = {"definition": f"cross-sectional standard deviation (ddof=1, percent) of member simple {k}-session returns, universe and per sector",
                                 "source": "house member closes", "basis": BASIS_HOUSE,
                                 "gaps": "members without both endpoint closes are not counted"}
        d[f"sector_dispersion_{k}d"] = {"definition": f"standard deviation (ddof=1, percent) across the 11 sector EW index simple {k}-session returns (n = sectors with a valid return)",
                                        "source": "house sector EW levels",
                                        "basis": BASIS_HOUSE, "gaps": SURVIVOR_GAP}
    for k in LEADERSHIP_HORIZONS:
        d[f"pct_beat_ew_{k}d"] = {"definition": f"percent of counted members whose simple {k}-session return strictly exceeds the EW universe index's over the same window",
                                  "source": "house member closes and EW universe index",
                                  "basis": BASIS_HOUSE, "gaps": SURVIVOR_GAP}
        d[f"n_beat_ew_{k}d"] = {"definition": f"count of members beating the EW universe index over {k} sessions (n = counted members)",
                                "source": "house member closes and EW universe index",
                                "basis": BASIS_HOUSE, "gaps": SURVIVOR_GAP}
    num_txt = {"ai_software": "ai_software basket EW index", "non_ai_software": "non_ai_software basket EW index",
               "igv": "IGV close", HIGH_BETA: "computed high-beta EW index", "sphb": "SPHB close"}
    den_txt = {"ew_universe": "the EW universe index", "ai_semiconductors": "the ai_semiconductors basket EW index",
               "soxx": "SOXX close"}
    for ns, nt in num_txt.items():
        for ds, dt in den_txt.items():
            etf_leg = ns in ("igv", "sphb") or ds == "soxx"
            gaps = []
            if ns == HIGH_BETA:
                gaps.append("computed, not curated, survivors only (rule in high_beta_computed)")
            elif ns not in ("igv", "sphb"):
                gaps.append(SURVIVOR_GAP)
            if etf_leg:
                gaps.append(DIVIDEND_GAP)
            if ns == "igv":
                gaps.append("IGV starts 2001-07-17")
            if ns == "sphb":
                gaps.append("SPHB starts 2011-05-05")
            if ds == "soxx":
                gaps.append("SOXX starts 2001-07-13")
            if ns in ("igv", "sphb") and ds == "soxx":
                basis, src = BASIS_ETF, "ETF close on main"
            elif etf_leg:
                basis, src = BASIS_MIXED, "house EW levels and ETF close on main"
            elif ns == HIGH_BETA:
                basis, src = BASIS_COMPUTED, "house EW levels"
            else:
                basis, src = BASIS_HOUSE, "house EW levels"
            d[f"rel_{ns}_vs_{ds}"] = {"definition": f"{nt} divided by {dt}, rebased to 100 at the first common session",
                                      "source": src, "basis": basis, "gaps": "; ".join(gaps)}
    return d


def _meta(df: pd.DataFrame, pq: Path, root: Path, closes: pd.DataFrame, dm: dict,
          cons: pd.DataFrame, bmem: pd.DataFrame, etf_dir: Path | None, hb_facts: dict,
          house_index: Path | None, levels: dict, census_json: Path | None,
          start_ts: pd.Timestamp) -> dict:
    defs = _series_defs(hb_facts)
    firsts = df.groupby("series")["date"].min()
    kinds = df.groupby("series")["kind"].agg(lambda s: sorted(set(s)))
    series = {}
    for s in sorted(defs):
        if s not in firsts.index:
            continue
        # Compact by design (continuation brief): one definition line, first date,
        # source, basis, kind, gaps (at most 3 short sentences). No per-date or
        # per-ticker lists; the rates/credit/dollar list lives in the report.
        series[s] = {**defs[s], "first_date": str(firsts[s].date()),
                     "kind": kinds[s][0] if len(kinds[s]) == 1 else kinds[s]}
    meta = {
        "basis": bt.BASIS, "basis_note": bt.BASIS_NOTE,
        "no_outcomes": NO_OUTCOMES,
        "scope": "series only: group and universe numbers; no member ticker, row or price; "
                 "no regime assignment of any kind",
        "start": {"date": str(start_ts.date()), "rule": START_RULE, "note": START_NOTE,
                  "reason_before": bt.REASON_START},
        "floors": {"index": bt.INDEX_FLOOR, "share_and_statistic": bt.BREADTH_FLOOR,
                   "source": "scripts/build_tree_breadth_and_index.py (COO ruling 34 s2)"},
        "index": {"rebalance_rule": bt.REBALANCE_RULE, "return": "total return (auto_adjust closes)",
                  "floor_gap": bt.FLOOR_GAP_NOTE, "dividend_effect": bt.INDEX_SENTENCE,
                  "survivors_only_effect": SURVIVOR_LONG},
        "high_beta_computed": hb_facts,
        "price_source": PRICE_SOURCE, "price_vintage": dm.get("vintage"),
        "price_retry": _retry_note(dm.get("retry")),
        "price_topup": _topup_note(dm.get("topup")),
        "etf_source": ETF_SOURCE,
        "etfs": {t: {"path": f"data/yahoo/{t}.parquet", "ref": "origin/main",
                     "column": ETF_COLUMN, "first_date": ETF_FIRST[t]} for t in ETFS},
        "universe": {"registry": "data/breadth/constituents.parquet",
                     "registry_sha256": _sha(root / "data/breadth/constituents.parquet"),
                     "members": int(len(cons)), "sectors": int(cons["sector"].nunique()),
                     "basis": "today's S&P 500 members and today's GICS sector labels, "
                              "same family sector basis as scripts/build_tree_breadth_and_index.py"},
        "baskets": {"registry": "data/baskets/membership.json",
                    "registry_sha256": _sha(root / "data/baskets/membership.json"),
                    "active_members": {b: int((bmem["group"] == b).sum()) for b in BASKETS}},
        "house_history_check": {
            "question": "does the house breadth history already hold universe rows?",
            "answer": "no universe group exists in any house history file; every universe "
                      "breadth series here is new",
            "files_checked": ["group_breadth_daily_current.parquet (11 sector groups)",
                              "group_breadth_daily_dated_sp500.parquet (11 sector groups)",
                              "basket_breadth_daily_current.parquet (49 basket groups)",
                              "house_breadth_weekly_current.parquet (gmi/rel families)",
                              "house_ew_index_daily_current.parquet (sector/basket/gmi/rel groups)"],
            "live_surface_note": "data/breadth/breadth.parquet (the live nightly collector "
                                 "surface) does carry universe pct_above_50/200 and nh/nl, "
                                 "but on collector-cache prices, not the house download; it "
                                 "is not history and is not mixed into this house-basis file",
            "source_rule": bt.SOURCE_SENTENCE},
        "weights_check": {
            "question": "are historical S&P 500 index weights on main?",
            "answer": "no: constituents files hold today's members only (name, sector), "
                      "desk_weights/shadow.json is desk allocation, rate_futures constituents "
                      "are futures contracts, cpi_relative_importance is CPI weights",
            "decision": "count-based leadership only; the weight-based top-10 measure is skipped"},
        "data_end": str(closes.index.max().date()),
        "series": series,
        "files": [pq.name], "rows": {pq.name: int(len(df))},
        "bytes": {pq.name: int(pq.stat().st_size)},
        "columns": list(df.columns),
        "missing_rule": "a session with no valid value carries no row; n is the counted "
                        "members (or priced members for a level) beside every value",
        "dispersion_units": "percent (a 0.01 return reads 1.0); ddof=1",
        "ratio_rule": "every ratio is rebased to 100 at the first session both legs are valid",
        "engine": "engine.baskets._ew_level; engine.group_breadth_history.member_flags/"
                  "group_levels/level_change; scripts.build_tree_breadth_and_index.group_index",
    }
    if house_index is not None and Path(house_index).exists():
        meta["self_check_house_index"] = _check_house(df, Path(house_index), root)
    if census_json is not None and Path(census_json).exists():
        # Compact summary only: the full path/series/first-date list lives in the
        # report (REGIME_INPUTS_REPORT.md), not the sidecar (continuation brief).
        cen = json.loads(Path(census_json).read_text())
        meta["rates_credit_dollar_on_main"] = {
            "ref": cen.get("ref"), "n_series": cen.get("n_series"),
            "scope_note": cen.get("scope_note"),
            "full_list_in": "research/breadth_history/REGIME_INPUTS_REPORT.md",
            "note": "census only, no build; per-series path/series/first-date list in the report"}
    return meta


def _check_house(df: pd.DataFrame, house_path: Path, root: Path) -> dict:
    """Recomputed sector/basket EW levels vs the committed house daily index."""
    h = pd.read_parquet(house_path)
    h = h[h["family"].isin(["sector", "basket"]) & h["level"].notna()]
    ours = df[(df["series"] == "ew_index") & df["group"].isin(set(h["group"]))]
    m = ours.merge(h[["date", "group", "level"]], on=["date", "group"], how="inner")
    diff = (m["value"] - m["level"]).abs()
    per = diff.groupby(m["group"]).max()
    hp = Path(house_path).resolve()
    try:
        house_file = str(hp.relative_to(Path(root).resolve()))
    except ValueError:
        house_file = str(hp)
    return {"house_file": house_file, "compared_rows": int(len(m)),
            "max_abs_level_diff": float(diff.max()) if len(m) else None,
            "max_abs_level_diff_by_group": {g: float(v) for g, v in per.items()},
            "note": "same download vintage; levels rounded to 6 decimals in the house file"}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--closes", type=Path, required=True)
    ap.add_argument("--download-meta", type=Path, default=None)
    ap.add_argument("--out", type=Path, default=_ROOT / "data/breadth/history")
    ap.add_argument("--basis", choices=("current", "dated", "fixchg-current"),
                    default="current")
    ap.add_argument("--start", default=None)
    ap.add_argument("--etf-dir", type=Path, default=None)
    ap.add_argument("--pit-dir", type=Path, default=None,
                    help="dated basis: scratch dir holding the two sp1500 parquets")
    ap.add_argument("--minimum", action="store_true",
                    help="dated basis: write the COO 13:58Z minimum set only")
    ap.add_argument("--house-index", type=Path, default=None)
    ap.add_argument("--census-json", type=Path, default=None)
    a = ap.parse_args()
    if a.basis == "dated":
        if a.pit_dir is None:
            ap.error("--basis dated requires --pit-dir")
        meta = build_dated(a.closes, a.pit_dir, a.out, start=a.start or START_DATED,
                           etf_dir=a.etf_dir, minimum=a.minimum)
    elif a.basis == "fixchg-current":
        if a.download_meta is None:
            ap.error("--basis fixchg-current requires --download-meta")
        meta = build_fixchg_current(a.closes, a.download_meta, a.out,
                                    start=a.start or START)
    else:
        if a.download_meta is None:
            ap.error("--basis current requires --download-meta")
        meta = build(a.closes, a.download_meta, a.out, start=a.start or START,
                     etf_dir=a.etf_dir, house_index=a.house_index,
                     census_json=a.census_json)
    print(json.dumps({"rows": meta["rows"], "bytes": meta["bytes"],
                      "series": len(meta["series"]), "data_end": meta["data_end"],
                      "self_check": meta.get("self_check_house_index")}))


if __name__ == "__main__":
    main()