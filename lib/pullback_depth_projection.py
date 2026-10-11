"""Pure additional-loss to total-episode-depth arithmetic for Risk Radar.

This is NOT an observer, forecast model, calibration gate or publisher. Reuse
lib.pullback_observation / the existing market presenter for episode identity,
phase, source clocks and price-basis validation. The caller must separately
qualify forecast quantiles for the same market, benchmark, origin and horizon.
No I/O, clock reads, state changes or capital-policy authority are introduced.

Inputs are positive same-basis prices and ordered additional-loss FRACTIONS,
not percentages or existing risk-intensity scores. Results are nonnegative
loss fractions. A rebound cannot erase a worse trough already experienced.
"""
from __future__ import annotations

from collections.abc import Sequence
from math import isfinite
from numbers import Real


def _finite_real(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f"{name} must be a finite real number, not a boolean")
    try:
        number = float(value)
    except (ValueError, TypeError, OverflowError) as exc:
        raise ValueError(f"{name} must be finite") from exc
    if not isfinite(number):
        raise ValueError(f"{name} must be finite")
    return number


def project_total_drawdown(
    peak: float,
    current: float,
    trough: float,
    additional_loss_fractions: Sequence[float],
) -> tuple[float, ...]:
    """Map sorted future-minimum loss quantiles to total episode loss.

    For peak H, current P, observed trough T and additional loss A:
    D = max(1 - T/H, 1 - (P/H)*(1-A)).

    Including the past trough is essential after a rebound. The monotone
    transform preserves quantile order and can legitimately create ties at
    the observed-worst floor. It grants no statistical validity to the inputs.
    Price above the supplied peak requires the owner to resolve the reference;
    this active/reference-bound helper rejects that case instead of resetting it.
    """
    h = _finite_real(peak, "peak")
    p = _finite_real(current, "current")
    t = _finite_real(trough, "trough")
    if not 0 < t <= p <= h:
        raise ValueError("prices must satisfy 0 < trough <= current <= peak")
    if (not isinstance(additional_loss_fractions, Sequence)
            or isinstance(additional_loss_fractions, (str, bytes))
            or len(additional_loss_fractions) == 0):
        raise ValueError("additional losses must be a nonempty ordered sequence")
    losses = tuple(_finite_real(value, "additional loss")
                   for value in additional_loss_fractions)
    if any(not 0 <= value <= 1 for value in losses):
        raise ValueError("additional loss fractions must be between zero and one")
    if any(right < left for left, right in zip(losses, losses[1:])):
        raise ValueError("additional loss quantiles must be nondecreasing")
    worst = 1 - t / h
    return tuple(max(worst, 1 - (p / h) * (1 - loss)) for loss in losses)
