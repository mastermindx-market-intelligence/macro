"""Step 5 build-c: formulas read a governed not-presented operand (R-FORMULA F3).

A formula never materializes a not-presented operand as zero.  Its versioned
``not_presented_policy`` decides: a qualified signed sum adds the presented
operands and prints the omitted ones on the VALUE receipt
(``provenance.qualified_not_presented``), a ratio becomes not applicable, and
a formula without a policy withholds.  The policy carries its own rule clock,
so receipts before that clock are the historical bytes.
"""

from __future__ import annotations

import json
from dataclasses import replace
from decimal import Decimal
from types import SimpleNamespace

import pytest

from engine.fundamental_forensics.metric_registry import load_core_metric_registry
from engine.fundamental_forensics.not_presented import NOT_PRESENTED_REASON
from engine.fundamental_forensics.query import (
    FORMULA_NOT_PRESENTED_PREFIX,
    FORMULA_NOT_PRESENTED_WITHHELD_PREFIX,
    FORMULA_QUALIFIED_WITHHELD_PREFIX,
    CellState,
    MetricCell,
    MetricMatrix,
    PeriodRequest,
    QueryValidationError,
    _formula_policy_outcome,
)
from engine.fundamental_forensics.raw_ledger import FactContext
from tests.test_fundamental_forensics_metric_registry import _formula, _raw, _registry
from tests.test_fundamental_forensics_not_presented import calc_xml, pre_xml
from tests.test_fundamental_forensics_query import (
    ENTITY_A,
    PERIOD,
    ROOT,
    _engine,
    _fact,
    _policy,
    _replace_contract,
)

ANCHOR = "0000000001-26-000001"
OTHER = "0000000001-26-000099"
INSTANT = PeriodRequest.instant("2025-12-31", label="FY2025 close")
AFTER = "2026-10-22T00:00:00Z"
BEFORE = "2026-10-20T23:59:59Z"
BALANCE_ROLE = "http://ext.example/role/ConsolidatedBalanceSheets"
CASH_FLOW_ROLE = "http://ext.example/role/ConsolidatedStatementsOfCashFlows"

# Current liabilities foot exactly without any short-term debt line.
DEBT_FACTS = {
    "LiabilitiesCurrent": "500",
    "AccountsPayableCurrent": "300",
    "LongTermDebtCurrent": "50",
    "OtherLiabilitiesCurrent": "150",
    "LongTermDebtNoncurrent": "1000",
    "CashAndCashEquivalentsAtCarryingValue": "200",
    "StockholdersEquity": "2000",
}
DEBT_ARCS = [
    ("us-gaap:LiabilitiesCurrent", "us-gaap:AccountsPayableCurrent", "1"),
    ("us-gaap:LiabilitiesCurrent", "us-gaap:LongTermDebtCurrent", "1"),
    ("us-gaap:LiabilitiesCurrent", "us-gaap:OtherLiabilitiesCurrent", "1"),
]
# No debt operand at all: both liability subtotals foot without a debt line.
NO_DEBT_FACTS = {
    "LiabilitiesCurrent": "450",
    "AccountsPayableCurrent": "300",
    "OtherLiabilitiesCurrent": "150",
    "LiabilitiesNoncurrent": "400",
    "OtherLiabilitiesNoncurrent": "250",
    "DeferredIncomeTaxLiabilitiesNet": "150",
    "CashAndCashEquivalentsAtCarryingValue": "200",
    "StockholdersEquity": "2000",
}
NO_DEBT_ARCS = [
    ("us-gaap:LiabilitiesCurrent", "us-gaap:AccountsPayableCurrent", "1"),
    ("us-gaap:LiabilitiesCurrent", "us-gaap:OtherLiabilitiesCurrent", "1"),
    ("us-gaap:LiabilitiesNoncurrent", "us-gaap:OtherLiabilitiesNoncurrent", "1"),
    ("us-gaap:LiabilitiesNoncurrent", "us-gaap:DeferredIncomeTaxLiabilitiesNet", "1"),
]
# Investing cash flow foots exactly without a capital expenditure line.
CASH_FLOW_FACTS = {
    "NetCashProvidedByUsedInOperatingActivities": "900",
    "NetCashProvidedByUsedInInvestingActivities": "-300",
    "PaymentsToAcquireBusinessesNetOfCashAcquired": "400",
    "ProceedsFromSaleMaturityAndCollectionsOfInvestments": "100",
}
CASH_FLOW_ARCS = [
    (
        "us-gaap:NetCashProvidedByUsedInInvestingActivities",
        "us-gaap:PaymentsToAcquireBusinessesNetOfCashAcquired",
        "-1",
    ),
    (
        "us-gaap:NetCashProvidedByUsedInInvestingActivities",
        "us-gaap:ProceedsFromSaleMaturityAndCollectionsOfInvestments",
        "1",
    ),
]


@pytest.fixture(scope="module")
def np_pack():
    from engine.fundamental_forensics.not_presented import load_not_presented_pack

    return load_not_presented_pack()


def _instant_context() -> FactContext:
    return FactContext(
        context_id=f"ctx-instant-{ENTITY_A}",
        entity_scheme="http://www.sec.gov/CIK",
        entity_identifier=ENTITY_A,
        instant="2025-12-31",
    )


def _facts(values: dict[str, str], *, accession: str = ANCHOR, instant: bool = True):
    return tuple(
        _fact(
            concept=concept,
            value=value,
            accession=accession,
            context=_instant_context() if instant else None,
            source_span=(index * 16, index * 16 + 8),
        )
        for index, (concept, value) in enumerate(values.items())
    )


def _package(role: str, arcs, concepts, *, accession: str = ANCHOR):
    abstract = (
        "us-gaap:StatementOfFinancialPositionAbstract"
        if role == BALANCE_ROLE
        else "us-gaap:StatementOfCashFlowsAbstract"
    )
    return SimpleNamespace(
        manifest={
            "accession": accession,
            "members": [
                {"name": "fixture_cal.xml", "state": "stored", "role": "calculation"},
                {"name": "fixture_pre.xml", "state": "stored", "role": "presentation"},
            ],
        },
        members={
            "fixture_cal.xml": calc_xml([(role, arcs)]),
            "fixture_pre.xml": pre_xml([(role, [abstract, *(f"us-gaap:{c}" for c in concepts)])]),
        },
    )


def _debt_engine(np_pack, values=DEBT_FACTS, arcs=DEBT_ARCS, **kwargs):
    return _engine(
        *_facts(values),
        not_presented_pack=np_pack,
        filing_packages=(_package(BALANCE_ROLE, arcs, values),),
        **kwargs,
    )


def _query(engine, metric: str, *, period=INSTANT, recorded: str = AFTER):
    policy = _policy(source=recorded, recorded=recorded)
    return engine.query_matrix(tickers=["AAA"], metrics=[metric], periods=[period], policy=policy)


def _dependency(cell: MetricCell, metric_id: str):
    (node,) = [node for node in cell.dependency_nodes if node.metric_id == metric_id]
    return node


def _forge_root(cell: MetricCell, **provenance_changes) -> dict:
    forged = replace(
        cell.root_node,
        provenance=replace(cell.provenance, **provenance_changes),
        cell_id=None,
    )
    wire = cell.to_dict()
    wire["root_cell_id"] = forged.cell_id
    nodes = [node for node in wire["nodes"] if node["cell_id"] != cell.root_node.cell_id]
    wire["nodes"] = sorted([*nodes, forged.to_dict()], key=lambda node: node["cell_id"])
    return wire


# ------------------------------------------------------- qualified sum --


def test_total_debt_omits_a_not_presented_operand_and_prints_it(np_pack) -> None:
    matrix = _query(_debt_engine(np_pack), "total_debt")
    cell = matrix.cells[0]

    assert cell.state is CellState.VALUE
    assert cell.value == Decimal("1050")
    assert cell.reason is None
    assert cell.provenance.qualified_not_presented == ("short_term_debt",)
    omitted = _dependency(cell, "short_term_debt")
    assert omitted.state is CellState.NOT_APPLICABLE
    assert omitted.reason == NOT_PRESENTED_REASON
    assert omitted.value is None
    # The receipt's revision basis is the presented operands' shared filing.
    assert cell.provenance.accession == ANCHOR

    receipt = cell.to_dict()
    root = [node for node in receipt["nodes"] if node["cell_id"] == receipt["root_cell_id"]][0]
    assert root["provenance"]["qualified_not_presented"] == ["short_term_debt"]
    assert MetricCell.from_dict(receipt).to_dict() == receipt

    replayed = MetricMatrix.from_dict(json.loads(matrix.export_json().payload))
    assert replayed.query_hash == matrix.query_hash
    assert replayed.cells[0].provenance.qualified_not_presented == ("short_term_debt",)


@pytest.mark.parametrize(
    ("metric", "expected"),
    [
        ("net_debt", Decimal("850")),
        ("cash_to_total_debt", Decimal("200") / Decimal("1050")),
        ("debt_to_equity", Decimal("1050") / Decimal("2000")),
    ],
)
def test_debt_consumers_inherit_the_qualifier(np_pack, metric: str, expected: Decimal) -> None:
    matrix = _query(_debt_engine(np_pack), metric)
    cell = matrix.cells[0]

    assert cell.state is CellState.VALUE
    assert cell.value.quantize(Decimal("1e-12")) == expected.quantize(Decimal("1e-12"))
    assert cell.provenance.qualified_not_presented == ("short_term_debt",)
    assert _dependency(cell, "total_debt").provenance.qualified_not_presented == ("short_term_debt",)
    receipt = cell.to_dict()
    assert MetricCell.from_dict(receipt).to_dict() == receipt


def test_free_cash_flow_omits_capital_expenditures_only(np_pack) -> None:
    engine = _engine(
        *_facts(CASH_FLOW_FACTS, instant=False),
        not_presented_pack=np_pack,
        filing_packages=(_package(CASH_FLOW_ROLE, CASH_FLOW_ARCS, CASH_FLOW_FACTS),),
    )
    cell = _query(engine, "free_cash_flow", period=PERIOD).cells[0]

    assert cell.state is CellState.VALUE
    assert cell.value == Decimal("900")
    assert cell.provenance.qualified_not_presented == ("capital_expenditures",)
    assert _dependency(cell, "capital_expenditures").reason == NOT_PRESENTED_REASON


# ---------------------------------------------------- never a zero --


def test_every_operand_not_presented_is_not_applicable_never_zero(np_pack) -> None:
    engine = _debt_engine(np_pack, NO_DEBT_FACTS, NO_DEBT_ARCS)
    total = _query(engine, "total_debt").cells[0]

    assert total.state is CellState.NOT_APPLICABLE
    assert total.value is None
    assert total.reason == (
        FORMULA_NOT_PRESENTED_PREFIX + "short_term_debt, long_term_debt_current, long_term_debt"
    )
    assert total.provenance.qualified_not_presented == ()
    assert "qualified_not_presented" not in total.to_dict()["nodes"][0]["provenance"]

    # A ratio or a difference reading that N/A total is itself N/A, never zero.
    for metric in ("net_debt", "cash_to_total_debt", "debt_to_equity"):
        cell = _query(engine, metric).cells[0]
        assert cell.state is CellState.NOT_APPLICABLE, metric
        assert cell.value is None
        assert cell.reason == FORMULA_NOT_PRESENTED_PREFIX + "total_debt"
        receipt = cell.to_dict()
        assert MetricCell.from_dict(receipt).to_dict() == receipt


def test_a_missing_operand_keeps_the_sum_absent(np_pack) -> None:
    values = {key: value for key, value in DEBT_FACTS.items() if key != "LongTermDebtNoncurrent"}
    cell = _query(_debt_engine(np_pack, values), "total_debt").cells[0]

    assert cell.state is CellState.MISSING
    assert cell.value is None
    assert cell.reason.startswith("missing_dependency: long_term_debt (")
    assert _dependency(cell, "short_term_debt").reason == NOT_PRESENTED_REASON


def test_without_a_policy_the_formula_withholds(np_pack) -> None:
    registry = load_core_metric_registry(ROOT)
    contract = registry.metric("total_debt")
    stripped = _replace_contract(
        registry, "total_debt", formula=replace(contract.formula, not_presented_policy=None)
    )
    cell = _query(_debt_engine(np_pack, registry=stripped), "total_debt").cells[0]

    assert cell.state is CellState.MISSING
    assert cell.value is None
    assert cell.reason == FORMULA_NOT_PRESENTED_WITHHELD_PREFIX + "short_term_debt"


# ------------------------------------------------------- byte-identity --


def test_before_the_policy_clock_receipts_are_the_historical_bytes(np_pack) -> None:
    registry = load_core_metric_registry(ROOT)
    stripped = _replace_contract(
        registry,
        "total_debt",
        formula=replace(registry.metric("total_debt").formula, not_presented_policy=None),
    )
    present = dict(DEBT_FACTS, ShortTermBorrowings="25")
    with_policy = _engine(*_facts(present))
    without_policy = _engine(*_facts(present), registry=stripped)

    before = _query(with_policy, "total_debt", recorded=BEFORE)
    assert before.cells[0].state is CellState.VALUE
    assert before.cells[0].value == Decimal("1075")
    assert (
        before.export_json().payload
        == _query(without_policy, "total_debt", recorded=BEFORE).export_json().payload
    )
    # After the clock the policy is governance the receipt must name.
    assert (
        _query(with_policy, "total_debt").export_json().payload
        != _query(without_policy, "total_debt").export_json().payload
    )
    assert registry.governance_bundle_at(BEFORE).formula_for("total_debt").not_presented_policy is None
    assert registry.governance_bundle_at(AFTER).formula_for("total_debt").not_presented_policy is not None

    # The not-presented pack and the policy share the clock: before it the
    # omitted operand is an ordinary absence and the sum stays absent.
    early = _query(_debt_engine(np_pack), "total_debt", recorded=BEFORE).cells[0]
    assert early.state is CellState.MISSING
    assert early.reason.startswith("missing_dependency: short_term_debt (")
    assert (
        _query(_debt_engine(np_pack), "total_debt", recorded=BEFORE).export_json().payload
        == _query(_engine(*_facts(DEBT_FACTS)), "total_debt", recorded=BEFORE).export_json().payload
    )


def test_policy_round_trips_on_the_governance_bundle_wire() -> None:
    from engine.fundamental_forensics.metric_registry import GovernanceBundle

    bundle = load_core_metric_registry(ROOT).governance_bundle_at(AFTER)
    wire = bundle.to_dict()
    formulas = {item["metric_id"]: item for item in wire["formulas"]}
    assert formulas["total_debt"]["not_presented_policy"]["mode"] == "qualified_sum"
    assert formulas["net_debt"]["not_presented_policy"]["qualified_operand"] == "inherit"
    assert "not_presented_policy" not in formulas["working_capital"]
    assert GovernanceBundle.from_dict(wire).to_dict() == wire


# --------------------------------------------------- replay refusals --


def test_a_tampered_qualifier_does_not_replay(np_pack) -> None:
    cell = _query(_debt_engine(np_pack), "total_debt").cells[0]

    with pytest.raises(QueryValidationError, match="qualifier does not recompute"):
        MetricCell.from_dict(_forge_root(cell, qualified_not_presented=()))
    with pytest.raises(QueryValidationError, match="qualifier does not recompute"):
        MetricCell.from_dict(
            _forge_root(cell, qualified_not_presented=("long_term_debt", "short_term_debt"))
        )

    wire = cell.to_dict()
    root = [node for node in wire["nodes"] if node["cell_id"] == wire["root_cell_id"]][0]
    root["provenance"]["qualified_not_presented"] = []
    with pytest.raises(QueryValidationError, match="omitted, never empty"):
        MetricCell.from_dict(wire)


def test_the_qualifier_is_printed_only_on_a_formula_value(np_pack) -> None:
    cell = _query(_debt_engine(np_pack), "total_debt").cells[0]
    direct = _dependency(cell, "long_term_debt")
    with pytest.raises(QueryValidationError, match="printed only on a formula value"):
        replace(direct.provenance, qualified_not_presented=("short_term_debt",))

    total = _query(_debt_engine(np_pack, NO_DEBT_FACTS, NO_DEBT_ARCS), "total_debt").cells[0]
    with pytest.raises(QueryValidationError, match="printed only on a formula value"):
        replace(total.provenance, qualified_not_presented=("short_term_debt",))


# ------------------------------------------- the decision, function level --


def _op(metric_id, state=CellState.VALUE, value="1", *, reason=None, accession=ANCHOR,
        qualified=(), evidence_accession=None):
    return SimpleNamespace(
        metric_id=metric_id,
        state=state,
        value=Decimal(value) if state is CellState.VALUE else None,
        reason=reason,
        provenance=SimpleNamespace(
            source="sec-edgar" if state is CellState.VALUE else None,
            accession=accession if state is CellState.VALUE else None,
            document_id="fixture-10k.htm" if state is CellState.VALUE else None,
            source_body_sha256=("a" * 64) if state is CellState.VALUE else None,
            qualified_not_presented=qualified,
            not_presented=(
                SimpleNamespace(accession=evidence_accession) if evidence_accession else None
            ),
        ),
    )


def _np(metric_id, *, evidence_accession=ANCHOR):
    return _op(
        metric_id,
        CellState.NOT_APPLICABLE,
        reason=NOT_PRESENTED_REASON,
        evidence_accession=evidence_accession,
    )


@pytest.fixture(scope="module")
def formulas():
    registry = load_core_metric_registry(ROOT)
    return {metric: registry.metric(metric).formula for metric in registry.metric_ids}


def test_policy_decision_table(formulas) -> None:
    total_debt = formulas["total_debt"]
    fcf = formulas["free_cash_flow"]

    # No not-presented operand and no qualifier: the historical triage decides.
    assert _formula_policy_outcome([_op("short_term_debt"), _op("long_term_debt_current"), _op("long_term_debt")], total_debt) is None
    # A class N/A beside a not-presented operand also defers to that triage.
    assert _formula_policy_outcome(
        [_np("short_term_debt"), _op("long_term_debt_current", CellState.NOT_APPLICABLE, reason="class_policy: x"), _op("long_term_debt")],
        total_debt,
    ) is None

    # An ineligible omission withholds: operating cash flow is never omitted.
    outcome = _formula_policy_outcome([_np("net_cash_from_operating_activities"), _op("capital_expenditures")], fcf)
    assert (outcome.state, outcome.reason) == (
        CellState.MISSING,
        FORMULA_NOT_PRESENTED_WITHHELD_PREFIX + "net_cash_from_operating_activities",
    )

    # Every operand omitted: not applicable, never a zero sum.
    outcome = _formula_policy_outcome([_np("short_term_debt"), _np("long_term_debt_current"), _np("long_term_debt")], total_debt)
    assert (outcome.state, outcome.value) == (CellState.NOT_APPLICABLE, None)

    # Omission evidence from another filing, or presented operands from two
    # filings, cannot share one revision basis.
    outcome = _formula_policy_outcome(
        [_np("short_term_debt", evidence_accession=OTHER), _op("long_term_debt_current"), _op("long_term_debt")],
        total_debt,
    )
    assert outcome.state is CellState.NOT_EVALUABLE
    assert outcome.reason.startswith("incompatible_revision_basis: ")
    outcome = _formula_policy_outcome(
        [_np("short_term_debt"), _op("long_term_debt_current"), _op("long_term_debt", accession=OTHER)],
        total_debt,
    )
    assert outcome.state is CellState.NOT_EVALUABLE

    # A formula N/A operand carries no linkbase evidence of its own; inside a
    # qualified sum it fails closed.
    nested = _op(
        "short_term_debt",
        CellState.NOT_APPLICABLE,
        reason=FORMULA_NOT_PRESENTED_PREFIX + "x",
    )
    outcome = _formula_policy_outcome([nested, _op("long_term_debt_current"), _op("long_term_debt")], total_debt)
    assert outcome.state is CellState.NOT_EVALUABLE

    # A not-evaluable operand beside an omission stays not evaluable.
    outcome = _formula_policy_outcome(
        [_np("short_term_debt"), _op("long_term_debt_current", CellState.NOT_EVALUABLE, reason="x"), _op("long_term_debt")],
        total_debt,
    )
    assert outcome.state is CellState.NOT_EVALUABLE
    assert outcome.reason.startswith("incompatible_dependencies: long_term_debt_current")

    # A qualified operand feeds an inheriting formula and keeps a withholding
    # (or policy-less) formula absent.
    qualified = _op("total_debt", value="1050", qualified=("short_term_debt",))
    outcome = _formula_policy_outcome([qualified, _op("cash_and_cash_equivalents", value="200")], formulas["net_debt"])
    assert (outcome.state, outcome.value, outcome.qualified_not_presented) == (
        CellState.VALUE,
        Decimal("850"),
        ("short_term_debt",),
    )
    assert outcome.value_summary is False
    outcome = _formula_policy_outcome(
        [_op("gross_profit", qualified=("x",)), _op("revenue")], formulas["gross_margin"]
    )
    assert (outcome.state, outcome.reason) == (CellState.MISSING, FORMULA_QUALIFIED_WITHHELD_PREFIX + "gross_profit")
    outcome = _formula_policy_outcome(
        [_op("current_assets", qualified=("x",)), _op("current_liabilities")], formulas["working_capital"]
    )
    assert (outcome.state, outcome.reason) == (CellState.MISSING, FORMULA_QUALIFIED_WITHHELD_PREFIX + "current_assets")
    # And a policy-less formula withholds an omitted operand.
    outcome = _formula_policy_outcome([_np("current_assets"), _op("current_liabilities")], formulas["working_capital"])
    assert (outcome.state, outcome.reason) == (CellState.MISSING, FORMULA_NOT_PRESENTED_WITHHELD_PREFIX + "current_assets")


# ------------------------------------------------------------ loader --


def _set_policy(metric_id: str, **changes):
    raw = _raw()
    catalog, mappings, formulas = raw
    entry = _formula(formulas, metric_id)
    for key, value in changes.items():
        if key == "expression":
            entry["expression"] = value
        elif value is None:
            entry["not_presented_policy"].pop(key)
        else:
            entry["not_presented_policy"][key] = value
    return raw


@pytest.mark.parametrize(
    ("metric_id", "changes", "message"),
    [
        (
            "gross_margin",
            {"mode": "qualified_sum", "eligible_operands": ["gross_profit"], "all_not_presented": "not_applicable"},
            "signed sum",
        ),
        (
            "total_debt",
            {"expression": "short_term_debt + long_term_debt_current + long_term_debt - short_term_debt + short_term_debt"},
            "exactly once",
        ),
        ("total_debt", {"eligible_operands": ["cash_and_cash_equivalents"]}, "unknown input"),
        ("total_debt", {"eligible_operands": ["long_term_debt", "short_term_debt"]}, "dependency order"),
        ("total_debt", {"eligible_operands": []}, "at least one operand"),
        ("total_debt", {"all_not_presented": "zero"}, "all_not_presented is unsupported"),
        ("total_debt", {"all_not_presented": None}, "omits required field"),
        ("net_debt", {"mode": "zero_fill"}, "mode is unsupported"),
        ("net_debt", {"qualified_operand": "zero"}, "qualified_operand is unsupported"),
        ("net_debt", {"eligible_operands": ["total_debt"]}, "unsupported field"),
        ("net_debt", {"reason": "x" * 513}, "exceeds 512 characters"),
        (
            "net_debt",
            {"rule": {"rule_id": "formula_policy.net_debt/v1", "version": "1.0.0", "available_at": "2026-08-01T00:00:00Z", "confidence": "C"}},
            "cannot predate its formula rule",
        ),
        (
            "net_debt",
            {"rule": {"rule_id": "formula_policy.net_debt/v1", "version": "1.0.0", "available_at": "2026-10-21T00:00:00Z", "confidence": "B"}},
            "confidence must match",
        ),
        (
            "net_debt",
            {"rule": {"rule_id": "formula_policy.total_debt/v1", "version": "1.0.0", "available_at": "2026-10-21T00:00:00Z", "confidence": "C"}},
            "duplicate immutable rule",
        ),
    ],
)
def test_loader_refuses_an_ungoverned_policy(metric_id, changes, message) -> None:
    with pytest.raises(ValueError, match=message):
        _registry(_set_policy(metric_id, **changes))
