"""Typed current liquidity state from a window of PBOC open-market days.

Pure and IO-free. Display and context only: nothing here reads a store, a
collector, or the network. An announced zero stays a zero. A day that was not
observed stays missing, and a quiet stretch is called ample only when the
money-market rate agrees.
"""
from __future__ import annotations

import datetime
from dataclasses import dataclass

SCHEMA = "china_pboc_liquidity.v1"

_MIN_OBSERVED_DAYS = 3

# Display copy. Plain words only: these strings are what a reader sees.
LABELS: dict[str, dict[str, str]] = {
    "insufficient_data": {
        "en": "Not enough fresh observations to read liquidity",
        "zh": "观测不足，无法判断当前资金状态",
    },
    "zero_op_ample": {
        "en": "Quiet: no operations, money is ample",
        "zh": "无操作：资金充裕",
    },
    "zero_op_tight": {
        "en": "Quiet: no operations, money is tight",
        "zh": "无操作：资金偏紧",
    },
    "rollover": {
        "en": "Roughly balanced: new money matches what is coming due",
        "zh": "大致平衡：新投放与到期基本相当",
    },
    "net_support": {
        "en": "Net support: more money is added than comes due",
        "zh": "净投放：新增资金多于到期",
    },
    "net_drain": {
        "en": "Net drain: more money comes due than is added",
        "zh": "净回笼：到期资金多于新增",
    },
}


class FutureDatedInput(ValueError):
    """An open-market day is dated after the read's as-of date."""


@dataclass(frozen=True)
class OmoDay:
    date: datetime.date
    injection_cny_bn: float | None
    maturity_cny_bn: float | None
    op_count: int | None

    def __post_init__(self) -> None:
        for name, value in (
            ("injection_cny_bn", self.injection_cny_bn),
            ("maturity_cny_bn", self.maturity_cny_bn),
            ("op_count", self.op_count),
        ):
            if value is not None and value < 0:
                raise ValueError(f"{name} must be >= 0, got {value}")
        if (
            self.op_count == 0
            and self.injection_cny_bn is not None
            and self.injection_cny_bn > 0
        ):
            raise ValueError(
                "inconsistent bulletin: op_count is 0 but injection_cny_bn is positive"
            )


@dataclass(frozen=True)
class LiquidityInputs:
    asof: datetime.date
    window: tuple[OmoDay, ...]
    mlf_net_cny_bn: float | None
    fr007_pct: float | None
    policy_rate_7d_pct: float | None
    source: str


@dataclass(frozen=True)
class LiquidityRead:
    schema: str
    asof: datetime.date
    state: str
    net_cny_bn: float | None
    gross_injection_cny_bn: float | None
    gross_maturity_cny_bn: float | None
    spread_bp: float | None
    stale: bool
    days_observed: int
    days_missing: int
    reasons: tuple[str, ...]
    source: str

    def to_dict(self) -> dict[str, object]:
        """JSON-safe primitives. Dates are ISO strings. Reasons are a list."""
        return {
            "schema": self.schema,
            "asof": self.asof.isoformat(),
            "state": self.state,
            "net_cny_bn": self.net_cny_bn,
            "gross_injection_cny_bn": self.gross_injection_cny_bn,
            "gross_maturity_cny_bn": self.gross_maturity_cny_bn,
            "spread_bp": self.spread_bp,
            "stale": self.stale,
            "days_observed": self.days_observed,
            "days_missing": self.days_missing,
            "reasons": list(self.reasons),
            "source": self.source,
        }


def _observed(day: OmoDay) -> bool:
    return (
        day.injection_cny_bn is not None
        and day.maturity_cny_bn is not None
        and day.op_count is not None
    )


def _zero_op(day: OmoDay) -> bool:
    return day.op_count == 0 and day.injection_cny_bn == 0


def classify_liquidity(
    inputs: LiquidityInputs,
    *,
    window_days: int = 5,
    tight_spread_bp: float = 15.0,
    rollover_abs_cny_bn: float = 5.0,
    rollover_rel: float = 0.10,
    stale_after_days: int = 4,
) -> LiquidityRead:
    """Classify the current liquidity state from a bulletin window.

    Amounts are whatever unit the caller already used. This function does not
    rescale them. ``window_days == 0`` keeps no days, because ``seq[-0:]``
    would otherwise keep the whole window. A negative count raises ValueError.
    """
    if window_days < 0:
        raise ValueError("window_days must be non-negative")

    for day in inputs.window:
        if day.date > inputs.asof:
            raise FutureDatedInput(
                f"open-market day {day.date.isoformat()} is after asof "
                f"{inputs.asof.isoformat()}"
            )
    seen: set[datetime.date] = set()
    for day in inputs.window:
        if day.date in seen:
            raise ValueError(f"duplicate open-market date {day.date.isoformat()}")
        seen.add(day.date)

    ordered = sorted(inputs.window, key=lambda day: day.date)
    # A non-positive count must keep nothing. seq[-0:] is the whole sequence.
    selected = ordered[-window_days:] if window_days else ()

    if not selected:
        stale = True
    else:
        latest = selected[-1].date
        stale = (inputs.asof - latest).days > stale_after_days

    observed = tuple(day for day in selected if _observed(day))
    days_observed = len(observed)
    days_missing = len(selected) - days_observed

    gross_injection = float(sum(day.injection_cny_bn or 0.0 for day in observed))
    gross_maturity = float(sum(day.maturity_cny_bn or 0.0 for day in observed))

    reasons: list[str] = []
    if stale:
        reasons.append("stale")
    if days_observed < _MIN_OBSERVED_DAYS:
        reasons.append("fewer_than_3_observed")
    if days_missing:
        reasons.append("partial_window")

    if inputs.mlf_net_cny_bn is None:
        mlf_net = 0.0
        reasons.append("mlf_unknown")
    else:
        mlf_net = float(inputs.mlf_net_cny_bn)
    net = gross_injection - gross_maturity + mlf_net

    if inputs.fr007_pct is not None and inputs.policy_rate_7d_pct is not None:
        spread_bp: float | None = float(
            (inputs.fr007_pct - inputs.policy_rate_7d_pct) * 100.0
        )
    else:
        spread_bp = None
        reasons.append("spread_unknown")

    # Announced zeros are not a drain. Maturities on those days stay inside
    # `net`, and the state follows the money-market spread.
    quiet = days_observed > 0 and all(_zero_op(day) for day in observed)
    blocked = stale or days_observed < _MIN_OBSERVED_DAYS
    if blocked:
        state = "insufficient_data"
    elif quiet:
        if spread_bp is None:
            state = "insufficient_data"
            reasons.append("zero_op_spread_unknown")
        elif spread_bp <= tight_spread_bp:
            state = "zero_op_ample"
        else:
            state = "zero_op_tight"
    else:
        tolerance = max(
            float(rollover_abs_cny_bn), float(rollover_rel) * gross_maturity
        )
        if abs(net) <= tolerance:
            state = "rollover"
        elif net > tolerance:
            state = "net_support"
        else:
            state = "net_drain"

    return LiquidityRead(
        schema=SCHEMA,
        asof=inputs.asof,
        state=state,
        net_cny_bn=net,
        gross_injection_cny_bn=gross_injection,
        gross_maturity_cny_bn=gross_maturity,
        spread_bp=spread_bp,
        stale=stale,
        days_observed=days_observed,
        days_missing=days_missing,
        reasons=tuple(reasons),
        source=inputs.source,
    )
