"""M1 source-native curator readiness composes existing research and Data OS hints.

All names, source clocks and legal issuers are research-only. This suite never
writes a graph edge, group, legal identity, money path or provider source.
"""
from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from engine.theme_graph.membership_evidence import (
    build_microtheme_curator_readiness,
    build_microtheme_identity_preflight,
    render_microtheme_curator_readiness_markdown,
)

ROOT = Path(__file__).resolve().parents[1]
ORIGINAL = ROOT / "research/theme_graph/microtheme_membership_candidates_2026-10-08.json"
ADDENDUM = ROOT / "research/theme_graph/micro_member_research_addendum_20261016/research_addendum.json"
CLI = ROOT / "scripts/explain_theme_overlap.py"


@pytest.fixture(scope="module")
def real_docs():
    return json.loads(ORIGINAL.read_text()), json.loads(ADDENDUM.read_text())


@pytest.fixture
def docs(real_docs):
    return copy.deepcopy(real_docs)


@pytest.fixture
def dataos_reference_rows():
    issuer_rows = [
        {"issuer_id": "ISS:US-XNAS-MU", "legal_name": "Micron Technology Inc", "status": "active"},
        {"issuer_id": "ISS:US-XNAS-ASML", "legal_name": "ASML HOLDING NV", "status": "active"},
        {"issuer_id": "ISS:US-XNYS-PL", "legal_name": "Planet Labs PBC", "status": "active"},
        {"issuer_id": "ISS:US-XNYS-PLNT", "legal_name": "Planet Fitness Inc", "status": "active"},
        {"issuer_id": "ISS:US-XNYS-CPT", "legal_name": "Camden Property Trust", "status": "active"},
        {"issuer_id": "ISS:US-XNAS-NONAME", "legal_name": None, "status": "active"},
        {"issuer_id": "ISS:US-XNYS-DEAD", "legal_name": "No longer current", "status": "retired"},
    ]
    securities = [
        {"security_id": i["issuer_id"].replace("ISS:", "SEC:"),
         "issuer_id": i["issuer_id"],
         "security_state": None,
         "issuer_state": "RESOLVED",
         "listing_key": i["issuer_id"].removeprefix("ISS:")}
        for i in issuer_rows if i["status"] == "active"
    ]
    return issuer_rows, securities


def review(docs, refs, **kwargs):
    return build_microtheme_curator_readiness(
        docs[0], docs[1],
        issuer_rows=refs[0], security_rows=refs[1],
        issuer_snapshot_sha256="a" * 64,
        security_snapshot_sha256="b" * 64,
        **kwargs,
    )


def test_curator_readiness_all_149_and_sources(docs, dataos_reference_rows):
    out = review(docs, dataos_reference_rows)
    c = out["counts"]
    assert out["schema"] == "gmi.microtheme_curator_readiness/v1"
    assert out["availability"] == "CURRENT_SOURCE_TRIAGE_ONLY_NO_ADMISSION"
    assert out["authority_ceiling"] == "research_internal_only"
    assert (c["original_activity_records"], c["additional_research_activity_records"],
            c["total_research_activity_records"], c["micro_definitions"]) == (103, 46, 149, 68)
    assert (c["separate_source_references"], c["distinct_source_urls"],
            c["distinct_urls_linked_to_candidate_roles"]) == (158, 157, 139)
    assert (c["research_records_missing_any_publisher_date"],
            c["research_records_missing_publication_day"],
            c["year_only_publisher_date_records"]) == (91, 99, 8)
    assert sum(c["current_identity_name_hint_states"].values()) == 149
    assert c["identity_qualified_memberships"] == c["exact_groups_admitted"] == 0
    assert c["graph_edges_admitted"] == c["measurement_cohorts_admitted"] == 0
    assert len(out["candidate_worklist"]) == 149
    assert len(out["micro_readiness"]) == 68
    assert sum(x["original_research_roles"] for x in out["micro_readiness"]) == 103
    assert sum(x["additional_unadmitted_roles"] for x in out["micro_readiness"]) == 46
    assert sum(out["stage_claim_counts"].values()) == 149
    assert out["reference"]["current_issuer_rows_without_legal_name"] == 1
    assert set(out["reference"]["covered_country_codes"]) == set()


def test_curator_reuses_exact_original_dataos_identity_names(docs, dataos_reference_rows):
    current = build_microtheme_identity_preflight(
        docs[0], issuer_rows=dataos_reference_rows[0],
        security_rows=dataos_reference_rows[1],
        issuer_snapshot_sha256="a" * 64, security_snapshot_sha256="b" * 64)
    combined = review(docs, dataos_reference_rows)
    initial = {
        r["record_id"]: r for r in combined["candidate_worklist"]
        if r["origin_kind"] == "INITIAL_RESEARCH_UNADMITTED"
    }
    for r in current["candidate_diagnostics"]:
        row = initial[r["record_id"]]
        assert row["current_name_hint_state"] == r["identity_hint_state"]
        assert row["possible_current_issuer_refs"] == r["possible_current_issuer_refs"]


def test_curator_planet_ambiguity_and_amd_not_camden(docs, dataos_reference_rows):
    out = review(docs, dataos_reference_rows)
    by_key = {r["record_id"]: r for r in out["candidate_worklist"]}
    assert by_key["M073"]["current_name_hint_state"] == "AMBIGUOUS_NAME_PREFIX"
    assert {x["issuer_id"] for x in by_key["M073"]["possible_current_issuer_refs"]} == {
        "ISS:US-XNYS-PL", "ISS:US-XNYS-PLNT"}
    assert by_key["M008"]["current_name_hint_state"] == "NO_NAME_PREFIX_IN_REFERENCE"
    assert by_key["M001"]["current_name_hint_state"] == "POSSIBLE_ONE_CURRENT_ISSUER"
    assert by_key["M001"]["dataos_legal_entity_qualification"] == "NOT_PERFORMED"


def test_curator_unadmitted_all_records_even_when_name_unique(docs, dataos_reference_rows):
    out = review(docs, dataos_reference_rows)
    for r in out["candidate_worklist"]:
        assert r["human_product_role_adjudication"] == "NOT_PERFORMED"
        assert r["source_use_qualification"] == r["source_authentication"] == "NOT_PERFORMED"
        assert r["dataos_legal_entity_qualification"] == "NOT_PERFORMED"
        assert not r["exact_group_qualified"] and not r["graph_membership_admitted"]
        assert not any(r[x] for x in ("measurement_eligible", "rank_eligible",
                                     "signal_eligible", "sizing_eligible", "trading_eligible"))
        assert r["known_at"] is None and r["effective_at"] is None
        assert r["next_source_owner_actions"][-1] == "OBTAIN_GMI_OWNER_RATIFICATION_BEFORE_GRAPH_EDGE"
        assert all(v["original_source_authenticated"] is False
                   and v["public_use_rights_qualified"] is False for v in r["sources"])


@pytest.mark.parametrize("mutation", [
    lambda d: d[0]["candidates"][0].__setitem__("canonical_security_id","SEC:FAKE"),
    lambda d: d[0]["population"].__setitem__("complete_global_membership", True),
    lambda d: d[1]["authority"].__setitem__("trading", True),
    lambda d: d[1]["proposed_activity_roles"][0].__setitem__("measurement_eligible", True),
    lambda d: d[1]["proposed_activity_roles"][0].__setitem__("canonical_entity_id", "co:us:FAKE"),
    lambda d: d[1]["sources"][next(iter(d[1]["sources"]))].__setitem__("source_use_qualification", "PUBLIC_REDIS"),
    lambda d: d[1]["population"].__setitem__("additional_activity_proposals", 45),
])
def test_curator_refuses_forged_source_authority(docs, dataos_reference_rows, mutation):
    mutation(docs)
    with pytest.raises((ValueError, TypeError), match="microtheme research refused"):
        review(docs, dataos_reference_rows)


def test_curator_refuses_bad_dataos_source(docs, dataos_reference_rows):
    dataos_reference_rows[0].append(copy.deepcopy(dataos_reference_rows[0][0]))
    with pytest.raises(ValueError, match="microtheme research refused"):
        review(docs, dataos_reference_rows)


def test_curator_refuses_tampered_tsv_without_side_effects(docs, dataos_reference_rows, tmp_path):
    inputs = ROOT / "research/theme_graph/micro_member_research_addendum_20261016"
    for filename in ("intake.tsv", "negative_intake.tsv", "scope_holds.tsv"):
        (tmp_path / filename).write_bytes((inputs / filename).read_bytes())
    (tmp_path / "intake.tsv").write_text(
        (tmp_path / "intake.tsv").read_text().replace("MKS Instruments","fake",1))
    with pytest.raises(ValueError, match="research intake bytes differ"):
        review(docs, dataos_reference_rows, intake_dir=tmp_path)


def test_curator_render_escape_no_rankings_and_input_unchanged(docs, dataos_reference_rows):
    before = json.dumps(docs, sort_keys=True)
    v = review(docs, dataos_reference_rows)
    v["candidate_worklist"][0]["entity_name"] = "new|<unsafe>"
    assert json.dumps(docs, sort_keys=True) == before
    md = render_microtheme_curator_readiness_markdown(v)
    assert "new&#124;&lt;unsafe&gt;" in md
    assert "NOTHING ADMITTED" in md
    assert "Missing day-level proof: 99 roles" in md
    assert "At least one linked source lacks a publisher date: 91 roles" in md


def test_cli_curator_readiness_with_actual_bounded_parquet_fixtures(docs, dataos_reference_rows, tmp_path):
    pa = pytest.importorskip("pyarrow")
    pq = pytest.importorskip("pyarrow.parquet")
    issuer = tmp_path / "issuer.parquet"
    security = tmp_path / "security.parquet"
    pq.write_table(pa.Table.from_pylist(dataos_reference_rows[0]), issuer)
    pq.write_table(pa.Table.from_pylist(dataos_reference_rows[1]), security)
    proc = subprocess.run([
        sys.executable, str(CLI), "--microtheme-research", str(ORIGINAL),
        "--microtheme-addendum", str(ADDENDUM),
        "--issuer-reference", str(issuer), "--security-reference", str(security),
        "--curator-readiness", "--format", "json",
    ], cwd=ROOT, text=True, capture_output=True, check=False)
    assert proc.returncode == 0, proc.stderr
    v = json.loads(proc.stdout)
    assert v["counts"]["total_research_activity_records"] == 149
    assert v["counts"]["graph_edges_admitted"] == 0


@pytest.mark.parametrize("args", [
    ["--microtheme-research", str(ORIGINAL), "--curator-readiness"],
    ["--microtheme-research", str(ORIGINAL), "--microtheme-addendum", str(ADDENDUM),
     "--curator-readiness"],
    ["--review", str(ORIGINAL), "--curator-readiness"],
    ["--microtheme-research", str(ORIGINAL), "--microtheme-addendum", str(ADDENDUM),
     "--issuer-reference", "a", "--security-reference", "b"],
])
def test_cli_curator_requirements_explicit_and_old_mixed_modes_still_refused(args):
    p = subprocess.run([sys.executable, str(CLI), *args],
                       cwd=ROOT, text=True, capture_output=True, check=False)
    assert p.returncode == 2
    assert json.loads(p.stderr)["ok"] is False
