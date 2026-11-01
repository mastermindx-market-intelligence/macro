"""RESEARCH REFERENCE — NOT WIRED.

Q01 — bid/ask-aware, arbitrage-constrained volatility surface (research reference for
the October 2026 quant assessment).

VERDICT: INSUFFICIENT_DATA. The licensed retained local data holds no same-session
European cash-settled index-option chain carrying per-contract bid, ask, quote
timestamp and condition, exact expiry and settlement, and an owner-supplied forward
and discount factor. The only local option chains (data/polygon_gex/chains) are
IV-only, American-style ETF/single-name snapshots with date-only clocks, and the
ThetaData EOD store holds zero roots. The preregistered surface comparison therefore
did not run; see research/quant_assessment_2026_10/Q01_arbitrage_constrained_surface/
VERDICT.md for the evidence and the exact missing input.

What this module is — pure functions with bounded inputs and no I/O:
  1. screen_quotes: reject wrong product/root, American or unknown style, inconsistent
     integer clocks, future quotes, non-finite/negative/crossed quotes, bad conditions,
     missing or mismatched owner forwards, and resolve duplicate coordinates — all
     before any fitting, order-invariantly, keeping every raw record verbatim;
  2. build_slices: merge call and parity-converted put bid/ask into normalized
     undiscounted call bands c = C / (D * F) per (expiry, strike); empty intersections
     are reported as PARITY_CONFLICT, never averaged away;
  3. fit_benchmark: the convex benchmark — one joint linear program over piecewise-
     linear call curves with static (bounds, monotone, convex incl. the c(0)=1 anchor)
     and calendar constraints; returns BANDS_INFEASIBLE when no admissible curve fits
     inside the quote bands instead of reporting a fabricated repair;
  4. fit_svi_surface: a constrained raw-SVI challenger (seeded multi-start L-BFGS-B
     with butterfly, Lee-wing, positivity and calendar penalties) with explicit
     FAILED_FIT / FAILED_CHECK states;
  5. dense-grid checks (strike and calendar) at declared tolerances, between nodes and
     not merely at observed strikes; a fit is admitted only if they pass;
  6. perturbation_sensitivity and evaluate_at: refits under draws inside the bid/ask
     bands, and SUPPORTED / EXTRAPOLATED / UNAVAILABLE flags for every queried point.

What it is not: imported, registered, scheduled or wired by anything. It carries no
display, rank, alert, score or deployment authority (authority() is all False). It
does not replace the incumbent Black-Scholes kernels (engine/intraday_greeks.py,
engine/greeks.py): its private normalized Black-76 helper exists only because this
reference may import nothing beyond stdlib/numpy/scipy/pandas; any production wiring
would have to reuse the single incumbent kernel. Forwards and discount factors are
inputs from a trusted owner (Q12 dependency) and are never inferred here. American
contracts are excluded until Q02. Clocks are integer ticks; nothing reads wall time.
"""
from __future__ import annotations

import copy
import json
import math
from typing import Any, Iterable, Mapping, Sequence

import numpy as np
from scipy import optimize, sparse
from scipy.stats import norm

RESEARCH_ONLY = True
SCHEMA = "options_arbfree_surface.research.v1"
VERDICT = "INSUFFICIENT_DATA"

ACCEPTED_PRODUCTS: tuple[str, ...] = ("INDEX_OPTION",)
ACCEPTED_STYLE = "EUROPEAN"
ACCEPTED_CONDITIONS: tuple[str, ...] = ("REGULAR",)

# Exclusion reasons (screen_quotes).
MALFORMED = "MALFORMED"
WRONG_PRODUCT = "WRONG_PRODUCT"
AMERICAN_EXCLUDED = "AMERICAN_EXCLUDED"
UNKNOWN_STYLE = "UNKNOWN_STYLE"
INCONSISTENT_CLOCK = "INCONSISTENT_CLOCK"
FUTURE_QUOTE = "FUTURE_QUOTE"
NONFINITE_QUOTE = "NONFINITE_QUOTE"
NEGATIVE_BID = "NEGATIVE_BID"
NONPOSITIVE_ASK = "NONPOSITIVE_ASK"
CROSSED_QUOTE = "CROSSED_QUOTE"
BAD_CONDITION = "BAD_CONDITION"
MISSING_FORWARD = "MISSING_FORWARD"
FORWARD_MISMATCH = "FORWARD_MISMATCH"
DUPLICATE_IDENTICAL = "DUPLICATE_IDENTICAL"
DUPLICATE_CONFLICT = "DUPLICATE_CONFLICT"
SUPERSEDED = "SUPERSEDED"

# Node, fit and support states.
PARITY_CONFLICT = "PARITY_CONFLICT"
ADMISSIBLE = "ADMISSIBLE"
BANDS_INFEASIBLE = "BANDS_INFEASIBLE"
NO_DATA = "NO_DATA"
SOLVER_FAILED = "SOLVER_FAILED"
ADMITTED = "ADMITTED"
FAILED_FIT = "FAILED_FIT"
FAILED_CHECK = "FAILED_CHECK"
SUPPORTED = "SUPPORTED"
EXTRAPOLATED = "EXTRAPOLATED"
UNAVAILABLE = "UNAVAILABLE"
NOT_ADMITTED = "NOT_ADMITTED"

# Declared tolerances.
DEFAULT_TOL = 1e-8             # dense price-space checks, normalized call units
DEFAULT_G_TOL = 1e-8           # Gatheral-Jacquier g(k) >= -tol
DEFAULT_CAL_TOL = 1e-8         # calendar checks (normalized call / total variance units)
DEFAULT_VIOLATION_TOL = 1e-6   # benchmark band violation per node, spread units
DEFAULT_MIN_SPREAD = 1e-6      # floor on band width used for spread weights
DEFAULT_GRID = 401             # dense-grid points per slice
MAX_RECORDS = 200_000          # bounded input

_AUTHORITY_KEYS = ("may_display", "may_rank", "may_alert", "may_score", "may_deploy")
_SVI_LOWER = (-1.0, 1e-6, -0.999, None, 1e-4)
_SVI_UPPER = (4.0, 2.0, 0.999, None, 3.0)


def authority() -> dict[str, bool]:
    """Every authority flag is False: this reference grants nothing."""
    return {key: False for key in _AUTHORITY_KEYS}


def _stamp(payload: dict) -> dict:
    payload["schema"] = SCHEMA
    payload["research_only"] = True
    payload["authority"] = authority()
    return payload


def _is_int(x: Any) -> bool:
    return isinstance(x, (int, np.integer)) and not isinstance(x, (bool, np.bool_))


def _num(x: Any) -> float | None:
    if x is None or isinstance(x, (bool, np.bool_)):
        return None
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def _canonical(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, default=repr, separators=(",", ":"))


# --------------------------------------------------------------------------- screen


def _normalize_forwards(forwards: Mapping[Any, Any] | None) -> dict[int, tuple[float, float]]:
    out: dict[int, tuple[float, float]] = {}
    for key, val in (forwards or {}).items():
        if not _is_int(key) or not isinstance(val, Mapping):
            continue
        fwd, disc = _num(val.get("forward")), _num(val.get("discount"))
        if fwd is None or disc is None or fwd <= 0 or disc <= 0:
            continue
        out[int(key)] = (fwd, disc)
    return out


def _record_reason(rec: Any, ctx: Mapping[str, Any]) -> str | None:
    if not isinstance(rec, Mapping):
        return MALFORMED
    if rec.get("product") not in ctx["products"] or rec.get("root") not in ctx["roots"]:
        return WRONG_PRODUCT
    style = rec.get("style")
    if style == "AMERICAN":
        return AMERICAN_EXCLUDED
    if style != ACCEPTED_STYLE:
        return UNKNOWN_STYLE
    sess, q_ts, e_ts = rec.get("session"), rec.get("quote_ts"), rec.get("expiry_ts")
    if not (_is_int(sess) and _is_int(q_ts) and _is_int(e_ts)):
        return INCONSISTENT_CLOCK
    if int(sess) != ctx["session"] or int(q_ts) < ctx["session_open"]:
        return INCONSISTENT_CLOCK
    if int(q_ts) > ctx["as_of"]:
        return FUTURE_QUOTE
    if int(e_ts) <= ctx["as_of"]:
        return INCONSISTENT_CLOCK
    if rec.get("right") not in ("C", "P"):
        return MALFORMED
    strike = _num(rec.get("strike"))
    if strike is None or strike <= 0:
        return MALFORMED
    bid, ask = _num(rec.get("bid")), _num(rec.get("ask"))
    if bid is None or ask is None:
        return NONFINITE_QUOTE
    if bid < 0:
        return NEGATIVE_BID
    if ask <= 0:
        return NONPOSITIVE_ASK
    if bid > ask:
        return CROSSED_QUOTE
    if rec.get("condition") not in ctx["conditions"]:
        return BAD_CONDITION
    owner = ctx["forwards"].get(int(e_ts))
    if owner is None:
        return MISSING_FORWARD
    if rec.get("forward") is not None:
        rec_fwd = _num(rec.get("forward"))
        if rec_fwd is None or abs(rec_fwd - owner[0]) > ctx["forward_rel_tol"] * owner[0]:
            return FORWARD_MISMATCH
    return None


def screen_quotes(
    records: Iterable[Any],
    *,
    session: int,
    session_open: int,
    as_of: int,
    forwards: Mapping[Any, Any],
    roots: Sequence[str],
    products: Sequence[str] = ACCEPTED_PRODUCTS,
    conditions: Sequence[str] = ACCEPTED_CONDITIONS,
    forward_rel_tol: float = 1e-6,
) -> dict:
    """Screen raw quotes before fitting; order-invariant and non-mutating.

    A record is a mapping with product, root, style, right ("C"/"P"), strike, bid,
    ask, condition and integer clocks session, quote_ts, expiry_ts. ``forwards``
    maps integer expiry_ts to {"forward": F, "discount": D} from a trusted owner.
    Records whose quote_ts exceeds ``as_of`` are FUTURE_QUOTE and can never displace
    an eligible record. Per coordinate (root, expiry_ts, strike, right) the latest
    quote_ts wins; identical payloads collapse, conflicting payloads at the same
    timestamp reject the coordinate (DUPLICATE_CONFLICT). Every input record is kept
    verbatim (deep copy) either under ``admitted`` or under ``excluded`` with reason.
    """
    if not (_is_int(session) and _is_int(session_open) and _is_int(as_of)):
        raise ValueError("session, session_open and as_of must be integer clocks")
    if int(session_open) > int(as_of):
        raise ValueError("session_open must not exceed as_of")
    recs = list(records)
    if len(recs) > MAX_RECORDS:
        raise ValueError("too many records for a research screen")
    ctx = {
        "session": int(session),
        "session_open": int(session_open),
        "as_of": int(as_of),
        "products": tuple(products),
        "roots": tuple(roots),
        "conditions": tuple(conditions),
        "forwards": _normalize_forwards(forwards),
        "forward_rel_tol": float(forward_rel_tol),
    }
    snapshot = [copy.deepcopy(r) for r in recs]
    order = sorted(range(len(snapshot)), key=lambda i: _canonical(snapshot[i]))
    excluded: list[dict] = []
    groups: dict[tuple, list] = {}
    for i in order:
        rec = snapshot[i]
        reason = _record_reason(rec, ctx)
        if reason is not None:
            excluded.append({"reason": reason, "raw": rec})
            continue
        key = (str(rec["root"]), int(rec["expiry_ts"]), float(rec["strike"]), str(rec["right"]))
        groups.setdefault(key, []).append(rec)
    admitted: list[dict] = []
    for key in sorted(groups):
        grp = groups[key]
        latest = max(int(r["quote_ts"]) for r in grp)
        top = [r for r in grp if int(r["quote_ts"]) == latest]
        for rec in grp:
            if int(rec["quote_ts"]) < latest:
                excluded.append({"reason": SUPERSEDED, "raw": rec})
        payloads = {(float(r["bid"]), float(r["ask"]), str(r.get("condition"))) for r in top}
        if len(payloads) > 1:
            for rec in top:
                excluded.append({"reason": DUPLICATE_CONFLICT, "raw": rec})
            continue
        admitted.append({"key": list(key), "raw": top[0]})
        for rec in top[1:]:
            excluded.append({"reason": DUPLICATE_IDENTICAL, "raw": rec})
    excluded.sort(key=lambda x: (x["reason"], _canonical(x["raw"])))
    counts: dict[str, int] = {"ADMITTED": len(admitted)}
    for item in excluded:
        counts[item["reason"]] = counts.get(item["reason"], 0) + 1
    fwd_list = [[e, f, d] for e, (f, d) in sorted(ctx["forwards"].items())]
    return _stamp({
        "session": ctx["session"],
        "session_open": ctx["session_open"],
        "as_of": ctx["as_of"],
        "roots": sorted(ctx["roots"]),
        "forwards": fwd_list,
        "n_input": len(recs),
        "admitted": admitted,
        "excluded": excluded,
        "counts": dict(sorted(counts.items())),
    })


# --------------------------------------------------------------------------- slices


def build_slices(
    screen: Mapping[str, Any],
    *,
    root: str | None = None,
    min_spread: float = DEFAULT_MIN_SPREAD,
    parity_tol: float = 1e-12,
) -> list[dict]:
    """Normalized undiscounted call bands per expiry from screened quotes.

    Calls give [bid, ask] / (D F); puts are converted by parity, c = p + 1 - K/F.
    Where both legs exist the band is their intersection; an empty intersection is a
    PARITY_CONFLICT node, listed and left out of the fit nodes.
    """
    fwd = {int(e): (float(f), float(d)) for e, f, d in screen["forwards"]}
    roots = sorted({a["key"][0] for a in screen["admitted"]})
    if root is None:
        if len(roots) > 1:
            raise ValueError("several roots admitted; pass root=")
        root = roots[0] if roots else None
    by_exp: dict[int, dict[float, list]] = {}
    for item in screen["admitted"]:
        r_root, e_ts, strike, right = item["key"]
        if r_root != root:
            continue
        f_val, d_val = fwd[int(e_ts)]
        bid = float(item["raw"]["bid"]) / (d_val * f_val)
        ask = float(item["raw"]["ask"]) / (d_val * f_val)
        shift = (1.0 - float(strike) / f_val) if right == "P" else 0.0
        by_exp.setdefault(int(e_ts), {}).setdefault(float(strike), []).append(
            (str(right), bid + shift, ask + shift))
    slices: list[dict] = []
    for e_ts in sorted(by_exp):
        f_val, d_val = fwd[e_ts]
        strikes, lo, hi, legs, conflicts = [], [], [], [], []
        for strike in sorted(by_exp[e_ts]):
            bands = by_exp[e_ts][strike]
            low = max(b[1] for b in bands)
            high = min(b[2] for b in bands)
            rights = "".join(sorted(b[0] for b in bands))
            if low > high + parity_tol:
                conflicts.append({"strike": strike, "state": PARITY_CONFLICT,
                                  "lo": low, "hi": high, "legs": rights})
                continue
            if low > high:
                low = high = 0.5 * (low + high)
            strikes.append(strike)
            lo.append(low)
            hi.append(high)
            legs.append(rights)
        k_arr = np.asarray(strikes, float) / f_val
        lo_arr, hi_arr = np.asarray(lo, float), np.asarray(hi, float)
        slices.append({
            "root": root,
            "expiry_ts": e_ts,
            "tau_ticks": e_ts - int(screen["as_of"]),
            "forward": f_val,
            "discount": d_val,
            "strike": [float(s) for s in strikes],
            "kappa": k_arr.tolist(),
            "lo": lo_arr.tolist(),
            "hi": hi_arr.tolist(),
            "mid": (0.5 * (lo_arr + hi_arr)).tolist(),
            "spread": np.maximum(hi_arr - lo_arr, min_spread).tolist(),
            "legs": legs,
            "parity_conflicts": conflicts,
        })
    return slices


def static_violations(kappa: Sequence[float], values: Sequence[float], *,
                      tol: float = DEFAULT_TOL, anchor: bool = True) -> dict:
    """Exact node-level static checks on normalized call values.

    Bounds (1 - kappa)^+ <= c <= 1, non-increasing in strike, and convex (chord test
    on consecutive nodes, including the c(0) = 1 anchor when ``anchor``).
    """
    x = np.asarray(kappa, float)
    y = np.asarray(values, float)
    if x.ndim != 1 or x.shape != y.shape or x.size == 0:
        raise ValueError("kappa and values must be equal-length 1-d arrays")
    if np.any(x <= 0) or np.any(np.diff(x) <= 0):
        raise ValueError("kappa must be positive and strictly increasing")
    lower = np.maximum(1.0 - x, 0.0)
    bounds = [int(i) for i in np.where((y < lower - tol) | (y > 1.0 + tol))[0]]
    xs = np.concatenate([[0.0], x]) if anchor else x
    ys = np.concatenate([[1.0], y]) if anchor else y
    shift = 1 if anchor else 0
    monotone = [int(i) - shift + 1 for i in np.where(np.diff(ys) > tol)[0]]
    convexity = []
    for b in range(1, xs.size - 1):
        h1, h2 = xs[b] - xs[b - 1], xs[b + 1] - xs[b]
        chord = (h2 * ys[b - 1] + h1 * ys[b + 1]) / (h1 + h2)
        if ys[b] > chord + tol:
            convexity.append(b - shift)
    return {"bounds": bounds, "monotone": monotone, "convexity": convexity,
            "ok": not (bounds or monotone or convexity)}


# ------------------------------------------------------------------- convex benchmark


def _interp_weights(x: np.ndarray, p: float) -> list[tuple[int, float]]:
    if x.size == 1:
        return [(0, 1.0)]
    i = int(np.clip(np.searchsorted(x, p, side="right") - 1, 0, x.size - 2))
    t = (p - x[i]) / (x[i + 1] - x[i])
    return [(i, 1.0 - t), (i + 1, t)]


def _calendar_points(xa: np.ndarray, xb: np.ndarray) -> np.ndarray:
    lo, hi = max(xa[0], xb[0]), min(xa[-1], xb[-1])
    if lo > hi:
        return np.empty(0)
    pts = np.concatenate([xa, xb, [lo, hi]])
    return np.unique(pts[(pts >= lo) & (pts <= hi)])


def fit_benchmark(
    slices: Sequence[Mapping[str, Any]],
    *,
    targets: Sequence[Sequence[float]] | None = None,
    calendar: bool = True,
    violation_tol: float = DEFAULT_VIOLATION_TOL,
    check_grid: int = DEFAULT_GRID,
) -> dict:
    """Convex piecewise-linear benchmark across all slices as one linear program.

    Stage 1 minimizes the spread-weighted L1 distance outside the bid/ask bands
    subject to static and calendar no-arbitrage constraints. If the minimal violation
    exceeds ``violation_tol`` (spread units, any node) the state is BANDS_INFEASIBLE:
    the least-violation projection is reported but is not admissible. Stage 2 keeps
    the stage-1 violation and minimizes the spread-weighted L1 distance to
    ``targets`` (default: band mids). If stage 2 fails, the stage-1 projection is
    reported with ``stage2_fallback=True`` and state SOLVER_FAILED (never admitted);
    ``stage1_state`` keeps the stage-1 band verdict. Calendar constraints are imposed at the union
    of both slices' nodes inside their common support, which is exact for piecewise-
    linear curves. Outside each slice's observed support nothing is claimed.
    """
    use = [s for s in slices if len(s["kappa"]) >= 1]
    if not use:
        return _stamp({"method": "convex_pl_benchmark", "state": NO_DATA,
                       "admissible": False, "slices": []})
    xs = [np.asarray(s["kappa"], float) for s in use]
    los = [np.asarray(s["lo"], float) for s in use]
    his = [np.asarray(s["hi"], float) for s in use]
    wts = [1.0 / np.asarray(s["spread"], float) for s in use]
    if targets is None:
        tgts = [np.asarray(s["mid"], float) for s in use]
    else:
        tgts = [np.asarray(t, float) for t in targets]
    offs = np.cumsum([0] + [x.size for x in xs])
    n = int(offs[-1])
    rows: list[int] = []
    cols: list[int] = []
    vals: list[float] = []
    rhs: list[float] = []

    def add_row(entries: list[tuple[int, float]], bound: float) -> None:
        r = len(rhs)
        for c, v in entries:
            rows.append(r)
            cols.append(c)
            vals.append(v)
        rhs.append(bound)

    for j, x in enumerate(xs):
        o = int(offs[j])
        for i in range(x.size):
            add_row([(o + i, 1.0), (n + o + i, -1.0)], float(his[j][i]))
            add_row([(o + i, -1.0), (2 * n + o + i, -1.0)], -float(los[j][i]))
        for i in range(x.size - 1):
            add_row([(o + i + 1, 1.0), (o + i, -1.0)], 0.0)
        pts = np.concatenate([[0.0], x])
        for b in range(1, pts.size - 1):
            h1, h2 = pts[b] - pts[b - 1], pts[b + 1] - pts[b]
            ca, cc = -h2 / (h1 + h2), -h1 / (h1 + h2)
            entries = [(o + b - 1, 1.0), (o + b, cc)]
            bound = 0.0
            if b - 1 == 0:
                bound = -ca  # anchor value 1 moved to the right-hand side
            else:
                entries.append((o + b - 2, ca))
            add_row(entries, bound)
    n_cal = 0
    if calendar:
        for j in range(len(xs)):
            for k in range(j + 1, len(xs)):
                for p in _calendar_points(xs[j], xs[k]):
                    entries = [(int(offs[j]) + i, w) for i, w in _interp_weights(xs[j], p)]
                    entries += [(int(offs[k]) + i, -w) for i, w in _interp_weights(xs[k], p)]
                    add_row(entries, 0.0)
                    n_cal += 1
    lower_v = np.concatenate([np.maximum(1.0 - x, 0.0) for x in xs])
    n_rows = len(rhs)
    w_all = np.concatenate(wts)
    opts = {"primal_feasibility_tolerance": 1e-10, "dual_feasibility_tolerance": 1e-10}

    a1 = sparse.coo_matrix((vals, (rows, cols)), shape=(n_rows, 3 * n)).tocsr()
    c1 = np.concatenate([np.zeros(n), w_all, w_all])
    bnds1 = [(float(lv), 1.0) for lv in lower_v] + [(0.0, None)] * (2 * n)
    res1 = optimize.linprog(c1, A_ub=a1, b_ub=np.asarray(rhs), bounds=bnds1,
                            method="highs", options=opts)
    if res1.status != 0:
        return _stamp({"method": "convex_pl_benchmark", "state": SOLVER_FAILED,
                       "admissible": False, "solver_message": str(res1.message),
                       "slices": []})
    total_violation = float(res1.fun)

    t_all = np.concatenate(tgts)
    rows2, cols2, vals2, rhs2 = list(rows), list(cols), list(vals), list(rhs)
    r = len(rhs2)
    for g in range(n):
        rows2 += [r, r]
        cols2 += [g, 3 * n + g]
        vals2 += [1.0, -1.0]
        rhs2.append(float(t_all[g]))
        r += 1
        rows2 += [r, r]
        cols2 += [g, 3 * n + g]
        vals2 += [-1.0, -1.0]
        rhs2.append(-float(t_all[g]))
        r += 1
    for g in range(n):
        rows2 += [r, r]
        cols2 += [n + g, 2 * n + g]
        vals2 += [float(w_all[g]), float(w_all[g])]
    rhs2.append(total_violation * (1.0 + 1e-9) + 1e-10)
    r += 1
    a2 = sparse.coo_matrix((vals2, (rows2, cols2)), shape=(r, 4 * n)).tocsr()
    c2 = np.concatenate([np.zeros(3 * n), w_all])
    bnds2 = bnds1 + [(0.0, None)] * n
    res2 = optimize.linprog(c2, A_ub=a2, b_ub=np.asarray(rhs2), bounds=bnds2,
                            method="highs", options=opts)
    # A stage-2 failure leaves only the stage-1 least-violation projection, which is not the
    # pre-registered target fit: it is reported for diagnosis but never admitted (SOLVER_FAILED).
    stage2_fallback = res2.status != 0 or getattr(res2, "x", None) is None
    sol = res1.x if stage2_fallback else res2.x
    v_all = sol[:n]
    viol_all = w_all * (sol[n:2 * n] + sol[2 * n:3 * n])
    max_violation = float(np.max(viol_all)) if n else 0.0
    out_slices = []
    for j, s in enumerate(use):
        o0, o1 = int(offs[j]), int(offs[j + 1])
        out_slices.append({
            "expiry_ts": int(s["expiry_ts"]),
            "kappa": xs[j].tolist(),
            "value": v_all[o0:o1].tolist(),
            "lo": los[j].tolist(),
            "hi": his[j].tolist(),
            "violation_spread_units": viol_all[o0:o1].tolist(),
            "support": [float(xs[j][0]), float(xs[j][-1])],
        })
    stage1_state = ADMISSIBLE if max_violation <= violation_tol else BANDS_INFEASIBLE
    state = SOLVER_FAILED if stage2_fallback else stage1_state
    fit = {
        "method": "convex_pl_benchmark",
        "state": state,
        "stage1_state": stage1_state,
        "min_total_violation_spread_units": total_violation,
        "max_node_violation_spread_units": max_violation,
        "n_calendar_constraints": n_cal,
        "stage2_status": int(res2.status),
        "stage2_fallback": bool(stage2_fallback),
        "slices": out_slices,
    }
    if stage2_fallback:
        fit["solver_message"] = str(getattr(res2, "message", ""))
    check = dense_check_benchmark(fit, n_grid=check_grid)
    fit["dense_check"] = check
    if state == ADMISSIBLE and not check["pass"]:
        fit["state"] = FAILED_CHECK
    fit["admissible"] = fit["state"] == ADMISSIBLE
    return _stamp(fit)


def _price_dense_check(x: np.ndarray, c: np.ndarray, tol: float) -> dict:
    lower = np.maximum(1.0 - x, 0.0)
    bound_gap = float(min(np.min(c - lower), np.min(1.0 - c)))
    worst_mono = float(np.max(np.diff(c))) if c.size > 1 else 0.0
    second = c[:-2] - 2.0 * c[1:-1] + c[2:]
    worst_conv = float(np.min(second)) if second.size else 0.0
    return {
        "n_grid": int(x.size),
        "bounds_ok": bool(np.isfinite(bound_gap) and bound_gap >= -tol),
        "monotone_ok": bool(worst_mono <= tol),
        "convex_ok": bool(worst_conv >= -tol),
        "worst_bound_gap": bound_gap,
        "worst_increase": worst_mono,
        "worst_second_difference": worst_conv,
    }


def dense_check_benchmark(fit: Mapping[str, Any], *, n_grid: int = DEFAULT_GRID,
                          tol: float = DEFAULT_TOL, cal_tol: float = DEFAULT_CAL_TOL) -> dict:
    """Dense-grid strike and calendar checks of piecewise-linear benchmark curves."""
    per_slice, calendar = [], []
    ok = True
    sl = fit.get("slices", [])
    for s in sl:
        x = np.asarray(s["kappa"], float)
        v = np.asarray(s["value"], float)
        grid = np.linspace(x[0], x[-1], n_grid) if x.size > 1 else x.copy()
        res = _price_dense_check(grid, np.interp(grid, x, v), tol)
        exact = static_violations(x, v, tol=tol)
        res["node_exact_ok"] = exact["ok"]
        res["pass"] = bool(res["bounds_ok"] and res["monotone_ok"] and res["convex_ok"]
                           and exact["ok"])
        ok = ok and res["pass"]
        per_slice.append({"expiry_ts": s["expiry_ts"], **res})
    for j in range(len(sl)):
        for k in range(j + 1, len(sl)):
            xa, xb = np.asarray(sl[j]["kappa"], float), np.asarray(sl[k]["kappa"], float)
            lo, hi = max(xa[0], xb[0]), min(xa[-1], xb[-1])
            if lo > hi:
                calendar.append({"pair": [sl[j]["expiry_ts"], sl[k]["expiry_ts"]],
                                 "overlap": None, "pass": True})
                continue
            grid = np.unique(np.concatenate([np.linspace(lo, hi, n_grid),
                                             _calendar_points(xa, xb)]))
            gap = (np.interp(grid, xb, np.asarray(sl[k]["value"], float))
                   - np.interp(grid, xa, np.asarray(sl[j]["value"], float)))
            worst = float(np.min(gap))
            passed = bool(worst >= -cal_tol)
            ok = ok and passed
            calendar.append({"pair": [sl[j]["expiry_ts"], sl[k]["expiry_ts"]],
                             "overlap": [float(lo), float(hi)], "worst_gap": worst,
                             "n_grid": int(grid.size), "pass": passed})
    return {"slices": per_slice, "calendar": calendar, "pass": bool(ok),
            "tol": tol, "cal_tol": cal_tol}


# --------------------------------------------------------------------- SVI challenger


def black76_normalized_call(k: Any, w: Any) -> np.ndarray:
    """Undiscounted normalized call E[(S/F - e^k)^+] under Black-76 with total variance w.

    Private research helper (see module docstring): production code must reuse the
    incumbent single pricing kernel.
    """
    k_arr, w_arr = np.broadcast_arrays(np.asarray(k, float), np.asarray(w, float))
    shape = k_arr.shape
    k_flat, w_flat = k_arr.reshape(-1), w_arr.reshape(-1)
    out = np.maximum(1.0 - np.exp(k_flat), 0.0).astype(float)
    pos = w_flat > 1e-14
    if np.any(pos):
        sw = np.sqrt(w_flat[pos])
        kk = k_flat[pos]
        d1 = -kk / sw + 0.5 * sw
        out[pos] = norm.cdf(d1) - np.exp(kk) * norm.cdf(d1 - sw)
    return out.reshape(shape)


def implied_total_variance(k: float, c: float, *, w_max: float = 16.0) -> float:
    """Total implied variance for a normalized call; NaN outside the arbitrage bounds."""
    intrinsic = max(1.0 - math.exp(k), 0.0)
    if not math.isfinite(c) or c < intrinsic - 1e-12 or c >= 1.0:
        return float("nan")
    if c <= intrinsic + 1e-14:
        return 0.0
    f_hi = float(black76_normalized_call(k, w_max)) - c
    if f_hi < 0:
        return float("nan")
    return float(optimize.brentq(lambda w: float(black76_normalized_call(k, w)) - c,
                                 1e-14, w_max, xtol=1e-15, rtol=1e-12, maxiter=200))


def svi_total_variance(params: Sequence[float], k: Any) -> np.ndarray:
    a, b, rho, m, sig = (float(p) for p in params)
    d = np.asarray(k, float) - m
    return a + b * (rho * d + np.sqrt(d * d + sig * sig))


def svi_min_variance(params: Sequence[float]) -> float:
    a, b, rho, _m, sig = (float(p) for p in params)
    return a + b * sig * math.sqrt(max(1.0 - rho * rho, 0.0))


def svi_g(params: Sequence[float], k: Any) -> np.ndarray:
    """Gatheral-Jacquier butterfly function g(k); -inf where total variance <= 0."""
    a, b, rho, m, sig = (float(p) for p in params)
    kk = np.asarray(k, float)
    d = kk - m
    r = np.sqrt(d * d + sig * sig)
    w = a + b * (rho * d + r)
    w1 = b * (rho + d / r)
    w2 = b * sig * sig / (r ** 3)
    with np.errstate(divide="ignore", invalid="ignore"):
        g = (1.0 - kk * w1 / (2.0 * w)) ** 2 - 0.25 * w1 * w1 * (1.0 / w + 0.25) + 0.5 * w2
    return np.where(w > 0, g, -np.inf)


def check_svi_slice(params: Sequence[float], support_k: Sequence[float], *,
                    n_grid: int = DEFAULT_GRID, tol: float = DEFAULT_TOL,
                    g_tol: float = DEFAULT_G_TOL) -> dict:
    """Dense-grid static checks of one SVI slice over its supported log-moneyness range."""
    a, b, rho, _m, _s = (float(p) for p in params)
    k_lo, k_hi = float(support_k[0]), float(support_k[1])
    kg = np.linspace(k_lo, k_hi, n_grid) if k_hi > k_lo else np.asarray([k_lo])
    w = svi_total_variance(params, kg)
    g = svi_g(params, kg)
    kappa_grid = np.linspace(math.exp(k_lo), math.exp(k_hi), n_grid) if k_hi > k_lo \
        else np.asarray([math.exp(k_lo)])
    c = black76_normalized_call(np.log(kappa_grid), np.maximum(
        svi_total_variance(params, np.log(kappa_grid)), 0.0))
    price = _price_dense_check(kappa_grid, c, tol)
    out = {
        "min_variance": svi_min_variance(params),
        "min_variance_ok": bool(svi_min_variance(params) >= 0 and np.all(w > 0)),
        "lee_ok": bool(b * (1.0 + abs(rho)) <= 2.0 + tol),
        "min_g": float(np.min(g)),
        "butterfly_ok": bool(np.min(g) >= -g_tol),
        "n_grid": int(kg.size),
        **{f"price_{key}": val for key, val in price.items()},
    }
    out["pass"] = bool(out["min_variance_ok"] and out["lee_ok"] and out["butterfly_ok"]
                       and price["bounds_ok"] and price["monotone_ok"] and price["convex_ok"])
    return out


def check_svi_calendar(params_short: Sequence[float], support_short: Sequence[float],
                       params_long: Sequence[float], support_long: Sequence[float], *,
                       n_grid: int = DEFAULT_GRID, cal_tol: float = DEFAULT_CAL_TOL) -> dict:
    """Dense-grid calendar check w_long(k) >= w_short(k) over the common support."""
    lo = max(float(support_short[0]), float(support_long[0]))
    hi = min(float(support_short[1]), float(support_long[1]))
    if lo > hi:
        return {"overlap": None, "pass": True}
    kg = np.linspace(lo, hi, n_grid) if hi > lo else np.asarray([lo])
    gap = svi_total_variance(params_long, kg) - svi_total_variance(params_short, kg)
    worst = float(np.min(gap))
    return {"overlap": [lo, hi], "worst_gap": worst, "n_grid": int(kg.size),
            "pass": bool(worst >= -cal_tol)}


def check_svi_surface(params_list: Sequence[Sequence[float] | None],
                      supports_k: Sequence[Sequence[float]], *,
                      n_grid: int = DEFAULT_GRID, tol: float = DEFAULT_TOL,
                      g_tol: float = DEFAULT_G_TOL, cal_tol: float = DEFAULT_CAL_TOL) -> dict:
    """Dense static checks per slice and calendar checks for every ordered pair."""
    statics, calendars = [], []
    ok = True
    for p, sup in zip(params_list, supports_k):
        if p is None:
            statics.append({"pass": False, "state": NOT_ADMITTED})
            ok = False
            continue
        res = check_svi_slice(p, sup, n_grid=n_grid, tol=tol, g_tol=g_tol)
        statics.append(res)
        ok = ok and res["pass"]
    for j in range(len(params_list)):
        for k in range(j + 1, len(params_list)):
            if params_list[j] is None or params_list[k] is None:
                continue
            res = check_svi_calendar(params_list[j], supports_k[j], params_list[k],
                                     supports_k[k], n_grid=n_grid, cal_tol=cal_tol)
            res["pair"] = [j, k]
            calendars.append(res)
            ok = ok and res["pass"]
    return {"slices": statics, "calendar": calendars, "pass": bool(ok)}


def _svi_objective(p: np.ndarray, k: np.ndarray, lo: np.ndarray, hi: np.ndarray,
                   tgt: np.ndarray, spread: np.ndarray, lam: float, kg: np.ndarray,
                   floor: np.ndarray | None) -> float:
    w = svi_total_variance(p, k)
    if not np.all(np.isfinite(w)):
        return 1e12
    c = black76_normalized_call(k, np.maximum(w, 0.0))
    out_band = (np.maximum(lo - c, 0.0) + np.maximum(c - hi, 0.0)) / spread
    val = float(np.mean(out_band ** 2) + lam * np.mean(((c - tgt) / spread) ** 2))
    a, b, rho, _m, _s = p
    pen = max(1e-6 - svi_min_variance(p), 0.0) ** 2 + max(b * (1 + abs(rho)) - 2.0, 0.0) ** 2
    g = svi_g(p, kg)
    g = np.where(np.isfinite(g), g, -1.0)
    pen += float(np.mean(np.minimum(g - 1e-6, 0.0) ** 2))
    if floor is not None:
        wg = svi_total_variance(p, kg)
        gap = np.where(np.isfinite(floor), wg - floor - 1e-7, 0.0)
        pen += 1e3 * float(np.mean(np.minimum(gap, 0.0) ** 2))
    return val + 1e4 * pen


def fit_svi_surface(
    slices: Sequence[Mapping[str, Any]],
    *,
    targets: Sequence[Sequence[float]] | None = None,
    lam: float = 0.1,
    seed: int = 0,
    n_starts: int = 6,
    penalty_grid: int = 81,
    check_grid: int = DEFAULT_GRID,
    maxiter: int = 400,
) -> dict:
    """Raw-SVI challenger fitted slice by slice (shortest expiry first).

    Objective per slice: mean squared out-of-band distance in spread units plus
    ``lam`` times the squared distance to the targets (default mids), plus penalties
    for negative minimum variance, the Lee wing bound b(1+|rho|) <= 2, negative g(k)
    on a penalty grid, and calendar crossings below every earlier admitted slice.
    Seeded multi-start L-BFGS-B; no finite optimum -> FAILED_FIT; dense post-checks
    failing -> FAILED_CHECK. Only ADMITTED slices are ever evaluated as supported.
    """
    rng = np.random.default_rng(seed)
    out_slices: list[dict] = []
    admitted: list[tuple[list[float], list[float]]] = []
    for j, s in enumerate(slices):
        kappa = np.asarray(s["kappa"], float)
        entry: dict[str, Any] = {"expiry_ts": int(s["expiry_ts"]), "params": None,
                                 "support_kappa": None, "support_k": None}
        if kappa.size < 3:
            entry.update({"state": FAILED_FIT, "reason": "fewer than 3 nodes"})
            out_slices.append(entry)
            continue
        k = np.log(kappa)
        lo, hi = np.asarray(s["lo"], float), np.asarray(s["hi"], float)
        spread = np.asarray(s["spread"], float)
        tgt = np.asarray(targets[j], float) if targets is not None else np.asarray(s["mid"], float)
        support_k = [float(k[0]), float(k[-1])]
        entry["support_k"] = support_k
        entry["support_kappa"] = [float(kappa[0]), float(kappa[-1])]
        kg = np.linspace(support_k[0], support_k[1], penalty_grid)
        floor = None
        if admitted:
            floor = np.full(kg.size, -np.inf)
            for p_prev, sup_prev in admitted:
                inside = (kg >= sup_prev[0]) & (kg <= sup_prev[1])
                floor = np.where(inside, np.maximum(floor, svi_total_variance(p_prev, kg)), floor)
        w_mid = np.asarray([implied_total_variance(float(ki), float(ci)) for ki, ci in zip(k, tgt)])
        finite = w_mid[np.isfinite(w_mid) & (w_mid > 0)]
        w_atm = float(np.median(finite)) if finite.size else 0.04
        m_lo, m_hi = support_k[0] - 1.0, support_k[1] + 1.0
        bounds = [(_SVI_LOWER[0], _SVI_UPPER[0]), (_SVI_LOWER[1], _SVI_UPPER[1]),
                  (_SVI_LOWER[2], _SVI_UPPER[2]), (m_lo, m_hi), (_SVI_LOWER[4], _SVI_UPPER[4])]
        k_min_w = float(k[int(np.nanargmin(np.where(np.isfinite(w_mid), w_mid, np.inf)))]) \
            if finite.size else 0.0
        b0 = max(2.5 * w_atm, 1e-4)
        starts = [np.asarray([w_atm - 0.1 * b0, b0, -0.3, k_min_w, 0.1])]
        for _ in range(max(n_starts - 1, 0)):
            sig0 = rng.uniform(0.02, 0.5)
            rho0 = rng.uniform(-0.9, 0.5)
            bb = max(w_atm * math.exp(rng.uniform(math.log(0.5), math.log(20.0))), 1e-5)
            starts.append(np.asarray([
                w_atm - bb * sig0 * math.sqrt(1.0 - rho0 * rho0) * rng.uniform(0.5, 1.0),
                bb, rho0, rng.uniform(support_k[0], support_k[1]), sig0]))
        best = None
        for x0 in starts:
            x0 = np.clip(x0, [b[0] for b in bounds], [b[1] for b in bounds])
            try:
                res = optimize.minimize(_svi_objective, x0, method="L-BFGS-B", bounds=bounds,
                                        args=(k, lo, hi, tgt, spread, lam, kg, floor),
                                        options={"maxiter": maxiter})
            except (ValueError, FloatingPointError):
                continue
            if np.isfinite(res.fun) and np.all(np.isfinite(res.x)):
                if best is None or res.fun < best.fun - 1e-15:
                    best = res
        if best is None or best.fun >= 1e12:
            entry.update({"state": FAILED_FIT, "reason": "no finite optimum"})
            out_slices.append(entry)
            continue
        params = [float(v) for v in best.x]
        static = check_svi_slice(params, support_k, n_grid=check_grid)
        cal = [check_svi_calendar(p_prev, sup_prev, params, support_k, n_grid=check_grid)
               for p_prev, sup_prev in admitted]
        passed = static["pass"] and all(c["pass"] for c in cal)
        w_nodes = svi_total_variance(params, k)
        c_nodes = black76_normalized_call(k, np.maximum(w_nodes, 0.0))
        oob = (np.maximum(lo - c_nodes, 0.0) + np.maximum(c_nodes - hi, 0.0)) / spread
        entry.update({
            "state": ADMITTED if passed else FAILED_CHECK,
            "params": params,
            "objective": float(best.fun),
            "optimizer_message": str(best.message),
            "static_check": static,
            "calendar_checks": cal,
            "out_of_band_spread_units": oob.tolist(),
            "inside_bands": bool(float(np.max(oob)) <= DEFAULT_VIOLATION_TOL),
        })
        if passed:
            admitted.append((params, support_k))
        out_slices.append(entry)
    states = [e["state"] for e in out_slices]
    return _stamp({
        "method": "constrained_raw_svi",
        "seed": int(seed),
        "n_starts": int(n_starts),
        "lam": float(lam),
        "slices": out_slices,
        "state": "|".join(states) if states else NO_DATA,
        "surface_admitted": bool(states) and all(st == ADMITTED for st in states),
        "all_inside_bands": bool(states) and all(bool(e.get("inside_bands")) for e in out_slices),
    })


# ------------------------------------------------------------- evaluation and support


def evaluate_at(fit: Mapping[str, Any], slice_index: int, kappa_points: Sequence[float]) -> dict:
    """Values and support flags of one fitted slice at the requested kappa points.

    Benchmark: SUPPORTED inside the observed strike range, UNAVAILABLE (no value)
    outside. SVI: SUPPORTED inside, EXTRAPOLATED outside (value returned, flagged),
    NOT_ADMITTED (no value) when the slice failed its fit or checks.
    """
    s = fit["slices"][slice_index]
    pts = np.asarray(kappa_points, float)
    values: list[float | None] = []
    flags: list[str] = []
    if fit["method"] == "convex_pl_benchmark":
        x = np.asarray(s["kappa"], float)
        v = np.asarray(s["value"], float)
        usable = fit.get("state") == ADMISSIBLE
        for p in pts:
            if not usable:
                values.append(None)
                flags.append(NOT_ADMITTED)
            elif x[0] - 1e-15 <= p <= x[-1] + 1e-15:
                values.append(float(np.interp(p, x, v)))
                flags.append(SUPPORTED)
            else:
                values.append(None)
                flags.append(UNAVAILABLE)
    else:
        if s.get("state") != ADMITTED:
            return {"value": [None] * pts.size, "flag": [NOT_ADMITTED] * pts.size}
        lo, hi = s["support_kappa"]
        for p in pts:
            if p <= 0:
                values.append(None)
                flags.append(UNAVAILABLE)
                continue
            kk = math.log(p)
            values.append(float(black76_normalized_call(kk, max(float(
                svi_total_variance(s["params"], kk)), 0.0))))
            flags.append(SUPPORTED if lo - 1e-15 <= p <= hi + 1e-15 else EXTRAPOLATED)
    return {"value": values, "flag": flags}


def _fit_any(method: str, slices: Sequence[Mapping[str, Any]],
             targets: Sequence[Sequence[float]] | None, svi_options: Mapping[str, Any]) -> dict:
    if method == "benchmark":
        return fit_benchmark(slices, targets=targets)
    if method == "svi":
        return fit_svi_surface(slices, targets=targets, **dict(svi_options))
    raise ValueError("method must be 'benchmark' or 'svi'")


def perturbation_sensitivity(
    slices: Sequence[Mapping[str, Any]],
    *,
    method: str = "benchmark",
    n_draws: int = 8,
    seed: int = 0,
    n_grid: int = 101,
    tail_kappa: Sequence[float] = (),
    svi_options: Mapping[str, Any] | None = None,
) -> dict:
    """Refit under seeded draws inside each bid/ask band and report the spread.

    For every draw each node target is uniform in [lo, hi]. Reported per slice over
    the supported grid: max and median range of fitted values, max standard
    deviation, range of the implied density proxy (benchmark: probability mass at
    nodes from slope changes; SVI: second differences / h^2 on a uniform kappa grid),
    plus the fraction of draws whose fit state differs from the unperturbed fit.
    ``tail_kappa`` points are reported with their support flags, never as supported.
    """
    if n_draws < 1 or n_draws > 1000:
        raise ValueError("n_draws must be in [1, 1000]")
    svi_opts = dict(svi_options or {})
    rng = np.random.default_rng(seed)
    base = _fit_any(method, slices, None, svi_opts)
    base_state = base["state"]
    grids = []
    for s in base["slices"]:
        if method == "benchmark":
            sup = s["support"]
        else:
            sup = s.get("support_kappa") or [float("nan"), float("nan")]
        grids.append(np.linspace(sup[0], sup[1], n_grid) if np.all(np.isfinite(sup))
                     else np.empty(0))
    vals = [[] for _ in grids]
    dens = [[] for _ in grids]
    states = []
    for _ in range(n_draws):
        tg = [np.asarray(s["lo"], float) + rng.uniform(size=len(s["lo"]))
              * (np.asarray(s["hi"], float) - np.asarray(s["lo"], float)) for s in slices]
        fit = _fit_any(method, slices, tg, svi_opts)
        states.append(fit["state"])
        for j, grid in enumerate(grids):
            if grid.size == 0 or j >= len(fit["slices"]):
                continue
            ev = evaluate_at(fit, j, grid)
            row = np.asarray([np.nan if v is None else v for v in ev["value"]], float)
            vals[j].append(row)
            if method == "benchmark":
                x = np.asarray(fit["slices"][j]["kappa"], float)
                v = np.asarray(fit["slices"][j]["value"], float)
                slopes = np.diff(np.concatenate([[1.0], v])) / np.diff(np.concatenate([[0.0], x]))
                dens[j].append(np.diff(slopes))
            elif grid.size > 2 and np.all(np.isfinite(row)):
                h = grid[1] - grid[0]
                dens[j].append((row[:-2] - 2.0 * row[1:-1] + row[2:]) / (h * h))
    per_slice = []
    for j, s in enumerate(base["slices"]):
        arr = np.asarray(vals[j]) if vals[j] else np.empty((0, 0))
        entry = {"expiry_ts": s["expiry_ts"], "n_draws_with_values": int(arr.shape[0])}
        if arr.size and np.isfinite(arr).any():
            rng_v = np.nanmax(arr, axis=0) - np.nanmin(arr, axis=0)
            entry.update({
                "value_range_max": float(np.nanmax(rng_v)),
                "value_range_median": float(np.nanmedian(rng_v)),
                "value_std_max": float(np.nanmax(np.nanstd(arr, axis=0))),
            })
        if dens[j]:
            d_arr = np.asarray(dens[j])
            entry["density_range_max"] = float(np.max(np.max(d_arr, axis=0) - np.min(d_arr, axis=0)))
            entry["density_kind"] = "node_mass" if method == "benchmark" else "grid_second_difference"
        if tail_kappa:
            entry["tail"] = evaluate_at(base, j, tail_kappa)["flag"]
        per_slice.append(entry)
    changed = sum(1 for st in states if st != base_state)
    return _stamp({
        "method": method,
        "seed": int(seed),
        "n_draws": int(n_draws),
        "base_state": base_state,
        "state_change_fraction": changed / float(n_draws),
        "slices": per_slice,
    })


# ----------------------------------------------------------------- synthetic helper


def synthetic_svi_records(
    params_list: Sequence[Sequence[float]],
    expiries: Sequence[int],
    strikes: Sequence[float],
    *,
    forward: float = 100.0,
    discount: float = 1.0,
    half_spread_frac: float = 0.02,
    half_spread_floor: float = 0.01,
    session: int = 1,
    as_of: int = 390,
    quote_ts: int | None = None,
    root: str = "SPX",
    include_puts: bool = True,
    noise_seed: int | None = None,
) -> tuple[list[dict], dict[int, dict[str, float]]]:
    """European call/put quotes generated from known SVI slices (integer clocks only).

    Bid/ask straddle the model price by max(floor, frac * price); with ``noise_seed``
    the quote centre is jittered inside its own band. For tests and mechanics checks
    only; nothing generated here is evidence about any market.
    """
    if len(params_list) != len(expiries):
        raise ValueError("one parameter set per expiry")
    rng = np.random.default_rng(noise_seed) if noise_seed is not None else None
    q_ts = as_of - 1 if quote_ts is None else quote_ts
    records: list[dict] = []
    fwds: dict[int, dict[str, float]] = {}
    for params, e_ts in zip(params_list, expiries):
        fwds[int(e_ts)] = {"forward": float(forward), "discount": float(discount)}
        for strike in strikes:
            kk = math.log(float(strike) / forward)
            c = float(black76_normalized_call(kk, max(float(svi_total_variance(params, kk)), 0.0)))
            call = discount * forward * c
            put = call - discount * (forward - float(strike))
            for right, px in (("C", call), ("P", put)) if include_puts else (("C", call),):
                half = max(half_spread_floor, half_spread_frac * px)
                centre = px + (rng.uniform(-0.5, 0.5) * half if rng is not None else 0.0)
                records.append({
                    "product": "INDEX_OPTION", "root": root, "style": "EUROPEAN",
                    "right": right, "strike": float(strike),
                    "bid": max(centre - half, 0.0), "ask": centre + half,
                    "condition": "REGULAR", "session": int(session),
                    "quote_ts": int(q_ts), "expiry_ts": int(e_ts),
                })
    return records, fwds
