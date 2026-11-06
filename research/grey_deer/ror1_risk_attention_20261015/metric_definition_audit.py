"""Rigorously distinguish false-positive rate from false-discovery rate.

Given a day-level alert fraction A/N, precision TP/A, and an upper bound
on event prevalence P/N (on the SAME evaluation population), derive bounds
on FPR=FP/(FP+TN). This is arithmetic only; no market model is fitted.
"""
from __future__ import annotations

import math


def day_level_false_rate_bounds(
    alert_rate: float, precision: float, event_prevalence_upper: float
) -> dict[str, float]:
    a, p, u = float(alert_rate), float(precision), float(event_prevalence_upper)
    if not all(math.isfinite(v) for v in (a, p, u)):
        raise ValueError("Nonfinite metric")
    if not (0.0 <= a <= 1.0 and 0.0 <= p <= 1.0 and 0.0 <= u < 1.0):
        raise ValueError("Invalid rate or event upper bound")
    if a * p > u:
        raise ValueError("Observed true-alert share exceeds event-prevalence bound")
    false_alert_fraction = a * (1.0 - p)
    # FPR=FP / non-event days. Unknown event share e is in [0,u].
    # Thus FPR in [FP/N, FP/(N*(1-u))]. These are loose but valid bounds.
    return {
        "alert_rate": a,
        "precision": p,
        "false_alerts_per_day": false_alert_fraction,
        "false_discovery_rate": 1.0 - p,
        "fpr_lower_bound": false_alert_fraction,
        "fpr_upper_bound": false_alert_fraction / (1.0 - u),
        "event_prevalence_upper": u,
    }
