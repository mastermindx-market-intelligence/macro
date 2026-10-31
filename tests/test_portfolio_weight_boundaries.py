"""Synthetic descriptive-weight boundaries; no portfolio/data/provider I/O."""
import json
import math
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine.portfolio_brief import _normalize_holdings, compose_brief


def _brief(rows):
    ctx = {"asof": "2026-10-30", "sectors": {}, "tickers": {
        "AAA": {"sector": "Technology"}, "BBB": {"sector": "Energy"}}}
    result = compose_brief(ctx, rows, "2026-10-30", "2026-10-30T00:00:00Z",
                           population="positions")
    json.dumps(result, allow_nan=False)
    return result


@pytest.mark.parametrize("field", ["shares", "entry_price"])
@pytest.mark.parametrize("invalid", [True, False, float("inf"), -float("inf"),
    float("nan"), "inf", "NaN", 10**400, None, "bad", 0, -1],
    ids=["true", "false", "inf", "negative-inf", "nan", "inf-text", "nan-text",
         "overflow-int", "missing", "invalid-text", "zero", "negative"])
def test_invalid_cost_input_preserves_name_without_fabricated_weight(field, invalid):
    row = {"ticker": "AAA", "shares": 1, "entry_price": 2, field: invalid}
    rows = [row, {"ticker": "BBB", "shares": 1, "entry_price": 2}]
    order, weights, mode = _normalize_holdings(rows)
    assert order == ["AAA", "BBB"]
    assert mode == "positions"
    assert weights == {"AAA": 0.0, "BBB": 1.0}
    result = _brief(rows)
    assert result["book"]["n"] == 2
    assert result["data"]["concentration"]["top_name_pct"] == 100
    assert "Energy 100%" in result["headline"]["en"]


@pytest.mark.parametrize("rows,expected", [
    ([(1e308, 2), (1e308, 4)], [1/3, 2/3]),
    ([(1e308, 1), (1e308, 1)], [0.5, 0.5]),
    ([(1e-300, 1e-30), (2e-300, 1e-30)], [1/3, 2/3]),
    ([(1e308, 1e-308), (1e-308, 1e308)], [0.5, 0.5]),
    ([("10", "2.5"), (5, 5)], [0.5, 0.5]),
], ids=["product-overflow", "total-overflow", "product-underflow", "cross-scale", "ordinary"])
def test_valid_cost_ratios_survive_arithmetic_extremes(rows, expected):
    holdings = [dict(ticker=t, shares=s, entry_price=e)
                for t, (s, e) in zip(["AAA", "BBB"], rows)]
    _, weights, mode = _normalize_holdings(holdings)
    assert mode == "positions"
    assert list(weights.values()) == pytest.approx(expected)
    assert all(math.isfinite(w) and 0 <= w <= 1 for w in weights.values())
    assert sum(weights.values()) == pytest.approx(1)
    result = _brief(holdings)
    assert result["data"]["concentration"]["top_name_pct"] == round(max(expected)*100)


def test_duplicate_overflow_retains_cost_sum_and_first_seen_order():
    rows = [{"ticker": "aaa", "shares": 1e308, "entry_price": 1},
            {"ticker": "AAA", "shares": 1e308, "entry_price": 1},
            {"ticker": "BBB", "shares": 1e308, "entry_price": 1}]
    order, weights, mode = _normalize_holdings(rows)
    assert order == ["AAA", "BBB"] and mode == "positions"
    assert weights == pytest.approx({"AAA": 2/3, "BBB": 1/3})
    assert "Technology 67%" in _brief(rows)["headline"]["en"]


def test_all_invalid_costs_keep_existing_equal_weight_fallback():
    rows = [{"ticker": "aaa", "shares": float("inf"), "entry_price": 1},
            {"ticker": "AAA", "shares": True, "entry_price": 2},
            {"ticker": "BBB", "shares": None, "entry_price": None}]
    assert _normalize_holdings(rows) == (["AAA", "BBB"], {"AAA": .5, "BBB": .5}, "equal")
    assert _brief(rows)["weighting"]["mode"] == "equal"


def test_subnormal_products_keep_relative_cost_before_rounding():
    rows = [{"ticker": "AAA", "shares": 5e-324, "entry_price": 0.5},
            {"ticker": "BBB", "shares": 5e-324, "entry_price": 1}]
    _, weights, mode = _normalize_holdings(rows)
    assert mode == "positions"
    assert weights == pytest.approx({"AAA": 1/3, "BBB": 2/3})
    assert "Energy 67%" in _brief(rows)["headline"]["en"]


def test_unfunded_name_remains_zero_alongside_overflowing_valid_cost():
    rows = [{"ticker": "AAA", "shares": None, "entry_price": None},
            {"ticker": "BBB", "shares": 1e308, "entry_price": 2}]
    assert _normalize_holdings(rows) == (["AAA", "BBB"], {"AAA": 0.0, "BBB": 1.0}, "positions")
    assert "Energy 100%" in _brief(rows)["headline"]["en"]
