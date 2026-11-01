"""Query-side metric qualification wiring (S1-b) — acceptance harness.

Covers the two-stage ``qualify_metric`` wiring in
``engine/fundamental_forensics/query.py``: an issuer stage in
``BitemporalMetricQueryEngine._evaluate`` (after contract resolution, before
dispatch) and a denominator stage in ``_evaluate_formula`` (after dependency
cells assemble, before the not_evaluable/missing triage), plus the receipt
surface they emit:

- ``CellState.NOT_APPLICABLE = "not_applicable"`` (the S1-a
  ``ALLOWED_QUALIFICATION_STATES`` name reused verbatim).
- ``QueryEntity.issuer_sic: str | int | None = None`` (normalized digit-string
  or ``None``; flows through ``_normalize_entities`` wire mappings as an
  optional ``issuer_sic`` key, and ``_entity_for`` compares identity fields
  only).
- ``CellProvenance.issuer_class: str | None = None`` and
  ``CellProvenance.issuer_class_basis: str | None = None`` — emitted in
  ``to_dict`` ONLY when not ``None`` (byte-inert for every existing receipt)
  and accepted as optional keys by the wire ``from_dict`` parsers.
- Refusal reasons, verbatim from S1-a / E0:
  ``"not_applicable_for_issuer_class"`` (NOT_APPLICABLE),
  ``"issuer_class_unknown"`` (NOT_EVALUABLE),
  ``"denominator_missing:<input_id>"`` (NOT_EVALUABLE),
  ``"denominator_not_positive:<input_id>"`` (NOT_APPLICABLE).
- Receipt validators taught the new outcomes: the direct closed outcome
  tables, a pre-source qualification branch in ``_validate_direct_node``,
  an early issuer branch in ``_validate_formula_node``, and
  ``_expected_formula_outcome`` parity (including NOT_APPLICABLE dependency
  triage) so refusal receipts replay canonically.

Pins: the two digests in ``_PREWIRE_*`` were captured at 7fd00a6b754e
(S1-a PR #8952 head) by the prep lane over the PRODUCTION catalog with a
1x3x1 matrix (revenue, gross_profit, gross_margin; FY2025; industrial facts
100/40), and re-verified byte-identical at the S1-b base (S2 #9001 merged).
The G0 catalog change (issuer-class applicability on 16 metrics) is the
governed change the docstring below anticipated: ``_PREWIRE_QUERY_HASH``
and ``_PREWIRE_TO_DICT_SHA256`` were re-captured in the G0-r1p3 re-pin
commit e94ba62aa89 over the same industrial matrix, and the bank matrix — whose
"default-inert" premise that change retired by design — is pinned
separately in ``_BANK_QUERY_HASH`` / ``_BANK_TO_DICT_SHA256``.  All
captures hash ``canonical_json(matrix.to_dict())`` from
``engine.fundamental_forensics.models``.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from decimal import Decimal

import pytest

from engine.fundamental_forensics.detectors import (
    NOT_EVALUABLE_REASON_NOT_APPLICABLE_FOR_ISSUER_CLASS,  # requires E0 #8930 merged
)
from engine.fundamental_forensics.models import canonical_json
from engine.fundamental_forensics.metric_registry import (
    load_core_metric_registry,
    load_metric_registry,
    qualify_metric,
)
from engine.fundamental_forensics.query import (
    BitemporalMetricQueryEngine,
    BitemporalPolicy,
    CellState,
    PeriodRequest,
    ProvenanceKind,
    QueryEntity,
    QueryPolicy,
)
from engine.fundamental_forensics.raw_ledger import (
    FactContext,
    FactEventType,
    FactUnit,
    RawFactLedger,
    SourceIdentity,
    make_raw_fact,
)


ROOT = Path(__file__).resolve().parents[1]
ENTITY = "0000000001"
PERIOD = PeriodRequest.duration("2025-01-01", "2025-12-31", label="FY2025")
QUALIFICATION_ROOT = (
    ROOT / "tests" / "fixtures" / "fundamental_forensics" / "metric_registry_qualification"
)

# Captured at 7fd00a6b754eb4a1955b352639e9b5ac4cff402d (pre-wiring) by the
# S1-b prep lane; re-captured over the G0 catalog at the FIF G0-r1p3 re-pin
# commit (see the module docstring and that commit's message for the capture
# sha) with engine.fundamental_forensics.models.canonical_json over the same
# industrial 1x3x1 matrix; see module docstring.
_PREWIRE_QUERY_HASH = "17f6436d02a578227b561094a44dec4b23b5345b02dfa5cb3ac01a36d261e705"
_PREWIRE_TO_DICT_SHA256 = "fcc9a0d45503897f23023069a49a806a327a249fe7d9397f1c93e6befb76f29a"
# The BANK-SIC matrix under the G0 catalog (same 1x3x1 inputs, issuer SIC
# 6020): the two class-restricted metrics in the matrix read
# NOT_APPLICABLE(not_applicable_for_issuer_class) and the unrestricted
# revenue keeps its BASE value byte for byte (leaf-diff vs BASE 99b9a7f61fc0
# shows only digest-family leaves plus those two exception rows).
_BANK_QUERY_HASH = "2cbb5ee9b862cb47b7180814a3f0426329f8d654fba643edd194302b6e96f587"
_BANK_TO_DICT_SHA256 = "86015238cd66addf1bb96b9f98f06c9c2f609ea66b66666af54d2c780ac89937"


def _body(seed: str) -> str:
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()


def _fact(concept: str, value: str):
    return make_raw_fact(
        source=SourceIdentity(
            source="sec-edgar",
            entity_id=ENTITY,
            accession="0000000001-26-000001",
            document_id="fixture-10k.htm",
            body_sha256=_body(f"{ENTITY}:0000000001-26-000001:fixture-10k.htm"),
            source_url="https://www.sec.gov/Archives/0000000001-26-000001",
        ),
        concept_qname=f"us-gaap:{concept}",
        context=FactContext(
            context_id=f"ctx-{ENTITY}",
            entity_scheme="http://www.sec.gov/CIK",
            entity_identifier=ENTITY,
            start="2025-01-01",
            end="2025-12-31",
        ),
        unit=FactUnit("USD", ["iso4217:USD"]),
        raw_token=value,
        parsed_value=value,
        dimensions_known=True,
        source_span=(0, 8),
        accepted_at="2026-08-02T01:00:00Z",
        recorded_at="2026-08-02T02:00:00Z",
        event_type=FactEventType.FILED,
    )


def _revenue_fact() -> object:
    return _fact("RevenueFromContractWithCustomerExcludingAssessedTax", "100")


def _gross_profit_fact() -> object:
    return _fact("GrossProfit", "40")


def _zero_revenue_fact() -> object:
    return _fact("RevenueFromContractWithCustomerExcludingAssessedTax", "0")


def _policy() -> QueryPolicy:
    return QueryPolicy(
        source_snapshot_at="2026-08-05T00:00:00Z",
        recorded_at="2026-08-05T00:00:00Z",
        selection=BitemporalPolicy.LATEST_KNOWN_AS_OF,
    )


def _engine(facts, registry, *, issuer_sic: str | None) -> BitemporalMetricQueryEngine:
    facts = tuple(facts)
    metadata = {
        f.occurrence_id: {
            "accession": f.source.accession,
            "document_id": f.source.document_id,
            "source_body_sha256": f.source.body_sha256,
            "available_at": f.recorded_at,
            "form": "10-K",
        }
        for f in facts
    }
    entity = QueryEntity(ticker="AAA", entity_id=ENTITY, issuer_sic=issuer_sic)
    return BitemporalMetricQueryEngine(
        RawFactLedger(facts),
        registry,
        entities=[entity],
        filing_metadata=metadata or None,
    )


def _qualification_registry():
    return load_metric_registry(
        QUALIFICATION_ROOT / "metric_catalog.yaml",
        QUALIFICATION_ROOT / "mappings.yaml",
        QUALIFICATION_ROOT / "formulas.yaml",
        enforce_core_v1_inventory=False,
    )


def _production_matrix(issuer_sic: str | None):
    facts = (_revenue_fact(), _gross_profit_fact())
    engine = _engine(facts, load_core_metric_registry(ROOT), issuer_sic=issuer_sic)
    return engine.query_matrix(
        tickers=["AAA"],
        metrics=["revenue", "gross_profit", "gross_margin"],
        periods=[PERIOD],
        policy=_policy(),
    )


def test_default_inert_production_query_bytes_and_hash_unchanged() -> None:
    """Bank SIC under the G0 production catalog: the class gate fires.

    The catalog now declares issuer-class applicability (the G0 governed
    change the module docstring anticipated), so the historical
    "default-inert even for a bank issuer" premise is retired by design:
    the bank-restricted metrics in this matrix (gross_profit,
    gross_margin) read NOT_APPLICABLE(not_applicable_for_issuer_class)
    with the class stamped on their receipts, while every metric outside
    the class policy keeps its BASE-build value byte for byte (revenue:
    VALUE 100 — leaf-diff vs BASE 99b9a7f61fc0 over the same matrix
    shows only digest-family leaves on that node).
    """
    matrix = _production_matrix(issuer_sic="6020")
    assert matrix.query_hash == _BANK_QUERY_HASH
    payload = canonical_json(matrix.to_dict())
    assert hashlib.sha256(payload.encode("utf-8")).hexdigest() == _BANK_TO_DICT_SHA256
    by_metric = {cell.metric_id: cell for cell in matrix.cells}
    for restricted in ("gross_profit", "gross_margin"):
        cell = by_metric[restricted]
        assert cell.state is CellState.NOT_APPLICABLE
        assert cell.value is None
        assert cell.reason == "not_applicable_for_issuer_class"
        assert cell.provenance.issuer_class == "bank"
        assert cell.provenance.issuer_class_basis == "sic"
    revenue = by_metric["revenue"]
    assert revenue.state is CellState.VALUE
    assert revenue.value == Decimal("100")
    assert revenue.reason is None
    assert revenue.provenance.issuer_class is None


def test_bank_issuer_bank_inapplicable_metric_is_explicit_refusal() -> None:
    """A30: bank + bank-inapplicable metric -> explicit refusal, never a value."""
    fixture = _qualification_registry()
    margin = fixture.metric("gross_margin")
    # Registry-level ground truth (S1-a semantics) for the same inputs.
    bank = qualify_metric(margin, margin.formula, "bank", {"revenue": Decimal("100")})
    assert bank.state == "not_applicable"
    engine = _engine((), fixture, issuer_sic="6020")
    cell = engine.query_cell("AAA", "gross_margin", PERIOD, _policy())
    assert cell.state is CellState.NOT_APPLICABLE
    assert cell.value is None  # absent — never 0, never a number
    assert cell.reason == "not_applicable_for_issuer_class"
    # Issuer class and sector-native basis are printed on the receipt.
    assert cell.provenance.issuer_class == "bank"
    assert cell.provenance.issuer_class_basis == "sic"
    # The refusal receipt replays canonically (round-trip through wire form).
    replay = type(cell).from_dict(cell.to_dict())
    assert replay.state is CellState.NOT_APPLICABLE
    assert replay.value is None
    assert replay.provenance.issuer_class == "bank"


def test_absent_sic_on_class_restricted_metric_is_not_evaluable() -> None:
    """Absent SIC (issuer_class None) -> not_evaluable issuer_class_unknown.

    Note the S1-a semantics pinned here: an absent SIC yields issuer_class
    None and is not treated as applicable; an UNPARSEABLE SIC maps (via E0's
    issuer_class_for_sic) to the class name "unknown", which an exclude-style
    policy admits — only a None class produces issuer_class_unknown.
    """
    fixture = _qualification_registry()
    engine = _engine((), fixture, issuer_sic=None)
    cell = engine.query_cell("AAA", "gross_margin", PERIOD, _policy())
    assert cell.state is CellState.NOT_EVALUABLE
    assert cell.value is None
    assert cell.reason == "issuer_class_unknown"


def test_missing_denominator_is_not_evaluable_with_input_id() -> None:
    """Missing denominator input -> not_evaluable denominator_missing:<id>."""
    fixture = _qualification_registry()
    # gross_profit fact only: the revenue denominator cannot be assembled.
    engine = _engine((_gross_profit_fact(),), fixture, issuer_sic="3571")
    cell = engine.query_cell("AAA", "gross_margin", PERIOD, _policy())
    assert cell.state is CellState.NOT_EVALUABLE
    assert cell.value is None
    assert cell.reason == "denominator_missing:revenue"


def test_non_positive_denominator_is_not_applicable_with_input_id() -> None:
    """Non-positive denominator -> not_applicable denominator_not_positive:<id>."""
    fixture = _qualification_registry()
    # Revenue of 0 is a legitimate VALUE dependency; the constraint refuses it.
    engine = _engine(
        (_zero_revenue_fact(), _gross_profit_fact()), fixture, issuer_sic="3571"
    )
    cell = engine.query_cell("AAA", "gross_margin", PERIOD, _policy())
    assert cell.state is CellState.NOT_APPLICABLE
    assert cell.value is None
    assert cell.reason == "denominator_not_positive:revenue"


def test_industrial_issuer_applicable_metric_value_byte_identical() -> None:
    """Industrial issuer on an applicable metric: byte-identical value."""
    matrix = _production_matrix(issuer_sic="3571")
    assert matrix.query_hash == _PREWIRE_QUERY_HASH
    payload = canonical_json(matrix.to_dict())
    assert hashlib.sha256(payload.encode("utf-8")).hexdigest() == _PREWIRE_TO_DICT_SHA256
    by_metric = {cell.metric_id: cell for cell in matrix.cells}
    margin = by_metric["gross_margin"]
    assert margin.state is CellState.VALUE
    assert margin.value == Decimal("0.4")
    assert margin.reason is None
    assert margin.provenance.issuer_class is None  # applicable: nothing printed


INSTANT_PERIOD = PeriodRequest.instant("2025-12-31", label="FY2025I")
_PERIOD_REJECTION_REASON = (
    "outside_period_constraint: metric requires duration, requested instant"
)


def _instant_period_cell(issuer_sic: str | None):
    """gross_margin (duration formula metric) asked on an INSTANT period.

    Under the G0 catalog gross_margin is issuer-class restricted (bank
    excluded), so this request is BOTH class-refusable and
    period-rejected — the exact precedence probe of fix (a): the
    receipt validators weigh the period contract above the issuer gate,
    so the evaluated cell must carry the period rejection, never the
    class refusal.  The literals asserted below are the pre-G0 build's
    (BASE 99b9a7f61fc0, production registry) own cells, captured by
    running the identical construction under the BASE sources: every
    non-digest field is byte-equal, and the only differing leaves are
    the digest family (cell_id, governance_bundle content_id,
    catalog_digest — moved by the commissioned catalog content).
    """
    engine = _engine((), load_core_metric_registry(ROOT), issuer_sic=issuer_sic)
    return engine.query_cell("AAA", "gross_margin", INSTANT_PERIOD, _policy())


def test_period_rejection_outranks_bank_class_refusal() -> None:
    """T-a1: bank SIC 6021 + instant period -> the period-rejection cell.

    A bank issuer asking a restricted formula metric for a period that
    violates its period contract gets the same verdict the pre-G0
    build gave: NOT_EVALUABLE on the period contract, with no issuer
    class stamped on the receipt.
    """
    cell = _instant_period_cell("6021")
    assert cell.state is CellState.NOT_EVALUABLE
    assert cell.value is None
    assert cell.reason == _PERIOD_REJECTION_REASON
    assert cell.provenance.issuer_class is None
    assert cell.provenance.issuer_class_basis is None


def test_period_rejection_outranks_unknown_issuer_class() -> None:
    """T-a2: no resolved SIC + instant period -> period rejection, no raise.

    The SIC-less (resolver-None) entity on the same period-rejected
    formula metric must get the period-rejection cell — NOT
    issuer_class_unknown — and construction must not raise
    QueryValidationError (the class refusal would contradict the
    validators' period-first reconciliation and raise instead of
    returning a cell).
    """
    cell = _instant_period_cell(None)
    assert cell.state is CellState.NOT_EVALUABLE
    assert cell.value is None
    assert cell.reason == _PERIOD_REJECTION_REASON
    assert cell.provenance.issuer_class is None


def test_period_rejected_cell_matches_pre_g0_receipt_field_by_field() -> None:
    """T-a3: the period-rejected receipt is the pre-G0 receipt.

    Field-by-field against the BASE build's captured cell; the digest
    family (cell_id / governance bundle content id / catalog, rule and
    formula digests) is the only thing the commissioned catalog change
    may move.
    """
    cell = _instant_period_cell("6021")
    assert cell.ticker == "AAA"
    assert cell.entity_id == ENTITY
    assert cell.metric_id == "gross_margin"
    assert cell.period == INSTANT_PERIOD
    assert cell.state is CellState.NOT_EVALUABLE
    assert cell.value is None
    assert cell.unit == "ratio"
    assert cell.reason == _PERIOD_REJECTION_REASON
    assert cell.dependency_nodes == ()
    provenance = cell.provenance
    assert provenance.kind is ProvenanceKind.FORMULA
    assert provenance.reason == _PERIOD_REJECTION_REASON
    assert provenance.issuer_class is None
    assert provenance.issuer_class_basis is None
    assert provenance.metric_rule_id == "metric.gross_margin/v1"
    assert provenance.metric_rule_version == "1.0.0"
    assert provenance.formula_rule_id == "formula.gross_margin/v1"
    assert provenance.formula_rule_version == "1.0.0"
    assert provenance.catalog_id == "fundamental_forensics_core_gaap_metrics"
    assert provenance.dependency_cell_ids == ()
    assert provenance.selected_raw_fact is None
    # The period-rejection receipt replays canonically through the wire form.
    replay = type(cell).from_dict(cell.to_dict())
    assert replay.state is CellState.NOT_EVALUABLE
    assert replay.reason == _PERIOD_REJECTION_REASON
    assert replay.provenance.issuer_class is None


def test_refusal_reason_string_equals_e0_detector_constant() -> None:
    """The query-side refusal reason is E0's constant, byte for byte."""
    fixture = _qualification_registry()
    engine = _engine((), fixture, issuer_sic="6020")
    cell = engine.query_cell("AAA", "gross_margin", PERIOD, _policy())
    assert cell.reason == NOT_EVALUABLE_REASON_NOT_APPLICABLE_FOR_ISSUER_CLASS
    assert NOT_EVALUABLE_REASON_NOT_APPLICABLE_FOR_ISSUER_CLASS == (
        "not_applicable_for_issuer_class"
    )


def test_fixture_catalog_shape_pinned_for_the_writer() -> None:
    """Guard the fixture inputs themselves, so failures name the right layer."""
    fixture = _qualification_registry()
    margin = fixture.metric("gross_margin")
    assert margin.applicability.excluded_classes == ("bank",)
    assert margin.applicability.issuer_class_basis == "sic"
    assert margin.formula is not None
    assert margin.formula.denominator_constraints == ("revenue",)
