"""Direct tests for the F1 funding schedule (engine/capital_structure/funding.py).

Fixtures are built in-file.  The default fixture is a then-known scenario
dated 2026-09-01 over the horizon 2026-06-30 .. 2026-12-31, which the quarter
grid splits into [06-30, 09-30] and [09-30, 12-31] (92 elapsed days each).
Unrestricted cash of 5,000,000 usd is measured on 2026-06-30, and operating
cash flow of -1,810,000 usd over 2026-01-01 .. 2026-06-30 (181 inclusive
days) gives a burn of exactly 10,000 usd per day, i.e. 920,000.00 per period.

Acceptance rows: A28 (each item keeps its own availability and basis), A29
(net loss is not burn; negative or unknown burn never implies runway), A30
(dated obligations; gross, net and fees apart; assumptions are not cash; a
conversion relieves without providing cash; an undrawn conditional
commitment is not cash) and A48 (no probability, score or sizing).
"""

from __future__ import annotations

import dataclasses
import inspect
import json
import re
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterator

import pytest

from engine.capital_structure.funding import (
    CASH_BASIS_MEMBERS,
    CONTEXT_KINDS,
    FINANCIAL_ITEM_SCHEMA,
    FORBIDDEN_FIELDS,
    IMPLEMENTATION,
    ITEM_RULES,
    RULE_DIGEST,
    FundingInputError,
    project_funding,
)
from engine.capital_structure.issuer_state_contracts import (
    CASH_BASES,
    STATE_CONTRACT_VERSION,
    COMPATIBLE_INPUT_SCHEMAS,
    FORBIDDEN_PROPERTY_PATTERN,
    ActionSelection,
    CalculationReceipt,
    CapitalInputs,
    CapitalState,
    CommitmentInputs,
    ContractViolation,
    FamilyProvenance,
    FamilyState,
    FinancialInputs,
    FinancingScenario,
    FundingSchedule,
    GenerationBinding,
    PriceAssumption,
    Quantity,
    StateRequest,
    UnknownResolution,
    validate_state_record,
)

REPO = Path(__file__).resolve().parents[1]
CONFIG = REPO / "config" / "capital_structure_financial_input_binding.v1.json"

AS_OF = "2026-09-01T00:00:00Z"
H0 = "2026-06-30"
H1 = "2026-12-31"
AVAILABLE = "2026-08-10T20:00:00Z"
OCF_BASIS = "operating_cash_flow:2026-01-01:2026-06-30"
PER_PERIOD_BURN = Decimal("920000")
COV_SCHEMA = COMPATIBLE_INPUT_SCHEMAS["covenant_terms"][0]
DOC_SCHEMA = COMPATIBLE_INPUT_SCHEMAS["document_terms"][0]
RECEIPT_A = "a" * 64
RECEIPT_B = "b" * 64


# ---------------------------------------------------------------------------
# Fixture builders
# ---------------------------------------------------------------------------


def fact(
    item_id: str,
    kind: str,
    value: str | None,
    *,
    status: str = "known",
    unit: str = "usd",
    available_at: str = AVAILABLE,
    receipt: str | None = None,
    **extra: Any,
) -> dict[str, Any]:
    record: dict[str, Any] = {
        "schema": FINANCIAL_ITEM_SCHEMA,
        "item_id": item_id,
        "item_kind": kind,
        "amount": {"value": value if status == "known" else None, "unit": unit, "status": status},
        "available_at": available_at,
        "source": {
            "owner": "fundamental_forensics",
            "metric_id": None,
            "term_name": None,
            "receipt_sha256": receipt,
            "accession": None,
            "filed": None,
        },
    }
    if kind in ITEM_RULES:
        record["availability"] = ITEM_RULES[kind]["availability"]
    record.update(extra)
    return record


def cash(value: str = "5000000", measured: str = H0, item_id: str = "cash-q2", **kw: Any) -> dict[str, Any]:
    return fact(item_id, "unrestricted_cash", value, measured_at=measured, **kw)


def ocf(value: str = "-1810000", start: str = "2026-01-01", end: str = "2026-06-30", item_id: str = "ocf-h1") -> dict[str, Any]:
    return fact(item_id, "operating_cash_flow", value, period_start=start, period_end=end)


def obligation(item_id: str, kind: str, value: str | None, due: str | None, gross_net: str = "gross", **kw: Any) -> dict[str, Any]:
    return fact(item_id, kind, value, due_date=due, gross_net=gross_net, **kw)


def financials(*facts: dict[str, Any], basis: str = "unrestricted_cash") -> FinancialInputs:
    return FinancialInputs(
        binding=GenerationBinding("financials", FINANCIAL_ITEM_SCHEMA, "partial", generation_id="fin-gen-1"),
        facts=tuple(facts),
        cash_basis=basis,
    )


def covenant(
    observation_id: str,
    value: Any,
    *,
    name: str = "minimum_liquidity_amount",
    disposition: str = "direct",
    unit: str | None = "USD",
    available_at: str = "2026-08-05T21:00:00Z",
    accession: str = "0001234567-26-000101",
) -> dict[str, Any]:
    return {
        "schema": COV_SCHEMA,
        "observation_id": observation_id,
        "term": {"name": name},
        "state": {"disposition": disposition},
        "normalized": {"unit": unit, "value": value},
        "filing": {"accession": accession, "form": "10-Q", "filing_date": "2026-08-05", "accepted_at": "2026-08-05T21:00:00Z"},
        "point_in_time": {"source_available_at": available_at, "available_at": available_at},
    }


def covenants(*records: dict[str, Any]) -> CommitmentInputs:
    return CommitmentInputs(
        binding=GenerationBinding("covenant_terms", COV_SCHEMA, "partial", generation_id="cov-gen-1"),
        commitments=tuple(records),
    )


def document_term(
    observation_id: str,
    name: str,
    value: str | None,
    *,
    filing_date: str,
    disposition: str = "observed",
    available_at: str | None = None,
) -> dict[str, Any]:
    stamp = available_at or f"{filing_date}T21:00:00Z"
    return {
        "schema": DOC_SCHEMA,
        "observation_id": observation_id,
        "term": {"name": name},
        "state": {"disposition": disposition},
        "normalized": {"raw_text": None if value is None else f"${value}", "value": value, "unit": "USD", "currency": "USD", "scale": 1},
        "filing": {"accession": f"0001234567-26-{observation_id[-6:]}", "form": "S-3", "filing_date": filing_date, "accepted_at": stamp},
        "point_in_time": {"source_available_at": stamp, "available_at": stamp},
    }


def documents(*records: dict[str, Any]) -> CommitmentInputs:
    return CommitmentInputs(
        binding=GenerationBinding("document_terms", DOC_SCHEMA, "partial", generation_id="doc-gen-1"),
        commitments=tuple(records),
    )


def usd(value: str) -> Quantity:
    return Quantity(unit="usd", status="known", value=value)


def scenario(
    *,
    burn: str | None = OCF_BASIS,
    working_capital: str | None = "excluded",
    seasonality: str | None = "flat",
    actions: tuple[ActionSelection, ...] = (),
    fee_rate: str | None = None,
    resolutions: tuple[UnknownResolution, ...] = (),
    as_of: str = AS_OF,
    start: str = H0,
    end: str = H1,
    price: PriceAssumption | None = None,
) -> FinancingScenario:
    other = []
    for key, value in (("burn_basis", burn), ("working_capital_basis", working_capital), ("seasonality_basis", seasonality)):
        if value is not None:
            other.append((key, value))
    return FinancingScenario(
        view="then_known",
        as_of=as_of,
        horizon_start=start,
        horizon_end=end,
        price=price or PriceAssumption(kind="fixed", fixed_price="2.00"),
        actions=actions,
        fee_rate=fee_rate,
        other_assumptions=tuple(other),
        unknown_resolutions=resolutions,
    )


def base_facts() -> list[dict[str, Any]]:
    return [cash(), ocf()]


def run(
    facts: list[dict[str, Any]] | None = None,
    commitments: CommitmentInputs | None = None,
    basis: str = "unrestricted_cash",
    **scenario_kw: Any,
) -> FundingSchedule:
    return project_funding(
        financials(*(base_facts() if facts is None else facts), basis=basis),
        commitments if commitments is not None else covenants(covenant("cov-min-1", "1000000")),
        scenario(**scenario_kw),
    )


def unknown_ids(schedule: FundingSchedule) -> set[str]:
    return {item.unknown_id for item in schedule.unknowns}


def assumption(schedule: FundingSchedule, key: str) -> Any:
    matches = [item for item in schedule.assumptions if item.key == key]
    assert len(matches) == 1, f"assumption {key!r} not emitted exactly once"
    return matches[0]


def all_flows(schedule: FundingSchedule) -> list[Any]:
    return [flow for period in schedule.periods for flow in (*period.sources, *period.uses)]


def flow(schedule: FundingSchedule, flow_id: str) -> Any:
    matches = [item for item in all_flows(schedule) if item.flow_id == flow_id]
    assert len(matches) == 1, f"flow {flow_id!r} not present exactly once"
    return matches[0]


def dec(quantity: Quantity) -> Decimal:
    assert quantity.status == "known", f"expected a known quantity, got {quantity.status}: {quantity.note}"
    return Decimal(quantity.value)


def keys(value: Any) -> Iterator[str]:
    if isinstance(value, dict):
        for key, item in value.items():
            yield key
            yield from keys(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from keys(item)


def assert_identity(schedule: FundingSchedule) -> None:
    for period in schedule.periods:
        if period.closing_balance.status != "known":
            continue
        counted_sources = sum((dec(f.amount) for f in period.sources if f.certainty != "conditional"), Decimal(0))
        counted_uses = sum((dec(f.amount) for f in period.uses if f.certainty != "conditional"), Decimal(0))
        assert dec(period.closing_balance) == dec(period.opening_balance) + counted_sources - counted_uses


# ---------------------------------------------------------------------------
# 1. Review class 5: conditional funding advertised as cash on hand
# ---------------------------------------------------------------------------


def test_review_class_5_conditional_funding_is_never_cash_on_hand() -> None:
    revolver = fact(
        "revolver-1",
        "revolver_availability",
        "2000000",
        measured_at=H0,
        condition="borrowing base certificate and no event of default",
    )
    actions = (
        ActionSelection("atm-1", "at_the_market", "cash", quantity=usd("3000000"), conditions_assumed_met=("shelf effective",)),
        ActionSelection("draw-1", "debt_draw", "cash", quantity=usd("1000000")),
    )
    capacity = document_term("doc-cap-000001", "proposed_maximum_aggregate_offering_price", "50000000", filing_date="2026-07-01")
    schedule = run([*base_facts(), revolver], commitments=documents(capacity), actions=actions)

    first, second = schedule.periods
    # the opening is cash on hand only: the undrawn revolver is not in it
    assert dec(first.opening_balance) == Decimal("5000000")
    sources = [item for period in schedule.periods for item in period.sources]
    assert {item.flow_id for item in sources} == {"source:revolver-1", "source:atm-1:gross", "source:draw-1:gross"}
    assert all(item.certainty == "conditional" and item.condition for item in sources)
    assert "not executed" in flow(schedule, "source:atm-1:gross").condition
    assert flow(schedule, "source:revolver-1").condition == "borrowing base certificate and no event of default"
    # closings exclude every conditional source exactly
    assert dec(first.closing_balance) == Decimal("5000000") - PER_PERIOD_BURN
    assert dec(second.closing_balance) == Decimal("5000000") - 2 * PER_PERIOD_BURN
    assert_identity(schedule)
    # registered capacity is never a source of any kind
    assert all("doc-cap-000001" not in item.flow_id for item in all_flows(schedule))
    assert all(item.amount.value != "50000000" for item in all_flows(schedule))


def test_review_class_5_revolver_without_a_condition_is_refused() -> None:
    revolver = fact("revolver-1", "revolver_availability", "2000000", measured_at=H0)
    with pytest.raises(FundingInputError, match="must name its condition"):
        run([*base_facts(), revolver])


def test_assumed_burn_is_a_counted_use_and_never_a_source() -> None:
    schedule = run()
    burns = [item for item in all_flows(schedule) if item.flow_id.startswith("use:burn:")]
    assert [item.flow_id for item in burns] == ["use:burn:2026-09-30", "use:burn:2026-12-31"]
    assert all(item.kind == "use" and item.certainty == "assumed" for item in burns)
    assert all(item.certainty != "assumed" for period in schedule.periods for item in period.sources)


# ---------------------------------------------------------------------------
# 2. Absent burn: every closing unknown, no runway anywhere
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("burn", [None, "unknown"])
def test_absent_or_unknown_burn_makes_every_closing_unknown_and_implies_no_runway(burn: str | None) -> None:
    schedule = run(burn=burn)
    item = assumption(schedule, "burn_basis")
    assert item.value == "unknown"
    if burn is None:
        assert item.rationale == "not supplied by the scenario"
    assert "unknown:burn_basis" in unknown_ids(schedule)
    assert schedule.periods and all(period.closing_balance.status == "unknown" for period in schedule.periods)
    assert not [flow for flow in all_flows(schedule) if flow.flow_id.startswith("use:burn:")]
    record = schedule.as_record()
    forbidden = [key for key in keys(record) if FORBIDDEN_PROPERTY_PATTERN.match(key) or "runway" in key]
    assert forbidden == []


def test_burn_without_a_matching_operating_cash_flow_period_is_unknown() -> None:
    schedule = run(burn="operating_cash_flow:2026-04-01:2026-06-30")
    assert "unknown:burn_basis" in unknown_ids(schedule)
    assert all(period.closing_balance.status == "unknown" for period in schedule.periods)


def test_negative_scenario_burn_rate_is_refused() -> None:
    with pytest.raises(FundingInputError):
        run(burn="fixed_usd_per_day:-500")


def test_zero_scenario_burn_models_no_burn_and_implies_no_runway() -> None:
    schedule = run(burn="fixed_usd_per_day:0")
    assert not [flow for flow in all_flows(schedule) if flow.flow_id.startswith("use:burn:")]
    for period in schedule.periods:
        assert dec(period.closing_balance) == Decimal("5000000")
        assert "no runway implied" in period.closing_balance.note


def test_unrecognised_burn_basis_and_assumption_values_are_refused() -> None:
    with pytest.raises(FundingInputError):
        run(burn="trailing_average")
    with pytest.raises(FundingInputError):
        run(working_capital="included")
    with pytest.raises(FundingInputError):
        run(seasonality="quarterly_weights")


@pytest.mark.parametrize("key", ["working_capital", "seasonality"])
def test_unknown_working_capital_or_seasonality_makes_every_closing_unknown(key: str) -> None:
    schedule = run(**{key: None})
    full = {"working_capital": "working_capital_basis", "seasonality": "seasonality_basis"}[key]
    assert f"unknown:{full}" in unknown_ids(schedule)
    assert assumption(schedule, full).value == "unknown"
    assert all(period.closing_balance.status == "unknown" for period in schedule.periods)


# ---------------------------------------------------------------------------
# 3. Non-negative operating cash flow ("negative burn")
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("value", ["250000", "0"])
def test_non_negative_operating_cash_flow_is_no_burn_no_source_and_no_runway(value: str) -> None:
    maturity = obligation("dm-1", "debt_maturity", "100000", "2026-08-15")
    schedule = run([cash(), ocf(value), maturity])
    first, second = schedule.periods
    assert not [item for item in all_flows(schedule) if item.flow_id.startswith("use:burn:")]
    assert not [item for period in schedule.periods for item in period.sources]
    assert dec(first.closing_balance) == Decimal("4900000")
    assert dec(second.closing_balance) == Decimal("4900000")
    for period in schedule.periods:
        assert "operating cash flow non-negative over 2026-01-01..2026-06-30" in period.closing_balance.note
        assert "no runway implied" in period.closing_balance.note
    assert schedule.periods[-1].period_end == H1
    assert all(period.period_end <= H1 for period in schedule.periods)


def test_zero_length_horizon_has_no_periods() -> None:
    schedule = run(start=H0, end=H0)
    assert schedule.periods == ()


# ---------------------------------------------------------------------------
# 4. Net loss is not burn
# ---------------------------------------------------------------------------


def test_net_loss_burn_basis_is_refused() -> None:
    with pytest.raises(FundingInputError, match="net loss is not burn"):
        run(burn="net_loss:2026-01-01:2026-06-30")


def test_a_net_loss_fact_never_changes_any_flow() -> None:
    loss = fact("nl-h1", "net_loss", "-9000000", period_start="2026-01-01", period_end="2026-06-30")
    without = run()
    with_loss = run([*base_facts(), loss])
    assert [period.as_record() for period in with_loss.periods] == [period.as_record() for period in without.periods]
    assert with_loss.assumptions == without.assumptions
    assert unknown_ids(with_loss) == unknown_ids(without)


# ---------------------------------------------------------------------------
# 5. Prorated burn with 0.01 quantization; identity and chaining
# ---------------------------------------------------------------------------


def test_burn_is_prorated_by_elapsed_days_with_cent_quantization() -> None:
    # 1,000,000 / 181 days x 92 days = 508,287.2928... -> 508,287.29
    schedule = run([cash(), ocf("-1000000")])
    first, second = schedule.periods
    assert (first.period_start, first.period_end) == ("2026-06-30", "2026-09-30")
    assert (second.period_start, second.period_end) == ("2026-09-30", "2026-12-31")
    assert flow(schedule, "use:burn:2026-09-30").amount.value == "508287.29"
    assert flow(schedule, "use:burn:2026-12-31").amount.value == "508287.29"
    assert dec(first.closing_balance) == Decimal("4491712.71")
    assert dec(second.closing_balance) == Decimal("3983425.42")
    assert second.opening_balance == first.closing_balance
    assert_identity(schedule)


def test_exact_burn_and_partial_first_period() -> None:
    schedule = run(start="2026-08-15", end=H1, facts=[cash(measured="2026-08-15", available_at="2026-08-20T20:00:00Z"), ocf()])
    first, second = schedule.periods
    assert (first.period_start, first.period_end) == ("2026-08-15", "2026-09-30")
    assert flow(schedule, "use:burn:2026-09-30").amount.value == "460000.00"  # 46 days x 10,000
    assert flow(schedule, "use:burn:2026-12-31").amount.value == "920000.00"
    assert dec(second.closing_balance) == Decimal("5000000") - Decimal("1380000")
    assert_identity(schedule)


def test_known_closings_over_partial_owner_coverage_say_so() -> None:
    schedule = run()
    for kind in ("restricted_cash", "revolver_availability", "accrued_interest", "debt_maturity", "committed_expenditure"):
        assert f"unknown:owner:{kind}" in unknown_ids(schedule)
    for period in schedule.periods:
        assert period.closing_balance.status == "known"
        assert "over observed dated flows only; see unknowns" in period.closing_balance.note


# ---------------------------------------------------------------------------
# 6. Dated gross, net and fees
# ---------------------------------------------------------------------------


def test_scenario_proceeds_keep_gross_and_fee_apart_and_net_only_in_a_note() -> None:
    actions = (ActionSelection("atm-1", "at_the_market", "cash", quantity=usd("3000000")),)
    schedule = run(actions=actions, fee_rate="0.03")
    gross = flow(schedule, "source:atm-1:gross")
    fee = flow(schedule, "use:atm-1:fee")
    assert dec(gross.amount) == Decimal("3000000")
    assert "net 2910000.00 reported, not substituted" in gross.amount.note
    assert dec(fee.amount) == Decimal("90000.00")
    assert gross.certainty == fee.certainty == "conditional"
    assert not [item for item in all_flows(schedule) if "net" in item.flow_id.split(":")]


def test_share_quantity_converts_only_through_a_fixed_usd_price() -> None:
    shares = Quantity(unit="shares", status="known", value="1000000", share_basis="scenario_incremental_issuance")
    schedule = run(actions=(ActionSelection("rd-1", "registered_direct", "cash", quantity=shares),))
    proceeds = flow(schedule, "source:rd-1:gross")
    assert dec(proceeds.amount) == Decimal("2000000.00")
    assert proceeds.amount.note == "price assumption"
    path = PriceAssumption(kind="path", path=(("2026-07-01", "2.00"),))
    unpriced = run(actions=(ActionSelection("rd-1", "registered_direct", "cash", quantity=shares),), price=path)
    assert flow(unpriced, "source:rd-1:gross").amount.status == "unknown"
    assert "unknown:action_amount:rd-1" in unknown_ids(unpriced)


def test_registration_fee_history_is_excluded_and_an_in_horizon_fee_is_a_dated_use() -> None:
    history = document_term("doc-fee-000001", "registration_fee", "15000", filing_date="2026-05-01")
    current = document_term("doc-fee-000002", "registration_fee", "25000", filing_date="2026-07-15")
    schedule = run(commitments=documents(history, current))
    assert all("doc-fee-000001" not in item.flow_id for item in all_flows(schedule))
    fee = flow(schedule, "use:doc-fee-000002")
    assert (fee.certainty, fee.dated, dec(fee.amount)) == ("contractual_dated", "2026-07-15", Decimal("25000"))
    assert fee in schedule.periods[0].uses
    assert dec(schedule.periods[0].closing_balance) == Decimal("5000000") - PER_PERIOD_BURN - Decimal("25000")
    assert_identity(schedule)


def test_obligation_gross_and_fee_both_count_and_net_never_does() -> None:
    gross = obligation("dm-1", "debt_maturity", "1000000", "2026-11-15", receipt=RECEIPT_A)
    fee = obligation("fc-1", "financing_cost", "25000", "2026-11-15", gross_net="fee", receipt=RECEIPT_A)
    net = obligation("dm-1-net", "debt_maturity", "975000", "2026-11-15", gross_net="net", receipt=RECEIPT_A)
    schedule = run([*base_facts(), gross, fee, net])
    second = schedule.periods[1]
    assert {item.flow_id for item in second.uses} == {"use:dm-1", "use:fc-1", "use:burn:2026-12-31"}
    assert all(item.certainty in ("contractual_dated", "assumed") for item in second.uses)
    assert "net 975000 reported, not substituted" in flow(schedule, "use:dm-1").amount.note
    assert all("dm-1-net" not in item.flow_id for item in all_flows(schedule))
    expected = Decimal("5000000") - 2 * PER_PERIOD_BURN - Decimal("1025000")
    assert dec(second.closing_balance) == expected
    assert_identity(schedule)


def test_net_obligation_without_its_gross_makes_every_closing_unknown() -> None:
    net = obligation("dm-1-net", "debt_maturity", "975000", "2026-11-15", gross_net="net", receipt=RECEIPT_B)
    schedule = run([*base_facts(), net])
    assert "unknown:gross_missing:dm-1-net" in unknown_ids(schedule)
    assert all(period.closing_balance.status == "unknown" for period in schedule.periods)
    assert all("dm-1-net" not in item.flow_id for item in all_flows(schedule))


def test_undated_obligation_is_a_timing_unknown_and_blocks_closings() -> None:
    undated = obligation("ce-1", "committed_expenditure", "400000", None)
    schedule = run([*base_facts(), undated])
    assert "unknown:timing:ce-1" in unknown_ids(schedule)
    assert all(period.closing_balance.status == "unknown" for period in schedule.periods)


def test_obligations_outside_the_horizon_are_excluded() -> None:
    before = obligation("dm-old", "debt_maturity", "700000", "2026-03-31")
    after = obligation("dm-far", "debt_maturity", "800000", "2027-06-30")
    schedule = run([*base_facts(), before, after])
    assert all(item.flow_id not in ("use:dm-old", "use:dm-far") for item in all_flows(schedule))
    assert dec(schedule.periods[1].closing_balance) == Decimal("5000000") - 2 * PER_PERIOD_BURN


def test_dated_obligation_with_an_unknown_amount_is_counted_as_unknown() -> None:
    unknown_amount = obligation("ai-1", "accrued_interest", None, "2026-12-15", status="unknown")
    schedule = run([*base_facts(), unknown_amount])
    assert flow(schedule, "use:ai-1").amount.status == "unknown"
    assert "unknown:amount:ai-1" in unknown_ids(schedule)
    assert schedule.periods[0].closing_balance.status == "known"
    assert schedule.periods[1].closing_balance.status == "unknown"


def test_undated_debt_balance_is_context_and_a_timing_unknown() -> None:
    balance = fact("ltd-1", "undated_debt_balance", "3000000", measured_at=H0)
    schedule = run([*base_facts(), balance])
    assert "unknown:timing:ltd-1" in unknown_ids(schedule)
    assert all("ltd-1" not in item.flow_id for item in all_flows(schedule))


def test_obligation_gross_net_must_be_named() -> None:
    with pytest.raises(FundingInputError, match="gross_net"):
        run([*base_facts(), obligation("dm-1", "debt_maturity", "100000", "2026-11-15", gross_net="blended")])


# ---------------------------------------------------------------------------
# 7. Basis composition
# ---------------------------------------------------------------------------


def test_missing_basis_member_makes_the_opening_unknown_never_a_partial_sum() -> None:
    schedule = run(basis="unrestricted_cash_and_marketable_securities")
    assert schedule.periods[0].opening_balance.status == "unknown"
    assert "unknown:opening:marketable_securities" in unknown_ids(schedule)
    assert all(period.closing_balance.status == "unknown" for period in schedule.periods)


def test_basis_members_on_one_date_sum_exactly() -> None:
    securities = fact("ms-q2", "marketable_securities", "1250000.50", measured_at=H0)
    schedule = run([*base_facts(), securities], basis="unrestricted_cash_and_marketable_securities")
    opening = schedule.periods[0].opening_balance
    assert dec(opening) == Decimal("6250000.50")
    assert opening.provenance.input_family == "financials"
    assert opening.provenance.generation_id == "fin-gen-1"


def test_basis_members_on_different_dates_refuse() -> None:
    securities = fact("ms-q1", "marketable_securities", "1250000", measured_at="2026-03-31")
    schedule = run([*base_facts(), securities], basis="unrestricted_cash_and_marketable_securities")
    assert schedule.periods[0].opening_balance.status == "unknown"
    assert "unknown:opening:date_mismatch" in unknown_ids(schedule)


def test_restricted_cash_basis_has_no_owner_and_is_unknown() -> None:
    schedule = run(basis="unrestricted_and_restricted_cash")
    assert "unknown:opening:restricted_cash" in unknown_ids(schedule)
    assert schedule.periods[0].opening_balance.status == "unknown"
    description = {item.unknown_id: item.description for item in schedule.unknowns}["unknown:opening:restricted_cash"]
    assert "no current owner emits restricted_cash" in description


def test_unknown_cash_basis_composes_no_opening() -> None:
    schedule = run(basis="unknown")
    assert "unknown:cash_basis" in unknown_ids(schedule)
    assert schedule.periods[0].opening_balance.status == "unknown"


def test_receivables_are_never_counted() -> None:
    receivables = fact("ar-q2", "receivables", "9000000", measured_at=H0)
    baseline = run()
    schedule = run([*base_facts(), receivables])
    assert dec(schedule.periods[0].opening_balance) == Decimal("5000000")
    assert all("ar-q2" not in item.flow_id for item in all_flows(schedule))
    assert [p.closing_balance for p in schedule.periods] == [p.closing_balance for p in baseline.periods]


def test_same_date_disagreement_is_contradicted_and_neither_is_chosen() -> None:
    schedule = run([cash("5000000"), cash("5100000", item_id="cash-q2-alt"), ocf()])
    assert "unknown:opening:contradicted:unrestricted_cash" in unknown_ids(schedule)
    assert schedule.periods[0].opening_balance.status == "unknown"


def test_equal_same_date_observations_dedupe() -> None:
    schedule = run([cash("5000000"), cash("5000000", item_id="cash-q2-copy"), ocf()])
    assert dec(schedule.periods[0].opening_balance) == Decimal("5000000")


def test_later_unresolved_observation_is_never_skipped_for_an_older_known_one() -> None:
    older = cash("4000000", measured="2026-03-31", item_id="cash-q1")
    latest = cash(None, status="unknown", item_id="cash-q2")
    schedule = run([older, latest, ocf()])
    assert "unknown:opening:unrestricted_cash" in unknown_ids(schedule)
    assert schedule.periods[0].opening_balance.status == "unknown"


def test_measurement_before_the_horizon_names_the_interim_flows() -> None:
    schedule = run(start="2026-07-31", end=H1)
    assert dec(schedule.periods[0].opening_balance) == Decimal("5000000")
    assert "measured 2026-06-30" in schedule.periods[0].opening_balance.note
    assert "unknown:interim_flows" in unknown_ids(schedule)


def test_non_usd_basis_member_is_excluded_not_converted() -> None:
    schedule = run([cash("4000000", unit="ratio"), ocf()])
    assert "unknown:unit:cash-q2" in unknown_ids(schedule)
    assert schedule.periods[0].opening_balance.status == "unknown"


def test_each_item_keeps_its_own_availability() -> None:
    mislabeled = cash()
    mislabeled["availability"] = "available_after_sale"
    with pytest.raises(FundingInputError, match="availability"):
        run([mislabeled, ocf()])


# ---------------------------------------------------------------------------
# 8. Minimum liquidity
# ---------------------------------------------------------------------------


def test_direct_usd_covenant_sets_a_known_floor_and_the_gap() -> None:
    schedule = run(commitments=covenants(covenant("cov-min-1", "4500000")))
    first, second = schedule.periods
    assert dec(first.minimum_liquidity) == Decimal("4500000")
    assert "0001234567-26-000101" in first.minimum_liquidity.note
    assert dec(first.gap) == Decimal("420000")  # 4,500,000 - 4,080,000
    assert dec(second.gap) == Decimal("1340000")  # 4,500,000 - 3,160,000
    assert _MIN_LIQ not in unknown_ids(schedule)


def test_gap_is_zero_when_the_closing_clears_the_floor() -> None:
    schedule = run(commitments=covenants(covenant("cov-min-1", 1000000)))
    assert [dec(period.gap) for period in schedule.periods] == [Decimal(0), Decimal(0)]


_MIN_LIQ = "unknown:minimum_liquidity"


def test_ambiguous_covenant_leaves_the_floor_unknown() -> None:
    schedule = run(commitments=covenants(covenant("cov-min-1", "4500000", disposition="ambiguous")))
    assert all(period.minimum_liquidity.status == "unknown" for period in schedule.periods)
    assert all(period.gap.status == "unknown" for period in schedule.periods)
    assert _MIN_LIQ in unknown_ids(schedule)


def test_ratio_covenant_is_not_liquidity() -> None:
    ratio = covenant("cov-lev-1", "3.5", name="maximum_leverage_ratio", unit="ratio")
    schedule = run(commitments=covenants(ratio))
    assert schedule.periods[0].minimum_liquidity.status == "unknown"
    assert _MIN_LIQ in unknown_ids(schedule)


def test_two_distinct_covenant_values_are_contradicted() -> None:
    records = covenants(covenant("cov-min-1", "1000000"), covenant("cov-min-2", "2000000", accession="0001234567-26-000202"))
    schedule = run(commitments=records)
    assert all(period.minimum_liquidity.status == "contradicted" for period in schedule.periods)
    assert _MIN_LIQ in unknown_ids(schedule)


def test_scenario_resolution_of_the_floor_is_honored() -> None:
    resolution = UnknownResolution(_MIN_LIQ, usd("2000000"), "lender term sheet minimum")
    schedule = run(commitments=covenants(covenant("cov-min-1", "4500000", disposition="ambiguous")), resolutions=(resolution,))
    assert dec(schedule.periods[0].minimum_liquidity) == Decimal("2000000")
    assert schedule.periods[0].minimum_liquidity.note == "scenario resolution: lender term sheet minimum"
    resolved = assumption(schedule, f"resolved:{_MIN_LIQ}")
    assert (resolved.value, resolved.rationale) == ("2000000", "lender term sheet minimum")
    assert _MIN_LIQ not in unknown_ids(schedule)


def test_scenario_resolution_never_overrides_an_observed_floor() -> None:
    resolution = UnknownResolution(_MIN_LIQ, usd("0"), "assume no covenant")
    schedule = run(commitments=covenants(covenant("cov-min-1", "4500000")), resolutions=(resolution,))
    assert dec(schedule.periods[0].minimum_liquidity) == Decimal("4500000")
    assert assumption(schedule, f"unhonored_resolution:{_MIN_LIQ}").value == "ignored"


def test_an_opening_member_resolution_is_recorded_unhonored() -> None:
    resolution = UnknownResolution("unknown:opening:marketable_securities", usd("1000000"), "assume the Q2 portfolio")
    schedule = run(basis="unrestricted_cash_and_marketable_securities", resolutions=(resolution,))
    item = assumption(schedule, "unhonored_resolution:unknown:opening:marketable_securities")
    assert item.value == "ignored"
    assert item.rationale == "an assumed balance or flow is never cash; F1 honors only the minimum-liquidity floor"
    assert schedule.periods[0].opening_balance.status == "unknown"
    assert "unknown:opening:marketable_securities" in unknown_ids(schedule)


def test_document_terms_call_leaves_the_floor_unknown() -> None:
    schedule = run(commitments=documents())
    assert _MIN_LIQ in unknown_ids(schedule)
    description = {item.unknown_id: item.description for item in schedule.unknowns}[_MIN_LIQ]
    assert "covenant_terms were not supplied" in description


# ---------------------------------------------------------------------------
# 9. Deficit
# ---------------------------------------------------------------------------


def test_deficit_closing_is_unknown_with_the_gap_known_against_a_known_floor() -> None:
    schedule = run([cash("500000"), ocf()], commitments=covenants(covenant("cov-min-1", "100000")), end="2027-03-31")
    first, second, third = schedule.periods
    assert first.closing_balance.status == "unknown"
    assert "computed balance -420000.00 usd" in first.closing_balance.note
    assert "(deficit)" in first.closing_balance.note
    assert dec(first.gap) == Decimal("520000.00")  # 100,000 - (-420,000)
    assert second.opening_balance.status == "unknown"
    assert second.opening_balance.note == "prior period ended in deficit"
    assert dec(second.gap) == Decimal("1440000.00")
    assert third.period_end == "2027-03-31"
    assert dec(third.gap) == Decimal("2340000.00")  # 90 days of burn in Q1 2027


def test_deficit_without_a_floor_states_a_lower_bound() -> None:
    schedule = run([cash("1000000"), ocf()], commitments=covenants())
    first, second = schedule.periods
    assert dec(first.closing_balance) == Decimal("80000")
    assert second.closing_balance.status == "unknown"
    assert "computed balance -840000.00 usd" in second.closing_balance.note
    assert second.gap.status == "unknown"
    assert second.gap.note == "at least 840000.00 usd"


# ---------------------------------------------------------------------------
# 10. Point in time
# ---------------------------------------------------------------------------


def test_a_fact_available_after_the_as_of_is_ignored() -> None:
    restated = cash("6000000", item_id="cash-q2-restated", available_at="2026-09-15T20:00:00Z")
    schedule = run([*base_facts(), restated])
    assert dec(schedule.periods[0].opening_balance) == Decimal("5000000")
    assert "unknown:opening:contradicted:unrestricted_cash" not in unknown_ids(schedule)
    later_duplicate = cash("6000000", available_at="2026-09-15T20:00:00Z")  # same item_id, not yet known
    assert dec(run([*base_facts(), later_duplicate]).periods[0].opening_balance) == Decimal("5000000")


def test_a_covenant_available_after_the_as_of_is_ignored() -> None:
    late = covenant("cov-min-1", "4500000", available_at="2026-09-02T00:00:00Z")
    schedule = run(commitments=covenants(late))
    assert schedule.periods[0].minimum_liquidity.status == "unknown"
    assert _MIN_LIQ in unknown_ids(schedule)


def test_duplicate_available_item_is_refused() -> None:
    with pytest.raises(FundingInputError, match="duplicate"):
        run([cash(), cash("5000000"), ocf()])


# ---------------------------------------------------------------------------
# 11. Conversion relief and the other scenario routes
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("route", ["conversion", "exchange"])
def test_conversion_relieves_the_matching_maturity_without_providing_cash(route: str) -> None:
    maturity = obligation("note-2026", "debt_maturity", "2000000", "2026-10-15")
    plain = run([*base_facts(), maturity])
    assert dec(plain.periods[1].closing_balance) == Decimal("5000000") - 2 * PER_PERIOD_BURN - Decimal("2000000")

    relieved = run([*base_facts(), maturity], actions=(ActionSelection("note-2026", route, "unknown"),))
    use = flow(relieved, "use:note-2026")
    assert use.certainty == "conditional"
    assert use.condition == "relieved under scenario conversion note-2026; relief provides no cash"
    assert use.dated == "2026-10-15"
    assert not [item for period in relieved.periods for item in period.sources]
    assert dec(relieved.periods[1].closing_balance) == Decimal("5000000") - 2 * PER_PERIOD_BURN
    assert_identity(relieved)


def test_warrant_exercise_cash_only_when_settled_in_cash() -> None:
    actions = (
        ActionSelection("w-cash", "warrant_exercise", "cash", quantity=usd("600000")),
        ActionSelection("w-cashless", "warrant_exercise", "cashless", quantity=usd("600000")),
        ActionSelection("w-prefunded", "warrant_exercise", "pre_funded", quantity=usd("600000")),
        ActionSelection("w-unknown", "warrant_exercise", "unknown", quantity=usd("600000")),
    )
    schedule = run(actions=actions)
    assert flow(schedule, "source:w-cash:gross").certainty == "conditional"
    assert all(not item.flow_id.startswith(("source:w-cashless", "source:w-prefunded", "source:w-unknown")) for item in all_flows(schedule))
    assert "unknown:settlement:w-unknown" in unknown_ids(schedule)
    assert dec(schedule.periods[0].closing_balance) == Decimal("5000000") - PER_PERIOD_BURN


def test_repurchase_is_a_conditional_use_and_other_is_unmodeled() -> None:
    actions = (
        ActionSelection("buyback-1", "repurchase", "cash", quantity=usd("250000")),
        ActionSelection("misc-1", "other", "unknown"),
    )
    schedule = run(actions=actions)
    use = flow(schedule, "use:buyback-1:repurchase")
    assert use.certainty == "conditional"
    assert "unknown:action_amount:misc-1" in unknown_ids(schedule)
    assert dec(schedule.periods[0].closing_balance) == Decimal("5000000") - PER_PERIOD_BURN


# ---------------------------------------------------------------------------
# 12. Interface, determinism and receipt
# ---------------------------------------------------------------------------


def test_public_interface_takes_exactly_three_parameters() -> None:
    parameters = inspect.signature(project_funding).parameters
    assert len(parameters) == 3
    assert list(parameters) == ["financials", "commitments", "scenario"]
    assert issubclass(FundingInputError, ValueError)


def test_projection_is_deterministic_and_carries_its_receipt() -> None:
    inputs = (financials(*base_facts()), covenants(covenant("cov-min-1", "1000000")), scenario())
    first = project_funding(*inputs)
    second = project_funding(*inputs)
    assert first.as_record() == second.as_record()
    assert json.dumps(first.as_record(), sort_keys=True) == json.dumps(second.as_record(), sort_keys=True)
    sc = inputs[2]
    assert first.scenario_id == sc.scenario_id
    assert first.receipt.scenario_id == sc.scenario_id
    assert first.receipt.rule_digest == RULE_DIGEST
    assert first.receipt.computed_at == sc.as_of
    assert first.cash_basis == "unrestricted_cash"
    other = project_funding(inputs[0], inputs[1], scenario(fee_rate="0.02"))
    assert other.scenario_id != first.scenario_id
    assert other.receipt.input_digest != first.receipt.input_digest
    assert IMPLEMENTATION.startswith("engine.capital_structure.funding.project_funding/")


def test_schedule_record_satisfies_the_state_schema_and_names_no_score() -> None:
    actions = (ActionSelection("atm-1", "at_the_market", "cash", quantity=usd("3000000")),)
    revolver = fact("revolver-1", "revolver_availability", "2000000", measured_at=H0, condition="no default")
    schedule = run([*base_facts(), revolver], actions=actions, fee_rate="0.03")
    record = schedule.as_record()
    validate_state_record("funding_schedule", record)
    assert [key for key in keys(record) if FORBIDDEN_PROPERTY_PATTERN.match(key)] == []
    assert not set(keys(record)) & set(FORBIDDEN_FIELDS)


def test_schedule_state_id_is_an_input_identity_never_an_issuer_state_id() -> None:
    """Seat ruling (2026-10-14): joining is C1's; a raw schedule id cannot collide with a state id.

    ``project_funding`` receives no ``CapitalState``, so ``FundingSchedule.state_id``
    names the funding inputs actually consumed.  The C1 assembler re-stamps it with
    the issuer state's id.  Here a ``CapitalState`` is built over the very same
    scenario inputs; the two ids must differ, and the re-stamped schedule must still
    satisfy the C0 schema.
    """
    fin = financials(*base_facts())
    com = covenants(covenant("cov-min-1", "1000000"))
    sc = scenario()
    schedule = project_funding(fin, com, sc)
    pattern = re.compile(r"^state:cs:[A-Fa-f0-9]{32}$")
    assert pattern.match(schedule.state_id)
    same_inputs = {"financials": fin.as_record(), "commitments": com.as_record(), "scenario": sc.as_record()}
    state = CapitalState(
        request=StateRequest(
            issuer_id="cik:0001234567",
            as_of=sc.as_of,
            view_mode="current",
            input_generations=(fin.binding, com.binding),
            rule_pack_id="rule_pack:cs:funding-test",
            rule_pack_version="1",
            rule_pack_digest=RULE_DIGEST,
        ),
        generated_at=sc.as_of,
        families=(
            FamilyState(
                "cash_funding",
                FamilyProvenance(
                    family="cash_funding",
                    input_family="financials",
                    input_schema=FINANCIAL_ITEM_SCHEMA,
                    support="partial",
                    compiler_version=STATE_CONTRACT_VERSION,
                    generation_id=fin.binding.generation_id,
                    support_limits=("one commitment family per projection",),
                    as_of=sc.as_of,
                ),
                records=(schedule.as_record(),),
            ),
        ),
        receipt=CalculationReceipt.build(
            inputs=same_inputs,
            rule_digest=RULE_DIGEST,
            implementation=IMPLEMENTATION,
            computed_at=sc.as_of,
            scenario_id=None,
        ),
    )
    assert pattern.match(state.state_id)
    assert schedule.state_id != state.state_id
    # Unchanged across reruns of the same inputs: it is an identity, not a nonce.
    assert project_funding(fin, com, sc).state_id == schedule.state_id
    # The C1 join path: re-stamp with the issuer state's id, and it stays valid.
    joined = dataclasses.replace(schedule, state_id=state.state_id)
    assert joined.state_id == state.state_id
    validate_state_record("funding_schedule", joined.as_record())
    assert joined.receipt == schedule.receipt


def test_consumed_financial_facts_are_admissible_capital_inputs_records() -> None:
    """The facts F1 consumes validate as C0 ``capital_inputs.financials`` (schema fix in #9278)."""
    revolver = fact("revolver-1", "revolver_availability", "2000000", measured_at=H0, condition="no default")
    fin = financials(*base_facts(), revolver, obligation("dm-1", "debt_maturity", "750000", "2026-11-15"))
    capital_inputs = CapitalInputs(bindings=(fin.binding,), financials=fin.facts)
    validate_state_record("capital_inputs", capital_inputs.as_record())
    project_funding(fin, covenants(covenant("cov-min-1", "1000000")), scenario())


def test_wrong_argument_types_are_refused() -> None:
    with pytest.raises(FundingInputError):
        project_funding(financials(*base_facts()), scenario(), covenants())  # type: ignore[arg-type]


def test_forbidden_field_in_a_financial_fact_is_refused() -> None:
    flagged = cash()
    flagged["source"]["signal"] = "buy"
    with pytest.raises(FundingInputError, match="forbidden field"):
        run([flagged, ocf()])


def test_contract_forbidden_property_is_refused_before_projection() -> None:
    scored = cash()
    scored["score"] = 0.9
    with pytest.raises(ContractViolation):
        financials(scored, ocf())


@pytest.mark.parametrize(
    "mutate, match",
    [
        (lambda r: r.update(item_kind="ebitda"), "item_kind"),
        (lambda r: r.update(item_id="bad id"), "item_id"),
        (lambda r: r["amount"].update(value="-5"), "amount.value"),
        (lambda r: r.pop("measured_at"), "measured_at"),
    ],
)
def test_malformed_financial_facts_are_refused(mutate: Any, match: str) -> None:
    record = cash()
    mutate(record)
    with pytest.raises(FundingInputError, match=match):
        run([record, ocf()])


# ---------------------------------------------------------------------------
# 13. Config parity with the F0 binding
# ---------------------------------------------------------------------------


def test_cash_basis_members_name_exactly_the_contract_cash_bases() -> None:
    assert set(CASH_BASIS_MEMBERS) == set(CASH_BASES)


@pytest.mark.skipif(not CONFIG.exists(), reason="F0 financial input binding config not on this base")
def test_item_rules_mirror_the_f0_binding_config() -> None:
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    items = {item["item_kind"]: item for item in config["items"]}
    assert set(items) == set(ITEM_RULES)
    for kind, rule in ITEM_RULES.items():
        item = items[kind]
        assert rule["availability"] == item["availability"], kind
        assert rule["flow_role"] == item["flow_role"], kind
        assert list(rule["cash_bases"]) == list(item["cash_bases"]), kind
        assert rule["measure"] == item["measure"], kind
        assert rule["owner_state"] == item["owner_state"], kind
    assert list(CONTEXT_KINDS) == [item["item_kind"] for item in config["context_items"]]
    composition = {key: tuple(value) for key, value in config["cash_basis_composition"].items() if key != "rules"}
    assert composition == CASH_BASIS_MEMBERS
    assert list(FORBIDDEN_FIELDS) == list(config["item_schema"]["forbidden_fields"])
    assert config["item_schema"]["schema"] == FINANCIAL_ITEM_SCHEMA
