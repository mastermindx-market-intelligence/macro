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
The wiring must reproduce them byte-identically — including when the entity
carries a BANK SIC, because the production catalog declares no applicability
and the gate is default-inert. If a governed catalog change (adding
applicability) ever lands, re-capture in that same PR per the S1-a pin
convention (tests/test_fundamental_forensics_metric_qualification.py:33-39).
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
# S1-b prep lane; see module docstring.
_PREWIRE_QUERY_HASH = "149504ef7aa57dbb13c8e98e49bc277175d11af4b7c93042cf654917908e0b77"
_PREWIRE_TO_DICT_SHA256 = "23b950e491474c85b099a097508a72976833b3fe3fdacd511e65ee29af234ce2"


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
    """Default-inert: a BANK SIC under the production catalog changes nothing.

    The production catalog declares no applicability, so the gate must not
    fire even for a bank issuer: identical response bytes and query_hash to
    the pre-wiring capture at 7fd00a6b754e.
    """
    matrix = _production_matrix(issuer_sic="6020")
    assert matrix.query_hash == _PREWIRE_QUERY_HASH
    payload = canonical_json(matrix.to_dict())
    assert hashlib.sha256(payload.encode("utf-8")).hexdigest() == _PREWIRE_TO_DICT_SHA256
    states = {cell.metric_id: cell.state for cell in matrix.cells}
    assert states == {
        "revenue": CellState.VALUE,
        "gross_profit": CellState.VALUE,
        "gross_margin": CellState.VALUE,
    }


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
