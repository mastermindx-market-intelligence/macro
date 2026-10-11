#!/usr/bin/env python3
"""Observable shape classifier; never a causal corporate-action diagnosis."""
import math
import numpy as np

from contract import EvidenceError, finite_positive

OHLC = ("open", "high", "low", "close")


def classify_bar(old, new):
    if not isinstance(old, dict) or not isinstance(new, dict) or any(old.get(k) is None or new.get(k) is None for k in OHLC):
        return "incomplete_ohlc"
    try:
        x = np.array([finite_positive(old[k]) for k in OHLC])
        y = np.array([finite_positive(new[k]) for k in OHLC])
    except EvidenceError:
        return "invalid_ohlc"
    changed = [k for k, a, b in zip(OHLC, x, y) if abs(a - b) > max(abs(a), abs(b), 1.0) * 1e-6]
    if not changed:
        return "identical_ohlc"
    if changed == ["open"]:
        return "open_only_rewrite"
    ratios = y / x
    if all(math.isfinite(float(r)) and r > 0 for r in ratios) and max(ratios) - min(ratios) <= 1e-5 * max(abs(r) for r in ratios):
        return "uniform_ohlc_scale"
    if np.ptp(x) > 1e-6:
        a, b = np.polyfit(x, y, 1)
        if a > 0 and np.max(abs(y - (a * x + b))) <= max(np.max(abs(y)), 1) * 1e-5:
            return "uniform_ohlc_affine"
    return "mixed_field_revision"
