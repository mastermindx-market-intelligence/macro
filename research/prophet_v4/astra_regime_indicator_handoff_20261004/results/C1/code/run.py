"""Lane C1 — Rotation / leadership-persistence state variable (PIT-safe).

Build a daily, point-in-time-safe regime conditioning table from sector ETFs, breadth and
real rates; label each session by expanding-window terciles; measure agreement with the
incumbent PIT regime store; prove the variable passes two pre-declared positive controls.

Inputs (read-only):
  Sector ETF closes: XLK XLE XLF XLV XLI XLY XLP XLU XLB (from 1998-12)
  XLRE (from 2015-10), XLC (from 2018-06)
  SPY (master calendar) and RSP (breadth)
  data/fred/DFII10.parquet (us10y_real)
  data/regime/regime_v2_pit.parquet (flag_rotation_persistence, transition_state, pit_class)

The shift parameter on :func:`build_rotation_state_daily` is exposed so that test code can
exercise the export pipeline with shift=0 to prove leak detection power.
The `compute_cuts` helper is the same call path the pipeline uses for tercile cuts; tests
exercise it directly to verify PIT-safe cut computation (G1 round-3).
"""
from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, ".")

import numpy as np
import pandas as pd

# ─────────────────────── file locations ───────────────────────
SECTOR_ETFS = ["XLK", "XLE", "XLF", "XLV", "XLI", "XLY", "XLP", "XLU", "XLB", "XLRE", "XLC"]


def _find_repo() -> Path:
    """Locate the macro repo root.

    Walks up from this file's location looking for a directory that has both `data/` and
    `.git/`. The C1_REPO env var overrides the walk (used by CI or alternate checkouts).
    """
    env = os.environ.get("C1_REPO")
    if env:
        return Path(env).resolve()
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / "data").is_dir() and (p / ".git").exists():
            return p
        p = p.parent
    raise RuntimeError("Cannot find repo root (no C1_REPO and no data/.git ancestor)")


REPO = _find_repo()
RESULTS = REPO / "research/prophet_v4/astra_regime_indicator_handoff_20261004/results/C1"
CODE = RESULTS / "code"
YAHOO = REPO / "data/yahoo"
FRED = REPO / "data/fred"
REGIME = REPO / "data/regime/regime_v2_pit.parquet"

OUT_PARQUET = RESULTS / "rotation_state_daily.parquet"
OUT_CUTS_PARQUET = RESULTS / "rotation_cuts_daily.parquet"
OUT_RESULT_MD = RESULTS / "RESULT.md"
OUT_RESULT_JSON = RESULTS / "result.json"
OUT_HASHES = RESULTS / "hashes.txt"
OUT_TEST_SUMMARY = CODE / "_test_summary.txt"

# Round-2/3 frozen table hashes. Round 4 must not rewrite these files.
FROZEN_STATE_SHA256 = "9361dbf08018f0c23bc6e9b29fa014bc42429ed3289d359adf7a16f52be3e2dd"
FROZEN_CUTS_SHA256 = "484492539ae42cb3055416c12f144f93f748549bf21e4cf3de2f1e1eb6a002f8"

IDIO_CS_4DP_DEVIATION = (
    "idio_std and cs_std agree at 4 dp (0.0302): the positive control's "
    "idiosyncratic and cross-sectional scales are not distinguishable at that precision"
)

LAG = 21
MIN_COMMON = 6
MIN_TERCILE_HISTORY = 756
DEFAULT_SHIFT = 1  # one-session shift (PIT safety)

WINDOWS_FAST = [
    ("2020-11-09", "2020-12-31"),
    ("2021-02-01", "2021-03-31"),
]
WINDOWS_PERSISTENT = [
    ("2022-01-03", "2022-06-30"),
    ("2023-03-01", "2023-06-30"),
]


# ─────────────────────── pure helpers (testable in isolation) ───────────────────────
def tercile_cuts(v_arr: np.ndarray, i: int, lo_q: float = 1.0 / 3, hi_q: float = 2.0 / 3,
                 min_history: int = MIN_TERCILE_HISTORY) -> tuple[float, float]:
    """Compute the (lo, hi) tercile cuts for date index i using ONLY v_arr[:i] (strictly prior).

    Returns (nan, nan) when i == 0 or fewer than min_history prior non-NaN values exist.
    A pure function: it reads v_arr[:i] and nothing else — safe to leak-test by mutating
    v_arr[i:].
    """
    if i <= 0:
        return float("nan"), float("nan")
    prior = v_arr[:i]
    prior = prior[~np.isnan(prior)]
    if len(prior) < min_history:
        return float("nan"), float("nan")
    return float(np.quantile(prior, lo_q)), float(np.quantile(prior, hi_q))


def compute_cuts(v_arr: np.ndarray, lo_q: float = 1.0 / 3, hi_q: float = 2.0 / 3,
                 min_history: int = MIN_TERCILE_HISTORY) -> tuple[np.ndarray, np.ndarray]:
    """Compute per-session (lo, hi) tercile cuts for ALL indices using v_arr[:i] only.

    This is the SAME call path the main pipeline uses (via _compute_terciles); tests
    exercise this helper to verify PIT-safe cut construction (G1 / M1). The second
    argument to tercile_cuts MUST be `i` (not i+1): an include-t mutant is what
    test_pipeline_cut_unchanged_when_v_prior_only is built to catch.

    Returns two arrays of length len(v) where entry [i] is the cut for index i.
    """
    n = len(v_arr)
    cut_low = np.full(n, np.nan)
    cut_high = np.full(n, np.nan)
    for i in range(n):
        cl, ch = tercile_cuts(v_arr, i, lo_q=lo_q, hi_q=hi_q, min_history=min_history)
        cut_low[i] = cl
        cut_high[i] = ch
    return cut_low, cut_high


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _host_provenance() -> dict:
    """Seat-host interpreter and library versions (round-4 HOST+COMPLETION)."""
    def _ver(name: str) -> str | None:
        try:
            mod = __import__(name)
            return str(getattr(mod, "__version__", None))
        except Exception:
            return None
    return {
        "hostname": platform.node(),
        "python": sys.version.split()[0],
        "python_path": sys.executable,
        "pandas": _ver("pandas"),
        "numpy": _ver("numpy"),
        "pyarrow": _ver("pyarrow"),
        "scipy": _ver("scipy"),
        "pytest": _ver("pytest"),
    }


def positive_control_drifts(cs_std: float, n_sectors: int | None = None) -> np.ndarray:
    """Fixed sector-specific drift vector for the E6/G3 positive control.

    np.linspace(cs_std, -cs_std, n) has std ≈ 0.632·cs_std; rescale so
    np.std(drifts, ddof=0) == cs_std exactly (G3 (i) / M2).
    """
    n = len(SECTOR_ETFS) if n_sectors is None else int(n_sectors)
    drifts = np.linspace(cs_std, -cs_std, n)
    sd = float(np.std(drifts, ddof=0))
    assert sd > 0, "drifts std is zero — cs_std is zero?"
    drifts = drifts * (cs_std / sd)
    return drifts


def cohen_kappa(y: pd.Series, x: pd.Series) -> float:
    """Cohen's kappa for two binary 0/1 (or bool) series."""
    a = y.astype(bool).to_numpy()
    b = x.astype(bool).to_numpy()
    m = np.isfinite(a) & np.isfinite(b)
    a = a[m]; b = b[m]
    if len(a) == 0:
        return float("nan")
    po = float((a == b).mean())
    p1 = float(a.mean()); p2 = float(b.mean())
    pe = p1 * p2 + (1 - p1) * (1 - p2)
    if pe == 1.0:
        return float("nan")
    return (po - pe) / (1.0 - pe)


def era_split(d: pd.Timestamp) -> str:
    if d.year <= 2009:
        return "<=2009"
    if d.year <= 2019:
        return "2010-2019"
    return "2020-2026"


# ─────────────────────── data loaders ───────────────────────
def _read_close(path: Path) -> pd.Series:
    df = pd.read_parquet(path)
    s = df["close"] if "close" in df.columns else df.iloc[:, 0]
    s = pd.Series(s.to_numpy(), index=pd.DatetimeIndex(pd.to_datetime(df.index)).normalize(),
                  name=path.stem).sort_index()
    return s[~s.index.duplicated(keep="last")].astype(float)


def load_sector_panel() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (closes on SPY calendar with ffill<=5, availability mask)."""
    spy = _read_close(YAHOO / "SPY.parquet")
    master = spy.index
    sector_closes = pd.DataFrame(index=master)
    available = pd.DataFrame(index=master, columns=SECTOR_ETFS, dtype=bool)
    for t in SECTOR_ETFS:
        p = YAHOO / f"{t}.parquet"
        s = _read_close(p)
        s2 = s.reindex(master).ffill(limit=5)
        sector_closes[t] = s2
        first = s.index[0]
        avail_mask = pd.Series(False, index=master)
        for d in master:
            if d < first:
                continue
            n = (s.index <= d).sum()
            if n >= LAG:
                avail_mask.loc[d] = True
        available[t] = avail_mask
    return sector_closes, available.astype(bool)


def load_breadth(master: pd.DatetimeIndex) -> pd.Series:
    rsp = _read_close(YAHOO / "RSP.parquet").reindex(master).ffill(limit=5)
    return rsp


def load_real_rate(master: pd.DatetimeIndex) -> pd.Series:
    df = pd.read_parquet(FRED / "DFII10.parquet")
    s = df["us10y_real"]
    s = pd.Series(s.to_numpy(), index=pd.DatetimeIndex(pd.to_datetime(df.index)).normalize(),
                  name="us10y_real").sort_index()
    return s.reindex(master).ffill(limit=5)


# ─────────────────────── core construction ───────────────────────
def _spearman_per_row_exact(rank_t: np.ndarray, rank_lag: np.ndarray,
                            common: np.ndarray) -> np.ndarray:
    """Exact Spearman over the common subset: re-rank within the common mask and
    Pearson-correlate those ranks. Average ties. Drops rows where the common subset
    is < MIN_COMMON. NaN where the denominator is zero.
    """
    out = np.full(len(rank_t), np.nan)
    for i in range(len(rank_t)):
        m = common[i] & np.isfinite(rank_t[i]) & np.isfinite(rank_lag[i])
        n = int(m.sum())
        if n < MIN_COMMON:
            continue
        a = rank_t[i][m]
        b = rank_lag[i][m]
        # Re-rank within the common subset with average ties (preferred per R7)
        a_rank = pd.Series(a).rank(method="average").to_numpy()
        b_rank = pd.Series(b).rank(method="average").to_numpy()
        am = a_rank - a_rank.mean()
        bm = b_rank - b_rank.mean()
        den = np.sqrt((am * am).sum() * (bm * bm).sum())
        if den <= 0:
            continue
        out[i] = float((am * bm).sum() / den)
    return out


def build_rotation_state_daily(shift: int = DEFAULT_SHIFT) -> pd.DataFrame:
    """Build the daily rotation-state table.

    Parameters
    ----------
    shift : int
        Number of sessions to forward-shift the value/label series before export.
        Default 1 enforces PIT safety (exported row t = unshifted computation at t-1).
        Tests use shift=0 to prove leak-detection power.
    """
    master = pd.DatetimeIndex(pd.read_parquet(YAHOO / "SPY.parquet").index).normalize()
    master = master[~master.duplicated(keep="last")]
    sectors, avail = load_sector_panel()
    spy = _read_close(YAHOO / "SPY.parquet").reindex(master).ffill(limit=5)
    rsp = load_breadth(master)

    # 1. r21_sector
    ln21 = np.log(sectors / sectors.shift(LAG))
    ln21_spy = np.log(spy / spy.shift(LAG))
    r21 = ln21.sub(ln21_spy, axis=0)

    n_sec = avail.sum(axis=1).astype("Int64")

    # 2. cross-sectional rank: 1 = best (highest r21); method="average" breaks exact r21 ties
    rank = r21.rank(axis=1, method="average", ascending=False)

    # 3. LP(t) = exact Spearman(rank_t, rank_{t-21}) over the COMMON subset
    rank_lag = rank.shift(LAG)
    common = avail & avail.shift(LAG).fillna(False)
    lp = pd.Series(_spearman_per_row_exact(rank.to_numpy(), rank_lag.to_numpy(),
                                            common.to_numpy()),
                   index=rank.index, name="LP")
    rotation_speed = (1.0 - lp).rename("rotation_speed")

    # 4. retention = |top3(t) ∩ top3(t-21)| / 3 over the FULL available set at each date
    def _top3_set(row: pd.Series) -> set:
        valid = row.dropna()
        if len(valid) < 3:
            return set()
        return set(valid.nsmallest(3).index)

    top3_t = rank.apply(_top3_set, axis=1)
    top3_lag = rank_lag.apply(_top3_set, axis=1)
    retention = pd.Series(
        [len(t & l) / 3.0 if (t and l) else np.nan for t, l in zip(top3_t, top3_lag)],
        index=rank.index, name="retention",
    )

    # 5. breadth_spread
    breadth_spread = (np.log(rsp / rsp.shift(LAG)) - ln21_spy).rename("breadth_spread")

    # 6. participation_share
    pos = (r21 > 0) & avail
    part_share = pos.sum(axis=1) / avail.sum(axis=1).replace(0, np.nan)
    part_share.name = "participation_share"

    # 7. dfii_impulse
    real = load_real_rate(master)
    dfii_impulse = (real - real.shift(LAG)).rename("dfii_impulse")

    raw = pd.DataFrame({
        "LP": lp,
        "retention": retention,
        "rotation_speed": rotation_speed,
        "breadth_spread": breadth_spread,
        "participation_share": part_share,
        "dfii_impulse": dfii_impulse,
        "n_sectors": n_sec,
    })

    # 8. Terciles via compute_cuts() — same call path the tests exercise (G1)
    for var, col, lo_q, hi_q, lo_label, hi_label in [
        ("LP", "rotation_tercile", 1.0 / 3, 2.0 / 3, "fast", "persistent"),
        ("breadth_spread", "breadth_tercile", 1.0 / 3, 2.0 / 3, "narrow", "broad"),
        ("dfii_impulse", "dfii_tercile", 1.0 / 3, 2.0 / 3, "falling", "rising"),
    ]:
        v = raw[var]
        v_arr = v.to_numpy()
        cut_low, cut_high = compute_cuts(v_arr, lo_q=lo_q, hi_q=hi_q,
                                         min_history=MIN_TERCILE_HISTORY)
        cut_low_s = pd.Series(cut_low, index=v.index)
        cut_high_s = pd.Series(cut_high, index=v.index)
        label = pd.Series(np.where(v < cut_low_s, lo_label,
                            np.where(v > cut_high_s, hi_label, "mid")),
                          index=v.index, dtype=object)
        # Where cuts are NaN, replace label with NaN
        label = label.where(~cut_low_s.isna() & ~cut_high_s.isna(), other=np.nan)
        raw[col] = label

    # 9. one-session shift (or any shift requested for power checks)
    out = raw.shift(shift)
    out.index.name = "date"
    cols = ["LP", "retention", "rotation_speed", "rotation_tercile",
            "breadth_spread", "breadth_tercile", "participation_share",
            "dfii_impulse", "dfii_tercile", "n_sectors"]
    out = out[cols]
    # Trim to first date where LP is computable
    lp_first = out["LP"].dropna().index
    if len(lp_first) > 0:
        first_lp = lp_first[0]
        out = out.loc[first_lp:]
    return out


def build_rotation_cuts(shift: int = DEFAULT_SHIFT) -> pd.DataFrame:
    """Build the per-session cut-pair sidecar (LP, breadth, dfii) at the same shift as
    the main state table. One row per date with lo/hi columns for each variable.

    The cuts are taken from the unshifted pipeline call (shift=0), then shifted by
    `shift` so they align with the main state table's date semantics.
    """
    master, lp, breadth_spread, dfii_impulse = _unshifted_value_arrays()

    cuts = pd.DataFrame(index=master)
    for var, s in [("LP", lp), ("breadth_spread", breadth_spread),
                   ("dfii_impulse", dfii_impulse)]:
        cl, ch = compute_cuts(s.to_numpy())
        cuts[f"{var}_cut_lo"] = cl
        cuts[f"{var}_cut_hi"] = ch

    cuts = cuts.shift(shift)
    cuts.index.name = "date"
    # Trim to match the state table: the state trims to the first date where the
    # SHIFTED LP series is non-NaN, which equals the first unshifted-LP-computable
    # date plus shift business days.
    shifted_lp = lp.shift(shift)
    lp_first = shifted_lp.dropna().index
    if len(lp_first) > 0:
        cuts = cuts.loc[lp_first[0]:]
    return cuts


def _unshifted_value_arrays() -> tuple[pd.DatetimeIndex, pd.Series, pd.Series, pd.Series]:
    """Compute and return (master_index, lp, breadth_spread, dfii_impulse) at their
    unshifted, untrimmed values — exactly the arrays the pipeline feeds into
    compute_cuts. Used by tests to compare against the sidecar.
    """
    master = pd.DatetimeIndex(pd.read_parquet(YAHOO / "SPY.parquet").index).normalize()
    master = master[~master.duplicated(keep="last")]
    sectors, avail = load_sector_panel()
    spy = _read_close(YAHOO / "SPY.parquet").reindex(master).ffill(limit=5)
    rsp = load_breadth(master)

    ln21 = np.log(sectors / sectors.shift(LAG))
    ln21_spy = np.log(spy / spy.shift(LAG))
    breadth_spread = (np.log(rsp / rsp.shift(LAG)) - ln21_spy)
    real = load_real_rate(master)
    dfii_impulse = (real - real.shift(LAG))

    rank = (ln21.sub(ln21_spy, axis=0)).rank(axis=1, method="average", ascending=False)
    rank_lag = rank.shift(LAG)
    common = avail & avail.shift(LAG).fillna(False)
    lp = pd.Series(_spearman_per_row_exact(rank.to_numpy(), rank_lag.to_numpy(),
                                            common.to_numpy()),
                   index=rank.index, name="LP")
    return master, lp, breadth_spread, dfii_impulse


# ─────────────────────── agreement metrics ───────────────────────
def build_agreement(state: pd.DataFrame) -> dict:
    regime = pd.read_parquet(REGIME)
    regime.index = pd.DatetimeIndex(pd.to_datetime(regime.index)).normalize()
    regime = regime[~regime.index.duplicated(keep="last")].sort_index()
    j_raw = state.join(regime[["flag_rotation_persistence", "transition_state", "pit_class"]],
                        how="inner")
    j_used = j_raw.dropna(subset=["rotation_tercile", "flag_rotation_persistence"])

    rot = j_used["rotation_tercile"].astype(str)
    flag = j_used["flag_rotation_persistence"].astype(bool)

    # (a) contingency rotation_tercile × flag_rotation_persistence
    contingency_flag = {}
    for rt in ["fast", "mid", "persistent"]:
        contingency_flag[rt] = {}
        for f in [True, False]:
            contingency_flag[rt][str(f)] = int(((rot == rt) & (flag == f)).sum())

    # (b) Cohen's kappa — spec wording: (rotation_tercile == "persistent") vs flag == True
    persistent_bin = (rot == "persistent").astype(int)
    flag_bin = flag.astype(int)
    kappa_persistent = cohen_kappa(persistent_bin, flag_bin)
    # Masterplan §5.3 alternative: (rotation_tercile == "fast") vs flag == True
    fast_bin = (rot == "fast").astype(int)
    kappa_fast = cohen_kappa(fast_bin, flag_bin)

    era_n = {}
    kappa_by_era_persistent = {}
    kappa_by_era_fast = {}
    for era in ["<=2009", "2010-2019", "2020-2026"]:
        sub = j_used[j_used.index.to_series().apply(era_split) == era]
        era_n[era] = int(len(sub))
        if len(sub) == 0:
            kappa_by_era_persistent[era] = None
            kappa_by_era_fast[era] = None
            continue
        sub_rot = sub["rotation_tercile"].astype(str)
        sub_flag = sub["flag_rotation_persistence"].astype(bool)
        kappa_by_era_persistent[era] = cohen_kappa((sub_rot == "persistent").astype(int),
                                                   sub_flag.astype(int))
        kappa_by_era_fast[era] = cohen_kappa((sub_rot == "fast").astype(int),
                                             sub_flag.astype(int))

    # (c) contingency rotation_tercile × transition_state
    ts = j_used["transition_state"].astype(str).fillna("NA")
    cats = sorted(ts.unique().tolist())
    contingency_transition = {}
    for rt in ["fast", "mid", "persistent"]:
        contingency_transition[rt] = {}
        for c in cats:
            contingency_transition[rt][c] = int(((rot == rt) & (ts == c)).sum())

    # (d) share of joined rows by pit_class, by era
    pit = j_used["pit_class"].astype(str).fillna("NA")
    pit_share_by_era = {}
    for era in ["<=2009", "2010-2019", "2020-2026"]:
        sub_era = j_used[j_used.index.to_series().apply(era_split) == era]
        if len(sub_era) == 0:
            pit_share_by_era[era] = {}
            continue
        s = sub_era["pit_class"].astype(str).fillna("NA")
        vc = s.value_counts(normalize=True)
        pit_share_by_era[era] = {k: round(float(v), 4) for k, v in vc.items()}

    join_end_date = j_used.index.max().strftime("%Y-%m-%d") if len(j_used) else None
    return {
        "contingency_flag": contingency_flag,
        "contingency_transition": contingency_transition,
        "kappa_persistent": round(float(kappa_persistent), 4) if np.isfinite(kappa_persistent) else None,
        "kappa_fast": round(float(kappa_fast), 4) if np.isfinite(kappa_fast) else None,
        "kappa_overall": round(float(kappa_persistent), 4) if np.isfinite(kappa_persistent) else None,
        "kappa_by_era": {
            era: {
                "persistent": round(float(kappa_by_era_persistent[era]), 4)
                if kappa_by_era_persistent[era] is not None and np.isfinite(kappa_by_era_persistent[era]) else None,
                "fast": round(float(kappa_by_era_fast[era]), 4)
                if kappa_by_era_fast[era] is not None and np.isfinite(kappa_by_era_fast[era]) else None,
                "n": era_n[era],
            }
            for era in ["<=2009", "2010-2019", "2020-2026"]
        },
        "pit_class_share_by_era": pit_share_by_era,
        "n_joined_raw": int(len(j_raw)),
        "n_joined_used": int(len(j_used)),
        "n_dropped_nan_tercile": int(len(j_raw) - len(j_used)),
        "join_end_date": join_end_date,
        "era_n": era_n,
    }


# ─────────────────────── positive controls ───────────────────────
def _lp_autocorr(lp: pd.Series, lag: int) -> float:
    """Pearson corr(LP(t), LP(t-lag)) over all non-NaN pairs."""
    valid = lp.dropna()
    pairs = pd.DataFrame({"t": valid, "lag": valid.shift(lag)}).dropna()
    if len(pairs) < 2:
        return float("nan")
    return float(pairs["t"].corr(pairs["lag"]))


def run_controls(state: pd.DataFrame) -> dict:
    lp = state["LP"]

    # (a) AR(1) lag 21
    ar1 = _lp_autocorr(lp, LAG)
    ar1_pass = bool(ar1 > 0.5)

    # (b) window means — use the EXPORTED (shifted) LP series per spec
    win_means = {}
    fast_share = {}
    win_n = {}
    for name, wins in [("fast", WINDOWS_FAST), ("persistent", WINDOWS_PERSISTENT)]:
        for start, end in wins:
            sub = lp.loc[start:end].dropna()
            tag = f"{name}:{start}..{end}"
            win_means[tag] = round(float(sub.mean()), 4) if len(sub) else None
            sub_full = state.loc[start:end]
            win_n[tag] = {
                "n_sessions": int(len(sub_full)),
                "n_months": int(sub_full.index.to_period("M").nunique()) if len(sub_full) else 0,
            }
            fast_share[tag] = round(float((state["rotation_tercile"].loc[start:end] == "fast").mean()), 4)

    mean_fast = float(np.nanmean([win_means[k] for k in win_means if k.startswith("fast")]))
    mean_persist = float(np.nanmean([win_means[k] for k in win_means if k.startswith("persistent")]))
    mean_overall = float(lp.dropna().mean())
    direction_pass = bool(mean_fast < mean_persist)

    # LP autocorrelation profile (description only — does not change verdicts)
    acorr = {f"lag_{k}": round(_lp_autocorr(lp, k), 4) for k in (1, 5, 10, 21, 42, 63)}

    status = "PASS" if (ar1_pass and direction_pass) else "BROKEN"
    return {
        "ar1_lag21": round(ar1, 4),
        "ar1_pass": ar1_pass,
        "mean_LP_fast_windows": round(mean_fast, 4),
        "mean_LP_persistent_windows": round(mean_persist, 4),
        "mean_LP_overall": round(mean_overall, 4),
        "window_means": win_means,
        "fast_share_by_window": fast_share,
        "window_n": win_n,
        "direction_pass": direction_pass,
        "lp_autocorr_profile": acorr,
        "status": status,
    }


# ─────────────────────── calibrated control (E6 sensitivity, G2/G3 round-3) ─────
def _estimate_sim_scales() -> tuple[float, float, pd.DatetimeIndex, pd.DataFrame]:
    """Estimate (cs_std_median, idio_std_median) from the observed r21 panel.

    cs_std_median: median over sessions of cross-sectional std of r21.
    idio_std_median: median over sessions of cross-sectional std of residuals,
        where residuals are demeaned BOTH by the session CS mean AND by each
        sector's full-sample mean (a pre-declated distinct quantity per G3).
    Also returns the SPY session calendar and the observed r21 panel aligned to
    the same calendar (NaN outside each sector's availability window).
    """
    sectors_df, avail = load_sector_panel()
    spy = _read_close(YAHOO / "SPY.parquet")
    master = spy.index
    spy_r = spy.reindex(master).ffill(limit=5)
    ln21 = np.log(sectors_df / sectors_df.shift(LAG))
    ln21_spy = np.log(spy_r / spy_r.shift(LAG))
    r21 = ln21.sub(ln21_spy, axis=0)
    # Mask sectors to NaN outside their availability window so the panel reflects
    # the OBSERVED date-by-sector availability (XLRE/XLC NaN before their first dates).
    r21_masked = r21.where(avail.astype(float).reindex(master).fillna(False).astype(bool))
    cs_std = r21.std(axis=1, skipna=True).dropna()
    cs_mean = r21.mean(axis=1, skipna=True)
    idio_cs_only = r21.sub(cs_mean, axis=0)
    # G3: distinct quantity — also remove each sector's full-sample mean
    sector_full_mean = r21.mean(axis=0, skipna=True)
    idio = idio_cs_only.sub(sector_full_mean, axis=1)
    idio_std = idio.std(axis=1, skipna=True).dropna()
    return float(cs_std.median()), float(idio_std.median()), master, r21_masked


def _simulate_lp_series(r21_arr: np.ndarray, n_avail: np.ndarray | None = None) -> pd.Series:
    """Given a (n_sessions, n_sectors) array of r21 (and optional availability mask),
    compute the LP series exactly as run.py does, returning a Series aligned to the
    synthetic index.

    If n_avail is given, sectors are treated as unavailable (NaN) where the mask
    is False at that session.
    """
    n = r21_arr.shape[0]
    idx = pd.RangeIndex(n)
    df = pd.DataFrame(r21_arr, index=idx, columns=SECTOR_ETFS)
    if n_avail is not None:
        df = df.where(n_avail.astype(bool))
    rank = df.rank(axis=1, method="average", ascending=False)
    rank_lag = rank.shift(LAG)
    if n_avail is not None:
        avail = pd.DataFrame(n_avail, index=idx, columns=SECTOR_ETFS).astype(bool)
    else:
        avail = pd.DataFrame(True, index=idx, columns=SECTOR_ETFS)
    common = avail & avail.shift(LAG).fillna(False)
    lp_arr = _spearman_per_row_exact(rank.to_numpy(), rank_lag.to_numpy(),
                                     common.to_numpy())
    return pd.Series(lp_arr, index=idx)


def run_calibrated_control(state: pd.DataFrame, seed: int = 20261004,
                            n_sims: int = 200) -> dict:
    """Calibrated control sensitivity (E6 — seat addition, G2/G3 round-3 fixes).

    Pre-declared: the > 0.5 lag-21 gate was uncalibrated. This sensitivity
    builds two reference panels and reports where the OBSERVED lag-21 LP
    autocorrelation sits relative to them.

    (a) POSITIVE CONTROL — n_sims panels simulated on the observed session
        index and availability mask (6,942 sessions, 11 sectors, XLRE NaN
        before 2015-11-05 and XLC NaN before 2018-07-18). Each sector's r21
        = fixed sector-specific drift (ordering fixed for the whole sample,
        spread rescaled to equal the observed cross-sectional std of r21)
        plus iid N(0, idio_std) noise per session. Compute LP exactly as in
        run.py; report median, 5th and 95th percentile of LP autocorrelation
        at lags 5 / 10 / 21. (The noise is iid per session, so lag-5/10
        autocorrelation is approximately zero by construction; this control
        calibrates only the lag-21 persistence level.)

    (b) NULL — n_sims panels where the OBSERVED r21 panel and availability
        mask are permuted within non-overlapping 21-session blocks. For each
        block draw ONE permutation of the sector identities with
        rng = np.random.default_rng(20261004) and apply that same permutation
        to every row of the block (r21 and availability columns permuted
        jointly, so within-block persistence is preserved and cross-block
        persistence is destroyed). Compute LP exactly as in run.py; report
        median, 5th and 95th percentile of LP autocorrelation at lags
        5 / 10 / 21.

    Pre-declared rule: CALIBRATED_PASS iff observed lag-21 autocorrelation
    > null 95th percentile AND >= 0.5 × positive-control median; else
    CALIBRATED_FAIL. controls.status stays BROKEN regardless.
    """
    cs_std, idio_std, master, r21_observed = _estimate_sim_scales()
    n_sectors = len(SECTOR_ETFS)

    # Trim observed panel to the same dates the LP-computable table uses
    # (first LP-computable date = the first date the exported parquet starts).
    lp_first_idx = state.index[0]
    obs_panel = r21_observed.loc[lp_first_idx:].copy()
    avail_master = obs_panel.notna().to_numpy()
    # Replace NaN with 0 only for the simulation math (rank/r21 still NaN elsewhere
    # via the mask), so the panel has the right shape for permutation.
    r21_arr = obs_panel.fillna(0.0).to_numpy(dtype=float)
    n_sessions = r21_arr.shape[0]

    rng = np.random.default_rng(seed)

    # POSITIVE CONTROL: sector-specific drift ordered d_1 > ... > d_n with
    # np.std(drifts, ddof=0) == cs_std (rescaled from linspace — see G3 (i) / M2).
    drifts = positive_control_drifts(cs_std, n_sectors)

    pos_lag5, pos_lag10, pos_lag21 = [], [], []
    for _ in range(n_sims):
        noise = rng.normal(0.0, idio_std, size=(n_sessions, n_sectors))
        r21_sim = drifts[None, :] + noise
        lp = _simulate_lp_series(r21_sim, n_avail=avail_master).dropna()
        if len(lp) < 64:
            continue
        pos_lag5.append(float(_lp_autocorr(lp, 5)))
        pos_lag10.append(float(_lp_autocorr(lp, 10)))
        pos_lag21.append(float(_lp_autocorr(lp, 21)))

    # NULL (G2): per non-overlapping 21-session block, draw ONE permutation of the
    # sector identities and apply that same permutation to every row of the block
    # (r21 and availability permuted jointly).
    null_lag5, null_lag10, null_lag21 = [], [], []
    for _ in range(n_sims):
        r21_perm = r21_arr.copy()
        avail_perm = avail_master.copy()
        for start in range(0, n_sessions, LAG):
            end = min(start + LAG, n_sessions)
            perm = rng.permutation(n_sectors)
            r21_perm[start:end] = r21_perm[start:end][:, perm]
            avail_perm[start:end] = avail_perm[start:end][:, perm]
        lp = _simulate_lp_series(r21_perm, n_avail=avail_perm).dropna()
        if len(lp) < 64:
            continue
        null_lag5.append(float(_lp_autocorr(lp, 5)))
        null_lag10.append(float(_lp_autocorr(lp, 10)))
        null_lag21.append(float(_lp_autocorr(lp, 21)))

    pos21 = np.array(pos_lag21, dtype=float)
    null21 = np.array(null_lag21, dtype=float)
    observed = float(_lp_autocorr(state["LP"], LAG))

    pos_median = float(np.median(pos21)) if len(pos21) else float("nan")
    pos_p5 = float(np.percentile(pos21, 5)) if len(pos21) else float("nan")
    pos_p95 = float(np.percentile(pos21, 95)) if len(pos21) else float("nan")
    null_p95 = float(np.percentile(null21, 95)) if len(null21) else float("nan")
    null_median = float(np.median(null21)) if len(null21) else float("nan")
    null_p5 = float(np.percentile(null21, 5)) if len(null21) else float("nan")
    pos_median_lag5 = float(np.median(pos_lag5)) if pos_lag5 else float("nan")
    pos_median_lag10 = float(np.median(pos_lag10)) if pos_lag10 else float("nan")
    null_median_lag5 = float(np.median(null_lag5)) if null_lag5 else float("nan")
    null_median_lag10 = float(np.median(null_lag10)) if null_lag10 else float("nan")

    rule = ("CALIBRATED_PASS iff observed lag-21 autocorr > null 95th percentile "
            "AND >= 0.5 * positive-control median; else CALIBRATED_FAIL.")
    calibrated_pass = bool(
        np.isfinite(null_p95) and np.isfinite(pos_median)
        and observed > null_p95 and observed >= 0.5 * pos_median
    )

    return {
        "seed": seed,
        "n_sims": n_sims,
        "scales": {"cs_std_median": round(cs_std, 6), "idio_std_median": round(idio_std, 6)},
        "panel": {
            "n_sessions": int(n_sessions),
            "n_sectors": int(n_sectors),
            "first_date": lp_first_idx.strftime("%Y-%m-%d"),
        },
        "observed_lag21": round(observed, 4),
        "positive_control": {
            "n_used": int(len(pos21)),
            "median_lag5": round(pos_median_lag5, 4),
            "median_lag10": round(pos_median_lag10, 4),
            "median_lag21": round(pos_median, 4),
            "p5_lag21": round(pos_p5, 4),
            "p95_lag21": round(pos_p95, 4),
        },
        "null": {
            "n_used": int(len(null21)),
            "median_lag5": round(null_median_lag5, 4),
            "median_lag10": round(null_median_lag10, 4),
            "median_lag21": round(null_median, 4),
            "p5_lag21": round(null_p5, 4),
            "p95_lag21": round(null_p95, 4),
            "draws": [float(x) for x in null21],
            "description": ("NULL: per non-overlapping 21-session block of the OBSERVED "
                            "r21 panel and availability mask, draw ONE permutation of the "
                            "sector identities (seed 20261004) and apply that permutation to "
                            "every row of the block (r21 and availability permuted jointly). "
                            "Within-block persistence is preserved; cross-block persistence "
                            "is destroyed."),
        },
        "rule": rule,
        "calibrated_status": "CALIBRATED_PASS" if calibrated_pass else "CALIBRATED_FAIL",
    }


# Round-2/3 frozen calibrated-control table values. Round 4 may add draws
# but must not move any of these rounded numbers.
FROZEN_CALIBRATED = {
    "observed_lag21": -0.0404,
    "positive_control.median_lag21": 0.2533,
    "positive_control.p5_lag21": 0.2366,
    "positive_control.p95_lag21": 0.2711,
    "positive_control.median_lag5": 0.0303,
    "positive_control.median_lag10": 0.0319,
    "null.median_lag21": 0.0017,
    "null.p5_lag21": -0.0436,
    "null.p95_lag21": 0.0498,
    "null.median_lag5": 0.3269,
    "null.median_lag10": 0.097,
    "calibrated_status": "CALIBRATED_FAIL",
    "scales.cs_std_median": 0.030204,
    "scales.idio_std_median": 0.030158,
}


def _nested_get(d: dict, dotted: str):
    cur = d
    for part in dotted.split("."):
        cur = cur[part]
    return cur


def _assert_calibrated_frozen(calibrated: dict) -> None:
    """STOP if a frozen calibrated-control table value moved (round-4 freeze)."""
    mismatches = []
    for key, expected in FROZEN_CALIBRATED.items():
        got = _nested_get(calibrated, key)
        if isinstance(expected, float):
            if abs(float(got) - expected) > 1e-9 and round(float(got), 4) != round(expected, 4):
                mismatches.append(f"{key}: got {got} vs frozen {expected}")
        else:
            if got != expected:
                mismatches.append(f"{key}: got {got!r} vs frozen {expected!r}")
    if mismatches:
        raise SystemExit(
            "calibrated_control frozen values moved — STOP (round-4 freeze):\n  "
            + "\n  ".join(mismatches)
        )


# ─────────────────────── RESULT.md writer ───────────────────────
def write_result_md(state: pd.DataFrame, controls: dict, agreement: dict,
                    tercile_counts: dict, tests_summary: str, calibrated: dict,
                    *, failing_tests: list[str] | None = None) -> None:
    n_sessions = int(len(state))
    first_date = state.index[0].strftime("%Y-%m-%d")
    last_date = state.index[-1].strftime("%Y-%m-%d")

    md = []
    md.append("# Lane C1 — Rotation / leadership-persistence state variable (PIT-safe)\n")
    md.append("**Data class.** The price stores are FINAL-VINTAGE (as observed today, not "
              "point-in-time) and the universes are SURVIVOR-SELECTED (current membership only). "
              "Sector ETF closes are from `data/yahoo/`, breadth and SPY from the same store, the "
              "10y TIPS real yield from `data/fred/DFII10.parquet`, and the incumbent PIT regime "
              "store from `data/regime/regime_v2_pit.parquet`.\n")
    md.append("**ANSWER FIRST.** Lane C1 is **BROKEN** on its AR(1) lag-21 control: "
              f"`corr(LP(t), LP(t-21)) = {controls['ar1_lag21']:.4f}` "
              "(PASS threshold > 0.5). The direction control PASSES "
              f"(`mean_LP_fast = {controls['mean_LP_fast_windows']:.4f}` < "
              f"`mean_LP_persistent = {controls['mean_LP_persistent_windows']:.4f}`). "
              "Per spec §POSITIVE CONTROLS, the table is still exported and "
              "`controls.status = \"BROKEN\"` is recorded honestly in `result.json`. "
              "The BROKEN verdict is pre-declared (reviewer-verified on identical input vintage); "
              "this lane does not re-tune to recover the AR(1) gate.\n")

    md.append("## Summary\n")
    md.append(f"- Table: `rotation_state_daily.parquet` — {n_sessions:,} rows, "
              f"{first_date} → {last_date} (first date LP is computable → last SPY session)")
    md.append("- Sidecar: `rotation_cuts_daily.parquet` — per-session (lo, hi) tercile cuts the pipeline used")
    md.append("- One-session PIT shift applied: exported row at date `t` = unshifted computation at `t-1`")
    md.append("- Expanding-window terciles for LP, breadth_spread, dfii_impulse (≥ 756 prior non-NaN sessions gate)")
    md.append("- Forward-fill of missing sector / FRED closes limited to ≤ 5 sessions")
    md.append(f"- Repo head: `{REPO_HEAD}`\n")

    md.append("## Positive controls (the gating numbers)\n")
    md.append("| Control | Value | PASS / FAIL | Threshold |")
    md.append("|---|---|---|---|")
    md.append(f"| AR(1) lag 21 of LP | **{controls['ar1_lag21']:.4f}** | "
              f"**{'PASS' if controls['ar1_pass'] else 'FAIL'}** | > 0.5 |")
    md.append(f"| mean LP, fast windows (F) | **{controls['mean_LP_fast_windows']:.4f}** | — | — |")
    md.append(f"| mean LP, persistent windows (P) | **{controls['mean_LP_persistent_windows']:.4f}** | — | — |")
    md.append(f"| Direction: `mean(F) < mean(P)` | {controls['mean_LP_fast_windows']:.4f} < "
              f"{controls['mean_LP_persistent_windows']:.4f} | "
              f"**{'PASS' if controls['direction_pass'] else 'FAIL'}** | strict < |")
    md.append(f"| mean LP, overall | {controls['mean_LP_overall']:.4f} | — | — |")
    md.append(f"| **controls.status** | **{controls['status']}** | — | PASS only if both pass |\n")

    md.append("### Window-level diagnostics (sessions / months / mean LP / fast-share)\n")
    md.append("| Window | Class | n_sessions | n_months | mean LP | share labelled \"fast\" |")
    md.append("|---|---|---:|---:|---:|---:|")
    for tag, m in controls["window_means"].items():
        name, rng = tag.split(":")
        cls = name
        n_info = controls["window_n"][tag]
        md.append(f"| {rng} | {cls} | {n_info['n_sessions']} | {n_info['n_months']} | "
                  f"{m:.4f} | {controls['fast_share_by_window'][tag]:.4f} |")
    md.append("")

    md.append("### LP autocorrelation profile (description only)\n")
    md.append("| lag | corr(LP(t), LP(t-lag)) |")
    md.append("|---:|---:|")
    for k, v in controls["lp_autocorr_profile"].items():
        md.append(f"| {k.split('_')[1]} | {v:+.4f} |")
    md.append("")

    md.append("## Calibrated control (post-hoc sensitivity, added 2026-10-04 after the primary verdict was recorded)\n")
    pos = calibrated["positive_control"]
    nul = calibrated["null"]
    md.append(f"The pre-declared > 0.5 lag-21 gate was uncalibrated. The POSITIVE control "
              f"(fixed sector drift + iid per-session noise) shows that even with strong "
              f"fixed sector leadership, lag-21 LP autocorrelation only reaches a median of "
              f"**{pos['median_lag21']:+.4f}** — well below 0.5. This means the gate could not "
              f"have passed by construction, regardless of the real data. This sensitivity "
              f"positions the OBSERVED value between two reference panels built on the "
              f"observed {calibrated['panel']['n_sessions']:,}-session index and the "
              f"11-sector availability mask.\n")
    md.append("**Disclosure (G3):** the POSITIVE control noise is iid per session, so its "
              "lag-5 / lag-10 autocorrelation is ≈ 0 by construction. The control calibrates "
              "only the lag-21 persistence level, not the lag profile.\n")
    md.append(f"- **OBSERVED** lag-21 LP autocorrelation: "
              f"**{calibrated['observed_lag21']:+.4f}**")
    md.append(f"- **POSITIVE CONTROL** ({calibrated['n_sims']} sims, fixed sector drift with "
              f"`std(drifts) == cs_std = {calibrated['scales']['cs_std_median']:.6f}` + iid "
              f"N(0, idio_std = {calibrated['scales']['idio_std_median']:.6f}) noise per "
              f"session, simulated on the observed {calibrated['panel']['n_sessions']:,}-"
              f"session index and 11-sector availability mask): median lag-21 = "
              f"**{pos['median_lag21']:+.4f}** (5th pct = {pos['p5_lag21']:+.4f}, 95th pct = "
              f"{pos['p95_lag21']:+.4f}); median lag-5 = {pos['median_lag5']:+.4f}, median "
              f"lag-10 = {pos['median_lag10']:+.4f}")
    md.append(f"- **NULL** ({calibrated['n_sims']} sims): {nul['description']} 95th-pct "
              f"lag-21 = **{nul['p95_lag21']:+.4f}** (median = {nul['median_lag21']:+.4f}, "
              f"5th pct = {nul['p5_lag21']:+.4f}); median lag-5 = {nul['median_lag5']:+.4f}, "
              f"median lag-10 = {nul['median_lag10']:+.4f}")
    md.append(f"- **Pre-declared rule:** {calibrated['rule']}")
    md.append(f"- **Outcome:** **{calibrated['calibrated_status']}** "
              f"(observed {calibrated['observed_lag21']:+.4f} vs null p95 "
              f"{nul['p95_lag21']:+.4f}; positive-control 0.5×median = "
              f"{0.5 * pos['median_lag21']:+.4f}). controls.status remains BROKEN — "
              f"this sensitivity does not change the primary verdict.\n")

    md.append("## Agreement with incumbent PIT regime store (rotation_tercile × flag_rotation_persistence)\n")
    md.append(f"Raw inner join produced **{agreement['n_joined_raw']:,}** rows. "
              f"After dropping rows with NaN `rotation_tercile` (burn-in before the "
              f"first computable tercile), **{agreement['n_joined_used']:,}** rows remain "
              f"({agreement['n_dropped_nan_tercile']:,} dropped). The incumbent PIT regime "
              f"store ends on **{agreement['join_end_date']}**, so the join stops there even "
              f"though our exported table runs to {last_date}.\n")
    md.append("| rotation_tercile | flag=True | flag=False | row total |")
    md.append("|---|---:|---:|---:|")
    for rt in ["fast", "mid", "persistent"]:
        true_n = agreement["contingency_flag"][rt]["True"]
        false_n = agreement["contingency_flag"][rt]["False"]
        md.append(f"| {rt} | {true_n} | {false_n} | {true_n + false_n} |")
    md.append("")

    md.append("Cohen's κ — binary input: rotation_tercile vs flag_rotation_persistence:\n")
    md.append("| Era | n | κ (persistent) | κ (fast, per masterplan §5.3) |")
    md.append("|---|---:|---:|---:|")
    md.append(f"| Overall | {agreement['n_joined_used']:,} | "
              f"{agreement['kappa_persistent']:+.4f} | {agreement['kappa_fast']:+.4f} |")
    for era in ["<=2009", "2010-2019", "2020-2026"]:
        n_e = agreement["era_n"][era]
        kp = agreement["kappa_by_era"][era]["persistent"]
        kf = agreement["kappa_by_era"][era]["fast"]
        kp_str = f"{kp:+.4f}" if kp is not None else "—"
        kf_str = f"{kf:+.4f}" if kf is not None else "—"
        md.append(f"| {era} | {n_e:,} | {kp_str} | {kf_str} |")
    md.append("")
    md.append("Both binaries are reported because the masterplan §5.3 defines κ on "
              "`rotation_tercile == \"fast\"` while the spec wording uses `\"persistent\"`; "
              "the spec text governs the primary binary (`kappa_persistent`).\n")
    md.append("Agreement is near zero in every era — the incumbent `flag_rotation_persistence` "
              "is not aligned with our LP-based tercile. The two are different concepts: "
              "`flag_rotation_persistence` is a single-session flag from the regime cascade; "
              "our `rotation_tercile` is a relative-position label in an expanding window. The "
              "agreement is **reported**, not used to tune LP (per spec).\n")

    md.append("## Contingency: rotation_tercile × transition_state\n")
    cats = sorted({c for rt in agreement["contingency_transition"].values() for c in rt})
    header = "| rotation_tercile | " + " | ".join(cats) + " |"
    md.append(header)
    md.append("|" + "---|" * (len(cats) + 1))
    for rt in ["fast", "mid", "persistent"]:
        cells = " | ".join(str(agreement["contingency_transition"][rt].get(c, 0)) for c in cats)
        md.append(f"| {rt} | {cells} |")
    md.append("")

    md.append("## Joined-row composition by `pit_class` × era\n")
    md.append("| Era | pit_class composition | sessions |")
    md.append("|---|---|---:|")
    for era in ["<=2009", "2010-2019", "2020-2026"]:
        n_e = agreement["era_n"][era]
        comp = agreement["pit_class_share_by_era"][era]
        md.append(f"| {era} | {comp} | {n_e:,} |")
    md.append("")
    md.append("Pre-2020 the incumbent store reports all rows as `mixed`; the `pit_vintage` class "
              "only appears from 2020 onward. The pre-2020 share is therefore not informative "
              "about agreement.\n")

    md.append("## Tercile counts (after shift, non-NaN labels only)\n")
    md.append("| Variable | label | sessions |")
    md.append("|---|---|---:|")
    even_rot = tercile_counts["rotation"]["persistent"] + tercile_counts["rotation"]["mid"] + tercile_counts["rotation"]["fast"]
    even_share_rot = even_rot / 3
    for label in ["fast", "mid", "persistent"]:
        n = tercile_counts["rotation"].get(label, 0)
        md.append(f"| rotation | {label} | {n:,} |")
    even_breadth = tercile_counts["breadth"]["narrow"] + tercile_counts["breadth"]["broad"] + tercile_counts["breadth"]["mid"]
    even_share_breadth = even_breadth / 3
    for label in ["narrow", "mid", "broad"]:
        n = tercile_counts["breadth"].get(label, 0)
        md.append(f"| breadth | {label} | {n:,} |")
    even_dfii = tercile_counts["dfii"]["mid"] + tercile_counts["dfii"]["rising"] + tercile_counts["dfii"]["falling"]
    even_share_dfii = even_dfii / 3
    for label in ["falling", "mid", "rising"]:
        n = tercile_counts["dfii"].get(label, 0)
        md.append(f"| dfii | {label} | {n:,} |")
    md.append("")
    skew_breadth_narrow_pct = round((tercile_counts["breadth"]["narrow"] - even_share_breadth) / even_share_breadth * 100, 1)
    skew_dfii_falling_pct = round((tercile_counts["dfii"]["falling"] - even_share_dfii) / even_share_dfii * 100, 1)
    md.append(f"Rotation terciles are balanced (~33/33/33) as expected from expanding-window "
              f"quantiles; breadth is skewed — `narrow` ({tercile_counts['breadth']['narrow']:,}) "
              f"sits about **{skew_breadth_narrow_pct:+.1f}%** from an even share "
              f"({even_share_breadth:.0f}); dfii is skewed — `falling` "
              f"({tercile_counts['dfii']['falling']:,}) sits about **{skew_dfii_falling_pct:+.1f}%** "
              f"from an even share ({even_share_dfii:.0f}).\n")

    md.append("## Honest interpretation\n")
    md.append("The directional evidence (mean LP is lower in known fast-rotation windows than "
              "in known persistent-leadership windows) is consistent with the variable measuring "
              "something real about sector leadership persistence. The persistence-at-lag-21 test "
              "fails — LP is approximately white noise at a monthly lag. Any consumer that needs "
              "a slowly-evolving state should NOT rely on raw LP at lag 21; smoothing or a "
              "different lag would be needed. The agreement with `flag_rotation_persistence` is "
              "near zero in every era, so the two are not substitutes; if downstream wants "
              "\"rotation persistence\" it must pick one or fuse them deliberately.\n")

    md.append("## Deviations\n")
    for d in DEVIATIONS:
        md.append(f"- {d}")
    if not DEVIATIONS:
        md.append("- (none recorded beyond the declared items)")

    md.append("\n## Gaps\n")
    for g in GAPS:
        md.append(f"- {g}")

    md.append("\n## Provenance\n")
    prov = HOST_PROVENANCE or _host_provenance()
    md.append(f"- Host: `{prov.get('hostname')}` (seat host m2; this round 2026-10-04)")
    md.append(f"- python3: `{prov.get('python_path')}` {prov.get('python')}")
    md.append(f"- pandas {prov.get('pandas')} / numpy {prov.get('numpy')} / "
              f"pyarrow {prov.get('pyarrow')} / scipy {prov.get('scipy')} / "
              f"pytest {prov.get('pytest')}")
    md.append("- Frozen tables this round (unchanged): "
              f"`rotation_state_daily.parquet` sha256 `{FROZEN_STATE_SHA256}` ; "
              f"`rotation_cuts_daily.parquet` sha256 `{FROZEN_CUTS_SHA256}`.\n")

    md.append("\n## Tests\n")
    if MUTANT_POWER_DOC:
        md.append(MUTANT_POWER_DOC.rstrip() + "\n")
    else:
        md.append("Round-4 mutant/tamper power (scratch copies; clean tree afterwards). "
                  "Names are filled after the mutants are run.\n")
    if failing_tests:
        for ft in failing_tests:
            md.append(f"- `{ft}`")
        md.append("")
    md.append(f"```\n{tests_summary}\n```\n")

    OUT_RESULT_MD.write_text("\n".join(md))


# ─────────────────────── main ───────────────────────
GAPS: list[str] = []
DEVIATIONS: list[str] = []
REPO_HEAD: str = "(unknown)"
HOST_PROVENANCE: dict = {}
MUTANT_POWER_DOC: str = ""


def main():
    RESULTS.mkdir(parents=True, exist_ok=True)
    CODE.mkdir(parents=True, exist_ok=True)

    global REPO_HEAD
    REPO_HEAD = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO,
                                capture_output=True, text=True).stdout.strip()

    global HOST_PROVENANCE
    HOST_PROVENANCE = _host_provenance()

    skip_rebuild = os.environ.get("C1_SKIP_REBUILD") == "1"
    frozen_ok = (OUT_PARQUET.exists()
                 and _sha256_file(OUT_PARQUET) == FROZEN_STATE_SHA256
                 and OUT_CUTS_PARQUET.exists()
                 and _sha256_file(OUT_CUTS_PARQUET) == FROZEN_CUTS_SHA256)
    if skip_rebuild and frozen_ok:
        print("[C1] C1_SKIP_REBUILD: loading frozen rotation_state_daily.parquet "
              f"(sha256 {FROZEN_STATE_SHA256})", flush=True)
        state = pd.read_parquet(OUT_PARQUET)
    else:
        print("[C1] building rotation_state_daily…", flush=True)
        state = build_rotation_state_daily()
        state.to_parquet(OUT_PARQUET, engine="pyarrow", compression="zstd", index=True)
        print(f"[C1] wrote {OUT_PARQUET}", flush=True)
        got_state = _sha256_file(OUT_PARQUET)
        if got_state != FROZEN_STATE_SHA256:
            raise SystemExit(
                f"rotation_state_daily.parquet sha256 {got_state} moved from frozen "
                f"{FROZEN_STATE_SHA256} — STOP (round-4 freeze)"
            )
        print("[C1] building rotation_cuts_daily sidecar…", flush=True)
        cuts = build_rotation_cuts()
        cuts.to_parquet(OUT_CUTS_PARQUET, engine="pyarrow", compression="zstd", index=True)
        print(f"[C1] wrote {OUT_CUTS_PARQUET}  ({len(cuts):,} rows)", flush=True)
        got_cuts = _sha256_file(OUT_CUTS_PARQUET)
        if got_cuts != FROZEN_CUTS_SHA256:
            raise SystemExit(
                f"rotation_cuts_daily.parquet sha256 {got_cuts} moved from frozen "
                f"{FROZEN_CUTS_SHA256} — STOP (round-4 freeze)"
            )

    n_sessions = int(len(state))
    first_date = state.index[0].strftime("%Y-%m-%d")
    last_date = state.index[-1].strftime("%Y-%m-%d")
    print(f"[C1] rows={n_sessions}  first={first_date}  last={last_date}", flush=True)

    print("[C1] agreement…", flush=True)
    agreement = build_agreement(state)

    print("[C1] controls…", flush=True)
    controls = run_controls(state)

    print("[C1] calibrated control (E6 sensitivity, G2/G3 round-3, M4 draws)…", flush=True)
    reuse_cal = os.environ.get("C1_REUSE_CALIBRATED") == "1"
    prev_cal = None
    if reuse_cal and OUT_RESULT_JSON.exists():
        prev = json.loads(OUT_RESULT_JSON.read_text())
        prev_cal = prev.get("calibrated_control")
        if not (isinstance(prev_cal, dict) and prev_cal.get("null", {}).get("draws")):
            prev_cal = None
    if prev_cal is not None:
        calibrated = prev_cal
        print("[C1] C1_REUSE_CALIBRATED: keeping stored calibrated_control "
              f"(n_draws={len(calibrated['null']['draws'])})", flush=True)
    else:
        calibrated = run_calibrated_control(state)
        _assert_calibrated_frozen(calibrated)
    print(f"[C1] calibrated_status = {calibrated['calibrated_status']}", flush=True)

    tercile_counts = {}
    for var, col in [("rotation", "rotation_tercile"), ("breadth", "breadth_tercile"),
                     ("dfii", "dfii_tercile")]:
        vc = state[col].dropna().value_counts()
        tercile_counts[var] = {str(k): int(v) for k, v in vc.items()}

    # Final GAPS and DEVIATIONS (identical in RESULT.md and result.json — R6)
    gaps = [
        "AR(1) lag 21 control FAILED (value "
        f"{controls['ar1_lag21']:.4f} vs threshold 0.5) — see first paragraph.",
        f"The pit_class column reports `mixed` for 100% of pre-2020 joined rows; "
        "agreement statistics for those eras are not informative.",
        "Cohen's κ computed by hand per the spec (po, pe); no library reference for cross-check.",
    ]

    # G6 round-3: corrected wording — the lag profile difference relative to the reviewer's
    # pre-R7 values is ≤ 0.0003 (post-R7 vs reviewer's pre-R7). The 1e-4 tolerance applies to
    # recomputation from the exported parquet, which holds exactly.
    deviations = [
        "LP autocorrelation profile is reported for lags 1/5/10/21/42/63 as description only. "
        "Post-R7 exact Spearman re-rank shifts the lag-10/42/63 values by ≤ 0.0003 relative to "
        "the reviewer's pre-R7 values; the 1e-4 tolerance enforced by the test suite applies to "
        "recomputation from the exported parquet, which matches exactly. The BROKEN verdict on "
        "the lag-21 gate is unchanged.",
        "Masterplan §5.3 defines κ on rotation_tercile == \"fast\" while the spec text uses "
        "rotation_tercile == \"persistent\". Both kappas are emitted as kappa_persistent (primary, "
        "per spec) and kappa_fast (alt, per masterplan); the spec text governs the binary.",
    ]
    # M3 / G3: compare at 4-dp rounding (cs_std 0.030204 and idio_std 0.030158
    # agree at 4 dp = 0.0302). The previous 6-dp exact-equality check never fired.
    cs4 = round(float(calibrated["scales"]["cs_std_median"]), 4)
    idio4 = round(float(calibrated["scales"]["idio_std_median"]), 4)
    if cs4 == idio4:
        deviations.append(IDIO_CS_4DP_DEVIATION)

    tests_summary = "PENDING"

    GAPS.clear(); GAPS.extend(gaps)
    DEVIATIONS.clear(); DEVIATIONS.extend(deviations)

    write_result_md(state, controls, agreement, tercile_counts, tests_summary, calibrated,
                    failing_tests=None)
    print(f"[C1] wrote {OUT_RESULT_MD}", flush=True)

    result = {
        "lane": "C1",
        "status": controls["status"],
        "repo_head": REPO_HEAD,
        "data_class": {"vintage": "final", "universe": "sector ETFs, current list"},
        "n_sessions": n_sessions,
        "first_date": first_date,
        "last_date": last_date,
        "controls": controls,
        "calibrated_control": calibrated,
        "agreement": agreement,
        "tercile_counts": tercile_counts,
        # G7: store pass/skip/fail counts only (no wall time) so result.json sha256 is
        # reproducible given repo_head
        "tests_pass": 0,
        "tests_skip": 0,
        "tests_fail": 0,
        "gaps": gaps,
        "deviations": deviations,
        "provenance": {"host": HOST_PROVENANCE or _host_provenance()},
    }
    OUT_RESULT_JSON.write_text(json.dumps(result, indent=2, default=str))
    print(f"[C1] wrote {OUT_RESULT_JSON}", flush=True)
    return result


if __name__ == "__main__":
    main()