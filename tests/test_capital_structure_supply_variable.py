"""SPEC_I2 §3-§5: variable, reset and contingent terms through ``evaluate_supply``.

Every §4 fixture row is asserted end to end here with an exact Decimal string or
an exact integer — never approximately and never by a formatted comparison.  The
builders are imported from the I1 suite and from the pure-evaluator suite; none
is copied.  Fixtures are hand-built ``adjudicated_gold`` records: no filing text
is fabricated and no digest is hard-coded (every digest is derived with
:func:`sha256_of` or :func:`stable_id`).  The only float literals in this file are
inside the float-refusal tests.

Four laws shape every assertion:

* the three parameters of ``evaluate_supply`` are unchanged (§0 item 1);
* an unknown is never 0 and never unbounded, and a floating price with no floor
  is ``unbounded_by_contract`` rather than a finite maximum (§0 item 4, A26,
  masterplan L231);
* exclusive settlement branches are alternatives and only the elected one reaches
  the envelope (§0 item 5, A24);
* a cap, an unmet condition or a notice period limits DELIVERY and never shrinks
  the claim in ``as_converted_claims`` (§0 item 6, A25).
"""
from __future__ import annotations

import dataclasses
import inspect
from decimal import Decimal
from fractions import Fraction

import pytest

import tests.test_capital_structure_instrument_economics as IE
import tests.test_capital_structure_issuer_state_contracts as T
import tests.test_capital_structure_supply_scenarios as SS
import tests.test_capital_structure_variable_terms as V
from engine.capital_structure import issuer_state_contracts as c
from engine.capital_structure import supply_scenarios as supply_module
from engine.capital_structure import variable_terms as vt
from engine.capital_structure.instrument_economics import attach_economic_terms
from engine.capital_structure.supply_scenarios import (
    EVALUATION_ORDER,
    GUARD_CONDITION_NOT_MET,
    GUARD_EXCHANGE_CAP_LIMITS_DELIVERY as GUARD_EXCHANGE_CAP,
    GUARD_EXCLUSIVE_BRANCHES,
    GUARD_NO_ASSUMED_FLOOR,
    IMPLEMENTATION,
    SETTLEMENT_RULES,
    VARIABLE_TERM_RULES,
    evaluate_supply,
    supply_trace,
)

PATH_V = V.PATH_V
PATH_R = V.PATH_R
AS_OF = "2026-11-01T00:00:00Z"
HORIZON_START = "2026-11-02"
HORIZON_END = "2026-11-13"
I2_TRACE_KEYS = ("alternatives", "maximum_issuable", "variable_terms")


# ---------------------------------------------------------------------------
# The ONE shared validation helper every test in this suite calls
# ---------------------------------------------------------------------------


def evaluate(instruments, share_basis, selected_scenario):
    """Run both entry points and schema-check EVERY record this suite emits.

    The shared helper also enforces the two audit r1 row invariants — an unknown
    row names its Unknowns and every row Unknown is in the envelope (M3), and a
    ``bounded_by_floor`` maximum really bounds what the row delivers (M4) — on
    every supply result this suite emits, so every test below checks them.
    """
    envelope = evaluate_supply(instruments, share_basis, selected_scenario)
    trace = supply_trace(instruments, share_basis, selected_scenario)
    record = V.checked(envelope.as_record(), "supply_envelope", supply=(trace, envelope))
    V.checked(envelope.receipt.as_record(), "calculation_receipt")
    V.checked(instruments.as_record(), "instrument_set")
    V.checked(share_basis.as_record(), "share_basis_result")
    V.checked(selected_scenario.as_record(), "financing_scenario")
    V.assert_supply_rows(trace, envelope)
    assert trace["schema"] == SS.TRACE_SCHEMA
    assert trace["implementation"] == IMPLEMENTATION
    assert trace["state_id"] == envelope.state_id
    assert trace["scenario_id"] == envelope.scenario_id == selected_scenario.scenario_id
    for key in SS.TRACE_KEYS:
        assert key in trace, key
    for row in trace["rows"]:
        for key in SS.ROW_KEYS:
            assert key in row, key
    assert c.sha256_of(record) == c.sha256_of(envelope.as_record())
    return envelope, trace


def run(pairs, actions=(), share_basis=None, **over):
    """Build the instrument set, the basis and the scenario, then evaluate."""
    instruments = SS.instrument_set(*pairs)
    basis = share_basis or SS.basis()
    scenario = path_scenario(actions, **over)
    return evaluate(instruments, basis, scenario)


def path_scenario(actions=(), *, path=PATH_V, horizon_end=HORIZON_END, as_of=AS_OF,
                  horizon_start=HORIZON_START, **over):
    defaults = dict(as_of=as_of, horizon_start=horizon_start, horizon_end=horizon_end,
                    price=c.PriceAssumption("path", "USD", path=path), fee_rate=None)
    defaults.update(over)
    return SS.scenario(actions, **defaults)


def rows(trace: dict) -> dict:
    return SS.rows_by_route(trace)


def cash(envelope: c.SupplyEnvelope) -> dict:
    return SS.cash_by_route(envelope)


def unknowns(envelope: c.SupplyEnvelope) -> list:
    return SS.unknown_ids(envelope)


def delivered(envelope: c.SupplyEnvelope) -> str:
    return str(envelope.incremental_issuance.value)


def claimed(envelope: c.SupplyEnvelope) -> str:
    return str(envelope.as_converted_claims.value)


# ---------------------------------------------------------------------------
# Builders — every I2 term enters as adjudicated gold
# ---------------------------------------------------------------------------


def variable_note(series_key: str, built: c.PriceFormula, *, principal: str = "1000000", **extra):
    """A convertible note whose conversion price is a ``PriceFormula``."""
    instrument_id = SS.series_id(series_key)
    terms = dict(
        principal_outstanding=principal,
        cashless_exercise_permitted=True,
        conversion_price=V.price_formula_term(instrument_id, "conversion_price", built),
    )
    terms.update(extra)
    return SS.make_instrument(series_key, kind="convertible_note", **terms)


def market_note(series_key: str, aggregation: str = "lowest_daily", lookback: int = 10, *,
                percent: str = "80", window_end: str = "including_pricing_date",
                lowest_count: int | None = None, measure: str = V.CLOSED, **extra):
    return variable_note(series_key, V.formula([V.market(aggregation, lookback, percent=percent,
                                                         window_end=window_end, lowest_count=lowest_count,
                                                         measure=measure)]), **extra)


def reset_warrant(series_key: str, share_adjustment: str = "none", *, price: str = "1.60",
                  effective_at: str = V.EFFECTIVE, rule: str = "set_to_market",
                  floor: str | None = None, reset_date: str = "2026-11-13", **extra):
    """1,000,000 warrants, one share each, strike 1.60, one 2026-11-13 reset.

    ``extra`` overrides any term by name, which is how a COUNT term dated on or
    after the reset is supplied (audit r1 M2).
    """
    instrument_id = SS.series_id(series_key)
    schedule = c.ResetSchedule("reset_schedule", "exercise_price",
                               (V.reset_event(reset_date, rule, floor=floor,
                                              share_adjustment=share_adjustment),))
    terms = dict(
        instruments_outstanding="1000000", shares_per_instrument="1",
        exercise_price=SS.economic_term(instrument_id, "exercise_price", price, effective_at=effective_at),
        cashless_exercise_permitted=True,
        price_reset=V.structure_term(instrument_id, "price_reset", schedule, effective_at=effective_at))
    terms.update(extra)
    return SS.make_instrument(series_key, kind="warrant", **terms)


def anti_dilution_note(series_key: str, method: str, *, rounding: c.Rounding | None = None,
                       share_adjustment: str = "none"):
    instrument_id = SS.series_id(series_key)
    built = c.AntiDilution("anti_dilution", "conversion_price", method, price_rounding=rounding,
                           share_adjustment=share_adjustment)
    return SS.make_instrument(
        series_key, kind="convertible_note", principal_outstanding="1000000", conversion_price="1.00",
        cashless_exercise_permitted=True,
        anti_dilution=V.structure_term(instrument_id, "anti_dilution", built))


def accruing_preferred(series_key: str, day_count: str = "actual_365", compounding: str = "simple", *,
                       period_months: int | None = None, converts: bool = True, accrued: str | None = None,
                       accrued_at: str = "2026-04-01T00:00:00Z",
                       kind: str = "convertible_preferred", rate: str = "10"):
    instrument_id = SS.series_id(series_key)
    built = c.Accrual("accrual", c.Quantity.known(rate, "percent"), day_count, compounding,
                      "2026-01-01", converts, period_months=period_months)
    terms = dict(principal_outstanding="1000000", conversion_price="1.00",
                 cashless_exercise_permitted=True,
                 accrual_terms=V.structure_term(instrument_id, "accrual_terms", built))
    if accrued is not None:
        terms["accrued_amount_outstanding"] = SS.economic_term(
            instrument_id, "accrued_amount_outstanding", accrued, effective_at=accrued_at)
    return SS.make_instrument(series_key, kind=kind, **terms)


def branching_note(series_key: str, branches=("physical", "cash", "net_share"), elected_by: str = "issuer",
                   *, conversion_price: str = "5.00"):
    instrument_id = SS.series_id(series_key)
    built = c.SettlementBranches("settlement_branches", tuple(branches), elected_by)
    return SS.make_instrument(
        series_key, kind="convertible_note", principal_outstanding="1000000",
        conversion_price=conversion_price, cashless_exercise_permitted=True,
        settlement_branches=V.structure_term(instrument_id, "settlement_branches", built))


def conditioned_note(series_key: str, required_days: int = 5, window_days: int = 10, *,
                     conversion_price: str = "1.00"):
    instrument_id = SS.series_id(series_key)
    return SS.make_instrument(
        series_key, kind="convertible_note", principal_outstanding="1000000",
        conversion_price=conversion_price, cashless_exercise_permitted=True,
        conversion_condition=V.structure_term(instrument_id, "conversion_condition", V.condition(
            required_days, window_days)))


def conversion(instrument_id: str, settlement: str = "cashless", assumed_met=()) -> c.ActionSelection:
    return c.ActionSelection(instrument_id, "conversion", settlement,
                             conditions_assumed_met=tuple(assumed_met))


def fixed_price(price: str) -> c.PriceAssumption:
    return c.PriceAssumption("fixed", "USD", fixed_price=price)


def resolution(unknown_id: str, value: str) -> c.UnknownResolution:
    """A scenario resolution of one named unknown; the id is the evaluator's own."""
    return c.UnknownResolution(
        unknown_id=unknown_id,
        assumed=c.Quantity.known(value, "shares", share_basis="issued_and_outstanding"),
        rationale="the contract's fully-diluted base, stated by the scenario",
    )


# ---------------------------------------------------------------------------
# §0 item 1 — the arity is still three
# ---------------------------------------------------------------------------


def test_s0_1_evaluate_supply_arity_three():
    parameters = inspect.signature(evaluate_supply).parameters
    assert list(parameters) == ["instruments", "basis", "scenario"]
    assert len(parameters) == 3
    assert list(inspect.signature(supply_trace).parameters) == ["instruments", "basis", "scenario"]


def test_s0_1_the_integration_adds_no_module_level_state_or_network():
    source = inspect.getsource(supply_module)
    for banned in ("float(", "import socket", "import urllib", "import requests", "datetime.now("):
        assert banned not in source, banned
    assert not any(param.default is not inspect.Parameter.empty
                   for param in inspect.signature(evaluate_supply).parameters.values())


# ---------------------------------------------------------------------------
# §0 item 2 — a pre-I2 instrument evaluates and digests exactly as before
# ---------------------------------------------------------------------------


def test_s0_2_pre_i2_receipt_digest_is_unchanged_for_a_plain_instrument():
    instrument_id, instrument = SS.plain_warrant("series_i2a_plain")
    envelope, trace = run([(instrument_id, instrument)],
                          [SS.selection(instrument_id, "warrant_exercise", "cash")])
    # The I1 rule table alone, so the digest is the pre-I2 digest, derived here.
    assert envelope.receipt.rule_digest == c.sha256_of(SETTLEMENT_RULES)
    assert envelope.receipt.rule_digest != c.sha256_of(SETTLEMENT_RULES + VARIABLE_TERM_RULES)
    assert tuple(trace) == SS.TRACE_KEYS
    assert tuple(trace["rows"][0]) == SS.ROW_KEYS


def test_s0_2_an_i2_instrument_states_the_extended_rules_it_ran_under():
    instrument_id, instrument = market_note("series_i2a_rules", "lowest_daily", 10)
    envelope, trace = run([(instrument_id, instrument)], [conversion(instrument_id)])
    assert envelope.receipt.rule_digest == c.sha256_of(SETTLEMENT_RULES + VARIABLE_TERM_RULES)
    assert tuple(trace) == SS.TRACE_KEYS + I2_TRACE_KEYS


def test_s0_2_pre_i2_trace_and_row_keys_are_untouched_by_the_i1_suite():
    """The I1 helper asserts exact key tuples; it must still pass on a plain instrument."""
    instrument_id, instrument = SS.plain_warrant("series_i2a_i1helper")
    envelope, trace = SS.evaluate(SS.instrument_set((instrument_id, instrument)), SS.basis(),
                                  SS.scenario([SS.selection(instrument_id, "warrant_exercise", "cash")]))
    assert envelope.incremental_issuance.status == "known"
    assert "variable_terms" not in trace


# ---------------------------------------------------------------------------
# §0 item 3 — a float reaches no envelope
# ---------------------------------------------------------------------------


def test_s0_3_float_refused_in_an_attached_structure_reaches_no_envelope():
    """A float inside a structure is refused before any envelope can be built."""
    record = IE.term_record("price_reset", fact_origin="adjudicated_gold", value=None, unit=None)
    record["structure"] = c.ResetSchedule(
        "reset_schedule", "exercise_price", (V.reset_event(),)).as_record()
    record["structure"]["events"][0]["market"]["percent_of_measure"]["value"] = 100.0
    instruments = SS.instrument_set(*[IE.instrument_for(IE.SERIES)])
    with pytest.raises(c.ContractViolation, match="exact"):
        attach_economic_terms(instruments, [record], [IE.binding(record["occurrence_id"])], IE.AS_OF)


def test_s0_3_float_refused_in_a_price_path_reaches_no_envelope():
    with pytest.raises(c.ContractViolation):
        c.PriceAssumption("path", "USD", path=(("2026-11-02", 1.50),))


# ---------------------------------------------------------------------------
# §0 item 4 — unknown is never 0 and never unbounded
# ---------------------------------------------------------------------------


def test_s0_4_unknown_never_zero_or_unbounded_window_not_covered():
    instrument_id, instrument = market_note("series_i2a_low20", "lowest_daily", 20)
    envelope, trace = run([(instrument_id, instrument)], [conversion(instrument_id)])
    assert envelope.incremental_issuance.status == "unknown"
    assert envelope.incremental_issuance.value is None
    assert unknowns(envelope) == [f"price_window_not_covered_{instrument_id}"]
    assert "incremental_shares" in rows(trace)[instrument_id]


def test_s0_4_unknown_never_zero_or_unbounded_period_vwap_needs_volume():
    instrument_id, instrument = market_note("series_i2a_vwap", "period_vwap", 10)
    envelope, _trace = run([(instrument_id, instrument)], [conversion(instrument_id)])
    assert envelope.incremental_issuance.value is None
    assert unknowns(envelope) == [f"period_vwap_needs_volume_{instrument_id}"]


def test_s0_4_unknown_never_zero_or_unbounded_price_measure_mismatch():
    instrument_id, instrument = market_note("series_i2a_vwapmeasure", "lowest_daily", 10, measure=V.VWAP)
    envelope, _trace = run([(instrument_id, instrument)], [conversion(instrument_id)])
    assert envelope.incremental_issuance.value is None
    assert unknowns(envelope) == [f"price_measure_mismatch_{instrument_id}"]


def test_s0_4_unknown_never_zero_or_unbounded_floor_not_established():
    instrument_id, instrument = variable_note(
        "series_i2a_notestablished",
        V.formula([V.market("lowest_daily", 10)], floor_basis="not_established"))
    envelope, trace = run([(instrument_id, instrument)], [conversion(instrument_id)])
    # The price IS computable; only the maximum is not.
    assert delivered(envelope) == "1250000"
    assert f"floor_not_established_{instrument_id}" in unknowns(envelope)
    body = trace["maximum_issuable"][instrument_id]
    assert body["state"] == "unknown"
    assert "shares" not in body


def test_s0_4_unknown_never_zero_or_unbounded_no_floor_is_unbounded_by_contract():
    """A26 / L231: never a finite maximum and never infinity."""
    instrument_id, instrument = variable_note(
        "series_i2a_unbounded",
        V.formula([V.market("lowest_daily", 10)], floor_basis="none_in_complete_agreement"))
    envelope, trace = run([(instrument_id, instrument)], [conversion(instrument_id)])
    assert delivered(envelope) == "1250000"
    body = trace["maximum_issuable"][instrument_id]
    assert body["state"] == "unbounded_by_contract"
    assert "shares" not in body
    assert unknowns(envelope) == []
    assert GUARD_NO_ASSUMED_FLOOR in envelope.double_count_guards
    assert "inf" not in repr(body).lower()


def test_s0_4_unknown_never_zero_or_unbounded_make_whole_is_an_unknown_repayment():
    instrument_id, instrument = variable_note(
        "series_i2a_makewhole",
        V.formula([V.market("lowest_daily", 10)], floor_basis="stated", floor="1.00",
                  below_floor="floor_applies_with_cash_make_whole"))
    envelope, trace = run([(instrument_id, instrument)], [conversion(instrument_id)])
    assert delivered(envelope) == "1000000"
    assert vt.BLOCKER_FLOOR_MAKE_WHOLE in rows(trace)[instrument_id]["blockers"]
    assert unknowns(envelope) == [f"make_whole_amount_{instrument_id}"]
    effect = cash(envelope)[instrument_id]
    assert effect.kind == "repayment"
    assert effect.gross.status == "unknown"
    assert effect.gross.value is None


def test_s0_4_unknown_never_zero_or_unbounded_reset_outcome_not_evidenced():
    instrument_id, instrument = reset_warrant("series_i2a_resetpast", "none")
    envelope, _trace = run([(instrument_id, instrument)],
                           [SS.selection(instrument_id, "warrant_exercise", "cashless")],
                           path=PATH_R, as_of="2026-11-20T00:00:00Z", horizon_end="2026-11-20")
    assert envelope.incremental_issuance.value is None
    assert unknowns(envelope) == [f"reset_outcome_not_evidenced_{instrument_id}_2026-11-13"]


# ---------------------------------------------------------------------------
# §0 item 5 — exclusive branches are alternatives, never summed
# ---------------------------------------------------------------------------


def test_s0_5_exclusive_branches_never_summed():
    instrument_id, instrument = branching_note("series_i2a_branches")
    envelope, trace = run([(instrument_id, instrument)], [conversion(instrument_id, "net_share")],
                          price=fixed_price("7.50"))
    assert delivered(envelope) == "66666"
    assert str(cash(envelope)[instrument_id].gross.value) == "1000000"
    alternatives = trace["alternatives"]
    assert [item["branch"] for item in alternatives] == ["physical", "cash", "net_share"]
    assert sum(int(item["shares"]) for item in alternatives) == 200_000 + 0 + 66_666
    # The envelope carries ONLY the elected branch, never the sum of the three.
    assert delivered(envelope) != str(200_000 + 0 + 66_666)
    assert [item["elected"] for item in alternatives] == [False, False, True]
    assert {item["guard"] for item in alternatives} == {"exclusive_branches_never_summed"}
    assert GUARD_EXCLUSIVE_BRANCHES in envelope.double_count_guards


def test_s0_5_an_automatic_single_branch_applies_whatever_settlement_is_named():
    instrument_id, instrument = branching_note("series_i2a_autobranch", branches=("physical",),
                                               elected_by="automatic")
    envelope, trace = run([(instrument_id, instrument)], [conversion(instrument_id, "cashless")],
                          price=fixed_price("7.50"))
    assert delivered(envelope) == "200000"
    assert rows(trace)[instrument_id]["variable_terms"]["settlement_branch_elected_by"] == "automatic"


# ---------------------------------------------------------------------------
# §0 item 6 — a limit shrinks delivery, never the claim
# ---------------------------------------------------------------------------


def test_s0_6_cap_limits_delivery_not_claim():
    instrument_id, instrument = market_note("series_i2a_cap", "lowest_daily", 10,
                                            exchange_cap_shares="700000",
                                            shares_issued_under_instrument="200000")
    envelope, trace = run([(instrument_id, instrument)], [conversion(instrument_id)])
    assert delivered(envelope) == "500000"
    assert claimed(envelope) == "1250000"
    row = rows(trace)[instrument_id]
    assert row["variable_terms"]["blocked_by_exchange_cap"] == "750000"
    assert row["underlying_shares"] == "1250000"
    assert vt.BLOCKER_SHAREHOLDER_APPROVAL_REQUIRED in row["blockers"]
    assert GUARD_EXCHANGE_CAP in envelope.double_count_guards
    assert supply_module.GUARD_CLAIM_SURVIVES in row["guards"]


def test_s0_6_an_unmet_condition_limits_delivery_not_claim():
    instrument_id, instrument = conditioned_note("series_i2a_condnotmet", 10, 10)
    envelope, trace = run([(instrument_id, instrument)], [conversion(instrument_id)])
    assert delivered(envelope) == "0"
    assert claimed(envelope) == "1000000"
    row = rows(trace)[instrument_id]
    assert supply_module.GUARD_CLAIM_SURVIVES in row["guards"]
    assert GUARD_CONDITION_NOT_MET in row["guards"]


# ---------------------------------------------------------------------------
# §0 item 7 — no evaluator looks ahead of its pricing date
# ---------------------------------------------------------------------------


def test_s0_7_no_lookahead():
    """The §4 row priced at horizon_end 2026-11-11 ignores the 11-12 and 11-13 points."""
    instrument_id, instrument = market_note("series_i2a_nolookahead", "single_day", 1)
    envelope, trace = run([(instrument_id, instrument)], [conversion(instrument_id)],
                          horizon_end="2026-11-11")
    assert delivered(envelope) == "833333"
    row = rows(trace)[instrument_id]
    assert row["variable_terms"]["pricing_date"] == "2026-11-11"
    assert row["variable_terms"]["contract_price"] == "1.2"
    assert GUARD_NO_ASSUMED_FLOOR in envelope.double_count_guards


def test_s0_7_no_lookahead_the_same_formula_at_the_later_horizon_prices_differently():
    instrument_id, instrument = market_note("series_i2a_lookahead2", "single_day", 1)
    envelope, _trace = run([(instrument_id, instrument)], [conversion(instrument_id)])
    assert delivered(envelope) == "735294"


# ---------------------------------------------------------------------------
# §3 — the fixed evaluation order
# ---------------------------------------------------------------------------


def test_s3_the_evaluation_order_is_recorded_on_every_i2_row():
    instrument_id, instrument = market_note("series_i2a_order", "lowest_daily", 10,
                                            exchange_cap_shares="700000",
                                            shares_issued_under_instrument="200000")
    _envelope, trace = run([(instrument_id, instrument)], [conversion(instrument_id)])
    assert rows(trace)[instrument_id]["evaluation_order"] == list(EVALUATION_ORDER)
    assert EVALUATION_ORDER == ("amount", "price", "condition", "branch", "exchange_cap",
                                "holder_cap_and_notice")


def test_s3_a_pre_i2_row_carries_no_evaluation_order_key():
    instrument_id, instrument = SS.plain_warrant("series_i2a_orderless")
    _envelope, trace = run([(instrument_id, instrument)],
                           [SS.selection(instrument_id, "warrant_exercise", "cash")])
    assert "evaluation_order" not in trace["rows"][0]


def test_s3_an_expression_only_price_stays_unknown_unless_a_structure_is_admitted():
    """I2 never parses ``expression`` text (SPEC_I2 §3 last bullet)."""
    instrument_id = SS.series_id("series_i2a_expression")
    instrument_id, instrument = SS.make_instrument(
        "series_i2a_expression", kind="convertible_note", principal_outstanding="1000000",
        cashless_exercise_permitted=True,
        conversion_price=SS.economic_term(instrument_id, "conversion_price", None,
                                          expression="80% of the lowest daily close"))
    envelope, _trace = run([(instrument_id, instrument)], [conversion(instrument_id)])
    assert envelope.incremental_issuance.status == "unknown"
    assert delivered(envelope) == "None"


# ---------------------------------------------------------------------------
# §4 — the variable-conversion rows (principal 1,000,000; 80% of measure)
# ---------------------------------------------------------------------------


CONVERSION_ROWS = [
    ("lowest10inc", dict(aggregation="lowest_daily", lookback=10), "0.8", "1250000"),
    ("avg10", dict(aggregation="average_daily", lookback=10), "1.168", "856164"),
    ("avg_low3", dict(aggregation="average_of_lowest", lookback=10, lowest_count=3), "74/75", "1013513"),
    ("single_inc", dict(aggregation="single_day", lookback=1), "1.36", "735294"),
    ("single_prec", dict(aggregation="single_day", lookback=1,
                         window_end="preceding_pricing_date"), "1.28", "781250"),
    ("low5prec", dict(aggregation="lowest_daily", lookback=5,
                      window_end="preceding_pricing_date"), "1.04", "961538"),
    ("low5inc", dict(aggregation="lowest_daily", lookback=5), "1.16", "862068"),
]


@pytest.mark.parametrize("name,kwargs,price,shares", CONVERSION_ROWS,
                         ids=[row[0] for row in CONVERSION_ROWS])
def test_fx_variable_conversion_row(name, kwargs, price, shares):
    instrument_id, instrument = market_note(f"series_i2a_fx_{name}", **kwargs)
    envelope, trace = run([(instrument_id, instrument)], [conversion(instrument_id)])
    assert delivered(envelope) == shares
    assert claimed(envelope) == shares
    row = rows(trace)[instrument_id]
    assert row["variable_terms"]["contract_price"] == price
    assert row["variable_terms"]["adjusted_price"] == price
    assert row["variable_terms"]["amount"] == "1000000"


def test_fx_single_day_at_the_2026_11_11_horizon_end_ignores_later_points():
    instrument_id, instrument = market_note("series_i2a_fx_horizon11", "single_day", 1)
    envelope, trace = run([(instrument_id, instrument)], [conversion(instrument_id)],
                          horizon_end="2026-11-11")
    assert delivered(envelope) == "833333"
    assert rows(trace)[instrument_id]["variable_terms"]["contract_price"] == "1.2"


def test_fx_greater_of_fixed_1_10_and_lowest_daily_10():
    built = V.formula([V.fixed("1.10"), V.market("lowest_daily", 10)], combine="greater")
    instrument_id, instrument = variable_note("series_i2a_fx_greater", built)
    envelope, trace = run([(instrument_id, instrument)], [conversion(instrument_id)])
    assert delivered(envelope) == "909090"
    assert rows(trace)[instrument_id]["variable_terms"]["contract_price"] == "1.1"


def test_fx_lesser_of_fixed_1_10_and_lowest_daily_10():
    built = V.formula([V.fixed("1.10"), V.market("lowest_daily", 10)], combine="lesser")
    instrument_id, instrument = variable_note("series_i2a_fx_lesser", built)
    envelope, trace = run([(instrument_id, instrument)], [conversion(instrument_id)])
    assert delivered(envelope) == "1250000"
    assert rows(trace)[instrument_id]["variable_terms"]["contract_price"] == "0.8"


def test_fx_lowest_daily_20_is_unknown_not_a_short_window_price():
    instrument_id, instrument = market_note("series_i2a_fx_low20", "lowest_daily", 20)
    envelope, _trace = run([(instrument_id, instrument)], [conversion(instrument_id)])
    assert envelope.incremental_issuance.status == "unknown"
    assert unknowns(envelope) == [f"price_window_not_covered_{instrument_id}"]


def test_fx_period_vwap_is_unknown_because_a_price_path_carries_no_volume():
    instrument_id, instrument = market_note("series_i2a_fx_vwap", "period_vwap", 10)
    envelope, _trace = run([(instrument_id, instrument)], [conversion(instrument_id)])
    assert envelope.incremental_issuance.status == "unknown"
    assert unknowns(envelope) == [f"period_vwap_needs_volume_{instrument_id}"]


def test_fx_a_daily_vwap_formula_on_an_undeclared_path_is_unknown():
    instrument_id, instrument = market_note("series_i2a_fx_vwapmeasure", "lowest_daily", 10,
                                            measure=V.VWAP)
    envelope, _trace = run([(instrument_id, instrument)], [conversion(instrument_id)])
    assert envelope.incremental_issuance.status == "unknown"
    assert unknowns(envelope) == [f"price_measure_mismatch_{instrument_id}"]


def test_fx_a_declared_daily_vwap_path_is_a_scenario_assumption_not_a_fact():
    instrument_id, instrument = market_note("series_i2a_fx_vwapdeclared", "lowest_daily", 10,
                                            measure=V.VWAP)
    envelope, trace = run([(instrument_id, instrument)], [conversion(instrument_id)],
                          other_assumptions=((vt.PATH_MEASURE_ASSUMPTION, V.VWAP),))
    assert delivered(envelope) == "1250000"
    assert rows(trace)[instrument_id]["variable_terms"]["path_measure"] == V.VWAP
    assert unknowns(envelope) == []


def test_fx_floor_0_50_stated_does_not_bind():
    built = V.formula([V.market("lowest_daily", 10)], floor_basis="stated", floor="0.50",
                      below_floor="floor_applies")
    instrument_id, instrument = variable_note("series_i2a_fx_floor050", built)
    envelope, trace = run([(instrument_id, instrument)], [conversion(instrument_id)])
    assert delivered(envelope) == "1250000"
    assert rows(trace)[instrument_id]["variable_terms"]["floor_reached"] == "false"
    body = trace["maximum_issuable"][instrument_id]
    assert body["state"] == "bounded_by_floor"
    assert body["shares"] == "2000000"


def test_fx_floor_1_00_stated_binds():
    built = V.formula([V.market("lowest_daily", 10)], floor_basis="stated", floor="1.00",
                      below_floor="floor_applies")
    instrument_id, instrument = variable_note("series_i2a_fx_floor100", built)
    envelope, trace = run([(instrument_id, instrument)], [conversion(instrument_id)])
    assert delivered(envelope) == "1000000"
    assert rows(trace)[instrument_id]["variable_terms"]["floor_reached"] == "true"
    assert trace["maximum_issuable"][instrument_id]["shares"] == "1000000"


def test_fx_floor_1_00_with_a_cash_make_whole():
    built = V.formula([V.market("lowest_daily", 10)], floor_basis="stated", floor="1.00",
                      below_floor="floor_applies_with_cash_make_whole")
    instrument_id, instrument = variable_note("series_i2a_fx_makewhole", built)
    envelope, trace = run([(instrument_id, instrument)], [conversion(instrument_id)])
    assert delivered(envelope) == "1000000"
    assert vt.BLOCKER_FLOOR_MAKE_WHOLE in rows(trace)[instrument_id]["blockers"]
    assert unknowns(envelope) == [f"make_whole_amount_{instrument_id}"]
    assert cash(envelope)[instrument_id].gross.value is None


def test_fx_floor_basis_none_in_complete_agreement():
    built = V.formula([V.market("lowest_daily", 10)], floor_basis="none_in_complete_agreement")
    instrument_id, instrument = variable_note("series_i2a_fx_nofloor", built)
    envelope, trace = run([(instrument_id, instrument)], [conversion(instrument_id)])
    assert delivered(envelope) == "1250000"
    assert trace["maximum_issuable"][instrument_id]["state"] == "unbounded_by_contract"


def test_fx_floor_basis_not_established():
    built = V.formula([V.market("lowest_daily", 10)], floor_basis="not_established")
    instrument_id, instrument = variable_note("series_i2a_fx_unestablished", built)
    envelope, trace = run([(instrument_id, instrument)], [conversion(instrument_id)])
    assert delivered(envelope) == "1250000"
    body = trace["maximum_issuable"][instrument_id]
    assert body["state"] == "unknown"
    assert body["unknown_id"] == f"floor_not_established_{instrument_id}"


# ---------------------------------------------------------------------------
# §4 — the reset-warrant rows (1,000,000 warrants, K 1.60, reset 2026-11-13)
# ---------------------------------------------------------------------------


def reset_run(instrument_id, instrument, *, as_of=AS_OF, horizon_end="2026-11-16", actions=None):
    return run([(instrument_id, instrument)],
               actions if actions is not None else [SS.selection(instrument_id, "warrant_exercise", "cashless")],
               path=PATH_R, as_of=as_of, horizon_end=horizon_end)


def test_fx_reset_before_the_reset_date_is_out_of_the_money():
    instrument_id, instrument = reset_warrant("series_i2a_fx_rbefore", "none")
    envelope, trace = reset_run(instrument_id, instrument, horizon_end="2026-11-12")
    assert delivered(envelope) == "0"
    assert claimed(envelope) == "1000000"
    assert rows(trace)[instrument_id]["variable_terms"]["future_reset"] == "2026-11-13"


def test_fx_reset_after_the_reset_with_no_share_adjustment():
    instrument_id, instrument = reset_warrant("series_i2a_fx_rafter", "none")
    envelope, trace = reset_run(instrument_id, instrument)
    assert delivered(envelope) == "200000"
    assert rows(trace)[instrument_id]["variable_terms"]["adjusted_price"] == "1.2"
    assert rows(trace)[instrument_id]["variable_terms"]["reset_applied_2026-11-13"] == "1.2"


def test_fx_reset_after_the_reset_preserving_the_aggregate_exercise_price():
    instrument_id, instrument = reset_warrant("series_i2a_fx_rpreserve", "preserve_aggregate_exercise_price")
    envelope, trace = reset_run(instrument_id, instrument)
    assert delivered(envelope) == "266666"
    assert rows(trace)[instrument_id]["variable_terms"]["reset_share_adjustment_2026-11-13"] == \
        "1000000*1.6/1.2=4000000/3"


def test_fx_reset_adjusted_count_under_preserve_aggregate_exercise_price():
    instrument_id, instrument = reset_warrant("series_i2a_fx_rcount", "preserve_aggregate_exercise_price")
    envelope, _trace = reset_run(instrument_id, instrument, actions=[])
    assert claimed(envelope) == "1333333"


def test_fx_reset_in_the_past_with_no_later_price_term_is_unknown():
    instrument_id, instrument = reset_warrant("series_i2a_fx_rpast", "none")
    envelope, _trace = reset_run(instrument_id, instrument, as_of="2026-11-20T00:00:00Z",
                                 horizon_end="2026-11-20")
    assert envelope.incremental_issuance.status == "unknown"
    assert unknowns(envelope) == [f"reset_outcome_not_evidenced_{instrument_id}_2026-11-13"]


def test_fx_reset_in_the_past_evidenced_by_an_admitted_term_lets_that_term_rule():
    instrument_id, instrument = reset_warrant("series_i2a_fx_revidenced", "none", price="1.20",
                                              effective_at="2026-11-13T00:00:00Z")
    envelope, trace = reset_run(instrument_id, instrument, as_of="2026-11-20T00:00:00Z",
                                horizon_end="2026-11-20")
    assert delivered(envelope) == "200000"
    assert unknowns(envelope) == []
    assert rows(trace)[instrument_id]["variable_terms"]["past_reset"] == "2026-11-13"


# -- audit r1 M2: a past reset that adjusts the count needs the count evidenced --


def test_m2_past_reset_count_not_evidenced_is_unknown():
    """M2: the price is evidenced, the COUNT is not, so the row is Unknown.

    The pre-repair code kept the pre-reset count of 1,000,000 and delivered
    200,000 at P 1.50, understating supply against the honest 1,333,333 /
    266,666.  Neither number may appear: an unknown is never a guessed count.
    """
    series_key = "series_i2a_m2_count_unevidenced"
    instrument_id = SS.series_id(series_key)
    _id, instrument = reset_warrant(series_key, "preserve_aggregate_exercise_price",
                                    price="1.20", effective_at="2026-11-13T00:00:00Z")
    assert _id == instrument_id
    envelope, trace = reset_run(instrument_id, instrument, as_of="2026-11-20T00:00:00Z",
                                horizon_end="2026-11-20")
    unknown_id = f"reset_share_adjustment_not_evidenced_{instrument_id}_2026-11-13"
    row = rows(trace)[instrument_id]
    assert row["incremental_shares"] == "unknown"
    assert row["underlying_shares"] == "unknown"
    assert row["unknowns"] == [unknown_id]
    assert unknowns(envelope) == [unknown_id]
    # Neither the pre-reset count nor the cashless delivery it would produce is
    # reported as a delivered or a claimed number.
    assert envelope.incremental_issuance.status == "unknown"
    assert envelope.incremental_issuance.value is None
    assert envelope.as_converted_claims.status == "unknown"
    assert envelope.as_converted_claims.value is None


def test_m2_past_reset_count_evidenced_is_a_fact():
    """M2: with an admitted post-reset count term the adjusted count is a fact."""
    series_key = "series_i2a_m2_count_evidenced"
    instrument_id = SS.series_id(series_key)
    _id, instrument = reset_warrant(
        series_key, "preserve_aggregate_exercise_price", price="1.20",
        effective_at="2026-11-13T00:00:00Z",
        instruments_outstanding=SS.economic_term(
            instrument_id, "instruments_outstanding", "1333333",
            effective_at="2026-11-13T00:00:00Z"))
    assert _id == instrument_id
    envelope, trace = reset_run(instrument_id, instrument, as_of="2026-11-20T00:00:00Z",
                                horizon_end="2026-11-20")
    # Every figure below is derived here from the admitted term: the count is the
    # admitted 1,333,333 at one share each, and the cashless delivery nets the
    # spread of the admitted K 1.20 against the 2026-11-20 path point of 1.50.
    admitted_count = Fraction(1_333_333)
    shares_per_instrument = Fraction(1)
    claim = admitted_count * shares_per_instrument
    strike = Fraction(Decimal("1.20"))
    market = Fraction(Decimal("1.50"))
    delivery = claim * (market - strike) / market
    assert unknowns(envelope) == []
    assert claimed(envelope) == str(claim.numerator // claim.denominator)
    assert claimed(envelope) == "1333333"
    assert delivered(envelope) == str(delivery.numerator // delivery.denominator)
    assert delivered(envelope) == "266666"
    row = rows(trace)[instrument_id]["variable_terms"]
    assert row["past_reset"] == "2026-11-13"
    assert row["past_reset_count_2026-11-13"] == "instruments_outstanding"
    assert row["contract_price"] == "1.2"


def test_fx_reset_set_to_lesser_of_current_and_market_keeps_the_lower_price():
    instrument_id, instrument = reset_warrant("series_i2a_fx_rlesser", "none", price="1.10",
                                              rule="set_to_lesser_of_current_and_market")
    envelope, trace = reset_run(instrument_id, instrument)
    assert rows(trace)[instrument_id]["variable_terms"]["adjusted_price"] == "1.1"
    assert delivered(envelope) == "266666"


# ---------------------------------------------------------------------------
# §4 — the anti-dilution rows (CP 1.00, existing 10,000,000, 2,000,000 at 0.72)
# ---------------------------------------------------------------------------


AD_HORIZON = dict(as_of=AS_OF, horizon_end=HORIZON_END, price=fixed_price("0.90"),
                  discount_rate="0.20",
                  other_assumptions=((vt.DILUTIVE_ISSUANCE_SHARES, "2000000"),))


def ad_run(instrument_id, instrument, **over):
    assumptions = dict(AD_HORIZON)
    assumptions.update(over)
    return run([(instrument_id, instrument)], [conversion(instrument_id)], **assumptions)


def test_fx_anti_dilution_weighted_average_narrow():
    instrument_id, instrument = anti_dilution_note("series_i2a_fx_adnarrow", "weighted_average_narrow")
    envelope, trace = ad_run(instrument_id, instrument)
    assert delivered(envelope) == "1048951"
    row = rows(trace)[instrument_id]["variable_terms"]
    assert row["anti_dilution_price"] == "143/150"
    assert row["adjusted_price"] == "143/150"
    assert row["anti_dilution_base"] == "10000000"
    assert row["anti_dilution_equivalent_shares"] == "1440000"


def test_fx_anti_dilution_weighted_average_narrow_with_four_place_rounding():
    instrument_id, instrument = anti_dilution_note("series_i2a_fx_adround", "weighted_average_narrow",
                                                   rounding=c.Rounding(4, "half_up"))
    envelope, trace = ad_run(instrument_id, instrument)
    assert delivered(envelope) == "1048987"
    assert rows(trace)[instrument_id]["variable_terms"]["adjusted_price"] == "0.9533"


def test_fx_anti_dilution_full_ratchet():
    instrument_id, instrument = anti_dilution_note("series_i2a_fx_adratchet", "full_ratchet")
    envelope, trace = ad_run(instrument_id, instrument)
    assert delivered(envelope) == "1388888"
    assert rows(trace)[instrument_id]["variable_terms"]["adjusted_price"] == "0.72"


def test_fx_anti_dilution_an_issuance_at_1_05_is_not_triggered():
    instrument_id, instrument = anti_dilution_note("series_i2a_fx_adhi", "full_ratchet")
    envelope, trace = ad_run(instrument_id, instrument,
                             other_assumptions=((vt.DILUTIVE_ISSUANCE_SHARES, "2000000"),
                                                (vt.DILUTIVE_ISSUANCE_PRICE, "1.05")))
    assert delivered(envelope) == "1000000"
    assert vt.BLOCKER_ANTI_DILUTION_NOT_TRIGGERED in rows(trace)[instrument_id]["blockers"]
    assert rows(trace)[instrument_id]["variable_terms"]["anti_dilution_triggered"] == "false"


def test_fx_anti_dilution_broad_without_a_resolution_is_unknown():
    instrument_id, instrument = anti_dilution_note("series_i2a_fx_adbroad", "weighted_average_broad")
    envelope, _trace = ad_run(instrument_id, instrument)
    assert envelope.incremental_issuance.status == "unknown"
    assert unknowns(envelope) == [f"anti_dilution_broad_base_{instrument_id}"]


def test_fx_anti_dilution_broad_with_a_resolution_uses_the_stated_base():
    instrument_id, instrument = anti_dilution_note("series_i2a_fx_adbroad2", "weighted_average_broad")
    resolved = resolution(f"broad_base_{instrument_id}", "20000000")
    envelope, trace = ad_run(instrument_id, instrument, unknown_resolutions=(resolved,))
    assert rows(trace)[instrument_id]["variable_terms"]["anti_dilution_base"] == "20000000"
    assert rows(trace)[instrument_id]["variable_terms"]["anti_dilution_price"] == "268/275"
    assert delivered(envelope) == "1026119"


def test_s2_5_the_issuance_is_labelled_a_scenario_assumption_in_the_trace():
    instrument_id, instrument = anti_dilution_note("series_i2a_fx_adassumed", "full_ratchet")
    _envelope, trace = ad_run(instrument_id, instrument)
    row = rows(trace)[instrument_id]["variable_terms"]
    assert row["anti_dilution_issuance_is_a_scenario_assumption"] == "true"
    assert row["dilutive_issuance_price"] == "0.72"


# ---------------------------------------------------------------------------
# §4 — the accretion rows (1,000,000 at 10%, CP 1.00, 2026-01-01 → 2026-07-01)
# ---------------------------------------------------------------------------

ACCRUAL_HORIZON = dict(as_of="2026-01-01T00:00:00Z", horizon_start="2026-01-01",
                       horizon_end="2026-07-01", price=fixed_price("1.00"))

ACCRETION_ROWS = [
    ("simple_actual_365", dict(day_count="actual_365", compounding="simple"), "1049589"),
    ("simple_actual_360", dict(day_count="actual_360", compounding="simple"), "1050277"),
    ("periodic_three_month", dict(day_count="actual_365", compounding="periodic", period_months=3),
     "1050203"),
    ("simple_thirty_360", dict(day_count="thirty_360", compounding="simple"), "1050000"),
]


@pytest.mark.parametrize("name,kwargs,shares", ACCRETION_ROWS, ids=[row[0] for row in ACCRETION_ROWS])
def test_fx_accretion_row(name, kwargs, shares):
    instrument_id, instrument = accruing_preferred(f"series_i2a_fx_ac_{name}", **kwargs)
    envelope, trace = run([(instrument_id, instrument)], [conversion(instrument_id)], **ACCRUAL_HORIZON)
    assert delivered(envelope) == shares
    assert rows(trace)[instrument_id]["variable_terms"]["amount"] == "1000000"


def test_fx_accretion_an_evidenced_accrued_amount_continues_from_its_own_date():
    instrument_id, instrument = accruing_preferred("series_i2a_fx_ac_evidenced", "actual_365", "simple",
                                                   accrued="24657.53")
    envelope, trace = run([(instrument_id, instrument)], [conversion(instrument_id)], **ACCRUAL_HORIZON)
    assert delivered(envelope) == "1049589"
    row = rows(trace)[instrument_id]["variable_terms"]
    assert row["accrued_amount_evidenced"] == "24657.53"
    assert row["accrued_amount_evidenced_at"] == "2026-04-01"


def test_m1_supply_periodic_evidenced_claim():
    """M1 through ``evaluate_supply``: the claim at CP 1.00 is 1,050,203 shares.

    The evidenced 12,328.77 is stated at 2026-02-15, in the middle of the anchored
    Q1 period, so it re-bases the balance and never moves the grid.  The pre-repair
    code compounded 02-15 -> 05-15 plus a 47-day stub and claimed 1,049,889.
    """
    instrument_id, instrument = accruing_preferred(
        "series_i2a_m1_supply", "actual_365", "periodic", period_months=3,
        accrued="12328.77", accrued_at="2026-02-15T00:00:00Z")
    envelope, trace = run([(instrument_id, instrument)], [conversion(instrument_id)], **ACCRUAL_HORIZON)
    rate = Fraction(1, 10)
    balance = Fraction(1_000_000) + Fraction(Decimal("12328.77"))     # B at 2026-02-15
    opening = balance / (1 + rate * Fraction(45, 365))                # 2026-01-01 -> 2026-02-15
    at_april = balance + opening * rate * Fraction(45, 365)           # 2026-02-15 -> 2026-04-01
    claim = at_april * (1 + rate * Fraction(91, 365))                 # 2026-04-01 -> 2026-07-01
    assert claimed(envelope) == str(claim.numerator // claim.denominator)
    assert claimed(envelope) == "1050203"
    assert delivered(envelope) == "1050203"
    row = rows(trace)[instrument_id]["variable_terms"]
    assert row["accrual_period_grid_anchored_at"] == "2026-01-01"
    assert row["accrual_evidenced_period_start"] == "2026-01-01"
    assert row["accrued_amount_evidenced_at"] == "2026-02-15"


def test_fx_accretion_converts_with_principal_false_converts_principal_only():
    instrument_id, instrument = accruing_preferred("series_i2a_fx_ac_noconv", "actual_365", "simple",
                                                   converts=False)
    envelope, trace = run([(instrument_id, instrument)], [conversion(instrument_id)], **ACCRUAL_HORIZON)
    assert delivered(envelope) == "1000000"
    assert rows(trace)[instrument_id]["variable_terms"][vt.TRACE_ACCRUED_NOT_CONVERTED] == "3620000/73"


# ---------------------------------------------------------------------------
# §4 — the exchange-cap rows (the lowest_daily 10-day claim of 1,250,000)
# ---------------------------------------------------------------------------


def test_fx_exchange_cap_700000_with_200000_issued_delivers_500000():
    instrument_id, instrument = market_note("series_i2a_fx_cap", "lowest_daily", 10,
                                            exchange_cap_shares="700000",
                                            shares_issued_under_instrument="200000")
    envelope, trace = run([(instrument_id, instrument)], [conversion(instrument_id)])
    row = rows(trace)[instrument_id]
    assert delivered(envelope) == "500000"
    assert claimed(envelope) == "1250000"
    assert row["variable_terms"]["blocked_by_exchange_cap"] == "750000"
    assert vt.BLOCKER_SHAREHOLDER_APPROVAL_REQUIRED in row["blockers"]


def test_fx_exchange_cap_with_shareholder_approval_delivers_the_whole_claim():
    instrument_id, instrument = market_note("series_i2a_fx_capapproved", "lowest_daily", 10,
                                            exchange_cap_shares="700000",
                                            shares_issued_under_instrument="200000",
                                            shareholder_approval_obtained=True)
    envelope, trace = run([(instrument_id, instrument)], [conversion(instrument_id)])
    assert delivered(envelope) == "1250000"
    assert rows(trace)[instrument_id]["variable_terms"]["shareholder_approval_obtained"] == "true"
    assert "blockers" not in rows(trace)[instrument_id]


def test_fx_exchange_cap_fully_used_delivers_zero_and_keeps_the_claim():
    instrument_id, instrument = market_note("series_i2a_fx_capreached", "lowest_daily", 10,
                                            exchange_cap_shares="700000",
                                            shares_issued_under_instrument="700000")
    envelope, trace = run([(instrument_id, instrument)], [conversion(instrument_id)])
    row = rows(trace)[instrument_id]
    assert delivered(envelope) == "0"
    assert claimed(envelope) == "1250000"
    assert vt.BLOCKER_EXCHANGE_CAP_REACHED in row["blockers"]
    assert row["variable_terms"]["blocked_by_exchange_cap"] == "1250000"


def test_s0_4_unknown_never_zero_or_unbounded_an_unstated_issued_count():
    instrument_id, instrument = market_note("series_i2a_fx_capunknown", "lowest_daily", 10,
                                            exchange_cap_shares="700000")
    envelope, _trace = run([(instrument_id, instrument)], [conversion(instrument_id)])
    assert envelope.incremental_issuance.status == "unknown"
    assert f"shares_issued_under_instrument_{instrument_id}" in unknowns(envelope)
    assert claimed(envelope) == "1250000"


def test_s2_9_the_cap_basis_is_scenario_incremental_issuance():
    instrument_id, instrument = market_note("series_i2a_fx_capbasis", "lowest_daily", 10,
                                            exchange_cap_shares="700000",
                                            shares_issued_under_instrument="200000")
    terms = {term.name: term for term in instrument.economic_terms}
    assert terms["exchange_cap_shares"].value.share_basis == "scenario_incremental_issuance"
    assert terms["shares_issued_under_instrument"].value.share_basis == "issued_and_outstanding"
    assert instrument_id == SS.series_id("series_i2a_fx_capbasis")


# ---------------------------------------------------------------------------
# §4 — the settlement-branch rows (principal 1,000,000, CP 5.00)
# ---------------------------------------------------------------------------

BRANCH_ROWS = [
    ("7.50", "physical", "200000", "no_cash", None),
    ("7.50", "net_share", "66666", "repayment", "1000000"),
    ("7.50", "cash", "0", "repayment", "1500000"),
    ("4.00", "net_share", "0", "repayment", "800000"),
]


@pytest.mark.parametrize("price,settlement,shares,cash_kind,cash_amount", BRANCH_ROWS,
                         ids=[f"{row[0]}_{row[1]}" for row in BRANCH_ROWS])
def test_fx_settlement_branch_row(price, settlement, shares, cash_kind, cash_amount):
    instrument_id, instrument = branching_note(f"series_i2a_fx_sb_{price}_{settlement}")
    envelope, trace = run([(instrument_id, instrument)], [conversion(instrument_id, settlement)],
                          price=fixed_price(price))
    assert delivered(envelope) == shares
    assert claimed(envelope) == "200000"
    row = rows(trace)[instrument_id]
    assert row["variable_terms"]["settlement_branch_elected"] == settlement
    effect = cash(envelope)[instrument_id]
    assert effect.kind == cash_kind
    if cash_amount is None:
        assert str(effect.gross.value) == "0"
    else:
        assert str(effect.gross.value) == cash_amount


def test_fx_selecting_a_settlement_the_branches_do_not_admit_is_unknown():
    instrument_id, instrument = branching_note("series_i2a_fx_sbbad", branches=("cash", "net_share"))
    envelope, _trace = run([(instrument_id, instrument)], [conversion(instrument_id, "physical")],
                           price=fixed_price("7.50"))
    assert envelope.incremental_issuance.status == "unknown"
    assert unknowns(envelope) == [f"settlement_not_permitted_{instrument_id}"]


def test_s0_5_only_the_elected_branch_reaches_the_envelope():
    instrument_id, instrument = branching_note("series_i2a_fx_sbcash")
    envelope, trace = run([(instrument_id, instrument)], [conversion(instrument_id, "cash")],
                          price=fixed_price("7.50"))
    assert delivered(envelope) == "0"
    assert str(cash(envelope)[instrument_id].gross.value) == "1500000"
    elected = [item for item in trace["alternatives"] if item["elected"]]
    assert [item["branch"] for item in elected] == ["cash"]


# ---------------------------------------------------------------------------
# §4 — the conversion-condition rows (Path V, CP 1.00, ≥130% of CP, 9 of 10)
# ---------------------------------------------------------------------------


def test_fx_condition_required_5_of_10_is_met_and_delivers():
    instrument_id, instrument = conditioned_note("series_i2a_fx_ccmet", 5, 10)
    envelope, trace = run([(instrument_id, instrument)], [conversion(instrument_id)])
    assert delivered(envelope) == "1000000"
    assert rows(trace)[instrument_id]["variable_terms"]["conversion_condition"] == "met"


def test_fx_condition_required_10_of_10_is_not_met_delivers_zero_and_keeps_the_claim():
    instrument_id, instrument = conditioned_note("series_i2a_fx_ccnotmet", 10, 10)
    envelope, trace = run([(instrument_id, instrument)], [conversion(instrument_id)])
    assert delivered(envelope) == "0"
    assert claimed(envelope) == "1000000"
    assert GUARD_CONDITION_NOT_MET in rows(trace)[instrument_id]["guards"]


def test_s0_4_unknown_never_zero_or_unbounded_a_30_day_window_is_not_evaluable():
    instrument_id, instrument = conditioned_note("series_i2a_fx_cc30", 5, 30)
    envelope, trace = run([(instrument_id, instrument)], [conversion(instrument_id)])
    assert envelope.incremental_issuance.status == "unknown"
    assert unknowns(envelope) == [f"conversion_condition_{instrument_id}"]
    assert rows(trace)[instrument_id]["variable_terms"]["conversion_condition"] == "not_evaluable"
    assert claimed(envelope) == "1000000"


def test_fx_a_30_day_window_listed_in_conditions_assumed_met_is_evaluated_as_met():
    instrument_id, instrument = conditioned_note("series_i2a_fx_cc30a", 5, 30)
    envelope, trace = run([(instrument_id, instrument)],
                          [conversion(instrument_id, "cashless",
                                      assumed_met=(f"conversion_condition_{instrument_id}",))])
    assert delivered(envelope) == "1000000"
    row = rows(trace)[instrument_id]
    assert row["variable_terms"]["conversion_condition"] == "assumed_met"
    assert row["variable_terms"]["conversion_condition_is_a_scenario_assumption"] == "true"
    assert supply_module.BLOCKER_CONDITION_ASSUMED_MET in row["blockers"]


# ---------------------------------------------------------------------------
# §5 — the L172 reference cases, end to end
# ---------------------------------------------------------------------------


def test_l172_variable_price_note():
    """A variable-price convertible note: 80% of the lowest daily close over 10 days."""
    instrument_id, instrument = variable_note(
        "series_l172_variable_note",
        V.formula([V.market("lowest_daily", 10, percent="80")], floor_basis="none_in_complete_agreement"))
    envelope, trace = run([(instrument_id, instrument)], [conversion(instrument_id)])
    assert delivered(envelope) == "1250000"
    assert claimed(envelope) == "1250000"
    row = rows(trace)[instrument_id]
    assert row["variable_terms"]["contract_price"] == "0.8"
    assert row["evaluation_order"] == list(EVALUATION_ORDER)
    assert trace["maximum_issuable"][instrument_id]["state"] == "unbounded_by_contract"
    assert str(cash(envelope)[instrument_id].gross.value) == "0"


def test_l172_reset_warrant():
    """A reset warrant: 1,000,000 warrants at K 1.60, reset to market on 2026-11-13."""
    instrument_id, instrument = reset_warrant("series_l172_reset_warrant",
                                              "preserve_aggregate_exercise_price")
    envelope, trace = reset_run(instrument_id, instrument)
    assert delivered(envelope) == "266666"
    row = rows(trace)[instrument_id]
    assert row["variable_terms"]["adjusted_price"] == "1.2"
    assert row["variable_terms"]["reset_applied_2026-11-13"] == "1.2"
    assert str(cash(envelope)[instrument_id].gross.value) == "0"


def test_l172_convertible_preferred_accrued():
    """Convertible preferred, stated value 1,000,000, simple actual_365 accrual."""
    instrument_id, instrument = accruing_preferred("series_l172_preferred", "actual_365", "simple")
    envelope, trace = run([(instrument_id, instrument)], [conversion(instrument_id)], **ACCRUAL_HORIZON)
    assert delivered(envelope) == "1049589"
    assert claimed(envelope) == "1049589"
    row = rows(trace)[instrument_id]
    assert row["variable_terms"]["accrued_amount"] == "3620000/73"
    assert row["variable_terms"]["amount_owed"] == "76620000/73"
    assert row["variable_terms"]["amount"] == "1000000"
    assert str(cash(envelope)[instrument_id].gross.value) == "0"


# ---------------------------------------------------------------------------
# §5 — determinism
# ---------------------------------------------------------------------------


def test_determinism_same_inputs_give_an_identical_trace_and_receipt():
    instrument_id, instrument = market_note("series_i2a_determinism", "lowest_daily", 10,
                                            exchange_cap_shares="700000",
                                            shares_issued_under_instrument="200000")
    instruments = SS.instrument_set((instrument_id, instrument))
    basis = SS.basis()
    scenario = path_scenario([conversion(instrument_id)])
    first_envelope, first_trace = evaluate(instruments, basis, scenario)
    second_envelope, second_trace = evaluate(instruments, basis, scenario)
    assert first_trace == second_trace
    assert c.sha256_of(first_trace) == c.sha256_of(second_trace)
    assert first_envelope.receipt.receipt_id == second_envelope.receipt.receipt_id
    assert first_envelope.receipt.rule_digest == second_envelope.receipt.rule_digest
    assert first_envelope.state_id == second_envelope.state_id
    assert c.sha256_of(first_envelope.as_record()) == c.sha256_of(second_envelope.as_record())


def test_determinism_an_unknown_envelope_is_reproducible_too():
    instrument_id, instrument = market_note("series_i2a_determinism_unknown", "lowest_daily", 20)
    instruments = SS.instrument_set((instrument_id, instrument))
    scenario = path_scenario([conversion(instrument_id)])
    first, first_trace = evaluate(instruments, SS.basis(), scenario)
    second, second_trace = evaluate(instruments, SS.basis(), scenario)
    assert unknowns(first) == unknowns(second)
    assert first_trace == second_trace


def test_determinism_two_entry_points_agree_on_one_evaluation():
    instrument_id, instrument = branching_note("series_i2a_agree")
    instruments = SS.instrument_set((instrument_id, instrument))
    basis = SS.basis()
    scenario = path_scenario([conversion(instrument_id, "net_share")], price=fixed_price("7.50"))
    envelope = evaluate_supply(instruments, basis, scenario)
    trace = supply_trace(instruments, basis, scenario)
    V.checked(envelope.as_record(), "supply_envelope")
    assert trace["state_id"] == envelope.state_id
    assert c.sha256_of(envelope.as_record()) == c.sha256_of(evaluate_supply(instruments, basis, scenario).as_record())


# ---------------------------------------------------------------------------
# Audit r1 — M3, M4 and S2-S6 through ``evaluate_supply``
# ---------------------------------------------------------------------------


def formula_note(series_key: str, built: c.PriceFormula, *, value: str | None = None, **extra):
    """A convertible note whose conversion price is a formula, plus any I2 term.

    ``value`` states a KNOWN price alongside an all-fixed formula, which is what
    §1.4 permits and what audit r1 S3 is about.
    """
    instrument_id = SS.series_id(series_key)
    # §1.4: an admitted price term carries a known value OR its verbatim formula.
    # A stated value therefore has no expression, and a market formula has one.
    price_term = V.price_formula_term(
        instrument_id, "conversion_price", built, value=value, expression=None
    ) if value is not None else V.price_formula_term(instrument_id, "conversion_price", built)
    terms = dict(
        principal_outstanding="1000000",
        cashless_exercise_permitted=True,
        conversion_price=price_term,
    )
    terms.update(extra)
    return SS.make_instrument(series_key, kind="convertible_note", **terms)


def test_m3_warrant_settlement_branches_named_unknown():
    """M3: a warrant carrying settlement_branches is a NAMED unknown.

    The pre-repair row went unknown with an EMPTY unknown list, because I2 reads
    the branches term for every action but prices branches for a conversion only,
    and a warrant has no amount.  Nothing is raised: the term is valid.
    """
    series_key = "series_i2a_m3_warrant_branches"
    instrument_id = SS.series_id(series_key)
    built = c.SettlementBranches("settlement_branches", ("cash", "physical"), "issuer")
    _id, instrument = SS.make_instrument(
        series_key, kind="warrant", instruments_outstanding="1000000", shares_per_instrument="1",
        exercise_price="1.00", cashless_exercise_permitted=True,
        settlement_branches=V.structure_term(instrument_id, "settlement_branches", built))
    assert _id == instrument_id
    envelope, trace = run([(instrument_id, instrument)],
                          [SS.selection(instrument_id, "warrant_exercise", "cashless")],
                          price=fixed_price("7.50"))
    unknown_id = f"settlement_branches_not_evaluated_{instrument_id}"
    row = rows(trace)[instrument_id]
    assert row["incremental_shares"] == "unknown"
    assert row["unknowns"] == [unknown_id]
    assert unknowns(envelope) == [unknown_id]
    assert envelope.incremental_issuance.value is None
    # A25: the claim, which the branches term does not touch, still survives.
    assert claimed(envelope) == "1000000"
    assert trace["alternatives"] == []


def test_m4_full_ratchet_below_formula_floor_maximum_unbounded():
    """M4: the reported maximum must bound every delivered count.

    The formula states a 0.50 floor, but §2.5 anti-dilution applies no floor, so
    a full ratchet to a 0.40 issuance delivers 2,500,000 shares.  The pre-repair
    trace reported a ``bounded_by_floor`` maximum of 2,000,000 — a wrong number
    that its own row contradicted.
    """
    built = V.formula([V.market("lowest_daily", 10)], floor_basis="stated", floor="0.50",
                      below_floor="floor_applies")
    series_key = "series_i2a_m4_ratchet"
    ratchet_term = V.structure_term(
        SS.series_id(series_key), "anti_dilution",
        c.AntiDilution("anti_dilution", "conversion_price", "full_ratchet",
                       price_rounding=None, share_adjustment="none"))
    instrument_id, instrument = formula_note(series_key, built, anti_dilution=ratchet_term)
    envelope, trace = run(
        [(instrument_id, instrument)], [conversion(instrument_id)],
        other_assumptions=((vt.DILUTIVE_ISSUANCE_SHARES, "2000000"),
                           (vt.DILUTIVE_ISSUANCE_PRICE, "0.40")))
    ratchet = Fraction(Decimal("0.40"))
    expected = Fraction(1_000_000) / ratchet
    assert delivered(envelope) == str(expected.numerator // expected.denominator)
    assert delivered(envelope) == "2500000"
    body = trace["maximum_issuable"][instrument_id]
    assert body["state"] == "unbounded_by_contract"
    assert body["floor_basis"] == "stated"
    assert body[vt.TRACE_ANTI_DILUTION_BYPASSES_FLOOR] == "full_ratchet"
    assert body[vt.TRACE_AUTHORIZED_SHARES_NOT_EVALUATED] == "true"
    assert "shares" not in body
    assert "inf" not in repr(body).lower()


def test_s2_cap_not_listed_when_approval_obtained():
    """S2: an exchange cap that shareholder approval has lifted is not a limit."""
    instrument_id, instrument = market_note(
        "series_i2a_s2_approved", "lowest_daily", 10,
        exchange_cap_shares="700000", shares_issued_under_instrument="200000",
        shareholder_approval_obtained=True)
    envelope, trace = run([(instrument_id, instrument)], [conversion(instrument_id)])
    body = trace["maximum_issuable"][instrument_id]
    assert body["state"] == "unbounded_by_contract"
    assert body["binding_limits"] == []
    # The cap really is lifted: the whole claim is delivered.
    assert delivered(envelope) == "1250000"
    assert rows(trace)[instrument_id]["variable_terms"]["shareholder_approval_obtained"] == "true"


def test_s2_issued_under_instrument_not_a_limit():
    """S2: the issued count is the cap's USAGE, not a second limit."""
    instrument_id, instrument = market_note(
        "series_i2a_s2_usage", "lowest_daily", 10,
        exchange_cap_shares="700000", shares_issued_under_instrument="200000")
    envelope, trace = run([(instrument_id, instrument)], [conversion(instrument_id)])
    body = trace["maximum_issuable"][instrument_id]
    assert body["binding_limits"] == ["exchange_cap_shares"]
    assert "shares_issued_under_instrument" not in body["binding_limits"]
    # The usage stays in the row trace, where the cap arithmetic is visible, and
    # it still limits delivery to 700,000 - 200,000.
    row = rows(trace)[instrument_id]["variable_terms"]
    assert row["shares_issued_under_instrument"] == "200000"
    assert row["exchange_cap_remaining"] == "500000"
    assert delivered(envelope) == "500000"


def test_s2_authorized_shares_flagged_not_evaluated():
    """S2: authorized-share headroom is joined later, and the trace says so."""
    instrument_id, instrument = market_note(
        "series_i2a_s2_authorized", "lowest_daily", 10,
        exchange_cap_shares="700000", shares_issued_under_instrument="200000")
    _envelope, trace = run([(instrument_id, instrument)], [conversion(instrument_id)])
    body = trace["maximum_issuable"][instrument_id]
    assert body["state"] == "unbounded_by_contract"
    assert body[vt.TRACE_AUTHORIZED_SHARES_NOT_EVALUATED] == "true"
    assert "authorized_shares" not in body["binding_limits"]


def test_s3_fixed_value_respects_ceiling():
    """S3: a fixed known value still passes its own formula's ceiling.

    §1.4 lets an all-fixed formula carry a known value; the pre-repair row took
    the value and never ran §2.2, so a 0.90 ceiling on a 1.00 value was ignored.
    """
    built = V.formula([V.fixed("1.00")], ceiling="0.90")
    instrument_id, instrument = formula_note("series_i2a_s3_ceiling", built, value="1.00")
    envelope, trace = run([(instrument_id, instrument)], [conversion(instrument_id)])
    ceiling = Fraction(Decimal("0.90"))
    expected = Fraction(1_000_000) / ceiling
    row = rows(trace)[instrument_id]["variable_terms"]
    assert row["price_source"] == "price_formula"
    assert row["contract_price"] == "0.9"
    assert row["ceiling_reached"] == "true"
    assert row["price_term_also_states_a_value"] == "1.00"
    assert delivered(envelope) == str(expected.numerator // expected.denominator)
    assert delivered(envelope) == "1111111"


@pytest.mark.parametrize("key", [vt.DILUTIVE_ISSUANCE_SHARES, vt.DILUTIVE_ISSUANCE_PRICE],
                         ids=["shares", "price"])
@pytest.mark.parametrize("text", ["NaN", "inf", "1e5", "abc", "-1"])
def test_s4_dilutive_issuance_refusals(key, text):
    """S4: an issuance assumption is exact non-negative decimal text or it is refused.

    The pre-repair code parsed with ``Fraction(Decimal(str(text)))``, so "NaN" and
    "inf" died with a bare ValueError, "1e5" and "-1" were silently accepted, and
    none of them was a ContractViolation.
    """
    instrument_id, instrument = anti_dilution_note("series_i2a_s4_refusals", "full_ratchet")
    with pytest.raises(c.ContractViolation, match="dilutive_issuance"):
        ad_run(instrument_id, instrument, other_assumptions=((key, text),))


def test_s5_make_whole_not_applied_when_condition_not_met():
    """S5: no make-whole repayment is booked against a delivery of zero."""
    built = V.formula([V.market("lowest_daily", 10)], floor_basis="stated", floor="1.00",
                      below_floor="floor_applies_with_cash_make_whole")
    instrument_id, instrument = formula_note(
        "series_i2a_s5_notmet", built,
        conversion_condition=V.structure_term(
            SS.series_id("series_i2a_s5_notmet"), "conversion_condition", V.condition(10, 10)))
    envelope, trace = run([(instrument_id, instrument)], [conversion(instrument_id)])
    row = rows(trace)[instrument_id]
    assert row["variable_terms"]["conversion_condition"] == "not_met"
    assert row["variable_terms"]["floor_reached"] == "true"
    assert delivered(envelope) == "0"
    assert f"make_whole_amount_{instrument_id}" not in row["unknowns"]
    assert vt.BLOCKER_FLOOR_MAKE_WHOLE in row["blockers"]
    # The cash effect is the honest no-cash one, not an unknown repayment.
    effect = cash(envelope)[instrument_id]
    assert effect.kind == "no_cash"
    assert effect.gross.status == "known"
    assert str(effect.gross.value) == "0"
    assert str(effect.net.value) == "0"
    # The claim path runs BEFORE the condition (A25), so the envelope still names
    # the missing amount; the row, which books the cash, does not.
    assert unknowns(envelope) == [f"make_whole_amount_{instrument_id}"]
    assert claimed(envelope) == "1000000"


def test_s5_make_whole_ids_agree_row_and_envelope():
    """S5: when the make-whole applies, the row and the envelope name the same Unknown."""
    built = V.formula([V.market("lowest_daily", 10)], floor_basis="stated", floor="1.00",
                      below_floor="floor_applies_with_cash_make_whole")
    instrument_id, instrument = formula_note(
        "series_i2a_s5_agree", built,
        conversion_condition=V.structure_term(
            SS.series_id("series_i2a_s5_agree"), "conversion_condition", V.condition(5, 10)))
    envelope, trace = run([(instrument_id, instrument)], [conversion(instrument_id)])
    unknown_id = f"make_whole_amount_{instrument_id}"
    row = rows(trace)[instrument_id]
    assert row["variable_terms"]["conversion_condition"] == "met"
    assert row["variable_terms"]["floor_reached"] == "true"
    # The pre-repair row named nothing while the envelope named the make-whole.
    assert unknown_id in row["unknowns"]
    assert unknown_id in unknowns(envelope)
    assert set(row["unknowns"]) <= set(unknowns(envelope))
    assert delivered(envelope) == "1000000"
    effect = cash(envelope)[instrument_id]
    assert effect.kind == "repayment"
    assert effect.gross.status == "unknown"
    assert effect.gross.value is None
