"""Guard the narrow E3FMT R2->R3 source-evidence adjudication."""
import hashlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1] / "research/earnings_intelligence/e3"
R2 = ROOT / "tfg1_development_boundary_identity_adjudication_r2.json"
R3 = ROOT / "tfg1_development_boundary_identity_adjudication_r3.json"
ADDED = {"MBLY/2026Q2", "LTH/2026Q2", "BANR/2026Q2", "HTGC/2026Q2"}
CLEAN = {
    "OCSL/2026Q3", "GEF/2026Q3", "ARQQ/2026Q2", "UPBD/2026Q2",
    "SCCO/2026Q2", "AGM/2026Q2", "COF/2026Q2", "KREF/2026Q2",
}


def load():
    return json.loads(R2.read_text()), json.loads(R3.read_text())


def index(d):
    result = {row["pair"]: row for row in d["per_call"]}
    assert len(result) == len(d["per_call"]) == 16
    return result


def test_r3_amends_pinned_r2_without_rewriting_or_using_holdout():
    a, b = load()
    assert a["schema"].endswith(".r2") and b["schema"].endswith(".r3")
    assert b["amends"]["sha256"] == hashlib.sha256(R2.read_bytes()).hexdigest()
    assert b["source_operation_key"] == a["successor_operation_key"]
    assert b["status"].endswith("PENDING_PROTECTED_MERGE")
    assert "ratified_at" not in b
    assert b["method_law_unchanged"] is b["holdout_law_unchanged"] is True
    assert a["holdout_bodies_inspected"] == b["holdout_bodies_inspected"] == 0
    assert a["model_calls"] == b["model_calls"] == 0
    assert a["holdout_gate"] == b["holdout_gate"]


@pytest.mark.parametrize("field", [
    "calls", "true_question_handoffs",
    "direct_operator_next_speaker_matches", "explicit_full_name_proxy_handoffs",
    "source_supported_questioner_handoffs", "unresolved_questioner_handoffs",
])
def test_previously_adjudicated_count_unchanged(field):
    a, b = load()
    assert a["summary"][field] == b["summary"][field]


def test_exact_structural_source_sets_never_relabelled():
    a, b = load()
    lhs, rhs = index(a), index(b)
    assert set(lhs) == set(rhs)
    for pair in lhs:
        for key in (
            "true_question_handoff_indices", "direct_next_speaker_match_indices",
            "explicit_full_name_proxy_indices", "unresolved_questioner_indices",
        ):
            assert lhs[pair][key] == rhs[pair][key], (pair, key)
    assert a["proxy_law"] == b["proxy_law"]
    assert a["structural_separator_law"] == b["structural_separator_law"]
    assert a["three_omissions"] == b["three_omissions"]


def test_only_fang_moves_from_clean_to_refused():
    a, b = load()
    lhs, rhs = index(a), index(b)
    changed = {k for k in lhs if lhs[k]["source_clean_for_full_call_reconstruction"]
               != rhs[k]["source_clean_for_full_call_reconstruction"]}
    assert changed == {"FANG/2026Q2"}
    fang = rhs["FANG/2026Q2"]
    assert fang["source_clean_for_full_call_reconstruction"] is False
    assert fang["unresolved_questioner_indices"] == []
    assert fang["expected_refusal"] == "management_identity_insufficient at answerer segment 92"
    assert b["respondent_falsifier_evidence"]["fang_same_revision_roster_has_title"] is False


def test_corrected_partition_is_complete_and_disjoint():
    _, b = load()
    summary = b["summary"]
    good = set(summary["source_clean_call_pairs"])
    bad = set(summary["source_conflicted_or_identity_refusal_pairs"])
    assert len(good) == len(bad) == 8
    assert summary["source_clean_calls_for_full_call_reconstruction"] == 8
    assert good == CLEAN and not (good & bad)
    assert good | bad == set(index(b))
    assert all(row["source_clean_for_full_call_reconstruction"] == (row["pair"] in good)
               for row in b["per_call"])


def test_only_four_extra_declared_role_conflicts():
    a, b = load()
    lhs, rhs = index(a), index(b)
    changed = {k for k in lhs if lhs[k]["management_role_conflict"] != rhs[k]["management_role_conflict"]}
    assert changed == ADDED
    assert {k for k in rhs if rhs[k]["management_role_conflict"]} == ADDED | {"CTRE/2026Q2", "ARRY/2026Q2"}
    assert b["summary"]["calls_with_explicit_management_role_conflict"] == 6
    for pair in ADDED:
        assert lhs[pair]["source_clean_for_full_call_reconstruction"] is False
        assert rhs[pair]["source_clean_for_full_call_reconstruction"] is False


def test_provenance_and_source_supported_role_law_preserved():
    a, b = load()
    assert b["respondent_falsifier_evidence"]["pr"] == 7530
    assert b["respondent_falsifier_evidence"]["head_sha"] == "5f167f1fd16e3737d5996b7521c4920924d3bc33"
    assert b["respondent_falsifier_evidence"]["holdout_bodies_inspected"] == 0
    assert "qa_exchange.v1" in b["respondent_role_law"]
    assert "8/8 source-clean" in b["development_gate"]
    assert "7 exchanges / 26 answer turns / 68 replay spans" in b["development_gate"]
    assert "9 source-clean" in a["development_gate"]
