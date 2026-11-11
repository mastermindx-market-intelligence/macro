"""Rotation Core v2 — two-key defensive-rotation evaluation on Ken French 49 industries (corrected v1 engine).

Implements protocol_header_v2 (draft rev 3; the frozen JSON governs once it exists). Pure functions; research only.
Nothing here sizes, gates, ranks, alerts or trades.

Seal: any input path under `sealed_post2019/` is refused unless research/rotation_core/HOLDOUT_RELEASE_v2.json is
committed and clean; every loader also truncates at the caller's `end` before computing anything.
"""
from __future__ import annotations

import math
import subprocess
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from engine import rotation_core_evaluation as rc

ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / "research/rotation_core/HOLDOUT_RELEASE_v2.json"
SEALED_MARK = "sealed_post2019"
GRID = [(3, 25.0), (3, 37.5), (5, 25.0), (5, 37.5)]      # (h near-high %, b breadth-drop pp)
FEE_INDUSTRY_BP = 10.0
FEE_FUND_BP = 5.0


class SealedRefusal(PermissionError):
    pass


def _committed_clean(path: Path) -> bool:
    rel = str(path.relative_to(ROOT))
    try:
        subprocess.run(["git", "-C", str(ROOT), "ls-files", "--error-unmatch", rel], check=True, capture_output=True)
    except subprocess.CalledProcessError:
        return False
    out = subprocess.run(["git", "-C", str(ROOT), "status", "--porcelain", "--", rel], capture_output=True).stdout
    return out.strip() == b""


def seal_guard(path, release: Path = RELEASE) -> None:
    """Refuse any sealed path unless the parent-written release file is committed and clean."""
    if SEALED_MARK in str(path) and not (release.exists() and _committed_clean(release)):
        raise SealedRefusal(f"refused: {path} is under the hold-out seal and {release.name} is not committed")


def assert_window(end, release: Path = RELEASE) -> None:
    if pd.Timestamp(end) > rc.D_END and not (release.exists() and _committed_clean(release)):
        raise SealedRefusal(f"refused: window end {end} is after 2019-12-31 and {release.name} is not committed")


# --------------------------------------------------------------------------- loaders
def load_french_industries(path, end) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(value-weighted, equal-weighted) daily returns as fractions, NaN where missing (-99.99 / -999), dates <= end.
    Lines dated after `end` are skipped by their date field before any value is parsed."""
    seal_guard(path); assert_window(end)
    endk = pd.Timestamp(end).strftime("%Y%m%d")
    secs, cur = {}, None
    for ln in open(path):
        if "Weighted Returns -- Daily" in ln:
            cur = "vw" if "Value" in ln else "ew"; secs[cur] = {"cols": None, "rows": []}; continue
        if cur is None:
            continue
        if secs[cur]["cols"] is None and ln.startswith(","):
            secs[cur]["cols"] = [c.strip() for c in ln.split(",")[1:]]; continue
        k = ln.split(",", 1)[0].strip()
        if len(k) == 8 and k.isdigit():
            if k > endk:
                continue
            secs[cur]["rows"].append(ln.rstrip("\n").split(","))
    out = []
    for key in ("vw", "ew"):
        r = secs[key]["rows"]
        df = pd.DataFrame([x[1:] for x in r], index=pd.to_datetime([x[0].strip() for x in r], format="%Y%m%d"),
                          columns=secs[key]["cols"]).astype(float)
        out.append(df.where(df > -99.0) / 100.0)
    return out[0], out[1]


def load_french_market(path, end) -> tuple[pd.Series, pd.Series]:
    seal_guard(path); assert_window(end)
    endk = pd.Timestamp(end).strftime("%Y%m%d")
    rows = []
    for ln in open(path):
        p = [x.strip() for x in ln.split(",")]
        if len(p[0]) == 8 and p[0].isdigit() and p[0] <= endk:
            rows.append(p)
    idx = pd.to_datetime([r[0] for r in rows], format="%Y%m%d")
    mkt = pd.Series([float(r[1]) + float(r[4]) for r in rows], index=idx) / 100
    rf = pd.Series([float(r[4]) for r in rows], index=idx) / 100
    return mkt, rf


# --------------------------------------------------------------------------- legs, breadth
@dataclass
class Legs:
    formed: dict          # month-end -> (offence list, defence list, eligible list)
    returns: pd.DataFrame  # daily OFF, DEF, BASE leg returns (net of intra-leg re-formation cost at the leg level)
    valid: pd.DataFrame    # daily valid-member counts per leg
    dropped_industry_days: int


def form_legs(vw: pd.DataFrame, mkt: pd.Series, start=None, min_valid: int = 252, min_pairs: int = 200,
              fee_bp: float = FEE_INDUSTRY_BP) -> Legs:
    s = vw.index
    valid = vw.notna()
    nvalid = valid.cumsum()
    me = pd.DatetimeIndex(pd.Series(s, index=s).groupby([s.year, s.month]).max().values)
    if start is not None:
        me = me[me >= pd.Timestamp(start) - pd.offsets.MonthEnd(2)]
    formed = {}
    for t in me:
        i = s.get_loc(t)
        if i < 253:
            continue
        w = slice(s[i - 252], s[i - 1])                    # data to t-1
        y, x = vw.loc[w], mkt.reindex(s).loc[w]
        b = {}
        for c in vw.columns:
            ok = y[c].notna() & x.notna()
            if nvalid[c].iloc[i - 1] >= min_valid and ok.sum() >= min_pairs:
                b[c] = float(np.cov(y[c][ok], x[ok])[0, 1] / np.var(x[ok], ddof=1))
        if len(b) < 6:
            continue
        bs = pd.Series(b).sort_values(kind="mergesort")
        k = len(bs) // 3
        formed[t] = (list(bs.index[-k:]), list(bs.index[:k]), list(bs.index))
    keys = pd.DatetimeIndex(sorted(formed))
    R = pd.DataFrame(np.nan, index=s, columns=["OFF", "DEF", "BASE"])
    V = pd.DataFrame(0, index=s, columns=["OFF", "DEF", "BASE"])
    dropped = 0
    prev = None
    fee = fee_bp / 1e4
    for j, t in enumerate(keys):
        a = s.get_loc(t) + 1
        z = s.get_loc(keys[j + 1]) + 1 if j + 1 < len(keys) else len(s)
        days = s[a:z]
        legs = formed[t]
        for col, mem in zip(["OFF", "DEF", "BASE"], legs):
            blk = vw.loc[days, mem]
            ok = blk.notna()
            dropped += int((~ok).sum().sum())
            R.loc[days, col] = blk.mean(axis=1, skipna=True)     # missing industry-day dropped, not imputed
            V.loc[days, col] = ok.sum(axis=1)
            if prev is not None and len(days):
                old = set(prev[["OFF", "DEF", "BASE"].index(col)])
                repl = len(set(mem) - old) / max(1, len(mem))
                R.loc[days[0], col] = (1 + R.loc[days[0], col]) / (1 + 2 * repl * fee) - 1   # re-formation cost
        prev = legs
    return Legs(formed, R, V, dropped)


def breadth_i(vw: pd.DataFrame, legs: Legs, n: int = 50) -> pd.Series:
    """Share of the offence leg's industries above their own 50-session SMA (missing industry-days dropped)."""
    lvl = (1 + vw.fillna(0)).cumprod().where(vw.notna().cumsum() > 0)
    sma = lvl.rolling(n, min_periods=n).mean()
    above = (lvl > sma).astype(float).where(sma.notna() & vw.notna())
    out = pd.Series(np.nan, index=vw.index)
    keys = pd.DatetimeIndex(sorted(legs.formed))
    for j, t in enumerate(keys):
        a = vw.index.get_loc(t) + 1
        z = vw.index.get_loc(keys[j + 1]) + 1 if j + 1 < len(keys) else len(vw.index)
        days = vw.index[a:z]
        out.loc[days] = above.loc[days, legs.formed[t][0]].astype(float).mean(axis=1, skipna=True).to_numpy(dtype=float)
    return out


def relative_line(legs: Legs) -> pd.Series:
    r = legs.returns
    return (1 + r["OFF"].fillna(0)).cumprod() / (1 + r["DEF"].fillna(0)).cumprod()


# --------------------------------------------------------------------------- state machines
NEUTRAL, DEFEND, ATTACK = 0, 1, 2


def h1_states(rel: pd.Series, br: pd.Series, h: float, b: float, use_breadth: bool = True,
              wash_lo: float = 0.25, wash_days: int = 20, arm_memory: int = 21) -> pd.Series:
    """State decided at each close (header H1, precedence rules of draft rev 3)."""
    s = rel.index
    hi = rel.rolling(126, min_periods=126).max()
    sma = rel.rolling(50, min_periods=50).mean()
    bmax = br.rolling(126, min_periods=126).max()
    near = rel >= (1 - h / 100) * hi
    armed = near & ((br <= bmax - b / 100 + 1e-12) if use_breadth else True)
    armed_recent = armed.astype(float).rolling(arm_memory + 1, min_periods=1).max() > 0
    month_end = pd.Series(s, index=s).groupby([s.year, s.month]).transform("max") == s
    st = np.full(len(s), np.nan)
    state, hold_to_month = NEUTRAL, None
    wash_on, wash_day = False, None
    ready = (hi.notna() & sma.notna() & bmax.notna()).values
    for i, t in enumerate(s):
        if not ready[i]:
            continue
        defend = bool(armed_recent.iloc[i]) and rel.iloc[i] < sma.iloc[i] and rel.iloc[i - 1] >= sma.iloc[i - 1]
        attack = False
        bi = br.iloc[i]
        if np.isfinite(bi):
            if bi <= wash_lo:
                if not wash_on:
                    wash_on, wash_day = True, i
            elif wash_on:
                attack = (i - wash_day) <= wash_days
                wash_on = False
        if defend:                                          # DEFEND wins a same-day tie
            new = DEFEND
            wash_on = False
        elif attack:
            new = ATTACK
        else:
            new = None
        if new is not None:
            state = new
            ym = (t.year, t.month)
            hold_to_month = (ym if not month_end.iloc[i] else ((t + pd.offsets.MonthBegin(1)).year,
                                                                (t + pd.offsets.MonthBegin(1)).month))
        elif month_end.iloc[i] and state != NEUTRAL and hold_to_month == (t.year, t.month):
            state, hold_to_month = NEUTRAL, None
        st[i] = state
    return pd.Series(st, index=s)


def h3_states(legs: Legs) -> pd.Series:
    r = legs.returns
    lo = (1 + r["OFF"].fillna(0)).cumprod(); ld = (1 + r["DEF"].fillna(0)).cumprod()
    m126 = (lo / lo.shift(126)) - (ld / ld.shift(126))
    s = r.index
    me = pd.Series(s, index=s).groupby([s.year, s.month]).transform("max") == s
    st = pd.Series(np.nan, index=s)
    st[me & m126.notna()] = np.where(m126[me & m126.notna()] > 0, ATTACK, DEFEND)
    return st.ffill()


def targets_from_states(st: pd.Series, cash_for_defend: bool = False) -> pd.DataFrame:
    cols = ["OFF", "DEF", "BASE"]
    T = pd.DataFrame(np.nan, index=st.index, columns=cols)
    ok = st.notna()
    T.loc[ok] = 0.0
    T.loc[ok & (st == NEUTRAL), "BASE"] = 1.0
    T.loc[ok & (st == ATTACK), "OFF"] = 1.0
    if not cash_for_defend:
        T.loc[ok & (st == DEFEND), "DEF"] = 1.0
    return T


def simulate_states(st: pd.Series, legs: Legs, rf: pd.Series, start, end, cash_for_defend=False,
                    fee_bp=FEE_INDUSTRY_BP, name="v2") -> rc.Book:
    R = legs.returns.loc[start:end]
    avail = legs.valid.loc[start:end] > 0
    return rc.simulate(targets_from_states(st.loc[start:end], cash_for_defend), R, rf.reindex(R.index),
                       fee_bp, name, start=pd.Timestamp(start), end=pd.Timestamp(end), avail=avail,
                       equity_cols=("OFF", "DEF", "BASE"))


# --------------------------------------------------------------------------- matched-mix contrast
def matched_mix_stat(r, w, legs_r):
    """Annualised mean of r - (matched static mix), mix weights = this sample's own average weights.
    r: (B, n); w: (B, n, 3) start-of-day weights in OFF/DEF/BASE; legs_r: (B, n, 3); cash = 1 - sum(w) earns 0
    in the reference only if the strategy held cash (ablation), handled by the caller via the 4th column."""
    wbar = w.mean(axis=1, keepdims=True)
    ref = (wbar * legs_r).sum(axis=2)
    return (r - ref).mean(axis=1) * rc.TRADING_DAYS


def matched_contrast(book: rc.Book, legs_r: pd.DataFrame, cash: pd.Series, mask, B=10_000, block=21, seed=20261111):
    idx = book.returns.index[mask.reindex(book.returns.index).fillna(False).values]
    r = book.returns.loc[idx].values
    W = book.holdings.loc[idx, ["OFF", "DEF", "BASE"]].values
    W = np.concatenate([W, 1 - W.sum(axis=1, keepdims=True)], axis=1)       # cash column
    L = np.concatenate([legs_r.loc[idx, ["OFF", "DEF", "BASE"]].fillna(0).values,
                        cash.reindex(idx).fillna(0).values[:, None]], axis=1)
    obs = float(matched_mix_stat(r[None], W[None], L[None])[0])
    out = []
    for c in range(0, B, 1000):
        ii = rc.stationary_bootstrap_indices(len(r), min(1000, B - c), block, seed + c)
        out.append(matched_mix_stat(r[ii], W[ii], L[ii]))
    dist = np.concatenate(out)
    return {"observed": obs, "ci95": rc.ci95(dist), "p_one_sided_centred": rc.centred_p(dist, obs),
            "se": float(np.nanstd(dist, ddof=1)), "finite_draws": rc.finite_draws(dist), "n": int(len(r))}
