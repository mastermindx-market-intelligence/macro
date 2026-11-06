from __future__ import annotations

# The quant-assessment commission requires every new .py file to begin with the
# ``from __future__`` import, so the module docstring is bound to ``__doc__``
# explicitly on the next statement instead of being the first statement.
__doc__ = """RESEARCH REFERENCE — NOT WIRED.

Q02 American-exercise and discrete-dividend pricing / Greek qualification
(quant assessment 2026-10, research staging only).

VERDICT: INSUFFICIENT_DATA. The retained local data do not identify per-contract
exercise style, deliverable/multiplier, settlement clock, a point-in-time declared
cash-dividend schedule or an option price, so the brief's falsifier applies: only
the fail-closed applicability guard is meaningful on real contracts, and every
model output on real contracts stays UNAVAILABLE. The numerical reference below is
qualified on synthetic contracts only (see
research/quant_assessment_2026_10/Q02_american_exercise_greeks/VERDICT.md).

Nothing imports this module. It registers, schedules, promotes, gates and
activates nothing; ``RESEARCH_ONLY`` is True. It performs no I/O, reads no wall
clock and contains no calendar date: time is integer minute indexes from an
arbitrary origin plus a declared minutes-per-year.

Contents (all pure functions over bounded inputs):

* ``bs_price`` / ``bs_greeks`` — analytic continuous-yield European Black–Scholes.
  ``bs_greeks`` reproduces the formula of ``engine/greeks.py`` operation for
  operation (delta, gamma, vanna per 1.00 vol, charm per YEAR = -d delta / d tau).
* ``fd_solve`` — uniform-S-grid Crank–Nicolson with a Rannacher start (the first two
  CN steps after expiry and after each dividend jump become four implicit-Euler
  half steps), Ikonen–Toivanen splitting for the American constraint, and a
  declared cash-dividend jump ``V(S, t_d-) = V(max(S - D, 0), t_d+)`` (American:
  maximum with the immediate payoff). The spot is always a grid node.
* ``qualify_fd`` — N / 2N / 4N grid refinement of price, delta, gamma, vanna and
  charm with the frozen CONVERGED / INTERVAL / UNAVAILABLE rules, the
  near-exercise-boundary override and the ex-dividend charm-stencil override.
* ``crr_price`` and ``european_one_dividend_quadrature`` — independent references
  (CRR lattice with Vellekoop–Nieuwenhuis interpolation at the ex-dividend step;
  Gauss–Hermite quadrature for a European option with one cash dividend).
* ``point_in_time_dividends`` / ``select_model`` / ``price_contract`` — the
  fail-closed applicability selector. It never assumes a 100-share contract,
  never defaults a settlement clock and never infers a dividend.
* ``convert_size`` / ``convert_vol`` / ``convert_vega`` / ``convert_charm`` —
  explicit unit converters with no default multiplier or day basis.
"""

import math
from dataclasses import dataclass
from typing import Mapping, Optional, Sequence, Tuple

import numpy as np
from scipy.linalg import solve_banded

RESEARCH_ONLY = True
VERDICT = "INSUFFICIENT_DATA"

# --------------------------------------------------------------------------------------
# Frozen constants (PREREG.md sections 6-8)
# --------------------------------------------------------------------------------------

GRID_LEVELS: Tuple[int, int, int] = (100, 200, 400)
VOL_BUMP = 0.01
BOUNDARY_TOL = 1e-8
QUANTITIES: Tuple[str, ...] = ("price", "delta", "gamma", "vanna", "charm")
REFINEMENT_TOLERANCES: Mapping[str, Tuple[float, float]] = {
    "price": (1e-3, 1e-4),
    "delta": (5e-4, 0.0),
    "gamma": (2e-4, 1e-2),
    "vanna": (5e-3, 2e-2),
    "charm": (5e-3, 2e-2),
}

CONVERGED = "CONVERGED"
INTERVAL = "INTERVAL"
UNAVAILABLE = "UNAVAILABLE"

AMERICAN = "AMERICAN"
EUROPEAN = "EUROPEAN"
SHARES = "SHARES"
CASH_INDEX = "CASH_INDEX"
AM_OPEN = "AM_OPEN"
PM_CLOSE = "PM_CLOSE"
DECLARED = "DECLARED"
ESTIMATED = "ESTIMATED"
CANCELLED = "CANCELLED"

MODEL_EUROPEAN_BS_CONTINUOUS_YIELD = "EUROPEAN_BS_CONTINUOUS_YIELD"
MODEL_EUROPEAN_BS_EQUIVALENT = "EUROPEAN_BS_EQUIVALENT"
MODEL_EUROPEAN_FD_DISCRETE_DIVIDEND = "EUROPEAN_FD_DISCRETE_DIVIDEND"
MODEL_AMERICAN_FD = "AMERICAN_FD"
MODEL_UNAVAILABLE = "UNAVAILABLE"

# Input bounds (the module refuses anything outside them).
SIGMA_BOUNDS = (0.01, 5.0)
RATE_BOUNDS = (-0.1, 0.5)
YIELD_BOUNDS = (-0.1, 0.5)
T_MAX_YEARS = 10.0
PRICE_MAX = 1e7
LEVEL_BOUNDS = (20, 2000)
CRR_STEP_BOUNDS = (10, 20000)

_SQRT2 = math.sqrt(2.0)
_SQRT2PI = math.sqrt(2.0 * math.pi)


# --------------------------------------------------------------------------------------
# Analytic continuous-yield Black-Scholes (formula identical to engine/greeks.py)
# --------------------------------------------------------------------------------------

def _ncdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / _SQRT2))


def _npdf(x: float) -> float:
    return math.exp(-0.5 * x * x) / _SQRT2PI


def _finite_pos(x: float) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x) and x > 0.0


def bs_greeks(S: float, K: float, T: float, sigma: float, is_call: bool,
              r: float = 0.0, q: float = 0.0) -> Tuple[float, float, float, float]:
    """(delta, gamma, vanna, charm) of a European option, continuous yield q.

    Same expressions and operation order as ``engine.greeks.bs_greeks``: vanna is
    d delta / d sigma per 1.00 vol; charm is per YEAR, ``= -d delta / d tau``.
    Degenerate inputs return NaNs (no exception), as the incumbent does.
    """
    nan = float("nan")
    if not (_finite_pos(S) and _finite_pos(K) and _finite_pos(T) and _finite_pos(sigma)):
        return nan, nan, nan, nan
    sqrtT = math.sqrt(T)
    d1 = (math.log(S / K) + (r - q + 0.5 * sigma * sigma) * T) / (sigma * sqrtT)
    d2 = d1 - sigma * sqrtT
    eqT = math.exp(-q * T)
    pdf = _npdf(d1)
    gamma = eqT * pdf / (S * sigma * sqrtT)
    vanna = -eqT * pdf * d2 / sigma
    common = eqT * pdf * (2.0 * (r - q) * T - d2 * sigma * sqrtT) / (2.0 * T * sigma * sqrtT)
    if is_call:
        delta = eqT * _ncdf(d1)
        charm = q * eqT * _ncdf(d1) - common
    else:
        delta = eqT * (_ncdf(d1) - 1.0)
        charm = -q * eqT * _ncdf(-d1) - common
    return delta, gamma, vanna, charm


def bs_price(S: float, K: float, T: float, sigma: float, is_call: bool,
             r: float = 0.0, q: float = 0.0) -> float:
    """European Black–Scholes–Merton price with continuous yield q (per share).

    ``S == 0`` is allowed (absorbed underlying): the call is worth 0 and the put
    ``K exp(-rT)``. Other degenerate inputs return NaN.
    """
    if isinstance(S, (int, float)) and not isinstance(S, bool) and S == 0.0 \
            and _finite_pos(K) and _finite_pos(T):
        return 0.0 if is_call else K * math.exp(-r * T)
    if not (_finite_pos(S) and _finite_pos(K) and _finite_pos(T) and _finite_pos(sigma)):
        return float("nan")
    sqrtT = math.sqrt(T)
    d1 = (math.log(S / K) + (r - q + 0.5 * sigma * sigma) * T) / (sigma * sqrtT)
    d2 = d1 - sigma * sqrtT
    if is_call:
        return S * math.exp(-q * T) * _ncdf(d1) - K * math.exp(-r * T) * _ncdf(d2)
    return K * math.exp(-r * T) * _ncdf(-d2) - S * math.exp(-q * T) * _ncdf(-d1)


def bs_vega(S: float, K: float, T: float, sigma: float, r: float = 0.0, q: float = 0.0) -> float:
    """Black–Scholes vega per 1.00 (decimal) vol, per share."""
    if not (_finite_pos(S) and _finite_pos(K) and _finite_pos(T) and _finite_pos(sigma)):
        return float("nan")
    sqrtT = math.sqrt(T)
    d1 = (math.log(S / K) + (r - q + 0.5 * sigma * sigma) * T) / (sigma * sqrtT)
    return S * math.exp(-q * T) * _npdf(d1) * sqrtT


# --------------------------------------------------------------------------------------
# Input checks
# --------------------------------------------------------------------------------------

def _num(x: object) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(float(x))


def _check_pricing_inputs(S: float, K: float, T: float, sigma: float, r: float, q: float) -> None:
    if not (_num(S) and 0.0 < S <= PRICE_MAX):
        raise ValueError("spot out of bounds")
    if not (_num(K) and 0.0 < K <= PRICE_MAX):
        raise ValueError("strike out of bounds")
    if not (_num(T) and 0.0 < T <= T_MAX_YEARS):
        raise ValueError("time to expiry out of bounds")
    if not (_num(sigma) and SIGMA_BOUNDS[0] <= sigma <= SIGMA_BOUNDS[1]):
        raise ValueError("volatility out of bounds")
    if not (_num(r) and RATE_BOUNDS[0] <= r <= RATE_BOUNDS[1]):
        raise ValueError("rate out of bounds")
    if not (_num(q) and YIELD_BOUNDS[0] <= q <= YIELD_BOUNDS[1]):
        raise ValueError("continuous yield out of bounds")


def _normalise_dividends(dividends: Sequence[Tuple[float, float]], T: float) -> Tuple[Tuple[float, float], ...]:
    """Sort, check and merge same-time cash dividends ``(t_years_from_valuation, amount)``."""
    merged: dict = {}
    for item in dividends:
        if len(item) != 2:
            raise ValueError("dividend must be (t_years, amount)")
        t, amt = item
        if not (_num(t) and 0.0 < t <= T):
            raise ValueError("dividend time must lie in (0, T]")
        if not (_num(amt) and 0.0 <= amt <= PRICE_MAX):
            raise ValueError("dividend amount out of bounds")
        merged[float(t)] = merged.get(float(t), 0.0) + float(amt)
    return tuple(sorted(merged.items()))


# --------------------------------------------------------------------------------------
# Finite-difference solver (Crank-Nicolson + Rannacher + Ikonen-Toivanen + cash jumps)
# --------------------------------------------------------------------------------------

@dataclass(frozen=True)
class FDGrid:
    """Uniform S-grid with the spot on node ``j``: ``S_i = i * dS``, ``i = 0..M``."""
    M: int
    dS: float
    j: int

    @property
    def s_max(self) -> float:
        return self.M * self.dS


@dataclass(frozen=True)
class FDResult:
    price: float
    delta: float
    gamma: float
    charm: float
    grid: FDGrid
    s_nodes: np.ndarray
    values: np.ndarray
    boundary: Optional[float]
    n_upwind: int
    n_time_steps: int


def build_grid(S0: float, K: float, T: float, sigma: float, M: int,
               dividend_total: float = 0.0) -> FDGrid:
    """Spot-on-node uniform grid. ``S_max`` targets ``max(S_hi e^{6 sigma sqrt T}, 2 S_hi) + sum D``."""
    if not (isinstance(M, int) and not isinstance(M, bool) and LEVEL_BOUNDS[0] <= M <= LEVEL_BOUNDS[1]):
        raise ValueError("grid level out of bounds")
    s_hi = max(S0, K)
    target = max(s_hi * math.exp(6.0 * sigma * math.sqrt(T)), 2.0 * s_hi) + dividend_total
    j = int(round(M * S0 / target))
    j = min(max(j, 2), M - 2)
    return FDGrid(M=M, dS=S0 / j, j=j)


def _payoff(S: np.ndarray, K: float, is_call: bool) -> np.ndarray:
    return np.maximum(S - K, 0.0) if is_call else np.maximum(K - S, 0.0)


def _coefficients(M: int, sigma: float, r: float, q: float) -> Tuple[np.ndarray, np.ndarray, np.ndarray, int]:
    """Central-difference coefficients on interior nodes, upwinded where a or c < 0."""
    i = np.arange(1, M, dtype=float)
    s2 = sigma * sigma * i * i
    mu = (r - q) * i
    a = 0.5 * s2 - 0.5 * mu
    b = -s2 - r
    c = 0.5 * s2 + 0.5 * mu
    bad = (a < 0.0) | (c < 0.0)
    n_up = int(bad.sum())
    if n_up:
        if r - q >= 0.0:
            a = np.where(bad, 0.5 * s2, a)
            b = np.where(bad, -s2 - mu - r, b)
            c = np.where(bad, 0.5 * s2 + mu, c)
        else:
            a = np.where(bad, 0.5 * s2 - mu, a)
            b = np.where(bad, -s2 + mu - r, b)
            c = np.where(bad, 0.5 * s2, c)
    return a, b, c, n_up


def _boundaries(tau: float, s_max: float, K: float, r: float, q: float, is_call: bool,
                american: bool, divs_tau: Tuple[Tuple[float, float], ...]) -> Tuple[float, float]:
    if is_call:
        pv_div = sum(d * math.exp(-r * (tau - td)) for td, d in divs_tau if td < tau)
        upper = max(0.0, s_max * math.exp(-q * tau) - pv_div - K * math.exp(-r * tau))
        if american:
            upper = max(upper, s_max - K)
        return 0.0, upper
    lower = K * math.exp(-r * tau)
    if american:
        lower = max(K, lower)
    return lower, 0.0


def _time_plan(T: float, M: int, divs_tau: Tuple[Tuple[float, float], ...]) -> list:
    """Segments ``(tau_start, tau_end, n_steps)`` with every ex-time a node."""
    pts = sorted({0.0, T} | {td for td, _ in divs_tau if 0.0 < td < T})
    plan = []
    for lo, hi in zip(pts[:-1], pts[1:]):
        n = max(2, int(math.ceil(M * (hi - lo) / T - 1e-12)))
        plan.append((lo, hi, n))
    return plan


def fd_solve(S0: float, K: float, T: float, sigma: float, r: float, q: float, is_call: bool,
             american: bool, dividends: Sequence[Tuple[float, float]] = (), M: int = 400,
             grid: Optional[FDGrid] = None) -> FDResult:
    """Price, delta, gamma and charm (per year) at the spot node.

    ``dividends`` are ``(t_years_from_valuation, cash_amount)`` with ``0 < t <= T``.
    Pass ``grid`` to reuse a grid (fixed-grid volatility bumps for vanna).
    """
    _check_pricing_inputs(S0, K, T, sigma, r, q)
    divs = _normalise_dividends(dividends, T)
    if grid is None:
        grid = build_grid(S0, K, T, sigma, M, sum(d for _, d in divs))
    Mg, dS, j = grid.M, grid.dS, grid.j
    S = np.arange(Mg + 1, dtype=float) * dS
    g = _payoff(S, K, is_call)
    a, b, c, n_up = _coefficients(Mg, sigma, r, q)
    # tau = time to expiry; a dividend at t (from valuation) sits at tau = T - t.
    divs_tau = tuple(sorted(((max(T - t, 0.0), d) for t, d in divs), key=lambda x: x[0]))
    jumps: dict = {}
    for td, d in divs_tau:
        jumps[td] = jumps.get(td, 0.0) + d

    def jump(V: np.ndarray, amount: float) -> np.ndarray:
        out = np.interp(np.maximum(S - amount, 0.0), S, V)
        return np.maximum(out, g) if american else out

    def step(V: np.ndarray, tau0: float, dt: float, theta: float,
             lam: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        tau1 = tau0 + dt
        lo1, hi1 = _boundaries(tau1, grid.s_max, K, r, q, is_call, american, divs_tau)
        LV = a * V[:-2] + b * V[1:-1] + c * V[2:]
        rhs = V[1:-1] + (1.0 - theta) * dt * LV
        rhs[0] += theta * dt * a[0] * lo1
        rhs[-1] += theta * dt * c[-1] * hi1
        ab = np.zeros((3, Mg - 1))
        ab[0, 1:] = -theta * dt * c[:-1]
        ab[1, :] = 1.0 - theta * dt * b
        ab[2, :-1] = -theta * dt * a[1:]
        if american:
            rhs = rhs + dt * lam
        vt = solve_banded((1, 1), ab, rhs)
        if american:
            gi = g[1:-1]
            inner = np.maximum(vt - dt * lam, gi)
            lam = np.maximum(0.0, lam + (gi - vt) / dt)
        else:
            inner = vt
        out = np.empty_like(V)
        out[0], out[-1] = lo1, hi1
        out[1:-1] = inner
        return out, lam

    V = g.copy()
    if 0.0 in jumps:
        V = jump(V, jumps[0.0])
    lam = np.zeros(Mg - 1)
    n_steps = 0
    prev_V: Optional[np.ndarray] = None
    prev_dt = 0.0
    plan = _time_plan(T, Mg, divs_tau)
    for k, (lo, hi, n) in enumerate(plan):
        lam = np.zeros(Mg - 1)
        dt = (hi - lo) / n
        tau = lo
        schedule_steps = [(dt / 2.0, 1.0)] * 4 + [(dt, 0.5)] * (n - 2)
        for idx, (h, theta) in enumerate(schedule_steps):
            last = (idx == len(schedule_steps) - 1)
            if k == len(plan) - 1 and last:
                prev_V, prev_dt = V.copy(), h
            V, lam = step(V, tau, h, theta, lam)
            tau += h
            n_steps += 1
        if hi in jumps and hi < T:
            V = jump(V, jumps[hi])
    # One extra CN step past the valuation instant (no dividend there) for charm.
    V_next, _ = step(V, T, prev_dt, 0.5, lam.copy())

    def delta_at(W: np.ndarray) -> float:
        return float((W[j + 1] - W[j - 1]) / (2.0 * dS))

    price = float(V[j])
    delta = delta_at(V)
    gamma = float((V[j + 1] - 2.0 * V[j] + V[j - 1]) / (dS * dS))
    assert prev_V is not None
    charm = -(delta_at(V_next) - delta_at(prev_V)) / (2.0 * prev_dt)
    boundary = None
    if american:
        interior = np.arange(1, Mg)
        cand = interior[(g[1:-1] > 0.0) & (V[1:-1] - g[1:-1] <= BOUNDARY_TOL)]
        if cand.size:
            boundary = float(S[cand.min()] if is_call else S[cand.max()])
    s_ro = S.copy()
    s_ro.setflags(write=False)
    v_ro = V.copy()
    v_ro.setflags(write=False)
    return FDResult(price=price, delta=delta, gamma=gamma, charm=float(charm), grid=grid,
                    s_nodes=s_ro, values=v_ro, boundary=boundary, n_upwind=n_up,
                    n_time_steps=n_steps)


# --------------------------------------------------------------------------------------
# Grid-refinement classification (frozen rules, PREREG.md section 8)
# --------------------------------------------------------------------------------------

@dataclass(frozen=True)
class Refinement:
    status: str
    value: Optional[float]
    error: Optional[float]
    order: Optional[float]
    interval: Optional[Tuple[float, float]]
    reason: Optional[str]
    levels: Tuple[float, ...]


def classify_refinement(q1: float, q2: float, q3: float, atol: float, rtol: float) -> Refinement:
    """CONVERGED / INTERVAL / UNAVAILABLE for a quantity at grid levels N, 2N, 4N."""
    vals = (float(q1), float(q2), float(q3))
    if not all(math.isfinite(v) for v in vals):
        return Refinement(UNAVAILABLE, None, None, None, None, "non_finite_level_value", vals)
    d1 = vals[1] - vals[0]
    d2 = vals[2] - vals[1]
    tol = atol + rtol * abs(vals[2])
    if abs(d2) <= tol and (abs(d1) <= tol or abs(d2) <= 0.75 * abs(d1)):
        order = math.log2(abs(d1) / abs(d2)) if d1 != 0.0 and d2 != 0.0 else None
        return Refinement(CONVERGED, vals[2], abs(d2), order, None, None, vals)
    return _as_interval(vals, "refinement_not_converged")


def _as_interval(vals: Tuple[float, ...], reason: str) -> Refinement:
    d2 = abs(vals[2] - vals[1])
    return Refinement(INTERVAL, None, None, None, (min(vals) - d2, max(vals) + d2), reason, vals)


def _override_interval(res: Refinement, reason: str) -> Refinement:
    if res.status == UNAVAILABLE:
        return res
    return _as_interval(res.levels, reason)


@dataclass(frozen=True)
class Qualification:
    quantities: Mapping[str, Refinement]
    boundary: Optional[float]
    near_boundary: bool
    n_upwind: int
    levels: Tuple[int, ...]
    vol_bump: float


def qualify_fd(S0: float, K: float, T: float, sigma: float, r: float, q: float, is_call: bool,
               american: bool, dividends: Sequence[Tuple[float, float]] = (),
               levels: Sequence[int] = GRID_LEVELS) -> Qualification:
    """Refinement report for price, delta, gamma, vanna and charm over ``levels``."""
    _check_pricing_inputs(S0, K, T, sigma, r, q)
    levels = tuple(int(m) for m in levels)
    if len(levels) != 3 or not (levels[0] < levels[1] < levels[2]):
        raise ValueError("exactly three strictly increasing grid levels are required")
    divs = _normalise_dividends(dividends, T)
    # Vanna uses the frozen fixed-grid bump of +/- VOL_BUMP (PREREG section 7). When either
    # bumped volatility would leave SIGMA_BOUNDS, vanna is UNAVAILABLE with a named reason
    # instead of a shrunken bump or a ValueError; the other quantities use the base solve only.
    h = VOL_BUMP
    sigma_up = sigma + h
    sigma_dn = sigma - h
    bump_ok = (SIGMA_BOUNDS[0] <= sigma_dn <= SIGMA_BOUNDS[1]
               and SIGMA_BOUNDS[0] <= sigma_up <= SIGMA_BOUNDS[1])
    rows = {name: [] for name in QUANTITIES}
    boundary = None
    coarse_dS = None
    n_up = 0
    for idx, M in enumerate(levels):
        grid = build_grid(S0, K, T, sigma, M, sum(d for _, d in divs))
        base = fd_solve(S0, K, T, sigma, r, q, is_call, american, divs, grid=grid)
        rows["price"].append(base.price)
        rows["delta"].append(base.delta)
        rows["gamma"].append(base.gamma)
        rows["charm"].append(base.charm)
        n_up = max(n_up, base.n_upwind)
        if bump_ok:
            up = fd_solve(S0, K, T, sigma_up, r, q, is_call, american, divs, grid=grid)
            dn = fd_solve(S0, K, T, sigma_dn, r, q, is_call, american, divs, grid=grid)
            rows["vanna"].append((up.delta - dn.delta) / (2.0 * h))
            n_up = max(n_up, up.n_upwind, dn.n_upwind)
        if idx == 0:
            boundary = base.boundary
            coarse_dS = grid.dS
    out = {}
    for name in QUANTITIES:
        if name == "vanna" and not bump_ok:
            out[name] = _unavailable("vol_bump_out_of_bounds")
            continue
        atol, rtol = REFINEMENT_TOLERANCES[name]
        out[name] = classify_refinement(*rows[name], atol=atol, rtol=rtol)
    near = False
    if american and boundary is not None and coarse_dS is not None:
        near = abs(S0 - boundary) <= max(3.0 * coarse_dS, 0.02 * S0)
        if near:
            for name in ("gamma", "vanna", "charm"):
                out[name] = _override_interval(out[name], "near_exercise_boundary")
    stencil = T / levels[-1]
    if any(t <= stencil for t, _ in divs):
        out["charm"] = Refinement(UNAVAILABLE, None, None, None, None,
                                  "ex_dividend_within_charm_stencil", out["charm"].levels)
    return Qualification(quantities=out, boundary=boundary, near_boundary=near, n_upwind=n_up,
                         levels=levels, vol_bump=h)


# --------------------------------------------------------------------------------------
# Independent references
# --------------------------------------------------------------------------------------

def crr_price(S0: float, K: float, T: float, sigma: float, r: float, q: float, is_call: bool,
              american: bool, dividends: Sequence[Tuple[float, float]] = (),
              steps: int = 2000) -> float:
    """Cox–Ross–Rubinstein lattice; cash dividends by Vellekoop–Nieuwenhuis interpolation.

    The ex-time is snapped to the nearest lattice step. At that step the
    pre-dividend value at node S is the post-dividend layer interpolated linearly
    at ``S - D`` (linear extrapolation below the lowest node, floored at 0; the
    absorbed value when ``S - D <= 0``), then the American payoff maximum.
    """
    _check_pricing_inputs(S0, K, T, sigma, r, q)
    if not (isinstance(steps, int) and CRR_STEP_BOUNDS[0] <= steps <= CRR_STEP_BOUNDS[1]):
        raise ValueError("lattice steps out of bounds")
    divs = _normalise_dividends(dividends, T)
    dt = T / steps
    u = math.exp(sigma * math.sqrt(dt))
    d = 1.0 / u
    p = (math.exp((r - q) * dt) - d) / (u - d)
    if not (0.0 < p < 1.0):
        raise ValueError("lattice probability outside (0, 1); increase steps")
    disc = math.exp(-r * dt)
    div_at: dict = {}
    for t, amt in divs:
        m = min(max(int(round(t / dt)), 1), steps)
        div_at[m] = div_at.get(m, 0.0) + amt

    def nodes(m: int) -> np.ndarray:
        k = np.arange(m + 1, dtype=float)
        return S0 * u ** k * d ** (m - k)

    def payoff(s: np.ndarray) -> np.ndarray:
        return np.maximum(s - K, 0.0) if is_call else np.maximum(K - s, 0.0)

    def apply_div(m: int, V: np.ndarray, amount: float) -> np.ndarray:
        s = nodes(m)
        x = s - amount
        if V.size >= 2:
            out = np.interp(x, s, V)
            slope = (V[1] - V[0]) / (s[1] - s[0])
            below = x < s[0]
            out = np.where(below, V[0] + slope * (x - s[0]), out)
        else:
            out = np.full_like(x, V[0])
        out = np.maximum(out, 0.0)
        if is_call:
            absorbed = 0.0
        else:
            rem = T - m * dt
            absorbed = K * math.exp(-r * rem)
            if american:
                absorbed = max(K, absorbed)
        out = np.where(x <= 0.0, absorbed, out)
        return np.maximum(out, payoff(s)) if american else out

    V = payoff(nodes(steps))
    if steps in div_at:
        V = apply_div(steps, V, div_at[steps])
    for m in range(steps - 1, -1, -1):
        V = disc * (p * V[1:] + (1.0 - p) * V[:-1])
        if american:
            V = np.maximum(V, payoff(nodes(m)))
        if m in div_at and m > 0:
            V = apply_div(m, V, div_at[m])
    return float(V[0])


def european_one_dividend_quadrature(S0: float, K: float, T: float, sigma: float, r: float,
                                     q: float, is_call: bool, t_div: float, amount: float,
                                     n_nodes: int = 200) -> float:
    """European price with one cash dividend at ``t_div``: Gauss–Hermite over S(t_div-)."""
    _check_pricing_inputs(S0, K, T, sigma, r, q)
    if not (_num(t_div) and 0.0 < t_div < T):
        raise ValueError("dividend time must lie in (0, T)")
    if not (_num(amount) and 0.0 <= amount <= PRICE_MAX):
        raise ValueError("dividend amount out of bounds")
    if not (isinstance(n_nodes, int) and 20 <= n_nodes <= 400):
        raise ValueError("quadrature nodes out of bounds")
    x, w = np.polynomial.hermite_e.hermegauss(n_nodes)
    s = S0 * np.exp((r - q - 0.5 * sigma * sigma) * t_div + sigma * math.sqrt(t_div) * x)
    rem = T - t_div
    vals = np.array([bs_price(max(float(si) - amount, 0.0), K, rem, sigma, is_call, r, q)
                     for si in s])
    return float(math.exp(-r * t_div) * np.sum(w * vals) / _SQRT2PI)


# --------------------------------------------------------------------------------------
# Point-in-time dividends and the fail-closed applicability selector
# --------------------------------------------------------------------------------------

@dataclass(frozen=True)
class DividendRecord:
    """One revision of a cash-dividend record. Times are integer minute indexes."""
    record_id: str
    known_at: int
    ex_time: int
    amount: float
    status: str

    def __post_init__(self) -> None:
        if not isinstance(self.record_id, str) or not self.record_id:
            raise ValueError("record_id must be a non-empty string")
        for name in ("known_at", "ex_time"):
            v = getattr(self, name)
            if not isinstance(v, int) or isinstance(v, bool):
                raise ValueError(f"{name} must be an integer minute index")
        if self.status not in (DECLARED, ESTIMATED, CANCELLED):
            raise ValueError("status must be DECLARED, ESTIMATED or CANCELLED")
        if not (_num(self.amount) and 0.0 <= self.amount <= PRICE_MAX):
            raise ValueError("amount out of bounds")


@dataclass(frozen=True)
class DividendSchedule:
    """Point-in-time dividend records plus completeness assertions.

    ``completeness`` holds ``(known_at, complete_through)`` minute-index pairs: as
    of ``known_at`` the source asserted that every dividend with ex-time up to
    ``complete_through`` is present. A missing schedule is ``None`` at the call
    site; an empty ``records`` tuple with a covering assertion means "declared:
    no dividends", which is different.
    """
    records: Tuple[DividendRecord, ...]
    completeness: Tuple[Tuple[int, int], ...]


@dataclass(frozen=True)
class DividendFilter:
    in_window: Tuple[Tuple[int, float], ...]
    reasons: Tuple[str, ...]


def point_in_time_dividends(schedule: Optional[DividendSchedule], cutoff: int, valuation: int,
                            expiry: int) -> DividendFilter:
    """Dividends knowable at ``cutoff`` with ``valuation < ex_time <= expiry``.

    Raises ``ValueError`` when ``cutoff > valuation`` (look-ahead).
    """
    for name, v in (("cutoff", cutoff), ("valuation", valuation), ("expiry", expiry)):
        if not isinstance(v, int) or isinstance(v, bool):
            raise ValueError(f"{name} must be an integer minute index")
    if cutoff > valuation:
        raise ValueError("look-ahead: information cutoff is after the valuation instant")
    if schedule is None:
        return DividendFilter((), ("dividend_metadata_missing",
                                   "dividend_schedule_not_complete_through_expiry"))
    latest: dict = {}
    for rec in schedule.records:
        if rec.known_at > cutoff:
            continue
        cur = latest.get(rec.record_id)
        if cur is None or rec.known_at > cur.known_at:
            latest[rec.record_id] = rec
        elif rec.known_at == cur.known_at and rec != cur:
            raise ValueError(f"ambiguous revisions for record {rec.record_id!r}")
    reasons = []
    admissible = [ct for ka, ct in schedule.completeness if ka <= cutoff]
    if not admissible or max(admissible) < expiry:
        reasons.append("dividend_schedule_not_complete_through_expiry")
    in_window = []
    for rec in sorted(latest.values(), key=lambda x: (x.ex_time, x.record_id)):
        if rec.status == CANCELLED or not (valuation < rec.ex_time <= expiry):
            continue
        if rec.status == ESTIMATED:
            if "dividend_estimated_not_declared" not in reasons:
                reasons.append("dividend_estimated_not_declared")
            continue
        in_window.append((rec.ex_time, float(rec.amount)))
    return DividendFilter(tuple(in_window), tuple(reasons))


@dataclass(frozen=True)
class ContractTerms:
    """Declared contract terms. ``None`` means the source did not provide the term."""
    underlying: Optional[str]
    occ_root: Optional[str]
    exercise_style: Optional[str]
    deliverable_kind: Optional[str]
    deliverable_shares: Optional[float]
    multiplier: Optional[float]
    settlement: Optional[str]
    expiry_day_start: Optional[int]
    strike: float
    is_call: bool


@dataclass(frozen=True)
class SessionClock:
    """Declared session clock: settlement offsets from the expiry-day start (minutes)."""
    open_offset_minutes: int
    close_offset_minutes: int
    minutes_per_year: float


@dataclass(frozen=True)
class MarketInputs:
    spot: Optional[float]
    sigma: Optional[float]
    rate: Optional[float]
    continuous_yield: Optional[float]
    valuation: int
    cutoff: int
    dividends: Optional[DividendSchedule]


@dataclass(frozen=True)
class Decision:
    model: str
    reasons: Tuple[str, ...]
    t_years: Optional[float]
    strike_per_share: Optional[float]
    shares_per_contract: Optional[float]
    multiplier: Optional[float]
    q: Optional[float]
    dividends: Tuple[Tuple[float, float], ...]


def _adjusted_looking(root: Optional[str], underlying: Optional[str]) -> Optional[bool]:
    if root is None or underlying is None:
        return None
    return root != underlying or root[-1:].isdigit()


def select_model(terms: ContractTerms, clock: Optional[SessionClock], market: MarketInputs) -> Decision:
    """Fail-closed model choice from declared terms only; every failing reason is reported."""
    if market.cutoff > market.valuation:
        raise ValueError("look-ahead: information cutoff is after the valuation instant")
    reasons = []
    style = terms.exercise_style
    if style not in (AMERICAN, EUROPEAN):
        reasons.append("exercise_style_unknown")
    kind = terms.deliverable_kind
    shares = terms.deliverable_shares
    if kind is None:
        reasons.append("deliverable_unknown")
    elif kind not in (SHARES, CASH_INDEX):
        reasons.append("non_share_deliverable_not_modelled")
    if terms.multiplier is None:
        reasons.append("multiplier_unknown")
    elif not (_num(terms.multiplier) and terms.multiplier > 0.0):
        reasons.append("input_out_of_bounds")
    if kind == SHARES:
        if shares is None:
            adj = _adjusted_looking(terms.occ_root, terms.underlying)
            reasons.append("adjusted_deliverable_unknown" if adj else "deliverable_unknown")
        elif not (_num(shares) and shares > 0.0):
            reasons.append("input_out_of_bounds")
    expiry = None
    t_years = None
    if (terms.settlement not in (AM_OPEN, PM_CLOSE) or clock is None
            or terms.expiry_day_start is None):
        reasons.append("settlement_clock_unknown")
    else:
        off = clock.open_offset_minutes if terms.settlement == AM_OPEN else clock.close_offset_minutes
        expiry = int(terms.expiry_day_start) + int(off)
        if not (_num(clock.minutes_per_year) and clock.minutes_per_year > 0.0):
            reasons.append("settlement_clock_unknown")
        else:
            t_years = (expiry - market.valuation) / float(clock.minutes_per_year)
            if not (0.0 < t_years <= T_MAX_YEARS):
                reasons.append("input_out_of_bounds")
    if market.rate is None or not _num(market.rate):
        reasons.append("rates_missing")
    elif not (RATE_BOUNDS[0] <= market.rate <= RATE_BOUNDS[1]):
        reasons.append("input_out_of_bounds")
    if market.spot is None or market.sigma is None:
        reasons.append("market_input_missing")
    else:
        if not (_num(market.spot) and 0.0 < market.spot <= PRICE_MAX):
            reasons.append("input_out_of_bounds")
        if not (_num(market.sigma) and SIGMA_BOUNDS[0] <= market.sigma <= SIGMA_BOUNDS[1]):
            reasons.append("input_out_of_bounds")
    if not (_num(terms.strike) and 0.0 < terms.strike <= PRICE_MAX):
        reasons.append("input_out_of_bounds")
    q = None
    divs: Tuple[Tuple[float, float], ...] = ()
    if kind == CASH_INDEX:
        if market.continuous_yield is None:
            reasons.append("dividend_metadata_missing")
        elif not (_num(market.continuous_yield)
                  and YIELD_BOUNDS[0] <= market.continuous_yield <= YIELD_BOUNDS[1]):
            reasons.append("input_out_of_bounds")
        else:
            q = float(market.continuous_yield)
    elif kind == SHARES:
        if market.continuous_yield not in (None, 0.0):
            reasons.append("continuous_yield_conflicts_with_discrete_schedule")
        q = 0.0
        if expiry is not None:
            filt = point_in_time_dividends(market.dividends, market.cutoff, market.valuation, expiry)
            reasons.extend(filt.reasons)
            if not filt.reasons and t_years is not None and clock is not None:
                divs = tuple(((ex - market.valuation) / float(clock.minutes_per_year), amt)
                             for ex, amt in filt.in_window)
        elif market.dividends is None:
            reasons.append("dividend_metadata_missing")
            reasons.append("dividend_schedule_not_complete_through_expiry")
    reasons_t = tuple(dict.fromkeys(reasons))
    strike_ps = None
    spc = None
    if not reasons_t:
        if kind == SHARES:
            spc = float(shares)
            strike_ps = float(terms.strike) * float(terms.multiplier) / float(shares)
        else:
            spc = float(terms.multiplier)
            strike_ps = float(terms.strike)
    if reasons_t:
        model = MODEL_UNAVAILABLE
    elif kind == CASH_INDEX:
        model = MODEL_EUROPEAN_BS_CONTINUOUS_YIELD if style == EUROPEAN else MODEL_AMERICAN_FD
    elif style == EUROPEAN:
        model = MODEL_EUROPEAN_FD_DISCRETE_DIVIDEND if divs else MODEL_EUROPEAN_BS_CONTINUOUS_YIELD
    elif terms.is_call and not divs and float(market.rate) >= 0.0:
        model = MODEL_EUROPEAN_BS_EQUIVALENT
    else:
        model = MODEL_AMERICAN_FD
    return Decision(model=model, reasons=reasons_t, t_years=t_years if not reasons_t else None,
                    strike_per_share=strike_ps, shares_per_contract=spc,
                    multiplier=float(terms.multiplier) if not reasons_t else None,
                    q=q if not reasons_t else None, dividends=divs if not reasons_t else ())


@dataclass(frozen=True)
class ContractValuation:
    decision: Decision
    per_share: Mapping[str, Refinement]
    price_per_contract: Optional[Refinement]


def _unavailable(reason: str) -> Refinement:
    return Refinement(UNAVAILABLE, None, None, None, None, reason, ())


def _scaled(res: Refinement, factor: float) -> Refinement:
    if res.status == CONVERGED:
        return Refinement(CONVERGED, res.value * factor, (res.error or 0.0) * factor, res.order,
                          None, res.reason, tuple(v * factor for v in res.levels))
    if res.status == INTERVAL:
        lo, hi = res.interval  # type: ignore[misc]
        return Refinement(INTERVAL, None, None, None, (lo * factor, hi * factor), res.reason,
                          tuple(v * factor for v in res.levels))
    return res


def price_contract(terms: ContractTerms, clock: Optional[SessionClock], market: MarketInputs,
                   levels: Sequence[int] = GRID_LEVELS) -> ContractValuation:
    """Selector, then the selected model. UNAVAILABLE decisions price nothing."""
    dec = select_model(terms, clock, market)
    if dec.model == MODEL_UNAVAILABLE:
        reason = ";".join(dec.reasons)
        return ContractValuation(dec, {n: _unavailable(reason) for n in QUANTITIES}, None)
    S = float(market.spot)  # type: ignore[arg-type]
    sigma = float(market.sigma)  # type: ignore[arg-type]
    r = float(market.rate)  # type: ignore[arg-type]
    K = float(dec.strike_per_share)  # type: ignore[arg-type]
    T = float(dec.t_years)  # type: ignore[arg-type]
    q = float(dec.q)  # type: ignore[arg-type]
    if dec.model in (MODEL_EUROPEAN_BS_CONTINUOUS_YIELD, MODEL_EUROPEAN_BS_EQUIVALENT):
        _check_pricing_inputs(S, K, T, sigma, r, q)
        price = bs_price(S, K, T, sigma, terms.is_call, r, q)
        delta, gamma, vanna, charm = bs_greeks(S, K, T, sigma, terms.is_call, r, q)
        vals = {"price": price, "delta": delta, "gamma": gamma, "vanna": vanna, "charm": charm}
        per_share = {n: Refinement(CONVERGED, float(v), 0.0, None, None, "analytic_formula",
                                   (float(v),)) for n, v in vals.items()}
    else:
        qual = qualify_fd(S, K, T, sigma, r, q, terms.is_call,
                          american=(dec.model == MODEL_AMERICAN_FD), dividends=dec.dividends,
                          levels=levels)
        per_share = dict(qual.quantities)
    per_contract = _scaled(per_share["price"], float(dec.shares_per_contract))  # type: ignore[arg-type]
    return ContractValuation(dec, per_share, per_contract)


# --------------------------------------------------------------------------------------
# Explicit unit converters (no defaults)
# --------------------------------------------------------------------------------------

def convert_size(value: float, from_unit: str, to_unit: str, *, multiplier: float) -> float:
    """per_share <-> per_contract. ``multiplier`` (deliverable units per contract) is required."""
    units = ("per_share", "per_contract")
    if from_unit not in units or to_unit not in units:
        raise ValueError("unknown size unit")
    if not (_num(multiplier) and multiplier > 0.0):
        raise ValueError("multiplier must be a declared positive number")
    if from_unit == to_unit:
        return float(value)
    return float(value) * multiplier if to_unit == "per_contract" else float(value) / multiplier


def convert_vol(value: float, from_unit: str, to_unit: str) -> float:
    """decimal <-> vol_point (1 vol point = 0.01 decimal)."""
    units = ("decimal", "vol_point")
    if from_unit not in units or to_unit not in units:
        raise ValueError("unknown volatility unit")
    if from_unit == to_unit:
        return float(value)
    return float(value) * 100.0 if to_unit == "vol_point" else float(value) / 100.0


def convert_vega(value: float, from_unit: str, to_unit: str) -> float:
    """per_unit_vol (per 1.00 decimal vol) <-> per_vol_point (per 0.01)."""
    units = ("per_unit_vol", "per_vol_point")
    if from_unit not in units or to_unit not in units:
        raise ValueError("unknown vega unit")
    if from_unit == to_unit:
        return float(value)
    return float(value) / 100.0 if to_unit == "per_vol_point" else float(value) * 100.0


def convert_charm(value: float, from_unit: str, to_unit: str, *, days_per_year: int) -> float:
    """per_year <-> per_day with a declared day basis of 365 or 252."""
    units = ("per_year", "per_day")
    if from_unit not in units or to_unit not in units:
        raise ValueError("unknown charm unit")
    if isinstance(days_per_year, bool) or days_per_year not in (365, 252):
        raise ValueError("days_per_year must be declared as 365 or 252")
    if from_unit == to_unit:
        return float(value)
    return float(value) / days_per_year if to_unit == "per_day" else float(value) * days_per_year
