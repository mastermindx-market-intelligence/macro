"""Step 5 b2: the query kernel upgrades an absence to a governed not-presented N/A.

The upgrade is lawful only on recomputable linkbase evidence from the slot's
own filing (R-NP): the parent total's anchor filing must carry a calculation
and a presentation linkbase whose composition of the parent foots exactly
without the metric's family.  Every other path stays absent, and an engine
without a not-presented pack emits byte-identical receipts.
"""

from __future__ import annotations

import json
from dataclasses import replace
from types import SimpleNamespace

import pytest

from engine.fundamental_forensics.not_presented import (
    NA_BASIS_NOT_PRESENTED_ITEM,
    NOT_PRESENTED_REASON,
    NotPresentedEvidence,
    load_not_presented_pack,
)
from engine.fundamental_forensics.query import (
    BitemporalPolicy,
    CellState,
    MetricCell,
    MetricMatrix,
    PeriodRequest,
    QueryValidationError,
)
from engine.fundamental_forensics.raw_ledger import FactContext
from tests.test_fundamental_forensics_not_presented import (
    BS_ARCS,
    BS_FACTS,
    BS_PRE,
    STATEMENT_ROLE,
    calc_xml,
    pre_xml,
)
from tests.test_fundamental_forensics_query import ENTITY_A, _engine, _fact, _policy

ANCHOR = "0000000001-26-000001"
OTHER = "0000000001-26-000099"
INSTANT = PeriodRequest.instant("2025-12-31", label="FY2025 close")
AFTER = "2026-10-22T00:00:00Z"
BEFORE = "2026-10-20T23:59:59Z"


@pytest.fixture(scope="module")
def np_pack():
    return load_not_presented_pack()


def _instant_context(entity_id: str = ENTITY_A) -> FactContext:
    return FactContext(
        context_id=f"ctx-instant-{entity_id}",
        entity_scheme="http://www.sec.gov/CIK",
        entity_identifier=entity_id,
        instant="2025-12-31",
    )


def _balance_sheet(accession: str = ANCHOR, **overrides: str):
    values = {qname.split(":", 1)[1]: str(value) for qname, value in BS_FACTS.items()}
    values.update(overrides)
    return tuple(
        _fact(
            concept=concept,
            value=value,
            accession=accession,
            context=_instant_context(),
            source_span=(index * 16, index * 16 + 8),
        )
        for index, (concept, value) in enumerate(values.items())
    )


def _package(accession: str = ANCHOR, *, arcs=BS_ARCS, pre=BS_PRE, roles=("calculation", "presentation")):
    names = {"calculation": "fixture_cal.xml", "presentation": "fixture_pre.xml"}
    content = {
        "fixture_cal.xml": calc_xml([(STATEMENT_ROLE, arcs)]),
        "fixture_pre.xml": pre_xml(pre),
    }
    return SimpleNamespace(
        manifest={
            "accession": accession,
            "members": [
                {"name": names[role], "state": "stored", "role": role} for role in roles
            ],
        },
        members={names[role]: content[names[role]] for role in roles},
    )


def _query(engine, metric: str = "goodwill", *, recorded: str = AFTER, selection=None):
    policy = _policy(source=recorded, recorded=recorded)
    if selection is not None:
        policy = _policy(source=recorded, recorded=recorded, selection=selection)
    return engine.query_matrix(tickers=["AAA"], metrics=[metric], periods=[INSTANT], policy=policy)


def _np_engine(np_pack, *facts, packages=None):
    return _engine(
        *(facts or _balance_sheet()),
        not_presented_pack=np_pack,
        filing_packages=(_package(),) if packages is None else packages,
    )


# ------------------------------------------------------------- the verdict --


def test_absent_goodwill_becomes_not_presented_with_recomputable_evidence(np_pack) -> None:
    engine = _np_engine(np_pack)
    matrix = _query(engine)
    cell = matrix.cells[0]

    assert cell.state is CellState.NOT_APPLICABLE
    assert cell.value is None
    assert cell.reason == NOT_PRESENTED_REASON
    provenance = cell.provenance
    assert provenance.na_basis == NA_BASIS_NOT_PRESENTED_ITEM
    evidence = provenance.not_presented
    assert isinstance(evidence, NotPresentedEvidence)
    assert evidence.rule_id == "not_presented.goodwill/v1"
    assert evidence.accession == ANCHOR
    # AssetsNoncurrent has no fact in the anchor filing: the second tier anchors.
    assert evidence.parent_concepts == ("us-gaap:Assets",)
    assert evidence.footing == "exact"
    assert (evidence.children_n, evidence.children_with_fact_n) == (3, 3)
    # A source-less N/A: no raw fact, no source occurrence is claimed.
    assert provenance.selected_raw_fact is None
    assert provenance.source_occurrence_ids == ()

    engine.verify_not_presented(cell)

    receipt = cell.to_dict()
    node_provenance = receipt["nodes"][0]["provenance"]
    assert node_provenance["na_basis"] == NA_BASIS_NOT_PRESENTED_ITEM
    assert node_provenance["not_presented"]["np_accession"] == ANCHOR
    assert MetricCell.from_dict(receipt).to_dict() == receipt

    exported = matrix.export_json()
    replayed = MetricMatrix.from_dict(json.loads(exported.payload))
    assert replayed.query_hash == matrix.query_hash
    assert replayed.cells[0].provenance.not_presented == evidence


def test_finite_lived_intangibles_use_the_same_gate(np_pack) -> None:
    cell = _query(_np_engine(np_pack), "intangible_assets_net").cells[0]
    assert cell.state is CellState.NOT_APPLICABLE
    assert cell.provenance.not_presented.rule_id == "not_presented.intangible_assets_net/v1"


def test_a_present_alias_always_wins(np_pack) -> None:
    facts = _balance_sheet() + (
        _fact(
            concept="Goodwill",
            value="5",
            accession=ANCHOR,
            context=_instant_context(),
            source_span=(900, 908),
        ),
    )
    cell = _query(_np_engine(np_pack, *facts)).cells[0]
    assert cell.state is CellState.VALUE
    assert cell.provenance.na_basis is None
    assert cell.provenance.not_presented is None


# ------------------------------------------------------- byte-identity --


def test_without_a_pack_or_before_the_rule_is_visible_receipts_are_byte_identical(np_pack) -> None:
    plain = _engine(*_balance_sheet())
    baseline = _query(plain, recorded=BEFORE)
    assert baseline.cells[0].state is CellState.MISSING

    # The pack is admitted, but its rule is not yet visible at this cutoff.
    early = _query(_np_engine(np_pack), recorded=BEFORE)
    assert early.export_json().payload == baseline.export_json().payload
    assert early.export_csv().payload == baseline.export_csv().payload

    # A metric the pack never touches is byte-identical after visibility too.
    plain_total = _query(plain, "total_assets")
    np_total = _query(_np_engine(np_pack), "total_assets")
    assert np_total.cells[0].state is CellState.VALUE
    assert np_total.export_json().payload == plain_total.export_json().payload

    # And with no pack the post-visibility absence is the ordinary MISSING.
    after_plain = _query(plain)
    assert after_plain.cells[0].state is CellState.MISSING
    assert "na_basis" not in after_plain.cells[0].to_dict()["nodes"][0]["provenance"]


# ------------------------------------------------ absent stays absent --


@pytest.mark.parametrize(
    "packages",
    [
        (),
        (_package(OTHER),),
        (_package(roles=("presentation",)),),
        (_package(roles=("calculation",)),),
        (_package(roles=("calculation", "calculation", "presentation")),),
    ],
    ids=["no-package", "other-filing", "no-calculation", "no-presentation", "two-calculations"],
)
def test_missing_filing_evidence_stays_absent(np_pack, packages) -> None:
    cell = _query(_np_engine(np_pack, packages=packages)).cells[0]
    assert cell.state is CellState.MISSING
    assert cell.provenance.na_basis is None


def test_a_footing_miss_stays_absent(np_pack) -> None:
    facts = _balance_sheet(AssetsCurrent="600001")
    assert _query(_np_engine(np_pack, *facts)).cells[0].state is CellState.MISSING


def test_conflicting_values_in_the_anchor_filing_stay_absent(np_pack) -> None:
    facts = _balance_sheet() + (
        _fact(
            concept="AssetsCurrent",
            value="600001",
            accession=ANCHOR,
            context=_instant_context(),
            source_span=(700, 708),
        ),
    )
    assert _query(_np_engine(np_pack, *facts)).cells[0].state is CellState.MISSING


def test_a_goodwill_line_in_the_statement_presentation_stays_absent(np_pack) -> None:
    pre = [(STATEMENT_ROLE, [*BS_PRE[0][1], "us-gaap:Goodwill"])]
    cell = _query(_np_engine(np_pack, packages=(_package(pre=pre),))).cells[0]
    assert cell.state is CellState.MISSING


def test_latest_restated_never_upgrades_an_absence(np_pack) -> None:
    cell = _query(_np_engine(np_pack), selection=BitemporalPolicy.LATEST_RESTATED).cells[0]
    assert cell.state is not CellState.NOT_APPLICABLE
    assert cell.provenance.not_presented is None


# ------------------------------------------------------- verification --


def _np_cell(np_pack):
    engine = _np_engine(np_pack)
    return engine, _query(engine).cells[0]


def _as_verifiable(cell, provenance):
    return SimpleNamespace(
        provenance=provenance,
        state=cell.state,
        reason=cell.reason,
        entity_id=cell.entity_id,
        metric_id=cell.metric_id,
        period=cell.period,
    )


def test_verify_refuses_tampered_evidence(np_pack) -> None:
    engine, cell = _np_cell(np_pack)
    tampered = replace(cell.provenance.not_presented, cal_sha256="0" * 64)
    forged = _as_verifiable(cell, replace(cell.provenance, not_presented=tampered))
    with pytest.raises(QueryValidationError, match="does not match its recomputation"):
        engine.verify_not_presented(forged)

    recount = replace(cell.provenance.not_presented, children_with_fact_n=2)
    with pytest.raises(QueryValidationError, match="does not match its recomputation"):
        engine.verify_not_presented(_as_verifiable(cell, replace(cell.provenance, not_presented=recount)))


def test_verify_refuses_without_the_admitted_filing(np_pack) -> None:
    _engine_with, cell = _np_cell(np_pack)
    without_package = _np_engine(np_pack, packages=())
    with pytest.raises(QueryValidationError, match="names no admitted package"):
        without_package.verify_not_presented(cell)
    with pytest.raises(QueryValidationError, match="no not-presented pack"):
        _engine(*_balance_sheet()).verify_not_presented(cell)

    # Different filed facts: the recomputation no longer foots.
    moved = _np_engine(np_pack, *_balance_sheet(AssetsCurrent="600001"))
    with pytest.raises(QueryValidationError, match="does not recompute: np_unbalanced"):
        moved.verify_not_presented(cell)


def test_verify_refuses_a_non_not_presented_cell(np_pack) -> None:
    engine = _np_engine(np_pack)
    value_cell = _query(engine, "total_assets").cells[0]
    with pytest.raises(QueryValidationError, match="not a not-presented verdict"):
        engine.verify_not_presented(value_cell)


# ------------------------------------------------------ receipt shape --


def test_provenance_pairs_the_basis_with_its_evidence(np_pack) -> None:
    _engine_np, cell = _np_cell(np_pack)
    provenance = cell.provenance
    with pytest.raises(QueryValidationError, match="must appear together"):
        replace(provenance, na_basis=None)
    with pytest.raises(QueryValidationError, match="must appear together"):
        replace(provenance, not_presented=None)
    with pytest.raises(QueryValidationError, match="not a governed N/A basis"):
        replace(provenance, na_basis="class_policy")
    with pytest.raises(QueryValidationError, match="must match the not_presented reason"):
        replace(provenance, reason="missing_standard_fact: forged")


def test_static_validator_refuses_a_forged_not_presented_state(np_pack) -> None:
    _engine_np, cell = _np_cell(np_pack)
    forged_node = replace(cell.root_node, state=CellState.MISSING, cell_id=None)
    forged_wire = cell.to_dict()
    forged_wire["root_cell_id"] = forged_node.cell_id
    forged_wire["nodes"] = [forged_node.to_dict()]
    with pytest.raises(QueryValidationError, match="does not match a governed kernel outcome"):
        MetricCell.from_dict(forged_wire)


def test_static_validator_refuses_another_metrics_rule(np_pack) -> None:
    _engine_np, cell = _np_cell(np_pack)
    foreign = replace(cell.provenance.not_presented, rule_id="not_presented.intangible_assets_net/v1")
    forged_node = replace(
        cell.root_node,
        provenance=replace(cell.provenance, not_presented=foreign),
        cell_id=None,
    )
    forged_wire = cell.to_dict()
    forged_wire["root_cell_id"] = forged_node.cell_id
    forged_wire["nodes"] = [forged_node.to_dict()]
    with pytest.raises(QueryValidationError, match="another metric's rule"):
        MetricCell.from_dict(forged_wire)


# ---------------------------------------------------------- admission --


def test_package_admission_fails_closed(np_pack) -> None:
    with pytest.raises(QueryValidationError, match="require a not_presented_pack"):
        _engine(*_balance_sheet(), filing_packages=(_package(),))
    with pytest.raises(QueryValidationError, match="duplicate filing package"):
        _np_engine(np_pack, packages=(_package(), _package()))
    with pytest.raises(QueryValidationError, match="no accession identity"):
        _np_engine(np_pack, packages=(SimpleNamespace(manifest={}, members={}),))
    with pytest.raises(QueryValidationError, match="bounded collection"):
        _np_engine(np_pack, packages={"accession": ANCHOR})
    with pytest.raises(QueryValidationError, match="loaded NP rule pack"):
        _engine(*_balance_sheet(), not_presented_pack=object())
