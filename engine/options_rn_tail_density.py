"""RESEARCH REFERENCE — NOT WIRED.

Q13 — risk-neutral (Q) tail-density estimation with quote-uncertainty bounds.

VERDICT (quant assessment 2026-10, brief Q13): INSUFFICIENT_DATA. The
licensed retained data lacks every input an *admitted* surface needs:

- M1: per-strike executable quotes (bid/ask or NBBO) on a full chain snapshot;
- M2: a qualified forward/discount basis including dividends (the Q12 basis);
- M3: European exercise, or a Q02-qualified American-exercise adjustment;
- M4: a Q01-qualified arbitrage-checked surface.

The single proxy comparison (vendor-iv SPY chains with a *declared* quote
band) is diagnostic only. It is labeled ``PROXY — not admitted surface`` and
cannot promote, rank, size, gate or wire anything. See
``research/quant_assessment_2026_10/Q13_risk_neutral_tail_density/VERDICT.md``.

What this module is
-------------------
Pure, bounded, deterministic functions for the Breeden–Litzenberger
identities

    f_Q(K)       = D^{-1} d^2C/dK^2
    Q(S_T <= K)  = 1 + D^{-1} dC/dK

on a discrete strike grid, with one :class:`ForwardBasis` (forward ``F`` and
discount factor ``D``) used for pricing, parity, density normalization and the
forward/moment check. It provides:

- Black-76 pricing and implied vol on the basis;
- declared implied-vol quote bands converted to price bands (put bands map to
  call-equivalent bands by parity on the same basis);
- a static-arbitrage report and a slope-isotonic repair (weighted PAVA);
- the discrete-atom density of piecewise-linear calls, with explicit left/right
  grid-truncation masses and a forward interval check;
- model-free identified bounds ``[L, U]`` for ``Q(S_T <= K*)`` from price bands;
- a smoothed smile (Whittaker + PCHIP + linear wings capped by Lee's moment
  bound) that reports where it extrapolates;
- a quote-perturbation interval and an identification classifier that
  restricts output to identified price bounds (``PRICE_BOUNDS_ONLY``) when wing
  support is weak or curvature is unstable.

Every probability here is a **pricing-measure (Q) quantity**. It is not a
physical (P) probability, not crash odds and not a forecast. Converting Q to P
needs a pricing-kernel model, which this module refuses: :func:`to_physical`
raises :class:`MeasureError`.

Contract
--------
``RESEARCH_ONLY = True``. Importing this module performs no I/O, reads no
environment, configures no logging and registers nothing. No production code
imports it; only its own hermetic test and the Q13 research harness
(``research/quant_assessment_2026_10/Q13_risk_neutral_tail_density/evaluate.py``)
load it. It originates no signal, score, rank, size, gate or escalation, and
no language model originates any of its numbers.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Callable, Sequence

import numpy as np
from scipy.interpolate import PchipInterpolator
from scipy.special import ndtr

RESEARCH_ONLY = True
SCHEMA = "options.rn_tail_density/research-v1"
VERDICT = "INSUFFICIENT_DATA"
MEASURE = "Q"
MEASURE_LABEL = (
    "risk-neutral (pricing-measure) probability; not a physical probability, "
    "not crash odds, not a forecast"
)
ADMISSION_STATUS = "DIAGNOSTIC_UNADMITTED"
PROXY_LABEL = "PROXY — not admitted surface"
MISSING_INPUTS: tuple[str, ...] = (
    "M1: per-strike executable quotes (bid/ask or NBBO) on a full chain snapshot",
    "M2: qualified forward/discount basis including dividends (Q12 basis)",
    "M3: European exercise or Q02-qualified American-exercise adjustment",
    "M4: Q01-qualified arbitrage-checked surface",
)

IDENT_FULL = "FULL_DENSITY"
IDENT_BOUNDS = "PRICE_BOUNDS_ONLY"

# Frozen thresholds (PREREG section 13).
MIN_WING_STRIKES = 2
NEG_MASS_TOL = 0.01
REL_WIDTH_MAX = 0.5

# Smile / pricing bounds.
IV_FLOOR = 0.01
VOL_MIN = 1e-4
VOL_MAX = 5.0

# Input bounds (bounded inputs; reject rather than silently truncate).
MAX_QUOTES = 2000
MAX_GRID = 20001
MAX_DRAWS = 10000
MAX_T_YEARS = 10.0
DEFAULT_GRID_NODES = 1601
DEFAULT_FWD_TOL_REL = 1e-3


class MeasureError(Exception):
    """Raised when a caller asks for a physical-measure (P) quantity."""


# ---------------------------------------------------------------------------
# Basis
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ForwardBasis:
    """One forward/discount basis used for every price, parity and check."""

    forward: float
    discount: float
    T: float
    rate: float | None = None
    carry: float | None = None
    label: str = ""

    def __post_init__(self) -> None:
        for name, v in (("forward", self.forward), ("discount", self.discount), ("T", self.T)):
            if not isinstance(v, (int, float)) or isinstance(v, bool) or not math.isfinite(float(v)):
                raise ValueError(f"basis {name} must be a finite number")
        if self.forward <= 0:
            raise ValueError("basis forward must be > 0")
        if not (0.0 < self.discount < 2.0):
            raise ValueError("basis discount must lie in (0, 2)")
        if not (0.0 < self.T <= MAX_T_YEARS):
            raise ValueError(f"basis T must lie in (0, {MAX_T_YEARS}] years")

    def as_dict(self) -> dict[str, Any]:
        return {
            "forward": float(self.forward),
            "discount": float(self.discount),
            "T": float(self.T),
            "rate": None if self.rate is None else float(self.rate),
            "carry": None if self.carry is None else float(self.carry),
            "label": self.label,
        }


def make_forward_basis(spot: float, rate: float, T: float, carry: float = 0.0, label: str = "") -> ForwardBasis:
    """``F = spot * exp((rate - carry) T)``, ``D = exp(-rate T)`` (continuous)."""
    for name, v in (("spot", spot), ("rate", rate), ("T", T), ("carry", carry)):
        if not isinstance(v, (int, float)) or isinstance(v, bool) or not math.isfinite(float(v)):
            raise ValueError(f"{name} must be a finite number")
    if spot <= 0:
        raise ValueError("spot must be > 0")
    if abs(rate) > 1.0 or abs(carry) > 1.0:
        raise ValueError("rate and carry must be decimal rates with |x| <= 1")
    fwd = float(spot) * math.exp((float(rate) - float(carry)) * float(T))
    disc = math.exp(-float(rate) * float(T))
    return ForwardBasis(fwd, disc, float(T), float(rate), float(carry), label)


def from_forward(forward: float, discount: float, T: float, label: str = "") -> ForwardBasis:
    """Basis from an externally supplied forward and discount factor."""
    return ForwardBasis(float(forward), float(discount), float(T), None, None, label)


# ---------------------------------------------------------------------------
# Input validation helpers
# ---------------------------------------------------------------------------


def _as_1d(x: Any, name: str, max_len: int = MAX_QUOTES, allow_empty: bool = False) -> np.ndarray:
    a = np.asarray(x, dtype=float).reshape(-1)
    if a.size > max_len:
        raise ValueError(f"{name} has {a.size} entries; the bound is {max_len}")
    if a.size == 0 and not allow_empty:
        raise ValueError(f"{name} is empty")
    if not np.all(np.isfinite(a)):
        raise ValueError(f"{name} contains non-finite values")
    return a


def _as_bool_1d(x: Any, n: int, name: str) -> np.ndarray:
    if isinstance(x, (bool, np.bool_)):
        return np.full(n, bool(x))
    a = np.asarray(x).reshape(-1)
    if a.size != n:
        raise ValueError(f"{name} must have {n} entries")
    if a.dtype != bool:
        if not np.all(np.isin(a, [0, 1, True, False])):
            raise ValueError(f"{name} must be boolean")
        a = a.astype(bool)
    return a


def _strictly_increasing(K: np.ndarray, name: str = "strikes") -> None:
    if K.size >= 2 and not np.all(np.diff(K) > 0):
        raise ValueError(f"{name} must be strictly increasing")


# ---------------------------------------------------------------------------
# Black-76 on the basis
# ---------------------------------------------------------------------------


def black76_price(basis: ForwardBasis, K: Any, vol: Any, is_call: Any = True) -> np.ndarray:
    """Discounted Black-76 price on ``basis`` (vectorized)."""
    Ka = _as_1d(K, "K", MAX_GRID)
    if np.any(Ka <= 0):
        raise ValueError("strikes must be > 0")
    va = np.broadcast_to(_as_1d(vol, "vol", MAX_GRID), Ka.shape).astype(float)
    if np.any(va < 0):
        raise ValueError("vol must be >= 0")
    calls = _as_bool_1d(is_call, Ka.size, "is_call")
    F, D, T = basis.forward, basis.discount, basis.T
    sig = va * math.sqrt(T)
    pos = sig > 0
    safe = np.where(pos, sig, 1.0)
    d1 = (np.log(F / Ka) + 0.5 * safe * safe) / safe
    d2 = d1 - safe
    call = D * (F * ndtr(d1) - Ka * ndtr(d2))
    put = D * (Ka * ndtr(-d2) - F * ndtr(-d1))
    call = np.where(pos, call, D * np.maximum(F - Ka, 0.0))
    put = np.where(pos, put, D * np.maximum(Ka - F, 0.0))
    return np.where(calls, call, put)


def implied_vol_black76(basis: ForwardBasis, K: Any, price: Any, is_call: Any = True, n_iter: int = 200) -> np.ndarray:
    """Vectorized bisection implied vol on ``[VOL_MIN, VOL_MAX]``; NaN if unreachable."""
    Ka = _as_1d(K, "K", MAX_GRID)
    pa = np.broadcast_to(_as_1d(price, "price", MAX_GRID), Ka.shape).astype(float)
    calls = _as_bool_1d(is_call, Ka.size, "is_call")
    if not (10 <= int(n_iter) <= 1000):
        raise ValueError("n_iter must lie in [10, 1000]")
    lo = np.full(Ka.shape, VOL_MIN)
    hi = np.full(Ka.shape, VOL_MAX)
    p_lo = black76_price(basis, Ka, lo, calls)
    p_hi = black76_price(basis, Ka, hi, calls)
    tol = 1e-12 * max(basis.forward, 1.0)
    ok = (pa >= p_lo - tol) & (pa <= p_hi + tol)
    for _ in range(int(n_iter)):
        mid = 0.5 * (lo + hi)
        pm = black76_price(basis, Ka, mid, calls)
        up = pm < pa
        lo = np.where(up, mid, lo)
        hi = np.where(up, hi, mid)
    out = 0.5 * (lo + hi)
    return np.where(ok, out, np.nan)


def put_to_call(basis: ForwardBasis, K: Any, put_price: Any) -> np.ndarray:
    """Put-call parity on the same basis: ``C = P + D (F - K)``."""
    Ka = _as_1d(K, "K", MAX_GRID)
    pa = np.broadcast_to(_as_1d(put_price, "put_price", MAX_GRID), Ka.shape)
    return pa + basis.discount * (basis.forward - Ka)


def iv_half_width(k: Any, scale: float = 1.0) -> np.ndarray:
    """Declared implied-vol half-width ``scale * (0.005 + 0.05 |k|)`` (PREREG section 6)."""
    ka = _as_1d(k, "k", MAX_GRID)
    if not (math.isfinite(scale) and 0.0 <= scale <= 10.0):
        raise ValueError("band scale must lie in [0, 10]")
    return float(scale) * (0.005 + 0.05 * np.abs(ka))


def call_equivalent_bands(
    basis: ForwardBasis, K: Any, iv: Any, is_call: Any, half_width: Any
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Call-equivalent (mid, lo, hi) prices from an implied-vol band.

    Lower vol is floored at ``VOL_MIN``. Put prices map to calls by parity on
    the same basis (a constant shift per strike, so band order is preserved).
    """
    Ka = _as_1d(K, "K")
    iva = _as_1d(iv, "iv")
    hwa = np.broadcast_to(_as_1d(half_width, "half_width"), Ka.shape).astype(float)
    if iva.size != Ka.size:
        raise ValueError("K and iv must have equal length")
    if np.any(iva <= 0) or np.any(hwa < 0):
        raise ValueError("iv must be > 0 and half_width >= 0")
    calls = _as_bool_1d(is_call, Ka.size, "is_call")
    mid = black76_price(basis, Ka, iva, calls)
    lo = black76_price(basis, Ka, np.maximum(iva - hwa, VOL_MIN), calls)
    hi = black76_price(basis, Ka, iva + hwa, calls)
    shift = np.where(calls, 0.0, basis.discount * (basis.forward - Ka))
    return mid + shift, lo + shift, hi + shift


# ---------------------------------------------------------------------------
# Static arbitrage and repair
# ---------------------------------------------------------------------------


def _slopes(K: np.ndarray, C: np.ndarray) -> np.ndarray:
    return np.diff(C) / np.diff(K)


def _atom_masses(K: np.ndarray, C: np.ndarray, D: float) -> tuple[float, np.ndarray, float]:
    s = _slopes(K, C)
    left = 1.0 + s[0] / D
    interior = np.diff(s) / D
    right = -s[-1] / D
    return float(left), interior, float(right)


def static_arbitrage_report(K: Any, C: Any, basis: ForwardBasis, tol: float = 1e-10) -> dict[str, Any]:
    """Static no-arbitrage diagnostics of call prices on a strike grid."""
    Ka = _as_1d(K, "K", MAX_GRID)
    Ca = _as_1d(C, "C", MAX_GRID)
    if Ka.size != Ca.size or Ka.size < 3:
        raise ValueError("K and C must have equal length >= 3")
    _strictly_increasing(Ka)
    D, F = basis.discount, basis.forward
    s = _slopes(Ka, Ca)
    scale = tol * max(F, 1.0)
    n_monotone = int(np.sum(s > tol))
    n_slope_floor = int(np.sum(s < -D - tol))
    n_convex = int(np.sum(np.diff(s) < -tol))
    lower = D * np.maximum(F - Ka, 0.0)
    n_bound = int(np.sum(Ca < lower - scale) + np.sum(Ca > D * F + scale))
    left, interior, right = _atom_masses(Ka, Ca, D)
    neg = float(np.sum(np.clip(-interior, 0.0, None)) + max(-left, 0.0) + max(-right, 0.0))
    max_bfly = float(np.max(np.clip(-np.diff(s), 0.0, None))) if s.size > 1 else 0.0
    return {
        "n_nodes": int(Ka.size),
        "n_monotonicity_violations": n_monotone,
        "n_slope_floor_violations": n_slope_floor,
        "n_butterfly_violations": n_convex,
        "n_price_bound_violations": n_bound,
        "negative_atom_mass": neg,
        "max_butterfly_violation": max_bfly,
        "arbitrage_free": bool(n_monotone == 0 and n_slope_floor == 0 and n_convex == 0 and n_bound == 0),
    }


def _pava_nondecreasing(y: np.ndarray, w: np.ndarray) -> np.ndarray:
    vals: list[float] = []
    wts: list[float] = []
    cnts: list[int] = []
    for yi, wi in zip(y.tolist(), w.tolist()):
        vals.append(yi)
        wts.append(wi)
        cnts.append(1)
        while len(vals) > 1 and vals[-2] > vals[-1]:
            wsum = wts[-2] + wts[-1]
            v = (vals[-2] * wts[-2] + vals[-1] * wts[-1]) / wsum
            c = cnts[-2] + cnts[-1]
            vals.pop()
            wts.pop()
            cnts.pop()
            vals[-1] = v
            wts[-1] = wsum
            cnts[-1] = c
    return np.repeat(np.asarray(vals), np.asarray(cnts))


def repair_call_prices(K: Any, C: Any, basis: ForwardBasis) -> dict[str, Any]:
    """Slope-isotonic repair (PREREG section 8).

    Weighted PAVA (weights ``dK``) makes chord slopes nondecreasing, the slopes
    are clipped to ``[-D, 0]``, prices are re-integrated with the L2-optimal
    level, then shifted up to meet ``C(K_N) >= 0`` and
    ``C(K_0) >= D (F - K_0)``. Arbitrage-free input is returned unchanged up to
    floating-point error.
    """
    Ka = _as_1d(K, "K", MAX_GRID)
    Ca = _as_1d(C, "C", MAX_GRID)
    if Ka.size != Ca.size or Ka.size < 3:
        raise ValueError("K and C must have equal length >= 3")
    _strictly_increasing(Ka)
    D, F = basis.discount, basis.forward
    dK = np.diff(Ka)
    s = _slopes(Ka, Ca)
    s_iso = np.clip(_pava_nondecreasing(s, dK), -D, 0.0)
    cum = np.concatenate([[0.0], np.cumsum(s_iso * dK)])
    level = float(np.mean(Ca - cum))
    Cr = level + cum
    shift = max(0.0, -float(Cr[-1]), D * (F - float(Ka[0])) - float(Cr[0]))
    Cr = Cr + shift
    return {
        "C": Cr,
        "slopes": s_iso,
        "max_abs_change": float(np.max(np.abs(Cr - Ca))),
        "level_shift": float(shift),
    }


# ---------------------------------------------------------------------------
# Discrete-atom density
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RNDensity:
    """Discrete risk-neutral density of piecewise-linear calls on a grid.

    Interior atoms sit at ``K_1 .. K_{N-1}``. ``left_mass`` lies somewhere in
    ``[0, K_0]`` and ``right_mass`` beyond ``K_N`` with mean ``right_mean``;
    both are grid-truncation masses whose location is not identified.
    """

    grid: np.ndarray
    calls: np.ndarray
    slopes: np.ndarray
    atom_strikes: np.ndarray
    atom_masses: np.ndarray
    left_mass: float
    right_mass: float
    right_mean: float
    total_mass: float
    negative_mass: float
    raw_negative_mass: float
    forward_interval: tuple[float, float]
    forward_ok: bool
    forward_interval_raw: tuple[float, float]
    forward_ok_raw: bool
    forward_ok_repaired: bool
    repaired: bool
    max_repair_change: float
    level_shift: float
    basis: ForwardBasis
    raw_report: dict[str, Any] = field(default_factory=dict)
    measure: str = MEASURE

    def cdf(self, K: Any) -> np.ndarray:
        """``Q(S_T <= K) = 1 + s(K)/D`` with ``s`` interpolated between chord midpoints."""
        Ka = _as_1d(K, "K", MAX_GRID)
        mids = 0.5 * (self.grid[1:] + self.grid[:-1])
        s = np.interp(Ka, mids, self.slopes)
        return np.clip(1.0 + s / self.basis.discount, 0.0, 1.0)

    def left_tail_probability(self, k_star: float) -> float:
        return float(self.cdf([k_star])[0])

    def mean_interval(self) -> tuple[float, float]:
        return self.forward_interval


def _forward_check(K0: float, C0: float, left_mass: float, D: float, F: float, tol: float) -> tuple[float, float, bool]:
    """``E_Q[S_T]`` range ``[C0/D + K0 (1 - m_L), C0/D + K0]`` and whether it holds ``F``.

    An inverted range (negative left mass) fails the check.
    """
    base = C0 / D
    lo = base + K0 * (1.0 - left_mass)
    hi = base + K0
    ok = bool(lo <= hi + tol and lo - tol <= F <= hi + tol)
    return float(lo), float(hi), ok


def density_from_call_grid(
    K: Any,
    C: Any,
    basis: ForwardBasis,
    repair: bool = True,
    fwd_tol_rel: float = DEFAULT_FWD_TOL_REL,
) -> RNDensity:
    """Breeden–Litzenberger atoms from call prices on a strike grid.

    Probability accounting: ``left_mass + sum(atoms) + right_mass == 1`` by
    construction. The forward interval is the range of ``E_Q[S_T]`` over all
    placements of the left mass in ``[0, K_0]``; for arbitrage-free calls
    priced on the same basis it contains ``F``.

    The forward check runs on the RAW prices and on the repaired prices, and
    ``forward_ok`` requires both. The raw check matters because the repair's
    upward level shift enforces ``C(K_0) >= D (F - K_0)`` by construction and
    would otherwise hide a discount-factor or forward mismatch.
    """
    Ka = _as_1d(K, "K", MAX_GRID)
    Ca = _as_1d(C, "C", MAX_GRID)
    if Ka.size != Ca.size or Ka.size < 3:
        raise ValueError("K and C must have equal length >= 3")
    _strictly_increasing(Ka)
    if not (0.0 <= fwd_tol_rel <= 0.1):
        raise ValueError("fwd_tol_rel must lie in [0, 0.1]")
    D, F = basis.discount, basis.forward
    raw = static_arbitrage_report(Ka, Ca, basis)
    if repair:
        rep = repair_call_prices(Ka, Ca, basis)
        Cu, s, max_change, shift = rep["C"], rep["slopes"], rep["max_abs_change"], rep["level_shift"]
    else:
        Cu, s, max_change, shift = Ca.copy(), _slopes(Ka, Ca), 0.0, 0.0
    left, interior, right = _atom_masses(Ka, Cu, D)
    total = left + float(np.sum(interior)) + right
    neg = float(np.sum(np.clip(-interior, 0.0, None)) + max(-left, 0.0) + max(-right, 0.0))
    right_mean = float(Ka[-1] + Cu[-1] / (D * right)) if right > 1e-15 else float(Ka[-1])
    tol = fwd_tol_rel * F
    f_lo, f_hi, ok_rep = _forward_check(float(Ka[0]), float(Cu[0]), left, D, F, tol)
    left_raw = 1.0 + float(_slopes(Ka, Ca)[0]) / D
    r_lo, r_hi, ok_raw = _forward_check(float(Ka[0]), float(Ca[0]), left_raw, D, F, tol)
    return RNDensity(
        grid=Ka,
        calls=np.asarray(Cu, dtype=float),
        slopes=np.asarray(s, dtype=float),
        atom_strikes=Ka[1:-1].copy(),
        atom_masses=np.asarray(interior, dtype=float),
        left_mass=float(left),
        right_mass=float(right),
        right_mean=right_mean,
        total_mass=float(total),
        negative_mass=neg,
        raw_negative_mass=float(raw["negative_atom_mass"]),
        forward_interval=(float(f_lo), float(f_hi)),
        forward_ok=bool(ok_raw and ok_rep),
        forward_interval_raw=(float(r_lo), float(r_hi)),
        forward_ok_raw=bool(ok_raw),
        forward_ok_repaired=bool(ok_rep),
        repaired=bool(repair),
        max_repair_change=float(max_change),
        level_shift=float(shift),
        basis=basis,
        raw_report=raw,
    )


def reintegrate_call_prices(density: RNDensity, K: Any) -> np.ndarray:
    """``D * E_Q[(S_T - K)^+]`` from the atoms, for ``K`` inside the grid.

    Outside ``[K_0, K_N]`` the result depends on where the truncation masses
    sit, which is not identified, so such strikes raise ``ValueError``.
    """
    Ka = _as_1d(K, "K", MAX_GRID)
    g = density.grid
    if np.any(Ka < g[0]) or np.any(Ka > g[-1]):
        raise ValueError("reintegration is identified only inside the grid")
    D = density.basis.discount
    pay = np.maximum(density.atom_strikes[None, :] - Ka[:, None], 0.0) @ density.atom_masses
    pay = pay + density.right_mass * np.maximum(density.right_mean - Ka, 0.0)
    return D * pay


def reintegration_check(
    density: RNDensity, K: Any, lo: Any, hi: Any, tol_rel: float = 1e-6
) -> dict[str, Any]:
    """Do reintegrated prices fall inside source-compatible price intervals?"""
    Ka = _as_1d(K, "K")
    loa = _as_1d(lo, "lo")
    hia = _as_1d(hi, "hi")
    if not (Ka.size == loa.size == hia.size):
        raise ValueError("K, lo and hi must have equal length")
    if np.any(loa > hia):
        raise ValueError("price intervals must have lo <= hi")
    C = reintegrate_call_prices(density, Ka)
    tol = tol_rel * density.basis.forward
    excess = np.maximum(np.maximum(loa - C, C - hia), 0.0)
    half = np.maximum((hia - loa) / 2.0, 1e-300)
    return {
        "n": int(Ka.size),
        "n_outside": int(np.sum(excess > tol)),
        "max_excess": float(np.max(excess)) if excess.size else 0.0,
        "max_excess_over_half_width": float(np.max(excess / half)) if excess.size else 0.0,
        "within": bool(np.all(excess <= tol)),
        "tolerance": float(tol),
    }


def extrapolation_mass(density: RNDensity, k_min_quoted: float, k_max_quoted: float) -> dict[str, float]:
    """Mass outside the quoted strike range and outside the grid."""
    if not (k_min_quoted <= k_max_quoted):
        raise ValueError("quoted range must have min <= max")
    below = float(density.cdf([k_min_quoted])[0])
    above = float(1.0 - density.cdf([k_max_quoted])[0])
    return {
        "mass_below_quoted": below,
        "mass_above_quoted": above,
        "extrapolated_mass": below + above,
        "grid_truncation_mass": float(density.left_mass + density.right_mass),
        "left_truncation_mass": float(density.left_mass),
        "right_truncation_mass": float(density.right_mass),
    }


# ---------------------------------------------------------------------------
# Model-free identified bounds
# ---------------------------------------------------------------------------


def tail_probability_bounds(
    K: Any,
    C_lo: Any,
    C_hi: Any,
    basis: ForwardBasis,
    k_star: float,
    include_zero_anchor: bool = True,
) -> dict[str, Any]:
    """Identified interval ``[L, U]`` for ``Q(S_T <= k_star)`` from call-price bands.

    Left chords use ``K_a < K_b <= k_star`` (plus the exact anchor
    ``C(0) = D F``); right chords use ``k_star <= K_c < K_d``. Convexity of the
    true call function makes every chord a valid bound. ``L > U`` means the
    bands are inconsistent with static no-arbitrage.
    """
    Ka = _as_1d(K, "K")
    lo = _as_1d(C_lo, "C_lo")
    hi = _as_1d(C_hi, "C_hi")
    if not (Ka.size == lo.size == hi.size):
        raise ValueError("K, C_lo and C_hi must have equal length")
    if np.any(Ka <= 0):
        raise ValueError("strikes must be > 0")
    if np.any(lo > hi):
        raise ValueError("bands must have lo <= hi")
    if not (math.isfinite(k_star) and k_star > 0):
        raise ValueError("k_star must be finite and > 0")
    order = np.argsort(Ka, kind="mergesort")
    Ka, lo, hi = Ka[order], lo[order], hi[order]
    D, F = basis.discount, basis.forward

    left_sel = Ka <= k_star
    kl, lol, hil = Ka[left_sel], lo[left_sel], hi[left_sel]
    if include_zero_anchor:
        kl = np.concatenate([[0.0], kl])
        lol = np.concatenate([[D * F], lol])
        hil = np.concatenate([[D * F], hil])
    L_raw = None
    n_left = 0
    if kl.size >= 2:
        a, b = np.triu_indices(kl.size, k=1)
        dk = kl[b] - kl[a]
        ok = dk > 0
        if np.any(ok):
            slopes = (lol[b][ok] - hil[a][ok]) / dk[ok]
            n_left = int(np.sum(ok))
            L_raw = 1.0 + float(np.max(slopes)) / D
    right_sel = Ka >= k_star
    kr, lor, hir = Ka[right_sel], lo[right_sel], hi[right_sel]
    U_raw = None
    n_right = 0
    if kr.size >= 2:
        c, d = np.triu_indices(kr.size, k=1)
        dk = kr[d] - kr[c]
        ok = dk > 0
        if np.any(ok):
            slopes = (hir[d][ok] - lor[c][ok]) / dk[ok]
            n_right = int(np.sum(ok))
            U_raw = 1.0 + float(np.min(slopes)) / D
    L = 0.0 if L_raw is None else float(min(max(L_raw, 0.0), 1.0))
    U = 1.0 if U_raw is None else float(min(max(U_raw, 0.0), 1.0))
    consistent = bool(L <= U)
    denom = (U + L) / 2.0
    rel_width = float((U - L) / denom) if (consistent and denom > 0) else float("inf")
    return {
        "k_star": float(k_star),
        "L": L,
        "U": U,
        "L_unclipped": L_raw,
        "U_unclipped": U_raw,
        "consistent": consistent,
        "width": float(U - L),
        "relative_width": rel_width,
        "n_left_chords": n_left,
        "n_right_chords": n_right,
        "n_quoted_at_or_below": int(np.sum(left_sel)),
        "n_quoted_at_or_above": int(np.sum(right_sel)),
        "measure": MEASURE,
    }


def distance_to_interval(x: float, L: float, U: float) -> float:
    """Distance from ``x`` to ``[L, U]`` (0 inside)."""
    if not (math.isfinite(x) and math.isfinite(L) and math.isfinite(U)):
        return float("nan")
    if x < L:
        return float(L - x)
    if x > U:
        return float(x - U)
    return 0.0


# ---------------------------------------------------------------------------
# Smile
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Smile:
    """Implied-vol smile in log-moneyness ``k = ln(K/F)`` with explicit wings.

    Inside ``[k_min, k_max]`` the smile interpolates (PCHIP) and is floored at
    ``IV_FLOOR``. Outside, it extends linearly with the fitted wing slopes,
    floored at ``IV_FLOOR`` and capped by ``max(sqrt(2|k|/T), IV_FLOOR)`` when
    ``lee_cap`` is set.
    """

    knots_k: np.ndarray
    knots_iv: np.ndarray
    T: float
    left_slope: float
    right_slope: float
    lee_cap: bool = True
    label: str = ""

    @property
    def k_min(self) -> float:
        return float(self.knots_k[0])

    @property
    def k_max(self) -> float:
        return float(self.knots_k[-1])

    def extrapolated(self, k: Any) -> np.ndarray:
        ka = _as_1d(k, "k", MAX_GRID)
        return (ka < self.k_min) | (ka > self.k_max)

    def __call__(self, k: Any) -> np.ndarray:
        ka = _as_1d(k, "k", MAX_GRID)
        kk, vv = self.knots_k, self.knots_iv
        if kk.size >= 2:
            inner = PchipInterpolator(kk, vv, extrapolate=False)(np.clip(ka, kk[0], kk[-1]))
        else:
            inner = np.full(ka.shape, float(vv[0]))
        out = np.maximum(inner, IV_FLOOR)
        left = ka < kk[0]
        right = ka > kk[-1]
        lin = np.where(
            left,
            vv[0] + self.left_slope * (ka - kk[0]),
            vv[-1] + self.right_slope * (ka - kk[-1]),
        )
        wing = np.maximum(lin, IV_FLOOR)
        if self.lee_cap:
            cap = np.maximum(np.sqrt(2.0 * np.abs(ka) / self.T), IV_FLOOR)
            wing = np.minimum(wing, cap)
        return np.where(left | right, wing, out)


def _ls_slope(x: np.ndarray, y: np.ndarray) -> float:
    if x.size < 2:
        return 0.0
    xm = x - x.mean()
    den = float(np.sum(xm * xm))
    if den <= 0:
        return 0.0
    return float(np.sum(xm * (y - y.mean())) / den)


def whittaker_smooth(k: np.ndarray, iv: np.ndarray, lam: float) -> np.ndarray:
    """Solve ``(I + lam D2' W D2) s = iv`` on ``u = (k - k_min)/(k_max - k_min)``."""
    n = k.size
    if n < 3 or lam == 0.0:
        return iv.astype(float).copy()
    u = (k - k[0]) / (k[-1] - k[0])
    D2 = np.zeros((n - 2, n))
    for i in range(1, n - 1):
        h0 = u[i] - u[i - 1]
        h1 = u[i + 1] - u[i]
        D2[i - 1, i - 1] = 2.0 / (h0 * (h0 + h1))
        D2[i - 1, i] = -2.0 / (h0 * h1)
        D2[i - 1, i + 1] = 2.0 / (h1 * (h0 + h1))
    w = (u[2:] - u[:-2]) / 2.0
    A = np.eye(n) + lam * (D2.T * w) @ D2
    return np.linalg.solve(A, iv.astype(float))


def fit_smile(k: Any, iv: Any, T: float, lam: float = 1e-3, m: int = 5, label: str = "C") -> Smile:
    """Module smile (competitor C in the PREREG): Whittaker + PCHIP + capped linear wings."""
    ka = _as_1d(k, "k")
    iva = _as_1d(iv, "iv")
    if ka.size != iva.size:
        raise ValueError("k and iv must have equal length")
    if np.any(iva <= 0):
        raise ValueError("iv must be > 0")
    if not (math.isfinite(T) and 0.0 < T <= MAX_T_YEARS):
        raise ValueError("T out of range")
    if not (math.isfinite(lam) and 0.0 <= lam <= 1e6):
        raise ValueError("lam must lie in [0, 1e6]")
    if isinstance(m, bool) or not (1 <= int(m) <= 1000):
        raise ValueError("m must lie in [1, 1000]")
    order = np.argsort(ka, kind="mergesort")
    ka, iva = ka[order], iva[order]
    _strictly_increasing(ka, "log-moneyness")
    s = whittaker_smooth(ka, iva, float(lam)) if ka.size >= 2 else iva.copy()
    mm = min(int(m), ka.size)
    left_slope = _ls_slope(ka[:mm], s[:mm])
    right_slope = _ls_slope(ka[-mm:], s[-mm:])
    return Smile(ka, s, float(T), left_slope, right_slope, True, label)


def two_point_smile(k_a: float, iv_a: float, k_b: float, iv_b: float, T: float, label: str = "B1") -> Smile:
    """Linear-in-k smile through two points (flat if their ``k`` coincide), same floor and cap."""
    for v in (k_a, iv_a, k_b, iv_b, T):
        if not math.isfinite(v):
            raise ValueError("two_point_smile inputs must be finite")
    if iv_a <= 0 or iv_b <= 0:
        raise ValueError("iv must be > 0")
    if k_a == k_b:
        return Smile(np.array([k_a]), np.array([0.5 * (iv_a + iv_b)]), float(T), 0.0, 0.0, True, label)
    (k0, v0), (k1, v1) = sorted([(k_a, iv_a), (k_b, iv_b)])
    slope = (v1 - v0) / (k1 - k0)
    return Smile(np.array([k0, k1]), np.array([v0, v1]), float(T), slope, slope, True, label)


def flat_smile(iv0: float, T: float, label: str = "B0") -> Smile:
    """Constant smile (no wing cap): the flat baseline."""
    if not (math.isfinite(iv0) and iv0 > 0):
        raise ValueError("iv0 must be finite and > 0")
    return Smile(np.array([0.0]), np.array([float(iv0)]), float(T), 0.0, 0.0, False, label)


def default_grid(basis: ForwardBasis, smile: Smile, n_nodes: int = DEFAULT_GRID_NODES) -> np.ndarray:
    """Uniform-in-K grid on ``[F min(e^{-8 s0 sqrt T}, 0.6), F max(e^{8 s0 sqrt T}, 1.4)]``."""
    if isinstance(n_nodes, bool) or not (3 <= int(n_nodes) <= MAX_GRID):
        raise ValueError(f"n_nodes must lie in [3, {MAX_GRID}]")
    s0 = float(smile([0.0])[0])
    width = 8.0 * s0 * math.sqrt(basis.T)
    lo = basis.forward * min(math.exp(-width), 0.6)
    hi = basis.forward * max(math.exp(width), 1.4)
    return np.linspace(lo, hi, int(n_nodes))


def density_from_smile(
    smile: Smile, basis: ForwardBasis, n_nodes: int = DEFAULT_GRID_NODES, repair: bool = True
) -> RNDensity:
    """Grid -> Black-76 calls -> arbitrage report -> repair -> atoms."""
    K = default_grid(basis, smile, n_nodes)
    vol = smile(np.log(K / basis.forward))
    C = black76_price(basis, K, vol, True)
    return density_from_call_grid(K, C, basis, repair=repair)


def q_tail_probability(smile: Smile, basis: ForwardBasis, k_star: float, n_nodes: int = DEFAULT_GRID_NODES) -> float:
    """``q_hat = 1 + s(K*)/D`` from the repaired grid density, clipped to ``[0, 1]``."""
    if not (math.isfinite(k_star) and k_star > 0):
        raise ValueError("k_star must be finite and > 0")
    return density_from_smile(smile, basis, n_nodes).left_tail_probability(k_star)


# ---------------------------------------------------------------------------
# Uncertainty and identification
# ---------------------------------------------------------------------------


def perturbation_interval(
    basis: ForwardBasis,
    k: Any,
    iv: Any,
    half_width: Any,
    k_star: float,
    fitter: Callable[[np.ndarray, np.ndarray], Smile],
    n_draws: int = 100,
    seed: int = 13013,
    n_nodes: int = DEFAULT_GRID_NODES,
) -> dict[str, Any]:
    """Spread of ``q_hat`` when every quote's iv is drawn uniformly inside its band.

    A wider band widens the interval; a zero band collapses it to one value.
    The interval is a statement about quote uncertainty, never a sharper
    probability.
    """
    ka = _as_1d(k, "k")
    iva = _as_1d(iv, "iv")
    hwa = np.broadcast_to(_as_1d(half_width, "half_width"), ka.shape).astype(float)
    if iva.size != ka.size:
        raise ValueError("k and iv must have equal length")
    if np.any(hwa < 0):
        raise ValueError("half_width must be >= 0")
    if isinstance(n_draws, bool) or not (1 <= int(n_draws) <= MAX_DRAWS):
        raise ValueError(f"n_draws must lie in [1, {MAX_DRAWS}]")
    rng = np.random.default_rng(int(seed))
    lo = np.maximum(iva - hwa, VOL_MIN)
    hi = iva + hwa
    vals = []
    for _ in range(int(n_draws)):
        u = rng.random(ka.size)
        draw = lo + u * (hi - lo)
        q = q_tail_probability(fitter(ka, draw), basis, k_star, n_nodes)
        vals.append(q)
    v = np.asarray(vals, dtype=float)
    fin = v[np.isfinite(v)]
    if fin.size == 0:
        return {"n_draws": int(n_draws), "n_finite": 0, "lo": None, "hi": None, "p05": None, "p95": None,
                "width": None, "seed": int(seed), "measure": MEASURE}
    return {
        "n_draws": int(n_draws),
        "n_finite": int(fin.size),
        "lo": float(fin.min()),
        "hi": float(fin.max()),
        "p05": float(np.quantile(fin, 0.05)),
        "p95": float(np.quantile(fin, 0.95)),
        "width": float(fin.max() - fin.min()),
        "seed": int(seed),
        "measure": MEASURE,
    }


def classify_identification(
    n_quoted_at_or_below: int,
    k_star_extrapolated: bool,
    raw_negative_mass: float,
    bounds: dict[str, Any] | None,
) -> tuple[str, list[str]]:
    """``PRICE_BOUNDS_ONLY`` vs ``FULL_DENSITY`` by the frozen PREREG section 13 rules."""
    reasons: list[str] = []
    if int(n_quoted_at_or_below) < MIN_WING_STRIKES:
        reasons.append("weak_wing_support")
    if bool(k_star_extrapolated):
        reasons.append("k_star_extrapolated")
    if not math.isfinite(raw_negative_mass) or raw_negative_mass > NEG_MASS_TOL:
        reasons.append("unstable_curvature")
    if bounds is None:
        reasons.append("no_identified_interval")
    else:
        if not bounds.get("consistent", False):
            reasons.append("identified_interval_inconsistent")
        elif not (bounds.get("relative_width", float("inf")) <= REL_WIDTH_MAX):
            reasons.append("identified_interval_too_wide")
    return (IDENT_BOUNDS if reasons else IDENT_FULL), reasons


def to_physical(*_args: Any, **_kwargs: Any) -> None:
    """Refuse any Q -> P conversion (Q and P stay explicitly different)."""
    raise MeasureError(
        "risk-neutral (Q) quantities cannot be converted to physical (P) probabilities "
        "without a pricing-kernel model; this research module refuses"
    )


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------


def rn_tail_report(
    basis: ForwardBasis,
    K: Sequence[float],
    iv: Sequence[float],
    is_call: Sequence[bool],
    k_star_ratio: float = 0.90,
    lam: float = 1e-3,
    m: int = 5,
    band_scale: float = 1.0,
    n_draws: int = 100,
    seed: int = 13013,
    n_nodes: int = DEFAULT_GRID_NODES,
) -> dict[str, Any]:
    """Full research report for one surface; never admitted, never a P quantity.

    Under ``PRICE_BOUNDS_ONLY`` the point estimate and the model perturbation
    interval are withheld and only the identified price-implied bounds are
    reported.
    """
    Ka = _as_1d(K, "K")
    iva = _as_1d(iv, "iv")
    if Ka.size != iva.size or Ka.size < 2:
        raise ValueError("K and iv must have equal length >= 2")
    calls = _as_bool_1d(is_call, Ka.size, "is_call")
    if np.any(Ka <= 0) or np.any(iva <= 0):
        raise ValueError("K and iv must be > 0")
    if not (math.isfinite(k_star_ratio) and 0.0 < k_star_ratio < 10.0):
        raise ValueError("k_star_ratio out of range")
    F = basis.forward
    k_star = k_star_ratio * F
    k = np.log(Ka / F)
    hw = iv_half_width(k, band_scale)
    _, lo, hi = call_equivalent_bands(basis, Ka, iva, calls, hw)
    bounds = tail_probability_bounds(Ka, lo, hi, basis, k_star)

    def fitter(kk: np.ndarray, vv: np.ndarray) -> Smile:
        return fit_smile(kk, vv, basis.T, lam, m)

    smile = fitter(k, iva)
    density = density_from_smile(smile, basis, n_nodes)
    k_star_extrap = bool(smile.extrapolated([math.log(k_star_ratio)])[0])
    mode, reasons = classify_identification(
        bounds["n_quoted_at_or_below"], k_star_extrap, density.raw_negative_mass, bounds
    )
    inside = (Ka >= density.grid[0]) & (Ka <= density.grid[-1])
    reint = reintegration_check(density, Ka[inside], lo[inside], hi[inside]) if np.any(inside) else None
    extrap = extrapolation_mass(density, float(Ka.min()), float(Ka.max()))
    q_hat = density.left_tail_probability(k_star)
    pert = None
    if mode == IDENT_FULL:
        pert = perturbation_interval(basis, k, iva, hw, k_star, fitter, n_draws, seed, n_nodes)
    half = np.maximum((hi - lo) / 2.0, 1e-300)
    return {
        "schema": SCHEMA,
        "research_only": RESEARCH_ONLY,
        "admitted": False,
        "admission_status": ADMISSION_STATUS,
        "missing_inputs": list(MISSING_INPUTS),
        "verdict": VERDICT,
        "label": PROXY_LABEL,
        "measure": MEASURE,
        "measure_label": MEASURE_LABEL,
        "basis": basis.as_dict(),
        "k_star": float(k_star),
        "k_star_ratio": float(k_star_ratio),
        "identification": mode,
        "identification_reasons": reasons,
        "identified_bounds": {"L": bounds["L"], "U": bounds["U"], "consistent": bounds["consistent"],
                              "relative_width": bounds["relative_width"]},
        "point_estimate": float(q_hat) if mode == IDENT_FULL else None,
        "perturbation_interval": pert,
        "density": {
            "total_mass": density.total_mass,
            "negative_mass_after_repair": density.negative_mass,
            "raw_negative_mass": density.raw_negative_mass,
            "raw_butterfly_violations": int(density.raw_report["n_butterfly_violations"]),
            "max_repair_change": density.max_repair_change,
            "repair_over_median_half_width": float(density.max_repair_change / float(np.median(half))),
            "forward_interval": list(density.forward_interval),
            "forward_interval_raw": list(density.forward_interval_raw),
            "forward": float(F),
            "forward_ok": density.forward_ok,
            "forward_ok_raw": density.forward_ok_raw,
            "forward_ok_repaired": density.forward_ok_repaired,
            "level_shift": density.level_shift,
            **extrap,
        },
        "reintegration": reint,
        "smile": {"k_min": smile.k_min, "k_max": smile.k_max, "lam": float(lam), "m": int(m),
                  "k_star_extrapolated": k_star_extrap},
        "n_quotes": int(Ka.size),
    }
