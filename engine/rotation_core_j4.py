"""Rotation Core J4 — amplification: is within-sector RS selection more profitable inside leading sectors?

Bound to protocol_header_v1.json `candidates.J4` and PHASE2_ADDITIONS_v1.md section 7. Pure functions; research-only.
Formation at month-end session t uses prices <= t; execution at t+1 close; label to the next formation's execution
close. Sector membership is assigned statistically (max univariate R^2 vs eligible sector SPDRs over the 252 sessions
ending t, >= 200 paired observations). Stock daily returns are clipped at +/-50%.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

GICS_TO_ETF = {
    "Information Technology": "XLK", "Financials": "XLF", "Health Care": "XLV",
    "Consumer Discretionary": "XLY", "Consumer Staples": "XLP", "Energy": "XLE", "Industrials": "XLI",
    "Materials": "XLB", "Utilities": "XLU", "Real Estate": "XLRE", "Communication Services": "XLC",
}


def members_at(pit: pd.DataFrame, t: pd.Timestamp, legs=("sp500",)) -> list[str]:
    m = pit[pit["src"].isin(legs) & (pit["start_date"] <= t) & (pit["end_date"].isna() | (pit["end_date"] > t))]
    return sorted(set(m["ticker"]))


def still_member(pit: pd.DataFrame, ticker: str, d: pd.Timestamp, legs=("sp500",)) -> bool:
    m = pit[(pit["ticker"] == ticker) & pit["src"].isin(legs)]
    return bool(((m["start_date"] <= d) & (m["end_date"].isna() | (m["end_date"] > d))).any())


def assign_sectors(stock_r: pd.DataFrame, etf_r: pd.DataFrame, min_obs: int = 200) -> pd.Series:
    """Max-R^2 sector per stock over the supplied window (rows = sessions <= t)."""
    out = {}
    E = etf_r.to_numpy()
    for tkr in stock_r.columns:
        y = stock_r[tkr].to_numpy()
        best, bestr2 = None, -1.0
        for j, e in enumerate(etf_r.columns):
            x = E[:, j]
            ok = np.isfinite(y) & np.isfinite(x)
            if ok.sum() < min_obs:
                continue
            c = np.corrcoef(y[ok], x[ok])[0, 1]
            if np.isfinite(c) and c * c > bestr2:
                best, bestr2 = e, c * c
        if best is not None:
            out[tkr] = best
    return pd.Series(out, dtype=object)


def window_return(daily_r: pd.Series) -> tuple[float, bool]:
    """Compound daily returns over the label window; returns (return, ended_early)."""
    r = daily_r.to_numpy()
    fin = np.isfinite(r)
    if not fin.any():
        return float("nan"), True
    last = np.where(fin)[0].max()
    ended = last < len(r) - 1
    return float(np.prod(1 + np.nan_to_num(r[fin])) - 1), bool(ended)


def run_j4(prices: pd.DataFrame, etf_px: pd.DataFrame, spy_px: pd.Series, pit: pd.DataFrame, formations,
           sessions: pd.DatetimeIndex, eligible_etf: pd.DataFrame, labels_gics: pd.Series | None = None,
           cost_bp: float = 10.0, legs=("sp500",), assignment: str = "statistical") -> dict:
    """Return per-formation records and monthly series for J4-A / J4-B under the three bias treatments."""
    raw = prices.pct_change(fill_method=None)
    big = raw.abs() > 0.60
    clip_log = {"n_abs_gt_60pct": int(big.sum().sum()), "n_clipped_50pct": int((raw.abs() > 0.5).sum().sum()),
                "examples": [(c, str(i.date())) for i, c in raw[big].stack().index[:50]]}
    sr = raw.clip(-0.5, 0.5)
    er = etf_px.pct_change(fill_method=None)
    r63 = etf_px / etf_px.shift(63) - 1
    rs63 = (1 + r63).div(1 + (spy_px / spy_px.shift(63) - 1), axis=0) - 1
    pos = {d: i for i, d in enumerate(sessions)}
    recs, prev_w = [], {"L": {}, "A": {}}
    formations = [f for f in formations if f in pos]
    for k, t in enumerate(formations):
        i = pos[t]
        if i + 1 >= len(sessions):
            break
        e0 = sessions[i + 1]
        if k + 1 < len(formations):
            i1 = pos[formations[k + 1]] + 1
            if i1 >= len(sessions):
                break
        else:
            break
        e1 = sessions[i1]
        mem = members_at(pit, t, legs)
        elig = [e for e in etf_px.columns if bool(eligible_etf.at[t, e])]
        lo = max(0, i - 251)
        win = slice(sessions[lo], t)
        priced = [m for m in mem if m in prices.columns and np.isfinite(prices.at[t, m])
                  and sr.loc[win, m].notna().sum() >= 200]
        unpriced = [m for m in mem if m not in priced]
        if assignment == "statistical":
            sect = assign_sectors(sr.loc[win, priced], er.loc[win, elig])
        else:
            lab = labels_gics.reindex(priced).map(GICS_TO_ETF)
            sect = lab[lab.isin(elig)]
        rs = rs63.loc[t, elig].dropna()
        order = sorted(rs.items(), key=lambda kv: (-kv[1], kv[0]))
        lead = [e for e, _ in order[:3]]
        lag = [e for e, _ in order[-3:]]
        p0, p126, p21 = prices.iloc[i], prices.iloc[max(0, i - 126)], prices.iloc[max(0, i - 21)]
        e126, e21 = etf_px.iloc[max(0, i - 126)], etf_px.iloc[max(0, i - 21)]
        # positions are executed at the e0 close; the label earns returns dated after e0 up to the e1 close
        lab_win = sr.loc[(sr.index > e0) & (sr.index <= e1)]
        etf_win = er.loc[(er.index > e0) & (er.index <= e1)]
        per_sector, books = {}, {"L": {}, "A": {}}
        skipped = 0
        for e in elig:
            names = [m for m in sect.index if sect[m] == e]
            sig = {}
            for m in names:
                a, b = p21[m], p126[m]
                if np.isfinite(a) and np.isfinite(b) and b > 0:
                    sig[m] = (a / b) / (e21[e] / e126[e]) - 1
            if len(sig) < 3:
                skipped += 1      # fewer than 3 assigned names with a finite signal (counts both reasons)
                continue
            nsel = min(len(sig), max(3, math.ceil(0.2 * len(sig))))
            sel = [m for m, _ in sorted(sig.items(), key=lambda kv: (-kv[1], kv[0]))[:nsel]]
            etf_ret = float(np.prod(1 + etf_win[e].fillna(0)) - 1)
            rets_i, rets_iii = [], []
            for m in sel:
                rr, ended = window_return(lab_win[m])
                rr = 0.0 if not np.isfinite(rr) else rr
                rets_i.append(rr)
                if ended:
                    last = lab_win[m].dropna().index.max() if lab_win[m].notna().any() else t
                    rets_iii.append((1 + rr) * 0.7 - 1 if still_member(pit, m, last, legs) else rr)
                else:
                    rets_iii.append(rr)
            ew_i, ew_iii = float(np.mean(rets_i)), float(np.mean(rets_iii))
            per_sector[e] = {"n_assigned": len(names), "n_signal": len(sig), "n_selected": nsel,
                             "spread_i": (1 + ew_i) / (1 + etf_ret) - 1, "spread_iii": (1 + ew_iii) / (1 + etf_ret) - 1,
                             "ew_i": ew_i, "etf": etf_ret, "selected": sel, "rets_i": dict(zip(sel, rets_i))}
        def mean_spread(group, key):
            v = [per_sector[e][key] for e in group if e in per_sector]
            return float(np.mean(v)) if v else float("nan")
        # books: L = EW names in leading sectors; A = equal weight across sectors, EW within
        wl, wa = {}, {}
        lead_names = [m for e in lead if e in per_sector for m in per_sector[e]["selected"]]
        for m in lead_names:
            wl[m] = wl.get(m, 0) + 1 / len(lead_names)
        secs = list(per_sector)
        for e in secs:
            for m in per_sector[e]["selected"]:
                wa[m] = wa.get(m, 0) + 1 / len(secs) / len(per_sector[e]["selected"])
        allr = {m: v for e in per_sector for m, v in per_sector[e]["rets_i"].items()}

        def book(w, key):
            if not w:
                return float("nan"), 0.0
            gross = float(sum(w[m] * allr[m] for m in w))
            old = prev_w[key]
            turn = sum(abs(w.get(m, 0) - old.get(m, 0)) for m in set(w) | set(old))
            tot = 1 + gross
            prev_w[key] = {m: w[m] * (1 + allr[m]) / tot for m in w} if tot > 0 else {}
            return gross - turn * cost_bp / 1e4, turn

        rl, tl = book(wl, "L")
        ra, ta = book(wa, "A")
        n_lab = 0
        un_lead = un_lag = lab_lead = lab_lag = 0
        if labels_gics is not None:
            g = labels_gics.reindex(mem).map(GICS_TO_ETF)
            for m in mem:
                e = g.get(m)
                if e in lead:
                    lab_lead += 1; un_lead += m in unpriced
                elif e in lag:
                    lab_lag += 1; un_lag += m in unpriced
        recs.append({
            "formation": t, "exec": e0, "label_end": e1, "members": len(mem), "priced": len(priced),
            "priced_share": len(priced) / len(mem) if mem else float("nan"),
            "assigned": int(len(sect)), "sectors_skipped_lt3": skipped, "leading": lead, "lagging": lag,
            "S_lead_i": mean_spread(lead, "spread_i"), "S_lag_i": mean_spread(lag, "spread_i"),
            "S_lead_iii": mean_spread(lead, "spread_iii"), "S_lag_iii": mean_spread(lag, "spread_iii"),
            "book_L_net": rl, "book_A_net": ra, "turnover_L": tl, "turnover_A": ta,
            "unpriced_share_labelled_leading": un_lead / lab_lead if lab_lead else None,
            "unpriced_share_labelled_lagging": un_lag / lab_lag if lab_lag else None,
        })
    df = pd.DataFrame(recs).set_index("formation")
    df["delta_i"] = df["S_lead_i"] - df["S_lag_i"]
    df["delta_iii"] = df["S_lead_iii"] - df["S_lag_iii"]
    df["book_excess"] = df["book_L_net"] - df["book_A_net"]
    return {"records": df, "clip_log": clip_log}
