"""Contract checks for the company-intelligence relationship package family.

Covers the four schema files under contracts/company_intelligence/: they must be
draft-2020-12 checkable, closed on every object node that declares properties,
proposed-adoption with all-false authority, and they must accept the committed
extraction rows / source excerpts while refusing non-relationship species.
"""
from __future__ import annotations

import copy
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import jsonschema
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
CONTRACT_DIR = REPO_ROOT / "contracts" / "company_intelligence"
EXTRACTION_PATH = (
    REPO_ROOT
    / "research/theme_graph/gmi_relationships_20261021/extraction/swks_aapl_m1.jsonl"
)
SOURCES_DIR = REPO_ROOT / "research/theme_graph/gmi_relationships_20261021/sources"

EXTRACTION_SCHEMA = "relationship_extraction.v1.schema.json"
EXCERPT_SCHEMA = "relationship_source_excerpt.v1.schema.json"
PACKAGE_SCHEMA = "relationship_observation_package.v2.schema.json"
EDGES_SCHEMA = "relationship_edges.v1.schema.json"

SCHEMA_FILES = (EXTRACTION_SCHEMA, EXCERPT_SCHEMA, PACKAGE_SCHEMA, EDGES_SCHEMA)

REFUSED_SPECIES = (
    "planned_integration",
    "theme",
    "similarity",
    "correlation",
    "common_input",
)

# A24 — the knowledge clock, declared identically in all four contracts.
CLOCK_RULE = {
    "rule_id": "A24",
    "clock": "sec_acceptance",
    "source_field": "sec_index_header_acceptance_et",
    "source_format": "YYYYMMDDHHMMSS",
    "source_tz": "America/New_York",
    "target_tz": "UTC",
    "target_format": "YYYY-MM-DDTHH:MM:SSZ",
    "dst": "IANA tzdata; ambiguous (fall-back) or nonexistent (spring-forward) wall times are refused, never guessed",
    "not_a_clock": ["sec_submissions_acceptance_raw"],
    "note": (
        "The EDGAR submissions JSON acceptanceDateTime carries a 'Z' suffix but is "
        "NOT a UTC instant (observed +5h versus header-derived UTC on all three M1 "
        "documents, e.g. header 20241115163743 ET = 2024-11-15T21:37:43Z while the "
        "JSON reads 2024-11-16T02:37:43.000Z); it is retained only as "
        "sec_submissions_acceptance_raw and never used as a clock."
    ),
}

# The one-sentence A24 marking every acceptance-derived instant carries.
A24_DESCRIPTION = (
    "SEC EDGAR acceptance time: sec_index_header_acceptance_et read as "
    "America/New_York wall clock and converted to UTC (x-gmi-clock-rule A24)"
)


def _load_schema(name: str) -> dict:
    return json.loads((CONTRACT_DIR / name).read_text(encoding="utf-8"))


def _load_rows() -> list[dict]:
    return [
        json.loads(line)
        for line in EXTRACTION_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _validator(schema: dict):
    return jsonschema.validators.validator_for(schema)(schema)


def test_all_four_contracts_check_schema():
    for name in SCHEMA_FILES:
        schema = _load_schema(name)
        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        # Raises on any draft-2020-12 meta-schema violation.
        _validator(schema).check_schema(schema)


_CONDITIONAL_KEYS = ("if", "then", "else")


def _walk_object_nodes(node):
    if isinstance(node, dict):
        if "properties" in node:
            yield node
        for key, value in node.items():
            if key.startswith("x-"):
                continue  # annotation, not a schema node
            if key in _CONDITIONAL_KEYS:
                continue  # applicator subschema on an already-closed object
            yield from _walk_object_nodes(value)
    elif isinstance(node, list):
        for value in node:
            yield from _walk_object_nodes(value)


def _walk_conditional_owners(node):
    """Dicts that own an if/then/else applicator, at any depth."""
    if isinstance(node, dict):
        if any(key in node for key in _CONDITIONAL_KEYS):
            yield node
        for value in node.values():
            yield from _walk_conditional_owners(value)
    elif isinstance(node, list):
        for value in node:
            yield from _walk_conditional_owners(value)


def test_every_object_node_closed():
    for name in SCHEMA_FILES:
        schema = _load_schema(name)
        nodes = list(_walk_object_nodes(schema))
        assert nodes, f"{name}: walk found no property-bearing object nodes"
        for node in nodes:
            assert node.get("additionalProperties") is False, (
                f"{name}: an object node with properties is not closed "
                f"(properties={sorted(node.get('properties', {}))})"
            )
        for owner in _walk_conditional_owners(schema):
            assert owner.get("additionalProperties") is False, (
                f"{name}: the object owning an if/then/else is not closed "
                f"(properties={sorted(owner.get('properties', {}))})"
            )


def test_adoption_state_proposed_and_authority_all_false():
    for name in (PACKAGE_SCHEMA, EDGES_SCHEMA):
        schema = _load_schema(name)
        props = schema["properties"]
        assert props["adoption_state"] == {"const": "proposed"}
        assert props["authority"] == {"$ref": "#/$defs/authority"}
        authority = schema["$defs"]["authority"]
        assert authority["additionalProperties"] is False
        assert sorted(authority["properties"]) == [
            "gate",
            "prediction",
            "rank",
            "size",
            "trade",
        ]
        for key, node in authority["properties"].items():
            assert node == {"const": False}, f"{name}: authority.{key} not const false"
        assert sorted(authority["required"]) == [
            "gate",
            "prediction",
            "rank",
            "size",
            "trade",
        ]


def test_committed_rows_conform():
    schema = _load_schema(EXTRACTION_SCHEMA)
    validator = _validator(schema)
    rows = _load_rows()
    assert len(rows) == 4
    kinds = sorted(row["row_kind"] for row in rows)
    assert kinds == ["coverage", "document_assessment", "observation", "observation"]
    for row in rows:
        validator.validate(row)


def test_committed_excerpts_conform():
    schema = _load_schema(EXCERPT_SCHEMA)
    validator = _validator(schema)
    paths = sorted(SOURCES_DIR.glob("*.json"))
    assert len(paths) == 3
    for path in paths:
        validator.validate(json.loads(path.read_text(encoding="utf-8")))


@pytest.mark.parametrize("species", REFUSED_SPECIES)
def test_refused_species_rejected_by_contract(species):
    schema = _load_schema(EXTRACTION_SCHEMA)
    template = next(
        row for row in _load_rows() if row.get("row_kind") == "observation"
    )
    row = copy.deepcopy(template)
    row["species"] = species
    with pytest.raises(jsonschema.ValidationError):
        _validator(schema).validate(row)


def test_clock_rule_declared_in_contracts():
    for name in SCHEMA_FILES:
        schema = _load_schema(name)
        assert schema.get("x-gmi-clock-rule") == CLOCK_RULE, name
    extraction = _load_schema(EXTRACTION_SCHEMA)
    for row_kind in ("observation_row", "assessment_row", "coverage_row"):
        published_at = extraction["$defs"][row_kind]["properties"]["published_at"]
        assert published_at["description"] == A24_DESCRIPTION, row_kind
    assert (
        extraction["$defs"]["source_ref"]["properties"]["accepted_at"]["description"]
        == A24_DESCRIPTION
    )
    for row_kind in ("observation_row", "assessment_row"):
        props = extraction["$defs"][row_kind]["properties"]
        assert "America/New_York" in props["sec_index_header_acceptance_et"]["description"]
        raw_description = props["sec_submissions_acceptance_raw"]["description"]
        assert "NOT a clock" in raw_description
        assert "not_a_clock" in raw_description
    excerpt = _load_schema(EXCERPT_SCHEMA)
    assert excerpt["properties"]["accepted_at"]["description"] == A24_DESCRIPTION
    package = _load_schema(PACKAGE_SCHEMA)
    for entry in (
        "observation_entry",
        "assessment_entry",
        "coverage_entry",
        "non_edge",
        "magnitude_revision",
    ):
        known_at = package["$defs"][entry]["properties"]["known_at"]
        assert known_at.get("description") == A24_DESCRIPTION, entry
    edges = _load_schema(EDGES_SCHEMA)
    edge_props = edges["$defs"]["edge"]["properties"]
    for field in ("first_known_at", "last_asserted_at", "last_assessed_at"):
        assert edge_props[field].get("description") == A24_DESCRIPTION, field
    for entry in (
        "correction_lineage_entry",
        "coverage_entry",
        "magnitude_revision",
        "non_edge",
    ):
        known_at = edges["$defs"][entry]["properties"]["known_at"]
        assert known_at.get("description") == A24_DESCRIPTION, entry


def test_published_at_is_et_acceptance_converted_to_utc():
    def convert(header: str) -> str:
        naive = datetime.strptime(header, "%Y%m%d%H%M%S")
        aware = naive.replace(tzinfo=ZoneInfo("America/New_York"))
        return aware.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    excerpts = {
        path.stem: json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(SOURCES_DIR.glob("*.json"))
    }
    for row in _load_rows():
        header = row.get("sec_index_header_acceptance_et")
        if not header:
            continue
        expect = convert(header)
        assert row["published_at"] == expect, row.get("observation_id") or row
        source = row.get("source_ref")
        if source:
            assert excerpts[source["accession"]]["accepted_at"] == row["published_at"]

    from engine.company_intelligence.relationships import clock

    assert clock.SOURCE_TZ == "America/New_York"
    assert clock.et_acceptance_to_utc("20241115163743") == "2024-11-15T21:37:43Z"
    assert clock.et_acceptance_to_utc("20250801163000") == "2025-08-01T20:30:00Z"
    with pytest.raises(clock.ClockRefused):
        clock.et_acceptance_to_utc("20251102013000")  # fall-back repeat: ambiguous
    with pytest.raises(clock.ClockRefused):
        clock.et_acceptance_to_utc("20250309023000")  # spring-forward gap: nonexistent
    with pytest.raises(clock.ClockRefused):
        clock.et_acceptance_to_utc("2024111516374")  # 13 digits: format


def test_submissions_raw_is_not_the_clock():
    accessions = (
        "0000004127-24-000131",
        "0000004127-25-000085",
        "0000004127-26-000003",
    )
    rows = _load_rows()
    for accession in accessions:
        row = next(
            r for r in rows if (r.get("source_ref") or {}).get("accession") == accession
        )
        raw = datetime.fromisoformat(
            row["sec_submissions_acceptance_raw"].replace("Z", "+00:00")
        )
        published = datetime.strptime(
            row["published_at"], "%Y-%m-%dT%H:%M:%SZ"
        ).replace(tzinfo=timezone.utc)
        assert raw - published == timedelta(hours=5), accession


def _rights_validator():
    schema = _load_schema(EDGES_SCHEMA)
    return _validator(schema["$defs"]["rights"])


def _rights(**overrides) -> dict:
    rights = {
        "source_class": "SEC_PUBLIC_ACCESS",
        "purpose_permitted": ["private_api", "research"],
        "public_display": "unknown",
        "excerpt_display": "unknown",
        "magnitude_display": "unknown",
        "ruling_ref": None,
    }
    rights.update(overrides)
    return rights


def test_rights_binding_shape():
    validator = _rights_validator()
    ref = "GMI-REL-TEST-0001@sha256:" + "a" * 64
    # The committed default binds nothing.
    validator.validate(_rights())
    # A bound ruling with a valid ref.
    validator.validate(
        _rights(
            public_display="derived_facts_permitted",
            excerpt_display="entitled_only",
            magnitude_display="permitted",
            ruling_ref=ref,
        )
    )
    for bad in (
        _rights(public_display="derived_facts_permitted"),  # any non-unknown + null ref
        _rights(excerpt_display="public_permitted"),
        _rights(magnitude_display="entitled_only"),
        _rights(ruling_ref=ref),  # all-unknown + a ref
        _rights(ruling_ref="gmi-rel-test@sha256:" + "a" * 64),  # bad ref pattern
        _rights(ruling_ref="GMI-REL-TEST-0001@sha256:" + "g" * 64),
        _rights(extra_key=True),  # closed object
    ):
        with pytest.raises(jsonschema.ValidationError):
            validator.validate(bad)
