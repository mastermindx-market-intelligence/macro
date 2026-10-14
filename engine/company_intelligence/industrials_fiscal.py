"""Stated fiscal period end for an Industrials cell.

A later matcher may pass the same ``tolerance_days`` it uses to decide
whether two dates are one event. This function does not apply that window:
the stated cell end is the end the cell already carries.
"""
from __future__ import annotations

from datetime import date


def stated_period_end(stated_end: date, *, tolerance_days: int) -> date:
    """Return ``stated_end`` unchanged.

    ``tolerance_days`` is accepted and checked, then ignored. A stated 3 July
    stays 3 July.
    """
    if type(stated_end) is not date:
        raise TypeError(f"stated_end must be a date, not {type(stated_end).__name__}")
    if isinstance(tolerance_days, bool) or not isinstance(tolerance_days, int):
        raise TypeError(
            f"tolerance_days must be an int, not {type(tolerance_days).__name__}"
        )
    if tolerance_days < 0:
        raise ValueError(f"tolerance_days must be >= 0, got {tolerance_days}")
    return stated_end
