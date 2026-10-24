"""Public oversight findings stay quoted, source-attributed and non-inferential.

Ontology 1.3 / dossier 1.2 battery: a closed oversight row quotes ONE exact
excerpt from ONE qualified public official acquisition or congressional
source; report edition/publication metadata binds identity but never sets
claim currency; and no quantity, verdict, readiness, issuer allocation or
ranking is representable. All fixtures are synthetic.
"""
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
FUTURE = "2030-01-01T00:00:00+00:00"
PROGRAM = "acq-program:example"
ONTOLOGY_V13 = "government_program_ontology.v1_3.schema.json"
DOSSIER_V12 = "government_program_dossier.v1_2.schema.json"


def oversight_graph():
    result = b.empty_graph()
    result["schema_version"] = "1.3.0"
    identity = b.evidence_row("identity", claim_scopes=["program_identity"], known_at=OLD, retrieved_at=OLD)
    report = b.evidence_row("report", claim_scopes=["program_identity", "public_oversight"],
                            evidence_class="congressional_research",
                            source_url="https://crsreports.congress.gov/product/synthetic-overview")
    capacity = b.evidence_row("capacity", claim_scopes=["program_identity", "public_capacity"])
    result["evidence"] = [identity, report, capacity]
    result["programs"] = [b.program_row(known_at=OLD, evidence_refs=[identity["evidence_id"]])]
    result["public_capacity_assertions"] = []
    result["public_oversight_assertions"] = []
    return result


def oversight_refs(g):
    return [e["evidence_id"] for e in g["evidence"] if "public_oversight" in e.get("claim_scopes", [])]


def assertion(g, **changes):
    row = dict(revision=1, program_id=PROGRAM, finding_kind="cost",
        reported_by="oversight_body", report_series="Synthetic Oversight Series",
        report_document_id="SYN-2026-100", report_edition="First edition",
        published_on="2026-07-15", period_label="Fiscal year 2026 site observations",
        summary="The report records a cost growth observation against the program baseline.",
        excerpt="Reported program cost grew relative to the approved baseline acquisition cost.",
        page=14, printed_page_label="Page 14",
        known_at=b.DEFAULT_KNOWN_AT, valid_from=OLD, valid_to=None, verification_state="reviewed",
        evidence_refs=[oversight_refs(g)[0]], predecessor_id=None, succession_reason=None)
    row.update(changes)
    if "excerpt_sha256" not in changes:
        row["excerpt_sha256"] = po.public_oversight_excerpt_sha256(row["excerpt"])
    row["id"] = po.public_oversight_assertion_id(row)
    return row


def capacity_claim(g, **changes):
    refs = [e["evidence_id"] for e in g["evidence"] if "public_capacity" in e.get("claim_scopes", [])]
    row = dict(revision=1, program_id=PROGRAM, product_scope="whole_program",
        product_label="Example whole product", entity_id=None, kind="announced_target",
        quantity=2000, comparator="approximately", unit="units_per_year",
        period_label="Target within seven years", known_at=b.DEFAULT_KNOWN_AT, valid_from=OLD,
        valid_to=None, verification_state="reviewed", evidence_refs=[refs[0]],
        predecessor_id=None, succession_reason=None)
    row.update(changes)
    row["id"] = po.public_capacity_assertion_id(row)
    return row


def load(g):
    return po.load_program_ontology_graph(g)


def dossier(g, as_of="2026-08-22"):
    return pd.compose_program_dossier_bundle(ontology_graph=load(g), as_of=as_of,
                                             generated_at="2026-08-22T10:00:00+00:00")


def schema(name):
    return Draft202012Validator(json.loads((ROOT / "contracts/government_revenue" / name).read_text()),
                                format_checker=FormatChecker())


def test_valid_synthetic_example_admits_and_composes_with_qualified_source():
    g = oversight_graph()
    g["public_oversight_assertions"] = [assertion(g)]
    schema(ONTOLOGY_V13).validate(g)
    out = dossier(g)
    assert out["schema_version"] == "1.2.0"
    schema(DOSSIER_V12).validate(out)
    assert pd.is_valid_program_dossier_payload(out)
    rail = out["dossiers"][0]["public_oversight"]
    assert rail["state"] == "reviewed"
    row = rail["rows"][0]
    assert row["finding_kind"] == "cost" and row["reported_by"] == "oversight_body"
    assert row["page"] == 14 and row["printed_page_label"] == "Page 14"
    assert row["published_on"] == "2026-07-15" and row["report_edition"] == "First edition"
    assert row["excerpt_sha256"] == po.public_oversight_excerpt_sha256(row["excerpt"])
    assert row["source_url"] == g["evidence"][1]["source_url"]
    assert row["sha256"] == g["evidence"][1]["sha256"]
    assert not any(out["authority"][name] for name in ("can_rank", "can_size", "can_gate", "can_originate_signal"))


@pytest.mark.parametrize("finding_kind", sorted(po.PUBLIC_OVERSIGHT_FINDING_KINDS))
@pytest.mark.parametrize("reported_by", sorted(po.PUBLIC_OVERSIGHT_REPORTER_ENUM))
def test_every_finding_kind_and_reporter_is_public_process_evidence(reported_by, finding_kind):
    g = oversight_graph()
    g["public_oversight_assertions"] = [assertion(g, finding_kind=finding_kind, reported_by=reported_by)]
    out = dossier(g)
    row = out["dossiers"][0]["public_oversight"]["rows"][0]
    assert row["finding_kind"] == finding_kind and row["reported_by"] == reported_by
    assert pd.is_valid_program_dossier_payload(out)


@pytest.mark.parametrize("version", ["1.0.0", "1.1.0", "1.2.0"])
def test_old_versions_fail_closed_on_unknown_oversight_fields(version):
    # The new top-level collection refuses on every old version's own shape law.
    g = oversight_graph()
    g["schema_version"] = version
    g["public_oversight_assertions"] = [assertion(g)]
    with pytest.raises(po.OntologyInputError, match="ontology_shape_invalid"):
        po.load_program_ontology_graph(g)
    # And the new claim scope refuses on every old version's evidence scope law.
    g = oversight_graph()
    g["schema_version"] = version
    del g["public_oversight_assertions"]
    if version != "1.2.0":
        del g["public_capacity_assertions"]
        del g["evidence"][2]
    with pytest.raises(po.OntologyInputError):
        po.load_program_ontology_graph(g)


def test_future_and_mismatched_evidence_clocks_refuse():
    g = oversight_graph()
    g["public_oversight_assertions"] = [assertion(g, known_at=FUTURE)]
    with pytest.raises(po.OntologyInputError, match="future_known_claim"):
        po.load_program_ontology_graph(g)
    g = oversight_graph()
    g["public_oversight_assertions"] = [assertion(g, valid_from="2026-09-01T00:00:00+00:00")]
    with pytest.raises(po.OntologyInputError, match="future_effective_claim"):
        po.load_program_ontology_graph(g)
    g = oversight_graph()
    g["public_oversight_assertions"] = [assertion(g)]
    g["evidence"][1]["known_at"] = "2026-08-22T08:30:00+00:00"
    with pytest.raises(po.OntologyInputError, match="evidence_known_after_claim"):
        po.load_program_ontology_graph(g)


def test_missing_or_unqualified_sources_refuse():
    g = oversight_graph()
    g["public_oversight_assertions"] = [assertion(g, evidence_refs=["ev:000000000000"])]
    with pytest.raises(po.OntologyInputError, match="dangling_reference"):
        po.load_program_ontology_graph(g)
    # Identity-only evidence is not an oversight source.
    g = oversight_graph()
    g["public_oversight_assertions"] = [assertion(g, evidence_refs=[g["evidence"][0]["evidence_id"]])]
    with pytest.raises(po.OntologyInputError, match="public_oversight_evidence_unrelated"):
        po.load_program_ontology_graph(g)
    # Issuer IR disclosures are not official acquisition/congressional sources.
    g = oversight_graph()
    issuer = b.evidence_row("issuer", claim_scopes=["program_identity", "public_oversight"],
                            evidence_class="issuer_disclosure", source_url="https://ir.example.com/quarterly",
                            pinned_issuer_host="ir.example.com")
    g["evidence"].append(issuer)
    g["public_oversight_assertions"] = [assertion(g, evidence_refs=[issuer["evidence_id"]])]
    with pytest.raises(po.OntologyInputError, match="public_oversight_evidence_unrelated"):
        po.load_program_ontology_graph(g)
    # One excerpt is pinned to ONE document: mixed citations refuse.
    g = oversight_graph()
    other = b.evidence_row("report-2", claim_scopes=["program_identity", "public_oversight"],
                           evidence_class="congressional_research",
                           source_url="https://crsreports.congress.gov/product/synthetic-update")
    g["evidence"].append(other)
    g["public_oversight_assertions"] = [assertion(g, evidence_refs=[oversight_refs(g)[0], other["evidence_id"]])]
    with pytest.raises(po.OntologyInputError, match="public_oversight_evidence_unrelated"):
        po.load_program_ontology_graph(g)
    # The cited evidence must carry BOTH program and oversight scopes.
    g = oversight_graph()
    g["evidence"][1]["claim_scopes"] = ["public_oversight"]
    g["public_oversight_assertions"] = [assertion(g)]
    with pytest.raises(po.OntologyInputError, match="claim_scope_coverage_missing"):
        po.load_program_ontology_graph(g)


def test_excerpt_edits_are_detected_by_hash_then_by_content_identity():
    g = oversight_graph()
    row = assertion(g)
    tampered = deepcopy(row)
    tampered["excerpt"] = tampered["excerpt"] + " (adjusted)"
    g["public_oversight_assertions"] = [tampered]
    with pytest.raises(po.OntologyInputError, match="public_oversight_excerpt_hash_mismatch"):
        po.load_program_ontology_graph(g)
    tampered["excerpt_sha256"] = po.public_oversight_excerpt_sha256(tampered["excerpt"])
    g["public_oversight_assertions"] = [tampered]
    with pytest.raises(po.OntologyInputError, match="public_oversight_identity_invalid"):
        po.load_program_ontology_graph(g)


def test_duplicate_content_ids_refuse():
    g = oversight_graph()
    row = assertion(g)
    g["public_oversight_assertions"] = [row, deepcopy(row)]
    with pytest.raises(po.OntologyInputError, match="duplicate_identity_conflict"):
        po.load_program_ontology_graph(g)


def test_content_identity_binds_every_reported_field():
    g = oversight_graph()
    base = assertion(g)
    g["public_oversight_assertions"] = [base]
    load(g)
    for field, value in (("report_edition", "Revised printing"), ("published_on", "2026-08-01"),
                         ("printed_page_label", "14A"), ("summary", "A different summary sentence."),
                         ("period_label", "Calendar year 2025 observations"),
                         ("known_at", "2026-08-22T08:05:00+00:00"), ("page", 15)):
        changed = assertion(g, **{field: value})
        assert changed["id"] != base["id"]


@pytest.mark.parametrize("page", [0, -1, True, "14", None, 1.5])
def test_nonpositive_or_noninteger_pdf_pages_refuse(page):
    g = oversight_graph()
    row = assertion(g)
    row["page"] = page
    g["public_oversight_assertions"] = [row]
    with pytest.raises(po.OntologyInputError, match="public_oversight_(shape_invalid|page_invalid)"):
        po.load_program_ontology_graph(g)


@pytest.mark.parametrize("field,value", [("readiness_assessment", "high"), ("quantity", 12),
                                         ("investment_rank", 1), ("legal_verdict", "liable")])
def test_unknown_or_inferential_fields_are_unknown_shapes(field, value):
    g = oversight_graph()
    row = assertion(g)
    row[field] = value
    g["public_oversight_assertions"] = [row]
    with pytest.raises(po.OntologyInputError, match="public_oversight_shape_invalid"):
        po.load_program_ontology_graph(g)


def test_bad_enums_publication_dates_and_review_states_refuse():
    g = oversight_graph()
    g["public_oversight_assertions"] = [assertion(g, finding_kind="readiness")]
    with pytest.raises(po.OntologyInputError, match="public_oversight_finding_kind_invalid"):
        po.load_program_ontology_graph(g)
    g = oversight_graph()
    g["public_oversight_assertions"] = [assertion(g, reported_by="analyst_opinion")]
    with pytest.raises(po.OntologyInputError, match="public_oversight_reported_by_invalid"):
        po.load_program_ontology_graph(g)
    g = oversight_graph()
    g["public_oversight_assertions"] = [assertion(g, published_on="spring 2026")]
    with pytest.raises(po.OntologyInputError, match="public_oversight_publication_date_invalid"):
        po.load_program_ontology_graph(g)
    g = oversight_graph()
    g["public_oversight_assertions"] = [assertion(g, verification_state="proposed")]
    with pytest.raises(po.OntologyInputError, match="public_oversight_review_required"):
        po.load_program_ontology_graph(g)


def test_foreign_and_missing_programs_refuse():
    g = oversight_graph()
    g["public_oversight_assertions"] = [assertion(g, program_id="acq-program:unreviewed-foreign")]
    with pytest.raises(po.OntologyInputError, match="dangling_reference"):
        po.load_program_ontology_graph(g)
    g = oversight_graph()
    g["public_oversight_assertions"] = [assertion(g, valid_from="2010-01-01T00:00:00+00:00",
                                                  valid_to="2011-01-01T00:00:00+00:00")]
    with pytest.raises(po.OntologyInputError, match="temporal_incompatible"):
        po.load_program_ontology_graph(g)


def test_correction_succession_is_point_in_time_and_law_bound():
    g = oversight_graph()
    a = assertion(g)
    g["public_oversight_assertions"] = [a]
    corrected = assertion(g, summary="The report records the corrected cost growth observation.",
                          revision=2, predecessor_id=a["id"], succession_reason="attribute_revision",
                          known_at="2026-08-22T08:30:00+00:00")
    g["public_oversight_assertions"].append(corrected)
    rows = dossier(g)["dossiers"][0]["public_oversight"]["rows"]
    assert [r["revision"] for r in rows] == [2]
    for extra in ({"finding_kind": "schedule"}, {"revision": 5}, {"known_at": OLD},
                  {"reported_by": "quoted_program_office"}):
        payload = {"revision": 2, "predecessor_id": a["id"], "succession_reason": "attribute_revision"}
        payload.update(extra)
        bad = assertion(g, **payload)
        broken = deepcopy(g)
        broken["public_oversight_assertions"] = [a, bad]
        with pytest.raises(po.OntologyInputError, match="public_oversight_succession_invalid"):
            po.load_program_ontology_graph(broken)
    missing = assertion(g, revision=2, predecessor_id="prog-oversight:" + "f" * 24,
                        succession_reason="superseded_evidence")
    broken = deepcopy(g)
    broken["public_oversight_assertions"] = [a, missing]
    with pytest.raises(po.OntologyInputError, match="dangling_reference"):
        po.load_program_ontology_graph(broken)


def test_superseding_edition_succeeds_the_same_finding():
    g = oversight_graph()
    a = assertion(g, published_on="2026-02-10", report_edition="Interim edition")
    g["public_oversight_assertions"] = [a]
    later = assertion(g, published_on="2026-07-15", report_edition="Final revised edition",
                      report_document_id="SYN-2026-100R",
                      summary="The final report restates the cost observation.",
                      excerpt="Reported program cost grew relative to the approved baseline acquisition cost (final).",
                      revision=2, predecessor_id=a["id"], succession_reason="superseded_evidence",
                      known_at="2026-08-22T08:30:00+00:00")
    g["public_oversight_assertions"].append(later)
    schema(ONTOLOGY_V13).validate(g)
    rows = dossier(g)["dossiers"][0]["public_oversight"]["rows"]
    assert [r["report_edition"] for r in rows] == ["Final revised edition"]
    assert rows[0]["published_on"] == "2026-07-15"
    assert pd.is_valid_program_dossier_payload(dossier(g))


def test_edition_and_publication_are_metadata_not_current_state_truth():
    g = oversight_graph()
    g["public_oversight_assertions"] = [assertion(g, published_on="2024-03-15", report_edition="2024 third printing")]
    rail = dossier(g)["dossiers"][0]["public_oversight"]
    # A 2024 edition carrying 2026 review clocks is still cutoff-visible:
    # publication metadata neither expires nor defers the row, and the dossier
    # reports it verbatim instead of converting it into a validity claim.
    assert rail["state"] == "reviewed"
    assert rail["rows"][0]["published_on"] == "2024-03-15"
    assert rail["rows"][0]["report_edition"] == "2024 third printing"
    assert rail["rows"][0]["valid_from"] == OLD
    # The observation-period label is a LABEL: vague source prose is never
    # parsed into validity dates, so this row behaves like the precise one.
    g["public_oversight_assertions"] = [assertion(g, period_label="Sometime during the mid-2020s")]
    assert dossier(g)["dossiers"][0]["public_oversight"]["state"] == "reviewed"
    # Only the row's own claim clocks close it out.
    g["public_oversight_assertions"] = [assertion(g, published_on="2024-03-15",
                                                  valid_to="2026-08-22T00:00:00+00:00")]
    rail = dossier(g)["dossiers"][0]["public_oversight"]
    assert rail["rows"] == [] and rail["state"] == "not_reviewed"


def test_findings_are_cutoff_visible_only():
    g = oversight_graph()
    g["public_oversight_assertions"] = [assertion(g)]
    early = dossier(g, "2026-08-21")["dossiers"][0]["public_oversight"]
    assert early["state"] == "not_reviewed" and early["rows"] == []


def test_unreviewed_and_reviewed_none_states_are_truthful():
    g = oversight_graph()
    rail = dossier(g)["dossiers"][0]["public_oversight"]
    assert rail["state"] == "not_reviewed" and rail["rows"] == [] and rail["reviewed_at"] is None
    g["review_coverage"] = [b.review_coverage_row(scope="public_oversight", subject_type="program",
                                                  subject_id=PROGRAM)]
    schema(ONTOLOGY_V13).validate(g)
    rail = dossier(g)["dossiers"][0]["public_oversight"]
    assert rail["state"] == "reviewed_none" and rail["rows"] == []
    assert rail["reviewed_at"] == b.DEFAULT_KNOWN_AT


def test_blocked_program_reports_no_findings():
    g = oversight_graph()
    row = assertion(g)
    g["public_oversight_assertions"] = [row]
    g["overrides"] = [b.override_row(action="block", subject_type="program", subject_id=row["program_id"],
                                     evidence_refs=row["evidence_refs"])]
    rail = dossier(g)["dossiers"][0]["public_oversight"]
    assert rail["state"] == "not_reviewed" and rail["rows"] == []


def test_retired_finding_is_withheld():
    g = oversight_graph()
    a = assertion(g)
    g["public_oversight_assertions"] = [a]
    g["overrides"] = [b.override_row(action="retire_row", target_row_id=a["id"], evidence_refs=a["evidence_refs"])]
    assert dossier(g)["dossiers"][0]["public_oversight"]["rows"] == []


def test_conflicted_findings_are_suppressed_not_ranked():
    g = oversight_graph()
    a = assertion(g)
    other = assertion(g, summary="A differing account of the same cost observation.")
    g["public_oversight_assertions"] = [a, other]
    g["conflicts"] = [b.conflict_row(scope="public_oversight", subject_type="program", subject_id=PROGRAM,
                                     candidate_row_ids=[a["id"], other["id"]], reason_code="incompatible_claims",
                                     evidence_refs=a["evidence_refs"])]
    schema(ONTOLOGY_V13).validate(g)
    rail = dossier(g)["dossiers"][0]["public_oversight"]
    assert rail["state"] == "conflicted" and rail["rows"] == []


def test_conflict_rows_must_name_oversight_rows_of_that_program():
    g = oversight_graph()
    a = assertion(g)
    g["public_oversight_assertions"] = [a]
    g["conflicts"] = [b.conflict_row(scope="public_oversight", subject_type="program", subject_id=PROGRAM,
                                     candidate_row_ids=[a["id"], "prog-oversight:" + "0" * 24],
                                     reason_code="incompatible_claims", evidence_refs=a["evidence_refs"])]
    with pytest.raises(po.OntologyInputError, match="public_oversight_conflict_invalid"):
        po.load_program_ontology_graph(g)


def test_unavailable_ontology_yields_the_empty_bundle():
    out = pd.compose_program_dossier_bundle(ontology_graph=None, as_of="2026-08-22",
                                            generated_at="2026-08-22T10:00:00+00:00")
    assert out["dossiers"] == [] and out["schema_version"] == "1.0.0"
    assert pd.is_valid_program_dossier_payload(out)


def test_dossier_versions_stay_compatible_across_the_whole_ladder():
    # 1.3 ontology -> 1.2.0 dossier with BOTH rails populated.
    g = oversight_graph()
    g["public_capacity_assertions"] = [capacity_claim(g)]
    g["public_oversight_assertions"] = [assertion(g)]
    out = dossier(g)
    assert out["schema_version"] == "1.2.0"
    assert pd.is_valid_program_dossier_payload(out)
    assert out["dossiers"][0]["public_capacity"]["state"] == "reviewed"
    assert out["dossiers"][0]["public_oversight"]["state"] == "reviewed"
    # 1.2 ontology -> 1.1.0 dossier: capacity preserved, no oversight rail.
    g = oversight_graph()
    g["schema_version"] = "1.2.0"
    del g["public_oversight_assertions"]
    del g["evidence"][1]
    g["public_capacity_assertions"] = [capacity_claim(g)]
    out = dossier(g)
    assert out["schema_version"] == "1.1.0"
    assert pd.is_valid_program_dossier_payload(out)
    assert "public_oversight" not in out["dossiers"][0]
    # 1.0/1.1 ontologies -> 1.0.0 dossier with neither rail.
    for version in ("1.0.0", "1.1.0"):
        g = oversight_graph()
        g["schema_version"] = version
        del g["public_oversight_assertions"]
        del g["public_capacity_assertions"]
        del g["evidence"][1:3]
        out = dossier(g)
        assert out["schema_version"] == "1.0.0"
        assert pd.is_valid_program_dossier_payload(out)
        assert "public_capacity" not in out["dossiers"][0]
        assert "public_oversight" not in out["dossiers"][0]


@pytest.mark.parametrize("mutation", ["future_known", "future_effective", "expired", "false_reviewed",
                                      "duplicate", "wrong_program", "excerpt_edit", "unknown_row_field"])
def test_dossier_consumer_refuses_internal_oversight_forgery(mutation):
    g = oversight_graph()
    g["public_oversight_assertions"] = [assertion(g)]
    out = dossier(g)
    rail = out["dossiers"][0]["public_oversight"]
    row = rail["rows"][0]
    if mutation == "future_known":
        row["known_at"] = FUTURE
    elif mutation == "future_effective":
        row["valid_from"] = "2026-09-01T00:00:00+00:00"
    elif mutation == "expired":
        row["valid_to"] = "2026-08-22T00:00:00+00:00"
    elif mutation == "false_reviewed":
        rail["rows"] = []
    elif mutation == "duplicate":
        rail["rows"].append(deepcopy(row))
    elif mutation == "wrong_program":
        row["program_id"] = "acq-program:other"
    elif mutation == "excerpt_edit":
        row["excerpt"] = row["excerpt"].replace("grew", "shrank")
    else:
        row["readiness_assessment"] = "high"
    out["content_id"] = pd.dossier_content_id(out)
    assert not pd.is_valid_program_dossier_payload(out)


def test_rehashing_alone_cannot_legitimize_an_edited_row():
    g = oversight_graph()
    g["public_oversight_assertions"] = [assertion(g)]
    out = dossier(g)
    out["dossiers"][0]["public_oversight"]["rows"][0]["page"] = 99
    assert not pd.is_valid_program_dossier_payload(out)


def test_curator_explicit_migration_and_idempotent_reimport(tmp_path):
    g = oversight_graph()
    row = assertion(g)
    report_ev = g["evidence"][1]
    g["schema_version"] = "1.2.0"
    del g["public_oversight_assertions"]
    del g["evidence"][1]
    target = tmp_path / "program_ontology.json"
    target.write_text(json.dumps(g))
    worksheet = b.worksheet(
        coverage=[{"scope": "public_oversight", "subject_type": "program", "subject_id": PROGRAM}],
        rows=[{"action": "admit", "target_kind": "evidence", "candidate_row": report_ev},
              {"action": "admit", "target_kind": "public_oversight_assertion", "candidate_row": row}])
    source = tmp_path / "worksheet.json"
    source.write_text(json.dumps(worksheet))
    report = curator.curate_worksheet(source, target_path=target, schema_version="1.3.0")
    assert report["rejected_count"] == 0
    assert report["coverage_rows_minted"] == 1
    before = target.read_bytes()
    curator.curate_worksheet(source, target_path=target)
    assert target.read_bytes() == before
    stored = json.loads(before)
    assert len(stored["public_oversight_assertions"]) == 1
    assert stored["schema_version"] == "1.3.0"
    assert load(stored)["schema_version"] == "1.3.0"


def test_curator_refuses_oversight_rows_without_the_explicit_migration(tmp_path):
    g = oversight_graph()
    row = assertion(g)
    g["schema_version"] = "1.2.0"
    del g["public_oversight_assertions"]
    del g["evidence"][1]
    target = tmp_path / "program_ontology.json"
    target.write_text(json.dumps(g))
    worksheet = b.worksheet(rows=[{"action": "admit", "target_kind": "public_oversight_assertion",
                                   "candidate_row": row}])
    source = tmp_path / "worksheet.json"
    source.write_text(json.dumps(worksheet))
    report = curator.curate_worksheet(source, target_path=target)
    assert report["rejected_count"] == 1
    assert report["rejected"][0]["reason"] == "public_oversight_schema_migration_required"
    assert json.loads(target.read_text())["schema_version"] == "1.2.0"


def test_curator_refuses_downgrade_from_1_3(tmp_path):
    g = oversight_graph()
    target = tmp_path / "program_ontology.json"
    target.write_text(json.dumps(g))
    worksheet = b.worksheet(coverage=[{"scope": "public_oversight", "subject_type": "program",
                                       "subject_id": PROGRAM}])
    source = tmp_path / "worksheet.json"
    source.write_text(json.dumps(worksheet))
    curator.curate_worksheet(source, target_path=target)
    assert json.loads(target.read_text())["schema_version"] == "1.3.0"
    with pytest.raises(curator.CurateError, match="downgrade refused"):
        curator.curate_worksheet(source, target_path=target, schema_version="1.2.0")
    assert json.loads(target.read_text())["schema_version"] == "1.3.0"


def test_curator_preserves_capacity_admission_after_oversight_migration(tmp_path):
    g = oversight_graph()
    target = tmp_path / "program_ontology.json"
    target.write_text(json.dumps(g))
    row = capacity_claim(g)
    worksheet = b.worksheet(
        coverage=[{"scope": "public_capacity", "subject_type": "program", "subject_id": PROGRAM}],
        rows=[{"action": "admit", "target_kind": "public_capacity_assertion", "candidate_row": row}])
    source = tmp_path / "worksheet.json"
    source.write_text(json.dumps(worksheet))
    report = curator.curate_worksheet(source, target_path=target)
    assert report["rejected_count"] == 0
    stored = json.loads(target.read_text())
    assert stored["public_capacity_assertions"] == [row]
    out = dossier(stored)
    assert pd.is_valid_program_dossier_payload(out)
    assert out["dossiers"][0]["public_capacity"]["state"] == "reviewed"


@pytest.mark.parametrize("published_on", ["2026-08-23", "2030-01-01"])
def test_publication_cannot_postdate_claim_knowledge_even_with_valid_hashes(published_on):
    g=oversight_graph();g["public_oversight_assertions"]=[assertion(g,published_on=published_on)]
    with pytest.raises(po.OntologyInputError,match="public_oversight_publication_after_known"):
        load(g)


@pytest.mark.parametrize("published_on", ["2026-08-23", "2030-01-01"])
def test_dossier_rejects_future_publication_after_rehash(published_on):
    g=oversight_graph();g["public_oversight_assertions"]=[assertion(g)];out=dossier(g)
    row=out["dossiers"][0]["public_oversight"]["rows"][0];row["published_on"]=published_on
    row["id"]=po.public_oversight_assertion_id(row);out["content_id"]=pd.dossier_content_id(out)
    assert not pd.is_valid_program_dossier_payload(out)
