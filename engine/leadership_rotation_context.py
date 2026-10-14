"""Stateless additive projection for the leadership-rotation measured-product contract.

LR-MEAS-SPEC-1 contract layer (tasks T03/T04/T05/T08). This module is a pure,
stateless, additive, DISPLAY-ONLY projection over the existing leadership and
rotation owners. It is NOT a source, evaluator, event owner, store, publisher
or schedule; it holds no state and it never mutates an input argument. There is
no file or network I/O, no LLM call, no randomness and no clock read anywhere
in this module (never ``datetime.now``). Owner modules are never imported at
top level; adapter slices import them lazily inside the adapter functions.

Units conventions:
- Simple returns are FRACTIONS unless a field or metric name ends ``_pct`` or
  ``_pp`` (``0.10`` means ``+10%``). ``relative_wealth`` is a wealth ratio minus
  one, ``(1+R_g)/(1+R_b)-1``; ``return_difference`` is a plain difference
  ``R_g-R_b`` -- the two are different quantities and are never substituted.
- ``Breadth.k_over_n`` and ``coverage`` are fractions in ``[0.0, 1.0]``.
- Weights are non-negative and are scale-normalised only when the weight map is
  COMPLETE (never a hidden renormalisation of a partial map).
- Z-scores bind their exact reference ``cohort_id``; a cross-cohort lookup
  raises ``CohortMismatch``. Datetimes, where accepted, are aware UTC.

Unmeasured semantics:
- Anything unknown is returned as an explicit ``Unmeasured(reason)`` marker (or
  a dict / named tuple carrying one) -- NEVER ``0`` / ``0.0`` / ``False`` as a
  stand-in for unknown.
- ``Unmeasured`` has no truth value (``bool(u)`` raises ``TypeError``), no
  arithmetic and no ordering. Test measurability with :func:`is_measured`.
- The only raising paths are explicit programmer errors: ``ValueError`` for a
  malformed cohort id / counts / clock argument, and ``CohortMismatch`` for a
  cross-cohort z lookup.
"""

from __future__ import annotations

import copy
import dataclasses
import math
import numbers
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import NamedTuple

__all__ = [
    "SCHEMA",
    "DEFINITION_ID",
    "UNMEASURED",
    "EPS",
    "EVIDENCE_MODES",
    "GROUP_KINDS",
    "METRICS",
    "UNITS",
    "REASONS",
    "US_SECTOR_COHORT_ID",
    "Unmeasured",
    "is_measured",
    "Breadth",
    "CohortMismatch",
    "relative_wealth",
    "return_difference",
    "breadth",
    "breadth_change",
    "cohort_zscores",
    "z_for",
    "classify_coordinate",
    "rank_measured",
    "normalize_weights",
    "overlap",
    "concentration",
    "shared_members",
    "weight_coverage",
    "cohort_at",
    "parse_time",
    "admissible_as_known",
    "admit_use",
    "observation_clock",
    "confirmation_maturity",
    "clock_identities",
    "GroupMeasurement",
    "TransitionObservation",
    "ResearchEstimate",
    "rolling_carry",
    "decompose_trailing_change",
    "beta_only_residual",
    "pair_interpretation",
    "decompose_z_change",
    "dedupe_source_roots",
]

# ---------------------------------------------------------------------------
# 1. Constants
# ---------------------------------------------------------------------------

SCHEMA = "leadership_rotation_context/v1"
DEFINITION_ID = "leadership_rotation_context/1"
UNMEASURED = "unmeasured"
EPS = 1e-12
EVIDENCE_MODES = ("original_retained", "reconstructed_price_history", "corrected",
                  "synthetic_fixture", "prospective_estimate")
GROUP_KINDS = ("sector", "industry", "curated_theme", "broad_provider_grouping")
METRICS = ("relative_wealth", "relative_wealth_pct", "return_difference", "return_difference_pp_vs_median")
UNITS = ("fraction", "pct", "pp")
REASONS = ("missing_input", "non_finite_input", "benchmark_wealth_nonpositive",
           "group_wealth_negative", "empty_population", "no_measured_members", "invalid_counts",
           "empty_weights", "invalid_weights", "insufficient_reference", "degenerate_dispersion",
           "not_in_reference", "availability_unknown", "unparseable_time", "thin_history",
           "no_admitted_model_support")
US_SECTOR_COHORT_ID = "us_sectors_11"


# ---------------------------------------------------------------------------
# 2. The unmeasured marker
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Unmeasured:
    """Explicit "not measured here" marker; never a stand-in for 0 / False."""

    reason: str
    status: str = "unmeasured"

    def __post_init__(self) -> None:
        if self.reason not in REASONS:
            raise ValueError(f"Unmeasured reason must be one of REASONS, got {self.reason!r}")

    def __bool__(self) -> bool:
        # Deliberate: `x or 0.0` and `if x:` on an unknown must crash, never coerce.
        raise TypeError("Unmeasured has no truth value; use is_measured()")

    def to_dict(self) -> dict:
        return {"status": "unmeasured", "reason": self.reason}


def is_measured(x) -> bool:
    """True iff *x* is a real, finite, non-bool number (a valid 0.0 IS measured)."""
    if x is None or isinstance(x, bool) or not isinstance(x, numbers.Real):
        return False
    try:
        return math.isfinite(float(x))
    except (OverflowError, ValueError):
        return False


def _num(x):
    """float(x) when measured, else None (private)."""
    return float(x) if is_measured(x) else None


def _json(x):
    """JSON-safe projection of module values (private)."""
    if isinstance(x, Unmeasured):
        return x.to_dict()
    if isinstance(x, Breadth):
        return x.to_dict()
    if isinstance(x, tuple):
        return [_json(v) for v in x]
    if isinstance(x, list):
        return [_json(v) for v in x]
    if isinstance(x, dict):
        return {k: _json(v) for k, v in x.items()}
    if isinstance(x, (datetime, date)):
        return x.isoformat()
    return x


def _value_or_reason(x):
    """(value, None) when *x* is a finite real, else (None, reason)."""
    if x is None or isinstance(x, bool) or not isinstance(x, numbers.Real):
        return None, "missing_input"
    v = float(x)
    if not math.isfinite(v):
        return None, "non_finite_input"
    return v, None


def _is_count(x) -> bool:
    return isinstance(x, int) and not isinstance(x, bool)


def _zdiff(a, b):
    """a - b, propagating an Unmeasured operand instead of arithmetic."""
    if isinstance(a, Unmeasured):
        return a
    if isinstance(b, Unmeasured):
        return b
    return a - b


# ---------------------------------------------------------------------------
# 3. T05 -- comparable measurements
# ---------------------------------------------------------------------------

def relative_wealth(r_g, r_b):
    """Wealth ratio minus one: (1+R_g)/(1+R_b)-1, as a fraction."""
    vg, rg = _value_or_reason(r_g)
    vb, rb = _value_or_reason(r_b)
    if vg is None:
        return Unmeasured(rg)
    if vb is None:
        return Unmeasured(rb)
    if 1.0 + vb <= 0.0:
        return Unmeasured("benchmark_wealth_nonpositive")
    if 1.0 + vg < 0.0:
        return Unmeasured("group_wealth_negative")
    return (1.0 + vg) / (1.0 + vb) - 1.0


def return_difference(r_g, r_b):
    """Plain difference r_g - r_b (a pp difference is NOT a wealth relative)."""
    vg, rg = _value_or_reason(r_g)
    vb, rb = _value_or_reason(r_b)
    if vg is None:
        return Unmeasured(rg)
    if vb is None:
        return Unmeasured(rb)
    return vg - vb


class Breadth(NamedTuple):
    """Breadth k/n with coverage n/N and logical identification bounds."""

    k_over_n: object
    coverage: object
    bounds: object

    def to_dict(self) -> dict:
        if isinstance(self.bounds, Unmeasured):
            bounds_field = self.bounds.to_dict()
        else:
            bounds_field = [self.bounds[0], self.bounds[1]]
        return {
            "k_over_n": _json(self.k_over_n),
            "coverage": _json(self.coverage),
            "bounds": bounds_field,
            "bounds_kind": "identification_bounds_not_confidence_interval",
        }


def breadth(k, n, N) -> Breadth:
    """Breadth k/n, coverage n/N, identification bounds [k/N, (k+N-n)/N]."""
    if k is None or n is None or N is None:
        u = Unmeasured("missing_input")
        return Breadth(u, u, u)
    if not (_is_count(k) and _is_count(n) and _is_count(N)) or not (0 <= k <= n <= N):
        u = Unmeasured("invalid_counts")
        return Breadth(u, u, u)
    if N == 0:
        u = Unmeasured("empty_population")
        return Breadth(u, u, u)
    if n == 0:
        return Breadth(Unmeasured("no_measured_members"), 0.0, (0.0, 1.0))
    return Breadth(k / n, n / N, (k / N, (k + N - n) / N))


def breadth_change(before, after) -> dict:
    """Breadth change under the same-cohort rule (counts only common_known)."""
    b = dict(before) if before is not None else {}
    a = dict(after) if after is not None else {}

    def known_bool(mapping, key):
        return key in mapping and isinstance(mapping[key], bool)

    common_known = sorted(
        key for key in b
        if key in a and isinstance(b[key], bool) and isinstance(a[key], bool)
    )
    newly_positive_common = sorted(k for k in common_known if b[k] is False and a[k] is True)
    newly_negative_common = sorted(k for k in common_known if b[k] is True and a[k] is False)
    new_coverage_positive = sorted(k for k, v in a.items() if v is True and not known_bool(b, k))
    new_coverage_negative = sorted(k for k, v in a.items() if v is False and not known_bool(b, k))
    lost_coverage = sorted(k for k, v in b.items() if isinstance(v, bool) and not known_bool(a, k))
    entrants = sorted(k for k in a if k not in b)
    exits = sorted(k for k in b if k not in a)

    def breadth_of(mapping):
        trues = sum(1 for v in mapping.values() if v is True)
        bools = sum(1 for v in mapping.values() if isinstance(v, bool))
        return breadth(trues, bools, len(mapping))

    whole_list_before = breadth_of(b)
    whole_list_after = breadth_of(a)
    cb_trues = sum(1 for k in common_known if b[k] is True)
    ca_trues = sum(1 for k in common_known if a[k] is True)
    common_cohort_before = breadth(cb_trues, len(common_known), len(common_known))
    common_cohort_after = breadth(ca_trues, len(common_known), len(common_known))

    ko_b = whole_list_before.k_over_n
    ko_a = whole_list_after.k_over_n
    composition_only = bool(
        is_measured(ko_b)
        and is_measured(ko_a)
        and float(ko_a) > float(ko_b) + EPS
        and newly_positive_common == []
    )
    return {
        "common_known": common_known,
        "newly_positive_common": newly_positive_common,
        "newly_negative_common": newly_negative_common,
        "new_coverage_positive": new_coverage_positive,
        "new_coverage_negative": new_coverage_negative,
        "lost_coverage": lost_coverage,
        "entrants": entrants,
        "exits": exits,
        "whole_list_before": whole_list_before,
        "whole_list_after": whole_list_after,
        "common_cohort_before": common_cohort_before,
        "common_cohort_after": common_cohort_after,
        "composition_only": composition_only,
        "same_cohort_rule": "broadening counts only common_known members at both endpoints",
    }


class CohortMismatch(ValueError):
    """Raised when a z-score lookup names a different cohort than its reference."""


def cohort_zscores(values, *, cohort_id: str) -> dict:
    """Cross-sectional z-scores bound to the exact reference ``cohort_id``."""
    if not isinstance(cohort_id, str) or not cohort_id:
        raise ValueError("cohort_id must be a non-empty string")
    items = tuple(dict(values).items()) if values is not None else ()
    measured = {}
    for key, raw in items:
        v, _ = _value_or_reason(raw)
        if v is not None:
            measured[key] = v
    ids = [key for key, _ in items]
    n_reference = len(measured)
    if n_reference < 2:
        mean = next(iter(measured.values())) if n_reference == 1 else Unmeasured("empty_population")
        return {
            "cohort_id": cohort_id,
            "reference_ids": sorted(measured),
            "n_reference": n_reference,
            "mean": mean,
            "sd": Unmeasured("insufficient_reference"),
            "z": {key: Unmeasured("insufficient_reference") for key in ids},
            "state": "insufficient_reference",
        }
    mean = sum(measured.values()) / n_reference
    sd = math.sqrt(sum((v - mean) ** 2 for v in measured.values()) / n_reference)
    if sd <= EPS:
        # All at origin is a tie, not Leading: every measured z is unmeasured.
        z = {
            key: (Unmeasured("degenerate_dispersion") if key in measured
                  else Unmeasured("missing_input"))
            for key in ids
        }
        return {
            "cohort_id": cohort_id,
            "reference_ids": sorted(measured),
            "n_reference": n_reference,
            "mean": mean,
            "sd": sd,
            "z": z,
            "state": "neutral_tie",
        }
    z = {
        key: ((measured[key] - mean) / sd if key in measured else Unmeasured("missing_input"))
        for key in ids
    }
    return {
        "cohort_id": cohort_id,
        "reference_ids": sorted(measured),
        "n_reference": n_reference,
        "mean": mean,
        "sd": sd,
        "z": z,
        "state": "ok",
    }


def z_for(zs: dict, member_id: str, *, cohort_id: str):
    """Member z from a cohort_zscores result; refuses a mismatched cohort."""
    if cohort_id != zs["cohort_id"]:
        raise CohortMismatch(
            f"z-scores bind cohort {zs['cohort_id']!r}, asked for {cohort_id!r}"
        )
    z = zs["z"]
    if member_id not in z:
        return Unmeasured("not_in_reference")
    return z[member_id]


def classify_coordinate(x, y) -> str:
    """Quadrant label for a (level, momentum) coordinate; unknown -> "unmeasured"."""
    if not is_measured(x) or not is_measured(y):
        return "unmeasured"
    xf, yf = float(x), float(y)
    if abs(xf) <= EPS and abs(yf) <= EPS:
        return "neutral"
    if xf >= 0 and yf >= 0:
        return "leading"
    if xf >= 0:
        return "weakening"
    if yf >= 0:
        return "improving"
    return "lagging"


def rank_measured(values) -> dict:
    """Measured ids sorted by (-value, id); unmeasured inputs never rank."""
    items = tuple(dict(values).items()) if values is not None else ()
    measured = [(key, float(v)) for key, v in items if is_measured(v)]
    ranked = [key for key, _ in sorted(measured, key=lambda kv: (-kv[1], kv[0]))]
    measured_keys = {key for key, _ in measured}
    unranked = sorted(key for key, _ in items if key not in measured_keys)
    return {"ranked": ranked, "unranked": unranked}


# ---------------------------------------------------------------------------
# 4. T04 -- cohort, weights, overlap
# ---------------------------------------------------------------------------

def normalize_weights(w):
    """Scale-normalise a COMPLETE weight map; never invent or renormalise partially.

    A weight map is complete iff it is a non-empty mapping whose every value is
    measured and >= 0 with sum > EPS.
    """
    if w is None:
        return Unmeasured("empty_weights")
    try:
        items = tuple(w.items())
    except AttributeError:
        return Unmeasured("empty_weights")
    if not items:
        return Unmeasured("empty_weights")
    total = 0.0
    values = {}
    for key, raw in items:
        v, _ = _value_or_reason(raw)
        if v is None:
            return Unmeasured("missing_input")
        if v < 0:
            return Unmeasured("invalid_weights")
        values[key] = v
        total += v
    if total <= EPS:
        return Unmeasured("invalid_weights")
    return {key: v / total for key, v in values.items()}


def overlap(w_g, w_h):
    """Overlap sum_i min(w_gi, w_hi) of the two normalised weight maps."""
    ng = normalize_weights(w_g)
    if isinstance(ng, Unmeasured):
        return ng
    nh = normalize_weights(w_h)
    if isinstance(nh, Unmeasured):
        return nh
    union = set(ng) | set(nh)
    return sum(min(ng.get(i, 0.0), nh.get(i, 0.0)) for i in union)


def concentration(w):
    """Effective number of constituents, 1/sum(w_i^2).

    This is a COMPOSITION statistic about the weight map only: it is never an
    independent-sample count and must never feed any N in a statistical test.
    """
    nw = normalize_weights(w)
    if isinstance(nw, Unmeasured):
        return nw
    return 1.0 / sum(v * v for v in nw.values())


def shared_members(w_g, w_h) -> list:
    """Sorted ids with a measured weight > 0 in BOTH maps; None -> []."""
    if w_g is None or w_h is None:
        return []
    g_positive = {key for key, v in dict(w_g).items() if is_measured(v) and float(v) > 0}
    return sorted(
        key for key, v in dict(w_h).items()
        if key in g_positive and is_measured(v) and float(v) > 0
    )


def weight_coverage(expected_weights, measured_ids) -> dict:
    """How much of an expected weight map is actually measured."""
    expected = dict(expected_weights) if expected_weights is not None else {}
    measured = set(measured_ids) if measured_ids is not None else set()
    expected_ids = set(expected)
    present = expected_ids & measured
    expected_n = len(expected_ids)
    if expected_n == 0:
        count_coverage = Unmeasured("empty_population")
    else:
        count_coverage = len(present) / expected_n
    nw = normalize_weights(expected)
    if isinstance(nw, Unmeasured):
        measured_weight_share = nw
    else:
        measured_weight_share = sum(v for key, v in nw.items() if key in measured)
    return {
        "expected_n": expected_n,
        "measured_n": len(present),
        "missing_ids": sorted(expected_ids - measured),
        "unexpected_ids": sorted(measured - expected_ids),
        "weight_known_n": sum(1 for v in expected.values() if is_measured(v)),
        "count_coverage": count_coverage,
        "measured_weight_share": measured_weight_share,
    }


def cohort_at(memberships, *, as_of, as_known=False):
    """Cohort population at ``as_of`` (A08); optionally as-known-at ``as_of`` (A06).

    A row is IN iff ``effective_from <= as_of`` and (``effective_to`` is None or
    ``as_of < effective_to``) and, when ``as_known=True``, ``known_at`` is not
    None and ``known_at <= as_of``. A late joiner is never in an older cohort.
    """
    when = parse_time(as_of)
    if isinstance(when, Unmeasured):
        return Unmeasured("missing_input" if as_of is None else "unparseable_time")
    members = []
    future_effective = []
    expired = []
    not_yet_known = []
    knowledge_unknown = []
    unparseable = []
    for row in (memberships if memberships is not None else ()):
        try:
            member_id = row.get("member_id")
            from_raw = row.get("effective_from")
            to_raw = row.get("effective_to")
            known_raw = row.get("known_at")
        except AttributeError:
            unparseable.append(str(row))
            continue
        eff_from = parse_time(from_raw)
        eff_to = None if to_raw is None else parse_time(to_raw)
        known_at = None if known_raw is None else parse_time(known_raw)
        row_unparseable = (
            member_id is None
            or isinstance(eff_from, Unmeasured)
            or (to_raw is not None and isinstance(eff_to, Unmeasured))
            or (known_raw is not None and isinstance(known_at, Unmeasured))
        )
        if row_unparseable:
            unparseable.append(member_id if isinstance(member_id, str) else str(row))
            continue
        if eff_from > when:
            future_effective.append(member_id)
        elif eff_to is not None and when >= eff_to:
            expired.append(member_id)
        elif as_known and known_at is None:
            knowledge_unknown.append(member_id)
        elif as_known and known_at > when:
            not_yet_known.append(member_id)
        else:
            members.append(member_id)
    return {
        "as_of": as_of,
        "population": "as_known" if as_known else "reconstructed",
        "members": sorted(members),
        "excluded_future_effective": sorted(future_effective),
        "excluded_expired": sorted(expired),
        "excluded_not_yet_known": sorted(not_yet_known),
        "excluded_knowledge_unknown": sorted(knowledge_unknown) if as_known else [],
        "excluded_unparseable": sorted(unparseable),
    }


# ---------------------------------------------------------------------------
# 5. T03 -- group input and clock contracts
# ---------------------------------------------------------------------------

def parse_time(x):
    """Aware-UTC datetime from a date/datetime/ISO string; Unmeasured otherwise.

    A naive datetime (or naive ISO string, incl. plain ``YYYY-MM-DD``) is read
    as UTC; a ``date`` becomes 00:00 UTC. No clock is ever read here.
    """
    if x is None:
        return Unmeasured("missing_input")
    if isinstance(x, datetime):
        dt = x
    elif isinstance(x, date):
        dt = datetime(x.year, x.month, x.day)
    elif isinstance(x, str):
        text = x.strip()
        if not text:
            return Unmeasured("unparseable_time")
        if text[-1] in ("Z", "z"):
            text = text[:-1] + "+00:00"
        try:
            dt = datetime.fromisoformat(text)
        except ValueError:
            return Unmeasured("unparseable_time")
    else:
        return Unmeasured("unparseable_time")
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def admissible_as_known(available_at, decision_cutoff) -> str:
    """Is the input's ``available_at`` knowledge admissible at ``decision_cutoff`` (A06)?

    String states on purpose: a truthy marker must never admit an input. A
    revision available only AFTER the decision cutoff is not admissible.
    """
    if available_at is None:
        return "unknown"
    available = parse_time(available_at)
    cutoff = parse_time(decision_cutoff)
    if isinstance(available, Unmeasured) or isinstance(cutoff, Unmeasured):
        return "unknown"
    if available <= cutoff:
        return "admissible"
    return "not_admissible"


def admit_use(rights, use) -> str:
    """Use permission from a rights map (A05): acquisition is not permission.

    "permitted" iff ``rights[use] == "permitted"``; "refused" iff it equals
    "refused"; anything else -- None rights, absent use, a truthy non-string --
    is "withheld".
    """
    if rights is None:
        return "withheld"
    try:
        value = rights.get(use)
    except AttributeError:
        return "withheld"
    if value == "permitted":
        return "permitted"
    if value == "refused":
        return "refused"
    return "withheld"


def _checked_count(name, x) -> int:
    """Validate a session count: a real int >= 0; bools are programmer errors."""
    if isinstance(x, bool) or not isinstance(x, int) or x < 0:
        raise ValueError(f"{name} must be an int >= 0 (bool rejected), got {x!r}")
    return x


def observation_clock(session_end, *, vintage=None, confirmation_sessions=0,
                      horizon_sessions=0) -> dict:
    """Confirmation clock of an observation: maturity offset is c + H sessions."""
    c = _checked_count("confirmation_sessions", confirmation_sessions)
    h = _checked_count("horizon_sessions", horizon_sessions)
    return {
        "session_end": session_end,
        "vintage": vintage,
        "confirmation_sessions": c,
        "horizon_sessions": h,
        "maturity_offset_sessions": c + h,
        "maturity_rule": "t+c+H from the original origin",
    }


def confirmation_maturity(origin_index, c, h) -> int:
    """A transition matures at the origin t plus c confirmation plus H horizon."""
    t = _checked_count("origin_index", origin_index)
    cs = _checked_count("confirmation_sessions", c)
    hs = _checked_count("horizon_sessions", h)
    return t + cs + hs


def clock_identities(evidence_as_of, live_price_at) -> dict:
    """Keep the evidence clock and the live price clock distinct (A07).

    The two clocks are NEVER merged: the dict carries both labels and
    ``merged: False`` always. ``evidence_older_than_live`` is None when either
    side is missing or unparseable -- never a silent False.
    """
    evidence = parse_time(evidence_as_of)
    live = parse_time(live_price_at)
    evidence_known = not isinstance(evidence, Unmeasured)
    live_known = not isinstance(live, Unmeasured)
    if evidence_known and live_known:
        older = evidence < live
    else:
        older = None
    return {
        "evidence_as_of": evidence_as_of,
        "live_price_at": live_price_at,
        "evidence_older_than_live": older,
        "evidence_label": (f"group evidence as of {evidence_as_of}" if evidence_known
                           else "group evidence date unknown"),
        "live_label": (f"live price {live_price_at}" if live_known
                       else "live price unavailable"),
        "merged": False,
    }


def rolling_carry(L, h) -> dict:
    """Shared terms of a rolling L-window stepped by h: L-h (>0 => carry_flag)."""
    for name, x in (("L", L), ("h", h)):
        if isinstance(x, bool) or not isinstance(x, int) or x < 1:
            raise ValueError(f"{name} must be an int >= 1 (bool rejected), got {x!r}")
    return {
        "window_sessions": L,
        "step_sessions": h,
        "shared_terms": max(L - h, 0),
        "carry_flag": L - h > 0,
    }


def decompose_trailing_change(window_before, new_returns):
    """Split a trailing-window change into expiry vs new-return parts (A31).

    Identity: trailing_change == expiry_component + new_return_component.
    """
    if window_before is None or new_returns is None:
        return Unmeasured("missing_input")
    before_values = list(window_before)
    if not before_values:
        return Unmeasured("empty_population")
    before = []
    for raw in before_values:
        v, reason = _value_or_reason(raw)
        if v is None:
            return Unmeasured(reason)
        before.append(v)
    new = []
    for raw in new_returns:
        v, reason = _value_or_reason(raw)
        if v is None:
            return Unmeasured(reason)
        new.append(v)
    L = len(before)
    h = len(new)
    if h < L:
        expired = before[:h]
        after = before[h:] + new
    else:
        expired = before
        after = new[-L:]
    sum_before = sum(before)
    sum_after = sum(after)
    sum_expired = sum(expired)
    expiry_component = -sum_expired
    new_return_component = sum_after - sum_before + sum_expired
    trailing_change = sum_after - sum_before
    return {
        "window_sessions": L,
        "step_sessions": h,
        "shared_terms": max(L - h, 0),
        "carry_flag": L - h > 0,
        "expiry_component": expiry_component,
        "new_return_component": new_return_component,
        "trailing_change": trailing_change,
        "carry_only": abs(new_return_component) <= EPS and abs(trailing_change) > EPS,
    }


# ---------------------------------------------------------------------------
# 6. Objects -- group_measurement (T03), transition_observation (T08),
#    research_estimate. Three distinct objects, never substitutable.
# ---------------------------------------------------------------------------

_GROUP_MEASUREMENT_SCHEMA = "leadership_rotation_context.group_measurement/v1"
_TRANSITION_OBSERVATION_SCHEMA = "leadership_rotation_context.transition_observation/v1"
_RESEARCH_ESTIMATE_SCHEMA = "leadership_rotation_context.research_estimate/v1"
_RESEARCH_ESTIMATE_IDENTITY_FIELDS = (
    "target",
    "horizon_sessions",
    "origin",
    "exit_rule",
    "model",
    "protocol",
    "cohort_id",
    "training_cutoff",
    "supported_population",
    "uncertainty_definition",
    "evidence_tier",
)


def _object_to_dict(obj, schema: str, extra: dict) -> dict:
    """JSON-safe projection of a frozen contract object (private)."""
    payload = {"schema": schema, "display_only": True}
    for f in dataclasses.fields(obj):
        payload[f.name] = _json(getattr(obj, f.name))
    payload.update(extra)
    return payload


@dataclass(frozen=True)
class GroupMeasurement:
    """One measured group reading; display-only, never a ranking authority.

    Keyword construction is the contract. ``value`` is either a measured real
    (a valid 0.0 IS measured) or an explicit ``Unmeasured`` marker; it is never
    coerced. The object may never rank anything: ``may_rank`` is False in
    ``to_dict()`` by construction.
    """

    group_id: str
    group_kind: str
    cohort_id: str
    metric: str
    units: str
    membership_source: object = None
    membership_revision: object = None
    market: object = None
    session_end: object = None
    benchmark: object = None
    price_basis: object = None
    currency: object = None
    window_sessions: object = None
    rolling_window: bool = False
    observed_at: object = None
    source_available_at: object = None
    issued_at: object = None
    freshness: object = None
    correction_generation: int = 0
    expected_members: tuple = ()
    admitted_members: tuple = ()
    measured_members: tuple = ()
    missing_members: tuple = ()
    expected_n: object = None
    measured_n: object = None
    weight_source: object = None
    weight_effective_at: object = None
    weight_convention: object = None
    value: object = field(default_factory=lambda: Unmeasured("missing_input"))
    breadth: object = None
    concentration: object = None
    overlap_with: tuple = ()
    source_roots: tuple = ()
    withheld_inputs: tuple = ()
    evidence_mode: str = "reconstructed_price_history"
    use_rights: str = "withheld"
    notes: tuple = ()

    def __post_init__(self) -> None:
        if self.group_kind not in GROUP_KINDS:
            raise ValueError(f"group_kind must be one of GROUP_KINDS, got {self.group_kind!r}")
        if self.metric not in METRICS:
            raise ValueError(f"metric must be one of METRICS, got {self.metric!r}")
        if self.units not in UNITS:
            raise ValueError(f"units must be one of UNITS, got {self.units!r}")
        if self.evidence_mode not in EVIDENCE_MODES:
            raise ValueError(
                f"evidence_mode must be one of EVIDENCE_MODES, got {self.evidence_mode!r}"
            )
        if not isinstance(self.value, Unmeasured) and not is_measured(self.value):
            raise ValueError(
                "value must be an Unmeasured marker or a measured real (bool rejected), "
                f"got {self.value!r}"
            )

    @property
    def coverage(self):
        """Measured share of the expected population, or Unmeasured when unknown."""
        if self.expected_members:
            return len(self.measured_members) / len(self.expected_members)
        if _is_count(self.expected_n) and self.expected_n > 0 and _is_count(self.measured_n):
            return self.measured_n / self.expected_n
        return Unmeasured("empty_population")

    def to_dict(self) -> dict:
        return _object_to_dict(
            self,
            _GROUP_MEASUREMENT_SCHEMA,
            {"coverage": _json(self.coverage), "may_rank": False},
        )


@dataclass(frozen=True)
class TransitionObservation:
    """One early-transition coordinate observation; CONTEXT-ONLY, never an event.

    A reconstructed coordinate is ``naturally_observed=False`` by law: it was
    rebuilt from price history, not witnessed at the time. The observation is
    never attached to a legacy event (``relationship`` is pinned to
    "context_only"); confirmed status lives in the legacy event owner, not here.
    """

    definition_id: str
    definition_version: str
    roles: dict
    coordinate: dict
    evidence_mode: str
    naturally_observed: bool
    first_known_observation_id: object = None
    first_known_at: object = None
    current_observation_at: object = None
    episode_id: object = None
    status: str = "context_only"
    contrary_evidence: tuple = ()
    interpretation: object = None
    source_context: object = None
    relationship: str = "context_only"

    def __post_init__(self) -> None:
        if self.evidence_mode not in EVIDENCE_MODES:
            raise ValueError(
                f"evidence_mode must be one of EVIDENCE_MODES, got {self.evidence_mode!r}"
            )
        if not isinstance(self.naturally_observed, bool):
            raise ValueError(
                f"naturally_observed must be a bool, got {self.naturally_observed!r}"
            )
        if self.naturally_observed and self.evidence_mode != "original_retained":
            raise ValueError(
                "a reconstructed coordinate cannot claim natural observation: only "
                f"evidence_mode='original_retained' may be naturally_observed, got "
                f"{self.evidence_mode!r}"
            )
        if not isinstance(self.coordinate, dict):
            raise ValueError(f"coordinate must be a dict, got {self.coordinate!r}")
        for key in ("date", "vintage", "as_of"):
            if key not in self.coordinate:
                raise ValueError(f"coordinate lacks required key {key!r}")
        if self.relationship != "context_only":
            raise ValueError(
                "a transition observation is context-only and is never attached to a "
                f"legacy event, got relationship={self.relationship!r}"
            )

    def to_dict(self) -> dict:
        return _object_to_dict(self, _TRANSITION_OBSERVATION_SCHEMA, {})


@dataclass(frozen=True)
class ResearchEstimate:
    """A predictive research claim; unavailable unless BOTH probability and a
    complete identity are present.

    An estimate with an incomplete identity is unavailable -- never a placeholder
    probability, and a coverage percentage never enters the probability slot.
    """

    target: object = None
    horizon_sessions: object = None
    origin: object = None
    exit_rule: object = None
    model: object = None
    protocol: object = None
    cohort_id: object = None
    training_cutoff: object = None
    supported_population: object = None
    uncertainty_definition: object = None
    evidence_tier: object = None
    probability: object = field(
        default_factory=lambda: Unmeasured("no_admitted_model_support")
    )

    def __post_init__(self) -> None:
        if isinstance(self.probability, Unmeasured):
            return
        if not is_measured(self.probability) or not 0.0 <= float(self.probability) <= 1.0:
            raise ValueError(
                "probability must be an Unmeasured marker or a measured real in [0, 1] "
                f"(bool rejected), got {self.probability!r}"
            )
        missing = [
            name for name in _RESEARCH_ESTIMATE_IDENTITY_FIELDS
            if getattr(self, name) is None
        ]
        if missing:
            raise ValueError(
                "an estimate with an incomplete identity is unavailable; missing "
                f"identity fields: {missing}"
            )

    @property
    def status(self) -> str:
        return "unavailable" if isinstance(self.probability, Unmeasured) else "estimate"

    def to_dict(self) -> dict:
        return _object_to_dict(self, _RESEARCH_ESTIMATE_SCHEMA, {"status": self.status})


# ---------------------------------------------------------------------------
# 8. T08 -- coordinate-change attribution and repeated evidence
# ---------------------------------------------------------------------------

def beta_only_residual(r_g, r_m, beta):
    """Residual of r_g against a STATED hypothetical beta; no causal claim."""
    vg, rg = _value_or_reason(r_g)
    vm, rm = _value_or_reason(r_m)
    vb, rb = _value_or_reason(beta)
    if vg is None:
        return Unmeasured(rg)
    if vm is None:
        return Unmeasured(rm)
    if vb is None:
        return Unmeasured(rb)
    residual = vg - vb * vm
    explained = abs(residual) <= EPS
    return {
        "arithmetic_excess": vg - vm,
        "stated_beta": vb,
        "beta_residual": residual,
        "explained_by_stated_beta": explained,
        "beta_basis": "stated_hypothetical_past_known",
        "interpretation": ("fully explained by stated beta" if explained
                           else "residual association under stated beta (not causal, not flow)"),
    }


def pair_interpretation(r_receiver, r_donor):
    """Label a receiver/donor pair WITHOUT claiming flows, recovery or causality."""
    vr, rr = _value_or_reason(r_receiver)
    vd, rd = _value_or_reason(r_donor)
    if vr is None:
        return Unmeasured(rr)
    if vd is None:
        return Unmeasured(rd)
    rw = relative_wealth(vr, vd)
    if isinstance(rw, Unmeasured):
        return rw
    if vr < 0 and vd < 0:
        direction = "both_down"
    elif vr > 0 and vd > 0:
        direction = "both_up"
    else:
        direction = "mixed"
    if abs(rw) <= EPS:
        interpretation = "no_relative_change"
    elif rw < 0:
        interpretation = "relative_weakness"
    elif direction == "mixed":
        interpretation = "divergent_price_action"
    elif direction == "both_down":
        interpretation = "relative_resilience"
    else:
        interpretation = "relative_strength"
    return {
        "receiver_return": vr,
        "donor_return": vd,
        "relative_wealth": rw,
        "return_difference": vr - vd,
        "absolute_direction": direction,
        "interpretation": interpretation,
        "not_claimed": ["absolute_recovery", "measured_inflow", "causal_handoff"],
    }


def decompose_z_change(member_id, ref_before, ref_after, *, cohort_id_before, cohort_id_after) -> dict:
    """Split a member's z move into raw-move vs reference-change parts (A15)."""
    zb = cohort_zscores(ref_before, cohort_id=cohort_id_before)
    za = cohort_zscores(ref_after, cohort_id=cohort_id_after)
    z_before = zb["z"].get(member_id, Unmeasured("not_in_reference"))
    z_after = za["z"].get(member_id, Unmeasured("not_in_reference"))
    raw_before = _num(ref_before.get(member_id)) if ref_before is not None else None
    raw_after = _num(ref_after.get(member_id)) if ref_after is not None else None

    if raw_after is not None and zb["state"] == "ok":
        z_holding_reference = (raw_after - zb["mean"]) / zb["sd"]
    elif raw_after is not None and zb["state"] == "neutral_tie":
        z_holding_reference = Unmeasured("degenerate_dispersion")
    elif raw_after is not None and zb["state"] == "insufficient_reference":
        z_holding_reference = Unmeasured("insufficient_reference")
    else:
        z_holding_reference = Unmeasured("missing_input")

    raw_move_component = _zdiff(z_holding_reference, z_before)
    reference_change_component = _zdiff(z_after, z_holding_reference)
    total_change = _zdiff(z_after, z_before)

    measured_before = set(zb["reference_ids"])
    measured_after = set(za["reference_ids"])
    added_ids = sorted(measured_after - measured_before)
    removed_ids = sorted(measured_before - measured_after)

    def changed(field_b, field_a):
        if is_measured(field_b) and is_measured(field_a):
            return abs(float(field_a) - float(field_b)) > EPS
        return None

    mean_changed = changed(zb["mean"], za["mean"])
    sd_changed = changed(zb["sd"], za["sd"])
    cohort_id_changed = cohort_id_before != cohort_id_after
    if raw_before is not None and raw_after is not None:
        raw_unchanged = abs(raw_after - raw_before) <= EPS
    else:
        raw_unchanged = None
    reference_population_changed = bool(added_ids or removed_ids or mean_changed or sd_changed)
    promotion_from_normalization_only = bool(
        raw_unchanged is True and is_measured(total_change) and float(total_change) > EPS
    )
    return {
        "raw_move_component": raw_move_component,
        "reference_change_component": reference_change_component,
        "total_change": total_change,
        "added_ids": added_ids,
        "removed_ids": removed_ids,
        "mean_changed": mean_changed,
        "sd_changed": sd_changed,
        "cohort_id_changed": cohort_id_changed,
        "raw_unchanged": raw_unchanged,
        "reference_population_changed": reference_population_changed,
        "promotion_from_normalization_only": promotion_from_normalization_only,
    }


def dedupe_source_roots(evidence) -> dict:
    """Union-find families over shared source roots (A14 alias rule)."""
    items = []
    for ev in (evidence if evidence is not None else ()):
        items.append((ev.get("id"), tuple(ev.get("source_roots") or ())))
    parent = {}

    def find(x):
        root = x
        while parent[root] != root:
            root = parent[root]
        while parent[x] != root:
            parent[x], x = parent[parent[x]], parent[x]
        return root

    root_owner = {}
    for item_id, roots in items:
        parent.setdefault(item_id, item_id)
        for root in roots:
            owner = root_owner.setdefault(root, item_id)
            parent.setdefault(owner, owner)
            a, b = find(item_id), find(owner)
            if a != b:
                parent[b] = a

    families_map = {}
    for item_id, _ in items:
        families_map.setdefault(find(item_id), set()).add(item_id)
    families = sorted(sorted(members) for members in families_map.values())
    alias_ids = sorted(
        item_id for members in families_map.values() if len(members) > 1 for item_id in members
    )
    return {
        "families": families,
        "family_count": len(families),
        "item_count": len(items),
        "alias_ids": alias_ids,
        "unrooted_ids": sorted(item_id for item_id, roots in items if not roots),
        "independent_count_rule": "one family = one vote; aliases add no evidence",
    }
