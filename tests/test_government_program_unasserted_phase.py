"""Historical oversight identity never invents a current lifecycle phase."""
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from engine.government_revenue import program_ontology as po, program_dossier as pd
from tests.test_government_program_oversight import oversight_graph


def graph(version="1.4.0", phase=None):
    g = oversight_graph()
    g["schema_version"] = version
    g["programs"][0]["phase"] = phase
    if version in ("1.0.0", "1.1.0", "1.2.0"):
        g.pop("public_oversight_assertions")
        g["evidence"] = [g["evidence"][0]]
    if version in ("1.0.0", "1.1.0"):
        g.pop("public_capacity_assertions")
    return g


def test_explicit_null_phase_survives_native_composition_and_schema():
    candidate = graph()
    loaded = po.load_program_ontology_graph(candidate)
    root = Path(__file__).resolve().parents[1]
    schema = json.loads((root/"contracts/government_revenue/government_program_ontology.v1_4.schema.json").read_text())
    Draft202012Validator(schema).validate(candidate)
    bundle = pd.compose_program_dossier_bundle(ontology_graph=loaded, as_of="2026-08-22")
    assert pd.is_valid_program_dossier_payload(bundle)
    identity = bundle["dossiers"][0]["program_identity"]
    assert identity["state"] == "reviewed"
    assert identity["phase"] is None


@pytest.mark.parametrize("version", ["1.0.0", "1.1.0", "1.2.0", "1.3.0"])
def test_legacy_versions_do_not_gain_null_phase(version):
    with pytest.raises(po.OntologyInputError, match="ontology_row_shape_invalid"):
        po.load_program_ontology_graph(graph(version))


@pytest.mark.parametrize("phase", ["", " ", "unknown", "not_asserted", 0, False, [], {}])
def test_only_explicit_null_or_original_phase_enum_is_permitted(phase):
    with pytest.raises(po.OntologyInputError, match="ontology_row_shape_invalid"):
        po.load_program_ontology_graph(graph(phase=phase))


@pytest.mark.parametrize("phase", sorted(po.PHASE_ENUM))
def test_existing_phases_still_compose_without_reinterpretation(phase):
    candidate = graph(phase=phase)
    loaded = po.load_program_ontology_graph(candidate)
    assert loaded["programs"][0]["phase"] == phase
    assert loaded == candidate


@pytest.mark.parametrize("lang", ["en", "zh"])
def test_consumer_names_unasserted_phase_without_printing_protocol_values(lang):
    from tests.test_government_program_oversight_ui import run
    loaded = po.load_program_ontology_graph(graph())
    bundle = pd.compose_program_dossier_bundle(ontology_graph=loaded, as_of="2026-08-22")
    result = run(bundle, lang)
    assert result["state"] == "ok"
    assert ("not established by reviewed sources" if lang == "en" else "已复核来源尚未确立") in result["html"]
    assert "Phase: null" not in result["html"]


def test_missing_phase_is_not_an_explicit_null():
    candidate = graph()
    del candidate["programs"][0]["phase"]
    with pytest.raises(po.OntologyInputError, match="ontology_row_shape_invalid"):
        po.load_program_ontology_graph(candidate)
