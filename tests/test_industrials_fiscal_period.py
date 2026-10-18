"""Stated Industrials period end versus a later matcher's tolerance (W6-A).

The July 3 cell is the synthetic period already in
``same_number_two_headers.json``. A three-day tolerance may qualify event
matching later; it must not rewrite that cell to 30 June.
"""
from __future__ import annotations

from datetime import date

from engine.company_intelligence.industrials_fiscal import stated_period_end
from tests.industrials_result_cash_helpers import case


def test_stated_period_end_survives_tolerance() -> None:
    loaded = case("same_number_two_headers")
    ends = {cell["period"]["end"] for cell in loaded["cells"]}
    assert ends == {"2026-07-03"}
    result = stated_period_end(date(2026, 7, 3), tolerance_days=3)
    assert result == date(2026, 7, 3)
    assert result != date(2026, 6, 30)
