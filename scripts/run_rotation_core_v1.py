"""Run the Rotation Core historical evaluation bound to research/rotation_core/protocol_header_v1.json.

  python scripts/run_rotation_core_v1.py --stage D [--smoke]   # development window only (H sealed)
  python scripts/run_rotation_core_v1.py --stage H             # refuses unless HOLDOUT_RELEASE_v1.json is committed

Stage D truncates every price/macro input at 2019-12-31 (J4: formations <= 2015-12) BEFORE any computation, so no
statistic of a hold-out return can be produced. --smoke runs the full pipeline but prints only structural diagnostics
(no returns, no statistics) and writes nothing. Research-only and paper-only; outputs carry may_* = false.
"""
from __future__ import annotations

import argparse
import io
import json
import math
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from engine import rotation_core_evaluation as rc  # noqa: E402

HEADER = ROOT / "research/rotation_core/protocol_header_v1.json"
STAGE_D_JSON = ROOT / "research/rotation_core/results_stage_D.json"
STAGE_D_MD = ROOT / "research/rotation_core/RESULTS_STAGE_D.md"
RELEASE = ROOT / "research/rotation_core/HOLDOUT_RELEASE_v1.json"
PIN = "4d49b23a8f0246718fd48a24b4124c35129a1cfe"
YAHOO = Path("/home/ubuntu2/tmp/rotation-core/data/yahoo")
FRENCH = Path("/home/ubuntu2/tmp/rotation-core/data/french/x")
INCUMBENTS = Path("/home/ubuntu2/tmp/rotation-core/incumbents")
B = 10_000
SEED = 20261110
ETF_BP = 5.0
J1_FIRST = pd.Timestamp("1998-01-02")
J2_FIRST = pd.Timestamp("1999-12-31")
J3_FIRST = pd.Timestamp("2007-02-28")
DPEAK = {  # header named episodes inside D
    "E1998": ("1998-07-01", "1998-07-31", "1998-10-31"),
    "E2000_02": ("2000-01-01", "2000-12-31", "2002-12-31"),
    "E2008_09": ("2007-07-01", "2007-12-31", "2009-06-30"),
    "E2011": ("2011-04-01", "2011-07-31", "2011-12-31"),
    "E2015_16": ("2015-05-01", "2015-08-15", "2016-03-31"),
    "E2018Q4": ("2018-09-01", "2018-10-15", "2018-12-31"),
}
SEALED_EPISODES = ["E2020", "E2022", "E2025", "E2026"]
LPEAK = {  # PHASE2_ADDITIONS_v1 section 4
    "L1929_32": ("1929-08-01", "1929-10-15", "1932-12-31"),
    "L1937": ("1937-02-01", "1937-08-31", "1938-06-30"),
    "L1962": ("1961-11-15", "1962-01-31", "1962-07-31"),
    "L1966": ("1966-01-15", "1966-02-28", "1966-12-31"),
    "L1969_70": ("1968-11-15", "1968-12-31", "1970-07-31"),
    "L1973_74": ("1972-12-15", "1973-01-31", "1974-12-31"),
    "L1980_82": ("1980-11-01", "1980-12-31", "1982-09-30"),
    "L1987": ("1987-08-01", "1987-09-30", "1987-12-31"),
    "L1990": ("1990-06-15", "1990-07-31", "1990-11-30"),
}
INPUT_HASHES: dict[str, str] = {}

DEVIATIONS = [
    {"kind": "pre_outcome_access_restriction", "ref": "research/rotation_core/HOLDOUT_ACCESS_RULING_v1.md",
     "text": "H sealed until a parent-written HOLDOUT_RELEASE_v1.json is committed; Stage D truncates every input at "
             "2019-12-31 (J4 formations <= 2015-12). Narrows access only; header unchanged."},
    {"kind": "pre_outcome_addition", "ref": "PHASE2_ADDITIONS_v1.md s1",
     "text": "Pivot tables and J2 episode holdings cover D episodes only; G4 and the H half of G6 not evaluated; "
             "all G6 rows D-only and provisional."},
    {"kind": "pre_outcome_addition", "ref": "PHASE2_ADDITIONS_v1.md s2", "text": "Power lines (SE, MDE80 at Holm alpha/m)."},
    {"kind": "pre_outcome_addition", "ref": "PHASE2_ADDITIONS_v1.md s3",
     "text": "DSR trial count = sum of ledger effective_n over rotation_core_v1, thematic_rotation_phase0, "
             "cross_asset_phase0, index_direction_phase0 (124), ledger blob pinned at 623f0a4623."},
    {"kind": "pre_outcome_addition", "ref": "PHASE2_ADDITIONS_v1.md s4",
     "text": "Long-history J1 tier remainder (French market 1928-1997; Sahm rule from 1960; DBAA-DGS10 credit from 1987)."},
    {"kind": "deferred", "ref": "header windows.long_history_descriptive_tiers",
     "text": "J2_L (French 12 industries), J3_L (proxy tier) and J2_industry_etf (16 industry ETFs) are not computed "
             "in this Stage D run; descriptive tiers only, deferred to after the parent's Stage D adjudication."},
    {"kind": "pre_outcome_addition", "ref": "PHASE2_ADDITIONS_v1.md s5-s8",
     "text": "Pivot presentation; J2 episode holdings; J4 implementation details; interior missing-close forward fill."},
    {"kind": "implementation", "ref": "PRE_RUN_REVIEW findings 1,2,4-8,10-19 (Opus reviewer, separate context)",
     "text": "Fixed before any outcome: X rebuilt per era; pivot start-up spell and spells starting in D's last 63 "
             "sessions excluded from false pivots (counted as undetermined_sealed); deviations recorded; block-63 and "
             "block-6 sensitivities; incumbent Holm at m=8 with unavailable tests at p=1; J4 starts_late-only flags no "
             "longer mask vendor prices; J4 S&P 1500 sensitivity from 2013; J4 eras by label date; J4 statistics over "
             "formations with a finite delta; exit-before-trough strict and 3 H episodes; clip logging; one-way "
             "turnover, TE and IR per contrast; ledger pinned; dirty-harness refusal; G6 rows labelled provisional."},
    {"kind": "convention", "text": "J5-B and B2 bond leg = VFITX before 2002-08-01 then IEF (header B2 rule applied "
             "consistently); GLD eligible for J5-B's defensive leg from its 253rd session (2005-11)."},
    {"kind": "convention", "text": "Bootstrap seeds: base 20261110 with family offsets (+1000 J2, +2000 J3, +3000 FI, "
             "+4000 J4, +500000 block sensitivity); chunks use seed+k, so adjacent tests share random streams (common "
             "random numbers, no bias)."},
]


# --------------------------------------------------------------------------- #
# guards
# --------------------------------------------------------------------------- #
def _git(*a) -> str:
    return subprocess.check_output(["git", "-C", str(ROOT), *a]).decode()


def committed_clean(path: Path) -> bool:
    rel = str(path.relative_to(ROOT))
    try:
        _git("ls-files", "--error-unmatch", rel)
    except subprocess.CalledProcessError:
        return False
    return _git("status", "--porcelain", "--", rel).strip() == ""


def stage_guard(stage: str) -> None:
    if stage == "D":
        return
    if not committed_clean(STAGE_D_JSON):
        raise SystemExit("Stage H refused: results_stage_D.json is not committed and clean")
    if not committed_clean(RELEASE):
        raise SystemExit("Stage H refused: HOLDOUT_RELEASE_v1.json (parent-written) is not committed and clean")
    raise SystemExit("Stage H refused: not implemented until the parent's release names configurations "
                     "(HOLDOUT_ACCESS_RULING_v1.md); it will compute only the released configurations.")


# --------------------------------------------------------------------------- #
# data (every series truncated at `end` immediately on load)
# --------------------------------------------------------------------------- #
def _hash_bytes(key: str, b: bytes) -> None:
    INPUT_HASHES[key] = rc.sha256_bytes(b)


def yahoo(t: str, end, col: str = "Adj Close") -> pd.Series:
    p = YAHOO / f"{t.replace('^', 'IDX_').replace('=', '_')}.parquet"
    _hash_bytes(str(p), p.read_bytes())
    d = pd.read_parquet(p)
    s = d[col].astype(float)
    s.index = pd.DatetimeIndex(pd.to_datetime(d.index)).normalize()
    s = s[~s.index.duplicated()].sort_index().dropna()
    return s[s.index <= end]


def repo_fred(name: str, end) -> pd.Series:
    """FRED series from the repo store at the pin, in memory only (no copy written)."""
    raw = subprocess.check_output(["git", "-C", str(ROOT), "show", f"{PIN}:data/fred/{name}.parquet"])
    _hash_bytes(f"{PIN}:data/fred/{name}.parquet", raw)
    d = pd.read_parquet(io.BytesIO(raw))
    s = d.iloc[:, 0].astype(float)
    s.index = pd.to_datetime(d.index).normalize()
    s = s.sort_index().dropna()
    return s[s.index <= end]


def french_factors(end) -> pd.DataFrame:
    p = FRENCH / "F-F_Research_Data_Factors_daily.csv"
    _hash_bytes(str(p), p.read_bytes())
    rows, cols = [], None
    for ln in p.read_text().splitlines():
        parts = [x.strip() for x in ln.split(",")]
        if len(parts) > 1 and parts[1] == "Mkt-RF":
            cols = parts[1:]
            continue
        if cols and parts[0].isdigit() and len(parts[0]) == 8:
            rows.append(parts)
    df = pd.DataFrame([r[1:] for r in rows], index=pd.to_datetime([r[0] for r in rows], format="%Y%m%d"),
                      columns=cols).astype(float) / 100.0
    return df[df.index <= end]


def load(end) -> dict:
    spy = yahoo("SPY", end)
    sessions = spy.index
    gspc_full = yahoo("^GSPC", end, "Close")
    names = sorted(set(rc.SECTORS + rc.SLEEVES + ["VFITX"]))
    px = {t: yahoo(t, end) for t in names}
    adj = pd.DataFrame({t: s.reindex(sessions) for t, s in px.items()})
    gaps = {}
    for t in adj.columns:
        life = adj.index >= px[t].index.min()
        gaps[t] = int(adj.loc[life, t].isna().sum())
        adj.loc[life, t] = adj.loc[life, t].ffill()
    rets = adj.pct_change(fill_method=None)
    bond = pd.concat([px["VFITX"].pct_change()[lambda s: s.index < "2002-08-01"],
                      px["IEF"].pct_change()[lambda s: s.index >= "2002-08-01"]]).sort_index()
    rets["BOND"] = bond.reindex(sessions)
    adj["BOND"] = (1 + rets["BOND"].fillna(0)).cumprod().where(rets["BOND"].notna().cumsum() > 0)
    cash = rc.cash_returns(repo_fred("DTB3", end), sessions, fallback=yahoo("^IRX", end, "Close"))
    return {
        "sessions": sessions, "spy": spy, "gspc_full": gspc_full, "adj": adj, "rets": rets, "cash": cash,
        "hy": repo_fred("BAMLH0A0HYM2", end), "sahm": repo_fred("SAHMREALTIME", end),
        "dbaa": repo_fred("DBAA", end), "dgs10": repo_fred("DGS10", end),
        "dq": {"interior_ffill_sessions": gaps,
               "l0_priced_share_within_life": {t: float(1 - gaps[t] / max(1, int((adj.index >= px[t].index.min()).sum())))
                                               for t in gaps},
               "l0_ge_99pct": all(1 - gaps[t] / max(1, int((adj.index >= px[t].index.min()).sum())) >= 0.99 for t in gaps),
               "abs_daily_return_gt_25pct": {t: int((rets[t].abs() > 0.25).sum()) for t in rets.columns}},
    }


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def topk(scores: pd.Series, k: int) -> list[str]:
    s = scores.dropna()
    return [t for t, _ in sorted(s.items(), key=lambda kv: (-kv[1], kv[0]))[:k]]


def monthly_targets(sessions, decisions, cols, fn) -> pd.DataFrame:
    T = pd.DataFrame(np.nan, index=sessions, columns=cols)
    for d in decisions:
        w = fn(d)
        if w is None:
            continue
        row = np.zeros(len(cols))
        for a, v in w.items():
            row[cols.index(a)] += v
        T.loc[d] = row
    return T


def spy_targets(w: pd.Series, off_asset: str | None = None) -> pd.DataFrame:
    cols = ["SPY", "BOND"]
    T = pd.DataFrame(np.nan, index=w.index, columns=cols)
    ok = w.notna()
    T.loc[ok, "SPY"] = w[ok]
    T.loc[ok, "BOND"] = (1.0 - w[ok]) if off_asset == "BOND" else 0.0
    return T


def nanand(a, b):
    return (a * b).where(a.notna() & b.notna())


def nanor(a, b):
    return ((a + b) > 0).astype(float).where(a.notna() & b.notna())


def _al(mask, idx):
    return mask.reindex(idx).fillna(False).astype(bool)


def W(x, mask):
    """x restricted to the window mask (aligned on x's own index)."""
    return x[_al(mask, x.index)]


class XRef:
    """Exposure-matched reference rebuilt on each window tested (header baselines.X: mean(w_c) per window)."""

    def __init__(self, book, risky_r, cash):
        self.book, self.risky_r, self.cash = book, risky_r, cash

    def on(self, mask):
        return xref(self.book, self.risky_r, self.cash, mask)


def _stat(kind, a, b, c, seed, block):
    if kind == "mean":
        return rc.bootstrap_stat([a, b], rc.stat_mean_diff, B, block, seed)
    return rc.bootstrap_stat([a, b, c], rc.stat_sharpe_diff, B, block, seed)


def contrast(label, r_c, r_ref, cash, kind, mask, m, effect, unit, seed):
    """r_ref: a return Series, or an XRef rebuilt on each window (full D, E1, E2)."""
    mask = _al(mask, r_c.index)
    cash = cash.reindex(r_c.index)

    def ref_on(mk):
        if isinstance(r_ref, XRef):
            x, wbar = r_ref.on(mk)
            return x.reindex(r_c.index), wbar
        return r_ref.reindex(r_c.index), None

    ref, wbar = ref_on(mask)
    a, b, c = r_c[mask].values, ref[mask].values, cash[mask].values
    assert np.isfinite(a).all() and np.isfinite(b).all(), f"{label}: non-finite returns in window"
    obs = float((a - b).mean() * rc.TRADING_DAYS) if kind == "mean" else rc.sharpe(a, c) - rc.sharpe(b, c)
    dist = _stat(kind, a, b, c, seed, 21)
    dist63 = _stat(kind, a, b, c, seed + 500000, 63)
    se = float(np.nanstd(dist, ddof=1))
    d = a - b
    te = float(d.std(ddof=1) * math.sqrt(rc.TRADING_DAYS))
    eras, era_w = {}, {}
    for era, em in (("E1", mask & (r_c.index <= rc.ERA_SPLIT)), ("E2", mask & (r_c.index > rc.ERA_SPLIT))):
        if em.sum() < 50:
            eras[era] = None
            continue
        rr, ww = ref_on(em)
        era_w[era] = ww
        aa, bb, cc = r_c[em].values, rr[em].values, cash[em].values
        eras[era] = float((aa - bb).mean() * rc.TRADING_DAYS) if kind == "mean" else rc.sharpe(aa, cc) - rc.sharpe(bb, cc)
    return {"contrast": label, "kind": kind, "observed": obs, "ci95": rc.ci95(dist),
            "p_one_sided_centred": rc.centred_p(dist, obs), "eras": eras,
            "x_mean_weight": wbar, "x_mean_weight_eras": era_w or None,
            "tracking_error": te, "information_ratio": (float(d.mean() * rc.TRADING_DAYS) / te) if te > 0 else None,
            "block63": {"ci95": rc.ci95(dist63), "p_one_sided_centred": rc.centred_p(dist63, obs)},
            "power": rc.power_line(se, m, effect, unit)}


def xref(book, risky_r, cash, mask):
    wbar = float(book.risky_weight[_al(mask, book.risky_weight.index)].mean())
    return wbar * risky_r + (1 - wbar) * cash, wbar


def family(spec, cash, mask, m, seed0):
    """spec: list of (test_id, r_c, r_ref, kind, effect, unit)."""
    res, pv = {}, {}
    for i, (tid, r_c, r_ref, kind, effect, unit) in enumerate(spec):
        res[tid] = contrast(tid, r_c, r_ref, cash, kind, mask, m, effect, unit, seed0 + i)
        pv[tid] = res[tid]["p_one_sided_centred"]
    h = rc.holm(pv)
    h63 = rc.holm({k: r["block63"]["p_one_sided_centred"] for k, r in res.items()})
    for tid in res:
        res[tid]["holm"] = h[tid]
        res[tid]["block63"]["holm"] = h63[tid]
    return res


def ir(r, ref, mask):
    d = (r - ref.reindex(r.index))[_al(mask, r.index)]
    sd = d.std(ddof=1)
    return float(d.mean() / sd * math.sqrt(252)) if sd > 0 else None


SEALED_TAIL = 63   # spells starting in D's last 63 sessions may belong to the sealed E2020 window


def first_exec(b: rc.Book):
    t = b.traded[b.traded > 0]
    return t.index[0] if len(t) else None


def after_close_weight(b: rc.Book) -> pd.Series:
    """Equity weight in force after each close (the held weight of the next session)."""
    w = b.equity_weight.shift(-1)
    return w.fillna(b.equity_weight.iloc[-1])


# --------------------------------------------------------------------------- #
# J1
# --------------------------------------------------------------------------- #
def j1_weights(d):
    s = d["sessions"]
    T = rc.trend_broken(d["gspc_full"]).reindex(s)
    MTF = rc.mtf(d["gspc_full"]).reindex(s)
    C = rc.credit_flag(d["hy"], s)
    M = rc.sahm_available(d["sahm"], s)
    w = {"J1-A": 1 - C, "J1-B": 1 - nanand(T, C), "J1-C": 1 - nanor(T, C), "J1-D": MTF,
         "J1-E": 1 - nanand(T, M), "B3": 1 - T}
    return {k: v.where(s >= J1_FIRST) for k, v in w.items()}, {"T": T, "C": C, "M": M, "MTF": MTF}


def j1_books(d, w, mult=1.0, only=None):
    s, R, cash = d["sessions"], d["rets"][["SPY", "BOND"]], d["cash"]
    bp = ETF_BP * mult
    bk = {}
    for k, wk in w.items():
        if only and k not in only:
            continue
        bk[k] = rc.simulate(spy_targets(wk), R, cash, bp, k, start=J1_FIRST)
        if k.startswith("J1-") and not only:
            bk[k + "-IEF"] = rc.simulate(spy_targets(wk, "BOND"), R, cash, bp, k + "-IEF", start=J1_FIRST)
    if only:
        return bk
    one = pd.Series(1.0, index=s).where(s >= J1_FIRST)
    bk["B1"] = rc.simulate(spy_targets(one), R, cash, bp, "B1", start=J1_FIRST)
    me = rc.month_end_sessions(s)
    t6040 = pd.DataFrame(np.nan, index=s, columns=["SPY", "BOND"])
    t6040.loc[me[me >= J1_FIRST].union(pd.DatetimeIndex([J1_FIRST]))] = [0.6, 0.4]   # invested from the first decision
    bk["B2"] = rc.simulate(t6040, R, cash, bp, "B2", start=J1_FIRST, always_rebalance=True)
    sig = d["rets"]["SPY"].rolling(21, min_periods=21).std(ddof=1) * math.sqrt(252)
    wv = (0.15 / sig).clip(upper=1.0).where(s >= J1_FIRST)
    bk["B4"] = rc.simulate(spy_targets(wv), R, cash, bp, "B4", start=J1_FIRST, threshold=0.10)
    return bk


def incumbent_provenance(fname):
    """Require a reviewed provenance sidecar (timing semantics, pin, causality evidence) before using a replay."""
    pv = INCUMBENTS / fname.replace(".parquet", "_provenance.json")
    if not pv.exists():
        return None
    meta = json.loads(pv.read_text())
    _hash_bytes(str(pv), pv.read_bytes())
    return meta


def load_incumbent_weight(fname, col, sessions, end):
    p = INCUMBENTS / fname
    if not p.exists() or incumbent_provenance(fname) is None:
        return None, None
    _hash_bytes(str(p), p.read_bytes())
    s = pd.read_parquet(p)[col].astype(float)
    s.index = pd.to_datetime(s.index).normalize()
    s = s[s.index <= end]
    return s.reindex(sessions), str(p)


# --------------------------------------------------------------------------- #
# J2
# --------------------------------------------------------------------------- #
def j2_signals(d):
    adj = d["adj"]
    S = rc.SECTORS
    el = rc.eligible(adj[S])
    r63 = adj / adj.shift(63) - 1
    rs63 = (1 + r63[S]).div(1 + r63["SPY"], axis=0) - 1
    vel = rs63 - rs63.shift(21)
    r12_1 = adj[S].shift(21) / adj[S].shift(252) - 1
    r126 = adj[S] / adj[S].shift(126) - 1
    mtf_s = rc.mtf(adj[S])
    return {"el": el, "rs63": rs63, "vel": vel, "r12_1": r12_1, "r126": r126, "mtf": mtf_s}


def j2_rules(sig):
    el = sig["el"]

    def elig(dd):
        return [t for t in rc.SECTORS if bool(el.at[dd, t])]

    def topn(score, k=3):
        def f(dd):
            e = elig(dd)
            pick = topk(score.loc[dd, e], k)
            return {t: 1 / len(pick) for t in pick} if pick else None
        return f

    def ew(dd):
        e = elig(dd)
        return {t: 1 / len(e) for t in e}

    def j2c(dd):
        e = [t for t in elig(dd) if sig["rs63"].at[dd, t] > 0 and sig["vel"].at[dd, t] > 0]
        pick = topk(sig["rs63"].loc[dd, e], 3)
        w = {t: 1 / 3 for t in pick}
        w["SPY"] = 1 - len(pick) / 3
        return w

    def j2d(dd):
        e = [t for t in elig(dd) if sig["mtf"].at[dd, t] == 1]
        pick = topk(sig["rs63"].loc[dd, e], 3)
        w = {t: 1 / 3 for t in pick}
        w["SPY"] = 1 - len(pick) / 3
        return w

    return {"B5": ew, "B6": topn(sig["r12_1"]), "B7": topn(sig["r126"]), "J2-A": topn(sig["rs63"]),
            "J2-B": topn(sig["vel"]), "J2-C": j2c, "J2-D": j2d, "B1": lambda dd: {"SPY": 1.0}}


def j2_books(d, rules, mult=1.0, only=None, extra=None):
    s = d["sessions"]
    cols = rc.SECTORS + ["SPY"]
    dec = rc.month_end_sessions(s)
    dec = dec[dec >= J2_FIRST]
    bk, targets = {}, {}
    for k, f in rules.items():
        if only and k not in only:
            continue
        T = monthly_targets(s, dec, cols, f)
        targets[k] = T
        bk[k] = rc.simulate(T, d["rets"][cols], d["cash"], ETF_BP * mult, k, start=J2_FIRST,
                            equity_cols=cols, always_rebalance=True)
    return bk, targets


# --------------------------------------------------------------------------- #
# J3
# --------------------------------------------------------------------------- #
def j3_rules(d, j1flags):
    adj, cash = d["adj"], d["cash"]
    S = rc.SLEEVES
    el = rc.eligible(adj[S])
    r12_1 = adj[S].shift(21) / adj[S].shift(252) - 1
    rf12_1 = rc.cum_cash(cash, 252, 21)
    r126 = adj / adj.shift(126) - 1
    rf126 = rc.cum_cash(cash, 126, 0)
    r12 = adj / adj.shift(252) - 1
    rf12 = rc.cum_cash(cash, 252, 0)
    mtf_s = rc.mtf(adj[S])
    mclose = adj[S].loc[rc.month_end_sessions(d["sessions"])]
    msma10 = mclose.rolling(10, min_periods=10).mean()
    jb = nanand(j1flags["T"], j1flags["C"])   # J1-B risk-off flag

    def tsm(dd, t):
        sg = []
        for L in (63, 126, 252):
            i = adj.index.get_loc(dd)
            if i - 5 - L < 0:
                return np.nan
            a, b = adj[t].iloc[i - 5], adj[t].iloc[i - 5 - L]
            if np.isnan(a) or np.isnan(b):
                return np.nan
            sg.append(np.sign(a / b - 1))
        return float(np.mean(sg))

    def all_el(dd):
        return all(bool(el.at[dd, t]) for t in S)

    def B8(dd):
        return {t: 1 / 7 for t in S} if all_el(dd) else None

    def B9(dd):
        if not all_el(dd) or msma10.loc[dd].isna().any():
            return None
        return {t: 1 / 7 for t in S if mclose.at[dd, t] > msma10.at[dd, t]}

    def B10(dd):
        if np.isnan(r12.at[dd, "SPY"]) or np.isnan(r12.at[dd, "EFA"]):
            return None
        if r12.at[dd, "SPY"] > rf12[dd]:
            return {"SPY" if r12.at[dd, "SPY"] >= r12.at[dd, "EFA"] else "EFA": 1.0}
        return {"IEF": 1.0}

    def A(dd):
        if not all_el(dd):
            return None
        pick = topk(r12_1.loc[dd, S], 3)
        return {t: 1 / 3 for t in pick if r12_1.at[dd, t] > rf12_1[dd]}

    def Bm(dd):
        if not all_el(dd) or mtf_s.loc[dd].isna().any():
            return None
        return {t: mtf_s.at[dd, t] / 7 for t in S}

    def Cc(dd):
        if not all_el(dd) or np.isnan(jb[dd]):
            return None
        if jb[dd] == 1:
            pool, k = ["IEF", "TLT", "GLD"], 2
        else:
            pool, k = ["SPY", "EFA", "EEM", "DBC", "GLD"], 3
        pick = topk(r126.loc[dd, pool], k)
        return {t: 1 / k for t in pick if r126.at[dd, t] > rf126[dd]}

    def I1(dd):
        if not all_el(dd):
            return None
        v = {t: tsm(dd, t) for t in S}
        if any(np.isnan(x) for x in v.values()):
            return None
        return {t: max(0.0, x) / 7 for t, x in v.items()}

    return {"B8": B8, "B9": B9, "B10": B10, "J3-A": A, "J3-B": Bm, "J3-C": Cc, "J3-I1": I1,
            "B1": lambda dd: {"SPY": 1.0}, "B2": lambda dd: {"SPY": 0.6, "IEF": 0.4}}


def j3_books(d, rules, mult=1.0, only=None):
    s = d["sessions"]
    dec = rc.month_end_sessions(s)
    dec = dec[dec >= J3_FIRST]
    bk = {}
    for k, f in rules.items():
        if only and k not in only:
            continue
        T = monthly_targets(s, dec, rc.SLEEVES, f)
        bk[k] = rc.simulate(T, d["rets"][rc.SLEEVES], d["cash"], ETF_BP * mult, k, start=J3_FIRST,
                            equity_cols=["SPY", "EFA", "EEM"], always_rebalance=True)
    return bk


# --------------------------------------------------------------------------- #
# gates
# --------------------------------------------------------------------------- #
def exits_before_trough(pv) -> tuple[int, int]:
    k = n = 0
    for name, row in pv["episodes"].items():
        if row.get("status") == "outside_window":
            continue
        n += 1
        ed = row.get("exit_date")
        if ed and pd.Timestamp(ed) < pd.Timestamp(row["trough"]):
            k += 1
    return k, n


def gate_rows(primary, primary2x, effect, extra):
    g1 = bool(primary["holm"]["reject_h0"])
    g2 = primary["observed"] >= effect
    e = primary["eras"]
    g3 = bool(e["E1"] is not None and e["E2"] is not None and e["E1"] > 0 and e["E2"] > 0)
    g5 = bool(primary2x["holm"]["reject_h0"] and primary2x["observed"] >= effect)
    rows = [
        {"criterion": "G1 Holm p<0.05 on primary (D)", "observed": primary["holm"]["p_holm"], "met": g1},
        {"criterion": f"G2 primary >= {effect}", "observed": primary["observed"], "met": bool(g2)},
        {"criterion": "G3 positive in E1 and E2", "observed": e, "met": g3},
        {"criterion": "G4 hold-out", "observed": None, "met": "not_evaluated_sealed"},
        {"criterion": "G5 G1+G2 at 2x costs", "observed": {"p_holm": primary2x["holm"]["p_holm"],
                                                          "observed": primary2x["observed"]}, "met": g5},
    ] + extra + [{"criterion": "G7 clean window", "observed": "fixed textbook parameters", "met": True}]
    clears_d = g1 and g2 and g3 and g5
    return rows, clears_d


# --------------------------------------------------------------------------- #
# long-history tier
# --------------------------------------------------------------------------- #
def long_tier(end_long="1997-12-31"):
    ff = french_factors(pd.Timestamp(end_long))
    mkt = ff["Mkt-RF"] + ff["RF"]
    rf = ff["RF"]
    s = mkt.index
    g = yahoo("^GSPC", pd.Timestamp(end_long), "Close")
    gl = g.reindex(g.index.union(s)).ffill().reindex(s)
    T = rc.trend_broken(g).reindex(g.index.union(s)).ffill().reindex(s)
    MTF = rc.mtf(g).reindex(g.index.union(s)).ffill().reindex(s)
    M = rc.sahm_available(repo_fred("SAHMREALTIME", pd.Timestamp(end_long)), s)
    spread = (repo_fred("DBAA", pd.Timestamp(end_long)) - repo_fred("DGS10", pd.Timestamp(end_long))).dropna()
    C = rc.credit_flag(spread, s)
    R = pd.DataFrame({"MKT": mkt})
    level = (1 + mkt).cumprod()
    first_price = T.dropna().index.min()
    first_price = max(first_price, MTF.dropna().index.min())
    vol = mkt.rolling(21, min_periods=21).std(ddof=1) * math.sqrt(252)
    tiers = {
        "price_rules_1928_1997": (first_price, {"B1": pd.Series(1.0, index=s), "B3": 1 - T, "J1-D": MTF,
                                               "B4": (0.15 / vol).clip(upper=1.0)}),
        "sahm_rule_1960_1997": (pd.Timestamp("1960-01-04"), {"B1": pd.Series(1.0, index=s), "B3": 1 - T,
                                                             "J1-E": 1 - nanand(T, M)}),
        "credit_rules_1987_1997": (C.dropna().index.min(), {"B1": pd.Series(1.0, index=s), "B3": 1 - T,
                                                            "J1-A": 1 - C, "J1-B": 1 - nanand(T, C),
                                                            "J1-C": 1 - nanor(T, C)}),
    }
    out = {"returns_basis": "Ken French daily market (Mkt-RF + RF), cash = French RF; signals on ^GSPC levels; "
                            "index-level, no tradable instrument; 5 bp per side",
           "credit_spread": {"series": "DBAA - DGS10 (repo store at pin)", "first_obs": str(spread.index.min().date()),
                             "lag_rule": "value dated t-1, SMA of 252 observations ending t-1"},
           "tiers": {}}
    for tier, (start, ws) in tiers.items():
        start = pd.Timestamp(start)
        firsts = [v.dropna().index.min() for v in ws.values()]
        start = max([start] + [f for f in firsts if f is not None])
        bk = {}
        for k, w in ws.items():
            ww = w.where(s >= start)
            tgt = pd.DataFrame({"MKT": ww})
            thr = 0.10 if k == "B4" else None
            bk[k] = rc.simulate(tgt, R, rf, ETF_BP, k, start=start, equity_cols=["MKT"], threshold=thr)
        mask = pd.Series((s > start), index=s)
        met = {k: rc.book_metrics(b, mkt, rf, mask) for k, b in bk.items()}
        diffs = {k: {"ann_diff_vs_B1": float(W(b.returns - bk["B1"].returns, mask).mean() * 252),
                     "ann_diff_vs_B3": float(W(b.returns - bk["B3"].returns, mask).mean() * 252),
                     "sharpe_minus_B3": met[k]["sharpe"] - met["B3"]["sharpe"]} for k, b in bk.items()}
        eps = {}
        for name, (a, b2, c) in LPEAK.items():
            ep = rc.find_episode(level[level.index >= start], a, b2, c)
            if ep:
                eps[name] = ep
        piv = {k: rc.pivot_table(after_close_weight(b), b.returns, mkt.reindex(b.returns.index),
                                 level.reindex(b.returns.index), eps, first_exec=first_exec(b))
               for k, b in bk.items()}
        algo = rc.algorithmic_drawdowns(level[level.index >= start], 0.15)
        out["tiers"][tier] = {"first_decision": str(start.date()), "metrics": met, "point_differences": diffs,
                              "pivots": piv, "episodes": {k: {"peak": str(v["peak"].date()),
                                                              "trough": str(v["trough"].date()),
                                                              "drawdown": v["drawdown"]} for k, v in eps.items()},
                              "algorithmic_drawdowns_ge15": [{"peak": str(x["peak"].date()),
                                                              "trough": str(x["trough"].date()),
                                                              "drawdown": x["drawdown"]} for x in algo]}
    return out



# --------------------------------------------------------------------------- #
# J4
# --------------------------------------------------------------------------- #
J4DIR = Path("/home/ubuntu2/tmp/rotation-core/j4")
CACHE = Path("/home/ubuntu2/tmp/prophet-eval-cache/yahoo")
PIT = Path("/home/ubuntu2/tmp/rotation-core/data/repo/sp1500_pit_membership.parquet")
LABELS = Path("/home/ubuntu2/tmp/rotation-core/data/repo/sp1500_pit_sectors.parquet")
J4_LAST_FORMATION = pd.Timestamp("2015-12-31")


def j4_stage_d(d) -> dict:
    from engine import rotation_core_j4 as j4
    man = J4DIR / "manifest.json"
    if not man.exists():
        return {"status": "unavailable", "reason": "Phase-2 price fetch (P2-W2) has not produced j4/manifest.json"}
    manifest = json.loads(man.read_text())
    # identity-suspect handling is per membership interval: during a flagged interval (wrong issuer / span mismatch /
    # namespace collision) the ticker is treated as unpriced; 'no_series' intervals are unpriced anyway.
    bad = {}
    unmasked_starts_late = 0
    for r in manifest.get("identity_suspect_intervals", []):
        reasons = {x.split("(")[0] for x in str(r.get("why", "")).split(";")}
        if reasons <= {"starts_late", "ends_early"}:
            unmasked_starts_late += 1   # same issuer, series simply starts later: prices before first date are absent
            continue
        if r.get("why") != "no_series":
            bad.setdefault(r["ticker"], []).append((pd.Timestamp(r["start"]),
                                                    pd.Timestamp(r["end"]) if r.get("end") else pd.Timestamp("2100-01-01")))
    collide = set(manifest.get("variant_identity_policy", {}).get("collision_flagged", []))
    rec_rule = {}
    for r in manifest.get("recovered", []):
        if isinstance(r, dict):
            rec_rule[r.get("ticker")] = r.get("rule") or r.get("variant")
    _hash_bytes(str(PIT), PIT.read_bytes()); _hash_bytes(str(LABELS), LABELS.read_bytes())
    _hash_bytes(str(man), man.read_bytes())
    pit = pd.read_parquet(PIT)
    pit["start_date"] = pd.to_datetime(pit["start_date"]); pit["end_date"] = pd.to_datetime(pit["end_date"])
    labels = pd.read_parquet(LABELS).set_index("ticker")["sector"]
    s = d["sessions"]
    me = rc.month_end_sessions(s)
    forms = [t for t in me if pd.Timestamp("1998-01-01") <= t <= J4_LAST_FORMATION]
    nxt = me[me > J4_LAST_FORMATION][0]
    forms_plus = forms + [nxt]
    end_j4 = s[s.get_loc(nxt) + 1]
    s4 = s[s <= end_j4]
    tick = sorted(set(pit.loc[pit["src"].isin(["sp500", "sp400"]), "ticker"]))
    cols, src = {}, {"cache": 0, "fetched": 0, "suspect_intervals_masked": 0, "collision_excluded": 0, "missing": 0}
    for t in tick:
        p1, p2 = CACHE / f"{t}.parquet", J4DIR / "prices" / f"{t}.parquet"
        if p1.exists():
            x = pd.read_parquet(p1)
            ser = x["close"].astype(float); src["cache"] += 1
        elif p2.exists():
            x = pd.read_parquet(p2)
            v = str(x["variant"].iloc[0]) if "variant" in x.columns else "R0_as_is"
            if v in collide or v not in ("R0_as_is", "R7_repo_alias", "R1_slash_first"):   # R4/R6 collisions
                src["collision_excluded"] += 1
                continue
            ser = x["Adj Close"].astype(float); src["fetched"] += 1
        else:
            src["missing"] += 1
            continue
        ser.index = pd.to_datetime(ser.index).normalize()
        ser = ser[~ser.index.duplicated()].sort_index()
        for a, b in bad.get(t, []):
            ser[(ser.index >= a) & (ser.index <= b)] = np.nan
            src["suspect_intervals_masked"] += 1
        cols[t] = ser[ser.index <= end_j4].reindex(s4)
    prices = pd.DataFrame(cols)
    etf = d["adj"][rc.SECTORS].reindex(s4)
    el = rc.eligible(etf)
    res = j4.run_j4(prices, etf, d["adj"]["SPY"].reindex(s4), pit, forms_plus, s4, el, labels_gics=labels)
    df = res["records"]
    df = df[df.index <= J4_LAST_FORMATION]
    sens = j4.run_j4(prices, etf, d["adj"]["SPY"].reindex(s4), pit, forms_plus, s4, el, labels_gics=labels,
                     assignment="gics")["records"]
    sens = sens[sens.index <= J4_LAST_FORMATION]
    res2x = j4.run_j4(prices, etf, d["adj"]["SPY"].reindex(s4), pit, forms_plus, s4, el, labels_gics=labels,
                      cost_bp=20.0)["records"]
    res2x = res2x[res2x.index <= J4_LAST_FORMATION]
    # S&P 1500 sensitivity (header J4.universe): sp400 added one year after its 2012-01-13 floor
    f1500 = [f for f in forms_plus if f >= pd.Timestamp("2013-01-01")]
    s1500 = j4.run_j4(prices, etf, d["adj"]["SPY"].reindex(s4), pit, f1500, s4, el, labels_gics=labels,
                      legs=("sp500", "sp400"))["records"]
    s1500 = s1500[s1500.index <= J4_LAST_FORMATION]
    s500_same = df[df.index >= pd.Timestamp("2013-01-01")]
    # formations with a finite statistic only (no sector SPDR is eligible before ~1999-12)
    df = df[df["delta_i"].notna()]
    res2x = res2x[res2x["delta_i"].notna()]

    def mstat(x, seed, effect):
        x = x.dropna().to_numpy()
        obs = float(x.mean() * 12)
        dist = rc.bootstrap_stat([x], lambda a: a.mean(axis=1) * 12, B, 3, seed)
        se = float(np.std(dist, ddof=1))
        d6 = rc.bootstrap_stat([x], lambda a: a.mean(axis=1) * 12, B, 6, seed + 500000)
        return {"observed": obs, "ci95": rc.ci95(dist), "p_one_sided_centred": rc.centred_p(dist, obs),
                "block6": {"ci95": rc.ci95(d6), "p_one_sided_centred": rc.centred_p(d6, obs)},
                "n_months": int(len(x)), "power": rc.power_line(se, 2, effect, "per year (fraction)")}

    A = mstat(df["delta_i"], SEED + 4000, 0.02)
    Bk = mstat(df["book_excess"], SEED + 4001, 0.02)
    h = rc.holm({"J4-A": A["p_one_sided_centred"], "J4-B": Bk["p_one_sided_centred"]})
    A["holm"], Bk["holm"] = h["J4-A"], h["J4-B"]
    eras = {}
    for nm, col in (("J4-A", "delta_i"), ("J4-B", "book_excess")):
        le = pd.to_datetime(df["label_end"])
        eras[nm] = {"E1": float(df.loc[le <= rc.ERA_SPLIT, col].mean() * 12),
                    "E2": float(df.loc[le > rc.ERA_SPLIT, col].mean() * 12),
                    "split_by": "label_end (return date)"}
    A["eras"], Bk["eras"] = eras["J4-A"], eras["J4-B"]
    cov = df["priced_share"]
    treat = {"i_exclude_unpriced": A["observed"], "iii_minus30_terminal": float(df["delta_iii"].mean() * 12)}
    gates = [
        {"criterion": "G1 Holm p<0.05 (J4-A)", "observed": A["holm"]["p_holm"], "met": bool(A["holm"]["reject_h0"])},
        {"criterion": "G2 J4-A >= 0.02/yr", "observed": A["observed"], "met": A["observed"] >= 0.02},
        {"criterion": "G3 positive in E1 and E2", "observed": eras["J4-A"],
         "met": eras["J4-A"]["E1"] > 0 and eras["J4-A"]["E2"] > 0},
        {"criterion": "G4 hold-out", "observed": None, "met": "not_evaluated_sealed"},
        {"criterion": "G5 at 2x costs (J4-A has no costs; J4-B shown)",
         "observed": float(res2x["book_excess"].mean() * 12), "met": bool(A["holm"]["reject_h0"] and A["observed"] >= 0.02)},
        {"criterion": "G6 [D only, provisional] same sign under treatments (i) and (iii)", "observed": treat,
         "met": bool(np.sign(treat["i_exclude_unpriced"]) == np.sign(treat["iii_minus30_terminal"]))},
        {"criterion": "G6 [D only, provisional] median monthly priced share >= 0.85", "observed": float(cov.median()),
         "met": bool(cov.median() >= 0.85)},
        {"criterion": "G7 clean window", "observed": "fixed parameters", "met": True},
    ]
    yearly = df.groupby(df.index.year).agg(members=("members", "mean"), priced_share=("priced_share", "mean"),
                                           unpriced_lead=("unpriced_share_labelled_leading", "mean"),
                                           unpriced_lag=("unpriced_share_labelled_lagging", "mean"))
    return {"status": "evaluated", "formations_D": [str(df.index.min().date()), str(df.index.max().date())],
            "price_sources": src, "fetch_manifest_summary": {k: (len(v) if isinstance(v, list) else v)
                                                             for k, v in manifest.items()
                                                             if k in ("n_ever_members", "n_from_survivor_cache",
                                                                      "n_attempted", "n_recovered", "n_failed",
                                                                      "n_identity_suspect_intervals")},
            "J4-A": A, "J4-B": Bk, "treatments": treat, "J4-B_cost_2x_ann": float(res2x["book_excess"].mean() * 12),
            "suspect_starts_late_only_not_masked": unmasked_starts_late,
            "clipped_returns": res.get("clip_log"),
            "sensitivity_sp1500_from_2013": {"J4-A_ann_sp1500": float(s1500["delta_i"].mean() * 12),
                                             "J4-A_ann_sp500_same_months": float(s500_same["delta_i"].mean() * 12),
                                             "J4-B_ann_sp1500": float(s1500["book_excess"].mean() * 12),
                                             "months": int(s1500["delta_i"].notna().sum())},
            "sensitivity_gics_assignment": {"J4-A_ann": float(sens["delta_i"].mean() * 12),
                                            "J4-B_ann": float(sens["book_excess"].mean() * 12)},
            "coverage_by_formation_month": {str(k.date()): float(v) for k, v in cov.items()},
            "coverage_by_year": json.loads(yearly.to_json(orient="index")),
            "assigned_share_mean": float((df["assigned"] / df["members"]).mean()),
            "gates": gates, "cap": "L0 (priced coverage below 85%; header known cap)"}

# --------------------------------------------------------------------------- #
# Stage D
# --------------------------------------------------------------------------- #
def run_stage_d(smoke: bool) -> dict:
    END = rc.D_END
    d = load(END)
    s, cash, r_spy = d["sessions"], d["cash"], d["rets"]["SPY"].fillna(0.0)
    assert s.max() <= END and all(v.index.max() <= END for v in (d["hy"], d["dbaa"], d["dgs10"]))
    from engine.trial_ledger import TrialLedger
    import tempfile
    lraw = subprocess.check_output(["git", "-C", str(ROOT), "show", "623f0a4623:data/trial_ledger.jsonl"])
    _hash_bytes("623f0a4623:data/trial_ledger.jsonl", lraw)
    ltmp = Path(tempfile.mkdtemp()) / "trial_ledger.jsonl"
    ltmp.write_bytes(lraw)
    led = rc.SummedLedger(TrialLedger(path=str(ltmp)),
                          ["rotation_core_v1", "thematic_rotation_phase0", "cross_asset_phase0",
                           "index_direction_phase0"])
    out = {"jobs": {}, "data_quality": d["dq"], "deviations": list(DEVIATIONS)}

    # ---------------- J1
    w, flags = j1_weights(d)
    bk1 = j1_books(d, w)
    inc = {}
    for key, fname, col in (("J1-I1", "spvector_glide.parquet", "weight"),
                            ("J1-I2", "risk_radar_gross.parquet", "gross")):
        ws, src = load_incumbent_weight(fname, col, s, END)
        if ws is None:
            un = INCUMBENTS / ("risk_radar_unavailable.json" if key == "J1-I2" else "spvector_unavailable.json")
            inc[key] = {"status": "unavailable",
                        "reason": json.loads(un.read_text()) if un.exists() else "no replay output produced"}
            continue
        ws = ws.where(s >= J1_FIRST)
        bk1[key] = rc.simulate(spy_targets(ws), d["rets"][["SPY", "BOND"]], cash, ETF_BP, key, start=J1_FIRST)
        inc[key] = {"status": "evaluated", "source": src,
                    "first_weight": str(ws.first_valid_index().date()) if ws.notna().any() else None}
    m1 = pd.Series((s > J1_FIRST) & (s <= END), index=s)
    if smoke:
        print("J1 books:", {k: (len(b.returns), int(b.traded.gt(0).sum())) for k, b in bk1.items()})
        print("J1 flag coverage from J1_FIRST:", {k: int(v[s >= J1_FIRST].isna().sum()) for k, v in flags.items()})
    cands = ["J1-A", "J1-B", "J1-C", "J1-D", "J1-E"]

    def f1(bk):
        spec = []
        for c in cands:
            spec.append((f"{c}:P1", bk[c].returns, XRef(bk[c], r_spy, cash), "mean", 0.01, "per year (fraction)"))
            spec.append((f"{c}:P2", bk[c].returns, bk["B3"].returns, "sharpe", 0.10, "Sharpe"))
        return family(spec, cash, m1, 10, SEED)

    F1 = f1(bk1)
    bk1_2x = j1_books(d, w, 2.0, only=cands + ["B3"])
    F1_2x = f1(bk1_2x)
    met1 = {k: rc.book_metrics(b, r_spy, cash, m1) for k, b in bk1.items()}
    for k in met1:
        met1[k]["dsr"] = rc.dsr(W(bk1[k].returns, m1).values, W(cash, m1).values, led)
    xw = {c: xref(bk1[c], r_spy, cash, m1)[1] for c in cands + ["B3"]}
    eps = {}
    spy_level = (1 + r_spy).cumprod()
    for name, (a, b2, c) in DPEAK.items():
        ep = rc.find_episode(spy_level[s >= J1_FIRST], a, b2, c)
        if ep:
            eps[name] = ep
    piv1 = {k: rc.pivot_table(after_close_weight(b), b.returns, r_spy.reindex(b.returns.index),
                              spy_level.reindex(b.returns.index), eps, first_exec=first_exec(b),
                              sealed_tail=SEALED_TAIL) for k, b in bk1.items()}
    gates1 = {}
    spy_m = met1["B1"]
    for c in cands:
        mt, pv = met1[c], piv1[c]
        k_ex, n_ex = exits_before_trough(pv)
        extra = [
            {"criterion": "G6 [D only, provisional] down-capture <= up-capture - 0.20",
             "observed": [mt["down_capture_monthly"], mt["up_capture_monthly"]],
             "met": bool(mt["down_capture_monthly"] is not None and mt["up_capture_monthly"] is not None
                         and mt["down_capture_monthly"] <= mt["up_capture_monthly"] - 0.20)},
            {"criterion": "G6 [D only, provisional] MaxDD <= 0.70 x SPY MaxDD", "observed": [mt["max_drawdown"], spy_m["max_drawdown"]],
             "met": bool(mt["max_drawdown"] >= 0.70 * spy_m["max_drawdown"])},
            {"criterion": "G6 [D only, provisional] CAGR >= SPY CAGR - 2.0pp", "observed": [mt["ann_return"], spy_m["ann_return"]],
             "met": bool(mt["ann_return"] >= spy_m["ann_return"] - 0.02)},
            {"criterion": "G6 [D only, provisional] false pivots <= 1.5 per calm year", "observed": pv["false_pivots_per_calm_year"],
             "met": bool(pv["false_pivots_per_calm_year"] is not None and pv["false_pivots_per_calm_year"] <= 1.5)},
            {"criterion": "G6 [D only, provisional] exit before trough in >= 6 named episodes (D has 6 of the 9-10; H sealed)",
             "observed": f"{k_ex}/{n_ex}", "met": True if k_ex >= 6 else ("pending_H" if k_ex + 3 >= 6 else False)},
            {"criterion": "G6 [D only, provisional] Sharpe >= B2, B3, B4", "observed": [mt["sharpe"], met1["B2"]["sharpe"],
                                                                 met1["B3"]["sharpe"], met1["B4"]["sharpe"]],
             "met": bool(mt["sharpe"] >= max(met1["B2"]["sharpe"], met1["B3"]["sharpe"], met1["B4"]["sharpe"]))},
        ]
        rows, clears = gate_rows(F1[f"{c}:P1"], F1_2x[f"{c}:P1"], 0.01, extra)
        gates1[c] = {"criteria": rows, "clears_G1_G2_G3_G5_on_D": clears}
    # J1* selection on D
    p1obs = {c: F1[f"{c}:P1"]["observed"] for c in cands}
    xb3, _ = xref(bk1["B3"], r_spy, cash, m1)
    p1obs["B3"] = float((bk1["B3"].returns - xb3).pipe(W, m1).mean() * 252)
    best1 = max(p1obs, key=lambda k: (p1obs[k], k))
    j1star = best1 if p1obs[best1] > 0 else "B3"
    # incumbents FI (J1 part)
    fi_spec = []
    for key in ("J1-I1", "J1-I2"):
        if key in bk1:
            fi_spec.append((f"{key}:vsX", bk1[key].returns, XRef(bk1[key], r_spy, cash), "mean", 0.01,
                            "per year (fraction)", m1))
            fi_spec.append((f"{key}:SharpeVsB3", bk1[key].returns, bk1["B3"].returns, "sharpe", 0.10, "Sharpe", m1))
    out["jobs"]["J1"] = {"window_D": [str(J1_FIRST.date()), str(END.date())], "family_F1": F1,
                         "family_F1_cost_2x": F1_2x, "metrics": met1, "x_mean_weight": xw, "pivots": piv1,
                         "episodes_D": {k: {"peak": str(v["peak"].date()), "trough": str(v["trough"].date()),
                                            "drawdown": v["drawdown"]} for k, v in eps.items()},
                         "episodes_sealed": SEALED_EPISODES,
                         "algorithmic_drawdowns_ge15": [{"peak": str(x["peak"].date()), "trough": str(x["trough"].date()),
                                                         "drawdown": x["drawdown"]} for x in
                                                        rc.algorithmic_drawdowns(spy_level[s >= J1_FIRST], 0.15)],
                         "gates": gates1, "incumbents": inc,
                         "selection": {"p1_observed_D": p1obs, "J1_star": j1star}}

    # ---------------- J2
    sig2 = j2_signals(d)
    rules2 = j2_rules(sig2)
    st = INCUMBENTS / "sector_signals_states.parquet"
    if st.exists() and incumbent_provenance("sector_signals_states.parquet") is not None:
        _hash_bytes(str(st), st.read_bytes())
        states = pd.read_parquet(st)
        states.index = pd.to_datetime(states.index).normalize()
        states = states[states.index <= END].reindex(s)
        keep = {"BUY", "BUY_PARTIAL", "SETUP_BUY", "NEUTRAL", "EXTENDED"}

        def i1(dd):
            e = [t for t in rc.SECTORS if bool(sig2["el"].at[dd, t]) and t in states.columns
                 and states.at[dd, t] in keep]
            return {t: 1 / len(e) for t in e} if e else {"SPY": 1.0}
        rules2["J2-I1"] = i1
    bk2, tg2 = j2_books(d, rules2)
    m2 = pd.Series((s > J2_FIRST) & (s <= END), index=s)
    c2 = ["J2-A", "J2-B", "J2-C", "J2-D"]

    def f2(bk):
        spec = []
        for c in c2:
            spec.append((f"{c}:Q1", bk[c].returns, bk["B5"].returns, "mean", 0.01, "per year (fraction)"))
            spec.append((f"{c}:Q2", bk[c].returns, bk["B6"].returns, "mean", 0.01, "per year (fraction)"))
        return family(spec, cash, m2, 8, SEED + 1000)

    F2 = f2(bk2)
    bk2_2x, _ = j2_books(d, rules2, 2.0, only=c2 + ["B5", "B6"])
    F2_2x = f2(bk2_2x)
    met2 = {k: rc.book_metrics(b, r_spy, cash, m2) for k, b in bk2.items()}
    for k in met2:
        met2[k]["dsr"] = rc.dsr(W(bk2[k].returns, m2).values, W(cash, m2).values, led)
    gates2 = {}
    for c in c2:
        mt = met2[c]
        irv = ir(bk2[c].returns, bk2["B5"].returns, m2)
        extra = [
            {"criterion": "G6 [D only, provisional] IR vs B5 >= 0.20", "observed": irv, "met": bool(irv is not None and irv >= 0.20)},
            {"criterion": "G6 [D only, provisional] MaxDD no worse than B5 MaxDD - 5pp", "observed": [mt["max_drawdown"], met2["B5"]["max_drawdown"]],
             "met": bool(mt["max_drawdown"] >= met2["B5"]["max_drawdown"] - 0.05)},
            {"criterion": "G6 [D only, provisional] Q2 point > 0", "observed": F2[f"{c}:Q2"]["observed"], "met": F2[f"{c}:Q2"]["observed"] > 0},
            {"criterion": "G6 [D only, provisional] point excess vs B1 and B7 > 0",
             "observed": [float((bk2[c].returns - bk2[k].returns).pipe(W, m2).mean() * 252) for k in ("B1", "B7")],
             "met": all(float((bk2[c].returns - bk2[k].returns).pipe(W, m2).mean()) > 0 for k in ("B1", "B7"))},
        ]
        rows, clears = gate_rows(F2[f"{c}:Q1"], F2_2x[f"{c}:Q1"], 0.01, extra)
        gates2[c] = {"criteria": rows, "clears_G1_G2_G3_G5_on_D": clears}
    q1obs = {c: F2[f"{c}:Q1"]["observed"] for c in c2}
    q1obs["B6"] = float((bk2["B6"].returns - bk2["B5"].returns).pipe(W, m2).mean() * 252)
    best2 = max(q1obs, key=lambda k: (q1obs[k], k))
    j2star = best2 if q1obs[best2] > 0 else "B5"

    # ---------------- J5 / J2-E (descriptive in D)
    wj1 = w[j1star] if j1star in w else None
    comp = tg2[j2star].ffill()
    comp = comp.div(comp.sum(axis=1), axis=0)
    cols2 = rc.SECTORS + ["SPY"]
    trio = {t: 1 / 3 for t in rc.DEFENSIVE_TRIO}
    dec2 = rc.month_end_sessions(s)
    dec2 = dec2[dec2 >= J2_FIRST]

    def j2e(dd):
        if np.isnan(wj1[dd]):
            return None
        if wj1[dd] >= 0.5:
            row = comp.loc[dd]
            return {a: v for a, v in row.items() if v > 0}
        return trio
    T2e = monthly_targets(s, dec2, cols2, j2e)
    bk5 = {"J2-E": rc.simulate(T2e, d["rets"][cols2], cash, ETF_BP, "J2-E", start=J2_FIRST, equity_cols=cols2,
                               always_rebalance=True)}
    TA = comp.mul(wj1, axis=0)
    TA.loc[TA.index < J2_FIRST] = np.nan
    # J5 books rebalance at every J2* month-end decision and whenever the J1* weight changes
    wch = wj1.ne(wj1.shift(1)) & wj1.notna()
    exec_days = pd.Series(s.isin(dec2), index=s) | wch
    TA.loc[~exec_days] = np.nan
    bk5["J5-A"] = rc.simulate(TA, d["rets"][cols2], cash, ETF_BP, "J5-A", start=J2_FIRST, equity_cols=cols2,
                              always_rebalance=True)
    r126 = d["adj"] / d["adj"].shift(126) - 1
    rf126 = rc.cum_cash(cash, 126, 0)
    gl_el = rc.eligible(d["adj"][["GLD"]])["GLD"]
    defpick = pd.Series(np.nan, index=s, dtype=object)
    for dd in dec2:
        cand = {"BOND": r126.at[dd, "BOND"]}
        if bool(gl_el[dd]):
            cand["GLD"] = r126.at[dd, "GLD"]
        top = topk(pd.Series(cand), 1)
        defpick[dd] = top[0] if top and cand[top[0]] > rf126[dd] else "CASH"
    defpick = defpick.ffill()
    cols5 = cols2 + ["BOND", "GLD"]
    TB = pd.DataFrame(0.0, index=s, columns=cols5)
    TB[cols2] = TA[cols2].fillna(0.0)
    for a in ("BOND", "GLD"):
        TB[a] = np.where(defpick.values == a, 1 - wj1.reindex(s).fillna(1.0).values, 0.0)
    valid = TA.notna().any(axis=1) & defpick.notna()
    TB.loc[~valid] = np.nan
    bk5["J5-B"] = rc.simulate(TB, d["rets"][cols5], cash, ETF_BP, "J5-B", start=J2_FIRST, equity_cols=cols2,
                              always_rebalance=True)
    met5 = {k: rc.book_metrics(b, r_spy, cash, m2) for k, b in bk5.items()}
    for k in met5:
        met5[k]["dsr"] = rc.dsr(W(bk5[k].returns, m2).values, W(cash, m2).values, led)

    # J2 episode holdings (D episodes)
    eps2 = {k: v for k, v in eps.items() if v["peak"] > J2_FIRST}
    holdings = {}
    allbk2 = {**bk2, **bk5}
    for name, ep in eps2.items():
        pk, tr = ep["peak"], ep["trough"]
        trio_r = float(np.prod(1 + d["rets"].loc[(s > pk) & (s <= tr), rc.DEFENSIVE_TRIO].fillna(0).mean(axis=1)) - 1)
        spy_r = float(np.prod(1 + r_spy[(s > pk) & (s <= tr)]) - 1)
        rows = {}
        for k, b in allbk2.items():
            hpk = b.holdings.shift(-1).loc[pk]
            htr = b.holdings.shift(-1).loc[tr]
            span = b.holdings[(b.holdings.index > pk) & (b.holdings.index <= tr)]
            share = (span > 1e-9).mean()
            rows[k] = {"held_at_peak": {a: round(float(v), 3) for a, v in hpk.items() if v > 1e-9},
                       "held_at_trough": {a: round(float(v), 3) for a, v in htr.items() if v > 1e-9},
                       "share_of_sessions_held_peak_to_trough": {a: round(float(v), 3) for a, v in share.items() if v > 0}}
        holdings[name] = {"peak": str(pk.date()), "trough": str(tr.date()), "spy_return": spy_r,
                          "defensive_trio_return": trio_r, "trio_minus_spy": trio_r - spy_r, "books": rows}
    out["jobs"]["J2"] = {"window_D": [str(J2_FIRST.date()), str(END.date())], "family_F2": F2,
                         "family_F2_cost_2x": F2_2x, "metrics": met2, "gates": gates2,
                         "selection": {"q1_observed_D": q1obs, "J2_star": j2star},
                         "episode_holdings_D": holdings, "episodes_sealed": SEALED_EPISODES}
    out["jobs"]["J5"] = {"window_D": [str(J2_FIRST.date()), str(END.date())], "status": "descriptive_only_in_D",
                         "J1_star": j1star, "J2_star": j2star, "metrics": met5,
                         "point_differences_D": {
                             "J5-A_minus_J1star_on_SPY": float((bk5["J5-A"].returns - bk1[j1star].returns.reindex(s).fillna(0)).pipe(W, m2).mean() * 252),
                             "J5-B_minus_J5-A": float((bk5["J5-B"].returns - bk5["J5-A"].returns).pipe(W, m2).mean() * 252),
                             "J2-E_minus_J2star": float((bk5["J2-E"].returns - bk2[j2star].returns).pipe(W, m2).mean() * 252)},
                         "pivots": {k: rc.pivot_table(after_close_weight(b), b.returns, r_spy.reindex(b.returns.index),
                                                      spy_level.reindex(b.returns.index), eps2,
                                                      first_exec=first_exec(b), sealed_tail=SEALED_TAIL)
                                    for k, b in bk5.items()
                                    if k.startswith("J5")}}
    if "J2-I1" in bk2:
        fi_spec.append(("J2-I1:vsB5", bk2["J2-I1"].returns, bk2["B5"].returns, "mean", 0.01, "per year (fraction)", m2))
        fi_spec.append(("J2-I1:vsB6", bk2["J2-I1"].returns, bk2["B6"].returns, "mean", 0.01, "per year (fraction)", m2))

    # ---------------- J3
    rules3 = j3_rules(d, flags)
    bk3 = j3_books(d, rules3)
    m3 = pd.Series((s > J3_FIRST) & (s <= END), index=s)
    ew7 = d["rets"][rc.SLEEVES].mean(axis=1)
    c3 = ["J3-A", "J3-B", "J3-C"]

    def f3(bk):
        spec = []
        for c in c3:
            spec.append((f"{c}:R1", bk[c].returns, XRef(bk[c], ew7, cash), "mean", 0.01, "per year (fraction)"))
            spec.append((f"{c}:R2", bk[c].returns, bk["B9"].returns, "mean", 0.01, "per year (fraction)"))
        return family(spec, cash, m3, 6, SEED + 2000)

    F3 = f3(bk3)
    bk3_2x = j3_books(d, rules3, 2.0, only=c3 + ["B9"])
    F3_2x = f3(bk3_2x)
    met3 = {k: rc.book_metrics(b, r_spy, cash, m3) for k, b in bk3.items()}
    for k in met3:
        met3[k]["dsr"] = rc.dsr(W(bk3[k].returns, m3).values, W(cash, m3).values, led)
    gates3 = {}
    for c in c3:
        mt = met3[c]
        extra = [
            {"criterion": "G6 [D only, provisional] Sharpe >= B2, B9, B10", "observed": [mt["sharpe"], met3["B2"]["sharpe"],
                                                                 met3["B9"]["sharpe"], met3["B10"]["sharpe"]],
             "met": bool(mt["sharpe"] >= max(met3["B2"]["sharpe"], met3["B9"]["sharpe"], met3["B10"]["sharpe"]))},
            {"criterion": "G6 [D only, provisional] MaxDD <= B8 MaxDD", "observed": [mt["max_drawdown"], met3["B8"]["max_drawdown"]],
             "met": bool(mt["max_drawdown"] >= met3["B8"]["max_drawdown"])},
        ]
        rows, clears = gate_rows(F3[f"{c}:R1"], F3_2x[f"{c}:R1"], 0.01, extra)
        gates3[c] = {"criteria": rows, "clears_G1_G2_G3_G5_on_D": clears}
    fi_spec.append(("J3-I1:vsX3", bk3["J3-I1"].returns, XRef(bk3["J3-I1"], ew7, cash), "mean", 0.01,
                    "per year (fraction)", m3))
    fi_spec.append(("J3-I1:vsB9", bk3["J3-I1"].returns, bk3["B9"].returns, "mean", 0.01, "per year (fraction)", m3))
    out["jobs"]["J3"] = {"window_D": [str(J3_FIRST.date()), str(END.date())], "family_F3": F3,
                         "family_F3_cost_2x": F3_2x, "metrics": met3, "gates": gates3,
                         "note": "E1 for J3 is 2007-03..2009-12 only (about 2.8 years)."}

    # ---------------- incumbents FI
    FI, pv = {}, {}
    for i, (tid, a, b, kind, eff, unit, mk) in enumerate(fi_spec):
        FI[tid] = contrast(tid, a, b, cash, kind, mk, 8, eff, unit, SEED + 3000 + i)
        pv[tid] = FI[tid]["p_one_sided_centred"]
    declared = ["J1-I1:vsX", "J1-I1:SharpeVsB3", "J1-I2:vsX", "J1-I2:SharpeVsB3", "J2-I1:vsB5", "J2-I1:vsB6",
                "J3-I1:vsX3", "J3-I1:vsB9"]
    for tid in declared:
        if tid not in FI:
            FI[tid] = {"contrast": tid, "status": "unavailable", "p_one_sided_centred": 1.0}
            pv[tid] = 1.0
    h = rc.holm(pv)
    for tid in FI:
        FI[tid]["holm"] = h[tid]
    out["incumbents"] = {"family_FI": FI, "nominal_m": 8, "computed_m": len(fi_spec), "holm_m": len(pv),
                         "cap": "L0 (G7 fails: parameters chosen on the evaluation history)", "J1": inc,
                         "J2-I1": "evaluated" if "J2-I1" in bk2 else "unavailable (no state series)"}

    # ---------------- J4
    out["jobs"]["J4"] = j4_stage_d(d)

    # ---------------- long-history tier
    out["long_history"] = long_tier()

    if smoke:
        print("J2 books:", {k: int(b.traded.gt(0).sum()) for k, b in bk2.items()})
        print("J3 books:", {k: int(b.traded.gt(0).sum()) for k, b in bk3.items()})
        print("J5 books:", {k: int(b.traded.gt(0).sum()) for k, b in bk5.items()})
        print("episodes D:", list(eps))
        print("long tiers:", {k: v["first_decision"] for k, v in out["long_history"]["tiers"].items()})
        print("DSR n:", led.effective_n(), led.parts)
        print("J4:", out["jobs"]["J4"].get("status"), out["jobs"]["J4"].get("price_sources"))
        return {}
    out["dsr_trial_count"] = {"effective_n": led.effective_n(), "parts": led.parts}
    return out


# --------------------------------------------------------------------------- #
# output
# --------------------------------------------------------------------------- #
def jsonable(o):
    if isinstance(o, dict):
        return {str(k): jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [jsonable(v) for v in o]
    if isinstance(o, (np.floating, float)):
        return None if not np.isfinite(o) else float(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, (pd.Timestamp,)):
        return str(o.date())
    return o


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=["D", "H"], required=True)
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args()
    header = rc.verify_header(HEADER)
    stage_guard(args.stage)
    if not args.smoke:
        dirty = _git("status", "--porcelain", "--", "engine/rotation_core_evaluation.py", "engine/rotation_core_j4.py",
                     "scripts/run_rotation_core_v1.py", "scripts/rotation_core_report.py").strip()
        if dirty:
            raise SystemExit(f"Stage D refused: harness files are not committed:\n{dirty}")
    res = run_stage_d(args.smoke)
    if args.smoke:
        print("smoke OK (no statistics printed, nothing written)")
        return 0
    from scripts.rotation_core_report import build_artifact, write_markdown  # noqa: E402
    art = build_artifact(res, header, INPUT_HASHES, PIN, B, SEED)
    STAGE_D_JSON.write_text(json.dumps(jsonable(art), indent=1, sort_keys=False) + "\n")
    write_markdown(art, STAGE_D_MD)
    print("wrote", STAGE_D_JSON, STAGE_D_MD)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
