
"""GMI research-review consumer: no taxonomy admission, security identity or signal authority."""
from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from engine.theme_graph.membership_evidence import (
    build_microtheme_research_evidence,
    render_microtheme_research_markdown,
)

ROOT = Path(__file__).resolve().parents[1]
RESEARCH = ROOT / "research/theme_graph/microtheme_membership_candidates_2026-10-08.json"
CLI = ROOT / "scripts/explain_theme_overlap.py"


@pytest.fixture(scope="module")
def source_document():
    return json.loads(RESEARCH.read_text(encoding="utf-8"))


@pytest.fixture
def document(source_document):
    return copy.deepcopy(source_document)


def test_micro_research_real_document_is_readable_and_nonauthoritative(document):
    result = build_microtheme_research_evidence(document)
    assert result["schema"] == "gmi.microtheme_membership_review/v1"
    assert result["availability"]["state"] == "STRUCTURALLY_REVIEWABLE_NOT_ADMITTED"
    assert result["counts"]["micro_definitions"] == 68
    assert result["counts"]["subtheme_definitions"] == 12
    assert result["counts"]["parent_relationships"] == 132
    assert result["counts"]["candidate_activity_records"] == 103
    assert result["counts"]["source_references"] == 100
    assert result["counts"]["negative_cases"] == 14
    assert result["counts"]["cpu_scope_reviews"] == 3
    assert result["counts"]["canonical_memberships_admitted"] == 0
    assert result["counts"]["dataos_identities_qualified"] == 0
    assert result["counts"]["measurement_cohorts_admitted"] == 0
    assert all(x is False for x in result["authority"].values())
    assert all(x["canonical_security_id"] is None for x in result["candidates"])
    assert all(x["admission_status"] == "UNADMITTED_RESEARCH" for x in result["candidates"])
    assert all(x["measurement_eligible"] is False for x in result["candidates"])
    assert any(x["micro_id"] == "theme:hbm_packaging" for x in result["candidates"])
    assert any(x["parent_subtheme_ids"] for x in result["microthemes"])


def test_micro_research_no_runtime_graph_or_provider_needed(document, monkeypatch):
    from engine.theme_graph import store
    def refuse(*args, **kwargs):
        raise AssertionError("unexpected graph/data read or write")
    for name in ("read_nodes", "read_edges", "write_nodes", "write_edges"):
        monkeypatch.setattr(store, name, refuse)
    assert build_microtheme_research_evidence(document)["counts"]["candidate_activity_records"] == 103


def test_micro_research_no_input_mutation(document):
    previous = json.dumps(document, sort_keys=True)
    result = build_microtheme_research_evidence(document)
    result["candidates"][0]["role"] = "changed in output only"
    assert json.dumps(document, sort_keys=True) == previous


def test_micro_research_crosswalk_byte_fence(document, tmp_path):
    target = tmp_path / "crosswalk.yml"
    target.write_bytes((ROOT / "config/theme_crosswalk.yml").read_bytes() + b"\n# nonsemantic but different bytes\n")
    with pytest.raises(ValueError, match="crosswalk bytes differ"):
        build_microtheme_research_evidence(document, crosswalk_path=target)


@pytest.mark.parametrize("mutation", [
    lambda d: d["authority"].__setitem__("ranking", True),
    lambda d: d.__setitem__("runtime_member_map", {"AAPL": "theme:hbm_packaging"}),
    lambda d: d["microthemes"][0].__setitem__("admitted", True),
    lambda d: d["subthemes"][0].__setitem__("rank_weight", 1),
    lambda d: d["candidates"][0].__setitem__("rank_score", 1),
    lambda d: d["sources"]["S001"].__setitem__("public_display_allowed", True),
    lambda d: d["negative_cases"][0].__setitem__("reviewed_by", "human"),
    lambda d: d["population"].__setitem__("complete_global_membership", True),
    lambda d: d["population"].__setitem__("canonical_memberships_admitted", 1),
    lambda d: d["population"].__setitem__("candidate_activity_records", 99),
    lambda d: d["population"]["source_stage_counts"].__setitem__("OFFERED_PRODUCT", 1),
    lambda d: d["microthemes"][0].__setitem__("micro_id", "theme:invented_runtime_micro"),
    lambda d: d["microthemes"].append(copy.deepcopy(d["microthemes"][0])),
    lambda d: d["microthemes"][0].__setitem__("parent_theme_ids", ["theme:wrong_parent"]),
    lambda d: d["subthemes"][0].__setitem__("children", ["theme:fake_child"]),
    lambda d: d["candidates"][0].__setitem__("record_id", d["candidates"][1]["record_id"]),
    lambda d: d["candidates"][0].__setitem__("micro_id", "theme:invented_runtime_micro"),
    lambda d: d["candidates"][0].__setitem__("stage", "PROVEN_TRADING_SIGNAL"),
    lambda d: d["candidates"][0].__setitem__("admission_status", "RATIFIED"),
    lambda d: d["candidates"][0].__setitem__("proposed_by", "operator"),
    lambda d: d["candidates"][0].__setitem__("identity_status", "QUALIFIED"),
    lambda d: d["candidates"][0].__setitem__("canonical_security_id", "security:FAKE"),
    lambda d: d["candidates"][0].__setitem__("economic_share", 0.8),
    lambda d: d["candidates"][0].__setitem__("valid_from", "2025-01-01"),
    lambda d: d["candidates"][0].__setitem__("measurement_eligible", True),
    lambda d: d["candidates"][0].__setitem__("current_operation_asserted", True),
    lambda d: d["candidates"][0]["source_ids"].append("S999"),
    lambda d: d["negative_cases"][0].__setitem__("adjudication", "HUMAN_APPROVED"),
    lambda d: d["cpu_scope_review"][0].__setitem__("canonical_micro_id", "theme:cpu"),
    lambda d: d["sources"]["S001"].__setitem__("rights_use_qualification", "PUBLIC_GRANTED"),
    lambda d: d["sources"]["S001"].__setitem__("full_document_archived", True),
    lambda d: d["sources"]["S001"].__setitem__("url", "file:///etc/passwd"),
    lambda d: d["sources"]["S001"].__setitem__("url", "https://127.0.0.1/secret"),
    lambda d: d["sources"]["S001"].__setitem__("url", "https://localhost/private"),
    lambda d: d["sources"]["S001"].__setitem__("published_on", "2027-01-01"),
    lambda d: d["sources"]["S001"].__setitem__("publication_precision", "YEAR"),
    lambda d: d["source_pin"].__setitem__("crosswalk_sha256", "0" * 64),
    lambda d: d.__setitem__("schema", "gmi.microtheme_membership_research/v2"),
])
def test_micro_research_adversarial_refusals(document, mutation):
    mutation(document)
    with pytest.raises(ValueError, match="microtheme research refused"):
        build_microtheme_research_evidence(document)


def test_micro_research_valid_undated_year_and_day_source_precision(document):
    result = build_microtheme_research_evidence(document)
    assert result["sources"]["S007"]["published_on"] is None
    assert result["sources"]["S006"]["publication_precision"] == "YEAR"
    assert result["sources"]["S033"]["publication_precision"] == "DAY"


def test_micro_research_markdown_escapes_untrusted_strings(document):
    document["candidates"][0]["entity_name"] = "<script>alert(1)</script>|Broken"
    result = build_microtheme_research_evidence(document)
    md = render_microtheme_research_markdown(result)
    assert "<script>" not in md
    assert "&lt;script&gt;" in md
    assert "&#124;Broken" in md
    assert "UNADMITTED RESEARCH" in md
    assert "https://" in md


def _run_cli(*args):
    return subprocess.run(
        [sys.executable, str(CLI), *args],
        cwd=ROOT, capture_output=True, text=True, timeout=15
    )


def test_micro_research_cli_json_markdown_and_nonoverwrite(tmp_path):
    before = hashlib.sha256(RESEARCH.read_bytes()).hexdigest()
    js = _run_cli("--microtheme-research", str(RESEARCH), "--format", "json")
    assert js.returncode == 0, js.stderr
    body = json.loads(js.stdout)
    assert body["counts"]["candidate_activity_records"] == 103
    assert body["counts"]["canonical_memberships_admitted"] == 0
    md_path = tmp_path / "review.md"
    md = _run_cli("--microtheme-research", str(RESEARCH),
                  "--format", "markdown", "--out", str(md_path))
    assert md.returncode == 0, md.stderr
    assert "UNADMITTED RESEARCH" in md_path.read_text()
    assert _run_cli("--microtheme-research", str(RESEARCH), "--out", str(md_path)).returncode == 2
    assert _run_cli("--microtheme-research", str(RESEARCH), "--out", str(RESEARCH)).returncode == 2
    assert hashlib.sha256(RESEARCH.read_bytes()).hexdigest() == before


def test_micro_research_cli_refuses_invalid_without_output(tmp_path, document):
    document["authority"]["ranking"] = True
    bad = tmp_path / "research.json"
    bad.write_text(json.dumps(document))
    result = tmp_path / "never_written.json"
    process = _run_cli("--microtheme-research", str(bad), "--out", str(result))
    assert process.returncode == 2
    assert not result.exists()
    body = json.loads(process.stderr)
    assert body["schema"] == "gmi.microtheme_membership_review_refusal/v1"


def test_legacy_review_cli_requirement_retained():
    process = _run_cli("--format", "json")
    assert process.returncode != 0
    assert "--review" in process.stderr
