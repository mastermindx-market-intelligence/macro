"""F2 controls M06a/M06b: deterministic amount_format (copy_templates.v1).

Pins one minus sign for negative amounts and the zero case (M06a), and the
contract rule that scale is never inferred from a unit (endpoints.v1
normalisation.value; eval_grade does the same): a "thousands" unit is shown
as written, never as plain dollars and never rescaled (M06b). Only a unit that
means USD in the contract unit_map takes the $ billion/million tiers; every
other amount is raw with its unit plus the currency code the unit omits.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from engine.news_impact.eval_grade import UNIT_MAP
from engine.news_impact.prophet_adapter import SLOT_MAX, format_amount

ROOT = Path(__file__).resolve().parents[1]


def _q(value, unit="USD", currency="USD", bound="exact"):
    return {"form": "point", "value": value, "bound": bound,
            "unit": unit, "currency": currency, "basis": "total"}


def _r(low, high, unit="USD", currency="USD", bound="exact"):
    return {"form": "range", "low": low, "high": high, "bound": bound,
            "unit": unit, "currency": currency, "basis": "total"}


@pytest.mark.parametrize(
    ("quantity", "en", "zh"),
    [
        (_q(150_000_000_000), "$150 billion", "1500亿美元"),
        (_q(235_000_000_000), "$235 billion", "2350亿美元"),
        (_q(-1_500_000), "-$1.5 million", "-150万美元"),
        (_q(0), "$0", "0美元"),
        (_q(-0.04), "$0", "0美元"),
        (_q(5, unit="usd"), "$5", "5美元"),
        (_q(5, unit="$", currency="NA"), "$5", "5美元"),
        (_q(7, unit="dollars"), "$7", "7美元"),
        (_q(3_000_000, unit="US$"), "$3 million", "300万美元"),
        (_q(1_200_000, unit="JPY", currency="JPY"), "1200000 JPY", "1200000 JPY"),
        (_q(-5, unit="EUR", currency="EUR"), "-5 EUR", "-5 EUR"),
        (_q(1200, unit="units", currency=""), "1200 units", "1200 units"),
        (_q(2500, unit="shares", currency="NA"), "2500 shares", "2500 shares"),
        (_q(12.5, unit="percent", currency="NA"), "12.5 percent", "12.5 percent"),
    ],
)
def test_point_amount(quantity, en, zh):
    assert format_amount(quantity, "en") == en
    assert format_amount(quantity, "zh") == zh


@pytest.mark.parametrize(
    ("quantity", "en"),
    [
        (_q(2500, unit="thousands"), "2500 thousands USD"),
        (_q(150, unit="USD millions"), "150 USD millions"),
        (_q(2, unit="Billion"), "2 Billion USD"),
        (_q(1, unit="USD_million"), "1 USD_million"),
        (_q(1200, unit="thousands", currency="JPY"), "1200 thousands JPY"),
    ],
)
def test_scale_is_never_inferred_from_the_unit(quantity, en):
    assert format_amount(quantity, "en") == en
    assert format_amount(quantity, "zh") == en
    assert "$" not in en and "美元" not in format_amount(quantity, "zh")


def test_m06b_thousands_is_not_plain_dollars():
    quantity = _q(2500, unit="thousands")
    en, zh = format_amount(quantity, "en"), format_amount(quantity, "zh")
    assert en != "$2500" and "$" not in en and "美元" not in zh
    assert "thousands" in en and "thousands" in zh
    assert "2500" in en and "2500" in zh


def test_non_usd_is_never_converted():
    for quantity in (_q(1_200_000, unit="JPY", currency="JPY"),
                     _q(1200, unit="thousands", currency="JPY"),
                     _q(-5, unit="EUR", currency="EUR")):
        for locale in ("en", "zh"):
            text = format_amount(quantity, locale)
            assert "USD" not in text and "$" not in text and "美元" not in text


def test_non_monetary_units_never_take_dollars_or_a_currency_code():
    for unit in ("shares", "percent", "units"):
        text = format_amount(_q(2_000_000, unit=unit, currency="USD"), "en")
        assert text == f"2000000 {unit}"


def test_conflicting_unit_and_currency_shows_both():
    assert format_amount(_q(5, unit="USD", currency="EUR"), "en") == "5 USD EUR"


def test_rounding_selects_the_tier():
    assert format_amount(_q(-999_999.96), "en") == "-$1 million"
    assert format_amount(_q(-999_999.96), "zh") == "-100万美元"
    assert format_amount(_q(999_960_000), "en") == "$1 billion"
    assert format_amount(_q(999_960_000), "zh") == "10亿美元"
    assert format_amount(_q(999_949_999), "en") == "$999.9 million"


def test_negative_range_has_one_sign_per_end():
    assert format_amount(_r(-5, -2), "en") == "-$5–-$2"
    assert format_amount(_r(-5, -2), "zh") == "-5美元–-2美元"


def test_billion_range_keeps_structure():
    assert format_amount(_r(1_000_000_000, 2_000_000_000), "en") == "$1 billion–$2 billion"


@pytest.mark.parametrize(
    ("bound", "en_prefix", "zh_prefix"),
    [("approximately", "about ", "约"), ("up_to", "up to ", "至多"),
     ("at_least", "at least ", "至少")],
)
def test_bound_prefix_precedes_the_single_sign(bound, en_prefix, zh_prefix):
    quantity = _q(-1_500_000, bound=bound)
    assert format_amount(quantity, "en") == f"{en_prefix}-$1.5 million"
    assert format_amount(quantity, "zh") == f"{zh_prefix}-150万美元"


def test_absent_and_non_numeric_render_empty():
    assert format_amount({"form": "absent"}, "en") == ""
    assert format_amount(_q("12"), "en") == ""
    assert format_amount(_q(None), "zh") == ""
    assert format_amount(_q(True), "en") == ""


def test_amount_slot_length_stays_within_slot_max():
    widest = _q(-123_456_789_012.5, unit="thousand metric tonnes", currency="JPY",
                bound="approximately")
    for locale in ("en", "zh"):
        assert len(format_amount(widest, locale)) <= SLOT_MAX["amount_plain"]


def test_unit_map_is_the_contract_table():
    path = ROOT / "contracts" / "news_impact" / "endpoints.v1.json"
    contract = json.loads(path.read_text(encoding="utf-8"))
    assert UNIT_MAP == contract["normalisation"]["unit_map"]


def test_contract_examples_reproduce():
    path = ROOT / "contracts" / "news_impact" / "copy_templates.v1.json"
    examples = json.loads(path.read_text(encoding="utf-8"))["amount_format"]["examples"]
    assert len(examples) == 3
    for example in examples:
        quantity = {"form": "point", "value": example["value"], "currency": example["currency"]}
        assert format_amount(quantity, "en") == example["en"]
        assert format_amount(quantity, "zh") == example["zh"]
