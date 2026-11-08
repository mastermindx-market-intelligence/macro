from __future__ import annotations

__doc__ = """RESEARCH REFERENCE — NOT WIRED. Q19 first-passage ambiguity and censoring-aware
outcome diagnostics.

Verdict and evidence (Q19, quant assessment 2026-10) live only in
``research/quant_assessment_2026_10/Q19_censoring_path_ambiguity/VERDICT.md``; this
module carries no verdict text, so its bytes do not change when a verdict is written.
This is a research measurement-resolution diagnostic only. It carries no signal, edge,
grade, rank, gate or promotion authority, nothing imports it, and it registers nothing.

What it does (pure functions, bounded inputs, no I/O, no clock reads):

* ``bar_touch`` / ``first_passage``: classify which barrier a path crossed first
  from OHLC-style windows. When both barriers fall inside one window, the answer is
  ``"ambiguous"``, never an invented exact winner. The same OHLC is compatible with
  opposite intrabar orders.
* ``classify_attrition``: maps ledger status/reason into explicit attrition states.
  Pending/unmatured cases are administrative and are never losses. Delisted, halted
  and missing-data cases are ``informative_unknown`` by default, never benign
  censoring, unless the caller explicitly admits a non-informative assumption.
* ``evidence_admissible`` / ``refine_state``: join higher-resolution evidence only
  when its availability clock and rights permit the question, and only to narrow an
  ambiguous state consistently.
* ``first_passage_bounds``: identified best/worst (Manski) bounds with full
  denominator disclosure (complete, ambiguous, pending, unavailable, informative).
* ``cumulative_incidence``: a cause-specific Aalen-Johansen estimate that states its
  censoring assumptions. It fails to bounds when they are unsupported (informative
  or unadmitted censoring, or interval-ambiguous events), and to unavailable when
  there are no units.
* ``attach_diagnostic``: returns a copy of a canonical record with the diagnostic
  in its own namespace. Canonical IDs, grades and fixed horizons never change.
* ``circular_block_bootstrap``: dependence-aware percentile intervals over ordered
  blocks (for example session dates).
"""

import copy
import math
from typing import Any, Callable, Iterable, Mapping, Sequence

import numpy as np

RESEARCH_ONLY = True

UPPER_FIRST = "upper_first"
LOWER_FIRST = "lower_first"
AMBIGUOUS = "ambiguous"
NEITHER = "neither"
FIRST_PASSAGE_STATES = (UPPER_FIRST, LOWER_FIRST, AMBIGUOUS, NEITHER)

# Attrition / censoring classes. Only ``observed`` units enter the identified
# first-passage numerator; every other class stays in the disclosed denominator.
OBSERVED = "observed"
ADMINISTRATIVE_PENDING = "administrative_pending"
INFORMATIVE_UNKNOWN = "informative_unknown"
ASSUMED_NONINFORMATIVE = "assumed_noninformative"
INVALID = "invalid"
CENSORING_CLASSES = (OBSERVED, ADMINISTRATIVE_PENDING, INFORMATIVE_UNKNOWN,
                     ASSUMED_NONINFORMATIVE, INVALID)

# Reasons that are NEVER benign by default (requirement 3).
INFORMATIVE_REASONS = frozenset({
    "delisted", "halted", "trading_halt", "missing_data", "missing_bars",
    "price_unavailable", "unavailable", "no_price_path", "corporate_action_gap",
})
PENDING_STATUSES = frozenset({"pending", "unmatured", "open"})

CANONICAL_KEYS = ("episode_id", "outcome_id", "cohort_id", "grade", "horizon",
                  "horizon_sessions", "horizon_minutes", "status")
DIAGNOSTIC_NAMESPACE = "q19_first_passage_diagnostic"

MAX_WINDOWS = 100_000
MAX_UNITS = 5_000_000


def _finite_pos(x: object) -> bool:
    return (isinstance(x, (int, float, np.integer, np.floating))
            and not isinstance(x, (bool, np.bool_))
            and math.isfinite(float(x)) and float(x) > 0)


def bar_touch(high: float, low: float, upper: float, lower: float) -> str:
    """Return which barriers one window touches: 'upper', 'lower', 'both' or 'none'.

    A window is any OHLC aggregate (a bar or a cumulative-extremum segment). It
    carries no within-window ordering, so 'both' is not resolvable from it.
    """
    for v in (high, low, upper, lower):
        if not _finite_pos(v):
            raise ValueError("invalid_price")
    if float(low) > float(high):
        raise ValueError("low_above_high")
    if not float(lower) < float(upper):
        raise ValueError("barrier_order")
    up = float(high) >= float(upper)
    dn = float(low) <= float(lower)
    if up and dn:
        return "both"
    if up:
        return "upper"
    if dn:
        return "lower"
    return "none"


def first_passage(windows: Sequence[tuple[float, float]], upper: float, lower: float,
                  *, cumulative: bool = False) -> dict[str, Any]:
    """First-passage state from time-ordered (high, low) windows.

    ``cumulative=True`` means each window is a running extremum from the same entry
    (nested horizons). Then highs must be non-decreasing and lows non-increasing,
    and the first window whose running extremum crosses a barrier is the window in
    which the crossing happened.

    Returns ``{"state", "window_index", "n_windows"}``. ``state`` is 'ambiguous'
    when both barriers are first crossed inside the same window.
    """
    if not isinstance(windows, (list, tuple)) or len(windows) > MAX_WINDOWS:
        raise ValueError("windows_required")
    if len(windows) == 0:
        raise ValueError("empty_path")
    prev_h = prev_l = None
    touches: list[str] = []
    for w in windows:  # validate the whole path before reading any crossing
        if not isinstance(w, (list, tuple)) or len(w) != 2:
            raise ValueError("window_shape")
        h, low = w
        touches.append(bar_touch(h, low, upper, lower))
        if cumulative and prev_h is not None:
            if float(h) < prev_h or float(low) > prev_l:
                raise ValueError("non_nested_extrema")
        prev_h, prev_l = float(h), float(low)
    for i, touch in enumerate(touches):
        if touch == "both":
            return {"state": AMBIGUOUS, "window_index": i, "n_windows": len(windows)}
        if touch == "upper":
            return {"state": UPPER_FIRST, "window_index": i, "n_windows": len(windows)}
        if touch == "lower":
            return {"state": LOWER_FIRST, "window_index": i, "n_windows": len(windows)}
    return {"state": NEITHER, "window_index": None, "n_windows": len(windows)}


def ordering_convention(state: str, convention: str) -> str:
    """Resolve an ambiguous state by a named convention, for comparison only.

    'optimistic' maps ambiguous to upper_first and 'pessimistic' to lower_first.
    'identified' leaves it ambiguous. These conventions exist only to measure how
    far a forced winner departs from the identified bounds.
    """
    if state not in FIRST_PASSAGE_STATES:
        raise ValueError("unknown_state")
    if convention == "identified" or state != AMBIGUOUS:
        return state
    if convention == "optimistic":
        return UPPER_FIRST
    if convention == "pessimistic":
        return LOWER_FIRST
    raise ValueError("unknown_convention")


def classify_attrition(status: str | None, reason: str | None = None, *,
                       admitted_noninformative: Iterable[str] = ()) -> dict[str, Any]:
    """Map a ledger status/reason to an explicit censoring class.

    * complete             -> observed
    * pending/unmatured    -> administrative_pending (never a loss, never dropped)
    * delisted/halted/missing/unavailable -> informative_unknown, unless the reason
      is listed in ``admitted_noninformative`` (an explicit, caller-owned
      assumption), in which case -> assumed_noninformative
    * incomplete with a structural horizon reason -> administrative_pending
    * anything else unrecognised -> informative_unknown (fail closed)
    """
    admitted = frozenset(admitted_noninformative)
    s = (status or "").strip().lower()
    r = (reason or "").strip().lower()
    if s == "complete" and not r:
        return {"class": OBSERVED, "status": s, "reason": None, "benign": False}
    if s in PENDING_STATUSES:
        return {"class": ADMINISTRATIVE_PENDING, "status": s, "reason": r or None, "benign": False}
    if s == "invalid":
        return {"class": INVALID, "status": s, "reason": r or None, "benign": False}
    if r in INFORMATIVE_REASONS or s in INFORMATIVE_REASONS:
        key = r if r in INFORMATIVE_REASONS else s
        if key in admitted:
            return {"class": ASSUMED_NONINFORMATIVE, "status": s, "reason": key,
                    "benign": False, "assumption": "caller_admitted_noninformative"}
        return {"class": INFORMATIVE_UNKNOWN, "status": s, "reason": key, "benign": False}
    if s == "incomplete" and r in {"decision_after_session_close", "horizon_crosses_session_close",
                                   "decision_after_target_close"}:
        return {"class": ADMINISTRATIVE_PENDING, "status": s, "reason": r, "benign": False}
    return {"class": INFORMATIVE_UNKNOWN, "status": s or None, "reason": r or None, "benign": False}


def evidence_admissible(question_clock: int, evidence_available_at: int | None, *,
                        rights_ok: bool, same_entry: bool,
                        same_price_basis: bool = True) -> tuple[bool, str]:
    """Whether finer evidence may answer the question asked at ``question_clock``.

    Clocks are caller-supplied integers (for example epoch seconds); nothing here
    reads a wall clock. Evidence must already be available at the question clock,
    carry rights for this use, describe the same entry, and share the price basis.
    """
    if not isinstance(question_clock, (int, np.integer)) or isinstance(question_clock, bool):
        raise ValueError("integer_clock_required")
    if evidence_available_at is None:
        return False, "availability_unknown"
    if not isinstance(evidence_available_at, (int, np.integer)) or isinstance(evidence_available_at, bool):
        raise ValueError("integer_clock_required")
    if rights_ok is not True:
        return False, "rights_not_admitted"
    if same_entry is not True:
        return False, "entry_mismatch"
    if same_price_basis is not True:
        return False, "price_basis_mismatch"
    if int(evidence_available_at) > int(question_clock):
        return False, "not_available_at_question_clock"
    return True, "admitted"


def refine_state(coarse: str, fine: str | None, admissible: bool) -> dict[str, Any]:
    """Narrow a coarse state with finer evidence, only when admissible and consistent.

    Identified coarse states are never overwritten. An identified fine state that
    contradicts an identified coarse state is flagged and ignored. An ambiguous
    coarse state may become identified, or stay ambiguous.
    """
    if coarse not in FIRST_PASSAGE_STATES:
        raise ValueError("unknown_state")
    if fine is not None and fine not in FIRST_PASSAGE_STATES:
        raise ValueError("unknown_state")
    if not admissible or fine is None:
        return {"state": coarse, "refined": False, "note": "no_admissible_evidence"}
    if coarse == AMBIGUOUS:
        if fine == NEITHER:
            return {"state": coarse, "refined": False, "note": "inconsistent_evidence"}
        return {"state": fine, "refined": fine != AMBIGUOUS, "note": "refined" if fine != AMBIGUOUS else "still_ambiguous"}
    if fine != coarse:
        return {"state": coarse, "refined": False, "note": "inconsistent_evidence"}
    return {"state": coarse, "refined": False, "note": "consistent"}


def first_passage_bounds(units: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Identified bounds with full denominator disclosure.

    Each unit is ``{"censoring": <class>, "state": <first-passage state or None>}``.
    Only ``observed`` units carry a state. Nothing is dropped: every class is
    counted, and full-denominator bounds treat every non-observed unit as unknown.
    """
    if len(units) > MAX_UNITS:
        raise ValueError("too_many_units")
    counts = {c: 0 for c in CENSORING_CLASSES}
    states = {s: 0 for s in FIRST_PASSAGE_STATES}
    for u in units:
        c = u.get("censoring")
        if c not in counts:
            raise ValueError("unknown_censoring_class")
        counts[c] += 1
        if c == OBSERVED:
            s = u.get("state")
            if s not in states:
                raise ValueError("observed_unit_without_state")
            states[s] += 1
    n_total = len(units)
    n_obs = counts[OBSERVED]
    n_unknown = n_total - n_obs
    up, lo, amb = states[UPPER_FIRST], states[LOWER_FIRST], states[AMBIGUOUS]

    def _r(a: int, b: int) -> float | None:
        return a / b if b > 0 else None

    return {
        "denominator": {"n_total": n_total, "n_observed": n_obs, "n_unknown": n_unknown,
                        **{f"n_{k}": v for k, v in counts.items() if k != OBSERVED}},
        "states": states,
        "observed": {
            "upper_first": [_r(up, n_obs), _r(up + amb, n_obs)],
            "lower_first": [_r(lo, n_obs), _r(lo + amb, n_obs)],
            "ambiguous_share": _r(amb, n_obs),
            "optimistic_upper_first": _r(up + amb, n_obs),
            "pessimistic_upper_first": _r(up, n_obs),
        },
        "full_denominator": {
            "upper_first": [_r(up, n_total), _r(up + amb + n_unknown, n_total)],
            "lower_first": [_r(lo, n_total), _r(lo + amb + n_unknown, n_total)],
        },
        "pending_counted_as_loss": False,
        "dropped_units": 0,
    }


def _aalen_johansen(times: np.ndarray, causes: np.ndarray, grid: Sequence[float]) -> dict[int, list[float]]:
    """Cause-specific AJ cumulative incidence; cause 0 means censored."""
    order = np.lexsort((causes == 0, times))  # events before censoring at tied times
    t = times[order]
    c = causes[order]
    n = len(t)
    surv = 1.0
    cif = {1: 0.0, 2: 0.0}
    steps: list[tuple[float, float, float]] = []
    i = 0
    at_risk = n
    while i < n:
        tj = t[i]
        j = i
        d = {1: 0, 2: 0}
        cens = 0
        while j < n and t[j] == tj:
            if c[j] == 0:
                cens += 1
            else:
                d[int(c[j])] += 1
            j += 1
        if at_risk > 0:
            for k in (1, 2):
                cif[k] += surv * d[k] / at_risk
            surv *= 1.0 - (d[1] + d[2]) / at_risk
        steps.append((float(tj), cif[1], cif[2]))
        at_risk -= (j - i)
        i = j
    out = {1: [], 2: []}
    for g in grid:
        v1 = v2 = 0.0
        for tj, a, b in steps:
            if tj <= g:
                v1, v2 = a, b
        out[1].append(v1)
        out[2].append(v2)
    return out


def cumulative_incidence(units: Sequence[Mapping[str, Any]], grid: Sequence[float], *,
                         censoring_assumption: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Competing-risk cumulative incidence that states and enforces its assumptions.

    Each unit: ``{"time": float, "event": 'upper'|'lower'|'ambiguous'|None,
    "censoring": <class>}``. ``event=None`` means no event was observed by ``time``
    (censored at ``time`` when the class is not observed; end of follow-up otherwise).

    A point estimate is returned only when (a) the caller asserts
    ``censoring_assumption={"noninformative": True, "basis": <text>}``, (b) every
    censored unit is ``administrative_pending`` or ``assumed_noninformative``, and
    (c) no event is interval-ambiguous. Otherwise the result is Manski bounds, with
    ``status="bounds_only"`` and the failed condition named. With no units,
    ``status="unavailable"``.
    """
    if len(units) > MAX_UNITS:
        raise ValueError("too_many_units")
    grid = [float(g) for g in grid]
    assumption = dict(censoring_assumption or {})
    stated = {
        "noninformative_censoring_asserted": bool(assumption.get("noninformative") is True),
        "basis": assumption.get("basis"),
        "competing_events": ["upper", "lower"],
        "ambiguous_events": "interval-ambiguous; bounded by assignment to either cause",
        "informative_classes_never_benign": sorted([INFORMATIVE_UNKNOWN, INVALID]),
    }
    n = len(units)
    if n == 0:
        return {"status": "unavailable", "reason": "no_units", "assumptions": stated, "grid": grid}
    times = np.empty(n)
    raw_events: list[str | None] = []
    classes: list[str] = []
    for i, u in enumerate(units):
        tv = u.get("time")
        if not isinstance(tv, (int, float, np.integer, np.floating)) or isinstance(tv, bool) or not math.isfinite(float(tv)) or float(tv) < 0:
            raise ValueError("invalid_time")
        times[i] = float(tv)
        ev = u.get("event")
        if ev not in (None, "upper", "lower", "ambiguous"):
            raise ValueError("invalid_event")
        cl = u.get("censoring", OBSERVED)
        if cl not in CENSORING_CLASSES:
            raise ValueError("unknown_censoring_class")
        raw_events.append(ev)
        classes.append(cl)

    failures: list[str] = []
    if not stated["noninformative_censoring_asserted"]:
        failures.append("noninformative_censoring_not_asserted")
    if any(cl in (INFORMATIVE_UNKNOWN, INVALID) for cl in classes):
        failures.append("informative_or_invalid_censoring_present")
    if any(ev == "ambiguous" for ev in raw_events):
        failures.append("interval_ambiguous_events_present")

    # Manski bounds on the CIF: unknown/censored and ambiguous units may be either.
    lower_b = {"upper": [], "lower": []}
    upper_b = {"upper": [], "lower": []}
    for g in grid:
        for cause in ("upper", "lower"):
            hits = sum(1 for t, ev in zip(times, raw_events) if ev == cause and t <= g)
            amb = sum(1 for t, ev in zip(times, raw_events) if ev == "ambiguous" and t <= g)
            unk = sum(1 for t, ev, cl in zip(times, raw_events, classes)
                      if ev is None and cl != OBSERVED and t <= g)
            lower_b[cause].append(hits / n)
            upper_b[cause].append((hits + amb + unk) / n)
    bounds = {"lower": lower_b, "upper": upper_b}

    if failures:
        return {"status": "bounds_only", "failed_conditions": failures, "assumptions": stated,
                "grid": grid, "bounds": bounds, "n_units": n}

    code = np.array([0 if ev is None else (1 if ev == "upper" else 2) for ev in raw_events])
    aj = _aalen_johansen(times, code, grid)
    return {"status": "estimate", "failed_conditions": [], "assumptions": stated, "grid": grid,
            "cif": {"upper": aj[1], "lower": aj[2]}, "bounds": bounds, "n_units": n}


def attach_diagnostic(record: Mapping[str, Any], diagnostic: Mapping[str, Any]) -> dict[str, Any]:
    """Return a deep copy of ``record`` with ``diagnostic`` under its own namespace.

    The input is never mutated. Canonical IDs, grades and horizons are copied
    unchanged, and a diagnostic that tries to carry a canonical key is refused.
    """
    if not isinstance(record, Mapping) or not isinstance(diagnostic, Mapping):
        raise ValueError("mapping_required")
    clash = sorted(k for k in diagnostic if k in CANONICAL_KEYS)
    if clash:
        raise ValueError("diagnostic_overrides_canonical_key:" + ",".join(clash))
    if DIAGNOSTIC_NAMESPACE in record:
        raise ValueError("namespace_already_present")
    out = copy.deepcopy(dict(record))
    out[DIAGNOSTIC_NAMESPACE] = copy.deepcopy(dict(diagnostic))
    return out


def circular_block_bootstrap(block_values: Sequence[Any], stat: Callable[[list[Any]], float | None],
                             *, block_len: int, n_boot: int, seed: int,
                             alpha: float = 0.05) -> dict[str, Any]:
    """Percentile interval from a circular block bootstrap over ordered blocks.

    ``block_values`` is one item per ordered block (for example the list of units
    for one session date). Resamples keep runs of ``block_len`` consecutive blocks.
    """
    nb = len(block_values)
    if nb == 0:
        return {"status": "unavailable", "reason": "no_blocks"}
    if not (1 <= block_len <= nb) or not (1 <= n_boot <= 100_000) or not (0 < alpha < 1):
        raise ValueError("bad_bootstrap_params")
    rng = np.random.default_rng(int(seed))
    point = stat(list(block_values))
    draws: list[float] = []
    n_runs = int(math.ceil(nb / block_len))
    for _ in range(int(n_boot)):
        starts = rng.integers(0, nb, size=n_runs)
        idx = [(s + k) % nb for s in starts for k in range(block_len)][:nb]
        v = stat([block_values[i] for i in idx])
        if v is not None and math.isfinite(v):
            draws.append(float(v))
    if not draws:
        return {"status": "unavailable", "reason": "no_finite_draws", "point": point}
    arr = np.asarray(draws)
    return {"status": "ok", "point": point, "lo": float(np.quantile(arr, alpha / 2)),
            "hi": float(np.quantile(arr, 1 - alpha / 2)), "n_boot_finite": len(draws),
            "n_blocks": nb, "block_len": int(block_len)}
