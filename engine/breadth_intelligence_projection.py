"""Stateless read-only breadth projection over the existing live-breadth counter.

Caller MUST supply source-admitted, as-known GICS or theme-graph cohorts. This
module does not own prices, classifications, licences, history, polling, scores
or publications. It refuses stale/missing upstream and never mutates inputs.
"""
from __future__ import annotations

import math
from collections.abc import Callable, Mapping, Sequence
from datetime import datetime, timezone
from typing import Any

SCHEMA = "breadth_intelligence.group_projection.v1"
SUPPORTED_KINDS = frozenset(("sector", "industry", "subindustry", "curated_theme", "micro_theme"))
SUPPORTED_SESSIONS = frozenset(("rth", "pre", "post", "closed"))
RIGHTS = frozenset(("display_allowed", "not_authorized", "unknown"))
DEFAULT_COVERAGE_FLOOR = 90.0
DEFAULT_MIN_OBSERVED = 5


def _stamp(name: str, raw: Any) -> datetime:
    if not isinstance(raw, str) or not raw:
        raise ValueError(f"{name} requires an aware timestamp")
    try:
        result = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{name} invalid ISO timestamp") from exc
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError(f"{name} must include an explicit UTC offset")
    return result.astimezone(timezone.utc)


def _finite_positive(raw: Any) -> bool:
    return (isinstance(raw, (int, float)) and not isinstance(raw, bool)
            and math.isfinite(raw) and raw > 0)


def _finite(raw: Any) -> bool:
    return (isinstance(raw, (int, float)) and not isinstance(raw, bool)
            and math.isfinite(raw))


def _blank(group_id: str, kind: str, name: str, *, reason: str, eligible_n: int | None = None,
           observed_n: int | None = None, source: str | None = None,
           membership_revision: str | None = None, belief_at: str | None = None) -> dict[str, Any]:
    """No numeric reading when source/membership/rights/coverage is unqualified."""
    return {
        "id": group_id, "kind": kind, "name": name,
        "source": source, "membership_revision": membership_revision,
        "membership_belief_at": belief_at, "eligible_n": eligible_n,
        "observed_n": observed_n,
        "coverage_pct": (round(100.0 * observed_n / eligible_n, 3)
                         if eligible_n and observed_n is not None else None),
        "state": "unmeasured", "unmeasured_reason": reason,
        "adv": None, "dec": None, "unch": None,
        "positive_pct_of_observed": None,
        "adv_pct_excluding_unchanged": None,
        "pct_above_50": None, "pct_above_200": None,
        "new_highs": None, "new_lows": None,
        "logical_identification_bounds_pct": None,
        "aggregable_with_other_groups": False,
    }


def project_groups(
    *,
    groups: Sequence[Mapping[str, Any]],
    last_by_symbol: Mapping[str, float],
    thresholds_by_symbol: Mapping[str, Mapping[str, float | None]],
    source_asof: str,
    known_at: str,
    session: str,
    upstream_usable: bool,
    minimum_coverage_pct: float = DEFAULT_COVERAGE_FLOOR,
    minimum_observed: int = DEFAULT_MIN_OBSERVED,
    aggregate_tier: Callable[..., dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Project a single source-clock snapshot onto as-known groups.

    Group input comes from an existing GICS/Theme Graph rights+membership owner;
    this function never manufactures company-to-theme edges. Missing is never
    counted as unchanged, and overlapping groups are never added together.
    positive_pct_of_observed includes unchanged names in its denominator; the
    incumbent adv_pct_excluding_unchanged excludes them. Bounds are logical
    identification intervals, not statistical confidence intervals.
    """
    source_time = _stamp("source_asof", source_asof)
    built_time = _stamp("known_at", known_at)
    if built_time < source_time:
        raise ValueError("known_at cannot precede source_asof")
    if session not in SUPPORTED_SESSIONS:
        raise ValueError("unsupported session")
    if type(upstream_usable) is not bool:
        raise ValueError("upstream_usable must be boolean")
    if not _finite(minimum_coverage_pct) or not 0 < minimum_coverage_pct <= 100:
        raise ValueError("invalid coverage floor")
    if type(minimum_observed) is not int or minimum_observed < 1:
        raise ValueError("invalid minimum_observed")
    if aggregate_tier is None:
        from engine.live_breadth import compute_tier
        aggregate_tier = compute_tier
    seen_ids: set[str] = set()
    rows: list[dict[str, Any]] = []
    for group in groups:
        group_id, kind, name = group.get("id"), group.get("kind"), group.get("name")
        if not all(isinstance(v, str) and v for v in (group_id, name)):
            raise ValueError("group id and name must be nonempty")
        if kind not in SUPPORTED_KINDS:
            raise ValueError(f"unsupported group kind for {group_id}")
        if group_id in seen_ids:
            raise ValueError(f"duplicate group id: {group_id}")
        seen_ids.add(group_id)
        rights = group.get("rights_status", "unknown")
        if rights not in RIGHTS:
            raise ValueError("unknown rights_status contract")
        raw_members = group.get("members")
        if (not isinstance(raw_members, (tuple, list))
                or any(not isinstance(m, str) or not m for m in raw_members)):
            raise ValueError("members must be a sequence of canonical symbols")
        members = tuple(raw_members)
        if len(members) != len(set(members)):
            raise ValueError(f"duplicate member in group: {group_id}")
        N = len(members)
        src = group.get("source")
        rev = group.get("membership_revision")
        belief = group.get("membership_belief_at")
        kw = dict(source=src, membership_revision=rev, belief_at=belief)
        if rights != "display_allowed":
            # Display rights refusal must not leak group-size statistics.
            rows.append(_blank(group_id, kind, name, reason="rights_" + rights, **kw))
            continue
        if not rev or not belief or not src:
            rows.append(_blank(group_id, kind, name, reason="unbound_membership", **kw))
            continue
        if _stamp("membership_belief_at", belief) > source_time:
            rows.append(_blank(group_id, kind, name, reason="future_membership", **kw))
            continue
        if not upstream_usable or session == "closed":
            rows.append(_blank(group_id, kind, name, reason="upstream_unusable", **kw))
            continue
        if N == 0:
            rows.append(_blank(group_id, kind, name, reason="empty_cohort", eligible_n=0, observed_n=0, **kw))
            continue
        valid_symbols = [m for m in members
                         if _finite_positive(last_by_symbol.get(m))
                         and _finite_positive(thresholds_by_symbol.get(m, {}).get("prev_close"))]
        n = len(valid_symbols)
        if n < minimum_observed or 100*n/N < minimum_coverage_pct:
            rows.append(_blank(group_id, kind, name, reason="coverage_insufficient",
                               eligible_n=N, observed_n=n, **kw))
            continue
        levels = {m: dict(thresholds_by_symbol[m]) for m in valid_symbols}
        prices = {m: last_by_symbol[m] for m in valid_symbols}
        counter = aggregate_tier(group_id, group_id, {"en": name, "zh": name}, levels, prices)
        adv, dec, unch = (counter[k] for k in ("adv", "dec", "unch"))
        if (any(type(x) is not int or x < 0 for x in (adv, dec, unch))
                or adv + dec + unch != n or counter["n"] != n):
            raise ValueError("incumbent breadth counter inconsistent with admitted group")
        bounds = [round(100*adv/N, 3), round(100*(adv+N-n)/N, 3)]
        rows.append({
            "id": group_id, "kind": kind, "name": name, "source": src,
            "membership_revision": rev, "membership_belief_at": belief,
            "eligible_n": N, "observed_n": n, "coverage_pct": round(100*n/N, 3),
            "state": "measured", "unmeasured_reason": None,
            "adv": adv, "dec": dec, "unch": unch,
            "positive_pct_of_observed": round(100*adv/n, 3),
            "adv_pct_excluding_unchanged": counter["adv_pct"],
            "pct_above_50": counter["pa50"],
            "pct_above_200": counter["pa200"],
            "new_highs": counter["nh"], "new_lows": counter["nl"],
            "logical_identification_bounds_pct": bounds,
            "aggregable_with_other_groups": False,
        })
    return {
        "schema": SCHEMA,
        "authority": "display_only",
        "source_asof": source_asof, "known_at": known_at, "session": session,
        "upstream_usable": upstream_usable, "cohort_composition": "upstream_as_known_only",
        "membership_semantics": "bitemporal_sourced_not_derived_company_theme_edge",
        "minimum_coverage_pct": minimum_coverage_pct,
        "groups": rows,
    }
