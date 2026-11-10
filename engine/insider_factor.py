"""Insider-buying cross-sectional signal construction (Phase-0 factor research).

The aggregate net-dollar leaderboard (`collectors/sec_insider._insider_block`) is a
display gadget — it has never been IC-tested and it sums every open-market trade
into one number, which the literature says destroys the signal. This module builds
the constructions that actually carry edge, from the point-in-time per-transaction
panel (`collectors/sec_insider.backfill_panel`):

  * opportunistic-vs-routine (Cohen–Malloy–Pomorski) — drop insiders trading on a
    predictable annual cadence; only the OFF-schedule trades inform.
  * distinct-insider CLUSTERS — N independent insiders buying beats one big ticket.
  * role weighting — a CEO/CFO buy outweighs a director outweighs a 10% holder.
  * size-normalisation — net buy $ ÷ market cap, so a $5m buy at a $5bn small-cap
    isn't drowned out by $5m at a megacap.

Everything is causal: a trade only enters a rebalance once its FILING_DATE has
passed (the date it became public), and the routine/opportunistic flag for a trade
in calendar month M of year Y looks only at the SAME insider's trades in month M of
years Y−1/Y−2/Y−3 — strictly earlier, so no look-ahead.

Pure compute (no I/O); the harness `scripts/insider_phase0.py` feeds it the panel,
the close matrix, sector map and PIT shares, and runs the IC/FDR/DSR gates.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

# Title keywords that mark a top-of-house officer (weighted above a line officer).
_TOP_TITLE = ("CHIEF EXEC", "CEO", "CHIEF FIN", "CFO", "PRESIDENT", "CHAIR",
              "FOUNDER", "CHIEF OPER", "COO", "PRINCIPAL EXEC", "PRINCIPAL FIN")


def classify_routine(panel: pd.DataFrame) -> pd.DataFrame:
    """Add an `is_routine` column (Cohen–Malloy–Pomorski). A transaction is ROUTINE
    if the same insider (rptownercik) also traded in the SAME calendar month in EACH
    of the three preceding years — a predictable, scheduled pattern that the
    literature finds carries ~no information. Opportunistic = everything else.

    Causal by construction: the test references only years Y−1/Y−2/Y−3, all strictly
    earlier than the trade being classified. (Trades in the first ~3 years of the
    panel are therefore mostly tagged opportunistic for lack of prior history —
    evaluate opportunistic variants from ~3y after the panel start.)"""
    p = panel
    cik = p["rptownercik"].to_numpy()
    yr = p["filing_date"].dt.year.to_numpy()
    mo = p["filing_date"].dt.month.to_numpy()
    present = set(zip(cik.tolist(), yr.tolist(), mo.tolist()))
    routine = np.fromiter(
        (((c, y - 1, m) in present and (c, y - 2, m) in present and (c, y - 3, m) in present)
         for c, y, m in zip(cik.tolist(), yr.tolist(), mo.tolist())),
        dtype=bool, count=len(p))
    out = panel.copy()
    out["is_routine"] = routine
    return out


def role_weights(panel: pd.DataFrame) -> pd.Series:
    """Per-transaction conviction weight by the filer's role/title:
    top officer (CEO/CFO/…) 1.5 · line officer 1.0 · director 0.6 · 10% holder 0.3."""
    title = panel["title"].fillna("").str.upper()
    is_top = title.apply(lambda t: any(k in t for k in _TOP_TITLE))
    w = pd.Series(0.2, index=panel.index)         # other/unknown
    w = w.mask(panel["is_tenpct"], 0.3)
    w = w.mask(panel["is_director"], 0.6)
    w = w.mask(panel["is_officer"], 1.0)
    w = w.mask(panel["is_officer"] & is_top, 1.5)
    return w


def _monthly(values: pd.Series, month: pd.Series, ticker: pd.Series,
             full: pd.PeriodIndex) -> pd.DataFrame:
    """Sum `values` into a (month × ticker) matrix on a gap-free month index."""
    g = values.groupby([month, ticker]).sum().unstack()
    return g.reindex(full).fillna(0.0)


def _monthly_nunique(key: pd.Series, month: pd.Series, ticker: pd.Series,
                     full: pd.PeriodIndex) -> pd.DataFrame:
    """Count distinct `key` (e.g. insider CIK) per (month × ticker)."""
    g = key.groupby([month, ticker]).nunique().unstack()
    return g.reindex(full).fillna(0.0)


def _to_grid(roll: pd.DataFrame, grid: list[pd.Timestamp]) -> pd.DataFrame:
    """Map a (month-period × ticker) rolling matrix onto the rebalance trading-date
    grid: each rebalance date D takes its own calendar month's trailing value."""
    rows = {}
    for d in grid:
        per = pd.Timestamp(d).to_period("M")
        if per in roll.index:
            rows[d] = roll.loc[per]
    return pd.DataFrame(rows).T if rows else pd.DataFrame()


def build_signals(panel: pd.DataFrame, grid: list[pd.Timestamp], *,
                  mcap: pd.DataFrame | None = None, k_months: int = 6) -> dict:
    """Cross-sectional insider signals as (rebalance-date × ticker) matrices.

    Each signal sums/counts open-market activity from the first calendar day of
    the trailing `k_months` through the actual rebalance filing-date cutoff.
    Buyer breadth counts distinct owners across that complete window.

    Variants (each also gets a sector-neutral pass in the harness):
      buy_usd        gross open-market purchase $              (size-confounded baseline)
      net_usd        purchase − sale $
      n_buyers       distinct insiders buying     (cluster / breadth — size-robust)
      opp_buy_usd    opportunistic-only purchase $
      opp_buyers     distinct opportunistic insiders buying    (the CMP headline)
      role_buy_usd   role-weighted purchase $ (CEO/CFO > director > 10%)
    If `mcap` (date×ticker market cap) is given, the three dollar signals also get a
    `*_mcap` size-normalised variant (net buy $ ÷ market cap)."""
    p = panel.copy()
    p["m"] = p["filing_date"].dt.to_period("M")
    full = pd.period_range(p["m"].min(), p["m"].max(), freq="M")
    if (isinstance(k_months, (bool, np.bool_))
            or not isinstance(k_months, (int, np.integer)) or k_months < 1):
        raise ValueError("k_months must be a positive integer")
    buys = p[p["code"] == "P"]
    sells = p[p["code"] == "S"]
    opp_buys = buys[~buys["is_routine"]] if "is_routine" in buys else buys
    p["_role_usd"] = role_weights(p) * p["usd"]

    # Preserve the panel-derived support of each original monthly matrix.
    # No trade inside an observed month is zero; an unobserved month is absent.
    buy_columns = buys.groupby("ticker")["usd"].sum().index
    sell_columns = sells.groupby("ticker")["usd"].sum().index
    opp_columns = opp_buys.groupby("ticker")["usd"].sum().index
    columns = {
        "buy_usd": buy_columns, "net_usd": buy_columns.union(sell_columns),
        "n_buyers": buy_columns, "opp_buy_usd": opp_columns,
        "opp_buyers": opp_columns, "role_buy_usd": buy_columns,
    }
    rows = {name: {} for name in columns}
    for d in grid:
        cutoff = pd.Timestamp(d)
        month = cutoff.to_period("M")
        if month not in full:
            continue
        start = (month - (k_months - 1)).start_time
        window = p[(p["filing_date"] >= start) & (p["filing_date"] <= cutoff)]
        b = window[window["code"] == "P"]
        s = window[window["code"] == "S"]
        o = b[~b["is_routine"]] if "is_routine" in b else b
        buy = b.groupby("ticker")["usd"].sum()
        sell = s.groupby("ticker")["usd"].sum()
        values = {
            "buy_usd": buy,
            "net_usd": buy.subtract(sell, fill_value=0.0),
            "n_buyers": b.groupby("ticker")["rptownercik"].nunique(),
            "opp_buy_usd": o.groupby("ticker")["usd"].sum(),
            "opp_buyers": o.groupby("ticker")["rptownercik"].nunique(),
            "role_buy_usd": b.groupby("ticker")["_role_usd"].sum(),
        }
        for name, value in values.items():
            rows[name][d] = value.reindex(columns[name], fill_value=0.0).astype(float)
    sigs = {name: pd.DataFrame(values).T if values else pd.DataFrame()
            for name, values in rows.items()}

    if mcap is not None:
        mc = mcap.reindex(index=grid)
        for base in ("net_usd", "opp_buy_usd", "role_buy_usd"):
            s = sigs[base]
            common = s.columns.intersection(mc.columns)
            norm = s[common] / mc[common].replace(0.0, np.nan)
            sigs[f"{base}_mcap"] = norm
    # Buy-only signals carry information only where there IS buying; zeros are
    # "no insider bought", which is the vast majority and uninformative as a rank.
    # Leave zeros in place (a true low rank) but drop all-zero columns per date in
    # the harness via the forward-return join.
    return sigs


def market_cap(closes_me: pd.DataFrame, shares_panel: pd.DataFrame,
               grid: list[pd.Timestamp]) -> pd.DataFrame:
    """PIT market cap (date×ticker) = month-end price × most-recent shares with
    asof_date ≤ the rebalance (causal). `shares_panel` is fundamentals_panel.parquet
    (ticker, shares, asof_date); `closes_me` month-end close prices on `grid`."""
    sp = shares_panel.dropna(subset=["shares", "asof_date"]).copy()
    sp["asof_date"] = pd.to_datetime(sp["asof_date"])
    sp = sp.sort_values("asof_date")
    out = pd.DataFrame(index=grid, columns=closes_me.columns, dtype=float)
    for d in grid:
        avail = sp[sp["asof_date"] <= pd.Timestamp(d)]
        if avail.empty:
            continue
        shares = avail.groupby("ticker")["shares"].last()
        px = closes_me.reindex(index=[d]).iloc[0] if d in closes_me.index else None
        if px is None:
            continue
        common = shares.index.intersection(px.dropna().index)
        out.loc[d, common] = px[common].to_numpy() * shares[common].to_numpy()
    return out
