"""Synthetic contract tests; no provider or production acceptance implied."""

from copy import deepcopy
from decimal import Inexact, Rounded, ROUND_DOWN, Subnormal, Underflow, localcontext
import json

import pytest

from engine.options_statistics import LOCATIONS, measure_observed_prints


def row(**changes):
    return dict(root="SPY", expiration="2026-10-30", right="C", strike=760,
                sequence=1, price=2, size=3, bid=1, ask=3,
                trade_timestamp="2026-10-22T14:00:00+00:00",
                quote_timestamp="2026-10-22T13:59:59Z", exchange=1,
                premium_multiplier=100, premium_basis="qualified_contract_terms") | changes


def test_exhaustive_locations_and_independent_partitions():
    rows = [row(price=p, sequence=i, size=i + 1, right="C" if i % 2 else "P",
                exchange=1 if i % 2 else "1")
            for i, p in enumerate([0.5, 1, 1.5, 2, 2.5, 3, 4])]
    rows.append(row(sequence=7, size=8, bid=None, exchange=None))
    before = deepcopy(rows)
    result = measure_observed_prints(rows)
    assert rows == before
    assert result["totals"]["print_count"] == 8
    assert result["totals"]["contract_volume"] == 36
    # (0.5*1 + 1*2 + 1.5*3 + 2*4 + 2.5*5 + 3*6 + 4*7 + 2*8)*100
    assert result["totals"]["qualified_premium_usd"] == 8950
    assert result["nbbo_print_coverage"] == result["venue_print_coverage"] == 7 / 8
    assert set(result["venues"]) == {"int:1", "str:1", "UNKNOWN"}
    assert [result["locations"][k]["print_count"] for k in LOCATIONS] == [1] * 8
    for partition in ("rights", "locations", "venues"):
        for field in ("print_count", "contract_volume", "qualified_premium_usd"):
            assert sum(v[field] or 0 for v in result[partition].values()) == result["totals"][field]
    assert result == measure_observed_prints(list(reversed(rows)))


@pytest.mark.parametrize("changes", [
    {"bid": None}, {"ask": float("nan")}, {"bid": True}, {"bid": 3},
    {"bid": 4}, {"bid": 0}, {"quote_timestamp": "2026-10-22T14:00:01Z"},
    {"quote_timestamp": None}, {"quote_timestamp": "2026-10-22T13:59:59"},
    {"bid": 10**400},
])
def test_unusable_quotes_remain_in_raw_denominator(changes):
    result = measure_observed_prints([row(**changes)])
    assert result["totals"]["print_count"] == 1
    assert result["totals"]["contract_volume"] == 3
    assert result["locations"]["UNKNOWN"]["print_count"] == 1
    assert result["nbbo_print_coverage"] == 0


def test_premium_terms_and_unknowns_are_not_standardized():
    result = measure_observed_prints([
        row(), row(premium_multiplier=10), row(premium_basis=None),
        row(premium_multiplier=None), row(premium_multiplier=True),
        row(premium_multiplier=float("inf")), row(premium_multiplier=1e308),
    ])
    assert result["totals"]["print_count"] == 7
    assert result["totals"]["premium_qualified_print_count"] == 2
    assert result["totals"]["qualified_premium_usd"] == 660
    assert result["totals"]["premium_print_coverage"] == 2 / 7
    json.dumps(result, allow_nan=False)


@pytest.mark.parametrize("changes", [
    {"root": " spy"}, {"right": "call"}, {"expiration": "20261030"},
    {"expiration": "2026-02-30"}, {"strike": True}, {"price": float("inf")},
    {"price": 0}, {"size": True}, {"size": 1.5}, {"size": -1},
    {"size": 2**63}, {"sequence": True}, {"sequence": -1},
    {"trade_timestamp": "2026-10-22T14:00:00"}, {"trade_timestamp": None},
])
def test_invalid_core_does_not_manufacture_known_coverage(changes):
    result = measure_observed_prints([row(**changes)])
    assert result["status"] == "NO_VALID_ROWS"
    assert result["rejected_count"] == 1
    assert result["nbbo_print_coverage"] is None
    assert result["totals"]["qualified_premium_usd"] is None


def test_empty_unavailable_and_all_invalid_are_distinct():
    assert measure_observed_prints(None)["totals"] is None
    empty = measure_observed_prints([])
    assert empty["status"] == "OBSERVED_EMPTY"
    assert empty["totals"]["print_count"] == 0
    assert empty["totals"]["premium_print_coverage"] is None
    assert measure_observed_prints([None, {}])["rejected_count"] == 2
    with pytest.raises(TypeError):
        measure_observed_prints({})


def test_unknown_venue_and_precise_midpoint_do_not_infer_intent():
    result = measure_observed_prints([row(exchange=True, bid=0.1, ask=0.3, price=0.2)])
    assert result["locations"]["at_mid"]["print_count"] == 1
    assert result["venues"]["UNKNOWN"]["print_count"] == 1
    assert result["venue_print_coverage"] == 0
    baseline = measure_observed_prints([row(price=1.2345)])
    with localcontext() as context:
        context.prec = 2
        assert measure_observed_prints([row(price=1.2345)]) == baseline


def test_sum_overflow_is_explicit_not_nonfinite_json_or_zero():
    result = measure_observed_prints([row(price=1e308, size=1, premium_multiplier=1)] * 2)
    assert result["totals"]["premium_qualified_print_count"] == 2
    assert result["totals"]["qualified_premium_usd"] is None
    assert result["totals"]["premium_total_status"] == "UNREPRESENTABLE"
    json.dumps(result, allow_nan=False)


def test_huge_unqualified_terms_preserve_volume_and_unknown_premium():
    result = measure_observed_prints([row(premium_multiplier=10**400)])
    assert result["totals"]["print_count"] == 1
    assert result["totals"]["premium_qualified_print_count"] == 0
    assert result["totals"]["qualified_premium_usd"] is None


def test_underflow_is_missing_premium_not_known_zero():
    result = measure_observed_prints([row(price=5e-324, size=1, premium_multiplier=5e-324)])
    assert result["totals"]["print_count"] == 1
    assert result["totals"]["premium_qualified_print_count"] == 0
    assert result["totals"]["qualified_premium_usd"] is None


@pytest.mark.parametrize("root", ["BRK-B", "^SPX", "ABC=", "123", "SPXW"])
def test_incumbent_root_alphabet_is_preserved(root):
    assert measure_observed_prints([row(root=root)])["totals"]["print_count"] == 1


@pytest.mark.parametrize("sample", [
    row(price=1e100, size=1, premium_multiplier=100),
    row(price=1e-100, size=1, premium_multiplier=1),
    row(price=1e-310, size=1, premium_multiplier=1),
    row(price=1.2345, size=1, premium_multiplier=100),
])
def test_arithmetic_is_independent_of_caller_decimal_context(sample):
    expected = measure_observed_prints([sample])
    with localcontext() as caller:
        caller.prec = 2
        caller.Emax = 99
        caller.Emin = -99
        caller.rounding = ROUND_DOWN
        caller.clamp = 1
        caller.traps[Inexact] = True
        caller.traps[Rounded] = True
        caller.traps[Subnormal] = True
        caller.traps[Underflow] = True
        caller.flags[Inexact] = True
        before = repr(caller)
        assert measure_observed_prints([sample]) == expected
        assert repr(caller) == before
        json.dumps(expected, allow_nan=False)
