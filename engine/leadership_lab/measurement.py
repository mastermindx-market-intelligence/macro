"""Pure, explicitly uncalibrated Leadership Lab measurements.

No readers, stores, residual models, ranking policies or trading authority live here.
Caller-supplied values are structurally checked, not source-owner attested.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import date, datetime, timezone
import math
from numbers import Real


def finite_number(value: object) -> float | None:
    """Numeric source values only: Boolean, string, NaN and infinity are missing."""
    if isinstance(value, bool) or not isinstance(value, Real):
        return None
    number = float(value)
    return number if math.isfinite(number) else None


def session_date(value: object) -> str:
    if not isinstance(value, str):
        raise ValueError("session must be an ISO date")
    parsed = date.fromisoformat(value)
    if parsed.isoformat() != value:
        raise ValueError("session must be YYYY-MM-DD")
    return value


def _clock(value: object) -> datetime:
    if not isinstance(value, str):
        raise ValueError("clock must be a timezone-aware ISO timestamp")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("clock must carry timezone")
    return parsed.astimezone(timezone.utc)


def benchmark_window(
    stock: Mapping[str, object], benchmark: Mapping[str, object], *,
    sessions: Sequence[str], through: str, lookback: int, skip: int = 0,
) -> dict:
    """Exact endpoint relative wealth on an owner-supplied session calendar.

    A 252/21 window runs from through-252 to through-21 (231 returns).
    Require observations through the reference session even when recent returns
    are skipped: stale securities cannot borrow the snapshot-wide source date.
    This does not attest the calendar, price adjustment basis or PIT availability.
    """
    if (type(lookback) is not int or type(skip) is not int
            or lookback <= 0 or not 0 <= skip < lookback):
        raise ValueError("require integer lookback > skip >= 0")
    dates = [session_date(d) for d in sessions]
    if dates != sorted(set(dates)) or session_date(through) not in dates:
        raise ValueError("calendar must be unique, ascending and include through")
    end_index = dates.index(through)
    result = {
        "method": "leadership_lab.relative_wealth.v1",
        "status": "UNAVAILABLE", "through_session": through,
        "start_session": None, "end_session": None,
        "formation_sessions": lookback - skip, "reasons": [],
        "stock_return": None, "benchmark_return": None,
        "active_return_pp": None, "relative_wealth_return": None,
        "price_basis": "CALLER_SUPPLIED_UNATTESTED",
        "forecast_probability": None,
    }
    if end_index < lookback:
        result["reasons"] = ["INSUFFICIENT_HISTORY"]
        return result
    required = dates[end_index - lookback:end_index + 1]
    result.update(start_session=required[0], end_session=dates[end_index - skip])
    for label, source in (("STOCK", stock), ("BENCHMARK", benchmark)):
        if not isinstance(source, Mapping):
            result["reasons"].append(f"INVALID_{label}_SOURCE")
            continue
        if any(d not in source for d in required):
            result["reasons"].append(f"MISSING_{label}_SESSION")
        elif any((n := finite_number(source[d])) is None or n <= 0 for d in required):
            result["reasons"].append(f"INVALID_{label}_PRICE")
    if result["reasons"]:
        return result
    first, last = result["start_session"], result["end_session"]
    stock_wealth = float(stock[last]) / float(stock[first])
    benchmark_wealth = float(benchmark[last]) / float(benchmark[first])
    if benchmark_wealth <= 0 or not all(math.isfinite(x) and x > 0 for x in (stock_wealth, benchmark_wealth)):
        result["reasons"] = ["NONFINITE_RESULT"]
        return result
    relative = stock_wealth / benchmark_wealth - 1
    active_pp = (stock_wealth - benchmark_wealth) * 100
    if not all(math.isfinite(x) for x in (relative, active_pp)):
        result["reasons"] = ["NONFINITE_RESULT"]
        return result
    result.update(status="MEASURED_UNATTESTED", stock_return=stock_wealth - 1,
                  benchmark_return=benchmark_wealth - 1, active_return_pp=active_pp,
                  relative_wealth_return=relative)
    return result


def percentile_ranks(
    values: Mapping[str, object], *, eligible: Sequence[str],
    min_observed: int = 20, min_coverage: float = .8,
) -> dict:
    """Descriptive 1–99 percentiles; never a forecast or an IBD replication."""
    if (type(min_observed) is not int or min_observed < 2
            or finite_number(min_coverage) is None or not 0 <= min_coverage <= 1):
        raise ValueError("invalid coverage policy")
    names = list(eligible)
    if any(not isinstance(n, str) or not n for n in names) or len(names) != len(set(names)):
        raise ValueError("eligible identities must be nonempty and unique")
    names.sort()
    observed = {n: finite_number(values.get(n)) for n in names}
    observed = {n: v for n, v in observed.items() if v is not None}
    count, total = len(observed), len(names)
    coverage = count / total if total else 0.
    result = {"method": "leadership_lab.descriptive_percentile.v1", "status": "UNAVAILABLE",
              "eligible_count": total, "observed_count": count, "coverage": coverage,
              "ranks": dict.fromkeys(names), "forecast_probability": None, "reasons": []}
    if count < min_observed:
        result["reasons"].append("THIN_POPULATION")
    if coverage < min_coverage:
        result["reasons"].append("INSUFFICIENT_COVERAGE")
    if len(set(observed.values())) <= 1:
        result["reasons"].append("NO_DISPERSION")
    if result["reasons"]:
        return result
    ordered = sorted(observed, key=lambda n: (observed[n], n))
    start = 0
    while start < count:
        stop = start + 1
        while stop < count and observed[ordered[stop]] == observed[ordered[start]]:
            stop += 1
        average_zero_rank = (start + stop - 1) / 2
        for name in ordered[start:stop]:
            result["ranks"][name] = 1 + 98 * average_zero_rank / (count - 1)
        start = stop
    result["status"] = "DESCRIPTIVE_ONLY"
    return result


def earnings_multiple_bridge(start: Mapping, end: Mapping, *, cutoff: str) -> dict:
    """Arithmetic attribution on comparable, positive-EPS illustrative inputs.

    This neither authenticates source references nor identifies economic causation.
    A rolling NTM label cannot establish a common fixed forecast period.
    """
    numeric_fields = ("price_return", "eps_change", "multiple_change", "interaction",
                      "start_multiple", "end_multiple", "eps_log_contribution",
                      "multiple_log_contribution")
    result = {"method": "leadership_lab.earnings_multiple_bridge.v1",
              "status": "UNAVAILABLE", "reasons": [], "forecast_probability": None,
              "causal_claim": False, "source_qualification": "CALLER_SUPPLIED_UNATTESTED",
              **dict.fromkeys(numeric_fields)}
    try:
        limit = _clock(cutoff)
        clocks = []
        for point in (start, end):
            if not isinstance(point, Mapping):
                raise ValueError("point must be a mapping")
            for field in ("price", "eps"):
                value = finite_number(point.get(field))
                if value is None or value <= 0:
                    raise ValueError(f"nonpositive or invalid {field}")
            ref = point.get("source_ref")
            if not isinstance(ref, str) or not ref.strip():
                raise ValueError("source reference missing")
            known, observed = _clock(point.get("known_at")), _clock(point.get("observed_at"))
            if not known <= observed <= limit:
                raise ValueError("evidence clocks invalid or future")
            clocks.append((known, observed))
        if clocks[1][0] < clocks[0][0] or clocks[1][1] < clocks[0][1]:
            raise ValueError("end evidence predates start")
        for field in ("forecast_period", "currency", "accounting_basis", "share_basis"):
            value = start.get(field)
            if not isinstance(value, str) or not value.strip() or value != end.get(field):
                raise ValueError(f"incompatible or missing {field}")
        if "ntm" in start["forecast_period"].lower() or "rolling" in start["forecast_period"].lower():
            raise ValueError("fixed forecast endpoint required; rolling NTM is not a revision")
        p0, p1, e0, e1 = (float(start["price"]), float(end["price"]),
                           float(start["eps"]), float(end["eps"]))
        m0, m1 = p0 / e0, p1 / e1
        price_change, eps_change, multiple_change = p1 / p0 - 1, e1 / e0 - 1, m1 / m0 - 1
        output = dict(price_return=price_change, eps_change=eps_change,
                      multiple_change=multiple_change, interaction=eps_change * multiple_change,
                      start_multiple=m0, end_multiple=m1,
                      eps_log_contribution=math.log(e1 / e0),
                      multiple_log_contribution=math.log(m1 / m0))
        if not all(math.isfinite(value) for value in output.values()):
            raise ValueError("nonfinite arithmetic")
    except (ValueError, TypeError, KeyError, ZeroDivisionError, OverflowError) as exc:
        result["reasons"] = [str(exc)]
        return result
    result.update(output, status="ILLUSTRATIVE_CALCULATION")
    return result
