"""Equity/index dealer-gamma "magnets" engine — a VOL-REGIME + LEVELS MAP, NOT alpha.

Pure function over a per-strike option chain (the Cboe collector supplies it):
net GEX / VEX / CEX, the gamma-flip (zero-gamma spot, grid-reevaluated like
collectors/deribit._gamma_flip), the gamma regime, magnet strikes (where dealer
hedging concentrates), the charm anchor, ATM IV30, put/call OI and max-pain.

HONEST FRAMING (carried into every consumer, see
LIMITATIONS.md): the dealer long-call / short-put SIGN is an unobservable
assumption — weaker for single names (covered-call ETFs / retail call-buying can
flip true positioning); single-name GEX is fragile to one large non-dealer
position; the FREE Cboe feed is delayed / EOD so it MISSES the 0DTE flow that drives
intraday. Magnet / flip strikes are LEVELS (where hedging concentrates), never
targets. The one falsifiable claim — negative-gamma -> higher forward realized vol —
is checked in scripts/validate_gex.py.

Engine input contract — chain: DataFrame with columns
  K (strike), T (years to expiry), iv (DECIMAL vol), oi (open interest),
  is_call (bool), and optionally expiry. spot: float. cfg overrides DEFAULTS.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from engine.greeks import SQRT2PI, bs_greeks

DEFAULTS = dict(
    contract_multiplier=100.0, pct_move=0.01, strike_window_pct=0.25,
    max_expiry_days=365, near_money_pct=0.10, min_strikes=40,
    conc_share_warn=0.35, r=0.0, q=0.0,
)


def _window(chain: pd.DataFrame, S: float, cfg: dict) -> pd.DataFrame:
    w = cfg["strike_window_pct"]
    maxT = cfg["max_expiry_days"] / 365.0
    return chain[(chain["T"] > 0) & (chain["T"] <= maxT)
                 & chain["K"].between(S * (1 - w), S * (1 + w))
                 & (chain["iv"] > 0) & (chain["oi"] > 0)].copy()


# Absolute near-zero band for the net repriced dealer-gamma REGIME, in DOLLARS PER
# ``pct_move`` — the same units as ``gamma_profile``'s ``net`` array and
# ``compute_gex``'s ``net_gex_bn * 1e9``. |net gamma at S| <= REGIME_EPS is
# indeterminate, so ``gamma_regime`` is None rather than a synthesised long/short sign.
REGIME_EPS = 1e-8


def _valid_spot(S) -> bool:
    """True only for a finite, strictly positive numeric spot."""
    if isinstance(S, bool) or not isinstance(S, (int, float, np.integer, np.floating)):
        return False
    return bool(np.isfinite(S)) and S > 0


_REQUIRED_COLUMNS = ("K", "T", "iv", "oi", "is_call")
_POSITIVE_FIELDS = ("K", "T", "iv", "oi")
_CFG_NUMERIC_FIELDS = ("r", "q")
_CFG_POSITIVE_FIELDS = ("contract_multiplier", "pct_move")


def _usable_rows(c: pd.DataFrame):
    """The exact rows ``gamma_profile`` reprices — ``(K, T, sig, oi, sgn)`` float arrays
    (dealer sign: call +1 / put -1) or None.

    A row counts only when it is genuine inventory: K, T, iv and oi are finite and
    strictly positive, and ``is_call`` is a real boolean (``None``/strings/NA are
    rejected, never coerced). Fewer than 20 usable rows, missing columns, or a
    malformed frame return None rather than raising."""
    try:
        if c is None or not all(col in c.columns for col in _REQUIRED_COLUMNS):
            return None
        ic = c["is_call"]
        if not pd.api.types.is_bool_dtype(ic) or bool(ic.isna().any()):
            return None
        cols = {name: pd.to_numeric(c[name], errors="coerce").to_numpy(float)
                for name in _POSITIVE_FIELDS}
        keep = np.ones(len(c), dtype=bool)
        for arr in cols.values():
            keep &= np.isfinite(arr) & (arr > 0)
        if int(keep.sum()) < 20:
            return None
        sgn = np.where(ic.to_numpy(dtype=bool)[keep], 1.0, -1.0)
        return cols["K"][keep], cols["T"][keep], cols["iv"][keep], cols["oi"][keep], sgn
    except (KeyError, TypeError, ValueError, AttributeError):
        return None


def _valid_cfg(cfg: dict) -> bool:
    """True only for a cfg whose ``r``/``q`` are finite numbers and whose
    ``contract_multiplier``/``pct_move`` are finite and strictly positive."""
    try:
        for name in _CFG_NUMERIC_FIELDS:
            v = cfg[name]
            if isinstance(v, bool) or not isinstance(v, (int, float, np.integer, np.floating)):
                return False
            if not np.isfinite(v):
                return False
        for name in _CFG_POSITIVE_FIELDS:
            v = cfg[name]
            if isinstance(v, bool) or not isinstance(v, (int, float, np.integer, np.floating)):
                return False
            if not np.isfinite(v) or v <= 0:
                return False
        return True
    except (KeyError, TypeError, ValueError):
        return False


def _sampled_crossings(grid, net):
    """Spot values where the sampled profile brackets a change of sign.

    A crossing is recorded only where two ADJACENT samples lie outside the near-zero
    ``REGIME_EPS`` band with opposite sign, or where a sample is EXACTLY zero and its
    two finite neighbours are opposite-signed. An all-zero / all-within-band plateau
    has no unique root and yields none. Roots are linearly interpolated within their
    bracketing pair; the finite grid is a sample and this list is not a certified
    inventory of the curve's continuous roots."""
    signs = np.where(np.abs(net) <= REGIME_EPS, 0, np.where(net > 0, 1, -1))
    flips = []
    for i in range(len(grid) - 1):
        if signs[i] != 0 and signs[i + 1] != 0 and signs[i] != signs[i + 1]:
            y0, y1, x0, x1 = net[i], net[i + 1], grid[i], grid[i + 1]
            flips.append(float(x0 - y0 * (x1 - x0) / (y1 - y0)) if y1 != y0 else float(x0))
    for i in range(1, len(grid) - 1):
        if (net[i] == 0.0 and signs[i - 1] != 0 and signs[i + 1] != 0
                and signs[i - 1] != signs[i + 1]):
            flips.append(float(grid[i]))
    return sorted(flips)


def _repriced_net(K, T, sig, oi, sgn, cfg: dict, Sx: float) -> float:
    """Net dealer gamma RE-PRICED at one spot ``Sx`` — dollars per ``pct_move``.

    Same European Black-Scholes gamma and r/q/multiplier/pct_move conventions as
    ``gamma_profile`` (which is this function sampled on its ±25% grid): call +OI,
    put -OI on the assumption dealer long-call / short-put book."""
    r, q, mult, pm = cfg["r"], cfg["q"], cfg["contract_multiplier"], cfg["pct_move"]
    sqrtT = np.sqrt(T)
    d1 = (np.log(Sx / K) + (r - q + 0.5 * sig * sig) * T) / (sig * sqrtT)
    gamma = np.exp(-q * T) * np.exp(-0.5 * d1 * d1) / SQRT2PI / (Sx * sig * sqrtT)
    return float(np.sum(sgn * gamma * oi * mult * Sx * Sx * pm))


def gamma_profile(c: pd.DataFrame, S: float, cfg: dict):
    """Net dealer gamma RE-PRICED across a ±25% spot grid — the exposure PROFILE.

    This is the category's flagship object (masterplan §4.2 `profile`): exposure as a
    FUNCTION of spot, not merely at it. It is also the single source for the flip —
    ``_gamma_flip`` delegates here so the published curve and the published crossing
    can never disagree (the 2026-08-01 defect family was exactly two derivations of
    one quantity drifting apart).

    Returns ``(grid, net, flips)`` — numpy arrays of trial spots and net dealer gamma
    in dollars per ``pct_move`` at each, plus the interpolated spot roots bracketed by
    adjacent sampled sign changes. The grid is a finite sample, so ``flips`` is not a
    certified inventory of the curve's continuous roots. ``(None, None, [])`` is
    returned for an invalid spot, a thin / non-boolean / malformed chain, or a
    nonfinite cfg or repriced sample — never a fabricated or nonfinite root.
    """
    if not _valid_spot(S) or not _valid_cfg(cfg):
        return None, None, []
    rows = _usable_rows(c)
    if rows is None:
        return None, None, []
    K, T, sig, oi, sgn = rows
    grid = S * np.linspace(0.75, 1.25, 101)
    net = np.array([_repriced_net(K, T, sig, oi, sgn, cfg, Sx) for Sx in grid])
    if not np.all(np.isfinite(net)):
        return None, None, []
    return grid, net, _sampled_crossings(grid, net)


def _gamma_flip(c: pd.DataFrame, S: float, cfg: dict):
    """Zero-gamma crossing + regime for the CURRENT spot.

    Returns ``(flip, signed_dist_pct, gamma_regime)``. ``flip`` is the zero-crossing
    of the repriced ±25% profile NEAREST to ``S`` and ``signed_dist_pct`` is its signed
    distance — a separate quantity, kept as such. ``gamma_regime`` is read from the
    SAME repriced curve AT the actual spot ``S``, NEVER from ``S`` relative to the
    nearest crossing, so a curve whose gamma sign runs opposite its slope (e.g. a
    call-heavy-lower / put-heavy-upper "descending" book) still reports its true sign.

    ``gamma_regime`` is ``"long"``/``"short"``, or None for an invalid spot, a too-thin
    chain, nonfinite repricing, or |net gamma at S| <= REGIME_EPS (dollars per
    ``pct_move``) — never a synthesised sign. When no unique crossing exists (an
    all-zero / near-zero plateau, or a malformed book) the whole triple is
    ``(None, None, None)``: a near-zero regime must not keep a fabricated ``flip=S``."""
    if not _valid_spot(S) or not _valid_cfg(cfg):
        return None, None, None
    grid, net, flips = gamma_profile(c, S, cfg)
    if grid is None:
        return None, None, None
    flip = min(flips, key=lambda f: abs(f - S)) if flips else None
    if flip is not None and not np.isfinite(flip):
        flip = None
    dist = round(100.0 * (S - flip) / S, 2) if flip is not None else None
    rows = _usable_rows(c)
    val = _repriced_net(*rows, cfg, float(S)) if rows is not None else float("nan")
    if not np.isfinite(val) or abs(val) <= REGIME_EPS:
        regime = None
    else:
        regime = "long" if val > 0 else "short"
    return (float(flip) if flip is not None else None), dist, regime


def _max_pain(c: pd.DataFrame):
    front = c.groupby("expiry")["oi"].sum().idxmax()
    fe = c[c["expiry"] == front]
    strikes = np.sort(fe["K"].unique())
    if not len(strikes):
        return None
    pay = []
    for P in strikes:
        cc = (fe.loc[fe["is_call"], "oi"] * (P - fe.loc[fe["is_call"], "K"]).clip(lower=0)).sum()
        pp = (fe.loc[~fe["is_call"], "oi"] * (fe.loc[~fe["is_call"], "K"] - P).clip(lower=0)).sum()
        pay.append(cc + pp)
    return float(strikes[int(np.argmin(pay))])


def _iv30(c: pd.DataFrame, S: float):
    pts = []
    for _, g in c.groupby("expiry"):
        gv = g[g["iv"] > 0]
        if gv.empty:
            continue
        atm = gv.loc[(gv["K"] - S).abs().idxmin()]
        pts.append((float(atm["T"] * 365.0), float(atm["iv"])))
    if not pts:
        return None
    pts.sort()
    ten = [p[0] for p in pts]; ivs = [p[1] for p in pts]
    if ten[0] <= 30 <= ten[-1]:
        return float(np.interp(30, ten, ivs))
    return ivs[0] if 30 < ten[0] else ivs[-1]   # nearest listed tenor (no extrapolation)


def _pcr(c: pd.DataFrame):
    coi = c.loc[c["is_call"], "oi"].sum()
    poi = c.loc[~c["is_call"], "oi"].sum()
    return float(poi / coi) if coi > 0 else None


# Index products whose gamma regime is at least a market-wide read (still assumption-signed,
# but not a single-name product attribute). Everything else is treated as single-name.
_INDEX_PRODUCTS = frozenset({"SPX", "SPY", "QQQ", "NDX", "IWM", "RUT", "VIX", "DIA", "SPXW"})


def _gamma_regime_passport(symbol: str | None) -> dict:
    """Audit #29: the dealer long-call/short-put SIGN is unobservable from Cboe OI alone, so
    every gamma_regime is assumption-basis. For SINGLE NAMES the regime is additionally a
    near-constant PRODUCT ATTRIBUTE (covered-call ETFs / retail call-buying pin the sign), so
    the forward-RV validator's MIN_PER_BUCKET is structurally unreachable — it is NOT a
    time-varying signal and must never be read as one."""
    is_index = bool(symbol) and str(symbol).upper() in _INDEX_PRODUCTS
    return {
        "basis": "assumption",
        "structurally_constant": (not is_index) if symbol else None,
        "is_index_product": is_index if symbol else None,
        "verdict": "display-only",
        "note": ("dealer long-call/short-put sign is an unobservable assumption; "
                 + ("single-name gamma regime is a near-constant product attribute, not a "
                    "time-varying signal (validator MIN_PER_BUCKET structurally unreachable)"
                    if (symbol and not is_index) else
                    "even for indices SPY vs SPX can contradict same-day — read as assumption, "
                    "not observed")),
    }


def compute_gex(chain: pd.DataFrame, spot: float, cfg: dict | None = None,
                symbol: str | None = None) -> dict:
    """Per-strike chain -> magnets summary dict. Returns a low-confidence / empty
    tier when the chain is too thin to trust. NEVER fabricates. ``symbol`` (optional) lets the
    summary carry a gamma-regime PASSPORT flagging single-name regimes as assumption-signed +
    structurally-constant (audit #29)."""
    cf = {**DEFAULTS, **(cfg or {})}
    if chain is None or len(chain) == 0 or not (spot and spot > 0):
        return {"tier": "no_options", "note": "no listed options / empty chain"}
    c = _window(chain, spot, cf)
    n = int(len(c))
    if n < 6:
        return {"tier": "no_options", "n_strikes": n}
    if "expiry" not in c.columns:
        c["expiry"] = c["T"].round(6)

    g = [bs_greeks(spot, k, t, s, bool(cc), cf["r"], cf["q"])
         for k, t, s, cc in zip(c["K"], c["T"], c["iv"], c["is_call"])]
    c["gamma"] = [x[1] for x in g]
    c["vanna"] = [x[2] for x in g]
    c["charm"] = [x[3] for x in g]

    sign = np.where(c["is_call"], 1.0, -1.0)
    mult, pm = cf["contract_multiplier"], cf["pct_move"]
    dg = c["gamma"] * c["oi"] * mult * spot ** 2          # unsigned $ gamma (level)
    gex = sign * dg * pm                                   # $ / 1% move
    vex = sign * c["vanna"] * c["oi"] * mult * spot * pm   # $ delta / 1 vol pt-ish
    cex = sign * (c["charm"] / 365.0) * c["oi"] * mult * spot  # $ delta / day

    flip, dist, regime = _gamma_flip(c, spot, cf)

    dg_by_k = dg.groupby(c["K"]).sum()
    up = dg_by_k[dg_by_k.index > spot]
    dn = dg_by_k[dg_by_k.index < spot]
    magnet_up = float(up.idxmax()) if not up.empty else None
    magnet_dn = float(dn.idxmax()) if not dn.empty else None
    share = float(dg_by_k.max() / dg_by_k.sum()) if dg_by_k.sum() > 0 else 1.0

    nm = c[(c["K"] - spot).abs() <= spot * cf["near_money_pct"]]
    charm_anchor = None
    if not nm.empty:
        cex_by_k = cex[nm.index].groupby(nm["K"]).sum()
        if not cex_by_k.empty and float(cex_by_k.abs().max()) > 0:
            charm_anchor = float(cex_by_k.abs().idxmax())

    net_cex = float(cex.sum())
    tier = "thin_chain" if (n < cf["min_strikes"] or share > cf["conc_share_warn"]) else "full"

    return {
        "tier": tier, "n_strikes": n, "spot": float(spot),
        "net_gex_bn": float(gex.sum() / 1e9), "net_vex": float(vex.sum()), "net_cex": net_cex,
        "gamma_flip": flip, "dist_to_flip_pct": dist, "gamma_regime": regime,
        "regime_passport": _gamma_regime_passport(symbol),
        "magnet_up": magnet_up, "magnet_down": magnet_dn,
        "charm_anchor": charm_anchor,
        "charm_net_sign": (1 if net_cex > 0 else -1 if net_cex < 0 else 0),
        "iv30": _iv30(c, spot), "put_call_oi_ratio": _pcr(c), "max_pain": _max_pain(c),
        "top_oi_share": round(share, 3),
    }
