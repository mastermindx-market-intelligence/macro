from __future__ import annotations

import copy
import json
from decimal import Decimal
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, ValidationError

from engine import options_nbbo_cohort as nbbo

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "contracts/options/options.alpha_exact_option_outcome_policy.v1.schema.json"
POLICY = ROOT / "research/options_estate/options_alpha_exact_option_outcome_policy_v1.json"
PREREG = ROOT / "research/options_estate/OPTIONS_ALPHA_EXACT_OPTION_OUTCOME_PREREG_2026-09-19.md"


def _load() -> tuple[dict, dict]:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    policy = json.loads(POLICY.read_text(encoding="utf-8"))
    return schema, policy


def test_oa3_machine_policy_validates_exactly() -> None:
    schema, policy = _load()
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(policy)

    assert policy["schema"] == "options.alpha_exact_option_outcome_policy/v1"
    assert policy["policy_id"] == "oa3.long_single_leg_h60_nbbo/v1"
    assert policy["state"] == "preregistered_inactive"


def test_oa3_policy_is_long_single_leg_and_zero_authority() -> None:
    _schema, policy = _load()
    population = policy["population"]

    assert population == {
        "exact_expression_receipt_required": True,
        "selection_before_outcomes": True,
        "position": "long",
        "quantity_contracts": 1,
        "standard_multiplier": 100,
        "standard_deliverable_only": True,
        "same_day_expiration_allowed": False,
        "package_supported": False,
        "short_option_supported": False,
    }
    assert policy["authority"]
    assert set(policy["authority"].values()) == {False}


def test_oa3_clocks_anchor_to_expression_availability_then_entry_quote() -> None:
    _schema, policy = _load()

    assert policy["entry"] == {
        "boundary": "expression.available_at",
        "selected_side": "ask",
        "quote_event_window_seconds": 60,
        "minimum_displayed_contracts": 1,
    }
    assert policy["exit"] == {
        "target": "entry_quote.event_at+PT60M",
        "selected_side": "bid",
        "quote_event_window_seconds": 60,
        "minimum_displayed_contracts": 1,
    }
    assert policy["clock"]["same_nyse_rth_session_required"] is True
    assert policy["clock"]["entry_never_precedes_expression_availability"] is True
    assert policy["clock"]["retrieval_after_maturity_allowed"] is True
    assert policy["clock"]["benchmark_live_capture_lag_rule_inherited"] is False


def test_oa3_reuses_only_registered_generic_nbbo_mechanics() -> None:
    _schema, policy = _load()
    source = policy["quote_source"]
    cost = policy["cost"]

    assert source["endpoint"] == nbbo.SOURCE_ENDPOINT
    assert source["interval"] == nbbo.SOURCE_INTERVAL
    assert source["quote_rule_reference"] == nbbo.QUOTE_RULE_ID
    assert cost["fee_per_side_usd"] == format(nbbo.FEE_PER_SIDE_USD, "f")
    assert source["executable_fill_claim"] is False

    entry = Decimal("1.00")
    exit_bid = Decimal("1.20")
    expected = (
        (
            Decimal(100) * exit_bid
            - nbbo.FEE_PER_SIDE_USD
            - (Decimal(100) * entry + nbbo.FEE_PER_SIDE_USD)
        )
        / (Decimal(100) * entry + nbbo.FEE_PER_SIDE_USD)
        * Decimal(100)
    ).quantize(Decimal("0.000001"))
    assert nbbo.net_return_pct(entry, exit_bid) == expected


def test_oa3_forbids_non_executable_substitutes() -> None:
    _schema, policy = _load()

    assert policy["forbidden_substitutes"] == [
        "mid",
        "last",
        "eod_mark",
        "intrinsic",
        "black_scholes",
        "neighbor_contract",
        "underlying_return",
        "later_best_print",
    ]


def test_oa3_schema_rejects_authority_or_hidden_package_expansion() -> None:
    schema, policy = _load()
    validator = Draft202012Validator(schema)

    promoted = copy.deepcopy(policy)
    promoted["authority"]["may_trade"] = True
    with pytest.raises(ValidationError):
        validator.validate(promoted)

    widened = copy.deepcopy(policy)
    widened["population"]["package_supported"] = True
    with pytest.raises(ValidationError):
        validator.validate(widened)

    shifted = copy.deepcopy(policy)
    shifted["entry"]["boundary"] = "candidate.decision_at"
    with pytest.raises(ValidationError):
        validator.validate(shifted)


def test_preregistration_documents_benchmark_separation_and_no_substitution() -> None:
    text = PREREG.read_text(encoding="utf-8")

    assert "build_observation()" in text
    assert "source_query()" in text
    assert "not** OA-3 contracts" in text
    assert "expression.available_at" in text
    assert "first valid firm OPRA **ask**" in text
    assert "first valid firm OPRA **bid**" in text
    assert "No substitutes" in text
    assert "No second ledger/store/publisher" not in text
    assert "second outcome ledger" in text
