"""F2 controls M06a/M06b: deterministic amount_format (copy_templates.v1).

Pins one minus sign for negative amounts, the zero case, unit scale words
(thousand/million/billion/trillion) and non-USD units kept without conversion.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from engine.news_impact.prophet_adapter import format_amount

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
        (_q(165_000_000_000), "$165 billion", "1650亿美元"),
        (_q(-1_500_000), "-$1.5 million", "-150万美元"),
        (_q(0), "$0", "0美元"),
        (_q(-0.04), "$0", "0美元"),
        (_q(2500, unit="thousands"), "$2.5 million", "250万美元"),
        (_q(150, unit="USD millions"), "$150 million", "15000万美元"),
        (_q(2, unit="Billion"), "$2 billion", "20亿美元"),
        (_q(1_200_000, unit="JPY", currency="JPY"), "1200000 JPY", "1200000 JPY"),
        (_q(1200, unit="thousands", currency="JPY"), "1200000 JPY", "1200000 JPY"),
        (_q(-5, unit="EUR", currency="EUR"), "-5 EUR", "-5 EUR"),
        (_q(1200, unit="units", currency=""), "1200 units", "1200 units"),
    ],
)
def test_point_amount(quantity, en, zh):
    assert format_amount(quantity, "en") == en
    assert format_amount(quantity, "zh") == zh


def test_non_usd_is_never_converted():
    for quantity in (_q(1_200_000, unit="JPY", currency="JPY"),
                     _q(1200, unit="thousands", currency="JPY")):
        text = format_amount(quantity, "en")
        assert "JPY" in text and "USD" not in text and "$" not in text


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


def test_contract_examples_reproduce():
    path = ROOT / "contracts" / "news_impact" / "copy_templates.v1.json"
    examples = json.loads(path.read_text(encoding="utf-8"))["amount_format"]["examples"]
    assert len(examples) == 3
    for example in examples:
        quantity = {"form": "point", "value": example["value"], "currency": example["currency"]}
        assert format_amount(quantity, "en") == example["en"]
        assert format_amount(quantity, "zh") == example["zh"]
