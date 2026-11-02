"""Research-pointer extension review stays non-admitting and bound to source-intake bytes."""
from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from engine.theme_graph.membership_evidence import (
    build_microtheme_addendum_review, render_microtheme_addendum_markdown,
)

ROOT = Path(__file__).resolve().parents[1]
INPUTS = ROOT / "research/theme_graph/micro_member_research_addendum_20261016"
ORIGINAL = ROOT / "research/theme_graph/microtheme_membership_candidates_2026-10-08.json"
ADDENDUM = INPUTS / "research_addendum.json"
CLI = ROOT / "scripts/explain_theme_overlap.py"


@pytest.fixture(scope="module")
def baseline():
    return json.loads(ORIGINAL.read_text()), json.loads(ADDENDUM.read_text())


@pytest.fixture
def packet(baseline):
    return copy.deepcopy(baseline)


def view(packet, **kwargs):
    return build_microtheme_addendum_review(packet[0], packet[1], **kwargs)


def test_real_addendum_review_counts_and_authority(packet):
    a = view(packet)
    assert a["schema"] == "gmi.microtheme_member_research_addendum_review/v1"
    assert a["availability"] == "SOURCE_POINTERS_STRUCTURALLY_REVIEWABLE_UNADMITTED"
    assert a["authority_ceiling"] == "research_internal_only"
    c = a["counts"]
    assert c["original_activity_records"] == 103
    assert c["additional_activity_proposals"] == 46
    assert c["additional_negative_proposals"] == 7
    assert c["additional_scope_holds"] == 7
    assert c["additional_source_pointers"] == 58
    assert c["existing_micro_count"] == 68
    assert c["new_micro_ids"] == 0
    assert c["single_candidate_micros_before"] == 41
    assert c["single_candidate_micros_if_all_additions_accepted"] == 16
    assert c["undated_additional_candidate_rows"] == 36
    assert c["canonical_membership_admissions"] == 0
    assert c["dataos_identities_qualified"] == 0
    assert c["measurement_cohorts_admitted"] == 0
    assert len(a["candidate_activity_roles"]) == 46
    assert len(a["negative_cases"]) == len(a["scope_holds"]) == 7
    assert all(x["canonical_security_id"] is None for x in a["candidate_activity_roles"])
    assert all(not x["measurement_eligible"] for x in a["candidate_activity_roles"])
    assert all(not x["may_rank"] and not x["may_gate"] and not x["may_size"] and not x["may_trade"]
               for x in a["candidate_activity_roles"])
    assert all(x["independently_authenticated"] is False
               and x["source_use_qualification"] == "NOT_PERFORMED"
               for x in a["source_references"].values())
    assert sum(a["source_stage_counts"].values()) == 46


@pytest.mark.parametrize("change", [
    lambda p: p[1]["authority"].__setitem__("trading", True),
    lambda p: p[1]["authority"].__setitem__("canonical_membership", True),
    lambda p: p[1]["source_provenance"].__setitem__("source_rights_certified", True),
    lambda p: p[1]["source_provenance"].__setitem__("original_canonical_research_sha256", "0" * 64),
    lambda p: p[1]["population"].__setitem__("additional_activity_proposals", 45),
    lambda p: p[1]["population"].__setitem__("single_candidate_micros_if_all_additions_accepted", 8),
    lambda p: p[1]["proposed_activity_roles"][0].__setitem__("canonical_security_id", "SEC:US-XNYS-FAKE"),
    lambda p: p[1]["proposed_activity_roles"][0].__setitem__("measurement_eligible", True),
    lambda p: p[1]["proposed_activity_roles"][0].__setitem__("may_rank", True),
    lambda p: p[1]["proposed_activity_roles"][0].__setitem__("micro_id", "theme:unsourced_micro"),
    lambda p: p[1]["proposed_activity_roles"][0].__setitem__("entity_name", "invented name"),
    lambda p: p[1]["proposed_activity_roles"][0].__setitem__("product_or_activity", "invented role"),
    lambda p: p[1]["proposed_activity_roles"][0].__setitem__("qualification_note", "approved fully"),
    lambda p: p[1]["proposed_activity_roles"][0].__setitem__("origin_pointer", "hidden"),
    lambda p: p[1]["proposed_activity_roles"][0].__setitem__("source_ids", ["U0000000000000000"]),
    lambda p: p[1]["proposed_activity_roles"].append(copy.deepcopy(p[1]["proposed_activity_roles"][0])),
    lambda p: p[1]["negative_cases"][0].__setitem__("authority", "HUMAN_GOLD_LABEL"),
    lambda p: p[1]["negative_cases"][0].__setitem__("disposition_reason", "pretend adjudication"),
    lambda p: p[1]["scope_holds"][0].__setitem__("origin_pointer", "alternate"),
    lambda p: p[1]["sources"][next(iter(p[1]["sources"]))].__setitem__("source_use_qualification", "PUBLIC_REDIS"),
    lambda p: p[1]["sources"][next(iter(p[1]["sources"]))].__setitem__("independently_authenticated", True),
    lambda p: p[1]["sources"][next(iter(p[1]["sources"]))].__setitem__("url", "http://localhost/fake"),
    lambda p: p[1]["sources"][next(iter(p[1]["sources"]))].__setitem__("published_on", "2099-01-01"),
    lambda p: p[1].__setitem__("runtime_member_map", {"MU": "theme:hbm_packaging"}),
])
def test_mutations_refuse_admission_role_publisher_and_counts(packet, change):
    change(packet)
    with pytest.raises((ValueError, TypeError), match="microtheme research refused"):
        view(packet)


def test_intake_hash_refuses_changed_raw_rows(packet, tmp_path):
    for filename in ("intake.tsv", "negative_intake.tsv", "scope_holds.tsv"):
        (tmp_path / filename).write_bytes((INPUTS / filename).read_bytes())
    p = tmp_path / "intake.tsv"
    p.write_text(p.read_text().replace("MKS Instruments", "fake product", 1))
    with pytest.raises(ValueError, match="research intake bytes differ"):
        view(packet, intake_dir=tmp_path)


def test_unchanged_intake_hash_does_not_justify_modified_compiled_role(packet, tmp_path):
    for filename in ("intake.tsv", "negative_intake.tsv", "scope_holds.tsv"):
        (tmp_path / filename).write_bytes((INPUTS / filename).read_bytes())
    p = tmp_path / "intake.tsv"
    p.write_text(p.read_text().replace("MKS Instruments", "fake product", 1))
    packet[1]["source_provenance"]["intake_tsv_sha256"] = hashlib.sha256(p.read_bytes()).hexdigest()
    with pytest.raises(ValueError, match="research role absent from original intake"):
        view(packet, intake_dir=tmp_path)


def test_source_date_and_publisher_are_bound_to_intake(packet):
    src = next(iter(packet[1]["sources"].values()))
    src["publisher_hint"] = "Forged Publisher"
    with pytest.raises(ValueError, match="compiled source pointer changed from intake"):
        view(packet)


def test_source_research_not_mutated_and_escapes_markdown(packet):
    source_before = json.dumps(packet, sort_keys=True)
    result = view(packet)
    result["candidate_activity_roles"][0]["entity_name"] = "new|<script>"
    assert json.dumps(packet, sort_keys=True) == source_before
    output = render_microtheme_addendum_markdown(result)
    assert "new&#124;&lt;script&gt;" in output
    assert "NOT ADMITTED" in output
    assert "Source bodies, issuer/legal identities" in output


def test_cli_addendum_json_and_markdown_human_readable(tmp_path):
    for fmt in ("json", "markdown"):
        proc = subprocess.run([
            sys.executable, str(CLI),
            "--microtheme-research", str(ORIGINAL),
            "--microtheme-addendum", str(ADDENDUM),
            "--format", fmt,
        ], cwd=ROOT, text=True, capture_output=True, check=False)
        assert proc.returncode == 0, proc.stderr
        if fmt == "json":
            result = json.loads(proc.stdout)
            assert result["counts"]["additional_activity_proposals"] == 46
            assert result["counts"]["canonical_membership_admissions"] == 0
        else:
            assert "NOT ADMITTED" in proc.stdout
            assert "46 unadmitted additional role proposals" in proc.stdout


def test_cli_addendum_refuses_review_mode_identity_flags_and_output_overwrite():
    for cmd in (
        ["--review", str(ORIGINAL), "--microtheme-addendum", str(ADDENDUM)],
        ["--microtheme-research", str(ORIGINAL), "--microtheme-addendum", str(ADDENDUM),
         "--issuer-reference", "dummy.parquet", "--security-reference", "dummy.parquet"],
        ["--microtheme-research", str(ORIGINAL), "--microtheme-addendum", str(ADDENDUM),
         "--out", str(ADDENDUM)],
    ):
        proc = subprocess.run([sys.executable, str(CLI), *cmd], cwd=ROOT,
                              text=True, capture_output=True, check=False)
        assert proc.returncode == 2
        assert json.loads(proc.stderr)["code"] == "MICROTHEME_ADDENDUM_UNAVAILABLE"
