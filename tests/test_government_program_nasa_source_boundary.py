"""Ontology 1.4 admits one exact NASA OIG origin for acquisition-report evidence.

The 1.4.0 special case admits only the exact https://oig.nasa.gov origin, only
for evidence_class official_acquisition_report, only with a nonempty
claim_scopes subset of program_identity/public_oversight, and only when
source_url equals retrieved_from_url. Every legacy version keeps the publisher
gate closed, the global allowlist is unchanged, and the existing capacity and
oversight rails keep composing. All fixtures are synthetic.
"""
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker, ValidationError

from engine.government_revenue import program_ontology as po
from engine.government_revenue import program_dossier as pd
from scripts import curate_government_program_ontology as curator
from tests.fixtures.government_program_ontology import builders as b

ROOT = Path(__file__).resolve().parents[1]
OLD = "2020-01-01T00:00:00+00:00"
PROGRAM = "acq-program:example"
NASA_HOST = "https://oig.nasa.gov"
REPORT_PATH = "/reports/synthetic-acquisition-report"
NASA_URL = NASA_HOST + REPORT_PATH
CRS_URL = "https://crsreports.congress.gov/product/synthetic-overview"
ARMY_URL = "https://www.army.mil/article/291670"
ONTOLOGY_V13 = "government_program_ontology.v1_3.schema.json"
ONTOLOGY_V14 = "government_program_ontology.v1_4.schema.json"
DOSSIER_V12 = "government_program_dossier.v1_2.schema.json"


def graph(version="1.4.0", **changes):
    g = b.empty_graph()
    g["schema_version"] = version
    if version in ("1.2.0", "1.3.0", "1.4.0"):
        g["public_capacity_assertions"] = []
    if version in ("1.3.0", "1.4.0"):
        g["public_oversight_assertions"] = []
    row = b.evidence_row("nasa-source", claim_scopes=["program_identity"],
                         evidence_class="official_acquisition_report",
                         source_url=NASA_URL, retrieved_from_url=NASA_URL)
    row.update(changes)
    g["evidence"] = [row]
    return g


def load(g):
    return po.load_program_ontology_graph(g)


def schema(name):
    return Draft202012Validator(
        json.loads((ROOT / "contracts/government_revenue" / name).read_text()),
        format_checker=FormatChecker())


def rail_graph():
    result = b.empty_graph()
    result["schema_version"] = "1.4.0"
    identity = b.evidence_row("identity", claim_scopes=["program_identity"],
                              known_at=OLD, retrieved_at=OLD)
    report = b.evidence_row("report", claim_scopes=["program_identity", "public_oversight"],
                            evidence_class="official_acquisition_report",
                            source_url=NASA_URL, retrieved_from_url=NASA_URL)
    capacity = b.evidence_row("capacity", claim_scopes=["program_identity", "public_capacity"])
    result["evidence"] = [identity, report, capacity]
    result["programs"] = [b.program_row(known_at=OLD, evidence_refs=[identity["evidence_id"]])]
    result["public_capacity_assertions"] = []
    result["public_oversight_assertions"] = []
    return result


def oversight_refs(g):
    return [e["evidence_id"] for e in g["evidence"] if "public_oversight" in e.get("claim_scopes", [])]


def assertion(g, **changes):
    row = dict(revision=1, program_id=PROGRAM, finding_kind="cost", reported_by="oversight_body",
               report_series="Synthetic Oversight Series", report_document_id="SYN-2026-100",
               report_edition="First edition", published_on="2026-07-15",
               period_label="Fiscal year 2026 site observations",
               summary="The report records a cost growth observation against the program baseline.",
               excerpt="Reported program cost grew relative to the approved baseline acquisition cost.",
               page=14, printed_page_label="Page 14", known_at=b.DEFAULT_KNOWN_AT,
               valid_from=OLD, valid_to=None, verification_state="reviewed",
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
               period_label="Target within seven years", known_at=b.DEFAULT_KNOWN_AT,
               valid_from=OLD, valid_to=None, verification_state="reviewed",
               evidence_refs=[refs[0]], predecessor_id=None, succession_reason=None)
    row.update(changes)
    row["id"] = po.public_capacity_assertion_id(row)
    return row


def dossier(g, as_of="2026-08-22"):
    return pd.compose_program_dossier_bundle(ontology_graph=load(g), as_of=as_of,
                                             generated_at="2026-08-22T10:00:00+00:00")


@pytest.mark.parametrize("scopes", [["program_identity"], ["public_oversight"],
                                    ["program_identity", "public_oversight"]])
def test_new_version_admits_exact_origin_for_each_scope_subset(scopes):
    candidate = graph(claim_scopes=scopes)
    loaded = load(candidate)
    assert loaded["evidence"] == candidate["evidence"]


def test_new_shape_is_valid_under_the_new_schema():
    schema(ONTOLOGY_V14).validate(graph())


@pytest.mark.parametrize("version", ["1.0.0", "1.1.0", "1.2.0", "1.3.0"])
def test_legacy_versions_keep_nasa_oig_refused(version):
    with pytest.raises(po.OntologyInputError, match="publisher_host_refused"):
        load(graph(version))


@pytest.mark.parametrize("url", [
    f"http://oig.nasa.gov{REPORT_PATH}", f"https://user:password@oig.nasa.gov{REPORT_PATH}",
    f"https://oig.nasa.gov.evil.example{REPORT_PATH}", f"https://nasa.gov{REPORT_PATH}",
    f"https://www.nasa.gov{REPORT_PATH}", f"https://www.oig.nasa.gov{REPORT_PATH}",
    f"https://oig.nasa.gov:8443{REPORT_PATH}", f"HTTPS://OIG.NASA.GOV{REPORT_PATH}",
    f"https://oig.nasa.gov.{REPORT_PATH}", f" https://oig.nasa.gov{REPORT_PATH}",
    "https://[invalid/",
    "https://oi\tg.nasa.gov/reports/synthetic-acquisition-report",
    "https://oi\ng.nasa.gov/reports/synthetic-acquisition-report",
    f"https://oig.nasa.gov{REPORT_PATH}\x00", f"https://oig.nasa.gov{REPORT_PATH}\x7f",
    "https://oig.nasa.gov/reports/syn thetic-acquisition-report",
])
def test_noncanonical_origin_refuses(url):
    with pytest.raises(po.OntologyInputError, match="publisher_host_refused"):
        load(graph(source_url=url, retrieved_from_url=url))


@pytest.mark.parametrize("retrieved", [NASA_URL + "#other",
    f"https://www.nasa.gov{REPORT_PATH}", f"{NASA_HOST}/reports/other-synthetic-report"])
def test_retrieval_url_must_equal_the_source_url(retrieved):
    with pytest.raises(po.OntologyInputError, match="publisher_host_refused"):
        load(graph(retrieved_from_url=retrieved))


@pytest.mark.parametrize("evidence_class", ["official_program_page",
    "official_contract_announcement", "congressional_research", "official_alliance_policy"])
def test_origin_is_class_specific(evidence_class):
    with pytest.raises(po.OntologyInputError, match="publisher_host_refused"):
        load(graph(evidence_class=evidence_class))


@pytest.mark.parametrize("scopes", [["role"], ["public_capacity"], ["policy_context"],
    ["participants"], ["program_identity", "public_capacity"], ["public_oversight", "role"]])
def test_outside_scope_subset_refuses_without_crashing(scopes):
    with pytest.raises(po.OntologyInputError) as exc:
        load(graph(claim_scopes=scopes))
    assert "publisher_host_refused" in exc.value.errors
    assert ("ontology_row_shape_invalid" in exc.value.errors) == ("participants" in scopes)


@pytest.mark.parametrize("changes,expected", [({"claim_scopes": []}, "publisher_host_refused"),
    ({"claim_scopes": "program_identity"}, "ontology_row_shape_invalid"),
    ({"claim_scopes": [["program_identity"]]}, "ontology_row_shape_invalid")])
def test_empty_or_malformed_scopes_refuse(changes, expected):
    with pytest.raises(po.OntologyInputError, match=expected):
        load(graph(**changes))


def test_official_nasa_source_cannot_carry_an_issuer_pin():
    with pytest.raises(po.OntologyInputError, match="ontology_row_shape_invalid"):
        load(graph(pinned_issuer_host="oig.nasa.gov", pinned_issuer_host_basis="Not an issuer"))


def test_global_publisher_allowlist_is_not_expanded_by_the_new_origin():
    assert "oig.nasa.gov" not in po.PUBLISHER_HOST_ALLOWLIST
    assert "nasa.gov" not in po.PUBLISHER_HOST_ALLOWLIST
    assert "www.nasa.gov" not in po.PUBLISHER_HOST_ALLOWLIST


def test_existing_approved_publisher_still_admits_in_new_version():
    candidate = graph(claim_scopes=["program_identity", "public_capacity"],
                      evidence_class="official_contract_announcement",
                      source_url=ARMY_URL, retrieved_from_url=ARMY_URL)
    loaded = load(candidate)
    assert loaded["evidence"] == candidate["evidence"]


def test_new_version_composes_native_dossier_with_both_rails():
    g = rail_graph()
    g["public_oversight_assertions"] = [assertion(g)]
    g["public_capacity_assertions"] = [capacity_claim(g)]
    schema(ONTOLOGY_V14).validate(g)
    out = dossier(g)
    assert out["schema_version"] == "1.2.0"
    schema(DOSSIER_V12).validate(out)
    assert pd.is_valid_program_dossier_payload(out)
    rails = out["dossiers"][0]
    assert rails["public_oversight"]["state"] == "reviewed"
    assert rails["public_capacity"]["state"] == "reviewed"
    assert len(rails["public_oversight"]["rows"]) == 1
    assert len(rails["public_capacity"]["announced_target"]) == 1


def test_prior_version_capacity_and_oversight_rails_remain_supported_in_new_version():
    g = rail_graph()
    report = g["evidence"][1]
    report["evidence_class"] = "congressional_research"
    report["source_url"] = CRS_URL
    report["retrieved_from_url"] = CRS_URL
    g["public_oversight_assertions"] = [assertion(g)]
    g["public_capacity_assertions"] = [capacity_claim(g)]
    loaded = load(g)
    assert len(loaded["public_oversight_assertions"]) == 1
    assert len(loaded["public_capacity_assertions"]) == 1


def test_previous_ontology_schema_rejects_the_new_version():
    with pytest.raises(ValidationError):
        schema(ONTOLOGY_V13).validate(graph())


def test_curator_migrates_1_3_graph_to_1_4_and_refuses_downgrade(tmp_path):
    source = tmp_path / "worksheet.json"
    source.write_text(json.dumps(b.worksheet()), encoding="utf-8")
    target = tmp_path / "program_ontology.json"
    base = b.empty_graph()
    base.update(schema_version="1.3.0", public_capacity_assertions=[], public_oversight_assertions=[])
    target.write_text(json.dumps(base), encoding="utf-8")
    report = curator.curate_worksheet(source, target_path=target, schema_version="1.4.0")
    assert report["written"] is True
    assert json.loads(target.read_text(encoding="utf-8"))["schema_version"] == "1.4.0"
    with pytest.raises(curator.CurateError, match="downgrade"):
        curator.curate_worksheet(source, target_path=target, schema_version="1.3.0")
