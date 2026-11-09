from __future__ import annotations

__doc__ = """RESEARCH REFERENCE — NOT WIRED. Q10 condition-adjusted off-exchange participation residual.

VERDICT: KEEP (research reference / explanatory calibration correction only — NOT an alpha
signal). Single preregistered holdout run 2026-10-09T09:41:35Z: 90% interval score improves
13.9% vs the incumbent median/MAD baseline (block-bootstrap 95% CI 7.8%..18.2%, block 20)
and 13.9% vs its empirical-quantile variant (CI 8.2%..18.2%); held-out 90% coverage 0.906
(CI 0.900..0.912) on 321 test sessions / 372 issuers (17 non-overlapping 20-session blocks).
Most of the gain is the leave-one-out market factor (ablation: 13.5%). No forward-return or
alpha content was tested or is claimed. Details:
research/quant_assessment_2026_10/Q10_conditional_offexchange_anomalies/VERDICT.md.
Only this docstring paragraph changed after the evaluated run (evaluated module sha256
5513dd006c66a312e39f2d1b3dfe980d4e9a223dccf1f754b87c76c1da391b8d); nothing in the
repository imports this module: it registers nothing, schedules nothing, gates nothing,
ranks nothing and emits no direction.

WHAT IT MEASURES
----------------
Daily off-exchange participation ``p = offex_shares / consolidated_shares`` (the same basis
as ``engine/darkpool_signals.py``) is described relative to a predictive distribution built
ONLY from information available at that session's cutoff:

  * the issuer's own trailing level (robust median of the empirical logit over the prior
    ``LEVEL_WINDOW`` valid sessions, current session excluded) — persistent liquidity
    structure;
  * a leave-one-out cross-sectional market factor for the same session (median deviation
    of every OTHER fully supported issuer from its own trailing level) — market-wide
    internalization / reporting shifts;
  * the issuer's same-session relative consolidated volume (log volume minus its trailing
    median) — event-day volume.

The residual is standardised by an issuer trailing robust scale shrunk toward the
session's pooled scale (empirical-Bayes partial pooling), inflated for location
uncertainty, and mapped through training-fitted empirical quantiles. Share counts are NOT
treated as Bernoulli trials: no binomial variance is used anywhere.

MEASUREMENT CONTRACT
--------------------
* ``p == 0`` and ``p == 1`` are VALID observations (empirical logit
  ``log((x + 0.5) / (v - x + 0.5))`` is finite at both ends).
* ``x > v`` (ratio above one), ``x < 0`` and ``v <= 0`` are INVALID measurements. They are
  never clipped into apparent valid values and never enter any trailing statistic.
* Rows before an issuer's last share-unit level break (the incumbent split rule,
  reimplemented here without importing the incumbent) are EXCLUDED_SPLIT unless a caller
  supplies an explicit exclusion mask (for example from a corporate-action owner).
* Thin issuers are pooled (``POOLED`` support, disclosed pooling weight) and issuers with
  fewer than ``LEVEL_MIN_OBS`` comparable sessions ABSTAIN.

HOUSE LAW
---------
FINRA short volume is not short interest or net buying; ATS/non-ATS is a venue/reporting
category, not owner intent. This module therefore emits no buy/sell direction, no
beneficial-owner inference and no fused score. Output is a descriptive residual with its
support and uncertainty, research tier only.
"""

import math
import warnings
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

RESEARCH_ONLY = True
VERSION = "q10.offex_conditional_residual.v1"

# ── frozen constants (PREREG.md §Model) ─────────────────────────────────────────
LEVEL_WINDOW = 252        # trailing valid sessions for the issuer level
LEVEL_MIN_OBS = 10        # below this the issuer ABSTAINS
FULL_SUPPORT_OBS = 40     # at/above: FULL support; between: POOLED
VOL_WINDOW = 60           # trailing valid sessions for the volume norm
VOL_MIN_OBS = 10
SCALE_WINDOW = 252        # trailing valid residuals for the issuer scale
SCALE_PRIOR_K = 40.0      # pseudo-observations of the pooled scale
MARKET_MIN_ISSUERS = 30   # contributors required for the market factor
HUBER_C = 1.345
MAD_SCALE = 1.4826
BREAK_WINDOW = 20
BREAK_FACTOR = 1.8
QUANTILE_LEVELS = (0.005, 0.01, 0.025, 0.05, 0.10, 0.25, 0.5, 0.75, 0.90, 0.95, 0.975, 0.99, 0.995)
MAX_ROWS = 5_000_000
MAX_ISSUERS = 20_000

# status codes (distinct on purpose: unknown, invalid, excluded and abstained never merge)
VALID = "VALID"
MISSING = "MISSING"
INVALID_RATIO = "INVALID_RATIO"
INVALID_DENOMINATOR = "INVALID_DENOMINATOR"
EXCLUDED_SPLIT = "EXCLUDED_SPLIT"
ABSTAIN_NO_SUPPORT = "ABSTAIN_NO_SUPPORT"
ABSTAIN_NO_MARKET = "ABSTAIN_NO_MARKET"
SCORED_FULL = "SCORED_FULL"
SCORED_POOLED = "SCORED_POOLED"

OUTPUT_COLUMNS = (
    "date", "issuer", "p", "status", "n_level", "pool_weight", "market_factor",
    "n_market", "rel_volume", "deviation", "loc_logit", "scale", "residual_u", "pit",
    "lo90", "hi90", "lo98", "hi98", "lo50", "hi50",
)


# ── measurement ────────────────────────────────────────────────────────────────

def classify_participation(offex_shares, consolidated_shares):
    """Return ``(p, status)`` arrays. Never clips: invalid rows get ``p = NaN``."""
    x = np.asarray(offex_shares, dtype="float64")
    v = np.asarray(consolidated_shares, dtype="float64")
    if x.shape != v.shape:
        raise ValueError("shape mismatch")
    if x.size > MAX_ROWS:
        raise ValueError("input exceeds MAX_ROWS")
    status = np.full(x.shape, VALID, dtype=object)
    p = np.full(x.shape, np.nan)
    miss = ~np.isfinite(x) | ~np.isfinite(v)
    bad_den = ~miss & (v <= 0)
    bad_ratio = ~miss & ~bad_den & ((x < 0) | (x > v))
    ok = ~miss & ~bad_den & ~bad_ratio
    status[miss] = MISSING
    status[bad_den] = INVALID_DENOMINATOR
    status[bad_ratio] = INVALID_RATIO
    p[ok] = x[ok] / v[ok]
    return p, status


def empirical_logit(offex_shares, consolidated_shares):
    """Cox empirical logit; finite at p = 0 and p = 1, NaN for invalid rows."""
    x = np.asarray(offex_shares, dtype="float64")
    v = np.asarray(consolidated_shares, dtype="float64")
    p, status = classify_participation(x, v)
    out = np.full(x.shape, np.nan)
    ok = status == VALID
    out[ok] = np.log((x[ok] + 0.5) / (v[ok] - x[ok] + 0.5))
    return out


def inverse_empirical_logit(z, consolidated_shares):
    """Map an empirical-logit BOUND back to the participation scale (bounds clip to [0,1];
    observations are never passed through here)."""
    z = np.asarray(z, dtype="float64")
    v = np.asarray(consolidated_shares, dtype="float64")
    with np.errstate(over="ignore", invalid="ignore"):
        s = 1.0 / (1.0 + np.exp(-z))
        p = ((v + 1.0) * s - 0.5) / v
    return np.clip(p, 0.0, 1.0)


# ── split / unit-break rule (reimplements the incumbent rule; pure) ─────────────

def last_level_break(values, *, window: int = BREAK_WINDOW, factor: float = BREAK_FACTOR):
    """Position (in the given non-NaN series) of the last sustained level break, or None.

    Same arithmetic as the incumbent ``share_break_index``: rolling median of ``window``
    sessions (min periods max(5, window//2)) compared with the value ``window`` sessions
    earlier; a ratio at or beyond ``factor`` either way is a break.
    """
    s = pd.Series(np.asarray(values, dtype="float64")).dropna().reset_index(drop=True)
    if len(s) < window * 2 + 1:
        return None
    med = s.rolling(window, min_periods=max(5, window // 2)).median().to_numpy()
    pre = med[: len(s) - window]
    post = med[window:]
    with np.errstate(divide="ignore", invalid="ignore"):
        ratio = post / pre
    ok = np.isfinite(pre) & np.isfinite(post) & (pre > 0) & (post != 0)
    hit = ok & ((ratio >= factor) | (ratio <= 1.0 / factor))
    idx = np.flatnonzero(hit)
    return int(idx[-1] + window) if idx.size else None


def unit_consistent_mask(p_valid, *, window: int = BREAK_WINDOW, factor: float = BREAK_FACTOR):
    """Boolean mask over a per-issuer chronological array: True at/after the last break.

    NaN entries are ignored for detection and stay False in the mask only if they precede
    the break.
    """
    a = np.asarray(p_valid, dtype="float64")
    pos = np.flatnonzero(np.isfinite(a))
    mask = np.ones(a.shape, dtype=bool)
    b = last_level_break(a[pos], window=window, factor=factor)
    if b is not None:
        mask[: pos[b]] = False
    return mask


def known_event_mask(n_rows: int, event_positions) -> np.ndarray:
    """Exclusion mask from caller-supplied corporate-action positions (e.g. a Q03 owner):
    rows strictly before the latest event are in different share units → False."""
    mask = np.ones(int(n_rows), dtype=bool)
    ev = [int(e) for e in (event_positions or []) if 0 <= int(e) < n_rows]
    if ev:
        mask[: max(ev)] = False
    return mask


# ── trailing robust statistics over prior VALID observations ───────────────────

def trailing_stats(x, window: int, min_obs: int):
    """For every position t: median, MAD, mean, std(ddof=0) and count of the last
    ``window`` non-NaN observations strictly BEFORE t. Below ``min_obs`` → NaN stats."""
    a = np.asarray(x, dtype="float64")
    n = a.size
    valid = np.isfinite(a)
    c = a[valid]
    nv = c.size
    out = {k: np.full(n, np.nan) for k in ("median", "mad", "mean", "std")}
    out["count"] = np.zeros(n, dtype=int)
    if n == 0:
        return out
    k_before = np.cumsum(valid) - valid.astype(int)       # valid obs strictly before t
    padded = np.concatenate([np.full(window, np.nan), c])
    win = np.lib.stride_tricks.sliding_window_view(padded, window)  # nv+1 windows
    cnt = np.isfinite(win).sum(axis=1)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        med = np.nanmedian(win, axis=1)
        mad = np.nanmedian(np.abs(win - med[:, None]), axis=1)
        mean = np.nanmean(win, axis=1)
        std = np.nanstd(win, axis=1)
    enough = cnt >= min_obs
    for name, arr in (("median", med), ("mad", mad), ("mean", mean), ("std", std)):
        arr = np.where(enough, arr, np.nan)
        out[name] = arr[k_before]
    out["count"] = cnt[k_before]
    assert nv + 1 == win.shape[0]
    return out


def incumbent_baseline(p, *, window: int = 252, min_obs: int = 40):
    """The incumbent median/MAD construction (current excluded) on a per-issuer array.

    Returns (center, scale, count): scale = 1.4826·MAD, falling back to σ when MAD is 0
    (exactly as ``trailing_z``); NaN when unsupported or σ is 0.
    """
    st = trailing_stats(p, window, min_obs)
    mad_scale = st["mad"] * MAD_SCALE
    use_mad = np.isfinite(mad_scale) & (mad_scale > 0)
    center = np.where(use_mad, st["median"], st["mean"])
    scale = np.where(use_mad, mad_scale, st["std"])
    scale = np.where(np.isfinite(scale) & (scale > 0), scale, np.nan)
    center = np.where(np.isfinite(scale), center, np.nan)
    return center, scale, st["count"]


# ── leave-one-out cross-sectional median ───────────────────────────────────────

def loo_median(values, contributes):
    """Exact leave-one-out median per element over the contributing set.

    Non-contributors receive the median of all contributors (nothing to leave out).
    Returns (loo_med, n_used) where n_used is the number of values the median used.
    """
    v = np.asarray(values, dtype="float64")
    cmask = np.asarray(contributes, dtype=bool) & np.isfinite(v)
    out = np.full(v.shape, np.nan)
    n_used = np.zeros(v.shape, dtype=int)
    s_idx = np.flatnonzero(cmask)
    m = s_idx.size
    if m == 0:
        return out, n_used
    order = np.argsort(v[s_idx], kind="mergesort")
    srt = v[s_idx][order]
    full_med = float(np.median(srt))
    out[~cmask] = full_med
    n_used[~cmask] = m
    if m == 1:
        n_used[s_idx] = 0
        return out, n_used
    rank = np.empty(m, dtype=int)
    rank[order] = np.arange(m)
    r = m - 1                                    # remaining count
    lo_pos, hi_pos = (r - 1) // 2, r // 2        # positions in the remaining array

    def at(pos, removed):
        return np.where(pos < removed, srt[np.minimum(pos, m - 1)], srt[np.minimum(pos + 1, m - 1)])

    loo = 0.5 * (at(lo_pos, rank) + at(hi_pos, rank))
    out[s_idx] = loo
    n_used[s_idx] = r
    return out, n_used


# ── robust regression ──────────────────────────────────────────────────────────

def huber_regression(X, y, *, c: float = HUBER_C, max_iter: int = 50, tol: float = 1e-8):
    """Huber M-estimate by IRLS with MAD-based residual scale. Returns coefficients."""
    X = np.asarray(X, dtype="float64")
    y = np.asarray(y, dtype="float64")
    beta = np.linalg.lstsq(X, y, rcond=None)[0]
    for _ in range(max_iter):
        r = y - X @ beta
        s = MAD_SCALE * float(np.median(np.abs(r - np.median(r))))
        if not s > 0:
            break
        a = np.abs(r / s)
        w = np.where(a <= c, 1.0, c / np.maximum(a, 1e-12))
        sw = np.sqrt(w)
        new = np.linalg.lstsq(X * sw[:, None], y * sw, rcond=None)[0]
        if np.max(np.abs(new - beta)) < tol:
            beta = new
            break
        beta = new
    return beta


# ── scoring ────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class ModelParams:
    coef: tuple                      # (intercept, market, rel_volume, rel_volume_pos)
    quantiles: tuple                 # values at QUANTILE_LEVELS of the training residual_u
    pooled_scale: float              # training global pooled scale fallback
    use_market: bool = True
    n_train_rows: int = 0
    version: str = VERSION
    extras: dict = field(default_factory=dict)


def _prepare(panel: pd.DataFrame, excluded=None) -> pd.DataFrame:
    need = {"date", "issuer", "offex_shares", "cons_shares"}
    missing = need - set(panel.columns)
    if missing:
        raise ValueError(f"panel missing columns: {sorted(missing)}")
    if len(panel) > MAX_ROWS:
        raise ValueError("panel exceeds MAX_ROWS")
    df = panel[list(need)].copy()
    if excluded is not None:
        df["_excluded"] = np.asarray(excluded, dtype=bool)
    if df.duplicated(["date", "issuer"]).any():
        raise ValueError("duplicate (date, issuer) rows")
    if df["issuer"].nunique() > MAX_ISSUERS:
        raise ValueError("too many issuers")
    df = df.sort_values(["issuer", "date"], kind="mergesort").reset_index(drop=True)
    p, status = classify_participation(df["offex_shares"].to_numpy(), df["cons_shares"].to_numpy())
    df["p"] = p
    df["status"] = status
    df["zlogit"] = empirical_logit(df["offex_shares"].to_numpy(), df["cons_shares"].to_numpy())
    df["logv"] = np.where(df["cons_shares"].to_numpy(dtype="float64") > 0,
                          np.log(np.maximum(df["cons_shares"].to_numpy(dtype="float64"), 1e-300)), np.nan)
    df["n_level"] = 0
    df["L"] = np.nan
    df["rel_volume"] = np.nan
    for _, idx in df.groupby("issuer", sort=False).indices.items():
        sub_status = df["status"].to_numpy()[idx]
        pv = np.where(sub_status == VALID, df["p"].to_numpy()[idx], np.nan)
        if "_excluded" in df.columns:
            keep = ~df["_excluded"].to_numpy()[idx]
        else:
            keep = unit_consistent_mask(pv)
        st_arr = sub_status.copy()
        st_arr[(st_arr == VALID) & ~keep] = EXCLUDED_SPLIT
        df.loc[idx, "status"] = st_arr
        usable = st_arr == VALID
        z = np.where(usable, df["zlogit"].to_numpy()[idx], np.nan)
        lv = np.where(usable, df["logv"].to_numpy()[idx], np.nan)
        lvl = trailing_stats(z, LEVEL_WINDOW, LEVEL_MIN_OBS)
        vol = trailing_stats(lv, VOL_WINDOW, VOL_MIN_OBS)
        df.loc[idx, "L"] = lvl["median"]
        df.loc[idx, "n_level"] = lvl["count"]
        df.loc[idx, "rel_volume"] = lv - vol["median"]
    usable = df["status"].to_numpy() == VALID
    df["d"] = np.where(usable, df["zlogit"] - df["L"], np.nan)
    # market factor: leave-one-out median of d over FULL-support issuers on the session
    df["market_factor"] = np.nan
    df["n_market"] = 0
    contrib_all = usable & (df["n_level"].to_numpy() >= FULL_SUPPORT_OBS) & np.isfinite(df["d"].to_numpy())
    dvals = df["d"].to_numpy()
    mf = np.full(len(df), np.nan)
    nm = np.zeros(len(df), dtype=int)
    for _, idx in df.groupby("date", sort=False).indices.items():
        lm, nu = loo_median(dvals[idx], contrib_all[idx])
        mf[idx] = lm
        nm[idx] = nu
    df["market_factor"] = mf
    df["n_market"] = nm
    return df


def _design(df: pd.DataFrame, use_market: bool) -> np.ndarray:
    m = df["market_factor"].to_numpy() if use_market else np.zeros(len(df))
    v = df["rel_volume"].to_numpy()
    return np.column_stack([np.ones(len(df)), m, v, np.maximum(v, 0.0)])


def _scale_and_score(df: pd.DataFrame, coef, pooled_fallback: float, use_market: bool):
    X = _design(df, use_market)
    usable = (df["status"].to_numpy() == VALID) & (df["n_level"].to_numpy() >= LEVEL_MIN_OBS)
    has_market = df["n_market"].to_numpy() >= MARKET_MIN_ISSUERS if use_market else np.ones(len(df), bool)
    has_vol = np.isfinite(df["rel_volume"].to_numpy())
    model_ok = usable & has_market & has_vol & np.isfinite(df["d"].to_numpy())
    pred_d = X @ np.asarray(coef, dtype="float64")
    e = np.where(model_ok, df["d"].to_numpy() - pred_d, np.nan)
    df["_e"] = e
    s_own = np.full(len(df), np.nan)
    n_s = np.zeros(len(df), dtype=int)
    for _, idx in df.groupby("issuer", sort=False).indices.items():
        st = trailing_stats(e[idx], SCALE_WINDOW, 1)
        s_own[idx] = MAD_SCALE * st["mad"]
        n_s[idx] = st["count"]
    df["_s_own"] = s_own
    df["_n_s"] = n_s
    # pooled scale per session = median own scale over issuers with >= FULL_SUPPORT_OBS residuals
    pooled = np.full(len(df), np.nan)
    full_s = (n_s >= FULL_SUPPORT_OBS) & np.isfinite(s_own) & (s_own > 0)
    for _, idx in df.groupby("date", sort=False).indices.items():
        vals = s_own[idx][full_s[idx]]
        pooled[idx] = float(np.median(vals)) if vals.size >= MARKET_MIN_ISSUERS else pooled_fallback
    k = SCALE_PRIOR_K
    s_own_f = np.where(np.isfinite(s_own) & (n_s >= 2), s_own, 0.0)
    n_eff = np.where(np.isfinite(s_own) & (n_s >= 2), n_s, 0)
    s_post = np.sqrt((n_eff * s_own_f ** 2 + k * pooled ** 2) / (n_eff + k))
    n_level = df["n_level"].to_numpy().astype("float64")
    with np.errstate(divide="ignore", invalid="ignore"):
        infl = np.sqrt(1.0 + math.pi / (2.0 * np.maximum(n_level, 1.0)))
    scale = s_post * infl
    u = np.where(model_ok, e / scale, np.nan)
    loc = df["L"].to_numpy() + pred_d
    pool_weight = k / (n_eff + k)
    return model_ok, loc, scale, u, pool_weight


def fit_conditional_model(train_panel: pd.DataFrame, *, excluded=None, use_market: bool = True) -> ModelParams:
    """Fit coefficients and residual quantiles on TRAINING rows only."""
    df = _prepare(train_panel, excluded)
    X = _design(df, use_market)
    rows = ((df["status"].to_numpy() == VALID)
            & (df["n_level"].to_numpy() >= FULL_SUPPORT_OBS)
            & np.isfinite(df["rel_volume"].to_numpy())
            & np.isfinite(df["d"].to_numpy()))
    if use_market:
        rows &= df["n_market"].to_numpy() >= MARKET_MIN_ISSUERS
    if rows.sum() < 50:
        raise ValueError("insufficient training support")
    coef = huber_regression(X[rows], df["d"].to_numpy()[rows])
    # global pooled fallback scale from training residuals
    e = df["d"].to_numpy()[rows] - X[rows] @ coef
    pooled_fallback = MAD_SCALE * float(np.median(np.abs(e - np.median(e))))
    ok, loc, scale, u, pw = _scale_and_score(df, coef, pooled_fallback, use_market)
    full = ok & (df["n_level"].to_numpy() >= FULL_SUPPORT_OBS) & np.isfinite(u)
    q = np.quantile(u[full], QUANTILE_LEVELS)
    return ModelParams(coef=tuple(float(c) for c in coef), quantiles=tuple(float(x) for x in q),
                       pooled_scale=pooled_fallback, use_market=use_market,
                       n_train_rows=int(full.sum()))


def _pit(u, params: ModelParams):
    lv = np.asarray(QUANTILE_LEVELS)
    qv = np.asarray(params.quantiles)
    return np.interp(u, qv, lv, left=0.0, right=1.0)


def _q(params: ModelParams, level: float) -> float:
    return float(params.quantiles[QUANTILE_LEVELS.index(level)])


def score_panel(panel: pd.DataFrame, params: ModelParams, *, excluded=None) -> pd.DataFrame:
    """Score every row. Pure: returns a new frame with OUTPUT_COLUMNS."""
    df = _prepare(panel, excluded)
    ok, loc, scale, u, pw = _scale_and_score(df, params.coef, params.pooled_scale, params.use_market)
    status = df["status"].to_numpy().copy()
    n_level = df["n_level"].to_numpy()
    valid = status == VALID
    status[valid & (n_level < LEVEL_MIN_OBS)] = ABSTAIN_NO_SUPPORT
    nomkt = valid & (n_level >= LEVEL_MIN_OBS) & ~ok
    status[nomkt] = ABSTAIN_NO_MARKET
    status[ok & (n_level >= FULL_SUPPORT_OBS)] = SCORED_FULL
    status[ok & (n_level < FULL_SUPPORT_OBS)] = SCORED_POOLED
    cons = df["cons_shares"].to_numpy(dtype="float64")
    out = pd.DataFrame({
        "date": df["date"].to_numpy(), "issuer": df["issuer"].to_numpy(),
        "p": df["p"].to_numpy(), "status": status, "n_level": n_level,
        "pool_weight": np.where(ok, pw, np.nan),
        "market_factor": np.where(ok, df["market_factor"].to_numpy(), np.nan),
        "n_market": df["n_market"].to_numpy(),
        "rel_volume": np.where(ok, df["rel_volume"].to_numpy(), np.nan),
        "deviation": df["d"].to_numpy(),
        "loc_logit": np.where(ok, loc, np.nan), "scale": np.where(ok, scale, np.nan),
        "residual_u": u, "pit": np.where(ok, _pit(u, params), np.nan),
    })
    for name, a in (("90", 0.10), ("98", 0.02), ("50", 0.50)):
        lo = loc + scale * _q(params, round(a / 2, 4))
        hi = loc + scale * _q(params, round(1 - a / 2, 4))
        out["lo" + name] = np.where(ok, inverse_empirical_logit(lo, cons), np.nan)
        out["hi" + name] = np.where(ok, inverse_empirical_logit(hi, cons), np.nan)
    return out[list(OUTPUT_COLUMNS)]


# ── evaluation helpers ─────────────────────────────────────────────────────────

def interval_score(lo, hi, y, alpha: float):
    """Gneiting–Raftery interval score (lower is better; proper for central intervals)."""
    lo = np.asarray(lo, dtype="float64")
    hi = np.asarray(hi, dtype="float64")
    y = np.asarray(y, dtype="float64")
    return (hi - lo) + (2.0 / alpha) * np.maximum(lo - y, 0.0) + (2.0 / alpha) * np.maximum(y - hi, 0.0)


def moving_block_bootstrap(series_list, *, block: int, reps: int, seed: int, stat):
    """Moving-block bootstrap over aligned per-session series. ``stat`` maps the list of
    resampled arrays to a float. Returns an array of ``reps`` statistics."""
    arrs = [np.asarray(s, dtype="float64") for s in series_list]
    n = arrs[0].size
    if any(a.size != n for a in arrs):
        raise ValueError("series must be aligned")
    if block < 1 or n < block:
        raise ValueError("block length invalid for series length")
    rng = np.random.default_rng(seed)
    n_blocks = int(math.ceil(n / block))
    starts_max = n - block + 1
    out = np.empty(int(reps))
    offs = np.arange(block)
    for r in range(int(reps)):
        st = rng.integers(0, starts_max, size=n_blocks)
        ix = (st[:, None] + offs[None, :]).ravel()[:n]
        out[r] = stat([a[ix] for a in arrs])
    return out
