"""Portfolio factor-exposure engine — the "you own 8 names but ONE factor bet" lens.

The dashboard scores each stock in isolation. This module answers the *book-level*
question a discretionary trader actually has: across everything I hold, what am I
really long? It regresses each stock's daily return on a set of macro/style factor
returns and ships the per-ticker beta vector; the watchlist then aggregates those
betas against the user's actual position weights (client-side) into portfolio-level
exposures, per-factor risk contribution, a concentration ("one bet") read, and
factor shocks.

THE METHOD MATTERS. The naive version (the one ChatGPT's table implies) is a
*univariate* beta per factor — regress the stock on SPY, then separately on QQQ,
then on BTC, … But SPY/QQQ/BTC are 0.6–0.9 correlated, so each univariate beta
re-counts the same market move and the "exposures" sum to nonsense. Instead we
estimate a MULTIVARIATE model: the factors are orthogonalized in economic priority
order (market first, then style, then macro), so every reported beta is the
*marginal* exposure beyond the higher-priority factors. The factors are mutually
orthogonal on that common window. Missing stock observations can
break orthogonality on a ticker's fitted sample, so its coefficients use a joint
centered fit in that fixed basis. `raw_betas()` keeps univariate raw betas too: they
are the right number for a single-factor *shock* ("if oil +10%, the book moves …",
a total derivative) and they let the Phase-0 quantify the double-counting the
orthogonal set removes.

This is MEASUREMENT, not prediction — a thermometer, not a signal. So it does NOT go
through the IC/FDR/DSR alpha gauntlet; the honest gate (scripts/factor_exposure_phase0.py)
is whether the betas are STABLE out-of-sample and whether aggregation improves each
factor's persistence. That benefit is measured separately for each factor; it must
not be assumed for every secondary beta. The confidence metadata records the result.

ADDITIVE / leaf — nothing in the scoring path imports it. China is intentionally
absent as a *ticker* universe: the only onshore proxy we cache (510300.SS) trades on
a different clock than US names, so a same-day beta is timezone-contaminated; add it
when an FXI/MCHI (US-hours) proxy is collected. (An FXI-based `china` FACTOR is present
— it is US-hours.) HK/CN/CA cash equities are likewise unmodeled here and read
"unmodeled" in the watchlist; they need their own *clock-safe* factor models (own
proxies on their own session closes) — chartered in the WRI masterplan, not built here.

Crypto IS in the exposable universe: BTC-USD/ETH-USD (the coins) plus IBIT/ETHA/COIN
(spot-crypto ETFs + the Coinbase equity) get shipped betas like SPY/QQQ, so a user
holding them sees a real book contribution. Independent crypto variation can leave
idiosyncratic risk; BTC itself is a factor and can be exactly spanned by this model.
Timezone note: crypto trades ~24/7 while the
factor returns are US-session closes, so there is some async — but BTC-USD is ALREADY
the `btc` FACTOR, computed exactly this way (daily pct_change of the same close series),
so exposing BTC-USD/ETH-USD as tickers is CONSISTENT with existing treatment, not a new
source of contamination. This is why crypto is buildable now while HK/CN cash equities
(no US-hours proxy) are not.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np
import pandas as pd

from engine.equity_factors import _closes, _names_sectors
from lib import config, store

log = logging.getLogger(__name__)

TRADING_YEAR = 252

NOTE = ("Multivariate market, style and macro factor betas, "
        "orthogonalized so each beta is the MARGINAL exposure — not the double-counted "
        "univariate kind. A risk/exposure lens. Interpret secondary betas with each "
        "factor's historical confidence and scope.")


@dataclass(frozen=True)
class Factor:
    key: str
    group: str
    sid: str
    col: str
    sign: int      # +1, or -1 to orient (none needed today; kept for symmetry)
    label: str
    note: str


# Economic priority order: market is THE factor, then the style tilts that are highly
# collinear with it (so they must be orthogonalized AFTER market), then the macro
# factors. Orthogonalization peels each factor against all the ones above it, so the
# reported beta is "exposure beyond market / style / …". US-hours, tradeable proxies
# only — see the module docstring on the deliberate China gap.
FACTORS: list[Factor] = [
    Factor("mkt", "yahoo", "SPY", "close", 1,
           "Market", "S&P 500 (SPY) — broad beta, the dominant risk."),
    Factor("growth", "yahoo", "QQQ", "close", 1,
           "Growth / Tech", "Nasdaq-100 (QQQ) beyond market — long-duration / tech tilt."),
    Factor("size", "yahoo", "IWM", "close", 1,
           "Small-cap", "Russell 2000 (IWM) beyond market — small-cap / domestic-cyclical tilt."),
    Factor("rates", "yahoo", "TLT", "close", 1,
           "Rates (duration)", "20y+ Treasuries (TLT) — rises when long yields fall; + beta = bond-like / long-duration."),
    Factor("usd", "yahoo", "DX-Y.NYB", "close", 1,
           "US Dollar", "Dollar index (DXY) — + beta = benefits from a stronger dollar (rare for equities)."),
    Factor("oil", "commodity", "signals_oil", "close", 1,
           "Oil / energy", "WTI crude (26y daily) — + beta = energy / inflation-shock exposure."),
    Factor("china", "yahoo", "FXI", "close", 1,
           "China", "FXI (China large-cap, US-hours) beyond global beta — China/HK growth exposure."),
    Factor("btc", "yahoo", "BTC-USD", "close", 1,
           "Bitcoin / crypto", "BTC-USD — + beta = crypto / high-risk-appetite exposure."),
    Factor("gold", "yahoo", "GC=F", "close", 1,
           "Gold", "Gold futures (GC=F) — + beta = gold / metals & miners exposure; closes the "
           "metals coverage gap so miners read as the gold bets they are, not low-R² idiosyncratics."),
    # NB: a high-yield-credit factor (HYG) was evaluated and DROPPED — in an equity universe its
    # loaders were an incoherent low-beta mix (redundant with market + rates), i.e. it fit noise
    # rather than a clean credit dimension. Keep the observable set small and clean (overfit guardrail).
]

FACTOR_ORDER = [f.key for f in FACTORS]
FACTOR_BY_KEY = {f.key: f for f in FACTORS}

# Historical Phase-0 evidence: reports/factor-exposure-validation-2026-11-11.md.
# 20 evaluated monthly dates, 2024-10-31..2026-05-29; factor data ends 2026-09-25.
# `persist` is mean cross-sectional rank persistence from 252 finite factor
# observations to the next 63 (overlapping forward windows, not independent trials).
# Qualitative UI tiers/scopes retain their relative interpretation, not automatic
# cutoffs or a promise of future stability. single = individual display; book =
# basket-qualified; low = weak historical persistence, shown as context.
FACTOR_CONFIDENCE = {
    "mkt":    {"tier": "high",   "scope": "single", "persist": 0.676},
    "size":   {"tier": "high",   "scope": "single", "persist": 0.527},
    "growth": {"tier": "high",   "scope": "single", "persist": 0.448},
    "rates":  {"tier": "medium", "scope": "single", "persist": 0.324},
    "oil":    {"tier": "medium", "scope": "book",   "persist": 0.219},  # K=1: .231; K=40: .456
    "china":  {"tier": "low",    "scope": "low",    "persist": 0.132},
    "usd":    {"tier": "low",    "scope": "low",    "persist": 0.093},
    "btc":    {"tier": "low",    "scope": "low",    "persist": 0.039},
    "gold":   {"tier": "low",    "scope": "low",    "persist": 0.103},  # measured, still weak
}


def _cfg() -> dict:
    base = {"window_d": 252, "min_obs": 126, "min_factor_obs": 252,
            "max_abs_beta": 5.0, "top_n_idio": 12,
            "stress_window_d": 756, "stress_quantile": 0.25}
    return {**base, **(config.load().get("engine", {}).get("factor_exposure", {}) or {})}


# Common ETFs to also expose betas for — many watchlists hold these, and the model
# reads them cleanly (a holding of SPY should show market beta ~1). Only the ones we
# already cache in data/yahoo are used; the rest are skipped gracefully. Labelled so
# the client shows a readable name + an "ETF" sector tag.
ETF_NAMES = {
    "SPY": "S&P 500", "QQQ": "Nasdaq 100", "IWM": "Russell 2000", "RSP": "S&P 500 equal-wt",
    "IJH": "S&P MidCap 400", "IWD": "Russell 1000 Value", "IWF": "Russell 1000 Growth",
    "MTUM": "US Momentum", "QUAL": "US Quality", "SPHB": "S&P High Beta",
    "SPLV": "S&P Low Vol", "USMV": "US Min Vol", "SMH": "Semiconductors",
    "XLB": "Materials", "XLC": "Communication Svcs", "XLE": "Energy", "XLF": "Financials",
    "XLI": "Industrials", "XLK": "Technology", "XLP": "Consumer Staples",
    "XLRE": "Real Estate", "XLU": "Utilities", "XLV": "Health Care", "XLY": "Consumer Disc",
    "TLT": "20y+ Treasuries", "IEF": "7-10y Treasuries", "TIP": "TIPS",
    "HYG": "High-yield credit", "LQD": "IG credit", "EMB": "EM bonds",
    "FXI": "China large-cap",
}

# Crypto book — the coins themselves (BTC-USD/ETH-USD, already the `btc` FACTOR series)
# plus the spot-crypto ETFs and Coinbase equity many watchlists actually hold. Exposed
# so a holder sees a real book contribution instead of an "unmodeled" chip; tagged with
# a "Crypto" sector (not "ETF") so the client groups the sleeve honestly. These load
# btc-heavy; a self-factor tracker can have zero residual risk when caps do not bind.
# Only the cached ones are used (GBTC is NOT cached → skipped gracefully, like the rest);
# see the module docstring on why this is clock-consistent with the existing btc factor.
CRYPTO_NAMES = {
    "BTC-USD": "Bitcoin", "ETH-USD": "Ethereum",
    "IBIT": "iShares Bitcoin (spot)", "ETHA": "iShares Ethereum (spot)",
    "COIN": "Coinbase",
}

# Union universe read by `_etf_panels`; `compute_exposure` tags CRYPTO_NAMES → "Crypto",
# the rest → "ETF". Keys are unique across the two maps.
ETF_UNIVERSE = list(ETF_NAMES) + list(CRYPTO_NAMES)


def _etf_panels() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Prices and returns formed on each cached ETF/crypto source's own calendar."""
    cols: dict[str, pd.Series] = {}
    returns: dict[str, pd.Series] = {}
    for sym in ETF_UNIVERSE:
        df = store.read("yahoo", sym)
        if df is not None and "close" in getattr(df, "columns", []):
            cols[sym] = df["close"].astype(float)
            returns[sym] = cols[sym].pct_change(fill_method=None)
    return pd.DataFrame(cols).sort_index(), pd.DataFrame(returns).sort_index()


# --------------------------------------------------------------------------- #
# factor returns + orthogonalization
# --------------------------------------------------------------------------- #
def factor_frame(asof=None) -> pd.DataFrame:
    """Aligned daily RAW factor returns, one column per available factor key.
    Rows kept only where every present factor has a return (so the orthogonalization
    transform and the shared-design regression are well defined)."""
    cols: dict[str, pd.Series] = {}
    for f in FACTORS:
        df = store.read(f.group, f.sid)
        if df is None or f.col not in getattr(df, "columns", []):
            log.warning("factor_exposure: missing factor %s (%s/%s)", f.key, f.group, f.sid)
            continue
        r = df[f.col].astype(float).pct_change(fill_method=None) * f.sign
        cols[f.key] = r.dropna()
    if not cols:
        return pd.DataFrame()
    F = pd.DataFrame(cols)
    if asof is not None:
        F = F.loc[:pd.Timestamp(asof)]
    return _finite_factor_frame(F)


def _finite_factor_frame(F: pd.DataFrame) -> pd.DataFrame:
    """One common finite factor population for beta, calm and stress estimates."""
    return F.replace([np.inf, -np.inf], np.nan).dropna(how="any")


def orthogonalize_fit(F_win: pd.DataFrame) -> dict:
    """FIT the sequential (Gram-Schmidt) orthogonalization transform on one window.

    Returns the projection coefficients — for each factor k (in FACTOR_ORDER), the
    slope of its residual-so-far on each *already-orthogonalized* prior column p:
    `coeffs[k][p] = cov(v_k, g_p) / var(g_p)` computed exactly as the sequential peel
    encounters it. This is the fixed transform; `orthogonalize_apply` reproduces the
    same residuals on the fit window and — crucially for the stress lens — projects a
    DIFFERENT (e.g. longer) frame into the SAME orthogonal basis. Returns
    `{"order": [...], "coeffs": {k: {p: float, ...}, ...}}`."""
    order = [k for k in FACTOR_ORDER if k in F_win.columns]
    G = pd.DataFrame(index=F_win.index)
    coeffs: dict[str, dict[str, float]] = {}
    for k in order:
        v = F_win[k].astype(float)
        ck: dict[str, float] = {}
        for prior in G.columns:                          # priors are already orthogonal cols
            p = G[prior]
            var = float(p.var())
            beta = (float(v.cov(p)) / var) if var > 0 else 0.0
            ck[prior] = beta
            if beta:
                v = v - beta * p
        coeffs[k] = ck
        G[k] = v
    return {"order": order, "coeffs": coeffs}


def orthogonalize_apply(F: pd.DataFrame, transform: dict) -> pd.DataFrame:
    """APPLY a fitted transform (from `orthogonalize_fit`) to any frame with the same
    factor columns, producing the orthogonalized set in the FIXED basis.

    Peels each factor with the stored coefficients (against the priors it re-derives on
    THIS frame as it goes — identical construction to the fit, but the slopes are frozen
    from the fit window). Applying the fit-window transform back to the fit window
    reproduces `orthogonalize_factors` exactly; applying it to an extended window keeps
    every column in the shipped betas' basis (so b′·F_stress·b is meaningful)."""
    order = [k for k in transform["order"] if k in F.columns]
    coeffs = transform["coeffs"]
    G = pd.DataFrame(index=F.index)
    for k in order:
        v = F[k].astype(float)
        for prior, beta in coeffs.get(k, {}).items():
            if prior in G.columns and beta:
                v = v - beta * G[prior]
        G[k] = v
    return G


def orthogonalize_factors(F: pd.DataFrame) -> pd.DataFrame:
    """Sequential (Gram-Schmidt) orthogonalization in FACTOR_ORDER priority.

    Each factor is replaced by its residual after regressing out every higher-priority
    factor already processed. Market stays raw; 'growth' becomes QQQ⟂market; 'size'
    becomes IWM⟂{market,growth}; and so on. The result is a mutually-orthogonal factor
    set whose betas read as marginal exposures. Orthogonality holds on this fit
    population; a ticker's missing observations still require a joint regression.
    Estimated over the whole supplied window (static transform) — callers pass the
    estimation window so the transform and the betas share a sample. Convenience
    fit+apply on one frame; use `orthogonalize_fit`/`orthogonalize_apply` when the
    transform must be frozen on one window and applied to another (stress lens)."""
    return orthogonalize_apply(F, orthogonalize_fit(F))


# --------------------------------------------------------------------------- #
# per-stock betas
# --------------------------------------------------------------------------- #
def _betas_on_window(R_w: pd.DataFrame, G_w: pd.DataFrame, minp: int,
                     max_abs: float) -> dict:
    """Joint centered fits on each ticker's finite support in the SHARED basis.

    A ticker's missing rows can destroy the full-window orthogonality, so separate
    cov/var slopes are not generally a multivariate fit. Unidentified joint models
    are omitted: a present all-null record is treated as modeled zero risk by readers.
    Constant factors remain null while identifiable factors and residual risk survive.
    """
    if R_w.empty or G_w.empty:
        return {"betas": {}, "n": {}}
    X = G_w.to_numpy(dtype=float)
    factor_ok = np.isfinite(X).all(axis=1)
    if not factor_ok.any():
        return {"betas": {}, "n": {}}
    full_basis = X[factor_ok]
    active = np.any(full_basis != full_basis[0], axis=0)
    returns = R_w.reindex(G_w.index)
    out: dict[str, dict] = {}
    for t in returns.columns:
        y = returns[t].to_numpy(dtype=float)
        valid = factor_ok & np.isfinite(y)
        n = int(valid.sum())
        if n < minp or not n:
            continue
        x, y = X[valid], y[valid]
        # A globally varying factor that becomes constant only on this ticker's
        # support is unidentified, not a known zero exposure in the exported model.
        if np.any(active & ~np.any(x != x[0], axis=0)):
            continue
        xc, yc = x - x.mean(axis=0), y - y.mean()
        if not np.isfinite(xc).all() or not np.isfinite(yc).all():
            continue
        coefficients = np.zeros(X.shape[1], dtype=float)
        if active.any():
            try:
                fitted, _residuals, rank, _singular = np.linalg.lstsq(xc[:, active], yc, rcond=None)
            except np.linalg.LinAlgError:
                continue
            if rank != int(active.sum()) or not np.isfinite(fitted).all():
                continue
            coefficients[active] = np.clip(fitted, -max_abs, max_abs)
        residual = yc - xc @ coefficients
        var_y, var_e = float(np.mean(yc ** 2)), float(np.mean(residual ** 2))
        if not np.isfinite(var_y) or not np.isfinite(var_e):
            continue
        r2 = 1.0 - var_e / var_y if var_y > 0 else np.nan
        idio = np.sqrt(var_e) * np.sqrt(TRADING_YEAR)
        if not np.isfinite(idio):
            continue
        rec = {k: (round(float(coefficients[i]), 3) if active[i] else None)
               for i, k in enumerate(G_w.columns)}
        rec["r2"] = round(float(r2), 3) if np.isfinite(r2) else None
        rec["idio_vol"] = round(float(idio), 3) if np.isfinite(idio) else None
        rec["n"] = n
        out[str(t)] = rec
    return {"betas": out, "n": {t: rec["n"] for t, rec in out.items()}}


def stock_betas(closes: pd.DataFrame, F: pd.DataFrame, *, window: int, min_obs: int,
                max_abs: float, returns: pd.DataFrame | None = None) -> dict:
    """Ticker fits within the trailing finite factor window, in its shared basis.

    Optional `returns` preserves source calendars when `closes` is a union panel.
    Without it, `closes` must retain its native observation rows and predecessor.
    """
    if closes is None or closes.empty or F.empty:
        return {"betas": {}, "n": {}}
    Fw = _finite_factor_frame(F).tail(window)
    if len(Fw) < min_obs:
        return {"betas": {}, "n": {}}
    G_w = orthogonalize_factors(Fw)
    # Compute before filtering factor dates/window boundaries. A caller combining
    # source calendars supplies returns formed BEFORE that union.
    source_returns = closes.pct_change(fill_method=None) if returns is None else returns
    R_w = source_returns.reindex(Fw.index)
    return _betas_on_window(R_w, G_w, min_obs, max_abs)


def raw_betas(closes: pd.DataFrame, F: pd.DataFrame, *, window: int, min_obs: int,
              max_abs: float, returns: pd.DataFrame | None = None) -> dict:
    """UNIVARIATE betas to each RAW (non-orthogonal) factor — one regressor at a time.
    These over-count shared variance (don't sum them), but each is the right total
    derivative for a single-factor SHOCK and the baseline the orthogonal set improves
    on. Same shape as stock_betas()['betas'] minus r2/idio."""
    if closes is None or closes.empty or F.empty:
        return {}
    Fw = _finite_factor_frame(F).tail(window)
    if len(Fw) < min_obs:
        return {}
    source_returns = closes.pct_change(fill_method=None) if returns is None else returns
    R_w = source_returns.reindex(Fw.index).replace([np.inf, -np.inf], np.nan)
    cover = R_w.notna().sum()
    R_w = R_w[cover[cover >= min_obs].index]
    out: dict[str, dict] = {t: {} for t in R_w.columns}
    for k in Fw.columns:
        g = Fw[k]
        if not float(g.var()):
            continue
        for t in R_w.columns:
            sample = g.loc[R_w[t].notna()]
            var = float(sample.var())
            beta = R_w[t].loc[sample.index].cov(sample) / var if var > 0 else np.nan
            out[str(t)][k] = round(float(np.clip(beta, -max_abs, max_abs)), 3) if np.isfinite(beta) else None
    return out


# --------------------------------------------------------------------------- #
# portfolio aggregation (also runs client-side; kept here for tests + a server demo)
# --------------------------------------------------------------------------- #
def factor_cov(F: pd.DataFrame, *, window: int) -> pd.DataFrame:
    """Annualized covariance of the ORTHOGONAL factor returns over the trailing window
    (near-diagonal by construction) — the client uses it for risk decomposition and
    shocks."""
    F = _finite_factor_frame(F)
    if F.empty:
        return pd.DataFrame()
    G = orthogonalize_factors(F.tail(window))
    return G.cov() * TRADING_YEAR


def factor_cov_stress(F: pd.DataFrame, *, fit_window: int, stress_window: int,
                      quantile: float, min_stress_rows: int = 400,
                      min_stress_days: int = 60) -> dict:
    """Stress-conditioned orthogonal factor covariance — factor co-movement re-estimated
    on the worst-quartile market days, in the SAME orthogonal basis as the shipped betas.

    The core subtlety: the transform is FIT on the trailing `fit_window` rows (the window
    `stock_betas`/`factor_cov` use) and then APPLIED — never re-fit — to the trailing
    `stress_window` rows, so `b′·F_stress·b` client-side stays in one basis. Stress days
    are rows whose RAW `mkt` return (un-orthogonalized SPY daily) is ≤ its `quantile`
    percentile over the stress window. Returns a dict:
      {"available": bool, "cov": DataFrame|None, "vol_ann": {k: float}|None,
       "window_d": int, "n_stress": int, "mkt_cut_daily": float, "quantile": float,
       "reason": str (only when unavailable)}.
    Small-sample guard: <`min_stress_rows` usable rows → shrink window to what exists
    (stamped in window_d); <`min_stress_days` stress days → available=False, no cov."""
    F = _finite_factor_frame(F)
    if F.empty or "mkt" not in F.columns:
        return {"available": False, "reason": "no factor frame / missing mkt column",
                "window_d": 0, "n_stress": 0}

    # trailing stress window (shrink to what exists — never ship a scrap-sample cov)
    F_stress = F.tail(stress_window)
    win_actual = len(F_stress)

    # fit the transform on the SHIPPED-beta window, then APPLY it to the stress window
    F_fit = F.tail(fit_window)
    transform = orthogonalize_fit(F_fit)
    G_stress = orthogonalize_apply(F_stress, transform)

    # stress days: raw (un-orthogonalized) mkt ≤ its quantile over the same window
    mkt_raw = F_stress["mkt"].astype(float)
    cut = float(mkt_raw.quantile(quantile))
    mask = (mkt_raw <= cut).to_numpy()
    n_stress = int(mask.sum())

    meta = {"window_d": int(win_actual), "n_stress": n_stress,
            "mkt_cut_daily": round(cut, 5), "quantile": quantile}

    if win_actual < min_stress_rows or n_stress < min_stress_days:
        reason = (f"insufficient stress sample "
                  f"(window {win_actual} rows, {n_stress} stress days; "
                  f"need ≥{min_stress_rows} rows and ≥{min_stress_days} stress days)")
        return {"available": False, "reason": reason, **meta}

    G_days = G_stress.loc[mask]
    cov = G_days.cov() * TRADING_YEAR
    keys = list(cov.columns)
    vol_ann = {k: round(float(np.sqrt(max(cov.loc[k, k], 0.0))), 4) for k in keys}
    return {"available": True, "cov": cov, "vol_ann": vol_ann, **meta}


def portfolio_exposure(weights: dict[str, float], betas: dict[str, dict],
                       fcov: pd.DataFrame, idio: dict[str, float] | None = None) -> dict:
    """Aggregate a weighted book into portfolio factor betas, per-factor RISK
    contribution, and a concentration read.

    `weights` ticker→weight (need not sum to 1; normalized by gross). `betas` is
    stock_betas(...)['betas']; `fcov` the orthogonal factor covariance; `idio`
    optional ticker→annualized idiosyncratic vol for the residual risk sleeve.
    Risk contribution of factor k = b_k·(Σ_f b)_k / total variance (the factors are
    orthogonal so this is ≈ b_k²·var_k); the single biggest share is the "one bet"."""
    keys = [k for k in FACTOR_ORDER if k in fcov.columns]
    held = {t: w for t, w in weights.items() if t in betas and w}
    gross = sum(abs(w) for w in held.values())
    if not held or gross <= 0 or not keys:
        return {"verdict": "unknown", "headline": "no overlapping positions with factor betas"}

    b_p = {k: sum((held[t] / gross) * (betas[t].get(k) or 0.0) for t in held) for k in keys}
    bv = np.array([b_p[k] for k in keys])
    S = fcov.loc[keys, keys].to_numpy()
    factor_var = float(bv @ S @ bv)

    idio_var = 0.0
    if idio:
        idio_var = float(sum(((held[t] / gross) ** 2) * (idio.get(t, 0.0) ** 2) for t in held))
    total_var = factor_var + idio_var
    sd = np.sqrt(max(total_var, 0.0))

    mrc = bv * (S @ bv)                                   # marginal risk per factor
    rc = {k: (float(mrc[i]) / total_var if total_var > 0 else float("nan"))
          for i, k in enumerate(keys)}
    rc["idiosyncratic"] = (idio_var / total_var) if total_var > 0 else float("nan")

    ranked = sorted(((k, v) for k, v in rc.items() if k != "idiosyncratic"),
                    key=lambda kv: -abs(kv[1]))
    top_key, top_share = ranked[0]
    hhi = float(sum(v * v for _, v in ranked))            # factor-risk concentration
    verdict = ("concentrated" if top_share >= 0.50 else
               "tilted" if top_share >= 0.33 else "balanced")
    label = FACTOR_BY_KEY.get(top_key, Factor(top_key, "", "", "", 1, top_key, "")).label
    headline = (f"{round(top_share * 100)}% of this book's factor risk is {label.upper()} "
                f"(net beta {round(b_p[top_key], 2)}). "
                + ("Several names, largely one bet." if verdict == "concentrated"
                   else "A clear primary tilt." if verdict == "tilted"
                   else "Risk is spread across factors."))
    return {
        "verdict": verdict, "headline": headline,
        "n_positions": len(held), "gross": round(gross, 4),
        "port_vol_ann": round(float(sd), 4),
        "betas": {k: round(b_p[k], 3) for k in keys},
        "risk_contrib": {k: (round(v, 3) if np.isfinite(v) else None) for k, v in rc.items()},
        "top_factor": top_key, "top_share": round(float(top_share), 3),
        "concentration_hhi": round(hhi, 3),
    }


# --------------------------------------------------------------------------- #
# live snapshot / export
# --------------------------------------------------------------------------- #
def compute_exposure(asof=None, closes: pd.DataFrame | None = None) -> dict | None:
    """Live per-ticker factor-beta export for latest.json / site/exposure/betas.json.

    Ships the orthogonal betas (exposure/risk), the raw univariate betas (shocks),
    factor metadata, and the orthogonal factor covariance so the watchlist can do all
    the portfolio aggregation client-side from the user's own position weights."""
    cfg = _cfg()
    F = factor_frame(asof=asof)
    if F.empty or len(F) < int(cfg["min_factor_obs"]):
        log.warning("factor_exposure: too little factor history (%d rows)", len(F))
        return None
    if closes is None:
        closes = _closes()
    if closes is None or closes.empty:
        log.warning("factor_exposure: no close matrix")
        return None
    if asof is not None:
        closes = closes.loc[:pd.Timestamp(asof)]

    returns = closes.pct_change(fill_method=None)
    etf, etf_returns = _etf_panels()                       # preserve each source calendar
    if not etf.empty:
        if asof is not None:
            etf = etf.loc[:pd.Timestamp(asof)]
        closes = pd.concat([closes, etf], axis=1, sort=False)
        closes = closes.loc[:, ~closes.columns.duplicated()].sort_index()
        returns = pd.concat([returns, etf_returns], axis=1, sort=False)
        returns = returns.loc[:, ~returns.columns.duplicated()].sort_index()
    etf_set = set(ETF_UNIVERSE)

    win, minp, max_abs = int(cfg["window_d"]), int(cfg["min_obs"]), float(cfg["max_abs_beta"])
    res = stock_betas(closes, F, window=win, min_obs=minp, max_abs=max_abs, returns=returns)
    if not res["betas"]:
        log.warning("factor_exposure: no betas estimated")
        return None
    rb = raw_betas(closes, F, window=win, min_obs=minp, max_abs=max_abs, returns=returns)
    fcov = factor_cov(F, window=win)
    keys = list(fcov.columns)

    # Stress lens (W1): factor co-movement re-estimated on worst-quartile market days,
    # in the SAME orthogonal basis as the shipped betas (transform fit on `win`, applied
    # to the trailing stress window). Additive + guarded — a scrap sample emits nothing.
    stress = factor_cov_stress(F, fit_window=win, stress_window=int(cfg["stress_window_d"]),
                               quantile=float(cfg["stress_quantile"]))

    ns = _names_sectors()
    betas = res["betas"]
    for t, rec in betas.items():
        if t in CRYPTO_NAMES:
            # coins + spot-crypto ETFs + Coinbase: own "Crypto" sector so the sleeve
            # groups honestly. is_etf stays False (unused by the client; the coins/COIN
            # aren't ETFs and the sector tag already carries the grouping).
            rec["name"], rec["sector"], rec["is_etf"] = CRYPTO_NAMES[t], "Crypto", False
        elif t in etf_set:
            rec["name"], rec["sector"], rec["is_etf"] = ETF_NAMES.get(t, t), "ETF", True
        else:
            rec["name"], rec["sector"] = ns.get(t, (t, "—"))
            rec["is_etf"] = False
        rec["raw"] = rb.get(t, {})

    most_idio = sorted((t for t in betas if betas[t].get("idio_vol") is not None),
                       key=lambda t: -betas[t]["idio_vol"])[:int(cfg["top_n_idio"])]

    out = {
        "as_of": str(F.index.max().date()),
        "window_d": win, "n": len(betas), "note": NOTE,
        "factors": [{"key": f.key, "label": f.label, "note": f.note,
                     **FACTOR_CONFIDENCE.get(f.key, {})}
                    for f in FACTORS if f.key in keys],
        "factor_vol_ann": {k: round(float(np.sqrt(max(fcov.loc[k, k], 0.0))), 4) for k in keys},
        "factor_cov": {a: {b: round(float(fcov.loc[a, b]), 6) for b in keys} for a in keys},
        "betas": betas,
        "most_idiosyncratic": [{"ticker": t, "name": betas[t]["name"],
                                "idio_vol": betas[t]["idio_vol"], "r2": betas[t]["r2"]}
                               for t in most_idio],
    }

    # additive stress-lens emit — see factor_cov_stress(). Shares `keys` (== factor_cov
    # ordering) so the client reads both covariances in one basis. Guarded: on a scrap
    # sample only stress_meta (available:false) ships, no covariance.
    if stress.get("available"):
        scov = stress["cov"]
        skeys = [k for k in keys if k in scov.columns]
        out["factor_cov_stress"] = {a: {b: round(float(scov.loc[a, b]), 6) for b in skeys}
                                    for a in skeys}
        out["factor_vol_stress_ann"] = {k: stress["vol_ann"][k] for k in skeys}
        out["stress_meta"] = {
            "available": True, "window_d": stress["window_d"], "quantile": stress["quantile"],
            "n_stress": stress["n_stress"], "mkt_cut_daily": stress["mkt_cut_daily"],
            "note": ("factor co-movement re-estimated on worst-quartile market days; "
                     "idiosyncratic vol estimated on all days"),
        }
    else:
        out["stress_meta"] = {"available": False, "reason": stress.get("reason", "unavailable")}
    return out


def snapshot() -> dict:
    """latest.json["factor_exposure"] entry — degrades to verdict='unknown'."""
    out = compute_exposure()
    if out is None:
        return {"verdict": "unknown", "headline": "insufficient factor or price history"}
    return out
