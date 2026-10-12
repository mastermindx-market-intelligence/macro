"""Pin the specialist pack result envelope, catalogues, and validator."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from engine.fundamental_forensics.specialist_pack_contract import (
    PACK_IDS,
    load_envelope_schema,
    load_pack_schema,
    pack_schema_digest,
    validate_pack_result,
)


ROOT = Path(__file__).resolve().parents[1]
ENVELOPE_PATH = ROOT / "contracts" / "specialist_pack_result.v1.schema.json"
PACK_DIR = ROOT / "contracts" / "specialist_packs"

_ZERO_SHA = "0" * 64
_ENTITY = {
    "entity_id": "ISS:US-TEST-SP01",
    "cik": "0000000001",
    "ticker": "SP01",
    "name": "SPECIALIST PACK FIXTURE CORP",
    "identity_basis": "specialist_pack_contract_fixture",
    "source_entity_id": "0000000001",
}
_QUERY = {
    "policy": "as_reported",
    "source_event_cutoff": "2025-12-31T23:59:59Z",
    "system_recorded_cutoff": "2026-08-05T12:00:02Z",
    "requested_metrics": ["total_assets"],
    "requested_periods": ["FY2025"],
    "evaluation_mode": "historical_replay",
}


def _minimal_result(pack_id: str) -> dict:
    slug = pack_id.lower()
    return {
        "schema": "specialist_pack_result.v1",
        "pack_id": pack_id,
        "pack_schema_id": f"pack.{slug}/v1",
        "pack_schema_digest": pack_schema_digest(pack_id),
        "pack_content_sha256": _ZERO_SHA,
        "packet_id": "fip_" + "a" * 24,
        "entity": deepcopy(_ENTITY),
        "query": deepcopy(_QUERY),
        "applicability": {
            "state": "not_evaluable",
            "reason": "catalogue unspecified; pack not evaluated",
            "rule_id": "specialist_pack.catalogue_unspecified",
            "sic": None,
            "sic_source": None,
        },
        "fields": [],
        "checks": [],
        "coverage": {
            "valued_fields": 0,
            "missing_fields": 0,
            "unsupported_fields": 0,
            "not_applicable_fields": 0,
            "not_evaluable_fields": 0,
            "disclosure_coverage_state": "not_supplied",
        },
        "limitations": [
            "Pack catalogue is unspecified; this envelope is a contract pin, not an evaluation."
        ],
        "receipts": [],
        "authority": {"class": "context_only", "display_only": True},
    }


def _field_row() -> dict:
    return {
        "field_id": "probe.field",
        "name": "probe",
        "type": "decimal",
        "unit": "USD",
        "period": {"kind": "instant", "end": "2025-09-27"},
        "value": None,
        "non_value_state": "missing",
        "evidence_kind": "none",
        "required_evidence_kind": "ixbrl_fact",
        "source_occurrence_ids": [],
        "source_span": None,
        "table_cell": None,
        "concept": None,
        "taxonomy": None,
        "dimensions": [],
        "mapping_rule_id": None,
        "mapping_rule_digest": None,
        "formula_rule_id": None,
        "dependency_field_ids": [],
        "quality_state": "missing",
        "coverage_state": "unmapped",
        "reason": "probe row for schema pinning",
    }


def _object_nodes(node: object, path: str = "$"):
    if isinstance(node, dict):
        types = node.get("type")
        type_list = types if isinstance(types, list) else ([types] if types is not None else [])
        if "object" in type_list:
            yield path, node
        for key, value in node.items():
            yield from _object_nodes(value, f"{path}.{key}")
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from _object_nodes(value, f"{path}[{index}]")


@pytest.mark.parametrize("pack_id", PACK_IDS)
def test_minimal_valid_result_per_pack(pack_id: str) -> None:
    assert validate_pack_result(_minimal_result(pack_id)) == []


def test_unknown_pack_id_rejected() -> None:
    obj = _minimal_result("PK01")
    obj["pack_id"] = "PK99"
    errors = validate_pack_result(obj)
    assert errors
    assert any("pack_id" in item for item in errors)


def test_extra_top_level_property_rejected() -> None:
    obj = _minimal_result("PK01")
    obj["unexpected"] = True
    errors = validate_pack_result(obj)
    assert errors
    assert any("unexpected" in item or "Additional properties" in item for item in errors)


def test_field_row_missing_quality_state_rejected() -> None:
    obj = _minimal_result("PK01")
    row = _field_row()
    del row["quality_state"]
    obj["fields"] = [row]
    errors = validate_pack_result(obj)
    assert errors
    assert any("quality_state" in item for item in errors)


def test_authority_display_only_false_rejected() -> None:
    obj = _minimal_result("PK01")
    obj["authority"] = {"class": "context_only", "display_only": False}
    errors = validate_pack_result(obj)
    assert errors
    assert any("display_only" in item or "False" in item or "false" in item for item in errors)


def test_empty_limitations_rejected() -> None:
    obj = _minimal_result("PK01")
    obj["limitations"] = []
    errors = validate_pack_result(obj)
    assert errors
    assert any("limitations" in item for item in errors)


def test_wrong_pack_schema_digest_rejected() -> None:
    obj = _minimal_result("PK01")
    obj["pack_schema_digest"] = _ZERO_SHA
    errors = validate_pack_result(obj)
    assert errors
    assert any("pack_schema_digest" in item for item in errors)


def test_pack_schema_digest_is_deterministic() -> None:
    first = pack_schema_digest("PK01")
    second = pack_schema_digest("PK01")
    assert first == second
    assert len(first) == 64
    assert first != pack_schema_digest("PK02")


def test_pack_schema_id_pattern_rejected() -> None:
    obj = _minimal_result("PK01")
    obj["pack_schema_id"] = "PACK.pk01/v1"
    errors = validate_pack_result(obj)
    assert errors
    assert any("pack_schema_id" in item for item in errors)


def test_checks_kind_enum_rejected() -> None:
    obj = _minimal_result("PK01")
    obj["checks"] = [
        {
            "check_id": "probe.check",
            "kind": "not_a_declared_kind",
            "status": "pass",
            "operands": [],
            "tolerance": None,
            "evidence_field_ids": [],
            "reason": None,
        }
    ]
    errors = validate_pack_result(obj)
    assert errors
    assert any("kind" in item for item in errors)


@pytest.mark.parametrize("pack_id", PACK_IDS)
def test_pack_file_parses_and_pack_schema_id_matches(pack_id: str) -> None:
    schema = load_pack_schema(pack_id)
    slug = pack_id.lower()
    assert schema["pack_schema_id"] == f"pack.{slug}/v1"
    assert schema["catalogue_state"] == "unspecified"
    assert schema["fields"] == []
    path = PACK_DIR / f"pack.{slug}.v1.schema.json"
    assert path.is_file()


def test_envelope_additional_properties_false_everywhere() -> None:
    schema = load_envelope_schema()
    missing = [
        path
        for path, node in _object_nodes(schema)
        if node.get("additionalProperties") is not False
    ]
    assert missing == []


def test_pack_ids_match_envelope_enum() -> None:
    schema = load_envelope_schema()
    assert list(PACK_IDS) == schema["properties"]["pack_id"]["enum"]
    assert schema["$id"] == "https://mastermind-x.com/contracts/specialist_pack_result.v1.schema.json"
    assert schema["properties"]["schema"]["const"] == "specialist_pack_result.v1"
    assert ENVELOPE_PATH.is_file()


def test_valid_field_row_and_check_row_accepted() -> None:
    obj = _minimal_result("PK01")
    obj["fields"] = [_field_row()]
    obj["checks"] = [
        {
            "check_id": "probe.sum",
            "kind": "sum_identity",
            "status": "not_evaluable",
            "operands": ["probe.field"],
            "tolerance": None,
            "evidence_field_ids": ["probe.field"],
            "reason": "catalogue unspecified",
        }
    ]
    obj["coverage"]["missing_fields"] = 1
    obj["coverage"]["not_evaluable_fields"] = 1
    assert validate_pack_result(obj) == []


def test_unknown_pack_schema_load_raises() -> None:
    with pytest.raises(KeyError):
        load_pack_schema("PK99")
