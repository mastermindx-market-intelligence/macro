"""Mapping pack 1.1.0 / metric catalog 1.1.0: seat-ruled alias and scope appends.

Covers the 2026-10-19 seat rulings (R-ALIAS, R-INTANG, D1): the
``total_assets`` balance-sheet identity alias, the strict period-end us-gaap
``common_shares_outstanding`` alias, and the governed ``definition`` field
that states the measured scope of ``intangible_assets_net``.  Every query
fixture below is synthetic; entity identifiers, accessions, and tickers are
placeholders, not real issuers.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import hashlib
from pathlib import Path

import pytest
import yaml

from engine.fundamental_forensics.metric_registry import (
    GovernanceBundle,
    _contract_payload,
    _content_digest,
    _metric_contract_from_payload,
    load_core_metric_registry,
    metric_registry_from_dicts,
)
from engine.fundamental_forensics.models import utc_text
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
METRICS_ROOT = ROOT / "config" / "fundamental_forensics" / "metrics" / "v1"

# Synthetic issuer identifiers only (industrial SIC placeholder).
ENTITY_A = "0000000001"
SYNTHETIC_SIC = "3571"
SYNTHETIC_TICKER = "AAA"

TOTAL_ASSETS_ALIAS_RULE = (
    "mapping.total_assets.alias_liabilities_and_stockholders_equity/v1"
)
SHARES_ALIAS_RULE = (
    "mapping.common_shares_outstanding.alias_common_stock_shares_outstanding/v1"
)
NEW_MAPPING_RULE_IDS = {TOTAL_ASSETS_ALIAS_RULE, SHARES_ALIAS_RULE}


def _raw() -> tuple[dict, dict, dict]:
    return tuple(
        yaml.safe_load(path.read_text(encoding="utf-8"))
        for path in (
            METRICS_ROOT / "metric_catalog.yaml",
            METRICS_ROOT / "mappings" / "core.yaml",
            METRICS_ROOT / "formulas" / "core.yaml",
        )
    )


def _metric(catalog: dict, metric_id: str) -> dict:
    return next(item for item in catalog["metrics"] if item["metric_id"] == metric_id)


def _base_registry():
    """Rebuild the pre-1.1.0 (BASE) registry from the shipped YAML content.

    The two appended mapping entries and the ``intangible_assets_net``
    definition are removed from the loaded YAML, and both file digests are
    recomputed with the loader's own ``_content_digest``.
    """
    catalog, mappings, formulas = _raw()
    mappings["mappings"] = [
        entry
        for entry in mappings["mappings"]
        if entry["rule"]["rule_id"] not in NEW_MAPPING_RULE_IDS
    ]
    assert len(mappings["mappings"]) == 40
    _metric(catalog, "intangible_assets_net").pop("definition", None)
    catalog["content_sha256"] = _content_digest(catalog)
    mappings["content_sha256"] = _content_digest(mappings)
    return metric_registry_from_dicts(catalog, mappings, formulas)


def _alias_rule_clock(registry):
    """Read the new rule clock R from the loaded registry, never retyped."""
    for mapping in registry.metric("total_assets").mappings:
        if mapping.rule.rule_id == TOTAL_ASSETS_ALIAS_RULE:
            return mapping.rule.available_at
    return None


def _body(seed: str) -> str:
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()


def _instant_fact(
    *,
    concept: str,
    value: str,
    taxonomy: str = "us-gaap",
    unit: FactUnit | None = None,
    document_id: str,
    accession: str = "0000000001-26-000001",
):
    return make_raw_fact(
        source=SourceIdentity(
            source="sec-edgar",
            entity_id=ENTITY_A,
            accession=accession,
            document_id=document_id,
            body_sha256=_body(f"{ENTITY_A}:{accession}:{document_id}"),
            source_url=f"https://www.sec.gov/Archives/{accession}",
        ),
        concept_qname=f"{taxonomy}:{concept}",
        context=FactContext(
            context_id=f"ctx-{document_id}",
            entity_scheme="http://www.sec.gov/CIK",
            entity_identifier=ENTITY_A,
            instant="2025-12-31",
        ),
        unit=unit or FactUnit("USD", ["iso4217:USD"]),
        raw_token=value,
        parsed_value=value,
        is_nil=False,
        dimensions_known=True,
        source_span=(0, 8),
        accepted_at="2026-08-02T01:00:00Z",
        recorded_at="2026-08-02T02:00:00Z",
        event_type=FactEventType.FILED,
    )


def _engine(*facts, registry):
    return BitemporalMetricQueryEngine(
        RawFactLedger(tuple(facts)),
        registry,
        entities=(QueryEntity(SYNTHETIC_TICKER, ENTITY_A, issuer_sic=SYNTHETIC_SIC),),
        filing_metadata={
            fact.occurrence_id: {
                "accession": fact.source.accession,
                "document_id": fact.source.document_id,
                "source_body_sha256": fact.source.body_sha256,
                "available_at": fact.recorded_at,
                "form": "10-K",
            }
            for fact in facts
        },
    )


def _policy(recorded_at):
    return QueryPolicy(
        source_snapshot_at=utc_text(recorded_at),
        recorded_at=utc_text(recorded_at),
        selection=BitemporalPolicy.LATEST_KNOWN_AS_OF,
    )


def _instant_period():
    return PeriodRequest.instant("2025-12-31")


def test_v1_1_pack_and_catalog_versions_and_cutoff_gated_rules() -> None:
    registry = load_core_metric_registry(ROOT)
    assert registry.mapping_pack_version == "1.1.0"
    assert registry.catalog_version == "1.1.0"

    rule_clock = _alias_rule_clock(registry)
    assert rule_clock is not None, "alias rule is absent from the shipped pack"
    before = registry.governance_bundle_at(rule_clock - timedelta(seconds=1))
    after = registry.governance_bundle_at(rule_clock + timedelta(seconds=1))

    assert TOTAL_ASSETS_ALIAS_RULE in {
        mapping.rule.rule_id for mapping in after.mappings_for("total_assets")
    }
    assert SHARES_ALIAS_RULE in {
        mapping.rule.rule_id
        for mapping in after.mappings_for("common_shares_outstanding")
    }
    assert TOTAL_ASSETS_ALIAS_RULE not in {
        mapping.rule.rule_id for mapping in before.mappings_for("total_assets")
    }
    assert SHARES_ALIAS_RULE not in {
        mapping.rule.rule_id
        for mapping in before.mappings_for("common_shares_outstanding")
    }


def test_a53_no_hindsight_bundle_before_rule_clock_equals_base_bundle() -> None:
    registry = load_core_metric_registry(ROOT)
    rule_clock = _alias_rule_clock(registry)
    assert rule_clock is not None
    base = _base_registry()
    before = rule_clock - timedelta(seconds=1)

    projected = registry.governance_bundle_at(before)
    baseline = base.governance_bundle_at(before)
    assert projected.to_dict() == baseline.to_dict()
    assert projected.content_id == baseline.content_id

    # The definition is absent from every bundle before the rule clock and
    # present afterwards, including at the clock itself.
    for cutoff in (
        base.available_at,
        base.available_at + timedelta(days=30),
        before,
    ):
        assert registry.governance_bundle_at(cutoff).metric("intangible_assets_net").definition is None
    at_clock = registry.governance_bundle_at(rule_clock)
    after = registry.governance_bundle_at(rule_clock + timedelta(seconds=1))
    for bundle in (at_clock, after):
        definition = bundle.metric("intangible_assets_net").definition
        assert definition is not None
        assert definition.rule.rule_id == "definition.intangible_assets_net/v1"
        assert definition.scope.startswith("Finite-lived intangible assets")


# Seat ruling R-9761-CLK (a)/(d): the three new rules share one clock, set after
# the 2026-10-20 production publish so no generation admitted before it can see them.
R_9761_CLK_RULE_CLOCK = datetime(2026, 10, 21, 0, 0, 0, tzinfo=timezone.utc)


def test_a53_every_new_rule_carries_the_r_9761_clk_clock_and_is_cutoff_gated() -> None:
    registry = load_core_metric_registry(ROOT)
    clocks = {
        mapping.rule.rule_id: mapping.rule.available_at
        for metric_id in ("total_assets", "common_shares_outstanding")
        for mapping in registry.metric(metric_id).mappings
        if mapping.rule.rule_id in NEW_MAPPING_RULE_IDS
    }
    rule_clock = _alias_rule_clock(registry)
    at_clock = registry.governance_bundle_at(rule_clock)
    definition = at_clock.metric("intangible_assets_net").definition
    clocks[definition.rule.rule_id] = definition.rule.available_at
    assert clocks == {
        TOTAL_ASSETS_ALIAS_RULE: R_9761_CLK_RULE_CLOCK,
        SHARES_ALIAS_RULE: R_9761_CLK_RULE_CLOCK,
        "definition.intangible_assets_net/v1": R_9761_CLK_RULE_CLOCK,
    }
    assert rule_clock == R_9761_CLK_RULE_CLOCK

    before = registry.governance_bundle_at(rule_clock - timedelta(seconds=1))
    for bundle, visible in ((before, False), (at_clock, True)):
        rule_ids = {
            mapping.rule.rule_id
            for metric_id in ("total_assets", "common_shares_outstanding")
            for mapping in bundle.mappings_for(metric_id)
        }
        assert (rule_ids & NEW_MAPPING_RULE_IDS) == (NEW_MAPPING_RULE_IDS if visible else set())
        assert (bundle.metric("intangible_assets_net").definition is not None) is visible


def test_identity_alias_yields_value_after_rule_clock_and_base_state_before() -> None:
    registry = load_core_metric_registry(ROOT)
    rule_clock = _alias_rule_clock(registry)
    assert rule_clock is not None, "alias rule is absent from the shipped pack"
    base = _base_registry()
    before = rule_clock - timedelta(seconds=1)
    after = rule_clock + timedelta(seconds=1)
    fact = _instant_fact(
        concept="LiabilitiesAndStockholdersEquity",
        value="125000",
        document_id="fixture-balance-10k.htm",
    )
    period = _instant_period()

    valued = _engine(fact, registry=registry).query_cell(
        SYNTHETIC_TICKER, "total_assets", period, _policy(after)
    )
    assert valued.state is CellState.VALUE
    assert valued.value is not None
    assert str(valued.value) == "125000"
    assert valued.provenance.mapping_rule_id == TOTAL_ASSETS_ALIAS_RULE
    assert valued.provenance.concept_qname == "us-gaap:LiabilitiesAndStockholdersEquity"

    historical = _engine(fact, registry=registry).query_cell(
        SYNTHETIC_TICKER, "total_assets", period, _policy(before)
    )
    base_historical = _engine(fact, registry=base).query_cell(
        SYNTHETIC_TICKER, "total_assets", period, _policy(before)
    )
    assert historical.state is CellState.MISSING
    assert historical.value is None
    assert historical.reason == (
        "missing_standard_fact: no governed concept alias supplied an exact eligible source interval"
    )
    assert historical.to_dict() == base_historical.to_dict()
    assert historical.cell_id == base_historical.cell_id


def test_reported_assets_total_is_not_displaced_by_the_identity_alias() -> None:
    registry = load_core_metric_registry(ROOT)
    rule_clock = _alias_rule_clock(registry)
    assert rule_clock is not None
    after = rule_clock + timedelta(seconds=1)
    assets = _instant_fact(concept="Assets", value="130000", document_id="fixture-assets-10k.htm")
    identity = _instant_fact(
        concept="LiabilitiesAndStockholdersEquity",
        value="125000",
        document_id="fixture-identity-10k.htm",
    )

    cell = _engine(assets, identity, registry=registry).query_cell(
        SYNTHETIC_TICKER, "total_assets", _instant_period(), _policy(after)
    )
    assert cell.state is CellState.VALUE
    assert str(cell.value) == "130000"
    assert cell.provenance.mapping_rule_id == "mapping.total_assets/v1"
    assert cell.provenance.concept_qname == "us-gaap:Assets"


def test_strict_period_end_us_gaap_shares_outrank_the_dei_cover_fact() -> None:
    registry = load_core_metric_registry(ROOT)
    rule_clock = _alias_rule_clock(registry)
    assert rule_clock is not None, "alias rule is absent from the shipped pack"
    before = rule_clock - timedelta(seconds=1)
    after = rule_clock + timedelta(seconds=1)
    shares_unit = FactUnit("shares", ["xbrli:shares"])
    gaap = _instant_fact(
        concept="CommonStockSharesOutstanding",
        value="98000000",
        unit=shares_unit,
        document_id="fixture-shares-gaap-10k.htm",
    )
    dei = _instant_fact(
        concept="EntityCommonStockSharesOutstanding",
        value="120000000",
        taxonomy="dei",
        unit=shares_unit,
        document_id="fixture-shares-dei-10k.htm",
    )
    period = _instant_period()

    valued = _engine(gaap, dei, registry=registry).query_cell(
        SYNTHETIC_TICKER, "common_shares_outstanding", period, _policy(after)
    )
    assert valued.state is CellState.VALUE
    assert str(valued.value) == "98000000"
    assert valued.provenance.mapping_rule_id == SHARES_ALIAS_RULE
    assert valued.provenance.concept_qname == "us-gaap:CommonStockSharesOutstanding"

    historical = _engine(gaap, dei, registry=registry).query_cell(
        SYNTHETIC_TICKER, "common_shares_outstanding", period, _policy(before)
    )
    assert historical.state is CellState.VALUE
    assert str(historical.value) == "120000000"
    assert historical.provenance.mapping_rule_id == "mapping.common_shares_outstanding/v1"
    assert historical.provenance.concept_qname == "dei:EntityCommonStockSharesOutstanding"


def test_each_loader_refuses_its_pack_when_the_content_digest_is_altered() -> None:
    catalog, mappings, formulas = deepcopy(_raw())
    mappings["content_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="mappings.content_sha256 does not match"):
        metric_registry_from_dicts(catalog, mappings, formulas)

    catalog, mappings, formulas = deepcopy(_raw())
    catalog["content_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="catalog.content_sha256 does not match"):
        metric_registry_from_dicts(catalog, mappings, formulas)


def test_definition_loader_negatives_and_payload_round_trip() -> None:
    registry = load_core_metric_registry(ROOT)
    shipped = registry.metric("intangible_assets_net")
    assert shipped.definition is not None
    assert shipped.definition.scope

    def _registry(raw: tuple[dict, dict, dict]):
        catalog, mappings, formulas = raw
        catalog["content_sha256"] = _content_digest(catalog)
        mappings["content_sha256"] = _content_digest(mappings)
        return metric_registry_from_dicts(catalog, mappings, formulas)

    # A definition clock that predates its metric rule is refused.
    catalog, mappings, formulas = deepcopy(_raw())
    _metric(catalog, "intangible_assets_net")["definition"]["rule"]["available_at"] = (
        "2026-08-01T00:00:00Z"
    )
    with pytest.raises(ValueError, match="cannot predate its catalog or metric rule"):
        _registry((catalog, mappings, formulas))

    # A definition reusing an existing rule id is refused.
    catalog, mappings, formulas = deepcopy(_raw())
    _metric(catalog, "intangible_assets_net")["definition"]["rule"]["rule_id"] = (
        "metric.intangible_assets_net/v1"
    )
    with pytest.raises(ValueError, match="duplicate immutable rule/version"):
        _registry((catalog, mappings, formulas))

    # An unknown definition sub-key is refused.
    catalog, mappings, formulas = deepcopy(_raw())
    _metric(catalog, "intangible_assets_net")["definition"]["note"] = "ungoverned"
    with pytest.raises(ValueError, match="unsupported field"):
        _registry((catalog, mappings, formulas))

    # The wire payload round-trips a contract with and without a definition.
    with_definition = _metric_contract_from_payload(
        _contract_payload(shipped), field="round_trip"
    )
    assert with_definition == replace(shipped, mappings=(), formula=None)
    assert with_definition.definition == shipped.definition
    without = replace(shipped, definition=None)
    payload = _contract_payload(without)
    assert "definition" not in payload
    parsed = _metric_contract_from_payload(payload, field="round_trip")
    assert parsed == replace(without, mappings=(), formula=None)
    assert parsed.definition is None


def test_governance_bundle_refuses_a_definition_later_than_its_recorded_at() -> None:
    registry = load_core_metric_registry(ROOT)
    rule_clock = _alias_rule_clock(registry)
    assert rule_clock is not None
    before = rule_clock - timedelta(seconds=1)
    after = rule_clock + timedelta(seconds=1)
    definition = registry.governance_bundle_at(after).metric("intangible_assets_net").definition
    assert definition is not None

    bundle = registry.governance_bundle_at(before)
    assert bundle.metric("intangible_assets_net").definition is None
    with pytest.raises(ValueError, match="hidden at recorded_at"):
        replace(
            bundle,
            contracts=tuple(
                replace(contract, definition=definition)
                if contract.metric_id == "intangible_assets_net"
                else contract
                for contract in bundle.contracts
            ),
            content_id="",
        )

    assert GovernanceBundle.from_dict(
        registry.governance_bundle_at(after).to_dict()
    ).metric("intangible_assets_net").definition == definition
