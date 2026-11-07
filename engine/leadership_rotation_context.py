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
import json
import math
import numbers
import re
from collections.abc import Mapping
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
    "us_sector_cohort",
    "from_sector_record",
    "sector_cohort_snapshot",
    "from_leadership_receipt",
    "diagnose_rotation_payload",
    "attribute_coordinate",
    "earliest_observable_coordinate",
    "separate_from_legacy",
    "rolling_carry",
    "decompose_trailing_change",
    "beta_only_residual",
    "pair_interpretation",
    "decompose_z_change",
    "dedupe_source_roots",
    "SECTOR_WINDOW_MEASUREMENTS_SCHEMA",
    "SECTOR_WINDOW_SESSIONS",
    "measure_sector_windows",
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
    try:
        v = float(x)
    except (OverflowError, ValueError):
        # e.g. the legal int 10**400 cannot become a float: unmeasurable, not a crash.
        return None, "non_finite_input"
    if not math.isfinite(v):
        return None, "non_finite_input"
    return v, None


def _finite(v) -> bool:
    """True iff *v* is a finite float (private): an overflowed arithmetic result
    is an unmeasurable outcome, never a value."""
    return isinstance(v, float) and math.isfinite(v)


def _is_count(x) -> bool:
    return isinstance(x, int) and not isinstance(x, bool)


def _as_mapping(x):
    """None / non-mapping payloads read as {} (adapters stay total, never raise)."""
    return x if isinstance(x, Mapping) else {}


def _container_rows(x):
    """(rows, malformed_container) for an iterated payload container (private).

    Only a ``list`` / ``tuple`` is a container: anything else (dict, str, int)
    reads as EMPTY and is flagged, because iterating it would invent rows the
    owner never emitted (a dict yields its keys, a str its characters). An
    absent / ``None`` container is a missing input, not a malformed one.
    """
    if isinstance(x, (list, tuple)):
        return list(x), False
    return [], x is not None


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
    value = (1.0 + vg) / (1.0 + vb) - 1.0
    if not _finite(value):
        return Unmeasured("non_finite_input")
    return value


def return_difference(r_g, r_b):
    """Plain difference r_g - r_b (a pp difference is NOT a wealth relative)."""
    vg, rg = _value_or_reason(r_g)
    vb, rb = _value_or_reason(r_b)
    if vg is None:
        return Unmeasured(rg)
    if vb is None:
        return Unmeasured(rb)
    value = vg - vb
    if not _finite(value):
        return Unmeasured("non_finite_input")
    return value


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
    mean = None
    overflow = False
    try:
        mean = sum(measured.values()) / n_reference
        sd = math.sqrt(sum((v - mean) ** 2 for v in measured.values()) / n_reference)
    except OverflowError:
        # e.g. (1e308 - 0.0)**2 overflows: the dispersion is unmeasurable.
        overflow = True
    if overflow or not (math.isfinite(mean) and math.isfinite(sd)):
        mean_out = (mean if (mean is not None and math.isfinite(mean))
                    else Unmeasured("non_finite_input"))
        return {
            "cohort_id": cohort_id,
            "reference_ids": sorted(measured),
            "n_reference": n_reference,
            "mean": mean_out,
            "sd": Unmeasured("non_finite_input"),
            "z": {key: (Unmeasured("non_finite_input") if key in measured
                        else Unmeasured("missing_input"))
                  for key in ids},
            "state": "non_finite",
        }
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
    z = {}
    for key in ids:
        if key not in measured:
            z[key] = Unmeasured("missing_input")
            continue
        value = (measured[key] - mean) / sd
        z[key] = value if _finite(value) else Unmeasured("non_finite_input")
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
    if not math.isfinite(total):
        return Unmeasured("non_finite_input")
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
        v, _reason = _value_or_reason(raw)
        if v is None:
            return Unmeasured("missing_input")
        before.append(v)
    new = []
    for raw in new_returns:
        v, _reason = _value_or_reason(raw)
        if v is None:
            return Unmeasured("missing_input")
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
    if not (_finite(expiry_component) and _finite(new_return_component)
            and _finite(trailing_change)):
        return Unmeasured("non_finite_input")
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
        """Measured share of the expected population, or Unmeasured when unknown.

        SET-BASED over the expected ids: a member counts once however often it is
        listed, and an id measured but NOT expected never raises coverage above
        1.0 -- it is reported by :attr:`unexpected_members` instead. On the count
        path ``measured_n > expected_n`` is inconsistent counting, not a coverage
        above 1, so it stays ``Unmeasured("invalid_counts")``.
        """
        if self.expected_members:
            expected = set(self.expected_members)
            present = expected & set(self.measured_members)
            return len(present) / len(expected)
        if _is_count(self.expected_n) and self.expected_n > 0 and _is_count(self.measured_n):
            if self.measured_n > self.expected_n:
                return Unmeasured("invalid_counts")
            return self.measured_n / self.expected_n
        return Unmeasured("empty_population")

    @property
    def unexpected_members(self) -> tuple:
        """Measured ids OUTSIDE the expected set (read-only); they never count
        toward :attr:`coverage` and are never treated as expected members."""
        if not self.expected_members:
            return ()
        return tuple(sorted(set(self.measured_members) - set(self.expected_members), key=str))

    def to_dict(self) -> dict:
        return _object_to_dict(
            self,
            _GROUP_MEASUREMENT_SCHEMA,
            {"coverage": _json(self.coverage),
             "unexpected_members": list(self.unexpected_members),
             "may_rank": False},
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
# 7. Adapters over the existing owners (lazy imports; read-only)
# ---------------------------------------------------------------------------

_SECTOR_HORIZON_SESSIONS = {"rs_21d": 21, "rs_63d": 63, "rs_126d": 126}
_RECEIPT_HORIZON_SESSIONS = {"rel_5d": 5, "rel_20d": 20, "rel_60d": 60}


def us_sector_cohort() -> tuple:
    """The existing 11 US sector ETF tickers from the frozen owner -- no new ids."""
    from engine import sector_cycles

    return tuple(sorted(sector_cycles.SECTORS))


def _sector_record_value(rec, horizon: str):
    """(value) float or Unmeasured for one sector_cycles record (private)."""
    now = _as_mapping(rec.get("now"))
    if now.get("thin_history") is True:
        return Unmeasured("thin_history")
    raw = now.get(horizon)
    if is_measured(raw):
        return float(raw)
    return Unmeasured("missing_input")


def from_sector_record(rec, *, benchmark=None, session_end=None,
                       horizon: str = "rs_63d") -> GroupMeasurement | Unmeasured:
    """One sector_cycles sector record -> a display-only GroupMeasurement.

    A record with no identity (None / non-mapping / no string ``ticker``) has
    nothing to measure and returns ``Unmeasured("missing_input")`` instead.
    """
    if horizon not in _SECTOR_HORIZON_SESSIONS:
        raise ValueError(
            f"horizon must be one of {sorted(_SECTOR_HORIZON_SESSIONS)}, got {horizon!r}"
        )
    if not isinstance(rec, Mapping) or not isinstance(rec.get("ticker"), str):
        return Unmeasured("missing_input")
    value = _sector_record_value(rec, horizon)
    return GroupMeasurement(
        group_id=rec["ticker"],
        group_kind="sector",
        cohort_id=US_SECTOR_COHORT_ID,
        metric="relative_wealth_pct",
        units="pct",
        benchmark=benchmark,
        session_end=session_end,
        window_sessions=_SECTOR_HORIZON_SESSIONS[horizon],
        rolling_window=True,
        price_basis="total_return",
        membership_source="etf_proxy:engine.sector_cycles.SECTORS",
        source_roots=("engine.sector_cycles",),
        value=value,
        notes=("trailing rolling window: consecutive readings share L-h sessions",),
    )


def sector_cohort_snapshot(payload, *, horizon: str = "rs_63d") -> dict:
    """Whole-cohort read over a sector_cycles.compute() payload (never re-sources).

    Total over NESTED malformed payloads: every nested mapping read goes through
    ``_as_mapping``, a non-list/tuple ``sectors`` container reads as empty and is
    flagged (``malformed_container``), and a row that is not a mapping is skipped
    and counted (``malformed_rows``) -- an absent member stays a missing input.
    """
    payload = _as_mapping(payload)
    meta = _as_mapping(payload.get("meta"))
    container, malformed_container = _container_rows(payload.get("sectors"))
    records = {}
    malformed_rows = 0
    for rec in container:
        if not isinstance(rec, Mapping):
            malformed_rows += 1
            continue
        ticker = rec.get("ticker")
        if isinstance(ticker, str):
            records[ticker] = rec
    expected = us_sector_cohort()
    outside_cohort = sorted(set(records) - set(expected))
    values = {}
    measured_values = {}
    measured = []
    missing = []
    measurements = []
    for ticker in expected:
        rec = records.get(ticker)
        if rec is None:
            missing.append([ticker, "missing_input"])
            values[ticker] = Unmeasured("missing_input")
            continue
        value = _sector_record_value(rec, horizon)
        if is_measured(value):
            values[ticker] = float(value)
            measured_values[ticker] = float(value)
            measured.append(ticker)
        else:
            values[ticker] = value
            missing.append([ticker, value.reason])
        measurements.append(
            from_sector_record(rec, benchmark=meta.get("benchmark"),
                               session_end=meta.get("asOf"), horizon=horizon).to_dict()
        )
    positives = sum(1 for v in measured_values.values() if v > 0)
    return {
        "schema": "leadership_rotation_context.sector_cohort/v1",
        "cohort_id": US_SECTOR_COHORT_ID,
        "session_end": meta.get("asOf"),
        "benchmark": meta.get("benchmark"),
        "expected": list(expected),
        "measured": sorted(measured),
        "missing": sorted(missing),
        "positive_breadth": breadth(positives, len(measured), len(expected)).to_dict(),
        "ranking": rank_measured(values),
        "zscores": _json(cohort_zscores(values, cohort_id=US_SECTOR_COHORT_ID)),
        "measurements": measurements,
        "outside_cohort": outside_cohort,
        "malformed_rows": malformed_rows,
        "malformed_container": malformed_container,
    }


def from_leadership_receipt(receipt, *, group_id: str, cohort_id: str,
                            group_kind: str = "curated_theme",
                            horizon: str = "rel_20d") -> GroupMeasurement:
    """One leadership_receipt reading -> a FRACTION return_difference measurement."""
    if horizon not in _RECEIPT_HORIZON_SESSIONS:
        raise ValueError(
            f"horizon must be one of {sorted(_RECEIPT_HORIZON_SESSIONS)}, got {horizon!r}"
        )
    receipt = _as_mapping(receipt)
    benchmark = _as_mapping(receipt.get("benchmark"))
    sample = _as_mapping(receipt.get("sample"))
    observed_n = sample.get("observed_n")
    configured_n = sample.get("configured_n")
    raw = receipt.get(horizon)
    value = float(raw) if is_measured(raw) else Unmeasured("missing_input")
    return GroupMeasurement(
        group_id=group_id,
        group_kind=group_kind,
        cohort_id=cohort_id,
        metric="return_difference",
        units="fraction",
        benchmark=benchmark.get("label"),
        session_end=receipt.get("as_of"),
        window_sessions=_RECEIPT_HORIZON_SESSIONS[horizon],
        rolling_window=True,
        expected_n=configured_n if _is_count(configured_n) else None,
        measured_n=observed_n if _is_count(observed_n) else None,
        source_roots=("engine.leadership_receipt",),
        value=value,
    )


def diagnose_rotation_payload(payload, *, cohort_id: str) -> dict:
    """Name the two owner coercions in a subsector_rotation payload; never re-rank.

    The frozen owner maps a missing z to 0.0 (``_nanmean(...) or 0.0``) and can
    label the exact origin "leading". Both are flagged here; the owner payload
    is never modified.
    """
    payload = _as_mapping(payload)
    container, malformed_container = _container_rows(payload.get("subsectors"))
    rows = []
    flag_counts = {}
    malformed_rows = 0
    for row in container:
        if not isinstance(row, Mapping):
            malformed_rows += 1
            continue
        perf = _as_mapping(row.get("perf"))
        missing_coerced_to_zero = perf.get("1M") is None or perf.get("3M") is None
        rs_ratio = row.get("rs_ratio")
        rs_mom = row.get("rs_mom")
        neutral_origin_labelled_leading = bool(
            is_measured(rs_ratio) and is_measured(rs_mom)
            and abs(float(rs_ratio)) <= 1e-9 and abs(float(rs_mom)) <= 1e-9
            and row.get("quadrant") == "leading"
        )
        if missing_coerced_to_zero:
            projection_quadrant = "unmeasured"
        else:
            projection_quadrant = classify_coordinate(rs_ratio, rs_mom)
        flags = sorted(
            flag for flag, present in (
                ("missing_coerced_to_zero", missing_coerced_to_zero),
                ("neutral_origin_labelled_leading", neutral_origin_labelled_leading),
            ) if present
        )
        for flag in flags:
            flag_counts[flag] = flag_counts.get(flag, 0) + 1
        rows.append({
            "key": row.get("key"),
            "owner_quadrant": row.get("quadrant"),
            "projection_quadrant": projection_quadrant,
            "flags": flags,
        })
    return {
        "schema": "leadership_rotation_context.rotation_diagnostic/v1",
        "cohort_id": cohort_id,
        "asof": payload.get("asof"),
        "rs_units": "return_difference_pp_vs_median",
        "rows": rows,
        "flag_counts": flag_counts,
        "owner_fields_modified": False,
        "malformed_rows": malformed_rows,
        "malformed_container": malformed_container,
    }


def attribute_coordinate(receipts, *, as_of, vintage=None,
                         mode: str = "reconstructed_price_history",
                         recorded_at=None) -> dict:
    """Attribute early-rotation pair rows to context-only coordinate observations.

    A reconstructed mode can never claim natural observation: only
    ``original_retained`` with a ``recorded_at`` is naturally_observed.
    """
    if mode not in EVIDENCE_MODES:
        raise ValueError(f"mode must be one of EVIDENCE_MODES, got {mode!r}")
    from engine import rotation_events

    ctx = rotation_events.early_rotation_context(receipts, as_of=as_of)
    observations = []
    unavailable_pair_ids = []
    for row in ctx.get("pairs") or []:
        if row.get("eligible_2s") is not True:
            pair_id = row.get("pair_id")
            if isinstance(pair_id, str):
                unavailable_pair_ids.append(pair_id)
            continue
        observations.append(TransitionObservation(
            definition_id=ctx["definition_id"],
            definition_version=ctx["schema"],
            roles={"receiver": row["num"], "donor": row["den"],
                   "context_group": row["context_group"]},
            coordinate={"date": row.get("value_as_of") or ctx["as_of"],
                        "vintage": vintage, "as_of": as_of},
            evidence_mode=mode,
            naturally_observed=(mode == "original_retained" and recorded_at is not None),
            first_known_observation_id=f"{ctx['definition_id']}:{row['pair_id']}:{as_of}",
            first_known_at=recorded_at,
            current_observation_at=as_of,
            interpretation=row.get("interpretation"),
            source_context=copy.deepcopy(row),
        ))
    return {
        "schema": "leadership_rotation_context.coordinate_attribution/v1",
        "context_state": ctx.get("state"),
        "context_reason_codes": list(ctx.get("reason_codes") or []),
        "observations": observations,
        "unavailable_pair_ids": sorted(unavailable_pair_ids),
        "relationship": "context_only",
        "legacy_events_modified": False,
    }


def earliest_observable_coordinate(observations, *, before, roles=None):
    """Earliest observation strictly before ``before`` (roles filter optional)."""
    cutoff = parse_time(before)
    if isinstance(cutoff, Unmeasured):
        return Unmeasured("missing_input")
    best = None
    best_date = None
    for obs in (observations if observations is not None else ()):
        if not isinstance(obs, TransitionObservation):
            continue  # dicts / None and other non-observations are silently skipped
        coordinate = obs.coordinate
        if not isinstance(coordinate, dict):
            continue
        when = parse_time(coordinate.get("date"))
        if isinstance(when, Unmeasured) or not when < cutoff:
            continue
        if roles:
            obs_roles = obs.roles
            if not isinstance(obs_roles, dict) or any(
                obs_roles.get(key) != value for key, value in roles.items()
            ):
                continue
        if best_date is None or when < best_date:
            best, best_date = obs, when
    if best is None:
        return Unmeasured("missing_input")
    return {
        "coordinate": dict(best.coordinate),
        "evidence_mode": best.evidence_mode,
        "naturally_observed": best.naturally_observed,
        "first_known_observation_id": best.first_known_observation_id,
        "relationship": "context_only",
        "legacy_event_untouched": True,
    }


def separate_from_legacy(observations, ledger_history) -> dict:
    """Keep transition observations DISTINCT from legacy event history -- never attached."""
    legacy_events = [
        {
            "lifecycle_id": row.get("lifecycle_id"),
            "observation_date": row.get("observation_date"),
            "recorded_at": row.get("recorded_at"),
            "mode": row.get("mode"),
            "from_key": row.get("from_key"),
            "to_key": row.get("to_key"),
        }
        for row in (ledger_history or {}).get("rows") or []
    ]
    return {
        "schema": "leadership_rotation_context.legacy_separation/v1",
        "legacy_status": (ledger_history or {}).get("status"),
        "legacy_events": legacy_events,
        "transition_observations": [
            obs.to_dict() for obs in (observations or ())
        ],
        "relationship": "context_only",
        "attached_to_legacy": 0,
    }


# ---------------------------------------------------------------------------
# 8. T08 -- coordinate-change attribution and repeated evidence
# ---------------------------------------------------------------------------

def beta_only_residual(r_g, r_m, beta):
    """Residual of r_g against a STATED hypothetical beta; no causal claim."""
    vg, rg = _value_or_reason(r_g)
    vm, rm = _value_or_reason(r_m)
    vb, rb = _value_or_reason(beta)
    if vg is None or vm is None or vb is None:
        # An unmeasured INPUT is missing_input (the T08 reason letter), whatever
        # sub-reason the value probe produced.
        return Unmeasured("missing_input")
    residual = vg - vb * vm
    excess = vg - vm
    if not (_finite(residual) and _finite(excess) and _finite(vb)):
        return Unmeasured("non_finite_input")
    explained = abs(residual) <= EPS
    return {
        "arithmetic_excess": excess,
        "stated_beta": vb,
        "beta_residual": residual,
        "explained_by_stated_beta": explained,
        "beta_basis": "stated_hypothetical_past_known",
        "interpretation": ("fully explained by stated beta" if explained
                           else "residual association under stated beta (not causal, not flow)"),
    }


def pair_interpretation(r_receiver, r_donor):
    """Label a receiver/donor pair WITHOUT claiming flows, recovery or causality."""
    vr, _rr = _value_or_reason(r_receiver)
    vd, _rd = _value_or_reason(r_donor)
    if vr is None or vd is None:
        # An unmeasured INPUT is missing_input (the T08 reason letter).
        return Unmeasured("missing_input")
    rw = relative_wealth(vr, vd)
    if isinstance(rw, Unmeasured):
        return rw
    difference = return_difference(vr, vd)
    if isinstance(difference, Unmeasured):
        return difference
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
        "return_difference": difference,
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
        held = (raw_after - zb["mean"]) / zb["sd"]
        z_holding_reference = held if _finite(held) else Unmeasured("non_finite_input")
    elif raw_after is not None and zb["state"] == "non_finite":
        z_holding_reference = Unmeasured("non_finite_input")
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


# ---------------------------------------------------------------------------
# 9. T17 -- one bounded measured group read (display-tier; ORCH-PROD frozen spec)
# ---------------------------------------------------------------------------
# APPEND-ONLY section (LR-T17-1, COMMON_LAWS §3 sanctioned candidate module):
# everything above this line stays byte-identical to the #9240 body. This is a
# bounded READ over the existing owners (a sector_cycles payload + a
# rotation_events payload): not a source, evaluator, event owner, store,
# publisher or schedule; no state, no I/O, no clock, never mutates an input.
# Current measurement, reconstructed history, early context, confirmed events
# and the research estimate stay DISTINCT objects; generations are never joined
# silently (a mismatched as-of withholds, it never merges); unknown stays null
# (never 0, never ranked); duplicate event ids count once; the reconstructed
# trail is referenced, never copied; and no combined entry score exists.

MEASURED_READ_SCHEMA = "leadership_rotation_context.measured_group_read/v1"
MEASURED_READ_MAX_EVENT_ROWS = 12
_MEASURED_READ_HORIZON_SESSIONS = {"rs_21d": 21, "rs_63d": 63}
_MEASURED_READ_EVENT_KEYS = ("id", "event_type", "sector", "from_key", "to_key",
                             "started", "day_n", "asof", "severity")
_MEASURED_READ_HISTORY_SOURCE = "/sectordata/sector_cycles.json#sectors[].rs_history"
_MEASURED_READ_EVENTS_SOURCE = "/marketdata/rotation_events.json#active"
_MEASURED_READ_EARLY_SOURCE = "/marketdata/rotation_events.json#early_context"
#: The declared source basis words engine/sector_cycles.py emits -> the label this
#: read prints. An absent/None basis keeps the producer default ("tr"); any other
#: word is an unknown basis and is labelled "unknown", never a matching label.
_MEASURED_READ_PRICE_BASIS = {"tr": "total_return", "price": "price_only"}


def _measured_read_event_row(ev) -> dict:
    """Tolerant projection of one rotation_events active row (private).

    Both owner shapes are read: the v1 in-sector rows (``from_leg``/``to_leg``)
    and the v2 cross rows (``event_type``/``donor``/``receiver``). Absent owner
    fields project to ``None`` -- a value is never invented.
    """
    from_leg = _as_mapping(ev.get("from_leg"))
    to_leg = _as_mapping(ev.get("to_leg"))
    donor = _as_mapping(ev.get("donor"))
    receiver = _as_mapping(ev.get("receiver"))
    sector = ev.get("sector")
    if sector is None:
        sector = ev.get("from_sector")
    return {
        "id": ev.get("id"),
        "event_type": ev.get("event_type"),
        "sector": sector,
        "from_key": from_leg.get("key") if from_leg.get("key") is not None else donor.get("key"),
        "to_key": to_leg.get("key") if to_leg.get("key") is not None else receiver.get("key"),
        "started": ev.get("started"),
        "day_n": ev.get("day_n"),
        "asof": ev.get("asof"),
        "severity": ev.get("severity"),
    }


def _measured_read_reconstruction(rec, *, generation_mismatch: bool) -> dict:
    """Reconstruction sub-object for one sector record (private).

    The trail itself lives in the owner payload and is REFERENCED, never
    copied -- only its point count and endpoint dates are printed, so the read
    stays bounded and never double counts the owner's history.
    """
    block = {
        "mode": "reconstructed_price_history",
        "naturally_observed": False,
        "status": "unavailable",
        "reason": "missing_input",
        "points": 0,
        "first": None,
        "last": None,
        "source": _MEASURED_READ_HISTORY_SOURCE,
    }
    if generation_mismatch:
        # Never join across generations: a history trail stamped with a
        # different as-of is withheld whole, points included.
        block["status"] = "incompatible_generation"
        block["reason"] = "history_as_of_mismatch"
        return block
    if not isinstance(rec, Mapping):
        return block
    now = _as_mapping(rec.get("now"))
    hist = rec.get("rs_history")
    hist = hist if isinstance(hist, list) else []
    if now.get("thin_history") is True:
        block["reason"] = "thin_history"
        return block
    if not hist:
        return block
    first = hist[0].get("date") if isinstance(hist[0], Mapping) else None
    last = hist[-1].get("date") if isinstance(hist[-1], Mapping) else None
    block.update(status="available", reason=None, points=len(hist), first=first, last=last)
    return block


def _assert_window_composition_compatible(generation, measurements):
    """Bind a requested exact-window composition to the parent generation.

    The companion block is published INSIDE the parent measured read, so it
    must describe the SAME generation: the same session end, the same
    benchmark, the same native cohort on the same total-return basis, over the
    same native population and the same three windows.

    A composition that cannot be bound is a PROGRAMMER error -- the module's
    documented ``ValueError`` convention -- never a silently attached
    companion and never a quietly degraded read. Neither the parent nor the
    child is restamped to make the pair agree, and no compatibility key is
    minted.

    An UNKNOWN or MALFORMED parent identity cannot qualify a populated
    output: the parent must name a strict session end, a benchmark identity
    and the total-return basis before a companion may be attached at all.
    """
    session_end = generation.get("session_end")
    if not isinstance(session_end, str) or _window_day(session_end) is None:
        raise ValueError(
            "sector_window_inputs cannot be bound: the parent generation has no "
            "known session end")
    benchmark = generation.get("benchmark")
    if not isinstance(benchmark, str) or not benchmark.strip():
        raise ValueError(
            "sector_window_inputs cannot be bound: the parent generation has no "
            "known benchmark")
    if generation.get("cohort_id") != US_SECTOR_COHORT_ID:
        raise ValueError(
            "sector_window_inputs cannot be bound: the parent generation is not "
            "the native sector cohort")
    if generation.get("price_basis") != "total_return":
        raise ValueError(
            "sector_window_inputs cannot be bound: the parent generation is not "
            "on the total_return price basis")
    end_session = measurements.get("end_session")
    if measurements.get("source_session") != session_end or end_session != session_end:
        raise ValueError(
            f"sector_window_inputs cannot be bound: the companion session end "
            f"{end_session!r} is not the parent session end {session_end!r}")
    if str(measurements.get("benchmark") or "").strip().upper() != benchmark.strip().upper():
        raise ValueError(
            f"sector_window_inputs cannot be bound: the companion benchmark "
            f"{measurements.get('benchmark')!r} is not the parent benchmark "
            f"{benchmark!r}")
    if measurements.get("cohort_id") != US_SECTOR_COHORT_ID:
        raise ValueError(
            "sector_window_inputs cannot be bound: the companion is not the "
            "native sector cohort")
    if measurements.get("price_basis") != "total_return":
        raise ValueError(
            "sector_window_inputs cannot be bound: the companion is not on the "
            "total_return price basis")
    if measurements.get("population") != "eleven_sector_etf_proxies":
        raise ValueError(
            "sector_window_inputs cannot be bound: the companion population is "
            "not the native eleven sector ETF identities")
    if [group.get("group_id") for group in measurements.get("groups", [])] != list(
            us_sector_cohort()):
        raise ValueError(
            "sector_window_inputs cannot be bound: the companion does not publish "
            "the native eleven sector ETF identities in the cohort's own order")
    if measurements.get("windows_sessions") != list(SECTOR_WINDOW_SESSIONS):
        raise ValueError(
            "sector_window_inputs cannot be bound: the companion does not publish "
            "the exact 5/20/63-session windows")


def measured_group_read(cycles_payload, *, rotation_payload=None, research_estimate=None,
                        horizon: str = "rs_63d", include_sector_dossiers: bool = False,
                        sector_window_inputs=None) -> dict:
    """One bounded measured group read over the us_sectors_11 cohort (T17).

    Pure and total: malformed mapping inputs (None, non-mapping, missing keys)
    degrade to ``unavailable`` sub-objects, never raise; ``horizon`` outside
    ``{rs_21d, rs_63d}`` is a programmer error (ValueError).

    ``include_sector_dossiers=True`` adds a strictly qualified dated projection.
    The default preserves the frozen v1 producer/parser bytes. Consumer rollout
    is explicit; this option grants no historical or trading authority.

    ``sector_window_inputs`` is the OPTIONAL explicit composition argument: a
    mapping of the exact-window measurement inputs (see
    :func:`measure_sector_windows`). When it is supplied the read gains a
    ``sector_window_measurements`` companion key; when it is absent the output
    is byte-identical to the frozen v1 read. The closed ``sector_dossiers/v1``
    block is never touched by this argument.

    A malformed composition argument is a PROGRAMMER error, not a data
    condition: an unknown key, a non-mapping argument, or a malformed
    calendar / window / end session raises ``ValueError`` rather than
    degrading into a silent unavailable read. The same holds for a composition
    that cannot be BOUND to this read's own generation: the companion is
    published inside this read, so it must describe the same generation, and
    an unbound one raises instead of being attached, dropped or restamped.
    """
    if type(include_sector_dossiers) is not bool:
        raise ValueError("include_sector_dossiers must be a bool")
    if horizon not in _MEASURED_READ_HORIZON_SESSIONS:
        raise ValueError(
            f"horizon must be one of {sorted(_MEASURED_READ_HORIZON_SESSIONS)}, got {horizon!r}"
        )
    payload = _as_mapping(cycles_payload)
    meta = _as_mapping(payload.get("meta"))
    hist_meta = _as_mapping(meta.get("rs_history"))
    session_end = meta.get("asOf")
    benchmark = meta.get("benchmark")
    history_schema = hist_meta.get("schema")
    history_as_of = hist_meta.get("as_of")
    basis = hist_meta.get("basis")
    if basis is None:
        price_basis = "total_return"        # the producer default (basis "tr")
    elif isinstance(basis, str):
        price_basis = _MEASURED_READ_PRICE_BASIS.get(basis, "unknown")
    else:
        price_basis = "unknown"             # a non-str basis is no basis word
    history_mismatch = bool(
        history_as_of is not None and session_end is not None and history_as_of != session_end
    )

    expected = us_sector_cohort()
    container, _ = _container_rows(payload.get("sectors"))
    records = {}
    for rec in container:
        if not isinstance(rec, Mapping):
            continue
        ticker = rec.get("ticker")
        if isinstance(ticker, str):
            records[ticker] = rec
    outside_cohort = sorted(set(records) - set(expected))

    values = {}
    measured = []
    missing = []
    for ticker in expected:
        rec = records.get(ticker)
        if rec is None:
            missing.append([ticker, "missing_input"])
            values[ticker] = Unmeasured("missing_input")
            continue
        value = _sector_record_value(rec, horizon)
        if is_measured(value):
            values[ticker] = float(value)
            measured.append(ticker)
        else:
            missing.append([ticker, value.reason])
            values[ticker] = value
    measured_n = len(measured)
    positives = sum(1 for t in measured if values[t] > 0)
    if not payload or measured_n == 0:
        status = "unavailable"
    elif measured_n == len(expected):
        status = "available"
    else:
        status = "partial"

    generation_id = (
        f"{session_end}|{benchmark}|{US_SECTOR_COHORT_ID}"
        if session_end is not None and benchmark is not None else None
    )

    ranked = rank_measured(values)
    rank_of = {ticker: i + 1 for i, ticker in enumerate(ranked["ranked"])}
    zs = cohort_zscores(values, cohort_id=US_SECTOR_COHORT_ID)

    from engine import sector_cycles

    groups = []
    for ticker in expected:
        info = sector_cycles.SECTORS.get(ticker) or {}
        rec = records.get(ticker)
        v21 = _sector_record_value(rec, "rs_21d") if rec is not None else Unmeasured("missing_input")
        v63 = _sector_record_value(rec, "rs_63d") if rec is not None else Unmeasured("missing_input")
        selected = values[ticker]
        z = zs["z"].get(ticker)
        groups.append({
            "group_id": ticker,
            "group_kind": "sector",
            "name_en": info.get("name"),
            "name_zh": info.get("name_zh"),
            "current": {
                "status": "measured" if is_measured(selected) else "unmeasured",
                "reason": None if is_measured(selected) else selected.reason,
                "rs_21d": float(v21) if is_measured(v21) else None,
                "rs_63d": float(v63) if is_measured(v63) else None,
                "units": "pct",
                "metric": "relative_wealth_pct",
                "rank": rank_of.get(ticker),
                "z": float(z) if is_measured(z) else None,
            },
            "reconstruction": _measured_read_reconstruction(rec, generation_mismatch=history_mismatch),
        })

    early_context = {
        "context_only": True,
        "status": "unavailable",
        "reason": "missing_input",
        "as_of": None,
        "state": None,
        "reason_codes": [],
        "coverage": None,
        "source": _MEASURED_READ_EARLY_SOURCE,
    }
    confirmed_events = {
        "status": "unavailable",
        "reason": "missing_input",
        "as_of": None,
        "n_active": None,
        "truncated": False,
        "rows": [],
        "source": _MEASURED_READ_EVENTS_SOURCE,
    }
    rotation_usable = (
        isinstance(rotation_payload, Mapping)
        and rotation_payload.get("schema") == "rotation_events.v1"
        and rotation_payload.get("ok") is True
    )
    if rotation_payload is not None and not rotation_usable:
        early_context["reason"] = "invalid_payload"
        confirmed_events["reason"] = "invalid_payload"
    elif rotation_usable:
        ec = rotation_payload.get("early_context")
        if isinstance(ec, Mapping):
            ec_as_of = ec.get("as_of")
            ec_coverage = ec.get("coverage") if isinstance(ec.get("coverage"), Mapping) else None
            if ec_as_of is not None and session_end is not None and ec_as_of != session_end:
                early_context.update(
                    status="incompatible_generation", reason="as_of_mismatch", as_of=ec_as_of,
                    state=None, reason_codes=list(ec.get("reason_codes") or []),
                    coverage=ec_coverage,
                )
            else:
                early_context.update(
                    status="available", reason=None, as_of=ec_as_of, state=ec.get("state"),
                    reason_codes=list(ec.get("reason_codes") or []), coverage=ec_coverage,
                )
        rot_as_of = rotation_payload.get("as_of")
        active = rotation_payload.get("active")
        if rot_as_of is not None and session_end is not None and rot_as_of != session_end:
            confirmed_events.update(
                status="incompatible_generation", reason="as_of_mismatch", as_of=rot_as_of,
            )
        elif not isinstance(active, (list, tuple)):
            # Unmeasured is not zero: an absent / None `active` is a MISSING input
            # and any other non-container is a MALFORMED payload. Neither is a
            # measured zero, so n_active stays None and no row is projected.
            confirmed_events.update(
                status="unavailable",
                reason="missing_input" if active is None else "invalid_payload",
                as_of=rot_as_of,
            )
        else:
            seen = set()
            deduped = []
            for ev in active:
                if not isinstance(ev, Mapping):
                    continue
                ev_id = ev.get("id")
                if ev_id in seen:
                    continue  # duplicate ids count once: first wins
                seen.add(ev_id)
                deduped.append(ev)
            n_active = len(deduped)
            confirmed_events.update(
                status="none" if n_active == 0 else "available",
                reason=None,
                as_of=rot_as_of,
                n_active=n_active,
                truncated=n_active > MEASURED_READ_MAX_EVENT_ROWS,
                rows=[_measured_read_event_row(ev)
                      for ev in deduped[:MEASURED_READ_MAX_EVENT_ROWS]],
            )

    if isinstance(research_estimate, ResearchEstimate):
        research_block = research_estimate.to_dict()
    else:
        research_block = {"status": "unavailable", "reason": "no_admitted_model"}

    roots = {"engine.sector_cycles"}
    if rotation_payload is not None:
        roots.add("engine.rotation_events")

    result = {
        "schema": MEASURED_READ_SCHEMA,
        "definition_id": DEFINITION_ID,
        "status": status,
        "authority": {"tier": "display", "may_rank": False, "may_gate": False,
                      "may_size": False, "may_trade": False, "may_escalate": False},
        "generation": {
            "id": generation_id,
            "cohort_id": US_SECTOR_COHORT_ID,
            "session_end": session_end,
            "benchmark": benchmark,
            "price_basis": price_basis,
            "history_schema": history_schema,
            "history_as_of": history_as_of,
        },
        "cohort": {
            "horizon": horizon,
            "window_sessions": _MEASURED_READ_HORIZON_SESSIONS[horizon],
            "expected_n": len(expected),
            "measured_n": measured_n,
            "missing": sorted(missing),
            "outside_cohort": outside_cohort,
            "positive_breadth": breadth(positives, measured_n, len(expected)).to_dict(),
            "bounds_note": ("breadth bounds are whole-population bounds over unmeasured "
                            "members, not confidence intervals"),
        },
        "groups": groups,
        "early_context": early_context,
        "confirmed_events": confirmed_events,
        "research_estimate": research_block,
        "source_roots": sorted(roots),
    }
    if include_sector_dossiers:
        result["sector_dossiers"] = _compose_sector_dossiers(
            cycles_payload, result, expected_group_ids=expected,
        )
    if sector_window_inputs is not None:
        if not isinstance(sector_window_inputs, Mapping):
            raise ValueError("sector_window_inputs must be a mapping of measurement inputs")
        unknown = sorted(str(key) for key in sector_window_inputs
                         if key not in _WINDOW_INPUT_KEYS)
        if unknown:
            raise ValueError(f"unknown sector_window_inputs keys: {unknown}")
        measurements = measure_sector_windows(**sector_window_inputs)
        # The companion is published INSIDE this read, so it is bound to this
        # read's own generation BEFORE it is attached. An unbound composition
        # raises rather than being attached, dropped or restamped.
        _assert_window_composition_compatible(result["generation"], measurements)
        result["sector_window_measurements"] = measurements
    return result


# ---------------------------------------------------------------------------
# Persistent Sector Leadership: opt-in dated evidence, no new producer
# ---------------------------------------------------------------------------

_DOSSIER_SCHEMA = "leadership_rotation_context.sector_dossiers/v1"
_DOSSIER_MAX_INPUT_ROWS = 128
_DOSSIER_SOURCE = "engine.sector_cycles"
_DOSSIER_BENCHMARK = re.compile(r"[A-Z][A-Z0-9.^-]{0,15}\Z")
_DOSSIER_GROUP = re.compile(r"[A-Z][A-Z0-9]{0,7}\Z")


def _dossier_text(value, limit=120):
    if (not isinstance(value, str) or not value or len(value) > limit
            or any(ord(c) < 32 for c in value)):
        return None
    return value


def _dossier_day(value):
    if not isinstance(value, str) or len(value) != 10:
        return None
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.isoformat() == value else None


def _dossier_number(value):
    if isinstance(value, bool) or not isinstance(value, numbers.Real):
        return None
    try:
        result = float(value)
    except (ValueError, TypeError, OverflowError):
        return None
    return result if math.isfinite(result) else None


def _dossier_cutoff(value):
    if not isinstance(value, str) or len(value) > 64:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.astimezone(timezone.utc) if parsed.tzinfo is not None else None
    except (ValueError, OverflowError):
        return None


def _dossier_index(rows, key, expected):
    """Bound work before iteration; any duplicate identity is withheld."""
    found, duplicates, outsiders = {}, set(), set()
    malformed = 0
    if not isinstance(rows, (list, tuple)):
        return found, duplicates, [], 0, "missing_or_invalid_rows"
    if len(rows) > _DOSSIER_MAX_INPUT_ROWS:
        return found, duplicates, [], 0, "input_rows_exceed_bound"
    for row in rows:
        if not isinstance(row, Mapping):
            malformed += 1
            continue
        identity = row.get(key)
        if not isinstance(identity, str) or not _DOSSIER_GROUP.fullmatch(identity):
            malformed += 1
            continue
        if identity not in expected:
            outsiders.add(identity)
            continue
        if identity in found:
            duplicates.add(identity)
        else:
            found[identity] = row
    return found, duplicates, sorted(outsiders)[:11], malformed, None


def _dossier_unavailable(reason, **fields):
    return {"status": "unavailable", "reason": reason, **fields}


def _compose_sector_dossiers(cycles_payload, measured_read, *,
                            expected_group_ids, decision_cutoff=None):
    """Compose all native cohort identities without inventing a forecast.

    expected_group_ids is supplied by the incumbent us_sector_cohort() owner, not
    by a client request. Invalid owner configuration is a programming error.
    Data inputs degrade to explicit missingness. decision_cutoff must be an aware
    ISO datetime; supplying it always withholds values until an owner-native
    availability and correction contract is separately implemented.
    """
    if (not isinstance(expected_group_ids, (tuple, list))
            or len(expected_group_ids) != 11
            or any(not isinstance(x, str) or not _DOSSIER_GROUP.fullmatch(x)
                   for x in expected_group_ids)
            or len(set(expected_group_ids)) != 11):
        raise ValueError("expected_group_ids must be the eleven native sector identities")
    expected = tuple(expected_group_ids)
    source, read = _as_mapping(cycles_payload), _as_mapping(measured_read)
    meta = _as_mapping(source.get("meta"))
    history = _as_mapping(meta.get("rs_history"))
    generation = _as_mapping(read.get("generation"))
    native, duplicate_native, outsiders, malformed, native_error = _dossier_index(
        source.get("sectors"), "ticker", expected)
    projected, duplicate_projected, _, malformed_read, read_error = _dossier_index(
        read.get("groups"), "group_id", expected)

    reasons = []
    if read.get("schema") != MEASURED_READ_SCHEMA:
        reasons.append("invalid_measured_read_schema")
    if generation.get("cohort_id") != US_SECTOR_COHORT_ID:
        reasons.append("cohort_identity_mismatch")
    session = _dossier_day(meta.get("asOf"))
    if session is None:
        reasons.append("source_session_missing_or_invalid")
    elif generation.get("session_end") != session.isoformat():
        reasons.append("source_session_mismatch")
    history_session = _dossier_day(history.get("as_of"))
    if history_session is None:
        reasons.append("history_session_missing_or_invalid")
    elif session is not None and history_session != session:
        reasons.append("history_session_mismatch")
    benchmark = _dossier_text(meta.get("benchmark"), 16)
    if (benchmark is None or not _DOSSIER_BENCHMARK.fullmatch(benchmark)
            or benchmark in {"UNKNOWN", "NONE", "NULL"}):
        benchmark = None
        reasons.append("benchmark_missing_or_invalid")
    elif (generation.get("benchmark") != benchmark
          or history.get("benchmark") != benchmark):
        reasons.append("benchmark_identity_mismatch")
    basis = history.get("basis")
    if not isinstance(basis, str) or basis != "tr":
        reasons.append("return_basis_not_qualified")
    elif generation.get("price_basis") != "total_return":
        reasons.append("return_basis_mismatch")
    if history.get("schema") != "sector_cycles.rs_history.v1":
        reasons.append("history_schema_not_qualified")
    if (history.get("mode") != "reconstructed_price_history"
            or history.get("naturally_observed") is not False):
        reasons.append("evidence_mode_not_qualified")
    if native_error:
        reasons.append(native_error)
    if read_error:
        reasons.append("measured_" + read_error)
    # Only the source actually used here is attributed. Rotation roots carried by
    # the wider reader are not independent confirmations of the same ETF returns.
    raw_roots = read.get("source_roots")
    root_present = (isinstance(raw_roots, (list, tuple))
                    and len(raw_roots) <= 32
                    and any(x == _DOSSIER_SOURCE for x in raw_roots if isinstance(x, str)))
    if not root_present:
        reasons.append("measurement_source_root_missing")

    cut = _dossier_cutoff(decision_cutoff) if decision_cutoff is not None else None
    availability_reason = "original_availability_not_supplied"
    if decision_cutoff is not None:
        if cut is None:
            availability_reason = "invalid_decision_cutoff"
        elif session is not None and session > cut.date():
            availability_reason = "source_session_after_decision_cutoff"
        else:
            availability_reason = "availability_time_missing"
        reasons.append(availability_reason)

    rows = []
    for group_id in expected:
        raw, group = native.get(group_id), projected.get(group_id)
        current = _as_mapping(_as_mapping(group).get("current"))
        row_reasons = list(reasons)
        if raw is None or group is None:
            row_reasons.append("missing_group")
        if group_id in duplicate_native or group_id in duplicate_projected:
            row_reasons.append("duplicate_group_identity")
        if raw is not None and raw.get("kind") not in (None, "sector"):
            row_reasons.append("group_kind_mismatch")
        if group is not None and group.get("group_kind") != "sector":
            row_reasons.append("measured_group_kind_mismatch")
        if (current.get("metric") != "relative_wealth_pct"
                or current.get("units") != "pct"):
            row_reasons.append("measurement_definition_mismatch")
        now = _as_mapping(_as_mapping(raw).get("now"))
        if now.get("thin_history") is True:
            row_reasons.append("thin_history")
        if raw is not None and "series_provenance" in raw:
            provenance = raw["series_provenance"]
            if not isinstance(provenance, Mapping) or not provenance:
                row_reasons.append("row_provenance_invalid")
            else:
                if provenance.get("rs_basis") != "tr":
                    row_reasons.append("row_return_basis_mismatch")
                if provenance.get("benchmark") != benchmark:
                    row_reasons.append("row_benchmark_mismatch")

        values, nulls = {}, {}
        for sessions in (21, 63):
            field = f"rs_{sessions}d"
            owner_value, projected_value = _dossier_number(now.get(field)), _dossier_number(current.get(field))
            if row_reasons:
                value, reason = None, row_reasons[0]
            elif owner_value is None:
                value = None
                reason = "missing_input" if now.get(field) is None else "invalid_measurement"
            elif owner_value < -100.0:
                # Nonnegative group wealth / positive benchmark wealth cannot
                # produce a relative-wealth percentage below -100.
                value, reason = None, "outside_relative_wealth_domain"
            elif projected_value is None or owner_value != projected_value:
                value, reason = None, "measurement_projection_mismatch"
            else:
                value, reason = owner_value, None
            values[field], nulls[field] = value, reason
        count = sum(v is not None for v in values.values())
        rows.append({
            "group_id": group_id,
            "name_en": _dossier_text(_as_mapping(group).get("name_en")),
            "name_zh": _dossier_text(_as_mapping(group).get("name_zh")),
            "status": "available" if count == 2 else "partial" if count else "unavailable",
            "relative_wealth_pct": values,
            "null_reasons": nulls,
            "qualification_reasons": sorted(set(row_reasons)),
        })

    counts = {}
    for sessions in (21, 63):
        values = [row["relative_wealth_pct"][f"rs_{sessions}d"] for row in rows]
        valid = [v for v in values if v is not None]
        counts[str(sessions)] = {
            "expected_n": len(expected), "measured_n": len(valid),
            "positive_n": sum(v > 0 for v in valid) if valid else None,
        }
    available = sum(row["status"] == "available" for row in rows)
    any_values = any(row["status"] != "unavailable" for row in rows)
    return {
        "schema": _DOSSIER_SCHEMA,
        "status": "partial" if any_values else "unavailable",
        "measurement_status": ("available" if available == len(expected)
                               else "partial" if any_values else "unavailable"),
        "cohort_id": US_SECTOR_COHORT_ID,
        "population": "eleven_sector_etf_proxies",
        "as_of": session.isoformat() if session else None,
        "benchmark": benchmark,
        "price_basis": "total_return" if basis == "tr" else None,
        "units": "pct",
        "windows_sessions": [21, 63],
        "unavailable_windows": {"sessions": [5, 20], "reason": "not_supplied_by_owner"},
        "absolute_returns": _dossier_unavailable("not_supplied_by_owner"),
        "compatibility_key": _dossier_text(generation.get("id"), 160),
        "source_generation": _dossier_unavailable("immutable_generation_not_supplied", id=None),
        "availability": {
            "mode": "as_known" if decision_cutoff is not None else "dated_snapshot",
            "decision_cutoff": cut.isoformat() if cut else None,
            "original_available_at": None,
            "historically_admissible": False,
            "reason": availability_reason,
        },
        "history": {"mode": "reconstructed_price_history", "naturally_observed": False},
        "freshness": {"status": "unverified", "reason": "owner_freshness_receipt_not_supplied"},
        "corrections": _dossier_unavailable("native_revision_selection_not_supplied"),
        "authority": {"may_rank": False, "may_gate": False, "may_size": False,
                      "may_trade": False, "may_escalate": False},
        "forecasts": {"status": "not_qualified", "expected_return": None,
                      "persistence_estimate": None, "allocation_weight": None},
        "mechanism": _dossier_unavailable("no_qualified_evidence", owner="engine.theme_graph"),
        "risk": _dossier_unavailable("no_qualified_risk_context", owner="engine.risk_envelope", scope=None),
        "constituent_breadth": _dossier_unavailable("native_membership_not_supplied"),
        "constituent_concentration": _dossier_unavailable("native_weights_not_supplied"),
        "cross_sector_breadth_counts": counts,
        "dependency_audit": {
            "source_roots": [_DOSSIER_SOURCE] if root_present else [],
            "source_family_count": 1 if root_present else 0,
            "independence": "not_established",
            "shared_rolling_windows": True, "constituent_overlap": "unknown",
        },
        "diagnostics": {
            "qualification_reasons": reasons,
            "duplicate_groups": sorted(duplicate_native | duplicate_projected),
            "outside_cohort": outsiders,
            "malformed_source_rows": malformed, "malformed_measured_rows": malformed_read,
        },
        "groups": rows,
    }


# ---------------------------------------------------------------------------
# Persistent Sector Leadership: exact 5/20/63-session window measurements
# ---------------------------------------------------------------------------
#
# The incumbent sector owner publishes a ROLLING coordinate.
# engine.sector_cycles._relative_strength_series_counted drops every row whose
# price is missing, forward-fills a missing benchmark close for up to five
# sessions, and _leadership then takes pct_change over the SURVIVING rows. A
# gapped capture therefore measures a window that is not the requested one: the
# endpoints slide onto whatever rows survived, and the published label no
# longer says how many sessions the return actually spans. That incumbent is
# preserved unchanged here -- this section does not touch it and does not
# claim its 21/63/126 labels.
#
# This section adds a second, EXACT measurement of the same quantity over an
# explicit canonical session calendar. For window N the start session S_N is
# the session exactly N positions before the end session T ON THAT CALENDAR,
# so a 5-session return spans six session endpoints. Interior gaps never move
# an endpoint; they are disclosed as coverage instead.
#
# It is PURE: every input arrives as an argument -- no clock read, no file
# read, no network, no ambient resolution, no mutation of a caller's argument.
# It measures only. It never ranks, scores, forecasts, sizes, allocates or
# trades, and it manufactures no compatibility key, no native generation id
# and no content hash.

SECTOR_WINDOW_MEASUREMENTS_SCHEMA = "leadership_rotation_context.sector_window_measurements/v1"
SECTOR_WINDOW_SESSIONS = (5, 20, 63)

#: Bounded input sizes: a measurement never iterates an unbounded container.
_WINDOW_MAX_PANEL_ROWS = 20000
_WINDOW_MAX_CALENDAR = 20000
_WINDOW_MAX_WINDOWS = 16
_WINDOW_MAX_WINDOW_SESSIONS = 252
_WINDOW_MAX_COLUMNS = 64
_WINDOW_MAX_POPULATION = 64
_WINDOW_MAX_SOURCE_ROOTS = 32
_WINDOW_MAX_RECEIPT_KEYS = 32
#: How many duplicate/mismatched identities a diagnostic list may name.
_WINDOW_MAX_DIAGNOSTIC_NAMES = 16
#: Text bounds. A binding string is METADATA, never a payload: an identity, a
#: root or a clock is short, and a control character in any of them is a
#: malformed argument rather than content.
_WINDOW_MAX_IDENTITY_LENGTH = 64
_WINDOW_MAX_ROOT_LENGTH = 256
_WINDOW_MAX_CLOCK_LENGTH = 64
#: Receipt bounds. The receipt stays OPAQUE JSON metadata, so the budget is on
#: its STRUCTURE and its ENCODED size -- never on what a field means.
_WINDOW_MAX_RECEIPT_BYTES = 16384
_WINDOW_MAX_RECEIPT_DEPTH = 8
_WINDOW_MAX_RECEIPT_CONTAINER = 256
_WINDOW_MAX_RECEIPT_NODES = 2048
#: Presentation rounding. Every ratio is computed in full float precision
#: FIRST; only the published percentage is rounded.
_WINDOW_PCT_DECIMALS = 6

#: Every reason this section can publish, in one bounded vocabulary.
_WINDOW_REASONS = (
    # per-cell missingness
    "missing_input",
    "non_finite_input",
    "invalid_price",
    "benchmark_missing",
    "benchmark_invalid",
    "insufficient_reference_history",
    # block-level qualification
    "empty_panel",
    "future_tail",
    "source_session_mismatch",
    "ambiguous_duplicate_price_index",
    "ambiguous_duplicate_column",
    "cohort_identity_mismatch",
    "benchmark_identity_mismatch",
    "return_basis_not_qualified",
)

#: Every reason the LIMITATIONS block can publish. These describe what this
#: section does NOT establish; they are distinct from the measurement
#: missingness reasons above.
_WINDOW_LIMITATION_REASONS = (
    "owner_availability_clock_not_supplied",
    "owner_publication_clock_not_supplied",
    "owner_history_clock_not_supplied",
    "native_revision_selection_not_supplied",
    "owner_freshness_receipt_not_supplied",
    "point_in_time_admission_not_supplied",
)

#: The endpoint definition this section publishes, verbatim.
_WINDOW_ENDPOINT_DEFINITION = (
    "Endpoint return: P(T)/P(S_N) - 1, where T is the explicit end session and "
    "S_N is the canonical US session exactly N positions before T, so a "
    "5-session return spans 6 session endpoints. Relative wealth is "
    "(1+R_group)/(1+R_benchmark) - 1 -- a wealth ratio, never a return "
    "difference. Interior gaps never move an endpoint; they are disclosed as "
    "observed coverage. Prices are strictly positive, finite, total-return "
    "adjusted closes read at the two endpoints only."
)

_WINDOW_BINDING_KEYS = ("source_roots", "clocks", "receipt", "cohort_id",
                        "benchmark", "source_session", "price_basis")
_WINDOW_CLOCK_KEYS = ("publication", "availability", "correction", "history")
_WINDOW_INPUT_KEYS = ("closes", "benchmark", "end_session", "source_session",
                      "reference_sessions", "windows", "population", "source_binding")


def _window_day(value):
    """Strict ``YYYY-MM-DD`` -> the same string, else None (private)."""
    if not isinstance(value, str) or len(value) != 10:
        return None
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        return None
    return value if parsed.isoformat() == value else None


def _window_price(value):
    """(usable_price_or_None, reason_or_None) for one endpoint observation.

    A price is usable only when it is a finite, strictly positive REAL number.
    ``bool`` is a real subclass and is rejected explicitly; a non-finite value
    is reported apart from an invalid one so the two are never conflated.
    """
    if value is None:
        return None, "missing_input"
    if isinstance(value, bool):
        return None, "invalid_price"
    if not isinstance(value, numbers.Number):
        return None, "invalid_price"
    try:
        price = float(value)
    except (TypeError, ValueError, OverflowError):
        return None, "invalid_price"
    if not math.isfinite(price):
        return None, "non_finite_input"
    if price <= 0.0:
        return None, "invalid_price"
    return price, None


def _window_sizes(windows):
    """Validate the requested window sizes -> ascending tuple of ints."""
    if not isinstance(windows, (list, tuple)):
        raise ValueError("windows must be a list or tuple of session counts")
    if not windows:
        raise ValueError("windows must name at least one session count")
    if len(windows) > _WINDOW_MAX_WINDOWS:
        raise ValueError("windows exceeds the bounded window count")
    sizes, previous = [], None
    for item in windows:
        if isinstance(item, bool) or not isinstance(item, int):
            raise ValueError("window session counts must be integers")
        if item < 1 or item > _WINDOW_MAX_WINDOW_SESSIONS:
            raise ValueError("window session counts must be positive and bounded")
        if previous is not None and item <= previous:
            raise ValueError("windows must be strictly ascending and duplicate-free")
        previous = item
        sizes.append(item)
    return tuple(sizes)


def _window_calendar(reference_sessions, end_session):
    """Validate the canonical calendar -> (ascending day list, index of T).

    The calendar is an explicit argument, so a malformed one is a programmer
    error and raises: an unsorted or duplicated calendar would silently move
    an endpoint, which is exactly what this section exists to prevent.
    """
    if not isinstance(reference_sessions, (list, tuple)):
        raise ValueError("reference_sessions must be a list or tuple of ISO dates")
    if len(reference_sessions) > _WINDOW_MAX_CALENDAR:
        raise ValueError("reference_sessions exceeds the bounded calendar length")
    calendar, previous = [], None
    for item in reference_sessions:
        day = _window_day(item)
        if day is None:
            raise ValueError("reference_sessions must contain strict YYYY-MM-DD strings")
        if previous is not None and day <= previous:
            raise ValueError(
                "reference_sessions must be strictly ascending and duplicate-free")
        previous = day
        calendar.append(day)
    end = _window_day(end_session)
    if end is None:
        raise ValueError("end_session must be a strict YYYY-MM-DD string")
    if end not in calendar:
        raise ValueError("end_session must be a canonical session on the reference calendar")
    return calendar, calendar.index(end)


def _window_population(population):
    """Resolve the measured population -> (tickers, names, population label).

    ``None`` means the incumbent cohort owner: the canonical eleven native
    sector ETF identities in the cohort's own order. An explicit list is
    accepted for a bounded foreign cohort; it never renames a native identity.
    """
    if population is None:
        from engine import sector_cycles

        tickers = us_sector_cohort()
        names = {ticker: dict(sector_cycles.SECTORS.get(ticker) or {}) for ticker in tickers}
        return tickers, names, "eleven_sector_etf_proxies", US_SECTOR_COHORT_ID
    if not isinstance(population, (list, tuple)):
        raise ValueError("population must be a list or tuple of ticker identities")
    if not population:
        raise ValueError("population must name at least one identity")
    if len(population) > _WINDOW_MAX_POPULATION:
        raise ValueError("population exceeds the bounded population length")
    tickers = []
    for item in population:
        if not isinstance(item, str) or not item.strip():
            raise ValueError("population identities must be non-empty strings")
        tickers.append(item)
    if len(set(tickers)) != len(tickers):
        raise ValueError("population identities must be unique")
    # A foreign cohort is not the native one: it carries no native cohort id.
    return tuple(tickers), {}, "explicit_population", None


def _window_panel(rows):
    """Normalise the captured wide panel -> (prices, sessions, diagnostics).

    A row is one canonical session and carries one column per ticker. Ticker
    identity is the trimmed upper-cased column key, so two columns resolving
    to one identity are AMBIGUOUS; two rows carrying one session are an
    ambiguous price index. Neither is silently collapsed: both are reported.
    """
    if not isinstance(rows, (list, tuple)):
        raise ValueError("closes must be a list or tuple of session rows")
    if len(rows) > _WINDOW_MAX_PANEL_ROWS:
        raise ValueError("closes exceeds the bounded panel length")
    prices, column_owner = {}, {}
    sessions, duplicate_sessions, ambiguous_columns = set(), set(), set()
    malformed_rows = 0
    for row in rows:
        if not isinstance(row, Mapping):
            malformed_rows += 1
            continue
        session = _window_day(row.get("session"))
        if session is None:
            malformed_rows += 1
            continue
        if session in sessions:
            duplicate_sessions.add(session)
        sessions.add(session)
        for column, value in row.items():
            if column == "session":
                continue
            if not isinstance(column, str) or not column.strip():
                malformed_rows += 1
                continue
            ticker = column.strip().upper()
            owner = column_owner.get(ticker)
            if owner is None:
                column_owner[ticker] = column
            elif owner != column:
                ambiguous_columns.add(ticker)
            prices.setdefault(ticker, {})[session] = value
    if len(prices) > _WINDOW_MAX_COLUMNS:
        raise ValueError("closes exceeds the bounded column count")
    diagnostics = {
        "panel_rows": len(rows),
        "malformed_rows": malformed_rows,
        "duplicate_sessions": sorted(duplicate_sessions)[:_WINDOW_MAX_DIAGNOSTIC_NAMES],
        "ambiguous_columns": sorted(ambiguous_columns)[:_WINDOW_MAX_DIAGNOSTIC_NAMES],
        "columns": sorted(prices),
    }
    return prices, sessions, diagnostics


def _window_text(value, limit, what):
    """One bounded, control-free text value (private).

    A binding string is METADATA. A control character inside it is a malformed
    argument, never content, and an over-long value is an unbounded payload --
    both are refused rather than trimmed or repaired.
    """
    if not isinstance(value, str) or not value:
        raise ValueError(f"{what} must be a non-empty string")
    if len(value) > limit:
        raise ValueError(f"{what} exceeds the bounded length of {limit}")
    if any(ord(char) < 0x20 or ord(char) == 0x7F for char in value):
        raise ValueError(f"{what} must not contain control characters")
    return value


def _window_clock(value, key):
    """One bounded, timezone-aware ISO timestamp -- or None (private).

    A clock is an instant the owner asserts, so it must carry an explicit UTC
    offset: a naive ("wall clock") timestamp names no instant and is refused.
    This module reads no clock of its own -- none is manufactured here.
    """
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"source_binding clock {key} must be null or an ISO timestamp string")
    _window_text(value, _WINDOW_MAX_CLOCK_LENGTH, f"source_binding clock {key}")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        raise ValueError(f"source_binding clock {key} must be an ISO timestamp") from None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"source_binding clock {key} must carry an explicit UTC offset")
    return value


def _window_receipt(receipt):
    """Validate one opaque JSON receipt -> a detached, publishable copy (private).

    The receipt stays OPAQUE metadata: this section reads no field out of it
    and infers no freshness, availability or point-in-time admission from it.
    What is refused is a receipt that could not be published as JSON -- a
    non-finite number, a value JSON cannot carry, a cycle, or a container,
    depth or byte budget over the bounds. The published receipt is a DETACHED
    copy, so no mutable reference crosses into the published block and the
    caller keeps sole ownership of the object it handed over.
    """
    nodes = 0

    def _walk(node, depth, seen):
        nonlocal nodes
        nodes += 1
        if nodes > _WINDOW_MAX_RECEIPT_NODES:
            raise ValueError("source_binding receipt exceeds the bounded node count")
        if depth > _WINDOW_MAX_RECEIPT_DEPTH:
            raise ValueError("source_binding receipt exceeds the bounded depth")
        if node is None or isinstance(node, (str, bool, int)):
            return
        if isinstance(node, float):
            if not math.isfinite(node):
                raise ValueError("source_binding receipt carries a non-finite number")
            return
        if isinstance(node, (Mapping, list, tuple)):
            if id(node) in seen:
                raise ValueError("source_binding receipt carries a cycle")
            if len(node) > _WINDOW_MAX_RECEIPT_CONTAINER:
                raise ValueError("source_binding receipt exceeds the bounded container length")
            seen.add(id(node))
            try:
                if isinstance(node, Mapping):
                    for key, value in node.items():
                        if not isinstance(key, str):
                            raise ValueError("source_binding receipt keys must be strings")
                        _walk(value, depth + 1, seen)
                else:
                    for value in node:
                        _walk(value, depth + 1, seen)
            finally:
                seen.discard(id(node))
            return
        raise ValueError("source_binding receipt must carry JSON values only")

    _walk(receipt, 0, set())
    try:
        encoded = json.dumps(receipt, allow_nan=False)
    except (TypeError, ValueError, RecursionError) as exc:
        raise ValueError(f"source_binding receipt is not publishable JSON: {exc}") from exc
    if len(encoded.encode("utf-8")) > _WINDOW_MAX_RECEIPT_BYTES:
        raise ValueError("source_binding receipt exceeds the bounded encoded size")
    return json.loads(encoded)


def _window_binding(source_binding):
    """Validate the incumbent owner's source binding -> (binding, diagnostics).

    Only what the owner actually supplies is carried: an absent clock stays
    unknown (None) and is never replaced by a manufactured one. What the owner
    supplies is METADATA, so it is bounded on the way in -- short control-free
    strings, timezone-aware clocks, and a receipt that is finite, bounded and
    publishable as JSON -- and the receipt is published DETACHED, so the caller
    keeps sole ownership of the object it handed over.

    A supplied clock or receipt never establishes freshness, availability or
    point-in-time admission by itself: the LIMITATIONS block keeps reporting
    those as unverified whatever the owner supplies.
    """
    if source_binding is None:
        return {}, {"binding_keys": [], "receipt_withheld": False}
    if not isinstance(source_binding, Mapping):
        raise ValueError("source_binding must be a mapping")
    unknown = sorted(str(key) for key in source_binding if key not in _WINDOW_BINDING_KEYS)
    if unknown:
        raise ValueError(f"unknown source_binding keys: {unknown}")
    binding = {}
    roots = source_binding.get("source_roots")
    if roots is not None:
        if not isinstance(roots, (list, tuple)):
            raise ValueError("source_binding source_roots must be a list of strings")
        if len(roots) > _WINDOW_MAX_SOURCE_ROOTS:
            raise ValueError("source_binding source_roots exceeds the bounded count")
        binding["source_roots"] = [
            _window_text(root, _WINDOW_MAX_ROOT_LENGTH, "source_binding source_roots entry")
            for root in roots
        ]
    clocks = source_binding.get("clocks")
    if clocks is not None:
        if not isinstance(clocks, Mapping):
            raise ValueError("source_binding clocks must be a mapping")
        unknown_clocks = sorted(str(key) for key in clocks if key not in _WINDOW_CLOCK_KEYS)
        if unknown_clocks:
            raise ValueError(f"unknown source_binding clock keys: {unknown_clocks}")
        binding["clocks"] = {key: _window_clock(clocks.get(key), key)
                             for key in _WINDOW_CLOCK_KEYS}
    receipt = source_binding.get("receipt")
    withheld = False
    if receipt is not None:
        if not isinstance(receipt, Mapping):
            raise ValueError("source_binding receipt must be a mapping")
        if len(receipt) <= _WINDOW_MAX_RECEIPT_KEYS:
            binding["receipt"] = _window_receipt(receipt)
        else:
            withheld = True
    for key in ("cohort_id", "benchmark", "source_session", "price_basis"):
        value = source_binding.get(key)
        if value is not None:
            binding[key] = _window_text(
                value, _WINDOW_MAX_IDENTITY_LENGTH, f"source_binding {key}")
    if binding.get("source_session") is not None and _window_day(binding["source_session"]) is None:
        raise ValueError("source_binding source_session must be a strict YYYY-MM-DD string")
    return binding, {"binding_keys": sorted(binding), "receipt_withheld": withheld}


def _window_cell(absolute, absolute_reason, relative, relative_reason,
                 observed_n, expected_n):
    """One sector/window measurement cell (private)."""
    return {
        "status": ("available" if absolute is not None and relative is not None
                   else "partial" if absolute is not None or relative is not None
                   else "unavailable"),
        "absolute_return_pct": absolute,
        "relative_wealth_pct": relative,
        "null_reasons": {
            "absolute_return_pct": absolute_reason,
            "relative_wealth_pct": relative_reason,
        },
        "coverage": {
            "observed_n": observed_n,
            "expected_n": expected_n,
            "ratio": round(observed_n / expected_n, _WINDOW_PCT_DECIMALS) if expected_n else 0.0,
        },
    }


def _window_unavailable_cell(reason, expected_n):
    """One sector/window cell that could not be measured at all (private)."""
    return _window_cell(None, reason, None, reason, 0, expected_n)


def _window_return(start_price, end_price):
    """(return_fraction, reason) for two usable endpoints (private)."""
    value = end_price / start_price - 1.0
    if not math.isfinite(value):
        return None, "non_finite_input"
    return value, None


def _window_pct(fraction):
    """(published_pct_or_None, overflowed) for one measured fraction (private).

    The published unit is PERCENT, and a FINITE fraction can still overflow
    that scaling: 1e307 * 100 is an infinity. Finiteness is therefore validated
    AFTER the scaling, never before it, so an overflowed publication is null
    rather than an infinity in the JSON.

    ``(None, False)`` means there was nothing to publish and the caller keeps
    its own measurement reason; ``(None, True)`` means the fraction existed
    but its PERCENT rendering is not representable, so the publication is null
    and the caller reports the stable non-finite reason.
    """
    if fraction is None:
        return None, False
    try:
        scaled = float(fraction) * 100.0
    except (TypeError, ValueError, OverflowError):
        return None, True
    if not math.isfinite(scaled):
        return None, True
    return round(scaled, _WINDOW_PCT_DECIMALS), False


def _window_publication(absolute, absolute_reason, relative, relative_reason):
    """The four published values of one cell (private).

    ``(absolute_pct, absolute_reason, relative_pct, relative_reason)``. Each
    published PERCENT is validated on its own AFTER the scaling, so a finite
    fraction that overflows the percent scale is published as null with the
    stable non-finite reason instead of as an infinity -- and one overflowed
    value never disowns the other.
    """
    absolute_pct, absolute_overflowed = _window_pct(absolute)
    if absolute_overflowed:
        absolute_reason = "non_finite_input"
    relative_pct, relative_overflowed = _window_pct(relative)
    if relative_overflowed:
        relative_reason = "non_finite_input"
    return absolute_pct, absolute_reason, relative_pct, relative_reason


def measure_sector_windows(
    closes,
    *,
    benchmark,
    end_session,
    source_session,
    reference_sessions,
    windows=SECTOR_WINDOW_SESSIONS,
    population=None,
    source_binding=None,
) -> dict:
    """Exact 5/20/63-session window measurements over a captured total-return panel.

    Pure and total. Every input is an argument: the captured panel, the
    benchmark identity, the explicit end and source sessions, the canonical US
    session calendar, and the incumbent owner's source binding. Nothing is
    resolved from the environment, the clock, the filesystem or a global.

    ``closes`` is the captured WIDE panel: one row per canonical session, one
    column per ticker, the session named by the row's ``"session"`` key and
    each ticker carrying its total-return adjusted close at that session.

    The end session ``T`` must be a session on ``reference_sessions``. For
    window ``N`` the start session ``S_N`` is the session exactly ``N``
    positions before ``T`` ON THAT CALENDAR, so a 5-session return spans six
    session endpoints. Endpoints are read exactly at ``S_N`` and ``T``: a
    missing or invalid price nulls the affected values with a stable reason
    and NEVER moves an endpoint, and an interior gap is disclosed as coverage
    instead. Insufficient calendar history makes that window unavailable with
    no invented window dates.

    The result is a closed, bounded JSON object under
    ``leadership_rotation_context.sector_window_measurements/v1``. It carries
    the absolute return and the relative wealth per sector and window, the
    common benchmark return once per window, and nothing else: no rank, no
    score, no forecast, no allocation, no target and no trade. All authority
    flags are false. No compatibility key, native generation id or content
    hash is manufactured.
    """
    if not isinstance(benchmark, str) or not benchmark.strip():
        raise ValueError("benchmark must be a non-empty ticker identity")
    benchmark = benchmark.strip().upper()
    if len(benchmark) > 16:
        raise ValueError("benchmark ticker identity is too long")
    window_sizes = _window_sizes(windows)
    calendar, end_index = _window_calendar(reference_sessions, end_session)
    source_day = _window_day(source_session)
    if source_day is None:
        raise ValueError("source_session must be a strict YYYY-MM-DD string")
    end_day = calendar[end_index]
    tickers, names, population_label, cohort_id = _window_population(population)
    prices, panel_sessions, panel_diagnostics = _window_panel(closes)
    binding, binding_diagnostics = _window_binding(source_binding)

    # --- block-level qualification -----------------------------------------
    reasons = []
    if source_day != end_day:
        reasons.append("source_session_mismatch")
    tail = sorted(day for day in panel_sessions if day > end_day)
    if tail:
        reasons.append("future_tail")
    if panel_diagnostics["duplicate_sessions"]:
        reasons.append("ambiguous_duplicate_price_index")
    if panel_diagnostics["ambiguous_columns"]:
        reasons.append("ambiguous_duplicate_column")
    if not panel_sessions:
        reasons.append("empty_panel")
    if binding.get("cohort_id") is not None and binding["cohort_id"] != cohort_id:
        reasons.append("cohort_identity_mismatch")
    if binding.get("benchmark") is not None and binding["benchmark"].strip().upper() != benchmark:
        reasons.append("benchmark_identity_mismatch")
    if binding.get("source_session") is not None and binding["source_session"] != source_day:
        reasons.append("source_session_mismatch")
    if binding.get("price_basis") is not None and binding["price_basis"] != "total_return":
        reasons.append("return_basis_not_qualified")
    reasons = sorted(set(reasons))
    primary = reasons[0] if reasons else None

    # --- windows ------------------------------------------------------------
    windows_out, groups_out = {}, {ticker: {} for ticker in tickers}
    for size in window_sizes:
        key = str(size)
        start_index = end_index - size
        if start_index < 0:
            windows_out[key] = {
                "window_sessions": size,
                "status": "unavailable",
                "start_session": None,
                "end_session": end_day,
                "benchmark_return_pct": None,
                "benchmark_null_reason": "insufficient_reference_history",
                "benchmark_coverage": {"observed_n": 0, "expected_n": size + 1, "ratio": 0.0},
                "null_reason": "insufficient_reference_history",
            }
            for ticker in tickers:
                groups_out[ticker][key] = _window_unavailable_cell(
                    "insufficient_reference_history", size + 1)
            continue
        window_sessions = calendar[start_index:end_index + 1]
        start_day = window_sessions[0]
        expected_n = len(window_sessions)

        benchmark_series = prices.get(benchmark, {})
        b_start, b_start_reason = _window_price(benchmark_series.get(start_day))
        b_end, b_end_reason = _window_price(benchmark_series.get(end_day))
        benchmark_return, benchmark_reason = None, None
        if b_start is None or b_end is None:
            invalid = {b_start_reason, b_end_reason} & {"non_finite_input", "invalid_price"}
            benchmark_reason = "benchmark_invalid" if invalid else "benchmark_missing"
        else:
            benchmark_return, benchmark_reason = _window_return(b_start, b_end)
        # The published benchmark unit is PERCENT, and a FINITE fraction can
        # still overflow that scaling. Finiteness is therefore validated AFTER
        # the scaling: an overflowed benchmark is not publishable, and a
        # relative wealth needs a publishable benchmark -- exactly as it needs
        # a present one.
        benchmark_pct, benchmark_overflowed = _window_pct(benchmark_return)
        if benchmark_overflowed:
            benchmark_reason = "non_finite_input"
            benchmark_return = None
        benchmark_observed = sum(
            1 for day in window_sessions
            if _window_price(benchmark_series.get(day))[0] is not None)

        if reasons:
            # The capture is not qualified as a whole, so NO value is published:
            # every cell is null with the block reason. The observed counts stay
            # truthful -- the prices were seen, the measurement was refused.
            windows_out[key] = {
                "window_sessions": size,
                "status": "unavailable",
                "start_session": start_day,
                "end_session": end_day,
                "benchmark_return_pct": None,
                "benchmark_null_reason": primary,
                "benchmark_coverage": {
                    "observed_n": benchmark_observed,
                    "expected_n": expected_n,
                    "ratio": (round(benchmark_observed / expected_n, _WINDOW_PCT_DECIMALS)
                              if expected_n else 0.0),
                },
                "null_reason": primary,
            }
            for ticker in tickers:
                series = prices.get(ticker, {})
                observed = sum(
                    1 for day in window_sessions
                    if _window_price(series.get(day))[0] is not None)
                groups_out[ticker][key] = _window_cell(
                    None, primary, None, primary, observed, expected_n)
            continue

        measured_here = 0
        complete_here = 0
        for ticker in tickers:
            series = prices.get(ticker, {})
            g_start, g_start_reason = _window_price(series.get(start_day))
            g_end, g_end_reason = _window_price(series.get(end_day))
            absolute, absolute_reason = None, None
            if g_start is None:
                absolute_reason = g_start_reason
            elif g_end is None:
                absolute_reason = g_end_reason
            else:
                absolute, absolute_reason = _window_return(g_start, g_end)
            relative, relative_reason = None, None
            if absolute is None:
                relative_reason = absolute_reason
            elif benchmark_return is None:
                relative_reason = benchmark_reason
            else:
                wealth = relative_wealth(absolute, benchmark_return)
                if isinstance(wealth, Unmeasured):
                    relative_reason = {
                        "non_finite_input": "non_finite_input",
                        "benchmark_wealth_nonpositive": "benchmark_invalid",
                        "group_wealth_negative": "invalid_price",
                    }.get(wealth.reason, "non_finite_input")
                else:
                    relative = float(wealth)
            observed = sum(
                1 for day in window_sessions
                if _window_price(series.get(day))[0] is not None)
            cell = _window_cell(
                *_window_publication(absolute, absolute_reason,
                                     relative, relative_reason),
                observed, expected_n,
            )
            groups_out[ticker][key] = cell
            if cell["status"] != "unavailable":
                measured_here += 1
            if cell["status"] == "available":
                complete_here += 1
        windows_out[key] = {
            "window_sessions": size,
            "status": ("available" if tickers and complete_here == len(tickers)
                       else "partial" if measured_here else "unavailable"),
            "start_session": start_day,
            "end_session": end_day,
            "benchmark_return_pct": benchmark_pct,
            "benchmark_null_reason": benchmark_reason,
            "benchmark_coverage": {
                "observed_n": benchmark_observed,
                "expected_n": expected_n,
                "ratio": (round(benchmark_observed / expected_n, _WINDOW_PCT_DECIMALS)
                          if expected_n else 0.0),
            },
            "null_reason": None,
        }

    # --- groups -------------------------------------------------------------
    groups = []
    for ticker in tickers:
        info = names.get(ticker) or {}
        groups.append({
            "group_id": ticker,
            "name_en": info.get("name"),
            "name_zh": info.get("name_zh"),
            "windows": {key: groups_out[ticker][key] for key in groups_out[ticker]},
        })

    total_cells = len(tickers) * len(window_sizes)
    measured_cells = sum(
        1 for group in groups for cell in group["windows"].values()
        if cell["absolute_return_pct"] is not None or cell["relative_wealth_pct"] is not None)
    complete_cells = sum(
        1 for group in groups for cell in group["windows"].values()
        if cell["absolute_return_pct"] is not None and cell["relative_wealth_pct"] is not None)
    if reasons:
        status = "unavailable"
    elif total_cells and complete_cells == total_cells:
        status = "available"
    elif measured_cells:
        status = "partial"
    else:
        status = "unavailable"

    clocks = binding.get("clocks") or {}
    clocks = {key: (clocks.get(key) if isinstance(clocks.get(key), str) else None)
              for key in _WINDOW_CLOCK_KEYS}

    return {
        "schema": SECTOR_WINDOW_MEASUREMENTS_SCHEMA,
        "status": status,
        "reason": primary,
        "units": "pct",
        "price_basis": "total_return",
        "benchmark": benchmark,
        "cohort_id": cohort_id,
        "population": population_label,
        "source_session": source_day,
        "end_session": end_day,
        "windows_sessions": list(window_sizes),
        "endpoint_definition": _WINDOW_ENDPOINT_DEFINITION,
        "clocks": clocks,
        "source_roots": list(binding.get("source_roots") or []),
        "receipt": binding.get("receipt"),
        "limitations": {
            "availability": ({"status": "unknown", "reason": "owner_availability_clock_not_supplied"}
                             if clocks["availability"] is None else
                             {"status": "supplied", "clock": clocks["availability"]}),
            "publication": ({"status": "unknown", "reason": "owner_publication_clock_not_supplied"}
                            if clocks["publication"] is None else
                            {"status": "supplied", "clock": clocks["publication"]}),
            "corrections": {"status": "unavailable",
                            "reason": "native_revision_selection_not_supplied"},
            "history": ({"status": "unknown", "reason": "owner_history_clock_not_supplied"}
                        if clocks["history"] is None else
                        {"status": "supplied", "clock": clocks["history"]}),
            "freshness": {"status": "unverified",
                          "reason": "owner_freshness_receipt_not_supplied"},
            "point_in_time": {"status": "not_qualified",
                              "reason": "point_in_time_admission_not_supplied"},
        },
        "windows": windows_out,
        "groups": groups,
        "diagnostics": {
            **panel_diagnostics,
            **binding_diagnostics,
            "future_tail_sessions": tail[:_WINDOW_MAX_DIAGNOSTIC_NAMES],
            "expected_columns": len(tickers) + 1,
            "qualification_reasons": reasons,
            "measured_cells": measured_cells,
            "complete_cells": complete_cells,
            "total_cells": total_cells,
            "coverage_note": ("observed_n counts usable observations inside the window; "
                              "an interior gap never moves an endpoint"),
        },
        "authority": {"may_rank": False, "may_gate": False, "may_size": False,
                      "may_trade": False, "may_escalate": False},
    }
