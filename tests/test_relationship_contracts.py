"""Contract checks for the company-intelligence relationship package family.

Covers the four schema files under contracts/company_intelligence/: they must be
draft-2020-12 checkable, closed on every object node that declares properties,
proposed-adoption with all-false authority, and they must accept the committed
extraction rows / source excerpts while refusing non-relationship species.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

import jsonschema
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
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


def _walk_object_nodes(node):
    if isinstance(node, dict):
        if "properties" in node:
            yield node
        for value in node.values():
            yield from _walk_object_nodes(value)
    elif isinstance(node, list):
        for value in node:
            yield from _walk_object_nodes(value)


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
