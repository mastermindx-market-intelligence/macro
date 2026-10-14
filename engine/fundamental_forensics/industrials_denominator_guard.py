"""Refuse a company-revenue share presented as segment mix (IND-R206).

A ``revenue_share_pct`` cell is a legal operand only when
``business_dimensions`` carries one of the two ``(segment, denominator)``
pairs the synthetic fixture already uses. Any other pair, or a missing
key, returns ``mislabeled_denominator``. Any other metric is outside this
guard. This module does not derive a number.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

# Exactly the two pairs in tests/fixtures/industrials_result_cash/same_number_two_headers.json.
_AGREED_PAIRS = frozenset({
    ("group", "group_revenue"),
    ("engineering", "engineering_revenue"),
})

_SHARE_METRIC = "revenue_share_pct"
_MISLABELED = "mislabeled_denominator"


def denominator_refusal(cell: Mapping[str, Any]) -> str | None:
    """Return ``mislabeled_denominator`` when a share cell is not an agreed pair.

    ``None`` means the metric is not ``revenue_share_pct``, or the cell is one
    of the two agreed pairs. ``industrials_result_cash.qualify_operands``
    calls this guard for every parsed operand — unconditionally, never
    conditioned on a comparison receipt — so ``derive_result_cash`` refuses a
    mislabeled denominator with ``mislabeled_denominator`` before any formula
    code is reached.
    """
    if cell.get("metric") != _SHARE_METRIC:
        return None
    dimensions = cell.get("business_dimensions")
    if not isinstance(dimensions, Mapping):
        return _MISLABELED
    if "segment" not in dimensions or "denominator" not in dimensions:
        return _MISLABELED
    pair = (dimensions["segment"], dimensions["denominator"])
    if pair not in _AGREED_PAIRS:
        return _MISLABELED
    return None
