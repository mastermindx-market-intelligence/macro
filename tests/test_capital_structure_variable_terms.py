"""SPEC_I2 §1, §2 and §4: the structured variable terms and their pure evaluators.

Every §4 row that a pure evaluator decides is asserted here with an exact
``Fraction`` or an exact integer — never approximately, never by a formatted
string.  Fixtures are hand-built in this file: no network, no ``data/`` read, no
filing text and no digest is hard-coded (every id is derived with
:func:`stable_id`).  The only float literals in this file are inside the
float-refusal tests, which pass a float and assert the refusal.

Three laws shape every assertion:

* an unknown stays an unknown — a window the path does not cover, a
  volume-weighted measure a price path cannot supply, an unevidenced past reset,
  an unestablished floor and a make-whole no term states each produce a NAMED
  ``Unknown``, never 0 and never a bound (§0 item 4);
* no floor is assumed — a floating price with no stated floor is
  ``unbounded_by_contract``, never a finite maximum and never infinity (A26,
  masterplan L231);
* nothing looks ahead — every price read uses only path points dated on or
  before the date being priced (§0 item 7).
"""
from __future__ import annotations

import dataclasses
import inspect
from datetime import date
from decimal import Decimal
from fractions import Fraction

import pytest

import tests.test_capital_structure_instrument_economics as IE
import tests.test_capital_structure_issuer_state_contracts as T
import tests.test_capital_structure_supply_scenarios as SS
from engine.capital_structure import issuer_state_contracts as c
from engine.capital_structure import supply_scenarios as supply_module
from engine.capital_structure import variable_terms as vt

INST = "instrument:cs:i2a"
HORIZON_END = "2026-07-01"
EFFECTIVE = SS.EFFECTIVE
AVAILABLE = SS.AVAILABLE
CLOSED = "closing_price"
VWAP = "daily_vwap"
PRICING_DATE = "2026-11-13"
PRINCIPAL = Fraction(1_000_000)

#: SPEC_I2 §4 Path V: closing prices, weekdays 2026-11-02 … 2026-11-13.
PATH_V = (
    ("2026-11-02", "1.50"),
    ("2026-11-03", "1.40"),
    ("2026-11-04", "1.60"),
    ("2026-11-05", "1.00"),
    ("2026-11-06", "1.30"),
    ("2026-11-09", "1.45"),
    ("2026-11-10", "1.55"),
    ("2026-11-11", "1.50"),
    ("2026-11-12", "1.60"),
    ("2026-11-13", "1.70"),
)


# ---------------------------------------------------------------------------
# Builders — exact structures, exact terms (imported, never copied, by §5)
# ---------------------------------------------------------------------------


def assert_supply_rows(trace: dict, envelope) -> None:
    """The two row invariants every emitted supply result must satisfy (M3, M4).

    * **M3** — a row whose status is unknown must NAME at least one Unknown, and
      every Unknown a row names must also be named by the envelope.  An anonymous
      unknown tells a reader nothing about what would resolve it (§0 item 4).
    * **M4** — a maximum reported as ``bounded_by_floor`` must actually bound what
      the row delivers, or the reported maximum is simply a wrong number (§2.3).
    """
    envelope_ids = {item.unknown_id for item in envelope.unknowns}
    maxima = trace.get("maximum_issuable", {})
    for row in trace["rows"]:
        is_unknown = row["incremental_shares"] == "unknown"
        if is_unknown:
            assert row["unknowns"], f"row {row['route_id']} is unknown and names no Unknown"
        for unknown_id in row["unknowns"]:
            assert unknown_id in envelope_ids, (
                f"row {row['route_id']} names {unknown_id!r}, which the envelope does not"
            )
        body = maxima.get(row["instrument_id"])
        if body is None or body.get("state") != "bounded_by_floor" or is_unknown:
            continue
        delivered_shares = int(row["incremental_shares"])
        assert delivered_shares <= int(body["shares"]), (
            f"row {row['route_id']} delivers {delivered_shares}, above the maximum "
            f"{body['shares']} reported for {row['instrument_id']}"
        )


def checked(record, kind: str, *, supply: tuple | None = None) -> dict:
    """The ONE shared helper: schema-validate every record this suite emits.

    ``supply`` is a ``(trace, envelope)`` pair.  When it is given, the row
    invariants of :func:`assert_supply_rows` (audit r1 M3 and M4) are enforced on
    it as well.  This suite emits contract records only — it builds no envelope —
    so the supply suite hands its result to this same helper from its own shared
    helper on every test, which is what makes the guard cover the whole suite.
    """
    c.validate_state_record(kind, record)
    SS.assert_no_float(record, kind)
    if supply is not None:
        assert_supply_rows(*supply)
    return record


def market(aggregation: str, lookback_days: int, *, percent: str = "80",
           window_end: str = "including_pricing_date", lowest_count: int | None = None,
           measure: str = CLOSED) -> c.PriceComponent:
    return c.PriceComponent(
        "price_component", "market", measure=measure, aggregation=aggregation,
        lookback_days=lookback_days, lowest_count=lowest_count,
        percent_of_measure=c.Quantity.known(percent, "percent"), window_end=window_end,
    )


def fixed(price: str) -> c.PriceComponent:
    return c.PriceComponent("price_component", "fixed", fixed_price=c.Quantity.known(price, "usd"))


def formula(components, *, combine: str = "single", floor_basis: str = "none_in_complete_agreement",
            floor: str | None = None, below_floor: str | None = None, ceiling: str | None = None,
            rounding: c.Rounding | None = None) -> c.PriceFormula:
    if floor_basis == "stated" and below_floor is None:
        below_floor = "floor_applies"
    return c.PriceFormula(
        "price_formula", combine, tuple(components), floor_basis,
        floor=c.Quantity.known(floor, "usd") if floor is not None else None,
        below_floor=below_floor,
        ceiling=c.Quantity.known(ceiling, "usd") if ceiling is not None else None,
        rounding=rounding,
    )


def structure_term(instrument_id: str, name: str, structure, *, effective_at: str = EFFECTIVE,
                   fact_origin: str = "adjudicated_gold", status: str = "admitted",
                   expression: str | None = None, term_id: str | None = None) -> c.EconomicTerm:
    """An admitted structure-only term; the id is derived, never invented."""
    return c.EconomicTerm(
        term_id=term_id or c.stable_id("econterm", {
            "instrument_id": instrument_id, "name": name, "value": None, "status": status,
            "expression": expression, "flag": None, "date_value": None, "effective_at": effective_at,
        }),
        instrument_id=instrument_id, name=name, status=status, value=None, flag=None,
        expression=expression, date_value=None, evidence=(T.ev(3),), fact_origin=fact_origin,
        interpretation_version="1.0.0", available_at=AVAILABLE, effective_at=effective_at,
        structure=structure,
    )


def price_formula_term(instrument_id: str, name: str, structure: c.PriceFormula, *, value: str | None = None,
                       expression: str = "80% of the lowest daily close", effective_at: str = EFFECTIVE,
                       fact_origin: str = "adjudicated_gold") -> c.EconomicTerm:
    """A price term carrying a ``PriceFormula`` (§1.3 last line)."""
    term = SS.economic_term(instrument_id, name, value, expression=expression,
                            effective_at=effective_at, fact_origin=fact_origin)
    return dataclasses.replace(term, structure=structure)


def reset_event(reset_date: str = "2026-11-13", rule: str = "set_to_market", *, floor: str | None = None,
                share_adjustment: str = "none", percent: str = "100") -> c.ResetEvent:
    return c.ResetEvent(reset_date, rule, market("single_day", 1, percent=percent),
                        c.Quantity.known(floor, "usd") if floor is not None else None, share_adjustment)


def accrual(day_count: str = "actual_365", compounding: str = "simple", *, rate: str = "10",
            start: str = "2026-01-01", converts: bool = True, period_months: int | None = None) -> c.Accrual:
    return c.Accrual("accrual", c.Quantity.known(rate, "percent"), day_count, compounding, start,
                     converts, period_months=period_months)


def condition(required_days: int = 5, window_days: int = 10, *, comparison: str = "at_or_above",
              threshold: str = "130", measure: str = CLOSED,
              window_end: str = "including_pricing_date") -> c.ConversionCondition:
    return c.ConversionCondition("conversion_condition", required_days, window_days, comparison,
                                 "percent_of_conversion_price", c.Quantity.known(threshold, "percent"),
                                 measure, window_end)


def issuance(shares: str = "2000000", price: str = "0.72") -> dict:
    return {vt.DILUTIVE_ISSUANCE_SHARES: Fraction(Decimal(shares)),
            vt.DILUTIVE_ISSUANCE_PRICE: Fraction(Decimal(price))}


def value_term(name: str, value: str | None, *, instrument_id: str = INST,
               effective_at: str = EFFECTIVE, status: str = "admitted") -> c.EconomicTerm:
    return SS.economic_term(instrument_id, name, value, effective_at=effective_at, status=status)


# ---------------------------------------------------------------------------
# §1 — the contract delta
# ---------------------------------------------------------------------------


def test_s1_1_state_contract_version_is_the_next_minor():
    # X0 (transaction observations) landed first as 2.2.0, so I2 shipped as
    # 2.3.0; S0 (scenario composition) is the next purely additive minor and the
    # contract version this lane reads, so the literal follows the live value.
    assert c.STATE_CONTRACT_VERSION == "capital-structure-state-contracts/2.4.0"


def test_s1_2_physical_settlement_is_appended_last():
    assert c.SETTLEMENTS[-1] == "physical"
    assert c.SETTLEMENTS[:-1] == ("cash", "cashless", "net_share", "pre_funded", "unknown")


def test_s1_3_economic_term_names_gain_the_nine_i2_names_in_order():
    added = ("price_reset", "conversion_condition", "settlement_branches", "anti_dilution",
             "accrual_terms", "exchange_cap_shares", "shares_issued_under_instrument",
             "shareholder_approval_obtained", "accrued_amount_outstanding")
    tail = c.ECONOMIC_TERM_NAMES[-len(added):]
    assert tail == added


def test_s1_3_the_new_value_names_carry_their_unit_and_basis():
    assert c.ECONOMIC_TERM_UNITS["exchange_cap_shares"] == ("shares", "scenario_incremental_issuance")
    assert c.ECONOMIC_TERM_UNITS["shares_issued_under_instrument"] == ("shares", "issued_and_outstanding")
    assert c.ECONOMIC_TERM_UNITS["accrued_amount_outstanding"] == ("usd", None)
    assert "shareholder_approval_obtained" in c.ECONOMIC_TERM_FLAG_NAMES
    assert "accrued_amount_outstanding" in c.ECONOMIC_TERM_EFFECTIVE_NAMES


def test_s1_4_structure_is_the_last_field_of_economic_term():
    assert [field.name for field in dataclasses.fields(c.EconomicTerm)][-1] == "structure"


def test_s1_5_thirty_360_follows_the_isda_bond_basis():
    # D1 = 31 becomes 30; D2 = 31 becomes 30 when D1 is 30 or 31.
    assert vt._thirty_360_days(date(2026, 1, 31), date(2026, 7, 31)) == 180
    assert vt._thirty_360_days(date(2026, 1, 1), date(2026, 7, 1)) == 180
    assert vt._thirty_360_days(date(2026, 2, 28), date(2026, 3, 31)) == 33


def test_s1_5_every_structure_kind_is_a_literal_discriminator():
    kinds = {
        c.PriceFormula("price_formula", "single", (fixed("1.00"),), "not_established"): "price_formula",
        c.ResetSchedule("reset_schedule", "exercise_price", (reset_event(),)): "reset_schedule",
        condition(): "conversion_condition",
        c.SettlementBranches("settlement_branches", ("physical", "cash"), "issuer"): "settlement_branches",
        c.AntiDilution("anti_dilution", "conversion_price", "full_ratchet"): "anti_dilution",
        accrual(): "accrual",
    }
    for structure, kind in kinds.items():
        assert structure.kind == kind


def test_s1_6_structure_round_trips_through_as_record_and_the_schema():
    term = structure_term(INST, "price_reset", c.ResetSchedule("reset_schedule", "exercise_price", (reset_event(),)))
    record = checked(term.as_record(), "economic_term")
    assert record["structure"]["kind"] == "reset_schedule"
    assert c.structure_from_record(record["structure"]) == term.structure


@pytest.mark.parametrize("name,structure", [
    ("price_reset", lambda: c.ResetSchedule("reset_schedule", "exercise_price", (reset_event(),))),
    ("conversion_condition", condition),
    ("settlement_branches", lambda: c.SettlementBranches("settlement_branches", ("physical", "cash"), "issuer")),
    ("anti_dilution", lambda: c.AntiDilution("anti_dilution", "conversion_price", "full_ratchet")),
    ("accrual_terms", accrual),
    ("conversion_price", lambda: formula([market("lowest_daily", 10)])),
    ("exercise_price", lambda: formula([market("lowest_daily", 10)])),
])
def test_s1_6_every_structured_term_round_trips(name, structure):
    built = structure()
    if name in c.ECONOMIC_TERM_STRUCTURE_NAMES:
        term = structure_term(INST, name, built)
    else:
        term = price_formula_term(INST, name, built)
    record = checked(term.as_record(), "economic_term")
    assert c.structure_from_record(record["structure"]) == built


# ---------------------------------------------------------------------------
# §1.4 — the structure/name mismatch refusals
# ---------------------------------------------------------------------------


def test_s1_4_an_admitted_structure_only_name_requires_its_structure():
    with pytest.raises(c.ContractViolation, match="carries its structure"):
        SS.economic_term(INST, "price_reset", None, fact_origin="adjudicated_gold")


def test_s1_4_a_structure_must_match_the_name_it_is_attached_to():
    with pytest.raises(c.ContractViolation, match="carries a ResetSchedule"):
        structure_term(INST, "price_reset", c.AntiDilution("anti_dilution", "exercise_price", "full_ratchet"))


def test_s1_4_a_price_term_refuses_a_non_price_formula_structure():
    with pytest.raises(c.ContractViolation, match="carries a PriceFormula"):
        price_formula_term(INST, "conversion_price", c.ResetSchedule("reset_schedule", "conversion_price", (reset_event(),)))


def test_s1_4_a_structure_only_name_carries_no_quantity():
    schedule = c.ResetSchedule("reset_schedule", "exercise_price", (reset_event(),))
    with pytest.raises(c.ContractViolation, match="carries no quantity"):
        dataclasses.replace(structure_term(INST, "price_reset", schedule),
                            value=c.Quantity.unknown("usd"))


def test_s1_4_a_structure_only_name_carries_no_flag():
    schedule = c.ResetSchedule("reset_schedule", "exercise_price", (reset_event(),))
    with pytest.raises(c.ContractViolation, match="carries a flag"):
        dataclasses.replace(structure_term(INST, "price_reset", schedule), flag=True)


def test_s1_4_only_an_admitted_term_carries_a_structure():
    schedule = c.ResetSchedule("reset_schedule", "exercise_price", (reset_event(),))
    with pytest.raises(c.ContractViolation, match="only an admitted term carries a structure"):
        structure_term(INST, "price_reset", schedule, status="unknown")


def test_s1_4_a_market_price_formula_requires_a_non_known_value():
    with pytest.raises(c.ContractViolation, match="a formula term carries no known value"):
        price_formula_term(INST, "conversion_price", formula([market("lowest_daily", 10)]), value="1.00")


def test_s1_4_an_all_fixed_formula_must_combine_single():
    with pytest.raises(c.ContractViolation, match="single"):
        formula([fixed("1.00"), fixed("1.10")], combine="lesser")


def test_s1_4_a_fixed_price_with_a_floor_is_still_one_fixed_component():
    built = formula([fixed("1.10")], floor_basis="stated", floor="1.00", below_floor="floor_applies")
    assert built.components == (fixed("1.10"),)
    assert built.floor_basis == "stated"


def test_s1_4_lesser_and_greater_need_two_components():
    with pytest.raises(c.ContractViolation):
        formula([market("lowest_daily", 10)], combine="lesser")


# ---------------------------------------------------------------------------
# §0 item 2 — pre-I2 records and digests are byte-identical
# ---------------------------------------------------------------------------


def test_s0_2_pre_i2_digests_byte_identical():
    """An EconomicTerm without a structure serialises exactly as it did at 2.1.0."""
    term = SS.economic_term(INST, "exercise_price", "1.60")
    record = term.as_record()
    assert "structure" not in record
    # The 2.1.0 shape: exactly the fields that existed before I2, in that order.
    assert list(record) == [
        "term_id", "instrument_id", "name", "status", "value", "flag", "expression", "date_value",
        "evidence", "fact_origin", "interpretation_version", "available_at", "effective_at",
    ]
    legacy = dataclasses.replace(term, structure=None)
    assert c.sha256_of(record) == c.sha256_of(legacy.as_record())
    assert term.term_id == legacy.term_id


def test_s0_2_a_term_with_a_structure_adds_exactly_one_key():
    plain = SS.economic_term(INST, "conversion_price", None, expression="80% of the lowest daily close")
    structured = dataclasses.replace(plain, structure=formula([market("lowest_daily", 10)]))
    assert set(structured.as_record()) - set(plain.as_record()) == {"structure"}


def test_s0_2_an_instrument_without_structure_keeps_its_digest():
    """No I2 term anywhere ⇒ the same instrument set digest as before I2."""
    instrument_id, instrument = SS.plain_warrant("series_i2a_identity")
    before = SS.instrument_set((instrument_id, instrument))
    rebuilt = SS.instrument_set((instrument_id, dataclasses.replace(
        instrument, economic_terms=tuple(dataclasses.replace(term, structure=None)
                                         for term in instrument.economic_terms))))
    checked(before.as_record(), "instrument_set")
    assert c.sha256_of(before.as_record()) == c.sha256_of(rebuilt.as_record())


# ---------------------------------------------------------------------------
# §0 item 3 — a float is refused everywhere
# ---------------------------------------------------------------------------


def test_s0_3_float_refused_price_component_percent():
    with pytest.raises(c.ContractViolation):
        c.PriceComponent("price_component", "market", measure=CLOSED, aggregation="lowest_daily",
                         lookback_days=10, percent_of_measure=c.Quantity.known(80.0, "percent"),
                         window_end="including_pricing_date")


def test_s0_3_float_refused_price_component_fixed_price():
    with pytest.raises(c.ContractViolation):
        c.PriceComponent("price_component", "fixed", fixed_price=c.Quantity.known(1.10, "usd"))


def test_s0_3_float_refused_price_component_lookback():
    with pytest.raises(c.ContractViolation):
        c.PriceComponent("price_component", "market", measure=CLOSED, aggregation="lowest_daily",
                         lookback_days=10.0, percent_of_measure=c.Quantity.known("80", "percent"),
                         window_end="including_pricing_date")


def test_s0_3_float_refused_price_formula_floor():
    with pytest.raises(c.ContractViolation):
        formula([market("lowest_daily", 10)], floor_basis="stated", floor=1.00)


def test_s0_3_float_refused_price_formula_ceiling():
    with pytest.raises(c.ContractViolation):
        c.PriceFormula("price_formula", "single", (market("lowest_daily", 10),),
                       "none_in_complete_agreement", ceiling=c.Quantity.known(2.0, "usd"))


def test_s0_3_float_refused_rounding_places():
    with pytest.raises(c.ContractViolation):
        c.Rounding(4.0, "half_up")


def test_s0_3_float_refused_reset_event_floor():
    with pytest.raises(c.ContractViolation):
        c.ResetEvent("2026-11-13", "set_to_market", market("single_day", 1, percent="100"),
                     c.Quantity.known(1.0, "usd"), "none")


def test_s0_3_float_refused_reset_schedule_record():
    record = c.ResetSchedule("reset_schedule", "exercise_price", (reset_event(),)).as_record()
    record["events"][0]["market"]["lookback_days"] = 1.0
    with pytest.raises(c.ContractViolation):
        c.structure_from_record(record)


def test_s0_3_float_refused_conversion_condition_record():
    record = condition().as_record()
    record["required_days"] = 5.0
    with pytest.raises(c.ContractViolation):
        c.structure_from_record(record)


def test_s0_3_float_refused_settlement_branches_record():
    record = c.SettlementBranches("settlement_branches", ("physical", "cash"), "issuer").as_record()
    record["elected_by"] = 1.0
    with pytest.raises(c.ContractViolation):
        c.structure_from_record(record)


def test_s0_3_float_refused_anti_dilution_rounding():
    with pytest.raises(c.ContractViolation):
        c.AntiDilution("anti_dilution", "conversion_price", "weighted_average_narrow",
                       price_rounding=c.Rounding(2.0, "half_up"))


def test_s0_3_float_refused_accrual_rate_and_period():
    with pytest.raises(c.ContractViolation):
        c.Accrual("accrual", c.Quantity.known(10.0, "percent"), "actual_365", "simple",
                  "2026-01-01", True)
    with pytest.raises(c.ContractViolation):
        c.Accrual("accrual", c.Quantity.known("10", "percent"), "actual_365", "periodic",
                  "2026-01-01", True, period_months=3.0)


def test_s0_3_float_refused_price_path_point():
    with pytest.raises(c.ContractViolation):
        c.PriceAssumption("path", "USD", path=(("2026-11-02", 1.50),))


def test_s0_3_float_refused_scenario_assumption():
    """A float never reaches an evaluator as a float: the contract records an exact
    decimal string, and the supply guard refuses any float that does appear."""
    record = SS.scenario([], other_assumptions=((vt.DILUTIVE_ISSUANCE_SHARES, "2000000"),)).as_record()
    record["other_assumptions"][0][1] = 2000000.0
    with pytest.raises(c.ContractViolation, match="exact decimal strings only"):
        supply_module._refuse_numbers(record, "financing_scenario")


def test_s0_3_float_refused_by_every_evaluator_that_takes_a_number():
    built = formula([market("lowest_daily", 10)])
    with pytest.raises(c.ContractViolation):
        vt.maximum_issuable(built, 1000000.0, INST)
    with pytest.raises(c.ContractViolation):
        vt.settle_branch("cash", 1000000.0, Fraction(5), Fraction(Decimal("7.50")))
    with pytest.raises(c.ContractViolation):
        vt.accreted_amount(1000000.0, accrual(), None, HORIZON_END, INST)


def test_s0_3_float_refused_in_a_term_record_structure():
    record = IE.term_record("price_reset", fact_origin="adjudicated_gold")
    record["structure"] = c.ResetSchedule("reset_schedule", "exercise_price", (reset_event(),)).as_record()
    record["structure"]["events"][0]["floor"] = {"value": 1.0, "unit": "usd", "status": "known"}
    with pytest.raises(c.ContractViolation, match="exact"):
        gold_attach([record], [IE.binding(record["occurrence_id"])])


def test_s0_3_no_float_is_produced_by_any_evaluator():
    result = vt.formula_price(formula([market("average_daily", 10)]), PATH_V, PRICING_DATE, CLOSED, INST)
    assert isinstance(result.value, Fraction)
    SS.assert_no_float(dict(result.trace_items), "formula_price.trace")
    body = vt.maximum_issuable(formula([market("lowest_daily", 10)], floor_basis="stated", floor="0.50"),
                               PRINCIPAL, INST)
    SS.assert_no_float(body, "maximum_issuable")


# ---------------------------------------------------------------------------
# §2.1 component_price — the §4 variable-conversion price rows
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("aggregation,lookback,window_end,lowest_count,expected", [
    ("lowest_daily", 10, "including_pricing_date", None, "1.00"),
    ("average_daily", 10, "including_pricing_date", None, "1.46"),
    ("average_of_lowest", 10, "including_pricing_date", 3, "37/30"),
    ("single_day", 1, "including_pricing_date", None, "1.70"),
    ("single_day", 1, "preceding_pricing_date", None, "1.60"),
    ("lowest_daily", 5, "preceding_pricing_date", None, "1.30"),
    ("lowest_daily", 5, "including_pricing_date", None, "1.45"),
], ids=["lowest10inc", "avg10", "avg_low3", "single_inc", "single_prec", "low5prec", "low5inc"])
def test_fx_component_price_measures_the_window_exactly(aggregation, lookback, window_end, lowest_count, expected):
    """§4 Path V aggregates at 100% of measure; the 80% rows are §2.2 formula rows."""
    built = market(aggregation, lookback, percent="100", window_end=window_end, lowest_count=lowest_count)
    result = vt.component_price(built, PATH_V, PRICING_DATE, CLOSED, INST)
    assert result.unknown is None
    assert result.value == Fraction(expected)
    assert result.trace["path_points_are_trading_days"] == "true"


def test_fx_component_price_applies_percent_of_measure_exactly():
    built = market("lowest_daily", 10, percent="80")
    assert vt.component_price(built, PATH_V, PRICING_DATE, CLOSED, INST).value == Fraction(Decimal("0.80"))


def test_fx_fixed_component_ignores_the_path_entirely():
    result = vt.component_price(fixed("1.10"), (), PRICING_DATE, CLOSED, INST)
    assert result.value == Fraction(Decimal("1.10"))


def test_s0_4_unknown_never_zero_or_unbounded_window_not_covered():
    result = vt.component_price(market("lowest_daily", 20), PATH_V, PRICING_DATE, CLOSED, INST)
    assert result.value is None
    assert result.unknown.unknown_id == f"price_window_not_covered_{INST}"
    assert result.trace["path_points_are_trading_days"] == "true"


def test_s0_4_unknown_never_zero_or_unbounded_period_vwap_needs_volume():
    result = vt.component_price(market("period_vwap", 10), PATH_V, PRICING_DATE, CLOSED, INST)
    assert result.value is None
    assert result.unknown.unknown_id == f"period_vwap_needs_volume_{INST}"


def test_s0_4_unknown_never_zero_or_unbounded_price_measure_mismatch():
    result = vt.component_price(market("lowest_daily", 10, measure=VWAP), PATH_V, PRICING_DATE, CLOSED, INST)
    assert result.value is None
    assert result.unknown.unknown_id == f"price_measure_mismatch_{INST}"


def test_s0_7_no_lookahead_in_component_price():
    """Pricing at 2026-11-11 reads nothing after it, whatever the path holds."""
    at_horizon = vt.component_price(market("single_day", 1, percent="100"), PATH_V, "2026-11-11", CLOSED, INST)
    assert at_horizon.value == Fraction(Decimal("1.50"))
    assert at_horizon.trace["component_window_end_date"] == "2026-11-11"
    # The same aggregate over the window that ENDS at the pricing date is 1.4125;
    # the full 10-point path would average 1.46, so the later points were not read.
    truncated = vt.component_price(market("average_daily", 8, percent="100"), PATH_V, "2026-11-11", CLOSED, INST)
    assert truncated.value == Fraction(Decimal("1.4125"))
    assert truncated.trace["component_window_end_date"] == "2026-11-11"
    full = vt.component_price(market("average_daily", 10, percent="100"), PATH_V, PRICING_DATE, CLOSED, INST)
    assert full.value == Fraction(Decimal("1.46"))
    assert full.value != truncated.value


def test_s2_1_the_declared_path_measure_is_a_scenario_assumption_not_a_fact():
    assert vt.path_measure_of(()) == CLOSED
    assert vt.path_measure_of(((vt.PATH_MEASURE_ASSUMPTION, VWAP),)) == VWAP
    with pytest.raises(c.ContractViolation):
        vt.path_measure_of(((vt.PATH_MEASURE_ASSUMPTION, "not_a_measure"),))


# ---------------------------------------------------------------------------
# §2.2 formula_price — the §4 price and floor rows
# ---------------------------------------------------------------------------


def test_fx_lowest_daily_10_at_80_percent_is_eighty_cents():
    result = vt.formula_price(formula([market("lowest_daily", 10)]), PATH_V, PRICING_DATE, CLOSED, INST)
    assert result.value == Fraction(Decimal("0.80"))
    assert result.trace["floor_reached"] == "false"


def test_fx_average_daily_10_at_80_percent():
    result = vt.formula_price(formula([market("average_daily", 10)]), PATH_V, PRICING_DATE, CLOSED, INST)
    assert result.value == Fraction(Decimal("1.168"))


def test_fx_average_of_lowest_3_of_10_at_80_percent():
    result = vt.formula_price(formula([market("average_of_lowest", 10, lowest_count=3)]),
                              PATH_V, PRICING_DATE, CLOSED, INST)
    assert result.value == Fraction(74, 75)


def test_fx_single_day_including_at_80_percent():
    result = vt.formula_price(formula([market("single_day", 1)]), PATH_V, PRICING_DATE, CLOSED, INST)
    assert result.value == Fraction(Decimal("1.36"))


def test_fx_single_day_preceding_at_80_percent():
    result = vt.formula_price(formula([market("single_day", 1, window_end="preceding_pricing_date")]),
                              PATH_V, PRICING_DATE, CLOSED, INST)
    assert result.value == Fraction(Decimal("1.28"))


def test_fx_single_day_at_the_2026_11_11_horizon_end():
    result = vt.formula_price(formula([market("single_day", 1)]), PATH_V, "2026-11-11", CLOSED, INST)
    assert result.value == Fraction(Decimal("1.20"))


def test_fx_greater_of_fixed_and_lowest_daily_takes_the_fixed_price():
    built = formula([fixed("1.10"), market("lowest_daily", 10)], combine="greater")
    result = vt.formula_price(built, PATH_V, PRICING_DATE, CLOSED, INST)
    assert result.value == Fraction(Decimal("1.10"))


def test_fx_lesser_of_fixed_and_lowest_daily_takes_the_market_price():
    built = formula([fixed("1.10"), market("lowest_daily", 10)], combine="lesser")
    result = vt.formula_price(built, PATH_V, PRICING_DATE, CLOSED, INST)
    assert result.value == Fraction(Decimal("0.80"))


def test_fx_lowest_daily_5_preceding_at_80_percent():
    built = formula([market("lowest_daily", 5, window_end="preceding_pricing_date")])
    assert vt.formula_price(built, PATH_V, PRICING_DATE, CLOSED, INST).value == Fraction(Decimal("1.04"))


def test_fx_lowest_daily_5_including_at_80_percent():
    built = formula([market("lowest_daily", 5)])
    assert vt.formula_price(built, PATH_V, PRICING_DATE, CLOSED, INST).value == Fraction(Decimal("1.16"))


def test_fx_lowest_daily_20_is_unknown_not_the_short_window():
    result = vt.formula_price(formula([market("lowest_daily", 20)]), PATH_V, PRICING_DATE, CLOSED, INST)
    assert result.value is None
    assert result.unknown.unknown_id == f"price_window_not_covered_{INST}"


def test_fx_period_vwap_is_unknown_not_an_unweighted_average():
    result = vt.formula_price(formula([market("period_vwap", 10)]), PATH_V, PRICING_DATE, CLOSED, INST)
    assert result.value is None
    assert result.unknown.unknown_id == f"period_vwap_needs_volume_{INST}"


def test_fx_a_daily_vwap_formula_on_an_undeclared_path_is_unknown():
    result = vt.formula_price(formula([market("lowest_daily", 10, measure=VWAP)]),
                              PATH_V, PRICING_DATE, CLOSED, INST)
    assert result.value is None
    assert result.unknown.unknown_id == f"price_measure_mismatch_{INST}"


def test_fx_a_lesser_of_one_known_and_one_unknown_component_is_unknown():
    """Never the other component alone (§2.2)."""
    built = formula([fixed("1.10"), market("lowest_daily", 20)], combine="lesser")
    result = vt.formula_price(built, PATH_V, PRICING_DATE, CLOSED, INST)
    assert result.value is None
    assert result.unknown.unknown_id == f"price_window_not_covered_{INST}"


def test_fx_floor_0_50_stated_does_not_bind():
    built = formula([market("lowest_daily", 10)], floor_basis="stated", floor="0.50",
                    below_floor="floor_applies")
    result = vt.formula_price(built, PATH_V, PRICING_DATE, CLOSED, INST)
    assert result.value == Fraction(Decimal("0.80"))
    assert result.trace["floor_reached"] == "false"
    assert result.blockers == ()


def test_fx_floor_1_00_stated_binds():
    built = formula([market("lowest_daily", 10)], floor_basis="stated", floor="1.00",
                    below_floor="floor_applies")
    result = vt.formula_price(built, PATH_V, PRICING_DATE, CLOSED, INST)
    assert result.value == Fraction(1)
    assert result.trace["floor_reached"] == "true"


def test_fx_floor_1_00_with_a_cash_make_whole_names_the_unknown_and_never_guesses_it():
    built = formula([market("lowest_daily", 10)], floor_basis="stated", floor="1.00",
                    below_floor="floor_applies_with_cash_make_whole")
    result = vt.formula_price(built, PATH_V, PRICING_DATE, CLOSED, INST)
    assert result.value == Fraction(1)
    assert vt.BLOCKER_FLOOR_MAKE_WHOLE in result.blockers
    assert [item.unknown_id for item in result.extra_unknowns] == [f"make_whole_amount_{INST}"]


def test_fx_a_ceiling_binds_before_the_floor():
    built = formula([market("single_day", 1)], ceiling="1.20", floor_basis="stated", floor="1.00",
                    below_floor="floor_applies")
    result = vt.formula_price(built, PATH_V, PRICING_DATE, CLOSED, INST)
    assert result.value == Fraction(Decimal("1.20"))


def test_fx_rounding_is_applied_last():
    built = formula([market("average_of_lowest", 10, lowest_count=3)], rounding=c.Rounding(4, "half_up"))
    result = vt.formula_price(built, PATH_V, PRICING_DATE, CLOSED, INST)
    assert result.value == Fraction(Decimal("0.9867"))


def test_fx_floor_basis_none_in_complete_agreement_prices_with_no_floor():
    built = formula([market("lowest_daily", 10)], floor_basis="none_in_complete_agreement")
    result = vt.formula_price(built, PATH_V, PRICING_DATE, CLOSED, INST)
    assert result.value == Fraction(Decimal("0.80"))
    assert result.trace["floor_reached"] == "false"


def test_fx_floor_basis_not_established_prices_with_no_floor():
    built = formula([market("lowest_daily", 10)], floor_basis="not_established")
    result = vt.formula_price(built, PATH_V, PRICING_DATE, CLOSED, INST)
    assert result.value == Fraction(Decimal("0.80"))
    assert result.trace["floor_reached"] == "false"


def test_s1_5_a_stated_floor_basis_requires_its_floor_amount():
    with pytest.raises(c.ContractViolation):
        c.PriceFormula("price_formula", "single", (market("lowest_daily", 10),), "stated", floor=None)


def test_s1_5_below_floor_is_required_only_when_the_floor_is_stated():
    with pytest.raises(c.ContractViolation):
        formula([market("lowest_daily", 10)], floor_basis="none_in_complete_agreement",
                below_floor="floor_applies")


# ---------------------------------------------------------------------------
# §2.3 maximum_issuable — the §4 maximum rows
# ---------------------------------------------------------------------------


def test_fx_maximum_issuable_bounded_by_a_stated_floor():
    built = formula([market("lowest_daily", 10)], floor_basis="stated", floor="0.50",
                    below_floor="floor_applies")
    body = vt.maximum_issuable(built, PRINCIPAL, INST)
    assert body["state"] == "bounded_by_floor"
    assert body["shares"] == "2000000"
    assert body["floor"] == "0.5"


def test_fx_maximum_issuable_bounded_by_a_binding_floor():
    built = formula([market("lowest_daily", 10)], floor_basis="stated", floor="1.00",
                    below_floor="floor_applies")
    body = vt.maximum_issuable(built, PRINCIPAL, INST)
    assert body["state"] == "bounded_by_floor"
    assert body["shares"] == "1000000"


def test_s0_4_unknown_never_zero_or_unbounded_no_floor_is_unbounded_by_contract():
    """A26 / L231: never a finite maximum and never infinity."""
    built = formula([market("lowest_daily", 10)], floor_basis="none_in_complete_agreement")
    body = vt.maximum_issuable(built, PRINCIPAL, INST,
                               limits=("exchange_cap_shares", "shares_issued_under_instrument"))
    assert body["state"] == "unbounded_by_contract"
    assert body["binding_limits"] == ["exchange_cap_shares", "shares_issued_under_instrument"]
    assert "shares" not in body
    SS.assert_no_float(body, "maximum_issuable")
    assert "inf" not in repr(body).lower()


def test_s0_4_unknown_never_zero_or_unbounded_floor_not_established():
    built = formula([market("lowest_daily", 10)], floor_basis="not_established")
    body = vt.maximum_issuable(built, PRINCIPAL, INST)
    assert body["state"] == "unknown"
    assert body["unknown_id"] == f"floor_not_established_{INST}"
    assert "shares" not in body


def test_s2_3_maximum_issuable_never_returns_a_quantity():
    built = formula([market("lowest_daily", 10)], floor_basis="stated", floor="0.50",
                    below_floor="floor_applies")
    body = vt.maximum_issuable(built, PRINCIPAL, INST)
    assert all(not isinstance(item, c.Quantity) for item in body.values())
    assert all(isinstance(item, str) for item in body.values() if not isinstance(item, list))


def test_s2_3_a_formula_without_a_structure_reports_no_price_formula():
    assert vt.maximum_issuable(None, PRINCIPAL, INST)["state"] == "no_price_formula"


def test_s2_3_maximum_issuable_refuses_a_float_amount():
    with pytest.raises(c.ContractViolation):
        vt.maximum_issuable(formula([market("lowest_daily", 10)]), 1000000.0, INST)


# ---------------------------------------------------------------------------
# §2.4 apply_resets — the §4 reset-warrant rows
# ---------------------------------------------------------------------------

#: The reset path: 1.50 before, 1.20 at the 2026-11-13 reset, 1.50 after.
PATH_R = (
    ("2026-11-12", "1.50"),
    ("2026-11-13", "1.20"),
    ("2026-11-16", "1.50"),
    ("2026-11-20", "1.50"),
)
RESET_DATE = "2026-11-13"
STRIKE = Fraction(Decimal("1.60"))
COUNT = Fraction(1_000_000)


def reset_scenario(*, as_of: str = "2026-11-01T00:00:00Z", horizon_end: str = "2026-11-16"):
    return SS.scenario(as_of=as_of, horizon_start="2026-11-02", horizon_end=horizon_end,
                       price=c.PriceAssumption("path", "USD", path=PATH_R), fee_rate=None)


def schedule(share_adjustment: str = "none", rule: str = "set_to_market", *, floor: str | None = None,
             reset_date: str = RESET_DATE) -> c.ResetSchedule:
    return c.ResetSchedule("reset_schedule", "exercise_price",
                           (reset_event(reset_date, rule, floor=floor, share_adjustment=share_adjustment),))


def test_fx_reset_inside_the_horizon_sets_the_price_to_market():
    result = vt.apply_resets(schedule(), STRIKE, COUNT, {}, reset_scenario(), INST)
    assert result.value == Fraction(Decimal("1.20"))
    assert result.count == COUNT
    assert result.unknown is None
    assert result.trace[f"reset_applied_{RESET_DATE}"] == "1.2"


def test_fx_reset_preserve_aggregate_exercise_price_adjusts_the_count():
    result = vt.apply_resets(schedule("preserve_aggregate_exercise_price"), STRIKE, COUNT, {},
                             reset_scenario(), INST)
    assert result.value == Fraction(Decimal("1.20"))
    assert result.count == Fraction(1_333_333)
    assert result.trace[f"reset_share_adjustment_{RESET_DATE}"] == "1000000*1.6/1.2=4000000/3"


def test_fx_reset_set_to_lesser_keeps_the_lower_of_the_two():
    result = vt.apply_resets(schedule(rule="set_to_lesser_of_current_and_market"), STRIKE, COUNT, {},
                             reset_scenario(), INST)
    assert result.value == Fraction(Decimal("1.20"))
    raised = vt.apply_resets(schedule(rule="set_to_lesser_of_current_and_market"), Fraction(1), COUNT, {},
                             reset_scenario(), INST)
    assert raised.value == Fraction(1)


def test_fx_reset_event_floor_binds():
    result = vt.apply_resets(schedule(floor="1.30"), STRIKE, COUNT, {}, reset_scenario(), INST)
    assert result.value == Fraction(Decimal("1.30"))
    assert result.trace[f"reset_floor_applied_{RESET_DATE}"] == "1.3"


def test_s0_4_unknown_never_zero_or_unbounded_reset_outcome_not_evidenced():
    """A past reset with no admitted price term dated on or after it is Unknown."""
    scenario = reset_scenario(as_of="2026-11-20T00:00:00Z", horizon_end="2026-11-20")
    result = vt.apply_resets(schedule(), STRIKE, COUNT, {}, scenario, INST)
    assert result.value is None
    assert result.unknown.unknown_id == f"reset_outcome_not_evidenced_{INST}_{RESET_DATE}"


def test_fx_a_past_reset_evidenced_by_an_admitted_term_is_a_fact():
    scenario = reset_scenario(as_of="2026-11-20T00:00:00Z", horizon_end="2026-11-20")
    terms = {"exercise_price": value_term("exercise_price", "1.20", effective_at="2026-11-13T00:00:00Z")}
    result = vt.apply_resets(schedule(), STRIKE, COUNT, terms, scenario, INST)
    assert result.unknown is None
    assert result.value == STRIKE
    assert result.trace["past_reset"] == RESET_DATE
    assert result.trace[f"past_reset_{RESET_DATE}"] == "evidenced_by_admitted_term"


def test_s0_7_no_lookahead_a_reset_beyond_the_horizon_is_never_applied():
    scenario = reset_scenario(horizon_end="2026-11-12")
    result = vt.apply_resets(schedule(), STRIKE, COUNT, {}, scenario, INST)
    assert result.value == STRIKE
    assert result.count == COUNT
    assert result.trace["future_reset"] == RESET_DATE


def test_s0_7_no_lookahead_a_reset_reads_only_points_dated_on_or_before_it():
    scenario = reset_scenario(horizon_end="2026-11-20")
    result = vt.apply_resets(schedule(), STRIKE, COUNT, {}, scenario, INST)
    assert result.value == Fraction(Decimal("1.20"))
    assert result.trace["reset_horizon_end"] == "2026-11-20"


def test_s2_4_two_events_apply_in_date_order():
    events = (reset_event("2026-11-13", "set_to_market"),
              reset_event("2026-11-16", "set_to_market", percent="100"))
    built = c.ResetSchedule("reset_schedule", "exercise_price", events)
    result = vt.apply_resets(built, STRIKE, COUNT, {}, reset_scenario(), INST)
    assert result.value == Fraction(Decimal("1.50"))


def test_s2_4_events_must_ascend():
    events = (reset_event("2026-11-16"), reset_event("2026-11-13"))
    with pytest.raises(c.ContractViolation):
        c.ResetSchedule("reset_schedule", "exercise_price", events)


# ---------------------------------------------------------------------------
# §2.5 anti_dilution_price — the §4 anti-dilution rows
# ---------------------------------------------------------------------------

EXISTING = Fraction(10_000_000)
CP1 = Fraction(1)


def ad(method: str, *, rounding: c.Rounding | None = None, share_adjustment: str = "none",
       applies_to: str = "conversion_price") -> c.AntiDilution:
    return c.AntiDilution("anti_dilution", applies_to, method, price_rounding=rounding,
                          share_adjustment=share_adjustment)


def test_fx_weighted_average_narrow():
    result = vt.anti_dilution_price(ad("weighted_average_narrow"), CP1, issuance(), EXISTING, INST)
    assert result.value == Fraction(143, 150)
    assert result.unknown is None
    assert result.trace["anti_dilution_issuance_is_a_scenario_assumption"] == "true"


def test_fx_weighted_average_narrow_with_four_place_half_up_rounding():
    result = vt.anti_dilution_price(ad("weighted_average_narrow", rounding=c.Rounding(4, "half_up")),
                                    CP1, issuance(), EXISTING, INST)
    assert result.value == Fraction(Decimal("0.9533"))


def test_fx_full_ratchet_takes_the_issuance_price():
    result = vt.anti_dilution_price(ad("full_ratchet"), CP1, issuance(), EXISTING, INST)
    assert result.value == Fraction(Decimal("0.72"))


def test_fx_an_issuance_at_1_05_does_not_trigger():
    result = vt.anti_dilution_price(ad("full_ratchet"), CP1, issuance(price="1.05"), EXISTING, INST)
    assert result.value == CP1
    assert result.unknown is None
    assert result.blockers == (vt.BLOCKER_ANTI_DILUTION_NOT_TRIGGERED,)
    assert result.trace["anti_dilution_triggered"] == "false"


def test_s0_4_unknown_never_zero_or_unbounded_broad_base_is_never_computed():
    result = vt.anti_dilution_price(ad("weighted_average_broad"), CP1, issuance(), EXISTING, INST)
    assert result.value is None
    assert result.unknown.unknown_id == f"anti_dilution_broad_base_{INST}"
    assert vt.BROAD_BASE_PREFIX in result.unknown.resolving_fact


def test_fx_a_broad_base_from_an_unknown_resolution_is_used_as_given():
    result = vt.anti_dilution_price(ad("weighted_average_broad"), CP1, issuance(), EXISTING, INST,
                                    broad_base=Fraction(20_000_000))
    assert result.value == Fraction(21_440_000, 22_000_000)


def test_fx_none_in_complete_agreement_leaves_the_price_alone():
    result = vt.anti_dilution_price(ad("none_in_complete_agreement"), CP1, {}, EXISTING, INST)
    assert result.value == CP1
    assert result.unknown is None


def test_s2_5_preserve_aggregate_exercise_price_adjusts_the_count():
    result = vt.anti_dilution_price(ad("full_ratchet", share_adjustment="preserve_aggregate_exercise_price"),
                                    CP1, issuance(), EXISTING, INST, count=COUNT)
    assert result.value == Fraction(Decimal("0.72"))
    assert result.count == Fraction(1_388_888)


def test_s2_5_a_missing_issuance_assumption_is_unknown_never_zero():
    result = vt.anti_dilution_price(ad("full_ratchet"), CP1, {}, EXISTING, INST)
    assert result.value is None
    assert result.unknown.unknown_id == f"dilutive_issuance_{INST}"


def test_s2_5_a_missing_issuance_price_is_unknown_never_the_horizon_price():
    result = vt.anti_dilution_price(ad("full_ratchet"), CP1,
                                    {vt.DILUTIVE_ISSUANCE_SHARES: Fraction(2_000_000)}, EXISTING, INST)
    assert result.value is None
    assert result.unknown.unknown_id == f"dilutive_issuance_price_{INST}"


def test_s2_5_an_unselected_share_basis_leaves_the_narrow_base_unknown():
    result = vt.anti_dilution_price(ad("weighted_average_narrow"), CP1, issuance(), None, INST)
    assert result.value is None
    assert result.unknown.unknown_id == f"anti_dilution_existing_base_{INST}"


# ---------------------------------------------------------------------------
# §2.6 accreted_amount — the §4 accretion rows
# ---------------------------------------------------------------------------

HORIZON_END = "2026-07-01"


def test_fx_simple_actual_365_over_181_days():
    result = vt.accreted_amount(PRINCIPAL, accrual("actual_365", "simple"), None, HORIZON_END, INST)
    assert result.value == PRINCIPAL + Fraction(100_000) * Fraction(181, 365)
    assert result.trace["accrued_amount"] == "3620000/73"


def test_fx_simple_actual_360():
    result = vt.accreted_amount(PRINCIPAL, accrual("actual_360", "simple"), None, HORIZON_END, INST)
    assert result.value == PRINCIPAL + Fraction(100_000) * Fraction(181, 360)


def test_fx_periodic_three_month_actual_365():
    result = vt.accreted_amount(PRINCIPAL, accrual("actual_365", "periodic", period_months=3),
                                None, HORIZON_END, INST)
    first = PRINCIPAL * (1 + Fraction(1, 10) * Fraction(90, 365))
    second = first * (1 + Fraction(1, 10) * Fraction(91, 365))
    assert result.value == second
    assert result.trace["accrual_periods_compounded"] == "2"


def test_fx_simple_thirty_360_over_180_days():
    result = vt.accreted_amount(PRINCIPAL, accrual("thirty_360", "simple"), None, HORIZON_END, INST)
    assert result.value == Fraction(1_050_000)


def test_fx_an_evidenced_accrued_amount_continues_from_its_own_date():
    term = value_term("accrued_amount_outstanding", "24657.53", effective_at="2026-04-01T00:00:00Z")
    result = vt.accreted_amount(PRINCIPAL, accrual("actual_365", "simple"), term, HORIZON_END, INST)
    assert result.value == PRINCIPAL + Fraction(Decimal("24657.53")) + Fraction(100_000) * Fraction(91, 365)
    assert result.trace["accrued_amount_evidenced_at"] == "2026-04-01"


# -- audit r1 M1: the periodic grid is anchored to accrual_start --------------
#
# Period boundaries are ALWAYS accrual_start + k * period_months.  An admitted
# accrued_amount_outstanding term is a fact about the BALANCE at its own date, so
# it re-bases the balance inside the anchored period that contains it; it never
# moves the grid.  With B = principal + E stated at s, [p0, p1) the anchored
# period containing s and r the annual rate:
#
#   Pk  = B / (1 + r * yf(p0, s))      the period's opening balance
#   B1  = B + Pk * r * yf(s, p1)       simple interest to the period end
#   ...  then ordinary compounding on the anchored grid from p1.
#
# An s exactly on a boundary gives yf(p0, s) = 0, so Pk = B.


def _floor_of(value: Fraction) -> int:
    """The floored whole count of an exact positive rational."""
    return value.numerator // value.denominator


def test_m1_periodic_evidenced_mid_period_is_anchored():
    """M1: an amount evidenced MID-period never moves the anchored grid.

    The pre-repair code stepped the boundaries from the evidenced date
    (02-15 -> 05-15, then a 47-day stub) and reported 1,049,889.
    """
    evidenced = Fraction(Decimal("12328.77"))
    term = value_term("accrued_amount_outstanding", "12328.77", effective_at="2026-02-15T00:00:00Z")
    result = vt.accreted_amount(PRINCIPAL, accrual("actual_365", "periodic", period_months=3),
                                term, HORIZON_END, INST)
    rate = Fraction(1, 10)
    balance = PRINCIPAL + evidenced                          # B at 2026-02-15
    opening = balance / (1 + rate * Fraction(45, 365))       # Pk: 2026-01-01 -> 2026-02-15 = 45 days
    at_second_grid_point = balance + opening * rate * Fraction(45, 365)   # 2026-02-15 -> 2026-04-01
    expected = at_second_grid_point * (1 + rate * Fraction(91, 365))      # 2026-04-01 -> 2026-07-01
    assert result.unknown is None
    assert result.value == expected
    assert _floor_of(result.value) == 1_050_203
    # The grid is the anchored one, and the period the evidence falls in is Q1.
    assert result.trace["accrual_period_grid_anchored_at"] == "2026-01-01"
    assert result.trace["accrual_evidenced_period_start"] == "2026-01-01"
    # 7390 = 2 * 5 * 739 does not terminate in base 10, so the exact opening
    # balance is written as the reduced fraction it is, never as a rounding.
    assert opening == balance / (1 + rate * Fraction(45, 365))
    assert opening == Fraction(7_390_000_021, 7_390)
    assert result.trace["accrual_evidenced_period_opening_balance"] == f"{opening.numerator}/{opening.denominator}"
    assert result.trace["accrued_amount_evidenced_at"] == "2026-02-15"


def test_m1_periodic_evidenced_on_boundary():
    """M1: an amount evidenced exactly ON a boundary gives d = 0, so Pk = B.

    The exact Q1 accrual, 1,000,000 * 10% * 90/365 = 1,800,000/73, does not
    terminate in base 10 (73 divides no power of 10), so a term — which carries
    exact decimal text and nothing else — cannot state it.  The case is therefore
    derived from an exactly representable E, as the ruling allows, and the
    expectation is computed here from B * (1 + r * 91/365).
    """
    exact_first_quarter = PRINCIPAL * Fraction(1, 10) * Fraction(90, 365)
    assert exact_first_quarter == Fraction(1_800_000, 73)
    assert exact_first_quarter.denominator == 73
    evidenced = Fraction(Decimal("24657.53"))
    term = value_term("accrued_amount_outstanding", "24657.53", effective_at="2026-04-01T00:00:00Z")
    result = vt.accreted_amount(PRINCIPAL, accrual("actual_365", "periodic", period_months=3),
                                term, HORIZON_END, INST)
    rate = Fraction(1, 10)
    balance = PRINCIPAL + evidenced
    expected = balance * (1 + rate * Fraction(91, 365))      # 2026-04-01 -> 2026-07-01 = 91 days
    assert result.unknown is None
    assert result.value == expected
    assert _floor_of(result.value) == 1_050_203
    # d = 0, so the period's opening balance IS the evidenced balance.
    assert result.trace["accrual_evidenced_period_start"] == "2026-04-01"
    assert result.trace["accrual_evidenced_period_opening_balance"] == "1024657.53"


def test_m1b_periodic_stub_on_running_balance():
    """M1b: the partial final period earns simple interest on the RUNNING balance.

    Two full quarters plus a 45-day stub.  The pre-repair code earned the stub on
    the original principal only and reported 1,062,532.
    """
    stub_end = "2026-08-15"
    result = vt.accreted_amount(PRINCIPAL, accrual("actual_365", "periodic", period_months=3),
                                None, stub_end, INST)
    rate = Fraction(1, 10)
    first_quarter = PRINCIPAL * (1 + rate * Fraction(90, 365))     # 2026-01-01 -> 2026-04-01
    second_quarter = first_quarter * (1 + rate * Fraction(91, 365))  # 2026-04-01 -> 2026-07-01
    expected = second_quarter + second_quarter * rate * Fraction(45, 365)  # 2026-07-01 -> 2026-08-15
    assert result.unknown is None
    assert result.value == expected
    assert _floor_of(result.value) == 1_063_151
    assert result.trace["accrual_periods_compounded"] == "2"
    assert result.trace["accrual_period_grid_anchored_at"] == "2026-01-01"


def test_fx_converts_with_principal_false_converts_principal_only():
    result = vt.accreted_amount(PRINCIPAL, accrual("actual_365", "simple", converts=False),
                                None, HORIZON_END, INST)
    assert result.value == PRINCIPAL
    assert result.trace[vt.TRACE_ACCRUED_NOT_CONVERTED] == "3620000/73"


def test_s2_6_a_contradicted_accrued_amount_is_ignored_and_accrual_runs_from_the_start():
    term = value_term("accrued_amount_outstanding", None, status="contradicted")
    result = vt.accreted_amount(PRINCIPAL, accrual("actual_365", "simple"), term, HORIZON_END, INST)
    assert result.value == PRINCIPAL + Fraction(100_000) * Fraction(181, 365)
    assert "accrued_amount_evidenced" not in result.trace


def test_s2_6_an_unknown_accrual_rate_is_unknown_never_zero():
    built = dataclasses.replace(accrual("actual_365", "simple"),
                                annual_rate=c.Quantity.unknown("percent"))
    result = vt.accreted_amount(PRINCIPAL, built, None, HORIZON_END, INST)
    assert result.value is None
    assert result.unknown.unknown_id == f"accrual_rate_{INST}"


# ---------------------------------------------------------------------------
# §2.7 condition_met — the §4 conversion-condition rows
# ---------------------------------------------------------------------------


def test_fx_condition_required_5_of_10_is_met():
    assert vt.condition_met(condition(5, 10), PATH_V, PRICING_DATE, CLOSED, Fraction(1), INST) is True


def test_fx_condition_required_10_of_10_is_not_met():
    assert vt.condition_met(condition(10, 10), PATH_V, PRICING_DATE, CLOSED, Fraction(1), INST) is False


def test_s0_4_unknown_never_zero_or_unbounded_a_30_day_window_is_not_evaluable():
    """``None`` is not ``False``: an unreadable window never denies the claim."""
    assert vt.condition_met(condition(5, 30), PATH_V, PRICING_DATE, CLOSED, Fraction(1), INST) is None


def test_s2_7_a_measure_mismatch_is_not_evaluable():
    assert vt.condition_met(condition(5, 10, measure=VWAP), PATH_V, PRICING_DATE, CLOSED,
                            Fraction(1), INST) is None


def test_s2_7_an_unknown_conversion_price_makes_a_percent_threshold_unreadable():
    assert vt.condition_met(condition(5, 10), PATH_V, PRICING_DATE, CLOSED, None, INST) is None


def test_s2_7_at_or_below_counts_the_other_side():
    built = c.ConversionCondition("conversion_condition", 4, 10, "at_or_below", "price",
                                  c.Quantity.known("1.45", "usd"), CLOSED, "including_pricing_date")
    assert vt.condition_met(built, PATH_V, PRICING_DATE, CLOSED, Fraction(1), INST) is True
    stricter = c.ConversionCondition("conversion_condition", 5, 10, "at_or_below", "price",
                                     c.Quantity.known("1.45", "usd"), CLOSED, "including_pricing_date")
    assert vt.condition_met(stricter, PATH_V, PRICING_DATE, CLOSED, Fraction(1), INST) is False


def test_s0_7_no_lookahead_in_condition_met():
    """Only 6 of the first 7 points qualify at 2026-11-11, so 7 of 7 is not met."""
    assert vt.condition_met(condition(7, 7), PATH_V, "2026-11-11", CLOSED, Fraction(1), INST) is False
    assert vt.condition_met(condition(6, 7), PATH_V, "2026-11-11", CLOSED, Fraction(1), INST) is True


# ---------------------------------------------------------------------------
# §2.8 settle_branch — the §4 settlement-branch rows
# ---------------------------------------------------------------------------

CP_BRANCH = Fraction(5)


def test_fx_branch_physical_at_7_50():
    assert vt.settle_branch("physical", PRINCIPAL, CP_BRANCH, Fraction(Decimal("7.50"))) == (
        200_000, "no_cash", Fraction(0))


def test_fx_branch_net_share_at_7_50():
    assert vt.settle_branch("net_share", PRINCIPAL, CP_BRANCH, Fraction(Decimal("7.50"))) == (
        66_666, "repayment", PRINCIPAL)


def test_fx_branch_cash_at_7_50():
    assert vt.settle_branch("cash", PRINCIPAL, CP_BRANCH, Fraction(Decimal("7.50"))) == (
        0, "repayment", Fraction(1_500_000))


def test_fx_branch_net_share_at_4_00_pays_the_lesser_cash_and_no_shares():
    assert vt.settle_branch("net_share", PRINCIPAL, CP_BRANCH, Fraction(4)) == (
        0, "repayment", Fraction(800_000))


def test_s0_5_exclusive_branches_never_summed():
    """The three branches are alternatives: no caller can add them here."""
    priced = [vt.settle_branch(name, PRINCIPAL, CP_BRANCH, Fraction(Decimal("7.50")))
              for name in ("physical", "cash", "net_share")]
    assert [item.shares for item in priced] == [200_000, 0, 66_666]
    assert [item.cash_amount for item in priced] == [Fraction(0), Fraction(1_500_000), PRINCIPAL]
    assert len(inspect.signature(vt.settle_branch).parameters) == 4
    assert "branches" not in inspect.signature(vt.settle_branch).parameters


def test_s2_8_settle_branch_refuses_a_float():
    with pytest.raises(c.ContractViolation):
        vt.settle_branch("physical", 1000000.0, CP_BRANCH, Fraction(Decimal("7.50")))


def test_s2_8_settle_branch_refuses_a_name_that_is_not_a_branch():
    with pytest.raises(c.ContractViolation):
        vt.settle_branch("cashless", PRINCIPAL, CP_BRANCH, Fraction(Decimal("7.50")))


# ---------------------------------------------------------------------------
# §2.9 exchange_cap_remaining — the §4 exchange-cap rows
# ---------------------------------------------------------------------------


def cap_terms(cap: str | None = "700000", issued: str | None = "200000", approval: bool | None = None):
    cap_term = None if cap is None else value_term("exchange_cap_shares", cap)
    issued_term = None if issued is None else value_term("shares_issued_under_instrument", issued)
    approval_term = None if approval is None else SS.economic_term(
        INST, "shareholder_approval_obtained", flag=approval)
    return cap_term, issued_term, approval_term


def test_fx_cap_700000_with_200000_issued_leaves_500000():
    result = vt.exchange_cap_remaining(*cap_terms(), inst=INST)
    assert result.value == Fraction(500_000)
    assert result.blockers == (vt.BLOCKER_SHAREHOLDER_APPROVAL_REQUIRED,)
    assert result.trace["exchange_cap_remaining"] == "500000"
    assert result.unknown is None


def test_fx_shareholder_approval_removes_the_limit():
    result = vt.exchange_cap_remaining(*cap_terms(approval=True), inst=INST)
    assert result.value is None
    assert result.blockers == ()
    assert result.trace["shareholder_approval_obtained"] == "true"


def test_fx_a_fully_used_cap_leaves_zero_and_says_so():
    result = vt.exchange_cap_remaining(*cap_terms(issued="700000"), inst=INST)
    assert result.value == Fraction(0)
    assert result.blockers == (vt.BLOCKER_SHAREHOLDER_APPROVAL_REQUIRED, vt.BLOCKER_EXCHANGE_CAP_REACHED)


def test_s0_4_unknown_never_zero_or_unbounded_an_unstated_issued_count():
    result = vt.exchange_cap_remaining(*cap_terms(issued=None), inst=INST)
    assert result.value is None
    assert result.unknown.unknown_id == f"shares_issued_under_instrument_{INST}"


def test_s0_6_cap_limits_delivery_not_claim():
    """The function returns a deliverable count and nothing about the claim."""
    result = vt.exchange_cap_remaining(*cap_terms(), inst=INST)
    assert set(result.trace) <= {"shareholder_approval_obtained", "exchange_cap",
                                 "shares_issued_under_instrument", "exchange_cap_remaining"}
    assert vt.AFFECTS_DELIVERY == ("incremental_issuance",)
    unstated = vt.exchange_cap_remaining(*cap_terms(issued=None), inst=INST)
    assert unstated.unknown.affects == vt.AFFECTS_DELIVERY
    assert "as_converted_claims" not in unstated.unknown.affects


def test_s2_9_a_contradicted_cap_is_unknown_never_unlimited():
    result = vt.exchange_cap_remaining(value_term("exchange_cap_shares", None, status="contradicted"),
                                       value_term("shares_issued_under_instrument", "200000"), None, INST)
    assert result.value is None
    assert result.unknown.unknown_id == f"exchange_cap_shares_{INST}"


def test_s2_9_an_over_issued_cap_floors_at_zero_and_never_goes_negative():
    result = vt.exchange_cap_remaining(*cap_terms(issued="900000"), inst=INST)
    assert result.value == Fraction(0)


# ---------------------------------------------------------------------------
# §0 item 8 — structures enter only as adjudicated gold
# ---------------------------------------------------------------------------


GOLD_SERIES = IE.SERIES


def gold_instruments(series_key: str = GOLD_SERIES) -> c.InstrumentSet:
    _instrument_id, instruments = IE.warrant_set(series_key)
    return instruments


def gold_attach(records, bindings, series_key: str = GOLD_SERIES):
    """Attach through the I1 helper (which schema-validates) and return the record."""
    attached = IE.attach(gold_instruments(series_key), records, bindings)
    return checked(attached.as_record(), "instrument_set"), attached


def test_s0_8_terms_only_adjudicated_gold():
    """A canonical-extraction structure-only term is refused; gold is admitted."""
    schedule = c.ResetSchedule("reset_schedule", "exercise_price", (reset_event(),)).as_record()
    gold = IE.term_record("price_reset", fact_origin="adjudicated_gold", value=None, unit=None)
    gold["structure"] = schedule
    _record, attached = gold_attach([gold], [IE.binding(gold["occurrence_id"])])
    terms = IE.terms_of(attached, IE.instrument_for(GOLD_SERIES)[0])
    assert terms["price_reset"].structure == c.structure_from_record(schedule)


@pytest.mark.parametrize("name,structure", [
    ("price_reset", lambda: c.ResetSchedule("reset_schedule", "exercise_price", (reset_event(),))),
    ("conversion_condition", condition),
    ("settlement_branches", lambda: c.SettlementBranches("settlement_branches", ("physical", "cash"), "issuer")),
    ("anti_dilution", lambda: c.AntiDilution("anti_dilution", "conversion_price", "full_ratchet")),
    ("accrual_terms", accrual),
])
def test_s0_8_a_canonical_extraction_never_mints_a_structure(name, structure):
    record = IE.term_record(name, fact_origin="canonical_extraction", value=None, unit=None)
    record["structure"] = structure().as_record()
    with pytest.raises(c.ContractViolation, match="adjudicated_gold"):
        gold_attach([record], [IE.binding(record["occurrence_id"])])


def test_s0_8_a_price_formula_may_enter_as_canonical_extraction():
    """§1.3 last line: a price term is not one of the five gold-only names."""
    record = IE.term_record("conversion_price", value=None, expression="80% of the lowest daily close")
    record["structure"] = formula([market("lowest_daily", 10)]).as_record()
    _record, attached = gold_attach([record], [IE.binding(record["occurrence_id"])])
    terms = IE.terms_of(attached, IE.instrument_for(GOLD_SERIES)[0])
    assert terms["conversion_price"].structure.combine == "single"


def test_s0_8_a_market_formula_occurrence_carries_no_value():
    record = IE.term_record("conversion_price", value="1.00", expression="80% of the lowest daily close")
    record["structure"] = formula([market("lowest_daily", 10)]).as_record()
    with pytest.raises(c.ContractViolation, match="not a fact until the pricing date"):
        gold_attach([record], [IE.binding(record["occurrence_id"])])


def test_s0_8_a_conflicting_structure_at_the_same_effective_at_is_one_contradicted_term():
    """SPEC_I1 §4.4, extended to structures by SPEC_I2 §6."""
    first = IE.term_record("conversion_price", value=None, expression="80% of the lowest daily close",
                           manifest="manifest:1", span="span:a")
    first["structure"] = formula([market("lowest_daily", 10)]).as_record()
    second = IE.term_record("conversion_price", value=None, expression="80% of the lowest daily close",
                            manifest="manifest:2", span="span:b")
    second["structure"] = formula([market("average_daily", 10)]).as_record()
    binding = IE.binding(first["occurrence_id"], supersedes=[])
    other = IE.binding(second["occurrence_id"], supersedes=[])
    _record, attached = gold_attach([first, second], [binding, other])
    terms = IE.terms_of(attached, IE.instrument_for(GOLD_SERIES)[0])
    assert terms["conversion_price"].status == "contradicted"


# ---------------------------------------------------------------------------
# Module laws and determinism
# ---------------------------------------------------------------------------


def test_s2_the_module_declares_its_implementation_and_has_no_io_or_clock():
    assert vt.IMPLEMENTATION == "capital_structure.variable_terms.v1"
    source = inspect.getsource(vt)
    for banned in ("float(", "import socket", "import urllib", "import requests", "datetime.now",
                   "time.time", "random."):
        assert banned not in source, banned


def test_s2_every_evaluator_returns_a_frozen_result_with_value_unknown_and_trace():
    result = vt.formula_price(formula([market("lowest_daily", 10)]), PATH_V, PRICING_DATE, CLOSED, INST)
    assert isinstance(result, vt.TermResult)
    assert dataclasses.is_dataclass(result)
    with pytest.raises(dataclasses.FrozenInstanceError):
        result.value = Fraction(1)
    assert isinstance(result.trace, dict)
    assert all(isinstance(key, str) and isinstance(item, str) for key, item in result.trace.items())
    assert (result.value is None) != (result.unknown is None)


def test_determinism_same_inputs_give_an_identical_trace():
    built = formula([market("lowest_daily", 10)], floor_basis="stated", floor="1.00",
                    below_floor="floor_applies_with_cash_make_whole")
    first = vt.formula_price(built, PATH_V, PRICING_DATE, CLOSED, INST)
    second = vt.formula_price(built, PATH_V, PRICING_DATE, CLOSED, INST)
    assert first.trace == second.trace
    assert first.value == second.value
    assert c.sha256_of(first.trace) == c.sha256_of(second.trace)


def test_determinism_an_unknown_id_is_derived_not_random():
    first = vt.component_price(market("lowest_daily", 20), PATH_V, PRICING_DATE, CLOSED, INST)
    second = vt.component_price(market("lowest_daily", 20), PATH_V, PRICING_DATE, CLOSED, INST)
    assert first.unknown.unknown_id == second.unknown.unknown_id
    assert c.sha256_of(first.unknown.as_record()) == c.sha256_of(second.unknown.as_record())


def test_s2_unknown_ids_match_the_contract_id_pattern():
    unknowns = [
        vt.component_price(market("lowest_daily", 20), PATH_V, PRICING_DATE, CLOSED, INST).unknown,
        vt.component_price(market("period_vwap", 10), PATH_V, PRICING_DATE, CLOSED, INST).unknown,
        vt.component_price(market("lowest_daily", 10, measure=VWAP), PATH_V, PRICING_DATE, CLOSED, INST).unknown,
        vt.apply_resets(schedule(), STRIKE, COUNT, {},
                        reset_scenario(as_of="2026-11-20T00:00:00Z", horizon_end="2026-11-20"), INST).unknown,
        vt.anti_dilution_price(ad("weighted_average_broad"), CP1, issuance(), EXISTING, INST).unknown,
        vt.exchange_cap_remaining(*cap_terms(issued=None), inst=INST).unknown,
    ]
    import re
    pattern = re.compile(r"^[A-Za-z0-9][A-Za-z0-9:._/-]{0,199}$")
    for item in unknowns:
        assert item is not None
        assert pattern.match(item.unknown_id), item.unknown_id


# ---------------------------------------------------------------------------
# Audit r1 — M4 (the maximum must bound every delivery) and S6 (a sparse window)
# ---------------------------------------------------------------------------


def test_m4_reset_event_floor_lowers_the_bound():
    """M4: §2.4 applies the EVENT floor, so the bound is the LOWEST stated floor.

    Every expected value is computed here from the stated floors; none is read
    back from the implementation.
    """
    built = formula([market("lowest_daily", 10)], floor_basis="stated", floor="1.00",
                    below_floor="floor_applies")
    stated_floor = Fraction(1)
    event_floor = Fraction(Decimal("0.80"))
    with_floor = c.ResetSchedule("reset_schedule", "conversion_price",
                                 (reset_event(RESET_DATE, "set_to_market", floor="0.80"),))
    body = vt.maximum_issuable(built, PRINCIPAL, INST, schedule=with_floor)
    bound = min(stated_floor, event_floor)
    expected = PRINCIPAL / bound
    assert body["state"] == "bounded_by_floor"
    assert body["floor"] == "0.8"
    assert body["shares"] == str(expected.numerator // expected.denominator)
    assert body["shares"] == "1250000"
    SS.assert_no_float(body, "maximum_issuable")
    # A reset event that states NO floor can take the price anywhere below the
    # formula floor, so the contract bounds nothing: never the formula floor alone.
    without_floor = c.ResetSchedule("reset_schedule", "conversion_price",
                                    (reset_event(RESET_DATE, "set_to_market"),))
    open_body = vt.maximum_issuable(built, PRINCIPAL, INST, schedule=without_floor)
    assert open_body["state"] == "unbounded_by_contract"
    assert open_body[vt.TRACE_RESET_EVENT_FLOOR_NOT_STATED] == RESET_DATE
    assert open_body[vt.TRACE_AUTHORIZED_SHARES_NOT_EVALUATED] == "true"
    assert "shares" not in open_body
    SS.assert_no_float(open_body, "maximum_issuable")
    assert "inf" not in repr(open_body).lower()


def test_m4_an_anti_dilution_term_that_applies_no_floor_leaves_the_maximum_unbounded():
    """M4: §2.5 anti-dilution applies no floor, so a stated floor bounds nothing."""
    built = formula([market("lowest_daily", 10)], floor_basis="stated", floor="1.00",
                    below_floor="floor_applies")
    for method in vt.FLOOR_BYPASSING_ANTI_DILUTION:
        body = vt.maximum_issuable(built, PRINCIPAL, INST, anti_dilution=ad(method))
        assert body["state"] == "unbounded_by_contract", method
        assert body[vt.TRACE_ANTI_DILUTION_BYPASSES_FLOOR] == method
        assert "shares" not in body
        SS.assert_no_float(body, "maximum_issuable")
    # `none_in_complete_agreement` changes nothing, so the stated floor still binds.
    unchanged = vt.maximum_issuable(built, PRINCIPAL, INST,
                                    anti_dilution=ad("none_in_complete_agreement"))
    assert unchanged["state"] == "bounded_by_floor"
    assert unchanged["shares"] == "1000000"
    assert vt.TRACE_ANTI_DILUTION_BYPASSES_FLOOR not in unchanged


def test_m4_stated_floor_zero_is_unbounded():
    """M4 / N2: a stated floor of exactly 0 is unbounded — never a division by zero."""
    built = formula([market("lowest_daily", 10)], floor_basis="stated", floor="0")
    body = vt.maximum_issuable(built, PRINCIPAL, INST)
    assert body["state"] == "unbounded_by_contract"
    assert body["floor_basis"] == "stated"
    assert body[vt.TRACE_STATED_FLOOR_IS_ZERO] == "true"
    assert body["binding_limits"] == []
    assert body[vt.TRACE_AUTHORIZED_SHARES_NOT_EVALUATED] == "true"
    assert "shares" not in body
    # It is NOT the Unknown an unestablished floor produces.
    assert "unknown_id" not in body
    SS.assert_no_float(body, "maximum_issuable")


def test_s6_sparse_window_flagged():
    """S6: a sparse ``including_pricing_date`` window is visible, never silent."""
    sparse = PATH_V[:-1]                                  # the last point is 2026-11-12
    result = vt.component_price(market("single_day", 1), sparse, PRICING_DATE, CLOSED, INST)
    assert result.unknown is None
    assert result.value == Fraction(Decimal("1.60")) * Fraction(80, 100)
    assert result.trace["component_window_end_date"] == "2026-11-12"
    assert result.trace[vt.TRACE_WINDOW_LAST_POINT_BEFORE_PRICING_DATE] == "true"
    # Behaviour is otherwise unchanged: a window that does reach D is not flagged.
    covered = vt.component_price(market("single_day", 1), PATH_V, PRICING_DATE, CLOSED, INST)
    assert covered.value == Fraction(Decimal("1.70")) * Fraction(80, 100)
    assert vt.TRACE_WINDOW_LAST_POINT_BEFORE_PRICING_DATE not in covered.trace
    # A preceding_pricing_date window never reads a point at D by definition, so
    # it is not sparse and carries no flag.
    preceding = vt.component_price(market("single_day", 1, window_end="preceding_pricing_date"),
                                   PATH_V, PRICING_DATE, CLOSED, INST)
    assert preceding.value == result.value
    assert vt.TRACE_WINDOW_LAST_POINT_BEFORE_PRICING_DATE not in preceding.trace
