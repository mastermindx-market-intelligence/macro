from __future__ import annotations

"""Hermetic P08 engineering composition, NOT a real-source admission interface.

Only tests/research may import this module. Typed fixtures restrict accidental
payload adoption; they do not authenticate synthetic provenance. There is no
parser, CLI, loader, registration, or production caller. Q02's INSUFFICIENT_DATA
verdict, frozen numerics and real-source adoption hold remain unchanged.
"""

import math
from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping

from engine import options_american_exercise as reference

RESEARCH_ONLY = True
VERSION = "p08-synthetic-composition/v1"
MAX_MEMBERS = 4
MAX_AXIS = 4
MAX_QUALIFICATIONS = 16
METRICS = ("gamma", "vanna", "charm")
UNITS = MappingProxyType({
    "gamma": "USD_delta_change_per_1_percent_spot",
    "vanna": "USD_delta_change_per_1_vol_point",
    "charm": "USD_delta_change_per_elapsed_calendar_day_365",
})


@dataclass(frozen=True, slots=True)
class SyntheticPut:
    """Declared American put, share deliverable, no cash dividends, q=0.

    remaining_years is continuous economic time, not a calendar/date inference.
    sigma is a conditional parameter, never a fitted or source-certified IV.
    position_sign is an explicit assumed inventory convention, not observed flow.
    """

    strike: float
    remaining_years: float
    sigma: float
    rate: float
    multiplier: float
    open_interest: int
    position_sign: int
    continuous_yield: float
    discrete_dividends: tuple[()]


@dataclass(frozen=True, slots=True)
class SyntheticCase:
    members: tuple[SyntheticPut, ...]
    reference_spot: float
    spots: tuple[float, ...]
    elapsed_years: tuple[float, ...]


@dataclass(frozen=True, slots=True)
class MemberResult:
    member_index: int
    remaining_years: float
    zero_oi: bool
    qualification: reference.Qualification | None


@dataclass(frozen=True, slots=True)
class Total:
    value: float | None
    required_members: int
    converged_members: int
    zero_oi_members: int
    reason: str | None


@dataclass(frozen=True, slots=True)
class HedgeChange:
    anchor_shares: Total
    endpoint_shares: Total
    change_shares: float | None
    reference_notional_usd: float | None


@dataclass(frozen=True, slots=True)
class Cell:
    spot: float
    elapsed_years: float
    members: tuple[MemberResult, ...]
    exposures: Mapping[str, Total]
    hedge: HedgeChange


@dataclass(frozen=True, slots=True)
class SyntheticSurface:
    version: str
    baseline: tuple[MemberResult, ...]
    cells: tuple[Cell, ...]
    grid_levels: tuple[int, ...]


def _number(value: object, name: str, lo: float, hi: float, *, strict_lo=False) -> None:
    if (type(value) not in (int, float) or not math.isfinite(value)
            or value > hi or (value <= lo if strict_lo else value < lo)):
        raise ValueError(f"invalid {name}")


def _validate(case: SyntheticCase) -> None:
    if type(case) is not SyntheticCase:
        raise TypeError("explicit SyntheticCase required; source payloads are not accepted")
    if type(case.members) is not tuple or not 1 <= len(case.members) <= MAX_MEMBERS:
        raise ValueError("bounded nonempty member tuple required")
    _number(case.reference_spot, "reference_spot", 0, reference.PRICE_MAX, strict_lo=True)
    for name, axis in (("spots", case.spots), ("elapsed_years", case.elapsed_years)):
        if type(axis) is not tuple or not 1 <= len(axis) <= MAX_AXIS:
            raise ValueError(f"bounded nonempty {name} tuple required")
        for x in axis:
            _number(x, name, 0, reference.PRICE_MAX if name == "spots" else reference.T_MAX_YEARS,
                    strict_lo=name == "spots")
        if len(set(axis)) != len(axis):
            raise ValueError(f"duplicate {name}")
    if len(case.members) * (1 + len(case.spots) * len(case.elapsed_years)) > MAX_QUALIFICATIONS:
        raise ValueError("qualification work bound exceeded")
    for member in case.members:
        if type(member) is not SyntheticPut:
            raise TypeError("explicit SyntheticPut required; source payloads are not accepted")
        _number(member.strike, "strike", 0, reference.PRICE_MAX, strict_lo=True)
        _number(member.remaining_years, "remaining_years", 0, reference.T_MAX_YEARS, strict_lo=True)
        _number(member.sigma, "sigma", *reference.SIGMA_BOUNDS)
        _number(member.rate, "rate", 0, reference.RATE_BOUNDS[1])
        _number(member.multiplier, "multiplier", 0, 1e6, strict_lo=True)
        if type(member.open_interest) is not int or not 0 <= member.open_interest <= 10**9:
            raise ValueError("invalid open_interest")
        if type(member.position_sign) is not int or member.position_sign not in (-1, 1):
            raise ValueError("explicit position_sign -1 or +1 required")
        _number(member.continuous_yield, "continuous_yield", 0, 0)
        if type(member.discrete_dividends) is not tuple or member.discrete_dividends != ():
            raise ValueError("only declared no-discrete-dividend fixtures supported")
        if any(t >= member.remaining_years for t in case.elapsed_years):
            raise ValueError("horizon reaches economic expiry; no member may be dropped")


def _finite_sum(values: list[float]) -> float | None:
    # Same dollar-unit aggregation semantics as options_scenario_surface; unlike
    # its legacy finite mask, admission below never removes an unavailable member.
    try:
        value = math.fsum(values)
    except (OverflowError, ValueError):
        return None
    return value if math.isfinite(value) else None


def _total(case: SyntheticCase, reports: tuple[MemberResult, ...], quantity: str,
           factor: float) -> Total:
    values: list[float] = []
    required = converged = zero = 0
    for member, result in zip(case.members, reports, strict=True):
        if result.zero_oi:
            zero += 1
            continue
        required += 1
        ref = result.qualification.quantities[quantity]
        if ref.status != reference.CONVERGED or ref.value is None or not math.isfinite(ref.value):
            continue
        converged += 1
        values.append(member.position_sign * member.open_interest * member.multiplier * ref.value * factor)
    if converged != required:
        return Total(None, required, converged, zero, "member_quantity_not_converged")
    value = _finite_sum(values)
    return Total(value, required, converged, zero, None if value is not None else "nonfinite_aggregate")


def compose_synthetic(case: SyntheticCase) -> SyntheticSurface:
    """Compose fixed-inventory scenario cells. No real-source or forecast claim.

    Every member is validated before any solve, including zero OI. A zero-OI
    member contributes exactly zero without asserting an unavailable Greek was
    converged. Solver exceptions propagate; no partial surface is returned.
    """
    _validate(case)
    caches: list[dict[tuple[float, float], reference.Qualification]] = [{} for _ in case.members]

    def evaluate(spot: float, elapsed: float) -> tuple[MemberResult, ...]:
        results = []
        for i, member in enumerate(case.members):
            remaining = member.remaining_years - elapsed
            if member.open_interest == 0:
                results.append(MemberResult(i, remaining, True, None))
                continue
            key = (spot, remaining)
            if key not in caches[i]:
                caches[i][key] = reference.qualify_fd(
                    spot, member.strike, remaining, member.sigma, member.rate, 0.0,
                    is_call=False, american=True, dividends=(), levels=reference.GRID_LEVELS,
                )
            results.append(MemberResult(i, remaining, False, caches[i][key]))
        return tuple(results)

    baseline = evaluate(case.reference_spot, 0.0)
    anchor = _total(case, baseline, "delta", -1.0)
    cells = []
    for elapsed in case.elapsed_years:
        for spot in case.spots:
            reports = evaluate(spot, elapsed)
            exposures = MappingProxyType({
                "gamma": _total(case, reports, "gamma", spot * spot * 0.01),
                "vanna": _total(case, reports, "vanna", spot * 0.01),
                "charm": _total(case, reports, "charm", spot / 365.0),
            })
            endpoint = _total(case, reports, "delta", -1.0)
            change = (_finite_sum([endpoint.value, -anchor.value])
                      if endpoint.value is not None and anchor.value is not None else None)
            notional = _finite_sum([case.reference_spot * change]) if change is not None else None
            cells.append(Cell(spot, elapsed, reports, exposures,
                              HedgeChange(anchor, endpoint, change, notional)))
    return SyntheticSurface(VERSION, baseline, tuple(cells), tuple(reference.GRID_LEVELS))
