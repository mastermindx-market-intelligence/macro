"""Registry discovery must not turn an existing research corpus into PIT admission."""
import json
from pathlib import Path

from lib.dataos.registry import DatasetStatus, load_registry, validate_registry
from lib.dataos.web_workspace import DataWorkspace, RootBinding


REPO = Path(__file__).resolve().parents[1]
REGISTRY = REPO / "config/dataset_registry.yml"
EVIDENCE = REPO / "docs/tiingo-evidence/20261012-research-contracts/accepted-corpus.json"
PRODUCED = {
    "vendor.tiingo.raw.equity_eod", "vendor.tiingo.raw.fundamentals",
    "vendor.tiingo.research.eod", "vendor.tiingo.research.fundamentals",
}


def test_bounded_evidence_supports_only_the_four_existing_research_contracts():
    proof = json.loads(EVIDENCE.read_text())
    registry = load_registry(REGISTRY)
    ids = {name for name in registry.ids() if name.startswith("vendor.tiingo.")}
    assert set(proof["produced_dataset_ids"]) == PRODUCED
    assert len(ids) == 24
    assert {name for name in ids if registry.get(name).status is DatasetStatus.PRODUCED} == PRODUCED
    assert all(registry.get(name).status is DatasetStatus.PROPOSED for name in ids - PRODUCED)
    assert validate_registry(registry) == []
    for name in PRODUCED:
        contract = registry.get(name)
        assert "PRODUCED 2026-10-12" in contract.notes
        assert "20261012-research-contracts/accepted-corpus.json" in contract.notes
        assert contract.version == "0.2.0"
        assert contract.code_consumers
        if contract.layer.value == "L0":
            assert "{request_hash}-{content_hash_24}.raw.gz" in contract.storage
            assert "request_path" in contract.grain
        else:
            assert "{receipt_id_or_raw_sha256}.parquet" in contract.storage
            assert "source_receipt_id" in contract.grain
    assert proof["eod"]["all_selected_raw_and_reader_lineage_verified"] is True
    assert proof["fundamentals"]["original_revised_request_dimensions_preserved"] is True
    assert proof["fundamentals"]["requested_start"] < proof["fundamentals"]["earliest_served_date"]
    assert all(value is False for value in proof["unproven_or_unadmitted"].values())


def test_data_workspace_exposes_existence_without_granting_production_qualification(tmp_path):
    # An empty synthetic namespace is enough to test actual contract discovery.
    # It is never presented as the authenticated production corpus.
    ws = DataWorkspace((RootBinding("fixture", tmp_path, "research_sample"),), REGISTRY,
                       source_revision="source-contract-test")
    found = ws.search("vendor.tiingo.", limit=100)
    contracts = {item["dataset_id"]: item for item in found["results"]
                 if item["kind"] == "registered_contract"}
    assert len(contracts) == 24
    assert {name for name, item in contracts.items() if item["status"] == "PRODUCED"} == PRODUCED
    for name in PRODUCED:
        described = ws.describe("registry:" + name)
        assert described["contract"]["status"] == "PRODUCED"
        assert "unproven" in described["contract"]["notes"] or "unadmitted" in described["contract"]["notes"]
        assert described["availability"] == "NOT_ESTABLISHED_BY_DECLARATION"
        assert contracts[name]["availability"] == "NOT_ESTABLISHED_BY_DECLARATION"
        assert described["production_qualification"] == "NOT_ESTABLISHED_BY_THIS_ADAPTER"
        assert described["source_access"] == "read_only"
        if name.startswith("vendor.tiingo.research."):
            assert len(described["declared_inputs"]) == 1
            assert described["declared_inputs"][0] in PRODUCED
    assert contracts["vendor.tiingo.raw.boats"]["status"] == "PROPOSED"
