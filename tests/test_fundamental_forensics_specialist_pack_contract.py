"""Pin the specialist pack result envelope, catalogues, and validator."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from engine.fundamental_forensics import specialist_pack_contract as pack_contract
from engine.fundamental_forensics.specialist_pack_contract import (
    PACK_IDS,
    catalogue_errors,
    load_catalogue_schema,
    load_envelope_schema,
    load_pack_schema,
    pack_content_digest,
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
_QUALITY_COVERAGE = {
    "valued": "valued_fields",
    "missing": "missing_fields",
    "unsupported": "unsupported_fields",
    "not_evaluable": "not_evaluable_fields",
    "not_applicable": "not_applicable_fields",
}


def _minimal_result(pack_id: str) -> dict:
    slug = pack_id.lower()
    obj = {
        "schema": "specialist_pack_result.v1",
        "pack_id": pack_id,
        "pack_schema_id": f"pack.{slug}/v1",
        "pack_schema_digest": pack_schema_digest(pack_id),
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
    obj["pack_content_sha256"] = pack_content_digest(obj)
    return obj


def _field_row(**overrides) -> dict:
    row = {
        "field_id": "probe_field",
        "name": "probe",
        "type": "decimal",
        "unit": "USD",
        "period": {"kind": "instant", "end": "2025-09-27"},
        "value": None,
        "text_value": None,
        "non_value_state": "missing",
        "evidence_kind": "xbrl_fact",
        "required_evidence_kind": "xbrl_fact",
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
    row.update(overrides)
    return row


def _valued_row(**overrides) -> dict:
    row = _field_row(
        quality_state="valued",
        value="1.0",
        text_value=None,
        non_value_state=None,
        evidence_kind="xbrl_fact",
        required_evidence_kind="xbrl_fact",
        source_occurrence_ids=["occ-1"],
        concept="us-gaap:Assets",
        coverage_state="source_trace_complete",
        reason=None,
    )
    row.update(overrides)
    return row


def _set_applicable(obj: dict) -> dict:
    obj["applicability"] = {
        "state": "applicable",
        "reason": "contract fixture treats the pack as applicable",
        "rule_id": "specialist_pack.fixture_applicable",
        "sic": None,
        "sic_source": None,
    }
    return obj


def _sync_coverage(obj: dict) -> dict:
    counts = {
        "valued_fields": 0,
        "missing_fields": 0,
        "unsupported_fields": 0,
        "not_evaluable_fields": 0,
        "not_applicable_fields": 0,
    }
    for row in obj.get("fields") or []:
        key = _QUALITY_COVERAGE.get(row.get("quality_state"))
        if key is not None:
            counts[key] += 1
    obj["coverage"].update(counts)
    return obj


def _finish(obj: dict) -> dict:
    _sync_coverage(obj)
    obj["pack_content_sha256"] = pack_content_digest(obj)
    return obj


def _catalogue_field(**overrides) -> dict:
    row = {
        "field_id": "probe_field",
        "name": "probe",
        "type": "decimal",
        "unit": "USD",
        "period_kind": "instant",
        "allowed_evidence_kinds": ["xbrl_fact"],
        "required": True,
    }
    row.update(overrides)
    return row


def _specified_catalogue() -> dict:
    schema = load_pack_schema("PK01")
    schema["catalogue_state"] = "specified"
    schema["fields"] = [_catalogue_field()]
    schema["checks"] = [
        {
            "check_id": "probe_sum",
            "kind": "sum_identity",
            "operands": ["probe_field"],
        }
    ]
    return schema


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
    assert schema["pack_id"] == pack_id
    assert schema["catalogue_state"] == "unspecified"
    assert schema["fields"] == []
    assert schema["checks"] == []
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
            "operands": ["probe_field"],
            "tolerance": None,
            "evidence_field_ids": ["probe_field"],
            "reason": "catalogue unspecified",
        }
    ]
    _finish(obj)
    assert validate_pack_result(obj) == []


def test_unknown_pack_schema_load_raises() -> None:
    with pytest.raises(KeyError):
        load_pack_schema("PK99")


def test_referencing_registry_validates_minimal_result() -> None:
    pytest.importorskip("referencing")
    assert pack_contract._HAS_REFERENCING is True
    assert validate_pack_result(_minimal_result("PK01")) == []


def test_refresolver_fallback_validates_minimal_result(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pack_contract, "_HAS_REFERENCING", False)
    assert validate_pack_result(_minimal_result("PK01")) == []


def test_bad_evidence_kind_rejected() -> None:
    obj = _minimal_result("PK01")
    obj["fields"] = [_field_row(evidence_kind="none")]
    errors = validate_pack_result(obj)
    assert errors
    assert any("evidence_kind" in item for item in errors)


def test_bad_type_rejected() -> None:
    obj = _minimal_result("PK01")
    obj["fields"] = [_field_row(type="string")]
    errors = validate_pack_result(obj)
    assert errors
    assert any(".type" in item or item.startswith("type") or "type" in item for item in errors)


def test_valued_row_with_null_value_rejected() -> None:
    obj = _set_applicable(_minimal_result("PK01"))
    obj["fields"] = [_valued_row(value=None)]
    _finish(obj)
    errors = validate_pack_result(obj)
    assert errors
    assert any("fields.0.value" in item for item in errors)


def test_typed_absence_row_with_value_rejected() -> None:
    obj = _minimal_result("PK01")
    obj["fields"] = [_field_row(value="1.0")]
    _finish(obj)
    errors = validate_pack_result(obj)
    assert errors
    assert any("fields.0.value" in item for item in errors)


def test_absence_mismatched_non_value_state_rejected() -> None:
    obj = _minimal_result("PK01")
    obj["fields"] = [_field_row(non_value_state="not_evaluable")]
    _finish(obj)
    errors = validate_pack_result(obj)
    assert errors
    assert any("fields.0.non_value_state" in item for item in errors)


def test_numeric_row_with_text_value_rejected() -> None:
    obj = _minimal_result("PK01")
    obj["fields"] = [_field_row(text_value="not-numeric")]
    _finish(obj)
    errors = validate_pack_result(obj)
    assert errors
    assert any("fields.0.text_value" in item for item in errors)


def test_text_row_valued_via_text_value_accepted() -> None:
    obj = _set_applicable(_minimal_result("PK01"))
    obj["fields"] = [
        _valued_row(
            type="text",
            unit=None,
            value=None,
            text_value="going concern language",
            evidence_kind="text_span",
            required_evidence_kind="text_span",
            source_occurrence_ids=[],
            concept=None,
            source_span={"start_offset": 0, "end_offset": 8},
        )
    ]
    _finish(obj)
    assert validate_pack_result(obj) == []


def test_valued_xbrl_fact_without_occurrence_ids_rejected() -> None:
    obj = _set_applicable(_minimal_result("PK01"))
    obj["fields"] = [_valued_row(source_occurrence_ids=[])]
    _finish(obj)
    errors = validate_pack_result(obj)
    assert errors
    assert any("fields.0.source_occurrence_ids" in item for item in errors)


def test_valued_text_span_without_source_span_rejected() -> None:
    obj = _set_applicable(_minimal_result("PK01"))
    obj["fields"] = [
        _valued_row(
            type="text",
            unit=None,
            value=None,
            text_value="span",
            evidence_kind="text_span",
            required_evidence_kind="text_span",
            source_occurrence_ids=[],
            concept=None,
            source_span=None,
        )
    ]
    _finish(obj)
    errors = validate_pack_result(obj)
    assert errors
    assert any("fields.0.source_span" in item for item in errors)


def test_valued_table_cell_without_table_id_rejected() -> None:
    obj = _set_applicable(_minimal_result("PK01"))
    obj["fields"] = [
        _valued_row(
            evidence_kind="table_cell",
            required_evidence_kind="table_cell",
            source_occurrence_ids=[],
            concept=None,
            table_cell={"table_id": None, "row": 0, "column": 1},
        )
    ]
    _finish(obj)
    errors = validate_pack_result(obj)
    assert errors
    assert any("fields.0.table_cell" in item for item in errors)


def test_valued_formula_without_rule_id_rejected() -> None:
    obj = _set_applicable(_minimal_result("PK01"))
    operand = _field_row(field_id="operand_field")
    formula = _valued_row(
        field_id="formula_field",
        evidence_kind="formula",
        required_evidence_kind="formula",
        source_occurrence_ids=[],
        concept=None,
        formula_rule_id=None,
        dependency_field_ids=["operand_field"],
    )
    obj["fields"] = [operand, formula]
    _finish(obj)
    errors = validate_pack_result(obj)
    assert errors
    assert any("formula_rule_id" in item for item in errors)


def test_dangling_dependency_field_id_rejected() -> None:
    obj = _minimal_result("PK01")
    obj["fields"] = [_field_row(dependency_field_ids=["ghost_field"])]
    _finish(obj)
    errors = validate_pack_result(obj)
    assert errors
    assert any("dependency_field_ids" in item and "ghost_field" in item for item in errors)


def test_dangling_check_evidence_field_id_rejected() -> None:
    obj = _minimal_result("PK01")
    obj["fields"] = [_field_row()]
    obj["checks"] = [
        {
            "check_id": "probe_sum",
            "kind": "sum_identity",
            "status": "not_evaluable",
            "operands": ["probe_field"],
            "tolerance": None,
            "evidence_field_ids": ["ghost_field"],
            "reason": None,
        }
    ]
    _finish(obj)
    errors = validate_pack_result(obj)
    assert errors
    assert any("evidence_field_ids" in item and "ghost_field" in item for item in errors)


def test_duplicate_check_id_rejected() -> None:
    obj = _minimal_result("PK01")
    obj["fields"] = [_field_row()]
    check = {
        "check_id": "probe_sum",
        "kind": "sum_identity",
        "status": "not_evaluable",
        "operands": ["probe_field"],
        "tolerance": None,
        "evidence_field_ids": ["probe_field"],
        "reason": None,
    }
    obj["checks"] = [deepcopy(check), deepcopy(check)]
    _finish(obj)
    errors = validate_pack_result(obj)
    assert errors
    assert any("duplicate check_id" in item for item in errors)


def test_coverage_mismatch_rejected() -> None:
    obj = _minimal_result("PK01")
    obj["fields"] = [_field_row()]
    obj["pack_content_sha256"] = pack_content_digest(obj)
    errors = validate_pack_result(obj)
    assert errors
    assert any("coverage.missing_fields: declared 0, rows 1" in item for item in errors)


def test_valued_row_under_not_applicable_rejected() -> None:
    obj = _minimal_result("PK01")
    obj["applicability"] = {
        "state": "not_applicable",
        "reason": "fixture not applicable",
        "rule_id": "specialist_pack.fixture_not_applicable",
        "sic": None,
        "sic_source": None,
    }
    obj["fields"] = [_valued_row()]
    _finish(obj)
    errors = validate_pack_result(obj)
    assert errors
    assert any("quality_state" in item and "not_applicable" in item for item in errors)


def test_tampered_content_digest_rejected() -> None:
    obj = _minimal_result("PK01")
    obj["limitations"] = ["tampered limitation text"]
    errors = validate_pack_result(obj)
    assert errors
    assert any("pack_content_sha256" in item for item in errors)


def test_pack_content_digest_deterministic_under_key_reordering() -> None:
    obj = _minimal_result("PK01")
    first = pack_content_digest(obj)
    reordered = {key: obj[key] for key in reversed(list(obj))}
    nested = deepcopy(obj)
    nested["entity"] = {key: nested["entity"][key] for key in reversed(list(nested["entity"]))}
    assert pack_content_digest(reordered) == first
    assert pack_content_digest(nested) == first
    assert first == obj["pack_content_sha256"]


@pytest.mark.parametrize("pack_id", PACK_IDS)
def test_catalogue_errors_empty_for_pack_files(pack_id: str) -> None:
    assert catalogue_errors(pack_id) == []


def test_specified_catalogue_with_zero_fields_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = load_pack_schema("PK01")
    fake["catalogue_state"] = "specified"
    monkeypatch.setattr(pack_contract, "load_pack_schema", lambda pack_id: deepcopy(fake))
    errors = catalogue_errors("PK01")
    assert errors
    assert any("fields" in item for item in errors)


def test_unspecified_catalogue_with_a_field_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = load_pack_schema("PK01")
    fake["fields"] = [_catalogue_field()]
    monkeypatch.setattr(pack_contract, "load_pack_schema", lambda pack_id: deepcopy(fake))
    errors = catalogue_errors("PK01")
    assert errors
    assert any("fields" in item for item in errors)


def test_duplicate_catalogue_field_id_reported(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _specified_catalogue()
    fake["fields"] = [_catalogue_field(), _catalogue_field()]
    monkeypatch.setattr(pack_contract, "load_pack_schema", lambda pack_id: deepcopy(fake))
    errors = catalogue_errors("PK01")
    assert errors
    assert any("duplicate field_id" in item for item in errors)


def test_specified_catalogue_unknown_field_id_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _specified_catalogue()
    monkeypatch.setattr(pack_contract, "load_pack_schema", lambda pack_id: deepcopy(fake))
    obj = _minimal_result("PK01")
    obj["fields"] = [_field_row(field_id="unknown_field")]
    _finish(obj)
    errors = validate_pack_result(obj)
    assert errors
    assert any("unknown_field" in item and "catalogue" in item for item in errors)


def test_specified_catalogue_type_mismatch_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _specified_catalogue()
    monkeypatch.setattr(pack_contract, "load_pack_schema", lambda pack_id: deepcopy(fake))
    obj = _minimal_result("PK01")
    obj["fields"] = [_field_row(type="integer")]
    _finish(obj)
    errors = validate_pack_result(obj)
    assert errors
    assert any("fields.0.type" in item for item in errors)


def test_specified_catalogue_unit_mismatch_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _specified_catalogue()
    monkeypatch.setattr(pack_contract, "load_pack_schema", lambda pack_id: deepcopy(fake))
    obj = _minimal_result("PK01")
    obj["fields"] = [_field_row(unit="shares")]
    _finish(obj)
    errors = validate_pack_result(obj)
    assert errors
    assert any("fields.0.unit" in item for item in errors)


def test_specified_catalogue_disallowed_evidence_kind_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = _specified_catalogue()
    monkeypatch.setattr(pack_contract, "load_pack_schema", lambda pack_id: deepcopy(fake))
    obj = _set_applicable(_minimal_result("PK01"))
    obj["fields"] = [
        _valued_row(
            evidence_kind="text_span",
            required_evidence_kind="text_span",
            source_occurrence_ids=[],
            concept=None,
            source_span={"start_offset": 0, "end_offset": 4},
        )
    ]
    _finish(obj)
    errors = validate_pack_result(obj)
    assert errors
    assert any("fields.0.evidence_kind" in item for item in errors)


def test_specified_catalogue_required_field_absent_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = _specified_catalogue()
    monkeypatch.setattr(pack_contract, "load_pack_schema", lambda pack_id: deepcopy(fake))
    obj = _set_applicable(_minimal_result("PK01"))
    _finish(obj)
    errors = validate_pack_result(obj)
    assert errors
    assert any("required field_id" in item and "probe_field" in item for item in errors)


def test_specified_catalogue_required_field_typed_absence_accepted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = _specified_catalogue()
    monkeypatch.setattr(pack_contract, "load_pack_schema", lambda pack_id: deepcopy(fake))
    obj = _set_applicable(_minimal_result("PK01"))
    obj["fields"] = [_field_row()]
    _finish(obj)
    assert validate_pack_result(obj) == []


def test_specified_catalogue_unknown_check_id_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _specified_catalogue()
    monkeypatch.setattr(pack_contract, "load_pack_schema", lambda pack_id: deepcopy(fake))
    obj = _minimal_result("PK01")
    obj["checks"] = [
        {
            "check_id": "unknown_check",
            "kind": "sum_identity",
            "status": "not_evaluable",
            "operands": [],
            "tolerance": None,
            "evidence_field_ids": [],
            "reason": None,
        }
    ]
    _finish(obj)
    errors = validate_pack_result(obj)
    assert errors
    assert any("unknown_check" in item and "catalogue" in item for item in errors)


def test_catalogue_schema_additional_properties_false_everywhere() -> None:
    schema = load_catalogue_schema()
    missing = [
        path
        for path, node in _object_nodes(schema)
        if node.get("additionalProperties") is not False
    ]
    assert missing == []
    assert schema["$id"] == "https://mastermind-x.com/contracts/specialist_pack_catalogue.v1.schema.json"
