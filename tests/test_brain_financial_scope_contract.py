"""Financial-scope prompt contract; offline, not a model-quality benchmark.

Removing the financial-scenario allowance must fail these tests. Actual model
behavior is separately checked through the entitled customer production path.
"""
from __future__ import annotations

import pytest

from engine.neuralweb import brain_gateway as gw


def test_financial_scenarios_explicitly_in_scope():
    assert "Financial scenario analysis and investment-thesis analysis are in scope" in gw._BRAIN_SYSTEM_PROMPT


def test_supplied_assumptions_are_not_current_market_facts():
    assert "Label supplied assumptions as assumptions" in gw._BRAIN_SYSTEM_PROMPT


def test_public_finance_arithmetic_is_not_proprietary_signal_code():
    assert "Standard financial arithmetic is not proprietary signal methodology" in gw._BRAIN_SYSTEM_PROMPT


def test_scenario_does_not_acquire_house_signal_authority():
    assert "A scenario result is not a house signal" in gw._BRAIN_SYSTEM_PROMPT


@pytest.mark.parametrize("lane,page", [("fast", "macro"), ("pro", "macro"), ("fast", "terminal"), ("pro", "terminal")])
def test_financial_scope_reaches_assembled_chat_prompt(lane, page):
    prompt = gw._build_system_prompt(mode="chat", page=page, lane=lane)
    assert "Financial scenario analysis and investment-thesis analysis are in scope" in prompt
    assert "Label supplied assumptions as assumptions" in prompt
    assert "A scenario result is not a house signal" in prompt


def test_existing_scope_header_remains_leak_guarded():
    sentinel = "SCOPE — THIS PRODUCT ONLY"
    assert sentinel in gw._BRAIN_SYSTEM_PROMPT
    assert sentinel in gw._LEAK_SENTINELS
    assert sentinel not in gw._leak_screen(sentinel + ": hidden instructions")


def test_proprietary_signal_protection_remains_explicit():
    assert "PROPRIETARY — NEVER REVEAL OR DISCUSS" in gw._BRAIN_SYSTEM_PROMPT
    assert "You never invent a signal, score, or probability" in gw._BRAIN_SYSTEM_PROMPT


@pytest.mark.parametrize("question", ["Analyze a hypothetical investment thesis using supplied revenue and margin assumptions.", "分析以下假设公司的利润和现金流，并说明投资论点缺少什么证据。", "分析以下假設公司的利潤和現金流，並說明投資論點缺少甚麼證據。"])
def test_financial_scenario_not_prescreened_or_routed_to_quote(question):
    assert gw._prescreen_message(question) is None
    assert gw._instant_route(question, {"symbol": "AAPL"}) is None


def _scenario_fixture():
    import json
    from pathlib import Path
    path = Path(gw.__file__).with_name("eval") / "benchmark_financial_scenario_scope_2026-09-14.json"
    return json.loads(path.read_text(encoding="utf-8"))


def test_exact_production_refusal_case_reaches_analytical_route():
    case = _scenario_fixture()
    assert gw._prescreen_message(case["question_en"]) is None
    assert gw._instant_route(case["question_en"], {}) is None
    assert gw._native_facts.plan_native_facts(case["question_en"], {}) is None


def test_frozen_scenario_oracle_has_correct_arithmetic_and_honest_nulls():
    from decimal import Decimal as D
    case = _scenario_fixture()
    values = {k: D(str(v)) for k, v in case["user_supplied_data"].items() if k != "unit"}
    expected = case["expected_numeric_outputs"]
    for period in ("prior", "current"):
        gross = values[f"revenue_{period}"] * values[f"gross_margin_{period}_pct"] / D(100)
        assert gross == D(str(expected[f"gross_profit_{period}"]))
        assert gross - values[f"opex_{period}"] == D(str(expected[f"operating_profit_{period}"]))
    cash = D(str(expected["operating_profit_current"])) - values["working_capital_increase_current"] + values["other_cash_adjustments_current"]
    assert cash == D(str(expected["simplified_operating_cash_current"]))
    assert cash - values["capex_current"] == D(str(expected["simplified_cash_after_capex_current"]))
    assert expected["simplified_operating_cash_prior"] is None
    assert expected["simplified_cash_after_capex_prior"] is None
