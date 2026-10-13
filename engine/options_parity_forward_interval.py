from __future__ import annotations

__doc__ = """RESEARCH REFERENCE — NOT WIRED. Q12 option-implied forward interval and carry consistency.

Verdict (quant assessment 2026-10, brief Q12): INSUFFICIENT_DATA. No licensed, retained
local store carries synchronized same-timestamp call/put bid/ask pairs with deliverable,
settlement and exercise metadata (see
research/quant_assessment_2026_10/Q12_implied_forward_carry/VERDICT.md). This module is a
pure reference implementation of the measurement contract only. Nothing imports it,
nothing schedules it, and it has no production authority.

What it measures
----------------
European put-call parity, F = K + (C - P) / D, evaluated on quote BANDS rather than mids:

    pair interval = [K + (C_bid - P_ask) / D,  K + (C_ask - P_bid) / D]

over a discount-factor band [D_lo, D_hi]. Pairs of one (underlying, expiry,
deliverable, multiplier, settlement, exercise) group are combined by a CONSERVATIVE
INTERSECTION: every pair must hold at one common discount factor D, so the combined set is
the union over D in the band of the per-D intersections. With u = 1/D every bound is
linear in u (lo is a convex max of lines, hi a concave min of lines), so this is computed
exactly from line envelopes in O(n log n). Widening each pair over the band first and
intersecting afterwards would only give an OUTER bound that can report a forward no
single D supports. If no common D exists the pairs are reported as incompatible and the
forward is unavailable; they are never averaged. Intersection is not a robust consensus:
one valid but mispriced pair can make an otherwise consistent group incompatible, and it
is surfaced in `conflicts` rather than outvoted.

What it refuses to be
---------------------
* Not an executable arbitrage: vendor/NBBO bands are not guaranteed fills, and fees,
  margin, borrow and early exercise are not modelled.
* Not a spot forecast: the forward is the carry-adjusted settlement value implied by
  same-moment quotes, not a prediction of the future spot price.
* Carry is JOINTLY identified: a European forward embeds r - q - borrow together. The
  components are not separately identified from one expiry.
* American-exercise pairs give no parity equality. They return "unavailable" for the
  forward (American adjustment belongs to brief Q02); optional spot bounds are produced
  only when a dividend PV upper bound is supplied and borrow is declared negligible.

Clocks are integer indexes supplied by the caller (no wall-clock reads).
"""

import math
from dataclasses import dataclass, field
from typing import Iterable, Sequence

RESEARCH_ONLY = True
VERDICT = "INSUFFICIENT_DATA"

NOT_EXECUTABLE_ARBITRAGE = True
NOT_SPOT_FORECAST = True
CARRY_IDENTIFICATION = "joint r - q - borrow; components not separately identified"
MEASUREMENT_LABEL = "parity-implied forward interval (measurement only)"

SETTLEMENTS = ("physical", "cash_am", "cash_pm")
EXERCISE_STYLES = ("european", "american")

# Bounded inputs.
MAX_LEGS = 20_000
D_MIN, D_MAX = 0.5, 1.5
PRICE_MAX = 1e7


@dataclass(frozen=True)
class OptionQuote:
    """One option leg's two-sided quote with its full contract identity.

    `deliverable` names what one contract delivers (e.g. "100 XYZ"); an OCC-adjusted
    contract ("100 XYZ + 12.50 USD") is a different identity. `quote_index` is the
    caller's integer clock for when the quote was observed.
    """

    right: str  # "C" or "P"
    underlying: str
    expiry: str
    strike: float
    deliverable: str
    multiplier: float
    settlement: str
    exercise: str
    bid: float
    ask: float
    quote_index: int
    deliverable_standard: bool = True


IDENTITY_FIELDS = ("underlying", "expiry", "strike", "deliverable", "multiplier",
                   "settlement", "exercise", "deliverable_standard")
GROUP_FIELDS = tuple(f for f in IDENTITY_FIELDS if f != "strike")


def pair_identity(q: OptionQuote) -> tuple:
    """Identity two legs must share to form a parity pair (right excluded)."""
    return tuple(getattr(q, f) for f in IDENTITY_FIELDS)


def group_identity(q: OptionQuote) -> tuple:
    """Identity pairs must share to be combined (strike excluded)."""
    return tuple(getattr(q, f) for f in GROUP_FIELDS)


@dataclass(frozen=True)
class PairCheck:
    eligible: bool
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class PairInterval:
    """One pair's interval widened over the band; x_lo/x_hi keep the per-D form.

    x_lo = C_bid - P_ask and x_hi = C_ask - P_bid, so at discount factor D the pair
    bounds F by [strike + x_lo / D, strike + x_hi / D].
    """

    strike: float
    lo: float
    hi: float
    group: tuple
    x_lo: float | None = None
    x_hi: float | None = None


@dataclass(frozen=True)
class ForwardEstimate:
    """Combined result. Disclaimer fields are fixed at construction and frozen."""

    status: str  # consistent | incompatible | unavailable
    lo: float | None
    hi: float | None
    n_pairs: int
    reasons: tuple[str, ...] = ()
    conflicts: tuple[tuple[float, float, float], ...] = ()
    max_overlap_count: int = 0
    marginal: bool = False
    label: str = field(default=MEASUREMENT_LABEL, init=False)
    not_executable_arbitrage: bool = field(default=True, init=False)
    not_spot_forecast: bool = field(default=True, init=False)
    carry_identification: str = field(default=CARRY_IDENTIFICATION, init=False)


def _finite(*xs: float) -> bool:
    return all(isinstance(x, (int, float)) and math.isfinite(x) for x in xs)


def check_pair(call: OptionQuote, put: OptionQuote, *, now_index: int,
               max_quote_age: int, max_async: int) -> PairCheck:
    """Qualify a call/put pair. Every failure is named; nothing is silently repaired."""
    reasons: list[str] = []
    if str(call.right).upper() != "C" or str(put.right).upper() != "P":
        reasons.append("rights_not_call_put")
    for f in IDENTITY_FIELDS:
        if getattr(call, f) != getattr(put, f):
            reasons.append(f"identity_mismatch:{f}")
    for name, q in (("call", call), ("put", put)):
        if not _finite(q.bid, q.ask, q.strike, q.multiplier):
            reasons.append(f"non_finite_{name}")
            continue
        if q.bid < 0 or q.ask <= 0 or q.ask > PRICE_MAX:
            reasons.append(f"bad_price_{name}")
        if q.bid > q.ask:
            reasons.append(f"crossed_{name}")
        elif q.bid == q.ask:
            reasons.append(f"locked_{name}")
        if q.settlement not in SETTLEMENTS:
            reasons.append(f"unknown_settlement_{name}")
        if q.exercise not in EXERCISE_STYLES:
            reasons.append(f"unknown_exercise_{name}")
        age = now_index - int(q.quote_index)
        if age < 0:
            reasons.append(f"future_quote_{name}")
        elif age > max_quote_age:
            reasons.append(f"stale_{name}")
    if abs(int(call.quote_index) - int(put.quote_index)) > max_async:
        reasons.append("asynchronous_legs")
    if _finite(call.strike) and call.strike <= 0:
        reasons.append("bad_strike")
    return PairCheck(eligible=not reasons, reasons=tuple(reasons))


def applicability(q: OptionQuote) -> tuple[bool, str]:
    """Whether a parity EQUALITY forward is defined for this contract family."""
    if q.exercise == "american":
        return False, "american_exercise_no_parity_equality_requires_q02_adjustment"
    if not q.deliverable_standard:
        return False, "nonstandard_deliverable_forward_is_of_a_basket"
    if q.exercise != "european":
        return False, "unknown_exercise_style"
    return True, "european_parity_equality"


def pair_forward_interval(call: OptionQuote, put: OptionQuote,
                          d_band: tuple[float, float]) -> tuple[float, float]:
    """Interval for F from one qualified European pair over a discount-factor band."""
    d_lo, d_hi = _check_band(d_band)
    x_lo = call.bid - put.ask
    x_hi = call.ask - put.bid
    k = float(call.strike)
    lo = k + min(x_lo / d_lo, x_lo / d_hi)
    hi = k + max(x_hi / d_lo, x_hi / d_hi)
    return lo, hi


def _check_band(d_band: tuple[float, float]) -> tuple[float, float]:
    d_lo, d_hi = float(d_band[0]), float(d_band[1])
    if not (_finite(d_lo, d_hi) and D_MIN <= d_lo <= d_hi <= D_MAX):
        raise ValueError("discount band must satisfy 0.5 <= D_lo <= D_hi <= 1.5")
    return d_lo, d_hi


def _envelope(lines: Sequence[tuple[float, float]], u_lo: float,
              u_hi: float) -> tuple[list[tuple[float, float]], list[float]]:
    """Upper envelope of lines y = a + b*u on [u_lo, u_hi] (convex hull trick).

    Returns (hull lines in order of increasing u, interior breakpoints).
    """
    best: dict[float, float] = {}
    for a, b in lines:
        if b not in best or a > best[b]:
            best[b] = a
    ordered = sorted((b, a) for b, a in best.items())
    hull: list[tuple[float, float]] = []  # (a, b)

    def cross(l1: tuple[float, float], l2: tuple[float, float]) -> float:
        return (l1[0] - l2[0]) / (l2[1] - l1[1])

    for b, a in ordered:
        line = (a, b)
        while len(hull) >= 2 and cross(hull[-2], line) <= cross(hull[-2], hull[-1]):
            hull.pop()
        hull.append(line)
    breaks = [cross(hull[i], hull[i + 1]) for i in range(len(hull) - 1)]
    # clip to the band: keep only lines whose segment meets [u_lo, u_hi]
    keep_l, keep_b = [], []
    for i, line in enumerate(hull):
        left = breaks[i - 1] if i > 0 else -math.inf
        right = breaks[i] if i < len(breaks) else math.inf
        if right <= u_lo or left >= u_hi:
            continue
        if keep_l:  # strictly inside (u_lo, u_hi) here
            keep_b.append(left)
        keep_l.append(line)
    return keep_l, keep_b


def _env_value(env: tuple[list[tuple[float, float]], list[float]], u: float) -> float:
    hull, breaks = env
    lo, hi = 0, len(breaks)
    while lo < hi:  # first breakpoint >= u
        mid = (lo + hi) // 2
        if breaks[mid] < u:
            lo = mid + 1
        else:
            hi = mid
    a, b = hull[lo]
    return a + b * u


def _exact_band_intersection(intervals: Sequence[PairInterval], d_lo: float, d_hi: float
                             ) -> tuple[float, float] | tuple[None, tuple]:
    """Union over D in [d_lo, d_hi] of the per-D intersection of pair intervals.

    Returns (lo, hi) when some common D exists, else (None, conflicts) where conflicts
    are the pairs violating the bound at the least-infeasible D.
    """
    u_lo, u_hi = 1.0 / d_hi, 1.0 / d_lo
    lo_lines = [(iv.strike, iv.x_lo) for iv in intervals]
    hi_lines = [(-iv.strike, -iv.x_hi) for iv in intervals]  # min via negated max

    def at_d(d: float) -> tuple[float, float]:
        return (max(iv.strike + iv.x_lo / d for iv in intervals),
                min(iv.strike + iv.x_hi / d for iv in intervals))

    if u_lo == u_hi:
        cands = [u_lo]
        vals = {u_lo: at_d(d_lo)}
    else:
        env_l = _envelope(lo_lines, u_lo, u_hi)
        env_h = _envelope(hi_lines, u_lo, u_hi)
        cands = sorted(set([u_lo, u_hi] + env_l[1] + env_h[1]))
        vals = {u: (_env_value(env_l, u), -_env_value(env_h, u)) for u in cands[1:-1]}
        vals[u_lo] = at_d(d_hi)
        vals[u_hi] = at_d(d_lo)
    g = [vals[u][0] - vals[u][1] for u in cands]  # convex, piecewise linear between cands
    i_min = min(range(len(cands)), key=lambda i: g[i])
    if g[i_min] > 0:
        u_star = cands[i_min]
        big_l, small_h = vals[u_star]
        conflicts = []
        for iv in intervals:
            lo_k, hi_k = iv.strike + iv.x_lo * u_star, iv.strike + iv.x_hi * u_star
            if lo_k > small_h or hi_k < big_l:
                conflicts.append((iv.strike, lo_k, hi_k))
        return None, tuple(conflicts)
    # feasible u-set [a, b]: walk out from the minimum, root-find on the linear segment
    i = i_min
    while i > 0 and g[i - 1] <= 0:
        i -= 1
    a = cands[i]
    pts = []
    if i > 0:
        u0, u1, g0, g1 = cands[i - 1], cands[i], g[i - 1], g[i]
        a = u0 + (u1 - u0) * g0 / (g0 - g1)
        w = (a - u0) / (u1 - u0)
        pts.append((vals[u0][0] + w * (vals[u1][0] - vals[u0][0]),
                    vals[u0][1] + w * (vals[u1][1] - vals[u0][1])))
    j = i_min
    while j < len(cands) - 1 and g[j + 1] <= 0:
        j += 1
    if j < len(cands) - 1:
        u0, u1, g0, g1 = cands[j], cands[j + 1], g[j], g[j + 1]
        b = u0 + (u1 - u0) * (-g0) / (g1 - g0)
        w = (b - u0) / (u1 - u0)
        pts.append((vals[u0][0] + w * (vals[u1][0] - vals[u0][0]),
                    vals[u0][1] + w * (vals[u1][1] - vals[u0][1])))
    pts.extend(vals[cands[k]] for k in range(i, j + 1))
    # L convex attains its min, H concave its max, at a segment end or breakpoint
    return min(p[0] for p in pts), max(p[1] for p in pts)


def combine_intervals(intervals: Sequence[PairInterval], *, min_pairs: int = 1,
                      marginal_fraction: float = 0.1,
                      d_band: tuple[float, float] | None = None) -> ForwardEstimate:
    """Conservatively intersect same-group pair intervals; never average.

    With `d_band` and per-pair x_lo/x_hi, every pair must hold at one common discount
    factor (exact union over D of per-D intersections). Without them the band-widened
    [lo, hi] are intersected, which is an outer bound when the band is not a point.
    """
    if not intervals:
        return ForwardEstimate("unavailable", None, None, 0, ("no_eligible_pairs",))
    groups = {iv.group for iv in intervals}
    if len(groups) != 1:
        return ForwardEstimate("unavailable", None, None, len(intervals),
                               ("mixed_identity_groups_not_combined",))
    if len(intervals) < min_pairs:
        return ForwardEstimate("unavailable", None, None, len(intervals),
                               (f"fewer_than_{min_pairs}_pairs",))
    lo = max(iv.lo for iv in intervals)
    hi = min(iv.hi for iv in intervals)
    best = _max_overlap(intervals)
    exact = d_band is not None and all(
        iv.x_lo is not None and iv.x_hi is not None for iv in intervals)
    if exact and lo <= hi:
        d_lo, d_hi = _check_band(d_band)
        res = _exact_band_intersection(intervals, d_lo, d_hi)
        if res[0] is None:
            return ForwardEstimate("incompatible", None, None, len(intervals),
                                   ("no_common_discount_factor_in_band",),
                                   conflicts=res[1], max_overlap_count=best)
        lo, hi = res
    if lo <= hi:
        widths = sorted(iv.hi - iv.lo for iv in intervals)
        med = widths[len(widths) // 2]
        marginal = med > 0 and (hi - lo) < marginal_fraction * med
        return ForwardEstimate("consistent", lo, hi, len(intervals),
                               max_overlap_count=len(intervals), marginal=marginal)
    conflicts = tuple((iv.strike, iv.lo, iv.hi) for iv in intervals
                      if iv.hi < lo or iv.lo > hi)
    return ForwardEstimate("incompatible", None, None, len(intervals),
                           ("pair_intervals_do_not_intersect",), conflicts=conflicts,
                           max_overlap_count=best)


def _max_overlap(intervals: Iterable[PairInterval]) -> int:
    events = []
    for iv in intervals:
        events.append((iv.lo, 0))  # open before close at equal coordinate
        events.append((iv.hi, 1))
    events.sort()
    cur = best = 0
    for _, kind in events:
        cur = cur + 1 if kind == 0 else cur - 1
        best = max(best, cur)
    return best


def estimate_forward(quotes: Sequence[OptionQuote], *, d_band: tuple[float, float],
                     now_index: int, max_quote_age: int, max_async: int,
                     min_pairs: int = 1) -> tuple[ForwardEstimate, dict]:
    """End to end: pair legs, qualify, compute intervals, combine one group.

    Returns (estimate, diagnostics). Diagnostics list every rejected pair with reasons.
    """
    if len(quotes) > MAX_LEGS:
        raise ValueError("too many legs")
    by_key: dict[tuple, dict[str, OptionQuote]] = {}
    for q in quotes:
        slot = by_key.setdefault(pair_identity(q), {})
        r = str(q.right).upper()
        if r in slot:
            slot.setdefault("_dup", q)
        slot[r] = q
    rejected: list[tuple[tuple, tuple[str, ...]]] = []
    intervals: list[PairInterval] = []
    not_applicable: list[str] = []
    for key, legs in sorted(by_key.items(), key=lambda kv: repr(kv[0])):
        if "_dup" in legs:
            rejected.append((key, ("duplicate_leg_quotes",)))
            continue
        if "C" not in legs or "P" not in legs:
            rejected.append((key, ("missing_leg",)))
            continue
        chk = check_pair(legs["C"], legs["P"], now_index=now_index,
                         max_quote_age=max_quote_age, max_async=max_async)
        if not chk.eligible:
            rejected.append((key, chk.reasons))
            continue
        ok, why = applicability(legs["C"])
        if not ok:
            not_applicable.append(why)
            continue
        lo, hi = pair_forward_interval(legs["C"], legs["P"], d_band)
        intervals.append(PairInterval(legs["C"].strike, lo, hi, group_identity(legs["C"]),
                                      x_lo=legs["C"].bid - legs["P"].ask,
                                      x_hi=legs["C"].ask - legs["P"].bid))
    diag = {"rejected": rejected, "not_applicable": sorted(set(not_applicable)),
            "n_candidate_pairs": len(by_key)}
    if not intervals and not_applicable:
        return (ForwardEstimate("unavailable", None, None, 0, tuple(sorted(set(not_applicable)))),
                diag)
    return combine_intervals(intervals, min_pairs=min_pairs, d_band=d_band), diag


def american_spot_bounds(call: OptionQuote, put: OptionQuote, *, discount_factor: float,
                         dividend_pv_upper: float | None,
                         borrow_negligible: bool) -> tuple[str, float | None, float | None]:
    """American parity inequality S - Div - K <= C - P <= S - K*D, on bands.

    Gives bounds on the underlying VALUE implied by quotes (not a forward, not a
    forecast). Unavailable unless a dividend PV upper bound is given and borrow is
    declared negligible, because hard-to-borrow names break the inequality.
    """
    if call.exercise != "american" or put.exercise != "american":
        return "not_american", None, None
    if dividend_pv_upper is None or not borrow_negligible:
        return "unavailable_dividend_or_borrow_unknown", None, None
    d = float(discount_factor)
    if not (_finite(d, dividend_pv_upper) and D_MIN <= d <= D_MAX and dividend_pv_upper >= 0):
        raise ValueError("bad discount factor or dividend bound")
    k = float(call.strike)
    s_lo = (call.bid - put.ask) + k * d
    s_hi = (call.ask - put.bid) + k + float(dividend_pv_upper)
    return "bounds_only", s_lo, s_hi


def implied_net_carry_interval(f_lo: float, f_hi: float, s_lo: float, s_hi: float,
                               t_years: float) -> tuple[float, float]:
    """Joint carry b with F = S*exp(b*T); b = r - q - borrow, not decomposed."""
    if not (_finite(f_lo, f_hi, s_lo, s_hi, t_years) and 0 < f_lo <= f_hi
            and 0 < s_lo <= s_hi and 0 < t_years <= 10):
        raise ValueError("bad inputs for carry interval")
    return math.log(f_lo / s_hi) / t_years, math.log(f_hi / s_lo) / t_years
