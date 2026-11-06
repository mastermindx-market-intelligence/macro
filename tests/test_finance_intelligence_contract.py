from __future__ import annotations

import json
from pathlib import Path
import re

import pytest

from engine.sector_intelligence.contracts import (
    ContractRegistry,
    ContractValidationError,
    validate_contract,
)


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "data" / "sector_intelligence" / "fixtures" / "finance_intelligence_read_model.v1.valid.json"
CONTRACT_ID = "finance_intelligence_read_model.v1"

ATLAS_SLICE_IDS = frozenset(
    {
        "passive_etf_asset_managers",
        "active_asset_managers",
        "wealth_platforms_rias",
        "retirement_recordkeeping",
        "alternative_asset_managers",
        "private_credit_managers",
        "bdc_direct_lending_vehicles",
        "fund_admin_middle_backoffice",
        "deposit_franchise_quality",
        "universal_money_center_banks",
        "regional_superregional_banks",
        "community_local_banks",
        "nim_curve_normalization",
        "cre_credit_cycle",
        "cards_consumer_credit",
        "specialty_auto_equipment_finance",
        "digital_banks_neobanks",
        "mortgage_originators",
        "mortgage_servicers_msr",
        "equity_debt_capital_markets",
        "mna_advisory",
        "electronic_market_makers",
        "options_derivatives_ecosystem",
        "exchanges_trading_venues",
        "clearing_ccp_csd",
        "custody_asset_servicing",
        "prime_brokerage_securities_lending",
        "market_reference_data",
        "ratings_credit_information",
        "indices_benchmarks_etf_plumbing",
        "personal_pc_insurance",
        "commercial_specialty_pc",
        "reinsurance",
        "insurance_brokers",
        "mga_delegated_underwriting",
        "life_annuity_spread",
        "claims_insurance_data_workflow",
        "card_networks",
        "merchant_acquiring_processing",
        "issuer_processing",
        "gateways_orchestration",
        "ach_instant_b2b",
        "cross_border_remittance",
        "embedded_finance_baas",
        "fraud_identity_tokenization",
        "regtech_kyc_aml",
        "financial_cybersecurity",
        "core_banking_financial_software",
        "stablecoin_infrastructure",
        "digital_custody_tokenized_securities",
        "open_banking_api_finance",
        "agentic_ai_finance_workflow",
    }
)

AUTHORITY_CAPS = {
    "rank": False,
    "gate": False,
    "size": False,
    "trade": False,
    "create_theme": False,
    "change_membership": False,
    "write_graph": False,
    "admit_source": False,
}


def load_fixture() -> dict:
    return json.loads(FIXTURE.read_text())


def assert_invalid(document: dict) -> None:
    with pytest.raises(ContractValidationError):
        validate_contract(CONTRACT_ID, document)


def test_finance_contract_is_registered_and_fixture_validates() -> None:
    assert CONTRACT_ID in ContractRegistry(ROOT).contract_ids
    validate_contract(CONTRACT_ID, load_fixture())


def test_authority_caps_are_false_and_no_scoring_fields_exist() -> None:
    document = load_fixture()
    assert document["authority_caps"] == AUTHORITY_CAPS
    forbidden = re.compile(r"(^|_)(score|rank|attractiveness|composite|bottleneck_score)($|_)", re.I)

    def walk(value: object) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                if key != "rank":
                    assert forbidden.fullmatch(key) is None
                walk(child)
            return
        if isinstance(value, list):
            for child in value:
                walk(child)

    walk(document)


def test_missing_knowledge_cutoff_fails() -> None:
    document = load_fixture()
    del document["knowledge_cutoff"]
    assert_invalid(document)


def test_added_top_level_finance_score_fails() -> None:
    document = load_fixture()
    document["finance_score"] = 1
    assert_invalid(document)


def test_authority_rank_true_fails() -> None:
    document = load_fixture()
    document["authority_caps"]["rank"] = True
    assert_invalid(document)


def test_regime_break_must_not_be_marked_comparable() -> None:
    document = load_fixture()
    plane = document["slices"][0]["rerating"]["operating"]
    plane["state"] = "REGIME_BREAK"
    plane["comparability_state"] = "COMPARABLE"
    assert_invalid(document)


@pytest.mark.parametrize("missing", ["as_of", "source"])
def test_history_observation_requires_clock_and_source(missing: str) -> None:
    document = load_fixture()
    history = document["slices"][0]["rerating"]["expectations"]["history"]
    history["state"] = "DATED_CONSENSUS_AVAILABLE"
    history["observations"] = [
        {
            "as_of": "2026-09-01",
            "source": "src-001",
            "metric": "consensus_eps",
            "value": 1.25,
            "unit": "currency",
        }
    ]
    del history["observations"][0][missing]
    assert_invalid(document)


def test_no_historical_consensus_rejects_observations() -> None:
    document = load_fixture()
    history = document["slices"][0]["rerating"]["expectations"]["history"]
    history["state"] = "NO_HISTORICAL_CONSENSUS"
    history["observations"] = [
        {
            "as_of": "2026-09-01",
            "source": "src-001",
            "metric": "guidance:eps",
            "value": 1.25,
            "unit": "currency",
        }
    ]
    assert_invalid(document)


def test_unresolved_identity_cannot_carry_a_route() -> None:
    document = load_fixture()
    row = next(row for row in document["company_exposures"] if row["identity"]["state"] == "IDENTITY_UNRESOLVED")
    row["company_route"]["href"] = "https://example.invalid/companies/synthetic-global"
    assert_invalid(document)


def test_constraint_requires_an_economic_effect() -> None:
    document = load_fixture()
    document["constraints"][0]["economic_effect"] = ""
    assert_invalid(document)


def test_internal_only_source_cannot_include_an_excerpt() -> None:
    document = load_fixture()
    source = next(source for source in document["source_records"] if source["rights_state"] == "INTERNAL_ONLY")
    source["excerpt"] = "Synthetic internal text."
    assert_invalid(document)


def test_every_evidence_ref_resolves_to_a_source_record() -> None:
    document = load_fixture()
    record_ids = {source["record_id"] for source in document["source_records"]}
    references: list[str] = []

    def walk(value: object) -> None:
        if isinstance(value, dict):
            if "evidence_refs" in value:
                references.extend(value["evidence_refs"])
            for child in value.values():
                walk(child)
            return
        if isinstance(value, list):
            for child in value:
                walk(child)

    walk(document)
    assert references
    assert set(references) <= record_ids


def test_system_view_relationship_vocabularies_are_disjoint() -> None:
    document = load_fixture()
    views = {view["view_id"]: {edge["relationship"] for edge in view["edges"]} for view in document["system_views"]}
    assert set(views) == {"contractual_flow", "infrastructure_access", "public_equity_economics"}
    assert views["contractual_flow"].isdisjoint(views["infrastructure_access"])
    assert views["contractual_flow"].isdisjoint(views["public_equity_economics"])
    assert views["infrastructure_access"].isdisjoint(views["public_equity_economics"])

    document["system_views"][0]["edges"][0]["relationship"] = "LICENSES"
    assert_invalid(document)


def test_schema_slice_enum_equals_the_frozen_atlas() -> None:
    schema_path = ROOT / "contracts" / "sector_intelligence" / "finance_intelligence_read_model.v1.schema.json"
    schema = json.loads(schema_path.read_text())
    schema_slice_ids = frozenset(schema["$defs"]["slice_id"]["enum"])
    assert schema_slice_ids == ATLAS_SLICE_IDS
