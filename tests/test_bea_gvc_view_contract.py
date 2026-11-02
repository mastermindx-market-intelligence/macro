"""The human component is a projection of the existing NONPUBLIC owner contract.

No provider files, source admission, browser-token handling or public dataset.
Node runs the shipped JS, not a test reimplementation of its behavior.
"""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import shutil
import subprocess

import pytest
import yaml

from engine.market_ontology import bea_gvc_current as owner
from tests.test_bea_gvc_current_descriptive import check, fake_rows

ROOT = Path(__file__).resolve().parents[1]
JS = ROOT / "app/gmi_bea_view.js"


def run_js(expression: str, value=None):
    node = shutil.which("node")
    assert node, "Node is required to verify the shipped browser contract; do not silently skip"
    program = (
        "const v=require(" + json.dumps(str(JS)) + ");"
        "let raw='';process.stdin.on('data',x=>raw+=x);"
        "process.stdin.on('end',()=>{const input=JSON.parse(raw);"
        "console.log(JSON.stringify(" + expression + "));});"
    )
    result = subprocess.run([node, "-e", program], input=json.dumps(value),
                            text=True, capture_output=True, check=True, timeout=15)
    return json.loads(result.stdout)


def test_client_schema_and_vocabulary_are_exact_owner_projections():
    values = run_js("({contract:v.CONTRACT,reasons:Object.keys(v.REASONS).sort(),"
                    "candidate:v.CANDIDATE_FIELDS,unavailable:v.UNAVAILABLE_FIELDS,amounts:v.AMOUNTS})")
    c = values["contract"]
    assert c == {
        "schema": owner.SCHEMA, "edition": owner.EDITION_DATE,
        "years": list(owner.YEARS), "regions": list(owner.REGIONS),
        "candidateStatus": "CANDIDATE_NOT_PUBLISHED", "unavailableStatus": "UNAVAILABLE",
        "authority": owner.AUTHORITY, "numberKind": "integer_usd_millions",
        "maxInteger": owner.MAX_JSON_SAFE_INTEGER, "commoditiesPerYear": owner.COMMODITIES_PER_YEAR,
    }
    assert values["reasons"] == sorted(owner._UNAVAILABLE_REASONS)
    assert set(values["candidate"]) == owner._CANDIDATE_FIELDS
    assert set(values["unavailable"]) == owner._UNAVAILABLE_FIELDS
    assert tuple(values["amounts"]) == owner._ANNUAL_AMOUNT_FIELDS
    assert "PUBLISHED_CURRENT_DESCRIPTIVE" not in JS.read_text()


def test_shipped_js_accepts_real_candidate_only_as_unpublished_preview():
    packet = check()
    owner.candidate_packet_bytes(packet)
    assert run_js("v.validateCandidate(input)", packet) is True
    for change in (
        {"status": "PUBLISHED_CURRENT_DESCRIPTIVE", "may_publish": True},
        {"may_trade": True}, {"historical_pit_eligible": True},
        {"owner_digest_is_not_authenticated_here": False},
        {"dataos_native_admitted": True}, {"unknown_field": "hidden"},
        {"industry_code_exact": 5241},
    ):
        assert run_js("v.validateCandidate(input)", {**packet, **change}) is False
    result = run_js("v.failure(200,input,'5241X')", packet)
    assert result["reason"] == "CANDIDATE_NOT_PUBLISHED"
    assert "not" in result["title"].lower()


def test_source_integer_units_are_deliberate_not_silent_fractional_rounding():
    rows = fake_rows()
    rows[0]["world_import_million_USD"] = 0.5
    assert check(rows=rows)["reason"] == "SOURCE_AMOUNTS_INVALID"
    packet = check()
    packet["annual_descriptive"][0]["world_import_million_USD"] = 0.5
    assert run_js("v.validateCandidate(input)", packet) is False


def test_js_retains_zero_and_signed_geometry_without_absolute_value_disguise():
    result = run_js("input.map(n=>v.scale(input,48)(n))", [0, -10, 20])
    assert result == [0, 24, 48]
    packet = check()
    bad = deepcopy(packet)
    bad["annual_descriptive"][1]["year_over_year_change_million_USD"]["world_import_million_USD"] = True
    assert run_js("v.validateCandidate(input)", bad) is False
    bad = deepcopy(packet)
    bad["annual_descriptive"][0]["world_import_million_USD"] = 2 ** 53
    assert run_js("v.validateCandidate(input)", bad) is False


@pytest.mark.parametrize("code,expected", [
    ("5241X", "5241X"), ("5241x", "5241x"), ("I001", "I001"),
    ("5241X%2F..%2F..%2Fetc", None), ("%2e%2e%2fsecret", None),
    ("bad%00code", None), ("5241X%0A", None), ("5241X%0D", None), ("%E0%A4%A", None), ("a" * 33, None),
])
def test_path_parser_splits_before_decoding_exact_source_segment(code, expected):
    assert run_js("v.sourceCode(input)", "/api/gmi/bea/industry/" + code + "/view") == expected


def test_all_owner_refusals_have_specific_explanations_and_no_data():
    packets = [owner._unavailable(reason, "5241X") for reason in owner._UNAVAILABLE_REASONS]
    outputs = run_js("input.map(p=>({valid:v.unavailable(p,'5241X'),...v.failure(503,p,'5241X')}))", packets)
    assert all(result["valid"] for result in outputs)
    assert {r["reason"] for r in outputs} == owner._UNAVAILABLE_REASONS
    assert all(r["title"] and r["message"] for r in outputs)
    forged = owner._unavailable("SOURCE_NOT_PRODUCED", "5241X")
    forged["annual_descriptive"] = [{"world_import_million_USD": 123}]
    assert run_js("v.unavailable(input,'5241X')", forged) is False
    assert run_js("v.failure(503,input,'OTHER')", owner._unavailable("SOURCE_NOT_PRODUCED", "5241X"))["reason"] == "RESPONSE_CONTRACT_MISMATCH"


def test_client_errors_do_not_masquerade_as_connection_outages():
    assert run_js("v.failure(422,null,'5241X')")["reason"] == "INVALID_REQUEST"
    assert run_js("v.failure(502,null,'5241X')")["reason"] == "SERVICE_ERROR"
    assert run_js("v.failure(503,input,'5241X')", {"detail": {"error": "BEA_SOURCE_REGISTRY_UNAVAILABLE"}})["reason"] == "BEA_SOURCE_REGISTRY_UNAVAILABLE"
    assert run_js("v.failure(401,null,'5241X')")["reason"] == "AUTHENTICATION_REQUIRED"


def test_edited_browser_and_http_tests_are_in_the_required_pr_code_gate():
    manifest = yaml.safe_load((ROOT / ".github/ci/legacy-jobs.yml").read_text())
    job = manifest["jobs"]["bea-gvc-current-descriptive-consumer"]
    assert job["gate"] == "code"
    commands = "\n".join(str(step.get("run", "")) for step in job["steps"])
    for test in ("test_bea_gvc_current_descriptive.py", "test_bea_gvc_view_contract.py",
                 "test_bea_gvc_browser.py", "test_api_paywall.py", "test_api_no_store.py"):
        assert "tests/" + test in commands
    for path in ("app/main.py", "app/gmi_bea_view.html", "app/gmi_bea_view.css", "app/gmi_bea_view.js"):
        assert path in job["paths"]
    assert "playwright install --with-deps chromium" in commands


def test_owner_serializer_rejects_boolean_yearly_delta_even_when_equal_to_zero():
    packet = check()
    packet["annual_descriptive"][1]["year_over_year_change_million_USD"]["world_import_million_USD"] = False
    with pytest.raises(owner.BEADescriptiveRefused, match="YEARLY_CHANGE"):
        owner.candidate_packet_bytes(packet)


def test_unpublished_candidate_metadata_has_exact_not_permissive_end_anchors():
    packet = check()
    for change in ({"source_generation_id": "a" * 64 + "\n"},
                   {"industry_code_exact": "5241X\n"},
                   {"native_ingested_at": "2026-10-10T13:47:00Z\n"},
                   {"native_ingested_at": "2015-01-01T00:00:00Z"},
                   {"native_ingested_at": "2099-01-01T00:00:00Z"},
                   {"legacy_mapping_state": "APPROVED_CROSSWALK"},
                   {"attribution": "Some other publisher"}):
        assert run_js("v.validateCandidate(input)", {**packet, **change}) is False


def test_full_checkout_source_dependencies_are_not_lost_in_sparse_curation():
    """Hosted CI 39082707115 found real app-route dependencies absent locally.

    Check the declared path identities, not their sparse filesystem presence.
    Reading any provider source or the generated file contents is unnecessary.
    A local sparse pass must not erase these full-checkout integration facts.
    """
    hosted_dependencies = (
        'site/basketdata/baskets.json',
        'site/basketdata/fear_greed.json',
        'site/basketdata/foresight_cascade.json',
        'site/basketdata/narrative_emergence.json',
        'site/basketdata/radar.json',
        'site/basketdata/radar_enriched.json',
        'site/canadabasketdata/baskets.json',
        'site/chinabasketdata/baskets.json',
        'site/chinabasketdata/narrative_emergence.json',
        'site/coming-soon.html',
        'site/data/portfolio_ctx.json',
        'site/factordata/alerts_triage.json',
        'site/factordata/basket_washout_state.json',
        'site/factordata/china_standouts.json',
        'site/factordata/dna_class.json',
        'site/factordata/factors.json',
        'site/factordata/impulse.json',
        'site/factordata/reflexivity_overlay.json',
        'site/factordata/signal_gate.json',
        'site/factordata/stock_personality.json',
        'site/factordata/us_standouts.json',
        'site/factordata/us_standouts_v2.json',
        'site/flowleaders/leaders.json',
        'site/government-revenue-data/defense-economics.json',
        'site/government-revenue-data/program-theme-context.json',
        'site/government-revenue-data/research-state.json',
        'site/government-revenue-data/sbir-progression.json',
        'site/government-revenue-data/theme-context.json',
        'site/hkbasketdata/baskets.json',
        'site/leaderradar/radar.json',
        'site/marketdata/subsector_rotation.json',
        'site/master_brief.json',
        'site/neuralwebdata/theme_state.json',
        'site/prophet/index.json',
        'site/turn_watch/turn_watch.json',
        'site/vol/regime.json',
    )
    manifest = yaml.safe_load((ROOT / ".github/ci/legacy-jobs.yml").read_text())
    job = manifest["jobs"]["bea-gvc-current-descriptive-consumer"]
    assert job["scope"] == "exclusive" and job["gate"] == "code"
    missing = sorted(set(hosted_dependencies) - set(job["paths"]))
    assert not missing, f"Full-checkout source dependencies are undeclared: {missing}"
