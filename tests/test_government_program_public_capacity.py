"""Public economic capacity observations do not become revenue or readiness."""
from copy import deepcopy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker

from engine.government_revenue import program_ontology as po
from engine.government_revenue import program_dossier as pd
from scripts import curate_government_program_ontology as curator
from tests.fixtures.government_program_ontology import builders as b

ROOT = Path(__file__).resolve().parents[1]
OLD = "2020-01-01T00:00:00+00:00"


def graph():
    result = b.empty_graph()
    result["schema_version"] = "1.2.0"
    identity = b.evidence_row("identity", claim_scopes=["program_identity"], known_at=OLD, retrieved_at=OLD)
    capacity = b.evidence_row("capacity", claim_scopes=["program_identity", "public_capacity"])
    result["evidence"] = [identity, capacity]
    result["programs"] = [b.program_row(known_at=OLD, evidence_refs=[identity["evidence_id"]])]
    result["public_capacity_assertions"] = []
    return result


def claim(g, **changes):
    row = dict(revision=1, program_id="acq-program:example", product_scope="whole_program",
        product_label="Example whole product", entity_id=None, kind="announced_target",
        quantity=2000, comparator="approximately", unit="units_per_year", period_label="Target within seven years",
        known_at=b.DEFAULT_KNOWN_AT, valid_from=OLD, valid_to=None, verification_state="reviewed",
        evidence_refs=[g["evidence"][1]["evidence_id"]], predecessor_id=None, succession_reason=None)
    row.update(changes)
    row["id"] = po.public_capacity_assertion_id(row)
    return row


def dossier(g, as_of="2026-08-22"):
    loaded = po.load_program_ontology_graph(g)
    return pd.compose_program_dossier_bundle(ontology_graph=loaded, as_of=as_of,
                                            generated_at="2026-08-22T10:00:00+00:00")


def schema(name):
    return Draft202012Validator(json.loads((ROOT / "contracts/government_revenue" / name).read_text()), format_checker=FormatChecker())


def test_capacity_kinds_components_and_native_units_remain_separate():
    g = graph()
    g["public_capacity_assertions"] = [claim(g),
        claim(g, kind="installed_capacity", quantity=600, period_label="Disclosed current installed annual capacity"),
        claim(g, kind="demonstrated_throughput", quantity=620, unit="units", period_label="Units delivered during 2025"),
        claim(g, product_scope="component", product_label="Example seeker", quantity=3, unit="relative_multiplier")]
    schema("government_program_ontology.v1_2.schema.json").validate(g)
    out = dossier(g)
    assert pd.is_valid_program_dossier_payload(out)
    rail = out["dossiers"][0]["public_capacity"]
    assert rail["state"] == "reviewed"
    assert len(rail["announced_target"]) == 2
    assert rail["installed_capacity"][0]["quantity"] == 600
    assert rail["demonstrated_throughput"][0]["quantity"] == 620
    assert rail["demonstrated_throughput"][0]["unit"] == "units"
    assert {r["id"] for kind in po.PUBLIC_CAPACITY_KINDS for r in rail[kind]} == {r["id"] for r in g["public_capacity_assertions"]}
    assert not any(out["authority"][name] for name in ("can_rank", "can_size", "can_gate", "can_originate_signal"))


@pytest.mark.parametrize("version", ["1.0.0", "1.1.0"])
def test_legacy_shapes_stay_valid_and_reject_new_capacity_fields(version):
    g = graph(); g["schema_version"] = version
    with pytest.raises(po.OntologyInputError): po.load_program_ontology_graph(g)
    del g["public_capacity_assertions"]
    with pytest.raises(po.OntologyInputError): po.load_program_ontology_graph(g)
    g["evidence"] = g["evidence"][:1]
    out = dossier(g)
    assert out["schema_version"] == "1.0.0"
    assert "public_capacity" not in out["dossiers"][0]
    assert pd.is_valid_program_dossier_payload(out)


@pytest.mark.parametrize("kind,unit", [("installed_capacity", "units"), ("installed_capacity", "relative_multiplier"),
    ("demonstrated_throughput", "relative_multiplier"), ("announced_target", "USD"), ("readiness", "units")])
def test_incompatible_kind_units_refuse(kind, unit):
    g = graph(); g["public_capacity_assertions"] = [claim(g, kind=kind, unit=unit)]
    with pytest.raises(po.OntologyInputError, match="public_capacity_kind_unit_invalid"): po.load_program_ontology_graph(g)


@pytest.mark.parametrize("quantity", [True, False, 0, -1, float("inf"), float("nan"), "2000", None])
def test_quantity_must_be_positive_native_finite_number(quantity):
    g = graph(); row = claim(g); row["quantity"] = quantity; g["public_capacity_assertions"] = [row]
    with pytest.raises(po.OntologyInputError, match="public_capacity_quantity_invalid"): po.load_program_ontology_graph(g)


@pytest.mark.parametrize("field,value", [("program_id", "acq-program:invented"), ("evidence_refs", []),
    ("evidence_refs", ["ev:000000000000"]), ("verification_state", "proposed"), ("product_scope", "inferred"),
    ("valid_to", "2019-01-01T00:00:00+00:00"), ("known_at", "2030-01-01T00:00:00+00:00")])
def test_bad_identity_review_evidence_or_clocks_refuse_even_with_new_id(field, value):
    g = graph(); g["public_capacity_assertions"] = [claim(g, **{field: value})]
    with pytest.raises(po.OntologyInputError): po.load_program_ontology_graph(g)


def test_capacity_evidence_scope_and_availability_cannot_be_bypassed():
    g = graph(); g["public_capacity_assertions"] = [claim(g)]
    g["evidence"][1]["claim_scopes"] = ["program_identity"]
    with pytest.raises(po.OntologyInputError, match="claim_scope_coverage_missing"): po.load_program_ontology_graph(g)
    g = graph(); g["public_capacity_assertions"] = [claim(g)]
    g["evidence"][1]["known_at"] = "2026-08-22T08:30:00+00:00"
    with pytest.raises(po.OntologyInputError, match="evidence_known_after_claim"): po.load_program_ontology_graph(g)


def test_historical_cutoff_and_closed_validity_do_not_leak_later_capacity():
    g = graph(); g["public_capacity_assertions"] = [claim(g)]
    early = dossier(g, "2026-08-21")["dossiers"][0]["public_capacity"]
    assert early["state"] == "not_reviewed"
    assert all(early[k] == [] for k in po.PUBLIC_CAPACITY_KINDS)
    g["public_capacity_assertions"] = [claim(g, valid_to="2026-08-22T12:00:00+00:00")]
    assert all(dossier(g)["dossiers"][0]["public_capacity"][k] == [] for k in po.PUBLIC_CAPACITY_KINDS)


def test_changed_quantity_requires_new_owner_identity_and_dossier_rehash_is_insufficient():
    g = graph(); g["public_capacity_assertions"] = [claim(g)]
    changed = deepcopy(g); changed["public_capacity_assertions"][0]["quantity"] = 999
    with pytest.raises(po.OntologyInputError, match="public_capacity_identity_invalid"): po.load_program_ontology_graph(changed)
    out = dossier(g); out["dossiers"][0]["public_capacity"]["announced_target"][0]["quantity"] = 999
    out["content_id"] = pd.dossier_content_id(out)
    assert not pd.is_valid_program_dossier_payload(out)


def test_conflict_and_retirement_suppress_quantities():
    g = graph(); a = claim(g); b_row = claim(g, quantity=3000); g["public_capacity_assertions"] = [a, b_row]
    g["conflicts"] = [b.conflict_row(scope="public_capacity", subject_type="program", subject_id=a["program_id"],
        candidate_row_ids=[a["id"], b_row["id"]], evidence_refs=a["evidence_refs"])]
    rail = dossier(g)["dossiers"][0]["public_capacity"]
    assert rail["state"] == "conflicted" and all(rail[k] == [] for k in po.PUBLIC_CAPACITY_KINDS)
    g["conflicts"] = []; g["public_capacity_assertions"] = [a]
    g["overrides"] = [b.override_row(action="retire_row", target_row_id=a["id"], evidence_refs=a["evidence_refs"])]
    assert dossier(g)["dossiers"][0]["public_capacity"]["announced_target"] == []


def test_successor_is_point_in_time_and_cannot_turn_target_into_throughput():
    g = graph(); a = claim(g); g["public_capacity_assertions"] = [a]
    later = claim(g, quantity=2500, revision=2, predecessor_id=a["id"], succession_reason="attribute_revision")
    g["public_capacity_assertions"].append(later)
    assert [r["quantity"] for r in dossier(g)["dossiers"][0]["public_capacity"]["announced_target"]] == [2500]
    g["public_capacity_assertions"][1] = claim(g, kind="demonstrated_throughput", quantity=2500,
        revision=2, predecessor_id=a["id"], succession_reason="attribute_revision")
    with pytest.raises(po.OntologyInputError, match="public_capacity_succession_invalid"): po.load_program_ontology_graph(g)


def test_curator_explicit_migration_and_duplicate_import(tmp_path):
    g = graph(); row = claim(g)
    g["schema_version"] = "1.1.0"; del g["public_capacity_assertions"]
    evidence = g["evidence"].pop()
    target = tmp_path / "program_ontology.json"; target.write_text(json.dumps(g))
    worksheet = b.worksheet(coverage=[{"scope":"public_capacity", "subject_type":"program", "subject_id":row["program_id"]}], rows=[{"action": "admit", "target_kind": "evidence", "candidate_row": evidence},
        {"action": "admit", "target_kind": "public_capacity_assertion", "candidate_row": row}])
    source = tmp_path / "worksheet.json"; source.write_text(json.dumps(worksheet))
    report = curator.curate_worksheet(source, target_path=target, schema_version="1.2.0")
    assert report["rejected_count"] == 0
    before = target.read_bytes()
    curator.curate_worksheet(source, target_path=target)
    assert target.read_bytes() == before
    assert len(json.loads(before)["public_capacity_assertions"]) == 1


@pytest.mark.parametrize("field,value", [("kind", []), ("unit", {}), ("program_id", []),
    ("predecessor_id", []), ("product_label", None)])
def test_malformed_scalar_fields_raise_named_ontology_errors(field, value):
    g = graph(); row = claim(g); row[field] = value; g["public_capacity_assertions"] = [row]
    with pytest.raises(po.OntologyInputError, match="public_capacity_shape_invalid"): po.load_program_ontology_graph(g)


@pytest.mark.parametrize("mutation", ["future_known", "future_effective", "expired", "mixed_bucket", "false_reviewed", "duplicate", "wrong_program"])
def test_dossier_consumer_refuses_internal_forgery_even_after_both_hashes_change(mutation):
    g = graph(); g["public_capacity_assertions"] = [claim(g)]
    out = dossier(g); rail = out["dossiers"][0]["public_capacity"]; row = rail["announced_target"][0]
    if mutation == "future_known": row["known_at"] = "2030-01-01T00:00:00+00:00"
    elif mutation == "future_effective": row["valid_from"] = "2030-01-01T00:00:00+00:00"
    elif mutation == "expired": row["valid_to"] = "2026-08-22T00:00:00+00:00"
    elif mutation == "mixed_bucket": rail["demonstrated_throughput"] = rail["announced_target"]; rail["announced_target"] = []
    elif mutation == "false_reviewed": rail["announced_target"] = []
    elif mutation == "duplicate": rail["announced_target"].append(deepcopy(row))
    else: row["program_id"] = "acq-program:other"
    row["id"] = po.public_capacity_assertion_id(row)
    out["content_id"] = pd.dossier_content_id(out)
    assert not pd.is_valid_program_dossier_payload(out)


def test_migrated_dossier_is_consumed_by_existing_theme_owner_validator():
    from engine.government_revenue.program_theme_context import OwnerSnapshot
    g = graph(); g["public_capacity_assertions"] = [claim(g)]
    out = dossier(g)
    owner = OwnerSnapshot("program_dossier", json.dumps(out).encode(), "2026-08-22T10:00:00+00:00", "test-review", "qualified_public_display")
    assert owner.payload() == out


def test_blocked_program_and_unknown_fields_do_not_expose_capacity():
    g = graph(); row = claim(g); g["public_capacity_assertions"] = [row]
    g["overrides"] = [b.override_row(action="block", subject_type="program", subject_id=row["program_id"], evidence_refs=row["evidence_refs"])]
    assert dossier(g)["dossiers"][0]["public_capacity"]["state"] == "not_reviewed"
    row["inferred_utilization"] = .9
    with pytest.raises(po.OntologyInputError, match="public_capacity_shape_invalid"): po.load_program_ontology_graph(g)
